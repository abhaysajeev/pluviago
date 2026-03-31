import frappe
from frappe.model.document import Document


class RedMediumBatch(Document):
    def before_save(self):
        if not self.batch_number:
            self.batch_number = self.name
        if self.final_required_volume:
            self.red_volume_calculated = self.final_required_volume * 0.25

    def validate(self):
        passed_checkpoints = [qc for qc in self.qc_entries if qc.result == "Pass"]
        if self.overall_qc_status == "Passed":
            if len(passed_checkpoints) < 2:
                frappe.throw("At least 2 QC checkpoints (QC3 and QC4) must Pass before setting QC Status to Passed")
            if self.qc_checkpoint_3_clarity != "Pass":
                frappe.throw("QC Checkpoint 3 (Clarity) must be Pass before setting Overall QC Status to Passed")
            if self.qc_checkpoint_4_clarity != "Pass":
                frappe.throw("QC Checkpoint 4 (Clarity) must be Pass before setting Overall QC Status to Passed")

        from pluviago_biotech.utils.stock_utils import apply_corrective_action_logic
        apply_corrective_action_logic(self)

    @frappe.whitelist()
    def mark_preparation_complete(self):
        """
        Called when direct chemicals and stock solutions are physically added.
        Deducts stock from linked Raw Material Batches and moves to QC Pending.
        """
        if self.preparation_status != "Draft":
            frappe.throw("Preparation is already marked complete.")
        if not self.direct_chemicals:
            frappe.throw("Add at least one direct chemical before marking preparation complete.")

        from pluviago_biotech.utils.stock_utils import deduct_raw_materials
        deduct_raw_materials(self, action="Consumed")
        self.db_set("preparation_status", "QC Pending")
        frappe.msgprint("Preparation marked complete. Stock deducted. Proceed to QC checkpoints.")

    @frappe.whitelist()
    def mark_wasted(self, reason=""):
        """
        Called when QC fails after preparation.
        Chemicals are already consumed — no stock reversal.
        """
        if self.preparation_status != "QC Pending":
            frappe.throw("Can only mark as Wasted when in QC Pending state.")

        from pluviago_biotech.utils.stock_utils import log_waste
        if reason:
            self.db_set("remarks", (self.remarks or "") + f"\nWasted: {reason}")
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
        if self.overall_qc_status != "Passed":
            frappe.throw("Cannot submit: QC checkpoints 3 and 4 must pass")

        self.db_set("preparation_status", "Released")
        self.db_set("status", "Approved")

        from pluviago_biotech.utils.stock_utils import deduct_ssb_volume
        deduct_ssb_volume(self)

    def on_cancel(self):
        if self.preparation_status != "Draft":
            frappe.throw(
                "Cannot cancel a batch that has been physically prepared. "
                "Use 'Mark as Wasted' if QC failed."
            )
        from pluviago_biotech.utils.stock_utils import reverse_raw_materials, reverse_ssb_volume
        reverse_ssb_volume(self)
        reverse_raw_materials(self)
        self.db_set("status", "Draft")
