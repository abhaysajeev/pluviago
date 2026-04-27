frappe.ui.form.on('Harvest Batch', {
    actual_dry_weight(frm) {
        if (frm.doc.target_dry_weight) {
            frm.set_value('yield_percentage', (frm.doc.actual_dry_weight / frm.doc.target_dry_weight) * 100);
        }
    },
    refresh(frm) {
        // Confirm Packing — Approved → Packed
        if (frm.doc.docstatus === 1 && frm.doc.status === 'Approved') {
            frm.add_custom_button('Confirm Packing', function() {
                frappe.call({
                    method: 'confirm_packing',
                    doc: frm.doc,
                    freeze: true,
                    freeze_message: 'Confirming packing...',
                    callback() { frm.reload_doc(); }
                });
            }, 'Actions');
        }

        // Create Extraction Batch — available once Approved or Packed
        if (frm.doc.docstatus === 1 && ['Approved', 'Packed'].includes(frm.doc.status)) {
            frm.add_custom_button('Create Extraction Batch', function() {
                frappe.new_doc('Extraction Batch', {
                    harvest_batch: frm.doc.name
                });
            }, 'Actions');
        }
    }
});
