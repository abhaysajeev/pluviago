import frappe
from frappe.model.document import Document
from frappe.utils import today


class ApprovedVendor(Document):

	def before_save(self):
		if self.supplier_name:
			self.supplier_name = self.supplier_name.upper()
		self.approval_status = "Approved"

	def after_insert(self):
		"""Auto-create a Supplier record from the vendor details on this form."""
		self._create_or_link_supplier()

	def _create_or_link_supplier(self):
		existing = frappe.db.get_value(
			"Supplier",
			{"supplier_name": self.supplier_name},
			"name",
		)

		if existing:
			self.db_set("supplier", existing, update_modified=False)
			frappe.msgprint(
				f"Supplier <b>{self.supplier_name}</b> already exists. Linked to existing record.",
				indicator="blue",
				alert=True,
			)
		else:
			supplier = frappe.get_doc({
				"doctype": "Supplier",
				"supplier_name": self.supplier_name,
				"supplier_type": self.supplier_type or "Company",
				"supplier_group": "All Supplier Groups",
			})
			supplier.flags.ignore_permissions = True
			supplier.insert()

			self.db_set("supplier", supplier.name, update_modified=False)
			frappe.msgprint(
				f"Supplier <b>{supplier.name}</b> created successfully.",
				indicator="green",
				alert=True,
			)


@frappe.whitelist()
def create_purchase_order(avl_name):
	"""Create a Purchase Order draft from an Approved Vendor record server-side."""
	avl = frappe.get_doc("Approved Vendor", avl_name)

	if not avl.supplier:
		frappe.throw("No Supplier linked to this Approved Vendor record.")

	if not avl.approved_items:
		frappe.throw("No approved items found on this vendor record.")

	company = (
		frappe.defaults.get_user_default("company")
		or frappe.defaults.get_global_default("company")
		or frappe.db.get_single_value("Global Defaults", "default_company")
		or frappe.db.get_value("Company", {}, "name")  # fallback: first company in system
	)
	if not company:
		frappe.throw("No Company found in the system. Please create a Company first.")

	po = frappe.get_doc({
		"doctype": "Purchase Order",
		"company": company,
		"supplier": avl.supplier,
		"schedule_date": today(),
		"items": [],
	})

	for avl_item in avl.approved_items:
		item = frappe.get_cached_doc("Item", avl_item.item_code)
		uom = item.purchase_uom or item.stock_uom
		po.append("items", {
			"item_code": item.name,
			"item_name": item.item_name,
			"description": item.description,
			"qty": 1,
			"uom": uom,
			"stock_uom": item.stock_uom,
			"conversion_factor": get_uom_conversion_factor(item, uom),
			"rate": item.last_purchase_rate or 0,
			"schedule_date": today(),
		})

	po.flags.ignore_permissions = True
	po.insert()
	return po.name


def get_uom_conversion_factor(item, uom):
	"""Get conversion factor for the given UOM from item's UOM conversion table."""
	if uom == item.stock_uom:
		return 1.0

	for row in item.uoms or []:
		if row.uom == uom:
			return row.conversion_factor

	return 1.0
