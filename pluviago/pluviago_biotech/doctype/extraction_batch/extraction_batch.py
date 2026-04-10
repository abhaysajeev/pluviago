import frappe
from frappe.model.document import Document


class ExtractionBatch(Document):
    def before_save(self):
        if not self.batch_number:
            self.batch_number = self.name

    def validate(self):
        if self.harvest_batch:
            hb_status = frappe.db.get_value("Harvest Batch", self.harvest_batch, "status")
            if hb_status != "Approved":
                frappe.throw(
                    f"Harvest Batch <b>{self.harvest_batch}</b> has status <b>{hb_status}</b>. "
                    "Only Approved Harvest Batches can be dispatched for extraction."
                )
        if self.incoming_qc_status == "Failed":
            frappe.throw("Cannot submit: Incoming QC has Failed. Resolve before submitting.")

    def on_submit(self):
        if self.incoming_qc_status not in ("Passed", "Pending"):
            frappe.throw("Cannot submit: Incoming QC must be Passed (or Pending for deferred check).")
        self.db_set("status", "Dispatched")
        if self.harvest_batch:
            frappe.db.set_value("Harvest Batch", self.harvest_batch, "status", "Dispatched")

    def on_cancel(self):
        self.db_set("status", "Draft")
        if self.harvest_batch:
            frappe.db.set_value("Harvest Batch", self.harvest_batch, "status", "Approved")
