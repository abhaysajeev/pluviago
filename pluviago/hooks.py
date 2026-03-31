app_name = "pluviago"
app_title = "Pluviago"
app_publisher = "Sil"
app_description = "Pluviago Biotech Algae Production ERP"
app_email = "sil@gmail.com"
app_license = "mit"

required_apps = ["frappe", "erpnext"]

after_install = "pluviago.install.after_install"

# Module inclusion
fixtures = [
    {"dt": "Role", "filters": [["name", "in", [
        "QA Head", "QC Manager", "Production Manager",
        "Production Supervisor", "Production Operator",
        "Store Keeper", "Pluviago Admin"
    ]]]},
]

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
