function calc_fmb_expiry(frm) {
    if (frm.doc.shelf_life_days && frm.doc.preparation_date) {
        frm.set_value('expiry_date',
            frappe.datetime.add_days(frm.doc.preparation_date, frm.doc.shelf_life_days));
    }
}

function fmb_load_formula(frm) {
    if (!frm.doc.final_required_volume) {
        frappe.msgprint({ message: __('Please enter Final Required Volume first.'), indicator: 'orange' });
        return;
    }

    const d1 = new frappe.ui.Dialog({
        title: __('Load Formula — Final Medium Batch'),
        fields: [
            {
                label: __('Target Volume (L)'),
                fieldname: 'target_volume',
                fieldtype: 'Float',
                default: frm.doc.final_required_volume || '',
                reqd: 1,
                description: __('Green Medium = 75%, Red Medium = 25% of target volume.'),
            },
        ],
        primary_action_label: __('Next: Select Medium Batches'),
        primary_action(values) {
            const tv = values.target_volume;
            if (frm.doc.final_required_volume && Math.abs(frm.doc.final_required_volume - tv) > 0.0001) {
                frappe.show_alert({
                    message: __('Final Required Volume updated to {0} L to match formula target.', [tv]),
                    indicator: 'blue',
                }, 5);
            }
            frm.set_value('final_required_volume', tv);
            d1.hide();
            frappe.call({
                method: 'pluviago.pluviago_biotech.doctype.final_medium_batch.final_medium_batch.get_fmb_formula',
                args: { target_volume: tv },
                freeze: true,
                freeze_message: __('Fetching available medium batches...'),
                callback(r) {
                    if (r.message) _fmb_select_dialog(frm, r.message);
                },
            });
        },
    });
    d1.show();
}

function _fmb_select_dialog(frm, data) {
    const { target_volume, green_volume, red_volume, green_batches, red_batches } = data;

    function batch_opts(batches, required_vol, select_id) {
        if (!batches.length) {
            return `<span class="text-danger" style="font-size:12px">⚠ No approved batches available</span>`;
        }
        const opts = batches.map(b => {
            const exp = b.expiry_date ? ` | Exp: ${frappe.datetime.str_to_user(b.expiry_date)}` : '';
            const rem = (b.remaining_volume || 0).toFixed(3);
            const low = (b.remaining_volume || 0) < required_vol ? ' ⚠ LOW' : '';
            return `<option value="${b.name}">${b.name} | ${rem} L${exp}${low}</option>`;
        }).join('');
        return `<select id="${select_id}" class="form-control">${opts}</select>`;
    }

    const html = `
        <table class="table table-bordered" style="font-size:13px">
            <thead style="background:#f0f4f0">
                <tr>
                    <th>Medium Type</th>
                    <th style="text-align:right">Required (L)</th>
                    <th style="text-align:right">Ratio</th>
                    <th style="min-width:280px">Select Batch</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td style="vertical-align:middle"><b style="color:#2e7d32">Green Medium</b></td>
                    <td style="vertical-align:middle;text-align:right">${green_volume.toFixed(3)}</td>
                    <td style="vertical-align:middle;text-align:right">75%</td>
                    <td style="vertical-align:middle">${batch_opts(green_batches, green_volume, 'fmb-green-sel')}</td>
                </tr>
                <tr>
                    <td style="vertical-align:middle"><b style="color:#c62828">Red Medium</b></td>
                    <td style="vertical-align:middle;text-align:right">${red_volume.toFixed(3)}</td>
                    <td style="vertical-align:middle;text-align:right">25%</td>
                    <td style="vertical-align:middle">${batch_opts(red_batches, red_volume, 'fmb-red-sel')}</td>
                </tr>
            </tbody>
        </table>
        <p class="text-muted" style="font-size:12px;margin-top:6px">
            Batches are ordered by expiry date (earliest first). Selections can be changed on the form after loading.
        </p>`;

    const d2 = new frappe.ui.Dialog({
        title: __('Select Medium Batches — {0} L Total', [target_volume]),
        fields: [{ fieldtype: 'HTML', fieldname: 'tbl', options: html }],
        size: 'large',
        primary_action_label: __('Load into Form'),
        primary_action() {
            const form_vol = frm.doc.final_required_volume;
            if (form_vol && Math.abs(form_vol - target_volume) > 0.0001) {
                frappe.msgprint({
                    title: __('Volume Mismatch'),
                    message: __('Formula was scaled for <b>{0} L</b> but the form shows <b>{1} L</b>. Reload the formula after correcting the volume.', [target_volume, form_vol]),
                    indicator: 'red',
                });
                return;
            }
            const green_sel = d2.$wrapper.find('#fmb-green-sel').val();
            const red_sel   = d2.$wrapper.find('#fmb-red-sel').val();

            frm.clear_table('medium_sources');

            const green_row = frm.add_child('medium_sources');
            green_row.medium_type    = 'Green';
            green_row.medium_batch   = green_sel || '';
            green_row.ratio_pct      = 75;
            green_row.volume_required = parseFloat((target_volume * 0.75).toFixed(6));

            const red_row = frm.add_child('medium_sources');
            red_row.medium_type    = 'Red';
            red_row.medium_batch   = red_sel || '';
            red_row.ratio_pct      = 25;
            red_row.volume_required = parseFloat((target_volume * 0.25).toFixed(6));

            frm.refresh_field('medium_sources');
            d2.hide();
            frappe.show_alert({
                message: __('Medium sources loaded — review and confirm before submitting.'),
                indicator: 'green',
            });
        },
    });
    d2.show();
}

frappe.ui.form.on('Final Medium Batch', {
    onload(frm) {
        if (frm.is_new() && !frm.doc.prepared_by) {
            frm.set_value('prepared_by', frappe.session.user);
        }
        if (frm.is_new() && !frm.doc.preparation_date) {
            frm.set_value('preparation_date', frappe.datetime.get_today());
        }
    },

    refresh(frm) {
        // Status banner
        const status = frm.doc.status;
        if (frm.doc.docstatus === 0) {
            frm.dashboard.set_headline_alert(
                __('Draft — enter Final Required Volume, use Load Formula to select medium batches, then complete QC before submitting.'),
                'blue'
            );
        } else if (frm.doc.docstatus === 1) {
            if (status === 'Approved') {
                frm.dashboard.set_headline_alert(
                    __('Approved — {0} L remaining. Ready for use in Production Batches.', [frm.doc.remaining_volume || 0]),
                    'green'
                );
            } else if (status === 'Partially Used') {
                frm.dashboard.set_headline_alert(
                    __('Partially Used — {0} L remaining of {1} L.', [frm.doc.remaining_volume || 0, frm.doc.actual_final_volume || 0]),
                    'yellow'
                );
            } else if (status === 'Used') {
                frm.dashboard.set_headline_alert(__('Fully consumed.'), 'grey');
            } else if (status === 'Rejected') {
                frm.dashboard.set_headline_alert(__('Rejected — batch cannot be used.'), 'red');
            }
        } else if (frm.doc.docstatus === 2) {
            frm.dashboard.set_headline_alert(__('Cancelled.'), 'grey');
        }

        // Buttons
        if (frm.doc.docstatus === 0) {
            frm.add_custom_button(__('Load Formula'), () => fmb_load_formula(frm), __('Actions'));
        }
        if (frm.doc.docstatus === 1 && ['Approved', 'Partially Used'].includes(status)) {
            frm.add_custom_button(__('Create Production Batch'), () => {
                frappe.new_doc('Production Batch', { final_medium_batch: frm.doc.name });
            }, __('Actions'));
        }

        // Filter medium_sources child table by type
        frm.set_query('medium_batch', 'medium_sources', function(doc, cdt, cdn) {
            const row = locals[cdt][cdn];
            const filters = { docstatus: 1 };
            if (row.medium_type) filters.medium_type = row.medium_type;
            return { filters };
        });
    },

    final_required_volume(frm) {
        const frv = frm.doc.final_required_volume || 0;
        (frm.doc.medium_sources || []).forEach(row => {
            const ratio = row.medium_type === 'Green' ? 0.75 : (row.medium_type === 'Red' ? 0.25 : 0);
            frappe.model.set_value(row.doctype, row.name, 'ratio_pct', ratio * 100);
            frappe.model.set_value(row.doctype, row.name, 'volume_required',
                parseFloat((frv * ratio).toFixed(6)));
        });
        if (frm.doc.medium_sources && frm.doc.medium_sources.length) {
            frm.refresh_field('medium_sources');
        }
    },

    qc_status(frm) {
        if (frm.doc.qc_status && frm.doc.qc_status !== 'Pending') {
            if (!frm.doc.qc_date)       frm.set_value('qc_date', frappe.datetime.get_today());
            if (!frm.doc.qc_checked_by) frm.set_value('qc_checked_by', frappe.session.user);
        }
    },

    aseptic_mixing_done(frm) {
        if (frm.doc.aseptic_mixing_done && !frm.doc.aseptic_mixing_date) {
            frm.set_value('aseptic_mixing_date', frappe.datetime.now_datetime());
        }
    },

    shelf_life_days(frm) { calc_fmb_expiry(frm); },
    preparation_date(frm) { calc_fmb_expiry(frm); },
});

frappe.ui.form.on('FMB Medium Source', {
    medium_type(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        const frv = frm.doc.final_required_volume || 0;
        const ratio = row.medium_type === 'Green' ? 0.75 : (row.medium_type === 'Red' ? 0.25 : 0);
        frappe.model.set_value(cdt, cdn, 'ratio_pct', ratio * 100);
        frappe.model.set_value(cdt, cdn, 'volume_required', parseFloat((frv * ratio).toFixed(6)));
    },

    medium_batch(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (!row.medium_batch || !row.volume_required) return;
        frappe.db.get_value('Medium Batch', row.medium_batch,
            ['remaining_volume', 'status', 'medium_type'], (r) => {
            if (!r) return;
            if (r.medium_type && r.medium_type !== row.medium_type) {
                frappe.show_alert({
                    message: __('Row {0}: {1} is a {2} batch, not {3}.', [row.idx, row.medium_batch, r.medium_type, row.medium_type]),
                    indicator: 'red'
                });
                return;
            }
            const remaining = r.remaining_volume || 0;
            if (row.volume_required > remaining) {
                frappe.show_alert({
                    message: __('Row {0}: {1} only has {2} L remaining but {3} L is required.', [
                        row.idx, row.medium_batch, remaining.toFixed(3), row.volume_required.toFixed(3)
                    ]),
                    indicator: 'orange'
                });
            }
        });
    },
});
