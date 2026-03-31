import frappe
from frappe.utils import today, add_days

COMPANY = "Pluviago Biotech Pvt. Ltd."
WAREHOUSE = "Chemical Store RT - PB"
SUPPLIER = "Sisco Research Labs"
ITEM = "CHEM-001"
ITEM_NAME = "Calcium Chloride Dihydrate"

def cleanup():
	frappe.set_user("Administrator")
	for dt, filters in [
		("Chemical COA", {"supplier": SUPPLIER}),
		("Raw Material Batch", {"supplier": SUPPLIER}),
		("Approved Vendor", {"supplier": SUPPLIER}),
	]:
		for rec in frappe.get_all(dt, filters=filters):
			doc = frappe.get_doc(dt, rec.name)
			if doc.docstatus == 1:
				doc.cancel()
			frappe.delete_doc(dt, rec.name, ignore_permissions=True)
	for dt, filters in [
		("Purchase Receipt", {"supplier": SUPPLIER, "company": COMPANY}),
		("Purchase Order", {"supplier": SUPPLIER, "company": COMPANY}),
	]:
		for rec in frappe.get_all(dt, filters=filters):
			try:
				doc = frappe.get_doc(dt, rec.name)
				if doc.docstatus == 1:
					doc.cancel()
				frappe.delete_doc(dt, rec.name, ignore_permissions=True)
			except Exception:
				pass
	frappe.db.commit()


def make_approved_rmb():
	"""Helper — returns a submitted, approved RMB."""
	av = frappe.get_doc({
		"doctype": "Approved Vendor", "supplier": SUPPLIER, "item_code": ITEM,
		"material_name": ITEM_NAME, "approval_status": "Approved",
		"approval_date": today(), "valid_upto": add_days(today(), 365),
		"approved_by": "Administrator",
	})
	av.naming_series = "AVL-.YYYY.-.####"
	av.insert(ignore_permissions=True)

	po = frappe.get_doc({
		"doctype": "Purchase Order", "company": COMPANY, "supplier": SUPPLIER,
		"schedule_date": add_days(today(), 7),
		"items": [{"item_code": ITEM, "qty": 500, "uom": "mg", "rate": 0.5,
				   "warehouse": WAREHOUSE, "schedule_date": add_days(today(), 7)}],
	})
	po.insert(ignore_permissions=True)
	po.submit()

	pr = frappe.get_doc({
		"doctype": "Purchase Receipt", "company": COMPANY, "supplier": SUPPLIER,
		"posting_date": today(),
		"items": [{"item_code": ITEM, "item_name": ITEM_NAME, "qty": 500,
				   "uom": "mg", "rate": 0.5, "warehouse": WAREHOUSE, "purchase_order": po.name}],
	})
	pr.insert(ignore_permissions=True)
	pr.submit()

	rmb = frappe.get_doc({
		"doctype": "Raw Material Batch", "material_name": ITEM_NAME, "item_code": ITEM,
		"supplier": SUPPLIER, "supplier_batch_no": "SRL-TEST-001",
		"mfg_date": "2024-09-01", "expiry_date": add_days(today(), 730),
		"received_date": today(), "received_qty": 500, "received_qty_uom": "mg",
		"storage_condition": "Room Temperature", "warehouse": WAREHOUSE,
		"qc_status": "Approved", "qc_checked_by": "Administrator", "qc_date": today(),
		"coa_verified": 1, "coa_verified_by": "Administrator",
		"purchase_receipt": pr.name, "status": "Approved",
	})
	rmb.naming_series = "RMB-CHEM-.YYYY.-.####"
	rmb.insert(ignore_permissions=True)
	rmb.submit()
	frappe.db.commit()
	return rmb


def run():
	frappe.set_user("Administrator")
	errors = []

	print("\n=== PRE-TEST CLEANUP ===")
	cleanup()
	print("  Done.")

	# ────────────────────────────────────────────────────────────────────
	# FIX #3: Cancel guard — block cancel when consumed_qty > 0
	# ────────────────────────────────────────────────────────────────────
	print("\n=== FIX #3: CANCEL GUARD (consumed batch) ===")
	try:
		rmb = make_approved_rmb()
		print(f"  RMB created → {rmb.name} | remaining: {rmb.remaining_qty} mg")

		# Simulate a consumption by directly setting consumed_qty
		frappe.db.set_value("Raw Material Batch", rmb.name, {
			"consumed_qty": 100,
			"remaining_qty": 400,
		})
		rmb.reload()

		blocked = False
		try:
			rmb.cancel()
		except frappe.exceptions.ValidationError as e:
			if "consumed" in str(e).lower():
				blocked = True
				print(f"  PASS: Cancel correctly blocked — '{e}'")
		if not blocked:
			print("  FAIL: Cancel should have been blocked but was not")
			errors.append(("Cancel Guard", "No block on consumed batch"))
	except Exception as e:
		print(f"  FAIL: {e}")
		errors.append(("Cancel Guard", str(e)))

	# ────────────────────────────────────────────────────────────────────
	# FIX #4: recalculate_remaining_qty — corrects drift
	# ────────────────────────────────────────────────────────────────────
	print("\n=== FIX #4: RECALCULATE REMAINING QTY ===")
	try:
		rmb = frappe.get_doc("Raw Material Batch", rmb.name)

		# Artificially drift the values (simulates data inconsistency)
		frappe.db.set_value("Raw Material Batch", rmb.name, {
			"consumed_qty": 999,
			"remaining_qty": -499,
		})
		rmb.reload()
		print(f"  Before recalc → consumed: {rmb.consumed_qty} | remaining: {rmb.remaining_qty} (drifted)")

		# Create a real SCL entry to simulate 100mg consumed
		scl = frappe.get_doc({
			"doctype": "Stock Consumption Log",
			"raw_material_batch": rmb.name,
			"material_name": ITEM_NAME,
			"qty_change": -100,
			"uom": "mg",
			"balance_after": 400,
			"action": "Consumed",
			"preparation_stage": "A1",
			"performed_by": "Administrator",
			"remarks": "Test entry for recalculate",
		})
		scl.naming_series = "SCL-.YYYY.-.####"
		scl.insert(ignore_permissions=True)
		frappe.db.commit()

		rmb.recalculate_remaining_qty()
		rmb.reload()
		print(f"  After recalc  → consumed: {rmb.consumed_qty} | remaining: {rmb.remaining_qty} | status: {rmb.status}")

		if rmb.consumed_qty == 100 and rmb.remaining_qty == 400:
			print("  PASS: recalculate_remaining_qty corrected drift from SCL")
		else:
			print("  FAIL: Values not corrected correctly")
			errors.append(("Recalculate", f"consumed={rmb.consumed_qty}, remaining={rmb.remaining_qty}"))
	except Exception as e:
		print(f"  FAIL: {e}")
		errors.append(("Recalculate", str(e)))

	# ── Summary ──────────────────────────────────────────────────────────
	print("\n=== TEST SUMMARY ===")
	stages = ["Cancel Guard", "Recalculate"]
	failed = {e[0] for e in errors}
	for s in stages:
		print(f"  [{'FAIL' if s in failed else 'PASS'}] {s}")

	frappe.db.rollback()
	print("\n  (Test data rolled back)")
