import frappe
from frappe.model.document import Document


class ContaminationIncident(Document):
    def validate(self):
        # Auto-fill decision metadata when decision changes from Pending
        if self.decision and self.decision != "Pending":
            if not self.decision_date:
                self.decision_date = frappe.utils.today()
            if not self.decision_by:
                self.decision_by = frappe.session.user

        # Disposal date required when batch is marked disposed
        if self.batch_disposed and not self.disposal_date:
            self.disposal_date = frappe.utils.today()
            self.disposal_by = self.disposal_by or frappe.session.user

    def after_insert(self):
        """Flag the Production Batch as Contaminated when a new incident is raised."""
        if self.production_batch:
            frappe.db.set_value("Production Batch", self.production_batch, {
                "contamination_status": "Contaminated",
                "status": "Contaminated",
            })

    def before_submit(self):
        if self.decision == "Pending":
            frappe.throw(
                "Cannot submit: <b>Decision</b> is still Pending. "
                "Set the decision (Harvest Immediately, Dispose, or Continue with Monitoring) "
                "before closing this incident."
            )
        if self.status not in ("Resolved", "Closed"):
            frappe.throw(
                "Cannot submit: Status must be <b>Resolved</b> or <b>Closed</b> before submission. "
                "Update the status to reflect the final outcome of the investigation."
            )
        if not self.root_cause_category:
            frappe.throw(
                "Cannot submit: <b>Root Cause Category</b> must be filled before closing an incident. "
                "This is required for GMP traceability and trend analysis."
            )

    def on_submit(self):
        pass

    def on_cancel(self):
        """
        When a submitted incident is cancelled, reassess the Production Batch
        contamination status. If no other open/unsubmitted incidents remain
        for this batch, restore contamination_status to Clean.
        """
        if not self.production_batch:
            return
        other_active = frappe.db.count(
            "Contamination Incident",
            {
                "production_batch": self.production_batch,
                "docstatus": ["in", [0, 1]],
                "name": ["!=", self.name],
            }
        )
        if not other_active:
            frappe.db.set_value("Production Batch", self.production_batch, {
                "contamination_status": "Clean",
                "status": "Active",
            })
