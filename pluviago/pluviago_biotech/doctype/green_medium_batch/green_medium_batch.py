import frappe
from frappe.model.document import Document


class GreenMediumBatch(Document):
    def before_save(self):
        if not self.batch_number:
            self.batch_number = self.name
        if self.final_required_volume:
            self.green_volume_calculated = self.final_required_volume * 0.75
        if self.shelf_life_days and self.preparation_date:
            self.expiry_date = frappe.utils.add_days(self.preparation_date, int(self.shelf_life_days))

    def validate(self):
        # Individual checkpoint fields are authoritative for QC status
        if self.overall_qc_status == "Passed":
            if self.qc_checkpoint_1_clarity != "Pass":
                frappe.throw("QC Checkpoint 1 (Clarity) must be Pass before setting Overall QC Status to Passed.")
            if self.qc_checkpoint_2_clarity != "Pass":
                frappe.throw("QC Checkpoint 2 (Clarity) must be Pass before setting Overall QC Status to Passed.")

        from pluviago.pluviago_biotech.utils.stock_utils import apply_corrective_action_logic
        apply_corrective_action_logic(self)

    @frappe.whitelist()
    def mark_preparation_complete(self):
        """
        Called when direct chemicals and stock solutions are physically added.
        Deducts stock from Raw Material Batches and DI Water batch.
        Moves to QC Pending.
        """
        if self.preparation_status != "Draft":
            frappe.throw("Preparation is already marked complete.")
        if not self.direct_chemicals:
            frappe.throw("Add at least one direct chemical before marking preparation complete.")
        if not self.top_up_done:
            frappe.throw(
                "<b>Top-up Done</b> must be ticked — confirm DI water has been added "
                "to bring the batch to its final volume before marking complete."
            )

        from pluviago.pluviago_biotech.utils.stock_utils import deduct_raw_materials, deduct_di_water
        deduct_raw_materials(self, action="Consumed")
        deduct_di_water(self)
        self.db_set("preparation_status", "QC Pending")
        frappe.msgprint("Preparation marked complete. Stock deducted. Proceed to QC checkpoints.")

    @frappe.whitelist()
    def mark_wasted(self, reason=""):
        """Called when QC fails. No stock reversal — chemicals physically consumed."""
        if self.preparation_status != "QC Pending":
            frappe.throw("Can only mark as Wasted when in QC Pending state.")

        from pluviago.pluviago_biotech.utils.stock_utils import log_waste
        if reason:
            self.db_set("remarks", (self.remarks or "") + f"\nWasted: {reason}")
        log_waste(self)
        self.db_set("preparation_status", "Wasted")
        self.db_set("status", "Wasted")
        frappe.msgprint("Batch marked as Wasted. Stock loss recorded in consumption log.")

    def on_submit(self):
        if self.preparation_status == "Draft":
            frappe.throw("Cannot submit: Click 'Mark Preparation Complete' before submitting.")
        if self.preparation_status == "Wasted":
            frappe.throw("Cannot submit a wasted batch.")
        if self.overall_qc_status != "Passed":
            frappe.throw("Cannot submit: Overall QC Status must be Passed.")

        self.db_set("preparation_status", "Released")
        self.db_set("status", "Approved")
        self.db_set("remaining_volume", self.green_volume_calculated or 0)
        self.db_set("volume_consumed", 0)

        from pluviago.pluviago_biotech.utils.stock_utils import deduct_ssb_volume
        deduct_ssb_volume(self)

    def on_cancel(self):
        if self.preparation_status != "Draft":
            frappe.throw(
                "Cannot cancel a batch that has been physically prepared. "
                "Use 'Mark as Wasted' if QC failed."
            )
        from pluviago.pluviago_biotech.utils.stock_utils import (
            reverse_raw_materials, reverse_ssb_volume, reverse_di_water
        )
        reverse_ssb_volume(self)
        reverse_raw_materials(self)
        reverse_di_water(self)
        self.db_set("status", "Draft")
