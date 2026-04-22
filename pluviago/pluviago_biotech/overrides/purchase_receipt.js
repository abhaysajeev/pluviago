/**
 * Purchase Receipt customization for Pluviago Biotech.
 *
 * 1. Hides irrelevant sections and accounting/serial/asset fields
 * 2. Adds "Create Raw Material Batches" button on submitted PRs
 * 3. Adds "View Raw Material Batches" button to navigate to linked RMBs
 */
frappe.ui.form.on("Purchase Receipt", {
    refresh(frm) {
        _hide_irrelevant_sections(frm);
        _hide_irrelevant_fields(frm);

        if (frm.doc.docstatus !== 1) return;

        frm.add_custom_button(
            __("View Raw Material Batches"),
            () => frappe.set_route("List", "Raw Material Batch", {
                purchase_receipt: frm.doc.name,
            }),
            __("Actions")
        );
    },
});


function _hide_irrelevant_sections(frm) {
    const sections_to_hide = [
        "currency_and_price_list",      // Currency & Price List
        "pricing_rule_details",         // Pricing Rules
        "raw_material_details",         // Raw Materials Consumed (subcontracting)
        "taxes_charges_section",        // Taxes and Charges (header section)
        "taxes_section",                // Taxes table section
        "totals",                       // Tax totals section
        "sec_tax_breakup",              // Tax Breakup
        "section_break_42",             // Additional Discount
        "section_break_46",             // Grand Totals
        "accounting_dimensions_section",// Accounting Dimensions
        "subscription_detail",          // Auto Repeat
        "printing_settings",            // Printing Settings
        "transporter_info",             // Transporter
        "section_break_98",             // Shipping Address
        "billing_address_section",      // Company Billing Address
    ];
    sections_to_hide.forEach(fn => frm.set_df_property(fn, "hidden", 1));
}


function _hide_irrelevant_fields(frm) {
    const fields_to_hide = [
        // Accounting
        "base_rate", "base_amount", "net_rate", "net_amount",
        "base_net_rate", "base_net_amount", "valuation_rate",
        "item_tax_amount", "rm_supp_cost", "landed_cost_voucher_amount",
        "amount_difference_with_purchase_invoice", "billed_amt",
        "expense_account", "item_tax_rate", "provisional_expense_account",
        "stock_uom_rate", "item_tax_template", "pricing_rules",
        "apply_tds", "is_free_item",

        // References
        "material_request", "purchase_invoice",
        "purchase_order_item", "purchase_invoice_item",
        "purchase_receipt_item", "delivery_note_item",
        "material_request_item", "sales_order", "sales_order_item",
        "subcontracting_receipt_item", "putaway_rule",

        // Weight
        "weight_per_unit", "total_weight", "weight_uom",

        // Serial / Batch bundle (ERPNext native — we use RMB instead)
        "serial_and_batch_bundle", "use_serial_batch_fields",
        "serial_no", "batch_no", "add_serial_batch_bundle",
        "add_serial_batch_for_rejected_qty",
        "rejected_serial_and_batch_bundle", "rejected_serial_no",

        // Asset
        "is_fixed_asset", "asset_location", "asset_category",
        "wip_composite_asset",

        // Subcontract
        "include_exploded_items", "bom",

        // Misc
        "page_break", "allow_zero_valuation_rate",
        "return_qty_from_rejected_warehouse",
        "from_warehouse", "manufacturer", "manufacturer_part_no",

        // Section breaks (item-level)
        "accounting_details_section", "accounting_dimensions_section",
        "item_weight_details", "manufacture_details",
        "subcontract_bom_section", "section_break_45",
        "section_break_3vxt",
    ];

    fields_to_hide.forEach(fn => {
        frm.fields_dict.items.grid.update_docfield_property(fn, "hidden", 1);
    });

    frm.fields_dict.items.grid.refresh();
}


