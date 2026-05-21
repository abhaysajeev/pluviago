frappe.ui.form.on('Contamination Incident', {
    onload(frm) {
        if (frm.is_new()) {
            if (!frm.doc.reported_by) frm.set_value('reported_by', frappe.session.user);
            if (!frm.doc.incident_date) frm.set_value('incident_date', frappe.datetime.get_today());
        }
    },

    refresh(frm) {
        // ── Headline alerts ──────────────────────────────────────────────────
        if (frm.doc.docstatus === 0) {
            const color = frm.doc.status === 'Open' ? 'red'
                : frm.doc.status === 'Under Investigation' ? 'orange'
                : 'yellow';
            frm.dashboard.set_headline_alert(
                __('Incident {0} — fill in all details and close investigation before submitting.', [frm.doc.status || 'Open']),
                color
            );
        } else if (frm.doc.docstatus === 1) {
            frm.dashboard.set_headline_alert(
                __('Closed — this incident record is locked for GMP traceability.'),
                'green'
            );
        } else if (frm.doc.docstatus === 2) {
            frm.dashboard.set_headline_alert(__('Cancelled.'), 'grey');
        }

        // ── Filter production_batch to show only active/non-disposed batches ─
        frm.set_query('production_batch', function() {
            return {
                filters: { docstatus: ['in', [0, 1]] }
            };
        });
    },

    production_batch(frm) {
        if (!frm.doc.production_batch) return;
        frappe.db.get_value('Production Batch', frm.doc.production_batch,
            ['current_stage', 'phase'], (r) => {
            if (!r) return;
            if (r.current_stage && !frm.doc.reactor_stage) {
                frm.set_value('reactor_stage', r.current_stage);
            }
            if (r.phase && r.phase !== 'N/A' && !frm.doc.culture_phase_at_incident) {
                frm.set_value('culture_phase_at_incident', r.phase);
            }
        });
    },

    decision(frm) {
        if (frm.doc.decision === 'Dispose') {
            frappe.confirm(
                __('Mark decision as <b>Dispose</b>? This will flag the production batch for disposal.'),
                () => {
                    if (!frm.doc.decision_date) frm.set_value('decision_date', frappe.datetime.get_today());
                    if (!frm.doc.decision_by)   frm.set_value('decision_by', frappe.session.user);
                },
                () => {
                    frm.set_value('decision', 'Pending');
                }
            );
        } else if (frm.doc.decision && frm.doc.decision !== 'Pending') {
            if (!frm.doc.decision_date) frm.set_value('decision_date', frappe.datetime.get_today());
            if (!frm.doc.decision_by)   frm.set_value('decision_by', frappe.session.user);
        }
    },

    batch_disposed(frm) {
        if (frm.doc.batch_disposed) {
            if (!frm.doc.disposal_date) frm.set_value('disposal_date', frappe.datetime.get_today());
            if (!frm.doc.disposal_by)   frm.set_value('disposal_by', frappe.session.user);
        }
    },

    follow_up_done(frm) {
        if (frm.doc.follow_up_done && !frm.doc.follow_up_notes) {
            frm.set_df_property('follow_up_notes', 'reqd', 1);
        } else {
            frm.set_df_property('follow_up_notes', 'reqd', 0);
        }
    },

    status(frm) {
        if (frm.doc.status === 'Resolved' || frm.doc.status === 'Closed') {
            if (!frm.doc.root_cause_category) {
                frappe.show_alert({
                    message: __('Please fill in Root Cause Category before closing the incident.'),
                    indicator: 'orange'
                }, 5);
            }
        }
    }
});
