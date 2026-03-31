import frappe
from frappe.model.document import Document


class ApprovedVendor(Document):

	def validate(self):
		if self.valid_upto and self.approval_date:
			from frappe.utils import getdate
			if getdate(self.valid_upto) < getdate(self.approval_date):
				frappe.throw("Valid Upto cannot be earlier than Approval Date.")

	def before_save(self):
		# Auto-expire if valid_upto has passed
		if self.valid_upto and self.approval_status == "Approved":
			from frappe.utils import getdate, nowdate
			if getdate(self.valid_upto) < getdate(nowdate()):
				self.approval_status = "Expired"
