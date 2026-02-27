"""
Phase 2: Custom Configuration — Pluviago Biotech
==================================================
Creates:
  2.1  Custom Roles (7)
  2.2  Custom Fields on 6 standard DocTypes (28 fields)
  2.3  Update Item Master with chemical formulas & storage conditions
  2.4  Quality Inspection Templates (8 templates — 1 raw material, 5 in-process, 2 FG)
  2.5  Cost Centers (9 cost centers)

Run via:
    bench --site replica1.local execute pluviago.setup.phase2.execute

Idempotent — safe to run multiple times.
"""

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

# ──────────────────────────────────────────────
# CONSTANTS (must match Phase 1)
# ──────────────────────────────────────────────
COMPANY_NAME = "Pluviago Biotech Pvt. Ltd."
COMPANY_ABBR = "PB"

_abbr = None


def get_abbr():
    global _abbr
    if _abbr is None:
        _abbr = frappe.db.get_value("Company", COMPANY_NAME, "abbr") or COMPANY_ABBR
    return _abbr


def cc(name):
    """Cost center name with company abbreviation."""
    return f"{name} - {get_abbr()}"


# ══════════════════════════════════════════════
# MAIN ENTRY POINT
# ══════════════════════════════════════════════
def execute():
    """Main entry point for Phase 2 setup."""
    print("\n" + "=" * 70)
    print("  PHASE 2: Custom Configuration — Pluviago Biotech Pvt. Ltd.")
    print("=" * 70)

    setup_roles()
    frappe.db.commit()

    setup_custom_fields()
    frappe.db.commit()

    update_item_chemical_data()
    frappe.db.commit()

    setup_qi_templates()
    frappe.db.commit()

    setup_cost_centers()
    frappe.db.commit()

    print("\n" + "=" * 70)
    print("  ✅ PHASE 2 COMPLETE — All custom configuration applied!")
    print("=" * 70 + "\n")


# ══════════════════════════════════════════════
# 2.1  CUSTOM ROLES
# ══════════════════════════════════════════════
ROLES = [
    # (role_name, desk_access)
    ("QA Head",               1),
    ("QC Manager",            1),
    ("Production Manager",    1),
    ("Production Supervisor", 1),
    ("Production Operator",   1),
    ("Store Keeper",          1),
    ("Pluviago Admin",        1),
]


def setup_roles():
    print("\n── 2.1 Custom Roles ──")

    for role_name, desk_access in ROLES:
        if frappe.db.exists("Role", role_name):
            print(f"  ⏭  Role: {role_name} (already exists)")
            continue
        try:
            frappe.get_doc({
                "doctype": "Role",
                "role_name": role_name,
                "desk_access": desk_access,
                "is_custom": 1,
            }).insert(ignore_permissions=True)
            print(f"  ✅ Role: {role_name}")
        except Exception as e:
            print(f"  ❌ Role: {role_name} — {str(e)}")


# ══════════════════════════════════════════════
# 2.2  CUSTOM FIELDS ON STANDARD DOCTYPES
# ══════════════════════════════════════════════
def get_custom_field_definitions():
    """Return dict of {DocType: [field_definitions]} for create_custom_fields()."""

    return {
        # ────────────────────────────────────
        # ITEM — 7 fields (5 data + 2 layout)
        # ────────────────────────────────────
        "Item": [
            {
                "fieldname": "pluviago_section",
                "fieldtype": "Section Break",
                "label": "Pluviago Biotech — Chemical Properties",
                "insert_after": "description",
                "collapsible": 1,
            },
            {
                "fieldname": "chemical_formula",
                "fieldtype": "Data",
                "label": "Chemical / Molecular Formula",
                "insert_after": "pluviago_section",
                "translatable": 0,
            },
            {
                "fieldname": "storage_condition",
                "fieldtype": "Select",
                "label": "Storage Condition",
                "options": "\n2-8°C\nRoom Temperature\nProtected from Light\nCool, Dry, Protected from Light",
                "insert_after": "chemical_formula",
            },
            {
                "fieldname": "is_hazardous",
                "fieldtype": "Check",
                "label": "Is Hazardous Material",
                "insert_after": "storage_condition",
                "default": "0",
            },
            {
                "fieldname": "pluviago_item_col_break",
                "fieldtype": "Column Break",
                "insert_after": "is_hazardous",
            },
            {
                "fieldname": "coa_template",
                "fieldtype": "Link",
                "label": "COA Template",
                "options": "Quality Inspection Template",
                "insert_after": "pluviago_item_col_break",
                "description": "Quality Inspection Template used for COA verification",
            },
            {
                "fieldname": "shelf_life_months",
                "fieldtype": "Int",
                "label": "Shelf Life (Months)",
                "insert_after": "coa_template",
                "description": "Calculated from shelf_life_in_days for quick reference",
            },
        ],

        # ────────────────────────────────────
        # BATCH — 8 fields (6 data + 2 layout)
        # ────────────────────────────────────
        "Batch": [
            {
                "fieldname": "vendor_coa_section",
                "fieldtype": "Section Break",
                "label": "Vendor COA Details",
                "insert_after": "expiry_date",
                "collapsible": 1,
            },
            {
                "fieldname": "vendor_coa_number",
                "fieldtype": "Data",
                "label": "Vendor COA Number",
                "insert_after": "vendor_coa_section",
            },
            {
                "fieldname": "vendor_batch_no",
                "fieldtype": "Data",
                "label": "Vendor Batch No",
                "insert_after": "vendor_coa_number",
            },
            {
                "fieldname": "storage_condition_actual",
                "fieldtype": "Select",
                "label": "Actual Storage Condition",
                "options": "\n2-8°C\nRoom Temperature\nProtected from Light\nCool, Dry, Protected from Light",
                "insert_after": "vendor_batch_no",
            },
            {
                "fieldname": "vendor_coa_col_break",
                "fieldtype": "Column Break",
                "insert_after": "storage_condition_actual",
            },
            {
                "fieldname": "coa_verified",
                "fieldtype": "Check",
                "label": "COA Verified",
                "insert_after": "vendor_coa_col_break",
                "default": "0",
            },
            {
                "fieldname": "coa_verified_by",
                "fieldtype": "Link",
                "label": "COA Verified By",
                "options": "User",
                "insert_after": "coa_verified",
                "depends_on": "eval:doc.coa_verified==1",
                "mandatory_depends_on": "eval:doc.coa_verified==1",
            },
            {
                "fieldname": "coa_verification_date",
                "fieldtype": "Date",
                "label": "COA Verification Date",
                "insert_after": "coa_verified_by",
                "depends_on": "eval:doc.coa_verified==1",
            },
        ],

        # ────────────────────────────────────
        # QUALITY INSPECTION — 7 fields (5 data + 2 layout)
        # ────────────────────────────────────
        "Quality Inspection": [
            {
                "fieldname": "pluviago_qi_section",
                "fieldtype": "Section Break",
                "label": "Production Details",
                "insert_after": "inspected_by",
            },
            {
                "fieldname": "stage",
                "fieldtype": "Select",
                "label": "Production Stage",
                "options": "\nStock Solution Prep\nMedia Preparation\nFlask\nPBR 25L\nPBR 275L\nPBR 925L\nPBR 6600L\nHarvesting\nDrying\nPacking\nExtraction",
                "insert_after": "pluviago_qi_section",
            },
            {
                "fieldname": "phase",
                "fieldtype": "Select",
                "label": "Growth Phase",
                "options": "\nGreen\nRed\nTransition",
                "insert_after": "stage",
                "depends_on": "eval:['PBR 6600L','PBR 925L'].includes(doc.stage)",
            },
            {
                "fieldname": "pluviago_qi_col_break",
                "fieldtype": "Column Break",
                "insert_after": "phase",
            },
            {
                "fieldname": "contamination_status",
                "fieldtype": "Select",
                "label": "Contamination Status",
                "options": "\nClean\nSuspected\nContaminated",
                "insert_after": "pluviago_qi_col_break",
                "depends_on": "eval:['Flask','PBR 25L','PBR 275L','PBR 925L','PBR 6600L'].includes(doc.stage)",
            },
            {
                "fieldname": "decision",
                "fieldtype": "Select",
                "label": "QC Decision",
                "options": "\nProceed\nHold\nHarvest Early\nTerminate\nRestart",
                "insert_after": "contamination_status",
                "description": "Decision based on QC checkpoint result",
            },
            {
                "fieldname": "coa_attachment",
                "fieldtype": "Attach",
                "label": "COA Attachment",
                "insert_after": "decision",
            },
        ],

        # ────────────────────────────────────
        # WORK ORDER — 6 fields (4 data + 2 layout)
        # ────────────────────────────────────
        "Work Order": [
            {
                "fieldname": "pluviago_wo_section",
                "fieldtype": "Section Break",
                "label": "Production Stage & Yield Tracking",
                "insert_after": "actual_end_date",
                "collapsible": 1,
            },
            {
                "fieldname": "production_stage",
                "fieldtype": "Select",
                "label": "Production Stage",
                "options": "\nStock Solution Prep\nMedia Preparation\nFormulation Mixing\nFlask Inoculation\nPBR 25L Cultivation\nPBR 275L Cultivation\nPBR 925L Cultivation\nPBR 6600L Production\nHarvesting\nDrying\nPacking\nRe-Packing",
                "insert_after": "pluviago_wo_section",
            },
            {
                "fieldname": "pluviago_wo_col_break",
                "fieldtype": "Column Break",
                "insert_after": "production_stage",
            },
            {
                "fieldname": "expected_yield",
                "fieldtype": "Float",
                "label": "Expected Yield",
                "insert_after": "pluviago_wo_col_break",
                "precision": "3",
            },
            {
                "fieldname": "actual_yield",
                "fieldtype": "Float",
                "label": "Actual Yield",
                "insert_after": "expected_yield",
                "precision": "3",
            },
            {
                "fieldname": "yield_variance",
                "fieldtype": "Float",
                "label": "Yield Variance (%)",
                "insert_after": "actual_yield",
                "read_only": 1,
                "precision": "2",
                "description": "Auto-calculated: ((Actual - Expected) / Expected) × 100",
            },
        ],

        # ────────────────────────────────────
        # PURCHASE INVOICE — 7 fields (4 data + 3 layout)
        # ────────────────────────────────────
        "Purchase Invoice": [
            {
                "fieldname": "coa_preapproval_section",
                "fieldtype": "Section Break",
                "label": "COA Pre-Approval",
                "insert_after": "is_return",
                "collapsible": 1,
            },
            {
                "fieldname": "coa_preapproval_status",
                "fieldtype": "Select",
                "label": "COA Pre-Approval Status",
                "options": "Pending\nApproved\nRejected",
                "default": "Pending",
                "insert_after": "coa_preapproval_section",
                "in_list_view": 1,
            },
            {
                "fieldname": "vendor_coa_document",
                "fieldtype": "Attach",
                "label": "Vendor COA Document",
                "insert_after": "coa_preapproval_status",
            },
            {
                "fieldname": "coa_pi_col_break",
                "fieldtype": "Column Break",
                "insert_after": "vendor_coa_document",
            },
            {
                "fieldname": "coa_approved_by",
                "fieldtype": "Link",
                "label": "COA Approved By",
                "options": "User",
                "insert_after": "coa_pi_col_break",
                "depends_on": "eval:doc.coa_preapproval_status=='Approved'",
            },
            {
                "fieldname": "coa_approval_date",
                "fieldtype": "Date",
                "label": "COA Approval Date",
                "insert_after": "coa_approved_by",
                "depends_on": "eval:doc.coa_preapproval_status=='Approved'",
            },
        ],

        # ────────────────────────────────────
        # STOCK ENTRY — 7 fields (4 data + 3 layout)
        # ────────────────────────────────────
        "Stock Entry": [
            {
                "fieldname": "outsource_section",
                "fieldtype": "Section Break",
                "label": "Outsource / Subcontracting",
                "insert_after": "is_return",
                "collapsible": 1,
            },
            {
                "fieldname": "is_outsource_send",
                "fieldtype": "Check",
                "label": "Sent for Outsourcing",
                "insert_after": "outsource_section",
                "default": "0",
            },
            {
                "fieldname": "is_outsource_receive",
                "fieldtype": "Check",
                "label": "Received from Outsourcing",
                "insert_after": "is_outsource_send",
                "default": "0",
            },
            {
                "fieldname": "outsource_col_break",
                "fieldtype": "Column Break",
                "insert_after": "is_outsource_receive",
            },
            {
                "fieldname": "outsource_partner",
                "fieldtype": "Link",
                "label": "Outsource Partner",
                "options": "Supplier",
                "insert_after": "outsource_col_break",
                "depends_on": "eval:doc.is_outsource_send==1||doc.is_outsource_receive==1",
            },
            {
                "fieldname": "theoretical_yield",
                "fieldtype": "Float",
                "label": "Theoretical Yield",
                "insert_after": "outsource_partner",
                "depends_on": "eval:doc.is_outsource_receive==1",
                "precision": "3",
            },
        ],
    }


def setup_custom_fields():
    print("\n── 2.2 Custom Fields ──")

    field_defs = get_custom_field_definitions()

    # Count fields
    total_fields = sum(len(fields) for fields in field_defs.values())
    data_fields = sum(
        1 for fields in field_defs.values()
        for f in fields
        if f["fieldtype"] not in ("Section Break", "Column Break")
    )
    print(f"  📋 Creating {data_fields} data fields + layout fields across {len(field_defs)} DocTypes...")

    try:
        create_custom_fields(field_defs, update=True)
        print(f"  ✅ All custom fields created/updated successfully")

        # Print per-doctype summary
        for dt, fields in field_defs.items():
            data_count = sum(1 for f in fields if f["fieldtype"] not in ("Section Break", "Column Break"))
            print(f"     → {dt}: {data_count} fields")
    except Exception as e:
        print(f"  ❌ Custom fields error: {str(e)}")
        # Fallback: create one by one
        print("  🔄 Retrying fields individually...")
        _create_fields_individually(field_defs)


def _create_fields_individually(field_defs):
    """Fallback: create custom fields one at a time."""
    for dt, fields in field_defs.items():
        for field in fields:
            fieldname = field.get("fieldname")
            if frappe.db.exists("Custom Field", {"dt": dt, "fieldname": fieldname}):
                continue
            try:
                cf = frappe.get_doc({
                    "doctype": "Custom Field",
                    "dt": dt,
                    **field,
                })
                cf.insert(ignore_permissions=True)
                print(f"     ✅ {dt}.{fieldname}")
            except Exception as e:
                print(f"     ❌ {dt}.{fieldname} — {str(e)}")


# ══════════════════════════════════════════════
# 2.3  UPDATE ITEM MASTER — Chemical Formulas & Storage
# ══════════════════════════════════════════════
CHEMICAL_DATA = {
    # item_code: (chemical_formula, storage_condition, shelf_life_months, is_hazardous)
    "CHEM-001": ("CaCl₂·2H₂O",              "Cool, Dry, Protected from Light", 24, 0),
    "CHEM-002": ("MgSO₄·7H₂O",              "Cool, Dry, Protected from Light", 24, 0),
    "CHEM-003": ("NaCl",                      "Cool, Dry, Protected from Light", 24, 0),
    "CHEM-004": ("MnCl₂·4H₂O",              "Cool, Dry, Protected from Light", 24, 0),
    "CHEM-005": ("ZnCl₂",                    "Cool, Dry, Protected from Light", 24, 0),
    "CHEM-006": ("CoCl₂·6H₂O",              "Cool, Dry, Protected from Light", 24, 1),  # Hazardous
    "CHEM-007": ("Na₂MoO₄·2H₂O",            "Cool, Dry, Protected from Light", 24, 0),
    "CHEM-008": ("C₆₃H₈₈CoN₁₄O₁₄P",         "2-8°C",                           12, 0),
    "CHEM-009": ("C₁₀H₁₆N₂O₃S",             "2-8°C",                           12, 0),
    "CHEM-010": ("C₁₂H₁₇N₄OSCl·HCl",        "2-8°C",                           12, 0),
    "CHEM-011": ("C₆H₅FeO₇·H₂O",            "Cool, Dry, Protected from Light", 24, 0),
    "CHEM-012": ("NaNO₃",                    "Cool, Dry, Protected from Light", 24, 0),
    "CHEM-013": ("K₂HPO₄",                   "Cool, Dry, Protected from Light", 24, 0),
    "CHEM-014": ("KH₂PO₄",                   "Cool, Dry, Protected from Light", 24, 0),
    "CHEM-015": ("H₃BO₃",                    "Cool, Dry, Protected from Light", 24, 0),
    "CHEM-016": ("ZnSO₄·7H₂O",              "Cool, Dry, Protected from Light", 24, 0),
    "CHEM-017": ("CuSO₄·5H₂O",              "Cool, Dry, Protected from Light", 24, 1),  # Hazardous
    "CHEM-018": ("(NH₄)₆Mo₇O₂₄·4H₂O",      "Cool, Dry, Protected from Light", 24, 0),
    "CHEM-019": ("Ca(NO₃)₂·4H₂O",           "Cool, Dry, Protected from Light", 24, 0),
    "CHEM-020": ("C₆H₈O₇·xFe³⁺·yNH₃",      "Cool, Dry, Protected from Light", 24, 0),
    "CHEM-021": ("C₁₀H₁₄N₂Na₂O₈·2H₂O",     "Cool, Dry, Protected from Light", 24, 0),
    "CHEM-022": ("Na₂CO₃",                   "Cool, Dry, Protected from Light", 24, 0),
    "CHEM-023": ("C₆H₈O₇",                   "Cool, Dry, Protected from Light", 24, 0),
}


def update_item_chemical_data():
    print("\n── 2.3 Update Item Chemical Data ──")

    updated = 0
    skipped = 0

    for item_code, (formula, storage, shelf_months, hazardous) in CHEMICAL_DATA.items():
        if not frappe.db.exists("Item", item_code):
            print(f"  ⚠️  Item {item_code} not found — skipping")
            skipped += 1
            continue

        try:
            frappe.db.set_value("Item", item_code, {
                "chemical_formula": formula,
                "storage_condition": storage,
                "shelf_life_months": shelf_months,
                "is_hazardous": hazardous,
            }, update_modified=False)
            print(f"  ✅ {item_code}: formula={formula}, storage={storage}")
            updated += 1
        except Exception as e:
            print(f"  ❌ {item_code}: {str(e)}")
            skipped += 1

    print(f"\n  📊 Items updated: {updated}, skipped: {skipped}")


# ══════════════════════════════════════════════
# 2.4  QUALITY INSPECTION TEMPLATES
# ══════════════════════════════════════════════

def _manual(spec, value="Complies"):
    """Shorthand for a manual (visual/text) inspection parameter."""
    return {"specification": spec, "value": value, "min_value": 0, "max_value": 0}


def _numeric(spec, min_val, max_val):
    """Shorthand for a numeric inspection parameter."""
    return {"specification": spec, "value": "", "min_value": min_val, "max_value": max_val}


# ── Template definitions ──

QI_TEMPLATES = [
    # ──────────────────────────────────────
    # 1. RAW MATERIAL — General Incoming QC
    # ──────────────────────────────────────
    {
        "name": "Media Chemicals - Incoming QC",
        "readings": [
            _manual("Appearance (Colour)", "White / Colourless (as per spec)"),
            _manual("Appearance (Form)", "Crystalline powder / Granules"),
            _manual("Solubility", "Clear, no precipitate"),
            _numeric("Assay (%)", 95, 103),
            _numeric("pH", 2.0, 12.0),
            _numeric("Moisture / Loss on Drying (%)", 0, 5.0),
            _numeric("Iron (Fe) (%)", 0, 0.005),
            _numeric("Heavy Metals as Pb (%)", 0, 0.005),
            _numeric("Sulphate SO4 (%)", 0, 0.05),
            _numeric("Chloride Cl (%)", 0, 0.02),
            _manual("COA Verification", "Verified against vendor COA"),
            _manual("Vendor COA Attached", "Yes"),
        ],
    },

    # ──────────────────────────────────────
    # 2. IN-PROCESS — Flask Stage
    # ──────────────────────────────────────
    {
        "name": "Flask Stage - Seed Qualification",
        "readings": [
            _numeric("PAR Light Intensity (umol/m2/s)", 0, 0),
            _numeric("pH", 7.0, 8.5),
            _manual("Microscopy - Cell Morphology", "Normal healthy cells"),
            _manual("Microscopy - Contamination", "Absent"),
            _numeric("Cell Count (cells/mL)", 0, 0),
            _numeric("Optical Density OD", 0, 0),
            _numeric("Cell Size (um)", 0, 0),
            _manual("Automation/Aeration Status", "Running per SOP"),
        ],
    },

    # ──────────────────────────────────────
    # 3. IN-PROCESS — PBR 25L Stage
    # ──────────────────────────────────────
    {
        "name": "PBR 25L - Seed Acceptance",
        "readings": [
            _numeric("PAR Light Intensity (umol/m2/s)", 0, 0),
            _numeric("pH", 7.0, 8.5),
            _manual("Microscopy - Cell Morphology", "Normal healthy cells"),
            _manual("Microscopy - Contamination", "Absent"),
            _numeric("Cell Count (cells/mL)", 0, 0),
            _numeric("Optical Density OD", 0, 0),
            _numeric("Cell Size (um)", 0, 0),
            _numeric("Dry Weight (g/L)", 0, 0),
            _manual("Automation/Aeration Status", "Running per SOP"),
        ],
    },

    # ──────────────────────────────────────
    # 4. IN-PROCESS — PBR 275L (QC Gate 1)
    # ──────────────────────────────────────
    {
        "name": "PBR 275L - Contamination and Growth Check",
        "readings": [
            _numeric("PAR Light Intensity (umol/m2/s)", 0, 0),
            _numeric("pH", 7.0, 8.5),
            _manual("Microscopy - Cell Morphology", "Normal healthy cells"),
            _manual("Microscopy - Contamination Check", "Absent"),
            _numeric("Cell Count (cells/mL)", 0, 0),
            _numeric("Optical Density OD", 0, 0),
            _numeric("Cell Size (um)", 0, 0),
            _numeric("Dry Weight (g/L)", 0, 0),
            _manual("Contamination Decision", "Clean — Proceed to 925L"),
            _numeric("Assay - if stress phase (%)", 0, 0),
        ],
    },

    # ──────────────────────────────────────
    # 5. IN-PROCESS — PBR 925L (QC Gate 2)
    # ──────────────────────────────────────
    {
        "name": "PBR 925L - Seed Release QC",
        "readings": [
            _numeric("PAR Light Intensity (umol/m2/s)", 0, 0),
            _numeric("pH", 7.0, 8.5),
            _manual("Microscopy - Cell Morphology", "Normal healthy cells"),
            _manual("Microscopy - Contamination Check", "Absent"),
            _numeric("Cell Count (cells/mL)", 0, 0),
            _numeric("Optical Density OD", 0, 0),
            _numeric("Cell Size (um)", 0, 0),
            _numeric("Dry Weight (g/L)", 0, 0),
            _manual("Seed Release Decision", "Pass — Scale up to 6600L"),
        ],
    },

    # ──────────────────────────────────────
    # 6. IN-PROCESS — PBR 6600L Production
    # ──────────────────────────────────────
    {
        "name": "PBR 6600L - Production Monitoring",
        "readings": [
            _numeric("PAR Light Intensity - Green Phase (umol/m2/s)", 0, 0),
            _numeric("PAR Light Intensity - Red Phase (umol/m2/s)", 0, 0),
            _numeric("pH", 7.0, 8.5),
            _manual("Microscopy - Cell Morphology", "Normal"),
            _manual("Microscopy - Contamination Check", "Absent"),
            _numeric("Cell Count (cells/mL)", 0, 0),
            _numeric("Optical Density OD", 0, 0),
            _numeric("Cell Size (um)", 0, 0),
            _numeric("Dry Weight (g/L)", 0, 0),
            _numeric("Assay - Astaxanthin (%)", 0, 0),
            _manual("Phase Determination", "Green / Red / Transition"),
            _manual("Harvest Decision", "Continue / Harvest"),
        ],
    },

    # ──────────────────────────────────────
    # 7. FINISHED GOODS — Dried Biomass
    # ──────────────────────────────────────
    {
        "name": "Dried Biomass - Release Testing",
        "readings": [
            _numeric("Dry Weight (g/L)", 0, 0),
            _numeric("Assay - Astaxanthin (%)", 0, 0),
            _numeric("Moisture Content (%)", 0, 0),
            _manual("Appearance", "Dark red-brown powder"),
            _numeric("Total Viable Count TVC (CFU/g)", 0, 0),
            _numeric("Yeast and Mold (CFU/g)", 0, 0),
            _manual("Physical Inspection", "No foreign matter, uniform texture"),
        ],
    },

    # ──────────────────────────────────────
    # 8. FINISHED GOODS — Packing Release
    # ──────────────────────────────────────
    {
        "name": "Packing - Release Verification",
        "readings": [
            _manual("Label Verification", "Correct product name, batch no, dates"),
            _manual("Batch Seal Integrity", "Seal intact, no leakage"),
            _manual("COA Linkage", "COA document attached and matches batch"),
            _numeric("Weight Verification (Kg)", 0, 0),
            _manual("Packaging Material QC", "No defects, clean packaging"),
        ],
    },
]


def setup_qi_templates():
    print("\n── 2.4 Quality Inspection Templates ──")

    created = 0
    skipped = 0

    for template_def in QI_TEMPLATES:
        template_name = template_def["name"]

        if frappe.db.exists("Quality Inspection Template", template_name):
            print(f"  ⏭  QI Template: {template_name} (already exists)")
            skipped += 1
            continue

        try:
            doc = frappe.get_doc({
                "doctype": "Quality Inspection Template",
                "quality_inspection_template_name": template_name,
                "item_quality_inspection_parameter": template_def["readings"],
            })
            doc.insert(ignore_permissions=True)
            param_count = len(template_def["readings"])
            print(f"  ✅ QI Template: {template_name} ({param_count} parameters)")
            created += 1
        except Exception as e:
            print(f"  ❌ QI Template: {template_name} — {str(e)}")
            skipped += 1

    print(f"\n  📊 QI Templates: {created} created, {skipped} skipped")

    # Link raw material items to the general QI template
    _link_items_to_qi_template()


def _link_items_to_qi_template():
    """Link all CHEM-xxx items to the 'Media Chemicals - Incoming QC' template."""
    template_name = "Media Chemicals - Incoming QC"

    if not frappe.db.exists("Quality Inspection Template", template_name):
        print("  ⚠️  Cannot link items — general QI template not found")
        return

    print("\n  🔗 Linking raw material items to QI template...")
    linked = 0

    for item_code in CHEMICAL_DATA.keys():
        if frappe.db.exists("Item", item_code):
            try:
                frappe.db.set_value("Item", item_code, {
                    "coa_template": template_name,
                    "quality_inspection_template": template_name,
                }, update_modified=False)
                linked += 1
            except Exception:
                pass

    print(f"  ✅ Linked {linked} items to '{template_name}'")


# ══════════════════════════════════════════════
# 2.5  COST CENTERS
# ══════════════════════════════════════════════
def get_cost_center_tree():
    """Return cost center hierarchy as (name, parent_name, is_group) tuples."""
    root = COMPANY_NAME

    return [
        # Level 1 — main cost center groups
        ("Production",         root, 1),
        ("Quality Control",    root, 0),
        ("R&D",                root, 0),
        ("Administration",     root, 0),
        ("Sales & Marketing",  root, 0),

        # Level 2 — under Production
        ("Media Preparation",     "Production", 0),
        ("Fermentation",          "Production", 0),
        ("Harvesting & Drying",   "Production", 0),
        ("Packing",               "Production", 0),
    ]


def setup_cost_centers():
    print("\n── 2.5 Cost Centers ──")

    created = 0
    skipped = 0

    for name, parent, is_group in get_cost_center_tree():
        full_name = cc(name)

        if parent == COMPANY_NAME:
            parent_full = cc(COMPANY_NAME)
        else:
            parent_full = cc(parent)

        if frappe.db.exists("Cost Center", full_name):
            print(f"  ⏭  Cost Center: {full_name} (already exists)")
            skipped += 1
            continue

        # Check parent exists
        if not frappe.db.exists("Cost Center", parent_full):
            print(f"  ⚠️  Parent cost center not found: {parent_full}")
            skipped += 1
            continue

        try:
            frappe.get_doc({
                "doctype": "Cost Center",
                "cost_center_name": name,
                "parent_cost_center": parent_full,
                "company": COMPANY_NAME,
                "is_group": is_group,
            }).insert(ignore_permissions=True)
            print(f"  ✅ Cost Center: {full_name}")
            created += 1
        except Exception as e:
            print(f"  ❌ Cost Center: {full_name} — {str(e)}")
            skipped += 1

    print(f"\n  📊 Cost Centers: {created} created, {skipped} skipped")
