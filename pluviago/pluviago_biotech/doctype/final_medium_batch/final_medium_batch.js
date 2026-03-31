frappe.ui.form.on('Final Medium Batch', {
    final_required_volume(frm) {
        if (frm.doc.final_required_volume) {
            frm.set_value('green_medium_volume', frm.doc.final_required_volume * 0.75);
            frm.set_value('red_medium_volume', frm.doc.final_required_volume * 0.25);
        }
    }
});
