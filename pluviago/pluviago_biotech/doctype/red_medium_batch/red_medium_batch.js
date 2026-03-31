frappe.ui.form.on('Red Medium Batch', {
    final_required_volume(frm) {
        frm.set_value('red_volume_calculated', (frm.doc.final_required_volume || 0) * 0.25);
    },

    refresh(frm) {
        // Mark Preparation Complete button
        if (frm.doc.docstatus === 0 && frm.doc.preparation_status === 'Draft') {
            frm.add_custom_button(__('Mark Preparation Complete'), function () {
                frappe.confirm(
                    'Confirm that all direct chemicals and stock solutions have been physically added. '
                    + 'Stock will be deducted from Raw Material Batches. This cannot be undone.',
                    function () {
                        frappe.call({
                            method: 'mark_preparation_complete',
                            doc: frm.doc,
                            callback: function (r) {
                                frm.reload_doc();
                            }
                        });
                    }
                );
            }, __('Actions')).addClass('btn-primary');
        }

        // Mark as Wasted button
        if (frm.doc.docstatus === 0 && frm.doc.preparation_status === 'QC Pending') {
            frm.add_custom_button(__('Mark as Wasted'), function () {
                frappe.prompt(
                    { label: 'Reason for Waste', fieldname: 'reason', fieldtype: 'Text' },
                    function (values) {
                        frappe.call({
                            method: 'mark_wasted',
                            doc: frm.doc,
                            args: { reason: values.reason || '' },
                            callback: function (r) {
                                frm.reload_doc();
                            }
                        });
                    },
                    __('Mark Batch as Wasted (QC Failed)'),
                    __('Confirm Waste')
                );
            }, __('Actions')).addClass('btn-danger');
        }

        // Raise OOS Investigation button (Task 3.3)
        if (
            frm.doc.preparation_status === 'QC Pending' &&
            frm.doc.overall_qc_status === 'Failed'
        ) {
            frm.add_custom_button(__('Raise OOS Investigation'), function () {
                frappe.new_doc('OOS Investigation', {
                    linked_doctype: 'Red Medium Batch',
                    linked_batch: frm.doc.name,
                    reported_by: frappe.session.user
                });
            }, __('Actions'));
        }

        // Status indicators
        if (frm.doc.preparation_status === 'Draft') {
            frm.set_intro('Add direct chemicals and link stock solutions (A4–A7, A5M), then click Mark Preparation Complete.', 'blue');
        } else if (frm.doc.preparation_status === 'QC Pending') {
            frm.set_intro('Preparation complete. Complete QC Checkpoints 3 & 4. Submit if passed, or Mark as Wasted if failed.', 'orange');
        } else if (frm.doc.preparation_status === 'Released') {
            frm.set_intro('Red Medium batch released. Available for Final Medium formulation.', 'green');
        } else if (frm.doc.preparation_status === 'Wasted') {
            frm.set_intro('This batch was wasted (QC failed). Stock loss has been logged.', 'red');
        }

        // Quality Flag badge
        if (frm.doc.quality_flag === 'Conditional Release') {
            frm.set_intro('⚠️ Quality Flag: Conditional Release — batch passed after corrective action.', 'yellow');
        } else if (frm.doc.quality_flag === 'Rejected') {
            frm.set_intro('🚫 Quality Flag: Rejected — batch failed QC and cannot be used.', 'red');
        }
    }
});
