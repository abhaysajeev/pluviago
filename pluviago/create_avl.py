import frappe

def run():
    # Check for any Workflow linked to Purchase Receipt
    wf = frappe.db.get_all("Workflow", filters={"document_type": "Purchase Receipt", "is_active": 1}, fields=["name", "workflow_state_field"])
    print("\n=== Active Workflows on Purchase Receipt ===")
    if not wf:
        print("  None found")
    for w in wf:
        print(f"  Workflow: {w.name} | State Field: {w.workflow_state_field}")
        states = frappe.get_all("Workflow Document State", filters={"parent": w.name}, fields=["state", "doc_status", "update_field", "update_value", "allow_edit"], order_by="idx")
        print("  States:")
        for s in states:
            print(f"    - {s.state} (docstatus={s.doc_status}, allow_edit={s.allow_edit})")
        transitions = frappe.get_all("Workflow Transition", filters={"parent": w.name}, fields=["state", "action", "next_state", "allowed"], order_by="idx")
        print("  Transitions:")
        for t in transitions:
            print(f"    - {t.state} --[{t.action}]--> {t.next_state} (by {t.allowed})")
