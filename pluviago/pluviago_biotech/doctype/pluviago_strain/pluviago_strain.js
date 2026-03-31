frappe.ui.form.on('Pluviago Strain', {
    refresh(frm) {
        if (frm.doc.status === 'Quarantined') {
            frm.dashboard.set_headline_alert(
                '<div class="alert alert-warning">This strain is under quarantine.</div>'
            );
        }
    }
});
