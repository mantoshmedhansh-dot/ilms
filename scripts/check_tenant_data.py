"""
Quick diagnostic: Check what data exists in the tenant schema.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.database import async_session_factory, engine


async def check():
    async with engine.connect() as conn:
        # 1. Find the tenant
        result = await conn.execute(text(
            "SELECT id, name, subdomain, database_schema, status FROM public.tenants"
        ))
        tenants = result.fetchall()
        print("=== TENANTS ===")
        for t in tenants:
            print(f"  {t.name} | subdomain={t.subdomain} | schema={t.database_schema} | status={t.status}")

        if not tenants:
            print("  No tenants found!")
            return

        # Find the finaltest tenant
        target = None
        for t in tenants:
            if 'finaltest' in t.subdomain.lower() or 'finaltest' in t.name.lower():
                target = t
                break

        if not target:
            target = tenants[0]
            print(f"\n  No 'finaltest' tenant found, using first: {target.name}")

        schema = target.database_schema
        print(f"\n=== CHECKING SCHEMA: {schema} ===")

        # Set search path
        await conn.execute(text(f'SET search_path TO "{schema}"'))

        # Check tables and counts
        tables_to_check = [
            'users', 'products', 'categories', 'brands', 'customers',
            'orders', 'order_items', 'warehouses', 'inventory_summary',
            'stock_items', 'demand_forecasts', 'snop_scenarios',
            'supply_plans', 'inventory_optimizations', 'channels',
            'regions'
        ]

        for table in tables_to_check:
            try:
                r = await conn.execute(text(f'SELECT COUNT(*) FROM "{table}"'))
                count = r.scalar()
                status = "OK" if count > 0 else "EMPTY"
                print(f"  {table}: {count} rows [{status}]")
            except Exception as e:
                print(f"  {table}: ERROR - {str(e)[:60]}")
                await conn.rollback()
                await conn.execute(text(f'SET search_path TO "{schema}"'))


if __name__ == "__main__":
    asyncio.run(check())
