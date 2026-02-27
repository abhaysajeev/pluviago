"""
Phase 1: Foundation Setup - Pluviago Biotech
=============================================
Creates all master data for Pluviago Biotech ERPNext implementation.

Run via:
    bench --site replica1.local execute pluviago.setup.phase1.execute

This script is idempotent - safe to run multiple times.
It will skip records that already exist.
"""

import frappe
from frappe.utils import nowdate, getdate

# ──────────────────────────────────────────────
# CONSTANTS
# ──────────────────────────────────────────────
COMPANY_NAME = "Pluviago Biotech Pvt. Ltd."
COMPANY_ABBR = "PB"
COUNTRY = "India"
CURRENCY = "INR"

# Will be set dynamically based on actual company
_abbr = None


def get_abbr():
    global _abbr
    if _abbr is None:
        _abbr = frappe.db.get_value("Company", COMPANY_NAME, "abbr") or COMPANY_ABBR
    return _abbr


def wh(name):
    """Build warehouse name with company abbreviation. e.g., wh('Raw Material Store') => 'Raw Material Store - PB'"""
    return f"{name} - {get_abbr()}"


def create_if_not_exists(doctype, name, doc_dict):
    """Create a document if it doesn't already exist. Returns True if created, False if skipped."""
    if frappe.db.exists(doctype, name):
        print(f"  ⏭  {doctype}: {name} (already exists)")
        return False
    try:
        doc_dict["doctype"] = doctype
        doc = frappe.get_doc(doc_dict)
        doc.insert(ignore_permissions=True)
        print(f"  ✅ {doctype}: {name}")
        return True
    except frappe.DuplicateEntryError:
        print(f"  ⏭  {doctype}: {name} (duplicate)")
        return False
    except Exception as e:
        print(f"  ❌ {doctype}: {name} — Error: {str(e)}")
        return False


# ══════════════════════════════════════════════
# MAIN ENTRY POINT
# ══════════════════════════════════════════════
def execute():
    """Main entry point for Phase 1 setup."""
    print("\n" + "=" * 70)
    print("  PHASE 1: Foundation Setup — Pluviago Biotech Pvt. Ltd.")
    print("=" * 70)

    setup_company()
    frappe.db.commit()

    setup_fiscal_year()
    frappe.db.commit()

    setup_uoms()
    frappe.db.commit()

    setup_item_groups()
    frappe.db.commit()

    setup_warehouses()
    frappe.db.commit()

    setup_workstations()
    frappe.db.commit()

    setup_operations()
    frappe.db.commit()

    setup_suppliers()
    frappe.db.commit()

    setup_customers()
    frappe.db.commit()

    setup_items()
    frappe.db.commit()

    print("\n" + "=" * 70)
    print("  ✅ PHASE 1 COMPLETE — All master data created successfully!")
    print("=" * 70 + "\n")


# ──────────────────────────────────────────────
# 1.1 COMPANY SETUP
# ──────────────────────────────────────────────
def setup_company():
    global _abbr
    print("\n── 1.1 Company Setup ──")

    if frappe.db.exists("Company", COMPANY_NAME):
        _abbr = frappe.db.get_value("Company", COMPANY_NAME, "abbr")
        print(f"  ⏭  Company '{COMPANY_NAME}' already exists (abbr: {_abbr})")
        return

    try:
        company = frappe.get_doc({
            "doctype": "Company",
            "company_name": COMPANY_NAME,
            "abbr": COMPANY_ABBR,
            "default_currency": CURRENCY,
            "country": COUNTRY,
            "chart_of_accounts": "Standard",
            "enable_perpetual_inventory": 1,
        })
        company.insert(ignore_permissions=True)
        _abbr = COMPANY_ABBR
        print(f"  ✅ Company '{COMPANY_NAME}' created (abbr: {_abbr})")
    except Exception as e:
        print(f"  ❌ Company creation failed: {str(e)}")
        print("     → Please create the company manually via Setup Wizard and re-run this script.")
        # Try to use existing company
        existing = frappe.db.get_all("Company", fields=["name", "abbr"], limit=1)
        if existing:
            _abbr = existing[0].abbr
            print(f"     → Using existing company: {existing[0].name} (abbr: {_abbr})")


# ──────────────────────────────────────────────
# 1.1b FISCAL YEAR
# ──────────────────────────────────────────────
def setup_fiscal_year():
    print("\n── 1.1b Fiscal Year Setup ──")

    fiscal_years = [
        ("2025-2026", "2025-04-01", "2026-03-31"),
        ("2026-2027", "2026-04-01", "2027-03-31"),
    ]

    for fy_name, start, end in fiscal_years:
        create_if_not_exists("Fiscal Year", fy_name, {
            "year": fy_name,
            "year_start_date": start,
            "year_end_date": end,
        })


# ──────────────────────────────────────────────
# 1.2 UOM SETUP
# ──────────────────────────────────────────────
CUSTOM_UOMS = [
    # (uom_name, must_be_whole_number)
    ("mg", 0),
    ("mL", 0),
    ("g/L", 0),
    ("um", 0),           # micrometer (µm)
    ("cells/mL", 0),
    ("umol/m2/s", 0),    # PAR unit (µmol/m²/s)
    ("CFU/g", 0),
]


def setup_uoms():
    print("\n── 1.2 UOM Setup ──")

    for uom_name, whole_number in CUSTOM_UOMS:
        create_if_not_exists("UOM", uom_name, {
            "uom_name": uom_name,
            "must_be_whole_number": whole_number,
        })

    # UOM Conversion Factors (system-level)
    uom_conversions = [
        ("mg", "Gram", 0.001),
        ("mL", "Litre", 0.001),
        ("Gram", "Kg", 0.001),
    ]

    for from_uom, to_uom, value in uom_conversions:
        conversion_name = f"{from_uom}-{to_uom}"
        if not frappe.db.exists("UOM Conversion Factor", {"from_uom": from_uom, "to_uom": to_uom}):
            try:
                doc = frappe.get_doc({
                    "doctype": "UOM Conversion Factor",
                    "from_uom": from_uom,
                    "to_uom": to_uom,
                    "value": value,
                })
                doc.insert(ignore_permissions=True)
                print(f"  ✅ UOM Conversion: {from_uom} → {to_uom} ({value})")
            except Exception as e:
                print(f"  ⏭  UOM Conversion: {from_uom} → {to_uom} ({str(e)})")
        else:
            print(f"  ⏭  UOM Conversion: {from_uom} → {to_uom} (already exists)")


# ──────────────────────────────────────────────
# 1.3 ITEM GROUPS
# ──────────────────────────────────────────────
# Format: (group_name, parent_group, is_group)
ITEM_GROUPS = [
    # Level 1 — under "All Item Groups"
    ("Raw Materials", "All Item Groups", 1),
    ("Stock Solutions", "All Item Groups", 1),
    ("Culture Media", "All Item Groups", 0),
    ("Work In Progress", "All Item Groups", 1),
    ("Semi-Finished Goods", "All Item Groups", 0),
    ("Finished Goods", "All Item Groups", 0),
    ("Consumables", "All Item Groups", 1),
    ("Services", "All Item Groups", 0),

    # Level 2 — under Raw Materials
    ("Media Chemicals", "Raw Materials", 1),
    ("Packing Materials", "Raw Materials", 0),

    # Level 3 — under Media Chemicals
    ("Base Salts", "Media Chemicals", 0),
    ("Trace Elements", "Media Chemicals", 0),
    ("Vitamins", "Media Chemicals", 0),
    ("Nutrients", "Media Chemicals", 0),

    # Level 2 — under Stock Solutions
    ("Trace Element Stocks", "Stock Solutions", 0),
    ("Vitamin Stocks", "Stock Solutions", 0),
    ("Nutrient Stocks", "Stock Solutions", 0),

    # Level 2 — under Work In Progress
    ("Seed Culture", "Work In Progress", 0),
    ("Seed Reactor Output", "Work In Progress", 0),
    ("Production Biomass", "Work In Progress", 0),

    # Level 2 — under Consumables
    ("Lab Consumables", "Consumables", 0),
    ("Packaging Materials", "Consumables", 0),
]


def setup_item_groups():
    print("\n── 1.3 Item Group Hierarchy ──")

    for group_name, parent, is_group in ITEM_GROUPS:
        create_if_not_exists("Item Group", group_name, {
            "item_group_name": group_name,
            "parent_item_group": parent,
            "is_group": is_group,
        })


# ──────────────────────────────────────────────
# 1.4 WAREHOUSE HIERARCHY
# ──────────────────────────────────────────────
def get_warehouse_tree():
    """Returns warehouse hierarchy as (name, parent_name, is_group) tuples.
    Parent names use wh() to append company abbreviation."""
    root = COMPANY_NAME  # Root warehouse is auto-created with company

    return [
        # Level 1 — top-level warehouse groups
        ("Raw Material Store",       root, 1),
        ("QC Hold Area",             root, 1),
        ("Production Floor",         root, 1),
        ("Finished Goods Store",     root, 1),
        ("Subcontractor Transit",    root, 1),

        # Level 2 — under Raw Material Store
        ("Chemical Store Cold",      "Raw Material Store",    0),   # 2-8°C
        ("Chemical Store RT",        "Raw Material Store",    0),   # Room Temperature
        ("Packing Material Store",   "Raw Material Store",    0),

        # Level 2 — under QC Hold Area
        ("Incoming Material Hold",   "QC Hold Area",          0),
        ("In-Process Hold",          "QC Hold Area",          0),

        # Level 2 — under Production Floor
        ("Media Preparation Area",   "Production Floor",      0),
        ("Fermentation Area",        "Production Floor",      0),
        ("Harvesting Area",          "Production Floor",      0),
        ("Drying Area",              "Production Floor",      0),

        # Level 2 — under Finished Goods Store
        ("Packed Biomass Store",     "Finished Goods Store",  0),
        ("Dispatch Area",            "Finished Goods Store",  0),

        # Level 2 — under Subcontractor Transit
        ("Sent for Extraction",      "Subcontractor Transit", 0),
        ("Returned Material Hold",   "Subcontractor Transit", 0),
    ]


def setup_warehouses():
    print("\n── 1.4 Warehouse Hierarchy ──")
    a = get_abbr()

    for name, parent, is_group in get_warehouse_tree():
        full_name = wh(name)
        parent_full = wh(parent) if parent != COMPANY_NAME else wh(COMPANY_NAME)

        # Check if parent exists (company root warehouse)
        if parent == COMPANY_NAME and not frappe.db.exists("Warehouse", parent_full):
            # Company root warehouse should be auto-created, but if not, try the abbr-only version
            alt_parent = f"{COMPANY_NAME} - {a}"
            if frappe.db.exists("Warehouse", alt_parent):
                parent_full = alt_parent
            else:
                print(f"  ⚠️  Root warehouse not found: {parent_full}")
                print(f"     → Creating root warehouse")
                try:
                    frappe.get_doc({
                        "doctype": "Warehouse",
                        "warehouse_name": COMPANY_NAME,
                        "company": COMPANY_NAME,
                        "is_group": 1,
                    }).insert(ignore_permissions=True)
                    parent_full = wh(COMPANY_NAME)
                except Exception:
                    pass

        create_if_not_exists("Warehouse", full_name, {
            "warehouse_name": name,
            "parent_warehouse": parent_full,
            "company": COMPANY_NAME,
            "is_group": is_group,
        })


# ──────────────────────────────────────────────
# 1.5 WORKSTATIONS
# ──────────────────────────────────────────────
# Format: (workstation_name, production_capacity, hour_rate, description)
WORKSTATIONS = [
    ("Media Preparation Station",  50,   0, "Media prep lab — capacity 50 L/day"),
    ("Flask Culture Station",      20,   0, "Seed lab — capacity 20 flasks"),
    ("PBR 25L Reactor Bay",        2,    0, "Fermentation — 2 x 25L PBR units"),
    ("PBR 275L Reactor Bay",       2,    0, "Fermentation — 2 x 275L PBR units"),
    ("PBR 925L Reactor Bay",       2,    0, "Fermentation — 2 x 925L PBR units"),
    ("PBR 6600L Production Bay",   1,    0, "Fermentation — 1 x 6600L production PBR"),
    ("Harvesting Station",         1,    0, "Downstream — 1 batch at a time"),
    ("Drying Station",             1,    0, "Downstream — 1 batch at a time"),
    ("Packing Line",               100,  0, "Packing — capacity 100 Kg/day"),
]


def setup_workstations():
    print("\n── 1.5 Workstation Setup ──")

    for ws_name, capacity, hour_rate, desc in WORKSTATIONS:
        create_if_not_exists("Workstation", ws_name, {
            "workstation_name": ws_name,
            "production_capacity": capacity,
            "hour_rate": hour_rate,
            "description": desc,
        })


# ──────────────────────────────────────────────
# 1.6 OPERATIONS
# ──────────────────────────────────────────────
# Format: (operation_name, description)
OPERATIONS = [
    ("Stock Solution Preparation",   "Prepare trace element, vitamin, and nutrient stock solutions"),
    ("Green Medium Preparation",     "Prepare green culture medium from base salts and stock solutions"),
    ("Red Medium Preparation",       "Prepare BG-11 red culture medium from base salts and stock solutions"),
    ("Formulation Mixing",           "Mix 75% green medium + 25% red medium to create Formulation V"),
    ("Flask Inoculation",            "Inoculate seed culture in flask with Formulation V medium"),
    ("PBR 25L Cultivation",          "Seed reactor cultivation at 25L scale — ~72 hours"),
    ("PBR 275L Cultivation",         "Intermediate scale-up cultivation at 275L — ~96 hours"),
    ("PBR 925L Cultivation",         "Large seed reactor cultivation at 925L — ~120 hours"),
    ("PBR 6600L Production",         "Production reactor cultivation at 6600L — ~168 hours (Green→Red phase)"),
    ("Harvesting",                   "Biomass harvesting from production reactor"),
    ("Drying",                       "Industrial drying of harvested biomass — ~24 hours"),
    ("Packing",                      "Final product packing — bulk packaging and labelling"),
]


def setup_operations():
    print("\n── 1.6 Operation Setup ──")

    for op_name, desc in OPERATIONS:
        create_if_not_exists("Operation", op_name, {
            "name": op_name,
            "description": desc,
        })


# ──────────────────────────────────────────────
# 1.7 SUPPLIERS
# ──────────────────────────────────────────────
SUPPLIERS = [
    # (supplier_name, supplier_group, supplier_type, country)
    ("Sisco Research Labs",    "Raw Material",   "Company", "India"),
    ("SRL Chemicals",          "Raw Material",   "Company", "India"),
    ("Sigma Aldrich India",    "Raw Material",   "Company", "India"),
    ("Extraction Partner",     "Services",       "Company", "India"),
]


def setup_suppliers():
    print("\n── 1.7 Supplier Setup ──")

    # Ensure supplier groups exist
    for sg_name in ["Raw Material", "Services"]:
        if not frappe.db.exists("Supplier Group", sg_name):
            try:
                frappe.get_doc({
                    "doctype": "Supplier Group",
                    "supplier_group_name": sg_name,
                }).insert(ignore_permissions=True)
                print(f"  ✅ Supplier Group: {sg_name}")
            except Exception:
                print(f"  ⏭  Supplier Group: {sg_name} (already exists or error)")

    for sup_name, sup_group, sup_type, country in SUPPLIERS:
        create_if_not_exists("Supplier", sup_name, {
            "supplier_name": sup_name,
            "supplier_group": sup_group,
            "supplier_type": sup_type,
            "country": country,
        })


# ──────────────────────────────────────────────
# 1.8 CUSTOMERS
# ──────────────────────────────────────────────
CUSTOMERS = [
    # (customer_name, customer_group, customer_type, territory)
    ("Generic Pharma Customer",     "Commercial",    "Company", "India"),
    ("Generic Nutra Customer",      "Commercial",    "Company", "India"),
]


def setup_customers():
    print("\n── 1.8 Customer Setup ──")

    # Ensure customer groups exist
    for cg_name in ["Commercial"]:
        if not frappe.db.exists("Customer Group", cg_name):
            try:
                frappe.get_doc({
                    "doctype": "Customer Group",
                    "customer_group_name": cg_name,
                }).insert(ignore_permissions=True)
                print(f"  ✅ Customer Group: {cg_name}")
            except Exception:
                print(f"  ⏭  Customer Group: {cg_name} (already exists or error)")

    for cust_name, cust_group, cust_type, territory in CUSTOMERS:
        create_if_not_exists("Customer", cust_name, {
            "customer_name": cust_name,
            "customer_group": cust_group,
            "customer_type": cust_type,
            "territory": territory,
        })


# ──────────────────────────────────────────────
# 1.9 ITEMS — ALL MASTER DATA
# ──────────────────────────────────────────────
# Warehouse keys for default warehouse mapping
WH_KEYS = {
    "chem_rt":       "Chemical Store RT",
    "chem_cold":     "Chemical Store Cold",
    "media_prep":    "Media Preparation Area",
    "fermentation":  "Fermentation Area",
    "harvesting":    "Harvesting Area",
    "drying":        "Drying Area",
    "packed_store":  "Packed Biomass Store",
    "packing_mat":   "Packing Material Store",
    "fg_store":      "Finished Goods Store",
    "dispatch":      "Dispatch Area",
}

# ── Raw Materials: Base Salts ──
RAW_BASE_SALTS = [
    # (item_code, item_name, uom, shelf_life_days, description, wh_key)
    ("CHEM-001", "Calcium Chloride Dihydrate",           "mg", 730, "CaCl2·2H2O — Base salt for green & red culture media", "chem_rt"),
    ("CHEM-002", "Magnesium Sulphate Heptahydrate",      "mg", 730, "MgSO4·7H2O — Base salt for green & red culture media", "chem_rt"),
    ("CHEM-003", "Sodium Chloride",                      "mg", 730, "NaCl — Base salt for green culture medium",            "chem_rt"),
    ("CHEM-022", "Sodium Carbonate",                     "mg", 730, "Na2CO3 — BG-11 red medium component",                  "chem_rt"),
]

# ── Raw Materials: Trace Elements ──
RAW_TRACE_ELEMENTS = [
    ("CHEM-004", "Manganese Chloride Tetrahydrate",      "mg", 730, "MnCl2·4H2O — Trace element for green & A5M stocks",    "chem_rt"),
    ("CHEM-005", "Zinc Chloride",                        "mg", 730, "ZnCl2 — Trace element for green trace stock A1",        "chem_rt"),
    ("CHEM-006", "Cobalt Chloride Hexahydrate",          "mg", 730, "CoCl2·6H2O — Trace element for green trace stock A1",   "chem_rt"),
    ("CHEM-007", "Sodium Molybdate Dihydrate",           "mg", 730, "Na2MoO4·2H2O — Trace element for green trace stock A1", "chem_rt"),
    ("CHEM-015", "Boric Acid",                           "mg", 730, "H3BO3 — Trace element for A5M trace stock (BG-11)",     "chem_rt"),
    ("CHEM-016", "Zinc Sulphate Heptahydrate",           "mg", 730, "ZnSO4·7H2O — Trace element for A5M trace stock (BG-11)","chem_rt"),
    ("CHEM-017", "Cupric Sulphate Pentahydrate",         "mg", 730, "CuSO4·5H2O — Trace element for A5M trace stock (BG-11)","chem_rt"),
    ("CHEM-018", "Ammonium Molybdate",                   "mg", 730, "(NH4)6Mo7O24 — Trace element for A5M trace stock",      "chem_rt"),
]

# ── Raw Materials: Vitamins ──
RAW_VITAMINS = [
    ("CHEM-008", "Vitamin B12 Cyanocobalamin",           "mg", 365, "Vitamin B12 — Light-sensitive, store 2-8°C protected from light",  "chem_cold"),
    ("CHEM-009", "Biotin",                               "mg", 365, "Biotin — Vitamin for green medium stock A2",             "chem_cold"),
    ("CHEM-010", "Thiamine Hydrochloride",               "mg", 365, "Thiamine HCl / Vitamin B1 — For green & BG-11 media",    "chem_cold"),
]

# ── Raw Materials: Nutrients ──
RAW_NUTRIENTS = [
    ("CHEM-011", "Ferric Citrate",                       "mg", 730, "Iron source for green medium stock A3",                  "chem_rt"),
    ("CHEM-012", "Sodium Nitrate",                       "mg", 730, "NaNO3 — Nitrogen source for green medium stock A4",      "chem_rt"),
    ("CHEM-013", "Dipotassium Hydrogen Phosphate",       "mg", 730, "K2HPO4 — Phosphate buffer component for stock A5",       "chem_rt"),
    ("CHEM-014", "Potassium Dihydrogen Phosphate",       "mg", 730, "KH2PO4 — Phosphate buffer component for stock A5",       "chem_rt"),
    ("CHEM-019", "Calcium Nitrate",                      "mg", 730, "Ca(NO3)2 — Nitrogen source for BG-11 stock A7-I",        "chem_rt"),
    ("CHEM-020", "Ferric Ammonium Citrate",              "mg", 730, "FAC — Iron source for BG-11 stock A7-II",                "chem_rt"),
    ("CHEM-021", "EDTA Disodium Salt",                   "mg", 730, "EDTA — Chelating agent for BG-11 stock A7-III",          "chem_rt"),
    ("CHEM-023", "Citric Acid",                          "mg", 730, "Citric acid for BG-11 stock A7-V",                       "chem_rt"),
]

# ── Consumables ──
CONSUMABLES = [
    # (item_code, item_name, item_group, uom, shelf_life_days, description, wh_key, has_batch, has_expiry)
    ("CONS-001", "DI Water",                     "Lab Consumables",      "mL",  0,   "Deionized water for media preparation",    "media_prep",   0, 0),
    ("CONS-002", "Packaging Bags",               "Packaging Materials",  "Nos", 0,   "Packaging bags for biomass packing",       "packing_mat",  0, 0),
    ("CONS-003", "Packaging Labels",             "Packaging Materials",  "Nos", 0,   "Printed labels for product identification","packing_mat",  0, 0),
    ("CONS-004", "General Lab Consumables",      "Lab Consumables",      "Nos", 0,   "Gloves, pipette tips, petri dishes, etc.", "media_prep",   0, 0),
]

# ── Stock Solutions (Manufactured) ──
STOCK_SOLUTIONS = [
    # (item_code, item_name, item_sub_group, uom, shelf_life_days, description, wh_key)
    ("STKSOL-A1",     "Green Trace Element Stock 1L",       "Trace Element Stocks", "mL", 180, "A1 — MnCl2, ZnCl2, CoCl2, Na2MoO4 in DI Water. Store 2-8°C",          "media_prep"),
    ("STKSOL-A2",     "Vitamin Stock 500mL",                "Vitamin Stocks",       "mL", 90,  "A2 — B12, Biotin, Thiamine in DI Water. Filter sterilized. Store 2-8°C dark", "media_prep"),
    ("STKSOL-A3",     "Ferric Citrate Stock 500mL",         "Nutrient Stocks",      "mL", 180, "A3 — Ferric citrate in DI Water",                                     "media_prep"),
    ("STKSOL-A4",     "Sodium Nitrate Stock 100mL",         "Nutrient Stocks",      "mL", 180, "A4 — NaNO3 in DI Water",                                              "media_prep"),
    ("STKSOL-A5",     "Phosphate Buffer Stock 100mL",       "Nutrient Stocks",      "mL", 180, "A5 — K2HPO4 + KH2PO4 in DI Water",                                    "media_prep"),
    ("STKSOL-A6",     "A5M Trace Stock 1L",                 "Trace Element Stocks", "mL", 180, "A6 — Boric acid, MnCl2, ZnSO4, CuSO4, NH4 Molybdate for BG-11",       "media_prep"),
    ("STKSOL-A7-I",   "Calcium Nitrate Stock 100mL",        "Nutrient Stocks",      "mL", 180, "A7-I — Ca(NO3)2 in DI Water for BG-11",                                "media_prep"),
    ("STKSOL-A7-II",  "Ferric Ammonium Citrate Stock 100mL","Nutrient Stocks",      "mL", 180, "A7-II — FAC in DI Water for BG-11",                                    "media_prep"),
    ("STKSOL-A7-III", "EDTA Stock 100mL",                   "Nutrient Stocks",      "mL", 180, "A7-III — EDTA in DI Water for BG-11",                                  "media_prep"),
    ("STKSOL-A7-IV",  "Sodium Carbonate Stock 100mL",       "Nutrient Stocks",      "mL", 180, "A7-IV — Na2CO3 in DI Water for BG-11",                                 "media_prep"),
    ("STKSOL-A7-V",   "Citric Acid Stock 100mL",            "Nutrient Stocks",      "mL", 180, "A7-V — Citric acid in DI Water for BG-11",                             "media_prep"),
    ("STKSOL-A7-VI",  "Vitamin B1 Stock 100mL",             "Vitamin Stocks",       "mL", 90,  "A7-VI — Thiamine in DI Water for BG-11",                               "media_prep"),
]

# ── Culture Media (Manufactured) ──
CULTURE_MEDIA = [
    # (item_code, item_name, uom, shelf_life_days, description, wh_key)
    ("MEDIA-GRN", "Green Medium",       "mL", 90,  "Green culture medium — base salts + stock solutions A1-A5. 75% of Formulation V",   "media_prep"),
    ("MEDIA-RED", "Red Medium BG-11",   "mL", 90,  "Red BG-11 culture medium — base salts + stock solutions A6, A7-I to A7-VI. 25% of Formulation V", "media_prep"),
    ("MEDIA-FV",  "Formulation V",      "mL", 30,  "Final production medium — 75% Green Medium + 25% Red Medium BG-11",                 "media_prep"),
]

# ── Work-In-Progress (Manufactured) ──
WIP_ITEMS = [
    # (item_code, item_name, item_group, uom, description, wh_key)
    ("WIP-FLASK",     "Seed Culture Flask",              "Seed Culture",       "mL",    "Flask-stage seed culture inoculated with Formulation V medium",       "fermentation"),
    ("WIP-PBR25",     "PBR 25L Culture",                 "Seed Reactor Output","Litre", "25L seed reactor output — scaled up from flask",                      "fermentation"),
    ("WIP-PBR275",    "PBR 275L Culture",                "Seed Reactor Output","Litre", "275L intermediate reactor output — QC Gate 1 checkpoint",             "fermentation"),
    ("WIP-PBR925",    "PBR 925L Culture",                "Seed Reactor Output","Litre", "925L large seed reactor output — QC Gate 2 checkpoint",               "fermentation"),
    ("WIP-PBR6600-G", "PBR 6600L Biomass Green Phase",  "Production Biomass", "Litre", "6600L production biomass — green growth phase",                       "fermentation"),
    ("WIP-PBR6600-R", "PBR 6600L Biomass Red Phase",    "Production Biomass", "Litre", "6600L production biomass — red/stress phase for astaxanthin accumulation","fermentation"),
]

# ── Semi-Finished Goods ──
SFG_ITEMS = [
    # (item_code, item_name, uom, shelf_life_days, description, wh_key)
    ("SFG-HARVEST", "Harvested Biomass Wet",    "Kg", 0,   "Wet biomass harvested from production reactor",              "harvesting"),
    ("SFG-DRIED",   "Dried Biomass",            "Kg", 365, "Dried biomass after industrial drying — assay tested",       "drying"),
]

# ── Finished Goods ──
FG_ITEMS = [
    # (item_code, item_name, uom, shelf_life_days, description, wh_key)
    ("FG-PACKED",    "Packed Biomass Bulk",               "Kg", 730, "Packed dried biomass — bulk packaging with batch label and COA",      "packed_store"),
    ("FG-ASTAX",     "Astaxanthin Oleoresin Extract",     "Kg", 730, "Astaxanthin oleoresin — received from extraction partner",            "packed_store"),
    ("FG-ASTAX-CP",  "Astaxanthin Extract Customer Pack", "Kg", 730, "Astaxanthin oleoresin — customer-specific repacked units with COA",   "dispatch"),
]

# ── Services (Non-stock) ──
SERVICE_ITEMS = [
    # (item_code, item_name, description)
    ("SVC-EXTRACTION", "Astaxanthin Extraction Service", "Outsourced supercritical CO2 extraction of astaxanthin from dried biomass"),
]


def setup_items():
    print("\n── 1.9 Item Master Setup ──")

    created_count = 0
    skipped_count = 0

    # ── RAW MATERIALS (batch-managed, expiry-tracked, inspection required) ──
    print("\n  📦 Raw Materials — Base Salts")
    for code, name, uom, shelf_days, desc, wh_key in RAW_BASE_SALTS:
        result = _create_raw_material(code, name, "Base Salts", uom, shelf_days, desc, wh_key)
        created_count += 1 if result else 0
        skipped_count += 0 if result else 1

    print("\n  📦 Raw Materials — Trace Elements")
    for code, name, uom, shelf_days, desc, wh_key in RAW_TRACE_ELEMENTS:
        result = _create_raw_material(code, name, "Trace Elements", uom, shelf_days, desc, wh_key)
        created_count += 1 if result else 0
        skipped_count += 0 if result else 1

    print("\n  📦 Raw Materials — Vitamins")
    for code, name, uom, shelf_days, desc, wh_key in RAW_VITAMINS:
        result = _create_raw_material(code, name, "Vitamins", uom, shelf_days, desc, wh_key)
        created_count += 1 if result else 0
        skipped_count += 0 if result else 1

    print("\n  📦 Raw Materials — Nutrients")
    for code, name, uom, shelf_days, desc, wh_key in RAW_NUTRIENTS:
        result = _create_raw_material(code, name, "Nutrients", uom, shelf_days, desc, wh_key)
        created_count += 1 if result else 0
        skipped_count += 0 if result else 1

    # ── CONSUMABLES (non-batch, non-expiry) ──
    print("\n  🧪 Consumables")
    for code, name, group, uom, shelf_days, desc, wh_key, has_batch, has_expiry in CONSUMABLES:
        result = _create_item(
            code, name, group, uom, desc, wh_key,
            is_stock_item=1, has_batch_no=has_batch, has_expiry_date=has_expiry,
            shelf_life_in_days=shelf_days, valuation_method="FIFO",
            inspection_purchase=0, inspection_delivery=0
        )
        created_count += 1 if result else 0
        skipped_count += 0 if result else 1

    # ── STOCK SOLUTIONS (manufactured, batch-managed) ──
    print("\n  🧫 Stock Solutions (Manufactured)")
    for code, name, group, uom, shelf_days, desc, wh_key in STOCK_SOLUTIONS:
        result = _create_item(
            code, name, group, uom, desc, wh_key,
            is_stock_item=1, has_batch_no=1, has_expiry_date=1,
            shelf_life_in_days=shelf_days, valuation_method="FIFO",
            inspection_purchase=0, inspection_delivery=0
        )
        created_count += 1 if result else 0
        skipped_count += 0 if result else 1

    # ── CULTURE MEDIA (manufactured, batch-managed) ──
    print("\n  🧫 Culture Media (Manufactured)")
    for code, name, uom, shelf_days, desc, wh_key in CULTURE_MEDIA:
        result = _create_item(
            code, name, "Culture Media", uom, desc, wh_key,
            is_stock_item=1, has_batch_no=1, has_expiry_date=1,
            shelf_life_in_days=shelf_days, valuation_method="FIFO",
            inspection_purchase=0, inspection_delivery=0
        )
        created_count += 1 if result else 0
        skipped_count += 0 if result else 1

    # ── WORK-IN-PROGRESS (manufactured, batch-managed, no expiry) ──
    print("\n  🔄 Work In Progress")
    for code, name, group, uom, desc, wh_key in WIP_ITEMS:
        result = _create_item(
            code, name, group, uom, desc, wh_key,
            is_stock_item=1, has_batch_no=1, has_expiry_date=0,
            shelf_life_in_days=0, valuation_method="FIFO",
            inspection_purchase=0, inspection_delivery=0
        )
        created_count += 1 if result else 0
        skipped_count += 0 if result else 1

    # ── SEMI-FINISHED GOODS ──
    print("\n  📋 Semi-Finished Goods")
    for code, name, uom, shelf_days, desc, wh_key in SFG_ITEMS:
        has_expiry = 1 if shelf_days > 0 else 0
        result = _create_item(
            code, name, "Semi-Finished Goods", uom, desc, wh_key,
            is_stock_item=1, has_batch_no=1, has_expiry_date=has_expiry,
            shelf_life_in_days=shelf_days, valuation_method="FIFO",
            inspection_purchase=0, inspection_delivery=0
        )
        created_count += 1 if result else 0
        skipped_count += 0 if result else 1

    # ── FINISHED GOODS (batch-managed, expiry, inspection on delivery) ──
    print("\n  📦 Finished Goods")
    for code, name, uom, shelf_days, desc, wh_key in FG_ITEMS:
        result = _create_item(
            code, name, "Finished Goods", uom, desc, wh_key,
            is_stock_item=1, has_batch_no=1, has_expiry_date=1,
            shelf_life_in_days=shelf_days, valuation_method="FIFO",
            inspection_purchase=0, inspection_delivery=1
        )
        created_count += 1 if result else 0
        skipped_count += 0 if result else 1

    # ── SERVICES (non-stock) ──
    print("\n  🔧 Services")
    for code, name, desc in SERVICE_ITEMS:
        result = _create_item(
            code, name, "Services", "Nos", desc, None,
            is_stock_item=0, has_batch_no=0, has_expiry_date=0,
            shelf_life_in_days=0, valuation_method="",
            inspection_purchase=0, inspection_delivery=0
        )
        created_count += 1 if result else 0
        skipped_count += 0 if result else 1

    print(f"\n  📊 Items Summary: {created_count} created, {skipped_count} skipped")


def _create_raw_material(code, name, group, uom, shelf_days, desc, wh_key):
    """Helper to create a raw material item with standard settings."""
    return _create_item(
        code, name, group, uom, desc, wh_key,
        is_stock_item=1, has_batch_no=1, has_expiry_date=1,
        shelf_life_in_days=shelf_days, valuation_method="FIFO",
        inspection_purchase=1, inspection_delivery=0
    )


def _create_item(code, name, group, uom, desc, wh_key,
                 is_stock_item=1, has_batch_no=1, has_expiry_date=1,
                 shelf_life_in_days=0, valuation_method="FIFO",
                 inspection_purchase=0, inspection_delivery=0):
    """Generic item creation helper."""

    if frappe.db.exists("Item", code):
        print(f"  ⏭  Item: {code} — {name} (already exists)")
        return False

    item_dict = {
        "doctype": "Item",
        "item_code": code,
        "item_name": name,
        "item_group": group,
        "stock_uom": uom,
        "is_stock_item": is_stock_item,
        "has_batch_no": has_batch_no,
        "create_new_batch": 1 if has_batch_no else 0,
        "has_expiry_date": has_expiry_date,
        "description": desc,
        "valuation_method": valuation_method if valuation_method else "",
        "inspection_required_before_purchase": inspection_purchase,
        "inspection_required_before_delivery": inspection_delivery,
    }

    # Shelf life (only if expiry tracking is enabled)
    if has_expiry_date and shelf_life_in_days > 0:
        item_dict["shelf_life_in_days"] = shelf_life_in_days

    # Default warehouse
    if wh_key and is_stock_item:
        warehouse_name = WH_KEYS.get(wh_key, "")
        if warehouse_name:
            item_dict["item_defaults"] = [{
                "company": COMPANY_NAME,
                "default_warehouse": wh(warehouse_name),
            }]

    try:
        doc = frappe.get_doc(item_dict)
        doc.insert(ignore_permissions=True)
        print(f"  ✅ Item: {code} — {name}")
        return True
    except Exception as e:
        print(f"  ❌ Item: {code} — {name} — Error: {str(e)}")
        return False
