import frappe
from frappe.model.document import Document


class ContaminationIncident(Document):
    def after_insert(self):
        # Update the production batch status
        if self.production_batch:
            frappe.db.set_value("Production Batch", self.production_batch, "status", "Contaminated")
            frappe.db.commit()
