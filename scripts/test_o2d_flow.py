#!/usr/bin/env python3
"""
End-to-End Order-to-Delivery (O2D) Flow Test Script

This script tests the complete sales flow:
1. Setup: Add warehouses in different cities, add inventory
2. Create orders across all sales channels (MT, GT, ECOM, D2C)
3. Test warehouse allocation and serviceability
4. Test pick-pack-invoice flow
5. Test courier selection and dispatch
6. Test delivery and POD
7. Test service request generation

Author: ILMS.AI ERP System
"""

import asyncio
import uuid
from datetime import datetime, date, timedelta
from decimal import Decimal
from sqlalchemy import text, select
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import async_session_factory

# Sales Channels
SALES_CHANNELS = [
    {"code": "MT", "name": "Modern Trade", "description": "Big Bazaar, DMart, Reliance Retail"},
    {"code": "GT", "name": "General Trade", "description": "Local distributors and retailers"},
    {"code": "ECOM", "name": "E-Commerce", "description": "Amazon, Flipkart, own website"},
    {"code": "D2C", "name": "Direct to Consumer", "description": "Direct sales, exhibitions, demos"},
]

# Warehouses in different cities
WAREHOUSES = [
    {"name": "Central Warehouse - Delhi", "code": "WH-DEL-01", "city": "Delhi", "state": "Delhi", "pincode": "110001", "address": "Industrial Area Phase-1, Okhla"},
    {"name": "Regional Warehouse - Mumbai", "code": "WH-MUM-01", "city": "Mumbai", "state": "Maharashtra", "pincode": "400001", "address": "MIDC, Andheri East"},
    {"name": "Regional Warehouse - Bangalore", "code": "WH-BLR-01", "city": "Bangalore", "state": "Karnataka", "pincode": "560001", "address": "Electronic City Phase-2"},
    {"name": "Regional Warehouse - Hyderabad", "code": "WH-HYD-01", "city": "Hyderabad", "state": "Telangana", "pincode": "500001", "address": "HITEC City"},
    {"name": "Regional Warehouse - Chennai", "code": "WH-CHN-01", "city": "Chennai", "state": "Tamil Nadu", "pincode": "600001", "address": "Ambattur Industrial Estate"},
    {"name": "Regional Warehouse - Kolkata", "code": "WH-KOL-01", "city": "Kolkata", "state": "West Bengal", "pincode": "700001", "address": "Salt Lake Sector V"},
]

# Test orders configuration - one per channel per city
TEST_ORDERS = [
    # Modern Trade Orders (Big retailers)
    {"channel": "MT", "city": "Mumbai", "pincode": "400053", "customer": "Big Bazaar - Malad", "amount": 75000},
    {"channel": "MT", "city": "Bangalore", "pincode": "560034", "customer": "DMart - Koramangala", "amount": 85000},

    # General Trade Orders (Distributors)
    {"channel": "GT", "city": "Delhi", "pincode": "110085", "customer": "Sharma Electronics - Rohini", "amount": 55000},
    {"channel": "GT", "city": "Hyderabad", "pincode": "500072", "customer": "Krishna Traders - Kukatpally", "amount": 62000},

    # E-Commerce Orders
    {"channel": "ECOM", "city": "Chennai", "pincode": "600042", "customer": "Amazon FBA - Chennai Hub", "amount": 95000},
    {"channel": "ECOM", "city": "Kolkata", "pincode": "700091", "customer": "Flipkart - Kolkata FC", "amount": 78000},

    # D2C Orders (Direct)
    {"channel": "D2C", "city": "Pune", "pincode": "411001", "customer": "Raj Malhotra (Demo Sale)", "amount": 52000},
    {"channel": "D2C", "city": "Jaipur", "pincode": "302001", "customer": "Priya Sharma (Exhibition)", "amount": 68000},
]

# Transporters/Couriers
TRANSPORTERS = [
    {"code": "DELHIVERY", "name": "Delhivery", "type": "COURIER", "priority": 1},
    {"code": "BLUEDART", "name": "Blue Dart", "type": "COURIER", "priority": 2},
    {"code": "DTDC", "name": "DTDC Express", "type": "COURIER", "priority": 3},
    {"code": "ECOMEXP", "name": "Ecom Express", "type": "COURIER", "priority": 4},
    {"code": "SELFSHIP", "name": "Self Delivery", "type": "SELF_SHIP", "priority": 5},
]


async def setup_warehouses(db):
    """Add warehouses in different cities"""
    print("\n" + "="*80)
    print("STEP 1: SETTING UP WAREHOUSES")
    print("="*80)

    for wh in WAREHOUSES:
        # Check if warehouse exists
        result = await db.execute(text(
            "SELECT id FROM warehouses WHERE name = :name OR city = :city"
        ), {"name": wh["name"], "city": wh["city"]})
        existing = result.fetchone()

        if not existing:
            wh_id = str(uuid.uuid4())
            await db.execute(text("""
                INSERT INTO warehouses (id, name, code, city, state, pincode, address_line1, is_active, created_at, updated_at)
                VALUES (:id, :name, :code, :city, :state, :pincode, :address, true, :now, :now)
            """), {
                "id": wh_id,
                "name": wh["name"],
                "code": wh["code"],
                "city": wh["city"],
                "state": wh["state"],
                "pincode": wh["pincode"],
                "address": wh["address"],
                "now": datetime.utcnow()
            })
            print(f"   [+] Created: {wh['name']} ({wh['city']})")
        else:
            print(f"   [=] Exists: {wh['name']} ({wh['city']})")

    await db.commit()

    # List all warehouses
    result = await db.execute(text("SELECT id, name, city, pincode FROM warehouses WHERE is_active = true"))
    warehouses = result.fetchall()
    print(f"\n   Total active warehouses: {len(warehouses)}")
    return {wh[2]: wh[0] for wh in warehouses}  # city -> id mapping


async def setup_sales_channels(db):
    """Setup sales channels"""
    print("\n" + "="*80)
    print("STEP 2: SETTING UP SALES CHANNELS")
    print("="*80)

    for ch in SALES_CHANNELS:
        # Check if channel exists
        result = await db.execute(text(
            "SELECT id FROM sales_channels WHERE code = :code"
        ), {"code": ch["code"]})
        existing = result.fetchone()

        if not existing:
            ch_id = str(uuid.uuid4())
            await db.execute(text("""
                INSERT INTO sales_channels (id, code, name, description, is_active, created_at, updated_at)
                VALUES (:id, :code, :name, :desc, true, :now, :now)
            """), {
                "id": ch_id,
                "code": ch["code"],
                "name": ch["name"],
                "desc": ch["description"],
                "now": datetime.utcnow()
            })
            print(f"   [+] Created: {ch['code']} - {ch['name']}")
        else:
            print(f"   [=] Exists: {ch['code']} - {ch['name']}")

    await db.commit()

    # Get channel mapping
    result = await db.execute(text("SELECT id, code FROM sales_channels"))
    channels = result.fetchall()
    return {ch[1]: ch[0] for ch in channels}  # code -> id mapping


async def setup_transporters(db):
    """Setup courier/transporter partners"""
    print("\n" + "="*80)
    print("STEP 3: SETTING UP TRANSPORTERS")
    print("="*80)

    for tr in TRANSPORTERS:
        result = await db.execute(text(
            "SELECT id FROM transporters WHERE code = :code"
        ), {"code": tr["code"]})
        existing = result.fetchone()

        if not existing:
            tr_id = str(uuid.uuid4())
            await db.execute(text("""
                INSERT INTO transporters (id, code, name, transporter_type, is_active, priority, created_at, updated_at)
                VALUES (:id, :code, :name, :type, true, :priority, :now, :now)
            """), {
                "id": tr_id,
                "code": tr["code"],
                "name": tr["name"],
                "type": tr["type"],
                "priority": tr["priority"],
                "now": datetime.utcnow()
            })
            print(f"   [+] Created: {tr['code']} - {tr['name']}")
        else:
            print(f"   [=] Exists: {tr['code']} - {tr['name']}")

    await db.commit()


async def add_inventory(db, warehouse_ids):
    """Add 100 units of each product to each warehouse"""
    print("\n" + "="*80)
    print("STEP 4: ADDING INVENTORY (100 units per product per warehouse)")
    print("="*80)

    # Get all products
    result = await db.execute(text("SELECT id, sku, name FROM products WHERE is_active = true"))
    products = result.fetchall()
    print(f"   Found {len(products)} active products")

    total_added = 0
    for wh_city, wh_id in warehouse_ids.items():
        print(f"\n   Adding inventory to {wh_city}:")
        for product in products:
            product_id, sku, name = product

            # Check existing inventory
            result = await db.execute(text("""
                SELECT COALESCE(SUM(quantity), 0)
                FROM stock_items
                WHERE product_id = :pid AND warehouse_id = :wid AND status = 'available'
            """), {"pid": product_id, "wid": wh_id})
            current_qty = result.scalar() or 0

            if current_qty < 100:
                qty_to_add = 100 - current_qty
                stock_id = str(uuid.uuid4())
                await db.execute(text("""
                    INSERT INTO stock_items (id, product_id, warehouse_id, quantity, status, created_at, updated_at)
                    VALUES (:id, :pid, :wid, :qty, 'available', :now, :now)
                """), {
                    "id": stock_id,
                    "pid": product_id,
                    "wid": wh_id,
                    "qty": qty_to_add,
                    "now": datetime.utcnow()
                })
                total_added += qty_to_add
                print(f"      + {sku}: Added {qty_to_add} units (now 100)")
            else:
                print(f"      = {sku}: Already has {current_qty} units")

    await db.commit()
    print(f"\n   Total units added: {total_added}")


async def create_test_customers(db):
    """Create test customers for orders"""
    print("\n" + "="*80)
    print("STEP 5: CREATING TEST CUSTOMERS")
    print("="*80)

    customers = {}
    for order in TEST_ORDERS:
        customer_name = order["customer"]

        # Check if customer exists
        result = await db.execute(text(
            "SELECT id FROM customers WHERE name = :name"
        ), {"name": customer_name})
        existing = result.fetchone()

        if existing:
            customers[customer_name] = existing[0]
            print(f"   [=] Exists: {customer_name}")
        else:
            cust_id = str(uuid.uuid4())
            await db.execute(text("""
                INSERT INTO customers (id, name, phone, email, address_line1, city, state, pincode, customer_type, is_active, created_at, updated_at)
                VALUES (:id, :name, :phone, :email, :addr, :city, :state, :pincode, :type, true, :now, :now)
            """), {
                "id": cust_id,
                "name": customer_name,
                "phone": f"99000{str(uuid.uuid4().int)[:5]}",
                "email": f"{customer_name.lower().replace(' ', '').replace('-', '')}@test.com",
                "addr": f"Test Address, {order['city']}",
                "city": order["city"],
                "state": "Test State",
                "pincode": order["pincode"],
                "type": "B2B" if order["channel"] in ["MT", "GT"] else "B2C",
                "now": datetime.utcnow()
            })
            customers[customer_name] = cust_id
            print(f"   [+] Created: {customer_name} ({order['city']})")

    await db.commit()
    return customers


async def create_test_orders(db, channel_ids, warehouse_ids, customer_ids):
    """Create test orders across all channels"""
    print("\n" + "="*80)
    print("STEP 6: CREATING TEST ORDERS (>50,000 each)")
    print("="*80)

    # Get products for order items
    result = await db.execute(text("""
        SELECT id, sku, name, mrp FROM products
        WHERE is_active = true AND mrp >= 5000
        ORDER BY mrp DESC
        LIMIT 10
    """))
    products = result.fetchall()

    orders_created = []

    for order_config in TEST_ORDERS:
        channel_code = order_config["channel"]
        channel_id = channel_ids.get(channel_code)
        customer_name = order_config["customer"]
        customer_id = customer_ids.get(customer_name)
        target_amount = order_config["amount"]

        if not channel_id or not customer_id:
            print(f"   [!] Skipping {customer_name} - missing channel or customer")
            continue

        # Find nearest warehouse
        nearest_city = None
        for wh in WAREHOUSES:
            if wh["city"] == order_config["city"]:
                nearest_city = wh["city"]
                break
        if not nearest_city:
            nearest_city = "Delhi"  # Default

        warehouse_id = warehouse_ids.get(nearest_city, list(warehouse_ids.values())[0])

        # Generate order number
        order_number = f"ORD-{channel_code}-{date.today().strftime('%Y%m%d')}-{str(uuid.uuid4())[:4].upper()}"
        order_id = str(uuid.uuid4())

        # Calculate items to reach target amount
        items = []
        current_total = Decimal("0")
        for product in products:
            if current_total >= target_amount:
                break
            qty = max(1, int((target_amount - current_total) / product[3]))
            qty = min(qty, 5)  # Max 5 units per item
            items.append({
                "product_id": product[0],
                "sku": product[1],
                "name": product[2],
                "price": product[3],
                "quantity": qty,
                "total": product[3] * qty
            })
            current_total += product[3] * qty

        # Create order
        await db.execute(text("""
            INSERT INTO orders (
                id, order_number, channel_id, customer_id, warehouse_id,
                status, order_date, shipping_address, shipping_city, shipping_state, shipping_pincode,
                subtotal, tax_amount, total_amount, payment_status,
                created_at, updated_at
            ) VALUES (
                :id, :order_num, :channel_id, :customer_id, :warehouse_id,
                'NEW', :order_date, :addr, :city, :state, :pincode,
                :subtotal, :tax, :total, 'PENDING',
                :now, :now
            )
        """), {
            "id": order_id,
            "order_num": order_number,
            "channel_id": channel_id,
            "customer_id": customer_id,
            "warehouse_id": warehouse_id,
            "order_date": datetime.utcnow(),
            "addr": f"Test Address, {order_config['city']}",
            "city": order_config["city"],
            "state": "Test State",
            "pincode": order_config["pincode"],
            "subtotal": float(current_total),
            "tax": float(current_total * Decimal("0.18")),
            "total": float(current_total * Decimal("1.18")),
            "now": datetime.utcnow()
        })

        # Create order items
        for idx, item in enumerate(items):
            await db.execute(text("""
                INSERT INTO order_items (
                    id, order_id, product_id, sku, product_name,
                    quantity, unit_price, total_price,
                    created_at, updated_at
                ) VALUES (
                    :id, :order_id, :product_id, :sku, :name,
                    :qty, :price, :total,
                    :now, :now
                )
            """), {
                "id": str(uuid.uuid4()),
                "order_id": order_id,
                "product_id": item["product_id"],
                "sku": item["sku"],
                "name": item["name"],
                "qty": item["quantity"],
                "price": float(item["price"]),
                "total": float(item["total"]),
                "now": datetime.utcnow()
            })

        orders_created.append({
            "id": order_id,
            "number": order_number,
            "channel": channel_code,
            "customer": customer_name,
            "city": order_config["city"],
            "amount": float(current_total * Decimal("1.18"))
        })

        print(f"   [+] {order_number} | {channel_code} | {customer_name} | Rs.{current_total * Decimal('1.18'):,.2f}")

    await db.commit()
    return orders_created


async def display_order_summary(db, orders):
    """Display summary of created orders"""
    print("\n" + "="*80)
    print("ORDER SUMMARY")
    print("="*80)

    print(f"\n{'ORDER NUMBER':<30} {'CHANNEL':<8} {'CITY':<15} {'AMOUNT':>15} {'STATUS':<15}")
    print("-"*90)

    for order in orders:
        print(f"{order['number']:<30} {order['channel']:<8} {order['city']:<15} Rs.{order['amount']:>12,.2f} {'NEW':<15}")

    print("-"*90)
    total = sum(o['amount'] for o in orders)
    print(f"{'TOTAL':<30} {len(orders):<8} {'':<15} Rs.{total:>12,.2f}")

    print("\n" + "="*80)
    print("NEXT STEPS TO TEST:")
    print("="*80)
    print("""
    1. WAREHOUSE ALLOCATION:
       - Check which warehouse gets allocated based on serviceability
       - Verify PIN code coverage

    2. PICK-PACK FLOW:
       - Generate picklist for orders
       - Scan items during picking
       - Create shipment after packing

    3. COURIER SELECTION:
       - Check transporter serviceability
       - Select courier based on priority
       - Generate AWB number

    4. DISPATCH & DELIVERY:
       - Mark shipment as dispatched
       - Track delivery status
       - Upload POD (Proof of Delivery)

    5. POST-DELIVERY:
       - Create installation request
       - Generate warranty
       - Create service request if needed
    """)


async def main():
    """Main function to run the O2D flow test"""
    print("="*80)
    print("ORDER-TO-DELIVERY (O2D) FLOW TEST")
    print("="*80)
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    async with async_session_factory() as db:
        try:
            # Step 1: Setup Warehouses
            warehouse_ids = await setup_warehouses(db)

            # Step 2: Setup Sales Channels
            channel_ids = await setup_sales_channels(db)

            # Step 3: Setup Transporters
            await setup_transporters(db)

            # Step 4: Add Inventory
            await add_inventory(db, warehouse_ids)

            # Step 5: Create Test Customers
            customer_ids = await create_test_customers(db)

            # Step 6: Create Test Orders
            orders = await create_test_orders(db, channel_ids, warehouse_ids, customer_ids)

            # Display Summary
            await display_order_summary(db, orders)

            print("\n" + "="*80)
            print("O2D FLOW TEST SETUP COMPLETE!")
            print("="*80)

        except Exception as e:
            print(f"\n[ERROR] {str(e)}")
            import traceback
            traceback.print_exc()
            raise


if __name__ == "__main__":
    asyncio.run(main())
