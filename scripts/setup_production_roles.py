"""
Setup Accounts Head and Finance Head roles on PRODUCTION database.
Uses raw SQL with correct production permission codes (UPPERCASE format).

Usage:
    DATABASE_URL="postgresql+psycopg://..." python -m scripts.setup_production_roles
"""

import asyncio
import sys
import os
from pathlib import Path
import uuid

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text


# Get DATABASE_URL from environment - MUST be set
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    print("ERROR: DATABASE_URL environment variable not set!")
    print("Usage: DATABASE_URL='postgresql+psycopg://...' python -m scripts.setup_production_roles")
    sys.exit(1)


# Accounts Head permissions (day-to-day operations) - PRODUCTION FORMAT
ACCOUNTS_HEAD_PERMISSIONS = [
    "DASHBOARD_VIEW",
    "PRODUCTS_VIEW",
    "ORDERS_VIEW",
    "INVENTORY_VIEW",
    "CUSTOMERS_VIEW",
    "VENDORS_VIEW",
    "PROCUREMENT_VIEW",
    "PURCHASE_VIEW",
    "GRN_VIEW",
    "ACCOUNTING_VIEW", "ACCOUNTING_CREATE", "ACCOUNTING_UPDATE",
    "BILLING_VIEW", "BILLING_CREATE", "BILLING_UPDATE",
    "FINANCE_VIEW", "FINANCE_CREATE", "FINANCE_UPDATE",
    "REPORTS_VIEW",
    "SERVICE_VIEW",
]

# Finance Head permissions (strategic oversight) - PRODUCTION FORMAT
FINANCE_HEAD_PERMISSIONS = [
    "DASHBOARD_VIEW",
    "PRODUCTS_VIEW",
    "ORDERS_VIEW", "ORDERS_CREATE", "ORDERS_UPDATE",
    "INVENTORY_VIEW",
    "CUSTOMERS_VIEW",
    "VENDORS_VIEW", "VENDORS_CREATE", "VENDORS_UPDATE",
    "PROCUREMENT_VIEW", "PROCUREMENT_CREATE", "PROCUREMENT_UPDATE",
    "PURCHASE_VIEW", "PURCHASE_CREATE", "PURCHASE_UPDATE",
    "GRN_VIEW", "GRN_CREATE", "GRN_UPDATE",
    "ACCOUNTING_VIEW", "ACCOUNTING_CREATE", "ACCOUNTING_UPDATE", "ACCOUNTING_DELETE",
    "BILLING_VIEW", "BILLING_CREATE", "BILLING_UPDATE", "BILLING_DELETE",
    "FINANCE_VIEW", "FINANCE_CREATE", "FINANCE_UPDATE", "FINANCE_DELETE",
    "REPORTS_VIEW", "REPORTS_CREATE",
    "SERVICE_VIEW",
    "HR_VIEW",
    "PAYROLL_VIEW", "PAYROLL_PROCESS", "PAYROLL_APPROVE",
    "SETTINGS_VIEW",
]


async def setup_role(session, role_code: str, role_name: str, description: str, permissions: list):
    """Setup a role with permissions using raw SQL."""
    print(f"\nSetting up {role_name}...")

    # Check if role exists
    result = await session.execute(
        text("SELECT id FROM roles WHERE code = :code"),
        {"code": role_code}
    )
    row = result.fetchone()

    if row:
        role_id = row[0]
        print(f"  Role exists: {role_id}")
    else:
        # Create role
        role_id = uuid.uuid4()
        await session.execute(
            text("""
                INSERT INTO roles (id, name, code, description, level, department, is_system, is_active, created_at, updated_at)
                VALUES (:id, :name, :code, :description, 'HEAD', 'Finance', true, true, NOW(), NOW())
            """),
            {"id": role_id, "name": role_name, "code": role_code, "description": description}
        )
        print(f"  Created role: {role_id}")

    # Get existing permission assignments for this role
    result = await session.execute(
        text("SELECT permission_id FROM role_permissions WHERE role_id = :role_id"),
        {"role_id": role_id}
    )
    existing_perm_ids = {str(row[0]) for row in result.fetchall()}
    print(f"  Existing permissions: {len(existing_perm_ids)}")

    # Get permission IDs for the codes we want
    result = await session.execute(
        text("SELECT id, code FROM permissions WHERE code = ANY(:codes)"),
        {"codes": permissions}
    )
    perm_map = {row[1]: str(row[0]) for row in result.fetchall()}
    print(f"  Found {len(perm_map)} matching permissions")

    # Add missing permissions
    added = 0
    for perm_code in permissions:
        perm_id = perm_map.get(perm_code)
        if not perm_id:
            print(f"  Warning: Permission '{perm_code}' not found")
            continue
        if perm_id not in existing_perm_ids:
            await session.execute(
                text("""
                    INSERT INTO role_permissions (id, role_id, permission_id, created_at)
                    VALUES (:id, :role_id, :perm_id, NOW())
                """),
                {"id": uuid.uuid4(), "role_id": role_id, "perm_id": perm_id}
            )
            added += 1

    print(f"  Added {added} new permissions")
    print(f"  Total permissions: {len(existing_perm_ids) + added}")

    return role_id


async def assign_roles_to_user(session, email: str, role_ids: list):
    """Assign roles to user."""
    print(f"\nAssigning roles to {email}...")

    # Get user
    result = await session.execute(
        text("SELECT id, first_name, last_name FROM users WHERE email = :email"),
        {"email": email}
    )
    row = result.fetchone()

    if not row:
        print(f"  User not found!")
        return

    user_id = row[0]
    print(f"  Found user: {row[1]} {row[2]} ({user_id})")

    # Get existing role assignments
    result = await session.execute(
        text("SELECT role_id FROM user_roles WHERE user_id = :user_id"),
        {"user_id": user_id}
    )
    existing_role_ids = {str(row[0]) for row in result.fetchall()}

    # Assign missing roles (production schema: assigned_at instead of created_at)
    for role_id in role_ids:
        if str(role_id) in existing_role_ids:
            print(f"  Already has role: {role_id}")
        else:
            await session.execute(
                text("""
                    INSERT INTO user_roles (id, user_id, role_id, assigned_at, is_primary)
                    VALUES (:id, :user_id, :role_id, NOW(), false)
                """),
                {"id": uuid.uuid4(), "user_id": user_id, "role_id": role_id}
            )
            print(f"  + Assigned role: {role_id}")


async def main():
    print("=" * 60)
    print("Setup Accounts Head & Finance Head on Production")
    print("=" * 60)
    print(f"Connecting to: {DATABASE_URL[:50]}...")

    # Create engine directly with the provided URL
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        try:
            # Setup roles
            accounts_head_id = await setup_role(
                session,
                "accounts_head",
                "Accounts Head",
                "Head of Accounts - Day-to-day accounting, bookkeeping, reconciliation",
                ACCOUNTS_HEAD_PERMISSIONS
            )

            finance_head_id = await setup_role(
                session,
                "finance_head",
                "Finance Head",
                "Head of Finance - Strategic oversight, budgets, planning, approvals",
                FINANCE_HEAD_PERMISSIONS
            )

            # Assign to accounts user
            await assign_roles_to_user(
                session,
                "accounts@ilms.ai",
                [accounts_head_id, finance_head_id]
            )

            await session.commit()

            print("\n" + "=" * 60)
            print("SUCCESS! Roles configured on production.")
            print("=" * 60)

        except Exception as e:
            await session.rollback()
            print(f"\nError: {e}")
            raise
        finally:
            await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
