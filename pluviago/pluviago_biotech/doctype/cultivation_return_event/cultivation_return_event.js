frappe.ui.form.on('Cultivation Return Event', {
    refresh(frm) {
        // Always read-only audit log — make that clear
        frm.dashboard.set_headline_alert(
            __('Audit log — created automatically by the Return to Flask action. All fields are read-only.'),
            'blue'
        );

        // Summarise volumes in the intro bar
        const withdrawal = frm.doc.withdrawal_volume || 0;
        const dilution   = frm.doc.dilution_volume || 0;
        const total      = frm.doc.total_volume_to_flask || (withdrawal + dilution);
        if (total > 0) {
            frm.set_intro(
                __('Total volume to Flask: <b>{0} L</b> &nbsp;({1} L culture withdrawn + {2} L medium dilution)',
                    [total.toFixed(3), withdrawal.toFixed(3), dilution.toFixed(3)]),
                'blue'
            );
        }
    }
});
