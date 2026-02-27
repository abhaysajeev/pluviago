"""
Phase 7: HR Basics — Pluviago Biotech
=======================================
Creates:
  7.1  Departments (5 — Production, Quality Control, Warehouse, R&D, Admin)
  7.2  Designations (from Users(1).xlsx: QA Head, QC Manager, Production Manager,
       Supervisor, Operator, Warehouse Officer, ERP Admin, R&D Officer)

Note: Shift Type DocType does not exist in this ERPNext version,
      so shift setup is skipped.

Run via:
    bench --site replica1.local execute pluviago.setup.phase7.execute

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
    print("  PHASE 7: HR Basics — Pluviago Biotech Pvt. Ltd.")
    print("=" * 70)

    setup_departments()
    frappe.db.commit()

    setup_designations()
    frappe.db.commit()

    print("\n" + "=" * 70)
    print("  ✅ PHASE 7 COMPLETE — HR Basics configured!")
    print("=" * 70 + "\n")


# ══════════════════════════════════════════════
# 7.1  DEPARTMENTS
# ══════════════════════════════════════════════
DEPARTMENTS = [
    "Production",
    "Quality Control",
    "Warehouse",
    "Research & Development",
    "Administration",
]


def setup_departments():
    print("\n── 7.1 Departments ──")

    created = 0
    for dept_name in DEPARTMENTS:
        # Check with company suffix
        full_name = f"{dept_name} - {frappe.db.get_value('Company', COMPANY_NAME, 'abbr') or 'PB'}"
        if frappe.db.exists("Department", full_name) or frappe.db.exists("Department", dept_name):
            print(f"  ⏭  Department: {dept_name} (already exists)")
            continue
        try:
            doc = frappe.get_doc({
                "doctype": "Department",
                "department_name": dept_name,
                "company": COMPANY_NAME,
            })
            doc.insert(ignore_permissions=True)
            print(f"  ✅ Department: {dept_name}")
            created += 1
        except frappe.DuplicateEntryError:
            print(f"  ⏭  Department: {dept_name} (duplicate)")
        except Exception as e:
            print(f"  ❌ Department: {dept_name} — {str(e)[:80]}")

    print(f"  📊 Departments: {created} created")


# ══════════════════════════════════════════════
# 7.2  DESIGNATIONS
# ══════════════════════════════════════════════
# Derived from Users(1).xlsx roles + additional industry designations
DESIGNATIONS = [
    "QA Head",
    "QC Manager",
    "Production Manager",
    "Production Supervisor",
    "Production Operator",
    "Warehouse Officer",
    "ERP Administrator",
    "R&D Officer",
    "Lab Technician",
    "Plant Head",
]


def setup_designations():
    print("\n── 7.2 Designations ──")

    created = 0
    for desig_name in DESIGNATIONS:
        if frappe.db.exists("Designation", desig_name):
            print(f"  ⏭  Designation: {desig_name} (already exists)")
            continue
        try:
            frappe.get_doc({
                "doctype": "Designation",
                "designation_name": desig_name,
            }).insert(ignore_permissions=True)
            print(f"  ✅ Designation: {desig_name}")
            created += 1
        except frappe.DuplicateEntryError:
            print(f"  ⏭  Designation: {desig_name} (duplicate)")
        except Exception as e:
            print(f"  ❌ Designation: {desig_name} — {str(e)[:80]}")

    print(f"  📊 Designations: {created} created")
