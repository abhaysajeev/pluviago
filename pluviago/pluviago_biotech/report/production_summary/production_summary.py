import frappe


def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    return [
        {
            "label": "Harvest Batch",
            "fieldname": "batch_number",
            "fieldtype": "Link",
            "options": "Harvest Batch",
            "width": 150
        },
        {
            "label": "Harvest Date",
            "fieldname": "harvest_date",
            "fieldtype": "Date",
            "width": 120
        },
        {
            "label": "Production Batch",
            "fieldname": "production_batch",
            "fieldtype": "Link",
            "options": "Production Batch",
            "width": 150
        },
        {
            "label": "Strain",
            "fieldname": "strain",
            "fieldtype": "Data",
            "width": 130
        },
        {
            "label": "Target Dry Weight (kg)",
            "fieldname": "target_dry_weight",
            "fieldtype": "Float",
            "width": 150
        },
        {
            "label": "Actual Dry Weight (kg)",
            "fieldname": "actual_dry_weight",
            "fieldtype": "Float",
            "width": 150
        },
        {
            "label": "Yield %",
            "fieldname": "yield_percentage",
            "fieldtype": "Float",
            "width": 100
        },
        {
            "label": "QC Status",
            "fieldname": "qc_status",
            "fieldtype": "Data",
            "width": 100
        },
        {
            "label": "Status",
            "fieldname": "status",
            "fieldtype": "Data",
            "width": 100
        },
    ]


def get_data(filters):
    conditions = "1=1"
    filter_values = {}

    if filters:
        if filters.get("from_date"):
            conditions += " AND harvest_date >= %(from_date)s"
            filter_values["from_date"] = filters["from_date"]
        if filters.get("to_date"):
            conditions += " AND harvest_date <= %(to_date)s"
            filter_values["to_date"] = filters["to_date"]

    return frappe.db.sql(
        f"""
        SELECT
            hb.name as batch_number,
            hb.harvest_date,
            hb.production_batch,
            pb.strain,
            hb.target_dry_weight,
            hb.actual_dry_weight,
            hb.yield_percentage,
            hb.qc_status,
            hb.status
        FROM `tabHarvest Batch` hb
        LEFT JOIN `tabProduction Batch` pb ON pb.name = hb.production_batch
        WHERE {conditions}
        ORDER BY hb.harvest_date DESC
        """,
        filter_values,
        as_dict=True
    )
