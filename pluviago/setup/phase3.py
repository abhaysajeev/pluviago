"""
Phase 3: Automation Flow — Pluviago Biotech
=============================================
Creates:
  3.1  ERP Settings (Manufacturing, Stock, Buying, Selling)
  3.2  Workflows (3 — Purchase Order, Purchase Invoice, Quality Inspection)
  3.3  Server Scripts (5 document-event automations)
  3.4  Client Scripts (3 UI helpers)

Run via:
    bench --site replica1.local execute pluviago.setup.phase3.execute

Idempotent — safe to run multiple times.
"""

import frappe

# ──────────────────────────────────────────────
COMPANY_NAME = "Pluviago Biotech Pvt. Ltd."
COMPANY_ABBR = "PB"

_abbr = None


def get_abbr():
    global _abbr
    if _abbr is None:
        _abbr = frappe.db.get_value("Company", COMPANY_NAME, "abbr") or COMPANY_ABBR
    return _abbr


def wh(name):
    return f"{name} - {get_abbr()}"


# ══════════════════════════════════════════════
# MAIN ENTRY POINT
# ══════════════════════════════════════════════
def execute():
    print("\n" + "=" * 70)
    print("  PHASE 3: Automation Flow — Pluviago Biotech Pvt. Ltd.")
    print("=" * 70)

    configure_erp_settings()
    frappe.db.commit()

    setup_workflows()
    frappe.db.commit()

    setup_server_scripts()
    frappe.db.commit()

    setup_client_scripts()
    frappe.db.commit()

    print("\n" + "=" * 70)
    print("  ✅ PHASE 3 COMPLETE — All automation flows configured!")
    print("=" * 70 + "\n")


# ══════════════════════════════════════════════
# 3.1  ERP SETTINGS
# ══════════════════════════════════════════════
def _safe_set(doctype, field, value):
    """Set a single value on a Singles doctype, catching errors."""
    try:
        frappe.db.set_single_value(doctype, field, value)
        print(f"     ✅ {doctype}.{field} = {value}")
    except Exception as e:
        print(f"     ⚠️  {doctype}.{field} — {str(e)[:80]}")


def configure_erp_settings():
    print("\n── 3.1 ERP Settings ──")

    # ── Manufacturing Settings ──
    print("\n  ⚙️  Manufacturing Settings")
    _safe_set("Manufacturing Settings", "material_consumption", 1)
    _safe_set("Manufacturing Settings", "backflush_raw_materials_based_on", "BOM")
    _safe_set("Manufacturing Settings", "default_wip_warehouse", wh("Production Floor"))
    _safe_set("Manufacturing Settings", "overproduction_percentage_for_work_order", 10)
    _safe_set("Manufacturing Settings", "capacity_planning_for_workstation", 1)

    # ── Stock Settings ──
    print("\n  ⚙️  Stock Settings")
    _safe_set("Stock Settings", "show_barcode_field", 1)
    _safe_set("Stock Settings", "allow_negative_stock", 0)
    _safe_set("Stock Settings", "auto_insert_price_list_rate_if_missing", 1)

    # ── Buying Settings ──
    print("\n  ⚙️  Buying Settings")
    _safe_set("Buying Settings", "po_required", "Yes")
    _safe_set("Buying Settings", "pr_required", "Yes")
    _safe_set("Buying Settings", "maintain_same_rate", 1)

    # ── Selling Settings ──
    print("\n  ⚙️  Selling Settings")
    _safe_set("Selling Settings", "dn_required", "Yes")


# ══════════════════════════════════════════════
# 3.2  WORKFLOWS (3 workflows)
# ══════════════════════════════════════════════
def setup_workflows():
    print("\n── 3.2 Workflows ──")

    # First, create all required Workflow State records
    _create_workflow_states()

    _create_po_workflow()
    _create_pi_workflow()
    _create_qi_workflow()


def _create_workflow_states():
    """Create Workflow State records required by our workflows."""
    states_needed = [
        # (name, style)
        ("Draft",            ""),
        ("Pending Approval", "Primary"),
        ("Approved",         "Success"),
        ("Rejected",         "Danger"),
        ("COA Pending",      "Warning"),
        ("COA Approved",     "Success"),
        ("COA Rejected",     "Danger"),
        ("Ordered",          "Success"),
        ("COA Under Review", "Warning"),
        ("Submitted",        "Success"),
        ("Pending Review",   "Primary"),
        ("Accepted",         "Success"),
        ("On Hold",          "Warning"),
        ("Harvest Decision", "Info"),
    ]

    created = 0
    for state_name, style in states_needed:
        if not frappe.db.exists("Workflow State", state_name):
            try:
                frappe.get_doc({
                    "doctype": "Workflow State",
                    "workflow_state_name": state_name,
                    "style": style,
                }).insert(ignore_permissions=True)
                created += 1
            except Exception as e:
                print(f"  ⚠️  Workflow State '{state_name}' — {str(e)[:80]}")

    if created:
        print(f"  ✅ Created {created} Workflow States")
    else:
        print(f"  ⏭  All Workflow States already exist")

    # Create Workflow Action Master records
    actions_needed = [
        "Submit for Approval", "Approve", "Reject", "Revise",
        "Send for COA Review", "Approve COA", "Reject COA", "Re-submit COA",
        "Confirm Order", "Submit for COA Review", "Submit Invoice",
        "Submit for Review", "Accept", "Put on Hold", "Resume Review",
        "Harvest Early",
    ]
    action_created = 0
    for action_name in actions_needed:
        if not frappe.db.exists("Workflow Action Master", action_name):
            try:
                frappe.get_doc({
                    "doctype": "Workflow Action Master",
                    "workflow_action_name": action_name,
                }).insert(ignore_permissions=True)
                action_created += 1
            except Exception:
                pass  # duplicate or already exists

    if action_created:
        print(f"  ✅ Created {action_created} Workflow Actions")
    else:
        print(f"  ⏭  All Workflow Actions already exist")


def _create_workflow(name, doc_type, states, transitions, override_status=0):
    """Create a workflow if it doesn't already exist."""
    # Check if any active workflow already exists for this DocType
    existing = frappe.db.get_value(
        "Workflow",
        {"document_type": doc_type, "is_active": 1},
        "name"
    )
    if existing:
        print(f"  ⏭  Workflow for {doc_type}: '{existing}' already active")
        return False

    if frappe.db.exists("Workflow", name):
        print(f"  ⏭  Workflow: '{name}' already exists")
        return False

    try:
        wf = frappe.get_doc({
            "doctype": "Workflow",
            "workflow_name": name,
            "document_type": doc_type,
            "is_active": 1,
            "override_status": override_status,
            "send_email_alert": 0,
            "states": states,
            "transitions": transitions,
        })
        wf.insert(ignore_permissions=True)
        print(f"  ✅ Workflow: '{name}' ({len(states)} states, {len(transitions)} transitions)")
        return True
    except Exception as e:
        print(f"  ❌ Workflow: '{name}' — {str(e)[:120]}")
        return False


# ── 3.2.1 Purchase Order Workflow ──
def _create_po_workflow():
    """
    Flow: Draft → Pending Approval → Approved → COA Pending → COA Approved → Ordered
                                  ↘ Rejected → Draft (revise)
                                              COA Rejected → COA Pending (re-review)
    """
    states = [
        {"state": "Draft",             "doc_status": "0", "allow_edit": "Purchase User",     "style": ""},
        {"state": "Pending Approval",  "doc_status": "0", "allow_edit": "Purchase Manager",  "style": "Primary"},
        {"state": "Approved",          "doc_status": "0", "allow_edit": "Purchase Manager",  "style": "Success"},
        {"state": "Rejected",          "doc_status": "0", "allow_edit": "Purchase User",     "style": "Danger"},
        {"state": "COA Pending",       "doc_status": "0", "allow_edit": "QA Head",           "style": "Warning"},
        {"state": "COA Approved",      "doc_status": "0", "allow_edit": "Purchase Manager",  "style": "Success"},
        {"state": "COA Rejected",      "doc_status": "0", "allow_edit": "Purchase Manager",  "style": "Danger"},
        {"state": "Ordered",           "doc_status": "1", "allow_edit": "Purchase Manager",  "style": "Success"},
    ]

    transitions = [
        # Draft → Pending Approval
        {"state": "Draft",            "action": "Submit for Approval",  "next_state": "Pending Approval",  "allowed": "Purchase User",    "allow_self_approval": 1},
        {"state": "Draft",            "action": "Submit for Approval",  "next_state": "Pending Approval",  "allowed": "Purchase Manager", "allow_self_approval": 1},
        # Pending Approval → Approved / Rejected
        {"state": "Pending Approval", "action": "Approve",              "next_state": "Approved",           "allowed": "Purchase Manager", "allow_self_approval": 0},
        {"state": "Pending Approval", "action": "Reject",               "next_state": "Rejected",           "allowed": "Purchase Manager", "allow_self_approval": 0},
        # Rejected → Draft (revise)
        {"state": "Rejected",         "action": "Revise",               "next_state": "Draft",              "allowed": "Purchase User",    "allow_self_approval": 1},
        {"state": "Rejected",         "action": "Revise",               "next_state": "Draft",              "allowed": "Purchase Manager", "allow_self_approval": 1},
        # Approved → COA Pending
        {"state": "Approved",         "action": "Send for COA Review",  "next_state": "COA Pending",        "allowed": "Purchase Manager", "allow_self_approval": 1},
        # COA Pending → COA Approved / COA Rejected
        {"state": "COA Pending",      "action": "Approve COA",          "next_state": "COA Approved",       "allowed": "QA Head",          "allow_self_approval": 1},
        {"state": "COA Pending",      "action": "Approve COA",          "next_state": "COA Approved",       "allowed": "QC Manager",       "allow_self_approval": 1},
        {"state": "COA Pending",      "action": "Reject COA",           "next_state": "COA Rejected",       "allowed": "QA Head",          "allow_self_approval": 1},
        {"state": "COA Pending",      "action": "Reject COA",           "next_state": "COA Rejected",       "allowed": "QC Manager",       "allow_self_approval": 1},
        # COA Rejected → COA Pending (re-review)
        {"state": "COA Rejected",     "action": "Re-submit COA",        "next_state": "COA Pending",        "allowed": "Purchase Manager", "allow_self_approval": 1},
        # COA Approved → Ordered (Submit PO)
        {"state": "COA Approved",     "action": "Confirm Order",        "next_state": "Ordered",            "allowed": "Purchase Manager", "allow_self_approval": 1},
    ]

    _create_workflow("Pluviago PO Approval", "Purchase Order", states, transitions)


# ── 3.2.2 Purchase Invoice Pre-Approval Workflow ──
def _create_pi_workflow():
    """
    Flow: Draft → COA Under Review → COA Approved → Submitted
                                   ↘ COA Rejected → Draft (revise)
    """
    states = [
        {"state": "Draft",            "doc_status": "0", "allow_edit": "Purchase User",     "style": ""},
        {"state": "COA Under Review", "doc_status": "0", "allow_edit": "QA Head",           "style": "Warning"},
        {"state": "COA Approved",     "doc_status": "0", "allow_edit": "Purchase Manager",  "style": "Success"},
        {"state": "COA Rejected",     "doc_status": "0", "allow_edit": "Purchase User",     "style": "Danger"},
        {"state": "Submitted",        "doc_status": "1", "allow_edit": "Purchase Manager",  "style": "Success"},
    ]

    transitions = [
        # Draft → COA Under Review
        {"state": "Draft",            "action": "Submit for COA Review", "next_state": "COA Under Review", "allowed": "Purchase User",    "allow_self_approval": 1},
        {"state": "Draft",            "action": "Submit for COA Review", "next_state": "COA Under Review", "allowed": "Purchase Manager", "allow_self_approval": 1},
        # COA Under Review → Approved / Rejected
        {"state": "COA Under Review", "action": "Approve COA",           "next_state": "COA Approved",     "allowed": "QA Head",          "allow_self_approval": 1},
        {"state": "COA Under Review", "action": "Approve COA",           "next_state": "COA Approved",     "allowed": "QC Manager",       "allow_self_approval": 1},
        {"state": "COA Under Review", "action": "Reject COA",            "next_state": "COA Rejected",     "allowed": "QA Head",          "allow_self_approval": 1},
        {"state": "COA Under Review", "action": "Reject COA",            "next_state": "COA Rejected",     "allowed": "QC Manager",       "allow_self_approval": 1},
        # COA Rejected → Draft (revise)
        {"state": "COA Rejected",     "action": "Revise",                "next_state": "Draft",            "allowed": "Purchase User",    "allow_self_approval": 1},
        {"state": "COA Rejected",     "action": "Revise",                "next_state": "Draft",            "allowed": "Purchase Manager", "allow_self_approval": 1},
        # COA Approved → Submitted
        {"state": "COA Approved",     "action": "Submit Invoice",        "next_state": "Submitted",        "allowed": "Purchase Manager", "allow_self_approval": 1},
    ]

    _create_workflow("Pluviago PI COA Approval", "Purchase Invoice", states, transitions)


# ── 3.2.3 Quality Inspection Workflow ──
def _create_qi_workflow():
    """
    Flow: Draft → Pending Review → Accepted (submit)
                                 → Rejected (submit)
                                 → On Hold → Pending Review (resume)
                                           → Harvest Decision (submit)
    """
    states = [
        {"state": "Draft",            "doc_status": "0", "allow_edit": "QC Manager",         "style": ""},
        {"state": "Pending Review",   "doc_status": "0", "allow_edit": "QA Head",            "style": "Primary"},
        {"state": "Accepted",         "doc_status": "1", "allow_edit": "QA Head",            "style": "Success"},
        {"state": "Rejected",         "doc_status": "1", "allow_edit": "QA Head",            "style": "Danger"},
        {"state": "On Hold",          "doc_status": "0", "allow_edit": "QA Head",            "style": "Warning"},
        {"state": "Harvest Decision", "doc_status": "1", "allow_edit": "Production Manager", "style": "Info"},
    ]

    transitions = [
        # Draft → Pending Review
        {"state": "Draft",           "action": "Submit for Review",   "next_state": "Pending Review",  "allowed": "QC Manager",          "allow_self_approval": 1},
        {"state": "Draft",           "action": "Submit for Review",   "next_state": "Pending Review",  "allowed": "Production Operator", "allow_self_approval": 1},
        {"state": "Draft",           "action": "Submit for Review",   "next_state": "Pending Review",  "allowed": "QA Head",             "allow_self_approval": 1},
        # Pending Review → Accepted / Rejected / On Hold
        {"state": "Pending Review",  "action": "Accept",              "next_state": "Accepted",         "allowed": "QA Head",              "allow_self_approval": 1},
        {"state": "Pending Review",  "action": "Accept",              "next_state": "Accepted",         "allowed": "QC Manager",           "allow_self_approval": 1},
        {"state": "Pending Review",  "action": "Accept",              "next_state": "Accepted",         "allowed": "Production Supervisor","allow_self_approval": 1},
        {"state": "Pending Review",  "action": "Reject",              "next_state": "Rejected",         "allowed": "QA Head",              "allow_self_approval": 1},
        {"state": "Pending Review",  "action": "Reject",              "next_state": "Rejected",         "allowed": "QC Manager",           "allow_self_approval": 1},
        {"state": "Pending Review",  "action": "Reject",              "next_state": "Rejected",         "allowed": "Production Supervisor","allow_self_approval": 1},
        {"state": "Pending Review",  "action": "Put on Hold",         "next_state": "On Hold",          "allowed": "QA Head",              "allow_self_approval": 1},
        # On Hold → Resume / Harvest
        {"state": "On Hold",         "action": "Resume Review",       "next_state": "Pending Review",   "allowed": "QA Head",              "allow_self_approval": 1},
        {"state": "On Hold",         "action": "Harvest Early",       "next_state": "Harvest Decision", "allowed": "Production Manager",   "allow_self_approval": 1},
        {"state": "On Hold",         "action": "Harvest Early",       "next_state": "Harvest Decision", "allowed": "QA Head",              "allow_self_approval": 1},
    ]

    _create_workflow("Pluviago QI Review", "Quality Inspection", states, transitions)


# ══════════════════════════════════════════════
# 3.3  SERVER SCRIPTS (5 document-event scripts)
# ══════════════════════════════════════════════
SERVER_SCRIPTS = [
    # ──────────────────────────────────────
    # 1. Auto-Calculate Yield Variance
    # ──────────────────────────────────────
    {
        "name": "Pluviago - Yield Variance Calc",
        "script_type": "DocType Event",
        "reference_doctype": "Work Order",
        "doctype_event": "Before Save",
        "script": """# Auto-calculate yield variance percentage
if doc.actual_yield and doc.expected_yield and doc.expected_yield > 0:
    doc.yield_variance = round(
        ((doc.actual_yield - doc.expected_yield) / doc.expected_yield) * 100, 2
    )
elif not doc.actual_yield:
    doc.yield_variance = 0
""",
    },

    # ──────────────────────────────────────
    # 2. Block PI Submission without COA
    # ──────────────────────────────────────
    {
        "name": "Pluviago - PI COA Gate",
        "script_type": "DocType Event",
        "reference_doctype": "Purchase Invoice",
        "doctype_event": "Before Submit",
        "script": """# Prevent submission if COA not approved (safety net for workflow bypass)
if hasattr(doc, 'coa_preapproval_status') and doc.coa_preapproval_status != "Approved":
    frappe.throw(
        "Purchase Invoice cannot be submitted until COA is approved by QA.<br>"
        "Current COA status: <b>{}</b>".format(doc.coa_preapproval_status),
        title="COA Approval Required"
    )
""",
    },

    # ──────────────────────────────────────
    # 3. Contamination Alert Notification
    # ──────────────────────────────────────
    {
        "name": "Pluviago - Contamination Alert",
        "script_type": "DocType Event",
        "reference_doctype": "Quality Inspection",
        "doctype_event": "After Save",
        "script": """# Send alert when contamination is detected
if doc.contamination_status == "Contaminated":
    # Create a system notification for all QA and Production roles
    users = frappe.get_all("Has Role", filters={
        "role": ["in", ["QA Head", "QC Manager", "Production Manager"]],
        "parenttype": "User"
    }, fields=["parent"], distinct=True)

    for user in users:
        frappe.publish_realtime(
            event="msgprint",
            message="🚨 CONTAMINATION ALERT — Batch: {}, Stage: {}. Immediate action required.".format(
                doc.batch_no or "N/A", doc.stage or "N/A"
            ),
            user=user.parent
        )

    # Also create a Comment for audit trail
    frappe.get_doc({
        "doctype": "Comment",
        "comment_type": "Info",
        "reference_doctype": "Quality Inspection",
        "reference_name": doc.name,
        "content": "⚠️ CONTAMINATION DETECTED — Stage: {}, Batch: {}, Inspected by: {}".format(
            doc.stage or "N/A", doc.batch_no or "N/A", doc.inspected_by or "N/A"
        )
    }).insert(ignore_permissions=True)

    frappe.msgprint(
        msg="Contamination alert sent to QA Head, QC Manager, and Production Manager.",
        title="Contamination Alert Dispatched",
        indicator="red"
    )
""",
    },

    # ──────────────────────────────────────
    # 4. Auto-set Production Stage on Work Order
    # ──────────────────────────────────────
    {
        "name": "Pluviago - Auto Production Stage",
        "script_type": "DocType Event",
        "reference_doctype": "Work Order",
        "doctype_event": "Before Save",
        "script": """# Auto-set production_stage based on the item being produced
if doc.production_item and not doc.production_stage:
    item_code = doc.production_item
    stage_map = {
        "STKSOL-": "Stock Solution Prep",
        "MEDIA-GRN": "Media Preparation",
        "MEDIA-RED": "Media Preparation",
        "MEDIA-FV": "Formulation Mixing",
        "WIP-FLASK": "Flask Inoculation",
        "WIP-PBR25": "PBR 25L Cultivation",
        "WIP-PBR275": "PBR 275L Cultivation",
        "WIP-PBR925": "PBR 925L Cultivation",
        "WIP-PBR6600": "PBR 6600L Production",
        "SFG-HARVEST": "Harvesting",
        "SFG-DRIED": "Drying",
        "FG-PACKED": "Packing",
        "FG-ASTAX-CP": "Re-Packing",
    }

    for prefix, stage in stage_map.items():
        if item_code.startswith(prefix):
            doc.production_stage = stage
            break
""",
    },

    # ──────────────────────────────────────
    # 5. Batch Vendor Details Reminder
    # ──────────────────────────────────────
    {
        "name": "Pluviago - Batch Vendor Reminder",
        "script_type": "DocType Event",
        "reference_doctype": "Purchase Receipt",
        "doctype_event": "After Submit",
        "script": """# Remind user to update vendor COA details on Batch after GRN
batch_items = []
for item in doc.items:
    if item.batch_no:
        batch_items.append(item.batch_no)

if batch_items:
    batch_links = ", ".join(
        '<a href="/app/batch/{0}">{0}</a>'.format(b) for b in batch_items
    )
    frappe.msgprint(
        msg="Please update <b>Vendor COA Details</b> (Vendor COA Number, Vendor Batch No) "
            "on the following batch(es):<br><br>{}<br><br>"
            "Go to each Batch → Vendor COA Details section.".format(batch_links),
        title="Update Batch Vendor Details",
        indicator="blue"
    )
""",
    },
]


def setup_server_scripts():
    print("\n── 3.3 Server Scripts ──")

    # Check if Server Script is enabled in site config
    created = 0
    skipped = 0

    for script_def in SERVER_SCRIPTS:
        script_name = script_def["name"]

        if frappe.db.exists("Server Script", script_name):
            print(f"  ⏭  Server Script: {script_name} (already exists)")
            skipped += 1
            continue

        try:
            doc = frappe.get_doc({
                "doctype": "Server Script",
                "__newname": script_name,
                "script_type": script_def["script_type"],
                "reference_doctype": script_def["reference_doctype"],
                "doctype_event": script_def["doctype_event"],
                "script": script_def["script"],
                "enabled": 1,
            })
            doc.insert(ignore_permissions=True)
            print(f"  ✅ Server Script: {script_name} ({script_def['reference_doctype']} → {script_def['doctype_event']})")
            created += 1
        except Exception as e:
            err_msg = str(e)
            if "ServerScriptNotEnabled" in err_msg or "server_script_enabled" in err_msg:
                print(f"  ⚠️  Server Scripts not enabled! Run: bench --site replica1.local set-config server_script_enabled 1")
                print(f"     Then re-run this script.")
                return
            else:
                print(f"  ❌ Server Script: {script_name} — {err_msg[:120]}")
                skipped += 1

    print(f"\n  📊 Server Scripts: {created} created, {skipped} skipped")


# ══════════════════════════════════════════════
# 3.4  CLIENT SCRIPTS (3 UI helper scripts)
# ══════════════════════════════════════════════
CLIENT_SCRIPTS = [
    # ──────────────────────────────────────
    # 1. Dynamic QC Template Based on Stage
    # ──────────────────────────────────────
    {
        "name": "Pluviago - QI Stage Template Loader",
        "dt": "Quality Inspection",
        "view": "Form",
        "script": """
frappe.ui.form.on('Quality Inspection', {
    stage: function(frm) {
        // Auto-load the correct QI template based on production stage
        let template_map = {
            'Flask':       'Flask Stage - Seed Qualification',
            'PBR 25L':     'PBR 25L - Seed Acceptance',
            'PBR 275L':    'PBR 275L - Contamination and Growth Check',
            'PBR 925L':    'PBR 925L - Seed Release QC',
            'PBR 6600L':   'PBR 6600L - Production Monitoring',
            'Drying':      'Dried Biomass - Release Testing',
            'Packing':     'Packing - Release Verification'
        };

        if (template_map[frm.doc.stage]) {
            frm.set_value('quality_inspection_template', template_map[frm.doc.stage]);
            frappe.show_alert({
                message: __('QI Template set to: {0}', [template_map[frm.doc.stage]]),
                indicator: 'green'
            });
        }
    },

    contamination_status: function(frm) {
        // Visual alert when contamination is detected
        if (frm.doc.contamination_status === 'Contaminated') {
            frappe.confirm(
                '<b style="color:red;">⚠️ CONTAMINATION DETECTED</b><br><br>' +
                'This will trigger an alert to QA Head and Production Manager.<br>' +
                'Are you sure this sample is contaminated?',
                () => {
                    // User confirmed - set decision to Hold
                    frm.set_value('decision', 'Hold');
                },
                () => {
                    // User cancelled - reset
                    frm.set_value('contamination_status', 'Clean');
                }
            );
        }
    }
});
""",
    },

    # ──────────────────────────────────────
    # 2. Formulation Volume Calculator
    # ──────────────────────────────────────
    {
        "name": "Pluviago - Formulation V Calculator",
        "dt": "Work Order",
        "view": "Form",
        "script": """
frappe.ui.form.on('Work Order', {
    qty: function(frm) {
        // Show Green/Red medium split when producing Formulation V
        if (frm.doc.production_item === 'MEDIA-FV') {
            let total_mL = frm.doc.qty;
            let green_mL = (total_mL * 0.75).toFixed(1);
            let red_mL   = (total_mL * 0.25).toFixed(1);

            frappe.show_alert({
                message: __('Formulation V ({0} mL): Green Medium = {1} mL, Red Medium BG-11 = {2} mL',
                    [total_mL, green_mL, red_mL]),
                indicator: 'blue'
            }, 7);
        }
    },

    production_item: function(frm) {
        // Trigger qty handler if Formulation V is selected
        if (frm.doc.production_item === 'MEDIA-FV' && frm.doc.qty) {
            frm.trigger('qty');
        }
    },

    actual_yield: function(frm) {
        // Auto-trigger yield variance display
        if (frm.doc.actual_yield && frm.doc.expected_yield) {
            let variance = ((frm.doc.actual_yield - frm.doc.expected_yield) / frm.doc.expected_yield * 100).toFixed(2);
            let indicator = Math.abs(variance) > 10 ? 'red' : (Math.abs(variance) > 5 ? 'orange' : 'green');
            frappe.show_alert({
                message: __('Yield Variance: {0}%', [variance]),
                indicator: indicator
            }, 5);
        }
    }
});
""",
    },

    # ──────────────────────────────────────
    # 3. COA Verification Reminder on GRN
    # ──────────────────────────────────────
    {
        "name": "Pluviago - PR COA Reminder",
        "dt": "Purchase Receipt",
        "view": "Form",
        "script": """
frappe.ui.form.on('Purchase Receipt', {
    refresh: function(frm) {
        // Show reminder banner if items have batch tracking
        if (frm.doc.docstatus === 0) {
            let batch_items = (frm.doc.items || []).filter(d => d.item_code && d.item_code.startsWith('CHEM-'));
            if (batch_items.length > 0) {
                frm.dashboard.set_headline(
                    '<span style="color: #e67e22;">📋 Remember: Verify Vendor COA before accepting chemicals.</span>'
                );
            }
        }
    },

    before_submit: function(frm) {
        // Check if any batch-managed items are being received
        let chem_items = (frm.doc.items || []).filter(d => d.item_code && d.item_code.startsWith('CHEM-'));

        if (chem_items.length > 0) {
            frappe.validated = false;
            frappe.confirm(
                '<b>COA Verification Check</b><br><br>' +
                'You are receiving <b>' + chem_items.length + ' chemical item(s)</b>.<br><br>' +
                '✅ Have you verified the Vendor COA for all items?<br>' +
                '✅ Have you checked batch numbers and expiry dates?<br><br>' +
                '<i>After submission, update Vendor COA details on each Batch record.</i>',
                () => {
                    frappe.validated = true;
                    frm.save('Submit');
                }
            );
        }
    }
});
""",
    },
]


def setup_client_scripts():
    print("\n── 3.4 Client Scripts ──")

    created = 0
    skipped = 0

    for script_def in CLIENT_SCRIPTS:
        script_name = script_def["name"]

        if frappe.db.exists("Client Script", script_name):
            print(f"  ⏭  Client Script: {script_name} (already exists)")
            skipped += 1
            continue

        try:
            doc = frappe.get_doc({
                "doctype": "Client Script",
                "__newname": script_name,
                "dt": script_def["dt"],
                "view": script_def["view"],
                "script": script_def["script"],
                "enabled": 1,
            })
            doc.insert(ignore_permissions=True)
            print(f"  ✅ Client Script: {script_name} ({script_def['dt']})")
            created += 1
        except Exception as e:
            print(f"  ❌ Client Script: {script_name} — {str(e)[:120]}")
            skipped += 1

    print(f"\n  📊 Client Scripts: {created} created, {skipped} skipped")
