# Pluviago Biotech — Business Flow & Requirements

> This document describes what Pluviago Biotech does, how they produce their
> product, what they need tracked at every stage, and what the ERP must model.
> It is written purely from a business perspective — no software implementation
> details. Any developer or AI working on this project must read this first.

---

## 1. Who Is Pluviago Biotech

Pluviago Biotech cultivates the microalgae *Haematococcus pluvialis* to produce
**astaxanthin** — a high-value natural antioxidant. End products are astaxanthin
oil and tablets. The algae are grown in-house from strain to harvest. Extraction
of the active compound is outsourced to a third-party partner.

### Key characteristics

- Every operation is **batch-wise**. Each batch has its own identity, lineage,
  quality record, and cost.
- The production cycle is **fixed at one month** regardless of volume.
- The process is **biological**, not discrete manufacturing. Culture grows
  continuously, can fail at any stage, and must be traced to its biological
  origin (strain and generation).
- **Full traceability** is required: from the raw chemical vendor batch all
  the way to the final dispatched product.
- The company is building toward **GMP (Good Manufacturing Practice)** compliance.

---

## 2. The Complete Production Flow

```
STAGE 0   — Procurement & Incoming QC
STAGE 0A  — Stock Solution Preparation
STAGE 0B  — Green Medium & Red Medium Preparation
STAGE 0C  — Final Medium Formulation & Sterile Release
STAGE 1   — Flask Culture (Seed Qualification)
STAGE 2   — 25 L Photobioreactor
STAGE 3   — 275 L Photobioreactor
STAGE 4   — 925 L Photobioreactor
STAGE 5   — 6600 L Production Reactor (Green Phase → Red Phase)
STAGE 6   — Harvest
STAGE 7   — Drying
STAGE 8   — Packing
STAGE 9   — External Extraction (Outsourced)
STAGE 10  — Repacking & Final Dispatch
```

Each stage feeds the next. A failure at any stage stops forward movement —
the batch either gets corrective action, gets harvested early, or is terminated.

---

## 3. Stage 0 — Procurement & Incoming QC

### What happens

The company buys raw chemicals from approved vendors. Before any chemical
can be used in production, it must pass an incoming quality check by the
QC Manager.

### Vendor qualification

- Every vendor must be formally approved before a purchase order can be raised.
- Each vendor is approved for specific chemicals, not in general.
- Approval has an expiry date. Re-qualification is required periodically.
- A vendor can be Approved, Pending, or Suspended.

### Purchase to inventory flow

```
Material requirement identified
        ↓
Approved vendor selected
        ↓
Purchase Order raised
        ↓
Vendor delivers material + submits COA (Certificate of Analysis)
        ↓
QC Manager reviews vendor COA against internal specification
        ↓
    Approved → Goods Receipt created → Material enters inventory
    Rejected → Material returned to vendor, rejection documented
```

### Certificate of Analysis (COA)

Each received chemical batch must come with a COA from the vendor containing:

- Product name and batch number
- Manufacturer name and date
- Expiry date
- Purity assay %
- Identity test result
- Key parameter values (pH, appearance, heavy metals if required)
- Any other parameters defined in Pluviago's specification for that chemical

The QC Manager manually compares the vendor COA against the internal
specification template for that chemical. The review decision (Pass/Fail),
reviewer name, and review date are recorded. This is the primary incoming
quality gate.

### What gets tracked per received batch

- Chemical name and item code
- Vendor and vendor's own batch number
- Manufacture date and expiry date
- Quantity received and unit of measure
- Storage condition (Room Temperature / 2–8°C / −20°C)
- Warehouse / storage location
- QC status (Approved / Rejected / Pending)
- COA verified: yes/no, by whom, on what date
- Link to Purchase Receipt document

---

## 4. Stage 0A — Stock Solution Preparation

### What happens

Raw chemicals are not added directly to the culture medium. They are first
dissolved into **concentrated stock solutions** (labelled A1 through A7,
plus A5M). These are prepared in bulk, sterilized, stored, and drawn from
each time a batch of medium is made.

### Why this stage exists

- Ensures precision — small quantities of trace elements and vitamins can be
  measured accurately as a concentrated solution rather than weighing
  microgram amounts directly.
- Provides a reusable intermediate that is stable over weeks or months.
- Allows QC of the solution before it is used in cultivation.
- Maintains full chemical traceability: every stock solution records which
  raw material batch each chemical came from.

### The seven stock solutions

| Label | Name | Sterilization | Storage | Shelf Life |
|-------|------|--------------|---------|-----------|
| A1 | Green Trace Element Stock | Autoclave | 2–8°C | 1 year |
| A2 | Vitamin Stock | 0.22 µm Filter (NOT autoclave) | 2–8°C, Dark | 1 year |
| A3 | Ferric Citrate Stock | Autoclave | RT or 2–8°C | 2 years |
| A4 | Sodium Nitrate Stock | Autoclave | RT | 3 years |
| A5 | Phosphate Buffer Stock | Autoclave | RT | 3 years |
| A5M / A6 | Red Trace Element Stock (for Red Medium) | Autoclave | 2–8°C | 1 year |
| A7-I to A7-VI | Six individual BG-11 Red stocks | Autoclave (A7-VI by Filter) | RT or 2–8°C | 2–3 years |

### Formulations

**A1 — Green Trace Element Stock (per 1 L)**

| Chemical | Quantity |
|----------|---------|
| Manganese II Chloride (MnCl₂·4H₂O) | 41 mg |
| Zinc Chloride (ZnCl₂) | 5 mg |
| Cobalt Chloride (CoCl₂·6H₂O) | 2 mg |
| Sodium Molybdate (Na₂MoO₄·2H₂O) | 4 mg |

Usage: 18 mL per 1 L Green Medium

---

**A2 — Vitamin Stock (per 500 mL)**

| Chemical | Quantity |
|----------|---------|
| Vitamin B12 (Cyanocobalamin) | 25 mg |
| Biotin | 100 mg |
| Thiamine HCl (Vitamin B1) | 500 mg |

Usage: 2 mL per 1 L Green Medium. Must be protected from light at all times.
Filter sterilize only — heat from autoclave destroys vitamins.

---

**A3 — Ferric Citrate Stock (per 500 mL)**

| Chemical | Quantity |
|----------|---------|
| Ferric Citrate | 2.35 g |

Usage: 0.94 mL per 1 L Green Medium

---

**A4 — Sodium Nitrate Stock (per 100 mL)**

| Chemical | Quantity |
|----------|---------|
| Sodium Nitrate (NaNO₃) | 24.67 g |

Usage: 9.48 mL per 1 L Green Medium

---

**A5 — Phosphate Buffer Stock (per 100 mL)**

| Chemical | Quantity |
|----------|---------|
| Potassium Phosphate Dibasic (K₂HPO₄) | 4.535 g |
| Potassium Dihydrogen Phosphate (KH₂PO₄) | 3.58 g |

Usage: 4.4 mL per 1 L Green Medium

---

**A5M / A6 — Red Trace Element Stock (per 1 L)**

| Chemical | Quantity |
|----------|---------|
| Boric Acid (H₃BO₃) | 2.85 mg |
| Manganese II Chloride (MnCl₂·4H₂O) | 1.81 mg |
| Zinc Sulphate (ZnSO₄·7H₂O) | 0.2 mg |
| Cupric Sulphate (CuSO₄·5H₂O) | 79 mg |
| Molybdenum Trioxide (MoO₃) | 15 mg |

Usage: 1 mL per 1 L Red Medium

---

**A7 — Six Individual Red Medium Stocks (each 100 mL)**

| Sub-stock | Chemical | Quantity per 100 mL | Usage per 1 L Red |
|-----------|---------|--------------------|--------------------|
| A7-I | Calcium Nitrate Ca(NO₃)₂·4H₂O | 1 g | 1 mL |
| A7-II | Ferric Ammonium Citrate (FAC) | 600 mg | 1 mL |
| A7-III | EDTA Disodium | 1 g | 1 mL |
| A7-IV | Sodium Carbonate (Na₂CO₃) | 1 g | 1 mL |
| A7-V | Citric Acid | 600 mg | 1 mL |
| A7-VI | Vitamin B1 (Thiamine HCl) | 100 mg | 1 mL |

A7-VI must be filter sterilized (NOT autoclaved). All A7 stocks are added
individually — never pre-mixed — because several precipitate when combined early.

### Preparation procedure (all stocks)

1. Weigh chemicals precisely as per formula
2. Add to approximately 80% of target volume in DI/RO water
3. Stir until completely dissolved
4. Make up to final target volume with DI water
5. Sterilize by appropriate method (autoclave or 0.22 µm filter)
6. Label with: solution name, batch number, preparation date, expiry date, prepared by
7. Store under specified condition

### What gets tracked per stock solution batch

- Solution type (A1 through A7, A5M)
- Target and actual volume prepared
- Preparation date and expiry date
- Prepared by (operator)
- Sterilization method and date
- Storage condition and location
- Each ingredient used — with link to the specific raw material batch
  (this is the traceability link from medium back to vendor chemical)
- QC result: pH (where applicable), visual clarity, sterile filter used
- Volume remaining (decremented each time it is used in media preparation)
- Status: Available / Partially Used / Exhausted / Rejected

### QC gate on stock solutions

A stock solution must pass QC before it can be used to prepare medium.
Minimum checks: clarity (clear, no precipitate), pH where applicable.
A failed stock solution batch is discarded and re-prepared.

---

## 5. Stage 0B — Medium Preparation

### What happens

Stock solutions and a small set of base salts are combined with DI water to
produce two distinct culture media: **Green Medium** and **Red Medium**. These
are the nutrient environments in which the algae grow.

Green Medium supports the green (growth) phase.
Red Medium (BG-11) supports the red (carotenoid accumulation) phase.

Each medium batch must pass QC before it can be used in cultivation.

### Green Medium (per 1 L)

**Step 1 — Dissolve base salts in ~800 mL DI water:**

| Chemical | Quantity |
|----------|---------|
| Calcium Chloride (CaCl₂) | 75 mg |
| Magnesium Sulphate (MgSO₄·7H₂O) | 225 mg |
| Sodium Chloride (NaCl) | 75 mg |

**QC Checkpoint 1:** Inspect for clarity before sterilization.
Result must be: clear, no precipitate. Fail = discard and restart.

**Step 2 — Autoclave the base salt solution (not the stocks).**

**Step 3 — Cool to room temperature.**

**Step 4 — Add stock solutions aseptically (via 0.22 µm sterile filter):**

| Stock | Volume Added |
|-------|-------------|
| A1 (Green Trace) | 18 mL |
| A2 (Vitamins) | 2 mL |
| A3 (Ferric Citrate) | 0.94 mL |
| A4 (NaNO₃) | 9.48 mL |
| A5 (Phosphate Buffer) | 4.4 mL |

**Step 5 — Top up to exactly 1.000 L with sterile DI water. Mix.**

**QC Checkpoint 2:** Measure pH. Inspect clarity.
Result must be: pH within specification, clear, no precipitation.
Sterility: assured by aseptic process or periodic test.
Fail = adjust pH and retest if possible, otherwise discard.

**Step 6 — Green Medium released if both checkpoints pass.**

---

### Red Medium / BG-11 Red (per 1 L)

**Step 1 — Dissolve base salts in ~800 mL DI water:**

| Chemical | Quantity |
|----------|---------|
| Calcium Chloride (CaCl₂) | 100 mg |
| Magnesium Sulphate (MgSO₄) | 200 mg |

**QC Checkpoint 3:** Clarity check before sterilization.
Fail = discard and restart.

**Step 2 — Sterilize.** Preferred method: filter-sterilize the entire final
medium (0.22 µm). Alternative: autoclave base salt solution, then cool.

**Step 3 — Add stock solutions aseptically:**

| Stock | Volume Added |
|-------|-------------|
| A5M / A6 (Red Trace) | 1 mL |
| A7-I (Calcium Nitrate) | 1 mL |
| A7-II (FAC) | 1 mL |
| A7-III (EDTA) | 1 mL |
| A7-IV (Sodium Carbonate) | 1 mL |
| A7-V (Citric Acid) | 1 mL |
| A7-VI (Vitamin B1) | 1 mL |

> Important: A7-I (calcium) must be added last. Calcium precipitates when
> combined with sulphates or phosphates. This is not enforced by software —
> it is a lab procedural rule.

**Step 4 — Top up to exactly 1.000 L with sterile DI water. Mix.**

**QC Checkpoint 4:** pH and clarity.
Result must be: pH within BG-11 Red specification, clear.
Fail = adjust pH if possible, otherwise discard.

**Step 5 — Red Medium released if both checkpoints pass.**

---

### What gets tracked per medium batch

- Medium type (Green / Red)
- Target and actual volume
- Preparation date and operator
- Each stock solution batch used and volume drawn
- Each direct chemical (base salts) used, with quantity and raw material batch link
- Sterilization method and date
- QC checkpoint results for all applicable checkpoints
- Storage condition, location, expiry
- Volume remaining (decremented when used to prepare Final Medium)
- Status: Available / Partially Used / Exhausted / Rejected

---

## 6. Stage 0C — Final Medium Formulation & Sterile Release

### What happens

Green Medium and Red Medium are combined in a fixed 75:25 ratio to produce
the Final Medium used for cultivation.

### Formula — IMMUTABLE

```
Green Medium volume = 0.75 × required final volume
Red Medium volume   = 0.25 × required final volume
```

Example: To produce 10 L of Final Medium:
- Take 7.5 L Green Medium
- Take 2.5 L Red Medium

This ratio is fixed and cannot vary. The ERP calculates volumes automatically
from the target final volume entered.

### Procedure

1. Enter required final volume
2. System calculates Green and Red volumes
3. Transfer Green Medium to sterile mixing vessel
4. Transfer Red Medium to same vessel
5. Mix aseptically
6. **QC Checkpoint 5:** pH, clarity, sterility confirmation
   Result must be: pH within final formulation limits, clear and homogeneous
   Fail = do not use for cultivation, investigate and re-prepare

### What gets tracked

- Target final volume and actual volume produced
- Green Medium batch used and volume taken
- Red Medium batch used and volume taken
- Mixing date and operator
- QC Checkpoint 5 result
- Volume remaining (decremented when used to inoculate a bioreactor)
- Status: Available / Partially Used / Exhausted / Rejected

---

## 7. Biological Cultivation — Core Concepts

Before the stage-by-stage description, three biological concepts must be
understood because they shape how the entire cultivation module is designed.

### 7.1 Batch Numbering and Mother Culture Logic

Pluviago's production is **culture expansion**, not discrete manufacturing.
Every production batch has a biological origin. The batch numbering structure
must reflect this.

Required fields on every production batch (client requirement — mandatory):

| Field | Purpose |
|-------|---------|
| Mother Batch ID | Links this batch to its biological parent (where the inoculum came from) |
| Generation Number | Which expansion step this is (1 = Flask, 2 = 25L, etc.) |
| Lineage Status | Active / Returned / Archived |

This is essential for:
- Contamination investigation (trace back to the source)
- Genealogy report (full chain from strain to product)
- Audit readiness
- Strain stability monitoring (tracking how culture quality changes across generations)

### 7.2 Generation Numbering

```
Flask culture    = Generation 1  (derived from Mother Strain)
25 L PBR         = Generation 2  (derived from Gen 1)
275 L PBR        = Generation 3  (derived from Gen 2)
925 L PBR        = Generation 4  (derived from Gen 3)
6600 L PBR       = Generation 5  (derived from Gen 4)
```

Generations cannot be skipped. The system must enforce linear progression.
Each generation creates a new batch record linked to its parent via Mother Batch ID.

### 7.3 Return-to-Cultivation Loop (Back-Propagation)

The production flow is not strictly linear. In practice, Pluviago operates
a biological return loop:

```
6600 L or 275 L culture
        ↓
Culture withdrawal
        ↓
Dilution with fresh medium
        ↓
Back to Flask (cultivation rack)
```

This is a controlled culture propagation activity used for:
- Maintaining culture continuity without restarting from archived strain
- Generating fresh seed cultures from a known-good production culture

**Critical requirement from client (Roy):**

> This must be configured in ERP as **Material Transfer**, NOT Manufacturing.
> If treated as manufacturing, ERP will incorrectly calculate yield and distort
> genealogy records.

When this happens:
- A new Flask batch is created
- Its Mother Batch ID points to the 6600 L or 275 L batch it was derived from
- Generation number resets to 1 for the new Flask, but lineage is preserved
- Lineage Status of the returned-from batch is set to "Returned"

---

## 8. Stages 1–5 — Biological Cultivation Scale-Up

### Stage 1 — Flask Culture (Seed Qualification)

**Input:** Mother Strain or returned culture + Final Medium  
**Output:** Qualified seed culture ready to inoculate 25 L PBR  
**Duration:** Defined per SOP

**QC checks:**

| Parameter | Type |
|-----------|------|
| PAR (light intensity) | Process QC |
| pH | Process QC |
| Microscopy (visual cell observation) | Biological QC |
| Cell count | Biological QC |
| OD (Optical Density) | Biological QC |
| Cell size | Biological QC |

**Decision gate:**
- All parameters within specification → **PASS** → inoculate 25 L PBR
- Any critical parameter fails → **FAIL** → terminate batch, do not scale up

---

### Stage 2 — 25 L Photobioreactor (PBR)

**Input:** Flask culture (QC passed) + Fresh Medium if required  
**Output:** Expanded culture for 275 L, OR terminated batch

**QC checks:**

| Parameter | Type |
|-----------|------|
| PAR | Process QC |
| pH | Process QC |
| Microscopy | Biological QC |
| Cell count | Biological QC |
| OD | Biological QC |
| Cell size | Biological QC |
| Dry weight | Biological QC |

**Decision gate:**
- All parameters acceptable → **PASS** → scale up to 275 L
- Parameters marginal but no contamination → corrective action, retest
- Parameters fail / contamination confirmed → **FAIL** → terminate or harvest

---

### Stage 3 — 275 L Photobioreactor

**Input:** 25 L culture  
**Output:** Culture for 925 L, OR harvested early (contamination)

**QC checks:**
- Contamination check (microscopy and visual)
- Reddening observation

**Decision gate:**
- No contamination → scale up to 925 L
- Contamination / Reddening observed → **Harvest immediately**, do not scale further

---

### Stage 4 — 925 L Photobioreactor

**Input:** 275 L culture  
**Output:** Culture for 6600 L, OR harvested early

**Decision gate:**
- No contamination → scale up to 6600 L
- Contamination detected → **Harvest immediately**

---

### Stage 5 — 6600 L Production Reactor

**Input:** 925 L culture  
**Output:** Mature biomass ready for harvest

This is the main production stage. It has two biological phases:

**Green Phase** — active cell growth and biomass accumulation  
**Red Phase** — nutrient depletion triggers carotenoid (astaxanthin) accumulation.
               The culture visibly reddens. This is the target outcome.

**QC parameters monitored throughout:**

| Parameter | Type |
|-----------|------|
| PAR | Process QC |
| pH | Process QC |
| Cell count | Biological QC |
| Dry weight | Biological QC |
| Assay (astaxanthin %) | Biological QC |

**Decision gate:**
- Target dry weight and assay values achieved → **Harvest**
- Target not yet achieved → Continue cultivation
- Contamination / unexpected reddening before target → **Harvest immediately**

---

### QC Types — Formal Separation (Client Requirement)

The client explicitly requires QC parameters to be separated into two categories
for dashboards, reporting, and decision logic:

**A. Process QC** — physical and environmental parameters
- pH
- PAR (Photosynthetically Active Radiation)
- Automation / equipment logs

**B. Biological QC** — organism-level parameters
- Microscopy
- Cell size
- Cell count
- OD (Optical Density)
- Contamination status
- Dry weight
- Assay (astaxanthin %)

This separation must be reflected in QC record design, reports, and dashboards.

---

## 9. Stage 6 — Harvest

**Trigger:** Target dry weight and assay values confirmed at 6600 L, OR
contamination detected at any stage requiring early harvest.

**What happens:** Biomass is separated from the culture liquid (centrifugation
or filtration). Wet biomass mass and volume are recorded.

**QC Check:** Dry weight measurement of the harvested biomass.

**Batch linkage:** Harvest batch is linked to the Production Batch it came from,
inheriting full lineage.

---

## 10. Stage 7 — Drying

**Input:** Harvested wet biomass  
**Output:** Dry biomass (powder or flakes)

**Tracked:** Drying method, duration, temperature, input weight, output weight,
moisture content %, yield loss %.

**QC Check:** Assay (potency — astaxanthin %) of the dried biomass.
If assay passes specification → proceed to packing.
If assay fails → investigate, do not pack.

---

## 11. Stage 8 — Packing

**Input:** Dried biomass (assay passed)  
**Output:** Packed product batch

**Operations:** Filling into containers, labeling, sealing.

**Tracked:** Container type and count, packing materials used (with batch links),
net weight per unit, label details, operator, QC before and after packing,
label verification.

---

## 12. Stage 9 — External Extraction (Outsourced)

**What happens:** Pluviago dispatches packed biomass to a third-party extraction
partner who extracts the astaxanthin oil. This is not done in-house.

**Tracked:**
- Quantity dispatched (kg) and dispatch date
- Extraction partner name
- Expected return date
- Theoretical yield calculated from assay of starting material
- Actual extract quantity received back
- Actual assay of received extract
- Variance between theoretical and actual yield
- COA received from extraction partner
- QC incoming check: assay, visual inspection, COA validation

**Outcome:**
- Extract passes QC → proceed to repacking
- Extract fails QC → return to partner, log corrective action

---

## 13. Stage 10 — Repacking & Final Dispatch

Received extract is repacked into final commercial containers, labeled, and
dispatched to customers. Full batch traceability is maintained through the
final dispatch record.

---

## 14. Contamination Management

Contamination can occur at any cultivation stage. It is one of the highest-risk
events in algae production and requires a formal response workflow.

### Detection

- Visual observation (reddening, colour change, turbidity)
- Microscopy (foreign organisms visible)
- pH shift (unexpected change indicating competing organisms)

### Decision by stage

| Stage | Action on Contamination |
|-------|------------------------|
| Flask | Terminate batch. Do not scale. |
| 25 L | Corrective action if possible. Terminate if confirmed. |
| 275 L | Harvest immediately. Do not scale. |
| 925 L | Harvest immediately. Do not scale. |
| 6600 L | Harvest immediately. Process as contaminated batch. |

### What must be recorded

- Stage at which contamination was detected
- Detection method
- Contamination type (if identifiable)
- Operator(s) involved
- Mother batch ID (trace back to parent culture)
- Medium batch used (check if medium was the source)
- Corrective action taken
- Preventive action defined
- Follow-up verification scheduled

---

## 15. ERP Logical Hierarchy (Client Requirement)

The client (Roy) has specified that the ERP should model the following
organisational hierarchy to reflect cultivation as a living lineage system:

```
LEVEL 1 — Company
└── Pluviago Biotech Pvt Ltd

LEVEL 2 — Functional Domains
├── Procurement
├── Media Preparation
├── Cultivation
├── Downstream
├── Subcontract
├── Commercial
└── Quality

LEVEL 3 — Cultivation Lineage
├── Strain
├── Generation
├── Batch
├── Stage
└── Reactor

LEVEL 4 — Execution Layer
├── Work Order / Job Card
├── Quality Inspection
└── Stock Entry
```

---

## 16. Reporting Requirements

### What management needs to see

**Production**
- Current status of all active batches (which stage, how many days in stage)
- Batch genealogy — full chain from strain to product
- Stage-wise yield tracking across all batches
- Planned vs actual yield per batch
- Contamination frequency by stage and root cause
- Strain performance comparison

**Quality**
- QC pass/fail rates by stage
- Process QC trends (pH, PAR over time)
- Biological QC trends (cell count, OD, assay over batches)
- COA validation history — vendor compliance rate
- Rejected batches summary with reason

**Inventory**
- Chemical stock levels with expiry alerts (30 days, 7 days)
- Stock solution inventory — available volumes, expiry
- Medium batch inventory — available volumes
- Chemical consumption per production batch
- Full traceability: which vendor batch chemical went into which final product

**Cost & Finance**
- Batch-wise costing (raw material + labor + overhead)
- Cost per unit of finished product
- Yield loss cost analysis
- Outsourcing cost vs actual extract received

**Audit & Compliance**
- Full batch traceability report (chemical → stock solution → medium → reactor → harvest → product)
- All QC checkpoint records per batch
- COA validation records
- Contamination incident log
- User action audit trail (who did what, when)

---

## 17. Summary of Client Requirements (from Roy's email)

These are specific requirements stated by the client that must be honoured
exactly as specified:

### 1. Batch Numbering — Mother Culture Logic (Mandatory)

Every production batch must carry:
- **Mother Batch ID** — biological origin reference
- **Generation Number** — expansion step (1, 2, 3…)
- **Lineage Status** — Active / Returned / Archived

Required for contamination investigation, genealogy tracing, audit readiness,
and strain stability monitoring.

### 2. Return-to-Cultivation Loop

The back-propagation workflow (culture withdrawn from 6600 L or 275 L and
returned to Flask) must be implemented as **Material Transfer — not Manufacturing**.
Manufacturing treatment would distort yield calculations and genealogy records.

### 3. Medium Preparation as Formal Production Stages

The flow must include:
- **Stage 0A** — Stock Solution Preparation
- **Stage 0B** — Green Medium / Red Medium Preparation
- **Stage 0C** — Final Medium Formulation & Sterile Release

Without these stages, chemical traceability breaks, COA linkage is lost, and
audit risk increases.

### 4. Separation of Process QC and Biological QC

QC must be split into two distinct categories in the system:

**Process QC:** pH, PAR, automation logs  
**Biological QC:** Microscopy, cell size, contamination, assay

This separation improves dashboards, reporting clarity, and decision logic.

### 5. ERP Hierarchy

The ERP must model cultivation as a living lineage system — not as discrete
manufacturing lots. See Section 15 for the full hierarchy structure.

---

## 18. Complete Chemical Reference

All chemicals are purchased from vendors and tracked as individual inventory
batches with COA.

| Chemical | Formula | Grade | Primary Vendor(s) | Storage | Shelf Life |
|----------|---------|-------|------------------|---------|-----------|
| Calcium Chloride Dihydrate | CaCl₂·2H₂O | Extrapure AR 99.5% | SRL | RT | 5 yr |
| Magnesium Sulphate Heptahydrate | MgSO₄·7H₂O | Min 99% | Qualigens | RT | 5 yr |
| Sodium Chloride | NaCl | Extrapure AR 99.9% | SRL | RT | 5 yr |
| Manganese II Chloride | MnCl₂·4H₂O | 97–101% | Molychem | 2–8°C | 5 yr |
| Zinc Chloride | ZnCl₂ | Min 95% | Qualigens | RT | 5 yr |
| Cobalt Chloride | CoCl₂·6H₂O | 97–102% | HIMEDIA | RT | 3 yr |
| Sodium Molybdate | Na₂MoO₄·2H₂O | 98–103% | HIMEDIA | RT | 3 yr |
| Vitamin B12 | C₆₃H₈₈CoN₁₄O₁₄P | 96–102% | HIMEDIA | 2–8°C dark | 2–3 yr |
| Biotin | C₁₀H₁₆N₂O₃S | 99.5–100.5% | HIMEDIA | 2–8°C dark | 3 yr |
| Thiamine HCl | C₁₂H₁₇N₄OSCl·HCl | Min 98.5% | Qualigens | RT | 5 yr |
| Ferric Citrate | C₆H₅FeO₇·H₂O | Assay 18–22% | HIMEDIA | RT | 2 yr |
| Sodium Nitrate | NaNO₃ | >99% | Qualigens / Supelco | RT | 5 yr |
| Potassium Dihydrogen Phosphate | KH₂PO₄ | 99–101% | Qualigens | RT | 5 yr |
| Potassium Phosphate Dibasic | K₂HPO₄ | 98–102% | HIMEDIA | RT | 3 yr |
| Boric Acid | H₃BO₃ | Min 99.5% | SRL | RT | 5 yr |
| Zinc Sulphate | ZnSO₄·7H₂O | 99.5% | SRL / NICE | RT | 5 yr |
| Cupric Sulphate | CuSO₄·5H₂O | 99.5–100.5% | Qualigens | RT | 5 yr |
| Ammonium Molybdate | (NH₄)₆Mo₇O₂₄·4H₂O | Min 98% | Qualigens | RT | 5 yr |
| Calcium Nitrate | Ca(NO₃)₂·4H₂O | 98–99% | NICE / SRL | RT | 4 yr |
| Ferric Ammonium Citrate (FAC) | Variable | 16.5–22.5% Fe | NICE / Rankem / SRL | RT | 3 yr |
| EDTA Disodium | C₁₀H₁₄N₂Na₂O₈·2H₂O | Min 98% | Qualigens | RT | 5 yr |
| Sodium Carbonate | Na₂CO₃ | Min 99.5% | Qualigens | RT | 5 yr |
| Citric Acid | C₆H₈O₇ | Min 99.5% | Qualigens | RT | 4 yr |

---

## 19. QC Checkpoint Summary

| # | Stage | What Is Checked | Pass Criteria | Fail Action |
|---|-------|----------------|--------------|------------|
| QC1 | Green Medium pre-sterilization | Clarity | Clear, no precipitate | Discard, restart |
| QC2 | Green Medium final | pH, Clarity, Sterility | pH in spec, clear | Adjust pH or discard |
| QC3 | Red Medium pre-sterilization | Clarity | Clear, no precipitate | Discard, restart |
| QC4 | Red Medium final | pH, Clarity, Sterility | pH in spec, clear | Adjust pH or discard |
| QC5 | Final Medium | pH, Clarity, Sterility | pH in spec, clear, homogeneous | Do not use, re-prepare |
| QC6 | Flask (Seed Qualification) | PAR, pH, Microscopy, Cell Count, OD, Cell Size | All in spec | Terminate batch |
| QC7 | 25L / 275L / 925L / 6600L | PAR, pH, Cell Count, OD, Dry Weight, Contamination | No contamination, parameters in spec | Corrective action or harvest early |
| QC8 | Harvest | Dry Weight | Within spec | Investigate |
| QC9 | Post-drying | Assay % | Within spec | Do not pack, investigate |
| QC10 | External extract incoming | Assay, COA, Visual | Assay meets prediction, COA valid | Return to vendor |
