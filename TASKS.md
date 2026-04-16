# Pluviago ERP — Implementation Task List

All items below are NOT yet implemented. Each task is described in enough detail to
analyse, discuss, and implement independently. Tasks are grouped into phases in
recommended implementation order.

---

## PHASE 1 — Core Data Integrity (Must have before anything else)

These tasks fix gaps in the existing data model. Everything downstream depends on them.

---

### TASK 1.1 — Chemical Stock Deduction (consumed_qty / remaining_qty)

**What is missing:**
When a Stock Solution Batch is submitted, the quantity of each chemical used is recorded
in the `ingredients` child table but the Raw Material Batch `received_qty` is never
reduced. There is no running balance. A batch can be over-consumed with no warning.

**Fields to add to Raw Material Batch:**
- `consumed_qty` (Float, read-only) — sum of all ingredient rows across all submitted
  Stock Solution Batches that reference this Raw Material Batch
- `remaining_qty` (Float, read-only) — `received_qty - consumed_qty`

**Logic to add:**
- On `Stock Solution Batch.on_submit`: loop through `self.ingredients`, for each row
  that has a `raw_material_batch` link, add `row.qty` to that RMB's `consumed_qty`,
  recalculate `remaining_qty`, and if `remaining_qty <= 0` set `status = "Exhausted"`.
- On `Stock Solution Batch.on_cancel`: reverse the deduction (subtract back).

**Also applies to Medium Direct Ingredients:**
- Green Medium Batch and Red Medium Batch have a `direct_chemicals` child table
  (Medium Direct Ingredient) which also links to `raw_material_batch` and records qty.
- Same deduction logic must run on Green/Red Medium Batch submit/cancel.

**Files to modify:**
- `doctype/raw_material_batch/raw_material_batch.json` — add fields
- `doctype/stock_solution_batch/stock_solution_batch.py` — add deduction on submit/cancel
- `doctype/green_medium_batch/green_medium_batch.py` — add deduction on submit/cancel
- `doctype/red_medium_batch/red_medium_batch.py` — add deduction on submit/cancel

**Discussion points:**
- Do we deduct when the batch is saved (draft) or only on submit?
- If a Stock Solution Batch is cancelled, do we reverse the deduction fully?
- Should over-consumption (remaining_qty < 0) be a hard block or a warning?

---

### TASK 1.2 — Stock Solution Volume Tracking (remaining_volume)

**What is missing:**
A Stock Solution Batch records a `target_volume` (e.g. 1 L of A1). When that solution is
used in a Green or Red Medium Batch, the volume consumed is not deducted. There is no
way to know how much of a stock solution remains if it is partially used across multiple
medium batches.

**Fields to add to Stock Solution Batch:**
- `volume_used` (Float, read-only) — total volume consumed across all medium batches
- `remaining_volume` (Float, read-only) — `target_volume - volume_used`

**Logic to add:**
- On `Green Medium Batch.on_submit`: for each stock solution link (a1, a2, a3) and the
  volume recorded as used, add to that Stock Solution Batch's `volume_used`.
- Same for `Red Medium Batch.on_submit` (a4, a5, a6, a7, a5m).
- Reverse on cancel.

**Files to modify:**
- `doctype/stock_solution_batch/stock_solution_batch.json` — add fields
- `doctype/green_medium_batch/green_medium_batch.py`
- `doctype/red_medium_batch/red_medium_batch.py`

**Discussion points:**
- Currently Green/Red Medium Batch link to stock solutions but do NOT record how much
  volume of each stock solution was used. A `volume_used` field needs to be added to
  each stock solution link section on Green/Red Medium Batch first.
- Should the system block using a stock solution that has zero remaining volume?

---

### TASK 1.3 — Lineage Status Field on Production Batch

**What is missing:**
Client's email explicitly requested a `Lineage Status` field with values:
Active / Returned / Archived.

Current `status` field options: Active, Harvested, Disposed, Scaled Up, Contaminated.
"Returned" (used when a culture is withdrawn and sent back to Flask via
Return-to-Cultivation loop) and "Archived" do not exist.

**Change required:**
- Add `lineage_status` as a separate Select field on Production Batch
  (distinct from `status` which tracks operational state).
- Options: Active / Returned / Archived
- Default: Active
- Set to "Returned" when the Return-to-Cultivation action is triggered (Task 2.1).
- Set to "Archived" when a batch is older than X generations or manually closed.

**Files to modify:**
- `doctype/production_batch/production_batch.json` — add field
- `doctype/production_batch/production_batch.py` — set value in relevant hooks

**Discussion points:**
- Should Lineage Status be manual or system-controlled?
- What triggers "Archived" — age, generation number threshold, or manual?
- Is this a separate field from `status` or should we extend the existing status options?

---

## PHASE 2 — Biological Workflow (Client's specific requests from email)

---

### TASK 2.1 — Return-to-Cultivation Loop (Back-Propagation Workflow)

**What is missing:**
The entire return-to-cultivation workflow. Client described this flow:

```
6600L or 275L batch
    ↓ withdraw a volume of culture
    ↓ dilute with fresh medium
    ↓ back to Flask (new Production Batch, child of source)
```

This must be tracked as a Material Transfer, NOT manufacturing.

**What to build:**

1. A custom button "Return to Flask" on Production Batch form, visible only when
   `current_stage` is "275L PBR" or "6600L PBR".

2. Clicking it opens a dialog (or a linked form) capturing:
   - `withdrawal_volume` (Float) — how much culture was withdrawn (Litres)
   - `dilution_medium_batch` (Link to Final Medium Batch) — medium used for dilution
   - `dilution_volume` (Float) — volume of medium added
   - `return_date` (Date)
   - `returned_by` (User)
   - `reason` (Text)

3. On confirm, the system:
   - Creates a new Production Batch record with:
     - `parent_batch` = source batch name
     - `current_stage` = "Flask"
     - `strain` = inherited from source
     - `generation_number` = source generation_number + 1
     - `lineage_status` = "Active"
     - `inoculation_date` = return_date
   - Sets `lineage_status = "Returned"` on the source batch (source is NOT harvested or
     disposed — it continues running).
   - Creates a log entry (could be a child table row or a linked Return Event record).

4. The source batch continues as active — both the source and the new Flask batch are
   alive simultaneously (this is the key difference from normal scale-up).

**New DocType to consider:**
- `Cultivation Return Event` — logs each return-to-cultivation action with all fields
  above, linked to both source and child batch. This keeps the Production Batch clean.

**Files to create/modify:**
- New: `doctype/cultivation_return_event/` (optional but cleaner)
- `doctype/production_batch/production_batch.js` — add button and dialog
- `doctype/production_batch/production_batch.py` — add `create_return_batch()` method

**Discussion points:**
- Should the source batch (275L or 6600L) remain "Active" after return, or get a
  "Partially Returned" status?
- Can multiple return events happen from the same source batch (e.g. return to Flask
  twice from the same 6600L batch)?
- Does the returned Flask batch get a new batch number series or inherit from parent?
- Is a separate DocType for the Return Event needed or is a child table enough?

---

### TASK 2.2 — Batch Splitting (One Parent → Multiple Children)

**What is missing:**
Currently `parent_batch` is a single Link field — one parent per child. This models
a linear chain. The client's process can involve one Flask culture inoculating more
than one 25L PBR simultaneously (parallel runs from the same source).

**What to build:**
- Allow a Production Batch to have multiple child batches at the same stage.
- The `get_lineage()` method already walks upward — it needs a companion
  `get_children()` method that walks downward.
- A "Split Batch" button on Production Batch that creates N sibling child batches,
  all with `parent_batch` = current batch, at the next stage.

**Files to modify:**
- `doctype/production_batch/production_batch.py` — add `get_children()` and
  `create_split_batches()` methods
- `doctype/production_batch/production_batch.js` — add Split Batch button

**Discussion points:**
- Is splitting actually used in current operations or is it a future requirement?
- When splitting, does the volume divide equally across children or is it entered
  per child?
- Does the genealogy report need to show a tree (branching) rather than a list?

---

## PHASE 3 — QC Improvements

---

### TASK 3.1 — Separate Process QC and Biological QC on Production Batch

**What is missing:**
The `Production Batch QC` child table currently has all QC parameters in one mixed row:
PAR, pH, OD, cell_count, cell_size, dry_weight, microscopy_result, contamination_detected.

Client requested these be split into two categories for clearer reporting:

**Process QC:** pH, PAR, automation logs
**Biological QC:** Microscopy, cell size, contamination, assay

**Options to implement (pick one during discussion):**

Option A — Add `qc_type` Select field (Process QC / Biological QC) to the existing
`Production Batch QC` child table. Rows are filtered by type in reports.
- Minimal change. One child table, one new field.

Option B — Split into two child tables:
- `Production Process QC` (pH, PAR, OD, automation notes)
- `Production Biological QC` (microscopy, cell size, cell count, contamination, assay)
- More structured but requires schema change and two sections on the form.

**Files to modify (Option A):**
- `doctype/production_batch_qc/production_batch_qc.json` — add `qc_type` field
- `report/qc_compliance_report/qc_compliance_report.py` — filter by type

**Files to modify (Option B):**
- New: `doctype/production_process_qc/`
- New: `doctype/production_biological_qc/`
- `doctype/production_batch/production_batch.json` — replace old child table with two

**Discussion points:**
- Option A or Option B?
- Should existing QC entries be migrated if Option B is chosen?
- Does the QC Compliance Report need separate sections for Process vs Biological?

---

### TASK 3.2 — QC Checkpoint Failure Handling (Corrective Action Flow)

**What is missing:**
When a QC checkpoint fails (e.g. Checkpoint 1 on Green Medium — clarity fail), the
system currently has no structured response. The user is just blocked from progressing.
Client's email mentions corrective action for non-contamination failures.

**What to build:**
- When `qc_checkpoint_X_clarity = "Fail"` or `overall_qc_status = "Failed"`, allow
  the user to log a corrective action:
  - `corrective_action_taken` (Text)
  - `corrective_action_by` (User)
  - `corrective_action_date` (Date)
  - `re_qc_required` (Check) — triggers a new QC entry
- After corrective action, allow re-testing. If re-test passes, batch can proceed.
- If batch cannot be recovered, user sets status to "Rejected" with reason.

**Files to modify:**
- `doctype/green_medium_batch/green_medium_batch.json` — add corrective action fields
- `doctype/red_medium_batch/red_medium_batch.json` — same
- `doctype/final_medium_batch/final_medium_batch.json` — same

**Discussion points:**
- Should corrective action be a child table (multiple attempts) or fixed fields
  (one corrective action per batch)?
- Is re-testing allowed more than once?
- Should a failed-then-recovered batch be flagged differently from a clean-pass batch
  for audit purposes?

---

### TASK 3.3 — Out-of-Specification (OOS) Investigation Workflow

**What is missing:**
When a QC result fails, there is no formal OOS investigation record. For regulated
environments, a failed result must trigger an investigation that is documented, reviewed,
and formally closed before the batch is rejected or released.

**What to build:**
- New DocType: `OOS Investigation`
  - `linked_doctype` (Select — which batch type triggered it)
  - `linked_batch` (Dynamic Link)
  - `parameter_failed` (Data)
  - `failed_value` (Data)
  - `expected_range` (Data)
  - `investigation_by` (User)
  - `root_cause` (Text)
  - `conclusion` (Select: Lab Error / Process Deviation / True OOS)
  - `disposition` (Select: Retest / Reject / Release with Deviation)
  - `closed_by`, `closed_date`
  - `status` (Open / Under Investigation / Closed)

**Discussion points:**
- Is OOS investigation mandatory (blocks batch rejection until closed) or optional?
- Which QC failures trigger it — all failures or only critical parameter failures?
- Is this in scope for Phase 1 or a later phase?

---

## PHASE 4 — Alerts & Notifications

---

### TASK 4.1 — Expiry Alert on Raw Material Batch

**What is missing:**
The business flow PDF states: "orange alert for batches expiring within 30 days, red
alert for already-expired batches." The scheduler task only checks pending QC — no
expiry alert exists anywhere.

**What to build:**

1. Visual indicator on the Raw Material Batch form:
   - Red banner if `expiry_date < today`
   - Orange banner if `expiry_date` is within 30 days
   - Implemented via a client script (`raw_material_batch.js`) checking on form load.

2. List view color coding:
   - Add `indicator_color` logic in the list view so expired batches show red,
     near-expiry show orange.

3. Daily scheduler task (extend existing `tasks.py`):
   - Find all non-Exhausted Raw Material Batches expiring within 30 days.
   - Send a notification/email to Store Keeper and QC Manager roles.

**Files to modify/create:**
- New: `doctype/raw_material_batch/raw_material_batch.js`
- `pluviago_biotech/tasks.py` — extend `daily()` function
- `doctype/raw_material_batch/raw_material_batch.json` — list view indicator field

**Discussion points:**
- 30-day threshold — is this correct for all chemicals or does it vary?
- Who receives the daily expiry alert email?
- Should expired batches be auto-blocked from use in stock solutions (currently only
  QC-approved check exists, not expiry check on the ingredient validation)?

---

### TASK 4.2 — Low Stock / Reorder Alert

**What is missing:**
No minimum stock level or reorder point tracking exists for raw materials.

**What to build:**
- Add `min_stock_qty` (Float) and `reorder_qty` (Float) fields to Raw Material Batch
  (or better — to an Item-level configuration so it applies across all batches of
  that chemical).
- Daily scheduler: if total `remaining_qty` across all active batches of an item falls
  below `min_stock_qty`, send alert to Store Keeper and Procurement Officer.

**Discussion points:**
- Should the minimum stock level be set per chemical item or per individual batch?
- Is this in scope for Phase 1?

---

### TASK 4.3 — Pending QC Alert (extend existing scheduler)

**What is partially implemented:**
`tasks.py` already has a `check_pending_qc()` function that alerts on Production Batches
with `stage_decision = "Pending"` for 2+ days. It sends a realtime message to
Administrator only.

**What to improve:**
- Extend to also alert on:
  - Raw Material Batches with `qc_status = "Pending"` for more than X days
  - Stock Solution Batches with `qc_status = "Pending"` for more than X days
- Send to the correct role (QC Manager) not just Administrator.
- Send via email in addition to realtime notification.

**Files to modify:**
- `pluviago_biotech/tasks.py`

---

## PHASE 5 — UI / Navigation / Workspace

---

### TASK 5.1 — Production Pipeline Workspace (Stage 0A to 6600L)

**What is missing:**
There is no unified view showing the full production pipeline as connected stages.
Users navigate to each DocType separately. The client wants the hierarchy:

```
Stage 0A (Stock Solution) → Stage 0B (Green + Red Medium) →
Stage 0C (Final Medium) → Flask → 25L → 275L → 925L → 6600L → Harvest → Extract
```

**What to build:**
- A Frappe Workspace page for "Pluviago Biotech" showing:
  - Quick links to each DocType in pipeline order
  - Count badges: how many batches are active at each stage
  - Status summary: how many passed QC, how many pending, how many failed
- This is a workspace JSON configuration — no Python needed.

**Files to create:**
- `workspace/pluviago_biotech/pluviago_biotech.json`

**Discussion points:**
- Should this be a static workspace with links, or a dynamic dashboard with live counts?
- Dynamic counts require a custom page or dashboard chart configuration.

---

### TASK 5.2 — Functional Domain Menu Structure

**What is missing:**
Client proposed organising the ERP into functional domains:
Procurement / Media Preparation / Cultivation / Downstream / Quality

Currently all DocTypes are under one flat "Pluviago Biotech" module menu.

**What to build:**
Reorganise the workspace/module menu into sections:

- **Procurement:** Raw Material Batch, (Purchase Order link)
- **Media Preparation:** Stock Solution Batch, Green Medium Batch, Red Medium Batch,
  Final Medium Batch
- **Cultivation:** Pluviago Strain, Production Batch, Contamination Incident,
  Return Event (Task 2.1)
- **Downstream:** Harvest Batch, Extraction Batch
- **Quality:** QC Parameter Spec, OOS Investigation (Task 3.3), Reports

**Files to modify:**
- Workspace JSON or module configuration

---

## PHASE 6 — Compliance & Documentation

---

### TASK 6.1 — Batch Manufacturing Record (BMR) Print Format

**What is missing:**
No print format exists for any DocType. Client's SRS requires a BMR document that
can be printed or exported to PDF at the end of each production run.

**What to build:**
- A Print Format for Production Batch that includes:
  - Batch details (number, strain, generation, dates)
  - Linked Final Medium Batch details
  - All QC readings (child table)
  - Stage decisions and dates
  - Contamination incidents (if any)
  - Harvest Batch details if harvested
  - Signature fields (Production Manager, QC Manager)

**Files to create:**
- `print_format/production_batch_bmr/production_batch_bmr.json`
  (or configured via Frappe UI)

**Discussion points:**
- Should the BMR be a single document covering the full Flask-to-Harvest journey,
  or one document per stage?
- Is a PDF export via the standard Frappe print button enough, or does it need a
  custom formatted report?

---

### TASK 6.2 — SOP Document Linkage

**What is missing:**
No SOP attachment or reference field exists on any DocType (except `sop_reference`
Data field on Stock Solution Batch and Final Medium Batch — these are plain text,
not file attachments).

**What to build:**
- Add `sop_attachment` (Attach) field to:
  - Stock Solution Batch
  - Green Medium Batch
  - Red Medium Batch
  - Final Medium Batch
  - Production Batch
- Or create a central `SOP Master` DocType where SOPs are stored and linked by
  doctype/stage.

**Discussion points:**
- Central SOP Master vs per-batch attachment — which is preferred?
- Should the system enforce that an SOP is linked before submission?

---

### TASK 6.3 — Field-Level Role Permissions

**What is missing:**
Seven roles are defined (QA Head, QC Manager, Production Manager, etc.) but no
field-level or DocType-level permissions are configured. All authenticated users
can currently do everything.

**What to build:**
For each DocType, define which roles can:
- Read
- Create
- Write
- Submit
- Cancel
- Delete

Example rules:
- Lab Technician: Create/Write on Stock Solution Batch, Green/Red/Final Medium Batch.
  Cannot Submit.
- QC Analyst: Can Submit medium batches and harvest batches. Cannot delete.
- Production Manager: Full access to Production Batch. Can submit/cancel.
- Store Keeper: Create/Write/Read on Raw Material Batch only.
- Pluviago Admin: Full access everywhere.

**Files to modify:**
- Each DocType's `.json` file — `permissions` array
- Or configured via Frappe role permission manager UI and exported as fixtures.

**Discussion points:**
- Full permissions matrix needs to be defined by client before this can be implemented.
  This feeds directly into the client questions PDF (Question K2, K3).

---

## PHASE 7 — Reporting Enhancements

---

### TASK 7.1 — Reactor Yield Report

**What is missing:**
The current `Production Summary` report shows harvest-level yield. A dedicated
Reactor Yield Report showing yield trends per strain, per generation, per stage
does not exist.

**What to build:**
- New report: `reactor_yield_report`
- Columns: strain, generation_number, batch_number, current_stage, inoculation_date,
  harvest_date, harvested_volume, actual_dry_weight, yield_percentage, qc_status
- Filters: strain, from_date, to_date, stage, status
- Aggregations: average yield per strain, per generation range

**Files to create:**
- `report/reactor_yield_report/reactor_yield_report.py`
- `report/reactor_yield_report/reactor_yield_report.json`

---

### TASK 7.2 — QC Compliance Report — Add Production Batch QC Readings

**What is partially implemented:**
The QC Compliance Report covers Stock Solution, Green/Red/Final Medium, and Harvest
Batch. It does NOT include Production Batch QC readings (the per-stage PAR, pH,
microscopy readings recorded in the `Production Batch QC` child table).

**What to build:**
- Add a query to `qc_compliance_report.py` that joins `Production Batch` with
  `Production Batch QC` and returns each QC reading as a row.
- Filter by date, stage, result (Pass/Fail).

**Files to modify:**
- `report/qc_compliance_report/qc_compliance_report.py`

---

### TASK 7.3 — Inventory Dashboard / Stock Level Report

**What is missing:**
No report or dashboard shows current chemical stock levels, remaining quantities,
or expiry status across all Raw Material Batches.

**What to build:**
- New report: `chemical_inventory_status`
- Columns: batch_number, material_name, supplier, received_qty, consumed_qty,
  remaining_qty, expiry_date, days_to_expiry, status
- Colour indicators: red for expired, orange for expiring within 30 days,
  green for healthy stock
- Filters: material_name, supplier, status, expiry range

**Files to create:**
- `report/chemical_inventory_status/chemical_inventory_status.py`
- `report/chemical_inventory_status/chemical_inventory_status.json`

**Dependency:** Requires Task 1.1 (consumed_qty / remaining_qty) to be built first.

---

## PHASE 8 — Future / Optional (Discuss before committing)

---

### TASK 8.1 — HRMS (Employee, Training, Shift Tracking)

**Scope:** Track lab technicians, production operators, QC analysts, training records.

**Discussion:** Client SRS mentions this. Frappe HR module exists and can be enabled.
But this is a large separate module. Recommend deferring to Phase 2 post go-live.

---

### TASK 8.2 — Barcode / QR Code Scanning

**Scope:** Scan a physical chemical container to link to Raw Material Batch.
Scan a reactor label to open the Production Batch record.

**Discussion:** Requires physical label printing setup and a barcode scanner or
mobile camera integration. Frappe has barcode field support. Scope with client.

---

### TASK 8.3 — Mobile Access

**Scope:** Operators enter QC readings on a tablet at the reactor floor.

**Discussion:** Frappe/ERPNext is responsive and works on mobile browsers out of the box.
No custom development needed unless a simplified mobile-specific UI is requested.

---

### TASK 8.4 — SCADA / Instrument Integration

**Scope:** Auto-import pH, PAR, cell count readings from bioreactor control systems
or laboratory instruments directly into Production Batch QC records.

**Discussion:** Requires API access to the instruments. Large scope. Defer to later phase.

---

### TASK 8.5 — Email Notification System

**Scope:** Automated emails for: QC pending alerts, expiry warnings, batch approvals,
contamination incidents, stage decisions.

**Discussion:** Frappe has built-in email alert configuration (Notification DocType).
Most of these can be configured via UI without coding. Low effort once email server
is configured. Can be done in parallel with other tasks.

---

## Summary — Task Count by Phase

| Phase | Tasks | Priority |
|---|---|---|
| Phase 1 — Core Data Integrity | 3 tasks | Critical |
| Phase 2 — Biological Workflow | 2 tasks | Critical (client email) |
| Phase 3 — QC Improvements | 3 tasks | High |
| Phase 4 — Alerts & Notifications | 3 tasks | High |
| Phase 5 — UI / Workspace | 2 tasks | Medium |
| Phase 6 — Compliance & Docs | 3 tasks | Medium |
| Phase 7 — Reporting | 3 tasks | Medium |
| Phase 8 — Future / Optional | 5 tasks | Low / Deferred |
| **Total** | **24 tasks** | |

---

## Dependencies Map

```
Task 1.1 (stock deduction)
    └── Task 7.3 (inventory report) depends on this

Task 1.3 (lineage_status field)
    └── Task 2.1 (return-to-cultivation) depends on this

Task 2.1 (return-to-cultivation)
    └── Task 2.2 (batch splitting) is related

Task 3.1 (QC split Process vs Biological)
    └── Task 7.2 (QC compliance report enhancement) depends on this

Task 6.3 (role permissions)
    └── Needs client to answer K2/K3 in client questions PDF first
```

---

*Last updated: 2026-03-27*
*Status: Analysis complete — no coding started*
