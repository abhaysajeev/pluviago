"""Controller for /stock-lineage page.

Login-required. Fetches the initial KPI snapshot server-side so the page
has data on first paint; everything else is xcalled from the browser.
"""
import frappe
from frappe import _
from pluviago.pluviago_biotech.api import stock_lineage as api


def get_context(context):
    if frappe.session.user == "Guest":
        frappe.local.flags.redirect_location = "/login?redirect-to=/stock-lineage"
        raise frappe.Redirect

    context.no_cache = 1
    context.title = _("Stock Lineage")
    context.kpi = api.get_kpi_snapshot()

    initial_focus = frappe.local.form_dict.get("focus") or ""
    context.initial_focus = initial_focus
    return context
