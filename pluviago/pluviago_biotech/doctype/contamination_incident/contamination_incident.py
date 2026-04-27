import frappe
from frappe.model.document import Document


class ContaminationIncident(Document):
    def after_insert(self):
        if self.production_batch:
            frappe.db.set_value("Production Batch", self.production_batch, {
                "status": "Contaminated",
                "contamination_status": "Contaminated",
                "contamination_incident": self.name,
            })
            frappe.db.commit()
