# Pluviago — Change Log

## 2026-04-06: PR → RMB Auto-Creation Workflow

### Problem
Creating a Purchase Order, Purchase Receipt, and then manually creating Raw Material Batches
with the same data (supplier, item, qty, warehouse) felt like duplicate work. Users had to
enter the same information twice.

### Solution
Added a one-click "Create Raw Material Batches" button on submitted Purchase Receipts that
auto-generates Draft RMBs for all CHEM items, pre-filling all fields from the PR data.

### Files Changed

| File | Change |
|------|--------|
| `pluviago/patches/v1_0/add_pr_pharma_fields.py` | **[NEW]** Patch to add 4 custom fields to Purchase Receipt Item: `custom_supplier_batch_no`, `custom_mfg_date`, `custom_expiry_date`, `custom_storage_condition` |
| `pluviago/pluviago_biotech/overrides/purchase_receipt.py` | **[NEW]** Whitelisted `create_raw_material_batches()` function that creates Draft RMBs from PR data |
| `pluviago/pluviago_biotech/overrides/purchase_receipt.js` | **[NEW]** Client script that: hides ~40 irrelevant accounting/serial/asset fields from PR Item table, adds "Create Raw Material Batches" button |
| `pluviago/hooks.py` | **[MODIFIED]** Added `doctype_js` entry for Purchase Receipt |
| `pluviago/patches.txt` | **[MODIFIED]** Registered `add_pr_pharma_fields` patch |

### New User Flow

```
Purchase Order
    ↓
Purchase Receipt (fill Supplier Batch No, Mfg Date, Expiry Date, Storage Condition)
    ↓   Submit
Click "Actions → Create Raw Material Batches"
    ↓   (one click — creates Draft RMBs for all CHEM items)
QC Manager creates Chemical COA → reviews vendor COA → submits COA
    ↓   (auto-ticks coa_verified on RMB)
QC Manager sets qc_status = Approved on RMB → Submit
    ↓
Material available for Stock Solution / Medium preparation
```

### Old Flow (for comparison)

```
PO → PR → Submit → Then MANUALLY create each RMB (re-enter supplier, item, qty, etc.)
```

### Custom Fields Added to Purchase Receipt Item

| Field Name | Type | Purpose |
|------------|------|---------|
| `custom_supplier_batch_no` | Data | Vendor's batch number from label/COA |
| `custom_mfg_date` | Date | Manufacturing date from vendor |
| `custom_expiry_date` | Date | Expiry date from vendor |
| `custom_storage_condition` | Select | RT / 2-8C / -20C / 4C |

### Fields Hidden from PR Item Table

~40 fields hidden including: all accounting fields (base_rate, net_rate, valuation_rate, etc.),
serial/batch bundle fields, asset fields, weight fields, subcontract fields, and misc references.
Only procurement-relevant fields remain visible: item_code, qty, uom, rate, amount, warehouse,
and the 4 new pharma fields.

### Technical Notes

- RMBs are created in **Draft** mode — they cannot be used in production until QC approves
- Duplicate prevention: button checks if an RMB already exists for the same PR + item_code + supplier_batch_no
- Only items with `item_code` starting with "CHEM" are processed (non-chemical items are skipped)
- The PR's ERPNext stock ledger entry is unaffected — this is purely an overlay
- Custom fields use Frappe's `create_custom_fields()` API (not raw SQL), so they survive migrations

## 2026-04-06: Simplified QC & Improved AVL Schema

### Problem
1. **Validations too heavy:** Creating a full `Chemical COA` document was mandatory just to set the `coa_verified` flag on the `Raw Material Batch`, which was tedious for simple visual checks.
2. **AVL Data Duplication:** `Approved Vendor` previously mapped 1-to-1 with a chemical. If a vendor was approved for 15 chemicals, the user had to create 15 separate qualification records.

### Solution
1. **Optional QC COA:** Loosened the validation on `Raw Material Batch`. The `coa_verified` flag can now be ticked completely manually. The standalone `Chemical COA` document is now optional for when operators actually want to log specific test readings.
2. **AVL Child Table (1 to N):** Introduced a new `Approved Vendor Item` child table inside the `Approved Vendor` DocType. A single Approved Vendor record can now host an unlimited list of approved items.

### Files Changed

| File | Change |
|------|--------|
| `pluviago/pluviago_biotech/doctype/raw_material_batch/raw_material_batch.py` | **[MODIFIED]** Removed the hardcoded message forcing users to attach a COA document. |
| `pluviago/setup/update_avl.py` | **[NEW]** Setup script that created `Approved Vendor Item` child table, attached it to AVL, migrated existing 1-to-1 data into 1-to-N, and hid legacy deprecated fields. |
| `pluviago/pluviago_biotech/overrides/purchase_order.py` | **[MODIFIED]** Changed validation query to use Frappe SQL with a `JOIN` to check the `tabApproved Vendor Item` child table. |
| `pluviago/test_flow.py` | **[MODIFIED]** Updated integration tests to insert AVLs using the child table property `approved_items`. |

## 2026-04-07: Item-Group Detection, In-house Raw Materials, Hard-Block AVL Validation

### Problems
1. **Naming-convention fragility:** All raw material detection relied on `item_code.startswith("CHEM")`. Changing the naming series or adding a new chemical prefix would silently break AVL checks and PR→RMB creation.
2. **DI Water not trackable:** Client requirement — DI Water is prepared in-house (no PO, no vendor, no COA), but consumption must be tracked exactly like purchased chemicals. Previously the system had no way to handle non-purchased raw materials.
3. **AVL validation was a warning:** When a supplier was not on the Approved Vendor List for a raw material, the PO showed a `msgprint` warning — users could dismiss and proceed.
4. **AVL `Approved Vendor Item` was a Custom Field:** Created via `update_avl.py` using `create_custom_fields()`. Custom fields are erased when the DocType cache is rebuilt or `bench clear-cache` is run, making the child table non-durable across deployments.

### Solutions
1. **Item-group-based detection:** Central source of truth in `item_utils.py`. Raw materials are identified by their ERPNext Item Group (`Base Salts`, `Trace Elements`, `Nutrients`, `Vitamins` = purchased; `Lab Consumables` = in-house). Zero dependency on item code naming.
2. **`batch_source` field on Raw Material Batch:** New Select field (`Purchased` / `In-house`, default `Purchased`). Purchased batches require supplier + supplier_batch_no + expiry_date + coa_verified at submit. In-house batches only require qc_status = Approved.
3. **Hard-block on PO:** `frappe.throw()` replaces `frappe.msgprint()` — PO cannot be submitted if any raw material item has an unapproved or expired vendor qualification.
4. **Proper DocType for `Approved Vendor Item`:** Replaced the custom-field approach with a real app DocType (`approved_vendor_item/`) with a JSON schema file. Survives `bench migrate`, `bench clear-cache`, and fresh deployments. `material_name` auto-populates via `fetch_from: "item_code.item_name"`.

### Files Changed

| File | Change |
|------|--------|
| `pluviago/pluviago_biotech/utils/item_utils.py` | **[NEW]** Central module defining `PURCHASED_RAW_MATERIAL_GROUPS`, `IN_HOUSE_RAW_MATERIAL_GROUPS`, `ALL_TRACKABLE_GROUPS` frozensets and `get_item_groups(item_codes)` batched query helper |
| `pluviago/pluviago_biotech/doctype/approved_vendor_item/approved_vendor_item.json` | **[NEW]** Proper app DocType for the AVL child table — `istable:1`, fields: `item_code` (Link→Item, reqd), `material_name` (Data, fetch_from, read_only) |
| `pluviago/pluviago_biotech/doctype/approved_vendor_item/approved_vendor_item.py` | **[NEW]** Minimal controller (`class ApprovedVendorItem(Document): pass`) |
| `pluviago/pluviago_biotech/doctype/approved_vendor/approved_vendor.json` | **[MODIFIED]** Legacy `item_code`/`material_name` fields hidden; `approved_items` Table field now a proper DocField (was custom); `supplier_name` added to list view |
| `pluviago/pluviago_biotech/overrides/purchase_order.py` | **[MODIFIED]** Replaced `startswith("CHEM")` with `get_item_groups()` + `PURCHASED_RAW_MATERIAL_GROUPS`; single batched SQL for AVL check; `frappe.throw()` hard-block |
| `pluviago/pluviago_biotech/overrides/purchase_receipt.py` | **[MODIFIED]** Replaced `startswith("CHEM")` with `get_item_groups()` + `PURCHASED_RAW_MATERIAL_GROUPS`; all item groups fetched in one query before loop; sets `batch_source = "Purchased"` on created RMBs |
| `pluviago/pluviago_biotech/doctype/raw_material_batch/raw_material_batch.json` | **[MODIFIED]** Added `batch_source` Select field (Purchased/In-house, reqd, in_list_view); relaxed `supplier`, `supplier_batch_no`, `expiry_date` — no longer globally required |
| `pluviago/pluviago_biotech/doctype/raw_material_batch/raw_material_batch.py` | **[MODIFIED]** `on_submit` now conditional: QC Approved gate applies to all batches; supplier/COA/expiry gates apply only to `batch_source == "Purchased"` |
| `pluviago/pluviago_biotech/overrides/purchase_receipt.js` | **[MODIFIED]** Added "View Raw Material Batches" button on submitted PRs; added errors section to creation result dialog; removed redundant `onload` hook |
| `pluviago/tests/e2e_procurement_test.py` | **[NEW]** End-to-end test suite (45 assertions) covering: AVL schema, PO hard-block (item-group based), PR→RMB creation, Purchased RMB lifecycle, In-house RMB lifecycle (DI Water), PR link filter |

### New Raw Material Groups Recognized

| Item Group | Type | PO AVL Check | PR→RMB | Requires COA at Submit |
|------------|------|-------------|---------|----------------------|
| Base Salts | Purchased | ✅ | ✅ | ✅ |
| Trace Elements | Purchased | ✅ | ✅ | ✅ |
| Nutrients | Purchased | ✅ | ✅ | ✅ |
| Vitamins | Purchased | ✅ | ✅ | ✅ |
| Lab Consumables | In-house | ❌ (skipped) | ❌ (not via PR) | ❌ |

### In-house Raw Material Flow (DI Water example)

```
Store Keeper creates Raw Material Batch manually
    → batch_source = In-house
    → no supplier, no supplier_batch_no, no expiry_date required
    → received_qty = available volume (e.g. 200 L)
    ↓
QC checks and sets qc_status = Approved
    ↓
Submit RMB → status = Approved, remaining_qty = received_qty
    ↓
Material consumed via Stock Consumption Log (same as purchased chemicals)
```

### Technical Notes

- `get_item_groups()` uses a single `SELECT name, item_group FROM tabItem WHERE name IN (...)` — one DB hit per PO/PR regardless of item count
- `PURCHASED_RAW_MATERIAL_GROUPS` is a `frozenset` — O(1) membership check, immutable
- Adding a new raw material group requires only one line change in `item_utils.py`
- `bench migrate` automatically cleaned up the stale custom field for `approved_items` when the proper DocField was detected
