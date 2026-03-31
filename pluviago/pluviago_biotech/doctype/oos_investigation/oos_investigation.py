import frappe
from frappe.model.document import Document
from frappe.utils import today


class OOSInvestigation(Document):
    """
    Formal out-of-specification investigation record (Task 3.3).
    Created automatically via "Raise OOS Investigation" button on medium batch forms,
    or manually by QC Manager / QA Head.
    """

    def validate(self):
        # Closing checks
        if self.status == "Closed":
            if not self.conclusion:
                frappe.throw("A Conclusion must be selected before closing the investigation.")
            if not self.disposition:
                frappe.throw("A Disposition must be selected before closing the investigation.")
            if not self.closed_by:
                self.closed_by = frappe.session.user
            if not self.closed_date:
                self.closed_date = today()

    def on_update(self):
        # When disposition = Reject, flag the linked batch as Rejected via quality_flag
        if self.status == "Closed" and self.disposition == "Reject":
            self._flag_linked_batch_rejected()

    def _flag_linked_batch_rejected(self):
        """
        If conclusion is True OOS and disposition is Reject,
        set quality_flag = Rejected on the linked batch (if it has that field).
        """
        if not self.linked_doctype or not self.linked_batch:
            return
        try:
            frappe.db.set_value(
                self.linked_doctype,
                self.linked_batch,
                "quality_flag",
                "Rejected"
            )
        except Exception:
            pass  # linked doctype may not have quality_flag (e.g. Production Batch)
