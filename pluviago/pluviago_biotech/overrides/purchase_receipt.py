"""
Server-side function to create Raw Material Batches from a submitted
Purchase Receipt. Called by the client-side "Create Raw Material Batches" button.
"""
import frappe
from pluviago.pluviago_biotech.utils.item_utils import (
    PURCHASED_RAW_MATERIAL_GROUPS,
    get_item_groups,
)


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
            errors.append({"item_code": row.item_code, "reason": str(e)})

    frappe.db.commit()
    return {"created": created, "skipped": skipped, "errors": errors}
