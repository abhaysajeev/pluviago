frappe.ui.form.on('Stock Solution Batch', {
    refresh(frm) {
        // Mark Preparation Complete button
        if (frm.doc.docstatus === 0 && frm.doc.preparation_status === 'Draft') {
            frm.add_custom_button(__('Mark Preparation Complete'), function () {
                frappe.confirm(
                    'Confirm that all chemicals have been physically added and preparation is complete. '
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

        // Status indicators
        if (frm.doc.preparation_status === 'Draft') {
            frm.set_intro('Fill in ingredients and sterilisation details, then click Mark Preparation Complete.', 'blue');
        } else if (frm.doc.preparation_status === 'QC Pending') {
            frm.set_intro('Preparation complete. Fill in QC results. Submit if passed, or Mark as Wasted if failed.', 'orange');
        } else if (frm.doc.preparation_status === 'Released') {
            frm.set_intro('Batch released and available for use in medium preparation.', 'green');
        } else if (frm.doc.preparation_status === 'Wasted') {
            frm.set_intro('This batch was wasted (QC failed). Stock loss has been logged.', 'red');
        }
    }
});
