"""
Test that DB dependency now correctly uses tenant schema.
Simulates what happens when /orders/stats and /products/stats are called.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text, select, func
from app.database import engine, get_tenant_session


async def test():
    schema = "tenant_finaltest2026"

    # Simulate what TenantDB does - uses get_tenant_session
    async for session in get_tenant_session(schema):
        # Test order stats (what /orders/stats does)
        from app.models.order import Order
        total_orders = (await session.execute(select(func.count(Order.id)))).scalar()
        total_revenue = (await session.execute(
            select(func.sum(Order.total_amount)).where(
                func.upper(Order.payment_status) == "PAID"
            )
        )).scalar()
        total_customers = (await session.execute(
            select(func.count(func.distinct(Order.customer_id)))
        )).scalar()

        print(f"=== Tenant Schema ({schema}) ===")
        print(f"  Total Orders: {total_orders}")
        print(f"  Total Revenue: {total_revenue}")
        print(f"  Total Customers: {total_customers}")

        # Test product stats
        from app.models.product import Product
        total_products = (await session.execute(select(func.count(Product.id)))).scalar()
        print(f"  Total Products: {total_products}")

        if total_orders > 0 and total_products > 0:
            print("\n  FIX CONFIRMED: Data is accessible via tenant session!")
        else:
            print("\n  ISSUE: Still no data in tenant session")
        break


if __name__ == "__main__":
    asyncio.run(test())
