function calc_fmb_expiry(frm) {
    if (frm.doc.shelf_life_days && frm.doc.preparation_date) {
        frm.set_value('expiry_date',
            frappe.datetime.add_days(frm.doc.preparation_date, frm.doc.shelf_life_days));
    }
}

function check_medium_volume(frm, link_field, vol_field, label) {
    const batch = frm.doc[link_field];
    const required = frm.doc[vol_field] || 0;
    if (!batch || !required) return;

    frappe.db.get_value(
        link_field === 'green_medium_batch' ? 'Green Medium Batch' : 'Red Medium Batch',
        batch,
        ['remaining_volume', 'status'],
        (r) => {
            if (!r) return;
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
        }
    );
}

frappe.ui.form.on('Final Medium Batch', {
    final_required_volume(frm) {
        if (frm.doc.final_required_volume) {
            frm.set_value('green_medium_volume', frm.doc.final_required_volume * 0.75);
            frm.set_value('red_medium_volume', frm.doc.final_required_volume * 0.25);
        }
    },

    green_medium_batch(frm) {
        check_medium_volume(frm, 'green_medium_batch', 'green_medium_volume', 'Green Medium');
    },

    red_medium_batch(frm) {
        check_medium_volume(frm, 'red_medium_batch', 'red_medium_volume', 'Red Medium');
    },

    green_medium_volume(frm) {
        check_medium_volume(frm, 'green_medium_batch', 'green_medium_volume', 'Green Medium');
    },

    red_medium_volume(frm) {
        check_medium_volume(frm, 'red_medium_batch', 'red_medium_volume', 'Red Medium');
    },

    shelf_life_days(frm) { calc_fmb_expiry(frm); },
    preparation_date(frm) { calc_fmb_expiry(frm); },
});
