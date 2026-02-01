"""
Update Finance Head role with comprehensive permissions.

This script expands the Finance Head role to have full access to:
- Finance (accounting, billing, payments)
- Inventory (for stock valuation)
- Procurement (for AP/AR)
- Vendors (for supplier management)
- Orders (for revenue tracking)
- CRM (for customer financial data)
- Reports (all financial reports)

Also assigns Finance Head role to accounts@aquapurite user.

Usage:
    python -m scripts.update_finance_head_permissions
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


# Comprehensive Finance Head permissions
FINANCE_HEAD_PERMISSIONS = [
    # Dashboard
    "dashboard:view",

    # Products - View and export for cost tracking
    "products:view",
    "products:export",

    # Orders - Full access for revenue tracking
    "orders:view",
    "orders:create",
    "orders:update",
    "orders:approve",
    "orders:export",

    # Inventory - View and export for stock valuation
    "inventory:view",
    "inventory:export",
    "inventory:adjust",  # For stock write-offs

    # Service - View for service cost tracking
    "service:view",

    # CRM - View and export for customer financial data
    "crm:view",
    "crm:export",

    # Vendors - Full access for AP management
    "vendors:view",
    "vendors:create",
    "vendors:update",
    "vendors:approve",

    # Logistics - View for shipping cost tracking
    "logistics:view",
    "logistics:track",

    # Procurement - Full access for purchase management
    "procurement:view",
    "procurement:create",
    "procurement:update",
    "procurement:approve",
    "procurement:receive",

    # Finance - Full access
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


async def get_or_create_permissions(session) -> dict:
    """Get all permissions from database."""
    stmt = select(Permission)
    result = await session.execute(stmt)
    permissions = result.scalars().all()
    return {p.code: p for p in permissions}


async def update_finance_head_role(session, permission_map: dict):
    """Update Finance Head role with comprehensive permissions."""
    print("Updating Finance Head role...")

    # Get Finance Head role
    stmt = select(Role).where(Role.code == "finance_head")
    result = await session.execute(stmt)
    finance_head = result.scalar_one_or_none()

    if not finance_head:
        print("  Finance Head role not found! Creating it...")
        finance_head = Role(
            name="Finance Head",
            code="finance_head",
            description="Head of Finance department with comprehensive financial access",
            level=RoleLevel.HEAD,
            department="Finance",
            is_system=True,
        )
        session.add(finance_head)
        await session.flush()
        print("  Created Finance Head role")
    else:
        print(f"  Found Finance Head role: {finance_head.id}")

    # Get current permissions for this role
    stmt = select(RolePermission).where(RolePermission.role_id == finance_head.id)
    result = await session.execute(stmt)
    existing_role_perms = {rp.permission_id for rp in result.scalars().all()}
    print(f"  Current permissions count: {len(existing_role_perms)}")

    # Add missing permissions
    added_count = 0
    for perm_code in FINANCE_HEAD_PERMISSIONS:
        permission = permission_map.get(perm_code)
        if not permission:
            print(f"  Warning: Permission '{perm_code}' not found in database")
            continue

        if permission.id not in existing_role_perms:
            role_perm = RolePermission(
                role_id=finance_head.id,
                permission_id=permission.id,
            )
            session.add(role_perm)
            added_count += 1
            print(f"  + Added: {perm_code}")

    print(f"  Added {added_count} new permissions to Finance Head role")
    print(f"  Total permissions: {len(existing_role_perms) + added_count}")

    return finance_head


async def assign_finance_head_to_user(session, finance_head_role: Role, email: str):
    """Assign Finance Head role to a user."""
    print(f"\nAssigning Finance Head role to {email}...")

    # Get user
    stmt = select(User).where(User.email == email)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        print(f"  User '{email}' not found!")
        return

    print(f"  Found user: {user.first_name} {user.last_name} ({user.id})")

    # Check if already has Finance Head role
    stmt = select(UserRole).where(
        UserRole.user_id == user.id,
        UserRole.role_id == finance_head_role.id
    )
    result = await session.execute(stmt)
    existing_role = result.scalar_one_or_none()

    if existing_role:
        print(f"  User already has Finance Head role")
        return

    # Assign the role
    user_role = UserRole(
        user_id=user.id,
        role_id=finance_head_role.id,
    )
    session.add(user_role)
    print(f"  Assigned Finance Head role to {email}")


async def main():
    """Main function."""
    print("=" * 60)
    print("Update Finance Head Permissions")
    print("=" * 60)

    async with async_session_factory() as session:
        try:
            # Get all permissions
            permission_map = await get_or_create_permissions(session)
            print(f"Found {len(permission_map)} permissions in database")

            # Update Finance Head role
            finance_head = await update_finance_head_role(session, permission_map)

            # Assign to accounts user
            await assign_finance_head_to_user(session, finance_head, "accounts@aquapurite.com")

            # Commit changes
            await session.commit()

            print("\n" + "=" * 60)
            print("Update completed successfully!")
            print("=" * 60)
            print("\nFinance Head now has comprehensive permissions for:")
            print("  - Finance & Accounting (full access)")
            print("  - Orders & Revenue (view, create, approve, export)")
            print("  - Inventory & Stock (view, adjust, export)")
            print("  - Procurement & Purchasing (full access)")
            print("  - Vendors & Suppliers (full access)")
            print("  - CRM & Customers (view, export)")
            print("  - Reports & Analytics (full access)")

        except Exception as e:
            await session.rollback()
            print(f"\nError: {e}")
            import traceback
            traceback.print_exc()
            raise


if __name__ == "__main__":
    asyncio.run(main())
