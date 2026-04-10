import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def execute():
    # 1. Create Child DocType 'Approved Vendor Item' if not exists
    if not frappe.db.exists("DocType", "Approved Vendor Item"):
        doc = frappe.get_doc({
            "doctype": "DocType",
            "module": "Pluviago Biotech",
            "custom": 1,
            "istable": 1,
            "name": "Approved Vendor Item",
            "editable_grid": 1,
            "fields": [
                {
                    "fieldname": "item_code",
                    "fieldtype": "Link",
                    "label": "Item Code",
                    "options": "Item",
                    "in_list_view": 1,
                    "reqd": 1
                },
                {
                    "fieldname": "material_name",
                    "fieldtype": "Data",
                    "label": "Material Name",
                    "in_list_view": 1,
                    "fetch_from": "item_code.item_name",
                    "read_only": 1
                }
            ]
        })
        doc.insert(ignore_permissions=True)
        print("Created DocType: Approved Vendor Item")

    # 2. Add Child Table field to 'Approved Vendor'
    create_custom_fields({
        "Approved Vendor": [
            {
                "fieldname": "approved_items",
                "fieldtype": "Table",
                "label": "Approved Items",
                "options": "Approved Vendor Item",
                "insert_after": "supplier"
            }
        ]
    }, update=True)
    print("Added child table to Approved Vendor")

    # 3. Migrate existing data (Optional step - script part 1)
    avls = frappe.get_all("Approved Vendor", fields=["name", "item_code", "material_name"])
    for avl in avls:
        if avl.item_code:
            existing_children = frappe.get_all("Approved Vendor Item", filters={"parent": avl.name, "item_code": avl.item_code})
            if not existing_children:
                child = frappe.get_doc({
                    "doctype": "Approved Vendor Item",
                    "parent": avl.name,
                    "parenttype": "Approved Vendor",
                    "parentfield": "approved_items",
                    "item_code": avl.item_code,
                    "material_name": avl.material_name
                })
                child.insert(ignore_permissions=True)
                print(f"Migrated item {avl.item_code} into AVL {avl.name}")
    
    frappe.db.commit()

    # 4. Hide old fields on Approved Vendor
    frappe.db.set_value("DocField", {"parent": "Approved Vendor", "fieldname": "item_code"}, "hidden", 1)
    frappe.db.set_value("DocField", {"parent": "Approved Vendor", "fieldname": "material_name"}, "hidden", 1)
    
    # Remove mandatory requirement
    frappe.db.set_value("DocField", {"parent": "Approved Vendor", "fieldname": "item_code"}, "reqd", 0)
    frappe.db.set_value("DocField", {"parent": "Approved Vendor", "fieldname": "material_name"}, "reqd", 0)

    # Also ignore them in list view
    frappe.db.set_value("DocField", {"parent": "Approved Vendor", "fieldname": "item_code"}, "in_list_view", 0)
    frappe.db.set_value("DocField", {"parent": "Approved Vendor", "fieldname": "material_name"}, "in_list_view", 0)
    frappe.db.commit()

    print("Success: Approved Vendor updated with child table logic.")
