"""
Sync role_permissions table on PRODUCTION database.

This script:
1. Reads all existing roles from the database
2. Reads all existing permissions from the database
3. Assigns permissions to roles based on role level/department
4. Supports both permission code formats:
   - Legacy: "module:action" (lowercase with colon)
   - Production: "MODULE_ACTION" (uppercase with underscore)

Usage:
    DATABASE_URL="postgresql+psycopg://..." python -m scripts.sync_role_permissions
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


# Get DATABASE_URL from environment
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    print("ERROR: DATABASE_URL environment variable not set!")
    print("Usage: DATABASE_URL='postgresql+psycopg://...' python -m scripts.sync_role_permissions")
    sys.exit(1)


# Define what permissions each role should have
# Use generic action names that will be matched against actual permission codes
ROLE_PERMISSIONS = {
    "super_admin": "ALL",  # Gets all permissions

    "director": [
        # Strategic oversight - view access to everything, approval rights
        ("dashboard", "view"),
        ("products", "view"), ("products", "export"),
        ("orders", "view"), ("orders", "approve"), ("orders", "export"),
        ("inventory", "view"), ("inventory", "export"),
        ("service", "view"), ("service", "escalate"),
        ("crm", "view"), ("crm", "export"), ("customers", "view"), ("customers", "export"),
        ("complaints", "view"), ("complaints", "escalate"),
        ("vendors", "view"), ("vendors", "approve"),
        ("logistics", "view"), ("logistics", "track"),
        ("procurement", "view"), ("procurement", "approve"),
        ("purchase", "view"), ("purchase", "approve"),
        ("finance", "view"), ("finance", "approve"), ("finance", "export"),
        ("accounting", "view"), ("accounting", "approve"),
        ("billing", "view"), ("billing", "approve"),
        ("hr", "view"), ("hr", "approve"),
        ("marketing", "view"), ("marketing", "publish"),
        ("reports", "view"), ("reports", "export"), ("reports", "schedule"),
        ("notifications", "view"),
        ("settings", "view"),
        ("access_control", "view"),
    ],

    "sales_head": [
        ("dashboard", "view"),
        ("products", "view"), ("products", "export"),
        ("orders", "view"), ("orders", "create"), ("orders", "update"), ("orders", "approve"), ("orders", "export"),
        ("crm", "view"), ("crm", "create"), ("crm", "update"), ("crm", "export"),
        ("customers", "view"), ("customers", "create"), ("customers", "update"), ("customers", "export"),
        ("reports", "view"), ("reports", "export"),
        ("notifications", "view"),
    ],

    "service_head": [
        ("dashboard", "view"),
        ("products", "view"),
        ("service", "view"), ("service", "create"), ("service", "update"), ("service", "assign"), ("service", "close"), ("service", "escalate"),
        ("complaints", "view"), ("complaints", "create"), ("complaints", "update"), ("complaints", "assign"), ("complaints", "resolve"), ("complaints", "escalate"),
        ("crm", "view"), ("crm", "update"),
        ("customers", "view"), ("customers", "update"),
        ("inventory", "view"),
        ("reports", "view"), ("reports", "export"),
        ("notifications", "view"),
    ],

    "accounts_head": [
        ("dashboard", "view"),
        ("products", "view"),
        ("orders", "view"), ("orders", "export"),
        ("inventory", "view"), ("inventory", "adjust"), ("inventory", "export"),
        ("crm", "view"), ("crm", "export"),
        ("customers", "view"), ("customers", "export"),
        ("vendors", "view"), ("vendors", "create"), ("vendors", "update"),
        ("procurement", "view"), ("procurement", "receive"),
        ("purchase", "view"), ("purchase", "receive"),
        ("grn", "view"), ("grn", "create"), ("grn", "update"),
        ("finance", "view"), ("finance", "create"), ("finance", "update"), ("finance", "reconcile"), ("finance", "export"),
        ("accounting", "view"), ("accounting", "create"), ("accounting", "update"),
        ("billing", "view"), ("billing", "create"), ("billing", "update"),
        ("reports", "view"), ("reports", "export"),
        ("notifications", "view"),
        ("service", "view"),
    ],

    "finance_head": [
        ("dashboard", "view"),
        ("products", "view"), ("products", "export"),
        ("orders", "view"), ("orders", "create"), ("orders", "update"), ("orders", "approve"), ("orders", "export"),
        ("inventory", "view"), ("inventory", "adjust"), ("inventory", "export"),
        ("service", "view"),
        ("crm", "view"), ("crm", "export"),
        ("customers", "view"), ("customers", "export"),
        ("vendors", "view"), ("vendors", "create"), ("vendors", "update"), ("vendors", "approve"),
        ("logistics", "view"), ("logistics", "track"),
        ("procurement", "view"), ("procurement", "create"), ("procurement", "update"), ("procurement", "approve"), ("procurement", "receive"),
        ("purchase", "view"), ("purchase", "create"), ("purchase", "update"), ("purchase", "approve"), ("purchase", "receive"),
        ("grn", "view"), ("grn", "create"), ("grn", "update"), ("grn", "approve"),
        ("finance", "view"), ("finance", "create"), ("finance", "update"), ("finance", "approve"), ("finance", "reconcile"), ("finance", "export"),
        ("accounting", "view"), ("accounting", "create"), ("accounting", "update"), ("accounting", "approve"), ("accounting", "delete"),
        ("billing", "view"), ("billing", "create"), ("billing", "update"), ("billing", "approve"), ("billing", "delete"),
        ("hr", "view"),
        ("payroll", "view"), ("payroll", "process"), ("payroll", "approve"),
        ("marketing", "view"),
        ("reports", "view"), ("reports", "export"), ("reports", "schedule"), ("reports", "create"),
        ("notifications", "view"), ("notifications", "create"),
        ("settings", "view"),
        ("access_control", "view"),
    ],

    "operations_head": [
        ("dashboard", "view"),
        ("products", "view"), ("products", "update"),
        ("orders", "view"), ("orders", "update"),
        ("inventory", "view"), ("inventory", "create"), ("inventory", "update"), ("inventory", "transfer"), ("inventory", "adjust"), ("inventory", "export"),
        ("logistics", "view"), ("logistics", "create"), ("logistics", "update"), ("logistics", "assign"), ("logistics", "track"),
        ("procurement", "view"), ("procurement", "create"), ("procurement", "update"), ("procurement", "receive"),
        ("purchase", "view"), ("purchase", "create"), ("purchase", "update"), ("purchase", "receive"),
        ("grn", "view"), ("grn", "create"), ("grn", "update"),
        ("vendors", "view"), ("vendors", "create"), ("vendors", "update"),
        ("reports", "view"), ("reports", "export"),
        ("notifications", "view"),
    ],

    "regional_manager": [
        ("dashboard", "view"),
        ("products", "view"),
        ("orders", "view"), ("orders", "create"), ("orders", "update"), ("orders", "export"),
        ("crm", "view"), ("crm", "create"), ("crm", "update"),
        ("customers", "view"), ("customers", "create"), ("customers", "update"),
        ("complaints", "view"), ("complaints", "update"),
        ("reports", "view"), ("reports", "export"),
        ("notifications", "view"),
    ],

    "warehouse_manager": [
        ("dashboard", "view"),
        ("products", "view"),
        ("inventory", "view"), ("inventory", "create"), ("inventory", "update"), ("inventory", "transfer"), ("inventory", "adjust"),
        ("logistics", "view"), ("logistics", "create"), ("logistics", "assign"),
        ("procurement", "view"), ("procurement", "receive"),
        ("purchase", "view"), ("purchase", "receive"),
        ("grn", "view"), ("grn", "create"), ("grn", "update"),
        ("reports", "view"),
        ("notifications", "view"),
    ],

    "service_manager": [
        ("dashboard", "view"),
        ("products", "view"),
        ("service", "view"), ("service", "create"), ("service", "update"), ("service", "assign"), ("service", "close"),
        ("complaints", "view"), ("complaints", "update"), ("complaints", "assign"), ("complaints", "resolve"),
        ("crm", "view"), ("crm", "update"),
        ("customers", "view"), ("customers", "update"),
        ("inventory", "view"),
        ("reports", "view"),
        ("notifications", "view"),
    ],

    "marketing_manager": [
        ("dashboard", "view"),
        ("products", "view"),
        ("marketing", "view"), ("marketing", "create"), ("marketing", "update"), ("marketing", "delete"), ("marketing", "publish"),
        ("crm", "view"), ("crm", "export"),
        ("customers", "view"), ("customers", "export"),
        ("reports", "view"), ("reports", "export"),
        ("notifications", "view"), ("notifications", "create"), ("notifications", "send"),
    ],

    "customer_service_executive": [
        ("dashboard", "view"),
        ("products", "view"),
        ("service", "view"), ("service", "create"), ("service", "update"),
        ("complaints", "view"), ("complaints", "create"), ("complaints", "update"),
        ("crm", "view"), ("crm", "create"), ("crm", "update"),
        ("customers", "view"), ("customers", "create"), ("customers", "update"),
        ("orders", "view"),
        ("notifications", "view"),
    ],

    "sales_executive": [
        ("dashboard", "view"),
        ("products", "view"),
        ("orders", "view"), ("orders", "create"),
        ("crm", "view"), ("crm", "create"), ("crm", "update"),
        ("customers", "view"), ("customers", "create"), ("customers", "update"),
        ("inventory", "view"),
        ("notifications", "view"),
    ],

    "accounts_executive": [
        ("dashboard", "view"),
        ("orders", "view"),
        ("finance", "view"), ("finance", "create"), ("finance", "update"),
        ("accounting", "view"), ("accounting", "create"), ("accounting", "update"),
        ("billing", "view"), ("billing", "create"), ("billing", "update"),
        ("vendors", "view"),
        ("procurement", "view"),
        ("purchase", "view"),
        ("notifications", "view"),
    ],

    "technician_supervisor": [
        ("dashboard", "view"),
        ("products", "view"),
        ("service", "view"), ("service", "update"), ("service", "close"),
        ("complaints", "view"), ("complaints", "update"),
        ("inventory", "view"),
        ("logistics", "view"), ("logistics", "track"),
        ("notifications", "view"),
    ],
}


def normalize_permission(module: str, action: str) -> list:
    """
    Generate possible permission code formats for matching.
    Returns list of possible codes to check.
    """
    return [
        f"{module}:{action}",  # Legacy format: module:action
        f"{module.upper()}_{action.upper()}",  # Production format: MODULE_ACTION
        f"{module}_{action}",  # Lowercase underscore
        f"{module.upper()}:{action.upper()}",  # Uppercase colon
    ]


async def main():
    print("=" * 70)
    print("Sync Role Permissions on Production")
    print("=" * 70)
    print(f"Connecting to: {DATABASE_URL[:50]}...")

    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        try:
            # 1. Get all roles
            print("\n1. Fetching roles...")
            result = await session.execute(text("SELECT id, code, name FROM roles WHERE is_active = true"))
            roles = {row[1]: {"id": row[0], "name": row[2]} for row in result.fetchall()}
            print(f"   Found {len(roles)} active roles")
            for code, info in roles.items():
                print(f"   - {code}: {info['name']}")

            # 2. Get all permissions
            print("\n2. Fetching permissions...")
            result = await session.execute(
                text("SELECT id, code, name FROM permissions WHERE is_active = true")
            )
            permissions = {row[1]: {"id": row[0], "name": row[2]} for row in result.fetchall()}
            print(f"   Found {len(permissions)} active permissions")

            # Show sample permission codes to understand the format
            sample_codes = list(permissions.keys())[:5]
            print(f"   Sample codes: {sample_codes}")

            # 3. Get existing role_permissions
            print("\n3. Checking existing role_permissions...")
            result = await session.execute(
                text("SELECT role_id, permission_id FROM role_permissions")
            )
            existing = {(str(row[0]), str(row[1])) for row in result.fetchall()}
            print(f"   Found {len(existing)} existing assignments")

            # 4. Sync permissions for each role
            print("\n4. Syncing role permissions...")
            total_added = 0

            for role_code, perms in ROLE_PERMISSIONS.items():
                role_info = roles.get(role_code)
                if not role_info:
                    print(f"\n   SKIP: Role '{role_code}' not found in database")
                    continue

                role_id = str(role_info["id"])
                print(f"\n   Processing: {role_code} ({role_info['name']})")

                # Determine which permissions to assign
                if perms == "ALL":
                    perm_ids_to_assign = [str(p["id"]) for p in permissions.values()]
                else:
                    perm_ids_to_assign = []
                    for module, action in perms:
                        # Try to find matching permission code
                        possible_codes = normalize_permission(module, action)
                        found = False
                        for code in possible_codes:
                            if code in permissions:
                                perm_ids_to_assign.append(str(permissions[code]["id"]))
                                found = True
                                break
                        if not found:
                            # Try partial match
                            for perm_code in permissions.keys():
                                perm_lower = perm_code.lower().replace("_", ":")
                                target_lower = f"{module}:{action}"
                                if perm_lower == target_lower:
                                    perm_ids_to_assign.append(str(permissions[perm_code]["id"]))
                                    found = True
                                    break
                        # Don't warn for every missing permission - some may not exist

                # Count existing and new
                existing_count = sum(1 for pid in perm_ids_to_assign if (role_id, pid) in existing)
                new_perms = [pid for pid in perm_ids_to_assign if (role_id, pid) not in existing]

                print(f"      Existing: {existing_count}, New to add: {len(new_perms)}")

                # Add new permissions
                for perm_id in new_perms:
                    await session.execute(
                        text("""
                            INSERT INTO role_permissions (id, role_id, permission_id, created_at)
                            VALUES (:id, :role_id, :perm_id, NOW())
                            ON CONFLICT (role_id, permission_id) DO NOTHING
                        """),
                        {"id": uuid.uuid4(), "role_id": role_id, "perm_id": perm_id}
                    )
                    total_added += 1

            await session.commit()

            # 5. Verify final counts
            print("\n5. Verifying final state...")
            result = await session.execute(
                text("""
                    SELECT r.code, r.name, COUNT(rp.id) as perm_count
                    FROM roles r
                    LEFT JOIN role_permissions rp ON r.id = rp.role_id
                    WHERE r.is_active = true
                    GROUP BY r.id, r.code, r.name
                    ORDER BY r.code
                """)
            )
            print("\n   Role Permission Counts:")
            print("   " + "-" * 50)
            for row in result.fetchall():
                print(f"   {row[0]:30} : {row[2]} permissions")

            print("\n" + "=" * 70)
            print(f"SUCCESS! Added {total_added} new role-permission assignments")
            print("=" * 70)

        except Exception as e:
            await session.rollback()
            print(f"\nError: {e}")
            import traceback
            traceback.print_exc()
            raise
        finally:
            await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
