import frappe


def execute(filters=None):
    return get_columns(), get_data(filters)


def get_columns():
    return [
        {"label": "Strain", "fieldname": "strain", "fieldtype": "Link",
         "options": "Pluviago Strain", "width": 130},
        {"label": "Production Batch", "fieldname": "batch", "fieldtype": "Link",
         "options": "Production Batch", "width": 150},
        {"label": "Final Stage", "fieldname": "current_stage", "fieldtype": "Data", "width": 100},
        {"label": "Status", "fieldname": "status", "fieldtype": "Data", "width": 100},
        {"label": "Inoculation Date", "fieldname": "inoculation_date", "fieldtype": "Date", "width": 120},
        {"label": "Harvest Batch", "fieldname": "harvest_batch", "fieldtype": "Link",
         "options": "Harvest Batch", "width": 130},
        {"label": "Dry Biomass (kg)", "fieldname": "dry_biomass_weight", "fieldtype": "Float", "width": 120},
        {"label": "Astaxanthin Yield (g/kg)", "fieldname": "astaxanthin_yield", "fieldtype": "Float", "width": 150},
        {"label": "Generation No.", "fieldname": "generation_number", "fieldtype": "Int", "width": 100},
        {"label": "Lineage Status", "fieldname": "lineage_status", "fieldtype": "Data", "width": 110},
        {"label": "QC Readings", "fieldname": "qc_count", "fieldtype": "Int", "width": 90},
        {"label": "Contaminated", "fieldname": "contamination_status", "fieldtype": "Data", "width": 110},
    ]


def get_data(filters):
    filters = filters or {}
    conditions = ""
    vals = {}

    if filters.get("strain"):
        conditions += " AND pb.strain = %(strain)s"
        vals["strain"] = filters["strain"]
    if filters.get("status"):
        conditions += " AND pb.status = %(status)s"
        vals["status"] = filters["status"]
    if filters.get("from_date"):
        conditions += " AND pb.inoculation_date >= %(from_date)s"
        vals["from_date"] = filters["from_date"]
    if filters.get("to_date"):
        conditions += " AND pb.inoculation_date <= %(to_date)s"
        vals["to_date"] = filters["to_date"]

    rows = frappe.db.sql(f"""
        SELECT
            pb.strain,
            pb.name AS batch,
            pb.current_stage,
            pb.status,
            pb.inoculation_date,
            pb.harvest_batch,
            pb.generation_number,
            pb.lineage_status,
            pb.contamination_status,
            hb.dry_biomass_weight,
            hb.astaxanthin_yield,
            (SELECT COUNT(*) FROM `tabProduction Batch QC`
             WHERE parent = pb.name) AS qc_count
        FROM `tabProduction Batch` pb
        LEFT JOIN `tabHarvest Batch` hb ON hb.name = pb.harvest_batch
        WHERE 1=1 {conditions}
        ORDER BY pb.inoculation_date DESC
    """, vals, as_dict=True)

    return rows
