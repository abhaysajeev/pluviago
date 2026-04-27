const STAGE_SEQUENCE = ['Flask', '25L PBR', '275L PBR', '925L PBR', '6600L PBR'];

frappe.ui.form.on('Production Batch', {
    stage_decision(frm) {
        if (frm.doc.stage_decision === 'Dispose') {
            frappe.msgprint({
                title: 'Contamination Alert',
                indicator: 'red',
                message: 'Batch marked for disposal due to contamination. Please document and proceed with disposal protocol.'
            });
        }
    },

    refresh(frm) {
        // ── Create Next Stage Batch (enforced to exactly the next valid stage) ──
        if (frm.doc.docstatus === 1 && frm.doc.stage_decision === 'Scale Up') {
            frm.add_custom_button('Create Next Stage Batch', function() {
                const currentIdx = STAGE_SEQUENCE.indexOf(frm.doc.current_stage);
                const nextStage = currentIdx >= 0 && currentIdx < STAGE_SEQUENCE.length - 1
                    ? STAGE_SEQUENCE[currentIdx + 1] : null;
                if (!nextStage) {
                    frappe.msgprint('No further cultivation stage. Use Harvest or Return to Flask.');
                    return;
                }
                frappe.new_doc('Production Batch', {
                    parent_batch: frm.doc.name,
                    strain: frm.doc.strain,
                    current_stage: nextStage,
                    generation_number: (frm.doc.generation_number || 1) + 1,
                    final_medium_batch: frm.doc.final_medium_batch
                });
            }, 'Actions');
        }

        // ── Create Harvest Batch ────────────────────────────────────────────
        if (frm.doc.docstatus === 1 && frm.doc.stage_decision === 'Harvest') {
            frm.add_custom_button('Create Harvest Batch', function() {
                frappe.new_doc('Harvest Batch', {
                    production_batch: frm.doc.name
                });
            }, 'Actions');
        }

        // ── Return to Flask (back-propagation from 275L or 6600L only) ─────
        const returnEligible = ['275L PBR', '6600L PBR'];
        if (
            frm.doc.docstatus === 1 &&
            returnEligible.includes(frm.doc.current_stage) &&
            !['Harvested', 'Disposed'].includes(frm.doc.status)
        ) {
            frm.add_custom_button('Return to Flask', function() {
                _show_return_dialog(frm);
            }, 'Actions');
        }

        // ── Split Batch ─────────────────────────────────────────────────────
        if (
            frm.doc.docstatus === 1 &&
            !['Harvested', 'Disposed'].includes(frm.doc.status)
        ) {
            frm.add_custom_button('Split Batch', function() {
                _show_split_dialog(frm);
            }, 'Actions');
        }

        // ── Record Phase Transition (6600L only) ────────────────────────────
        if (
            frm.doc.docstatus === 1 &&
            frm.doc.current_stage === '6600L PBR' &&
            !['Harvested', 'Disposed'].includes(frm.doc.status)
        ) {
            frm.add_custom_button('Record Phase Transition', function() {
                _show_phase_transition_dialog(frm);
            }, 'Actions');
        }
    }
});


// ── Auto-fail QC reading when contamination is detected ───────────────────
frappe.ui.form.on('Production Batch QC', {
    contamination_detected(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (row.contamination_detected) {
            frappe.model.set_value(cdt, cdn, 'overall_result', 'Fail');
        }
    }
});


// ── Return-to-Cultivation dialog ──────────────────────────────────────────

function _show_return_dialog(frm) {
    const dialog = new frappe.ui.Dialog({
        title: `Return to Flask — ${frm.doc.name}`,
        fields: [
            {
                label: 'Withdrawal Volume (L)',
                fieldname: 'withdrawal_volume',
                fieldtype: 'Float',
                reqd: 1,
                description: 'Volume of culture withdrawn from this reactor'
            },
            {
                label: 'Dilution Medium Batch',
                fieldname: 'dilution_medium_batch',
                fieldtype: 'Link',
                options: 'Final Medium Batch',
                description: 'Final Medium used to dilute the withdrawn culture'
            },
            {
                label: 'Dilution Volume (L)',
                fieldname: 'dilution_volume',
                fieldtype: 'Float',
                description: 'Volume of medium added for dilution'
            },
            {
                label: 'Return Date',
                fieldname: 'return_date',
                fieldtype: 'Date',
                reqd: 1,
                default: frappe.datetime.get_today()
            },
            {
                label: 'Returned By',
                fieldname: 'returned_by',
                fieldtype: 'Link',
                options: 'User',
                default: frappe.session.user
            },
            {
                label: 'Reason / Notes',
                fieldname: 'reason',
                fieldtype: 'Text'
            }
        ],
        primary_action_label: 'Confirm Return',
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
                freeze_message: 'Creating Flask batch...',
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


// ── Split Batch dialog ────────────────────────────────────────────────────

function _show_split_dialog(frm) {
    const currentIdx = STAGE_SEQUENCE.indexOf(frm.doc.current_stage);
    const nextStage = currentIdx >= 0 && currentIdx < STAGE_SEQUENCE.length - 1
        ? STAGE_SEQUENCE[currentIdx + 1]
        : STAGE_SEQUENCE[0];

    const dialog = new frappe.ui.Dialog({
        title: `Split Batch — ${frm.doc.name}`,
        fields: [
            {
                label: 'Number of Child Batches',
                fieldname: 'n',
                fieldtype: 'Int',
                reqd: 1,
                default: 2,
                description: 'How many parallel batches to create (2–10)'
            },
            {
                label: 'Next Stage',
                fieldname: 'next_stage',
                fieldtype: 'Data',
                reqd: 1,
                default: nextStage,
                read_only: 1,
                description: 'Only the immediate next stage is valid'
            },
            {
                label: 'Inoculation Date',
                fieldname: 'inoculation_date',
                fieldtype: 'Date',
                reqd: 1,
                default: frappe.datetime.get_today()
            },
            {
                label: 'Medium Batch (optional)',
                fieldname: 'medium_batch',
                fieldtype: 'Link',
                options: 'Final Medium Batch',
                description: 'Pre-fill on all child batches (can be changed later)'
            },
            {
                label: 'Inoculum Volume per Child (L)',
                fieldname: 'inoculum_volume_per_child',
                fieldtype: 'Float',
                description: 'Optional — deducted from culture pool on each child submit'
            }
        ],
        primary_action_label: 'Create Child Batches',
        primary_action(values) {
            if (values.n < 2 || values.n > 10) {
                frappe.msgprint('Number of batches must be between 2 and 10.');
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
                freeze_message: `Creating ${values.n} batches...`,
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


// ── Phase Transition dialog (6600L only) ──────────────────────────────────

function _show_phase_transition_dialog(frm) {
    const currentPhase = frm.doc.phase || 'N/A';
    const nextPhase = currentPhase === 'Green Phase' ? 'Red Phase' : 'Green Phase';

    const dialog = new frappe.ui.Dialog({
        title: `Record Phase Transition — ${frm.doc.name}`,
        fields: [
            {
                label: 'Current Phase',
                fieldname: 'current_phase',
                fieldtype: 'Data',
                default: currentPhase,
                read_only: 1
            },
            {
                label: 'New Phase',
                fieldname: 'new_phase',
                fieldtype: 'Select',
                reqd: 1,
                options: 'Green Phase\nRed Phase',
                default: nextPhase,
                description: 'Green Phase → Red Phase transition is irreversible.'
            },
            {
                label: 'Transition Date',
                fieldname: 'transition_date',
                fieldtype: 'Date',
                reqd: 1,
                default: frappe.datetime.get_today()
            },
            {
                label: 'Transitioned By',
                fieldname: 'transitioned_by',
                fieldtype: 'Link',
                options: 'User',
                reqd: 1,
                default: frappe.session.user
            },
            {
                label: 'Notes',
                fieldname: 'notes',
                fieldtype: 'Text',
                description: 'Reason or observations at phase transition point'
            }
        ],
        primary_action_label: 'Confirm Transition',
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
                freeze_message: 'Recording phase transition...',
                callback(r) {
                    frm.reload_doc();
                }
            });
        }
    });
    dialog.show();
}
