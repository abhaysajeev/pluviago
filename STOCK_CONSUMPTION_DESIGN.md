
# Stock Consumption Design — Pluviago Biotech ERP

## Overview

This document describes how chemical stock consumption is tracked across the
preparation pipeline: Raw Material Batch → Stock Solution Batch → Green/Red Medium Batch.

---

## Core Principle

Chemicals are **physically consumed the moment preparation begins**, before QC.
The ERP reflects this reality:

- Stock is deducted when the operator clicks **Mark Preparation Complete**
- If QC **passes** → batch is submitted and released for downstream use
- If QC **fails** → batch is marked **Wasted** — stock stays deducted (chemicals are gone)
- Only a genuine data-entry error (batch never physically prepared) allows cancellation + reversal

---

## Workflow Per Preparation Stage

```
DRAFT
  │
  │  Fill ingredients / direct chemicals / sterilisation details
  │
  ▼
[Mark Preparation Complete]
  │  → Validates: UOM match, over-consumption check, RMB required
  │  → Deducts qty from each Raw Material Batch
  │  → Creates Stock Consumption Log (action = Consumed)
  │  → preparation_status → QC Pending
  │
  ▼
QC CHECK (fill pH, clarity, concentration etc.)
  │
  ├── QC FAIL
  │     [Mark as Wasted]
  │     → Creates Stock Consumption Log (action = Written Off / Loss)
  │     → preparation_status → Wasted
  │     → status → Wasted
  │     → NO stock reversal (chemicals are physically gone)
  │
  └── QC PASS
        [Submit]
        → preparation_status → Released
        → released_date + released_by recorded
        → available_volume = target_volume (Stock Solution only)
        → status → Approved
        → Batch available for next stage
```

### Cancel Rules

| preparation_status | Cancel allowed? | Stock effect |
|---|---|---|
| Draft | Yes | Reverse deduction + Reversed log entry |
| QC Pending | No — use Mark as Wasted | — |
| Released | No | — |
| Wasted | No | — |

---

## New Fields Added

### Raw Material Batch

| Field | Type | Description |
|---|---|---|
| `consumed_qty` | Float (read-only) | Total qty consumed across all submitted batches |
| `remaining_qty` | Float (read-only) | `received_qty - consumed_qty` |

Status auto-set to **Exhausted** when `remaining_qty <= 0`.

### Stock Solution Batch

| Field | Type | Description |
|---|---|---|
| `preparation_status` | Select | Draft / QC Pending / Released / Wasted |
| `released_date` | Date (read-only) | Date batch was approved and released |
| `released_by` | Link User (read-only) | Who released the batch |
| `available_volume` | Float (read-only) | Starts at `target_volume` on release; reduced as used in media |

### Green Medium Batch / Red Medium Batch

| Field | Type | Description |
|---|---|---|
| `preparation_status` | Select | Draft / QC Pending / Released / Wasted |

### Child Table Changes

- `stock_solution_ingredient.raw_material_batch` → now **required**
- `medium_direct_ingredient.raw_material_batch` → now **required**

---

## Stock Consumption Log

Standalone DocType. Read-only for all roles. Auto-created by the system.
Naming series: `SCL-.YYYY.-.####`

| Field | Description |
|---|---|
| `log_date` | Datetime of the event (auto) |
| `action` | Consumed / Written Off (Loss) / Reversed |
| `raw_material_batch` | Which RMB was affected |
| `material_name` | Chemical name (fetched) |
| `qty_change` | Negative = deduction, positive = reversal |
| `uom` | Unit of measure |
| `balance_after` | remaining_qty on RMB after this entry |
| `source_doctype` | Stock Solution Batch / Green Medium Batch / Red Medium Batch |
| `source_document` | Specific batch that triggered the event |
| `preparation_stage` | A1–A7 / Green Medium / Red Medium |
| `performed_by` | Session user |
| `remarks` | Free text (e.g. "QC failed — batch wasted") |

### Example Log for one production run

| Date | RMB | Material | Qty Change | Balance After | Action | Source |
|---|---|---|---|---|---|---|
| 2026-03-27 09:00 | RMB-001 | NaCl | -50 g | 450 g | Consumed | SSB-2026-0001 |
| 2026-03-27 09:00 | RMB-002 | MgSO4 | -20 g | 180 g | Consumed | SSB-2026-0001 |
| 2026-03-27 14:00 | RMB-001 | NaCl | 0 | 450 g | Written Off (Loss) | GMB-2026-0001 |
| 2026-03-28 10:00 | RMB-003 | CaCl2 | -30 g | 70 g | Consumed | GMB-2026-0002 |
| 2026-03-29 11:00 | RMB-001 | NaCl | +50 g | 500 g | Reversed | SSB-2026-0002 |

---

## Shared Utility: stock_utils.py

Location: `pluviago/pluviago_biotech/utils/stock_utils.py`

| Function | When called | Effect |
|---|---|---|
| `deduct_raw_materials(doc)` | Mark Preparation Complete | Validates + deducts qty + logs Consumed |
| `log_waste(doc)` | Mark as Wasted | Logs Written Off (Loss), no stock change |
| `reverse_raw_materials(doc)` | on_cancel (Draft only) | Reverses deduction + logs Reversed |

### Validations in deduct_raw_materials

1. `raw_material_batch` must be filled (required at form level too)
2. UOM on ingredient row must match `received_qty_uom` on the RMB
3. `qty` must not exceed `remaining_qty` on the RMB (hard block)
4. All rows validated before any write — no partial deductions

---

## UOM Policy

**Same UOM enforced.** If a chemical was received in `kg`, it must be consumed in `kg`.
Automatic conversion is not supported. The error message will state the mismatch clearly.

To avoid issues: ensure the ingredient row UOM matches what was entered on the RMB
at the time of receipt.

---

## Over-Consumption Policy

**Hard block.** If `qty` being consumed exceeds `remaining_qty` on the RMB, the system
throws an error and prevents the preparation from being marked complete. No partial
deductions are made.

---

## Files Modified / Created

| File | Change |
|---|---|
| `utils/__init__.py` | New — empty init |
| `utils/stock_utils.py` | New — shared deduction, waste, reversal, log logic |
| `doctype/stock_consumption_log/stock_consumption_log.json` | New DocType |
| `doctype/stock_consumption_log/stock_consumption_log.py` | New controller |
| `doctype/raw_material_batch/raw_material_batch.json` | Added consumed_qty, remaining_qty |
| `doctype/stock_solution_ingredient/stock_solution_ingredient.json` | raw_material_batch now required |
| `doctype/medium_direct_ingredient/medium_direct_ingredient.json` | raw_material_batch now required |
| `doctype/stock_solution_batch/stock_solution_batch.json` | Added preparation_status, released_date, released_by, available_volume, Wasted status |
| `doctype/stock_solution_batch/stock_solution_batch.py` | Added mark_preparation_complete, mark_wasted, revised on_submit/on_cancel |
| `doctype/green_medium_batch/green_medium_batch.json` | Added preparation_status, Wasted status |
| `doctype/green_medium_batch/green_medium_batch.py` | Added mark_preparation_complete, mark_wasted, revised on_submit/on_cancel |
| `doctype/red_medium_batch/red_medium_batch.json` | Added preparation_status, Wasted status |
| `doctype/red_medium_batch/red_medium_batch.py` | Added mark_preparation_complete, mark_wasted, revised on_submit/on_cancel |

---

## Test Scenarios

1. **Happy path — SSB released**
   - Create RMB (received_qty=100g). Submit.
   - Create SSB, add ingredient (same RMB, qty=30g). Click Mark Preparation Complete.
   - Verify: RMB consumed_qty=30, remaining_qty=70. SCL entry: action=Consumed, qty_change=-30.
   - Set qc_status=Passed. Submit.
   - Verify: preparation_status=Released, available_volume=target_volume.

2. **QC failure — batch wasted**
   - Repeat above up to Mark Preparation Complete.
   - Click Mark as Wasted.
   - Verify: preparation_status=Wasted, status=Wasted.
   - Verify: SCL entry action=Written Off (Loss).
   - Verify: RMB remaining_qty still 70 (no reversal).

3. **Over-consumption blocked**
   - Create SSB with qty=80g (only 70 remaining on RMB).
   - Click Mark Preparation Complete → expect hard block error.

4. **Data error cancellation**
   - Create SSB. Do NOT click Mark Preparation Complete (preparation_status=Draft).
   - Cancel → verify: SCL Reversed entry, consumed_qty decrements, remaining_qty restored.
   - Create SSB. Click Mark Preparation Complete. Try to cancel → expect hard block.

5. **UOM mismatch blocked**
   - RMB received in kg. Ingredient row UOM = g. Click Mark Preparation Complete → block.

6. **Green/Red Medium — same flow applies**
   - Same test sequence using direct_chemicals child table instead of ingredients.

---

*Document version: 2026-03-27*
*Covers: Task 1.1 — Chemical Stock Deduction*
