import frappe


def after_install():
    create_module_def()


def create_module_def():
    if not frappe.db.exists("Module Def", "Pluviago Biotech"):
        doc = frappe.get_doc({
            "doctype": "Module Def",
            "module_name": "Pluviago Biotech",
            "app_name": "pluviago"
        })
        doc.insert(ignore_permissions=True)
        frappe.db.commit()
        print("Created Module Def: Pluviago Biotech")
    else:
        print("Module Def: Pluviago Biotech already exists")
