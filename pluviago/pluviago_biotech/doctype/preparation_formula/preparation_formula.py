import frappe
from frappe.model.document import Document


class PreparationFormula(Document):
    pass


@frappe.whitelist()
def get_formula_with_batches(formula_name, target_volume):
    """
    Return scaled ingredient list for the given formula + target_volume,
    with available approved RMBs per ingredient for manual batch selection.
    """
    formula = frappe.get_doc("Preparation Formula", formula_name)
    target_volume = float(target_volume or 0)
    ref_volume = float(formula.reference_volume or 1)
    scale = (target_volume / ref_volume) if ref_volume else 1

    # Fetch all needed item codes in one query
    item_codes = [row.item_code for row in formula.items if row.item_code]
    batch_map = _get_batches_by_item(item_codes)

    items = []
    for row in formula.items:
        scaled_qty = round((row.quantity or 0) * scale, 6)
        items.append({
            "item_code": row.item_code,
            "material_name": row.material_name or row.item_code,
            "quantity": scaled_qty,
            "uom": row.uom,
            "notes": row.notes,
            "available_batches": batch_map.get(row.item_code, []),
        })

    return {
        "formula_name": formula.formula_name,
        "applies_to": formula.applies_to,
        "items": items,
    }


def _get_batches_by_item(item_codes):
    if not item_codes:
        return {}
    placeholders = ", ".join(["%s"] * len(item_codes))
    rows = frappe.db.sql(f"""
        SELECT item_code, name, material_name, remaining_qty, received_qty_uom, expiry_date
        FROM `tabRaw Material Batch`
        WHERE item_code IN ({placeholders})
          AND docstatus = 1
          AND qc_status = 'Approved'
          AND remaining_qty > 0
        ORDER BY item_code, expiry_date ASC
    """, item_codes, as_dict=True)

    result = {}
    for r in rows:
        result.setdefault(r.item_code, []).append({
            "name": r.name,
            "material_name": r.material_name or "",
            "remaining_qty": r.remaining_qty,
            "received_qty_uom": r.received_qty_uom,
            "expiry_date": str(r.expiry_date) if r.expiry_date else "",
        })
    return result
