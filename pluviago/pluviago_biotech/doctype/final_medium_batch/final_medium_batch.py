import frappe
from frappe.model.document import Document

_RATIO = {"Green": 75.0, "Red": 25.0}


class FinalMediumBatch(Document):
    def before_save(self):
        if not self.batch_number:
            self.batch_number = self.name
        frv = self.final_required_volume or 0
        for row in self.medium_sources or []:
            ratio = _RATIO.get(row.medium_type, 0)
            row.ratio_pct = ratio
            row.volume_required = round(frv * ratio / 100, 6) if frv else 0
        if not self.actual_final_volume and frv:
            self.actual_final_volume = frv
        if self.shelf_life_days and self.preparation_date:
            self.expiry_date = frappe.utils.add_days(self.preparation_date, int(self.shelf_life_days))

    def validate(self):
        frv = self.final_required_volume or 0
        _usable = ("Approved", "Partially Used")

        for row in self.medium_sources or []:
            if not row.medium_batch:
                continue

            ratio = _RATIO.get(row.medium_type, 0)
            required_vol = round(frv * ratio / 100, 6) if frv else (row.volume_required or 0)

            mb = frappe.db.get_value(
                "Medium Batch", row.medium_batch,
                ["status", "medium_type", "remaining_volume", "expiry_date"], as_dict=True,
            )
            if not mb:
                frappe.throw(f"Row {row.idx}: Medium Batch <b>{row.medium_batch}</b> not found.")
            if mb.medium_type != row.medium_type:
                frappe.throw(
                    f"Row {row.idx}: <b>{row.medium_batch}</b> is a {mb.medium_type} batch "
                    f"but the row is set to <b>{row.medium_type}</b>. They must match."
                )
            if mb.status not in _usable:
                frappe.throw(
                    f"Row {row.idx}: {row.medium_type} Medium Batch <b>{row.medium_batch}</b> "
                    f"has status <b>{mb.status}</b>. Only Approved or Partially Used batches can be used."
                )
            if mb.expiry_date and str(mb.expiry_date) < frappe.utils.today():
                frappe.throw(
                    f"Row {row.idx}: Medium Batch <b>{row.medium_batch}</b> expired on "
                    f"<b>{mb.expiry_date}</b>."
                )
            if required_vol:
                remaining = mb.remaining_volume or 0
                if required_vol > remaining:
                    frappe.throw(
                        f"Row {row.idx}: {row.medium_type} Medium Batch <b>{row.medium_batch}</b> "
                        f"only has <b>{remaining:.3f} L</b> remaining but "
                        f"<b>{required_vol:.3f} L</b> is required ({ratio:.0f}% of {frv} L)."
                    )

        from pluviago.pluviago_biotech.utils.stock_utils import apply_corrective_action_logic
        apply_corrective_action_logic(self)

    def on_submit(self):
        if self.qc_status != "Passed":
            frappe.throw("Cannot submit: QC Checkpoint 5 must be Passed.")
        if not self.aseptic_mixing_done:
            frappe.throw("Cannot submit: Aseptic Mixing must be confirmed before submission.")
        if not self.medium_sources:
            frappe.throw("Cannot submit: Medium Sources table must have at least one row.")

        actual = self.actual_final_volume or self.final_required_volume or 0
        self.db_set("actual_final_volume", actual)
        self.db_set("status", "Approved")
        self.db_set("remaining_volume", actual)
        self.db_set("volume_consumed", 0)

        from pluviago.pluviago_biotech.utils.stock_utils import deduct_medium_volume
        deduct_medium_volume(self)

    def on_cancel(self):
        if (self.remaining_volume or 0) < (self.actual_final_volume or self.final_required_volume or 0):
            frappe.throw(
                "Cannot cancel: this Final Medium Batch has already been partially consumed by a "
                "Production Batch. Cancel the Production Batch first."
            )
        self.db_set("status", "Draft")
        self.db_set("remaining_volume", 0)
        self.db_set("volume_consumed", 0)

        from pluviago.pluviago_biotech.utils.stock_utils import reverse_medium_volume
        reverse_medium_volume(self)


@frappe.whitelist()
def get_fmb_formula(target_volume):
    """
    Returns available Green and Red Medium Batches for the given target volume
    with computed 75:25 split volumes. Used by the Load Formula dialog.
    """
    target_volume = float(target_volume or 0)
    if target_volume <= 0:
        frappe.throw("Target volume must be greater than zero.")

    green_vol = round(target_volume * 0.75, 6)
    red_vol   = round(target_volume * 0.25, 6)
    today = frappe.utils.today()

    green_batches = frappe.db.sql("""
        SELECT name, remaining_volume, expiry_date, status
        FROM `tabMedium Batch`
        WHERE medium_type = 'Green'
          AND docstatus = 1
          AND status IN ('Approved', 'Partially Used')
          AND (expiry_date IS NULL OR expiry_date >= %s)
          AND (remaining_volume IS NULL OR remaining_volume > 0)
        ORDER BY expiry_date ASC
    """, today, as_dict=True)

    red_batches = frappe.db.sql("""
        SELECT name, remaining_volume, expiry_date, status
        FROM `tabMedium Batch`
        WHERE medium_type = 'Red'
          AND docstatus = 1
          AND status IN ('Approved', 'Partially Used')
          AND (expiry_date IS NULL OR expiry_date >= %s)
          AND (remaining_volume IS NULL OR remaining_volume > 0)
        ORDER BY expiry_date ASC
    """, today, as_dict=True)

    return {
        "target_volume": target_volume,
        "green_volume":  green_vol,
        "red_volume":    red_vol,
        "green_batches": green_batches,
        "red_batches":   red_batches,
    }
