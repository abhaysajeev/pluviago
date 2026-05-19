
"""
Stock lineage API for the /stock-lineage page.

Three whitelisted endpoints:
- get_kpi_snapshot()   — single-shot counts for the KPI strip
- search_batches(q)    — autocomplete across all seven stock doctypes
- get_lineage(dt, n)   — bi-directional lineage payload for one batch

Lane order across the page (left to right):
    RMB → SSB → MED → FMB → PB → HB → EB
"""
import frappe
from frappe.utils import add_days, today


# ---------------------------------------------------------------------------
# Lane configuration
# ---------------------------------------------------------------------------

LANES = ["RMB", "SSB", "MED", "FMB", "PB", "HB", "EB"]

DT_TO_LANE = {
    "Raw Material Batch":   "RMB",
    "Stock Solution Batch": "SSB",
    "Medium Batch":         "MED",
    "Final Medium Batch":   "FMB",
    "Production Batch":     "PB",
    "Harvest Batch":        "HB",
    "Extraction Batch":     "EB",
}

LANE_TO_DT = {v: k for k, v in DT_TO_LANE.items()}


# ---------------------------------------------------------------------------
# KPI snapshot
# ---------------------------------------------------------------------------

@frappe.whitelist()
def get_kpi_snapshot():
    """Counts that populate the KPI strip. One query per tile to keep it readable."""
    soon = add_days(today(), 30)

    def _count(doctype, filters):
        return frappe.db.count(doctype, filters=filters)

    return {
        "approved_rmbs": _count("Raw Material Batch", {"qc_status": "Approved", "docstatus": 1}),
        "near_expiry_rmbs": frappe.db.sql("""
            SELECT COUNT(*) FROM `tabRaw Material Batch`
            WHERE qc_status='Approved' AND docstatus=1
              AND expiry_date IS NOT NULL AND expiry_date <= %s
              AND (remaining_qty IS NULL OR remaining_qty > 0)
        """, soon)[0][0],
        "ssbs_released": _count("Stock Solution Batch", {"preparation_status": "Released"}),
        "media_in_prep": _count("Medium Batch", {"preparation_status": ["in", ["Draft", "QC Pending"]]}),
        "fmbs_ready": _count("Final Medium Batch", {"status": "Approved"}),
        "active_pbs": _count("Production Batch", {"status": ["not in", ["Harvested", "Disposed"]]}),
        "harvests_30d": frappe.db.sql("""
            SELECT COUNT(*) FROM `tabHarvest Batch` WHERE creation >= %s
        """, add_days(today(), -30))[0][0],
        "extractions_30d": frappe.db.sql("""
            SELECT COUNT(*) FROM `tabExtraction Batch` WHERE creation >= %s
        """, add_days(today(), -30))[0][0],
    }


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

# Per-doctype config: which fields to query and what to show as the label.
_SEARCH_DTS = [
    ("Raw Material Batch",   "material_name",  ["name", "material_name", "qc_status"]),
    ("Stock Solution Batch", "solution_type",  ["name", "solution_type", "preparation_status"]),
    ("Medium Batch",         "medium_type",    ["name", "medium_type", "preparation_status"]),
    ("Final Medium Batch",   None,             ["name", "status"]),
    ("Production Batch",     "strain",         ["name", "strain", "current_stage"]),
    ("Harvest Batch",        "production_batch", ["name", "production_batch", "status"]),
    ("Extraction Batch",     "harvest_batch",  ["name", "harvest_batch", "status"]),
]


@frappe.whitelist()
def search_batches(query, limit=15):
    """Autocomplete across all seven stock doctypes.

    Matches on `name` LIKE '%query%' OR `label_field` LIKE '%query%' per doctype.
    Returns a flat list sorted by lane order then name.
    """
    query = (query or "").strip()
    if len(query) < 2:
        return []

    pattern = f"%{query}%"
    limit = int(limit)
    results = []

    for doctype, label_field, fields in _SEARCH_DTS:
        if label_field:
            filters = [["name", "like", pattern]]
            rows_by_name = frappe.db.get_all(doctype, filters=filters, fields=fields, limit=limit)
            rows_by_label = frappe.db.get_all(
                doctype, filters=[[label_field, "like", pattern]], fields=fields, limit=limit
            )
            # de-dup by name
            seen = {r["name"]: r for r in rows_by_name}
            for r in rows_by_label:
                seen.setdefault(r["name"], r)
            rows = list(seen.values())
        else:
            rows = frappe.db.get_all(doctype, filters=[["name", "like", pattern]],
                                     fields=fields, limit=limit)

        lane = DT_TO_LANE[doctype]
        for r in rows:
            label = r.get(label_field) if label_field else ""
            results.append({
                "doctype": doctype,
                "name":    r["name"],
                "lane":    lane,
                "label":   label or "",
                "status":  r.get("status") or r.get("qc_status") or r.get("preparation_status")
                           or r.get("current_stage") or "",
            })

    results.sort(key=lambda x: (LANES.index(x["lane"]), x["name"]))
    return results[:limit]


# ---------------------------------------------------------------------------
# Lineage
# ---------------------------------------------------------------------------

@frappe.whitelist()
def get_lineage(doctype, name):
    """Full bi-directional lineage payload for one batch."""
    if doctype not in DT_TO_LANE:
        frappe.throw(f"Unsupported doctype: {doctype}")
    if not frappe.db.exists(doctype, name):
        frappe.throw(f"{doctype} <b>{name}</b> not found.")

    focal_card = _card(doctype, name, is_focal=True)

    up_nodes, up_edges = _walk(doctype, name, "up")
    down_nodes, down_edges = _walk(doctype, name, "down")

    lanes = {lane: [] for lane in LANES}
    lanes[DT_TO_LANE[doctype]].append(focal_card)

    for lane, items in up_nodes.items():
        for dt, n in items:
            lanes[lane].append(_card(dt, n))
    for lane, items in down_nodes.items():
        for dt, n in items:
            lanes[lane].append(_card(dt, n))

    # Stable sort inside each lane by name so order is deterministic
    for lane in lanes:
        lanes[lane].sort(key=lambda c: (not c.get("is_focal"), c["name"]))

    return {
        "focal":  focal_card,
        "lanes":  lanes,
        "edges":  up_edges + down_edges,
        "log":    _consumption_log(doctype, name),
    }


# ---------------------------------------------------------------------------
# Traversal
# ---------------------------------------------------------------------------

def _walk(start_dt, start_name, direction):
    """BFS in one direction. Returns ({lane: [(dt, name), ...]}, edges).
    Starting node is NOT included in the result."""
    assert direction in ("up", "down")
    queue = [(start_dt, start_name)]
    seen = {(start_dt, start_name)}
    nodes_by_lane = {lane: [] for lane in LANES}
    edges = []

    step = _parents_of if direction == "up" else _children_of

    while queue:
        current_dt, current_name = queue.pop(0)
        for next_dt, next_name, qty, uom in step(current_dt, current_name):
            if direction == "down":
                edges.append({"from_dt": current_dt, "from_name": current_name,
                              "to_dt": next_dt, "to_name": next_name,
                              "qty": qty, "uom": uom})
            else:
                edges.append({"from_dt": next_dt, "from_name": next_name,
                              "to_dt": current_dt, "to_name": current_name,
                              "qty": qty, "uom": uom})

            key = (next_dt, next_name)
            if key not in seen:
                seen.add(key)
                nodes_by_lane[DT_TO_LANE[next_dt]].append(key)
                queue.append(key)

    return nodes_by_lane, edges


def _parents_of(doctype, name):
    """Immediate upstream nodes: list of (dt, name, edge_qty, edge_uom)."""
    if doctype == "Stock Solution Batch":
        rows = frappe.db.sql("""
            SELECT raw_material_batch AS rn, qty, uom
            FROM `tabStock Solution Ingredient`
            WHERE parent=%s AND parenttype='Stock Solution Batch'
              AND raw_material_batch IS NOT NULL AND raw_material_batch != ''
        """, name, as_dict=True)
        return [("Raw Material Batch", r.rn, r.qty, r.uom) for r in rows]

    if doctype == "Medium Batch":
        ssb_rows = frappe.db.sql("""
            SELECT stock_solution_batch AS rn, volume_used_ml
            FROM `tabMedium SSB Usage`
            WHERE parent=%s AND parenttype='Medium Batch'
              AND stock_solution_batch IS NOT NULL AND stock_solution_batch != ''
        """, name, as_dict=True)
        rmb_rows = frappe.db.sql("""
            SELECT raw_material_batch AS rn, quantity, uom
            FROM `tabMedium Direct Ingredient`
            WHERE parent=%s AND parenttype='Medium Batch'
              AND raw_material_batch IS NOT NULL AND raw_material_batch != ''
        """, name, as_dict=True)
        return (
            [("Stock Solution Batch", r.rn, r.volume_used_ml, "mL") for r in ssb_rows]
            + [("Raw Material Batch", r.rn, r.quantity, r.uom) for r in rmb_rows]
        )

    if doctype == "Final Medium Batch":
        fmb = frappe.db.get_value(
            "Final Medium Batch", name,
            ["green_medium_batch", "red_medium_batch",
             "green_medium_volume", "red_medium_volume"],
            as_dict=True,
        ) or {}
        parents = []
        if fmb.get("green_medium_batch"):
            parents.append(("Medium Batch", fmb.green_medium_batch,
                            fmb.get("green_medium_volume"), "L"))
        if fmb.get("red_medium_batch"):
            parents.append(("Medium Batch", fmb.red_medium_batch,
                            fmb.get("red_medium_volume"), "L"))
        return parents

    if doctype == "Production Batch":
        pb = frappe.db.get_value(
            "Production Batch", name,
            ["final_medium_batch", "medium_volume_used", "parent_batch"],
            as_dict=True,
        ) or {}
        parents = []
        if pb.get("final_medium_batch"):
            parents.append(("Final Medium Batch", pb.final_medium_batch,
                            pb.get("medium_volume_used"), "L"))
        # parent_batch (inoculum source) is self-lineage; render as an extra PB edge
        if pb.get("parent_batch"):
            parents.append(("Production Batch", pb.parent_batch, None, None))
        return parents

    if doctype == "Harvest Batch":
        pb = frappe.db.get_value("Harvest Batch", name, "production_batch")
        return [("Production Batch", pb, None, None)] if pb else []

    if doctype == "Extraction Batch":
        hb = frappe.db.get_value("Extraction Batch", name, "harvest_batch")
        return [("Harvest Batch", hb, None, None)] if hb else []

    return []  # Raw Material Batch has no upstream nodes in pluviago


def _children_of(doctype, name):
    """Immediate downstream nodes: list of (dt, name, edge_qty, edge_uom)."""
    if doctype == "Raw Material Batch":
        ssb_rows = frappe.db.sql("""
            SELECT parent AS rn, qty, uom
            FROM `tabStock Solution Ingredient`
            WHERE raw_material_batch=%s AND parenttype='Stock Solution Batch'
        """, name, as_dict=True)
        mb_rows = frappe.db.sql("""
            SELECT parent AS rn, quantity, uom
            FROM `tabMedium Direct Ingredient`
            WHERE raw_material_batch=%s AND parenttype='Medium Batch'
        """, name, as_dict=True)
        return (
            [("Stock Solution Batch", r.rn, r.qty, r.uom) for r in ssb_rows]
            + [("Medium Batch", r.rn, r.quantity, r.uom) for r in mb_rows]
        )

    if doctype == "Stock Solution Batch":
        rows = frappe.db.sql("""
            SELECT parent AS rn, volume_used_ml
            FROM `tabMedium SSB Usage`
            WHERE stock_solution_batch=%s AND parenttype='Medium Batch'
        """, name, as_dict=True)
        return [("Medium Batch", r.rn, r.volume_used_ml, "mL") for r in rows]

    if doctype == "Medium Batch":
        mt = frappe.db.get_value("Medium Batch", name, "medium_type")
        link_field = "green_medium_batch" if mt == "Green" else "red_medium_batch"
        vol_field = "green_medium_volume" if mt == "Green" else "red_medium_volume"
        rows = frappe.db.sql(f"""
            SELECT name AS rn, {vol_field} AS vol
            FROM `tabFinal Medium Batch`
            WHERE {link_field}=%s
        """, name, as_dict=True)
        return [("Final Medium Batch", r.rn, r.vol, "L") for r in rows]

    if doctype == "Final Medium Batch":
        rows = frappe.db.sql("""
            SELECT name AS rn, medium_volume_used
            FROM `tabProduction Batch`
            WHERE final_medium_batch=%s
        """, name, as_dict=True)
        return [("Production Batch", r.rn, r.medium_volume_used, "L") for r in rows]

    if doctype == "Production Batch":
        hb_rows = frappe.db.sql("""
            SELECT name AS rn FROM `tabHarvest Batch` WHERE production_batch=%s
        """, name, as_dict=True)
        # Child production batches (next inoculum generation)
        child_pb_rows = frappe.db.sql("""
            SELECT name AS rn FROM `tabProduction Batch` WHERE parent_batch=%s
        """, name, as_dict=True)
        return (
            [("Harvest Batch", r.rn, None, None) for r in hb_rows]
            + [("Production Batch", r.rn, None, None) for r in child_pb_rows]
        )

    if doctype == "Harvest Batch":
        rows = frappe.db.sql("""
            SELECT name AS rn FROM `tabExtraction Batch` WHERE harvest_batch=%s
        """, name, as_dict=True)
        return [("Extraction Batch", r.rn, None, None) for r in rows]

    return []  # Extraction Batch is terminal


# ---------------------------------------------------------------------------
# Card details + consumption log
# ---------------------------------------------------------------------------

# Per-doctype: (label_field, qty_field, qty_uom, status_field)
_CARD_SHAPE = {
    "Raw Material Batch":   ("material_name",   "remaining_qty",      "received_qty_uom", "qc_status"),
    "Stock Solution Batch": ("solution_type",   "available_volume",   None,               "preparation_status"),
    "Medium Batch":         ("medium_type",     "remaining_volume",   None,               "preparation_status"),
    "Final Medium Batch":   (None,              "remaining_volume",   None,               "status"),
    "Production Batch":     ("strain",          "medium_volume_used", None,               "current_stage"),
    "Harvest Batch":        ("production_batch", "actual_dry_weight", None,               "status"),
    "Extraction Batch":     ("harvest_batch",   None,                 None,               "status"),
}


def _card(doctype, name, is_focal=False):
    """One card-shaped dict for the lane grid."""
    label_field, qty_field, qty_uom_field, status_field = _CARD_SHAPE[doctype]

    fields = ["name"]
    for f in (label_field, qty_field, qty_uom_field, status_field):
        if f and f not in fields:
            fields.append(f)
    # Always include expiry_date when present on the doctype, so the card can flag near-expiry
    if doctype in ("Raw Material Batch", "Stock Solution Batch", "Medium Batch", "Final Medium Batch"):
        fields.append("expiry_date")

    row = frappe.db.get_value(doctype, name, fields, as_dict=True) or {}

    qty_val = row.get(qty_field) if qty_field else None
    if qty_field == "remaining_volume" and qty_val is None:
        # Pre-consumption: fall back to capacity so the card isn't blank
        for fb in ("medium_volume_calculated", "actual_final_volume", "final_required_volume"):
            if doctype in ("Medium Batch", "Final Medium Batch"):
                qty_val = frappe.db.get_value(doctype, name, fb)
                if qty_val is not None:
                    break

    uom = None
    if qty_uom_field:
        uom = row.get(qty_uom_field)
    elif doctype == "Stock Solution Batch":
        uom = "L"
    elif doctype in ("Medium Batch", "Final Medium Batch", "Production Batch"):
        uom = "L"
    elif doctype == "Harvest Batch":
        uom = "kg"

    return {
        "doctype":     doctype,
        "name":        name,
        "lane":        DT_TO_LANE[doctype],
        "label":       row.get(label_field) if label_field else "",
        "qty":         qty_val,
        "uom":         uom,
        "status":      row.get(status_field) or "",
        "expiry_date": str(row["expiry_date"]) if row.get("expiry_date") else None,
        "is_focal":    bool(is_focal),
    }


def _consumption_log(doctype, name, limit=50):
    """Stock Consumption Log entries relevant to this batch.

    For RMB: every row where raw_material_batch = name.
    For all other doctypes: every row where the focal batch is the source_document
    (i.e. this batch is the one that triggered the consumption).
    """
    if doctype == "Raw Material Batch":
        rows = frappe.db.sql("""
            SELECT creation, qty_change, uom, balance_after, action,
                   source_doctype, source_document, performed_by, remarks
            FROM `tabStock Consumption Log`
            WHERE raw_material_batch=%s
            ORDER BY creation DESC
            LIMIT %s
        """, (name, int(limit)), as_dict=True)
    else:
        rows = frappe.db.sql("""
            SELECT creation, qty_change, uom, balance_after, action,
                   source_doctype, source_document, raw_material_batch,
                   material_name, performed_by, remarks
            FROM `tabStock Consumption Log`
            WHERE source_doctype=%s AND source_document=%s
            ORDER BY creation DESC
            LIMIT %s
        """, (doctype, name, int(limit)), as_dict=True)

    for r in rows:
        r["creation"] = str(r["creation"]) if r.get("creation") else None
    return rows
