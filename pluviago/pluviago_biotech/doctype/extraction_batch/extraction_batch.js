frappe.ui.form.on('Extraction Batch', {
    refresh(frm) {
        if (frm.doc.docstatus === 1 && frm.doc.status === 'Dispatched') {
            frm.set_intro('Batch has been dispatched to extraction partner.', 'blue');
        }
        if (frm.doc.docstatus === 1 && frm.doc.status === 'Completed') {
            frm.set_intro('Extraction process completed.', 'green');
        }
    }
});
