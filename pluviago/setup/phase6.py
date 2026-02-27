"""
Phase 6: Role-Based Access Control (RBAC) — Pluviago Biotech
==============================================================
Creates:
  6.1  Any missing custom roles
  6.2  Custom DocPerm rules for 7 custom roles across key DocTypes

Roles:
  - Production Manager  → Full access to Work Order, Job Card, Stock Entry
  - QA Head             → Approve QI, view all batches, full QC access
  - QC Manager          → Create/submit QI, view batches
  - Production Operator → Update Job Cards only
  - Store Keeper        → Stock Entries, view-only on most
  - Pluviago Admin      → Full system access
  - R&D Officer         → Read-only on production, full on R&D data

Run via:
    bench --site replica1.local execute pluviago.setup.phase6.execute

Idempotent — safe to run multiple times.
"""

import frappe

# ──────────────────────────────────────────────
COMPANY_NAME = "Pluviago Biotech Pvt. Ltd."


# ══════════════════════════════════════════════
# MAIN ENTRY POINT
# ══════════════════════════════════════════════
def execute():
    print("\n" + "=" * 70)
    print("  PHASE 6: Role-Based Access Control — Pluviago Biotech")
    print("=" * 70)

    setup_roles()
    frappe.db.commit()

    setup_permissions()
    frappe.db.commit()

    print("\n" + "=" * 70)
    print("  ✅ PHASE 6 COMPLETE — RBAC configured!")
    print("=" * 70 + "\n")


# ══════════════════════════════════════════════
# 6.1  CUSTOM ROLES
# ══════════════════════════════════════════════
CUSTOM_ROLES = [
    "Production Manager",
    "QA Head",
    "QC Manager",
    "Production Operator",
    "Store Keeper",
    "Pluviago Admin",
    "R&D Officer",
]


def setup_roles():
    print("\n── 6.1 Custom Roles ──")

    created = 0
    for role_name in CUSTOM_ROLES:
        if frappe.db.exists("Role", role_name):
            print(f"  ⏭  Role: {role_name} (already exists)")
            continue
        try:
            frappe.get_doc({
                "doctype": "Role",
                "role_name": role_name,
                "desk_access": 1,
                "is_custom": 1,
            }).insert(ignore_permissions=True)
            print(f"  ✅ Role: {role_name}")
            created += 1
        except Exception as e:
            print(f"  ❌ Role: {role_name} — {str(e)[:80]}")

    print(f"  📊 Roles: {created} created")


# ══════════════════════════════════════════════
# 6.2  CUSTOM DOC PERMS
# ══════════════════════════════════════════════

# Permission matrix:
# (parent_doctype, role, permlevel, select, read, write, create, delete, submit, cancel, amend, report, export, print, email, share)
# Using shorthand: R=read, W=write, C=create, D=delete, S=submit, X=cancel, A=amend, RP=report, EX=export, PR=print, EM=email, SH=share

def _perm(parent, role, permlevel=0, **kwargs):
    """Helper to build a permission dict."""
    return {
        "parent": parent,
        "role": role,
        "permlevel": permlevel,
        "select": kwargs.get("select", 1),
        "read": kwargs.get("read", 1),
        "write": kwargs.get("write", 0),
        "create": kwargs.get("create", 0),
        "delete": kwargs.get("delete", 0),
        "submit": kwargs.get("submit", 0),
        "cancel": kwargs.get("cancel", 0),
        "amend": kwargs.get("amend", 0),
        "report": kwargs.get("report", 1),
        "export": kwargs.get("export", 0),
        "print": kwargs.get("print", 1),
        "email": kwargs.get("email", 0),
        "share": kwargs.get("share", 0),
    }


PERMISSION_RULES = [
    # ──── Production Manager ────
    # Full access to Work Order, Job Card, Stock Entry, BOM
    _perm("Work Order", "Production Manager",
          write=1, create=1, delete=1, submit=1, cancel=1, amend=1,
          export=1, email=1, share=1),
    _perm("Job Card", "Production Manager",
          write=1, create=1, delete=1, submit=1, cancel=1, amend=1,
          export=1, share=1),
    _perm("Stock Entry", "Production Manager",
          write=1, create=1, submit=1, cancel=1, amend=1,
          export=1),
    _perm("BOM", "Production Manager",
          write=1, create=1, submit=1, cancel=1, amend=1,
          export=1),
    # Read access to QI, Batch, Item
    _perm("Quality Inspection", "Production Manager"),
    _perm("Batch", "Production Manager"),
    _perm("Item", "Production Manager"),
    _perm("Warehouse", "Production Manager"),
    # Asset read
    _perm("Asset", "Production Manager"),
    _perm("Asset Maintenance", "Production Manager", write=1),

    # ──── QA Head ────
    # Full QI access including approve
    _perm("Quality Inspection", "QA Head",
          write=1, create=1, delete=1, submit=1, cancel=1, amend=1,
          export=1, email=1, share=1),
    # Read all batches, items
    _perm("Batch", "QA Head", write=1, export=1),
    _perm("Item", "QA Head", export=1),
    # Read work orders and stock entries
    _perm("Work Order", "QA Head"),
    _perm("Stock Entry", "QA Head"),
    # Purchase Invoice (COA approval workflow)
    _perm("Purchase Invoice", "QA Head", write=1),
    # Quality Inspection Template
    _perm("Quality Inspection Template", "QA Head",
          write=1, create=1, delete=1, export=1),

    # ──── QC Manager ────
    # Create/submit QI
    _perm("Quality Inspection", "QC Manager",
          write=1, create=1, submit=1, amend=1,
          export=1, email=1),
    _perm("Batch", "QC Manager", export=1),
    _perm("Item", "QC Manager"),
    _perm("Work Order", "QC Manager"),
    _perm("Stock Entry", "QC Manager"),
    _perm("Quality Inspection Template", "QC Manager",
          write=1, create=1),

    # ──── Production Operator ────
    # Update Job Cards, read Work Orders
    _perm("Job Card", "Production Operator",
          write=1, submit=1),
    _perm("Work Order", "Production Operator"),
    _perm("Stock Entry", "Production Operator",
          write=1, create=1, submit=1),
    _perm("Item", "Production Operator"),
    _perm("Batch", "Production Operator"),
    _perm("Warehouse", "Production Operator"),

    # ──── Store Keeper ────
    # Stock Entries, Purchase Receipt
    _perm("Stock Entry", "Store Keeper",
          write=1, create=1, submit=1, cancel=1,
          export=1),
    _perm("Purchase Receipt", "Store Keeper",
          write=1, create=1, submit=1),
    _perm("Delivery Note", "Store Keeper",
          write=1, create=1, submit=1),
    _perm("Item", "Store Keeper"),
    _perm("Batch", "Store Keeper", export=1),
    _perm("Warehouse", "Store Keeper"),
    _perm("Material Request", "Store Keeper",
          write=1, create=1, submit=1),
    # Read-only on manufacturing
    _perm("Work Order", "Store Keeper"),
    _perm("BOM", "Store Keeper"),

    # ──── Pluviago Admin ────
    # Full access everywhere
    _perm("Work Order", "Pluviago Admin",
          write=1, create=1, delete=1, submit=1, cancel=1, amend=1,
          export=1, email=1, share=1),
    _perm("Job Card", "Pluviago Admin",
          write=1, create=1, delete=1, submit=1, cancel=1, amend=1,
          export=1, share=1),
    _perm("Stock Entry", "Pluviago Admin",
          write=1, create=1, delete=1, submit=1, cancel=1, amend=1,
          export=1, email=1, share=1),
    _perm("Quality Inspection", "Pluviago Admin",
          write=1, create=1, delete=1, submit=1, cancel=1, amend=1,
          export=1, email=1, share=1),
    _perm("BOM", "Pluviago Admin",
          write=1, create=1, delete=1, submit=1, cancel=1, amend=1,
          export=1, share=1),
    _perm("Batch", "Pluviago Admin",
          write=1, create=1, delete=1,
          export=1, share=1),
    _perm("Item", "Pluviago Admin",
          write=1, create=1, delete=1,
          export=1, share=1),
    _perm("Warehouse", "Pluviago Admin",
          write=1, create=1, delete=1, share=1),
    _perm("Purchase Order", "Pluviago Admin",
          write=1, create=1, delete=1, submit=1, cancel=1, amend=1,
          export=1, email=1, share=1),
    _perm("Purchase Invoice", "Pluviago Admin",
          write=1, create=1, delete=1, submit=1, cancel=1, amend=1,
          export=1, email=1, share=1),
    _perm("Purchase Receipt", "Pluviago Admin",
          write=1, create=1, delete=1, submit=1, cancel=1, amend=1,
          export=1, share=1),
    _perm("Delivery Note", "Pluviago Admin",
          write=1, create=1, delete=1, submit=1, cancel=1, amend=1,
          export=1, share=1),
    _perm("Sales Order", "Pluviago Admin",
          write=1, create=1, delete=1, submit=1, cancel=1, amend=1,
          export=1, email=1, share=1),
    _perm("Material Request", "Pluviago Admin",
          write=1, create=1, delete=1, submit=1, cancel=1, amend=1,
          export=1, share=1),
    _perm("Asset", "Pluviago Admin",
          write=1, create=1, delete=1, submit=1, cancel=1, amend=1,
          export=1, share=1),
    _perm("Asset Maintenance", "Pluviago Admin",
          write=1, create=1, delete=1,
          export=1, share=1),
    _perm("Quality Inspection Template", "Pluviago Admin",
          write=1, create=1, delete=1,
          export=1),

    # ──── R&D Officer ────
    # Read-only on production, full on QI templates
    _perm("Work Order", "R&D Officer"),
    _perm("Job Card", "R&D Officer"),
    _perm("Stock Entry", "R&D Officer"),
    _perm("Quality Inspection", "R&D Officer", export=1),
    _perm("Batch", "R&D Officer", export=1),
    _perm("Item", "R&D Officer", export=1),
    _perm("BOM", "R&D Officer", write=1, create=1, export=1),
    _perm("Quality Inspection Template", "R&D Officer",
          write=1, create=1, export=1),
]


def setup_permissions():
    print("\n── 6.2 Custom DocPerm Rules ──")

    created = 0
    skipped = 0

    for perm in PERMISSION_RULES:
        parent = perm["parent"]
        role = perm["role"]
        permlevel = perm.get("permlevel", 0)

        # Check if this exact rule already exists
        existing = frappe.db.exists("Custom DocPerm", {
            "parent": parent,
            "role": role,
            "permlevel": permlevel,
        })

        if existing:
            skipped += 1
            continue

        try:
            doc = frappe.get_doc({
                "doctype": "Custom DocPerm",
                **perm,
            })
            doc.insert(ignore_permissions=True)
            print(f"  ✅ {parent}: {role} (perm level {permlevel})")
            created += 1
        except Exception as e:
            print(f"  ❌ {parent}: {role} — {str(e)[:100]}")
            skipped += 1

    print(f"\n  📊 Permissions: {created} created, {skipped} skipped")
