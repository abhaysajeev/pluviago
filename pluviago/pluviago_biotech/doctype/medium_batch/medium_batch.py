import frappe
from frappe.model.document import Document
from frappe.model.naming import make_autoname

# Hard-coded SRS formulation constants — these are fixed by the biotech protocol.
# Quantities are per 1 L of final medium volume.
_GREEN_BASE_SALTS = [
    {"chemical_name": "Calcium Chloride Dihydrate",      "qty_per_L": 75,  "uom": "mg"},
    {"chemical_name": "Magnesium Sulphate Heptahydrate", "qty_per_L": 225, "uom": "mg"},
    {"chemical_name": "Sodium Chloride",                 "qty_per_L": 75,  "uom": "mg"},
]
_RED_BASE_SALTS = [
    {"chemical_name": "Calcium Chloride Dihydrate",      "qty_per_L": 100, "uom": "mg"},
    {"chemical_name": "Magnesium Sulphate Heptahydrate", "qty_per_L": 200, "uom": "mg"},
]

# SSB volumes per 1 L of medium (in mL). A7-I is listed last (add_last=True).
_GREEN_SSB_ADDITIONS = [
    {"solution_type": "A1",  "vol_per_L_ml": 18.0,  "add_last": False},
    {"solution_type": "A2",  "vol_per_L_ml": 2.0,   "add_last": False},
    {"solution_type": "A3",  "vol_per_L_ml": 0.94,  "add_last": False},
    {"solution_type": "A4",  "vol_per_L_ml": 9.48,  "add_last": False},
    {"solution_type": "A5",  "vol_per_L_ml": 4.4,   "add_last": False},
]
_RED_SSB_ADDITIONS = [
    {"solution_type": "A5M", "vol_per_L_ml": 1.0, "add_last": False},
    {"solution_type": "A7-II",  "vol_per_L_ml": 1.0, "add_last": False},
    {"solution_type": "A7-III", "vol_per_L_ml": 1.0, "add_last": False},
    {"solution_type": "A7-IV",  "vol_per_L_ml": 1.0, "add_last": False},
    {"solution_type": "A7-V",   "vol_per_L_ml": 1.0, "add_last": False},
    {"solution_type": "A7-VI",  "vol_per_L_ml": 1.0, "add_last": False},
    {"solution_type": "A7-I",   "vol_per_L_ml": 1.0, "add_last": True},  # Calcium — LAST
]


class MediumBatch(Document):
    def autoname(self):
        if not self.medium_type:
            frappe.throw("Medium Type must be selected before saving.")
        code = "GRN" if self.medium_type == "Green" else "RED"
        self.name = make_autoname(f"MED-{code}-.YYYY.-.MM.-.####")

    def before_save(self):
        if not self.batch_number:
            self.batch_number = self.name
        if self.final_required_volume:
            factor = 0.75 if self.medium_type == "Green" else 0.25
            self.medium_volume_calculated = round(self.final_required_volume * factor, 6)
        if self.shelf_life_days and self.preparation_date:
            self.expiry_date = frappe.utils.add_days(self.preparation_date, int(self.shelf_life_days))

    def validate(self):
        if not self.medium_type:
            frappe.throw("Medium Type is required.")

        if self.overall_qc_status == "Passed":
            if self.medium_type == "Green":
                if self.qc_checkpoint_1_clarity != "Pass":
                    frappe.throw(
                        "QC Checkpoint 1 (Clarity) must be Pass before setting Overall QC Status to Passed."
                    )
                if self.qc_checkpoint_2_clarity != "Pass":
                    frappe.throw(
                        "QC Checkpoint 2 (Clarity) must be Pass before setting Overall QC Status to Passed."
                    )
                if not self.qc_checkpoint_2_ph:
                    frappe.throw(
                        "QC Checkpoint 2 (pH) must be recorded before setting Overall QC Status to Passed."
                    )
                if self.qc_checkpoint_2_sterility not in ("Pass", "By Process"):
                    frappe.throw(
                        "QC Checkpoint 2 (Sterility) must be Pass or By Process before setting "
                        "Overall QC Status to Passed."
                    )
            else:  # Red
                if self.qc_checkpoint_3_clarity != "Pass":
                    frappe.throw(
                        "QC Checkpoint 3 (Clarity) must be Pass before setting Overall QC Status to Passed."
                    )
                if self.qc_checkpoint_4_clarity != "Pass":
                    frappe.throw(
                        "QC Checkpoint 4 (Clarity) must be Pass before setting Overall QC Status to Passed."
                    )
                if not self.qc_checkpoint_4_ph:
                    frappe.throw(
                        "QC Checkpoint 4 (pH) must be recorded before setting Overall QC Status to Passed."
                    )
                if self.qc_checkpoint_4_sterility not in ("Pass", "By Process"):
                    frappe.throw(
                        "QC Checkpoint 4 (Sterility) must be Pass or By Process before setting "
                        "Overall QC Status to Passed."
                    )

        from pluviago.pluviago_biotech.utils.stock_utils import apply_corrective_action_logic
        apply_corrective_action_logic(self)

    @frappe.whitelist()
    def mark_preparation_complete(self):
        if self.preparation_status != "Draft":
            frappe.throw("Preparation is already marked complete.")
        if not self.direct_chemicals:
            frappe.throw("Add at least one direct chemical before marking preparation complete.")
        if self.medium_type == "Green" and not self.top_up_done:
            frappe.throw(
                "<b>Top-up Done</b> must be ticked — confirm DI water has been added "
                "to bring the batch to its final volume before marking complete."
            )

        from pluviago.pluviago_biotech.utils.stock_utils import deduct_raw_materials, deduct_di_water
        deduct_raw_materials(self, action="Consumed")
        deduct_di_water(self)
        self.db_set("preparation_status", "QC Pending")
        frappe.msgprint("Preparation marked complete. Stock deducted. Proceed to QC checkpoints.")

    @frappe.whitelist()
    def mark_wasted(self, reason=""):
        if self.preparation_status != "QC Pending":
            frappe.throw("Can only mark as Wasted when in QC Pending state.")

        from pluviago.pluviago_biotech.utils.stock_utils import log_waste
        if reason:
            self.db_set("remarks", (self.remarks or "") + f"\nWasted: {reason}")
        log_waste(self)
        self.db_set("preparation_status", "Wasted")
        self.db_set("status", "Wasted")
        frappe.msgprint("Batch marked as Wasted. Stock loss recorded in consumption log.")

    def on_submit(self):
        if self.preparation_status == "Draft":
            frappe.throw("Cannot submit: Click 'Mark Preparation Complete' before submitting.")
        if self.preparation_status == "Wasted":
            frappe.throw("Cannot submit a wasted batch.")
        if self.overall_qc_status != "Passed":
            frappe.throw("Cannot submit: Overall QC Status must be Passed.")

        self.db_set("preparation_status", "Released")
        self.db_set("status", "Approved")
        self.db_set("remaining_volume", self.medium_volume_calculated or 0)
        self.db_set("volume_consumed", 0)

        from pluviago.pluviago_biotech.utils.stock_utils import deduct_ssb_volume
        deduct_ssb_volume(self)

    def on_cancel(self):
        if self.preparation_status != "Draft":
            frappe.throw(
                "Cannot cancel a batch that has been physically prepared. "
                "Use 'Mark as Wasted' if QC failed."
            )
        from pluviago.pluviago_biotech.utils.stock_utils import (
            reverse_raw_materials, reverse_ssb_volume, reverse_di_water
        )
        reverse_ssb_volume(self)
        reverse_raw_materials(self)
        reverse_di_water(self)
        self.db_set("status", "Draft")


@frappe.whitelist()
def get_medium_formula(medium_type, target_volume):
    """
    Returns scaled base salt quantities and available SSB batches for the given
    medium type and target volume. Used by the Load Full Formula dialog.

    target_volume is in Litres (same unit as final_required_volume on the form).
    """
    target_volume = float(target_volume or 0)
    if target_volume <= 0:
        frappe.throw("Target volume must be greater than zero.")

    base_salts_def = _GREEN_BASE_SALTS if medium_type == "Green" else _RED_BASE_SALTS
    ssb_defs = _GREEN_SSB_ADDITIONS if medium_type == "Green" else _RED_SSB_ADDITIONS

    # Build scaled base salts + available RMBs per ingredient
    base_salts = []
    for ing in base_salts_def:
        scaled_qty = round(ing["qty_per_L"] * target_volume, 4)
        # Get item_code and available RMBs matching this chemical name
        rmbs = frappe.db.get_all(
            "Raw Material Batch",
            filters={
                "material_name": ing["chemical_name"],
                "docstatus": 1,
                "qc_status": "Approved",
            },
            fields=["name", "material_name", "remaining_qty", "received_qty_uom", "expiry_date"],
            order_by="expiry_date asc",
        )
        rmbs = [r for r in rmbs if (r.remaining_qty or 0) > 0]

        # Try to get item_code from one of the available RMBs
        item_code = ""
        if rmbs:
            item_code = frappe.db.get_value(
                "Raw Material Batch", rmbs[0]["name"], "item_code"
            ) or ""

        base_salts.append({
            "chemical_name": ing["chemical_name"],
            "item_code": item_code,
            "scaled_qty": scaled_qty,
            "uom": ing["uom"],
            "available_rmbs": rmbs,
        })

    # Build scaled SSB volumes + available SSB batches per solution type
    stock_solutions = []
    for ssb_def in ssb_defs:
        required_ml = round(ssb_def["vol_per_L_ml"] * target_volume, 4)
        ssbs = frappe.db.get_all(
            "Stock Solution Batch",
            filters={
                "solution_type": ssb_def["solution_type"],
                "docstatus": 1,
                "qc_status": "Approved",
                "preparation_status": "Released",
            },
            fields=["name", "available_volume", "volume_used", "expiry_date"],
            order_by="expiry_date asc",
        )
        for s in ssbs:
            s["remaining_ml"] = round(
                (s.available_volume or 0) * 1000 - (s.volume_used or 0), 2
            )
        ssbs = [s for s in ssbs if s["remaining_ml"] > 0]

        stock_solutions.append({
            "solution_type": ssb_def["solution_type"],
            "required_ml": required_ml,
            "add_last": ssb_def["add_last"],
            "available_ssbs": ssbs,
        })

    return {
        "medium_type": medium_type,
        "target_volume": target_volume,
        "base_salts": base_salts,
        "stock_solutions": stock_solutions,
    }
