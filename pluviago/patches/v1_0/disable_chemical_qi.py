"""
Disable ERPNext Quality Inspection on all chemical items.
Pluviago uses its own Chemical COA + RMB qc_status system for incoming
material QC — ERPNext's built-in QI is redundant and blocks Purchase Receipt.
"""

import frappe


CHEMICAL_ITEM_GROUPS = (
    "Base Salts",
    "Trace Elements",
    "Nutrients",
    "Vitamins",
    "Media Chemicals",
    "Raw Materials",
    "Raw Material",
)


def execute():
    groups_placeholder = ", ".join(["%s"] * len(CHEMICAL_ITEM_GROUPS))
    items = frappe.db.sql(
        f"""
        SELECT name FROM `tabItem`
        WHERE item_group IN ({groups_placeholder})
          AND (inspection_required_before_purchase = 1
               OR inspection_required_before_delivery = 1)
        """,
        CHEMICAL_ITEM_GROUPS,
        as_dict=True,
    )

    if not items:
        print("  No chemical items with QI enabled — nothing to do.")
        return

    names = [r.name for r in items]
    frappe.db.sql(
        f"""
        UPDATE `tabItem`
        SET inspection_required_before_purchase = 0,
            inspection_required_before_delivery = 0
        WHERE name IN ({', '.join(['%s'] * len(names))})
        """,
        names,
    )
    frappe.db.commit()
    print(f"  Disabled QI on {len(names)} chemical item(s): {', '.join(names)}")
