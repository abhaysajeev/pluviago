import frappe
from frappe.model.document import Document


@frappe.whitelist()
def get_spec_parameters(item_code):
	"""Return QC Parameter Spec rows for a given chemical (item_code)."""
	specs = frappe.get_all(
		"QC Parameter Spec",
		filters={"applicable_doctype": "Raw Material Batch", "item_code": item_code},
		fields=["parameter_name", "expected_text", "min_value", "max_value", "unit", "is_critical"],
		order_by="is_critical desc, parameter_name asc",
	)
	rows = []
	for s in specs:
		if s.expected_text:
			specification = s.expected_text
		elif s.min_value is not None and s.max_value is not None:
			specification = f"{s.min_value} – {s.max_value} {s.unit or ''}".strip()
		elif s.min_value is not None:
			specification = f">= {s.min_value} {s.unit or ''}".strip()
		elif s.max_value is not None:
			specification = f"<= {s.max_value} {s.unit or ''}".strip()
		else:
			specification = ""
		rows.append({
			"parameter_name": s.parameter_name,
			"specification": specification,
			"observed_value": "",
			"result": "",
		})
	return rows


class ChemicalCOA(Document):

	def before_submit(self):
		if not self.overall_result:
			frappe.throw("Set Overall Result (Pass / Fail) before submitting.")
		if not self.verified_by:
			frappe.throw("Verified By is required before submitting.")
		if not self.verification_date:
			frappe.throw("Verification Date is required before submitting.")

		self.status = "Verified" if self.overall_result == "Pass" else "Rejected"

		# Sync verification status back to the linked Raw Material Batch
		if self.raw_material_batch:
			rmb = frappe.get_doc("Raw Material Batch", self.raw_material_batch)
			rmb.coa_verified = 1
			rmb.coa_verified_by = self.verified_by
			rmb.save(ignore_permissions=True)
