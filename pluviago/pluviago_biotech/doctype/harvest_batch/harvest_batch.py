import frappe
from frappe.model.document import Document


class HarvestBatch(Document):
    def before_save(self):
        if not self.batch_number:
            self.batch_number = self.name
        if self.target_dry_weight and self.actual_dry_weight and self.target_dry_weight > 0:
            self.yield_percentage = (self.actual_dry_weight / self.target_dry_weight) * 100

    def validate(self):
        if self.production_batch:
            pb_status = frappe.db.get_value("Production Batch", self.production_batch, "status")
            if pb_status not in ["Harvested", "Active"]:
                frappe.throw("Linked Production Batch is not in a harvestable state")

    def on_submit(self):
        if self.qc_status != "Passed":
            frappe.throw("Cannot submit: QC must be Passed")
        self.status = "Approved"
        self.db_set("status", "Approved")
        # Update production batch
        if self.production_batch:
            frappe.db.set_value("Production Batch", self.production_batch, {
                "status": "Harvested",
                "harvest_batch": self.name
            })

    def on_cancel(self):
        self.status = "Draft"
        self.db_set("status", "Draft")
