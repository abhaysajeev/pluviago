app_name = "pluviago"
app_title = "Pluviago"
app_publisher = "Sil"
app_description = "Pluviago Biotech Algae Production ERP"
app_email = "sil@gmail.com"
app_license = "mit"

required_apps = ["frappe", "erpnext"]

# Include workspace CSS/JS on all authenticated Desk pages
app_include_css = [
    "/assets/pluviago/css/pluviago_workspace.css",
]
app_include_js = [
    "/assets/pluviago/js/pluviago_workspace.js",
    "/assets/pluviago/js/load_formula.js",
    "/assets/pluviago/js/load_medium_formula.js",
]

after_install = "pluviago.install.after_install"

# Module inclusion
fixtures = [
    {"dt": "Role", "filters": [["name", "in", [
        "QA Head", "QC Manager", "Production Manager",
        "Production Supervisor", "Production Operator",
        "Store Keeper", "Pluviago Admin"
    ]]]},
    {"dt": "Workflow", "filters": [["name", "in", [
        "Pluviago PO Approval",
        "Pluviago PR COA Approval",
    ]]]},
]

# Override standard ERPNext doctype classes
override_doctype_class = {
    "Purchase Receipt": "pluviago.pluviago_biotech.overrides.purchase_receipt.CustomPurchaseReceipt",
}

# DocType JS — inject custom client scripts into standard ERPNext forms
doctype_js = {
    "Purchase Receipt": "pluviago_biotech/overrides/purchase_receipt.js",
    "Purchase Order": "pluviago_biotech/overrides/purchase_order.js",
    "Raw Material Batch": "pluviago_biotech/doctype/raw_material_batch/raw_material_batch.js",
}

# Document Events
doc_events = {
    "Purchase Order": {
        "validate": "pluviago.pluviago_biotech.overrides.purchase_order.validate",
        "before_submit": "pluviago.pluviago_biotech.overrides.purchase_order.before_submit",
    },
    "Purchase Receipt": {
        "on_workflow_action": "pluviago.pluviago_biotech.overrides.purchase_receipt.on_workflow_action",
    },
}

# Scheduled Tasks
scheduler_events = {
    "daily": [
        "pluviago.pluviago_biotech.tasks.daily",
    ],
}

# Home page
# home_page = "login"
