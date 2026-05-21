import frappe
from frappe.model.document import Document


class CultivationReturnEvent(Document):
    """
    Read-only audit log of each Return-to-Cultivation event.
    Always created by ProductionBatch.create_return_batch() — never manually.
    """

    def validate(self):
        if self.is_new() and not self.source_batch:
            frappe.throw(
                "Cultivation Return Events are created automatically by the "
                "<b>Return to Flask</b> action on a Production Batch. "
                "Do not create them manually."
            )
