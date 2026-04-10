"""
Medium Batch Lifecycle Report
==============================
Shows the complete lifecycle of a Final Medium Batch:

  UPSTREAM (what built this FMB)
    Raw Material Batch → Stock Solution Batch → Green/Red Medium Batch → Final Medium Batch

  DOWNSTREAM (where it was consumed)
    Final Medium Batch → Production Batch(es) → Harvest Batch → Extraction Batch

Filter: final_medium_batch (required)
"""

import frappe


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def execute(filters=None):
    filters = filters or {}
    fmb_name = filters.get("final_medium_batch")
    if not fmb_name:
        frappe.msgprint("Please select a Final Medium Batch.", alert=True)
        return get_columns(), []

    fmb = frappe.db.get_value(
        "Final Medium Batch", fmb_name,
        ["name", "batch_number", "preparation_date", "prepared_by",
         "final_required_volume", "actual_final_volume", "remaining_volume",
         "volume_consumed", "green_medium_batch", "green_medium_volume",
         "red_medium_batch", "red_medium_volume", "qc_status", "status",
         "expiry_date", "shelf_life_days", "storage_condition"],
        as_dict=True,
    )
    if not fmb:
        frappe.throw(f"Final Medium Batch <b>{fmb_name}</b> not found.")

    rows = []
    _add_upstream(rows, fmb)
    _add_fmb_row(rows, fmb)
    _add_downstream(rows, fmb_name)
    return get_columns(), rows


# ---------------------------------------------------------------------------
# Columns
# ---------------------------------------------------------------------------

def get_columns():
    return [
        {"label": "Layer", "fieldname": "layer", "fieldtype": "Data", "width": 240},
        {"label": "Batch / Document", "fieldname": "batch_name", "fieldtype": "Data", "width": 180},
        {"label": "Type", "fieldname": "batch_type", "fieldtype": "Data", "width": 140},
        {"label": "Date", "fieldname": "event_date", "fieldtype": "Date", "width": 110},
        {"label": "Volume / Qty", "fieldname": "volume", "fieldtype": "Data", "width": 130},
        {"label": "Consumed", "fieldname": "consumed", "fieldtype": "Data", "width": 120},
        {"label": "Remaining", "fieldname": "remaining", "fieldtype": "Data", "width": 120},
        {"label": "QC / Status", "fieldname": "qc_status", "fieldtype": "Data", "width": 130},
        {"label": "Expiry Date", "fieldname": "expiry_date", "fieldtype": "Date", "width": 110},
        {"label": "Remarks", "fieldname": "remarks", "fieldtype": "Data", "width": 220},
    ]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _row(layer, batch_name, batch_type, event_date=None, volume=None,
         consumed=None, remaining=None, qc_status=None, expiry_date=None,
         remarks=None, bold=False):
    return {
        "layer": layer,
        "batch_name": batch_name or "",
        "batch_type": batch_type or "",
        "event_date": event_date,
        "volume": volume or "",
        "consumed": consumed or "",
        "remaining": remaining or "",
        "qc_status": qc_status or "",
        "expiry_date": expiry_date,
        "remarks": remarks or "",
        "bold": 1 if bold else 0,
    }


def _vol(val, unit="L"):
    if val is None:
        return ""
    return f"{val:.3f} {unit}"


# ---------------------------------------------------------------------------
# Upstream: Raw Material → SSB → GMB/RMB → FMB
# ---------------------------------------------------------------------------

def _add_upstream(rows, fmb):
    rows.append(_row("━━ UPSTREAM ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
                     "", "", bold=True))

    # Green Medium Batch
    if fmb.green_medium_batch:
        _add_medium_branch(rows, "Green Medium Batch", fmb.green_medium_batch,
                           fmb.green_medium_volume, "  └─ GMB →")

    # Red Medium Batch
    if fmb.red_medium_batch:
        _add_medium_branch(rows, "Red Medium Batch", fmb.red_medium_batch,
                           fmb.red_medium_volume, "  └─ RMB →")


def _add_medium_branch(rows, doctype, batch_name, vol_used_fmb, prefix):
    mb = frappe.db.get_value(
        doctype, batch_name,
        ["name", "batch_number", "preparation_date", "prepared_by",
         "remaining_volume", "volume_consumed",
         "green_volume_calculated" if doctype == "Green Medium Batch" else "red_volume_calculated",
         "overall_qc_status" if doctype in ("Green Medium Batch", "Red Medium Batch") else "qc_status",
         "status", "expiry_date"],
        as_dict=True,
    )
    if not mb:
        return

    capacity = mb.get("green_volume_calculated") or mb.get("red_volume_calculated") or 0
    qc = mb.get("overall_qc_status") or mb.get("qc_status") or ""
    short = "GMB" if doctype == "Green Medium Batch" else "RMB"

    rows.append(_row(
        layer=f"{prefix} {batch_name}",
        batch_name=batch_name,
        batch_type=short,
        event_date=mb.preparation_date,
        volume=_vol(capacity),
        consumed=_vol(mb.volume_consumed),
        remaining=_vol(mb.remaining_volume),
        qc_status=f"{qc} / {mb.status}",
        expiry_date=mb.expiry_date,
        remarks=f"Used {_vol(vol_used_fmb)} in this FMB",
    ))

    # SSBs used in this GMB/RMB
    _add_ssb_rows(rows, doctype, batch_name)


def _add_ssb_rows(rows, doctype, batch_name):
    ssb_fields = {
        "Green Medium Batch": [
            ("stock_solution_a1", "a1_volume_used", "A1"),
            ("stock_solution_a2", "a2_volume_used", "A2"),
            ("stock_solution_a3", "a3_volume_used", "A3"),
        ],
        "Red Medium Batch": [
            ("stock_solution_a4",     "a4_volume_used",     "A4"),
            ("stock_solution_a5",     "a5_volume_used",     "A5"),
            ("stock_solution_a6",     "a6_volume_used",     "A6"),
            ("a5m_trace_stock_batch", "a5m_volume_used",    "A5M"),
            ("stock_solution_a7_i",   "a7_i_volume_used",   "A7-I"),
            ("stock_solution_a7_ii",  "a7_ii_volume_used",  "A7-II"),
            ("stock_solution_a7_iii", "a7_iii_volume_used", "A7-III"),
            ("stock_solution_a7_iv",  "a7_iv_volume_used",  "A7-IV"),
            ("stock_solution_a7_v",   "a7_v_volume_used",   "A7-V"),
            ("stock_solution_a7_vi",  "a7_vi_volume_used",  "A7-VI"),
        ],
    }

    mb_doc = frappe.db.get_value(
        doctype, batch_name,
        [f for f, _, _ in ssb_fields.get(doctype, [])] +
        [v for _, v, _ in ssb_fields.get(doctype, [])],
        as_dict=True,
    )
    if not mb_doc:
        return

    for link_field, vol_field, label in ssb_fields.get(doctype, []):
        ssb_name = mb_doc.get(link_field)
        vol_ml = mb_doc.get(vol_field) or 0
        if not ssb_name:
            continue

        ssb = frappe.db.get_value(
            "Stock Solution Batch", ssb_name,
            ["name", "preparation_date", "available_volume", "volume_used",
             "preparation_status", "expiry_date"],
            as_dict=True,
        )
        if not ssb:
            continue

        available_ml = (ssb.available_volume or 0) * 1000
        rows.append(_row(
            layer=f"      └─ SSB ({label}) → {ssb_name}",
            batch_name=ssb_name,
            batch_type=f"SSB {label}",
            event_date=ssb.preparation_date,
            volume=_vol(available_ml, "mL"),
            consumed=_vol(ssb.volume_used, "mL"),
            remaining=_vol(available_ml - (ssb.volume_used or 0), "mL"),
            qc_status=ssb.preparation_status,
            expiry_date=ssb.expiry_date,
            remarks=f"Used {_vol(vol_ml, 'mL')} in {doctype.replace(' Batch','').replace('Green Medium','GMB').replace('Red Medium','RMB')}",
        ))

        # Raw materials used in this SSB
        _add_raw_material_rows(rows, ssb_name)


def _add_raw_material_rows(rows, ssb_name):
    ingredients = frappe.get_all(
        "Stock Solution Ingredient",
        filters={"parent": ssb_name},
        fields=["raw_material_batch", "item_name", "qty", "uom"],
    )
    for ing in ingredients:
        if not ing.raw_material_batch:
            continue
        rmb = frappe.db.get_value(
            "Raw Material Batch", ing.raw_material_batch,
            ["name", "material_name", "received_qty", "consumed_qty",
             "remaining_qty", "received_qty_uom", "status", "expiry_date"],
            as_dict=True,
        )
        if not rmb:
            continue
        rows.append(_row(
            layer=f"         └─ RM → {rmb.name}",
            batch_name=rmb.name,
            batch_type="Raw Material",
            volume=_vol(rmb.received_qty, rmb.received_qty_uom or ""),
            consumed=_vol(rmb.consumed_qty, rmb.received_qty_uom or ""),
            remaining=_vol(rmb.remaining_qty, rmb.received_qty_uom or ""),
            qc_status=rmb.status,
            expiry_date=rmb.expiry_date,
            remarks=f"{rmb.material_name} — used {ing.qty} {ing.uom or ''}",
        ))


# ---------------------------------------------------------------------------
# FMB itself
# ---------------------------------------------------------------------------

def _add_fmb_row(rows, fmb):
    rows.append(_row("", "", "", bold=False))  # spacer
    rows.append(_row(
        layer="━━ FINAL MEDIUM BATCH ━━━━━━━━━━━━━━━━━━━━━━━━━",
        batch_name="", batch_type="", bold=True,
    ))
    rows.append(_row(
        layer=f"  {fmb.name}",
        batch_name=fmb.name,
        batch_type="FMB",
        event_date=fmb.preparation_date,
        volume=_vol(fmb.actual_final_volume or fmb.final_required_volume),
        consumed=_vol(fmb.volume_consumed),
        remaining=_vol(fmb.remaining_volume),
        qc_status=f"{fmb.qc_status} / {fmb.status}",
        expiry_date=fmb.expiry_date,
        remarks=f"Storage: {fmb.storage_condition or 'N/A'} | Shelf life: {fmb.shelf_life_days or 'N/A'} days",
        bold=True,
    ))


# ---------------------------------------------------------------------------
# Downstream: FMB → Production Batch → Harvest Batch → Extraction Batch
# ---------------------------------------------------------------------------

def _add_downstream(rows, fmb_name):
    rows.append(_row("", "", "", bold=False))  # spacer
    rows.append(_row("━━ DOWNSTREAM ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
                     "", "", bold=True))

    prod_batches = frappe.get_all(
        "Production Batch",
        filters={"final_medium_batch": fmb_name},
        fields=["name", "current_stage", "strain", "generation_number",
                "parent_batch", "inoculation_date", "stage_decision",
                "status", "lineage_status", "medium_volume_used",
                "harvest_batch", "contamination_status"],
        order_by="inoculation_date asc",
    )

    if not prod_batches:
        rows.append(_row("  (No Production Batches consumed this FMB yet)",
                         "", "", remarks=""))
        return

    for pb in prod_batches:
        rows.append(_row(
            layer=f"  └─ PB → {pb.name}",
            batch_name=pb.name,
            batch_type=f"Production ({pb.current_stage})",
            event_date=pb.inoculation_date,
            volume=_vol(pb.medium_volume_used),
            consumed=_vol(pb.medium_volume_used),
            qc_status=f"{pb.status} / {pb.lineage_status}",
            remarks=(
                f"Strain: {pb.strain or 'N/A'} | Gen {pb.generation_number} | "
                f"Decision: {pb.stage_decision or 'Pending'} | "
                f"Contamination: {pb.contamination_status or 'Clean'}"
            ),
        ))

        # Harvest Batch
        if pb.harvest_batch:
            _add_harvest_row(rows, pb.harvest_batch)

        # Child batches created from this PB (Scale Up or Return-to-Cultivation)
        children = frappe.get_all(
            "Production Batch",
            filters={"parent_batch": pb.name},
            fields=["name", "current_stage", "generation_number",
                    "inoculation_date", "status", "stage_decision"],
            order_by="inoculation_date asc",
        )
        for child in children:
            rows.append(_row(
                layer=f"      └─ Child PB → {child.name}",
                batch_name=child.name,
                batch_type=f"Child ({child.current_stage})",
                event_date=child.inoculation_date,
                qc_status=child.status,
                remarks=f"Gen {child.generation_number} | Decision: {child.stage_decision or 'Pending'}",
            ))


def _add_harvest_row(rows, hb_name):
    hb = frappe.db.get_value(
        "Harvest Batch", hb_name,
        ["name", "harvest_date", "harvested_volume", "actual_dry_weight",
         "yield_percentage", "qc_status", "status"],
        as_dict=True,
    )
    if not hb:
        return

    rows.append(_row(
        layer=f"      └─ HB → {hb.name}",
        batch_name=hb.name,
        batch_type="Harvest",
        event_date=hb.harvest_date,
        volume=_vol(hb.harvested_volume),
        qc_status=f"{hb.qc_status} / {hb.status}",
        remarks=(
            f"Dry weight: {hb.actual_dry_weight or 'N/A'} kg | "
            f"Yield: {round(hb.yield_percentage, 1) if hb.yield_percentage else 'N/A'}%"
        ),
    ))

    # Extraction Batch linked to this Harvest Batch
    eb = frappe.db.get_value(
        "Extraction Batch",
        {"harvest_batch": hb_name, "docstatus": ("!=", 2)},
        ["name", "dispatch_date", "dispatch_qty", "incoming_qc_status",
         "extract_purity", "final_dispatch_date", "final_customer",
         "final_dispatch_qty", "coa_issued", "status"],
        as_dict=True,
    )
    if eb:
        rows.append(_row(
            layer=f"         └─ EB → {eb.name}",
            batch_name=eb.name,
            batch_type="Extraction",
            event_date=eb.dispatch_date,
            volume=_vol(eb.dispatch_qty, "kg"),
            qc_status=f"{eb.incoming_qc_status or 'Pending'} / {eb.status}",
            remarks=(
                f"Purity: {eb.extract_purity or 'N/A'}% | "
                f"Customer: {eb.final_customer or 'N/A'} | "
                f"Final dispatch: {eb.final_dispatch_date or 'N/A'} | "
                f"COA issued: {'Yes' if eb.coa_issued else 'No'}"
            ),
        ))
