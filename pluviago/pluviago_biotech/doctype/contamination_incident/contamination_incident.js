frappe.ui.form.on('Contamination Incident', {
    decision(frm) {
        if (frm.doc.decision === 'Dispose') {
            frappe.confirm(
                'Are you sure you want to mark the decision as Dispose? This will flag the production batch for disposal.',
                () => {
                    // confirmed - proceed
                },
                () => {
                    frm.set_value('decision', 'Pending');
                }
            );
        }
    }
});
