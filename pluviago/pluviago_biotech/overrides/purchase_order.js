frappe.ui.form.on("Purchase Order", {
	refresh(frm) {
		// Hide sections not used by Pluviago
		const hidden_sections = [
			"currency_and_price_list",
			"accounting_dimensions_section",
			"taxes_section",        // Taxes and Charges section (template + table)
			"totals",               // Tax totals section break
			"sec_tax_breakup",
			"discount_section",
			"section_break_48",    // Pricing Rules
			"totals_section",
			"payment_schedule_section",
			"terms_section_break",
		];
		hidden_sections.forEach((fn) => frm.set_df_property(fn, "hidden", 1));
	},
});
