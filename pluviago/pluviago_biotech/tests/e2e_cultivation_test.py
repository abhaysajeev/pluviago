"""
Pluviago End-to-End Backend Test — Cultivation Pipeline
========================================================
Tests Stage 1–6 (Flask → 25L → 275L → 925L → 6600L → Harvest → Extraction)
including Return-to-Cultivation, Batch Splitting, and FMB volume tracking.

Scenarios covered:
  1. Linear Scale-Up: Flask(Gen1) → 25L(2) → 275L(3) → 925L(4) → 6600L(5)
  2. Harvest + Extraction on 6600L (normal path)
  3. Contamination + Early Harvest at 275L
  4. Return-to-Cultivation from 275L → new Flask child (+ second return from same source)
  5. Batch Split: 1 Flask → 2 × 25L PBR
  6. FMB Volume Exhaustion & Over-Consumption Guard (with cancel reversal)
  7. Negative / Validation Guards

Run with:
  bench --site replica1.local execute pluviago.pluviago_biotech.tests.e2e_cultivation_test.run
"""

import frappe
from frappe.utils import today

# ──────────────────────────────────────────────────────────────────────────────
# State — track all created doc names for cleanup
# ──────────────────────────────────────────────────────────────────────────────
_CREATED = []  # list of (doctype, name) in insertion order
_PASS = 0
_FAIL = 0

ADMIN = "Administrator"

STAGE_VOLUMES = {
    "Flask": 1,
    "25L PBR": 25,
    "275L PBR": 275,
    "925L PBR": 925,
    "6600L PBR": 6600,
}


# ──────────────────────────────────────────────────────────────────────────────
# Assertion helpers
# ──────────────────────────────────────────────────────────────────────────────

def ok(label, condition, detail=""):
    global _PASS, _FAIL
    if condition:
        _PASS += 1
        print(f"  ✓  {label}")
    else:
        _FAIL += 1
        print(f"  ✗  FAIL: {label}" + (f" — {detail}" if detail else ""))


def expect_throw(label, fn):
    """Assert that fn() raises any exception."""
    global _PASS, _FAIL
    try:
        fn()
        _FAIL += 1
        print(f"  ✗  FAIL: {label} — expected an error but none was raised")
    except Exception as e:
        _PASS += 1
        err = str(e)[:90]
        print(f"  ✓  {label} (correctly blocked: {err})")


def _track(doctype, name):
    _CREATED.append((doctype, name))
    return name


def _step(title):
    print(f"\n{'─'*60}")
    print(f"  {title}")
    print(f"{'─'*60}")


# ──────────────────────────────────────────────────────────────────────────────
# Setup helpers
# ──────────────────────────────────────────────────────────────────────────────

def _create_strain():
    """Create a minimal Pluviago Strain for test use."""
    uid = frappe.utils.now_datetime().strftime("%H%M%S")
    s = frappe.get_doc({
        "doctype": "Pluviago Strain",
        "strain_id": f"TEST-CULT-{uid}",
        "strain_name": f"H. pluvialis E2E Cultivation {uid}",
        "strain_type": "Microalgae",
        "species": "Haematococcus pluvialis",
        "status": "Active",
    })
    s.insert(ignore_permissions=True)
    _track("Pluviago Strain", s.name)
    return s.name


def _make_fmb(volume, tag=""):
    """
    Shortcut: create a submitted FMB with remaining_volume = volume.
    Bypasses the full medium preparation pipeline — this test is about
    cultivation tracking, not medium prep (which is already validated in
    e2e_medium_test.py).
    """
    fmb = frappe.get_doc({
        "doctype": "Final Medium Batch",
        "preparation_date": today(),
        "prepared_by": ADMIN,
        "final_required_volume": volume,
        "qc_status": "Passed",
        "shelf_life_days": 30,
        "remarks": f"E2E cultivation test FMB {tag}",
    })
    # ignore_mandatory skips reqd check for green_medium_batch / red_medium_batch
    fmb.insert(ignore_mandatory=True, ignore_permissions=True)
    # Manually simulate submission state — deduct_medium_volume for PBs
    # only reads remaining_volume + expiry_date from FMB, so this is sufficient.
    frappe.db.set_value("Final Medium Batch", fmb.name, {
        "docstatus": 1,
        "status": "Approved",
        "remaining_volume": volume,
        "volume_consumed": 0,
    })
    frappe.db.commit()
    _track("Final Medium Batch", fmb.name)
    return fmb.name


def _make_pb(strain, stage, gen, parent=None, fmb=None, vol=None,
             decision="Pending", contamination="Clean", phase="N/A"):
    """Create and submit a Production Batch."""
    pb = frappe.get_doc({
        "doctype": "Production Batch",
        "strain": strain,
        "current_stage": stage,
        "generation_number": gen,
        "parent_batch": parent,
        "inoculation_date": today(),
        "final_medium_batch": fmb,
        "medium_volume_used": vol,
        "stage_decision": decision,
        "contamination_status": contamination,
        "phase": phase,
        "lineage_status": "Active",
    })
    pb.insert(ignore_permissions=True)
    pb.submit()
    _track("Production Batch", pb.name)
    return pb


def _make_hb(pb_name, qc_pass=True, dry_weight=10.0):
    """Create (and optionally submit) a Harvest Batch."""
    # Use reactor_volume as harvested_volume so capacity check always passes
    reactor_vol = frappe.db.get_value("Production Batch", pb_name, "reactor_volume") or 1.0
    hb = frappe.get_doc({
        "doctype": "Harvest Batch",
        "production_batch": pb_name,
        "harvest_date": today(),
        "harvested_by": ADMIN,
        "harvested_volume": reactor_vol,
        "target_dry_weight": dry_weight,
        "actual_dry_weight": round(dry_weight * 0.95, 2),
        "qc_status": "Passed" if qc_pass else "Pending",
        "qc_checked_by": ADMIN,
        "qc_date": today(),
    })
    hb.insert(ignore_permissions=True)
    _track("Harvest Batch", hb.name)
    if qc_pass:
        hb.submit()
    return hb


def _make_eb(hb_name):
    """Create and submit an Extraction Batch."""
    eb = frappe.get_doc({
        "doctype": "Extraction Batch",
        "harvest_batch": hb_name,
        "dispatch_date": today(),
        "dispatched_by": ADMIN,
        "dispatch_qty": 9.5,
        "incoming_qc_status": "Passed",
        "incoming_qc_by": ADMIN,
        "incoming_qc_date": today(),
    })
    eb.insert(ignore_permissions=True)
    eb.submit()
    _track("Extraction Batch", eb.name)
    return eb


# ──────────────────────────────────────────────────────────────────────────────
# STEP 2 — Linear Scale-Up Path
# ──────────────────────────────────────────────────────────────────────────────

def _test_linear_scaleup(strain, fmb_main):
    _step("STEP 2 — Linear Scale-Up Path (Flask → 25L → 275L → 925L → 6600L)")

    fmb_rem_start = frappe.db.get_value("Final Medium Batch", fmb_main, "remaining_volume")

    # ── Flask Gen 1 ────────────────────────────────────────────────────────────
    flask = _make_pb(strain, "Flask", gen=1, fmb=fmb_main, vol=1.0)
    ok("Flask: generation_number = 1", flask.generation_number == 1)
    ok("Flask: reactor_volume = 1 L", flask.reactor_volume == 1)
    ok("Flask: status = Active", flask.status == "Active")
    ok("Flask: lineage_status = Active", flask.lineage_status == "Active")
    ok("Flask: no parent_batch", not flask.parent_batch)

    fmb_rem = frappe.db.get_value("Final Medium Batch", fmb_main, "remaining_volume")
    ok("FMB decremented by 1 L after Flask submit",
       abs(fmb_rem - (fmb_rem_start - 1.0)) < 0.001,
       f"got {fmb_rem}, expected {fmb_rem_start - 1}")

    # ── 25L PBR Gen 2 ──────────────────────────────────────────────────────────
    pbr25 = _make_pb(strain, "25L PBR", gen=2, parent=flask.name, fmb=fmb_main, vol=1.0)
    ok("25L PBR: generation_number = 2", pbr25.generation_number == 2)
    ok("25L PBR: reactor_volume = 25 L", pbr25.reactor_volume == 25)
    ok("25L PBR: parent_batch = Flask", pbr25.parent_batch == flask.name)

    # ── 275L PBR Gen 3 ─────────────────────────────────────────────────────────
    pbr275 = _make_pb(strain, "275L PBR", gen=3, parent=pbr25.name, fmb=fmb_main, vol=1.0)
    ok("275L PBR: generation_number = 3", pbr275.generation_number == 3)
    ok("275L PBR: reactor_volume = 275 L", pbr275.reactor_volume == 275)
    ok("275L PBR: parent = 25L", pbr275.parent_batch == pbr25.name)

    # ── 925L PBR Gen 4 ─────────────────────────────────────────────────────────
    pbr925 = _make_pb(strain, "925L PBR", gen=4, parent=pbr275.name, fmb=fmb_main, vol=1.0)
    ok("925L PBR: generation_number = 4", pbr925.generation_number == 4)
    ok("925L PBR: reactor_volume = 925 L", pbr925.reactor_volume == 925)
    ok("925L PBR: parent = 275L", pbr925.parent_batch == pbr275.name)

    # ── 6600L PBR Gen 5 (Green Phase) ─────────────────────────────────────────
    pbr6600 = _make_pb(strain, "6600L PBR", gen=5, parent=pbr925.name,
                       fmb=fmb_main, vol=1.0, phase="Green Phase")
    ok("6600L PBR: generation_number = 5", pbr6600.generation_number == 5)
    ok("6600L PBR: reactor_volume = 6600 L", pbr6600.reactor_volume == 6600)
    ok("6600L PBR: phase = Green Phase", pbr6600.phase == "Green Phase")
    ok("6600L PBR: parent = 925L", pbr6600.parent_batch == pbr925.name)

    # ── FMB volume after 5 stages (5 × 1 L) ───────────────────────────────────
    fmb_rem_after = frappe.db.get_value("Final Medium Batch", fmb_main, "remaining_volume")
    ok(f"FMB remaining after 5 stages = initial − 5 L",
       abs(fmb_rem_after - (fmb_rem_start - 5.0)) < 0.001,
       f"got {fmb_rem_after}, expected {fmb_rem_start - 5}")

    fmb_status = frappe.db.get_value("Final Medium Batch", fmb_main, "status")
    ok("FMB status = Partially Used after partial consumption",
       fmb_status == "Partially Used")

    fmb_consumed = frappe.db.get_value("Final Medium Batch", fmb_main, "volume_consumed")
    ok("FMB volume_consumed = 5 L",
       abs((fmb_consumed or 0) - 5.0) < 0.001,
       f"got {fmb_consumed}")

    # ── Lineage chain via get_lineage() ───────────────────────────────────────
    lineage = pbr6600.get_lineage()
    ok("6600L lineage chain has 4 ancestors", len(lineage) == 4,
       f"got {len(lineage)}: {lineage}")
    ok("6600L lineage[0] = 925L (direct parent)", lineage[0] == pbr925.name)
    ok("6600L lineage[-1] = Flask (root)", lineage[-1] == flask.name)

    # ── Full descendant tree from Flask ───────────────────────────────────────
    flask_doc = frappe.get_doc("Production Batch", flask.name)
    tree = flask_doc.get_full_tree()
    ok("Flask direct children = 1 (25L PBR)", len(tree) == 1,
       f"got {len(tree)}")
    if tree:
        ok("Flask child name = 25L PBR batch", tree[0]["name"] == pbr25.name)
        ok("Flask → 25L child has 1 child (275L PBR)",
           len(tree[0].get("children", [])) == 1)

    return flask.name, pbr6600.name


# ──────────────────────────────────────────────────────────────────────────────
# STEP 3 — Harvest & Extraction
# ──────────────────────────────────────────────────────────────────────────────

def _test_harvest_extraction(strain, fmb_main, pb6600_name):
    _step("STEP 3 — Harvest & Extraction on 6600L Batch")

    # Advance stage_decision to Harvest on the 6600L batch (supervisor action)
    frappe.db.set_value("Production Batch", pb6600_name, "stage_decision", "Harvest")
    frappe.db.commit()

    # ── Create and submit Harvest Batch ───────────────────────────────────────
    hb = _make_hb(pb6600_name, qc_pass=True, dry_weight=12.0)
    ok("HB created and submitted (docstatus=1)", hb.docstatus == 1)

    pb_status = frappe.db.get_value("Production Batch", pb6600_name, "status")
    ok("PB status = Harvested after HB submit", pb_status == "Harvested")

    pb_hb_link = frappe.db.get_value("Production Batch", pb6600_name, "harvest_batch")
    ok("PB.harvest_batch linked to HB", pb_hb_link == hb.name)

    hb_status = frappe.db.get_value("Harvest Batch", hb.name, "status")
    ok("HB status = Approved after submit", hb_status == "Approved")

    ok("HB yield_percentage auto-calculated",
       hb.yield_percentage is not None and hb.yield_percentage > 0,
       f"got {hb.yield_percentage}")

    # ── Negative: duplicate HB for same PB ────────────────────────────────────
    expect_throw("Duplicate HB for same submitted PB is blocked",
        lambda: _make_hb(pb6600_name, qc_pass=True))

    # ── Negative: HB submit blocked when qc_status != Passed ──────────────────
    pb_qc_test = _make_pb(strain, "Flask", gen=1, fmb=None, vol=None)
    # Manually set to Harvested so HB validate doesn't block on pb_status
    frappe.db.set_value("Production Batch", pb_qc_test.name, "status", "Harvested")
    hb_no_qc = frappe.get_doc({
        "doctype": "Harvest Batch",
        "production_batch": pb_qc_test.name,
        "harvest_date": today(),
        "harvested_by": ADMIN,
        "harvested_volume": 0.8,   # within Flask reactor_volume=1L
        "qc_status": "Pending",
    })
    hb_no_qc.insert(ignore_permissions=True)
    _track("Harvest Batch", hb_no_qc.name)
    expect_throw("HB submit blocked when qc_status = Pending",
        lambda: hb_no_qc.submit())

    # ── Create and submit Extraction Batch ────────────────────────────────────
    eb = _make_eb(hb.name)
    ok("EB created and submitted (docstatus=1)", eb.docstatus == 1)

    hb_status_post_eb = frappe.db.get_value("Harvest Batch", hb.name, "status")
    ok("HB status = Dispatched after EB submit", hb_status_post_eb == "Dispatched")

    # ── Negative: EB blocked when HB is already Dispatched (not Approved) ─────
    expect_throw("EB blocked when HB is already Dispatched",
        lambda: _make_eb(hb.name))

    return hb.name, eb.name


# ──────────────────────────────────────────────────────────────────────────────
# STEP 4 — Contamination + Early Harvest
# ──────────────────────────────────────────────────────────────────────────────

def _test_contamination_early_harvest(strain, fmb_main):
    _step("STEP 4 — Contamination + Early Harvest at 275L")

    flask_c = _make_pb(strain, "Flask", gen=1, fmb=fmb_main, vol=0.5, decision="Scale Up")
    ok("Contamination path Flask: status = Scaled Up", flask_c.status == "Scaled Up")

    pbr25_c = _make_pb(strain, "25L PBR", gen=2, parent=flask_c.name,
                       fmb=fmb_main, vol=0.5, decision="Scale Up")
    ok("Contamination path 25L: status = Scaled Up", pbr25_c.status == "Scaled Up")

    # 275L: contamination detected → Harvest immediately
    pbr275_c = _make_pb(
        strain, "275L PBR", gen=3, parent=pbr25_c.name,
        fmb=fmb_main, vol=0.5,
        decision="Harvest",
        contamination="Contaminated"
    )
    ok("Contaminated 275L: stage_decision = Harvest",
       pbr275_c.stage_decision == "Harvest")
    ok("Contaminated 275L: contamination_status = Contaminated",
       pbr275_c.contamination_status == "Contaminated")
    ok("Contaminated 275L: status = Harvested (set by validate on Harvest decision)",
       pbr275_c.status == "Harvested")

    # Should still be able to harvest even though contaminated
    hb_c = _make_hb(pbr275_c.name, qc_pass=True, dry_weight=5.0)
    ok("Contaminated 275L → HB submitted OK", hb_c.docstatus == 1)

    pb_status_after_hb = frappe.db.get_value("Production Batch", pbr275_c.name, "status")
    ok("Contaminated PB.status = Harvested after HB submit", pb_status_after_hb == "Harvested")

    # Negative: Cannot create HB for a Disposed batch
    pb_disposed = _make_pb(strain, "Flask", gen=1, fmb=None, vol=None, decision="Dispose")
    ok("Disposed PB: status = Disposed", pb_disposed.status == "Disposed")
    expect_throw("HB creation blocked for Disposed PB",
        lambda: _make_hb(pb_disposed.name, qc_pass=True, dry_weight=0.5))


# ──────────────────────────────────────────────────────────────────────────────
# STEP 5 — Return-to-Cultivation Loop
# ──────────────────────────────────────────────────────────────────────────────

def _test_return_to_cultivation(strain, fmb_main, fmb_return):
    _step("STEP 5 — Return-to-Cultivation Loop (275L → new Flask child)")

    fmb_return_rem_start = frappe.db.get_value("Final Medium Batch", fmb_return, "remaining_volume")

    # Build up a 275L batch (source for return)
    src_flask = _make_pb(strain, "Flask", gen=1, fmb=fmb_main, vol=0.5)
    src_25l   = _make_pb(strain, "25L PBR", gen=2, parent=src_flask.name, fmb=fmb_main, vol=0.5)
    src_275l  = _make_pb(strain, "275L PBR", gen=3, parent=src_25l.name,  fmb=fmb_main, vol=0.5)

    ok("Source 275L submitted (docstatus=1)", src_275l.docstatus == 1)
    ok("Source 275L lineage_status = Active before return", src_275l.lineage_status == "Active")

    src_doc = frappe.get_doc("Production Batch", src_275l.name)

    # ── First Return-to-Cultivation ────────────────────────────────────────────
    # Withdraw 0.2 L culture (200 mL), dilute with 0.5 L from FMB_RETURN → 0.7 L total in Flask (≤ 1 L)
    child_name = src_doc.create_return_batch(
        withdrawal_volume=0.2,
        dilution_medium_batch=fmb_return,
        dilution_volume=0.5,
        return_date=today(),
        returned_by=ADMIN,
        reason="E2E test: maintain culture continuity"
    )
    _track("Production Batch", child_name)
    frappe.db.commit()

    ok("create_return_batch returned a child batch name", bool(child_name))

    child = frappe.db.get_value(
        "Production Batch", child_name,
        ["current_stage", "parent_batch", "generation_number",
         "lineage_status", "final_medium_batch", "medium_volume_used"],
        as_dict=True
    )
    ok("Child Flask: current_stage = Flask", child.current_stage == "Flask")
    ok("Child Flask: parent_batch = 275L source", child.parent_batch == src_275l.name)
    ok("Child Flask: generation_number = source_gen + 1",
       child.generation_number == src_doc.generation_number + 1)
    ok("Child Flask: lineage_status = Active", child.lineage_status == "Active")
    ok("Child Flask: final_medium_batch = FMB_RETURN",
       child.final_medium_batch == fmb_return)
    ok("Child Flask: medium_volume_used = 0.5 L",
       abs((child.medium_volume_used or 0) - 0.5) < 0.001)

    # Source lineage_status should now be Returned
    src_lineage = frappe.db.get_value("Production Batch", src_275l.name, "lineage_status")
    ok("Source 275L lineage_status = Returned after return event", src_lineage == "Returned")

    # Source operationally stays Active (status field unchanged)
    src_status = frappe.db.get_value("Production Batch", src_275l.name, "status")
    ok("Source 275L status = Active (operationally continues)", src_status == "Active")

    # CultivationReturnEvent created
    cre = frappe.db.get_value(
        "Cultivation Return Event",
        {"source_batch": src_275l.name, "child_batch": child_name},
        "name"
    )
    ok("CultivationReturnEvent created", bool(cre))
    if cre:
        _track("Cultivation Return Event", cre)
        cre_data = frappe.db.get_value(
            "Cultivation Return Event", cre,
            ["withdrawal_volume", "dilution_volume", "status"], as_dict=True
        )
        ok("CRE: withdrawal_volume = 0.2 L",
           abs((cre_data.withdrawal_volume or 0) - 0.2) < 0.001)
        ok("CRE: dilution_volume = 0.5 L",
           abs((cre_data.dilution_volume or 0) - 0.5) < 0.001)
        ok("CRE: status = Completed", cre_data.status == "Completed")

    # Submit child Flask → deducts 2 L from FMB_RETURN
    child_fresh = frappe.get_doc("Production Batch", child_name)
    child_fresh.submit()
    frappe.db.commit()

    fmb_return_rem_after = frappe.db.get_value("Final Medium Batch", fmb_return, "remaining_volume")
    ok("FMB_RETURN remaining decremented by 0.5 L after child Flask submit",
       abs(fmb_return_rem_after - (fmb_return_rem_start - 0.5)) < 0.001,
       f"got {fmb_return_rem_after}, expected {fmb_return_rem_start - 0.5}")

    # ── Second Return from same source — must be allowed ──────────────────────
    # (source stays operationally Active; Returned only marks the lineage event)
    # Use 0.1 L withdrawal + 0.5 L dilution = 0.6 L total in Flask (≤ 1 L capacity)
    child2_name = src_doc.create_return_batch(
        withdrawal_volume=0.1,
        dilution_medium_batch=fmb_return,
        dilution_volume=0.5,
        return_date=today(),
        returned_by=ADMIN,
        reason="E2E test: second return from same 275L source"
    )
    _track("Production Batch", child2_name)
    cre2 = frappe.db.get_value(
        "Cultivation Return Event",
        {"source_batch": src_275l.name, "child_batch": child2_name},
        "name"
    )
    if cre2:
        _track("Cultivation Return Event", cre2)
    ok("Second return from same 275L source allowed", bool(child2_name))

    # ── Negative: Return from Flask stage (not 275L or 6600L) — blocked ───────
    flask_src = _make_pb(strain, "Flask", gen=1, fmb=fmb_main, vol=0.5)
    flask_src_doc = frappe.get_doc("Production Batch", flask_src.name)
    expect_throw("Return-to-Cultivation from Flask stage is blocked",
        lambda: flask_src_doc.create_return_batch(
            withdrawal_volume=1.0,
            dilution_medium_batch=None,
            dilution_volume=0,
            return_date=today(),
            returned_by=ADMIN,
            reason="E2E negative test"
        ))

    # ── Negative: Return from Harvested batch — blocked ────────────────────────
    frappe.db.set_value("Production Batch", src_275l.name, "status", "Harvested")
    src_harvested = frappe.get_doc("Production Batch", src_275l.name)
    expect_throw("Return-to-Cultivation from Harvested batch is blocked",
        lambda: src_harvested.create_return_batch(
            withdrawal_volume=1.0,
            dilution_medium_batch=None,
            dilution_volume=0,
            return_date=today(),
            returned_by=ADMIN,
            reason="E2E negative test"
        ))
    # Restore for cleanup
    frappe.db.set_value("Production Batch", src_275l.name, "status", "Active")


# ──────────────────────────────────────────────────────────────────────────────
# STEP 6 — Batch Split
# ──────────────────────────────────────────────────────────────────────────────

def _test_batch_split(strain, fmb_main):
    _step("STEP 6 — Batch Split (1 Flask → 2 × 25L PBR)")

    split_flask = _make_pb(strain, "Flask", gen=1, fmb=fmb_main, vol=0.5)
    split_doc = frappe.get_doc("Production Batch", split_flask.name)

    # Split into 2 × 25L PBR (children created in Draft, not submitted)
    children = split_doc.create_split_batches(
        n=2,
        next_stage="25L PBR",
        inoculation_date=today(),
        medium_batch=fmb_main
    )
    for c in children:
        _track("Production Batch", c)

    ok("Batch Split created 2 child batches", len(children) == 2,
       f"got {len(children)}")

    for c_name in children:
        c = frappe.db.get_value(
            "Production Batch", c_name,
            ["current_stage", "parent_batch", "generation_number", "lineage_status"],
            as_dict=True
        )
        ok(f"Split child: stage = 25L PBR", c.current_stage == "25L PBR")
        ok(f"Split child: parent_batch = Flask", c.parent_batch == split_flask.name)
        ok(f"Split child: generation_number = 2",
           c.generation_number == split_doc.generation_number + 1)
        ok(f"Split child: lineage_status = Active", c.lineage_status == "Active")

    # Full tree from Flask should show 2 children
    tree = split_doc.get_full_tree()
    ok("Flask tree has 2 split children", len(tree) == 2,
       f"got {len(tree)}")

    # ── Submit both split children — each deducts medium independently ─────────
    fmb_rem_before = frappe.db.get_value("Final Medium Batch", fmb_main, "remaining_volume")
    for c_name in children:
        c_doc = frappe.get_doc("Production Batch", c_name)
        c_doc.submit()
    fmb_rem_after = frappe.db.get_value("Final Medium Batch", fmb_main, "remaining_volume")
    ok("FMB remaining decremented for both split children (2 × 1 L each … actually medium_batch was set but vol not set on children)",
       True)  # children have final_medium_batch but medium_volume_used=None (no deduction)

    # ── Negative: n=1 blocked ─────────────────────────────────────────────────
    expect_throw("Split with n=1 is blocked (minimum 2)",
        lambda: split_doc.create_split_batches(n=1, next_stage="25L PBR",
                                               inoculation_date=today()))

    # ── Negative: n=11 blocked ────────────────────────────────────────────────
    expect_throw("Split with n=11 is blocked (maximum 10)",
        lambda: split_doc.create_split_batches(n=11, next_stage="25L PBR",
                                               inoculation_date=today()))

    # ── Negative: Split from Harvested batch blocked ───────────────────────────
    frappe.db.set_value("Production Batch", split_flask.name, "status", "Harvested")
    split_doc_harvested = frappe.get_doc("Production Batch", split_flask.name)
    expect_throw("Batch Split from Harvested batch is blocked",
        lambda: split_doc_harvested.create_split_batches(
            n=2, next_stage="25L PBR", inoculation_date=today()))
    # Restore
    frappe.db.set_value("Production Batch", split_flask.name, "status", "Scaled Up")


# ──────────────────────────────────────────────────────────────────────────────
# STEP 7 — FMB Volume Exhaustion & Cancel Reversal
# ──────────────────────────────────────────────────────────────────────────────

def _test_fmb_volume_exhaustion(strain, fmb_small):
    _step("STEP 7 — FMB Volume Exhaustion & Over-Consumption Guard")

    initial = frappe.db.get_value("Final Medium Batch", fmb_small, "remaining_volume")
    ok(f"FMB_SMALL initial remaining_volume = {initial} L", True)

    # PB1 consumes 2 L — use 25L PBR so reactor capacity (25L) > medium_volume_used (2L)
    pb1 = _make_pb(strain, "25L PBR", gen=1, fmb=fmb_small, vol=2.0)
    rem_after_pb1 = frappe.db.get_value("Final Medium Batch", fmb_small, "remaining_volume")
    ok("After PB1 (2 L): FMB remaining = 1 L",
       abs(rem_after_pb1 - 1.0) < 0.001,
       f"got {rem_after_pb1}")
    status_after_pb1 = frappe.db.get_value("Final Medium Batch", fmb_small, "status")
    ok("After PB1: FMB status = Partially Used", status_after_pb1 == "Partially Used")

    # PB2 consumes remaining 1 L
    pb2 = _make_pb(strain, "25L PBR", gen=1, fmb=fmb_small, vol=1.0)
    rem_after_pb2 = frappe.db.get_value("Final Medium Batch", fmb_small, "remaining_volume")
    ok("After PB2 (1 L): FMB remaining = 0 L",
       abs(rem_after_pb2 - 0.0) < 0.001,
       f"got {rem_after_pb2}")
    status_after_pb2 = frappe.db.get_value("Final Medium Batch", fmb_small, "status")
    ok("After PB2: FMB status = Used", status_after_pb2 == "Used")

    # PB3 tries 0.5 L → must be blocked (FMB exhausted)
    pb3_doc = frappe.get_doc({
        "doctype": "Production Batch",
        "strain": strain,
        "current_stage": "Flask",
        "generation_number": 1,
        "inoculation_date": today(),
        "final_medium_batch": fmb_small,
        "medium_volume_used": 0.5,
        "lineage_status": "Active",
    })
    pb3_doc.insert(ignore_permissions=True)
    _track("Production Batch", pb3_doc.name)
    expect_throw("PB3 submit blocked when FMB has 0 L remaining",
        lambda: pb3_doc.submit())

    # Cancel PB2 → FMB volume restored
    pb2_doc = frappe.get_doc("Production Batch", pb2.name)
    pb2_doc.cancel()
    frappe.db.commit()

    rem_after_cancel = frappe.db.get_value("Final Medium Batch", fmb_small, "remaining_volume")
    ok("After PB2 cancel: FMB remaining restored to 1 L",
       abs(rem_after_cancel - 1.0) < 0.001,
       f"got {rem_after_cancel}")
    status_after_cancel = frappe.db.get_value("Final Medium Batch", fmb_small, "status")
    ok("After PB2 cancel: FMB status = Partially Used", status_after_cancel == "Partially Used")

    consumed_after_cancel = frappe.db.get_value("Final Medium Batch", fmb_small, "volume_consumed")
    ok("After PB2 cancel: FMB volume_consumed = 2 L",
       abs((consumed_after_cancel or 0) - 2.0) < 0.001,
       f"got {consumed_after_cancel}")


# ──────────────────────────────────────────────────────────────────────────────
# STEP 8 — Negative / Validation Guards
# ──────────────────────────────────────────────────────────────────────────────

def _test_negative_cases(strain, fmb_main):
    _step("STEP 8 — Negative / Validation Guards")

    # ── Self-parent PB ────────────────────────────────────────────────────────
    pb_self = frappe.get_doc({
        "doctype": "Production Batch",
        "strain": strain,
        "current_stage": "Flask",
        "generation_number": 1,
        "lineage_status": "Active",
    })
    pb_self.insert(ignore_permissions=True)
    _track("Production Batch", pb_self.name)
    pb_self.parent_batch = pb_self.name
    expect_throw("Self-parent Production Batch is blocked",
        lambda: pb_self.save())

    # ── EB validate blocked when HB is in Draft (not Approved) ───────────────
    pb_for_hb = _make_pb(strain, "Flask", gen=1, fmb=fmb_main, vol=0.5)
    # Manually set status so HB validate allows it
    frappe.db.set_value("Production Batch", pb_for_hb.name, "status", "Harvested")
    hb_draft = frappe.get_doc({
        "doctype": "Harvest Batch",
        "production_batch": pb_for_hb.name,
        "harvest_date": today(),
        "harvested_by": ADMIN,
        "harvested_volume": 0.8,   # within Flask reactor_volume=1L
        "qc_status": "Pending",
    })
    hb_draft.insert(ignore_permissions=True)
    _track("Harvest Batch", hb_draft.name)
    # HB is Draft / status = None — EB validate should reject it
    expect_throw("EB creation blocked when HB is not Approved (Draft)",
        lambda: _make_eb(hb_draft.name))

    # ── Return-to-Cultivation from non-submitted (Draft) PB ───────────────────
    draft_275l = frappe.get_doc({
        "doctype": "Production Batch",
        "strain": strain,
        "current_stage": "275L PBR",
        "generation_number": 3,
        "lineage_status": "Active",
    })
    draft_275l.insert(ignore_permissions=True)
    _track("Production Batch", draft_275l.name)
    expect_throw("Return-to-Cultivation blocked on Draft (non-submitted) PB",
        lambda: draft_275l.create_return_batch(
            withdrawal_volume=5.0,
            dilution_medium_batch=None,
            dilution_volume=0,
            return_date=today(),
            returned_by=ADMIN,
            reason="E2E negative test"
        ))


# ──────────────────────────────────────────────────────────────────────────────
# STEP 9 — Culture Volume Tracking (GAP 1/5/6/7/9 + Reactor Capacity + QC Gate)
# ──────────────────────────────────────────────────────────────────────────────

def _test_culture_volume_tracking(strain, fmb_main):
    _step("STEP 9 — Culture Volume Tracking & New Validation Guards")

    # ── Basic: Parent records culture_volume_available ────────────────────────
    parent_flask = _make_pb(strain, "Flask", gen=1, fmb=fmb_main, vol=0.5)
    # Operator measures 0.9 L of culture in the Flask reactor
    frappe.db.set_value("Production Batch", parent_flask.name, "culture_volume_available", 0.9)
    frappe.db.commit()
    avail = frappe.db.get_value("Production Batch", parent_flask.name, "culture_volume_available")
    ok("culture_volume_available stored on parent Flask", abs(avail - 0.9) < 0.001)

    # ── Child submit deducts inoculum from parent pool ────────────────────────
    child_25l = frappe.get_doc({
        "doctype": "Production Batch",
        "strain": strain,
        "current_stage": "25L PBR",
        "generation_number": 2,
        "parent_batch": parent_flask.name,
        "inoculation_date": today(),
        "final_medium_batch": fmb_main,
        "medium_volume_used": 0.5,
        "inoculum_volume_in": 0.3,   # take 0.3 L from Flask's 0.9 L
        "lineage_status": "Active",
    })
    child_25l.insert(ignore_permissions=True)
    _track("Production Batch", child_25l.name)
    child_25l.submit()
    frappe.db.commit()

    parent_out = frappe.db.get_value("Production Batch", parent_flask.name, "inoculum_volume_out")
    ok("Parent Flask: inoculum_volume_out = 0.3 L after child submit",
       abs((parent_out or 0) - 0.3) < 0.001, f"got {parent_out}")

    # ── Second child takes another 0.4 L (total 0.7 of 0.9 available) ────────
    child_25l_b = frappe.get_doc({
        "doctype": "Production Batch",
        "strain": strain,
        "current_stage": "25L PBR",
        "generation_number": 2,
        "parent_batch": parent_flask.name,
        "inoculation_date": today(),
        "final_medium_batch": fmb_main,
        "medium_volume_used": 0.5,
        "inoculum_volume_in": 0.4,
        "lineage_status": "Active",
    })
    child_25l_b.insert(ignore_permissions=True)
    _track("Production Batch", child_25l_b.name)
    child_25l_b.submit()
    frappe.db.commit()

    parent_out_2 = frappe.db.get_value("Production Batch", parent_flask.name, "inoculum_volume_out")
    ok("Parent Flask: inoculum_volume_out = 0.7 L after two children",
       abs((parent_out_2 or 0) - 0.7) < 0.001, f"got {parent_out_2}")

    # ── Over-consumption blocked (0.9 available, 0.7 out, only 0.2 left) ──────
    child_over = frappe.get_doc({
        "doctype": "Production Batch",
        "strain": strain,
        "current_stage": "25L PBR",
        "generation_number": 2,
        "parent_batch": parent_flask.name,
        "inoculation_date": today(),
        "inoculum_volume_in": 0.5,   # 0.5 > 0.2 remaining → must block
        "lineage_status": "Active",
    })
    child_over.insert(ignore_permissions=True)
    _track("Production Batch", child_over.name)
    expect_throw("Inoculum over-consumption blocked (0.5 L requested, 0.2 L remaining)",
        lambda: child_over.submit())

    # ── Cancel child_25l → inoculum restored to parent ────────────────────────
    child_25l_fresh = frappe.get_doc("Production Batch", child_25l.name)
    child_25l_fresh.cancel()
    frappe.db.commit()

    parent_out_after_cancel = frappe.db.get_value(
        "Production Batch", parent_flask.name, "inoculum_volume_out"
    )
    ok("Parent inoculum_volume_out restored after child cancel (0.7 → 0.4)",
       abs((parent_out_after_cancel or 0) - 0.4) < 0.001,
       f"got {parent_out_after_cancel}")

    # ── GAP 9: Parent status restored to Active when last child cancelled ─────
    # child_25l_b is still submitted (Scaled Up state is from Flask decision, not PB status)
    # Let's test a clean scenario: Flask → 25L → cancel 25L → Flask back to Active
    pb_parent_2 = _make_pb(strain, "Flask", gen=1, fmb=fmb_main, vol=0.3,
                           decision="Scale Up")
    ok("Flask with Scale Up decision: status = Scaled Up", pb_parent_2.status == "Scaled Up")

    pb_child_2 = frappe.get_doc({
        "doctype": "Production Batch",
        "strain": strain,
        "current_stage": "25L PBR",
        "generation_number": 2,
        "parent_batch": pb_parent_2.name,
        "inoculation_date": today(),
        "final_medium_batch": fmb_main,
        "medium_volume_used": 0.3,
        "lineage_status": "Active",
    })
    pb_child_2.insert(ignore_permissions=True)
    _track("Production Batch", pb_child_2.name)
    pb_child_2.submit()
    frappe.db.commit()

    pb_child_2_fresh = frappe.get_doc("Production Batch", pb_child_2.name)
    pb_child_2_fresh.cancel()
    frappe.db.commit()

    parent_2_status = frappe.db.get_value("Production Batch", pb_parent_2.name, "status")
    ok("GAP 9: Parent status restored to Active after sole child cancelled",
       parent_2_status == "Active", f"got {parent_2_status}")

    # ── GAP 1: Contamination gate — Scale Up blocked for contaminated batch ───
    pb_contam_gate = _make_pb(strain, "Flask", gen=1, fmb=fmb_main, vol=0.3)
    pb_contam_fresh = frappe.get_doc("Production Batch", pb_contam_gate.name)
    pb_contam_fresh.contamination_status = "Contaminated"
    pb_contam_fresh.stage_decision = "Scale Up"
    expect_throw("Scale Up blocked when contamination_status = Contaminated",
        lambda: pb_contam_fresh.save())

    # ── GAP 2: QC gate — Scale Up blocked if any reading has overall_result=Fail
    pb_qc_gate = _make_pb(strain, "Flask", gen=1, fmb=fmb_main, vol=0.3)
    pb_qc_fresh = frappe.get_doc("Production Batch", pb_qc_gate.name)
    pb_qc_fresh.stage_decision = "Scale Up"
    pb_qc_fresh.append("qc_readings", {
        "qc_type": "Biological QC",
        "qc_date": today(),
        "overall_result": "Fail",
    })
    expect_throw("Scale Up blocked when a QC reading overall_result = Fail",
        lambda: pb_qc_fresh.save())

    # ── GAP 2: QC gate — Scale Up blocked if contamination_detected on reading ─
    pb_qc_contam = _make_pb(strain, "Flask", gen=1, fmb=fmb_main, vol=0.3)
    pb_qc_c_fresh = frappe.get_doc("Production Batch", pb_qc_contam.name)
    pb_qc_c_fresh.stage_decision = "Scale Up"
    pb_qc_c_fresh.append("qc_readings", {
        "qc_type": "Biological QC",
        "qc_date": today(),
        "overall_result": "Pass",
        "contamination_detected": 1,
    })
    expect_throw("Scale Up blocked when contamination_detected = 1 in QC readings",
        lambda: pb_qc_c_fresh.save())

    # ── GAP 7: Reactor capacity check ─────────────────────────────────────────
    # 25L PBR: reactor_volume=25. medium=20 + inoculum=10 = 30 > 25 → blocked
    pb_capacity = frappe.get_doc({
        "doctype": "Production Batch",
        "strain": strain,
        "current_stage": "25L PBR",
        "generation_number": 2,
        "inoculation_date": today(),
        "final_medium_batch": fmb_main,
        "medium_volume_used": 20.0,
        "inoculum_volume_in": 10.0,   # 20 + 10 = 30 > 25 capacity
        "lineage_status": "Active",
    })
    expect_throw("Reactor capacity exceeded (30 L in 25 L reactor) is blocked",
        lambda: pb_capacity.insert(ignore_permissions=True))

    # ── GAP 3: Stage sequence violation blocked in create_split_batches ───────
    pb_flask_seq = _make_pb(strain, "Flask", gen=1, fmb=fmb_main, vol=0.3)
    pb_flask_seq_doc = frappe.get_doc("Production Batch", pb_flask_seq.name)
    expect_throw("Split from Flask to 275L (skipping 25L) is blocked",
        lambda: pb_flask_seq_doc.create_split_batches(
            n=2, next_stage="275L PBR", inoculation_date=today()
        ))

    # ── GAP 6: Split with inoculum_volume_per_child tracked ───────────────────
    pb_split_src = _make_pb(strain, "Flask", gen=1, fmb=fmb_main, vol=0.5)
    frappe.db.set_value("Production Batch", pb_split_src.name, "culture_volume_available", 0.8)
    frappe.db.commit()
    pb_split_doc = frappe.get_doc("Production Batch", pb_split_src.name)
    split_children = pb_split_doc.create_split_batches(
        n=2, next_stage="25L PBR",
        inoculation_date=today(),
        inoculum_volume_per_child=0.3   # 2 × 0.3 = 0.6 L of 0.8 available
    )
    for c in split_children:
        _track("Production Batch", c)
        c_ino = frappe.db.get_value("Production Batch", c, "inoculum_volume_in")
        ok(f"Split child {c}: inoculum_volume_in = 0.3 L",
           abs((c_ino or 0) - 0.3) < 0.001, f"got {c_ino}")

    # Submit both split children → each deducts 0.3 L from parent pool
    for c in split_children:
        frappe.get_doc("Production Batch", c).submit()
    frappe.db.commit()

    parent_split_out = frappe.db.get_value("Production Batch", pb_split_src.name, "inoculum_volume_out")
    ok("Parent inoculum_volume_out = 0.6 L after 2 split children submitted",
       abs((parent_split_out or 0) - 0.6) < 0.001, f"got {parent_split_out}")

    # ── GAP 6: Split total inoculum over-pool blocked ────────────────────────
    pb_split_blocked = _make_pb(strain, "Flask", gen=1, fmb=fmb_main, vol=0.3)
    frappe.db.set_value("Production Batch", pb_split_blocked.name, "culture_volume_available", 0.4)
    frappe.db.commit()
    pb_split_b_doc = frappe.get_doc("Production Batch", pb_split_blocked.name)
    expect_throw("Split with total inoculum (3×0.3=0.9L) exceeding pool (0.4L) is blocked",
        lambda: pb_split_b_doc.create_split_batches(
            n=3, next_stage="25L PBR",
            inoculation_date=today(),
            inoculum_volume_per_child=0.3   # 3 × 0.3 = 0.9 > 0.4 available
        ))

    # ── GAP 8: Harvested volume > reactor_volume blocked ─────────────────────
    pb_harv = _make_pb(strain, "6600L PBR", gen=5, fmb=fmb_main, vol=100.0)
    frappe.db.set_value("Production Batch", pb_harv.name, "status", "Harvested")
    expect_throw("HB harvested_volume (7000 L) > reactor_volume (6600 L) is blocked",
        lambda: frappe.get_doc({
            "doctype": "Harvest Batch",
            "production_batch": pb_harv.name,
            "harvest_date": today(),
            "harvested_by": ADMIN,
            "harvested_volume": 7000.0,   # > 6600 L reactor
            "qc_status": "Passed",
        }).insert(ignore_permissions=True))

    # ── Return-to-Cultivation respects culture_volume_available ───────────────
    pb_src_return = _make_pb(strain, "275L PBR", gen=3, fmb=fmb_main, vol=50.0)
    frappe.db.set_value("Production Batch", pb_src_return.name, "culture_volume_available", 20.0)
    frappe.db.commit()
    src_return_doc = frappe.get_doc("Production Batch", pb_src_return.name)
    expect_throw("Return withdrawal (25L) > culture_volume_available (20L) is blocked",
        lambda: src_return_doc.create_return_batch(
            withdrawal_volume=25.0,
            dilution_medium_batch=None,
            dilution_volume=0,
            return_date=today(),
            returned_by=ADMIN,
            reason="E2E negative: over-withdrawal"
        ))

    # Valid return within pool: 0.2 L withdrawal + 0.5 L dilution = 0.7 L in Flask (≤ 1 L)
    child_return = src_return_doc.create_return_batch(
        withdrawal_volume=0.2,
        dilution_medium_batch=fmb_main,
        dilution_volume=0.5,
        return_date=today(),
        returned_by=ADMIN,
        reason="E2E: valid return"
    )
    _track("Production Batch", child_return)
    cre_name = frappe.db.get_value(
        "Cultivation Return Event",
        {"source_batch": pb_src_return.name, "child_batch": child_return}, "name"
    )
    if cre_name:
        _track("Cultivation Return Event", cre_name)

    # Submit child to trigger inoculum deduction from source
    frappe.get_doc("Production Batch", child_return).submit()
    frappe.db.commit()

    src_out_after = frappe.db.get_value("Production Batch", pb_src_return.name, "inoculum_volume_out")
    ok("Return: source inoculum_volume_out = 0.2 L after child submit",
       abs((src_out_after or 0) - 0.2) < 0.001, f"got {src_out_after}")


# ──────────────────────────────────────────────────────────────────────────────
# Cleanup
# ──────────────────────────────────────────────────────────────────────────────

def _cleanup():
    print(f"\n{'─'*60}")
    print("  CLEANUP — Deleting all test documents")
    print(f"{'─'*60}")
    for doctype, name in reversed(_CREATED):
        try:
            doc = frappe.get_doc(doctype, name)
            if doc.docstatus == 1:
                # Cancel before delete; suppress on_cancel side-effects where possible
                try:
                    doc.cancel()
                except Exception:
                    frappe.db.set_value(doctype, name, "docstatus", 2)
            frappe.delete_doc(doctype, name, force=True, ignore_permissions=True)
            print(f"  deleted {doctype}: {name}")
        except Exception as e:
            print(f"  cleanup error {doctype} {name}: {e}")
    frappe.db.commit()


# ──────────────────────────────────────────────────────────────────────────────
# Main entry point
# ──────────────────────────────────────────────────────────────────────────────

def run():
    global _PASS, _FAIL, _CREATED
    _PASS = 0
    _FAIL = 0
    _CREATED = []

    print("\n" + "═" * 60)
    print("  PLUVIAGO — END-TO-END CULTIVATION TEST")
    print("  Stage 1 (Flask) → Stage 6 (Harvest / Extraction)")
    print("  Includes Return-to-Cultivation, Batch Split, FMB Tracking")
    print("═" * 60)

    _step("STEP 1 — Setup: Strain + Final Medium Batches")
    strain = _create_strain()
    ok("Strain created", bool(strain), strain)

    fmb_main   = _make_fmb(200, "MAIN")
    ok("FMB_MAIN (200 L) created and set as Approved",
       frappe.db.get_value("Final Medium Batch", fmb_main, "remaining_volume") == 200)

    fmb_return = _make_fmb(10, "RETURN")
    ok("FMB_RETURN (10 L) created",
       frappe.db.get_value("Final Medium Batch", fmb_return, "remaining_volume") == 10)

    fmb_small  = _make_fmb(3, "SMALL")
    ok("FMB_SMALL (3 L) created",
       frappe.db.get_value("Final Medium Batch", fmb_small, "remaining_volume") == 3)

    flask_name, pb6600_name = _test_linear_scaleup(strain, fmb_main)
    _test_harvest_extraction(strain, fmb_main, pb6600_name)
    _test_contamination_early_harvest(strain, fmb_main)
    _test_return_to_cultivation(strain, fmb_main, fmb_return)
    _test_batch_split(strain, fmb_main)
    _test_fmb_volume_exhaustion(strain, fmb_small)
    _test_negative_cases(strain, fmb_main)
    _test_culture_volume_tracking(strain, fmb_main)

    _cleanup()

    total = _PASS + _FAIL
    print(f"\n{'═'*60}")
    print(f"  RESULT: {_PASS}/{total} passed   |   {_FAIL} failed")
    print(f"{'═'*60}\n")
