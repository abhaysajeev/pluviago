"""
Purchase Receipt override for Pluviago — non-accounting workflow.

Skips all GL/accounting entry creation so the doctype works without a
Chart of Accounts setup. Stock ledger updates still run normally so
inventory levels are tracked correctly.
"""
import frappe
from erpnext.stock.doctype.purchase_receipt.purchase_receipt import PurchaseReceipt
from pluviago.pluviago_biotech.utils.item_utils import (
    PURCHASED_RAW_MATERIAL_GROUPS,
    get_item_groups,
)


class CustomPurchaseReceipt(PurchaseReceipt):
    """PurchaseReceipt subclass that disables all accounting entries."""

    def before_submit(self):
        self.taxes = []
        self.taxes_and_charges = None
        self.additional_discount_percentage = 0
        self.discount_amount = 0
        self.pricing_rules = []

    def make_gl_entries(self, *args, **kwargs):
        pass

    def make_gl_entries_on_cancel(self, *args, **kwargs):
        pass

    def repost_future_sle_and_gle(self, *args, **kwargs):
        pass

    def validate_cwip_accounts(self):
        pass

    def validate_provisional_expense_account(self):
        pass

    def on_submit(self):
        super().on_submit()
        self._auto_create_raw_material_batches()

    def _auto_create_raw_material_batches(self):
        from pluviago.pluviago_biotech.utils.item_utils import (
            PURCHASED_RAW_MATERIAL_GROUPS,
            get_item_groups,
        )

        all_codes = list({row.item_code for row in self.items if row.item_code})
        if not all_codes:
            return

        try:
            item_groups = get_item_groups(all_codes)
        except Exception:
            frappe.log_error(frappe.get_traceback(), "RMB Auto-Create: failed to fetch item groups")
            return

        for row in self.items:
            if not row.item_code:
                continue
            if item_groups.get(row.item_code, "") not in PURCHASED_RAW_MATERIAL_GROUPS:
                continue

            try:
                supplier_batch_no = row.get("custom_supplier_batch_no") or ""
                filters = {"purchase_receipt": self.name, "item_code": row.item_code}
                if supplier_batch_no:
                    filters["supplier_batch_no"] = supplier_batch_no

                if frappe.db.exists("Raw Material Batch", filters):
                    continue

                item_name = (
                    frappe.db.get_value("Item", row.item_code, "item_name")
                    or row.item_name
                    or row.item_code
                )

                rmb = frappe.new_doc("Raw Material Batch")
                rmb.batch_source      = "Purchased"
                rmb.material_name     = item_name
                rmb.item_code         = row.item_code
                rmb.supplier          = self.supplier
                rmb.supplier_batch_no = supplier_batch_no
                rmb.mfg_date          = row.get("custom_mfg_date")
                rmb.expiry_date       = row.get("custom_expiry_date")
                rmb.received_date     = self.posting_date
                rmb.received_qty      = row.qty
                rmb.received_qty_uom  = row.uom
                rmb.storage_condition = row.get("custom_storage_condition") or ""
                rmb.warehouse         = row.warehouse
                rmb.purchase_receipt  = self.name
                rmb.purchase_order    = row.get("purchase_order") or ""
                rmb.coa_attachment    = self.get("custom_coa_attach") or ""
                coa_approved_by       = self.get("custom_coa_approved_by") or ""
                rmb.coa_verified      = 1 if coa_approved_by else 0
                rmb.coa_verified_by   = coa_approved_by
                rmb.qc_status         = "Pending"
                rmb.insert(ignore_permissions=True)

            except Exception:
                frappe.log_error(
                    frappe.get_traceback(),
                    f"RMB Auto-Create: failed for item {row.item_code} in {self.name}"
                )


def on_workflow_action(doc, method=None, workflow_action=None, **kwargs):
    """Capture who approved the COA so auto-created RMBs can be pre-verified."""
    if workflow_action == "Approve COA":
        doc.db_set("custom_coa_approved_by", frappe.session.user, notify=True)


@frappe.whitelist()
def create_raw_material_batches(purchase_receipt_name):
    """
    Creates one Raw Material Batch (Draft, batch_source=Purchased) for each
    purchased raw material item row in the PR that does not already have an RMB.

    Detection is item-group based — not dependent on item code naming convention.
    Returns a dict with 'created', 'skipped', and 'errors' lists.
    """
    pr = frappe.get_doc("Purchase Receipt", purchase_receipt_name)
    if pr.docstatus != 1:
        frappe.throw("Purchase Receipt must be submitted before creating Raw Material Batches.")

    # Fetch all item groups in one query
    all_codes = list({row.item_code for row in pr.items if row.item_code})
    item_groups = get_item_groups(all_codes)

    created = []
    skipped = []
    errors = []

    for row in pr.items:
        if not row.item_code:
            continue

        group = item_groups.get(row.item_code, "")
        if group not in PURCHASED_RAW_MATERIAL_GROUPS:
            skipped.append({
                "item_code": row.item_code,
                "reason": f"Not a purchased raw material (group: {group or 'unknown'})",
            })
            continue

        # Duplicate check: PR + item_code; add supplier_batch_no when provided
        # so two rows of the same item with different batch numbers both get created
        supplier_batch_no = row.get("custom_supplier_batch_no") or ""
        filters = {"purchase_receipt": pr.name, "item_code": row.item_code}
        if supplier_batch_no:
            filters["supplier_batch_no"] = supplier_batch_no

        existing = frappe.db.get_value("Raw Material Batch", filters, "name")
        if existing:
            skipped.append({
                "item_code": row.item_code,
                "reason": f"RMB already exists: {existing}",
            })
            continue

        try:
            item_name = (
                frappe.db.get_value("Item", row.item_code, "item_name")
                or row.item_name
                or row.item_code
            )

            rmb = frappe.new_doc("Raw Material Batch")
            rmb.batch_source     = "Purchased"
            rmb.material_name    = item_name
            rmb.item_code        = row.item_code
            rmb.supplier         = pr.supplier
            rmb.supplier_batch_no = supplier_batch_no
            rmb.mfg_date         = row.get("custom_mfg_date")
            rmb.expiry_date      = row.get("custom_expiry_date")
            rmb.received_date    = pr.posting_date
            rmb.received_qty     = row.qty
            rmb.received_qty_uom = row.uom
            rmb.storage_condition = row.get("custom_storage_condition") or ""
            rmb.warehouse        = row.warehouse
            rmb.purchase_receipt = pr.name
            rmb.purchase_order   = row.get("purchase_order") or ""
            rmb.qc_status        = "Pending"
            rmb.coa_verified     = 0
            rmb.insert(ignore_permissions=True)

            created.append({
                "item_code": row.item_code,
                "material_name": item_name,
                "rmb_name": rmb.name,
            })

        except Exception as e:
            frappe.log_error(
                frappe.get_traceback(),
                f"RMB Create: failed for item {row.item_code} in {purchase_receipt_name}"
            )
            errors.append({"item_code": row.item_code, "reason": str(e)})

    frappe.db.commit()
    return {"created": created, "skipped": skipped, "errors": errors}
