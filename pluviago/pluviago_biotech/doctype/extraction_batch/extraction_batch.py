import frappe
from frappe.model.document import Document


EXPECTED_ASTAXANTHIN_FRACTION = 0.025  # 2.5% — update from config doctype when available


class ExtractionBatch(Document):
    def before_save(self):
        if not self.batch_number:
            self.batch_number = self.name

    def validate(self):
        if self.harvest_batch:
            hb_status = frappe.db.get_value("Harvest Batch", self.harvest_batch, "status")
            if hb_status not in ("Approved", "Packed"):
                frappe.throw(
                    f"Harvest Batch <b>{self.harvest_batch}</b> has status <b>{hb_status}</b>. "
                    "Only Approved or Packed Harvest Batches can be dispatched for extraction."
                )
        if self.incoming_qc_status == "Failed":
            frappe.throw("Cannot submit: Incoming QC has Failed. Resolve before submitting.")
        self._calculate_yield_variance()

    def _calculate_yield_variance(self):
        """Compute theoretical yield and variance from Harvest Batch dry weight."""
        if not self.harvest_batch:
            return
        hb = frappe.db.get_value(
            "Harvest Batch", self.harvest_batch,
            ["actual_dry_weight"], as_dict=True
        )
        if not hb or not hb.actual_dry_weight:
            return
        theoretical = round(hb.actual_dry_weight * EXPECTED_ASTAXANTHIN_FRACTION, 4)
        self.theoretical_yield_kg = theoretical

        if self.extract_qty and theoretical > 0:
            variance = ((self.extract_qty - theoretical) / theoretical) * 100
            self.yield_variance_pct = round(variance, 2)
            if abs(variance) <= 10:
                self.yield_variance_flag = "Normal"
            elif abs(variance) <= 25:
                self.yield_variance_flag = "Warning"
            else:
                self.yield_variance_flag = "Critical"
                frappe.msgprint(
                    f"Yield variance is <b>{variance:.1f}%</b> — "
                    "investigate before completing extraction.",
                    indicator="orange"
                )

    def on_submit(self):
        if self.incoming_qc_status not in ("Passed", "Pending"):
            frappe.throw("Cannot submit: Incoming QC must be Passed (or Pending for deferred check).")
        self.db_set("status", "Dispatched")
        if self.harvest_batch:
            frappe.db.set_value("Harvest Batch", self.harvest_batch, "status", "Dispatched")

    def on_cancel(self):
        self.db_set("status", "Draft")
        if self.harvest_batch:
            frappe.db.set_value("Harvest Batch", self.harvest_batch, "status", "Approved")

    @frappe.whitelist()
    def mark_extract_received(self, received_date, received_by):
        """Advance status from Dispatched → Processing when extract arrives from partner."""
        if self.status != "Dispatched":
            frappe.throw("Extract can only be received when batch is Dispatched.")
        if not self.extract_qty:
            frappe.throw("Enter Extract Quantity before marking received.")
        self.db_set("status", "Processing")
        frappe.msgprint("Extract received. Status updated to Processing.", indicator="blue")

    @frappe.whitelist()
    def complete_extraction(self):
        """Advance status from Processing → Completed after repacking and final dispatch."""
        if self.status != "Processing":
            frappe.throw("Batch must be in Processing state before completing.")
        if not self.repacking_date or not self.final_dispatch_date:
            frappe.throw("Repacking Date and Final Dispatch Date are required to complete.")
        self.db_set("status", "Completed")
        frappe.msgprint("Extraction batch completed.", indicator="green")
