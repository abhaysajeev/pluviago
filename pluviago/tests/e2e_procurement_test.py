"""
Pluviago End-to-End Backend Test — Procurement Pipeline
========================================================
Tests:
  1. AVL child table schema durability
  2. PO validation — item-group based detection, unapproved vendor hard-block
  3. PR → RMB auto-creation: item-group detection, duplicate prevention, per-row errors
  4. RMB lifecycle (Purchased): Draft → QC + COA → Submit → Cancel guard
  5. RMB lifecycle (In-house / DI Water): no supplier, no COA, QC only
  6. View RMBs — purchase_receipt filter works

Run with:
  bench --site replica1.local execute pluviago.tests.e2e_procurement_test.run
"""

import frappe
from frappe.utils import today, add_days

# ── Constants ─────────────────────────────────────────────────────────────────
COMPANY   = "Pluviago Biotech Pvt. Ltd."
WAREHOUSE = "Chemical Store RT - PB"
SUPPLIER  = "Sisco Research Labs"
SUPPLIER2 = "Qualigens Fine Chemicals"   # used for unapproved-vendor test

ITEM_1      = "CHEM-001"   # Calcium Chloride Dihydrate  — Base Salts
ITEM_2      = "CHEM-002"   # Magnesium Sulphate           — Base Salts
ITEM_DI     = "CONS-001"   # DI Water                    — Lab Consumables (in-house)
ITEM_ASSET  = "AST-OD-001" # Spectrophotometer            — All Item Groups (not trackable)

_CREATED  = []
_PASS = 0
_FAIL = 0


# ── Helpers ───────────────────────────────────────────────────────────────────

def ok(label, condition, detail=""):
    global _PASS, _FAIL
    if condition:
        _PASS += 1
        print(f"  ✓  {label}")
    else:
        _FAIL += 1
        print(f"  ✗  FAIL: {label}" + (f" — {detail}" if detail else ""))


def expect_throw(label, fn):
    global _PASS, _FAIL
    try:
        fn()
        _FAIL += 1
        print(f"  ✗  FAIL: {label} — expected error but none raised")
    except Exception as e:
        _PASS += 1
        print(f"  ✓  {label} (blocked: {str(e)[:90]})")


def _track(doctype, name):
    _CREATED.append((doctype, name))
    return name


def _step(title):
    print(f"\n{'─'*60}")
    print(f"  {title}")
    print(f"{'─'*60}")


def _make_av(supplier, items, days_valid=365):
    av = frappe.get_doc({
        "doctype": "Approved Vendor",
        "supplier": supplier,
        "approval_status": "Approved",
        "approval_date": today(),
        "valid_upto": add_days(today(), days_valid),
        "approved_by": "Administrator",
        "approved_items": [{"item_code": item} for item in items],
    })
    av.insert(ignore_permissions=True)
    _track("Approved Vendor", av.name)
    return av


def _make_po(supplier, items):
    po = frappe.get_doc({
        "doctype": "Purchase Order",
        "company": COMPANY,
        "supplier": supplier,
        "schedule_date": add_days(today(), 7),
        "items": [
            {
                "item_code": item,
                "qty": 500,
                "uom": "Gram",
                "rate": 1.0,
                "warehouse": WAREHOUSE,
                "schedule_date": add_days(today(), 7),
            }
            for item in items
        ],
    })
    po.insert(ignore_permissions=True)
    po.submit()
    _track("Purchase Order", po.name)
    return po


def _make_pr(supplier, po_name, items_meta):
    items = []
    for m in items_meta:
        items.append({
            "item_code": m["item_code"],
            "item_name": frappe.db.get_value("Item", m["item_code"], "item_name") or m["item_code"],
            "qty": m.get("qty", 500),
            "uom": "Gram",
            "rate": 1.0,
            "warehouse": WAREHOUSE,
            "purchase_order": po_name,
            "custom_supplier_batch_no": m.get("supplier_batch_no", ""),
            "custom_mfg_date": m.get("mfg_date", add_days(today(), -30)),
            "custom_expiry_date": m.get("expiry_date", add_days(today(), 700)),
            "custom_storage_condition": m.get("storage_condition", "Room Temperature"),
        })
    pr = frappe.get_doc({
        "doctype": "Purchase Receipt",
        "company": COMPANY,
        "supplier": supplier,
        "posting_date": today(),
        "items": items,
    })
    pr.insert(ignore_permissions=True)
    pr.submit()
    _track("Purchase Receipt", pr.name)
    return pr


def _cleanup():
    print("\n  [cleanup]")
    for dt, name in reversed(_CREATED):
        try:
            doc = frappe.get_doc(dt, name)
            if doc.docstatus == 1:
                doc.cancel()
        except Exception:
            pass
        try:
            frappe.delete_doc(dt, name, force=True, ignore_permissions=True)
        except Exception:
            pass
    frappe.db.commit()


# ── STEP 1 ────────────────────────────────────────────────────────────────────

def _test_avl_schema():
    _step("STEP 1 — Approved Vendor List: child table schema durability")

    av = _make_av(SUPPLIER, [ITEM_1, ITEM_2])
    ok("AVL created", bool(av.name))
    ok("AVL has 2 approved_items rows", len(av.approved_items) == 2)

    children = frappe.db.sql(
        "SELECT item_code FROM `tabApproved Vendor Item` WHERE parent = %s", av.name
    )
    codes = {r[0] for r in children}
    ok("Approved Vendor Item rows in DB = 2", len(codes) == 2, f"got {len(codes)}")
    ok(f"ITEM_1 ({ITEM_1}) in child table", ITEM_1 in codes)
    ok(f"ITEM_2 ({ITEM_2}) in child table", ITEM_2 in codes)

    is_custom = frappe.db.get_value("DocType", "Approved Vendor Item", "custom")
    ok("Approved Vendor Item is proper app DocType (custom=0)", not is_custom)

    field_meta = frappe.db.get_value(
        "DocField",
        {"parent": "Approved Vendor", "fieldname": "item_code"},
        ["hidden", "reqd"], as_dict=True,
    )
    ok("Legacy AVL.item_code is hidden", field_meta and field_meta.hidden == 1)
    ok("Legacy AVL.item_code is not required", field_meta and field_meta.reqd == 0)

    stale = frappe.db.get_all("Custom Field",
        filters={"dt": "Approved Vendor", "fieldname": "approved_items"}, fields=["name"])
    ok("No stale Custom Field for approved_items", len(stale) == 0, f"found: {stale}")

    return av


# ── STEP 2 ────────────────────────────────────────────────────────────────────

def _test_po_validation(av):
    _step("STEP 2 — PO Validation: item-group detection, hard-block on unapproved")

    # Approved supplier + approved items → PO goes through
    po = _make_po(SUPPLIER, [ITEM_1, ITEM_2])
    ok("PO with approved supplier submitted OK", po.docstatus == 1)

    # Unapproved supplier ordering a purchased raw material → hard-block on insert/save
    expect_throw("PO with unapproved supplier for CHEM item is hard-blocked",
        lambda: frappe.get_doc({
            "doctype": "Purchase Order",
            "company": COMPANY,
            "supplier": SUPPLIER2,
            "schedule_date": add_days(today(), 7),
            "items": [{
                "item_code": ITEM_1,
                "qty": 100, "uom": "Gram", "rate": 1.0,
                "warehouse": WAREHOUSE,
                "schedule_date": add_days(today(), 7),
            }],
        }).insert(ignore_permissions=True))

    # Non-trackable item (asset) → validation skips it, no error
    from pluviago.pluviago_biotech.overrides.purchase_order import validate as po_validate
    class _FakeRow:
        item_code = ITEM_ASSET
        item_name = "Spectrophotometer"
    class _FakeDoc:
        items = [_FakeRow()]
        supplier = SUPPLIER2
    po_validate(_FakeDoc())
    ok("Non-trackable item (asset group) is skipped — no error raised", True)

    # DI Water (Lab Consumables) is also skipped by PO validation — it's never purchased
    class _FakeRowDI:
        item_code = ITEM_DI
        item_name = "DI Water"
    class _FakeDocDI:
        items = [_FakeRowDI()]
        supplier = SUPPLIER2
    po_validate(_FakeDocDI())
    ok("DI Water (Lab Consumables) skipped by PO AVL check — not a purchased chemical", True)

    return po


# ── STEP 3 ────────────────────────────────────────────────────────────────────

def _test_pr_rmb_creation(po):
    _step("STEP 3 — PR → RMB Auto-Creation (item-group based)")

    from pluviago.pluviago_biotech.overrides.purchase_receipt import create_raw_material_batches

    pr = _make_pr(SUPPLIER, po.name, [
        {"item_code": ITEM_1, "qty": 500, "supplier_batch_no": "SRL-BATCH-001",
         "expiry_date": add_days(today(), 700)},
        {"item_code": ITEM_2, "qty": 300, "supplier_batch_no": "SRL-BATCH-002",
         "expiry_date": add_days(today(), 600)},
    ])
    ok("Purchase Receipt submitted", pr.docstatus == 1)

    result = create_raw_material_batches(pr.name)
    created, skipped, errors = result["created"], result["skipped"], result["errors"]

    ok("2 RMBs created", len(created) == 2, f"got {len(created)}: {created}")
    ok("0 errors", len(errors) == 0, f"{errors}")
    ok("0 skipped on first run", len(skipped) == 0, f"{skipped}")

    for c in created:
        _track("Raw Material Batch", c["rmb_name"])

    rmb1 = frappe.db.get_value(
        "Raw Material Batch",
        {"purchase_receipt": pr.name, "item_code": ITEM_1},
        ["supplier_batch_no", "received_qty", "warehouse", "qc_status",
         "coa_verified", "batch_source"],
        as_dict=True,
    )
    ok("RMB1: batch_source = Purchased", rmb1 and rmb1.batch_source == "Purchased")
    ok("RMB1: supplier_batch_no = SRL-BATCH-001", rmb1 and rmb1.supplier_batch_no == "SRL-BATCH-001")
    ok("RMB1: received_qty = 500", rmb1 and rmb1.received_qty == 500)
    ok("RMB1: warehouse set", rmb1 and bool(rmb1.warehouse))
    ok("RMB1: qc_status = Pending", rmb1 and rmb1.qc_status == "Pending")
    ok("RMB1: coa_verified = 0", rmb1 and rmb1.coa_verified == 0)

    # Duplicate run → all skipped
    result2 = create_raw_material_batches(pr.name)
    ok("Second run: 0 created", len(result2["created"]) == 0)
    ok("Second run: 2 skipped", len(result2["skipped"]) == 2, f"got {len(result2['skipped'])}")

    # Draft PR blocked
    pr_draft = frappe.get_doc({
        "doctype": "Purchase Receipt",
        "company": COMPANY, "supplier": SUPPLIER, "posting_date": today(),
        "items": [{"item_code": ITEM_1, "qty": 10, "uom": "Gram",
                   "rate": 1.0, "warehouse": WAREHOUSE, "purchase_order": po.name}],
    })
    pr_draft.insert(ignore_permissions=True)
    _track("Purchase Receipt", pr_draft.name)
    expect_throw("create_raw_material_batches on Draft PR is blocked",
        lambda: create_raw_material_batches(pr_draft.name))

    return pr, created


# ── STEP 4 ────────────────────────────────────────────────────────────────────

def _test_rmb_lifecycle_purchased(created_rmbs):
    _step("STEP 4 — RMB Lifecycle (Purchased): QC + COA required before submit")

    rmb_name = created_rmbs[0]["rmb_name"]

    # Block: qc_status=Pending
    rmb_doc = frappe.get_doc("Raw Material Batch", rmb_name)
    expect_throw("Submit blocked when qc_status=Pending", lambda: rmb_doc.submit())
    frappe.db.rollback()

    # Block: qc_status=Approved but coa_verified=0
    frappe.db.set_value("Raw Material Batch", rmb_name, "qc_status", "Approved")
    frappe.db.commit()
    rmb_doc = frappe.get_doc("Raw Material Batch", rmb_name)
    expect_throw("Submit blocked when coa_verified=0 (Purchased batch)",
        lambda: rmb_doc.submit())
    frappe.db.rollback()

    # Pass: QC Approved + COA verified
    frappe.db.set_value("Raw Material Batch", rmb_name, {
        "qc_status": "Approved",
        "coa_verified": 1,
        "coa_verified_by": "Administrator",
        "qc_checked_by": "Administrator",
        "qc_date": today(),
    })
    frappe.db.commit()
    rmb_doc = frappe.get_doc("Raw Material Batch", rmb_name)
    rmb_doc.submit()
    ok("RMB submitted after QC Approved + COA verified", rmb_doc.docstatus == 1)
    ok("RMB status = Approved after submit",
       frappe.db.get_value("Raw Material Batch", rmb_name, "status") == "Approved")
    ok("RMB remaining_qty = received_qty after submit",
       frappe.db.get_value("Raw Material Batch", rmb_name, "remaining_qty") == 500)

    # Cancel — no consumption
    rmb_doc.cancel()
    ok("RMB cancelled (no consumption)", rmb_doc.docstatus == 2)
    ok("RMB status = Received after cancel",
       frappe.db.get_value("Raw Material Batch", rmb_name, "status") == "Received")

    # Cancel guard — consumed_qty > 0
    rmb2_name = created_rmbs[1]["rmb_name"]
    frappe.db.set_value("Raw Material Batch", rmb2_name, {
        "qc_status": "Approved", "coa_verified": 1,
        "coa_verified_by": "Administrator",
        "qc_checked_by": "Administrator", "qc_date": today(),
    })
    frappe.db.commit()
    rmb_doc2 = frappe.get_doc("Raw Material Batch", rmb2_name)
    rmb_doc2.submit()

    frappe.db.set_value("Raw Material Batch", rmb2_name, "consumed_qty", 50.0)
    frappe.db.commit()
    rmb_doc2 = frappe.get_doc("Raw Material Batch", rmb2_name)
    cancel_blocked = False
    try:
        rmb_doc2.cancel()
    except Exception:
        cancel_blocked = True
    ok("Cancel blocked when consumed_qty > 0", cancel_blocked)

    # Restore for cleanup
    frappe.db.set_value("Raw Material Batch", rmb2_name,
        {"docstatus": 1, "consumed_qty": 0, "status": "Approved"})
    frappe.db.commit()


# ── STEP 5 ────────────────────────────────────────────────────────────────────

def _test_rmb_lifecycle_inhouse():
    _step("STEP 5 — RMB Lifecycle (In-house / DI Water): no supplier, no COA needed")

    di_name = frappe.db.get_value("Item", ITEM_DI, "item_name") or "DI Water"

    # Create DI Water RMB manually — no supplier, no batch number, no expiry
    rmb = frappe.new_doc("Raw Material Batch")
    rmb.batch_source    = "In-house"
    rmb.material_name   = di_name
    rmb.item_code       = ITEM_DI
    rmb.received_qty    = 50.0
    rmb.received_qty_uom = "Litre"
    rmb.received_date   = today()
    rmb.storage_condition = "Room Temperature"
    rmb.warehouse       = WAREHOUSE
    rmb.qc_status       = "Pending"
    rmb.insert(ignore_permissions=True)
    frappe.db.commit()   # commit insert before submit attempt so rollback doesn't undo it
    _track("Raw Material Batch", rmb.name)

    ok("In-house RMB inserted (no supplier, no batch no, no expiry)", bool(rmb.name))
    ok("batch_source = In-house", rmb.batch_source == "In-house")
    ok("supplier is blank", not rmb.supplier)

    # Block: qc_status still Pending
    expect_throw("In-house RMB: submit blocked when qc_status=Pending",
        lambda: rmb.submit())
    frappe.db.rollback()

    # Pass: only QC Approved needed — no COA required for In-house
    frappe.db.set_value("Raw Material Batch", rmb.name, {
        "qc_status": "Approved",
        "qc_checked_by": "Administrator",
        "qc_date": today(),
    })
    frappe.db.commit()
    rmb = frappe.get_doc("Raw Material Batch", rmb.name)
    rmb.submit()
    ok("In-house RMB submitted with only QC Approved (no COA needed)", rmb.docstatus == 1)
    ok("In-house RMB status = Approved",
       frappe.db.get_value("Raw Material Batch", rmb.name, "status") == "Approved")
    ok("In-house RMB remaining_qty = 50",
       frappe.db.get_value("Raw Material Batch", rmb.name, "remaining_qty") == 50.0)

    # Cancel
    rmb.cancel()
    ok("In-house RMB cancelled", rmb.docstatus == 2)


# ── STEP 6 ────────────────────────────────────────────────────────────────────

def _test_purchase_receipt_link(pr):
    _step("STEP 6 — Purchase Receipt link: View RMBs filter works")

    rmbs = frappe.db.sql(
        "SELECT name, item_code FROM `tabRaw Material Batch` WHERE purchase_receipt = %s",
        pr.name, as_dict=True,
    )
    ok(f"RMBs linked to PR ({pr.name}) found via purchase_receipt filter",
       len(rmbs) == 2, f"got {len(rmbs)}")
    codes = {r["item_code"] for r in rmbs}
    ok(f"ITEM_1 ({ITEM_1}) found", ITEM_1 in codes)
    ok(f"ITEM_2 ({ITEM_2}) found", ITEM_2 in codes)


# ── Entry point ───────────────────────────────────────────────────────────────

def run():
    global _PASS, _FAIL
    _PASS = 0
    _FAIL = 0

    frappe.set_user("Administrator")
    print("\n" + "═" * 60)
    print("  PLUVIAGO — END-TO-END PROCUREMENT TEST")
    print("  AVL · PO Validation · PR→RMB · Purchased RMB · In-house RMB")
    print("═" * 60)

    try:
        av          = _test_avl_schema()
        po          = _test_po_validation(av)
        pr, created = _test_pr_rmb_creation(po)
        _test_rmb_lifecycle_purchased(created)
        _test_rmb_lifecycle_inhouse()
        _test_purchase_receipt_link(pr)
    finally:
        _cleanup()

    print(f"\n{'═'*60}")
    indicator = "✓" if _FAIL == 0 else "✗"
    print(f"  {indicator}  RESULT: {_PASS}/{_PASS + _FAIL} passed   |   {_FAIL} failed")
    print("═" * 60)
