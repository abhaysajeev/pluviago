import frappe
from frappe.model.document import Document


class FinalMediumBatch(Document):
    def before_save(self):
        if not self.batch_number:
            self.batch_number = self.name
        if self.final_required_volume:
            self.green_medium_volume = self.final_required_volume * 0.75
            self.red_medium_volume = self.final_required_volume * 0.25

    def validate(self):
        # Validate linked green and red batches are Approved
        if self.green_medium_batch:
            status = frappe.db.get_value("Green Medium Batch", self.green_medium_batch, "status")
            if status != "Approved":
                frappe.throw(f"Green Medium Batch {self.green_medium_batch} is not Approved")
        if self.red_medium_batch:
            status = frappe.db.get_value("Red Medium Batch", self.red_medium_batch, "status")
            if status != "Approved":
                frappe.throw(f"Red Medium Batch {self.red_medium_batch} is not Approved")

        from pluviago_biotech.utils.stock_utils import apply_corrective_action_logic
        apply_corrective_action_logic(self)

    def on_submit(self):
        if self.qc_status != "Passed":
            frappe.throw("Cannot submit: QC must be Passed")
        self.status = "Approved"
        self.db_set("status", "Approved")
        # Mark source batches as Used
        if self.green_medium_batch:
            frappe.db.set_value("Green Medium Batch", self.green_medium_batch, "status", "Used")
        if self.red_medium_batch:
            frappe.db.set_value("Red Medium Batch", self.red_medium_batch, "status", "Used")

    def on_cancel(self):
        self.status = "Draft"
        self.db_set("status", "Draft")
