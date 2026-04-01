import frappe
from frappe.utils import nowdate


def validate(doc, method=None):
	"""
	On Purchase Order validate:
	  - Warn if supplier is not in Approved Vendor list for any ordered chemical item,
	    or if their qualification has expired (valid_upto < today).
	  - Does not hard-block (warning only) — COA verification is the real quality gate.
	"""
	if not doc.items:
		return

	unapproved = []

	for row in doc.items:
		if not row.item_code:
			continue

		# Only check items that are chemicals (item_group in chemical groups)
		item_group = frappe.db.get_value("Item", row.item_code, "item_group")
		chemical_groups = {
			"Base Salts", "Trace Elements", "Nutrients",
			"Vitamins", "Media Chemicals", "Raw Materials", "Raw Material"
		}
		if item_group not in chemical_groups:
			continue

		approved = frappe.db.get_value("Approved Vendor", [
			["supplier", "=", doc.supplier],
			["item_code", "=", row.item_code],
			["approval_status", "=", "Approved"],
			["valid_upto", ">=", nowdate()],
		], "name")

		if not approved:
			unapproved.append(f"<li>{row.item_name or row.item_code}</li>")

	if unapproved:
		items_html = "".join(unapproved)
		frappe.msgprint(
			msg=f"""
				Supplier <b>{doc.supplier}</b> is not in the Approved Vendor List for:<ul>{items_html}</ul>
				Proceed only if vendor qualification is in progress.
				Create an Approved Vendor record to suppress this warning.
			""",
			title="Vendor Not Qualified",
			indicator="orange",
		)
