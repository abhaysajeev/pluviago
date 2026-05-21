import frappe
from frappe.model.document import Document


class DryingBatch(Document):
    def before_save(self):
        if not self.batch_number:
            self.batch_number = self.name
        if self.actual_dry_weight and self.wet_biomass_in and self.wet_biomass_in > 0:
            self.yield_percentage = round(
                (self.actual_dry_weight / self.wet_biomass_in) * 100, 2
            )

    def validate(self):
        if not self.harvest_batch:
            return

        hb = frappe.db.get_value(
            "Harvest Batch", self.harvest_batch,
            ["docstatus", "status", "wet_biomass_kg"], as_dict=True
        )
        if not hb:
            frappe.throw(f"Harvest Batch <b>{self.harvest_batch}</b> not found.")
        if hb.docstatus != 1:
            frappe.throw(
                f"Harvest Batch <b>{self.harvest_batch}</b> must be submitted before creating a Drying Batch."
            )
        if hb.status not in ("Approved", "Packed"):
            frappe.throw(
                f"Harvest Batch <b>{self.harvest_batch}</b> has status <b>{hb.status}</b>. "
                "Only Approved or Packed Harvest Batches can be dried."
            )

        # Pre-fill wet_biomass_in from HB if not set
        if not self.wet_biomass_in and hb.wet_biomass_kg:
            self.wet_biomass_in = hb.wet_biomass_kg

        # Duplicate guard: only one submitted Drying Batch per Harvest Batch
        if self.is_new():
            existing = frappe.db.get_value(
                "Drying Batch",
                {"harvest_batch": self.harvest_batch, "docstatus": 1},
                "name"
            )
            if existing:
                frappe.throw(
                    f"Harvest Batch <b>{self.harvest_batch}</b> already has a submitted "
                    f"Drying Batch <b>{existing}</b>. Cancel it first before creating a new one."
                )

    def before_submit(self):
        if self.qc_status != "Passed":
            frappe.throw("QC Status must be Passed before finalising the Drying Batch.")

    def on_submit(self):
        self.db_set("status", "Approved")

        # Write drying results back to the Harvest Batch for downstream use
        frappe.db.set_value("Harvest Batch", self.harvest_batch, {
            "actual_dry_weight": self.actual_dry_weight,
            "yield_percentage": self.yield_percentage or 0,
            "drying_batch": self.name,
        })

    def on_cancel(self):
        self.db_set("status", "Draft")

        # Clear drying results from Harvest Batch
        frappe.db.set_value("Harvest Batch", self.harvest_batch, {
            "actual_dry_weight": 0,
            "yield_percentage": 0,
            "drying_batch": None,
        })
