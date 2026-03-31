import frappe
from frappe.model.document import Document


class PluviagoStrain(Document):
    def before_save(self):
        if not self.strain_id:
            self.strain_id = self.name

    def validate(self):
        if self.parent_strain and self.parent_strain == self.name:
            frappe.throw("A strain cannot be its own parent strain")
