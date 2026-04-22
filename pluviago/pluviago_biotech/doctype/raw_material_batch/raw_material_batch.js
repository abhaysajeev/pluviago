frappe.ui.form.on("Raw Material Batch", {
	purchase_receipt(frm) {
		if (!frm.doc.purchase_receipt) return;

		frappe.call({
			method: "frappe.client.get",
			args: { doctype: "Purchase Receipt", name: frm.doc.purchase_receipt },
			callback(r) {
				if (!r.message) return;
				const pr = r.message;

				frm.set_value("supplier", pr.supplier);
				frm.set_value("received_date", pr.posting_date);
				if (pr.custom_coa_attach) frm.set_value("coa_attachment", pr.custom_coa_attach);

				const items = (pr.items || []).filter(i => i.item_code);
				if (!items.length) return;

				const current_item = frm.doc.item_code;
				const matched = current_item ? items.find(i => i.item_code === current_item) : null;

				if (matched) {
					_populate_from_pr_item(frm, matched);
				} else if (items.length === 1) {
					_populate_from_pr_item(frm, items[0]);
				} else {
					const options = items.map(i =>
						`${i.item_code} — ${i.item_name || ""} (qty: ${i.qty} ${i.uom || ""})`
					);
					frappe.prompt(
						[{
							fieldname: "item",
							fieldtype: "Select",
							label: "Select Item from Receipt",
							options: options.join("\n"),
							reqd: 1,
						}],
						(vals) => {
							const idx = options.indexOf(vals.item);
							if (idx >= 0) _populate_from_pr_item(frm, items[idx]);
						},
						__("Which item is this batch for?")
					);
				}
			},
		});
	},

	qc_status(frm) {
		if (frm.doc.qc_status === "Approved") {
			if (!frm.doc.qc_checked_by) {
				frm.set_value("qc_checked_by", frappe.session.user);
			}
			if (!frm.doc.qc_date) {
				frm.set_value("qc_date", frappe.datetime.get_today());
			}
		}
	},

	coa_verified(frm) {
		if (frm.doc.coa_verified && !frm.doc.coa_verified_by) {
			frm.set_value("coa_verified_by", frappe.session.user);
		}
	},

	refresh(frm) {
		// Expiry alerts
		if (frm.doc.expiry_date) {
			const today = frappe.datetime.get_today();
			if (frm.doc.expiry_date < today) {
				frm.dashboard.set_headline_alert("This batch has EXPIRED", "red");
			} else {
				const days = frappe.datetime.get_diff(frm.doc.expiry_date, today);
				if (days <= 30) {
					frm.dashboard.set_headline_alert(`Expires in ${days} days`, "orange");
				}
			}
		}

		// Recalculate Stock button — visible on submitted docs for admin/QC roles
		if (frm.doc.docstatus === 1) {
			frm.add_custom_button(__("Recalculate Stock"), () => {
				frappe.call({
					method: "pluviago.pluviago_biotech.doctype.raw_material_batch.raw_material_batch.recalculate_stock",
					args: { rmb_name: frm.doc.name },
					freeze: true,
					freeze_message: __("Recalculating..."),
					callback(r) {
						if (r.message) {
							frappe.show_alert({
								message: __(
									"Recalculated — Consumed: {0}, Remaining: {1}",
									[r.message.consumed_qty, r.message.remaining_qty]
								),
								indicator: "green",
							});
							frm.reload_doc();
						}
					},
				});
			}, __("Actions"));
		}
	},
});


function _populate_from_pr_item(frm, row) {
	frm.set_value("item_code", row.item_code);
	if (row.item_name) frm.set_value("material_name", row.item_name);
	frm.set_value("received_qty", row.qty);
	frm.set_value("received_qty_uom", row.uom);
	if (row.warehouse) frm.set_value("warehouse", row.warehouse);
	if (row.custom_supplier_batch_no) frm.set_value("supplier_batch_no", row.custom_supplier_batch_no);
	if (row.custom_mfg_date) frm.set_value("mfg_date", row.custom_mfg_date);
	if (row.custom_expiry_date) frm.set_value("expiry_date", row.custom_expiry_date);
	if (row.custom_storage_condition) frm.set_value("storage_condition", row.custom_storage_condition);
	if (row.purchase_order) frm.set_value("purchase_order", row.purchase_order);
}
