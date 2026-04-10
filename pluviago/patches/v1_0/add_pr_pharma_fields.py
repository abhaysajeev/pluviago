"""
Patch: Add custom pharma fields to Purchase Receipt Item
for Pluviago's RMB workflow.
"""
import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields


def execute():
    custom_fields = {
        "Purchase Receipt Item": [
            {
                "fieldname": "custom_pharma_section",
                "fieldtype": "Section Break",
                "label": "Pharma Batch Details",
                "insert_after": "schedule_date",
                "collapsible": 0,
            },
            {
                "fieldname": "custom_supplier_batch_no",
                "fieldtype": "Data",
                "label": "Supplier Batch No",
                "insert_after": "custom_pharma_section",
                "in_list_view": 1,
                "description": "Batch number printed on vendor label / COA",
            },
            {
                "fieldname": "custom_mfg_date",
                "fieldtype": "Date",
                "label": "Mfg Date",
                "insert_after": "custom_supplier_batch_no",
            },
            {
                "fieldname": "custom_pharma_col_break",
                "fieldtype": "Column Break",
                "insert_after": "custom_mfg_date",
            },
            {
                "fieldname": "custom_expiry_date",
                "fieldtype": "Date",
                "label": "Expiry Date",
                "insert_after": "custom_pharma_col_break",
            },
            {
                "fieldname": "custom_storage_condition",
                "fieldtype": "Select",
                "label": "Storage Condition",
                "insert_after": "custom_expiry_date",
                "options": "\nRoom Temperature\n2-8C\n-20C\n4C",
            },
        ]
    }

    create_custom_fields(custom_fields, update=True)
    frappe.db.commit()
    print("✓ Pharma batch fields added to Purchase Receipt Item")
