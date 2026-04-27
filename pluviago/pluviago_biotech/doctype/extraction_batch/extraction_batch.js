frappe.ui.form.on('Extraction Batch', {
    refresh(frm) {
        if (frm.doc.docstatus === 1 && frm.doc.status === 'Dispatched') {
            frm.set_intro('Batch has been dispatched to extraction partner.', 'blue');

            frm.add_custom_button('Mark Extract Received', function() {
                frappe.prompt([
                    {
                        label: 'Received Date',
                        fieldname: 'received_date',
                        fieldtype: 'Date',
                        reqd: 1,
                        default: frappe.datetime.get_today()
                    },
                    {
                        label: 'Received By',
                        fieldname: 'received_by',
                        fieldtype: 'Link',
                        options: 'User',
                        reqd: 1,
                        default: frappe.session.user
                    }
                ], function(values) {
                    frappe.call({
                        method: 'mark_extract_received',
                        doc: frm.doc,
                        args: {
                            received_date: values.received_date,
                            received_by: values.received_by
                        },
                        freeze: true,
                        freeze_message: 'Marking extract as received...',
                        callback() { frm.reload_doc(); }
                    });
                }, 'Mark Extract Received', 'Confirm');
            }, 'Actions');
        }

        if (frm.doc.docstatus === 1 && frm.doc.status === 'Processing') {
            frm.set_intro('Extract received — awaiting repacking and final dispatch.', 'blue');

            frm.add_custom_button('Complete Extraction', function() {
                frappe.call({
                    method: 'complete_extraction',
                    doc: frm.doc,
                    freeze: true,
                    freeze_message: 'Completing extraction batch...',
                    callback() { frm.reload_doc(); }
                });
            }, 'Actions');
        }

        if (frm.doc.docstatus === 1 && frm.doc.status === 'Completed') {
            frm.set_intro('Extraction process completed.', 'green');
        }
    }
});
