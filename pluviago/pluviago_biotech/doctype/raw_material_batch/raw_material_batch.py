import json
import frappe
from frappe.model.document import Document


@frappe.whitelist()
def bulk_submit_rmbs(names):
    """
    Bulk-submit a list of Draft Raw Material Batches.
    Returns per-batch result so the client can show a summary.
    Accepts a JSON-encoded list or a Python list.
    """
    if isinstance(names, str):
        names = json.loads(names)

    results = {"submitted": [], "failed": []}
    for name in names:
        try:
            doc = frappe.get_doc("Raw Material Batch", name)
            if doc.docstatus != 0:
                results["failed"].append({"name": name, "reason": "Not in Draft state"})
                continue
            doc.submit()
            results["submitted"].append(name)
        except Exception as e:
            frappe.db.rollback()
            results["failed"].append({"name": name, "reason": str(e)})

    return results


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
        # Keep remaining_qty in sync while in draft
        if self.docstatus == 0:
            self.remaining_qty = max((self.received_qty or 0) - (self.consumed_qty or 0), 0)

    def validate(self):
        if self.expiry_date and self.mfg_date:
            if self.expiry_date <= self.mfg_date:
                frappe.throw("Expiry Date must be after Manufacturing Date.")
        if self.expiry_date:
            from frappe.utils import getdate, nowdate
            if getdate(self.expiry_date) < getdate(nowdate()):
                frappe.msgprint(
                    "Warning: This material batch has already expired.",
                    indicator="orange",
                )

    def on_submit(self):
        # QC gate applies to ALL batches regardless of source
        if self.qc_status != "Approved":
            frappe.throw(
                "Cannot submit: QC Status must be <b>Approved</b> before submitting a Raw Material Batch."
            )

        # Purchased batches have additional requirements
        if self.batch_source == "Purchased":
            if not self.supplier:
                frappe.throw(
                    "Cannot submit: <b>Supplier</b> is required for Purchased batches."
                )
            if not self.supplier_batch_no:
                frappe.throw(
                    "Cannot submit: <b>Supplier Batch No</b> is required for Purchased batches."
                )
            if not self.expiry_date:
                frappe.throw(
                    "Cannot submit: <b>Expiry Date</b> is required for Purchased batches."
                )
            if not self.coa_verified:
                frappe.throw(
                    "Cannot submit: <b>COA Verified</b> must be ticked for Purchased batches. "
                    "QC Manager must verify the vendor COA before submission."
                )

        self.db_set("status", "Approved")
        self.db_set("consumed_qty", 0)
        self.db_set("remaining_qty", self.received_qty)

    def on_cancel(self):
        if self.consumed_qty and self.consumed_qty > 0:
            frappe.throw(
                f"Cannot cancel: <b>{self.consumed_qty} {self.received_qty_uom or ''}</b> has already "
                "been consumed from this batch. Cancellation is only allowed before any consumption occurs."
            )
        self.db_set("status", "Received")
        self.db_set("consumed_qty", 0)
        self.db_set("remaining_qty", 0)

    def recalculate_remaining_qty(self):
        """
        Recompute consumed_qty by summing all Consumed/Written Off SCL entries
        and reverse-summing Reversed entries. Updates via db_set.
        """
        from frappe.utils import flt

        result = frappe.db.sql("""
            SELECT
                SUM(CASE WHEN action IN ('Consumed', 'Written Off (Loss)') THEN ABS(qty_change) ELSE 0 END) AS total_consumed,
                SUM(CASE WHEN action = 'Reversed' THEN ABS(qty_change) ELSE 0 END) AS total_reversed
            FROM `tabStock Consumption Log`
            WHERE raw_material_batch = %s
        """, self.name, as_dict=True)

        row = result[0] if result else {}
        net_consumed = max(flt(row.get("total_consumed")) - flt(row.get("total_reversed")), 0)
        remaining = max(flt(self.received_qty) - net_consumed, 0)

        self.db_set("consumed_qty", net_consumed)
        self.db_set("remaining_qty", remaining)

        if remaining <= 0 and self.status not in ("Exhausted", "Rejected"):
            self.db_set("status", "Exhausted")
