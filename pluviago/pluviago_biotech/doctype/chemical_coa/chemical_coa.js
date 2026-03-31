frappe.ui.form.on("Chemical COA", {
	refresh(frm) {
		if (frm.doc.docstatus === 0 && frm.doc.item_code) {
			frm.add_custom_button(__("Load Spec Template"), () => {
				frm.call({
					method: "pluviago.pluviago_biotech.doctype.chemical_coa.chemical_coa.get_spec_parameters",
					args: { item_code: frm.doc.item_code },
					callback(r) {
						if (!r.message || !r.message.length) {
							frappe.msgprint(__("No QC Parameter Specs found for this chemical. Create specs in QC Parameter Spec with Applicable Stage = Raw Material Batch."));
							return;
						}
						const existing = frm.doc.test_parameters || [];
						if (existing.length) {
							frappe.confirm(
								__("This will replace existing test parameters. Continue?"),
								() => load_rows(frm, r.message)
							);
						} else {
							load_rows(frm, r.message);
						}
					}
				});
			}, __("Actions"));
		}
	},

	item_code(frm) {
		// Auto-fetch supplier name from linked Raw Material Batch if item changes
		if (frm.doc.raw_material_batch) {
			frappe.db.get_value("Raw Material Batch", frm.doc.raw_material_batch, "supplier", (r) => {
				if (r && r.supplier) frm.set_value("supplier", r.supplier);
			});
		}
	},

	raw_material_batch(frm) {
		if (!frm.doc.raw_material_batch) return;
		frappe.db.get_value(
			"Raw Material Batch",
			frm.doc.raw_material_batch,
			["material_name", "item_code", "supplier", "supplier_batch_no", "expiry_date"],
			(r) => {
				if (!r) return;
				if (r.material_name) frm.set_value("material_name", r.material_name);
				if (r.item_code) frm.set_value("item_code", r.item_code);
				if (r.supplier) frm.set_value("supplier", r.supplier);
				if (r.supplier_batch_no) frm.set_value("supplier_batch_no", r.supplier_batch_no);
				if (r.expiry_date) frm.set_value("expiry_date", r.expiry_date);
			}
		);
	}
});

function load_rows(frm, rows) {
	frm.clear_table("test_parameters");
	rows.forEach(row => {
		const child = frm.add_child("test_parameters");
		child.parameter_name = row.parameter_name;
		child.specification = row.specification;
		child.observed_value = "";
		child.result = "";
	});
	frm.refresh_field("test_parameters");
	frappe.show_alert({ message: __("{0} parameters loaded from spec template", [rows.length]), indicator: "green" });
}
