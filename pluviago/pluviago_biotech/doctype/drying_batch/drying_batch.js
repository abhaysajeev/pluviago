frappe.ui.form.on('Drying Batch', {
    onload(frm) {
        if (frm.is_new()) {
            if (!frm.doc.operator)    frm.set_value('operator', frappe.session.user);
            if (!frm.doc.drying_date) frm.set_value('drying_date', frappe.datetime.get_today());
        }
    },

    refresh(frm) {
        // ── Headline alerts ──────────────────────────────────────────────────
        if (frm.doc.docstatus === 0) {
            frm.dashboard.set_headline_alert(
                __('Draft — fill drying parameters, record dry weight, and complete QC before submitting.'),
                'blue'
            );
        } else if (frm.doc.docstatus === 1) {
            if (frm.doc.status === 'Approved') {
                frm.dashboard.set_headline_alert(
                    __('Approved — dry weight and yield written back to Harvest Batch.'),
                    'green'
                );
            } else if (frm.doc.status === 'Rejected') {
                frm.dashboard.set_headline_alert(__('Rejected — drying batch failed QC.'), 'red');
            }
        } else if (frm.doc.docstatus === 2) {
            frm.dashboard.set_headline_alert(__('Cancelled — Harvest Batch dry weight cleared.'), 'grey');
        }

        // ── Filter harvest_batch to submitted, Approved/Packed batches ────────
        frm.set_query('harvest_batch', function() {
            return {
                filters: { docstatus: 1, status: ['in', ['Approved', 'Packed']] }
            };
        });
    },

    harvest_batch(frm) {
        if (!frm.doc.harvest_batch) return;
        frappe.db.get_value('Harvest Batch', frm.doc.harvest_batch, 'wet_biomass_kg', (r) => {
            if (r && r.wet_biomass_kg && !frm.doc.wet_biomass_in) {
                frm.set_value('wet_biomass_in', r.wet_biomass_kg);
                frappe.show_alert({
                    message: __('Wet biomass pre-filled from Harvest Batch ({0} kg). Confirm or adjust.', [r.wet_biomass_kg]),
                    indicator: 'blue'
                }, 4);
            }
        });
    },

    actual_dry_weight(frm) {
        const wet = frm.doc.wet_biomass_in || 0;
        const dry = frm.doc.actual_dry_weight || 0;
        if (wet > 0 && dry > 0) {
            frm.set_value('yield_percentage', parseFloat(((dry / wet) * 100).toFixed(2)));
        }
    },

    wet_biomass_in(frm) {
        const wet = frm.doc.wet_biomass_in || 0;
        const dry = frm.doc.actual_dry_weight || 0;
        if (wet > 0 && dry > 0) {
            frm.set_value('yield_percentage', parseFloat(((dry / wet) * 100).toFixed(2)));
        }
    },

    qc_status(frm) {
        if (frm.doc.qc_status && frm.doc.qc_status !== 'Pending') {
            if (!frm.doc.qc_date)       frm.set_value('qc_date', frappe.datetime.get_today());
            if (!frm.doc.qc_checked_by) frm.set_value('qc_checked_by', frappe.session.user);
        }
    }
});
