frappe.ui.form.on('Pluviago Strain', {
    refresh(frm) {
        // ── Headline alerts by status ────────────────────────────────────────
        const status = frm.doc.status;
        if (status === 'In Use') {
            frm.dashboard.set_headline_alert(
                __('Strain is actively being cultured in one or more Production Batches.'),
                'blue'
            );
        } else if (status === 'Quarantined') {
            frm.dashboard.set_headline_alert(
                __('This strain is under quarantine — do not use for new batches.'),
                'orange'
            );
        } else if (status === 'Retired') {
            frm.dashboard.set_headline_alert(__('This strain has been retired.'), 'grey');
        }

        // ── Update Generation Count button ───────────────────────────────────
        if (!frm.is_new()) {
            frm.add_custom_button(__('Update Generation Count'), function() {
                frappe.call({
                    method: 'update_generation_count',
                    doc: frm.doc,
                    freeze: true,
                    freeze_message: __('Counting cultivation cycles...'),
                    callback(r) {
                        if (r.message !== undefined) frm.reload_doc();
                    }
                });
            }, __('Actions'));
        }
    },

    status(frm) {
        if (frm.doc.status === 'In Use') {
            frappe.show_alert({
                message: __('Set to "In Use" when a Production Batch using this strain is active. This is informational only.'),
                indicator: 'blue'
            }, 5);
        }
    }
});
