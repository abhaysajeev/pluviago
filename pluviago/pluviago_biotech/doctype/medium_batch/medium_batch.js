// Default shelf life (days) by medium type and storage condition
const _MB_SHELF_LIFE = {
    'Green': { '2-8°C': 21, 'Room Temperature': 7 },
    'Red':   { '2-8°C': 21, 'Room Temperature': 7 },
};

function calc_mb_expiry(frm) {
    if (frm.doc.shelf_life_days && frm.doc.preparation_date) {
        frm.set_value('expiry_date',
            frappe.datetime.add_days(frm.doc.preparation_date, frm.doc.shelf_life_days));
    }
}

function apply_medium_type_layout(frm) {
    const is_green = frm.doc.medium_type === 'Green';
    const is_red   = frm.doc.medium_type === 'Red';

    const green_fields = [
        'section_break_qc_green', 'qc_checkpoint_1_clarity', 'qc_checkpoint_1_date', 'qc_checkpoint_1_by',
        'section_break_qc2',      'qc_checkpoint_2_clarity', 'qc_checkpoint_2_ph',
        'qc_checkpoint_2_date',   'qc_checkpoint_2_by',      'top_up_done',
    ];
    const red_fields = [
        'section_break_qc_red', 'qc_checkpoint_3_clarity', 'qc_checkpoint_3_date', 'qc_checkpoint_3_by',
        'section_break_qc4',    'qc_checkpoint_4_clarity', 'qc_checkpoint_4_ph',
        'qc_checkpoint_4_date', 'qc_checkpoint_4_by',
    ];

    green_fields.forEach(f => frm.toggle_display(f, is_green));
    red_fields.forEach(f => frm.toggle_display(f, is_red));

    if (frm.doc.medium_type) {
        const pct   = is_green ? '75%' : '25%';
        const label = `Medium Volume for Final Mix (L) [${pct}]`;
        frm.set_df_property('medium_volume_calculated', 'label', label);
    }
}

function apply_qc_progressive_lock(frm) {
    if (frm.doc.medium_type === 'Green') {
        const cp1_done = frm.doc.qc_checkpoint_1_clarity === 'Pass';
        const cp1_fail = frm.doc.qc_checkpoint_1_clarity === 'Fail';
        ['qc_checkpoint_2_clarity','qc_checkpoint_2_ph','qc_checkpoint_2_date','qc_checkpoint_2_by']
            .forEach(f => frm.set_df_property(f, 'read_only', cp1_done ? 0 : 1));
        if (cp1_fail && frm.doc.preparation_status === 'QC Pending') {
            frm.dashboard.add_comment(
                '⚠ QC Checkpoint 1 FAILED — Clarity not acceptable. Discard using "Mark as Wasted".',
                'red', true
            );
        }
    } else if (frm.doc.medium_type === 'Red') {
        const cp3_done = frm.doc.qc_checkpoint_3_clarity === 'Pass';
        const cp3_fail = frm.doc.qc_checkpoint_3_clarity === 'Fail';
        ['qc_checkpoint_4_clarity','qc_checkpoint_4_ph','qc_checkpoint_4_date','qc_checkpoint_4_by']
            .forEach(f => frm.set_df_property(f, 'read_only', cp3_done ? 0 : 1));
        if (cp3_fail && frm.doc.preparation_status === 'QC Pending') {
            frm.dashboard.add_comment(
                '⚠ QC Checkpoint 3 FAILED — Clarity not acceptable. Discard using "Mark as Wasted".',
                'red', true
            );
        }
    }
}

function auto_check_overall_qc(frm) {
    if (frm.doc.medium_type === 'Green') {
        if (frm.doc.qc_checkpoint_1_clarity === 'Pass' && frm.doc.qc_checkpoint_2_clarity === 'Pass') {
            frm.set_value('overall_qc_status', 'Passed');
        } else if (frm.doc.qc_checkpoint_1_clarity === 'Fail' || frm.doc.qc_checkpoint_2_clarity === 'Fail') {
            frm.set_value('overall_qc_status', 'Failed');
        }
    } else if (frm.doc.medium_type === 'Red') {
        if (frm.doc.qc_checkpoint_3_clarity === 'Pass' && frm.doc.qc_checkpoint_4_clarity === 'Pass') {
            frm.set_value('overall_qc_status', 'Passed');
        } else if (frm.doc.qc_checkpoint_3_clarity === 'Fail' || frm.doc.qc_checkpoint_4_clarity === 'Fail') {
            frm.set_value('overall_qc_status', 'Failed');
        }
    }
}

function fill_checkpoint_meta(frm, date_field, by_field) {
    if (!frm.doc[date_field]) frm.set_value(date_field, frappe.datetime.get_today());
    if (!frm.doc[by_field])   frm.set_value(by_field, frappe.session.user);
}

function set_medium_type_defaults(frm) {
    if (!frm.doc.medium_type) return;
    const storage = frm.doc.storage_condition || '2-8°C';
    const days = (_MB_SHELF_LIFE[frm.doc.medium_type] || {})[storage] || 21;
    if (!frm.doc.shelf_life_days) frm.set_value('shelf_life_days', days);
    if (!frm.doc.prepared_by)     frm.set_value('prepared_by', frappe.session.user);
    if (!frm.doc.preparation_date) frm.set_value('preparation_date', frappe.datetime.get_today());
    if (!frm.doc.storage_condition) frm.set_value('storage_condition', '2-8°C');
}

function clear_for_type_change(frm) {
    // QC fields
    ['qc_checkpoint_1_clarity','qc_checkpoint_2_clarity',
     'qc_checkpoint_3_clarity','qc_checkpoint_4_clarity'].forEach(f => frm.set_value(f, 'Pending'));
    ['qc_checkpoint_1_date','qc_checkpoint_1_by',
     'qc_checkpoint_2_date','qc_checkpoint_2_by','qc_checkpoint_2_ph',
     'qc_checkpoint_3_date','qc_checkpoint_3_by',
     'qc_checkpoint_4_date','qc_checkpoint_4_by','qc_checkpoint_4_ph'].forEach(f => frm.set_value(f, null));
    frm.set_value('overall_qc_status', 'Pending');
    frm.set_value('quality_flag', 'Normal');
    // Process fields
    frm.set_value('sterilization_method', null);
    frm.set_value('sterilization_done', 0);
    frm.set_value('sterilization_date', null);
    frm.set_value('top_up_done', 0);
    frm.set_value('remarks', null);
    // Child tables
    frm.clear_table('direct_chemicals');
    frm.refresh_field('direct_chemicals');
    frm.clear_table('ssb_used');
    frm.refresh_field('ssb_used');
    frm.clear_table('corrective_actions');
    frm.refresh_field('corrective_actions');
    // Reset shelf life to type default
    frm.set_value('shelf_life_days', null);
}

frappe.ui.form.on('Medium Batch', {
    onload(frm) {
        // Auto-fill prepared_by on new doc
        if (frm.is_new() && !frm.doc.prepared_by) {
            frm.set_value('prepared_by', frappe.session.user);
        }
        if (frm.is_new() && !frm.doc.preparation_date) {
            frm.set_value('preparation_date', frappe.datetime.get_today());
        }
    },

    medium_type(frm) {
        const has_data =
            (frm.doc.direct_chemicals || []).length > 0 ||
            (frm.doc.ssb_used || []).length > 0 ||
            (frm.doc.qc_checkpoint_1_clarity !== 'Pending' && frm.doc.qc_checkpoint_1_clarity) ||
            (frm.doc.qc_checkpoint_3_clarity !== 'Pending' && frm.doc.qc_checkpoint_3_clarity);

        const do_change = () => {
            clear_for_type_change(frm);
            set_medium_type_defaults(frm);
            if (frm.doc.final_required_volume && frm.doc.medium_type) {
                const factor = frm.doc.medium_type === 'Green' ? 0.75 : 0.25;
                frm.set_value('medium_volume_calculated',
                    parseFloat((frm.doc.final_required_volume * factor).toFixed(6)));
            }
            apply_medium_type_layout(frm);
            frm.trigger('refresh');
        };

        if (has_data && frm.doc.medium_type) {
            frappe.confirm(
                `Changing Medium Type will clear all formula data, QC records, and child tables. Continue?`,
                () => do_change(),
                () => {
                    // Revert to previous value by reloading
                    frm.reload_doc();
                }
            );
        } else {
            do_change();
        }
    },

    storage_condition(frm) {
        // Update shelf life default when storage changes (only if not already customised)
        if (frm.doc.medium_type) {
            const days = (_MB_SHELF_LIFE[frm.doc.medium_type] || {})[frm.doc.storage_condition] || 21;
            frm.set_value('shelf_life_days', days);
        }
    },

    final_required_volume(frm) {
        if (!frm.doc.medium_type || !frm.doc.final_required_volume) return;
        const factor = frm.doc.medium_type === 'Green' ? 0.75 : 0.25;
        const new_vol = parseFloat((frm.doc.final_required_volume * factor).toFixed(6));
        frm.set_value('medium_volume_calculated', new_vol);

        const has_chems = (frm.doc.direct_chemicals || []).filter(r => r.quantity).length > 0;
        const has_ssbs  = (frm.doc.ssb_used || []).filter(r => r.volume_used_ml).length > 0;
        if ((has_chems || has_ssbs) && frm._prev_final_volume && frm.doc.final_required_volume !== frm._prev_final_volume) {
            const old_vol = frm._prev_final_volume;
            frappe.confirm(
                `Volume changed from ${old_vol} L to ${frm.doc.final_required_volume} L. Rescale existing formula quantities?`,
                () => {
                    const ratio = frm.doc.final_required_volume / old_vol;
                    (frm.doc.direct_chemicals || []).forEach(row => {
                        if (row.quantity) frappe.model.set_value(row.doctype, row.name, 'quantity',
                            parseFloat((row.quantity * ratio).toFixed(4)));
                    });
                    (frm.doc.ssb_used || []).forEach(row => {
                        if (row.volume_used_ml) frappe.model.set_value(row.doctype, row.name, 'volume_used_ml',
                            parseFloat((row.volume_used_ml * ratio).toFixed(4)));
                    });
                    frm.refresh_field('direct_chemicals');
                    frm.refresh_field('ssb_used');
                }
            );
        }
        frm._prev_final_volume = frm.doc.final_required_volume;
    },

    shelf_life_days(frm) { calc_mb_expiry(frm); },
    preparation_date(frm) { calc_mb_expiry(frm); },

    // QC auto-fill date + user, then check if overall can be set
    qc_checkpoint_1_clarity(frm) {
        if (frm.doc.qc_checkpoint_1_clarity && frm.doc.qc_checkpoint_1_clarity !== 'Pending') {
            fill_checkpoint_meta(frm, 'qc_checkpoint_1_date', 'qc_checkpoint_1_by');
        }
        apply_qc_progressive_lock(frm);
        auto_check_overall_qc(frm);
    },
    qc_checkpoint_2_clarity(frm) {
        if (frm.doc.qc_checkpoint_2_clarity && frm.doc.qc_checkpoint_2_clarity !== 'Pending') {
            fill_checkpoint_meta(frm, 'qc_checkpoint_2_date', 'qc_checkpoint_2_by');
        }
        auto_check_overall_qc(frm);
    },
    qc_checkpoint_3_clarity(frm) {
        if (frm.doc.qc_checkpoint_3_clarity && frm.doc.qc_checkpoint_3_clarity !== 'Pending') {
            fill_checkpoint_meta(frm, 'qc_checkpoint_3_date', 'qc_checkpoint_3_by');
        }
        apply_qc_progressive_lock(frm);
        auto_check_overall_qc(frm);
    },
    qc_checkpoint_4_clarity(frm) {
        if (frm.doc.qc_checkpoint_4_clarity && frm.doc.qc_checkpoint_4_clarity !== 'Pending') {
            fill_checkpoint_meta(frm, 'qc_checkpoint_4_date', 'qc_checkpoint_4_by');
        }
        auto_check_overall_qc(frm);
    },

    refresh(frm) {
        frm._prev_final_volume = frm._prev_final_volume || frm.doc.final_required_volume;

        apply_medium_type_layout(frm);
        apply_qc_progressive_lock(frm);

        // DI Water filter — in-house Lab Consumables only
        frm.set_query('di_water_rmb', () => ({
            query: 'pluviago.pluviago_biotech.utils.stock_utils.di_water_rmb_query'
        }));

        // direct_chemicals RMB filter — submitted, approved, matching item_code
        frm.set_query('raw_material_batch', 'direct_chemicals', function(doc, cdt, cdn) {
            const row = locals[cdt][cdn];
            const filters = { docstatus: 1, qc_status: 'Approved' };
            if (row.item_code) filters.item_code = row.item_code;
            return { filters };
        });

        // A7-I last-addition reminder for Red Medium
        if (frm.doc.medium_type === 'Red' && (frm.doc.ssb_used || []).length > 0) {
            frm.dashboard.add_comment(
                '⚠ Procedural: Add A7-I (Calcium Nitrate) LAST when combining stock solutions into the vessel. ' +
                'Calcium precipitates if mixed with sulphates or phosphates early.',
                'yellow', true
            );
        }

        // Load Full Formula button
        if (frm.doc.docstatus === 0 && frm.doc.preparation_status === 'Draft' && frm.doc.medium_type) {
            frm.add_custom_button(__('Load Full Formula'), function () {
                pluviago.load_medium_formula(frm);
            }, __('Actions'));
        }

        // Mark Preparation Complete
        if (frm.doc.docstatus === 0 && frm.doc.preparation_status === 'Draft') {
            frm.add_custom_button(__('Mark Preparation Complete'), function () {
                frappe.confirm(
                    'Confirm that all direct chemicals and stock solutions have been physically added. '
                    + 'Stock will be deducted from Raw Material Batches. This cannot be undone.',
                    function () {
                        frappe.call({
                            method: 'mark_preparation_complete',
                            doc: frm.doc,
                            callback: function () { frm.reload_doc(); }
                        });
                    }
                );
            }, __('Actions')).addClass('btn-primary');
        }

        // Mark as Wasted
        if (frm.doc.docstatus === 0 && frm.doc.preparation_status === 'QC Pending') {
            frm.add_custom_button(__('Mark as Wasted'), function () {
                frappe.prompt(
                    { label: 'Reason for Waste', fieldname: 'reason', fieldtype: 'Text' },
                    function (values) {
                        frappe.call({
                            method: 'mark_wasted',
                            doc: frm.doc,
                            args: { reason: values.reason || '' },
                            callback: function () { frm.reload_doc(); }
                        });
                    },
                    __('Mark Batch as Wasted (QC Failed)'),
                    __('Confirm Waste')
                );
            }, __('Actions')).addClass('btn-danger');
        }

        // Create Final Medium quick action
        if (frm.doc.docstatus === 1 && ['Approved', 'Partially Used'].includes(frm.doc.status)) {
            frm.add_custom_button(__('Create Final Medium'), function () {
                frappe.prompt(
                    [{ label: 'Target Final Volume (L)', fieldname: 'final_vol', fieldtype: 'Float', reqd: 1 }],
                    function (values) {
                        const is_green = frm.doc.medium_type === 'Green';
                        frappe.new_doc('Final Medium Batch', {
                            [is_green ? 'green_medium_batch' : 'red_medium_batch']: frm.doc.name,
                            final_required_volume: values.final_vol,
                            preparation_date: frappe.datetime.get_today(),
                            prepared_by: frappe.session.user,
                        });
                    },
                    __('Create Final Medium Batch'),
                    __('Create')
                );
            }, __('Actions'));
        }

        // View Lineage
        if (frm.doc.docstatus === 1) {
            frm.add_custom_button(__('View Lineage'), () => {
                frappe.call({
                    method: 'pluviago.pluviago_biotech.utils.stock_utils.get_medium_lineage',
                    args: { batch_name: frm.doc.name, batch_doctype: 'Medium Batch' },
                    callback(r) {
                        const d = r.message || {};
                        const fmbs  = d.final_medium_batches || [];
                        const prods = d.production_batches || [];
                        let html = '';
                        if (fmbs.length) {
                            html += '<b>Final Medium Batches:</b><br>' + fmbs.map(f =>
                                `<a href="/app/final-medium-batch/${f.name}">${f.name}</a> (${f.status})`
                            ).join('<br>') + '<br><br>';
                        }
                        if (prods.length) {
                            html += '<b>Production Batches:</b><br>' + prods.map(p =>
                                `<a href="/app/production-batch/${p.name}">${p.name}</a> (${p.status})`
                            ).join('<br>');
                        }
                        if (!html) html = 'Not yet consumed by any downstream batch.';
                        frappe.msgprint({ title: __('Downstream Lineage'), message: html, indicator: 'blue' });
                    }
                });
            }, __('Actions'));
        }

        // Status banners
        const type_label = frm.doc.medium_type ? `${frm.doc.medium_type} Medium` : 'Medium';
        if (frm.doc.preparation_status === 'Draft') {
            frm.set_intro(
                frm.doc.medium_type
                    ? `${type_label} — Add base salts and link stock solutions, then click Mark Preparation Complete.`
                    : 'Select Medium Type to begin preparation.',
                'blue'
            );
        } else if (frm.doc.preparation_status === 'QC Pending') {
            const cp_label = frm.doc.medium_type === 'Green' ? 'QC Checkpoints 1 & 2' : 'QC Checkpoints 3 & 4';
            frm.set_intro(`Preparation complete. Complete ${cp_label}. Submit if passed, or Mark as Wasted if failed.`, 'orange');
        } else if (frm.doc.preparation_status === 'Released') {
            frm.set_intro(`${type_label} batch released. Available for Final Medium formulation.`, 'green');
        } else if (frm.doc.preparation_status === 'Wasted') {
            frm.set_intro('This batch was wasted (QC failed). Stock loss has been logged.', 'red');
        }

        if (frm.doc.quality_flag === 'Conditional Release') {
            frm.set_intro('⚠ Quality Flag: Conditional Release — batch passed after corrective action.', 'yellow');
        } else if (frm.doc.quality_flag === 'Rejected') {
            frm.set_intro('🚫 Quality Flag: Rejected — batch failed QC and cannot be used.', 'red');
        }
    }
});
