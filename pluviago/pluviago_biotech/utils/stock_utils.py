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
# Stock Solution Volume deduction
# ---------------------------------------------------------------------------
# SSB available_volume is stored in L; SSB volume_used is stored in mL.
# All comparisons are done in mL via _ssb_remaining_ml().

def _ssb_remaining_ml(ssb):
    """Single conversion point: L → mL for available_volume vs mL volume_used."""
    return (ssb.available_volume or 0) * 1000 - (ssb.volume_used or 0)


def deduct_ssb_volume(doc):
    """
    Deduct mL volumes from linked Stock Solution Batches when a
    Green / Red Medium Batch is submitted.
    Reads from the ssb_used child table (Medium SSB Usage rows).
    Fail-fast: all rows validated before any write.
    """
    rows = getattr(doc, "ssb_used", []) or []
    if not rows:
        return

    to_deduct = []
    for row in rows:
        if not row.stock_solution_batch or not row.volume_used_ml:
            continue

        ssb = frappe.db.get_value(
            "Stock Solution Batch",
            row.stock_solution_batch,
            ["name", "preparation_status", "available_volume", "volume_used",
             "solution_type", "status", "expiry_date"],
            as_dict=True,
        )
        if not ssb:
            frappe.throw(f"Row {row.idx}: Stock Solution Batch <b>{row.stock_solution_batch}</b> not found.")
        if ssb.expiry_date and str(ssb.expiry_date) < frappe.utils.today():
            frappe.throw(
                f"Row {row.idx}: <b>{row.stock_solution_batch}</b> ({ssb.solution_type}) "
                f"expired on <b>{ssb.expiry_date}</b>."
            )
        if ssb.preparation_status != "Released":
            frappe.throw(
                f"Row {row.idx}: <b>{row.stock_solution_batch}</b> is not Released "
                f"(status: <b>{ssb.preparation_status}</b>). Only Released batches may be consumed."
            )

        remaining_ml = _ssb_remaining_ml(ssb)
        if row.volume_used_ml > remaining_ml:
            frappe.throw(
                f"Row {row.idx}: <b>{row.stock_solution_batch}</b> ({ssb.solution_type}): "
                f"only <b>{remaining_ml:.2f} mL</b> remaining, "
                f"but <b>{row.volume_used_ml} mL</b> is being consumed."
            )
        to_deduct.append((ssb, row.volume_used_ml))

    for ssb, vol_ml in to_deduct:
        new_used_ml = round((ssb.volume_used or 0) + vol_ml, 6)
        available_ml = (ssb.available_volume or 0) * 1000
        new_status = "Used" if new_used_ml >= available_ml else "Partially Used"
        frappe.db.set_value("Stock Solution Batch", ssb.name, {
            "volume_used": new_used_ml,
            "status": new_status,
        })


def reverse_ssb_volume(doc):
    """
    Reverse SSB volume deductions when a Green / Red Medium Batch is cancelled.
    Iterates ssb_used child table — symmetric with deduct_ssb_volume.
    """
    rows = getattr(doc, "ssb_used", []) or []
    for row in rows:
        if not row.stock_solution_batch or not row.volume_used_ml:
            continue

        ssb = frappe.db.get_value(
            "Stock Solution Batch",
            row.stock_solution_batch,
            ["name", "available_volume", "volume_used", "status"],
            as_dict=True,
        )
        if not ssb:
            continue

        new_used_ml = round(max((ssb.volume_used or 0) - row.volume_used_ml, 0), 6)
        new_status = "Approved" if new_used_ml <= 0 else "Partially Used"
        frappe.db.set_value("Stock Solution Batch", ssb.name, {
            "volume_used": new_used_ml,
            "status": new_status,
        })


# ---------------------------------------------------------------------------
# Batch lineage queries (reverse direction)
# ---------------------------------------------------------------------------

@frappe.whitelist()
def get_ssb_lineage(ssb_name):
    """Return all medium batches that consumed the given Stock Solution Batch."""
    rows = frappe.db.sql("""
        SELECT u.parent AS medium_batch, mb.medium_type, u.volume_used_ml
        FROM `tabMedium SSB Usage` u
        LEFT JOIN `tabMedium Batch` mb ON mb.name = u.parent
        WHERE u.stock_solution_batch = %s AND u.parenttype = 'Medium Batch'
    """, ssb_name, as_dict=True)
    return rows


@frappe.whitelist()
def get_medium_lineage(batch_name, batch_doctype):
    """Return all downstream batches that consumed the given Medium Batch or Final Medium Batch."""
    result = {}
    if batch_doctype == "Medium Batch":
        fmbs = frappe.db.sql("""
            SELECT DISTINCT fmb.name, fmb.preparation_date, fmb.status
            FROM `tabFinal Medium Batch` fmb
            JOIN `tabFMB Medium Source` src ON src.parent = fmb.name
            WHERE src.medium_batch = %s
        """, batch_name, as_dict=True)
        result["final_medium_batches"] = fmbs
        fmb_names = [f["name"] for f in fmbs]
        if fmb_names:
            prod = frappe.db.get_all(
                "Production Batch",
                filters=[["final_medium_batch", "in", fmb_names]],
                fields=["name", "preparation_date", "status"],
            )
            result["production_batches"] = prod
    elif batch_doctype == "Final Medium Batch":
        prod = frappe.db.get_all(
            "Production Batch",
            filters=[["final_medium_batch", "=", batch_name]],
            fields=["name", "preparation_date", "status"],
        )
        result["production_batches"] = prod
    return result


# ---------------------------------------------------------------------------
# Medium Batch volume deduction
# ---------------------------------------------------------------------------

def deduct_medium_volume(doc):
    """
    Deduct L volumes from linked Medium Batches when a Final Medium Batch is submitted,
    or from a Final Medium Batch when a Production Batch is submitted.
    """
    if doc.doctype == "Final Medium Batch":
        _deduct_from_medium_sources(doc)
    else:
        # Production Batch → deduct from Final Medium Batch
        _deduct_from_fmb(doc)


def _deduct_from_medium_sources(fmb_doc):
    """Iterate FMB medium_sources child table and deduct each row from its Medium Batch."""
    to_deduct = []
    for row in fmb_doc.medium_sources or []:
        if not row.medium_batch or not (row.volume_required or 0):
            continue
        mb = frappe.db.get_value(
            "Medium Batch", row.medium_batch,
            ["name", "status", "remaining_volume", "medium_volume_calculated",
             "volume_consumed", "expiry_date"],
            as_dict=True,
        )
        if not mb:
            frappe.throw(f"Row {row.idx}: Medium Batch <b>{row.medium_batch}</b> not found.")
        if mb.expiry_date and str(mb.expiry_date) < frappe.utils.today():
            frappe.throw(
                f"Row {row.idx}: Medium Batch <b>{row.medium_batch}</b> expired on "
                f"<b>{mb.expiry_date}</b>. Expired batches cannot be consumed."
            )
        remaining = mb.remaining_volume
        if remaining is None:
            remaining = mb.medium_volume_calculated or 0
        vol = row.volume_required
        if vol > remaining:
            frappe.throw(
                f"Row {row.idx}: Medium Batch <b>{row.medium_batch}</b>: only "
                f"<b>{remaining:.3f} L</b> remaining but <b>{vol:.3f} L</b> is being consumed."
            )
        to_deduct.append((mb, vol, remaining))

    for mb, vol, remaining in to_deduct:
        new_remaining = round(remaining - vol, 6)
        new_consumed = round((mb.volume_consumed or 0) + vol, 6)
        new_status = "Used" if new_remaining <= 0 else "Partially Used"
        frappe.db.set_value("Medium Batch", mb.name, {
            "remaining_volume": new_remaining,
            "volume_consumed": new_consumed,
            "status": new_status,
        })


def _deduct_from_fmb(prod_doc):
    """Production Batch submission — deduct consumed volume from Final Medium Batch."""
    batch_name = prod_doc.get("final_medium_batch")
    vol = prod_doc.get("medium_volume_used") or 0
    if not batch_name or vol <= 0:
        return

    fmb = frappe.db.get_value(
        "Final Medium Batch", batch_name,
        ["name", "status", "remaining_volume", "actual_final_volume",
         "final_required_volume", "volume_consumed", "expiry_date"],
        as_dict=True,
    )
    if not fmb:
        frappe.throw(f"Final Medium Batch <b>{batch_name}</b> not found.")
    if fmb.expiry_date and str(fmb.expiry_date) < frappe.utils.today():
        frappe.throw(
            f"Final Medium Batch <b>{batch_name}</b> expired on <b>{fmb.expiry_date}</b>. "
            "Expired batches cannot be consumed."
        )
    remaining = fmb.remaining_volume
    if remaining is None:
        remaining = fmb.actual_final_volume or fmb.final_required_volume or 0
    if vol > remaining:
        frappe.throw(
            f"Final Medium Batch <b>{batch_name}</b>: only <b>{remaining:.3f} L</b> remaining, "
            f"but <b>{vol:.3f} L</b> is being consumed."
        )
    new_remaining = round(remaining - vol, 6)
    new_consumed = round((fmb.volume_consumed or 0) + vol, 6)
    new_status = "Used" if new_remaining <= 0 else "Partially Used"
    frappe.db.set_value("Final Medium Batch", fmb.name, {
        "remaining_volume": new_remaining,
        "volume_consumed": new_consumed,
        "status": new_status,
    })


def reverse_medium_volume(doc):
    """
    Restore medium batch volumes when a Final Medium Batch or Production Batch is cancelled.
    """
    if doc.doctype == "Final Medium Batch":
        _reverse_medium_sources(doc)
    else:
        _reverse_fmb(doc)


def _reverse_medium_sources(fmb_doc):
    """Restore Medium Batch volumes from FMB medium_sources child table rows."""
    for row in fmb_doc.medium_sources or []:
        if not row.medium_batch or not (row.volume_required or 0):
            continue
        mb = frappe.db.get_value(
            "Medium Batch", row.medium_batch,
            ["name", "remaining_volume", "volume_consumed", "status"],
            as_dict=True,
        )
        if not mb:
            continue
        vol = row.volume_required
        new_remaining = round((mb.remaining_volume or 0) + vol, 6)
        new_consumed = round(max((mb.volume_consumed or 0) - vol, 0), 6)
        new_status = "Approved" if new_consumed <= 0 else "Partially Used"
        frappe.db.set_value("Medium Batch", mb.name, {
            "remaining_volume": new_remaining,
            "volume_consumed": new_consumed,
            "status": new_status,
        })


def _reverse_fmb(prod_doc):
    """Restore Final Medium Batch volume when a Production Batch is cancelled."""
    batch_name = prod_doc.get("final_medium_batch")
    vol = prod_doc.get("medium_volume_used") or 0
    if not batch_name or vol <= 0:
        return

    fmb = frappe.db.get_value(
        "Final Medium Batch", batch_name,
        ["name", "remaining_volume", "volume_consumed", "status"],
        as_dict=True,
    )
    if not fmb:
        return
    new_remaining = round((fmb.remaining_volume or 0) + vol, 6)
    new_consumed = round(max((fmb.volume_consumed or 0) - vol, 0), 6)
    new_status = "Approved" if new_consumed <= 0 else "Partially Used"
    frappe.db.set_value("Final Medium Batch", fmb.name, {
        "remaining_volume": new_remaining,
        "volume_consumed": new_consumed,
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
