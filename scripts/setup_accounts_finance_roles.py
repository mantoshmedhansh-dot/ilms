"""
Setup Accounts Head and Finance Head roles with appropriate permissions.

This script:
1. Creates "Accounts Head" role (if not exists) - Day-to-day accounting operations
2. Updates "Finance Head" role - Strategic finance oversight
3. Assigns BOTH roles to accounts@aquapurite user

Role Definitions:
- Finance Head: Strategic - Budgets, Financial Planning, Treasury, High-value Approvals
- Accounts Head: Operational - Bookkeeping, Reconciliation, Compliance, Daily Accounting

Usage:
    python -m scripts.setup_accounts_finance_roles
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from app.database import async_session_factory, engine, Base
from app.models.module import Module
from app.models.permission import Permission, RolePermission
from app.models.role import Role, RoleLevel
from app.models.user import User, UserRole


# ==================== ACCOUNTS HEAD PERMISSIONS ====================
# Day-to-day operational accounting
ACCOUNTS_HEAD_PERMISSIONS = [
    # Dashboard
    "dashboard:view",

    # Products - View for cost tracking
    "products:view",

    # Orders - View and export for revenue tracking
    "orders:view",
    "orders:export",

    # Inventory - View and adjust for stock valuation
    "inventory:view",
    "inventory:adjust",
    "inventory:export",

    # CRM - View for customer accounting
    "crm:view",
    "crm:export",

    # Vendors - Full access for AP management
    "vendors:view",
    "vendors:create",
    "vendors:update",

    # Procurement - View and receive for purchase accounting
    "procurement:view",
    "procurement:receive",

    # Finance - Full operational access
    "finance:view",
    "finance:create",
    "finance:update",
    "finance:reconcile",
    "finance:export",

    # Reports - View and export
    "reports:view",
    "reports:export",

    # Notifications
    "notifications:view",
]

# ==================== FINANCE HEAD PERMISSIONS ====================
# Strategic finance oversight
FINANCE_HEAD_PERMISSIONS = [
    # Dashboard
    "dashboard:view",

    # Products - View and export for cost analysis
    "products:view",
    "products:export",

    # Orders - Full access for revenue management
    "orders:view",
    "orders:create",
    "orders:update",
    "orders:approve",
    "orders:export",

    # Inventory - View and export for valuation
    "inventory:view",
    "inventory:export",
    "inventory:adjust",

    # Service - View for service cost tracking
    "service:view",

    # CRM - View and export for customer financial data
    "crm:view",
    "crm:export",

    # Vendors - Full access including approvals
    "vendors:view",
    "vendors:create",
    "vendors:update",
    "vendors:approve",

    # Logistics - View for shipping cost tracking
    "logistics:view",
    "logistics:track",

    # Procurement - Full access including approvals
    "procurement:view",
    "procurement:create",
    "procurement:update",
    "procurement:approve",
    "procurement:receive",

    # Finance - Full access including approvals
    "finance:view",
    "finance:create",
    "finance:update",
    "finance:approve",
    "finance:reconcile",
    "finance:export",

    # HR - View for payroll data
    "hr:view",

    # Marketing - View for campaign costs
    "marketing:view",

    # Reports - Full access
    "reports:view",
    "reports:export",
    "reports:schedule",

    # Notifications
    "notifications:view",
    "notifications:create",

    # Settings - View for financial configurations
    "settings:view",
]


async def get_permissions(session) -> dict:
    """Get all permissions from database."""
    stmt = select(Permission)
    result = await session.execute(stmt)
    permissions = result.scalars().all()
    return {p.code: p for p in permissions}


async def create_or_update_role(session, role_code: str, role_name: str,
                                 department: str, description: str,
                                 permission_codes: list, permission_map: dict) -> Role:
    """Create or update a role with permissions."""
    print(f"\nSetting up {role_name} role...")

    # Get or create role
    stmt = select(Role).where(Role.code == role_code)
    result = await session.execute(stmt)
    role = result.scalar_one_or_none()

    if not role:
        print(f"  Creating new role: {role_name}")
        role = Role(
            name=role_name,
            code=role_code,
            description=description,
            level=RoleLevel.HEAD,
            department=department,
            is_system=True,
        )
        session.add(role)
        await session.flush()
    else:
        print(f"  Found existing role: {role.id}")

    # Get current permissions for this role
    stmt = select(RolePermission).where(RolePermission.role_id == role.id)
    result = await session.execute(stmt)
    existing_perm_ids = {rp.permission_id for rp in result.scalars().all()}
    print(f"  Current permissions: {len(existing_perm_ids)}")

    # Add missing permissions
    added_count = 0
    for perm_code in permission_codes:
        permission = permission_map.get(perm_code)
        if not permission:
            print(f"  Warning: Permission '{perm_code}' not found")
            continue

        if permission.id not in existing_perm_ids:
            role_perm = RolePermission(
                role_id=role.id,
                permission_id=permission.id,
            )
            session.add(role_perm)
            added_count += 1

    print(f"  Added {added_count} new permissions")
    print(f"  Total permissions: {len(existing_perm_ids) + added_count}")

    return role


async def assign_roles_to_user(session, user_email: str, roles: list):
    """Assign multiple roles to a user."""
    print(f"\nAssigning roles to {user_email}...")

    # Get user
    stmt = select(User).where(User.email == user_email)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        print(f"  User '{user_email}' not found!")
        print(f"  Note: You may need to run this on the production database")
        return

    print(f"  Found user: {user.first_name} {user.last_name} ({user.id})")

    # Get existing role assignments
    stmt = select(UserRole).where(UserRole.user_id == user.id)
    result = await session.execute(stmt)
    existing_role_ids = {ur.role_id for ur in result.scalars().all()}

    # Assign missing roles
    for role in roles:
        if role.id in existing_role_ids:
            print(f"  Already has: {role.name}")
        else:
            user_role = UserRole(
                user_id=user.id,
                role_id=role.id,
            )
            session.add(user_role)
            print(f"  + Assigned: {role.name}")


async def main():
    """Main function."""
    print("=" * 60)
    print("Setup Accounts Head and Finance Head Roles")
    print("=" * 60)

    async with async_session_factory() as session:
        try:
            # Get all permissions
            permission_map = await get_permissions(session)
            print(f"Found {len(permission_map)} permissions in database")

            # Create/Update Accounts Head role
            accounts_head = await create_or_update_role(
                session,
                role_code="accounts_head",
                role_name="Accounts Head",
                department="Finance",
                description="Head of Accounts - Day-to-day accounting operations, bookkeeping, reconciliation",
                permission_codes=ACCOUNTS_HEAD_PERMISSIONS,
                permission_map=permission_map,
            )

            # Create/Update Finance Head role
            finance_head = await create_or_update_role(
                session,
                role_code="finance_head",
                role_name="Finance Head",
                department="Finance",
                description="Head of Finance - Strategic finance oversight, budgets, planning, high-value approvals",
                permission_codes=FINANCE_HEAD_PERMISSIONS,
                permission_map=permission_map,
            )

            # Assign both roles to accounts user
            await assign_roles_to_user(
                session,
                "accounts@aquapurite.com",
                [accounts_head, finance_head]
            )

            # Commit changes
            await session.commit()

            print("\n" + "=" * 60)
            print("Setup completed successfully!")
            print("=" * 60)
            print("\nRole Summary:")
            print("\n  ACCOUNTS HEAD (Operational):")
            print("    - Day-to-day accounting & bookkeeping")
            print("    - Bank reconciliation")
            print("    - Vendor payments (create, no approve)")
            print("    - Financial data entry")
            print("    - Reports (view, export)")
            print(f"    - Permissions: {len(ACCOUNTS_HEAD_PERMISSIONS)}")
            print("\n  FINANCE HEAD (Strategic):")
            print("    - Financial planning & budgets")
            print("    - High-value approvals (orders, procurement, payments)")
            print("    - Vendor approvals")
            print("    - Full reports access (view, export, schedule)")
            print("    - System settings view")
            print(f"    - Permissions: {len(FINANCE_HEAD_PERMISSIONS)}")
            print("\n  Both roles assigned to: accounts@aquapurite.com")

        except Exception as e:
            await session.rollback()
            print(f"\nError: {e}")
            import traceback
            traceback.print_exc()
            raise


if __name__ == "__main__":
    asyncio.run(main())
