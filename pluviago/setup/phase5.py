"""
Phase 5: Asset Management — Pluviago Biotech
=============================================
Creates:
  5.1  Locations (5 production locations)
  5.2  Asset Categories (3 — Bioreactors, Lab Equipment, Process Equipment)
  5.3  Asset Items (non-stock fixed asset items for each equipment)
  5.4  Assets (13 equipment records)
  5.5  Asset Maintenance Team + Asset Maintenance Schedules

Run via:
    bench --site replica1.local execute pluviago.setup.phase5.execute

Idempotent — safe to run multiple times.
"""

import frappe
from frappe.utils import nowdate, add_months

# ──────────────────────────────────────────────
COMPANY_NAME = "Pluviago Biotech Pvt. Ltd."
COMPANY_ABBR = "PB"

_abbr = None


def get_abbr():
    global _abbr
    if _abbr is None:
        _abbr = frappe.db.get_value("Company", COMPANY_NAME, "abbr") or COMPANY_ABBR
    return _abbr


def acct(name):
    return f"{name} - {get_abbr()}"


# ══════════════════════════════════════════════
# MAIN ENTRY POINT
# ══════════════════════════════════════════════
def execute():
    print("\n" + "=" * 70)
    print("  PHASE 5: Asset Management — Pluviago Biotech Pvt. Ltd.")
    print("=" * 70)

    setup_locations()
    frappe.db.commit()

    setup_asset_categories()
    frappe.db.commit()

    setup_asset_items()
    frappe.db.commit()

    setup_assets()
    frappe.db.commit()

    setup_maintenance()
    frappe.db.commit()

    print("\n" + "=" * 70)
    print("  ✅ PHASE 5 COMPLETE — Asset Management configured!")
    print("=" * 70 + "\n")


# ══════════════════════════════════════════════
# 5.1  LOCATIONS
# ══════════════════════════════════════════════
LOCATIONS = [
    "Media Lab",
    "Seed Lab",
    "Fermentation Hall",
    "Downstream Processing",
    "QC Lab",
    "Packing Area",
]


def setup_locations():
    print("\n── 5.1 Locations ──")

    created = 0
    for loc_name in LOCATIONS:
        if frappe.db.exists("Location", loc_name):
            print(f"  ⏭  Location: {loc_name} (already exists)")
            continue
        try:
            frappe.get_doc({
                "doctype": "Location",
                "location_name": loc_name,
            }).insert(ignore_permissions=True)
            print(f"  ✅ Location: {loc_name}")
            created += 1
        except Exception as e:
            print(f"  ❌ Location: {loc_name} — {str(e)[:80]}")

    print(f"  📊 Locations: {created} created")


# ══════════════════════════════════════════════
# 5.2  ASSET CATEGORIES
# ══════════════════════════════════════════════
ASSET_CATEGORIES = [
    # (category_name, fixed_asset_account)
    ("Bioreactors",       "Plants and Machineries"),
    ("Lab Equipment",     "Capital Equipments"),
    ("Process Equipment", "Plants and Machineries"),
]


def setup_asset_categories():
    print("\n── 5.2 Asset Categories ──")

    created = 0
    for cat_name, fa_account_short in ASSET_CATEGORIES:
        if frappe.db.exists("Asset Category", cat_name):
            print(f"  ⏭  Asset Category: {cat_name} (already exists)")
            continue
        try:
            doc = frappe.get_doc({
                "doctype": "Asset Category",
                "asset_category_name": cat_name,
                "accounts": [{
                    "company_name": COMPANY_NAME,
                    "fixed_asset_account": acct(fa_account_short),
                    "accumulated_depreciation_account": acct("Accumulated Depreciation"),
                    "depreciation_expense_account": acct("Depreciation"),
                    "capital_work_in_progress_account": acct("CWIP Account"),
                }],
            })
            doc.insert(ignore_permissions=True)
            print(f"  ✅ Asset Category: {cat_name}")
            created += 1
        except Exception as e:
            print(f"  ❌ Asset Category: {cat_name} — {str(e)[:120]}")

    print(f"  📊 Asset Categories: {created} created")


# ══════════════════════════════════════════════
# 5.3  ASSET ITEMS (non-stock, fixed asset items)
# ══════════════════════════════════════════════
ASSET_ITEMS = [
    # (item_code, item_name, asset_category, description)
    ("AST-PBR-025",    "Photobioreactor 25L",       "Bioreactors",       "Closed PBR for seed culture — 25L capacity"),
    ("AST-PBR-275",    "Photobioreactor 275L",      "Bioreactors",       "Closed PBR for intermediate culture — 275L capacity"),
    ("AST-PBR-925",    "Photobioreactor 925L",      "Bioreactors",       "Closed PBR for large seed culture — 925L capacity"),
    ("AST-PBR-6600",   "Photobioreactor 6600L",     "Bioreactors",       "Closed PBR for production — 6600L capacity"),
    ("AST-AUT-001",    "Autoclave",                 "Lab Equipment",     "Steam sterilizer for media and equipment"),
    ("AST-MIC-001",    "Microscope",                "Lab Equipment",     "Optical microscope for cell morphology and contamination checks"),
    ("AST-PHM-001",    "pH Meter",                  "Lab Equipment",     "Digital pH meter for media and culture pH monitoring"),
    ("AST-OD-001",     "Spectrophotometer",         "Lab Equipment",     "UV-Vis spectrophotometer for OD and assay measurements"),
    ("AST-DRY-001",    "Industrial Dryer",          "Process Equipment", "Spray/drum dryer for biomass drying"),
    ("AST-HRV-001",    "Harvester",                 "Process Equipment", "Centrifugal harvester for biomass separation"),
]


def setup_asset_items():
    print("\n── 5.3 Asset Items (Fixed Asset) ──")

    created = 0
    for item_code, item_name, asset_category, desc in ASSET_ITEMS:
        if frappe.db.exists("Item", item_code):
            print(f"  ⏭  Asset Item: {item_code} (already exists)")
            continue
        try:
            frappe.get_doc({
                "doctype": "Item",
                "item_code": item_code,
                "item_name": item_name,
                "item_group": "All Item Groups",
                "stock_uom": "Nos",
                "is_stock_item": 0,
                "is_fixed_asset": 1,
                "asset_category": asset_category,
                "description": desc,
            }).insert(ignore_permissions=True)
            print(f"  ✅ Asset Item: {item_code} — {item_name}")
            created += 1
        except Exception as e:
            print(f"  ❌ Asset Item: {item_code} — {str(e)[:120]}")

    print(f"  📊 Asset Items: {created} created")


# ══════════════════════════════════════════════
# 5.4  ASSETS
# ══════════════════════════════════════════════
ASSETS = [
    # (asset_name, item_code, location, gross_value)
    ("Photobioreactor 25L #1",    "AST-PBR-025",  "Fermentation Hall",      500000),
    ("Photobioreactor 25L #2",    "AST-PBR-025",  "Fermentation Hall",      500000),
    ("Photobioreactor 275L #1",   "AST-PBR-275",  "Fermentation Hall",     1500000),
    ("Photobioreactor 275L #2",   "AST-PBR-275",  "Fermentation Hall",     1500000),
    ("Photobioreactor 925L #1",   "AST-PBR-925",  "Fermentation Hall",     3000000),
    ("Photobioreactor 925L #2",   "AST-PBR-925",  "Fermentation Hall",     3000000),
    ("Photobioreactor 6600L",     "AST-PBR-6600", "Fermentation Hall",     8000000),
    ("Autoclave",                 "AST-AUT-001",  "Media Lab",              300000),
    ("Microscope",                "AST-MIC-001",  "QC Lab",                 150000),
    ("pH Meter",                  "AST-PHM-001",  "QC Lab",                  25000),
    ("Spectrophotometer",         "AST-OD-001",   "QC Lab",                 400000),
    ("Industrial Dryer",          "AST-DRY-001",  "Downstream Processing",  600000),
    ("Harvester",                 "AST-HRV-001",  "Downstream Processing",  450000),
]


def setup_assets():
    print("\n── 5.4 Assets ──")

    created = 0
    for asset_name, item_code, location, gross_value in ASSETS:
        if frappe.db.exists("Asset", {"asset_name": asset_name, "company": COMPANY_NAME}):
            print(f"  ⏭  Asset: {asset_name} (already exists)")
            continue
        try:
            doc = frappe.get_doc({
                "doctype": "Asset",
                "asset_name": asset_name,
                "item_code": item_code,
                "company": COMPANY_NAME,
                "location": location,
                "purchase_date": "2025-01-01",
                "gross_purchase_amount": gross_value,
                "asset_owner": "Company",
                "asset_owner_company": COMPANY_NAME,
                "is_existing_asset": 1,
            })
            doc.insert(ignore_permissions=True)
            print(f"  ✅ Asset: {asset_name} (₹{gross_value:,.0f})")
            created += 1
        except Exception as e:
            print(f"  ❌ Asset: {asset_name} — {str(e)[:120]}")

    print(f"  📊 Assets: {created} created")


# ══════════════════════════════════════════════
# 5.5  ASSET MAINTENANCE
# ══════════════════════════════════════════════
# Maintenance tasks per asset category
MAINTENANCE_TASKS = {
    "Bioreactors": [
        ("CIP Cleaning",        "Preventive Maintenance",  "Monthly"),
        ("Seal Inspection",     "Preventive Maintenance",  "Quarterly"),
        ("Sensor Calibration",  "Calibration",             "Monthly"),
    ],
    "Lab Equipment": [
        ("Calibration",                "Calibration",             "Monthly"),
        ("Preventive Maintenance",     "Preventive Maintenance",  "Quarterly"),
    ],
    "Process Equipment": [
        ("General Maintenance", "Preventive Maintenance",  "Monthly"),
        ("Performance Check",   "Preventive Maintenance",  "Quarterly"),
    ],
}

# Special overrides for specific assets
ASSET_MAINTENANCE_OVERRIDES = {
    "Microscope": [
        ("Lens Cleaning & Calibration", "Calibration", "Yearly"),
    ],
    "Autoclave": [
        ("Pressure Validation",    "Preventive Maintenance",  "Quarterly"),
        ("Steam Trap Inspection",  "Preventive Maintenance",  "Yearly"),
    ],
}


def setup_maintenance():
    print("\n── 5.5 Asset Maintenance ──")

    # First ensure a maintenance team exists
    team_name = _ensure_maintenance_team()
    if not team_name:
        print("  ⚠️  Cannot create maintenance schedules without a team")
        return

    created = 0

    # Get all created assets
    assets = frappe.get_all(
        "Asset",
        filters={"company": COMPANY_NAME},
        fields=["name", "asset_name", "item_code", "asset_category"]
    )

    for asset in assets:
        # Check if maintenance already exists
        if frappe.db.exists("Asset Maintenance", {"asset_name": asset.name}):
            print(f"  ⏭  Maintenance: {asset.asset_name} (already exists)")
            continue

        # Determine tasks: use override if exists, else category default
        asset_display = asset.asset_name
        tasks = ASSET_MAINTENANCE_OVERRIDES.get(asset_display, [])

        if not tasks:
            # Use category-based tasks
            category = asset.asset_category or ""
            tasks = MAINTENANCE_TASKS.get(category, [])

        if not tasks:
            print(f"  ⏭  Maintenance: {asset_display} (no tasks defined)")
            continue

        try:
            today = nowdate()

            # Get team members to assign tasks to
            team_doc = frappe.get_doc("Asset Maintenance Team", team_name)
            admin_user = team_doc.maintenance_team_members[0].team_member if team_doc.maintenance_team_members else "Administrator"

            task_rows = []
            for task_name, maint_type, periodicity in tasks:
                task_rows.append({
                    "maintenance_task": task_name,
                    "maintenance_type": maint_type,
                    "periodicity": periodicity,
                    "maintenance_status": "Planned",
                    "start_date": today,
                    "assign_to": admin_user,
                })

            doc = frappe.get_doc({
                "doctype": "Asset Maintenance",
                "asset_name": asset.name,
                "company": COMPANY_NAME,
                "maintenance_team": team_name,
                "asset_maintenance_tasks": task_rows,
            })
            doc.insert(ignore_permissions=True)
            print(f"  ✅ Maintenance: {asset_display} ({len(task_rows)} tasks)")
            created += 1
        except Exception as e:
            print(f"  ❌ Maintenance: {asset_display} — {str(e)[:120]}")

    print(f"\n  📊 Asset Maintenance: {created} created")


def _ensure_maintenance_team():
    """Create or find maintenance team."""
    team_name = "Pluviago Maintenance Team"

    if frappe.db.exists("Asset Maintenance Team", team_name):
        print(f"  ⏭  Maintenance Team: {team_name} (already exists)")
        return team_name

    try:
        # Get admin user for team manager
        admin_user = frappe.db.get_value("User", {"name": ("like", "%admin%"), "enabled": 1}, "name")
        if not admin_user:
            admin_user = frappe.session.user or "Administrator"

        # maintenance_role is required on team members
        maint_role = "Production Manager"
        if not frappe.db.exists("Role", maint_role):
            maint_role = "System Manager"

        doc = frappe.get_doc({
            "doctype": "Asset Maintenance Team",
            "maintenance_team_name": team_name,
            "company": COMPANY_NAME,
            "maintenance_manager": admin_user,
            "maintenance_team_members": [
                {
                    "team_member": admin_user,
                    "maintenance_role": maint_role,
                }
            ],
        })
        doc.insert(ignore_permissions=True)
        print(f"  ✅ Maintenance Team: {team_name}")
        return team_name
    except Exception as e:
        print(f"  ❌ Maintenance Team: {str(e)[:120]}")
        return None
