import frappe
from frappe.model.document import Document


class CultivationReturnEvent(Document):
    """
    Read-only audit log of each Return-to-Cultivation event.
    Always created by ProductionBatch.create_return_batch() — never manually.
    """
    pass
