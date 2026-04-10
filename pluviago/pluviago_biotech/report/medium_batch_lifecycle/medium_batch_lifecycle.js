frappe.query_reports["Medium Batch Lifecycle"] = {
    filters: [
        {
            fieldname: "final_medium_batch",
            label: __("Final Medium Batch"),
            fieldtype: "Link",
            options: "Final Medium Batch",
            reqd: 1
        }
    ],
    formatter: function(value, row, column, data, default_formatter) {
        value = default_formatter(value, row, column, data);
        if (data && data.bold) {
            value = `<strong>${value}</strong>`;
        }
        // Colour-code the QC/Status column
        if (column.fieldname === "qc_status" && data) {
            const v = (data.qc_status || "").toLowerCase();
            if (v.includes("passed") || v.includes("approved") || v.includes("released")) {
                value = `<span style="color: green; font-weight: bold;">${data.qc_status}</span>`;
            } else if (v.includes("failed") || v.includes("rejected") || v.includes("contaminated")) {
                value = `<span style="color: red; font-weight: bold;">${data.qc_status}</span>`;
            } else if (v.includes("pending") || v.includes("partially")) {
                value = `<span style="color: orange;">${data.qc_status}</span>`;
            }
        }
        return value;
    }
};
