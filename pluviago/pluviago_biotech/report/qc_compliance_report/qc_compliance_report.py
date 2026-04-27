import frappe


def execute(filters=None):
    return get_columns(), get_data(filters)


def get_columns():
    return [
        {"label": "Batch", "fieldname": "batch", "fieldtype": "Data", "width": 140},
        {"label": "DocType", "fieldname": "doctype_name", "fieldtype": "Data", "width": 160},
        {"label": "Stage / Checkpoint", "fieldname": "stage", "fieldtype": "Data", "width": 140},
        {"label": "QC Type", "fieldname": "qc_type", "fieldtype": "Data", "width": 120},
        {"label": "Phase", "fieldname": "phase", "fieldtype": "Data", "width": 100},
        {"label": "QC Status", "fieldname": "qc_status", "fieldtype": "Data", "width": 110},
        {"label": "QC Date", "fieldname": "qc_date", "fieldtype": "Date", "width": 110},
        {"label": "Checked By", "fieldname": "checked_by", "fieldtype": "Data", "width": 130},
        {"label": "pH", "fieldname": "ph_value", "fieldtype": "Float", "width": 70},
        {"label": "PAR", "fieldname": "par_value", "fieldtype": "Float", "width": 70},
        {"label": "Dry Weight (g/L)", "fieldname": "dry_weight", "fieldtype": "Float", "width": 110},
        {"label": "Assay (%)", "fieldname": "assay_value", "fieldtype": "Float", "width": 90},
        {"label": "Contamination", "fieldname": "contamination_detected", "fieldtype": "Check", "width": 100},
        {"label": "Remarks", "fieldname": "remarks", "fieldtype": "Data", "width": 200},
    ]


def get_data(filters):
    filters = filters or {}
    from_date = filters.get("from_date")
    to_date = filters.get("to_date")
    qc_type_filter = filters.get("qc_type")  # "Process QC" / "Biological QC" / None
    phase_filter = filters.get("phase")       # "Green Phase" / "Red Phase" / None

    data = []

    # ── Build shared date conditions ─────────────────────────────────────
    date_cond = ""
    vals = {}
    if from_date:
        date_cond += " AND qc_date >= %(from_date)s"
        vals["from_date"] = from_date
    if to_date:
        date_cond += " AND qc_date <= %(to_date)s"
        vals["to_date"] = to_date

    green_date_cond, green_vals = "", {}
    red_date_cond, red_vals = "", {}
    if from_date:
        green_date_cond += " AND preparation_date >= %(from_date)s"
        green_vals["from_date"] = from_date
        red_date_cond += " AND preparation_date >= %(from_date)s"
        red_vals["from_date"] = from_date
    if to_date:
        green_date_cond += " AND preparation_date <= %(to_date)s"
        green_vals["to_date"] = to_date
        red_date_cond += " AND preparation_date <= %(to_date)s"
        red_vals["to_date"] = to_date

    # ── Production Batch QC readings (new — respects qc_type + phase) ────
    pb_qc_cond = ""
    pb_qc_vals = dict(vals)
    if qc_type_filter:
        pb_qc_cond += " AND pbq.qc_type = %(qc_type)s"
        pb_qc_vals["qc_type"] = qc_type_filter
    if phase_filter:
        pb_qc_cond += " AND pbq.phase = %(phase)s"
        pb_qc_vals["phase"] = phase_filter

    rows = frappe.db.sql(f"""
        SELECT
            pb.name AS batch,
            'Production Batch' AS doctype_name,
            CONCAT(pb.current_stage, ' — ', pb.strain) AS stage,
            pbq.qc_type AS qc_type,
            pbq.phase AS phase,
            pbq.overall_result AS qc_status,
            pbq.qc_date AS qc_date,
            pbq.qc_by AS checked_by,
            pbq.ph_value,
            pbq.par_value,
            pbq.dry_weight,
            pbq.assay_value,
            pbq.contamination_detected,
            pbq.remarks
        FROM `tabProduction Batch QC` pbq
        JOIN `tabProduction Batch` pb ON pb.name = pbq.parent
        WHERE 1=1 {date_cond.replace('qc_date', 'pbq.qc_date')} {pb_qc_cond}
        ORDER BY pb.name, pbq.qc_date
    """, pb_qc_vals, as_dict=True)
    data.extend(rows)

    # ── Media / Stock / Harvest QC (not filtered by qc_type — they are always Process) ──
    # Skip if user explicitly filters for Biological QC only
    if not qc_type_filter or qc_type_filter == "Process QC":
        rows = frappe.db.sql(f"""
            SELECT name AS batch, 'Stock Solution Batch' AS doctype_name, solution_type AS stage,
                   'Process QC' AS qc_type, NULL AS phase,
                   qc_status, qc_date, qc_checked_by AS checked_by,
                   NULL AS ph_value, NULL AS par_value, NULL AS dry_weight,
                   NULL AS assay_value, 0 AS contamination_detected, qc_remarks AS remarks
            FROM `tabStock Solution Batch` WHERE 1=1 {date_cond}
        """, vals, as_dict=True)
        data.extend(rows)

        rows = frappe.db.sql(f"""
            SELECT name AS batch,
                   CONCAT(medium_type, ' Medium Batch') AS doctype_name,
                   CONCAT(medium_type, ' Medium') AS stage,
                   'Process QC' AS qc_type, NULL AS phase,
                   overall_qc_status AS qc_status, preparation_date AS qc_date,
                   prepared_by AS checked_by,
                   CASE WHEN medium_type = 'Green' THEN qc_checkpoint_2_ph
                        ELSE qc_checkpoint_4_ph END AS ph_value,
                   NULL AS par_value, NULL AS dry_weight,
                   NULL AS assay_value, 0 AS contamination_detected, NULL AS remarks
            FROM `tabMedium Batch` WHERE 1=1 {green_date_cond}
        """, green_vals, as_dict=True)
        data.extend(rows)

        rows = frappe.db.sql(f"""
            SELECT name AS batch, 'Final Medium Batch' AS doctype_name, 'Final Medium' AS stage,
                   'Process QC' AS qc_type, NULL AS phase,
                   qc_status, qc_date, qc_checked_by AS checked_by,
                   NULL AS ph_value, NULL AS par_value, NULL AS dry_weight,
                   NULL AS assay_value, 0 AS contamination_detected, qc_remarks AS remarks
            FROM `tabFinal Medium Batch` WHERE 1=1 {date_cond}
        """, vals, as_dict=True)
        data.extend(rows)

        rows = frappe.db.sql(f"""
            SELECT name AS batch, 'Harvest Batch' AS doctype_name, 'Harvest / Dry Biomass' AS stage,
                   'Biological QC' AS qc_type, NULL AS phase,
                   qc_status, qc_date, qc_checked_by AS checked_by,
                   NULL AS ph_value, NULL AS par_value, NULL AS dry_weight,
                   NULL AS assay_value, 0 AS contamination_detected, NULL AS remarks
            FROM `tabHarvest Batch` WHERE 1=1 {date_cond}
        """, vals, as_dict=True)
        data.extend(rows)

    return data
