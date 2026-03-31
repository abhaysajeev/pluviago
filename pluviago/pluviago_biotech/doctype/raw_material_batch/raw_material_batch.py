import frappe
from frappe.model.document import Document


@frappe.whitelist()
def recalculate_stock(rmb_name):
	"""Whitelisted entry point — called from the form button."""
	doc = frappe.get_doc("Raw Material Batch", rmb_name)
	doc.recalculate_remaining_qty()
	return {
		"consumed_qty": doc.consumed_qty,
		"remaining_qty": doc.remaining_qty,
		"status": doc.status,
	}


class RawMaterialBatch(Document):
    def before_save(self):
        if not self.batch_number:
            self.batch_number = self.name

    def validate(self):
        if self.expiry_date and self.mfg_date:
            if self.expiry_date <= self.mfg_date:
                frappe.throw("Expiry Date must be after Manufacturing Date")
        if self.expiry_date:
            from frappe.utils import getdate, nowdate
            if getdate(self.expiry_date) < getdate(nowdate()):
                frappe.msgprint("Warning: This material batch has already expired.", indicator="orange")

    def on_submit(self):
        if self.qc_status != "Approved":
            frappe.throw(
                "Cannot submit: QC Status must be <b>Approved</b> before submitting a Raw Material Batch."
            )
        if not self.coa_verified:
            frappe.throw(
                "Cannot submit: COA has not been verified. "
                "QC Manager must attach the COA document and tick <b>COA Verified</b> before submission."
            )
        self.db_set("status", "Approved")
        self.db_set("consumed_qty", 0)
        self.db_set("remaining_qty", self.received_qty)

    def on_cancel(self):
        if self.consumed_qty and self.consumed_qty > 0:
            frappe.throw(
                f"Cannot cancel: <b>{self.consumed_qty} {self.received_qty_uom}</b> has already been "
                "consumed from this batch. Cancellation is only allowed before any consumption occurs."
            )
        self.db_set("status", "Received")
        self.db_set("consumed_qty", 0)
        self.db_set("remaining_qty", 0)

    def recalculate_remaining_qty(self):
        """
        Recompute consumed_qty by summing all Consumed/Written Off SCL entries
        and reverse-summing Reversed entries for this batch.
        Updates consumed_qty and remaining_qty via db_set.
        """
        from frappe.utils import flt

        result = frappe.db.sql("""
            SELECT
                SUM(CASE WHEN action IN ('Consumed', 'Written Off (Loss)') THEN ABS(qty_change) ELSE 0 END) as total_consumed,
                SUM(CASE WHEN action = 'Reversed' THEN ABS(qty_change) ELSE 0 END) as total_reversed
            FROM `tabStock Consumption Log`
            WHERE raw_material_batch = %s
        """, self.name, as_dict=True)

        row = result[0] if result else {}
        total_consumed = flt(row.get("total_consumed"))
        total_reversed = flt(row.get("total_reversed"))
        net_consumed = max(total_consumed - total_reversed, 0)
        remaining = max(flt(self.received_qty) - net_consumed, 0)

        self.db_set("consumed_qty", net_consumed)
        self.db_set("remaining_qty", remaining)

        if remaining <= 0 and self.status not in ("Exhausted", "Rejected"):
            self.db_set("status", "Exhausted")
