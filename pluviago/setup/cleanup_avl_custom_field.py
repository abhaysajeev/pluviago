import frappe

def execute():
    result = frappe.db.get_all(
        'Custom Field',
        filters={'dt': 'Approved Vendor', 'fieldname': 'approved_items'},
        fields=['name']
    )
    for r in result:
        frappe.db.delete('Custom Field', {'name': r['name']})
        frappe.db.commit()
        print(f"Deleted stale custom field: {r['name']}")
    if not result:
        print("No stale custom fields found — already clean")
