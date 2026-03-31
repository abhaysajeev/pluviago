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
        // ── Create Next Stage Batch (normal scale-up) ──────────────────────
        if (frm.doc.docstatus === 1 && frm.doc.stage_decision === 'Scale Up') {
            frm.add_custom_button('Create Next Stage Batch', function() {
                frappe.new_doc('Production Batch', {
                    parent_batch: frm.doc.name,
                    strain: frm.doc.strain,
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

        // ── Return to Flask (back-propagation) ─────────────────────────────
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

        // ── Split Batch (Task 2.2) ──────────────────────────────────────────
        // One parent seeds multiple reactors simultaneously.
        if (
            frm.doc.docstatus === 1 &&
            !['Harvested', 'Disposed'].includes(frm.doc.status)
        ) {
            frm.add_custom_button('Split Batch', function() {
                _show_split_dialog(frm);
            }, 'Actions');
        }
    }
});


// ── Return-to-Cultivation dialog ───────────────────────────────────────────

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


// ── Split Batch dialog (Task 2.2) ──────────────────────────────────────────

function _show_split_dialog(frm) {
    // Build next-stage options based on current stage
    const stageSequence = ['Flask', '25L PBR', '275L PBR', '925L PBR', '6600L PBR'];
    const currentIdx = stageSequence.indexOf(frm.doc.current_stage);
    const nextStage = currentIdx >= 0 && currentIdx < stageSequence.length - 1
        ? stageSequence[currentIdx + 1]
        : stageSequence[0];

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
                fieldtype: 'Select',
                reqd: 1,
                options: stageSequence.join('\n'),
                default: nextStage,
                description: 'Stage for all child batches'
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
                    medium_batch: values.medium_batch || null
                },
                freeze: true,
                freeze_message: `Creating ${values.n} batches...`,
                callback(r) {
                    if (r.message && r.message.length) {
                        frm.reload_doc();
                        // Navigate to the first child batch
                        frappe.set_route('Form', 'Production Batch', r.message[0]);
                    }
                }
            });
        }
    });
    dialog.show();
}
