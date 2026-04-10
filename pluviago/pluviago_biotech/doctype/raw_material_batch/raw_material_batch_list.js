frappe.listview_settings["Raw Material Batch"] = {
    add_fields: ["qc_status", "batch_source", "status", "item_code", "received_qty", "remaining_qty"],

    get_indicator(doc) {
        const map = {
            "Approved":  ["green",  "status,=,Approved"],
            "Received":  ["blue",   "status,=,Received"],
            "Exhausted": ["grey",   "status,=,Exhausted"],
            "Rejected":  ["red",    "status,=,Rejected"],
        };
        return map[doc.status] || ["grey", "status,=," + doc.status];
    },

    onload(listview) {
        listview.page.add_action_item(__("Submit Selected"), () => {
            const selected = listview.get_checked_items();
            if (!selected.length) {
                frappe.msgprint(__("Select at least one Raw Material Batch."));
                return;
            }

            const drafts = selected.filter(r => r.docstatus === 0);
            if (!drafts.length) {
                frappe.msgprint(__("No Draft batches in selection — only Drafts can be submitted."));
                return;
            }

            frappe.confirm(
                __("Submit {0} selected Draft batch(es)?", [drafts.length]),
                () => {
                    frappe.call({
                        method: "pluviago.pluviago_biotech.doctype.raw_material_batch.raw_material_batch.bulk_submit_rmbs",
                        args: { names: drafts.map(r => r.name) },
                        freeze: true,
                        freeze_message: __("Submitting batches..."),
                        callback(r) {
                            if (!r.message) return;
                            const { submitted, failed } = r.message;

                            let msg = "";
                            if (submitted.length) {
                                msg += `<b>${submitted.length} submitted:</b><br>`;
                                submitted.forEach(n => { msg += `✓ ${n}<br>`; });
                            }
                            if (failed.length) {
                                msg += `<br><b>${failed.length} failed:</b><br>`;
                                failed.forEach(f => { msg += `✗ ${f.name}: ${f.reason}<br>`; });
                            }

                            frappe.msgprint({
                                title: __("Bulk Submit Result"),
                                message: msg || __("No changes made."),
                                indicator: failed.length ? "orange" : "green",
                            });
                            listview.refresh();
                        },
                    });
                }
            );
        });
    },
};
