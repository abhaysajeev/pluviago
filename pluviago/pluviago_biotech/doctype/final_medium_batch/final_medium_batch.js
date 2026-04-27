function calc_fmb_expiry(frm) {
    if (frm.doc.shelf_life_days && frm.doc.preparation_date) {
        frm.set_value('expiry_date',
            frappe.datetime.add_days(frm.doc.preparation_date, frm.doc.shelf_life_days));
    }
}

function check_medium_volume(frm, link_field, vol_field, expected_type, label) {
    const batch = frm.doc[link_field];
    const required = frm.doc[vol_field] || 0;
    if (!batch || !required) return;

    frappe.db.get_value('Medium Batch', batch, ['remaining_volume', 'status', 'medium_type'], (r) => {
        if (!r) return;
        if (r.medium_type && r.medium_type !== expected_type) {
            frappe.show_alert({
                message: __("{0} is a {1} batch, not {2}.", [batch, r.medium_type, expected_type]),
                indicator: 'red'
            });
            return;
        }
        if (!['Approved', 'Partially Used'].includes(r.status)) {
            frappe.show_alert({
                message: __("{0} batch {1} is not released (status: {2}).", [label, batch, r.status]),
                indicator: 'red'
            });
            return;
        }
        const remaining = r.remaining_volume || 0;
        if (required > remaining) {
            frappe.show_alert({
                message: __(
                    "{0} {1}: only {2} L remaining, but {3} L required.",
                    [label, batch, remaining.toFixed(3), required.toFixed(3)]
                ),
                indicator: 'orange'
            });
        }
    });
}

frappe.ui.form.on('Final Medium Batch', {
    onload(frm) {
        if (frm.is_new() && !frm.doc.prepared_by) {
            frm.set_value('prepared_by', frappe.session.user);
        }
        if (frm.is_new() && !frm.doc.preparation_date) {
            frm.set_value('preparation_date', frappe.datetime.get_today());
        }
    },

    final_required_volume(frm) {
        if (frm.doc.final_required_volume) {
            frm.set_value('green_medium_volume', frm.doc.final_required_volume * 0.75);
            frm.set_value('red_medium_volume',   frm.doc.final_required_volume * 0.25);
        }
    },

    green_medium_batch(frm) {
        check_medium_volume(frm, 'green_medium_batch', 'green_medium_volume', 'Green', 'Green Medium');
    },

    red_medium_batch(frm) {
        check_medium_volume(frm, 'red_medium_batch', 'red_medium_volume', 'Red', 'Red Medium');
    },

    green_medium_volume(frm) {
        check_medium_volume(frm, 'green_medium_batch', 'green_medium_volume', 'Green', 'Green Medium');
    },

    red_medium_volume(frm) {
        check_medium_volume(frm, 'red_medium_batch', 'red_medium_volume', 'Red', 'Red Medium');
    },

    qc_status(frm) {
        if (frm.doc.qc_status && frm.doc.qc_status !== 'Pending') {
            if (!frm.doc.qc_date)       frm.set_value('qc_date', frappe.datetime.get_today());
            if (!frm.doc.qc_checked_by) frm.set_value('qc_checked_by', frappe.session.user);
        }
    },

    shelf_life_days(frm) { calc_fmb_expiry(frm); },
    preparation_date(frm) { calc_fmb_expiry(frm); },

    refresh(frm) {
        frm.set_query('green_medium_batch', () => ({
            filters: { medium_type: 'Green', docstatus: 1 }
        }));
        frm.set_query('red_medium_batch', () => ({
            filters: { medium_type: 'Red', docstatus: 1 }
        }));
    }
});
