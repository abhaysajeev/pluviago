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
                label: __('Target Volume'),
                fieldname: 'target_volume',
                fieldtype: 'Float',
                default: frm.doc[cfg.volume_field] || '',
                reqd: 1,
                description: __('Ingredient quantities will be scaled proportionally from the formula reference volume.'),
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
                },
                freeze: true,
                freeze_message: __('Fetching available stock batches...'),
                callback(r) {
                    if (r.message) {
                        _batch_selection_dialog(frm, r.message, cfg);
                    }
                },
            });
        },
    });
    d.show();
}

function _batch_selection_dialog(frm, formula_data, cfg) {
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
                return `<option value="${b.name}">
                            ${b.name} &nbsp;|&nbsp; ${b.remaining_qty} ${b.received_qty_uom}${exp}
                        </option>`;
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
                    () => _apply_rows(frm, items, selections, cfg, d)
                );
            } else {
                _apply_rows(frm, items, selections, cfg, d);
            }
        },
    });
    d.show();
}

function _apply_rows(frm, items, selections, cfg, dialog) {
    frm.clear_table(cfg.child_table);
    items.forEach((item, idx) => {
        const row = frm.add_child(cfg.child_table);
        row.item_code = item.item_code;
        row[cfg.qty_fieldname] = item.quantity;
        row.uom = item.uom;
        row.raw_material_batch = selections[idx] || '';
        if (cfg.child_table === 'direct_chemicals') {
            row.chemical_name = item.material_name;
        }
    });
    frm.refresh_field(cfg.child_table);
    dialog.hide();
    frappe.show_alert({
        message: __('Formula loaded — review quantities and confirm batch selections.'),
        indicator: 'green',
    });
}
