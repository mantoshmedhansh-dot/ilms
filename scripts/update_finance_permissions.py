"""
Script to add new granular finance permissions and update existing roles.
This script adds new finance sub-module permissions and assigns them to
Accounts Head, Finance Head, and Accounts Executive roles.

Usage:
    python -m scripts.update_finance_permissions
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from app.database import async_session_factory
from app.models.module import Module
from app.models.permission import Permission, RolePermission
from app.models.role import Role


# New modules to create (if they don't exist)
NEW_MODULES = [
    {"name": "Chart of Accounts", "code": "accounts", "description": "Ledger accounts management", "icon": "account_tree", "sort_order": 21},
    {"name": "Journal Entries", "code": "journals", "description": "Journal entry management", "icon": "book", "sort_order": 22},
    {"name": "Fixed Assets", "code": "assets", "description": "Fixed assets management", "icon": "business", "sort_order": 23},
    {"name": "Bank Reconciliation", "code": "bank_recon", "description": "Bank statement reconciliation", "icon": "account_balance", "sort_order": 24},
    {"name": "Cost Centers", "code": "cost_centers", "description": "Cost center management", "icon": "hub", "sort_order": 25},
    {"name": "Financial Periods", "code": "periods", "description": "Accounting period management", "icon": "date_range", "sort_order": 26},
    {"name": "GST Returns", "code": "gst", "description": "GST filing and reports", "icon": "receipt_long", "sort_order": 27},
    {"name": "TDS", "code": "tds", "description": "TDS management", "icon": "payments", "sort_order": 28},
]

# New permissions to create
NEW_PERMISSIONS = [
    # Chart of Accounts (4 permissions)
    ("accounts", "view", "View Chart of Accounts", "View ledger accounts"),
    ("accounts", "create", "Create Accounts", "Create new ledger accounts"),
    ("accounts", "update", "Update Accounts", "Modify ledger accounts"),
    ("accounts", "delete", "Delete Accounts", "Delete ledger accounts"),

    # Journal Entries (4 permissions)
    ("journals", "view", "View Journal Entries", "View journal entries"),
    ("journals", "create", "Create Journal Entries", "Create journal entries"),
    ("journals", "approve", "Approve Journal Entries", "Approve/post journal entries"),
    ("journals", "reverse", "Reverse Journal Entries", "Reverse posted entries"),

    # Fixed Assets (4 permissions)
    ("assets", "view", "View Fixed Assets", "View asset register"),
    ("assets", "create", "Create Fixed Assets", "Add new assets"),
    ("assets", "update", "Update Fixed Assets", "Modify asset details"),
    ("assets", "depreciate", "Run Depreciation", "Calculate depreciation"),

    # Bank Reconciliation (3 permissions)
    ("bank_recon", "view", "View Bank Reconciliation", "View bank statements"),
    ("bank_recon", "reconcile", "Perform Reconciliation", "Match bank transactions"),
    ("bank_recon", "import", "Import Bank Statements", "Import bank files"),

    # Cost Centers (3 permissions)
    ("cost_centers", "view", "View Cost Centers", "View cost centers"),
    ("cost_centers", "create", "Create Cost Centers", "Create cost centers"),
    ("cost_centers", "update", "Update Cost Centers", "Modify cost centers"),

    # Financial Periods (3 permissions)
    ("periods", "view", "View Financial Periods", "View accounting periods"),
    ("periods", "create", "Create Periods", "Create new periods"),
    ("periods", "close", "Close Periods", "Close accounting periods"),

    # GST Returns (4 permissions)
    ("gst", "view", "View GST Returns", "View GSTR-1/2A/3B"),
    ("gst", "generate", "Generate GST Returns", "Generate GST reports"),
    ("gst", "file", "File GST Returns", "Submit GST returns"),
    ("gst", "export", "Export GST Data", "Export GST files"),

    # TDS (3 permissions)
    ("tds", "view", "View TDS", "View TDS reports"),
    ("tds", "create", "Create TDS Entries", "Record TDS deductions"),
    ("tds", "file", "File TDS Returns", "Submit TDS returns"),
]

# Role permissions mapping
ROLE_PERMISSIONS = {
    "accounts_head": [
        # Full access to all finance sub-modules
        "accounts:view", "accounts:create", "accounts:update", "accounts:delete",
        "journals:view", "journals:create", "journals:approve", "journals:reverse",
        "assets:view", "assets:create", "assets:update", "assets:depreciate",
        "bank_recon:view", "bank_recon:reconcile", "bank_recon:import",
        "cost_centers:view", "cost_centers:create", "cost_centers:update",
        "periods:view", "periods:create", "periods:close",
        "gst:view", "gst:generate", "gst:file", "gst:export",
        "tds:view", "tds:create", "tds:file",
    ],
    "finance_head": [
        # Full access to all finance sub-modules (same as accounts head)
        "accounts:view", "accounts:create", "accounts:update", "accounts:delete",
        "journals:view", "journals:create", "journals:approve", "journals:reverse",
        "assets:view", "assets:create", "assets:update", "assets:depreciate",
        "bank_recon:view", "bank_recon:reconcile", "bank_recon:import",
        "cost_centers:view", "cost_centers:create", "cost_centers:update",
        "periods:view", "periods:create", "periods:close",
        "gst:view", "gst:generate", "gst:file", "gst:export",
        "tds:view", "tds:create", "tds:file",
    ],
    "accounts_executive": [
        # Limited access - view and create only (no approve/delete)
        "accounts:view", "accounts:create",
        "journals:view", "journals:create",
        "bank_recon:view",
        "gst:view", "gst:generate",
        "tds:view", "tds:create",
    ],
}


async def create_modules(session) -> dict:
    """Create new modules if they don't exist."""
    print("Creating new modules...")
    module_map = {}

    for module_data in NEW_MODULES:
        stmt = select(Module).where(Module.code == module_data["code"])
        existing = (await session.execute(stmt)).scalar_one_or_none()

        if existing:
            module_map[module_data["code"]] = existing
            print(f"  Module '{module_data['name']}' already exists")
        else:
            module = Module(**module_data)
            session.add(module)
            await session.flush()
            module_map[module_data["code"]] = module
            print(f"  Created module: {module_data['name']}")

    return module_map


async def create_permissions(session, module_map: dict) -> dict:
    """Create new permissions if they don't exist."""
    print("\nCreating new permissions...")
    permission_map = {}
    created_count = 0

    for module_code, action, name, description in NEW_PERMISSIONS:
        code = f"{module_code}:{action}"
        module = module_map.get(module_code)

        if not module:
            print(f"  Warning: Module '{module_code}' not found for permission '{code}'")
            continue

        stmt = select(Permission).where(Permission.code == code)
        existing = (await session.execute(stmt)).scalar_one_or_none()

        if existing:
            permission_map[code] = existing
        else:
            permission = Permission(
                name=name,
                code=code,
                description=description,
                module_id=module.id,
                action=action,
            )
            session.add(permission)
            await session.flush()
            permission_map[code] = permission
            created_count += 1
            print(f"  Created permission: {code}")

    print(f"  Created {created_count} new permissions")
    return permission_map


async def update_role_permissions(session, permission_map: dict):
    """Add new permissions to existing roles."""
    print("\nUpdating role permissions...")

    for role_code, perm_codes in ROLE_PERMISSIONS.items():
        # Get the role
        stmt = select(Role).where(Role.code == role_code)
        role = (await session.execute(stmt)).scalar_one_or_none()

        if not role:
            print(f"  Warning: Role '{role_code}' not found")
            continue

        print(f"  Updating role: {role.name}")
        added_count = 0

        for perm_code in perm_codes:
            permission = permission_map.get(perm_code)
            if not permission:
                continue

            # Check if already assigned
            stmt = select(RolePermission).where(
                RolePermission.role_id == role.id,
                RolePermission.permission_id == permission.id
            )
            existing = (await session.execute(stmt)).scalar_one_or_none()

            if not existing:
                role_perm = RolePermission(
                    role_id=role.id,
                    permission_id=permission.id,
                )
                session.add(role_perm)
                added_count += 1

        print(f"    Added {added_count} new permissions to {role.name}")


async def main():
    """Main function to run the update."""
    print("=" * 60)
    print("UPDATING FINANCE PERMISSIONS")
    print("=" * 60)

    async with async_session_factory() as session:
        try:
            # Step 1: Create modules
            module_map = await create_modules(session)

            # Step 2: Create permissions
            permission_map = await create_permissions(session, module_map)

            # Step 3: Update role permissions
            await update_role_permissions(session, permission_map)

            # Commit all changes
            await session.commit()

            print("\n" + "=" * 60)
            print("UPDATE COMPLETED SUCCESSFULLY")
            print("=" * 60)
            print("\nNew permissions have been added to:")
            print("  - Accounts Head (full finance access)")
            print("  - Finance Head (full finance access)")
            print("  - Accounts Executive (limited access)")
            print("\nPlease log out and log back in to see the changes.")

        except Exception as e:
            await session.rollback()
            print(f"\nError: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(main())
