"""
Phase 4: Print Formats & Custom Reports — Pluviago Biotech
============================================================
Creates:
  4.1  Custom Print Formats (4 — COA, Batch Label, Production Record, Dispatch COA)
  4.2  Custom Reports (5 — Batch Genealogy, Yield Analysis, Contamination, Vendor COA, Production Summary)

Run via:
    bench --site replica1.local execute pluviago.setup.phase4.execute

Idempotent — safe to run multiple times.
"""

import frappe

# ──────────────────────────────────────────────
COMPANY_NAME = "Pluviago Biotech Pvt. Ltd."
COMPANY_ABBR = "PB"


# ══════════════════════════════════════════════
# MAIN ENTRY POINT
# ══════════════════════════════════════════════
def execute():
    print("\n" + "=" * 70)
    print("  PHASE 4: Print Formats & Custom Reports — Pluviago Biotech")
    print("=" * 70)

    setup_print_formats()
    frappe.db.commit()

    setup_custom_reports()
    frappe.db.commit()

    print("\n" + "=" * 70)
    print("  ✅ PHASE 4 COMPLETE — Print Formats & Reports created!")
    print("=" * 70 + "\n")


# ══════════════════════════════════════════════
# 4.1  CUSTOM PRINT FORMATS
# ══════════════════════════════════════════════

# ── 4.1.1 COA Print Format ──
COA_PRINT_HTML = """
<style>
    .coa-header { text-align: center; border-bottom: 2px solid #333; padding-bottom: 10px; margin-bottom: 15px; }
    .coa-header h2 { margin: 0; color: #0b5394; }
    .coa-header h3 { margin: 5px 0 0; font-weight: normal; color: #555; }
    .coa-info-table { width: 100%; margin-bottom: 15px; }
    .coa-info-table td { padding: 4px 8px; vertical-align: top; }
    .coa-info-table .label { font-weight: bold; width: 150px; color: #333; }
    .coa-params { width: 100%; border-collapse: collapse; margin-bottom: 15px; }
    .coa-params th { background: #0b5394; color: #fff; padding: 6px 8px; text-align: left; font-size: 11px; }
    .coa-params td { padding: 5px 8px; border-bottom: 1px solid #ddd; font-size: 11px; }
    .coa-params tr:nth-child(even) { background: #f4f8fc; }
    .coa-status { text-align: center; margin-top: 15px; padding: 10px; font-size: 14px; font-weight: bold; }
    .coa-status.accepted { background: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
    .coa-status.rejected { background: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
    .coa-footer { margin-top: 30px; display: flex; justify-content: space-between; }
    .coa-signature { text-align: center; min-width: 200px; }
    .coa-signature .line { border-top: 1px solid #333; margin-top: 40px; padding-top: 5px; }
</style>

<div class="coa-header">
    <h2>CERTIFICATE OF ANALYSIS</h2>
    <h3>{{ doc.company or "Pluviago Biotech Pvt. Ltd." }}</h3>
</div>

<table class="coa-info-table">
    <tr>
        <td class="label">QI Number:</td><td>{{ doc.name }}</td>
        <td class="label">Inspection Type:</td><td>{{ doc.inspection_type or "-" }}</td>
    </tr>
    <tr>
        <td class="label">Item:</td><td>{{ doc.item_code }} — {{ doc.item_name }}</td>
        <td class="label">Batch No:</td><td>{{ doc.batch_no or "-" }}</td>
    </tr>
    <tr>
        <td class="label">Reference:</td><td>{{ doc.reference_type or "" }} {{ doc.reference_name or "" }}</td>
        <td class="label">Report Date:</td><td>{{ doc.report_date or frappe.utils.today() }}</td>
    </tr>
    <tr>
        <td class="label">Stage:</td><td>{{ doc.stage or "-" }}</td>
        <td class="label">Inspected By:</td><td>{{ doc.inspected_by or "-" }}</td>
    </tr>
    {% if doc.stage in ["PBR 6600L", "PBR 925L"] %}
    <tr>
        <td class="label">Growth Phase:</td><td>{{ doc.phase or "-" }}</td>
        <td class="label">Contamination:</td><td>{{ doc.contamination_status or "-" }}</td>
    </tr>
    {% endif %}
</table>

<h4 style="color:#0b5394; margin-bottom:5px;">Test Parameters & Results</h4>
<table class="coa-params">
    <thead>
        <tr>
            <th>#</th>
            <th>Parameter</th>
            <th>Specification</th>
            <th>Reading / Result</th>
            <th>Status</th>
        </tr>
    </thead>
    <tbody>
        {% for row in doc.readings %}
        <tr>
            <td>{{ loop.index }}</td>
            <td>{{ row.specification }}</td>
            <td>
                {% if row.min_value and row.max_value and row.min_value != row.max_value %}
                    {{ row.min_value }} — {{ row.max_value }}
                {% elif row.value %}
                    {{ row.value }}
                {% else %}
                    —
                {% endif %}
            </td>
            <td>
                {% if row.reading_1 %}{{ row.reading_1 }}{% elif row.reading_value %}{{ row.reading_value }}{% else %}—{% endif %}
            </td>
            <td>{{ row.status or "—" }}</td>
        </tr>
        {% endfor %}
    </tbody>
</table>

{% if doc.decision %}
<p><strong>QC Decision:</strong> {{ doc.decision }}</p>
{% endif %}

<div class="coa-status {{ 'accepted' if doc.status == 'Accepted' else 'rejected' if doc.status == 'Rejected' else '' }}">
    Overall Status: {{ doc.status or "Pending" }}
</div>

<div class="coa-footer">
    <div class="coa-signature">
        <div class="line">Tested By</div>
    </div>
    <div class="coa-signature">
        <div class="line">Reviewed By</div>
    </div>
    <div class="coa-signature">
        <div class="line">Approved By</div>
    </div>
</div>
"""

# ── 4.1.2 Batch Label Print Format ──
BATCH_LABEL_HTML = """
<style>
    .batch-label { border: 2px solid #333; padding: 12px; width: 300px; font-family: Arial, sans-serif; font-size: 11px; }
    .batch-label .company { text-align: center; font-weight: bold; font-size: 12px; color: #0b5394; border-bottom: 1px solid #999; padding-bottom: 5px; margin-bottom: 8px; }
    .batch-label .row { display: flex; justify-content: space-between; margin-bottom: 3px; }
    .batch-label .lbl { font-weight: bold; color: #333; }
    .batch-label .val { text-align: right; }
    .batch-label .barcode-area { text-align: center; margin-top: 10px; padding-top: 8px; border-top: 1px dashed #999; }
    .batch-label .storage { margin-top: 8px; padding: 4px; text-align: center; font-weight: bold; font-size: 10px; }
    .batch-label .storage.cold { background: #cce5ff; color: #004085; border: 1px solid #b8daff; }
    .batch-label .storage.rt { background: #fff3cd; color: #856404; border: 1px solid #ffeeba; }
</style>

<div class="batch-label">
    <div class="company">Pluviago Biotech Pvt. Ltd.</div>

    <div class="row">
        <span class="lbl">Item:</span>
        <span class="val">{{ doc.item or "-" }}</span>
    </div>
    <div class="row">
        <span class="lbl">Item Name:</span>
        <span class="val">{{ doc.item_name or frappe.db.get_value("Item", doc.item, "item_name") if doc.item else "-" }}</span>
    </div>
    <div class="row">
        <span class="lbl">Batch No:</span>
        <span class="val"><strong>{{ doc.name }}</strong></span>
    </div>
    <div class="row">
        <span class="lbl">Mfg Date:</span>
        <span class="val">{{ doc.manufacturing_date or "-" }}</span>
    </div>
    <div class="row">
        <span class="lbl">Expiry:</span>
        <span class="val">{{ doc.expiry_date or "-" }}</span>
    </div>

    {% if doc.vendor_batch_no %}
    <div class="row">
        <span class="lbl">Vendor Batch:</span>
        <span class="val">{{ doc.vendor_batch_no }}</span>
    </div>
    {% endif %}

    {% set storage = doc.storage_condition_actual or "" %}
    {% if storage %}
    <div class="storage {{ 'cold' if '2-8' in storage else 'rt' }}">
        Storage: {{ storage }}
    </div>
    {% endif %}

    <div class="barcode-area">
        <img src="https://barcode.tec-it.com/barcode.ashx?data={{ doc.name }}&code=QRCode&dpi=96&dataseparator=" style="width:80px;height:80px;" alt="QR"/>
        <br><small>{{ doc.name }}</small>
    </div>
</div>
"""

# ── 4.1.3 Production Batch Record ──
PRODUCTION_RECORD_HTML = """
<style>
    .pbr-header { text-align: center; border-bottom: 2px solid #0b5394; padding-bottom: 8px; margin-bottom: 12px; }
    .pbr-header h2 { margin: 0; color: #0b5394; font-size: 16px; }
    .pbr-header h3 { margin: 3px 0 0; font-weight: normal; color: #555; font-size: 12px; }
    .pbr-table { width: 100%; border-collapse: collapse; margin-bottom: 12px; font-size: 11px; }
    .pbr-table th { background: #0b5394; color: #fff; padding: 5px 8px; text-align: left; }
    .pbr-table td { padding: 4px 8px; border-bottom: 1px solid #ddd; }
    .pbr-table tr:nth-child(even) { background: #f4f8fc; }
    .pbr-info td { padding: 3px 8px; }
    .pbr-info .lbl { font-weight: bold; width: 160px; }
    .pbr-yield { margin: 10px 0; padding: 8px; border: 1px solid #ddd; }
    .pbr-yield .title { font-weight: bold; color: #0b5394; margin-bottom: 5px; }
</style>

<div class="pbr-header">
    <h2>PRODUCTION BATCH RECORD</h2>
    <h3>{{ doc.company or "Pluviago Biotech Pvt. Ltd." }}</h3>
</div>

<table class="pbr-info">
    <tr><td class="lbl">Work Order:</td><td>{{ doc.name }}</td><td class="lbl">Status:</td><td>{{ doc.status }}</td></tr>
    <tr><td class="lbl">Production Item:</td><td>{{ doc.production_item }} — {{ doc.item_name or "" }}</td><td class="lbl">BOM:</td><td>{{ doc.bom_no or "-" }}</td></tr>
    <tr><td class="lbl">Production Stage:</td><td>{{ doc.production_stage or "-" }}</td><td class="lbl">Qty to Produce:</td><td>{{ doc.qty }} {{ doc.stock_uom }}</td></tr>
    <tr><td class="lbl">Planned Start:</td><td>{{ doc.planned_start_date or "-" }}</td><td class="lbl">Planned End:</td><td>{{ doc.expected_delivery_date or "-" }}</td></tr>
    <tr><td class="lbl">Actual Start:</td><td>{{ doc.actual_start_date or "-" }}</td><td class="lbl">Actual End:</td><td>{{ doc.actual_end_date or "-" }}</td></tr>
</table>

<div class="pbr-yield">
    <div class="title">Yield Tracking</div>
    <table class="pbr-info">
        <tr>
            <td class="lbl">Expected Yield:</td><td>{{ doc.expected_yield or "-" }}</td>
            <td class="lbl">Actual Yield:</td><td>{{ doc.actual_yield or "-" }}</td>
            <td class="lbl">Yield Variance:</td><td>{{ doc.yield_variance or 0 }}%</td>
        </tr>
    </table>
</div>

{% if doc.required_items %}
<h4 style="color:#0b5394; margin-top:12px;">Raw Materials Consumed</h4>
<table class="pbr-table">
    <thead>
        <tr><th>#</th><th>Item Code</th><th>Item Name</th><th>Required Qty</th><th>Consumed Qty</th><th>UOM</th></tr>
    </thead>
    <tbody>
        {% for item in doc.required_items %}
        <tr>
            <td>{{ loop.index }}</td>
            <td>{{ item.item_code }}</td>
            <td>{{ item.item_name }}</td>
            <td>{{ item.required_qty }}</td>
            <td>{{ item.consumed_qty or 0 }}</td>
            <td>{{ item.stock_uom }}</td>
        </tr>
        {% endfor %}
    </tbody>
</table>
{% endif %}

{% if doc.operations %}
<h4 style="color:#0b5394; margin-top:12px;">Operations</h4>
<table class="pbr-table">
    <thead>
        <tr><th>#</th><th>Operation</th><th>Workstation</th><th>Time (mins)</th><th>Completed Qty</th><th>Status</th></tr>
    </thead>
    <tbody>
        {% for op in doc.operations %}
        <tr>
            <td>{{ loop.index }}</td>
            <td>{{ op.operation }}</td>
            <td>{{ op.workstation }}</td>
            <td>{{ op.time_in_mins or 0 }}</td>
            <td>{{ op.completed_qty or 0 }}</td>
            <td>{{ op.status or "-" }}</td>
        </tr>
        {% endfor %}
    </tbody>
</table>
{% endif %}

<div style="margin-top:30px; display:flex; justify-content:space-between;">
    <div style="text-align:center; min-width:180px;"><div style="border-top:1px solid #333; margin-top:40px; padding-top:5px;">Produced By</div></div>
    <div style="text-align:center; min-width:180px;"><div style="border-top:1px solid #333; margin-top:40px; padding-top:5px;">Verified By (QC)</div></div>
    <div style="text-align:center; min-width:180px;"><div style="border-top:1px solid #333; margin-top:40px; padding-top:5px;">Approved By</div></div>
</div>
"""

# ── 4.1.4 Dispatch COA ──
DISPATCH_COA_HTML = """
<style>
    .dcoa-header { text-align: center; border-bottom: 2px solid #0b5394; padding-bottom: 8px; margin-bottom: 12px; }
    .dcoa-header h2 { margin: 0; color: #0b5394; }
    .dcoa-header h3 { margin: 3px 0 0; font-weight: normal; color: #555; }
    .dcoa-table { width: 100%; border-collapse: collapse; margin-bottom: 12px; font-size: 11px; }
    .dcoa-table th { background: #0b5394; color: #fff; padding: 5px 8px; text-align: left; }
    .dcoa-table td { padding: 4px 8px; border-bottom: 1px solid #ddd; }
    .dcoa-info td { padding: 3px 8px; }
    .dcoa-info .lbl { font-weight: bold; width: 140px; }
</style>

<div class="dcoa-header">
    <h2>DISPATCH CERTIFICATE OF ANALYSIS</h2>
    <h3>{{ doc.company or "Pluviago Biotech Pvt. Ltd." }}</h3>
</div>

<table class="dcoa-info">
    <tr><td class="lbl">Delivery Note:</td><td>{{ doc.name }}</td><td class="lbl">Date:</td><td>{{ doc.posting_date }}</td></tr>
    <tr><td class="lbl">Customer:</td><td>{{ doc.customer_name or doc.customer }}</td><td class="lbl">PO Reference:</td><td>{{ doc.po_no or "-" }}</td></tr>
    <tr><td class="lbl">Transporter:</td><td>{{ doc.transporter_name or "-" }}</td><td class="lbl">LR No:</td><td>{{ doc.lr_no or "-" }}</td></tr>
</table>

<h4 style="color:#0b5394; margin-top:12px;">Items Dispatched</h4>
<table class="dcoa-table">
    <thead>
        <tr><th>#</th><th>Item Code</th><th>Item Name</th><th>Batch No</th><th>Qty</th><th>UOM</th></tr>
    </thead>
    <tbody>
        {% for item in doc.items %}
        <tr>
            <td>{{ loop.index }}</td>
            <td>{{ item.item_code }}</td>
            <td>{{ item.item_name }}</td>
            <td>{{ item.batch_no or "-" }}</td>
            <td>{{ item.qty }}</td>
            <td>{{ item.uom }}</td>
        </tr>
        {% endfor %}
    </tbody>
</table>

<p style="font-size:11px; color:#555;">
    This certificate confirms that the above items have been manufactured and tested
    in accordance with our standard operating procedures. Quality Inspection records
    are available on request.
</p>

<div style="margin-top:30px; display:flex; justify-content:space-between;">
    <div style="text-align:center; min-width:180px;"><div style="border-top:1px solid #333; margin-top:40px; padding-top:5px;">Dispatch Officer</div></div>
    <div style="text-align:center; min-width:180px;"><div style="border-top:1px solid #333; margin-top:40px; padding-top:5px;">QA Approval</div></div>
</div>
"""

PRINT_FORMATS = [
    {
        "name": "Pluviago COA Print",
        "doc_type": "Quality Inspection",
        "html": COA_PRINT_HTML,
    },
    {
        "name": "Pluviago Batch Label",
        "doc_type": "Batch",
        "html": BATCH_LABEL_HTML,
    },
    {
        "name": "Pluviago Production Batch Record",
        "doc_type": "Work Order",
        "html": PRODUCTION_RECORD_HTML,
    },
    {
        "name": "Pluviago Dispatch COA",
        "doc_type": "Delivery Note",
        "html": DISPATCH_COA_HTML,
    },
]


def setup_print_formats():
    print("\n── 4.1 Custom Print Formats ──")

    created = 0
    skipped = 0

    for pf_def in PRINT_FORMATS:
        pf_name = pf_def["name"]

        if frappe.db.exists("Print Format", pf_name):
            print(f"  ⏭  Print Format: {pf_name} (already exists)")
            skipped += 1
            continue

        try:
            doc = frappe.get_doc({
                "doctype": "Print Format",
                "__newname": pf_name,
                "doc_type": pf_def["doc_type"],
                "module": "Pluviago",
                "standard": "No",
                "custom_format": 1,
                "print_format_type": "Jinja",
                "html": pf_def["html"],
                "disabled": 0,
            })
            doc.insert(ignore_permissions=True)
            print(f"  ✅ Print Format: {pf_name} ({pf_def['doc_type']})")
            created += 1
        except Exception as e:
            print(f"  ❌ Print Format: {pf_name} — {str(e)[:120]}")
            skipped += 1

    print(f"\n  📊 Print Formats: {created} created, {skipped} skipped")


# ══════════════════════════════════════════════
# 4.2  CUSTOM REPORTS
# ══════════════════════════════════════════════

# ── 4.2.1 Batch Genealogy Report ──
BATCH_GENEALOGY_QUERY = """
SELECT
    se.posting_date       AS `Date`,
    se.name               AS `Stock Entry`,
    se.stock_entry_type   AS `Type`,
    sed.item_code         AS `Item Code`,
    sed.item_name         AS `Item Name`,
    sed.batch_no          AS `Batch No`,
    sed.qty               AS `Qty`,
    sed.stock_uom         AS `UOM`,
    sed.s_warehouse       AS `Source Warehouse`,
    sed.t_warehouse       AS `Target Warehouse`,
    se.work_order         AS `Work Order`
FROM
    `tabStock Entry Detail` sed
JOIN
    `tabStock Entry` se ON se.name = sed.parent
WHERE
    se.docstatus = 1
    AND sed.batch_no IS NOT NULL
    AND sed.batch_no != ''
    %(conditions)s
ORDER BY
    se.posting_date DESC, se.name
"""

BATCH_GENEALOGY_JS = """
frappe.query_reports["Batch Genealogy"] = {
    filters: [
        {
            fieldname: "batch_no",
            label: __("Batch No"),
            fieldtype: "Link",
            options: "Batch",
        },
        {
            fieldname: "item_code",
            label: __("Item Code"),
            fieldtype: "Link",
            options: "Item",
        },
        {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date",
            default: frappe.datetime.add_months(frappe.datetime.get_today(), -3),
        },
        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date",
            default: frappe.datetime.get_today(),
        },
    ]
};
"""

BATCH_GENEALOGY_PY = '''
import frappe

def execute(filters=None):
    columns = [
        {"fieldname": "date", "label": "Date", "fieldtype": "Date", "width": 100},
        {"fieldname": "stock_entry", "label": "Stock Entry", "fieldtype": "Link", "options": "Stock Entry", "width": 140},
        {"fieldname": "type", "label": "Type", "fieldtype": "Data", "width": 130},
        {"fieldname": "item_code", "label": "Item Code", "fieldtype": "Link", "options": "Item", "width": 120},
        {"fieldname": "item_name", "label": "Item Name", "fieldtype": "Data", "width": 180},
        {"fieldname": "batch_no", "label": "Batch No", "fieldtype": "Link", "options": "Batch", "width": 120},
        {"fieldname": "qty", "label": "Qty", "fieldtype": "Float", "width": 80},
        {"fieldname": "uom", "label": "UOM", "fieldtype": "Data", "width": 60},
        {"fieldname": "s_warehouse", "label": "Source Warehouse", "fieldtype": "Link", "options": "Warehouse", "width": 150},
        {"fieldname": "t_warehouse", "label": "Target Warehouse", "fieldtype": "Link", "options": "Warehouse", "width": 150},
        {"fieldname": "work_order", "label": "Work Order", "fieldtype": "Link", "options": "Work Order", "width": 140},
    ]

    conditions = []
    values = {}

    if filters.get("batch_no"):
        conditions.append("sed.batch_no = %(batch_no)s")
        values["batch_no"] = filters["batch_no"]

    if filters.get("item_code"):
        conditions.append("sed.item_code = %(item_code)s")
        values["item_code"] = filters["item_code"]

    if filters.get("from_date"):
        conditions.append("se.posting_date >= %(from_date)s")
        values["from_date"] = filters["from_date"]

    if filters.get("to_date"):
        conditions.append("se.posting_date <= %(to_date)s")
        values["to_date"] = filters["to_date"]

    where_clause = " AND ".join(conditions) if conditions else "1=1"

    data = frappe.db.sql("""
        SELECT
            se.posting_date, se.name, se.stock_entry_type,
            sed.item_code, sed.item_name, sed.batch_no,
            sed.qty, sed.stock_uom,
            sed.s_warehouse, sed.t_warehouse,
            se.work_order
        FROM `tabStock Entry Detail` sed
        JOIN `tabStock Entry` se ON se.name = sed.parent
        WHERE se.docstatus = 1
            AND sed.batch_no IS NOT NULL AND sed.batch_no != \'\'
            AND {where}
        ORDER BY se.posting_date DESC, se.name
    """.format(where=where_clause), values, as_dict=True)

    return columns, data
'''

# ── 4.2.2 Stage-wise Yield Analysis ──
YIELD_ANALYSIS_PY = '''
import frappe

def execute(filters=None):
    columns = [
        {"fieldname": "name", "label": "Work Order", "fieldtype": "Link", "options": "Work Order", "width": 150},
        {"fieldname": "production_item", "label": "Item", "fieldtype": "Link", "options": "Item", "width": 120},
        {"fieldname": "item_name", "label": "Item Name", "fieldtype": "Data", "width": 180},
        {"fieldname": "production_stage", "label": "Stage", "fieldtype": "Data", "width": 140},
        {"fieldname": "qty", "label": "Planned Qty", "fieldtype": "Float", "width": 100},
        {"fieldname": "produced_qty", "label": "Produced Qty", "fieldtype": "Float", "width": 100},
        {"fieldname": "expected_yield", "label": "Expected Yield", "fieldtype": "Float", "width": 110},
        {"fieldname": "actual_yield", "label": "Actual Yield", "fieldtype": "Float", "width": 100},
        {"fieldname": "yield_variance", "label": "Variance (%)", "fieldtype": "Float", "width": 100},
        {"fieldname": "status", "label": "Status", "fieldtype": "Data", "width": 100},
    ]

    conditions = []
    values = {}

    if filters.get("production_stage"):
        conditions.append("wo.production_stage = %(production_stage)s")
        values["production_stage"] = filters["production_stage"]

    if filters.get("from_date"):
        conditions.append("wo.planned_start_date >= %(from_date)s")
        values["from_date"] = filters["from_date"]

    if filters.get("to_date"):
        conditions.append("wo.planned_start_date <= %(to_date)s")
        values["to_date"] = filters["to_date"]

    if filters.get("item"):
        conditions.append("wo.production_item = %(item)s")
        values["item"] = filters["item"]

    where_clause = " AND ".join(conditions) if conditions else "1=1"

    data = frappe.db.sql("""
        SELECT
            wo.name, wo.production_item, wo.item_name,
            wo.production_stage, wo.qty, wo.produced_qty,
            wo.expected_yield, wo.actual_yield, wo.yield_variance,
            wo.status
        FROM `tabWork Order` wo
        WHERE wo.docstatus IN (0, 1)
            AND {where}
        ORDER BY wo.planned_start_date DESC
    """.format(where=where_clause), values, as_dict=True)

    return columns, data
'''

YIELD_ANALYSIS_JS = """
frappe.query_reports["Stage-wise Yield Analysis"] = {
    filters: [
        {
            fieldname: "production_stage",
            label: __("Production Stage"),
            fieldtype: "Select",
            options: "\\nStock Solution Prep\\nMedia Preparation\\nFormulation Mixing\\nFlask Inoculation\\nPBR 25L Cultivation\\nPBR 275L Cultivation\\nPBR 925L Cultivation\\nPBR 6600L Production\\nHarvesting\\nDrying\\nPacking",
        },
        {
            fieldname: "item",
            label: __("Production Item"),
            fieldtype: "Link",
            options: "Item",
        },
        {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date",
            default: frappe.datetime.add_months(frappe.datetime.get_today(), -3),
        },
        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date",
            default: frappe.datetime.get_today(),
        },
    ]
};
"""

# ── 4.2.3 Contamination Report ──
CONTAMINATION_REPORT_PY = '''
import frappe

def execute(filters=None):
    columns = [
        {"fieldname": "name", "label": "QI No", "fieldtype": "Link", "options": "Quality Inspection", "width": 150},
        {"fieldname": "report_date", "label": "Date", "fieldtype": "Date", "width": 100},
        {"fieldname": "item_code", "label": "Item", "fieldtype": "Link", "options": "Item", "width": 120},
        {"fieldname": "item_name", "label": "Item Name", "fieldtype": "Data", "width": 160},
        {"fieldname": "batch_no", "label": "Batch", "fieldtype": "Link", "options": "Batch", "width": 120},
        {"fieldname": "stage", "label": "Stage", "fieldtype": "Data", "width": 120},
        {"fieldname": "contamination_status", "label": "Contamination", "fieldtype": "Data", "width": 110},
        {"fieldname": "decision", "label": "Decision", "fieldtype": "Data", "width": 110},
        {"fieldname": "inspected_by", "label": "Inspected By", "fieldtype": "Data", "width": 120},
        {"fieldname": "status", "label": "QI Status", "fieldtype": "Data", "width": 100},
    ]

    conditions = []
    values = {}

    if filters.get("from_date"):
        conditions.append("qi.report_date >= %(from_date)s")
        values["from_date"] = filters["from_date"]

    if filters.get("to_date"):
        conditions.append("qi.report_date <= %(to_date)s")
        values["to_date"] = filters["to_date"]

    if filters.get("stage"):
        conditions.append("qi.stage = %(stage)s")
        values["stage"] = filters["stage"]

    where_clause = " AND ".join(conditions) if conditions else "1=1"

    data = frappe.db.sql("""
        SELECT
            qi.name, qi.report_date, qi.item_code, qi.item_name,
            qi.batch_no, qi.stage, qi.contamination_status,
            qi.decision, qi.inspected_by, qi.status
        FROM `tabQuality Inspection` qi
        WHERE qi.contamination_status IN (\'Suspected\', \'Contaminated\')
            AND {where}
        ORDER BY qi.report_date DESC
    """.format(where=where_clause), values, as_dict=True)

    return columns, data
'''

CONTAMINATION_REPORT_JS = """
frappe.query_reports["Contamination Report"] = {
    filters: [
        {
            fieldname: "stage",
            label: __("Stage"),
            fieldtype: "Select",
            options: "\\nFlask\\nPBR 25L\\nPBR 275L\\nPBR 925L\\nPBR 6600L",
        },
        {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date",
            default: frappe.datetime.add_months(frappe.datetime.get_today(), -6),
        },
        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date",
            default: frappe.datetime.get_today(),
        },
    ]
};
"""

# ── 4.2.4 Vendor COA Compliance ──
VENDOR_COA_PY = '''
import frappe

def execute(filters=None):
    columns = [
        {"fieldname": "supplier", "label": "Supplier", "fieldtype": "Link", "options": "Supplier", "width": 160},
        {"fieldname": "total_invoices", "label": "Total PIs", "fieldtype": "Int", "width": 80},
        {"fieldname": "coa_approved", "label": "COA Approved", "fieldtype": "Int", "width": 100},
        {"fieldname": "coa_rejected", "label": "COA Rejected", "fieldtype": "Int", "width": 100},
        {"fieldname": "coa_pending", "label": "COA Pending", "fieldtype": "Int", "width": 100},
        {"fieldname": "approval_rate", "label": "Approval Rate (%)", "fieldtype": "Float", "width": 120},
    ]

    conditions = []
    values = {}

    if filters.get("supplier"):
        conditions.append("pi.supplier = %(supplier)s")
        values["supplier"] = filters["supplier"]

    if filters.get("from_date"):
        conditions.append("pi.posting_date >= %(from_date)s")
        values["from_date"] = filters["from_date"]

    if filters.get("to_date"):
        conditions.append("pi.posting_date <= %(to_date)s")
        values["to_date"] = filters["to_date"]

    where_clause = " AND ".join(conditions) if conditions else "1=1"

    data = frappe.db.sql("""
        SELECT
            pi.supplier,
            COUNT(*) AS total_invoices,
            SUM(CASE WHEN pi.coa_preapproval_status = \'Approved\' THEN 1 ELSE 0 END) AS coa_approved,
            SUM(CASE WHEN pi.coa_preapproval_status = \'Rejected\' THEN 1 ELSE 0 END) AS coa_rejected,
            SUM(CASE WHEN pi.coa_preapproval_status = \'Pending\' THEN 1 ELSE 0 END) AS coa_pending,
            ROUND(
                SUM(CASE WHEN pi.coa_preapproval_status = \'Approved\' THEN 1 ELSE 0 END) * 100.0
                / NULLIF(COUNT(*), 0), 1
            ) AS approval_rate
        FROM `tabPurchase Invoice` pi
        WHERE pi.docstatus IN (0, 1)
            AND {where}
        GROUP BY pi.supplier
        ORDER BY approval_rate DESC
    """.format(where=where_clause), values, as_dict=True)

    return columns, data
'''

VENDOR_COA_JS = """
frappe.query_reports["Vendor COA Compliance"] = {
    filters: [
        {
            fieldname: "supplier",
            label: __("Supplier"),
            fieldtype: "Link",
            options: "Supplier",
        },
        {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date",
            default: frappe.datetime.add_months(frappe.datetime.get_today(), -12),
        },
        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date",
            default: frappe.datetime.get_today(),
        },
    ]
};
"""

# ── 4.2.5 Production Batch Summary ──
PRODUCTION_SUMMARY_PY = '''
import frappe

def execute(filters=None):
    columns = [
        {"fieldname": "name", "label": "Work Order", "fieldtype": "Link", "options": "Work Order", "width": 150},
        {"fieldname": "production_item", "label": "Item", "fieldtype": "Link", "options": "Item", "width": 120},
        {"fieldname": "item_name", "label": "Item Name", "fieldtype": "Data", "width": 160},
        {"fieldname": "production_stage", "label": "Stage", "fieldtype": "Data", "width": 130},
        {"fieldname": "qty", "label": "Planned", "fieldtype": "Float", "width": 80},
        {"fieldname": "produced_qty", "label": "Produced", "fieldtype": "Float", "width": 80},
        {"fieldname": "status", "label": "WO Status", "fieldtype": "Data", "width": 100},
        {"fieldname": "qi_count", "label": "QI Count", "fieldtype": "Int", "width": 80},
        {"fieldname": "qi_status", "label": "Latest QI", "fieldtype": "Data", "width": 100},
        {"fieldname": "planned_start_date", "label": "Start Date", "fieldtype": "Date", "width": 100},
    ]

    conditions = []
    values = {}

    if filters.get("from_date"):
        conditions.append("wo.planned_start_date >= %(from_date)s")
        values["from_date"] = filters["from_date"]

    if filters.get("to_date"):
        conditions.append("wo.planned_start_date <= %(to_date)s")
        values["to_date"] = filters["to_date"]

    if filters.get("production_stage"):
        conditions.append("wo.production_stage = %(production_stage)s")
        values["production_stage"] = filters["production_stage"]

    if filters.get("status"):
        conditions.append("wo.status = %(status)s")
        values["status"] = filters["status"]

    where_clause = " AND ".join(conditions) if conditions else "1=1"

    data = frappe.db.sql("""
        SELECT
            wo.name, wo.production_item, wo.item_name,
            wo.production_stage, wo.qty, wo.produced_qty,
            wo.status, wo.planned_start_date,
            (SELECT COUNT(*) FROM `tabQuality Inspection` qi
             WHERE qi.reference_name = wo.name AND qi.docstatus = 1) AS qi_count,
            (SELECT qi2.status FROM `tabQuality Inspection` qi2
             WHERE qi2.reference_name = wo.name AND qi2.docstatus = 1
             ORDER BY qi2.report_date DESC LIMIT 1) AS qi_status
        FROM `tabWork Order` wo
        WHERE wo.docstatus IN (0, 1)
            AND {where}
        ORDER BY wo.planned_start_date DESC
    """.format(where=where_clause), values, as_dict=True)

    return columns, data
'''

PRODUCTION_SUMMARY_JS = """
frappe.query_reports["Production Batch Summary"] = {
    filters: [
        {
            fieldname: "production_stage",
            label: __("Stage"),
            fieldtype: "Select",
            options: "\\nStock Solution Prep\\nMedia Preparation\\nFormulation Mixing\\nFlask Inoculation\\nPBR 25L Cultivation\\nPBR 275L Cultivation\\nPBR 925L Cultivation\\nPBR 6600L Production\\nHarvesting\\nDrying\\nPacking",
        },
        {
            fieldname: "status",
            label: __("Status"),
            fieldtype: "Select",
            options: "\\nDraft\\nNot Started\\nIn Process\\nCompleted\\nStopped\\nCancelled",
        },
        {
            fieldname: "from_date",
            label: __("From Date"),
            fieldtype: "Date",
            default: frappe.datetime.add_months(frappe.datetime.get_today(), -1),
        },
        {
            fieldname: "to_date",
            label: __("To Date"),
            fieldtype: "Date",
            default: frappe.datetime.get_today(),
        },
    ]
};
"""

# ── Report definitions ──
CUSTOM_REPORTS = [
    {
        "name": "Batch Genealogy",
        "ref_doctype": "Stock Entry",
        "report_type": "Script Report",
        "report_script": BATCH_GENEALOGY_PY,
        "javascript": BATCH_GENEALOGY_JS,
    },
    {
        "name": "Stage-wise Yield Analysis",
        "ref_doctype": "Work Order",
        "report_type": "Script Report",
        "report_script": YIELD_ANALYSIS_PY,
        "javascript": YIELD_ANALYSIS_JS,
    },
    {
        "name": "Contamination Report",
        "ref_doctype": "Quality Inspection",
        "report_type": "Script Report",
        "report_script": CONTAMINATION_REPORT_PY,
        "javascript": CONTAMINATION_REPORT_JS,
    },
    {
        "name": "Vendor COA Compliance",
        "ref_doctype": "Purchase Invoice",
        "report_type": "Script Report",
        "report_script": VENDOR_COA_PY,
        "javascript": VENDOR_COA_JS,
    },
    {
        "name": "Production Batch Summary",
        "ref_doctype": "Work Order",
        "report_type": "Script Report",
        "report_script": PRODUCTION_SUMMARY_PY,
        "javascript": PRODUCTION_SUMMARY_JS,
    },
]


def setup_custom_reports():
    print("\n── 4.2 Custom Reports ──")

    created = 0
    skipped = 0

    for rpt_def in CUSTOM_REPORTS:
        rpt_name = rpt_def["name"]

        if frappe.db.exists("Report", rpt_name):
            print(f"  ⏭  Report: {rpt_name} (already exists)")
            skipped += 1
            continue

        try:
            doc = frappe.get_doc({
                "doctype": "Report",
                "report_name": rpt_name,
                "ref_doctype": rpt_def["ref_doctype"],
                "report_type": rpt_def["report_type"],
                "is_standard": "No",
                "module": "Pluviago",
                "report_script": rpt_def.get("report_script", ""),
                "javascript": rpt_def.get("javascript", ""),
                "query": rpt_def.get("query", ""),
                "disabled": 0,
                "roles": [{"role": "System Manager"}],
            })
            doc.insert(ignore_permissions=True)
            print(f"  ✅ Report: {rpt_name} ({rpt_def['report_type']} → {rpt_def['ref_doctype']})")
            created += 1
        except Exception as e:
            print(f"  ❌ Report: {rpt_name} — {str(e)[:120]}")
            skipped += 1

    print(f"\n  📊 Reports: {created} created, {skipped} skipped")
