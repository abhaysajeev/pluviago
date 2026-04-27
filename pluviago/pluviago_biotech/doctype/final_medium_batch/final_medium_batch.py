import frappe
from frappe.model.document import Document


class FinalMediumBatch(Document):
    def before_save(self):
        if not self.batch_number:
            self.batch_number = self.name
        if self.final_required_volume:
            self.green_medium_volume = self.final_required_volume * 0.75
            self.red_medium_volume = self.final_required_volume * 0.25
        if self.shelf_life_days and self.preparation_date:
            self.expiry_date = frappe.utils.add_days(self.preparation_date, int(self.shelf_life_days))

    def validate(self):
        _usable = ("Approved", "Partially Used")
        if self.green_medium_batch:
            row = frappe.db.get_value(
                "Medium Batch", self.green_medium_batch, ["status", "medium_type"], as_dict=True
            )
            if not row:
                frappe.throw(f"Medium Batch <b>{self.green_medium_batch}</b> not found.")
            if row.medium_type != "Green":
                frappe.throw(
                    f"<b>{self.green_medium_batch}</b> is a {row.medium_type} Medium batch. "
                    "The Green Medium field must link a Green type batch."
                )
            if row.status not in _usable:
                frappe.throw(
                    f"Green Medium Batch <b>{self.green_medium_batch}</b> has status <b>{row.status}</b>. "
                    "Only Approved or Partially Used batches can be used."
                )
        if self.red_medium_batch:
            row = frappe.db.get_value(
                "Medium Batch", self.red_medium_batch, ["status", "medium_type"], as_dict=True
            )
            if not row:
                frappe.throw(f"Medium Batch <b>{self.red_medium_batch}</b> not found.")
            if row.medium_type != "Red":
                frappe.throw(
                    f"<b>{self.red_medium_batch}</b> is a {row.medium_type} Medium batch. "
                    "The Red Medium field must link a Red type batch."
                )
            if row.status not in _usable:
                frappe.throw(
                    f"Red Medium Batch <b>{self.red_medium_batch}</b> has status <b>{row.status}</b>. "
                    "Only Approved or Partially Used batches can be used."
                )

        from pluviago.pluviago_biotech.utils.stock_utils import apply_corrective_action_logic
        apply_corrective_action_logic(self)

    def on_submit(self):
        if self.qc_status != "Passed":
            frappe.throw("Cannot submit: QC must be Passed")
        self.db_set("status", "Approved")
        self.db_set("remaining_volume", self.actual_final_volume or (self.final_required_volume or 0))
        self.db_set("volume_consumed", 0)

        from pluviago.pluviago_biotech.utils.stock_utils import deduct_medium_volume
        deduct_medium_volume(self)

    def on_cancel(self):
        self.db_set("status", "Draft")

        from pluviago.pluviago_biotech.utils.stock_utils import reverse_medium_volume
        reverse_medium_volume(self)
