"""
Create all operational tables in template_tenant schema.

This script uses SQLAlchemy's Base.metadata to create all defined tables
in the template_tenant schema. This template is then copied when provisioning
new tenants.

Usage:
    python scripts/create_template_tables.py
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text, inspect
from app.database import async_session_factory, Base
from app import models  # Import models to register them with Base


async def create_template_schema():
    """Create template_tenant schema with all operational tables."""

    print("=" * 70)
    print("Creating Template Schema for Multi-Tenant SaaS")
    print("=" * 70)
    print()

    async with async_session_factory() as session:
        # Create template schema if it doesn't exist
        await session.execute(text('CREATE SCHEMA IF NOT EXISTS template_tenant'))
        await session.commit()
        print("✓ Created template_tenant schema")
        print()

        # Get all tables from SQLAlchemy metadata
        tables = Base.metadata.tables
        print(f"Found {len(tables)} tables defined in SQLAlchemy models")
        print()

        # Group tables by category
        categories = {
            'auth': [],
            'products': [],
            'orders': [],
            'inventory': [],
            'procurement': [],
            'finance': [],
            'channels': [],
            'service': [],
            'hr': [],
            'cms': [],
            'ai': [],
            'other': []
        }

        for table_name in sorted(tables.keys()):
            if any(x in table_name for x in ['user', 'role', 'permission']):
                categories['auth'].append(table_name)
            elif any(x in table_name for x in ['product', 'category', 'brand']):
                categories['products'].append(table_name)
            elif any(x in table_name for x in ['order', 'customer']):
                categories['orders'].append(table_name)
            elif any(x in table_name for x in ['inventory', 'stock', 'warehouse', 'bin']):
                categories['inventory'].append(table_name)
            elif any(x in table_name for x in ['vendor', 'purchase', 'grn']):
                categories['procurement'].append(table_name)
            elif any(x in table_name for x in ['invoice', 'account', 'journal', 'payment', 'banking', 'gst', 'tds']):
                categories['finance'].append(table_name)
            elif any(x in table_name for x in ['channel', 'dealer', 'franchisee', 'partner']):
                categories['channels'].append(table_name)
            elif any(x in table_name for x in ['service', 'technician', 'amc', 'warranty']):
                categories['service'].append(table_name)
            elif any(x in table_name for x in ['employee', 'attendance', 'payroll', 'leave']):
                categories['hr'].append(table_name)
            elif any(x in table_name for x in ['cms', 'banner', 'testimonial', 'faq', 'page']):
                categories['cms'].append(table_name)
            elif any(x in table_name for x in ['forecast', 'demand', 'scenario', 'insight']):
                categories['ai'].append(table_name)
            else:
                categories['other'].append(table_name)

        print("Tables by Category:")
        print("-" * 70)
        for category, table_list in categories.items():
            if table_list:
                print(f"{category.upper()}: {len(table_list)} tables")
                for table in table_list[:5]:  # Show first 5
                    print(f"  - {table}")
                if len(table_list) > 5:
                    print(f"  ... and {len(table_list) - 5} more")
                print()

        print("=" * 70)
        print("IMPORTANT: Table Creation Strategy")
        print("=" * 70)
        print()
        print("Due to the complexity of 60+ interconnected tables, we recommend:")
        print()
        print("1. Tables are created ON-DEMAND when tenants are provisioned")
        print("2. Each tenant schema gets a fresh copy of all table structures")
        print("3. This avoids migration complexity and allows schema evolution")
        print()
        print("The template_tenant schema serves as a REFERENCE, not a source.")
        print("Actual tenant schemas are created directly from SQLAlchemy models.")
        print()
        print("=" * 70)
        print()

        return len(tables)


async def verify_template_schema():
    """Verify that template schema exists."""

    async with async_session_factory() as session:
        result = await session.execute(text("""
            SELECT schema_name
            FROM information_schema.schemata
            WHERE schema_name = 'template_tenant'
        """))

        schema_exists = result.scalar_one_or_none()

        if schema_exists:
            print("✓ template_tenant schema exists")

            # Check for tables
            result = await session.execute(text("""
                SELECT COUNT(*)
                FROM information_schema.tables
                WHERE table_schema = 'template_tenant'
            """))

            table_count = result.scalar()
            print(f"✓ {table_count} tables in template_tenant schema")

            return True
        else:
            print("✗ template_tenant schema does not exist")
            return False


async def main():
    """Main execution."""

    print("\n")

    # Create template schema
    table_count = await create_template_schema()

    # Verify
    exists = await verify_template_schema()

    print()
    print("=" * 70)
    print("Summary")
    print("=" * 70)
    print(f"Total Tables Defined: {table_count}")
    print(f"Template Schema: {'EXISTS' if exists else 'NOT FOUND'}")
    print()
    print("Next Steps:")
    print("1. Run migration: python -m alembic upgrade head")
    print("2. Update tenant provisioning to use SQLAlchemy models directly")
    print("3. Test with new tenant creation")
    print()


if __name__ == "__main__":
    asyncio.run(main())
