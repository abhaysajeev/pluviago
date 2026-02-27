"""
Master Setup Script - Run All Phases
Pluviago Biotech ERPNext Implementation

Usage:
    bench --site <site_name> execute pluviago.setup.run_all_phases.execute
"""

import frappe


def execute():
    print("\n" + "=" * 80)
    print("  PLUVIAGO BIOTECH - COMPLETE SYSTEM SETUP")
    print("  Running All Phases (1-7)")
    print("=" * 80 + "\n")

    phases = [
        ("Phase 1: Master Data", "pluviago.setup.phase1.execute"),
        ("Phase 2: Custom Configuration", "pluviago.setup.phase2.execute"),
        ("Phase 3: Automation Flows", "pluviago.setup.phase3.execute"),
        ("Phase 4: Print Formats & Reports", "pluviago.setup.phase4.execute"),
        ("Phase 5: Asset Management", "pluviago.setup.phase5.execute"),
        ("Phase 6: RBAC Permissions", "pluviago.setup.phase6.execute"),
        ("Phase 7: HR Basics", "pluviago.setup.phase7.execute"),
    ]

    completed = []
    failed = []

    for phase_name, module_path in phases:
        try:
            print(f"\n{'=' * 80}")
            print(f"  Starting {phase_name}")
            print(f"{'=' * 80}\n")
            frappe.call(module_path)
            frappe.db.commit()
            completed.append(phase_name)
            print(f"\n✅ {phase_name} - COMPLETED\n")
        except Exception as e:
            frappe.db.rollback()
            failed.append((phase_name, str(e)))
            print(f"\n❌ {phase_name} - FAILED")
            print(f"   Error: {str(e)[:200]}\n")

    print("\n" + "=" * 80)
    print("  SETUP SUMMARY")
    print("=" * 80)
    print(f"\n✅ Completed: {len(completed)}/{len(phases)} phases")
    for phase in completed:
        print(f"   ✓ {phase}")

    if failed:
        print(f"\n❌ Failed: {len(failed)}/{len(phases)} phases")
        for phase_name, error in failed:
            print(f"   ✗ {phase_name}")
            print(f"     Error: {error[:150]}...")
    else:
        print("\n🎉 ALL PHASES COMPLETED SUCCESSFULLY!")
        print("\n" + "=" * 80)
        print("  NEXT STEPS:")
        print("=" * 80)
        print("  1. Create BOMs for each production stage via UI")
        print("  2. Assign roles to users (Settings → User → Roles tab)")
        print("  3. Test workflows and automation")
        print("  4. Generate reports and verify print formats")
        print("=" * 80 + "\n")
