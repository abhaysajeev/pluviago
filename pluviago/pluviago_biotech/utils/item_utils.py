"""
Central definitions for raw material item groups.
Import from here — never hardcode group names or item_code prefixes elsewhere.
"""
import frappe

# Purchased from vendors — require AVL approval before PO, COA before RMB submit
PURCHASED_RAW_MATERIAL_GROUPS = frozenset({
    "Base Salts",
    "Trace Elements",
    "Nutrients",
    "Vitamins",
})

# Prepared in-house (e.g. DI Water) — no vendor, no COA, but consumption tracked
IN_HOUSE_RAW_MATERIAL_GROUPS = frozenset({
    "Lab Consumables",
})

# All groups that can appear as a Raw Material Batch
ALL_TRACKABLE_GROUPS = PURCHASED_RAW_MATERIAL_GROUPS | IN_HOUSE_RAW_MATERIAL_GROUPS


def get_item_groups(item_codes):
    """
    Fetch item_group for a list of item codes in one query.
    Returns {item_code: item_group}.
    """
    if not item_codes:
        return {}
    placeholders = ", ".join(["%s"] * len(item_codes))
    rows = frappe.db.sql(
        f"SELECT name, item_group FROM tabItem WHERE name IN ({placeholders})",
        list(item_codes),
    )
    return {r[0]: r[1] for r in rows}


def filter_purchased_raw_materials(item_codes):
    """Return the subset of item_codes that belong to PURCHASED_RAW_MATERIAL_GROUPS."""
    groups = get_item_groups(item_codes)
    return [code for code in item_codes if groups.get(code, "") in PURCHASED_RAW_MATERIAL_GROUPS]
