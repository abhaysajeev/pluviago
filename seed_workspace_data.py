"""
Pluviago Workspace — Seed Data Script
======================================
Run via:  bench --site replica1.local execute pluviago.seed_workspace_data.run

Creates:
  • 3 Suppliers (Item Supplier master)
  • 5 Items (chemical items)
  • 6 Approved Vendors (mix of Approved / Pending / Suspended)
  • 4 Purchase Orders (submitted)
  • 4 Purchase Receipts (from POs)
  • 8 Raw Material Batches (submitted — mix of Approved / Pending / Rejected QC)
  • 6 Chemical COAs (submitted — mix of Pass / Fail)
  • 4 Stock Consumption Log entries

All data is safe to re-run: existing records are skipped.
"""

import frappe
from frappe.utils import nowdate, add_days, add_months, today, getdate


def run():
    frappe.flags.ignore_permissions = True
    print("\n🧬 Pluviago Workspace — Seeding demo data...\n")

    company = "Pluviago Biotech Pvt. Ltd."
    # Ensure company exists
    if not frappe.db.exists("Company", company):
        print(f"⚠  Company '{company}' not found — using default company.")
        company = frappe.defaults.get_defaults().get("company") or frappe.db.get_single_value("Global Defaults", "default_company")
        if not company:
            print("❌ No company found. Create a company first.")
            return
    print(f"  Company: {company}")

    # ─── SUPPLIERS ───
    suppliers = [
        {"name1": "ChemSource India Pvt Ltd", "group": "Raw Material"},
        {"name1": "BioReagents Global LLC",   "group": "Raw Material"},
        {"name1": "PharmaGrade Chemicals",    "group": "Raw Material"},
    ]
    sup_names = []
    for s in suppliers:
        if not frappe.db.exists("Supplier", {"supplier_name": s["name1"]}):
            # Ensure supplier group exists
            sg = s.get("group", "Raw Material")
            if not frappe.db.exists("Supplier Group", sg):
                frappe.get_doc({"doctype": "Supplier Group", "supplier_group_name": sg}).insert()
            doc = frappe.get_doc({
                "doctype": "Supplier",
                "supplier_name": s["name1"],
                "supplier_group": sg,
                "supplier_type": "Company",
                "country": "India",
            }).insert()
            sup_names.append(doc.name)
            print(f"  ✅ Supplier: {doc.name}")
        else:
            sup_names.append(frappe.db.get_value("Supplier", {"supplier_name": s["name1"]}, "name"))
            print(f"  ⏭  Supplier exists: {s['name1']}")

    # ─── ITEMS ───
    items_data = [
        {"item_code": "CHEM-001", "item_name": "Sodium Chloride",       "uom": "Kg"},
        {"item_code": "CHEM-002", "item_name": "Potassium Phosphate",   "uom": "Kg"},
        {"item_code": "CHEM-003", "item_name": "Magnesium Sulfate",     "uom": "Kg"},
        {"item_code": "CHEM-004", "item_name": "Ferric Citrate",        "uom": "Gram"},
        {"item_code": "CHEM-005", "item_name": "EDTA Disodium Salt",    "uom": "Gram"},
    ]
    for it in items_data:
        if not frappe.db.exists("Item", it["item_code"]):
            # Ensure item group
            ig = "Raw Material"
            if not frappe.db.exists("Item Group", ig):
                frappe.get_doc({"doctype": "Item Group", "item_group_name": ig, "parent_item_group": "All Item Groups"}).insert()
            doc = frappe.get_doc({
                "doctype": "Item",
                "item_code": it["item_code"],
                "item_name": it["item_name"],
                "item_group": ig,
                "stock_uom": it["uom"],
                "is_stock_item": 1,
            }).insert()
            print(f"  ✅ Item: {doc.item_code}")
        else:
            print(f"  ⏭  Item exists: {it['item_code']}")

    # ─── APPROVED VENDORS ─── (Not submittable — just saved)
    avl_data = [
        {"supplier": sup_names[0], "item_code": "CHEM-001", "status": "Approved"},
        {"supplier": sup_names[0], "item_code": "CHEM-002", "status": "Approved"},
        {"supplier": sup_names[1], "item_code": "CHEM-003", "status": "Approved"},
        {"supplier": sup_names[1], "item_code": "CHEM-004", "status": "Pending"},
        {"supplier": sup_names[2], "item_code": "CHEM-005", "status": "Approved"},
        {"supplier": sup_names[2], "item_code": "CHEM-001", "status": "Suspended"},
    ]
    avl_names = []
    for a in avl_data:
        existing = frappe.db.exists("Approved Vendor", {"supplier": a["supplier"], "item_code": a["item_code"]})
        if not existing:
            doc = frappe.get_doc({
                "doctype": "Approved Vendor",
                "supplier": a["supplier"],
                "item_code": a["item_code"],
                "material_name": frappe.db.get_value("Item", a["item_code"], "item_name"),
                "approval_status": a["status"],
                "approval_date": add_days(nowdate(), -30),
                "valid_upto": add_months(nowdate(), 12),
                "approved_by": "Administrator",
            }).insert()
            # Submit if it's submittable
            if doc.meta.is_submittable:
                doc.submit()
            avl_names.append(doc.name)
            print(f"  ✅ AVL: {doc.name} ({a['status']})")
        else:
            avl_names.append(existing)
            print(f"  ⏭  AVL exists: {a['supplier']} / {a['item_code']}")

    # ─── Ensure warehouse ───
    wh = f"Stores - {frappe.db.get_value('Company', company, 'abbr')}"
    if not frappe.db.exists("Warehouse", wh):
        # Try any leaf warehouse
        wh = frappe.db.get_value("Warehouse", {"company": company, "is_group": 0}, "name")
    if not wh:
        print("⚠  No warehouse found — skipping PO/PR creation.")
        wh = None
    else:
        print(f"  Warehouse: {wh}")

    # ─── RAW MATERIAL BATCHES ─── (create first since COA needs them)
    rmb_defs = [
        {"material": "Sodium Chloride",     "supplier": sup_names[0], "batch": "SC-2026-A1",  "qty": 25,  "uom": "Kg",   "item": "CHEM-001", "qc": "Approved", "exp_days": 365},
        {"material": "Potassium Phosphate", "supplier": sup_names[0], "batch": "KP-2026-B2",  "qty": 10,  "uom": "Kg",   "item": "CHEM-002", "qc": "Approved", "exp_days": 270},
        {"material": "Magnesium Sulfate",   "supplier": sup_names[1], "batch": "MS-2026-C3",  "qty": 15,  "uom": "Kg",   "item": "CHEM-003", "qc": "Approved", "exp_days": 180},
        {"material": "Ferric Citrate",      "supplier": sup_names[1], "batch": "FC-2026-D4",  "qty": 500, "uom": "Gram", "item": "CHEM-004", "qc": "Pending",  "exp_days": 120},
        {"material": "EDTA Disodium Salt",  "supplier": sup_names[2], "batch": "EDTA-2026-E5","qty": 250, "uom": "Gram", "item": "CHEM-005", "qc": "Approved", "exp_days": 90},
        {"material": "Sodium Chloride",     "supplier": sup_names[2], "batch": "SC-2026-F6",  "qty": 5,   "uom": "Kg",   "item": "CHEM-001", "qc": "Rejected", "exp_days": 200},
        {"material": "Potassium Phosphate", "supplier": sup_names[0], "batch": "KP-2026-G7",  "qty": 8,   "uom": "Kg",   "item": "CHEM-002", "qc": "Approved", "exp_days": 20},  # expiring soon
        {"material": "Magnesium Sulfate",   "supplier": sup_names[1], "batch": "MS-2025-H8",  "qty": 3,   "uom": "Kg",   "item": "CHEM-003", "qc": "Approved", "exp_days": -10}, # already expired
    ]
    rmb_names = []
    for r in rmb_defs:
        existing = frappe.db.exists("Raw Material Batch", {"supplier_batch_no": r["batch"]})
        if existing:
            rmb_names.append(existing)
            print(f"  ⏭  RMB exists: {r['batch']}")
            continue

        exp = add_days(nowdate(), r["exp_days"])
        mfg = add_days(nowdate(), -60) if r["exp_days"] > 0 else add_days(nowdate(), -400)

        doc = frappe.get_doc({
            "doctype": "Raw Material Batch",
            "material_name": r["material"],
            "supplier": r["supplier"],
            "item_code": r["item"],
            "supplier_batch_no": r["batch"],
            "mfg_date": mfg,
            "expiry_date": exp,
            "received_date": add_days(nowdate(), -15),
            "received_qty": r["qty"],
            "received_qty_uom": r["uom"],
            "storage_condition": "Room Temperature",
            "warehouse": wh,
            "qc_status": r["qc"],
            "qc_checked_by": "Administrator",
            "qc_date": nowdate(),
            "coa_verified": 1 if r["qc"] == "Approved" else 0,
            "coa_verified_by": "Administrator" if r["qc"] == "Approved" else None,
        })
        doc.insert()

        # Only submit Approved ones
        if r["qc"] == "Approved":
            doc.submit()
            print(f"  ✅ RMB submitted: {doc.name} ({r['material']}, QC={r['qc']})")
        else:
            print(f"  ✅ RMB saved (draft): {doc.name} ({r['material']}, QC={r['qc']})")
        rmb_names.append(doc.name)

    # ─── PURCHASE ORDERS ───
    po_names = []
    if wh:
        po_defs = [
            {"supplier": sup_names[0], "items": [("CHEM-001", 25, "Kg", 450), ("CHEM-002", 10, "Kg", 1200)]},
            {"supplier": sup_names[1], "items": [("CHEM-003", 15, "Kg", 800)]},
            {"supplier": sup_names[1], "items": [("CHEM-004", 500, "Gram", 3500)]},
            {"supplier": sup_names[2], "items": [("CHEM-005", 250, "Gram", 2800)]},
        ]
        for p in po_defs:
            # Check if PO already exists for this supplier (rough check)
            existing = frappe.db.exists("Purchase Order", {
                "supplier": p["supplier"],
                "company": company,
                "docstatus": 1,
            })
            if existing:
                po_names.append(existing)
                print(f"  ⏭  PO exists for {p['supplier']}")
                continue
            items = []
            for item_code, qty, uom, rate in p["items"]:
                items.append({
                    "item_code": item_code,
                    "qty": qty,
                    "uom": uom,
                    "rate": rate,
                    "warehouse": wh,
                    "schedule_date": add_days(nowdate(), 7),
                })
            doc = frappe.get_doc({
                "doctype": "Purchase Order",
                "supplier": p["supplier"],
                "company": company,
                "schedule_date": add_days(nowdate(), 7),
                "items": items,
            })
            doc.insert()
            doc.submit()
            po_names.append(doc.name)
            print(f"  ✅ PO submitted: {doc.name}")

        # ─── PURCHASE RECEIPTS (from POs) ───
        for po_name in po_names[:3]:  # Create PRs for first 3 POs
            existing_pr = frappe.db.exists("Purchase Receipt", {
                "purchase_order": po_name,
                "company": company,
                "docstatus": 1,
            })
            if existing_pr:
                print(f"  ⏭  PR exists for {po_name}")
                continue
            try:
                po_doc = frappe.get_doc("Purchase Order", po_name)
                pr_items = []
                for row in po_doc.items:
                    pr_items.append({
                        "item_code": row.item_code,
                        "qty": row.qty,
                        "uom": row.uom,
                        "rate": row.rate,
                        "warehouse": row.warehouse,
                        "purchase_order": po_name,
                        "purchase_order_item": row.name,
                    })
                pr = frappe.get_doc({
                    "doctype": "Purchase Receipt",
                    "supplier": po_doc.supplier,
                    "company": company,
                    "items": pr_items,
                })
                pr.insert()
                pr.submit()
                print(f"  ✅ PR submitted: {pr.name}")
            except Exception as e:
                print(f"  ⚠  PR creation failed for {po_name}: {e}")

    # ─── CHEMICAL COAs ───
    coa_results = ["Pass", "Pass", "Pass", "Pass", "Fail", "Fail"]
    submitted_rmbs = [n for n in rmb_names if frappe.db.get_value("Raw Material Batch", n, "docstatus") == 1]
    for idx, result in enumerate(coa_results):
        rmb_name = submitted_rmbs[idx % len(submitted_rmbs)] if submitted_rmbs else rmb_names[idx % len(rmb_names)]
        rmb_doc = frappe.get_doc("Raw Material Batch", rmb_name)

        existing = frappe.db.exists("Chemical COA", {"raw_material_batch": rmb_name, "overall_result": result})
        if existing:
            print(f"  ⏭  COA exists for {rmb_name} ({result})")
            continue

        doc = frappe.get_doc({
            "doctype": "Chemical COA",
            "raw_material_batch": rmb_name,
            "material_name": rmb_doc.material_name,
            "supplier": rmb_doc.supplier,
            "item_code": rmb_doc.item_code,
            "supplier_batch_no": rmb_doc.supplier_batch_no,
            "analysis_date": add_days(nowdate(), -10),
            "expiry_date": rmb_doc.expiry_date,
            "manufacture_date": rmb_doc.mfg_date,
            "received_date": rmb_doc.received_date,
            "grade": "AR Grade",
            "overall_result": result,
            "verified_by": "Administrator",
            "verification_date": nowdate(),
            "verification_remarks": f"Seed data — {result}",
        })
        doc.insert()
        doc.submit()
        print(f"  ✅ COA submitted: {doc.name} ({result})")

    # ─── STOCK CONSUMPTION LOGS ───
    scl_defs = [
        {"rmb": rmb_names[0], "qty": -2,   "action": "Consumed",  "stage": "Stock Solution A1"},
        {"rmb": rmb_names[0], "qty": -1.5, "action": "Consumed",  "stage": "Stock Solution A2"},
        {"rmb": rmb_names[1], "qty": -3,   "action": "Consumed",  "stage": "Green Medium"},
        {"rmb": rmb_names[2], "qty": -0.5, "action": "Written Off (Loss)", "stage": "Stock Solution A3"},
    ]
    for s in scl_defs:
        rmb_name = s["rmb"]
        rmb_doc = frappe.get_doc("Raw Material Batch", rmb_name)
        existing = frappe.db.count("Stock Consumption Log", {"raw_material_batch": rmb_name})
        if existing >= 2:
            print(f"  ⏭  SCL entries already exist for {rmb_name}")
            continue
        remaining = (rmb_doc.remaining_qty or rmb_doc.received_qty or 0) + s["qty"]
        doc = frappe.get_doc({
            "doctype": "Stock Consumption Log",
            "log_date": nowdate(),
            "action": s["action"],
            "raw_material_batch": rmb_name,
            "material_name": rmb_doc.material_name,
            "qty_change": s["qty"],
            "uom": rmb_doc.received_qty_uom,
            "balance_after": max(remaining, 0),
            "source_doctype": "Stock Solution Batch",
            "source_document": "SSB-SEED-001",
            "preparation_stage": s["stage"],
            "performed_by": "Administrator",
            "remarks": "Seed data for workspace demo",
        })
        doc.insert()
        print(f"  ✅ SCL: {doc.name} ({s['action']}, {s['qty']})")

    frappe.db.commit()
    print(f"\n🎉 Seed data complete! Reload your workspace to see the dashboard.\n")
