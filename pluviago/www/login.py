"""
Custom Login Page Handler for Pluviago
Serves the custom login.html page and handles authentication
"""

import frappe
from frappe import _
from frappe.utils import get_url


def get_context(context):
    """
    Context for the custom login page
    """
    context.no_cache = 1
    context.title = _("Pluviago — Sign In")
    context.brand_html = "Pluviago Biotech"
    
    # Get redirect URL if provided
    redirect_to = frappe.local.form_dict.get("redirect-to")
    if redirect_to:
        context.redirect_to = redirect_to
    
    return context
