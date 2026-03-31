import frappe


def daily():
    """Daily scheduled tasks for Pluviago Biotech"""
    check_pending_qc()


def check_pending_qc():
    """Alert on Production Batches with QC pending for more than 2 days"""
    pending = frappe.db.sql(
        """
        SELECT name, current_stage, inoculation_date
        FROM `tabProduction Batch`
        WHERE stage_decision = 'Pending'
        AND docstatus = 1
        AND DATE(inoculation_date) <= DATE_SUB(CURDATE(), INTERVAL 2 DAY)
        """,
        as_dict=True
    )

    for batch in pending:
        frappe.publish_realtime(
            "msgprint",
            {
                "message": (
                    f"Production Batch {batch.name} ({batch.current_stage}) "
                    f"has pending QC decision for over 2 days."
                )
            },
            user="Administrator"
        )
