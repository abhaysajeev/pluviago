function calc_ssb_expiry(frm) {
    if (frm.doc.shelf_life_days && frm.doc.preparation_date) {
        frm.set_value('expiry_date',
            frappe.datetime.add_days(frm.doc.preparation_date, frm.doc.shelf_life_days));
    }
}

frappe.ui.form.on('Stock Solution Batch', {
    shelf_life_days(frm) { calc_ssb_expiry(frm); },
    preparation_date(frm) { calc_ssb_expiry(frm); },

    refresh(frm) {
        // Lineage: show which medium batches consumed this SSB
        if (frm.doc.docstatus === 1) {
            frm.add_custom_button(__('View Lineage'), () => {
                frappe.call({
                    method: 'pluviago.pluviago_biotech.utils.stock_utils.get_ssb_lineage',
                    args: { ssb_name: frm.doc.name },
                    callback(r) {
                        const rows = r.message || [];
                        if (!rows.length) {
                            frappe.msgprint(__('This batch has not been consumed by any medium batch yet.'));
                            return;
                        }
                        const html = `<table class="table table-bordered" style="font-size:13px">
                            <thead><tr><th>Medium Batch</th><th>Type</th><th>Volume Used (mL)</th></tr></thead>
                            <tbody>${rows.map(r =>
                                `<tr><td><a href="/app/${r.medium_type.toLowerCase().replace(/ /g,'-')}/${r.medium_batch}">${r.medium_batch}</a></td>
                                <td>${r.medium_type}</td><td>${r.volume_used_ml}</td></tr>`
                            ).join('')}</tbody></table>`;
                        frappe.msgprint({ title: __('Consumed By'), message: html, indicator: 'blue' });
                    }
                });
            }, __('Actions'));
        }

        // Load Formula button
        pluviago.add_load_formula_button(frm, {
            applies_to: 'Stock Solution Batch',
            volume_field: 'target_volume',
            child_table: 'ingredients',
            qty_fieldname: 'qty',
        });

        // Mark Preparation Complete button
        if (frm.doc.docstatus === 0 && frm.doc.preparation_status === 'Draft') {
            frm.add_custom_button(__('Mark Preparation Complete'), function () {
                frappe.confirm(
                    'Confirm that all chemicals have been physically added and preparation is complete. '
                    + 'Stock will be deducted from Raw Material Batches. This cannot be undone.',
                    function () {
                        frappe.call({
                            method: 'mark_preparation_complete',
                            doc: frm.doc,
                            callback: function (r) {
                                frm.reload_doc();
                            }
                        });
                    }
                );
            }, __('Actions')).addClass('btn-primary');
        }

        // Mark as Wasted button
        if (frm.doc.docstatus === 0 && frm.doc.preparation_status === 'QC Pending') {
            frm.add_custom_button(__('Mark as Wasted'), function () {
                frappe.prompt(
                    { label: 'Reason for Waste', fieldname: 'reason', fieldtype: 'Text' },
                    function (values) {
                        frappe.call({
                            method: 'mark_wasted',
                            doc: frm.doc,
                            args: { reason: values.reason || '' },
                            callback: function (r) {
                                frm.reload_doc();
                            }
                        });
                    },
                    __('Mark Batch as Wasted (QC Failed)'),
                    __('Confirm Waste')
                );
            }, __('Actions')).addClass('btn-danger');
        }

        // Status indicators
        if (frm.doc.preparation_status === 'Draft') {
            frm.set_intro('Fill in ingredients and sterilisation details, then click Mark Preparation Complete.', 'blue');
        } else if (frm.doc.preparation_status === 'QC Pending') {
            frm.set_intro('Preparation complete. Fill in QC results. Submit if passed, or Mark as Wasted if failed.', 'orange');
        } else if (frm.doc.preparation_status === 'Released') {
            frm.set_intro('Batch released and available for use in medium preparation.', 'green');
        } else if (frm.doc.preparation_status === 'Wasted') {
            frm.set_intro('This batch was wasted (QC failed). Stock loss has been logged.', 'red');
        }
    }
});
