frappe.ui.form.on("Approved Vendor", {
	refresh(frm) {
		if (!frm.is_new()) {
			frm.add_custom_button(__("Create Purchase Order"), function () {
				const approved_items = frm.doc.approved_items || [];

				if (!approved_items.length) {
					frappe.msgprint(__("No approved items found on this vendor record."));
					return;
				}

				frappe.model.with_doctype("Purchase Order", function () {
					const doc = frappe.model.get_new_doc("Purchase Order");
					doc.supplier = frm.doc.supplier;

					approved_items.forEach(function (avl_item) {
						const row = frappe.model.add_child(doc, "Purchase Order Item", "items");
						row.item_code = avl_item.item_code;
						row.item_name = avl_item.material_name;
						row.qty = 1;
					});

					frappe.set_route("Form", "Purchase Order", doc.name);
				});
			}, __("Create"));
		}
	},
});
