import frappe


def execute(filters=None):
    return get_columns(), get_data(filters)


def get_columns():
    return [
        {"label": "OOS ID", "fieldname": "name", "fieldtype": "Link",
         "options": "OOS Investigation", "width": 140},
        {"label": "Date", "fieldname": "investigation_date", "fieldtype": "Date", "width": 110},
        {"label": "Batch Type", "fieldname": "linked_doctype", "fieldtype": "Data", "width": 150},
        {"label": "Batch", "fieldname": "linked_batch", "fieldtype": "Data", "width": 150},
        {"label": "Parameter Failed", "fieldname": "parameter_failed", "fieldtype": "Data", "width": 120},
        {"label": "Failed Value", "fieldname": "failed_value", "fieldtype": "Data", "width": 100},
        {"label": "Expected Range", "fieldname": "expected_range", "fieldtype": "Data", "width": 120},
        {"label": "Conclusion", "fieldname": "conclusion", "fieldtype": "Data", "width": 140},
        {"label": "Disposition", "fieldname": "disposition", "fieldtype": "Data", "width": 150},
        {"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 120},
        {"label": "Reported By", "fieldname": "reported_by", "fieldtype": "Data", "width": 120},
    ]


def get_data(filters):
    filters = filters or {}
    conditions = ""
    vals = {}

    if filters.get("from_date"):
        conditions += " AND investigation_date >= %(from_date)s"
        vals["from_date"] = filters["from_date"]
    if filters.get("to_date"):
        conditions += " AND investigation_date <= %(to_date)s"
        vals["to_date"] = filters["to_date"]
    if filters.get("linked_doctype"):
        conditions += " AND linked_doctype = %(linked_doctype)s"
        vals["linked_doctype"] = filters["linked_doctype"]
    if filters.get("conclusion"):
        conditions += " AND conclusion = %(conclusion)s"
        vals["conclusion"] = filters["conclusion"]
    if filters.get("status"):
        conditions += " AND status = %(status)s"
        vals["status"] = filters["status"]

    rows = frappe.db.sql(f"""
        SELECT name, investigation_date, linked_doctype, linked_batch,
               parameter_failed, failed_value, expected_range,
               conclusion, disposition, status, reported_by
        FROM `tabOOS Investigation`
        WHERE 1=1 {conditions}
        ORDER BY investigation_date DESC
    """, vals, as_dict=True)

    return rows
