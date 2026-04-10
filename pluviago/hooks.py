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
]

after_install = "pluviago.install.after_install"

# Module inclusion
fixtures = [
    {"dt": "Role", "filters": [["name", "in", [
        "QA Head", "QC Manager", "Production Manager",
        "Production Supervisor", "Production Operator",
        "Store Keeper", "Pluviago Admin"
    ]]]},
]

# DocType JS — inject custom client scripts into standard ERPNext forms
doctype_js = {
    "Purchase Receipt": "pluviago_biotech/overrides/purchase_receipt.js",
}

# Document Events
doc_events = {
    "Purchase Order": {
        "validate": "pluviago.pluviago_biotech.overrides.purchase_order.validate",
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
