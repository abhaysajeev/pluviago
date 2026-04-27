import frappe
from frappe.model.document import Document


class HarvestBatch(Document):
    def before_save(self):
        if not self.batch_number:
            self.batch_number = self.name
        if self.target_dry_weight and self.actual_dry_weight and self.target_dry_weight > 0:
            self.yield_percentage = (self.actual_dry_weight / self.target_dry_weight) * 100

    def validate(self):
        if self.production_batch:
            pb = frappe.db.get_value(
                "Production Batch", self.production_batch,
                ["status", "reactor_volume", "stage_decision", "current_stage"], as_dict=True
            )
            if not pb:
                frappe.throw(f"Production Batch <b>{self.production_batch}</b> not found.")
            if pb.status not in ["Harvested", "Active", "Contaminated"]:
                frappe.throw("Linked Production Batch is not in a harvestable state.")
            # Active batch must have stage_decision = Harvest before HB can be created
            if pb.status == "Active" and pb.stage_decision not in ("Harvest",):
                frappe.throw(
                    f"Production Batch <b>{self.production_batch}</b> has Stage Decision "
                    f"<b>{pb.stage_decision or 'Pending'}</b>. "
                    "Set Stage Decision to <b>Harvest</b> before creating a Harvest Batch."
                )
            # GAP 8: Harvested volume cannot exceed reactor capacity
            if self.harvested_volume and pb.reactor_volume:
                if self.harvested_volume > pb.reactor_volume:
                    frappe.throw(
                        f"Harvested volume (<b>{self.harvested_volume} L</b>) cannot exceed "
                        f"the reactor capacity (<b>{pb.reactor_volume:.0f} L</b>) of the "
                        f"linked Production Batch."
                    )
            # Guard against duplicate Harvest Batches for the same Production Batch
            if self.is_new():
                existing_hb = frappe.db.get_value(
                    "Harvest Batch",
                    {"production_batch": self.production_batch, "docstatus": 1},
                    "name"
                )
                if existing_hb:
                    frappe.throw(
                        f"Production Batch <b>{self.production_batch}</b> already has a submitted "
                        f"Harvest Batch <b>{existing_hb}</b>. Cancel it first before creating a new one."
                    )

    def on_submit(self):
        if self.qc_status != "Passed":
            frappe.throw("Cannot submit: QC must be Passed")
        self.db_set("status", "Approved")
        if self.production_batch:
            frappe.db.set_value("Production Batch", self.production_batch, {
                "status": "Harvested",
                "harvest_batch": self.name,
                "actual_completion": frappe.utils.today(),
            })

    def on_cancel(self):
        self.db_set("status", "Draft")
        if self.production_batch:
            frappe.db.set_value("Production Batch", self.production_batch, {
                "status": "Active",
                "harvest_batch": None,
            })

    @frappe.whitelist()
    def confirm_packing(self):
        """Advance status from Approved → Packed after packing and label verification."""
        if self.status != "Approved":
            frappe.throw("Batch must be Approved before confirming packing.")
        if not self.packing_date or not self.packed_by:
            frappe.throw("Packing Date and Packed By are required before confirming packing.")
        if not self.label_batch_no:
            frappe.throw("Label Batch Number must be entered for label verification.")
        self.db_set("status", "Packed")
        frappe.msgprint("Packing confirmed. Batch is ready for dispatch.", indicator="green")
