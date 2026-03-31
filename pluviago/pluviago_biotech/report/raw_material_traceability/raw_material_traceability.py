import frappe


def execute(filters=None):
    return get_columns(), get_data(filters)


def get_columns():
    return [
        {"label": "Raw Material Batch", "fieldname": "rm_batch", "fieldtype": "Link", "options": "Raw Material Batch", "width": 170},
        {"label": "Material Name", "fieldname": "material_name", "fieldtype": "Data", "width": 150},
        {"label": "Supplier", "fieldname": "supplier", "fieldtype": "Link", "options": "Supplier", "width": 130},
        {"label": "Vendor Batch No", "fieldname": "supplier_batch_no", "fieldtype": "Data", "width": 130},
        {"label": "COA Number", "fieldname": "coa_number", "fieldtype": "Data", "width": 120},
        {"label": "Expiry Date", "fieldname": "expiry_date", "fieldtype": "Date", "width": 110},
        {"label": "QC Status", "fieldname": "qc_status", "fieldtype": "Data", "width": 100},
        {"label": "Stock Solution Batch", "fieldname": "stock_solution_batch", "fieldtype": "Data", "width": 160},
        {"label": "Medium Batch", "fieldname": "medium_batch", "fieldtype": "Data", "width": 140},
        {"label": "Production Batch", "fieldname": "production_batch", "fieldtype": "Data", "width": 140},
        {"label": "Harvest Batch", "fieldname": "harvest_batch", "fieldtype": "Data", "width": 130},
    ]


def get_data(filters):
    conditions = "1=1"
    vals = {}
    if filters:
        if filters.get("supplier"):
            conditions += " AND rmb.supplier = %(supplier)s"
            vals["supplier"] = filters["supplier"]
        if filters.get("from_date"):
            conditions += " AND rmb.received_date >= %(from_date)s"
            vals["from_date"] = filters["from_date"]
        if filters.get("to_date"):
            conditions += " AND rmb.received_date <= %(to_date)s"
            vals["to_date"] = filters["to_date"]

    # Get raw material batches and trace forward through the chain
    rm_batches = frappe.db.sql(f"""
        SELECT rmb.name as rm_batch, rmb.material_name, rmb.supplier,
               rmb.supplier_batch_no, rmb.coa_number, rmb.expiry_date, rmb.qc_status
        FROM `tabRaw Material Batch` rmb
        WHERE {conditions}
        ORDER BY rmb.received_date DESC
    """, vals, as_dict=True)

    result = []
    for rm in rm_batches:
        # Find stock solution batches that used this raw material
        ssb_rows = frappe.db.sql("""
            SELECT DISTINCT ssb.name
            FROM `tabStock Solution Batch` ssb
            INNER JOIN `tabStock Solution Ingredient` ssi ON ssi.parent = ssb.name
            WHERE ssi.raw_material_batch = %(rm)s
        """, {"rm": rm.rm_batch}, as_dict=True)

        if not ssb_rows:
            rm["stock_solution_batch"] = ""
            rm["medium_batch"] = ""
            rm["production_batch"] = ""
            rm["harvest_batch"] = ""
            result.append(rm)
        else:
            for ssb in ssb_rows:
                row = rm.copy()
                row["stock_solution_batch"] = ssb.name
                # Medium batches that used this stock solution
                medium_batches = frappe.db.sql("""
                    SELECT name FROM `tabGreen Medium Batch`
                    WHERE stock_solution_a1=%(s)s OR stock_solution_a2=%(s)s OR stock_solution_a3=%(s)s
                    UNION
                    SELECT name FROM `tabRed Medium Batch`
                    WHERE stock_solution_a4=%(s)s OR stock_solution_a5=%(s)s OR stock_solution_a6=%(s)s OR stock_solution_a7=%(s)s
                """, {"s": ssb.name}, as_dict=True)
                if medium_batches:
                    for mb in medium_batches:
                        row2 = row.copy()
                        row2["medium_batch"] = mb.name
                        # Final medium that used this medium
                        fmb = frappe.db.get_value("Final Medium Batch",
                            {"green_medium_batch": mb.name}, "name") or \
                              frappe.db.get_value("Final Medium Batch",
                            {"red_medium_batch": mb.name}, "name")
                        row2["production_batch"] = ""
                        row2["harvest_batch"] = ""
                        if fmb:
                            pb = frappe.db.get_value("Production Batch", {"final_medium_batch": fmb}, "name")
                            if pb:
                                row2["production_batch"] = pb
                                hb = frappe.db.get_value("Harvest Batch", {"production_batch": pb}, "name")
                                row2["harvest_batch"] = hb or ""
                        result.append(row2)
                else:
                    row["medium_batch"] = ""
                    row["production_batch"] = ""
                    row["harvest_batch"] = ""
                    result.append(row)
    return result
