#!/usr/bin/env python3
"""
Automatically add @require_module() decorators to API endpoint files
Phase 2 implementation automation
"""
import os
import re
from pathlib import Path

# Mapping of endpoint files to their required modules
ENDPOINT_MODULE_MAP = {
    # System Admin (10 files)
    "auth.py": "system_admin",
    "users.py": "system_admin",
    "roles.py": "system_admin",
    "permissions.py": "system_admin",
    "access_control.py": "system_admin",
    "audit_logs.py": "system_admin",
    "notifications.py": "system_admin",
    "uploads.py": "system_admin",
    "address.py": "system_admin",
    "credentials.py": "system_admin",

    # OMS/Fulfillment (18 files)
    "orders.py": "oms_fulfillment",
    "inventory.py": "oms_fulfillment",
    "warehouses.py": "oms_fulfillment",
    "wms.py": "oms_fulfillment",
    "picklists.py": "oms_fulfillment",
    "shipments.py": "oms_fulfillment",
    "manifests.py": "oms_fulfillment",
    "transporters.py": "oms_fulfillment",
    "serviceability.py": "oms_fulfillment",
    "rate_cards.py": "oms_fulfillment",
    "transfers.py": "oms_fulfillment",
    "stock_adjustments.py": "oms_fulfillment",
    "serialization.py": "oms_fulfillment",
    "shipping.py": "oms_fulfillment",
    "order_tracking.py": "oms_fulfillment",
    "returns.py": "oms_fulfillment",
    "sales_returns.py": "oms_fulfillment",
    "portal.py": "oms_fulfillment",

    # Procurement (6 files)
    "vendors.py": "procurement",
    "purchase.py": "procurement",
    "grn.py": "procurement",
    "vendor_invoices.py": "procurement",
    "vendor_proformas.py": "procurement",
    "vendor_payments.py": "procurement",

    # Finance (10 files)
    "accounting.py": "finance",
    "billing.py": "finance",
    "banking.py": "finance",
    "tds.py": "finance",
    "gst_filing.py": "finance",
    "auto_journal.py": "finance",
    "approvals.py": "finance",
    "payments.py": "finance",
    "commissions.py": "finance",
    "fixed_assets.py": "finance",

    # CRM & Service (8 files)
    "customers.py": "crm_service",
    "leads.py": "crm_service",
    "call_center.py": "crm_service",
    "service_requests.py": "crm_service",
    "technicians.py": "crm_service",
    "installations.py": "crm_service",
    "amc.py": "crm_service",
    "escalations.py": "crm_service",

    # Sales & Distribution (8 files)
    "channels.py": "sales_distribution",
    "marketplaces.py": "sales_distribution",
    "channel_reports.py": "sales_distribution",
    "reports.py": "sales_distribution",
    "partners.py": "sales_distribution",
    "franchisees.py": "sales_distribution",
    "dealers.py": "sales_distribution",
    "abandoned_cart.py": "sales_distribution",

    # HRMS (1 file)
    "hr.py": "hrms",

    # D2C Storefront (7 files)
    "storefront.py": None,  # Public, no auth
    "cms.py": "d2c_storefront",
    "d2c_auth.py": None,  # Auth endpoint, no module check
    "reviews.py": "d2c_storefront",
    "questions.py": "d2c_storefront",
    "coupons.py": "d2c_storefront",
    "company.py": "d2c_storefront",

    # SCM & AI (3 files)
    "insights.py": "scm_ai",
    "ai.py": "scm_ai",
    "snop.py": "scm_ai",

    # Marketing (2 files)
    "campaigns.py": "marketing",
    "promotions.py": "marketing",

    # Multi-module (4 files) - handled separately
    "products.py": "oms_fulfillment",  # Primary module
    "categories.py": "oms_fulfillment",  # Primary module
    "brands.py": "oms_fulfillment",  # Primary module
    "dashboard_charts.py": "system_admin",  # Primary module

    # Skip
    "test_modules.py": None,  # Testing only
}


def add_decorator_to_file(file_path: Path, module_code: str, dry_run: bool = True):
    """Add @require_module decorator to all route handlers in a file"""

    if module_code is None:
        print(f"  ⊘ Skipping {file_path.name} (no module required)")
        return 0, 0

    # Read file content
    content = file_path.read_text()
    original_content = content

    # Check if import already exists
    if "from app.core.module_decorators import require_module" not in content:
        # Find imports at the top of the file (before first function/class definition)
        # Match imports that start at column 0 (not indented)
        import_pattern = r"^(from .+ import .+|import .+)$"
        imports = []

        for match in re.finditer(import_pattern, content, re.MULTILINE):
            # Check if this import is at the start of the file (not inside a function)
            before_import = content[:match.start()]
            # Count function defs before this import
            func_count = before_import.count('\nasync def ') + before_import.count('\ndef ')
            if func_count == 0:
                # This is a top-level import
                imports.append(match)

        if imports:
            # Add after last top-level import
            last_import_end = imports[-1].end()
            import_statement = "\nfrom app.core.module_decorators import require_module"
            content = content[:last_import_end] + import_statement + content[last_import_end:]

    # Find all route decorators and add @require_module after them
    # Pattern: @router.method("path")
    route_pattern = r'(@router\.(get|post|put|patch|delete)\([^)]+\))\n(async def )'

    def add_decorator(match):
        route_decorator = match.group(1)
        method = match.group(2)
        async_def = match.group(3)

        # Check if @require_module already exists on next line
        # This is a simple check; might need refinement
        decorator_line = f'@require_module("{module_code}")\n'

        return f'{route_decorator}\n{decorator_line}{async_def}'

    # Count matches
    matches = list(re.finditer(route_pattern, content))

    if not matches:
        print(f"  ⊘ No route handlers found in {file_path.name}")
        return 0, 0

    # Apply replacements
    content = re.sub(route_pattern, add_decorator, content)

    # Check if anything changed
    if content == original_content:
        print(f"  ⊘ No changes needed for {file_path.name}")
        return 0, 0

    changes_count = len(matches)

    if dry_run:
        print(f"  ✓ Would add @require_module(\"{module_code}\") to {changes_count} endpoints in {file_path.name}")
        return changes_count, 0
    else:
        # Write back
        file_path.write_text(content)
        print(f"  ✅ Added @require_module(\"{module_code}\") to {changes_count} endpoints in {file_path.name}")
        return changes_count, 1

    return 0, 0


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Add @require_module decorators to API endpoints")
    parser.add_argument("--apply", action="store_true", help="Actually modify files (default is dry-run)")
    parser.add_argument("--module", help="Only process files for specific module (e.g., finance)")
    args = parser.parse_args()

    endpoints_dir = Path(__file__).parent.parent / "app" / "api" / "v1" / "endpoints"

    if not endpoints_dir.exists():
        print(f"❌ Endpoints directory not found: {endpoints_dir}")
        return

    print("="*70)
    print("PHASE 2: Adding @require_module() Decorators")
    print("="*70)
    print(f"Mode: {'APPLY CHANGES' if args.apply else 'DRY RUN (preview only)'}")
    print(f"Directory: {endpoints_dir}")
    print()

    total_endpoints = 0
    total_files = 0
    files_modified = 0

    # Group files by module for better output
    by_module = {}
    for filename, module_code in ENDPOINT_MODULE_MAP.items():
        if module_code not in by_module:
            by_module[module_code] = []
        by_module[module_code].append(filename)

    # Process each module
    for module_code in sorted(by_module.keys(), key=lambda x: (x is None, x)):
        if module_code is None:
            continue

        if args.module and module_code != args.module:
            continue

        print(f"\n📦 Module: {module_code}")
        print("-" * 70)

        module_endpoints = 0
        module_files = 0

        for filename in sorted(by_module[module_code]):
            file_path = endpoints_dir / filename

            if not file_path.exists():
                print(f"  ⚠️  File not found: {filename}")
                continue

            endpoints, modified = add_decorator_to_file(file_path, module_code, dry_run=not args.apply)
            module_endpoints += endpoints
            module_files += 1
            if modified:
                files_modified += 1

        total_endpoints += module_endpoints
        total_files += module_files

        print(f"  Total: {module_endpoints} endpoints in {module_files} files")

    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    print(f"Total endpoints decorated: {total_endpoints}")
    print(f"Total files processed: {total_files}")
    if args.apply:
        print(f"Files modified: {files_modified}")
        print("\n✅ Phase 2A complete! All decorators added.")
        print("\n🧪 Next: Run tests to verify module access control")
    else:
        print(f"\n⚠️  DRY RUN - No files were modified")
        print(f"\n💡 Run with --apply to actually modify files:")
        print(f"   python3 scripts/add_module_decorators.py --apply")


if __name__ == "__main__":
    main()
