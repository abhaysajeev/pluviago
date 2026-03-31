import frappe


def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data


def get_columns():
    return [
        {
            "label": "Batch",
            "fieldname": "batch_number",
            "fieldtype": "Link",
            "options": "Production Batch",
            "width": 150
        },
        {
            "label": "Stage",
            "fieldname": "current_stage",
            "fieldtype": "Data",
            "width": 120
        },
        {
            "label": "Strain",
            "fieldname": "strain",
            "fieldtype": "Link",
            "options": "Pluviago Strain",
            "width": 130
        },
        {
            "label": "Generation",
            "fieldname": "generation_number",
            "fieldtype": "Int",
            "width": 100
        },
        {
            "label": "Parent Batch",
            "fieldname": "parent_batch",
            "fieldtype": "Link",
            "options": "Production Batch",
            "width": 150
        },
        {
            "label": "Inoculation Date",
            "fieldname": "inoculation_date",
            "fieldtype": "Date",
            "width": 120
        },
        {
            "label": "Decision",
            "fieldname": "stage_decision",
            "fieldtype": "Data",
            "width": 100
        },
        {
            "label": "Status",
            "fieldname": "status",
            "fieldtype": "Data",
            "width": 100
        },
        {
            "label": "Final Medium",
            "fieldname": "final_medium_batch",
            "fieldtype": "Link",
            "options": "Final Medium Batch",
            "width": 130
        },
        {
            "label": "Harvest Batch",
            "fieldname": "harvest_batch",
            "fieldtype": "Link",
            "options": "Harvest Batch",
            "width": 130
        },
    ]


def get_data(filters):
    conditions = "1=1"
    filter_values = {}

    if filters:
        if filters.get("strain"):
            conditions += " AND strain = %(strain)s"
            filter_values["strain"] = filters["strain"]
        if filters.get("status"):
            conditions += " AND status = %(status)s"
            filter_values["status"] = filters["status"]
        if filters.get("from_date"):
            conditions += " AND inoculation_date >= %(from_date)s"
            filter_values["from_date"] = filters["from_date"]
        if filters.get("to_date"):
            conditions += " AND inoculation_date <= %(to_date)s"
            filter_values["to_date"] = filters["to_date"]

    return frappe.db.sql(
        f"""
        SELECT
            name as batch_number,
            current_stage,
            strain,
            generation_number,
            parent_batch,
            inoculation_date,
            stage_decision,
            status,
            final_medium_batch,
            harvest_batch
        FROM `tabProduction Batch`
        WHERE {conditions}
        ORDER BY inoculation_date DESC, generation_number ASC
        """,
        filter_values,
        as_dict=True
    )
