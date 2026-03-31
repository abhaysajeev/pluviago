frappe.ui.form.on("Raw Material Batch", {
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
