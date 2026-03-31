import frappe
from frappe.model.document import Document


class StockConsumptionLog(Document):
    def before_insert(self):
        if not self.log_date:
            self.log_date = frappe.utils.now()
