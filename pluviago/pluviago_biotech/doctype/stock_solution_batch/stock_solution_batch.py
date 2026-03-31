import frappe
from frappe.model.document import Document


class StockSolutionBatch(Document):
    def before_save(self):
        if not self.batch_number:
            self.batch_number = self.name

    def validate(self):
        if self.qc_date and self.preparation_date:
            if self.qc_date < self.preparation_date:
                frappe.throw("QC Date cannot be before Preparation Date")
        self._validate_raw_material_batches()

    def _validate_raw_material_batches(self):
        """
        Every ingredient row must link a Raw Material Batch that is:
          1. Submitted (docstatus = 1)
          2. QC Status = Approved
          3. COA Verified = True
        """
        for row in self.ingredients or []:
            if not row.raw_material_batch:
                continue

            rm = frappe.db.get_value(
                "Raw Material Batch",
                row.raw_material_batch,
                ["docstatus", "qc_status", "coa_verified"],
                as_dict=True,
            )

            if not rm:
                frappe.throw(
                    f"Row {row.idx}: Raw Material Batch <b>{row.raw_material_batch}</b> does not exist."
                )
            if rm.docstatus != 1:
                frappe.throw(
                    f"Row {row.idx}: Raw Material Batch <b>{row.raw_material_batch}</b> is not submitted. "
                    "Only submitted (Approved) batches can be used."
                )
            if rm.qc_status != "Approved":
                frappe.throw(
                    f"Row {row.idx}: Raw Material Batch <b>{row.raw_material_batch}</b> "
                    f"has QC Status = <b>{rm.qc_status}</b>. Only Approved batches may be used."
                )
            if not rm.coa_verified:
                frappe.throw(
                    f"Row {row.idx}: Raw Material Batch <b>{row.raw_material_batch}</b> — "
                    "COA has not been verified."
                )

    @frappe.whitelist()
    def mark_preparation_complete(self):
        """
        Called when chemicals are physically added and preparation is complete.
        Deducts stock from linked Raw Material Batches and moves to QC Pending.
        This is irreversible — cancel is blocked after this point.
        """
        if self.preparation_status != "Draft":
            frappe.throw("Preparation is already marked complete.")
        if not self.ingredients:
            frappe.throw("Add at least one ingredient before marking preparation complete.")

        from pluviago_biotech.utils.stock_utils import deduct_raw_materials
        deduct_raw_materials(self, action="Consumed")
        self.db_set("preparation_status", "QC Pending")
        frappe.msgprint("Preparation marked complete. Stock deducted. Proceed to QC check.")

    @frappe.whitelist()
    def mark_wasted(self, reason=""):
        """
        Called when QC fails after preparation.
        Chemicals are already consumed — no stock reversal.
        Logs the event as Written Off (Loss).
        """
        if self.preparation_status != "QC Pending":
            frappe.throw("Can only mark as Wasted when in QC Pending state.")

        from pluviago_biotech.utils.stock_utils import log_waste
        if reason:
            self.db_set("qc_remarks", reason)
        log_waste(self)
        self.db_set("preparation_status", "Wasted")
        self.db_set("status", "Wasted")
        frappe.msgprint("Batch marked as Wasted. Stock loss recorded in consumption log.")

    def on_submit(self):
        if self.preparation_status == "Draft":
            frappe.throw(
                "Cannot submit: Click 'Mark Preparation Complete' before submitting."
            )
        if self.preparation_status == "Wasted":
            frappe.throw("Cannot submit a wasted batch.")
        if self.preparation_status != "QC Pending":
            frappe.throw(
                f"Cannot submit: Preparation Status is '{self.preparation_status}'."
            )
        if self.qc_status != "Passed":
            frappe.throw("Cannot submit: QC Status must be Passed.")

        self.db_set("preparation_status", "Released")
        self.db_set("released_date", frappe.utils.today())
        self.db_set("released_by", frappe.session.user)
        self.db_set("available_volume", self.target_volume or 0)
        self.db_set("status", "Approved")

    def on_cancel(self):
        if self.preparation_status != "Draft":
            frappe.throw(
                "Cannot cancel a batch that has been physically prepared. "
                "Use 'Mark as Wasted' if QC failed, or contact an administrator."
            )
        from pluviago_biotech.utils.stock_utils import reverse_raw_materials
        reverse_raw_materials(self)
        self.db_set("status", "Draft")
