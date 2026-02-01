"""
O2D Flow Test Setup Script
--------------------------
1. Add 100 units inventory for each product (serialized)
2. Create test orders across all channels (> Rs. 50,000 each)
3. Test the complete Order-to-Delivery flow
"""
import asyncio
import uuid
from datetime import datetime, timedelta
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

DATABASE_URL = "sqlite+aiosqlite:///consumer_durable.db"

# Test customers in different cities
TEST_CUSTOMERS = [
    {"first_name": "Rajesh", "last_name": "Kumar", "phone": "9876543001", "email": "rajesh@test.com", "city": "Delhi", "state": "Delhi", "pincode": "110001"},
    {"first_name": "Priya", "last_name": "Sharma", "phone": "9876543002", "email": "priya@test.com", "city": "Mumbai", "state": "Maharashtra", "pincode": "400001"},
    {"first_name": "Amit", "last_name": "Patel", "phone": "9876543003", "email": "amit@test.com", "city": "Bangalore", "state": "Karnataka", "pincode": "560001"},
    {"first_name": "Sunita", "last_name": "Reddy", "phone": "9876543004", "email": "sunita@test.com", "city": "Hyderabad", "state": "Telangana", "pincode": "500001"},
    {"first_name": "Vijay", "last_name": "Singh", "phone": "9876543005", "email": "vijay@test.com", "city": "Chennai", "state": "Tamil Nadu", "pincode": "600001"},
    {"first_name": "Neha", "last_name": "Gupta", "phone": "9876543006", "email": "neha@test.com", "city": "Kolkata", "state": "West Bengal", "pincode": "700001"},
    {"first_name": "Rahul", "last_name": "Verma", "phone": "9876543007", "email": "rahul@test.com", "city": "Pune", "state": "Maharashtra", "pincode": "411001"},
    {"first_name": "Anita", "last_name": "Joshi", "phone": "9876543008", "email": "anita@test.com", "city": "Ahmedabad", "state": "Gujarat", "pincode": "380001"},
]

# Order sources mapping to channels
ORDER_SOURCES = ["WEBSITE", "AMAZON", "FLIPKART", "DEALER"]


async def setup_test_data():
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        print("=" * 80)
        print("O2D FLOW TEST SETUP")
        print("=" * 80)

        # 1. Get warehouse
        print("\n1. FETCHING WAREHOUSE...")
        result = await db.execute(text("SELECT id, name FROM warehouses WHERE is_active = true LIMIT 1"))
        warehouse = result.fetchone()
        if not warehouse:
            print("   ERROR: No active warehouse found!")
            return
        warehouse_id = warehouse[0]
        print(f"   Using warehouse: {warehouse[1]} ({warehouse_id})")

        # 2. Get all products
        print("\n2. FETCHING PRODUCTS...")
        result = await db.execute(text("SELECT id, sku, name, mrp FROM products WHERE is_active = true"))
        products = result.fetchall()
        print(f"   Found {len(products)} active products")

        # 3. Check existing inventory
        result = await db.execute(text("SELECT COUNT(*) FROM stock_items"))
        existing_count = result.scalar()
        print(f"   Existing inventory: {existing_count} items")

        # 4. Add 100 units for each product (only if not already added)
        if existing_count < 100:
            print("\n3. ADDING INVENTORY (100 units per product)...")
            total_added = 0

            for product in products:
                product_id, sku, name, mrp = product
                print(f"   Adding 100 units of {sku}: {name[:40]}...")

                for i in range(1, 101):
                    stock_id = str(uuid.uuid4())
                    serial = f"{sku}-2026-{i:05d}"
                    barcode = f"AP{sku.replace('-', '')}{i:05d}"

                    await db.execute(text("""
                        INSERT INTO stock_items (
                            id, product_id, warehouse_id, serial_number, barcode,
                            status, purchase_price, landed_cost,
                            received_date, quality_grade, inspection_status,
                            created_at, updated_at
                        ) VALUES (
                            :id, :product_id, :warehouse_id, :serial, :barcode,
                            'AVAILABLE', :cost, :landed,
                            :received, 'A', 'PASSED',
                            :now, :now
                        )
                    """), {
                        "id": stock_id,
                        "product_id": product_id,
                        "warehouse_id": warehouse_id,
                        "serial": serial,
                        "barcode": barcode,
                        "cost": float(mrp) * 0.4 if mrp else 5000,  # 40% of MRP as cost
                        "landed": float(mrp) * 0.45 if mrp else 5500,  # 45% of MRP as landed cost
                        "received": datetime.now(),
                        "now": datetime.now()
                    })
                    total_added += 1

            await db.commit()
            print(f"   TOTAL INVENTORY ADDED: {total_added} items")
        else:
            print(f"   Inventory already exists ({existing_count} items), skipping...")

        # 5. Check if test customers exist, create if not
        print("\n4. SETTING UP TEST CUSTOMERS...")
        customer_ids = []
        for i, cust in enumerate(TEST_CUSTOMERS):
            result = await db.execute(text(
                "SELECT id FROM customers WHERE phone = :phone"
            ), {"phone": cust["phone"]})
            existing = result.fetchone()

            full_name = f"{cust['first_name']} {cust['last_name']}"
            if existing:
                customer_ids.append(existing[0])
                print(f"   Found: {full_name} ({cust['city']})")
            else:
                cust_id = str(uuid.uuid4())
                customer_code = f"TEST-{i+1:04d}"
                await db.execute(text("""
                    INSERT INTO customers (
                        id, customer_code, first_name, last_name, phone, email,
                        customer_type, source, is_active, is_verified,
                        created_at, updated_at
                    ) VALUES (
                        :id, :code, :first_name, :last_name, :phone, :email,
                        'INDIVIDUAL', 'WEBSITE', true, true,
                        :now, :now
                    )
                """), {
                    "id": cust_id,
                    "code": customer_code,
                    "first_name": cust["first_name"],
                    "last_name": cust["last_name"],
                    "phone": cust["phone"],
                    "email": cust["email"],
                    "now": datetime.now()
                })
                customer_ids.append(cust_id)
                print(f"   Created: {full_name} ({cust['city']})")

        await db.commit()

        # 5. Create test orders (one per channel, > Rs. 50,000 each)
        print("\n5. CREATING TEST ORDERS (> Rs. 50,000 each)...")

        # Get high-value products (MRP >= 10000)
        result = await db.execute(text(
            "SELECT id, sku, name, mrp FROM products WHERE mrp >= 10000 AND is_active = true ORDER BY mrp DESC"
        ))
        high_value_products = result.fetchall()

        if not high_value_products:
            print("   ERROR: No high-value products found!")
            return

        # Check existing test orders
        result = await db.execute(text("SELECT COUNT(*) FROM orders WHERE order_number LIKE 'TEST-%'"))
        existing_orders = result.scalar()

        if existing_orders >= 8:
            print(f"   Test orders already exist ({existing_orders}), skipping...")
        else:
            import json
            orders_created = []
            source_index = 0

            for i, (cust_id, cust_data) in enumerate(zip(customer_ids, TEST_CUSTOMERS)):
                # Rotate through order sources
                source = ORDER_SOURCES[source_index % len(ORDER_SOURCES)]
                source_index += 1

                order_id = str(uuid.uuid4())
                order_number = f"TEST-{source}-{datetime.now().strftime('%Y%m%d')}-{i+1:03d}"

                # Select products to reach > Rs. 50,000
                # Use 2 high-value products
                prod1 = high_value_products[i % len(high_value_products)]
                prod2 = high_value_products[(i + 1) % len(high_value_products)]

                subtotal = float(prod1[3]) + float(prod2[3])  # MRP of both products
                tax_amount = subtotal * 0.18  # 18% GST
                total_amount = subtotal + tax_amount

                # Shipping address as JSON
                full_name = f"{cust_data['first_name']} {cust_data['last_name']}"
                shipping_address = json.dumps({
                    "name": full_name,
                    "phone": cust_data["phone"],
                    "email": cust_data["email"],
                    "address_line1": f"123 Test Street",
                    "address_line2": f"Sector 15",
                    "city": cust_data["city"],
                    "state": cust_data["state"],
                    "pincode": cust_data["pincode"],
                    "country": "India"
                })

                # Create order
                await db.execute(text("""
                    INSERT INTO orders (
                        id, order_number, customer_id, source,
                        status, payment_status, payment_method, amount_paid,
                        subtotal, tax_amount, shipping_amount, discount_amount, total_amount,
                        shipping_address, internal_notes,
                        created_at, updated_at
                    ) VALUES (
                        :id, :order_number, :customer_id, :source,
                        'NEW', 'PAID', 'PREPAID', :total,
                        :subtotal, :tax, 0, 0, :total,
                        :shipping_address, :notes,
                        :now, :now
                    )
                """), {
                    "id": order_id,
                    "order_number": order_number,
                    "customer_id": cust_id,
                    "source": source,
                    "subtotal": subtotal,
                    "tax": tax_amount,
                    "total": total_amount,
                    "shipping_address": shipping_address,
                    "notes": f"Test order for O2D flow testing - Source: {source}",
                    "now": datetime.now()
                })

                # Create order items
                for j, prod in enumerate([prod1, prod2]):
                    item_id = str(uuid.uuid4())
                    unit_price = float(prod[3])
                    tax_rate = 18.0
                    item_tax = unit_price * (tax_rate / 100)
                    item_total = unit_price + item_tax

                    await db.execute(text("""
                        INSERT INTO order_items (
                            id, order_id, product_id,
                            product_name, product_sku,
                            quantity, unit_price, unit_mrp,
                            discount_amount, tax_rate, tax_amount, total_amount,
                            warranty_months, created_at
                        ) VALUES (
                            :id, :order_id, :product_id,
                            :name, :sku,
                            1, :price, :mrp,
                            0, :tax_rate, :tax_amount, :total,
                            12, :now
                        )
                    """), {
                        "id": item_id,
                        "order_id": order_id,
                        "product_id": prod[0],
                        "name": prod[2],
                        "sku": prod[1],
                        "price": unit_price,
                        "mrp": unit_price,
                        "tax_rate": tax_rate,
                        "tax_amount": item_tax,
                        "total": item_total,
                        "now": datetime.now()
                    })

                orders_created.append({
                    "order_number": order_number,
                    "source": source,
                    "customer": full_name,
                    "city": cust_data["city"],
                    "amount": total_amount
                })

                print(f"   Created: {order_number} | {source} | {full_name} ({cust_data['city']}) | Rs. {total_amount:,.0f}")

            await db.commit()

        # 8. Summary
        print("\n" + "=" * 80)
        print("SETUP COMPLETE - SUMMARY")
        print("=" * 80)

        # Final counts
        result = await db.execute(text("SELECT COUNT(*) FROM stock_items WHERE status = 'AVAILABLE'"))
        avail_inventory = result.scalar()

        result = await db.execute(text("SELECT COUNT(*) FROM orders WHERE status = 'NEW'"))
        new_orders = result.scalar()

        result = await db.execute(text("""
            SELECT o.order_number, o.source as channel,
                   c.first_name || ' ' || c.last_name as customer,
                   json_extract(o.shipping_address, '$.city') as city,
                   o.total_amount, o.status
            FROM orders o
            JOIN customers c ON o.customer_id = c.id
            WHERE o.status = 'NEW'
            ORDER BY o.created_at DESC
            LIMIT 10
        """))
        pending_orders = result.fetchall()

        print(f"\n   Available Inventory: {avail_inventory} units")
        print(f"   New Orders (Ready for Processing): {new_orders}")
        print("\n   PENDING ORDERS:")
        print("   " + "-" * 75)
        print(f"   {'Order Number':<25} {'Channel':<12} {'Customer':<15} {'City':<12} {'Amount':>10}")
        print("   " + "-" * 75)
        for order in pending_orders:
            print(f"   {order[0]:<25} {order[1]:<12} {order[2]:<15} {order[3]:<12} Rs.{order[4]:>8,.0f}")

        print("\n" + "=" * 80)
        print("NEXT STEPS - TEST THE O2D FLOW:")
        print("=" * 80)
        print("""
   1. ALLOCATION: Call POST /api/v1/orders/{order_id}/allocate
      - Check warehouse allocation based on serviceability
      - Verify inventory is reserved

   2. PICKLIST: Call POST /api/v1/picklists/generate
      - Generate picklist for allocated orders
      - Assign picker, start picking

   3. PACK: Call POST /api/v1/shipments
      - Create shipment with packing details
      - Generate shipping label and invoice

   4. MANIFEST: Call POST /api/v1/manifests
      - Create manifest for courier handover
      - Assign transporter

   5. DISPATCH: Call POST /api/v1/manifests/{id}/confirm
      - Mark shipments as shipped
      - Generate AWB numbers

   6. DELIVERY: Call POST /api/v1/shipments/{id}/deliver
      - Update tracking status
      - Upload POD (Proof of Delivery)

   7. SERVICE REQUEST: Verify auto-creation
      - Check if installation request is created post-delivery
        """)


async def test_allocation_flow():
    """Test the allocation flow for a single order"""
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as db:
        print("\n" + "=" * 80)
        print("TESTING ORDER ALLOCATION FLOW")
        print("=" * 80)

        # Get a NEW order
        result = await db.execute(text("""
            SELECT o.id, o.order_number,
                   json_extract(o.shipping_address, '$.pincode') as pincode,
                   o.total_amount, o.source as channel,
                   c.first_name || ' ' || c.last_name as customer
            FROM orders o
            JOIN customers c ON o.customer_id = c.id
            WHERE o.status = 'NEW'
            LIMIT 1
        """))
        order = result.fetchone()

        if not order:
            print("   No NEW orders found to test!")
            return

        print(f"\n   Testing Order: {order[1]}")
        print(f"   Channel: {order[4]} | Customer: {order[5]}")
        print(f"   Delivery Pincode: {order[2]} | Amount: Rs. {order[3]:,.0f}")

        # Get order items
        result = await db.execute(text("""
            SELECT oi.id, p.sku, p.name, oi.quantity
            FROM order_items oi
            JOIN products p ON oi.product_id = p.id
            WHERE oi.order_id = :order_id
        """), {"order_id": order[0]})
        items = result.fetchall()

        print(f"\n   Order Items:")
        for item in items:
            print(f"   - {item[1]}: {item[2][:40]} x {item[3]}")

        # Check warehouse and available inventory
        result = await db.execute(text("""
            SELECT w.id, w.name, w.city
            FROM warehouses w
            WHERE w.is_active = true
        """))
        warehouses = result.fetchall()

        print(f"\n   Available Warehouses:")
        for wh in warehouses:
            # Count available inventory
            result = await db.execute(text("""
                SELECT COUNT(*) FROM stock_items
                WHERE warehouse_id = :wh_id AND status = 'AVAILABLE'
            """), {"wh_id": wh[0]})
            inv_count = result.scalar()
            print(f"   - {wh[1]} ({wh[2]}): {inv_count} units available")

        # Simulate allocation
        print(f"\n   ALLOCATION SIMULATION:")
        warehouse_id = warehouses[0][0] if warehouses else None

        if warehouse_id:
            for item in items:
                # Find available stock for this product
                result = await db.execute(text("""
                    SELECT id, serial_number FROM stock_items
                    WHERE product_id = (SELECT id FROM products WHERE sku = :sku)
                    AND warehouse_id = :wh_id
                    AND status = 'AVAILABLE'
                    LIMIT :qty
                """), {"sku": item[1], "wh_id": warehouse_id, "qty": item[3]})
                stock_items = result.fetchall()

                if len(stock_items) >= item[3]:
                    print(f"   ✓ {item[1]}: {len(stock_items)} units available (need {item[3]})")

                    # Reserve inventory
                    for si in stock_items:
                        await db.execute(text("""
                            UPDATE stock_items
                            SET status = 'RESERVED',
                                order_id = :order_id,
                                order_item_id = :item_id,
                                allocated_at = :now
                            WHERE id = :si_id
                        """), {
                            "order_id": order[0],
                            "item_id": item[0],
                            "now": datetime.now(),
                            "si_id": si[0]
                        })
                else:
                    print(f"   ✗ {item[1]}: Only {len(stock_items)} units available (need {item[3]}) - BACKORDER")

            # Update order status
            await db.execute(text("""
                UPDATE orders SET status = 'ALLOCATED', allocated_at = :now, updated_at = :now
                WHERE id = :order_id
            """), {"order_id": order[0], "now": datetime.now()})

            await db.commit()
            print(f"\n   ✓ Order {order[1]} ALLOCATED successfully!")
        else:
            print("   ✗ No warehouse available for allocation!")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "allocate":
        asyncio.run(test_allocation_flow())
    else:
        asyncio.run(setup_test_data())
