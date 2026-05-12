/**
 * Pluviago — Load Formula dialog utility
 *
 * Provides pluviago.add_load_formula_button(frm, cfg) where cfg is:
 *   applies_to       — "Stock Solution Batch" / "Green Medium Batch" / "Red Medium Batch"
 *   volume_field     — field name on frm.doc holding the target volume (e.g. "target_volume")
 *   child_table      — child table fieldname to populate (e.g. "ingredients" / "direct_chemicals")
 *   qty_fieldname    — field on the child row for quantity (e.g. "qty" / "quantity")
 */
window.pluviago = window.pluviago || {};

pluviago.add_load_formula_button = function (frm, cfg) {
    if (frm.doc.docstatus !== 0 || frm.doc.preparation_status !== 'Draft') return;

    frm.add_custom_button(__('Load Formula'), function () {
        _pick_formula_dialog(frm, cfg);
    }, __('Actions'));
};

function _pick_formula_dialog(frm, cfg) {
    const d = new frappe.ui.Dialog({
        title: __('Load Preparation Formula'),
        fields: [
            {
                label: __('Formula'),
                fieldname: 'formula',
                fieldtype: 'Link',
                options: 'Preparation Formula',
                filters: { applies_to: cfg.applies_to },
                reqd: 1,
                description: __('Only formulas matching this document type are shown.'),
            },
            {
                label: __('Formula Reference'),
                fieldname: 'ref_hint',
                fieldtype: 'Data',
                read_only: 1,
                description: __('UOM and target volume auto-set from the formula when selected.'),
            },
            {
                fieldtype: 'Column Break',
            },
            {
                label: __('Target Volume'),
                fieldname: 'target_volume',
                fieldtype: 'Float',
                default: frm.doc[cfg.volume_field] || '',
                reqd: 1,
                description: __('Quantities are scaled proportionally. You can use mL or L — the system converts automatically.'),
            },
            {
                label: __('UOM'),
                fieldname: 'target_volume_uom',
                fieldtype: 'Link',
                options: 'UOM',
                default: (cfg.volume_uom_field && frm.doc[cfg.volume_uom_field]) || 'mL',
                reqd: 1,
            },
        ],
        primary_action_label: __('Next: Select Batches'),
        primary_action(values) {
            d.hide();
            frappe.call({
                method: 'pluviago.pluviago_biotech.doctype.preparation_formula.preparation_formula.get_formula_with_batches',
                args: {
                    formula_name: values.formula,
                    target_volume: values.target_volume,
                    target_volume_uom: values.target_volume_uom,
                },
                freeze: true,
                freeze_message: __('Fetching available stock batches...'),
                callback(r) {
                    if (r.message) {
                        _batch_selection_dialog(frm, r.message, cfg, values.target_volume);
                    }
                },
            });
        },
    });
    d.show();

    // Fetch reference_volume + UOM from a validated formula name and apply to dialog fields.
    // Called directly (not via trigger) so it always runs after the Link field resolves.
    function _apply_formula_meta(formula_name) {
        if (!formula_name) return;
        frappe.db.get_value(
            'Preparation Formula',
            formula_name,                                    // exact name — Link-field validated
            ['reference_volume', 'reference_volume_uom'],
            function (r) {
                if (!r || !r.reference_volume) return;
                const ref_vol = r.reference_volume;
                const ref_uom = r.reference_volume_uom || 'mL';
                d.set_value('ref_hint', `${ref_vol} ${ref_uom}`);
                d.set_value('target_volume_uom', ref_uom);
                if (!d.get_value('target_volume')) {
                    d.set_value('target_volume', ref_vol);
                }
            }
        );
    }

    // Auto-populate formula from solution_type already on the form,
    // then call _apply_formula_meta directly — no trigger() needed.
    const solution_type = cfg.solution_type_field && frm.doc[cfg.solution_type_field];
    if (solution_type) {
        frappe.db.get_list('Preparation Formula', {
            filters: { solution_type: solution_type, applies_to: cfg.applies_to },
            fields: ['name'],
            limit: 1,
        }).then(rows => {
            if (rows && rows.length) {
                d.set_value('formula', rows[0].name);
                _apply_formula_meta(rows[0].name);
            }
        });
    }

    // When user manually picks a formula via the Link field dropdown
    d.fields_dict.formula.$input.on('awesomplete-selectcomplete', function () {
        _apply_formula_meta(d.get_value('formula'));
    });
}

function _batch_selection_dialog(frm, formula_data, cfg, target_volume) {
    const items = formula_data.items;

    const rows_html = items.map((item, idx) => {
        let cell;
        if (!item.available_batches.length) {
            cell = `<span class="text-danger" style="font-size:12px">
                        ⚠ No approved stock available
                    </span>`;
        } else {
            const opts = item.available_batches.map(b => {
                const exp = b.expiry_date
                    ? ` | Exp: ${frappe.datetime.str_to_user(b.expiry_date)}`
                    : '';
                const batch_label = b.supplier_batch_no || b.name;
                return `<option value="${b.name}">${batch_label} | ${b.remaining_qty} ${b.received_qty_uom}${exp}</option>`;
            }).join('');
            cell = `<select class="form-control form-control-sm rmb-select" data-idx="${idx}">
                        <option value="">— select batch —</option>
                        ${opts}
                    </select>`;
        }
        return `<tr>
                    <td style="vertical-align:middle">${frappe.utils.escape_html(item.material_name)}</td>
                    <td style="vertical-align:middle;text-align:right">${item.quantity}</td>
                    <td style="vertical-align:middle">${frappe.utils.escape_html(item.uom || '')}</td>
                    <td style="vertical-align:middle;min-width:280px">${cell}</td>
                </tr>`;
    }).join('');

    const table_html = `
        <div style="overflow-x:auto">
            <table class="table table-bordered" style="margin:0;font-size:13px">
                <thead style="background:#f5f5f5">
                    <tr>
                        <th>Ingredient</th>
                        <th style="text-align:right">Qty</th>
                        <th>UOM</th>
                        <th>Select Batch from Stock</th>
                    </tr>
                </thead>
                <tbody>${rows_html}</tbody>
            </table>
        </div>
        <p class="text-muted" style="margin-top:8px;font-size:12px">
            You can change batch selections after loading. Rows with no stock available can be filled in manually.
        </p>`;

    const d = new frappe.ui.Dialog({
        title: __('Select Batches — {0}', [formula_data.formula_name]),
        fields: [{ fieldtype: 'HTML', fieldname: 'tbl', options: table_html }],
        size: 'large',
        primary_action_label: __('Load into Form'),
        primary_action() {
            const selections = {};
            d.$wrapper.find('.rmb-select').each(function () {
                selections[$(this).data('idx')] = $(this).val();
            });

            const existing_rows = (frm.doc[cfg.child_table] || []).filter(r => r.item_code);
            if (existing_rows.length) {
                frappe.confirm(
                    __('This will replace {0} existing ingredient row(s). Continue?', [existing_rows.length]),
                    () => _apply_rows(frm, items, selections, cfg, d, target_volume)
                );
            } else {
                _apply_rows(frm, items, selections, cfg, d, target_volume);
            }
        },
    });
    d.show();
}

function _apply_rows(frm, items, selections, cfg, dialog, target_volume) {
    frm.clear_table(cfg.child_table);
    items.forEach((item, idx) => {
        const row = frm.add_child(cfg.child_table);
        row.item_code = item.item_code;
        row.item_name = item.material_name;
        row[cfg.qty_fieldname] = item.quantity;
        row.uom = item.uom;
        row.raw_material_batch = selections[idx] || '';
        if (cfg.child_table === 'direct_chemicals') {
            row.chemical_name = item.material_name;
        }
    });
    if (target_volume && cfg.volume_field) {
        frm.set_value(cfg.volume_field, target_volume);
    }
    frm.refresh_field(cfg.child_table);
    dialog.hide();
    frappe.show_alert({
        message: __('Formula loaded — review quantities and confirm batch selections.'),
        indicator: 'green',
    });
}
