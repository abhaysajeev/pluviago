# Pluviago Cultivation Pipeline — Bug Report
**Generated:** 2026-05-20  
**Source:** e2e_cultivation_test.py run results

---

## CRITICAL — Code Bugs

### BUG-001: on_submit validation leaves document in inconsistent state
**Severity:** High  
**Affected files:**
- `harvest_batch.py` — `on_submit` line: `if self.qc_status != "Passed": frappe.throw(...)`
- `drying_batch.py` — `on_submit` line: `if self.qc_status != "Passed": frappe.throw(...)`
- `production_batch.py` — `on_submit` line: `if self.stage_decision == "Pending": frappe.throw(...)`

**Root cause:**  
In Frappe v15, `submit()` writes `docstatus=1` to the database *before* calling `on_submit()`. If `on_submit` throws, the exception propagates but the docstatus change is already committed. This leaves the document in an inconsistent state: `docstatus=1` (appears submitted) but with none of the on_submit side-effects applied (e.g., `status` still shows "Draft" instead of "Approved").

**Observed behaviour:**
- Trying to submit a Harvest Batch with `qc_status=Pending` → exception thrown by on_submit.
- HB remains in DB with `docstatus=1`, `status=None/Draft` (not "Approved").
- Any subsequent attempt to create a second HB for the same Production Batch hits the duplicate guard ("already has a submitted Harvest Batch") even though the first HB never completed on_submit.
- Any Drying Batch linked to this HB hits "Only Approved or Packed HBs can be dried" rather than the expected path.

**Fix required:**  
Move all submit-gate checks from `on_submit` to `before_submit`. Frappe runs `before_submit` *before* writing `docstatus=1`, so a throw there rolls back cleanly.

```python
# harvest_batch.py — CHANGE THIS:
def on_submit(self):
    if self.qc_status != "Passed":
        frappe.throw("Cannot submit: QC must be Passed")
    self.db_set("status", "Approved")

# TO THIS:
def before_submit(self):
    if self.qc_status != "Passed":
        frappe.throw("Cannot submit: QC must be Passed")

def on_submit(self):
    self.db_set("status", "Approved")
    ...
```

Apply the same pattern to `drying_batch.py` and `production_batch.py`.

---

### BUG-002: Harvest Batch validate rejects "Scaled Up" production batches
**Severity:** Medium  
**Affected file:** `harvest_batch.py` — `validate()` method  
**Status:** FIXED (2026-05-20)

**Root cause:**  
`validate()` only allowed `["Harvested", "Active", "Contaminated"]` as harvestable PB statuses. A PB that was previously submitted with "Scale Up" decision has `status = "Scaled Up"`. If the operator then changes their mind and creates a Harvest Batch for it, the validate would incorrectly block it.

**Fix applied:**
```python
# Before:
if pb.status not in ["Harvested", "Active", "Contaminated"]:
    frappe.throw("Linked Production Batch is not in a harvestable state.")
if pb.status == "Active" and pb.stage_decision not in ("Harvest",):

# After:
if pb.status not in ["Harvested", "Active", "Contaminated", "Scaled Up"]:
    frappe.throw("Linked Production Batch is not in a harvestable state.")
if pb.status in ("Active", "Scaled Up") and pb.stage_decision not in ("Harvest",):
```

---

## MINOR — Test Design Issues (not production code bugs)

### BUG-003: Test reuses same PB across multiple negative HB tests
**Severity:** Low (test only)  
**Affected file:** `e2e_cultivation_test.py` — `_test_harvest_drying()`

**Description:**  
The test creates `pb_qc_test` and `hb_no_qc` for the "HB submit blocked" negative case. Due to BUG-001, after the failed submit attempt, `hb_no_qc` ends up with `docstatus=1`. The subsequent attempt to create `hb2` for the same `pb_qc_test` then hits the duplicate guard rather than the intended qc_status gate.

**Fix:** Use a fresh PB for every negative test case. Never reuse a PB that had a failed submit attempt.

---

### BUG-004: Test crash stops execution after STEP 3
**Severity:** Medium (test only)  
**Affected file:** `e2e_cultivation_test.py` — `_test_harvest_drying()` line 389

**Description:**  
The crash at `hb2 = _make_hb(pb_qc_test.name, qc_pass=False)` raises an unhandled exception (duplicate HB guard fires because of BUG-001 + BUG-003). This crash is not caught by `expect_throw`, so it propagates and stops the entire test run — STEP 4 through STEP 11 never execute.

**Fix:** Apply BUG-001 fix first, then fix BUG-003. The crash disappears when the PB reuse is eliminated.

---

## Test Results Summary (current state)

| Step | Coverage | Status |
|------|----------|--------|
| STEP 1 — Strain + FMB setup | 4 checks | ✓ All pass |
| STEP 2 — Linear scale-up Flask→6600L | 28 checks | ✓ All pass |
| STEP 3 — Phase transition, Harvest, Drying | 16 checks | 15 pass / 1 fail (BUG-003) |
| STEP 4 — Contamination Incident lifecycle | — | ✗ Not reached (crash) |
| STEP 5 — Contamination + early harvest | — | ✗ Not reached |
| STEP 6 — Return-to-Cultivation | — | ✗ Not reached |
| STEP 7 — Batch Split | — | ✗ Not reached |
| STEP 8 — FMB volume exhaustion | — | ✗ Not reached |
| STEP 9 — Negative/validation guards | — | ✗ Not reached |
| STEP 10 — Inoculum pool tracking | — | ✗ Not reached |
| STEP 11 — Confirm Packing | — | ✗ Not reached |

**Root fix order:**
1. Fix BUG-001 (`before_submit` pattern in all 3 doctypes)
2. Fix BUG-003 (fresh PBs per negative test)
3. Re-run → full suite should complete
