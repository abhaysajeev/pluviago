import frappe
from frappe.utils import nowdate
from pluviago.pluviago_biotech.utils.item_utils import (
    PURCHASED_RAW_MATERIAL_GROUPS,
    get_item_groups,
)


def validate(doc, method=None):
    """
    On Purchase Order validate: hard-block if supplier is not in the Approved
    Vendor List for any purchased raw material item, or if qualification expired.
    Detection is item-group based — not dependent on item code naming.
    """
    if not doc.items:
        return

    # One query to get item groups for all items on this PO
    all_codes = list({row.item_code for row in doc.items if row.item_code})
    item_groups = get_item_groups(all_codes)

    # Only check items whose group requires AVL (purchased raw materials)
    trackable = [
        code for code in all_codes
        if item_groups.get(code, "") in PURCHASED_RAW_MATERIAL_GROUPS
    ]
    if not trackable:
        return

    # Single query — find which trackable items ARE approved for this supplier
    placeholders = ", ".join(["%s"] * len(trackable))
    approved_rows = frappe.db.sql(
        f"""
        SELECT avi.item_code
        FROM `tabApproved Vendor` av
        JOIN `tabApproved Vendor Item` avi ON avi.parent = av.name
        WHERE av.supplier = %s
          AND avi.item_code IN ({placeholders})
          AND av.approval_status = 'Approved'
          AND av.valid_upto >= %s
        """,
        [doc.supplier] + trackable + [nowdate()],
    )
    approved_set = {row[0] for row in approved_rows}

    unapproved = []
    for row in doc.items:
        if (row.item_code
                and item_groups.get(row.item_code, "") in PURCHASED_RAW_MATERIAL_GROUPS
                and row.item_code not in approved_set):
            unapproved.append(f"<li>{row.item_name or row.item_code}</li>")

    if unapproved:
        frappe.throw(
            msg=f"""
                Supplier <b>{doc.supplier}</b> is not in the Approved Vendor List for:
                <ul>{"".join(unapproved)}</ul>
                Create an Approved Vendor record with status <b>Approved</b> before raising a Purchase Order.
            """,
            title="Vendor Not Approved",
        )
