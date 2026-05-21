import frappe
from frappe.model.document import Document


class PluviagoStrain(Document):
    def before_save(self):
        if not self.strain_id:
            self.strain_id = self.name

    def validate(self):
        if self.parent_strain and self.parent_strain == self.name:
            frappe.throw("A strain cannot be its own parent strain.")

        # Warn when retiring or quarantining a strain with active Production Batches
        if self.status in ("Retired", "Quarantined"):
            active_batches = frappe.db.count(
                "Production Batch",
                {
                    "strain": self.name,
                    "status": ["in", ["Active", "Scaled Up"]],
                    "docstatus": 1,
                }
            )
            if active_batches:
                frappe.msgprint(
                    f"Warning: <b>{active_batches}</b> active Production Batch(es) are linked "
                    "to this strain. Review and close them before retiring or quarantining.",
                    indicator="orange",
                    title="Active Batches Found"
                )

    @frappe.whitelist()
    def update_generation_count(self):
        """
        Count submitted Flask Production Batches for this strain.
        Each Flask batch represents one distinct cultivation cycle initiated.
        """
        count = frappe.db.count(
            "Production Batch",
            {
                "strain": self.name,
                "current_stage": "Flask",
                "docstatus": 1,
            }
        )
        self.db_set("generation_count", count)
        frappe.msgprint(
            f"Generation count updated to <b>{count}</b> "
            f"(submitted Flask batches for this strain).",
            indicator="green"
        )
        return count
