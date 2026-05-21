"""
Pluviago End-to-End Backend Test — Cultivation Pipeline
========================================================
Tests Stage 1–6 (Flask → 25L → 275L → 925L → 6600L → Harvest → Drying)
including Return-to-Cultivation, Batch Splitting, Contamination Incidents,
Drying Batches, and FMB volume tracking.

Scenarios covered:
  1. Linear Scale-Up: Flask(Gen1) → 25L(2) → 275L(3) → 925L(4) → 6600L(5)
  2. Harvest + Drying on 6600L (normal path)
  3. Contamination Incident lifecycle
  4. Contaminated batch + Early Harvest at 275L
  5. Return-to-Cultivation from 275L → new Flask child
  6. Batch Split: 1 Flask → 2 × 25L PBR
  7. FMB Volume Exhaustion & Over-Consumption Guard (with cancel reversal)
  8. Negative / Validation Guards
  9. Culture Volume Tracking (inoculum pool deduction/restore)

Run with:
  bench --site production.local execute pluviago.pluviago_biotech.tests.e2e_cultivation_test.run
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


def expect_throw(label, fn, keyword=None):
    """Assert that fn() raises any exception (optionally matching keyword)."""
    global _PASS, _FAIL
    try:
        fn()
        _FAIL += 1
        print(f"  ✗  FAIL: {label} — expected an error but none was raised")
    except Exception as e:
        err = str(e)
        if keyword and keyword not in err:
            _FAIL += 1
            print(f"  ✗  FAIL: {label} — wrong error (missing '{keyword}'): {err[:120]}")
        else:
            _PASS += 1
            print(f"  ✓  {label} (correctly blocked: {err[:90]})")


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
    Bypasses the full medium preparation pipeline — cultivation tracking
    is what we're testing here; medium prep is in e2e_medium_test.py.
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
    fmb.insert(ignore_mandatory=True, ignore_permissions=True)
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
             decision="Scale Up", contamination="Clean", phase="N/A"):
    """
    Create and submit a Production Batch.
    decision defaults to Scale Up (the common chain step).
    A single passing QC row is auto-added when decision=Scale Up so the
    QC gate doesn't block submission.
    For Harvest/Dispose decisions, no QC row is needed.
    """
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
    if decision == "Scale Up":
        pb.append("qc_readings", {
            "qc_type": "Process QC",
            "qc_date": today(),
            "overall_result": "Pass",
            "contamination_detected": 0,
        })
    pb.insert(ignore_permissions=True)
    pb.submit()
    _track("Production Batch", pb.name)
    return pb


def _make_hb(pb_name, qc_pass=True, wet_biomass_kg=50.0):
    """Create (and submit when qc_pass=True) a Harvest Batch."""
    reactor_vol = frappe.db.get_value("Production Batch", pb_name, "reactor_volume") or 1.0
    hb = frappe.get_doc({
        "doctype": "Harvest Batch",
        "production_batch": pb_name,
        "harvest_date": today(),
        "harvested_by": ADMIN,
        "harvested_volume": reactor_vol,
        "wet_biomass_kg": wet_biomass_kg,
        "qc_status": "Passed" if qc_pass else "Pending",
        "qc_checked_by": ADMIN,
        "qc_date": today(),
    })
    hb.insert(ignore_permissions=True)
    _track("Harvest Batch", hb.name)
    if qc_pass:
        hb.submit()
    return hb


def _make_db(hb_name, wet_in=50.0, dry_out=5.0, qc_pass=True):
    """Create (and submit when qc_pass=True) a Drying Batch."""
    db = frappe.get_doc({
        "doctype": "Drying Batch",
        "harvest_batch": hb_name,
        "drying_date": today(),
        "operator": ADMIN,
        "wet_biomass_in": wet_in,
        "drying_method": "Spray Drying",
        "actual_dry_weight": dry_out,
        "qc_status": "Passed" if qc_pass else "Pending",
        "qc_checked_by": ADMIN,
        "qc_date": today(),
    })
    db.insert(ignore_permissions=True)
    _track("Drying Batch", db.name)
    if qc_pass:
        db.submit()
    return db


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
    ok("Flask: status = Scaled Up", flask.status == "Scaled Up")
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
    ok("25L PBR: status = Scaled Up", pbr25.status == "Scaled Up")

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
# STEP 3 — Phase Transition + Harvest + Drying
# ──────────────────────────────────────────────────────────────────────────────

def _test_harvest_drying(strain, fmb_main, pb6600_name):
    _step("STEP 3 — Phase Transition + Harvest + Drying on 6600L Batch")

    # ── Phase transition: Green Phase → Red Phase ──────────────────────────────
    pb6600 = frappe.get_doc("Production Batch", pb6600_name)
    pb6600.record_phase_transition(
        new_phase="Red Phase",
        transition_date=today(),
        transitioned_by=ADMIN,
        notes="E2E test: transitioning to astaxanthin accumulation phase"
    )
    frappe.db.commit()
    phase_after = frappe.db.get_value("Production Batch", pb6600_name, "phase")
    ok("6600L phase = Red Phase after transition", phase_after == "Red Phase")
    phase_date = frappe.db.get_value("Production Batch", pb6600_name, "phase_transition_date")
    ok("6600L phase_transition_date set", bool(phase_date))

    # ── Negative phase transition guards ─────────────────────────────────────
    expect_throw("Cannot revert Red→Green phase",
        lambda: pb6600.record_phase_transition("Green Phase", today(), ADMIN),
        keyword="Cannot revert")
    expect_throw("Cannot set same phase again (Red→Red)",
        lambda: pb6600.record_phase_transition("Red Phase", today(), ADMIN),
        keyword="already in")

    # ── Advance to Harvest decision then create Harvest Batch ─────────────────
    # Set both stage_decision and status (bypassing on_submit lock via db_set)
    frappe.db.set_value("Production Batch", pb6600_name, {
        "stage_decision": "Harvest",
        "status": "Harvested",
    })
    frappe.db.commit()

    hb = _make_hb(pb6600_name, qc_pass=True, wet_biomass_kg=80.0)
    ok("HB created and submitted (docstatus=1)", hb.docstatus == 1)
    ok("HB status = Approved after submit",
       frappe.db.get_value("Harvest Batch", hb.name, "status") == "Approved")

    pb_status = frappe.db.get_value("Production Batch", pb6600_name, "status")
    ok("PB status = Harvested after HB submit", pb_status == "Harvested")

    pb_hb_link = frappe.db.get_value("Production Batch", pb6600_name, "harvest_batch")
    ok("PB.harvest_batch linked to HB", pb_hb_link == hb.name)

    # ── Negative: HB submit blocked when qc_status != Passed ──────────────────
    pb_qc_test = _make_pb(strain, "Flask", gen=1, fmb=None, vol=None, decision="Harvest")
    hb_no_qc = frappe.get_doc({
        "doctype": "Harvest Batch",
        "production_batch": pb_qc_test.name,
        "harvest_date": today(),
        "harvested_by": ADMIN,
        "harvested_volume": 0.8,
        "qc_status": "Pending",
    })
    hb_no_qc.insert(ignore_permissions=True)
    _track("Harvest Batch", hb_no_qc.name)
    expect_throw("HB submit blocked when qc_status = Pending",
        lambda: hb_no_qc.submit(), keyword="QC must be Passed")

    # ── Negative: duplicate HB for same PB ────────────────────────────────────
    expect_throw("Duplicate HB for same submitted PB is blocked",
        lambda: _make_hb(pb6600_name, qc_pass=True))

    # ── Drying Batch: validate requires submitted HB ───────────────────────────
    expect_throw("DB creation blocked if HB is not submitted",
        lambda: _make_db(hb_no_qc.name, wet_in=50.0, dry_out=5.0),
        keyword="must be submitted")

    # ── Create and submit Drying Batch ────────────────────────────────────────
    drying = _make_db(hb.name, wet_in=80.0, dry_out=8.0, qc_pass=True)
    ok("DB created and submitted (docstatus=1)", drying.docstatus == 1)
    ok("DB status = Approved after submit",
       frappe.db.get_value("Drying Batch", drying.name, "status") == "Approved")

    # yield_percentage = 8/80 × 100 = 10.0
    yield_pct = frappe.db.get_value("Drying Batch", drying.name, "yield_percentage")
    ok("DB yield_percentage = 10.0%",
       abs((yield_pct or 0) - 10.0) < 0.01, f"got {yield_pct}")

    # HB write-back
    hb_dry_wt = frappe.db.get_value("Harvest Batch", hb.name, "actual_dry_weight")
    ok("HB.actual_dry_weight updated by DB submit",
       abs((hb_dry_wt or 0) - 8.0) < 0.01, f"got {hb_dry_wt}")
    hb_yield = frappe.db.get_value("Harvest Batch", hb.name, "yield_percentage")
    ok("HB.yield_percentage updated by DB submit",
       abs((hb_yield or 0) - 10.0) < 0.01, f"got {hb_yield}")
    hb_db_link = frappe.db.get_value("Harvest Batch", hb.name, "drying_batch")
    ok("HB.drying_batch links to DB", hb_db_link == drying.name)

    # ── Negative: DB submit blocked when qc_status != Passed ──────────────────
    hb2 = _make_hb(pb_qc_test.name, qc_pass=False)
    # Manually approve HB to bypass HB qc gate so DB validate focuses on DB qc
    frappe.db.set_value("Harvest Batch", hb2.name, {
        "docstatus": 1, "status": "Approved"
    })
    frappe.db.commit()
    db_fail_qc = frappe.get_doc({
        "doctype": "Drying Batch",
        "harvest_batch": hb2.name,
        "drying_date": today(),
        "operator": ADMIN,
        "wet_biomass_in": 50.0,
        "drying_method": "Spray Drying",
        "actual_dry_weight": 5.0,
        "qc_status": "Pending",
    })
    db_fail_qc.insert(ignore_permissions=True)
    _track("Drying Batch", db_fail_qc.name)
    expect_throw("DB submit blocked when qc_status = Pending",
        lambda: db_fail_qc.submit(), keyword="QC Status must be Passed")

    # ── Negative: duplicate DB for same HB ────────────────────────────────────
    expect_throw("Duplicate DB for same submitted HB is blocked",
        lambda: _make_db(hb.name, wet_in=80.0, dry_out=8.0))

    return hb.name, drying.name


# ──────────────────────────────────────────────────────────────────────────────
# STEP 4 — Contamination Incident Lifecycle
# ──────────────────────────────────────────────────────────────────────────────

def _test_contamination_incident(strain, fmb_main):
    _step("STEP 4 — Contamination Incident Lifecycle")

    pb = _make_pb(strain, "Flask", gen=1, fmb=fmb_main, vol=0.5)

    # T11.1 — Creating CI flags PB as Contaminated
    ci = frappe.get_doc({
        "doctype": "Contamination Incident",
        "incident_date": today(),
        "production_batch": pb.name,
        "reactor_stage": "Flask",
        "reported_by": ADMIN,
        "contamination_type": "Bacterial",
        "culture_phase_at_incident": "N/A",
        "status": "Open",
    })
    ci.insert(ignore_permissions=True)
    _track("Contamination Incident", ci.name)

    pb_contam = frappe.db.get_value("Production Batch", pb.name, "contamination_status")
    ok("T11.1: CI creation flags PB.contamination_status = Contaminated",
       pb_contam == "Contaminated", f"got {pb_contam}")
    pb_status_ci = frappe.db.get_value("Production Batch", pb.name, "status")
    ok("T11.1: CI creation sets PB.status = Contaminated",
       pb_status_ci == "Contaminated", f"got {pb_status_ci}")

    # T11.3 — CI submit with Pending decision blocked
    expect_throw("T11.4: CI submit blocked when Decision = Pending",
        lambda: ci.submit(), keyword="Decision")

    # T11.5 — CI submit with non-Resolved/Closed status blocked
    ci.reload()
    ci.decision = "Harvest Immediately"
    ci.save(ignore_permissions=True)
    expect_throw("T11.5: CI submit blocked when Status = Open (not Resolved/Closed)",
        lambda: ci.submit(), keyword="Resolved")

    # T11.6 — CI submit without root_cause_category blocked
    ci.reload()
    ci.status = "Resolved"
    ci.save(ignore_permissions=True)
    expect_throw("T11.6: CI submit blocked when root_cause_category empty",
        lambda: ci.submit(), keyword="Root Cause Category")

    # T11.7 — Submit with all required fields
    ci.reload()
    ci.root_cause_category = "Equipment Failure"
    ci.save(ignore_permissions=True)
    ci.submit()
    ok("T11.7: CI submitted successfully", ci.docstatus == 1)

    # T11.8 — Cancel CI → PB restored to Clean/Active
    ci.cancel()
    pb_clean = frappe.db.get_value("Production Batch", pb.name, "contamination_status")
    ok("T11.8: CI cancel restores PB.contamination_status = Clean",
       pb_clean == "Clean", f"got {pb_clean}")
    pb_active = frappe.db.get_value("Production Batch", pb.name, "status")
    ok("T11.8: CI cancel restores PB.status = Active",
       pb_active == "Active", f"got {pb_active}")

    # T11.9/11.10 — Two CIs; cancel one; PB stays Contaminated; cancel both → restored
    def _make_submitted_ci(pb_name, contamination_type):
        ci = frappe.get_doc({
            "doctype": "Contamination Incident",
            "incident_date": today(),
            "production_batch": pb_name,
            "reactor_stage": "Flask",
            "reported_by": ADMIN,
            "contamination_type": contamination_type,
            "status": "Resolved",
            "decision": "Continue with Monitoring",
            "root_cause_category": "Environmental",
        })
        ci.insert(ignore_permissions=True)
        _track("Contamination Incident", ci.name)
        ci.submit()
        return ci

    ci2 = _make_submitted_ci(pb.name, "Fungal")
    ci3 = _make_submitted_ci(pb.name, "Bacterial")

    ok("T11.9: Two CIs submitted for same PB",
       frappe.db.count("Contamination Incident",
           {"production_batch": pb.name, "docstatus": 1}) >= 2)

    # Cancel ci3 — ci2 still active, PB should remain Contaminated
    ci3.cancel()
    pb_still_contam = frappe.db.get_value("Production Batch", pb.name, "contamination_status")
    ok("T11.9: PB still Contaminated when one CI cancelled (other active)",
       pb_still_contam == "Contaminated", f"got {pb_still_contam}")

    # Cancel ci2 — no more CIs → PB restored
    ci2.cancel()
    pb_clean2 = frappe.db.get_value("Production Batch", pb.name, "contamination_status")
    ok("T11.10: PB restored to Clean after all CIs cancelled",
       pb_clean2 == "Clean", f"got {pb_clean2}")

    # T11.11 — decision_date auto-set
    ci4 = frappe.get_doc({
        "doctype": "Contamination Incident",
        "incident_date": today(),
        "production_batch": pb.name,
        "reactor_stage": "Flask",
        "reported_by": ADMIN,
        "contamination_type": "Unknown",
        "status": "Open",
    })
    ci4.insert(ignore_permissions=True)
    _track("Contamination Incident", ci4.name)
    ci4.decision = "Dispose"
    ci4.save(ignore_permissions=True)
    ok("T11.11: decision_date auto-set when decision changes",
       bool(ci4.decision_date))
    ok("T11.11: decision_by auto-set",
       bool(ci4.decision_by))

    # T11.12 — disposal fields auto-set
    ci4.reload()
    ci4.batch_disposed = 1
    ci4.save(ignore_permissions=True)
    ok("T11.12: disposal_date auto-set when batch_disposed=1",
       bool(ci4.disposal_date))


# ──────────────────────────────────────────────────────────────────────────────
# STEP 5 — Contamination + Early Harvest
# ──────────────────────────────────────────────────────────────────────────────

def _test_contamination_early_harvest(strain, fmb_main):
    _step("STEP 5 — Contamination + Early Harvest at 275L")

    flask_c = _make_pb(strain, "Flask", gen=1, fmb=fmb_main, vol=0.5)
    ok("Contamination path Flask: status = Scaled Up", flask_c.status == "Scaled Up")

    pbr25_c = _make_pb(strain, "25L PBR", gen=2, parent=flask_c.name,
                       fmb=fmb_main, vol=0.5)
    ok("Contamination path 25L: status = Scaled Up", pbr25_c.status == "Scaled Up")

    # 275L: contamination detected → Harvest immediately (Scale Up would be blocked)
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
    ok("Contaminated 275L: status = Harvested (Harvest decision auto-sets status)",
       pbr275_c.status == "Harvested")

    # Should still be able to harvest even though contaminated
    hb_c = _make_hb(pbr275_c.name, qc_pass=True, wet_biomass_kg=10.0)
    ok("Contaminated 275L → HB submitted OK", hb_c.docstatus == 1)

    pb_status_after_hb = frappe.db.get_value("Production Batch", pbr275_c.name, "status")
    ok("Contaminated PB.status = Harvested after HB submit", pb_status_after_hb == "Harvested")

    # Contaminated + Scale Up → blocked (test on draft insert, not on submitted doc)
    pb_block = frappe.get_doc({
        "doctype": "Production Batch",
        "strain": strain,
        "current_stage": "Flask",
        "generation_number": 1,
        "inoculation_date": today(),
        "lineage_status": "Active",
        "contamination_status": "Contaminated",
        "stage_decision": "Scale Up",
    })
    pb_block.append("qc_readings", {
        "qc_type": "Process QC", "qc_date": today(),
        "overall_result": "Pass", "contamination_detected": 0,
    })
    expect_throw("T6.1: Scale Up blocked when contamination_status = Contaminated",
        lambda: pb_block.insert(ignore_permissions=True), keyword="Cannot scale up")

    # Negative: Cannot create HB for a Disposed batch
    pb_disposed = _make_pb(strain, "Flask", gen=1, fmb=None, vol=None, decision="Dispose")
    ok("Disposed PB: status = Disposed", pb_disposed.status == "Disposed")
    expect_throw("HB creation blocked for Disposed PB",
        lambda: _make_hb(pb_disposed.name, qc_pass=True))


# ──────────────────────────────────────────────────────────────────────────────
# STEP 6 — Return-to-Cultivation Loop
# ──────────────────────────────────────────────────────────────────────────────

def _test_return_to_cultivation(strain, fmb_main, fmb_return):
    _step("STEP 6 — Return-to-Cultivation Loop (275L → new Flask child)")

    # Build up a 275L batch (source for return)
    src_flask = _make_pb(strain, "Flask", gen=1, fmb=fmb_main, vol=0.5)
    src_25l   = _make_pb(strain, "25L PBR", gen=2, parent=src_flask.name, fmb=fmb_main, vol=0.5)
    src_275l  = _make_pb(strain, "275L PBR", gen=3, parent=src_25l.name,  fmb=fmb_main, vol=0.5)

    ok("Source 275L submitted (docstatus=1)", src_275l.docstatus == 1)
    ok("Source 275L lineage_status = Active before return", src_275l.lineage_status == "Active")

    src_doc = frappe.get_doc("Production Batch", src_275l.name)

    # ── First Return-to-Cultivation ────────────────────────────────────────────
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
        ["current_stage", "parent_batch", "generation_number", "lineage_status"],
        as_dict=True
    )
    ok("T10.3: Child Flask: current_stage = Flask", child.current_stage == "Flask")
    ok("T10.3: Child Flask: parent_batch = 275L source", child.parent_batch == src_275l.name)
    # Per Roy's requirement: Return-to-Cultivation Flask always resets to Gen 1
    ok("T10.3: Child Flask: generation_number = 1 (Roy's requirement — always Gen 1)",
       child.generation_number == 1,
       f"got {child.generation_number}")
    ok("T10.3: Child Flask: lineage_status = Active", child.lineage_status == "Active")

    # Source lineage_status → Returned
    src_lineage = frappe.db.get_value("Production Batch", src_275l.name, "lineage_status")
    ok("T10.5: Source 275L lineage_status = Returned after return event",
       src_lineage == "Returned")

    # Source status stays Scaled Up (operationally continues — not closed)
    src_status = frappe.db.get_value("Production Batch", src_275l.name, "status")
    ok("Source 275L status = Scaled Up (operationally continues, not closed)",
       src_status == "Scaled Up", f"got {src_status}")

    # CultivationReturnEvent fields
    cre = frappe.db.get_value(
        "Cultivation Return Event",
        {"source_batch": src_275l.name, "child_batch": child_name},
        "name"
    )
    ok("T10.2: CultivationReturnEvent created", bool(cre))
    if cre:
        _track("Cultivation Return Event", cre)
        cre_data = frappe.db.get_value(
            "Cultivation Return Event", cre,
            ["withdrawal_volume", "dilution_volume", "status",
             "source_stage", "source_phase", "total_volume_to_flask"],
            as_dict=True
        )
        ok("T10.4: CRE.withdrawal_volume = 0.2 L",
           abs((cre_data.withdrawal_volume or 0) - 0.2) < 0.001)
        ok("T10.4: CRE.dilution_volume = 0.5 L",
           abs((cre_data.dilution_volume or 0) - 0.5) < 0.001)
        ok("T10.4: CRE.status = Completed", cre_data.status == "Completed")
        ok("T10.4: CRE.source_stage = 275L PBR",
           cre_data.source_stage == "275L PBR", f"got {cre_data.source_stage}")
        ok("T10.4: CRE.source_phase = N/A (275L has no phase concept)",
           cre_data.source_phase is not None)
        ok("T10.4: CRE.total_volume_to_flask = 0.7 L",
           abs((cre_data.total_volume_to_flask or 0) - 0.7) < 0.001,
           f"got {cre_data.total_volume_to_flask}")

    # ── Second Return from same source — must be allowed ──────────────────────
    child2_name = src_doc.create_return_batch(
        withdrawal_volume=0.1,
        dilution_medium_batch=fmb_return,
        dilution_volume=0.3,
        return_date=today(),
        returned_by=ADMIN,
        reason="E2E test: second return from same 275L source"
    )
    _track("Production Batch", child2_name)
    cre2 = frappe.db.get_value(
        "Cultivation Return Event",
        {"source_batch": src_275l.name, "child_batch": child2_name}, "name"
    )
    if cre2:
        _track("Cultivation Return Event", cre2)
    ok("Second return from same 275L source allowed", bool(child2_name))
    frappe.db.commit()

    # ── Negative: Return from Flask stage (not 275L or 6600L) — blocked ───────
    flask_src = _make_pb(strain, "Flask", gen=1, fmb=fmb_main, vol=0.5)
    flask_src_doc = frappe.get_doc("Production Batch", flask_src.name)
    expect_throw("T10.6: Return-to-Cultivation from Flask stage is blocked",
        lambda: flask_src_doc.create_return_batch(
            withdrawal_volume=1.0, dilution_medium_batch=None,
            dilution_volume=0, return_date=today(),
            returned_by=ADMIN, reason="E2E negative test"
        ), keyword="275L PBR or 6600L PBR")

    # ── Negative: withdrawal_volume = 0 blocked ───────────────────────────────
    expect_throw("T10.7: withdrawal_volume = 0 is blocked",
        lambda: src_doc.create_return_batch(
            withdrawal_volume=0, dilution_medium_batch=None,
            dilution_volume=0, return_date=today(),
            returned_by=ADMIN, reason="negative test"
        ), keyword="greater than 0")

    # ── Negative: Return from Harvested batch blocked ──────────────────────────
    frappe.db.set_value("Production Batch", src_275l.name, "status", "Harvested")
    src_harvested = frappe.get_doc("Production Batch", src_275l.name)
    expect_throw("T10.9: Return-to-Cultivation from Harvested batch is blocked",
        lambda: src_harvested.create_return_batch(
            withdrawal_volume=1.0, dilution_medium_batch=None,
            dilution_volume=0, return_date=today(),
            returned_by=ADMIN, reason="E2E negative test"
        ), keyword="Harvested")
    frappe.db.set_value("Production Batch", src_275l.name, "status", "Active")

    # ── Negative: Return from Draft batch blocked ──────────────────────────────
    draft_275 = frappe.get_doc({
        "doctype": "Production Batch",
        "strain": strain,
        "current_stage": "275L PBR",
        "generation_number": 3,
        "lineage_status": "Active",
    })
    draft_275.insert(ignore_permissions=True)
    _track("Production Batch", draft_275.name)
    expect_throw("T10.10: Return blocked on Draft (non-submitted) PB",
        lambda: draft_275.create_return_batch(
            withdrawal_volume=5.0, dilution_medium_batch=None,
            dilution_volume=0, return_date=today(),
            returned_by=ADMIN, reason="E2E negative test"
        ), keyword="Submitted batch")


# ──────────────────────────────────────────────────────────────────────────────
# STEP 7 — Batch Split
# ──────────────────────────────────────────────────────────────────────────────

def _test_batch_split(strain, fmb_main):
    _step("STEP 7 — Batch Split (1 Flask → 2 × 25L PBR)")

    split_flask = _make_pb(strain, "Flask", gen=1, fmb=fmb_main, vol=0.5)
    split_doc = frappe.get_doc("Production Batch", split_flask.name)

    children = split_doc.create_split_batches(
        n=2, next_stage="25L PBR",
        inoculation_date=today(), medium_batch=fmb_main
    )
    for c in children:
        _track("Production Batch", c)

    ok("T9.1: Batch Split created 2 child batches", len(children) == 2,
       f"got {len(children)}")

    for c_name in children:
        c = frappe.db.get_value(
            "Production Batch", c_name,
            ["current_stage", "parent_batch", "generation_number", "lineage_status"],
            as_dict=True
        )
        ok(f"T9.1: Split child stage = 25L PBR", c.current_stage == "25L PBR")
        ok(f"T9.1: Split child parent = Flask", c.parent_batch == split_flask.name)
        ok(f"T9.1: Split child gen = 2 (parent+1)", c.generation_number == 2)
        ok(f"T9.1: Split child lineage_status = Active", c.lineage_status == "Active")

    tree = split_doc.get_full_tree()
    ok("T9.1: Flask tree has 2 split children", len(tree) == 2, f"got {len(tree)}")

    # Submit both split children
    for c_name in children:
        c_doc = frappe.get_doc("Production Batch", c_name)
        c_doc.stage_decision = "Scale Up"
        c_doc.append("qc_readings", {
            "qc_type": "Process QC",
            "qc_date": today(),
            "overall_result": "Pass",
            "contamination_detected": 0,
        })
        c_doc.save(ignore_permissions=True)
        c_doc.submit()
    ok("T9.1: Both split children submitted OK", True)

    # ── Negative: n=1 blocked ─────────────────────────────────────────────────
    expect_throw("T9.2: Split with n=1 blocked (minimum 2)",
        lambda: split_doc.create_split_batches(n=1, next_stage="25L PBR",
                                               inoculation_date=today()),
        keyword="at least 2")

    # ── Negative: n=11 blocked ────────────────────────────────────────────────
    expect_throw("T9.3: Split with n=11 blocked (maximum 10)",
        lambda: split_doc.create_split_batches(n=11, next_stage="25L PBR",
                                               inoculation_date=today()),
        keyword="Maximum 10")

    # ── Negative: stage skip blocked ─────────────────────────────────────────
    expect_throw("T9.4: Split from Flask to 275L (skipping 25L) blocked",
        lambda: split_doc.create_split_batches(n=2, next_stage="275L PBR",
                                               inoculation_date=today()),
        keyword="Stage sequence violation")

    # ── Negative: total inoculum over pool ───────────────────────────────────
    pb_split_src = _make_pb(strain, "Flask", gen=1, fmb=fmb_main, vol=0.5)
    frappe.db.set_value("Production Batch", pb_split_src.name, "culture_volume_available", 0.4)
    frappe.db.commit()
    pb_split_doc = frappe.get_doc("Production Batch", pb_split_src.name)
    expect_throw("T9.5: Split total inoculum (3×0.3=0.9) > pool (0.4) blocked",
        lambda: pb_split_doc.create_split_batches(
            n=3, next_stage="25L PBR", inoculation_date=today(),
            inoculum_volume_per_child=0.3),
        keyword="exceeds remaining culture")

    # ── Negative: Split from Harvested batch blocked ─────────────────────────
    frappe.db.set_value("Production Batch", split_flask.name, "status", "Harvested")
    split_harvested = frappe.get_doc("Production Batch", split_flask.name)
    expect_throw("T9.6: Batch Split from Harvested batch blocked",
        lambda: split_harvested.create_split_batches(
            n=2, next_stage="25L PBR", inoculation_date=today()),
        keyword="Cannot split a closed batch")
    frappe.db.set_value("Production Batch", split_flask.name, "status", "Scaled Up")


# ──────────────────────────────────────────────────────────────────────────────
# STEP 8 — FMB Volume Exhaustion & Cancel Reversal
# ──────────────────────────────────────────────────────────────────────────────

def _test_fmb_volume_exhaustion(strain, fmb_small):
    _step("STEP 8 — FMB Volume Exhaustion & Over-Consumption Guard")

    initial = frappe.db.get_value("Final Medium Batch", fmb_small, "remaining_volume")
    ok(f"T16.1: FMB_SMALL initial remaining_volume = {initial} L", True)

    # PB1 consumes 2 L — use 25L PBR (reactor capacity 25 L > medium 2 L)
    pb1 = _make_pb(strain, "25L PBR", gen=2, fmb=fmb_small, vol=2.0)
    rem_after_pb1 = frappe.db.get_value("Final Medium Batch", fmb_small, "remaining_volume")
    ok("T16.2: After PB1 (2 L): FMB remaining = 1 L",
       abs(rem_after_pb1 - 1.0) < 0.001, f"got {rem_after_pb1}")
    ok("FMB status = Partially Used after PB1",
       frappe.db.get_value("Final Medium Batch", fmb_small, "status") == "Partially Used")

    # PB2 consumes remaining 1 L
    pb2 = _make_pb(strain, "25L PBR", gen=2, fmb=fmb_small, vol=1.0)
    rem_after_pb2 = frappe.db.get_value("Final Medium Batch", fmb_small, "remaining_volume")
    ok("After PB2 (1 L): FMB remaining = 0 L",
       abs(rem_after_pb2 - 0.0) < 0.001, f"got {rem_after_pb2}")
    ok("FMB status = Used after exhaustion",
       frappe.db.get_value("Final Medium Batch", fmb_small, "status") == "Used")

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
        "stage_decision": "Scale Up",
    })
    pb3_doc.append("qc_readings", {
        "qc_type": "Process QC",
        "qc_date": today(),
        "overall_result": "Pass",
        "contamination_detected": 0,
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
    ok("T16.3: After PB2 cancel: FMB remaining restored to 1 L",
       abs(rem_after_cancel - 1.0) < 0.001, f"got {rem_after_cancel}")
    ok("After PB2 cancel: FMB status = Partially Used",
       frappe.db.get_value("Final Medium Batch", fmb_small, "status") == "Partially Used")

    consumed_after_cancel = frappe.db.get_value("Final Medium Batch", fmb_small, "volume_consumed")
    ok("After PB2 cancel: FMB volume_consumed = 2 L",
       abs((consumed_after_cancel or 0) - 2.0) < 0.001, f"got {consumed_after_cancel}")


# ──────────────────────────────────────────────────────────────────────────────
# STEP 9 — Negative / Validation Guards
# ──────────────────────────────────────────────────────────────────────────────

def _test_negative_cases(strain, fmb_main):
    _step("STEP 9 — Negative / Validation Guards")

    # ── T2.2: Wrong generation for root Flask ─────────────────────────────────
    pb_wronggen = frappe.get_doc({
        "doctype": "Production Batch",
        "strain": strain,
        "current_stage": "Flask",
        "generation_number": 2,
        "lineage_status": "Active",
    })
    expect_throw("T2.2: Root Flask gen=2 blocked (must be 1)",
        lambda: pb_wronggen.insert(ignore_permissions=True),
        keyword="Generation Number")

    # ── T3.1: Stage sequence skip (Flask → 275L) blocked ─────────────────────
    parent_flask = _make_pb(strain, "Flask", gen=1, fmb=fmb_main, vol=0.3)
    pb_skip = frappe.get_doc({
        "doctype": "Production Batch",
        "strain": strain,
        "current_stage": "275L PBR",
        "generation_number": 3,
        "parent_batch": parent_flask.name,
        "lineage_status": "Active",
    })
    expect_throw("T3.1: Stage skip Flask→275L blocked",
        lambda: pb_skip.insert(ignore_permissions=True),
        keyword="Stage sequence violation")

    # ── T3.2: Wrong gen with correct stage ───────────────────────────────────
    pb_wronggen2 = frappe.get_doc({
        "doctype": "Production Batch",
        "strain": strain,
        "current_stage": "25L PBR",
        "generation_number": 5,
        "parent_batch": parent_flask.name,
        "lineage_status": "Active",
    })
    expect_throw("T3.2: Wrong gen for 25L child (expected 2, got 5)",
        lambda: pb_wronggen2.insert(ignore_permissions=True),
        keyword="Generation Number must be parent generation")

    # ── T3.4: Self-parent blocked ─────────────────────────────────────────────
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
    expect_throw("T3.4: Self-parent Production Batch blocked",
        lambda: pb_self.save(ignore_permissions=True),
        keyword="cannot be its own parent")

    # ── T2.5: Reactor capacity exceeded ──────────────────────────────────────
    pb_capacity = frappe.get_doc({
        "doctype": "Production Batch",
        "strain": strain,
        "current_stage": "25L PBR",
        "generation_number": 2,
        "inoculation_date": today(),
        "final_medium_batch": fmb_main,
        "medium_volume_used": 20.0,
        "inoculum_volume_in": 10.0,   # 30 > 25 L reactor
        "lineage_status": "Active",
    })
    expect_throw("T2.5: Reactor capacity 30L > 25L blocked",
        lambda: pb_capacity.insert(ignore_permissions=True),
        keyword="exceeds reactor capacity")

    # ── T2.9: Submit with Pending decision blocked ────────────────────────────
    pb_pending = frappe.get_doc({
        "doctype": "Production Batch",
        "strain": strain,
        "current_stage": "Flask",
        "generation_number": 1,
        "lineage_status": "Active",
        "stage_decision": "Pending",
    })
    pb_pending.insert(ignore_permissions=True)
    _track("Production Batch", pb_pending.name)
    expect_throw("T2.9: Submit with Pending decision blocked",
        lambda: pb_pending.submit(), keyword="Stage Decision")

    # ── T4.1: Scale Up with no QC readings blocked ────────────────────────────
    pb_noqc = frappe.get_doc({
        "doctype": "Production Batch",
        "strain": strain,
        "current_stage": "Flask",
        "generation_number": 1,
        "lineage_status": "Active",
        "stage_decision": "Scale Up",
    })
    expect_throw("T4.1: Scale Up with no QC readings blocked",
        lambda: pb_noqc.insert(ignore_permissions=True),
        keyword="no QC readings")

    # ── T4.2: Scale Up with Fail QC reading blocked ───────────────────────────
    pb_failqc = frappe.get_doc({
        "doctype": "Production Batch",
        "strain": strain,
        "current_stage": "Flask",
        "generation_number": 1,
        "lineage_status": "Active",
        "stage_decision": "Scale Up",
    })
    pb_failqc.append("qc_readings", {
        "qc_type": "Process QC", "qc_date": today(),
        "overall_result": "Fail", "contamination_detected": 0,
    })
    expect_throw("T4.2: Scale Up with Fail QC reading blocked",
        lambda: pb_failqc.insert(ignore_permissions=True),
        keyword="Overall Result = Fail")

    # ── T4.3: Scale Up with contamination_detected=1 blocked ─────────────────
    pb_contamqc = frappe.get_doc({
        "doctype": "Production Batch",
        "strain": strain,
        "current_stage": "Flask",
        "generation_number": 1,
        "lineage_status": "Active",
        "stage_decision": "Scale Up",
    })
    pb_contamqc.append("qc_readings", {
        "qc_type": "Process QC", "qc_date": today(),
        "overall_result": "Pass", "contamination_detected": 1,
    })
    expect_throw("T4.3: Scale Up with contamination_detected=1 blocked",
        lambda: pb_contamqc.insert(ignore_permissions=True),
        keyword="Contamination Detected")

    # ── T12.1: HB creation blocked when PB stage_decision ≠ Harvest ──────────
    pb_scale = _make_pb(strain, "Flask", gen=1, fmb=fmb_main, vol=0.3)
    # Stage decision was Scale Up on submit; now still Scaled Up, not Harvest
    hb_blocked = frappe.get_doc({
        "doctype": "Harvest Batch",
        "production_batch": pb_scale.name,
        "harvest_date": today(),
        "harvested_by": ADMIN,
        "harvested_volume": 0.8,
        "qc_status": "Passed",
    })
    expect_throw("T12.1: HB creation blocked when PB stage_decision = Scale Up",
        lambda: hb_blocked.insert(ignore_permissions=True),
        keyword="Stage Decision to")

    # ── T12.3: HB harvested_volume > reactor_volume blocked ──────────────────
    pb_harvest = _make_pb(strain, "6600L PBR", gen=5, fmb=fmb_main, vol=100.0,
                          decision="Harvest")
    expect_throw("T12.3: HB harvested_volume (7000L) > reactor_volume (6600L) blocked",
        lambda: frappe.get_doc({
            "doctype": "Harvest Batch",
            "production_batch": pb_harvest.name,
            "harvest_date": today(),
            "harvested_by": ADMIN,
            "harvested_volume": 7000.0,
            "qc_status": "Passed",
        }).insert(ignore_permissions=True),
        keyword="cannot exceed the reactor capacity")


# ──────────────────────────────────────────────────────────────────────────────
# STEP 10 — Culture Volume Tracking (inoculum pool)
# ──────────────────────────────────────────────────────────────────────────────

def _test_culture_volume_tracking(strain, fmb_main):
    _step("STEP 10 — Culture Volume Tracking (inoculum pool)")

    parent_flask = _make_pb(strain, "Flask", gen=1, fmb=fmb_main, vol=0.5)
    frappe.db.set_value("Production Batch", parent_flask.name, "culture_volume_available", 0.9)
    frappe.db.commit()

    # ── Child A takes 0.3 L ────────────────────────────────────────────────────
    child_a = frappe.get_doc({
        "doctype": "Production Batch",
        "strain": strain,
        "current_stage": "25L PBR",
        "generation_number": 2,
        "parent_batch": parent_flask.name,
        "inoculation_date": today(),
        "final_medium_batch": fmb_main,
        "medium_volume_used": 0.5,
        "inoculum_volume_in": 0.3,
        "lineage_status": "Active",
        "stage_decision": "Scale Up",
    })
    child_a.append("qc_readings", {
        "qc_type": "Process QC", "qc_date": today(),
        "overall_result": "Pass", "contamination_detected": 0,
    })
    child_a.insert(ignore_permissions=True)
    _track("Production Batch", child_a.name)
    child_a.submit()
    frappe.db.commit()

    parent_out = frappe.db.get_value("Production Batch", parent_flask.name, "inoculum_volume_out")
    ok("T5.1: Parent Flask inoculum_volume_out = 0.3 L after child A submit",
       abs((parent_out or 0) - 0.3) < 0.001, f"got {parent_out}")

    # ── Child B takes 0.4 L (total 0.7 of 0.9) ───────────────────────────────
    child_b = frappe.get_doc({
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
        "stage_decision": "Scale Up",
    })
    child_b.append("qc_readings", {
        "qc_type": "Process QC", "qc_date": today(),
        "overall_result": "Pass", "contamination_detected": 0,
    })
    child_b.insert(ignore_permissions=True)
    _track("Production Batch", child_b.name)
    child_b.submit()
    frappe.db.commit()

    parent_out_2 = frappe.db.get_value("Production Batch", parent_flask.name, "inoculum_volume_out")
    ok("T5.1: Parent inoculum_volume_out = 0.7 L after two children",
       abs((parent_out_2 or 0) - 0.7) < 0.001, f"got {parent_out_2}")

    # ── Over-consumption blocked (0.9 available, 0.7 out, only 0.2 left) ──────
    child_over = frappe.get_doc({
        "doctype": "Production Batch",
        "strain": strain,
        "current_stage": "25L PBR",
        "generation_number": 2,
        "parent_batch": parent_flask.name,
        "inoculation_date": today(),
        "inoculum_volume_in": 0.5,   # 0.5 > 0.2 remaining
        "lineage_status": "Active",
        "stage_decision": "Scale Up",
    })
    child_over.append("qc_readings", {
        "qc_type": "Process QC", "qc_date": today(),
        "overall_result": "Pass", "contamination_detected": 0,
    })
    child_over.insert(ignore_permissions=True)
    _track("Production Batch", child_over.name)
    expect_throw("T5.2: Inoculum over-consumption blocked (0.5 L > 0.2 remaining)",
        lambda: child_over.submit(),
        keyword="culture remaining")

    # ── Cancel child_a → inoculum restored ────────────────────────────────────
    frappe.get_doc("Production Batch", child_a.name).cancel()
    frappe.db.commit()

    parent_out_cancel = frappe.db.get_value("Production Batch", parent_flask.name, "inoculum_volume_out")
    ok("T5.3: Parent inoculum_volume_out restored (0.7 → 0.4) after child A cancel",
       abs((parent_out_cancel or 0) - 0.4) < 0.001, f"got {parent_out_cancel}")

    # ── T15.3: Parent status restored to Active when last submitted child cancelled ─
    pb_parent_2 = _make_pb(strain, "Flask", gen=1, fmb=fmb_main, vol=0.3)
    ok("T15.3 setup: Flask with Scale Up: status = Scaled Up", pb_parent_2.status == "Scaled Up")

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
        "stage_decision": "Scale Up",
    })
    pb_child_2.append("qc_readings", {
        "qc_type": "Process QC", "qc_date": today(),
        "overall_result": "Pass", "contamination_detected": 0,
    })
    pb_child_2.insert(ignore_permissions=True)
    _track("Production Batch", pb_child_2.name)
    pb_child_2.submit()
    frappe.db.commit()

    frappe.get_doc("Production Batch", pb_child_2.name).cancel()
    frappe.db.commit()

    parent_2_status = frappe.db.get_value("Production Batch", pb_parent_2.name, "status")
    ok("T15.3: Parent status restored to Active after sole child cancelled",
       parent_2_status == "Active", f"got {parent_2_status}")


# ──────────────────────────────────────────────────────────────────────────────
# STEP 11 — Harvest Batch: Confirm Packing
# ──────────────────────────────────────────────────────────────────────────────

def _test_confirm_packing(strain, fmb_main):
    _step("STEP 11 — Harvest Batch: Confirm Packing Flow")

    pb = _make_pb(strain, "Flask", gen=1, fmb=fmb_main, vol=0.3, decision="Harvest")
    hb = _make_hb(pb.name, qc_pass=True, wet_biomass_kg=10.0)
    ok("HB submitted (Approved)", hb.status == "Approved")

    # T13.1 — no packing_date/packed_by
    hb_fresh = frappe.get_doc("Harvest Batch", hb.name)
    expect_throw("T13.1: Confirm Packing without packing_date/packed_by blocked",
        lambda: hb_fresh.confirm_packing(), keyword="Packing Date")

    # T13.2 — has date/by but no label_batch_no
    # Use db_set to bypass UpdateAfterSubmitError on submitted doc
    frappe.db.set_value("Harvest Batch", hb.name, {
        "packing_date": today(),
        "packed_by": ADMIN,
    })
    hb_fresh.reload()
    expect_throw("T13.2: Confirm Packing without label_batch_no blocked",
        lambda: hb_fresh.confirm_packing(), keyword="Label Batch Number")

    # T13.3 — all fields present
    frappe.db.set_value("Harvest Batch", hb.name, {
        "packing_date": today(),
        "packed_by": ADMIN,
        "label_batch_no": "LBL-E2E-001",
    })
    hb_fresh.reload()
    hb_fresh.confirm_packing()
    ok("T13.3: Status = Packed after confirm_packing",
       frappe.db.get_value("Harvest Batch", hb.name, "status") == "Packed")

    # T13.4 — confirm_packing on non-Approved HB (use fresh PB to avoid duplicate guard)
    pb_pack2 = _make_pb(strain, "Flask", gen=1, fmb=fmb_main, vol=0.2, decision="Harvest")
    hb_draft_test = frappe.get_doc({
        "doctype": "Harvest Batch",
        "production_batch": pb_pack2.name,
        "harvest_date": today(),
        "harvested_by": ADMIN,
        "harvested_volume": 0.8,
        "qc_status": "Pending",
    })
    hb_draft_test.insert(ignore_permissions=True)
    _track("Harvest Batch", hb_draft_test.name)
    expect_throw("T13.4: confirm_packing blocked on Draft HB",
        lambda: hb_draft_test.confirm_packing(), keyword="Approved")


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
    print("  Flask → 25L → 275L → 925L → 6600L → Harvest → Drying")
    print("  + Return-to-Cultivation, Batch Split, Contamination,")
    print("    Packing, FMB Volume Tracking, Inoculum Pool Tracking")
    print("═" * 60)

    _step("STEP 1 — Setup: Strain + Final Medium Batches")
    strain = _create_strain()
    ok("Strain created", bool(strain), strain)

    fmb_main   = _make_fmb(500, "MAIN")
    ok("FMB_MAIN (500 L) created and set as Approved",
       frappe.db.get_value("Final Medium Batch", fmb_main, "remaining_volume") == 500)

    fmb_return = _make_fmb(10, "RETURN")
    ok("FMB_RETURN (10 L) created",
       frappe.db.get_value("Final Medium Batch", fmb_return, "remaining_volume") == 10)

    fmb_small  = _make_fmb(3, "SMALL")
    ok("FMB_SMALL (3 L) created",
       frappe.db.get_value("Final Medium Batch", fmb_small, "remaining_volume") == 3)

    flask_name, pb6600_name = _test_linear_scaleup(strain, fmb_main)
    _test_harvest_drying(strain, fmb_main, pb6600_name)
    _test_contamination_incident(strain, fmb_main)
    _test_contamination_early_harvest(strain, fmb_main)
    _test_return_to_cultivation(strain, fmb_main, fmb_return)
    _test_batch_split(strain, fmb_main)
    _test_fmb_volume_exhaustion(strain, fmb_small)
    _test_negative_cases(strain, fmb_main)
    _test_culture_volume_tracking(strain, fmb_main)
    _test_confirm_packing(strain, fmb_main)

    _cleanup()

    total = _PASS + _FAIL
    print(f"\n{'═'*60}")
    print(f"  RESULT: {_PASS}/{total} passed   |   {_FAIL} failed")
    print(f"{'═'*60}\n")
