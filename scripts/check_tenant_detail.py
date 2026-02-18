"""
Detailed diagnostic: Check data quality in tenant schema.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.database import engine


async def check():
    schema = "tenant_finaltest2026"

    async with engine.connect() as conn:
        await conn.execute(text(f'SET search_path TO "{schema}"'))

        # 1. Check order payment_status distribution
        print("=== ORDERS: payment_status distribution ===")
        r = await conn.execute(text(
            "SELECT payment_status, COUNT(*) as cnt FROM orders GROUP BY payment_status"
        ))
        for row in r.fetchall():
            print(f"  {row.payment_status}: {row.cnt}")

        # 2. Check order status distribution
        print("\n=== ORDERS: status distribution ===")
        r = await conn.execute(text(
            "SELECT status, COUNT(*) as cnt FROM orders GROUP BY status"
        ))
        for row in r.fetchall():
            print(f"  {row.status}: {row.cnt}")

        # 3. Check total_amount sum for PAID orders
        print("\n=== REVENUE (PAID orders) ===")
        r = await conn.execute(text(
            "SELECT SUM(total_amount) as revenue FROM orders WHERE UPPER(payment_status) = 'PAID'"
        ))
        print(f"  Revenue (PAID): {r.scalar()}")

        r = await conn.execute(text(
            "SELECT SUM(total_amount) as revenue FROM orders"
        ))
        print(f"  Revenue (ALL): {r.scalar()}")

        # 4. Check sample orders
        print("\n=== SAMPLE ORDERS (first 5) ===")
        r = await conn.execute(text(
            "SELECT order_number, status, payment_status, total_amount, created_at FROM orders ORDER BY created_at DESC LIMIT 5"
        ))
        for row in r.fetchall():
            print(f"  {row.order_number} | status={row.status} | pay={row.payment_status} | total={row.total_amount} | {row.created_at}")

        # 5. Check products
        print("\n=== PRODUCTS ===")
        r = await conn.execute(text(
            "SELECT name, sku, status, is_active, selling_price FROM products LIMIT 5"
        ))
        for row in r.fetchall():
            print(f"  {row.name} | sku={row.sku} | status={row.status} | active={row.is_active} | price={row.selling_price}")

        # 6. Check warehouses
        print("\n=== WAREHOUSES ===")
        r = await conn.execute(text(
            "SELECT name, code, warehouse_type, is_active FROM warehouses"
        ))
        for row in r.fetchall():
            print(f"  {row.name} | code={row.code} | type={row.warehouse_type} | active={row.is_active}")

        # 7. Check inventory_summary
        print("\n=== INVENTORY SUMMARY (sample) ===")
        r = await conn.execute(text(
            "SELECT product_id, warehouse_id, total_quantity, available_quantity FROM inventory_summary LIMIT 5"
        ))
        for row in r.fetchall():
            print(f"  product={str(row.product_id)[:8]}... | wh={str(row.warehouse_id)[:8]}... | total={row.total_quantity} | avail={row.available_quantity}")

        # 8. Check snop_scenarios
        print("\n=== SNOP SCENARIOS ===")
        r = await conn.execute(text(
            "SELECT scenario_name, status, projected_revenue, projected_margin FROM snop_scenarios"
        ))
        for row in r.fetchall():
            print(f"  {row.scenario_name} | status={row.status} | revenue={row.projected_revenue} | margin={row.projected_margin}")

        # 9. Check user info
        print("\n=== USERS ===")
        r = await conn.execute(text(
            "SELECT email, first_name, last_name, is_active FROM users"
        ))
        for row in r.fetchall():
            print(f"  {row.email} | {row.first_name} {row.last_name} | active={row.is_active}")


if __name__ == "__main__":
    asyncio.run(check())
