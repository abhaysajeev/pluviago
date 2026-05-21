/**
 * Pluviago — Load Full Formula dialog for Medium Batch
 *
 * Provides pluviago.load_medium_formula(frm) which opens a two-step dialog:
 *   Step 1: Confirm target volume
 *   Step 2: Select RMB batches for base salts + SSB batches for stock solutions
 *
 * Populates both direct_chemicals and ssb_used child tables on the Medium Batch form.
 */
window.pluviago = window.pluviago || {};

pluviago.load_medium_formula = function (frm) {
    if (!frm.doc.medium_type) {
        frappe.msgprint({ message: __('Please select Medium Type first.'), indicator: 'orange' });
        return;
    }
    _step1_volume_dialog(frm);
};

function _step1_volume_dialog(frm) {
    const d = new frappe.ui.Dialog({
        title: __('Load Full Formula — {0} Medium', [frm.doc.medium_type]),
        fields: [
            {
                label: __('Target Volume (L)'),
                fieldname: 'target_volume',
                fieldtype: 'Float',
                default: frm.doc.final_required_volume || '',
                reqd: 1,
                description: __('All quantities will be scaled proportionally from SRS constants per litre.'),
            },
        ],
        primary_action_label: __('Next: Select Batches'),
        primary_action(values) {
            const tv = values.target_volume;
            // Keep form field in sync with what the dialog was told to scale for
            if (frm.doc.final_required_volume && frm.doc.final_required_volume !== tv) {
                frappe.show_alert({
                    message: __('Final Required Volume updated to {0} L to match the formula target.', [tv]),
                    indicator: 'blue',
                }, 5);
            }
            frm.set_value('final_required_volume', tv);
            d.hide();
            frappe.call({
                method: 'pluviago.pluviago_biotech.doctype.medium_batch.medium_batch.get_medium_formula',
                args: {
                    medium_type: frm.doc.medium_type,
                    target_volume: tv,
                },
                freeze: true,
                freeze_message: __('Fetching available batches...'),
                callback(r) {
                    if (r.message) {
                        _step2_batch_dialog(frm, r.message);
                    }
                },
            });
        },
    });
    d.show();
}

function _step2_batch_dialog(frm, data) {
    const { base_salts, stock_solutions, medium_type } = data;

    // ---- Base Salts Section ----
    const salt_rows = base_salts.map((item, idx) => {
        let batch_cell;
        if (!item.available_rmbs.length) {
            batch_cell = `<span class="text-danger" style="font-size:12px">⚠ No approved stock available</span>`;
        } else {
            const opts = item.available_rmbs.map(b => {
                const exp = b.expiry_date ? ` | Exp: ${frappe.datetime.str_to_user(b.expiry_date)}` : '';
                const label = b.material_name ? `${b.material_name} (${b.name})` : b.name;
                return `<option value="${b.name}">${label} | ${b.remaining_qty} ${b.received_qty_uom}${exp}</option>`;
            }).join('');
            batch_cell = `<select class="form-control form-control-sm salt-rmb-select" data-idx="${idx}">
                            <option value="">— select batch —</option>
                            ${opts}
                          </select>`;
        }
        const warn = item.available_rmbs.length === 0
            ? '' : '';
        return `<tr>
            <td style="vertical-align:middle">${frappe.utils.escape_html(item.chemical_name)}</td>
            <td style="vertical-align:middle;text-align:right">${item.scaled_qty}</td>
            <td style="vertical-align:middle">${item.uom}</td>
            <td style="vertical-align:middle;min-width:260px">${batch_cell}</td>
        </tr>`;
    }).join('');

    // ---- Stock Solutions Section ----
    const ssb_rows = stock_solutions.map((item, idx) => {
        let ssb_cell;
        if (!item.available_ssbs.length) {
            ssb_cell = `<span class="text-danger" style="font-size:12px">⚠ No approved SSB available</span>`;
        } else {
            const opts = item.available_ssbs.map(b => {
                const exp = b.expiry_date ? ` | Exp: ${frappe.datetime.str_to_user(b.expiry_date)}` : '';
                const vol_warn = b.remaining_ml < item.required_ml ? ' ⚠ LOW' : '';
                return `<option value="${b.name}">${b.name} | ${b.remaining_ml} mL${exp}${vol_warn}</option>`;
            }).join('');
            const vol_warn_cell = item.available_ssbs.every(b => b.remaining_ml < item.required_ml)
                ? `<div class="text-warning" style="font-size:11px;margin-top:2px">⚠ Available volume may be insufficient (${item.required_ml} mL needed)</div>`
                : '';
            ssb_cell = `<select class="form-control form-control-sm ssb-select" data-idx="${idx}">
                            <option value="">— select batch —</option>
                            ${opts}
                         </select>${vol_warn_cell}`;
        }
        return `<tr>
            <td style="vertical-align:middle">${frappe.utils.escape_html(item.solution_type)}</td>
            <td style="vertical-align:middle;text-align:right">${item.required_ml}</td>
            <td style="vertical-align:middle">mL</td>
            <td style="vertical-align:middle;min-width:260px">${ssb_cell}</td>
        </tr>`;
    }).join('');

    const table_html = `
        <h6 style="margin-bottom:6px;color:#555">Section A — Direct Ingredients (Base Salts &amp; DI Water)</h6>
        <div style="overflow-x:auto;margin-bottom:16px">
            <table class="table table-bordered" style="margin:0;font-size:13px">
                <thead style="background:#f0f4f0">
                    <tr>
                        <th>Chemical</th>
                        <th style="text-align:right">Qty</th>
                        <th>UOM</th>
                        <th>Select Raw Material Batch</th>
                    </tr>
                </thead>
                <tbody>${salt_rows}</tbody>
            </table>
        </div>
        <h6 style="margin-bottom:6px;color:#555">Section B — Stock Solution Additions</h6>
        <div style="overflow-x:auto">
            <table class="table table-bordered" style="margin:0;font-size:13px">
                <thead style="background:#f0f4f0">
                    <tr>
                        <th>Solution Type</th>
                        <th style="text-align:right">Volume (mL)</th>
                        <th>UOM</th>
                        <th>Select Stock Solution Batch</th>
                    </tr>
                </thead>
                <tbody>${ssb_rows}</tbody>
            </table>
        </div>
        <p class="text-muted" style="margin-top:8px;font-size:12px">
            Batch selections can be changed after loading. Rows with no stock available must be filled manually.
        </p>`;

    const d = new frappe.ui.Dialog({
        title: __('Select Batches — {0} Medium ({1} L)', [medium_type, data.target_volume]),
        fields: [{ fieldtype: 'HTML', fieldname: 'tbl', options: table_html }],
        size: 'extra-large',
        primary_action_label: __('Load into Form'),
        primary_action() {
            const salt_selections = {};
            d.$wrapper.find('.salt-rmb-select').each(function () {
                salt_selections[$(this).data('idx')] = $(this).val();
            });
            const ssb_selections = {};
            d.$wrapper.find('.ssb-select').each(function () {
                ssb_selections[$(this).data('idx')] = $(this).val();
            });

            const existing_chems = (frm.doc.direct_chemicals || []).filter(r => r.chemical_name).length;
            const existing_ssbs  = (frm.doc.ssb_used || []).filter(r => r.solution_type).length;
            const total_existing = existing_chems + existing_ssbs;

            // Guard: final_required_volume on the form must match the target this formula was scaled for
            const form_vol = frm.doc.final_required_volume;
            const formula_vol = data.target_volume;
            if (form_vol && Math.abs(form_vol - formula_vol) > 0.0001) {
                frappe.msgprint({
                    title: __('Volume Mismatch'),
                    message: __('The formula was scaled for <b>{0} L</b> but Final Required Volume on the form is <b>{1} L</b>. '
                        + 'Please reload the formula after correcting the volume.', [formula_vol, form_vol]),
                    indicator: 'red',
                });
                return;
            }

            if (total_existing > 0) {
                frappe.confirm(
                    __('This will replace {0} existing row(s) in the ingredient tables. Continue?', [total_existing]),
                    () => _apply_medium_rows(frm, base_salts, stock_solutions, salt_selections, ssb_selections, d)
                );
            } else {
                _apply_medium_rows(frm, base_salts, stock_solutions, salt_selections, ssb_selections, d);
            }
        },
    });
    d.show();
}

function _apply_medium_rows(frm, base_salts, stock_solutions, salt_selections, ssb_selections, dialog) {
    // Populate direct_chemicals (base salts)
    frm.clear_table('direct_chemicals');
    base_salts.forEach((item, idx) => {
        const row = frm.add_child('direct_chemicals');
        row.chemical_name = item.chemical_name;
        row.item_code = item.item_code || '';
        row.quantity = item.scaled_qty;
        row.uom = item.uom;
        row.raw_material_batch = salt_selections[idx] || '';
    });
    frm.refresh_field('direct_chemicals');

    // Populate ssb_used (stock solutions)
    frm.clear_table('ssb_used');
    stock_solutions.forEach((item, idx) => {
        const row = frm.add_child('ssb_used');
        row.solution_type = item.solution_type;
        row.volume_used_ml = item.required_ml;
        row.stock_solution_batch = ssb_selections[idx] || '';
    });
    frm.refresh_field('ssb_used');

    dialog.hide();
    frappe.show_alert({
        message: __('Full formula loaded — review quantities and confirm batch selections before marking preparation complete.'),
        indicator: 'green',
    });
}
