import frappe
from frappe.model.document import Document

STAGE_SEQUENCE = ["Flask", "25L PBR", "275L PBR", "925L PBR", "6600L PBR", "Harvested", "Disposed"]
STAGE_VOLUMES = {
    "Flask": 1,
    "25L PBR": 25,
    "275L PBR": 275,
    "925L PBR": 925,
    "6600L PBR": 6600
}


class ProductionBatch(Document):
    def before_save(self):
        if not self.batch_number:
            self.batch_number = self.name
        if self.current_stage and self.current_stage in STAGE_VOLUMES:
            self.reactor_volume = STAGE_VOLUMES[self.current_stage]
        # Default lineage_status for new records
        if not self.lineage_status:
            self.lineage_status = "Active"

    def validate(self):
        if self.parent_batch and self.parent_batch == self.name:
            frappe.throw("A batch cannot be its own parent")
        if self.stage_decision == "Dispose":
            self.status = "Disposed"
        elif self.stage_decision == "Harvest":
            self.status = "Harvested"
        elif self.stage_decision == "Scale Up":
            self.status = "Scaled Up"

    def on_submit(self):
        # Update parent strain's generation count
        if self.strain:
            strain_doc = frappe.get_doc("Pluviago Strain", self.strain)
            strain_doc.generation_count = (strain_doc.generation_count or 0) + 1
            strain_doc.save(ignore_permissions=True)

    def on_cancel(self):
        self.status = "Active"
        self.db_set("status", "Active")

    def get_lineage(self):
        """Return full ancestor chain for this batch"""
        lineage = []
        current = self.parent_batch
        while current:
            lineage.append(current)
            current = frappe.db.get_value("Production Batch", current, "parent_batch")
        return lineage

    @frappe.whitelist()
    def mark_returned(self):
        """
        Mark this batch as Returned — called by the Return-to-Cultivation
        workflow (Task 2.1) when a child Flask batch is created from this batch.
        The source batch stays Active operationally; Returned indicates that a
        culture withdrawal and back-propagation event has occurred.
        """
        if self.lineage_status == "Archived":
            frappe.throw("Cannot mark an Archived batch as Returned.")
        self.db_set("lineage_status", "Returned")
        frappe.msgprint(f"Lineage Status set to Returned for {self.name}.")

    @frappe.whitelist()
    def archive_batch(self):
        """
        Manually archive a batch — used when a batch is permanently closed
        beyond normal Harvested/Disposed status (e.g. strain retired,
        generation threshold exceeded).
        """
        self.db_set("lineage_status", "Archived")
        frappe.msgprint(f"{self.name} has been Archived.")
    @frappe.whitelist()
    def create_return_batch(self, withdrawal_volume, dilution_medium_batch,
                            dilution_volume, return_date, returned_by, reason):
        """
        Return-to-Cultivation workflow (Task 2.1).

        Withdraws a volume of culture from a live 275L or 6600L reactor,
        dilutes it with fresh medium, and back-propagates it to a new Flask batch.

        This is a Material Transfer — the source batch is NOT closed.
        Both source and new Flask batch remain simultaneously active.
        Multiple return events from the same source batch are supported.
        """
        from frappe.utils import flt

        RETURN_ELIGIBLE_STAGES = ("275L PBR", "6600L PBR")

        # --- Validations ---
        if self.docstatus != 1:
            frappe.throw("Return-to-Cultivation can only be triggered from a Submitted batch.")

        if self.current_stage not in RETURN_ELIGIBLE_STAGES:
            frappe.throw(
                f"Return-to-Cultivation is only allowed from "
                f"{' or '.join(RETURN_ELIGIBLE_STAGES)} stages. "
                f"This batch is at <b>{self.current_stage}</b>."
            )

        if self.status in ("Harvested", "Disposed"):
            frappe.throw(
                f"Batch <b>{self.name}</b> is already <b>{self.status}</b>. "
                "Cannot return a closed batch."
            )

        try:
            withdrawal_volume = float(withdrawal_volume)
        except (TypeError, ValueError):
            frappe.throw("Withdrawal volume must be a number.")

        if withdrawal_volume <= 0:
            frappe.throw("Withdrawal volume must be greater than 0.")

        # --- Create child Flask batch ---
        child = frappe.new_doc("Production Batch")
        child.strain = self.strain
        child.parent_batch = self.name
        child.current_stage = "Flask"
        child.generation_number = (self.generation_number or 1) + 1
        child.lineage_status = "Active"
        child.inoculation_date = return_date
        child.final_medium_batch = dilution_medium_batch or None
        child.medium_volume_used = flt(dilution_volume) if dilution_volume else None
        child.remarks = (
            f"Created via Return-to-Cultivation from {self.name}. "
            f"Reason: {reason or 'N/A'}"
        )
        child.insert(ignore_permissions=True)

        # --- Create audit record ---
        event = frappe.new_doc("Cultivation Return Event")
        event.source_batch = self.name
        event.child_batch = child.name
        event.withdrawal_volume = withdrawal_volume
        event.dilution_medium_batch = dilution_medium_batch or None
        event.dilution_volume = flt(dilution_volume) if dilution_volume else None
        event.return_date = return_date
        event.returned_by = returned_by or frappe.session.user
        event.reason = reason
        event.status = "Completed"
        event.insert(ignore_permissions=True)

        # --- Mark source batch lineage as Returned ---
        # Source stays operationally Active; lineage_status records the event.
        self.db_set("lineage_status", "Returned")

        frappe.msgprint(
            f"Return-to-Cultivation complete. New Flask batch "
            f"<b><a href='/app/production-batch/{child.name}'>{child.name}</a></b> created. "
            f"Event logged: <b>{event.name}</b>.",
            title="Return Successful",
            indicator="green"
        )

        return child.name

    def get_children(self):
        """
        Return direct child batch names (one level down).
        Supports branching — multiple children can share the same parent_batch.
        """
        return frappe.get_all(
            "Production Batch",
            filters={"parent_batch": self.name},
            pluck="name"
        )

    def get_full_tree(self, depth=0, max_depth=10):
        """
        Return the full descendant tree as a nested list of dicts.
        Each node: {name, current_stage, status, lineage_status, children: [...]}
        Depth-limited to prevent runaway loops.
        """
        if depth >= max_depth:
            return []
        children = self.get_children()
        tree = []
        for child_name in children:
            child = frappe.get_doc("Production Batch", child_name)
            tree.append({
                "name": child.name,
                "current_stage": child.current_stage,
                "status": child.status,
                "lineage_status": child.lineage_status,
                "children": child.get_full_tree(depth + 1, max_depth)
            })
        return tree

    @frappe.whitelist()
    def create_split_batches(self, n, next_stage, inoculation_date, medium_batch=None):
        """
        Batch Splitting (Task 2.2).

        Creates N sibling child batches at the specified next stage,
        all sharing this batch as parent. Used when one seed culture
        inoculates multiple reactors simultaneously (e.g. Flask → 2× 25L PBR).

        Args:
            n (int): Number of child batches to create (min 2, max 10).
            next_stage (str): Stage for child batches (e.g. "25L PBR").
            inoculation_date (str): Date for all child batches.
            medium_batch (str): Optional Final Medium Batch name to pre-fill.

        Returns:
            list[str]: Names of created child batches.
        """
        from frappe.utils import cint

        VALID_STAGES = ["Flask", "25L PBR", "275L PBR", "925L PBR", "6600L PBR"]

        # --- Validations ---
        if self.docstatus != 1:
            frappe.throw("Split Batch can only be triggered from a Submitted batch.")

        n = cint(n)
        if n < 2:
            frappe.throw("You must create at least 2 child batches for a split.")
        if n > 10:
            frappe.throw("Maximum 10 child batches per split.")

        if next_stage not in VALID_STAGES:
            frappe.throw(f"Invalid next stage: {next_stage}.")

        if self.status in ("Harvested", "Disposed"):
            frappe.throw(
                f"Batch <b>{self.name}</b> is already <b>{self.status}</b>. "
                "Cannot split a closed batch."
            )

        # --- Create N children ---
        created = []
        for i in range(n):
            child = frappe.new_doc("Production Batch")
            child.strain = self.strain
            child.parent_batch = self.name
            child.current_stage = next_stage
            child.generation_number = (self.generation_number or 1) + 1
            child.lineage_status = "Active"
            child.inoculation_date = inoculation_date
            child.final_medium_batch = medium_batch or None
            child.remarks = (
                f"Split {i + 1}/{n} from {self.name} "
                f"(Split Batch — Task 2.2)"
            )
            child.insert(ignore_permissions=True)
            created.append(child.name)

        frappe.msgprint(
            f"Created {n} child batches at <b>{next_stage}</b>: "
            + ", ".join(f"<b>{c}</b>" for c in created),
            title="Split Complete",
            indicator="green"
        )

        return created
