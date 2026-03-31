import frappe
from frappe.model.document import Document


class ExtractionBatch(Document):
    def before_save(self):
        if not self.batch_number:
            self.batch_number = self.name

    def validate(self):
        if self.harvest_batch:
            hb_status = frappe.db.get_value("Harvest Batch", self.harvest_batch, "status")
            if hb_status not in ["Approved", "Dispatched"]:
                frappe.throw("Harvest Batch must be Approved before creating Extraction Batch")

    def on_submit(self):
        self.status = "Dispatched"
        self.db_set("status", "Dispatched")
        if self.harvest_batch:
            frappe.db.set_value("Harvest Batch", self.harvest_batch, "status", "Dispatched")

    def on_cancel(self):
        self.status = "Draft"
        self.db_set("status", "Draft")
