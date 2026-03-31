import frappe


def execute(filters=None):
    return get_columns(), get_data(filters)


def get_columns():
    return [
        {"label": "Raw Material Batch", "fieldname": "rm_batch", "fieldtype": "Link", "options": "Raw Material Batch", "width": 170},
        {"label": "Material", "fieldname": "material_name", "fieldtype": "Data", "width": 150},
        {"label": "Supplier", "fieldname": "supplier", "fieldtype": "Link", "options": "Supplier", "width": 130},
        {"label": "COA Number", "fieldname": "coa_number", "fieldtype": "Data", "width": 130},
        {"label": "Vendor Batch No", "fieldname": "supplier_batch_no", "fieldtype": "Data", "width": 130},
        {"label": "Received Date", "fieldname": "received_date", "fieldtype": "Date", "width": 120},
        {"label": "Expiry Date", "fieldname": "expiry_date", "fieldtype": "Date", "width": 110},
        {"label": "COA Verified", "fieldname": "coa_verified", "fieldtype": "Check", "width": 100},
        {"label": "Verified By", "fieldname": "coa_verified_by", "fieldtype": "Link", "options": "User", "width": 130},
        {"label": "QC Status", "fieldname": "qc_status", "fieldtype": "Data", "width": 100},
        {"label": "QC Date", "fieldname": "qc_date", "fieldtype": "Date", "width": 100},
        {"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 100},
    ]


def get_data(filters):
    conditions = "1=1"
    vals = {}
    if filters:
        if filters.get("supplier"):
            conditions += " AND supplier = %(supplier)s"
            vals["supplier"] = filters["supplier"]
        if filters.get("from_date"):
            conditions += " AND received_date >= %(from_date)s"
            vals["from_date"] = filters["from_date"]
        if filters.get("to_date"):
            conditions += " AND received_date <= %(to_date)s"
            vals["to_date"] = filters["to_date"]
        if filters.get("qc_status"):
            conditions += " AND qc_status = %(qc_status)s"
            vals["qc_status"] = filters["qc_status"]

    return frappe.db.sql(f"""
        SELECT name as rm_batch, material_name, supplier, coa_number,
               supplier_batch_no, received_date, expiry_date,
               coa_verified, coa_verified_by, qc_status, qc_date, status
        FROM `tabRaw Material Batch`
        WHERE {conditions}
        ORDER BY received_date DESC
    """, vals, as_dict=True)
