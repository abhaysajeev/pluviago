frappe.ui.form.on("Approved Vendor", {
	setup(frm) {
		// Force uppercase display on supplier_name field
		frm.fields_dict.supplier_name &&
			frm.fields_dict.supplier_name.$input &&
			frm.fields_dict.supplier_name.$input.css("text-transform", "uppercase");
	},

	supplier_name(frm) {
		if (frm.doc.supplier_name) {
			frm.set_value("supplier_name", frm.doc.supplier_name.toUpperCase());
		}
	},

	before_save(frm) {
		if (frm.is_new() && !frm.__confirmed_save) {
			frappe.validated = false;

			frappe.confirm(
				__("A new Supplier <b>{0}</b> will be created. Proceed?", [frm.doc.supplier_name]),
				() => {
					frm.__confirmed_save = true;
					frm.save();
				}
			);
		}
	},

	refresh(frm) {
		// Reset the confirmation flag on every refresh so re-saves work normally
		frm.__confirmed_save = false;

		if (!frm.is_new() && frm.doc.supplier) {
			frm.add_custom_button(__("Create Purchase Order"), function () {
				if (!frm.doc.approved_items || !frm.doc.approved_items.length) {
					frappe.msgprint(__("No approved items found on this vendor record."));
					return;
				}

				// Create the PO fully server-side (avoids client-side mandatory issues)
				frappe.call({
					method: "pluviago.pluviago_biotech.doctype.approved_vendor.approved_vendor.create_purchase_order",
					args: { avl_name: frm.doc.name },
					freeze: true,
					freeze_message: __("Creating Purchase Order..."),
					callback(r) {
						if (r.message) {
							frappe.set_route("Form", "Purchase Order", r.message);
						}
					},
				});
			}, __("Create"));
		}
	},
});
