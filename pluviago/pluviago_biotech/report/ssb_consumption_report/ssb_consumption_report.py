import frappe


def execute(filters=None):
    return get_columns(), get_data(filters)


def get_columns():
    return [
        {"label": "SSB Name", "fieldname": "ssb", "fieldtype": "Link",
         "options": "Stock Solution Batch", "width": 160},
        {"label": "Solution Type", "fieldname": "solution_type", "fieldtype": "Data", "width": 120},
        {"label": "Prepared On", "fieldname": "preparation_date", "fieldtype": "Date", "width": 110},
        {"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 100},
        {"label": "Available Vol. (mL)", "fieldname": "available_volume_ml",
         "fieldtype": "Float", "width": 130},
        {"label": "Volume Used (mL)", "fieldname": "volume_used", "fieldtype": "Float", "width": 120},
        {"label": "Remaining (mL)", "fieldname": "remaining_ml", "fieldtype": "Float", "width": 120},
        {"label": "% Consumed", "fieldname": "pct_consumed", "fieldtype": "Percent", "width": 100},
        {"label": "Expiry Date", "fieldname": "expiry_date", "fieldtype": "Date", "width": 110},
    ]


def get_data(filters):
    filters = filters or {}
    conditions = ""
    vals = {}

    if filters.get("solution_type"):
        conditions += " AND solution_type = %(solution_type)s"
        vals["solution_type"] = filters["solution_type"]
    if filters.get("status"):
        conditions += " AND status = %(status)s"
        vals["status"] = filters["status"]

    rows = frappe.db.sql(f"""
        SELECT
            name AS ssb,
            solution_type,
            preparation_date,
            status,
            (available_volume * 1000) AS available_volume_ml,
            COALESCE(volume_used, 0) AS volume_used,
            GREATEST((available_volume * 1000) - COALESCE(volume_used, 0), 0) AS remaining_ml,
            CASE WHEN (available_volume * 1000) > 0
                 THEN ROUND((COALESCE(volume_used, 0) / (available_volume * 1000)) * 100, 1)
                 ELSE 0
            END AS pct_consumed,
            expiry_date
        FROM `tabStock Solution Batch`
        WHERE 1=1 {conditions}
        ORDER BY preparation_date DESC
    """, vals, as_dict=True)

    return rows
