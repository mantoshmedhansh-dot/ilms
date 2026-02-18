"""Seed dense historical order data for ML model training."""
import asyncio
import sys
import uuid
import random
from pathlib import Path
from datetime import datetime, timedelta, timezone, date
from decimal import Decimal

sys.path.insert(0, str(Path(__file__).parent.parent))
from sqlalchemy import text
from app.database import engine

# Products with prices
PRODUCTS = [
    ("450ee794-8f70-4fe1-a1ad-4c934d2e5de9", "Aquapurite RO 7-Stage", "APR-7S-001", 15999),
    ("132af918-71fd-4019-9a2f-8cc4660d6295", "Aquapurite UV+UF Classic", "AUC-001", 10999),
    ("c8515b79-7ab3-45df-a31f-4394b1238b4f", "HydroTech Commercial 500LPH", "HTC-500", 75000),
    ("d4f9f788-7536-4e03-89a7-df7c555f0393", "Aquapurite Alkaline Booster", "AAB-001", 19999),
    ("95c8a5c4-99c9-42c1-896e-5e9ec2f04637", "RO Membrane 75GPD", "ROM-75", 1999),
    ("20fbaf53-7c0e-445c-aa3d-1167624eae19", "Sediment Filter 10inch", "SF-10", 299),
    ("f1d5cf9d-5ac6-4d0e-ab41-330e4ece9cda", "Pre-Carbon Filter", "PCF-001", 449),
    ("42ecc1f9-17e7-4ec2-8da4-2839f5cc12c9", "Smart TDS Meter", "STM-001", 1199),
]

PAYMENT_METHODS = ["ONLINE", "COD", "UPI", "CARD", "BANK_TRANSFER"]
SOURCES = ["WEBSITE", "PHONE", "B2B", "MARKETPLACE"]
SHIPPING_ADDRESS = '{"name":"Customer","phone":"9876543210","address_line1":"123 Main St","city":"Mumbai","state":"Maharashtra","pincode":"400001","country":"India"}'


async def main():
    random.seed(42)

    async with engine.connect() as conn:
        await conn.execute(text('SET search_path TO "tenant_finaltest2026"'))

        # Get customers and warehouses
        r = await conn.execute(text("SELECT id FROM customers"))
        customers = [str(row[0]) for row in r.fetchall()]

        r = await conn.execute(text("SELECT id FROM warehouses WHERE is_active = true"))
        warehouses = [str(row[0]) for row in r.fetchall()]

        # Check existing order numbers to avoid conflicts
        r = await conn.execute(text("SELECT MAX(order_number) FROM orders"))
        max_num = r.scalar() or "ORD-0000"

        # Generate orders for every day from 2025-03-01 to 2026-02-16
        start_date = date(2025, 3, 1)
        end_date = date(2026, 2, 16)

        order_counter = 10000
        total_orders = 0
        total_items = 0
        batch_orders = []
        batch_items = []

        current = start_date
        while current <= end_date:
            # Seasonal demand: higher in summer (Apr-Jun) and winter (Nov-Jan)
            month = current.month
            if month in (4, 5, 6):  # Summer peak
                base_orders = random.randint(3, 7)
            elif month in (11, 12, 1):  # Winter peak
                base_orders = random.randint(3, 6)
            elif month in (7, 8, 9):  # Monsoon dip
                base_orders = random.randint(1, 4)
            else:
                base_orders = random.randint(2, 5)

            # Weekend dip
            if current.weekday() >= 5:
                base_orders = max(1, base_orders - 1)

            for _ in range(base_orders):
                order_id = str(uuid.uuid4())
                order_counter += 1
                order_number = f"ORD-{order_counter}"
                customer_id = random.choice(customers)
                warehouse_id = random.choice(warehouses)

                # Pick 1-3 products for this order
                num_products = random.choices([1, 2, 3], weights=[50, 35, 15])[0]
                selected = random.sample(PRODUCTS, min(num_products, len(PRODUCTS)))

                subtotal = Decimal("0")
                order_items_sql = []
                for prod_id, prod_name, sku, price in selected:
                    qty = random.randint(1, 5) if price < 5000 else random.randint(1, 2)
                    unit_price = Decimal(str(price)) * Decimal(str(random.uniform(0.9, 1.0)))
                    unit_price = round(unit_price, 2)
                    discount = round(unit_price * Decimal(str(random.uniform(0, 0.1))), 2)
                    tax_rate = Decimal("18.0")
                    line_total = (unit_price - discount) * qty
                    tax_amt = round(line_total * tax_rate / 100, 2)
                    item_total = round(line_total + tax_amt, 2)
                    subtotal += item_total

                    item_id = str(uuid.uuid4())
                    created_ts = datetime.combine(current, datetime.min.time()).replace(
                        hour=random.randint(8, 20),
                        minute=random.randint(0, 59),
                        tzinfo=timezone.utc,
                    )
                    batch_items.append(
                        f"('{item_id}','{order_id}','{prod_id}','{prod_name}','{sku}',"
                        f"{qty},{unit_price},{unit_price},{discount},{tax_rate},{tax_amt},"
                        f"{item_total},'84219900',12,'{created_ts.isoformat()}')"
                    )
                    total_items += 1

                tax_total = round(subtotal * Decimal("0.153"), 2)  # ~15.3% effective
                total_amount = subtotal
                order_ts = datetime.combine(current, datetime.min.time()).replace(
                    hour=random.randint(8, 20),
                    minute=random.randint(0, 59),
                    tzinfo=timezone.utc,
                )
                delivered_ts = order_ts + timedelta(days=random.randint(2, 7))
                payment_method = random.choice(PAYMENT_METHODS)

                batch_orders.append(
                    f"('{order_id}','{order_number}','{customer_id}','DELIVERED',"
                    f"'{random.choice(SOURCES)}','{warehouse_id}',"
                    f"{round(subtotal - tax_total, 2)},{tax_total},0,0,{total_amount},"
                    f"'{payment_method}','PAID',{total_amount},"
                    f"'{SHIPPING_ADDRESS}'::jsonb,"
                    f"'{order_ts.isoformat()}','{order_ts.isoformat()}',"
                    f"'{delivered_ts.isoformat()}')"
                )
                total_orders += 1

            current += timedelta(days=1)

            # Batch insert every 100 days
            if len(batch_orders) >= 300 or current > end_date:
                if batch_orders:
                    orders_sql = (
                        "INSERT INTO orders (id, order_number, customer_id, status, source, "
                        "warehouse_id, subtotal, tax_amount, discount_amount, shipping_amount, "
                        "total_amount, payment_method, payment_status, amount_paid, "
                        "shipping_address, created_at, updated_at, delivered_at) VALUES "
                        + ",".join(batch_orders)
                    )
                    await conn.execute(text(orders_sql))

                    items_sql = (
                        "INSERT INTO order_items (id, order_id, product_id, product_name, "
                        "product_sku, quantity, unit_price, unit_mrp, discount_amount, "
                        "tax_rate, tax_amount, total_amount, hsn_code, warranty_months, "
                        "created_at) VALUES "
                        + ",".join(batch_items)
                    )
                    await conn.execute(text(items_sql))
                    await conn.commit()
                    print(f"  Inserted batch: {len(batch_orders)} orders, {len(batch_items)} items (up to {current})")
                    batch_orders = []
                    batch_items = []

        print(f"\nTotal: {total_orders} orders, {total_items} items")

        # Verify
        r = await conn.execute(text("SELECT COUNT(*), COUNT(DISTINCT created_at::date) FROM orders"))
        row = r.fetchone()
        print(f"DB now has: {row[0]} orders across {row[1]} unique dates")


asyncio.run(main())
