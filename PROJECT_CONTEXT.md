# Pluviago Biotech ERP — Project Context & SRS Reference

> This file is the single source of truth for any developer or LLM working on this
> project. It captures the business, the full production process, all client
> requirements from the SRS and supporting documents, and the current
> implementation status. Read this before touching any code.

---

## Table of Contents

1. [Company Overview](#1-company-overview)
2. [Technology Stack](#2-technology-stack)
3. [End-to-End Production Flow](#3-end-to-end-production-flow)
4. [Module Requirements](#4-module-requirements)
5. [Custom DocTypes — Full Field Reference](#5-custom-doctypes--full-field-reference)
6. [Stock Solution Formulations](#6-stock-solution-formulations)
7. [Medium Preparation Recipes](#7-medium-preparation-recipes)
8. [QC Process Design](#8-qc-process-design)
9. [User Roles & Permissions](#9-user-roles--permissions)
10. [Reports Required](#10-reports-required)
11. [Integration Requirements](#11-integration-requirements)
12. [Business Rules & Constraints](#12-business-rules--constraints)
13. [Chemical Master Reference](#13-chemical-master-reference)
14. [Implementation Status](#14-implementation-status)
15. [Key Design Decisions](#15-key-design-decisions)
16. [Known Issues & Technical Notes](#16-known-issues--technical-notes)

---

## 1. Company Overview

**Company:** Pluviago Biotech Pvt. Ltd.  
**Sister Company (ERP owner):** Softland India Ltd (SIL) — two-company ERPNext setup  
**Site URL:** replica1.local  
**ERPNext Version:** v15  
**Custom App:** `pluviago` (GitHub: abhaysajeev/pluviago)

### What They Do

Pluviago Biotech cultivates the microalgae *Haematococcus pluvialis* to produce
**astaxanthin** — a high-value antioxidant. End products are astaxanthin oil and
tablets. The production process is biological/pharma in nature, not discrete
manufacturing.

### Production Characteristics

- All operations are **batch-wise** — every stage is traced to a specific batch number
- Production cycle is **fixed at one month** regardless of output volume
- Extraction is **outsourced** to a third-party partner
- The company is building toward **GMP compliance**
- Full chain-of-custody traceability is a core requirement: raw chemical → final product

---

## 2. Technology Stack

| Layer | Technology |
|-------|-----------|
| ERP Backend | Frappe Framework v15 + ERPNext v15 |
| Custom App | `pluviago` — Python/Frappe DocTypes |
| Database | MariaDB |
| Frontend | Frappe UI (standard forms) + custom JS |
| Accounting Integration | Zoho Books (planned) |
| Mobile App | Android (planned — separate scope) |
| Server | Ubuntu, bench deployment |

### Why Custom DocTypes Instead of ERPNext BOM/Work Order

ERPNext's manufacturing module (BOM + Work Order) was evaluated and rejected
because:
- It has no concept of biological lifecycle (QC Pending → Wasted states)
- It cannot model multi-stage bioreactor genealogy (Flask → 25L → 275L → 925L → 6600L)
- It has no pharma-grade audit trail for chemical consumption
- BOM assumes discrete manufacturing, not continuous biological growth

All production tracking uses custom Frappe DocTypes purpose-built for this workflow.

---

## 3. End-to-End Production Flow

```
Stage 0:   Vendor Qualification
               ↓
           Purchase Order
               ↓
           Purchase Receipt (ERPNext)
               ↓
           COA Verification (Chemical COA)
               ↓
           Raw Material Batch (inventory registration)
               ↓
Stage 0A:  Stock Solution Preparation (A1–A7, A5M)
               ↓
Stage 0B:  Green Medium Preparation   Red Medium Preparation
               ↓                              ↓
Stage 0C:      Final Medium (75% Green + 25% Red)
               ↓
Stage 1:   Flask Culture (Seed Qualification)
               ↓  QC PASS / FAIL gate
Stage 2:   25 L PBR
               ↓  QC PASS / FAIL gate
Stage 3:   275 L PBR
               ↓  Contamination check → if YES: harvest early
Stage 4:   925 L PBR
               ↓  Contamination check → if YES: harvest early
Stage 5:   6600 L Production Reactor (Green Phase → Red Phase)
               ↓  Target dry weight achieved
Stage 6:   Harvest
               ↓
Stage 7:   Drying + QC Assay
               ↓
Stage 8:   Packing + Label Verification
               ↓
           Dispatch to External Extraction Partner
               ↓
           Receive Extract + QC Incoming (Assay + COA)
               ↓
           Repacking → Final Dispatch
```

### Stage Details

| Stage | Vessel | Volume | Key Output |
|-------|--------|--------|-----------|
| Flask | Lab flask | ~250 mL | Seed culture, QC qualified |
| 25L PBR | Photobioreactor | 25 L | Scaled inoculum |
| 275L PBR | Photobioreactor | 275 L | Scaled culture |
| 925L PBR | Photobioreactor | 925 L | Scaled culture |
| 6600L PBR | Production reactor | 6600 L | Biomass (green then red phase) |
| Harvest | Centrifuge/filter | — | Wet biomass |
| Drying | Dryer | — | Dry biomass (kg) |
| Extraction | External partner | — | Astaxanthin oil/extract |

### Strain Generation Numbering

```
Flask     = Generation 1
25L PBR   = Generation 2
275L PBR  = Generation 3
925L PBR  = Generation 4
6600L PBR = Generation 5
```

Cannot skip generations. Linear progression enforced.

---

## 4. Module Requirements

### 4.1 Modules in Scope

| # | Module | Status |
|---|--------|--------|
| 1 | Initial Setup & Configuration | Done |
| 2 | HRMS & Workforce Management | Planned |
| 3 | Inventory Management | Partial (RMB done) |
| 4 | Procurement & Vendor Approval | Done |
| 5 | Purchase Invoice Pre-Approval & QC Verification | Done (manual COA flow) |
| 6 | Asset Management | Planned |
| 7 | Production Planning, Recipe Management & Outsource | In Progress |
| 8 | Sampling | Planned |
| 9 | Engineering Management | Planned |
| 10 | Finished Product & Packing | Planned |
| 11 | Sales Management | Planned |
| 12 | Accounting & Zoho Books Integration | Planned |
| 13 | Reporting & Dashboards | Partial |

### 4.2 Procurement & Vendor Approval Flow (Detailed)

```
Material Requirement Generated
    ↓
Approved Vendor Selected (check Approved Vendor List)
    ↓
Purchase Order Created (soft warning if vendor not in AVL)
    ↓
Material Delivered
    ↓
Material Receipt Note / Purchase Receipt (ERPNext)
    ↓
Vendor submits COA (physical/PDF)
    ↓
QA reviews COA manually against internal spec
    ↓
Decision:
    Approved → Chemical COA submitted → Raw Material Batch created
    Rejected → Return to vendor
```

**Key rule:** GRN (Purchase Receipt) is allowed immediately — COA review happens
in parallel via Chemical COA doctype. The COA Verified checkbox on RMB is the
gate before the material can be used in production.

---

## 5. Custom DocTypes — Full Field Reference

### 5.1 Approved Vendor (AVL)

**Purpose:** Vendor qualification record — maps a specific supplier to a specific
chemical item they are approved to supply.

**Naming Series:** `AVL-.YYYY.-.####`

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| supplier | Link:Supplier | Yes | ERPNext supplier master |
| item_code | Link:Item | Yes | Chemical item |
| material_name | Data | No | Auto-fetched from item |
| approval_status | Select | Yes | Approved / Pending / Suspended |
| approval_date | Date | Yes | Date of formal approval |
| valid_upto | Date | Yes | Expiry of this qualification |
| approved_by | Link:User | No | QA Head |

**Validation logic:** `valid_upto` must be in the future to be considered active.
The PO hook checks for Approved status and valid date range.

---

### 5.2 Chemical COA

**Purpose:** Records the QC Manager's manual review of the vendor's Certificate
of Analysis for a received chemical batch.

**Naming Series:** `COA-.YYYY.-.####`

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| supplier | Link:Supplier | Yes | Who issued the COA |
| item_code | Link:Item | No | Chemical assessed |
| material_name | Data | No | Auto-fetched |
| supplier_batch_no | Data | No | Vendor's batch number on label |
| coa_date | Date | No | Date printed on vendor COA |
| expiry_date | Date | No | Expiry on vendor COA/label |
| raw_material_batch | Link:Raw Material Batch | No | Link to RMB (optional) |
| overall_result | Select | Yes (to submit) | Pass / Fail |
| verified_by | Link:User | Yes (to submit) | QC Manager |
| verification_date | Date | Yes (to submit) | Date of review |
| test_parameters | Child table:COA Test Parameter | No | Parameter rows |

**Child table: COA Test Parameter**

| Field | Type | Notes |
|-------|------|-------|
| parameter_name | Data | e.g., Assay, pH, Appearance |
| specification | Data | Expected range (from QC Spec) |
| result_value | Data | Vendor's reported value |
| result | Select | Pass / Fail |

**Client-side actions:**
- `raw_material_batch` onchange: auto-fetches material_name, item_code, supplier,
  supplier_batch_no, expiry_date from linked RMB
- "Load Spec Template" button (Actions menu): calls `get_spec_parameters(item_code)`
  which queries QC Parameter Spec and pre-fills parameter rows

**Submit gate (before_submit):**
- overall_result must be filled
- verified_by must be filled
- verification_date must be filled
- On submit: sets status = "Verified", syncs `coa_verified = 1` to linked RMB

---

### 5.3 Raw Material Batch (RMB)

**Purpose:** Central pharma-grade inventory record for each received chemical
batch. Tracks identity, stock quantities, QC decision, COA verification, storage,
and links to Purchase Receipt.

**Naming Series:** `RMB-CHEM-.YYYY.-.####`

**Status lifecycle:** Draft → Submitted (Approved/Rejected/Received) → Exhausted

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| material_name | Data | Yes | Full chemical name |
| item_code | Link:Item | No | ERPNext item master |
| supplier | Link:Supplier | Yes | Source supplier |
| supplier_batch_no | Data | No | Vendor's batch number |
| mfg_date | Date | No | Manufacture date |
| expiry_date | Date | No | Expiry date — must be after mfg_date |
| batch_number | Data | Read-only | Auto-set to doc.name in before_save |
| received_date | Date | No | Physical receipt date |
| received_qty | Float | Yes | Starting stock quantity |
| received_qty_uom | Link:UOM | Yes | Unit of measure |
| remaining_qty | Float | Read-only | Remaining stock (auto-managed) |
| consumed_qty | Float | Read-only | Total consumed (auto-managed) |
| storage_condition | Select | No | Room Temperature / 2-8C / -20C / 4C |
| warehouse | Link:Warehouse | No | Physical storage location |
| qc_status | Select | Yes (to submit) | Approved / Rejected / Pending |
| qc_checked_by | Link:User | No | QC Manager |
| qc_date | Date | No | Date of QC decision |
| coa_verified | Check | Yes (to submit) | Must be ticked before submit |
| coa_verified_by | Link:User | No | Who verified COA |
| purchase_receipt | Link:Purchase Receipt | No | ERPNext PR link |
| status | Select | Read-only | Received / Approved / Rejected / Exhausted |

**Submit gate (before_submit):**
- qc_status must be "Approved"
- coa_verified must be checked
- expiry_date must be after mfg_date (if both set)
- On submit: `db_set("remaining_qty", received_qty)`, `db_set("consumed_qty", 0)`
- Expiry warning (not block) if expiry_date < today

**Cancel guard (on_cancel):**
- Blocked if `consumed_qty > 0`

**`recalculate_remaining_qty()`:**
- Recomputes consumed_qty and remaining_qty from Stock Consumption Log
- Used for recovery if incremental updates drift
- Also exposed as `@frappe.whitelist()` function `recalculate_stock(rmb_name)`
- Client-side "Recalculate Stock" button in Actions menu on submitted docs

---

### 5.4 QC Parameter Spec

**Purpose:** Master data defining acceptable parameter ranges for chemicals or
batches. Used by Chemical COA's "Load Spec Template" to pre-fill test rows.

**Naming Series:** `QPS-.YYYY.-.####`

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| parameter_name | Data | Yes | e.g., Assay, pH, Appearance |
| applicable_doctype | Select | Yes | Raw Material Batch / Stock Solution Batch / etc. |
| item_code | Link:Item | No | Chemical-specific spec |
| parameter_type | Select | No | Assay / pH / Appearance / Clarity etc. |
| min_value | Float | No | Lower bound |
| max_value | Float | No | Upper bound |
| unit | Data | No | %, pH units, etc. |
| expected_text | Data | No | For text-type parameters (e.g., "White crystalline powder") |
| is_critical | Check | No | Flags critical parameters |

---

### 5.5 Stock Consumption Log (SCL)

**Purpose:** Audit trail entry for every chemical consumption event. This is the
source of truth for remaining_qty on RMB — never trust RMB fields alone; always
reconcile against SCL.

**Naming Series:** `SCL-.YYYY.-.####`

| Field | Type | Notes |
|-------|------|-------|
| raw_material_batch | Link:Raw Material Batch | Which RMB was consumed |
| action | Select | Consumed / Written Off (Loss) / Reversed |
| qty_change | Float | Amount (positive number; sign derived from action) |
| source_doctype | Data | DocType of the consuming document |
| source_document | Dynamic Link | Link to the consuming document |
| consumed_by | Link:User | Who performed consumption |
| consumption_date | Date | When consumed |
| notes | Small Text | Optional notes |

**`recalculate_remaining_qty()` SQL logic:**
```sql
SELECT
    SUM(CASE WHEN action IN ('Consumed','Written Off (Loss)')
        THEN ABS(qty_change) ELSE 0 END) as total_consumed,
    SUM(CASE WHEN action = 'Reversed'
        THEN ABS(qty_change) ELSE 0 END) as total_reversed
FROM `tabStock Consumption Log`
WHERE raw_material_batch = %s
```
`net_consumed = total_consumed - total_reversed`
`remaining = received_qty - net_consumed`

---

### 5.6 Stock Solution Batch (SSB)

**Purpose:** Records preparation of concentrated stock solutions (A1–A7, A5M).
These are intermediate formulations — prepared once in bulk from raw chemicals,
stored, then drawn from when preparing culture media.

**Naming Series:** `SSB-.YYYY.-.####`

*(Implementation in progress — see Section 14)*

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| solution_type | Select | Yes | A1 / A2 / A3 / A4 / A5 / A5M / A6 / A7-I through A7-VI |
| solution_name | Data | No | Descriptive name |
| batch_number | Data | Read-only | Auto-set to doc.name |
| prepared_date | Date | Yes | Preparation date |
| prepared_by | Link:User | Yes | Lab technician |
| target_volume | Float | Yes | Intended volume (mL) |
| actual_volume | Float | No | Final volume produced |
| volume_uom | Link:UOM | Yes | mL / L |
| remaining_volume | Float | Read-only | Volume remaining |
| used_volume | Float | Read-only | Volume consumed |
| sterilization_method | Select | Yes | Autoclave / Filter (0.22µm) / None |
| sterilization_date | Date | No | When sterilized |
| storage_condition | Select | Yes | RT / 2-8C / -20C |
| storage_location | Data | No | Lab fridge, shelf |
| expiry_date | Date | Yes | Calculated or entered |
| qc_ph_target | Float | No | Expected pH |
| qc_ph_actual | Float | No | Measured pH |
| qc_clarity | Select | No | Clear / Cloudy / Precipitate |
| qc_sterile_filtered | Check | No | Was 0.22µm filter used |
| qc_status | Select | Yes | Approved / Rejected / Pending |
| qc_checked_by | Link:User | No | QC reviewer |
| qc_date | Date | No | Date of QC |
| status | Select | Read-only | Draft / Available / Partially Used / Exhausted / Rejected |
| ingredients | Child table:SSB Ingredient | Yes | Chemicals consumed |
| notes | Small Text | No | Preparation notes |

**Child table: SSB Ingredient**

| Field | Type | Notes |
|-------|------|-------|
| item_code | Link:Item | Chemical used |
| material_name | Data | Auto-fetched |
| raw_material_batch | Link:Raw Material Batch | Source RMB — required for traceability |
| qty_used | Float | Amount weighed out |
| uom | Link:UOM | Unit |

**Submit gate (planned):**
- qc_status must be "Approved"
- actual_volume must be filled
- sterilization_method must be filled
- On submit: remaining_volume = actual_volume, used_volume = 0
- Triggers SCL entries for each ingredient row (deducts from linked RMBs)

---

### 5.7 Green Medium Batch

**Purpose:** Records preparation of Green Medium — base salts dissolved in DI
water, sterilized, then stock solutions A1–A5 added aseptically.

**Naming Series:** `GMB-.YYYY.-.####`

*(DocType exists, full implementation pending)*

| Field | Type | Notes |
|-------|------|-------|
| batch_number | Data | Read-only, auto-set |
| prepared_date | Date | Preparation date |
| prepared_by | Link:User | Lab tech |
| target_volume | Float | e.g., 1000 mL |
| actual_volume | Float | Final volume |
| remaining_volume | Float | Read-only |
| status | Select | Draft / Available / Partially Used / Exhausted / Rejected |
| **Base Salts (direct addition)** | | |
| cacl2_qty | Float | CaCl₂ in mg |
| mgso4_qty | Float | MgSO₄·7H₂O in mg |
| nacl_qty | Float | NaCl in mg |
| di_water_initial | Float | ~800 mL initial water |
| **Stock Solutions** | | |
| a1_batch | Link:Stock Solution Batch | Trace stock batch used |
| a1_volume | Float | 18 mL per 1L |
| a2_batch | Link:Stock Solution Batch | Vitamin stock |
| a2_volume | Float | 2 mL per 1L |
| a3_batch | Link:Stock Solution Batch | Ferric citrate |
| a3_volume | Float | 0.94 mL per 1L |
| a4_batch | Link:Stock Solution Batch | NaNO₃ stock |
| a4_volume | Float | 9.48 mL per 1L |
| a5_batch | Link:Stock Solution Batch | Phosphate buffer |
| a5_volume | Float | 4.4 mL per 1L |
| **QC** | | |
| qc_checkpoint1_clarity | Select | Pass / Fail (pre-sterilization) |
| qc_checkpoint2_ph | Float | Final pH |
| qc_checkpoint2_clarity | Select | Pass / Fail (final) |
| qc_checkpoint2_sterility | Select | Pass / Fail / By Process |
| qc_status | Select | Approved / Rejected / Pending |
| **Sterilization** | | |
| sterilization_method | Select | Autoclave / Filter |
| sterilization_date | Date | |

---

### 5.8 Red Medium Batch

**Purpose:** Records preparation of Red Medium (BG-11 Red) — base salts + seven
A7 sub-stocks added aseptically. A7 calcium is added last (kept separate to
prevent precipitation).

**Naming Series:** `RMD-.YYYY.-.####`

*(DocType exists, full implementation pending)*

Similar structure to Green Medium Batch but with A6 and A7-I through A7-VI as
stock solution links instead of A1–A5.

---

### 5.9 Final Medium Batch

**Purpose:** Aseptic combination of Green + Red medium in 75:25 ratio. System
auto-calculates volumes from target final volume.

**Naming Series:** `FMB-.YYYY.-.####`

| Field | Type | Notes |
|-------|------|-------|
| target_final_volume | Float | Required volume (mL or L) |
| green_medium_batch | Link:Green Medium Batch | Source green batch |
| green_volume_used | Float | Auto-calc: 0.75 × target_final_volume |
| red_medium_batch | Link:Red Medium Batch | Source red batch |
| red_volume_used | Float | Auto-calc: 0.25 × target_final_volume |
| actual_final_volume | Float | |
| remaining_volume | Float | Read-only |
| qc_checkpoint5_ph | Float | Final pH measurement |
| qc_checkpoint5_clarity | Select | Pass / Fail |
| qc_checkpoint5_sterility | Select | Pass / Fail / By Process |
| qc_status | Select | Approved / Rejected |
| status | Select | Available / Partially Used / Exhausted / Rejected |

**Business rule:** Green:Red ratio is 75:25 — IMMUTABLE. Auto-calculated by system.

---

### 5.10 Production Batch

**Purpose:** Tracks the biological cultivation lifecycle from Flask through 6600L
PBR. Multi-stage document with QC checkpoints at each stage.

**Naming Series:** `PROD-.YYYY.-.####`

*(DocType exists, full wiring pending)*

| Field | Type | Notes |
|-------|------|-------|
| product | Link:Item | Target product |
| strain | Link:Pluviago Strain | Strain used |
| strain_generation | Int | Generation number (1–5) |
| mother_batch | Link:Production Batch | Parent batch (lineage) |
| final_medium_batch | Link:Final Medium Batch | Medium used at inoculation |
| planned_volume | Float | Target output |
| start_date | Date | |
| expected_completion | Date | |
| actual_completion | Date | |
| status | Select | Planned / In Progress / Completed / Failed / On Hold |
| current_stage | Select | Flask / 25L PBR / 275L PBR / 925L PBR / 6600L PBR Green / 6600L PBR Red |
| stages | Child table | Stage-wise tracking |
| qc_readings | Child table | QC parameter readings per stage |
| contamination_status | Select | Clean / Contaminated |
| remedial_action | Data | e.g., Harvest early, Reddening |

---

### 5.11 Pluviago Strain

**Purpose:** Master data for algae strains. Each production batch references a
strain with its generation number.

| Field | Type | Notes |
|-------|------|-------|
| strain_name | Data | Common/scientific name |
| organism_type | Data | e.g., Haematococcus pluvialis |
| source_origin | Small Text | Where strain was obtained |
| storage_condition | Select | 2-8C / -20C / RT |
| storage_location | Data | Lab location |
| last_verification_date | Date | Purity check date |
| is_active | Check | In use or archived |

---

### 5.12 Harvest Batch

*(DocType exists)*

Linked to a Production Batch. Records harvest date, wet biomass, drying process,
final dried weight, assay result, and dispatch for external extraction.

---

### 5.13 Contamination Incident

*(DocType exists)*

Records contamination events during cultivation. Linked to a Production Batch.
Captures type of contamination, stage detected, action taken (harvest early,
discard, reddening).

---

### 5.14 Cultivation Return Event

*(DocType exists)*

Records back-propagation events — when a later-stage culture is used to re-seed
an earlier stage (e.g., 275L culture returned to Flask for new lineage).

---

## 6. Stock Solution Formulations

### A1 — Green Trace Element Stock (1 L)

**Storage:** 2–8°C | **Expiry:** 1 year | **Sterilization:** Autoclave

| Chemical | Formula | Qty (per 1L) |
|----------|---------|-------------|
| Manganese II Chloride | MnCl₂·4H₂O | 41 mg |
| Zinc Chloride | ZnCl₂ | 5 mg |
| Cobalt Chloride | CoCl₂·6H₂O | 2 mg |
| Sodium Molybdate | Na₂MoO₄·2H₂O | 4 mg |

**Usage in media:** 18 mL per 1L Green Medium

### A2 — Vitamin Stock (500 mL)

**Storage:** 2–8°C Dark | **Expiry:** 1 year | **Sterilization:** 0.22µm Filter (NOT autoclave)

| Chemical | Formula | Qty (per 500mL) |
|----------|---------|----------------|
| Vitamin B12 | C₆₃H₈₈CoN₁₄O₁₄P | 25 mg |
| Biotin | C₁₀H₁₆N₂O₃S | 100 mg |
| Thiamine HCl | C₁₂H₁₇N₄OSCl·HCl | 500 mg |

**Usage in media:** 2 mL per 1L Green Medium

### A3 — Ferric Citrate Stock (500 mL)

**Storage:** RT or 2–8°C | **Expiry:** 2 years | **Sterilization:** Autoclave

| Chemical | Formula | Qty (per 500mL) |
|----------|---------|----------------|
| Ferric Citrate | C₆H₅FeO₇·H₂O | 2.35 g |

**Usage in media:** 0.94 mL per 1L Green Medium

### A4 — Sodium Nitrate Stock (100 mL)

**Storage:** RT | **Expiry:** 3 years | **Sterilization:** Autoclave

| Chemical | Formula | Qty (per 100mL) |
|----------|---------|----------------|
| Sodium Nitrate | NaNO₃ | 24.67 g |

**Usage in media:** 9.48 mL per 1L Green Medium

### A5 — Phosphate Buffer Stock (100 mL)

**Storage:** RT | **Expiry:** 3 years | **Sterilization:** Autoclave

| Chemical | Formula | Qty (per 100mL) |
|----------|---------|----------------|
| Potassium Phosphate Dibasic | K₂HPO₄ | 4.535 g |
| Potassium Dihydrogen Phosphate | KH₂PO₄ | 3.58 g |

**Usage in media:** 4.4 mL per 1L Green Medium

### A5M / A6 — Trace Stock for Red Medium (1 L)

**Storage:** 2–8°C | **Expiry:** 1 year | **Sterilization:** Autoclave

| Chemical | Formula | Qty (per 1L) |
|----------|---------|-------------|
| Boric Acid | H₃BO₃ | 2.85 mg |
| Manganese II Chloride | MnCl₂·4H₂O | 1.81 mg |
| Zinc Sulphate | ZnSO₄·7H₂O | 0.2 mg |
| Cupric Sulphate | CuSO₄·5H₂O | 79 mg |
| Molybdenum Trioxide | MoO₃ | 15 mg |

**Usage in media:** 1 mL per 1L Red Medium

### A7 — Six Individual Red Medium Stocks (Each 100 mL)

**Storage:** RT (vitamins at 2–8°C dark) | **Sterilization:** Autoclave (A7-VI: 0.22µm Filter)

| Sub-stock | Key Chemical | Qty | Usage |
|-----------|-------------|-----|-------|
| A7-I — Calcium Nitrate | Ca(NO₃)₂·4H₂O | 1 g / 100mL | 1 mL per 1L Red |
| A7-II — FAC (Ferric Ammonium Citrate) | FAC | 600 mg / 100mL | 1 mL per 1L Red |
| A7-III — EDTA | C₁₀H₁₄N₂Na₂O₈·2H₂O | 1 g / 100mL | 1 mL per 1L Red |
| A7-IV — Sodium Carbonate | Na₂CO₃ | 1 g / 100mL | 1 mL per 1L Red |
| A7-V — Citric Acid | C₆H₈O₇ | 600 mg / 100mL | 1 mL per 1L Red |
| A7-VI — Vitamin B1 | C₁₂H₁₇N₄OSCl·HCl | 100 mg / 100mL | 1 mL per 1L Red |

**Important:** A7-I (calcium) must be added last during Red Medium preparation.
Calcium precipitates if mixed with sulphates/phosphates early. This is a formulation
constraint — not enforced by system, but documented for the lab.

---

## 7. Medium Preparation Recipes

### Green Medium (1 L)

**Base salts (direct, before sterilization):**

| Chemical | Qty |
|----------|-----|
| CaCl₂ | 75 mg |
| MgSO₄·7H₂O | 225 mg |
| NaCl | 75 mg |

**Process:**
1. Add ~800 mL DI water
2. Dissolve base salts
3. **QC Checkpoint 1:** Clarity check (Pass = Clear, no precipitate)
4. Autoclave base solution
5. Cool to room temperature
6. Aseptically add (via 0.22µm filter):
   - A1: 18 mL, A2: 2 mL, A3: 0.94 mL, A4: 9.48 mL, A5: 4.4 mL
7. Top up to 1L with DI water
8. **QC Checkpoint 2:** pH (spec), Clarity, Sterility (by process)
9. Release as Green Medium

**Storage:** 2–8°C (2–4 weeks) or RT (1 week)

---

### Red Medium — BG-11 Red (1 L)

**Base salts (direct, before sterilization):**

| Chemical | Qty |
|----------|-----|
| CaCl₂ | 100 mg |
| MgSO₄ | 200 mg |

**Process:**
1. Add ~800 mL DI water
2. Dissolve base salts
3. **QC Checkpoint 3:** Clarity check
4. Sterilize — preferred: filter-sterilize final medium (0.22µm); alt: autoclave base + cool
5. Aseptically add:
   - A6 (A5M): 1 mL, A7-I through A7-VI: 1 mL each
6. Top up to 1L with DI water
7. **QC Checkpoint 4:** pH (BG-11 Red spec), Clarity, Sterility
8. Release as Red Medium

---

### Final Medium (Target Volume V)

| Component | Volume |
|-----------|--------|
| Green Medium | 0.75 × V |
| Red Medium | 0.25 × V |

**Process:**
1. Enter required volume V in ERP — system auto-calculates Green and Red volumes
2. Aseptically transfer Green Medium to sterile tank
3. Aseptically add Red Medium
4. Mix
5. **QC Checkpoint 5:** pH, Clarity, Sterility
6. Release as Final Medium

**Rule: 75:25 ratio is IMMUTABLE. No deviation.**

---

## 8. QC Process Design

Pluviago has **two distinct QC processes** — both are separate from ERPNext's
built-in Quality Inspection (which is disabled for all chemical items).

### QC Process 1 — Incoming Material QC (Physical/Chemical)

**When:** On receipt of chemicals from vendor  
**What:** Check chemical identity, purity, physical appearance vs vendor COA  
**How:** Manual review — QC Manager compares vendor PDF against internal spec  
**System record:** Chemical COA doctype + `qc_status` on Raw Material Batch  
**Gate:** RMB cannot be submitted (used) unless `qc_status = Approved` AND `coa_verified = 1`

### QC Process 2 — In-Process / Preparation QC

**When:** After each preparation step (stock solution, media, each cultivation stage)  
**What:** Physical/chemical parameters of the prepared material  
**System records:**
- Stock Solution Batch: pH actual, clarity, sterile filtered, qc_status
- Green/Red/Final Medium Batch: 5 QC checkpoints (see Section 7)
- Production Batch: PAR, pH, OD, cell count, microscopy per stage

#### The 9 QC Checkpoints in Full

| # | Stage | Parameters | Decision |
|---|-------|-----------|---------|
| QC1 | Green Medium pre-steril | Clarity | Pass → autoclave / Fail → discard |
| QC2 | Green Medium final | pH, Clarity, Sterility | Pass → release / Fail → discard |
| QC3 | Red Medium pre-steril | Clarity | Pass → sterilize / Fail → discard |
| QC4 | Red Medium final | pH, Clarity, Sterility | Pass → release / Fail → discard |
| QC5 | Final Medium | pH, Clarity, Sterility | Pass → release / Fail → discard |
| QC6 | Flask (Seed Qual.) | PAR, pH, Microscopy, Cell Count, OD, Cell Size | Pass → 25L / Fail → terminate |
| QC7 | Each PBR stage | PAR, pH, Microscopy, Cell Count, OD, Cell Size, Dry Weight, Contamination | Pass → next stage / Fail → corrective action or harvest |
| QC8 | Harvest | Dry Weight | Pass → drying / Fail → investigate |
| QC9 | Post-drying | Assay % | Pass → pack / Fail → investigate |

#### Biological QC Parameters

| Parameter | Method | When |
|-----------|--------|------|
| Microscopy | Direct visual observation under microscope | Flask, all PBR stages |
| Cell count | Haemocytometer or automated counter | Flask, 25L, 275L, 925L, 6600L |
| Cell size | Microscopy measurement | Flask, 25L, 275L |
| OD (Optical Density) | Spectrophotometer | Flask, all PBR stages |
| Contamination check | Microscopy + visual | 275L, 925L (decision gate) |
| Dry weight | Filtration + oven dry | 25L onwards, Harvest |
| Assay (astaxanthin %) | HPLC or spectrophotometry | Post-drying, post-extraction |
| PAR | PAR meter | All cultivation stages |

---

## 9. User Roles & Permissions

| Role | Key Permissions |
|------|----------------|
| Admin | Full system access, user management, configuration |
| Procurement Manager | Create PO, approve vendors, track deliveries |
| QA Analyst | Verify COA, approve/reject batches, QC entry |
| Lab Technician | Prepare stocks/media, perform and record QC tests |
| Production Operator | Enter checkpoint data, update batch status |
| Production Supervisor | Approve/reject stage transitions, handle failures |
| Harvest Operator | Record harvest, manage drying |
| Packing Operator | Execute packing, apply and verify labels |
| Engineering Manager | Asset registration, maintenance planning |
| HRMS Manager | Payroll, attendance, shift allocation |
| Accounts Manager | Transactions, reconciliation, reports |
| Sales Manager | Sales orders, payments, deliveries |
| Management | Read-only dashboards, approval of high-value transactions |

**Field-level restrictions:**
- Vendor COA Submission: only QA can approve/reject
- Production Batch QC: only Supervisor can approve stage transitions
- Accounting GL postings: only Accounts Manager
- Asset disposal: only Admin/Management

---

## 10. Reports Required

### Production

1. **Batch Genealogy Report** — Full lineage: Strain → Flask → 25L → 275L → 925L → 6600L → Harvest
2. **Production Batch Summary** — Batch ID, status, planned vs actual yield, cost per batch
3. **QC Compliance Report** — Pass/fail rates by stage, contamination incidents, checkpoint adherence
4. **Reactor Yield Report** — Stage-wise yield efficiency and loss analysis
5. **Raw Material Traceability Report** — Chemical batch → SSB → Medium → Reactor → Harvest → Product

### Inventory

6. **Chemical Stock & Consumption Report** — Current levels, movement history, batch expiry alerts
7. **Stock Solution Inventory Report** — A1–A7 stocks available, expiry, linked production batches
8. **Batch Expiry Alert Report** — Materials approaching or past expiry

### Quality & Compliance

9. **COA Validation History Report** — Vendor submissions, QA approvals/rejections, timeline
10. **Sampling Report** — Schedule vs actual, pass/fail trends
11. **OOS Trend Report** — Out-of-Specification events and analysis

### Asset & Maintenance

12. **Asset Lifecycle Report**
13. **Maintenance Schedule & Calibration Due Report**

### Financial

14. **Batch Costing Report** — RM cost + labor + overhead per batch
15. **Profitability Report** — Revenue, COGS, gross/net margin
16. **Zoho Books Sync Report**

### Dashboards

- Production Dashboard (batch status, stage progress, yield trends, alerts)
- QC Dashboard (pass/fail rates, contamination, assay results)
- Inventory Dashboard (stock levels, expiry alerts, low-stock)
- Financial Dashboard (batch costs, revenue, cash position)

---

## 11. Integration Requirements

### Zoho Books (Priority)

Real-time sync of purchase, production, and expense transactions to Zoho Books GL.
Uses Zoho Books API v3. All batch-wise costs auto-calculated and synced.

### Planned / Optional

| Integration | Purpose |
|-------------|---------|
| LIMS | COA template sync, test result import |
| SCADA / Reactor Automation | Real-time PAR, pH, temperature from bioreactors |
| Barcode / QR Code | Batch ID scanning, material tracking, asset ID |
| IoT Sensors | PAR probes, pH probes, temperature sensors |
| Android Mobile App | GRN receipt, attendance, checkpoint entry, asset scan |

### Mobile App Scope (Android)

- Secure role-based login
- Mark GRN receive status
- Mark attendance / shift entry
- Supervisor approvals
- Scan asset QR/barcode
- Upload maintenance photos
- Collect payments against invoices
- View financial summaries (management)
- All entries sync real-time (offline → sync on reconnect)

---

## 12. Business Rules & Constraints

### Procurement Rules

- No PO without vendor approval in AVL — soft warning fires (not hard block)
- COA template must be defined before material procurement begins
- GRN (Purchase Receipt) allowed after PO — COA review happens in parallel
- Material cannot be used in production until RMB is submitted (qc_status = Approved + coa_verified = 1)
- ERPNext Quality Inspection is **disabled** for all chemical items — replaced by COA + RMB flow

### Inventory Rules

- Every consumption must be linked to a specific RMB (batch traceability)
- Cannot use expired materials (expiry check on submit/use)
- System alerts 30 days before expiry
- Stock level alerts when below minimum; auto-generate material requisition
- Consumed qty tracked via Stock Consumption Log — source of truth

### Medium Formulation Rules

- Final Medium = 75% Green + 25% Red — IMMUTABLE — auto-calculated
- Cannot use expired or unapproved stock solutions in media preparation
- All 5 QC checkpoints must be recorded before medium is released

### Production Rules

- Cannot skip bioreactor stages (Flask → 25L → 275L → 925L → 6600L)
- Contamination at any stage → harvest early (no further scaling)
- Must pass QC gate before proceeding to next stage
- Production cycle is fixed at one month per batch
- All batches must be traceable to the strain and generation number
- Outsourced extraction: theoretical yield calculated; variance from actual return must be flagged

### QC Rules

- Cannot skip QC checkpoints
- Parameters must be within specification before stage can be approved
- Operator records checkpoint → Supervisor approves
- Failed QC → corrective action documented or batch terminated
- All QC data stored under batch record permanently

### Financial Rules

- Batch costs auto-calculated from consumed materials + labor + overhead
- Real-time sync with Zoho Books
- PO above threshold requires management approval

### Audit & Compliance (GMP)

- Full audit trail — every transaction logged with timestamp and user
- Historical records cannot be edited
- Digital batch records maintained end-to-end
- COA verification documented with reviewer name and date

---

## 13. Chemical Master Reference

All 23 chemicals are in the ERPNext Item master under item groups:
Base Salts, Trace Elements, Nutrients, Vitamins, Media Chemicals, Raw Materials.

Item codes follow pattern `CHEM-001` through `CHEM-023`.

| Chemical Name | CAS / Formula | Grade | Vendor(s) | Storage | Shelf Life |
|---------------|--------------|-------|-----------|---------|-----------|
| Calcium Chloride Dihydrate | CaCl₂·2H₂O | Extrapure AR 99.5% | SRL | RT | 5 yr |
| Magnesium Sulphate Heptahydrate | MgSO₄·7H₂O | Min assay 99% | Qualigens | RT | 5 yr |
| Sodium Chloride | NaCl | Extrapure AR 99.9% | SRL | RT | 5 yr |
| Manganese II Chloride Tetrahydrate | MnCl₂·4H₂O | 97–101% | Molychem | 2-8°C | 5 yr |
| Zinc Chloride | ZnCl₂ | Min 95% | Qualigens | RT | 5 yr |
| Cobalt Chloride Hexahydrate | CoCl₂·6H₂O | 97–102% | HIMEDIA | RT | 3 yr |
| Sodium Molybdate Dihydrate | Na₂MoO₄·2H₂O | 98–103% | HIMEDIA | RT | 3 yr |
| Vitamin B12 (Cyanocobalamin) | C₆₃H₈₈CoN₁₄O₁₄P | 96–102% | HIMEDIA | 2-8°C dark | 2–3 yr |
| Biotin | C₁₀H₁₆N₂O₃S | 99.5–100.5% | HIMEDIA | 2-8°C dark | 3 yr |
| Thiamine Hydrochloride | C₁₂H₁₇N₄OSCl·HCl | Min 98.5% | Qualigens | RT | 5 yr |
| Ferric Citrate | C₆H₅FeO₇·H₂O | Assay 18–22% | HIMEDIA | RT | 2 yr |
| Sodium Nitrate | NaNO₃ | >99% | Qualigens / Supelco | RT | 5 yr |
| Potassium Dihydrogen Phosphate | KH₂PO₄ | 99–101% | Qualigens | RT | 5 yr |
| Potassium Phosphate Dibasic | K₂HPO₄ | 98–102% | HIMEDIA | RT | 3 yr |
| Boric Acid | H₃BO₃ | Min 99.5% | SRL | RT | 5 yr |
| Zinc Sulphate Heptahydrate | ZnSO₄·7H₂O | 99.5% | SRL / NICE | RT | 5 yr |
| Cupric Sulphate Pentahydrate | CuSO₄·5H₂O | 99.5–100.5% | Qualigens | RT | 5 yr |
| Ammonium Molybdate | (NH₄)₆Mo₇O₂₄·4H₂O | Min 98% | Qualigens | RT | 5 yr |
| Calcium Nitrate Tetrahydrate | Ca(NO₃)₂·4H₂O | 98–99% | NICE / SRL | RT | 4 yr |
| Ammonium Ferric Citrate (FAC) | C₆H₈O₇·xFe³⁺·yNH₃ | 16.5–22.5% | NICE / Rankem / SRL | RT | 3 yr |
| EDTA Disodium Dihydrate | C₁₀H₁₄N₂Na₂O₈·2H₂O | Min 98% | Qualigens | RT | 5 yr |
| Sodium Carbonate | Na₂CO₃ | Min 99.5% | Qualigens | RT | 5 yr |
| Citric Acid Monohydrate | C₆H₈O₇ | Min 99.5% | Qualigens | RT | 4 yr |

---

## 14. Implementation Status

### Done (Tested & Committed)

| Component | Status |
|-----------|--------|
| Approved Vendor doctype | Done |
| Purchase Order hook (AVL soft warning) | Done |
| Chemical COA doctype + JS | Done |
| Raw Material Batch doctype + JS | Done |
| QC Parameter Spec doctype | Done |
| Stock Consumption Log doctype | Done |
| `recalculate_remaining_qty()` from SCL | Done |
| "Recalculate Stock" client button | Done |
| `get_spec_parameters()` whitelist function | Done |
| "Load Spec Template" button on COA | Done |
| Disable ERPNext QI on all 23 CHEM items | Done |
| Data patch `disable_chemical_qi` registered in patches.txt | Done |
| Full test script `test_flow.py` | Done |

### In Progress

| Component | Status |
|-----------|--------|
| Stock Solution Batch (SSB) — ingredient consumption + QC gate | Next |
| SSB volume tracking (remaining_volume on use) | Next |

### Planned (Not Started)

| Component | Notes |
|-----------|-------|
| Green Medium Batch — full ingredient wiring + QC checkpoints | After SSB |
| Red Medium Batch | After Green |
| Final Medium Batch — 75:25 auto-calc | After Red |
| Production Batch — stage progression + QC gates | After media |
| Biological QC readings (microscopy, cell count) | Part of Production Batch |
| Contamination Incident wiring | Part of Production Batch |
| Harvest Batch — full flow | After Production Batch |
| Extraction Batch — outsource + QC incoming | After Harvest |
| Packing Batch | After Extraction |
| HRMS | Separate phase |
| Asset Management | Separate phase |
| Sales Management | Separate phase |
| Zoho Books integration | Separate phase |
| Android Mobile App | Separate scope |
| Reports (all) | After doctypes are stable |

---

## 15. Key Design Decisions

### Why Not ERPNext BOM/Work Order

Evaluated and rejected. ERPNext manufacturing is for discrete production (units).
Pluviago's process is biological — batch quantities change continuously, culture
can fail at any stage, lineage tracking is multi-generational. Custom DocTypes
were the correct choice.

### COA Verification is Manual

The client confirmed: COA is a manual process. QC Manager reads the vendor PDF,
compares visually against internal spec, and ticks the `coa_verified` checkbox.
The system records the decision — it does not automate the comparison.
Parameter entries in Chemical COA are informational/audit trail only.

### AVL Check is Soft Warning, Not Hard Block

The client confirmed soft warning is preferred for PO from unapproved vendors.
This allows emergency procurement while maintaining a visible audit trail.
The orange warning message fires via `frappe.msgprint` in the PO validate hook.

### ERPNext QI Disabled

ERPNext's `inspection_required_before_purchase` was blocking Purchase Receipt
submissions for all CHEM items. Since Pluviago uses Chemical COA + RMB qc_status
as their QC system (parameter-level + batch-level decision), ERPNext QI is
redundant. Disabled via `patches/v1_0/disable_chemical_qi.py`.

### Stock Consumption Log as Source of Truth

RMB fields (`remaining_qty`, `consumed_qty`) are maintained incrementally but
the SCL is the authoritative audit trail. `recalculate_remaining_qty()` can
always recompute from SCL if drift occurs. This prevents data inconsistency.

### Two-Company Setup

- `Softland India Ltd (SIL)` — parent/owner company
- `Pluviago Biotech Pvt. Ltd. (PB)` — operational company for all production

All PO/PR/RMB work must use `Pluviago Biotech Pvt. Ltd.` as company. Warehouses
belong to PB company. Default company in ERPNext may show SIL — always verify.

---

## 16. Known Issues & Technical Notes

### Frappe-Specific Gotchas

| Issue | Root Cause | Fix |
|-------|-----------|-----|
| `'DocType' object has no attribute 'naming_series'` | Custom doctypes need `doc.naming_series = "..."` set before `insert()` | Set it explicitly after `frappe.get_doc({...})` |
| "Value cannot be changed for Series" | `set_only_once: 1` on naming_series field conflicts with cancelled docs | Remove `set_only_once: 1` from all custom doctype JSON |
| `fetch_from` not working server-side | `fetch_from` is client-side JS only | Use explicit `frappe.db.get_value()` in Python |
| Group warehouse error | Parent warehouse nodes cannot receive stock | Use leaf warehouse (e.g., `Chemical Store RT - PB`, not `Raw Material Store - PB`) |
| `server_script_enabled` not working | Was in `site_config.json` — Frappe reads it from `common_site_config.json` only | Added to `/sites/common_site_config.json` |
| Dynamic Link validation failure in tests | `source_document` Dynamic Link validates linked doc exists — fake test names fail | Omit `source_doctype`/`source_document` in test inserts, or use real doc names |
| `remaining_qty = 0` after RMB submit | `on_submit` was not initializing stock fields | Added `db_set("remaining_qty", self.received_qty)` in `on_submit` |
| Date comparison `str vs datetime.date` | `frappe.utils.getdate()` not used | Always use `frappe.utils.getdate()` for date comparisons |

### File Paths

```
Custom app root:       /home/silpc-068/replica-bench/apps/pluviago/
Main doctype dir:      pluviago/pluviago_biotech/doctype/
Overrides:             pluviago/pluviago_biotech/overrides/
Utils:                 pluviago/pluviago_biotech/utils/stock_utils.py
Patches:               pluviago/patches/v1_0/
Test script:           pluviago/test_flow.py
Hooks:                 pluviago/hooks.py
Patches index:         patches.txt (app root)
Site config:           /home/silpc-068/replica-bench/sites/common_site_config.json
```

### Common Bench Commands

```bash
# Activate virtualenv
source /home/silpc-068/replica-bench/env/bin/activate

# Migrate after doctype JSON changes
bench --site replica1.local migrate

# Run test script
bench --site replica1.local execute pluviago.test_flow.run_all_tests

# Run a specific patch
bench --site replica1.local execute pluviago.patches.v1_0.disable_chemical_qi.execute

# Clear cache after JS changes
bench --site replica1.local clear-cache

# Restart server
bench restart
```
