import frappe


def deduct_raw_materials(doc, action="Consumed"):
    """
    Deduct ingredient quantities from linked Raw Material Batches.
    Called when preparation is physically complete (Mark Preparation Complete).
    Validates UOM match and over-consumption BEFORE making any changes (fail-fast).
    """
    rows = _get_ingredient_rows(doc)
    if not rows:
        return

    # Validate all rows first — no partial writes on failure
    for row in rows:
        _validate_row(row)

    # All clear — apply deductions
    for row in rows:
        qty = _get_qty(row)
        rmb = frappe.get_doc("Raw Material Batch", row.raw_material_batch)
        new_consumed = (rmb.consumed_qty or 0) + qty
        new_remaining = (rmb.received_qty or 0) - new_consumed
        new_status = "Exhausted" if new_remaining <= 0 else rmb.status

        frappe.db.set_value("Raw Material Batch", rmb.name, {
            "consumed_qty": new_consumed,
            "remaining_qty": new_remaining,
            "status": new_status,
        })
        _create_log(
            rmb=rmb,
            qty_change=-qty,
            balance_after=new_remaining,
            action=action,
            doc=doc,
        )


def reverse_raw_materials(doc):
    """
    Reverse a previous deduction.
    Only called when cancelling a batch that was NEVER physically prepared
    (preparation_status = 'Draft'). Adds a 'Reversed' log entry — original
    log entry is kept for full audit trail.
    """
    rows = _get_ingredient_rows(doc)
    if not rows:
        return

    affected_rmbs = []
    for row in rows:
        if not row.raw_material_batch:
            continue
        qty = _get_qty(row)
        rmb = frappe.get_doc("Raw Material Batch", row.raw_material_batch)
        new_consumed = max((rmb.consumed_qty or 0) - qty, 0)
        new_remaining = (rmb.received_qty or 0) - new_consumed

        if new_remaining > 0 and rmb.status == "Exhausted":
            new_status = "Approved"
        else:
            new_status = rmb.status

        frappe.db.set_value("Raw Material Batch", rmb.name, {
            "consumed_qty": new_consumed,
            "remaining_qty": new_remaining,
            "status": new_status,
        })
        _create_log(
            rmb=rmb,
            qty_change=qty,
            balance_after=new_remaining,
            action="Reversed",
            doc=doc,
        )
        affected_rmbs.append(rmb.name)

    # Recalculate from SCL as a safety reconciliation after all reversals
    for rmb_name in set(affected_rmbs):
        frappe.get_doc("Raw Material Batch", rmb_name).recalculate_remaining_qty()


def log_waste(doc):
    """
    Log all ingredient rows as Written Off (Loss) when a batch is marked Wasted.
    No stock reversal — chemicals were physically consumed.
    """
    rows = _get_ingredient_rows(doc)
    if not rows:
        return

    for row in rows:
        if not row.raw_material_batch:
            continue
        rmb = frappe.get_doc("Raw Material Batch", row.raw_material_batch)
        _create_log(
            rmb=rmb,
            qty_change=0,
            balance_after=(rmb.remaining_qty or 0),
            action="Written Off (Loss)",
            doc=doc,
            remarks="QC failed — batch wasted",
        )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_ingredient_rows(doc):
    """Return the relevant ingredient child table rows for the given doc."""
    if hasattr(doc, "ingredients") and doc.ingredients:
        return doc.ingredients
    if hasattr(doc, "direct_chemicals") and doc.direct_chemicals:
        return doc.direct_chemicals
    return []


def _get_qty(row):
    """Handle qty (Stock Solution Ingredient) vs quantity (Medium Direct Ingredient)."""
    return getattr(row, "qty", None) or getattr(row, "quantity", None) or 0


def _validate_row(row):
    """Validate UOM match and available stock before deduction."""
    if not row.raw_material_batch:
        frappe.throw(f"Row {row.idx}: Raw Material Batch is required.")

    rmb = frappe.db.get_value(
        "Raw Material Batch",
        row.raw_material_batch,
        ["name", "received_qty", "consumed_qty", "remaining_qty",
         "received_qty_uom", "status", "material_name"],
        as_dict=True,
    )
    if not rmb:
        frappe.throw(
            f"Row {row.idx}: Raw Material Batch <b>{row.raw_material_batch}</b> not found."
        )

    row_uom = getattr(row, "uom", None)
    if row_uom and rmb.received_qty_uom and row_uom != rmb.received_qty_uom:
        frappe.throw(
            f"Row {row.idx}: UOM mismatch for <b>{rmb.material_name}</b>. "
            f"Ingredient uses <b>{row_uom}</b> but Raw Material Batch "
            f"<b>{row.raw_material_batch}</b> was received in "
            f"<b>{rmb.received_qty_uom}</b>. Use the same UOM."
        )

    qty = _get_qty(row)
    available = (rmb.received_qty or 0) - (rmb.consumed_qty or 0)
    if qty > available:
        frappe.throw(
            f"Row {row.idx}: Over-consumption for <b>{rmb.material_name}</b>. "
            f"<b>{row.raw_material_batch}</b> has <b>{available} {rmb.received_qty_uom}</b> "
            f"available, but <b>{qty} {row_uom}</b> is being consumed."
        )


def _create_log(rmb, qty_change, balance_after, action, doc, remarks=""):
    """Insert one Stock Consumption Log record."""
    stage = getattr(doc, "solution_type", None) or doc.doctype.replace(" Batch", "")
    frappe.get_doc({
        "doctype": "Stock Consumption Log",
        "raw_material_batch": rmb.name,
        "material_name": rmb.material_name,
        "qty_change": qty_change,
        "uom": rmb.received_qty_uom,
        "balance_after": balance_after,
        "action": action,
        "source_doctype": doc.doctype,
        "source_document": doc.name,
        "preparation_stage": stage,
        "performed_by": frappe.session.user,
        "remarks": remarks,
    }).insert(ignore_permissions=True)


# ---------------------------------------------------------------------------
# Stock Solution Volume deduction (Task 1.2)
# ---------------------------------------------------------------------------

# Maps each doctype to its (ssb_link_field, volume_used_field) pairs.
# volume_used fields on medium batches are in mL.
# SSB available_volume is stored in L — converted to mL for all comparisons.
# SSB volume_used is stored in mL for operator-readable display.
_SSB_VOLUME_PAIRS = {
    "Green Medium Batch": [
        ("stock_solution_a1", "a1_volume_used"),
        ("stock_solution_a2", "a2_volume_used"),
        ("stock_solution_a3", "a3_volume_used"),
    ],
    "Red Medium Batch": [
        ("stock_solution_a4", "a4_volume_used"),
        ("stock_solution_a5", "a5_volume_used"),
        ("stock_solution_a6", "a6_volume_used"),
        ("stock_solution_a7", "a7_volume_used"),
        ("a5m_trace_stock_batch", "a5m_volume_used"),
    ],
}


def deduct_ssb_volume(doc):
    """
    Deduct mL volumes from linked Stock Solution Batches when a
    Green / Red Medium Batch is submitted.

    Validations (all rows checked before any write — fail-fast):
      - SSB must be preparation_status = Released
      - volume to consume must not exceed SSB remaining volume
    Auto-sets SSB status = 'Used' when volume_used_ml >= available_volume_ml.
    """
    pairs = _SSB_VOLUME_PAIRS.get(doc.doctype, [])
    if not pairs:
        return

    to_deduct = []
    for link_field, vol_field in pairs:
        ssb_name = doc.get(link_field)
        vol_ml = doc.get(vol_field) or 0
        if not ssb_name or vol_ml <= 0:
            continue  # field blank — skip silently

        ssb = frappe.db.get_value(
            "Stock Solution Batch",
            ssb_name,
            ["name", "preparation_status", "available_volume", "volume_used", "solution_type", "status"],
            as_dict=True,
        )
        if not ssb:
            frappe.throw(f"Stock Solution Batch <b>{ssb_name}</b> not found.")
        if ssb.preparation_status != "Released":
            frappe.throw(
                f"Stock Solution Batch <b>{ssb_name}</b> is not Released "
                f"(current status: <b>{ssb.preparation_status}</b>). "
                "Only Released batches may be consumed."
            )

        available_ml = (ssb.available_volume or 0) * 1000  # L → mL
        already_used_ml = ssb.volume_used or 0
        remaining_ml = available_ml - already_used_ml

        if vol_ml > remaining_ml:
            frappe.throw(
                f"<b>{ssb_name}</b> ({ssb.solution_type}): "
                f"only <b>{remaining_ml:.2f} mL</b> remaining, "
                f"but <b>{vol_ml} mL</b> is being consumed."
            )

        to_deduct.append((ssb, vol_ml))

    # All validations passed — apply writes
    for ssb, vol_ml in to_deduct:
        new_used_ml = (ssb.volume_used or 0) + vol_ml
        available_ml = (ssb.available_volume or 0) * 1000
        new_status = "Used" if new_used_ml >= available_ml else ssb.status

        frappe.db.set_value("Stock Solution Batch", ssb.name, {
            "volume_used": new_used_ml,
            "status": new_status,
        })


def reverse_ssb_volume(doc):
    """
    Reverse SSB volume deduction when a Green / Red Medium Batch is cancelled.
    Restores SSB status from 'Used' → 'Approved' if volume drops below the available limit.
    """
    pairs = _SSB_VOLUME_PAIRS.get(doc.doctype, [])
    if not pairs:
        return

    for link_field, vol_field in pairs:
        ssb_name = doc.get(link_field)
        vol_ml = doc.get(vol_field) or 0
        if not ssb_name or vol_ml <= 0:
            continue

        ssb = frappe.db.get_value(
            "Stock Solution Batch",
            ssb_name,
            ["name", "available_volume", "volume_used", "status"],
            as_dict=True,
        )
        if not ssb:
            continue

        new_used_ml = max((ssb.volume_used or 0) - vol_ml, 0)
        available_ml = (ssb.available_volume or 0) * 1000
        new_status = (
            "Approved"
            if ssb.status == "Used" and new_used_ml < available_ml
            else ssb.status
        )

        frappe.db.set_value("Stock Solution Batch", ssb.name, {
            "volume_used": new_used_ml,
            "status": new_status,
        })


# ---------------------------------------------------------------------------
# Corrective Action helpers (Task 3.2)
# ---------------------------------------------------------------------------

def apply_corrective_action_logic(doc):
    """
    Called from validate() on Green/Red/Final Medium Batch.

    1. Auto-numbers corrective action rows (attempt_number).
    2. Sets doc.quality_flag:
       - "Conditional Release"  → corrective actions exist AND last re_qc_result = "Pass"
       - "Rejected"             → overall_qc_status = "Failed" + last re_qc_result = "Fail"
                                   (only if no corrective action pending)
       - "Normal"               → clean pass, no corrective actions
    3. Validates: if overall_qc_status = "Passed" but corrective actions exist and
       last re_qc_result ≠ "Pass", throws — the re-QC must pass before submission.
    """
    # Auto-number rows
    for i, row in enumerate(doc.corrective_actions or [], start=1):
        row.attempt_number = i

    ca_rows = doc.corrective_actions or []
    last_re_qc = ca_rows[-1].re_qc_result if ca_rows else None

    if not ca_rows:
        # No corrective actions — quality depends purely on QC status
        doc.quality_flag = "Normal"
    elif last_re_qc == "Pass":
        doc.quality_flag = "Conditional Release"
    elif last_re_qc == "Fail":
        doc.quality_flag = "Rejected"
        doc.overall_qc_status = "Failed"  # keep QC status consistent
    else:
        # Corrective action logged but re-QC not yet done — leave flag as-is
        pass

    # Guard: if user tries to mark overall Passed but re-QC hasn't passed yet
    overall = getattr(doc, "overall_qc_status", None)
    if overall == "Passed" and ca_rows and last_re_qc not in ("Pass", None):
        frappe.throw(
            "Overall QC Status cannot be Passed while the last Re-QC result "
            f"is <b>{last_re_qc}</b>. Update the corrective action Re-QC Result to Pass first."
        )
