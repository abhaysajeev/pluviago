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
RETURN_ELIGIBLE_STAGES = ("275L PBR", "6600L PBR")


class ProductionBatch(Document):
    def before_validate(self):
        # Set reactor_volume from stage so GAP 7 capacity check in validate() can use it
        if self.current_stage and self.current_stage in STAGE_VOLUMES:
            self.reactor_volume = STAGE_VOLUMES[self.current_stage]
        if not self.lineage_status:
            self.lineage_status = "Active"

    def before_save(self):
        if not self.batch_number:
            self.batch_number = self.name

    def validate(self):
        # ── Self-parent guard ──────────────────────────────────────────────────
        if self.parent_batch and self.parent_batch == self.name:
            frappe.throw("A batch cannot be its own parent")

        # ── Stage decision → status sync ──────────────────────────────────────
        if self.stage_decision == "Dispose":
            self.status = "Disposed"
        elif self.stage_decision == "Harvest":
            self.status = "Harvested"
        elif self.stage_decision == "Scale Up":
            self.status = "Scaled Up"

        # ── GAP 1: Contamination gate — contaminated batch cannot be scaled up ─
        if self.contamination_status == "Contaminated" and self.stage_decision == "Scale Up":
            frappe.throw(
                "Cannot scale up a <b>Contaminated</b> batch. "
                "Change Stage Decision to <b>Harvest</b> or <b>Dispose</b>."
            )

        # ── GAP 2: QC gate — any Fail or contamination reading blocks Scale Up ─
        if self.stage_decision == "Scale Up" and self.qc_readings:
            contaminated_readings = [
                r for r in self.qc_readings if r.contamination_detected
            ]
            if contaminated_readings:
                frappe.throw(
                    f"Cannot scale up: {len(contaminated_readings)} QC reading(s) have "
                    f"<b>Contamination Detected</b> flagged."
                )
            failed_readings = [
                r for r in self.qc_readings if r.overall_result == "Fail"
            ]
            if failed_readings:
                frappe.throw(
                    f"Cannot scale up: {len(failed_readings)} QC reading(s) have "
                    f"<b>Overall Result = Fail</b>. Resolve before scaling up."
                )

        # ── GAP 7: Reactor capacity check ─────────────────────────────────────
        if self.reactor_volume:
            total_vol = (self.inoculum_volume_in or 0) + (self.medium_volume_used or 0)
            if total_vol > self.reactor_volume:
                frappe.throw(
                    f"Total volume entering reactor "
                    f"({self.inoculum_volume_in or 0:.2f} L inoculum + "
                    f"{self.medium_volume_used or 0:.2f} L medium = "
                    f"<b>{total_vol:.2f} L</b>) exceeds reactor capacity "
                    f"(<b>{self.reactor_volume:.0f} L</b>)."
                )

    def on_submit(self):
        # Update parent strain's generation count
        if self.strain:
            strain_doc = frappe.get_doc("Pluviago Strain", self.strain)
            strain_doc.generation_count = (strain_doc.generation_count or 0) + 1
            strain_doc.save(ignore_permissions=True)

        # Deduct medium volume from linked Final Medium Batch
        if self.final_medium_batch and self.medium_volume_used:
            from pluviago.pluviago_biotech.utils.stock_utils import deduct_medium_volume
            deduct_medium_volume(self)

        # ── GAP 5/6: Deduct inoculum from parent batch culture pool ───────────
        if self.parent_batch and self.inoculum_volume_in:
            _deduct_inoculum_from_parent(self)

    def on_cancel(self):
        self.db_set("status", "Active")

        # Restore medium volume to Final Medium Batch
        if self.final_medium_batch and self.medium_volume_used:
            from pluviago.pluviago_biotech.utils.stock_utils import reverse_medium_volume
            reverse_medium_volume(self)

        # ── GAP 5/6: Restore inoculum to parent batch ─────────────────────────
        if self.parent_batch and self.inoculum_volume_in:
            _restore_inoculum_to_parent(self)

        # ── GAP 9: Restore parent status to Active if no other submitted children
        _restore_parent_status(self)

    def get_lineage(self):
        """Return full ancestor chain for this batch."""
        lineage = []
        current = self.parent_batch
        while current:
            lineage.append(current)
            current = frappe.db.get_value("Production Batch", current, "parent_batch")
        return lineage

    @frappe.whitelist()
    def mark_returned(self):
        if self.lineage_status == "Archived":
            frappe.throw("Cannot mark an Archived batch as Returned.")
        self.db_set("lineage_status", "Returned")
        frappe.msgprint(f"Lineage Status set to Returned for {self.name}.")

    @frappe.whitelist()
    def archive_batch(self):
        self.db_set("lineage_status", "Archived")
        frappe.msgprint(f"{self.name} has been Archived.")

    @frappe.whitelist()
    def create_return_batch(self, withdrawal_volume, dilution_medium_batch,
                            dilution_volume, return_date, returned_by, reason):
        """
        Return-to-Cultivation workflow.

        Withdraws a volume of culture from a live 275L or 6600L reactor,
        dilutes it with fresh medium, and back-propagates it to a new Flask batch.

        This is a Material Transfer — the source batch is NOT closed.
        The inoculum_volume_in on the child is set here; the actual deduction
        from this batch's culture pool happens when the child is submitted.
        """
        from frappe.utils import flt

        # ── Validations ───────────────────────────────────────────────────────
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

        # ── GAP 5: Validate culture pool before deducting ─────────────────────
        available = self.culture_volume_available or 0
        already_out = self.inoculum_volume_out or 0
        remaining_culture = available - already_out
        if available > 0 and withdrawal_volume > remaining_culture:
            frappe.throw(
                f"Batch <b>{self.name}</b> has only <b>{remaining_culture:.3f} L</b> "
                f"culture remaining (available: {available:.3f} L, already withdrawn: "
                f"{already_out:.3f} L). Requested withdrawal: "
                f"<b>{withdrawal_volume:.3f} L</b>."
            )

        # ── Create child Flask batch ──────────────────────────────────────────
        child = frappe.new_doc("Production Batch")
        child.strain = self.strain
        child.parent_batch = self.name
        child.current_stage = "Flask"
        child.generation_number = (self.generation_number or 1) + 1
        child.lineage_status = "Active"
        child.inoculation_date = return_date
        child.final_medium_batch = dilution_medium_batch or None
        child.medium_volume_used = flt(dilution_volume) if dilution_volume else None
        # Record inoculum received — deduction from parent pool on child submit
        child.inoculum_volume_in = withdrawal_volume
        child.remarks = (
            f"Created via Return-to-Cultivation from {self.name}. "
            f"Reason: {reason or 'N/A'}"
        )
        child.insert(ignore_permissions=True)

        # ── Create audit record ───────────────────────────────────────────────
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

        # Mark source lineage as Returned (operational status stays Active)
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
        """Return direct child batch names (one level down)."""
        return frappe.get_all(
            "Production Batch",
            filters={"parent_batch": self.name},
            pluck="name"
        )

    def get_full_tree(self, depth=0, max_depth=10):
        """Return the full descendant tree as a nested list of dicts."""
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
    def create_split_batches(self, n, next_stage, inoculation_date,
                             medium_batch=None, inoculum_volume_per_child=None):
        """
        Batch Splitting.

        Creates N sibling child batches at the specified next stage,
        all sharing this batch as parent. inoculum_volume_per_child
        (optional) records how much culture each child receives and
        is deducted from this batch's culture pool when each child submits.

        Args:
            n (int): Number of child batches to create (min 2, max 10).
            next_stage (str): Must be the immediate next stage in sequence.
            inoculation_date (str): Date for all child batches.
            medium_batch (str): Optional Final Medium Batch to pre-fill.
            inoculum_volume_per_child (float): Optional inoculum L per child.
        """
        from frappe.utils import cint, flt

        VALID_STAGES = ["Flask", "25L PBR", "275L PBR", "925L PBR", "6600L PBR"]

        # ── Validations ───────────────────────────────────────────────────────
        if self.docstatus != 1:
            frappe.throw("Split Batch can only be triggered from a Submitted batch.")

        n = cint(n)
        if n < 2:
            frappe.throw("You must create at least 2 child batches for a split.")
        if n > 10:
            frappe.throw("Maximum 10 child batches per split.")

        if next_stage not in VALID_STAGES:
            frappe.throw(f"Invalid next stage: {next_stage}.")

        # ── GAP 3: Enforce stage sequence — no skipping ───────────────────────
        if self.current_stage in STAGE_SEQUENCE:
            current_idx = STAGE_SEQUENCE.index(self.current_stage)
            # next_stage must be exactly one step ahead (Flask children excluded
            # from this check as they can come from Return-to-Cultivation)
            if next_stage in STAGE_SEQUENCE:
                next_idx = STAGE_SEQUENCE.index(next_stage)
                if next_idx != current_idx + 1:
                    expected = STAGE_SEQUENCE[current_idx + 1] if current_idx + 1 < len(STAGE_SEQUENCE) else "none"
                    frappe.throw(
                        f"Stage sequence violation: from <b>{self.current_stage}</b>, "
                        f"the only valid next stage is <b>{expected}</b>. "
                        f"Cannot jump to <b>{next_stage}</b>."
                    )

        if self.status in ("Harvested", "Disposed"):
            frappe.throw(
                f"Batch <b>{self.name}</b> is already <b>{self.status}</b>. "
                "Cannot split a closed batch."
            )

        # ── GAP 6: Validate total inoculum does not exceed culture pool ────────
        inoculum_per_child = flt(inoculum_volume_per_child) if inoculum_volume_per_child else None
        if inoculum_per_child:
            available = self.culture_volume_available or 0
            already_out = self.inoculum_volume_out or 0
            remaining_culture = available - already_out
            total_requested = inoculum_per_child * n
            if available > 0 and total_requested > remaining_culture:
                frappe.throw(
                    f"Total inoculum requested ({total_requested:.3f} L = "
                    f"{inoculum_per_child:.3f} L × {n}) exceeds remaining culture "
                    f"(<b>{remaining_culture:.3f} L</b>) in this batch."
                )

        # ── Create N children ─────────────────────────────────────────────────
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
            if inoculum_per_child:
                child.inoculum_volume_in = inoculum_per_child
            child.remarks = (
                f"Split {i + 1}/{n} from {self.name} "
                f"(Batch Split)"
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


# ──────────────────────────────────────────────────────────────────────────────
# Culture volume helpers (GAP 5 / GAP 6 / GAP 9)
# ──────────────────────────────────────────────────────────────────────────────

def _deduct_inoculum_from_parent(doc):
    """
    Deduct inoculum_volume_in from the parent batch's culture pool on submit.
    Only enforces the limit if culture_volume_available was entered by the operator.
    """
    parent = frappe.db.get_value(
        "Production Batch", doc.parent_batch,
        ["name", "culture_volume_available", "inoculum_volume_out",
         "current_stage", "status"],
        as_dict=True,
    )
    if not parent:
        frappe.throw(f"Parent batch <b>{doc.parent_batch}</b> not found.")

    available = parent.culture_volume_available or 0
    already_out = parent.inoculum_volume_out or 0
    remaining = available - already_out

    # Enforce only when the operator has recorded a culture_volume_available
    if available > 0 and doc.inoculum_volume_in > remaining:
        frappe.throw(
            f"Parent batch <b>{doc.parent_batch}</b> ({parent.current_stage}) "
            f"has only <b>{remaining:.3f} L</b> culture remaining "
            f"(available: {available:.3f} L, already out: {already_out:.3f} L). "
            f"Requested inoculum: <b>{doc.inoculum_volume_in:.3f} L</b>."
        )

    new_out = round(already_out + doc.inoculum_volume_in, 6)
    frappe.db.set_value("Production Batch", doc.parent_batch, "inoculum_volume_out", new_out)


def _restore_inoculum_to_parent(doc):
    """Restore inoculum_volume_in to parent's culture pool on cancel."""
    current_out = frappe.db.get_value(
        "Production Batch", doc.parent_batch, "inoculum_volume_out"
    ) or 0
    new_out = max(0.0, round(current_out - doc.inoculum_volume_in, 6))
    frappe.db.set_value("Production Batch", doc.parent_batch, "inoculum_volume_out", new_out)


def _restore_parent_status(doc):
    """
    GAP 9: When a child batch is cancelled, restore parent to Active
    if no other submitted children remain from that parent.
    """
    if not doc.parent_batch:
        return
    parent_status = frappe.db.get_value("Production Batch", doc.parent_batch, "status")
    if parent_status != "Scaled Up":
        return
    # Only restore if this was the last submitted child
    other_submitted_children = frappe.db.count(
        "Production Batch",
        {"parent_batch": doc.parent_batch, "docstatus": 1, "name": ["!=", doc.name]}
    )
    if not other_submitted_children:
        frappe.db.set_value("Production Batch", doc.parent_batch, "status", "Active")
