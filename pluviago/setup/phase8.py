"""
Phase 8: Preparation Formulas — Pluviago Biotech
==================================================
Creates Preparation Formula records for all stock solutions and media:

  8.1  Stock Solution Formulas (A1 – A6, A7-I – A7-VI)
  8.2  Green Medium Formula   (direct base-salt chemicals)
  8.3  Red Medium Formula     (direct base-salt chemicals)

Source:
  - docs/3. Medium Compounding_Process_Flow (003).docx
  - docs/2.ERP_Item_Master_Chemicals_Pluviago.xlsx
  - docs/PLUVIAGO_BUSINESS_FLOW.md

Run via:
    bench --site replica1.local execute pluviago.setup.phase8.execute

Idempotent — safe to run multiple times.
"""

import frappe


# ──────────────────────────────────────────────────────────────────────────────
# FORMULA DEFINITIONS
# Each entry:
#   formula_name    : unique name for the record
#   applies_to      : "Stock Solution Batch" | "Green Medium Batch" | "Red Medium Batch"
#   solution_type   : A1 / A2 / … / A7-VI  (blank for medium formulas)
#   reference_volume: numeric volume the ingredient quantities are based on
#   reference_volume_uom: "mL" or "Litre"
#   notes           : SOP / sterilization notes shown in the form
#   items           : list of (item_code, material_name, quantity, uom, notes)
# ──────────────────────────────────────────────────────────────────────────────

FORMULAS = [
    # ── A1 — Green Trace Element Stock ──────────────────────────────────────
    {
        "formula_name": "A1 — Green Trace Element Stock",
        "applies_to": "Stock Solution Batch",
        "solution_type": "A1",
        "reference_volume": 1000,
        "reference_volume_uom": "mL",
        "notes": "Sterilize by Autoclaving (121°C, 15 min). Store at 2–8°C. "
                 "Usage: 18 mL per 1 L Green Medium.",
        "items": [
            ("CHEM-004", "Manganese Chloride Tetrahydrate (MnCl₂·4H₂O)", 41,   "mg", ""),
            ("CHEM-005", "Zinc Chloride (ZnCl₂)",                          5,    "mg", ""),
            ("CHEM-006", "Cobalt Chloride Hexahydrate (CoCl₂·6H₂O)",       2,    "mg", ""),
            ("CHEM-007", "Sodium Molybdate Dihydrate (Na₂MoO₄·2H₂O)",      4,    "mg", ""),
        ],
    },

    # ── A2 — Vitamin Stock ───────────────────────────────────────────────────
    {
        "formula_name": "A2 — Vitamin Stock",
        "applies_to": "Stock Solution Batch",
        "solution_type": "A2",
        "reference_volume": 500,
        "reference_volume_uom": "mL",
        "notes": "DO NOT autoclave — vitamins are heat-labile. "
                 "Sterilize by 0.22 µm membrane filtration only. "
                 "Protect from light throughout preparation and storage. "
                 "Store at 2–8°C in amber/foil-wrapped bottles. "
                 "Usage: 2 mL per 1 L Green Medium.",
        "items": [
            ("CHEM-008", "Vitamin B12 (Cyanocobalamin)",    25,  "mg", ""),
            ("CHEM-009", "Biotin",                          100, "mg", "Handle in subdued light"),
            ("CHEM-010", "Thiamine Hydrochloride (Vit B1)", 500, "mg", ""),
        ],
    },

    # ── A3 — Ferric Citrate Stock ────────────────────────────────────────────
    {
        "formula_name": "A3 — Ferric Citrate Stock",
        "applies_to": "Stock Solution Batch",
        "solution_type": "A3",
        "reference_volume": 500,
        "reference_volume_uom": "mL",
        "notes": "Sterilize by Autoclaving (121°C, 15 min). "
                 "Store at RT or 2–8°C. Shelf life: 2 years. "
                 "Usage: 0.94 mL per 1 L Green Medium.",
        "items": [
            ("CHEM-011", "Ferric Citrate", 2350, "mg", "2.35 g dissolved in ~400 mL DI water"),
        ],
    },

    # ── A4 — Sodium Nitrate Stock ────────────────────────────────────────────
    {
        "formula_name": "A4 — Sodium Nitrate Stock",
        "applies_to": "Stock Solution Batch",
        "solution_type": "A4",
        "reference_volume": 100,
        "reference_volume_uom": "mL",
        "notes": "Sterilize by Autoclaving (121°C, 15 min). "
                 "Store at Room Temperature. Shelf life: 3 years. "
                 "Usage: 9.48 mL per 1 L Green Medium.",
        "items": [
            ("CHEM-012", "Sodium Nitrate (NaNO₃)", 24670, "mg", "24.67 g dissolved in ~80 mL DI water"),
        ],
    },

    # ── A5 — Phosphate Buffer Stock ──────────────────────────────────────────
    {
        "formula_name": "A5 — Phosphate Buffer Stock",
        "applies_to": "Stock Solution Batch",
        "solution_type": "A5",
        "reference_volume": 100,
        "reference_volume_uom": "mL",
        "notes": "Sterilize by Autoclaving (121°C, 15 min). "
                 "Store at Room Temperature. Shelf life: 3 years. "
                 "Usage: 4.4 mL per 1 L Green Medium.",
        "items": [
            ("CHEM-013", "Dipotassium Hydrogen Phosphate (K₂HPO₄)",  4535, "mg", "4.535 g"),
            ("CHEM-014", "Potassium Dihydrogen Phosphate (KH₂PO₄)",  3580, "mg", "3.58 g"),
        ],
    },

    # ── A6 — A5M Red Trace Element Stock ────────────────────────────────────
    {
        "formula_name": "A6 — A5M Red Trace Element Stock",
        "applies_to": "Stock Solution Batch",
        "solution_type": "A6",
        "reference_volume": 1000,
        "reference_volume_uom": "mL",
        "notes": "Sterilize by Autoclaving (121°C, 15 min). "
                 "Store at 2–8°C. Shelf life: 1 year. "
                 "Usage: 1 mL per 1 L Red Medium (BG-11).",
        "items": [
            ("CHEM-015", "Boric Acid (H₃BO₃)",                          2.85, "mg", ""),
            ("CHEM-004", "Manganese Chloride Tetrahydrate (MnCl₂·4H₂O)", 1.81, "mg", ""),
            ("CHEM-016", "Zinc Sulphate Heptahydrate (ZnSO₄·7H₂O)",      0.2,  "mg", ""),
            ("CHEM-017", "Cupric Sulphate Pentahydrate (CuSO₄·5H₂O)",    79,   "mg", ""),
            ("CHEM-018", "Ammonium Molybdate",                            15,   "mg", ""),
        ],
    },

    # ── A7-I — Calcium Nitrate Stock ────────────────────────────────────────
    {
        "formula_name": "A7-I — Calcium Nitrate Stock",
        "applies_to": "Stock Solution Batch",
        "solution_type": "A7-I",
        "reference_volume": 100,
        "reference_volume_uom": "mL",
        "notes": "Sterilize by Autoclaving (121°C, 15 min). Store at RT. "
                 "⚠ Add to Red Medium LAST — calcium precipitates with sulphates/phosphates. "
                 "Usage: 1 mL per 1 L Red Medium.",
        "items": [
            ("CHEM-019", "Calcium Nitrate (Ca(NO₃)₂·4H₂O)", 1000, "mg", "1 g per 100 mL"),
        ],
    },

    # ── A7-II — Ferric Ammonium Citrate Stock ───────────────────────────────
    {
        "formula_name": "A7-II — Ferric Ammonium Citrate Stock",
        "applies_to": "Stock Solution Batch",
        "solution_type": "A7-II",
        "reference_volume": 100,
        "reference_volume_uom": "mL",
        "notes": "Sterilize by Autoclaving (121°C, 15 min). Store at 2–8°C. "
                 "Usage: 1 mL per 1 L Red Medium.",
        "items": [
            ("CHEM-020", "Ferric Ammonium Citrate (FAC)", 600, "mg", ""),
        ],
    },

    # ── A7-III — EDTA Stock ─────────────────────────────────────────────────
    {
        "formula_name": "A7-III — EDTA Stock",
        "applies_to": "Stock Solution Batch",
        "solution_type": "A7-III",
        "reference_volume": 100,
        "reference_volume_uom": "mL",
        "notes": "Sterilize by Autoclaving (121°C, 15 min). Store at RT. "
                 "Usage: 1 mL per 1 L Red Medium.",
        "items": [
            ("CHEM-021", "EDTA Disodium", 1000, "mg", "1 g per 100 mL"),
        ],
    },

    # ── A7-IV — Sodium Carbonate Stock ──────────────────────────────────────
    {
        "formula_name": "A7-IV — Sodium Carbonate Stock",
        "applies_to": "Stock Solution Batch",
        "solution_type": "A7-IV",
        "reference_volume": 100,
        "reference_volume_uom": "mL",
        "notes": "Sterilize by Autoclaving (121°C, 15 min). Store at RT. "
                 "Usage: 1 mL per 1 L Red Medium.",
        "items": [
            ("CHEM-022", "Sodium Carbonate (Na₂CO₃)", 1000, "mg", "1 g per 100 mL"),
        ],
    },

    # ── A7-V — Citric Acid Stock ─────────────────────────────────────────────
    {
        "formula_name": "A7-V — Citric Acid Stock",
        "applies_to": "Stock Solution Batch",
        "solution_type": "A7-V",
        "reference_volume": 100,
        "reference_volume_uom": "mL",
        "notes": "Sterilize by Autoclaving (121°C, 15 min). Store at RT. "
                 "Usage: 1 mL per 1 L Red Medium.",
        "items": [
            ("CHEM-023", "Citric Acid", 600, "mg", ""),
        ],
    },

    # ── A7-VI — Vitamin B1 Stock ─────────────────────────────────────────────
    {
        "formula_name": "A7-VI — Vitamin B1 Stock",
        "applies_to": "Stock Solution Batch",
        "solution_type": "A7-VI",
        "reference_volume": 100,
        "reference_volume_uom": "mL",
        "notes": "DO NOT autoclave — heat-labile vitamin. "
                 "Sterilize by 0.22 µm membrane filtration only. "
                 "Protect from light. Store at 2–8°C. "
                 "Usage: 1 mL per 1 L Red Medium.",
        "items": [
            ("CHEM-010", "Thiamine Hydrochloride (Vitamin B1)", 100, "mg", ""),
        ],
    },

    # ── Green Medium — Direct Base Salts ────────────────────────────────────
    {
        "formula_name": "Green Medium — Direct Base Salts",
        "applies_to": "Green Medium Batch",
        "solution_type": "",
        "reference_volume": 1000,
        "reference_volume_uom": "mL",
        "notes": "Base salt quantities for 1 L Green Medium. "
                 "Dissolve in ~800 mL DI water, check clarity (QC1), autoclave. "
                 "After cooling add stock solutions A1 (18 mL), A2 (2 mL), "
                 "A3 (0.94 mL), A4 (9.48 mL), A5 (4.4 mL) aseptically. "
                 "Top up to 1.000 L. Check pH and clarity (QC2).",
        "items": [
            ("CHEM-001", "Calcium Chloride (CaCl₂)",              75,  "mg", ""),
            ("CHEM-002", "Magnesium Sulphate Heptahydrate (MgSO₄·7H₂O)", 225, "mg", ""),
            ("CHEM-003", "Sodium Chloride (NaCl)",                 75,  "mg", ""),
        ],
    },

    # ── Red Medium — Direct Base Salts ──────────────────────────────────────
    {
        "formula_name": "Red Medium — Direct Base Salts",
        "applies_to": "Red Medium Batch",
        "solution_type": "",
        "reference_volume": 1000,
        "reference_volume_uom": "mL",
        "notes": "Base salt quantities for 1 L Red Medium (BG-11). "
                 "Dissolve in ~800 mL DI water, check clarity (QC3), sterilize. "
                 "Preferred: filter-sterilize entire final medium (0.22 µm). "
                 "After cooling add stocks A6 (1 mL), A7-II (1 mL), A7-III (1 mL), "
                 "A7-IV (1 mL), A7-V (1 mL), A7-VI (1 mL), A7-I (1 mL) aseptically. "
                 "⚠ A7-I (Calcium Nitrate) must be added LAST. "
                 "Top up to 1.000 L. Check pH and clarity (QC4).",
        "items": [
            ("CHEM-001", "Calcium Chloride (CaCl₂)",              100, "mg", ""),
            ("CHEM-002", "Magnesium Sulphate Heptahydrate (MgSO₄·7H₂O)", 200, "mg", ""),
        ],
    },
]


# ──────────────────────────────────────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────────────────────────────────────

def _item_exists(item_code):
    return frappe.db.exists("Item", item_code)


def _uom_exists(uom):
    return frappe.db.exists("UOM", uom)


def create_formula(f):
    name = f["formula_name"]

    if frappe.db.exists("Preparation Formula", name):
        print(f"  ⏭  {name} (already exists)")
        return

    # Validate items
    items = []
    for item_code, material_name, qty, uom, notes in f["items"]:
        if not _item_exists(item_code):
            print(f"  ⚠  {name}: item {item_code} not found — row skipped")
            continue
        if not _uom_exists(uom):
            print(f"  ⚠  {name}: UOM '{uom}' not found — row skipped")
            continue
        items.append({
            "doctype": "Formula Item",
            "item_code": item_code,
            "material_name": material_name,
            "quantity": qty,
            "uom": uom,
            "notes": notes,
        })

    doc = frappe.get_doc({
        "doctype": "Preparation Formula",
        "formula_name": name,
        "applies_to": f["applies_to"],
        "solution_type": f.get("solution_type", ""),
        "reference_volume": f["reference_volume"],
        "reference_volume_uom": f["reference_volume_uom"],
        "notes": f.get("notes", ""),
        "items": items,
    })
    doc.insert(ignore_permissions=True)
    print(f"  ✅  {name}  ({len(items)} ingredients)")


# ──────────────────────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────────────────────

def execute():
    print("\n" + "=" * 70)
    print("  PHASE 8: Preparation Formulas — Pluviago Biotech")
    print("=" * 70)

    print("\n── 8.1  Stock Solution Formulas (A1 – A7-VI) ──")
    for f in FORMULAS:
        if f["applies_to"] == "Stock Solution Batch":
            create_formula(f)

    frappe.db.commit()

    print("\n── 8.2  Medium Formulas (Green + Red) ──")
    for f in FORMULAS:
        if f["applies_to"] in ("Green Medium Batch", "Red Medium Batch"):
            create_formula(f)

    frappe.db.commit()

    total = len(FORMULAS)
    print(f"\n  Done — {total} formulas processed.")
    print("=" * 70)
