const STAGE_SEQUENCE = ['Flask', '25L PBR', '275L PBR', '925L PBR', '6600L PBR'];

frappe.ui.form.on('Production Batch', {
    onload(frm) {
        if (frm.is_new() && !frm.doc.start_date) {
            frm.set_value('start_date', frappe.datetime.get_today());
        }
    },

    stage_decision(frm) {
        if (frm.doc.stage_decision === 'Dispose') {
            frappe.msgprint({
                title: 'Contamination Alert',
                indicator: 'red',
                message: 'Batch marked for disposal. Please document and proceed with disposal protocol.'
            });
        }
        if (frm.doc.stage_decision && !frm.doc.decision_date) {
            frm.set_value('decision_date', frappe.datetime.get_today());
        }
        if (frm.doc.stage_decision && !frm.doc.decision_by) {
            frm.set_value('decision_by', frappe.session.user);
        }
    },

    refresh(frm) {
        // ── Headline alerts ──────────────────────────────────────────────────
        if (frm.doc.docstatus === 0) {
            const decision = frm.doc.stage_decision;
            if (!decision || decision === 'Pending') {
                frm.dashboard.set_headline_alert(
                    __('Draft — add QC readings and set Stage Decision before submitting.'),
                    'blue'
                );
            } else {
                frm.dashboard.set_headline_alert(
                    __('Ready to submit — Stage Decision: {0}. Submit to finalise this stage.', [decision]),
                    'yellow'
                );
            }
        } else if (frm.doc.docstatus === 1) {
            const sd = frm.doc.stage_decision;
            if (sd === 'Scale Up') {
                frm.dashboard.set_headline_alert(
                    __('Scaled Up — use Create Next Stage Batch to continue cultivation.'),
                    'green'
                );
            } else if (sd === 'Harvest') {
                frm.dashboard.set_headline_alert(
                    __('Harvested — create a Harvest Batch to record yield.'),
                    'yellow'
                );
            } else if (sd === 'Dispose') {
                frm.dashboard.set_headline_alert(__('Disposed — batch terminated.'), 'red');
            }
        } else if (frm.doc.docstatus === 2) {
            frm.dashboard.set_headline_alert(__('Cancelled.'), 'grey');
        }

        // ── Create Next Stage Batch (Scale Up → exactly next valid stage) ────
        if (frm.doc.docstatus === 1 && frm.doc.stage_decision === 'Scale Up') {
            frm.add_custom_button(__('Create Next Stage Batch'), function() {
                const currentIdx = STAGE_SEQUENCE.indexOf(frm.doc.current_stage);
                const nextStage = currentIdx >= 0 && currentIdx < STAGE_SEQUENCE.length - 1
                    ? STAGE_SEQUENCE[currentIdx + 1] : null;
                if (!nextStage) {
                    frappe.msgprint(__('No further cultivation stage. Use Harvest or Return to Flask.'));
                    return;
                }
                frappe.new_doc('Production Batch', {
                    parent_batch: frm.doc.name,
                    strain: frm.doc.strain,
                    current_stage: nextStage,
                    generation_number: (frm.doc.generation_number || 1) + 1,
                    final_medium_batch: frm.doc.final_medium_batch
                });
            }, __('Actions'));
        }

        // ── Create Harvest Batch ─────────────────────────────────────────────
        if (frm.doc.docstatus === 1 && frm.doc.stage_decision === 'Harvest') {
            frm.add_custom_button(__('Create Harvest Batch'), function() {
                frappe.new_doc('Harvest Batch', {
                    production_batch: frm.doc.name
                });
            }, __('Actions'));
        }

        // ── Return to Flask (back-propagation from 275L or 6600L only) ───────
        const returnEligible = ['275L PBR', '6600L PBR'];
        if (
            frm.doc.docstatus === 1 &&
            returnEligible.includes(frm.doc.current_stage) &&
            !['Harvested', 'Disposed'].includes(frm.doc.status)
        ) {
            frm.add_custom_button(__('Return to Flask'), function() {
                _show_return_dialog(frm);
            }, __('Actions'));
        }

        // ── Split Batch ──────────────────────────────────────────────────────
        if (
            frm.doc.docstatus === 1 &&
            !['Harvested', 'Disposed'].includes(frm.doc.status)
        ) {
            frm.add_custom_button(__('Split Batch'), function() {
                _show_split_dialog(frm);
            }, __('Actions'));
        }

        // ── Record Phase Transition (6600L only) ─────────────────────────────
        if (
            frm.doc.docstatus === 1 &&
            frm.doc.current_stage === '6600L PBR' &&
            !['Harvested', 'Disposed'].includes(frm.doc.status)
        ) {
            frm.add_custom_button(__('Record Phase Transition'), function() {
                _show_phase_transition_dialog(frm);
            }, __('Actions'));
        }

        // ── Final Medium Batch filter: only Approved / Partially Used ─────────
        frm.set_query('final_medium_batch', function() {
            return {
                filters: { docstatus: 1, status: ['in', ['Approved', 'Partially Used']] }
            };
        });
    }
});


// ── Auto-fail QC reading when contamination is detected ───────────────────────
frappe.ui.form.on('Production Batch QC', {
    contamination_detected(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (row.contamination_detected) {
            frappe.model.set_value(cdt, cdn, 'overall_result', 'Fail');
        }
    },

    qc_by(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (!row.qc_by) {
            frappe.model.set_value(cdt, cdn, 'qc_by', frappe.session.user);
        }
    }
});


// ── Return-to-Cultivation dialog ──────────────────────────────────────────────

function _show_return_dialog(frm) {
    const dialog = new frappe.ui.Dialog({
        title: __('Return to Flask — {0}', [frm.doc.name]),
        fields: [
            {
                label: __('Withdrawal Volume (L)'),
                fieldname: 'withdrawal_volume',
                fieldtype: 'Float',
                reqd: 1,
                description: __('Volume of culture withdrawn from this reactor')
            },
            {
                label: __('Dilution Medium Batch'),
                fieldname: 'dilution_medium_batch',
                fieldtype: 'Link',
                options: 'Final Medium Batch',
                description: __('Final Medium used to dilute the withdrawn culture')
            },
            {
                label: __('Dilution Volume (L)'),
                fieldname: 'dilution_volume',
                fieldtype: 'Float',
                description: __('Volume of medium added for dilution')
            },
            {
                label: __('Return Date'),
                fieldname: 'return_date',
                fieldtype: 'Date',
                reqd: 1,
                default: frappe.datetime.get_today()
            },
            {
                label: __('Returned By'),
                fieldname: 'returned_by',
                fieldtype: 'Link',
                options: 'User',
                default: frappe.session.user
            },
            {
                label: __('Reason / Notes'),
                fieldname: 'reason',
                fieldtype: 'Text'
            }
        ],
        primary_action_label: __('Confirm Return'),
        primary_action(values) {
            dialog.hide();
            frappe.call({
                method: 'create_return_batch',
                doc: frm.doc,
                args: {
                    withdrawal_volume: values.withdrawal_volume,
                    dilution_medium_batch: values.dilution_medium_batch || null,
                    dilution_volume: values.dilution_volume || 0,
                    return_date: values.return_date,
                    returned_by: values.returned_by,
                    reason: values.reason || ''
                },
                freeze: true,
                freeze_message: __('Creating Flask batch...'),
                callback(r) {
                    if (r.message) {
                        frm.reload_doc();
                        frappe.set_route('Form', 'Production Batch', r.message);
                    }
                }
            });
        }
    });
    dialog.show();
}


// ── Split Batch dialog ────────────────────────────────────────────────────────

function _show_split_dialog(frm) {
    const currentIdx = STAGE_SEQUENCE.indexOf(frm.doc.current_stage);
    const nextStage = currentIdx >= 0 && currentIdx < STAGE_SEQUENCE.length - 1
        ? STAGE_SEQUENCE[currentIdx + 1]
        : STAGE_SEQUENCE[0];

    const dialog = new frappe.ui.Dialog({
        title: __('Split Batch — {0}', [frm.doc.name]),
        fields: [
            {
                label: __('Number of Child Batches'),
                fieldname: 'n',
                fieldtype: 'Int',
                reqd: 1,
                default: 2,
                description: __('How many parallel batches to create (2–10)')
            },
            {
                label: __('Next Stage'),
                fieldname: 'next_stage',
                fieldtype: 'Data',
                reqd: 1,
                default: nextStage,
                read_only: 1,
                description: __('Only the immediate next stage is valid')
            },
            {
                label: __('Inoculation Date'),
                fieldname: 'inoculation_date',
                fieldtype: 'Date',
                reqd: 1,
                default: frappe.datetime.get_today()
            },
            {
                label: __('Medium Batch (optional)'),
                fieldname: 'medium_batch',
                fieldtype: 'Link',
                options: 'Final Medium Batch',
                description: __('Pre-fill on all child batches (can be changed later)')
            },
            {
                label: __('Inoculum Volume per Child (L)'),
                fieldname: 'inoculum_volume_per_child',
                fieldtype: 'Float',
                description: __('Optional — deducted from culture pool on each child submit')
            }
        ],
        primary_action_label: __('Create Child Batches'),
        primary_action(values) {
            if (values.n < 2 || values.n > 10) {
                frappe.msgprint(__('Number of batches must be between 2 and 10.'));
                return;
            }
            dialog.hide();
            frappe.call({
                method: 'create_split_batches',
                doc: frm.doc,
                args: {
                    n: values.n,
                    next_stage: values.next_stage,
                    inoculation_date: values.inoculation_date,
                    medium_batch: values.medium_batch || null,
                    inoculum_volume_per_child: values.inoculum_volume_per_child || null
                },
                freeze: true,
                freeze_message: __('Creating {0} batches...', [values.n]),
                callback(r) {
                    if (r.message && r.message.length) {
                        frm.reload_doc();
                        frappe.set_route('Form', 'Production Batch', r.message[0]);
                    }
                }
            });
        }
    });
    dialog.show();
}


// ── Phase Transition dialog (6600L only) ──────────────────────────────────────

function _show_phase_transition_dialog(frm) {
    const currentPhase = frm.doc.phase || 'N/A';
    const nextPhase = currentPhase === 'Green Phase' ? 'Red Phase' : 'Green Phase';

    const dialog = new frappe.ui.Dialog({
        title: __('Record Phase Transition — {0}', [frm.doc.name]),
        fields: [
            {
                label: __('Current Phase'),
                fieldname: 'current_phase',
                fieldtype: 'Data',
                default: currentPhase,
                read_only: 1
            },
            {
                label: __('New Phase'),
                fieldname: 'new_phase',
                fieldtype: 'Select',
                reqd: 1,
                options: 'Green Phase\nRed Phase',
                default: nextPhase,
                description: __('Green Phase → Red Phase transition is irreversible.')
            },
            {
                label: __('Transition Date'),
                fieldname: 'transition_date',
                fieldtype: 'Date',
                reqd: 1,
                default: frappe.datetime.get_today()
            },
            {
                label: __('Transitioned By'),
                fieldname: 'transitioned_by',
                fieldtype: 'Link',
                options: 'User',
                reqd: 1,
                default: frappe.session.user
            },
            {
                label: __('Notes'),
                fieldname: 'notes',
                fieldtype: 'Text',
                description: __('Reason or observations at phase transition point')
            }
        ],
        primary_action_label: __('Confirm Transition'),
        primary_action(values) {
            dialog.hide();
            frappe.call({
                method: 'record_phase_transition',
                doc: frm.doc,
                args: {
                    new_phase: values.new_phase,
                    transition_date: values.transition_date,
                    transitioned_by: values.transitioned_by,
                    notes: values.notes || ''
                },
                freeze: true,
                freeze_message: __('Recording phase transition...'),
                callback(r) {
                    frm.reload_doc();
                }
            });
        }
    });
    dialog.show();
}
