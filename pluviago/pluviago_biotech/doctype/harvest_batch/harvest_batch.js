frappe.ui.form.on('Harvest Batch', {
    onload(frm) {
        if (frm.is_new()) {
            if (!frm.doc.harvested_by) frm.set_value('harvested_by', frappe.session.user);
        }
    },

    refresh(frm) {
        // ── Headline alerts ──────────────────────────────────────────────────
        if (frm.doc.docstatus === 0) {
            frm.dashboard.set_headline_alert(
                __('Draft — record harvest data and complete QC before submitting.'),
                'blue'
            );
        } else if (frm.doc.docstatus === 1) {
            const status = frm.doc.status;
            if (status === 'Approved') {
                frm.dashboard.set_headline_alert(
                    __('Approved — create a Drying Batch to record drying process.'),
                    'green'
                );
            } else if (status === 'Packed') {
                frm.dashboard.set_headline_alert(__('Packed — ready for dispatch.'), 'yellow');
            } else if (status === 'Dispatched') {
                frm.dashboard.set_headline_alert(__('Dispatched to extraction.'), 'grey');
            } else if (status === 'Rejected') {
                frm.dashboard.set_headline_alert(__('Rejected — batch cannot be used.'), 'red');
            }
        } else if (frm.doc.docstatus === 2) {
            frm.dashboard.set_headline_alert(__('Cancelled.'), 'grey');
        }

        // ── Create Drying Batch — available when Approved ────────────────────
        if (frm.doc.docstatus === 1 && frm.doc.status === 'Approved') {
            frm.add_custom_button(__('Create Drying Batch'), function() {
                frappe.new_doc('Drying Batch', {
                    harvest_batch: frm.doc.name
                });
            }, __('Actions'));
        }

        // ── Confirm Packing — Approved → Packed ──────────────────────────────
        if (frm.doc.docstatus === 1 && frm.doc.status === 'Approved') {
            frm.add_custom_button(__('Confirm Packing'), function() {
                frappe.call({
                    method: 'confirm_packing',
                    doc: frm.doc,
                    freeze: true,
                    freeze_message: __('Confirming packing...'),
                    callback() { frm.reload_doc(); }
                });
            }, __('Actions'));
        }

        // ── Create Extraction Batch — Approved or Packed ──────────────────────
        if (frm.doc.docstatus === 1 && ['Approved', 'Packed'].includes(frm.doc.status)) {
            frm.add_custom_button(__('Create Extraction Batch'), function() {
                frappe.new_doc('Extraction Batch', {
                    harvest_batch: frm.doc.name
                });
            }, __('Actions'));
        }
    },

    qc_status(frm) {
        if (frm.doc.qc_status && frm.doc.qc_status !== 'Pending') {
            if (!frm.doc.qc_date)       frm.set_value('qc_date', frappe.datetime.get_today());
            if (!frm.doc.qc_checked_by) frm.set_value('qc_checked_by', frappe.session.user);
        }
    }
});
