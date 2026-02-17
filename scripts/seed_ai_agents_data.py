"""
Seed data for OMS AI (5 agents) and WMS AI (4 agents) to function.

Seeds:
  PUBLIC SCHEMA:
    - oms_ai and wms_ai ErpModule records
    - TenantSubscription linking tenant to these modules

  TENANT SCHEMA (tenant_finaltest2026):
    OMS AI data:
      - Return orders (for fraud detection + returns prediction)
      - Diverse order patterns (COD high-value, address mismatch, late-night, etc.)

    WMS AI data:
      - Warehouse workers (12 active workers)
      - Work shifts (45 days of history)
      - Labor standards (PICK, PUTAWAY, PACK, REPLENISH)
      - Warehouse tasks (45 days of completed PICK/PUTAWAY/PACK/REPLENISH tasks)
      - Stock movements (45 days)
      - Productivity metrics (45 days)
      - Stock items with bin assignments
"""
import asyncio
import sys
import uuid
import random
import json
from pathlib import Path
from datetime import datetime, timedelta, timezone, date, time
from decimal import Decimal

sys.path.insert(0, str(Path(__file__).parent.parent))
from sqlalchemy import text
from app.database import engine

TENANT_SCHEMA = "tenant_finaltest2026"


async def create_missing_tables(conn):
    """Create WMS AI tables if they don't exist in the tenant schema."""
    print("\n=== Creating Missing WMS Tables ===")

    await conn.execute(text(f'SET search_path TO "{TENANT_SCHEMA}"'))

    # Check and create warehouse_workers
    r = await conn.execute(text("""
        SELECT EXISTS (SELECT 1 FROM information_schema.tables
        WHERE table_schema = :schema AND table_name = 'warehouse_workers')
    """), {"schema": TENANT_SCHEMA})
    if not r.scalar():
        await conn.execute(text("""
            CREATE TABLE warehouse_workers (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                tenant_id UUID NOT NULL,
                user_id UUID REFERENCES users(id) ON DELETE SET NULL,
                employee_code VARCHAR(30) NOT NULL,
                first_name VARCHAR(100) NOT NULL,
                last_name VARCHAR(100) NOT NULL,
                email VARCHAR(100),
                phone VARCHAR(20),
                worker_type VARCHAR(30) NOT NULL DEFAULT 'FULL_TIME',
                status VARCHAR(30) NOT NULL DEFAULT 'ACTIVE',
                hire_date DATE NOT NULL,
                termination_date DATE,
                primary_warehouse_id UUID NOT NULL REFERENCES warehouses(id) ON DELETE RESTRICT,
                primary_zone_id UUID REFERENCES warehouse_zones(id) ON DELETE SET NULL,
                supervisor_id UUID REFERENCES warehouse_workers(id) ON DELETE SET NULL,
                skills JSONB,
                certifications JSONB,
                equipment_certified JSONB,
                preferred_shift VARCHAR(30),
                max_hours_per_week INTEGER DEFAULT 40,
                can_work_overtime BOOLEAN DEFAULT TRUE,
                can_work_weekends BOOLEAN DEFAULT TRUE,
                hourly_rate NUMERIC(10,2) DEFAULT 0,
                overtime_multiplier NUMERIC(3,2) DEFAULT 1.5,
                avg_picks_per_hour NUMERIC(10,2),
                avg_units_per_hour NUMERIC(10,2),
                accuracy_rate NUMERIC(5,2),
                productivity_score NUMERIC(5,2),
                attendance_rate NUMERIC(5,2),
                tardiness_count_ytd INTEGER DEFAULT 0,
                absence_count_ytd INTEGER DEFAULT 0,
                annual_leave_balance NUMERIC(5,2) DEFAULT 0,
                sick_leave_balance NUMERIC(5,2) DEFAULT 0,
                casual_leave_balance NUMERIC(5,2) DEFAULT 0,
                notes TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW(),
                UNIQUE(tenant_id, employee_code)
            )
        """))
        await conn.execute(text("CREATE INDEX ix_warehouse_workers_status ON warehouse_workers(status)"))
        await conn.execute(text("CREATE INDEX ix_warehouse_workers_tenant ON warehouse_workers(tenant_id)"))
        print("  Created warehouse_workers table")
    else:
        print("  warehouse_workers table already exists")

    # Check and create work_shifts
    r = await conn.execute(text("""
        SELECT EXISTS (SELECT 1 FROM information_schema.tables
        WHERE table_schema = :schema AND table_name = 'work_shifts')
    """), {"schema": TENANT_SCHEMA})
    if not r.scalar():
        await conn.execute(text("""
            CREATE TABLE work_shifts (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                tenant_id UUID NOT NULL,
                worker_id UUID NOT NULL REFERENCES warehouse_workers(id) ON DELETE CASCADE,
                warehouse_id UUID NOT NULL REFERENCES warehouses(id) ON DELETE CASCADE,
                shift_date DATE NOT NULL,
                shift_type VARCHAR(30) NOT NULL,
                status VARCHAR(30) NOT NULL DEFAULT 'SCHEDULED',
                scheduled_start TIME NOT NULL,
                scheduled_end TIME NOT NULL,
                scheduled_break_minutes INTEGER DEFAULT 30,
                actual_start TIMESTAMPTZ,
                actual_end TIMESTAMPTZ,
                actual_break_minutes INTEGER,
                assigned_zone_id UUID REFERENCES warehouse_zones(id) ON DELETE SET NULL,
                assigned_function VARCHAR(50),
                supervisor_id UUID REFERENCES warehouse_workers(id) ON DELETE SET NULL,
                tasks_completed INTEGER DEFAULT 0,
                units_processed INTEGER DEFAULT 0,
                errors_count INTEGER DEFAULT 0,
                productive_minutes INTEGER,
                idle_minutes INTEGER,
                travel_minutes INTEGER,
                is_overtime BOOLEAN DEFAULT FALSE,
                overtime_hours NUMERIC(4,2) DEFAULT 0,
                overtime_approved_by UUID,
                notes TEXT,
                no_show_reason TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            )
        """))
        await conn.execute(text("CREATE INDEX ix_work_shifts_date ON work_shifts(shift_date)"))
        await conn.execute(text("CREATE INDEX ix_work_shifts_worker ON work_shifts(worker_id, shift_date)"))
        print("  Created work_shifts table")
    else:
        print("  work_shifts table already exists")

    # Check and create labor_standards
    r = await conn.execute(text("""
        SELECT EXISTS (SELECT 1 FROM information_schema.tables
        WHERE table_schema = :schema AND table_name = 'labor_standards')
    """), {"schema": TENANT_SCHEMA})
    if not r.scalar():
        await conn.execute(text("""
            CREATE TABLE labor_standards (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                tenant_id UUID NOT NULL,
                warehouse_id UUID NOT NULL REFERENCES warehouses(id) ON DELETE CASCADE,
                function VARCHAR(50) NOT NULL,
                zone_id UUID REFERENCES warehouse_zones(id) ON DELETE SET NULL,
                units_per_hour NUMERIC(10,2) NOT NULL,
                lines_per_hour NUMERIC(10,2),
                orders_per_hour NUMERIC(10,2),
                travel_time_per_pick INTEGER DEFAULT 15,
                pick_time_per_unit INTEGER DEFAULT 5,
                setup_time INTEGER DEFAULT 60,
                threshold_minimum NUMERIC(5,2) DEFAULT 70,
                threshold_target NUMERIC(5,2) DEFAULT 100,
                threshold_excellent NUMERIC(5,2) DEFAULT 120,
                effective_from DATE NOT NULL,
                effective_to DATE,
                is_active BOOLEAN DEFAULT TRUE,
                notes TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW(),
                created_by UUID,
                UNIQUE(tenant_id, warehouse_id, function, zone_id)
            )
        """))
        print("  Created labor_standards table")
    else:
        print("  labor_standards table already exists")

    # Check and create warehouse_tasks
    r = await conn.execute(text("""
        SELECT EXISTS (SELECT 1 FROM information_schema.tables
        WHERE table_schema = :schema AND table_name = 'warehouse_tasks')
    """), {"schema": TENANT_SCHEMA})
    if not r.scalar():
        await conn.execute(text("""
            CREATE TABLE warehouse_tasks (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                tenant_id UUID NOT NULL,
                task_number VARCHAR(30) NOT NULL,
                task_type VARCHAR(50) NOT NULL,
                status VARCHAR(50) NOT NULL DEFAULT 'PENDING',
                priority VARCHAR(20) NOT NULL DEFAULT 'NORMAL',
                warehouse_id UUID NOT NULL REFERENCES warehouses(id) ON DELETE RESTRICT,
                zone_id UUID REFERENCES warehouse_zones(id) ON DELETE SET NULL,
                source_bin_id UUID REFERENCES warehouse_bins(id) ON DELETE SET NULL,
                source_bin_code VARCHAR(100),
                destination_bin_id UUID REFERENCES warehouse_bins(id) ON DELETE SET NULL,
                destination_bin_code VARCHAR(100),
                product_id UUID REFERENCES products(id) ON DELETE SET NULL,
                variant_id UUID,
                sku VARCHAR(100),
                product_name VARCHAR(255),
                quantity_required INTEGER DEFAULT 0,
                quantity_completed INTEGER DEFAULT 0,
                quantity_exception INTEGER DEFAULT 0,
                wave_id UUID,
                picklist_id UUID,
                picklist_item_id UUID,
                grn_id UUID,
                cross_dock_id UUID,
                assigned_to UUID REFERENCES users(id) ON DELETE SET NULL,
                assigned_at TIMESTAMPTZ,
                suggested_next_task_id UUID,
                equipment_type VARCHAR(50),
                equipment_id VARCHAR(50),
                due_at TIMESTAMPTZ,
                sla_priority_boost BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW(),
                started_at TIMESTAMPTZ,
                completed_at TIMESTAMPTZ
            )
        """))
        await conn.execute(text("CREATE INDEX ix_warehouse_tasks_status_priority ON warehouse_tasks(status, priority)"))
        await conn.execute(text("CREATE INDEX ix_warehouse_tasks_assigned ON warehouse_tasks(assigned_to, status)"))
        await conn.execute(text("CREATE INDEX ix_warehouse_tasks_type_status ON warehouse_tasks(task_type, status)"))
        print("  Created warehouse_tasks table")
    else:
        print("  warehouse_tasks table already exists")

    # Check and create productivity_metrics
    r = await conn.execute(text("""
        SELECT EXISTS (SELECT 1 FROM information_schema.tables
        WHERE table_schema = :schema AND table_name = 'productivity_metrics')
    """), {"schema": TENANT_SCHEMA})
    if not r.scalar():
        await conn.execute(text("""
            CREATE TABLE productivity_metrics (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                tenant_id UUID NOT NULL,
                worker_id UUID NOT NULL REFERENCES warehouse_workers(id) ON DELETE CASCADE,
                warehouse_id UUID NOT NULL REFERENCES warehouses(id) ON DELETE CASCADE,
                metric_date DATE NOT NULL,
                function VARCHAR(50) NOT NULL,
                hours_worked NUMERIC(5,2) DEFAULT 0,
                productive_hours NUMERIC(5,2) DEFAULT 0,
                idle_hours NUMERIC(5,2) DEFAULT 0,
                units_processed INTEGER DEFAULT 0,
                lines_processed INTEGER DEFAULT 0,
                orders_processed INTEGER DEFAULT 0,
                tasks_completed INTEGER DEFAULT 0,
                units_per_hour NUMERIC(10,2) DEFAULT 0,
                lines_per_hour NUMERIC(10,2) DEFAULT 0,
                standard_units_per_hour NUMERIC(10,2) DEFAULT 0,
                performance_percentage NUMERIC(6,2) DEFAULT 0,
                errors_count INTEGER DEFAULT 0,
                accuracy_rate NUMERIC(5,2) DEFAULT 100,
                labor_cost NUMERIC(12,2) DEFAULT 0,
                cost_per_unit NUMERIC(10,4) DEFAULT 0,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW(),
                UNIQUE(tenant_id, worker_id, metric_date, function)
            )
        """))
        await conn.execute(text("CREATE INDEX ix_productivity_metrics_date ON productivity_metrics(metric_date)"))
        print("  Created productivity_metrics table")
    else:
        print("  productivity_metrics table already exists")

    await conn.commit()
    print("  Table creation complete")

# Products (reuse from existing seed)
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

PAYMENT_METHODS = ["ONLINE", "COD", "UPI", "CARD", "NET_BANKING"]
SOURCES = ["WEBSITE", "MOBILE_APP", "PHONE", "AMAZON", "FLIPKART", "STORE", "DEALER"]
STATUSES = ["NEW", "CONFIRMED", "ALLOCATED", "PICKING", "PICKED", "PACKED", "SHIPPED", "IN_TRANSIT", "DELIVERED"]
CITIES = ["Mumbai", "Delhi", "Bangalore", "Chennai", "Hyderabad", "Pune", "Kolkata", "Ahmedabad", "Jaipur", "Lucknow"]
PINCODES = ["400001", "110001", "560001", "600001", "500001", "411001", "700001", "380001", "302001", "226001"]

WORKER_NAMES = [
    ("Rajesh", "Kumar"), ("Sunil", "Sharma"), ("Amit", "Singh"), ("Vijay", "Patel"),
    ("Deepak", "Yadav"), ("Ravi", "Verma"), ("Sanjay", "Gupta"), ("Manoj", "Tiwari"),
    ("Anil", "Joshi"), ("Pradeep", "Mishra"), ("Ramesh", "Chauhan"), ("Suresh", "Nair"),
]


async def seed_public_modules(conn):
    """Create oms_ai and wms_ai ErpModule records + tenant subscriptions."""
    print("\n=== Seeding AI Modules (public schema) ===")
    await conn.execute(text('SET search_path TO "public"'))

    # Get tenant id
    r = await conn.execute(text("SELECT id FROM tenants WHERE status = 'active' LIMIT 1"))
    tenant_row = r.fetchone()
    if not tenant_row:
        print("ERROR: No active tenant found!")
        return
    tenant_id = str(tenant_row[0])
    print(f"  Tenant ID: {tenant_id}")

    # Check if modules already exist
    r = await conn.execute(text("SELECT id, code FROM modules WHERE code IN ('oms_ai', 'wms_ai')"))
    existing = {row[1]: str(row[0]) for row in r.fetchall()}

    oms_ai_id = existing.get('oms_ai')
    wms_ai_id = existing.get('wms_ai')

    if not oms_ai_id:
        oms_ai_id = str(uuid.uuid4())
        await conn.execute(text("""
            INSERT INTO modules (id, code, name, description, category, icon, color, is_active, is_base_module,
                                 price_monthly, price_yearly, created_at, updated_at)
            VALUES (:id, 'oms_ai', 'OMS AI Agents', 'AI-powered order management: Fraud Detection, Smart Routing, Delivery Promise, Order Prioritization, Returns Prediction',
                    'ai', 'Brain', '#8B5CF6', true, false, 0, 0, NOW(), NOW())
        """), {"id": oms_ai_id})
        print(f"  Created oms_ai module: {oms_ai_id}")
    else:
        print(f"  oms_ai module already exists: {oms_ai_id}")

    if not wms_ai_id:
        wms_ai_id = str(uuid.uuid4())
        await conn.execute(text("""
            INSERT INTO modules (id, code, name, description, category, icon, color, is_active, is_base_module,
                                 price_monthly, price_yearly, created_at, updated_at)
            VALUES (:id, 'wms_ai', 'WMS AI Agents', 'AI-powered warehouse management: Anomaly Detection, Smart Slotting, Labor Forecasting, Replenishment',
                    'ai', 'Brain', '#EC4899', true, false, 0, 0, NOW(), NOW())
        """), {"id": wms_ai_id})
        print(f"  Created wms_ai module: {wms_ai_id}")
    else:
        print(f"  wms_ai module already exists: {wms_ai_id}")

    # Create subscriptions
    for mod_id, mod_code in [(oms_ai_id, 'oms_ai'), (wms_ai_id, 'wms_ai')]:
        r = await conn.execute(text("""
            SELECT id FROM tenant_subscriptions
            WHERE tenant_id = :tid AND module_id = :mid AND status = 'active'
        """), {"tid": tenant_id, "mid": mod_id})
        if not r.fetchone():
            sub_id = str(uuid.uuid4())
            await conn.execute(text("""
                INSERT INTO tenant_subscriptions (id, tenant_id, module_id, status, subscription_type,
                                                   billing_cycle, price_paid, starts_at, expires_at,
                                                   is_trial, auto_renew, created_at, updated_at)
                VALUES (:id, :tid, :mid, 'active', 'SUBSCRIPTION', 'YEARLY', 0,
                        NOW(), NOW() + INTERVAL '365 days', false, true, NOW(), NOW())
            """), {"id": sub_id, "tid": tenant_id, "mid": mod_id})
            print(f"  Subscribed tenant to {mod_code}")
        else:
            print(f"  Tenant already subscribed to {mod_code}")

    await conn.commit()
    return tenant_id


async def seed_return_orders(conn, customers, orders_with_items):
    """Seed return orders for fraud detection and returns prediction."""
    print("\n=== Seeding Return Orders ===")

    # Check if already seeded
    r = await conn.execute(text("SELECT COUNT(*) FROM return_orders WHERE rma_number LIKE 'RMA-%'"))
    existing = r.scalar() or 0
    if existing > 0:
        print(f"  {existing} return orders already exist, skipping")
        return

    # Pick ~15% of delivered orders to have returns
    delivered = [o for o in orders_with_items if o['status'] == 'DELIVERED']
    return_count = max(5, len(delivered) // 7)
    return_orders = random.sample(delivered, min(return_count, len(delivered)))

    reasons = ["DAMAGED", "DEFECTIVE", "WRONG_ITEM", "NOT_AS_DESCRIBED", "CHANGED_MIND", "SIZE_FIT_ISSUE", "QUALITY_ISSUE", "OTHER"]
    return_types = ["RETURN", "RETURN", "RETURN", "REPLACEMENT", "EXCHANGE"]
    return_statuses = ["INITIATED", "AUTHORIZED", "RECEIVED", "APPROVED", "REFUND_PROCESSED", "CLOSED"]

    count = 0
    for order in return_orders:
        ret_id = str(uuid.uuid4())
        ret_status = random.choice(return_statuses)
        requested_at = order['created_at'] + timedelta(days=random.randint(3, 15))
        received_at = requested_at + timedelta(days=random.randint(2, 7)) if ret_status in ("RECEIVED", "APPROVED", "REFUND_PROCESSED", "CLOSED") else None
        rma_num = f"RMA-{count+1:05d}"

        # Calculate return amount from order total (random portion)
        total_return = Decimal(str(random.randint(500, 15000)))
        restocking = Decimal(str(round(float(total_return) * random.uniform(0, 0.1), 2))) if ret_status in ("APPROVED", "REFUND_PROCESSED", "CLOSED") else Decimal("0")
        shipping_ded = Decimal(str(random.choice([0, 50, 100, 150])))
        net_refund = total_return - restocking - shipping_ded
        if net_refund < 0:
            net_refund = Decimal("0")

        await conn.execute(text("""
            INSERT INTO return_orders (id, rma_number, order_id, customer_id, return_type, return_reason, status,
                                        requested_at, received_at, inspection_notes,
                                        total_return_amount, restocking_fee, shipping_deduction,
                                        net_refund_amount, store_credit_amount,
                                        created_at, updated_at)
            VALUES (:id, :rma, :oid, :cid, :rtype, :reason, :status, :req_at, :recv_at, :notes,
                    :total_ret, :restock, :ship_ded, :net_refund, 0,
                    :req_at, NOW())
        """), {
            "id": ret_id, "rma": rma_num, "oid": order['id'], "cid": order['customer_id'],
            "rtype": random.choice(return_types), "reason": random.choice(reasons),
            "status": ret_status, "req_at": requested_at.isoformat(),
            "recv_at": received_at.isoformat() if received_at else None,
            "notes": f"Inspection: {random.choice(['Pass', 'Fail - damaged', 'Partial refund approved'])}" if ret_status in ("APPROVED", "REFUND_PROCESSED", "CLOSED") else None,
            "total_ret": str(total_return), "restock": str(restocking),
            "ship_ded": str(shipping_ded), "net_refund": str(net_refund),
        })
        count += 1

    await conn.commit()
    print(f"  Created {count} return orders")


async def seed_oms_fraud_orders(conn, customers, warehouses):
    """Seed orders with specific fraud patterns for fraud detection agent."""
    print("\n=== Seeding Fraud-Pattern Orders (OMS AI) ===")

    # Check if already seeded
    r = await conn.execute(text("SELECT COUNT(*) FROM orders WHERE order_number LIKE 'ORD-AI-%'"))
    existing = r.scalar() or 0
    if existing > 0:
        print(f"  {existing} fraud-pattern orders already exist, skipping")
        return []

    # Get max order number
    r = await conn.execute(text("SELECT COUNT(*) FROM orders"))
    order_offset = r.scalar() or 0
    counter = order_offset + 5000

    fraud_orders = []
    now = datetime.now(timezone.utc)

    for i in range(30):
        counter += 1
        oid = str(uuid.uuid4())
        cust = random.choice(customers)
        wh = random.choice(warehouses)
        pattern = random.choice(['high_value_cod', 'address_mismatch', 'velocity', 'late_night', 'new_high_value', 'normal'])

        if pattern == 'high_value_cod':
            amount = Decimal(str(random.randint(30000, 90000)))
            payment = "COD"
            ship_pin = random.choice(PINCODES)
            bill_pin = ship_pin
            created = now - timedelta(days=random.randint(0, 5))
        elif pattern == 'address_mismatch':
            amount = Decimal(str(random.randint(5000, 25000)))
            payment = random.choice(["ONLINE", "CARD", "COD"])
            ship_pin = random.choice(PINCODES[:5])
            bill_pin = random.choice(PINCODES[5:])  # Different city
            created = now - timedelta(days=random.randint(0, 5))
        elif pattern == 'velocity':
            amount = Decimal(str(random.randint(2000, 15000)))
            payment = random.choice(PAYMENT_METHODS)
            ship_pin = random.choice(PINCODES)
            bill_pin = ship_pin
            created = now - timedelta(hours=random.randint(1, 12))  # Multiple orders same day
        elif pattern == 'late_night':
            amount = Decimal(str(random.randint(5000, 40000)))
            payment = random.choice(PAYMENT_METHODS)
            ship_pin = random.choice(PINCODES)
            bill_pin = ship_pin
            created = (now - timedelta(days=random.randint(0, 3))).replace(hour=random.randint(1, 4))
        elif pattern == 'new_high_value':
            amount = Decimal(str(random.randint(25000, 75000)))
            payment = "COD"
            ship_pin = random.choice(PINCODES)
            bill_pin = ship_pin
            created = now - timedelta(days=random.randint(0, 2))
        else:
            amount = Decimal(str(random.randint(1000, 15000)))
            payment = random.choice(["ONLINE", "UPI", "CARD"])
            ship_pin = random.choice(PINCODES)
            bill_pin = ship_pin
            created = now - timedelta(days=random.randint(0, 7))

        ship_city = CITIES[PINCODES.index(ship_pin)]
        bill_city = CITIES[PINCODES.index(bill_pin)]
        status = random.choice(["NEW", "CONFIRMED", "ALLOCATED"])
        source = random.choice(SOURCES)
        tax = amount * Decimal("0.18")

        discount = Decimal("0")
        shipping_amt = Decimal(str(random.choice([0, 49, 99, 149])))
        total = amount + tax + shipping_amt - discount
        amount_paid = total if payment != "COD" else Decimal("0")

        ship_addr = json.dumps({"name": "Customer", "phone": "9876543210", "address_line1": f"{random.randint(1,500)} Main St", "city": ship_city, "state": "State", "pincode": ship_pin, "country": "India"})
        bill_addr = json.dumps({"name": "Customer", "phone": "9876543210", "address_line1": f"{random.randint(1,500)} Bill St", "city": bill_city, "state": "State", "pincode": bill_pin, "country": "India"})

        await conn.execute(text("""
            INSERT INTO orders (id, order_number, customer_id, warehouse_id, status, source, payment_method,
                                payment_status, subtotal, tax_amount, discount_amount, shipping_amount,
                                total_amount, amount_paid, shipping_address,
                                billing_address, created_at, updated_at)
            VALUES (:id, :num, :cid, :wid, :status, :source, :pay, 'PENDING',
                    :sub, :tax, :disc, :ship_amt, :total, :paid, :ship, :bill, :created, :created)
        """), {
            "id": oid, "num": f"ORD-AI-{counter}", "cid": cust, "wid": wh,
            "status": status, "source": source, "pay": payment,
            "sub": str(amount), "tax": str(tax), "disc": str(discount),
            "ship_amt": str(shipping_amt), "total": str(total), "paid": str(amount_paid),
            "ship": ship_addr, "bill": bill_addr, "created": created.isoformat(),
        })

        # Add order items
        prod = random.choice(PRODUCTS)
        qty = random.randint(1, 5) if pattern != 'velocity' else random.randint(10, 60)
        item_tax_rate = Decimal("18")
        item_tax = Decimal(str(prod[3])) * Decimal("0.18") * qty
        item_total = Decimal(str(prod[3])) * qty
        await conn.execute(text("""
            INSERT INTO order_items (id, order_id, product_id, product_name, product_sku, quantity,
                                      unit_price, unit_mrp, discount_amount, tax_rate, tax_amount,
                                      total_amount, warranty_months, created_at)
            VALUES (:id, :oid, :pid, :pname, :sku, :qty, :price, :mrp, 0, :tax_rate, :tax, :total, 12, :created)
        """), {
            "id": str(uuid.uuid4()), "oid": oid, "pid": prod[0], "pname": prod[1], "sku": prod[2],
            "qty": qty, "price": str(prod[3]), "mrp": str(prod[3]),
            "tax_rate": str(item_tax_rate), "tax": str(item_tax), "total": str(item_total),
            "created": created.isoformat(),
        })

        fraud_orders.append({"id": oid, "customer_id": cust, "created_at": created, "status": status})

    await conn.commit()
    print(f"  Created {len(fraud_orders)} fraud-pattern orders")
    return fraud_orders


async def seed_zones_and_bins(conn, warehouse_id):
    """Seed warehouse zones and bins if they don't exist."""
    print("\n=== Seeding Warehouse Zones & Bins ===")

    zones = [
        ("RCV", "Receiving Dock", "RECEIVING", 5000, 500),
        ("STR-A", "Storage Area A", "STORAGE", 20000, 3000),
        ("STR-B", "Storage Area B", "STORAGE", 15000, 2000),
        ("PICK", "Forward Pick Zone", "PICKING", 8000, 1500),
        ("PACK", "Packing Station", "PACKING", 3000, 200),
        ("SHIP", "Shipping Dock", "SHIPPING", 4000, 300),
        ("RET", "Returns Area", "RETURNS", 2000, 100),
        ("QC", "Quality Control", "QUARANTINE", 1000, 50),
    ]

    zone_ids = []
    for code, name, ztype, area, capacity in zones:
        zid = str(uuid.uuid4())
        is_pick = ztype in ("PICKING", "PACKING")
        is_recv = ztype in ("RECEIVING", "RETURNS")
        current = random.randint(int(capacity * 0.3), int(capacity * 0.8))
        await conn.execute(text("""
            INSERT INTO warehouse_zones (id, warehouse_id, zone_code, zone_name, zone_type,
                                          floor_number, area_sqft, max_capacity, current_capacity,
                                          is_active, is_pickable, is_receivable, sort_order, created_at, updated_at)
            VALUES (:id, :wh, :code, :name, :ztype, 1, :area, :cap, :cur,
                    true, :pick, :recv, :sort, NOW(), NOW())
        """), {
            "id": zid, "wh": warehouse_id, "code": code, "name": name, "ztype": ztype,
            "area": area, "cap": capacity, "cur": current,
            "pick": is_pick, "recv": is_recv, "sort": len(zone_ids) + 1,
        })
        zone_ids.append(zid)

    # Create bins in each zone
    bin_ids = []
    bin_counter = 0
    bin_types = ["SHELF", "RACK", "RACK", "SHELF", "FLOOR", "PALLET"]
    for i, zid in enumerate(zone_ids):
        num_bins = random.randint(8, 20)
        zone_code = zones[i][0]
        for b in range(num_bins):
            bin_counter += 1
            bid = str(uuid.uuid4())
            aisle = chr(65 + (b // 5))  # A, B, C...
            rack = (b % 5) + 1
            shelf = random.randint(1, 4)
            max_cap = random.randint(20, 100)
            current_items = random.randint(0, max_cap)
            btype = random.choice(bin_types)
            is_pick = zones[i][2] in ("PICKING", "PACKING")

            await conn.execute(text("""
                INSERT INTO warehouse_bins (id, warehouse_id, zone_id, bin_code, bin_name,
                                             barcode, aisle, rack, shelf, bin_type,
                                             max_capacity, current_items, max_weight_kg, current_weight_kg,
                                             is_active, is_reserved, is_pickable, is_receivable, pick_sequence,
                                             created_at, updated_at)
                VALUES (:id, :wh, :zid, :code, :name, :barcode, :aisle, :rack, :shelf, :btype,
                        :max, :cur, :maxw, :curw, true, false, :pick, :recv, :seq, NOW(), NOW())
            """), {
                "id": bid, "wh": warehouse_id, "zid": zid,
                "code": f"{zone_code}-{aisle}{rack:02d}-S{shelf}",
                "name": f"{zone_code} Aisle {aisle} Rack {rack} Shelf {shelf}",
                "barcode": f"BIN-{bin_counter:05d}",
                "aisle": aisle, "rack": str(rack), "shelf": str(shelf), "btype": btype,
                "max": max_cap, "cur": current_items,
                "maxw": max_cap * 5, "curw": current_items * 3,
                "pick": is_pick, "recv": zones[i][2] in ("RECEIVING", "RETURNS"),
                "seq": bin_counter,
            })
            bin_ids.append(bid)

    await conn.commit()
    print(f"  Created {len(zone_ids)} zones and {len(bin_ids)} bins")
    return zone_ids, bin_ids


async def seed_wms_workers(conn, tenant_id, warehouse_id, zone_ids):
    """Seed warehouse workers."""
    print("\n=== Seeding Warehouse Workers ===")

    worker_ids = []
    for i, (first, last) in enumerate(WORKER_NAMES):
        wid = str(uuid.uuid4())
        zone_id = random.choice(zone_ids) if zone_ids else None
        skills = json.dumps({"PICKING": random.choice(["PROFICIENT", "EXPERT"]),
                              "PACKING": random.choice(["INTERMEDIATE", "PROFICIENT"]),
                              "PUTAWAY": random.choice(["NOVICE", "INTERMEDIATE", "PROFICIENT"])})

        await conn.execute(text("""
            INSERT INTO warehouse_workers (id, tenant_id, employee_code, first_name, last_name,
                                            phone, worker_type, status, hire_date, primary_warehouse_id,
                                            primary_zone_id, skills, preferred_shift, max_hours_per_week,
                                            can_work_overtime, can_work_weekends, hourly_rate,
                                            avg_picks_per_hour, avg_units_per_hour, accuracy_rate,
                                            productivity_score, attendance_rate, created_at, updated_at)
            VALUES (:id, :tid, :code, :fn, :ln, :phone, :wtype, 'ACTIVE', :hire, :wh, :zone, :skills,
                    :shift, 48, true, true, :rate, :picks, :units, :acc, :prod, :att, NOW(), NOW())
        """), {
            "id": wid, "tid": tenant_id, "code": f"WH-{i+1:03d}",
            "fn": first, "ln": last, "phone": f"98765{random.randint(10000,99999)}",
            "wtype": random.choice(["FULL_TIME", "FULL_TIME", "FULL_TIME", "PART_TIME", "CONTRACT"]),
            "hire": (date.today() - timedelta(days=random.randint(90, 730))).isoformat(),
            "wh": warehouse_id, "zone": zone_id, "skills": skills,
            "shift": random.choice(["MORNING", "AFTERNOON", "NIGHT"]),
            "rate": str(Decimal(str(random.randint(150, 350)))),
            "picks": str(Decimal(str(random.randint(22, 45)))),
            "units": str(Decimal(str(random.randint(30, 60)))),
            "acc": str(Decimal(str(random.uniform(92, 99.5)))),
            "prod": str(Decimal(str(random.uniform(65, 98)))),
            "att": str(Decimal(str(random.uniform(85, 99)))),
        })
        worker_ids.append(wid)

    await conn.commit()
    print(f"  Created {len(worker_ids)} warehouse workers")
    return worker_ids


async def seed_labor_standards(conn, tenant_id, warehouse_id):
    """Seed labor standards for productivity benchmarking."""
    print("\n=== Seeding Labor Standards ===")

    # Check if already seeded
    r = await conn.execute(text("SELECT COUNT(*) FROM labor_standards WHERE warehouse_id = :wh"), {"wh": warehouse_id})
    existing = r.scalar() or 0
    if existing > 0:
        print(f"  {existing} labor standards already exist, skipping")
        return

    standards = [
        ("PICKING", 30, 15, 5),
        ("PACKING", 25, 10, 8),
        ("PUTAWAY", 20, 20, 10),
        ("REPLENISH", 18, 25, 12),
        ("CYCLE_COUNT", 15, 10, 15),
    ]

    for func, uph, travel, pick_time in standards:
        await conn.execute(text("""
            INSERT INTO labor_standards (id, tenant_id, warehouse_id, function, units_per_hour,
                                          travel_time_per_pick, pick_time_per_unit, setup_time,
                                          threshold_minimum, threshold_target, threshold_excellent,
                                          effective_from, is_active, created_at, updated_at)
            VALUES (:id, :tid, :wh, :func, :uph, :travel, :pick, 60, 70, 100, 120,
                    :eff, true, NOW(), NOW())
        """), {
            "id": str(uuid.uuid4()), "tid": tenant_id, "wh": warehouse_id,
            "func": func, "uph": uph, "travel": travel, "pick": pick_time,
            "eff": (date.today() - timedelta(days=90)).isoformat(),
        })

    await conn.commit()
    print(f"  Created {len(standards)} labor standards")


async def seed_work_shifts(conn, tenant_id, warehouse_id, worker_ids, zone_ids):
    """Seed 45 days of work shift history."""
    print("\n=== Seeding Work Shifts (45 days) ===")

    # Check if already seeded
    r = await conn.execute(text("SELECT COUNT(*) FROM work_shifts WHERE warehouse_id = :wh"), {"wh": warehouse_id})
    existing = r.scalar() or 0
    if existing > 0:
        print(f"  {existing} work shifts already exist, skipping")
        return

    shifts = [
        ("MORNING", time(6, 0), time(14, 0)),
        ("AFTERNOON", time(14, 0), time(22, 0)),
        ("NIGHT", time(22, 0), time(6, 0)),
    ]

    count = 0
    today = date.today()
    for day_offset in range(45):
        shift_date = today - timedelta(days=day_offset)
        if shift_date.weekday() == 6:  # Skip Sundays
            continue

        for shift_type, sched_start, sched_end in shifts:
            # Assign 3-5 workers per shift
            num_workers = random.randint(3, min(5, len(worker_ids)))
            shift_workers = random.sample(worker_ids, num_workers)

            for wid in shift_workers:
                status = "COMPLETED" if day_offset > 0 else random.choice(["COMPLETED", "IN_PROGRESS", "SCHEDULED"])
                tasks_done = random.randint(15, 50) if status == "COMPLETED" else random.randint(0, 20)
                units_done = tasks_done * random.randint(2, 5)

                actual_start = datetime.combine(shift_date, sched_start, tzinfo=timezone.utc) + timedelta(minutes=random.randint(-5, 15)) if status in ("COMPLETED", "IN_PROGRESS") else None
                actual_end = datetime.combine(shift_date, sched_end, tzinfo=timezone.utc) + timedelta(minutes=random.randint(-10, 30)) if status == "COMPLETED" else None
                # Handle night shift crossing midnight
                if shift_type == "NIGHT" and actual_end and actual_end < actual_start:
                    actual_end += timedelta(days=1)

                await conn.execute(text("""
                    INSERT INTO work_shifts (id, tenant_id, worker_id, warehouse_id, shift_date, shift_type,
                                              status, scheduled_start, scheduled_end, scheduled_break_minutes,
                                              actual_start, actual_end, actual_break_minutes,
                                              assigned_zone_id, assigned_function,
                                              tasks_completed, units_processed, errors_count,
                                              productive_minutes, idle_minutes, created_at, updated_at)
                    VALUES (:id, :tid, :wid, :wh, :sd, :st, :status, :ss, :se, 30,
                            :as_, :ae, :ab, :zone, :func, :tc, :up, :err, :pm, :im, NOW(), NOW())
                """), {
                    "id": str(uuid.uuid4()), "tid": tenant_id, "wid": wid, "wh": warehouse_id,
                    "sd": shift_date.isoformat(), "st": shift_type, "status": status,
                    "ss": sched_start.isoformat(), "se": sched_end.isoformat(),
                    "as_": actual_start.isoformat() if actual_start else None,
                    "ae": actual_end.isoformat() if actual_end else None,
                    "ab": random.randint(25, 35) if status == "COMPLETED" else None,
                    "zone": random.choice(zone_ids) if zone_ids else None,
                    "func": random.choice(["PICKING", "PACKING", "PUTAWAY", "RECEIVING"]),
                    "tc": tasks_done, "up": units_done,
                    "err": random.randint(0, 3) if status == "COMPLETED" else 0,
                    "pm": random.randint(360, 450) if status == "COMPLETED" else None,
                    "im": random.randint(10, 60) if status == "COMPLETED" else None,
                })
                count += 1

    await conn.commit()
    print(f"  Created {count} work shifts")


async def seed_warehouse_tasks(conn, tenant_id, warehouse_id, zone_ids, bin_ids, worker_ids):
    """Seed 45 days of warehouse tasks (PICK, PUTAWAY, PACK, REPLENISH) using batch inserts."""
    print("\n=== Seeding Warehouse Tasks (45 days) ===")

    # Check if already seeded (allow partial re-seed if < 100)
    r = await conn.execute(text("SELECT COUNT(*) FROM warehouse_tasks WHERE warehouse_id = :wh"), {"wh": warehouse_id})
    existing = r.scalar() or 0
    if existing > 100:
        print(f"  {existing} warehouse tasks already exist, skipping")
        return

    # Clear partial data
    if existing > 0:
        await conn.execute(text("DELETE FROM warehouse_tasks WHERE warehouse_id = :wh"), {"wh": warehouse_id})
        await conn.commit()
        print(f"  Cleared {existing} partial warehouse tasks")

    task_types = ["PICK", "PICK", "PICK", "PUTAWAY", "PUTAWAY", "PACK", "PACK", "REPLENISH"]
    priorities = ["NORMAL", "NORMAL", "NORMAL", "HIGH", "URGENT", "LOW"]
    today = datetime.now(timezone.utc)
    count = 0
    task_counter = 0
    batch = []

    for day_offset in range(45):
        day = today - timedelta(days=day_offset)
        num_tasks = random.randint(15, 30)  # Reduced from 20-50

        for t in range(num_tasks):
            task_counter += 1
            ttype = random.choice(task_types)
            status = "COMPLETED" if day_offset > 0 else random.choice(["COMPLETED", "IN_PROGRESS", "PENDING"])
            prio = random.choice(priorities)
            zone = random.choice(zone_ids) if zone_ids else None
            src_bin = random.choice(bin_ids) if bin_ids else None
            dst_bin = random.choice(bin_ids) if bin_ids else None
            prod = random.choice(PRODUCTS)
            qty_req = random.randint(1, 20)
            qty_done = qty_req if status == "COMPLETED" else random.randint(0, qty_req)

            created = day.replace(hour=random.randint(6, 22), minute=random.randint(0, 59))
            started = created + timedelta(minutes=random.randint(1, 30)) if status in ("COMPLETED", "IN_PROGRESS") else None
            completed = started + timedelta(minutes=random.randint(3, 45)) if status == "COMPLETED" and started else None

            batch.append({
                "id": str(uuid.uuid4()), "tid": tenant_id,
                "num": f"TK-{day.strftime('%Y%m%d')}-{task_counter:04d}",
                "ttype": ttype, "status": status, "prio": prio,
                "wh": warehouse_id, "zone": zone, "src": src_bin, "dst": dst_bin,
                "pid": prod[0], "pname": prod[1], "sku": prod[2],
                "qreq": qty_req, "qdone": qty_done,
                "assignee": None,
                "assigned_at": started.isoformat() if started else None,
                "created": created.isoformat(),
                "started": started.isoformat() if started else None,
                "completed": completed.isoformat() if completed else None,
            })
            count += 1

        # Batch insert every 5 days
        if day_offset % 5 == 4 or day_offset == 44:
            if batch:
                for row in batch:
                    await conn.execute(text("""
                        INSERT INTO warehouse_tasks (id, tenant_id, task_number, task_type, status, priority,
                                                      warehouse_id, zone_id, source_bin_id, destination_bin_id,
                                                      product_id, product_name, sku,
                                                      quantity_required, quantity_completed,
                                                      assigned_to, assigned_at,
                                                      created_at, updated_at, started_at, completed_at)
                        VALUES (:id, :tid, :num, :ttype, :status, :prio,
                                :wh, :zone, :src, :dst, :pid, :pname, :sku,
                                :qreq, :qdone, :assignee, :assigned_at,
                                :created, :created, :started, :completed)
                    """), row)
                await conn.commit()
                print(f"    Batch committed: {len(batch)} tasks (total: {count})")
                batch = []

    if batch:
        for row in batch:
            await conn.execute(text("""
                INSERT INTO warehouse_tasks (id, tenant_id, task_number, task_type, status, priority,
                                              warehouse_id, zone_id, source_bin_id, destination_bin_id,
                                              product_id, product_name, sku,
                                              quantity_required, quantity_completed,
                                              assigned_to, assigned_at,
                                              created_at, updated_at, started_at, completed_at)
                VALUES (:id, :tid, :num, :ttype, :status, :prio,
                        :wh, :zone, :src, :dst, :pid, :pname, :sku,
                        :qreq, :qdone, :assignee, :assigned_at,
                        :created, :created, :started, :completed)
            """), row)
        await conn.commit()

    print(f"  Created {count} warehouse tasks")


async def seed_stock_movements(conn, warehouse_id, bin_ids):
    """Seed 45 days of stock movements."""
    print("\n=== Seeding Stock Movements (45 days) ===")

    # Check if already seeded
    r = await conn.execute(text("SELECT COUNT(*) FROM stock_movements WHERE warehouse_id = :wh AND notes LIKE 'Auto-seeded%'"), {"wh": warehouse_id})
    existing = r.scalar() or 0
    if existing > 0:
        print(f"  {existing} stock movements already exist, skipping")
        return

    movement_types = ["RECEIPT", "ISSUE", "ISSUE", "ISSUE", "TRANSFER_IN", "TRANSFER_OUT", "ADJUSTMENT_PLUS", "RETURN_IN"]
    today = datetime.now(timezone.utc)
    count = 0
    mv_counter = 0

    for day_offset in range(45):
        day = today - timedelta(days=day_offset)
        num_movements = random.randint(8, 15)  # Reduced

        for _ in range(num_movements):
            mv_counter += 1
            prod = random.choice(PRODUCTS)
            mtype = random.choice(movement_types)
            qty = random.randint(1, 20) if mtype != "ISSUE" else -random.randint(1, 15)
            bal_before = random.randint(10, 200)
            bal_after = bal_before + qty

            await conn.execute(text("""
                INSERT INTO stock_movements (id, movement_number, movement_type, movement_date,
                                              warehouse_id, product_id, quantity,
                                              balance_before, balance_after, unit_cost, total_cost,
                                              reference_type, reference_number, notes, created_at, updated_at)
                VALUES (:id, :num, :mtype, :mdate, :wh, :pid, :qty,
                        :bb, :ba, :uc, :tc, :rtype, :rnum, :notes, :mdate, :mdate)
            """), {
                "id": str(uuid.uuid4()), "num": f"SM-{day.strftime('%Y%m%d')}-{mv_counter:04d}",
                "mtype": mtype, "mdate": day.replace(hour=random.randint(6, 20)).isoformat(),
                "wh": warehouse_id, "pid": prod[0], "qty": qty,
                "bb": bal_before, "ba": bal_after,
                "uc": str(prod[3]), "tc": str(abs(qty) * prod[3]),
                "rtype": "ORDER" if mtype == "ISSUE" else "GRN" if mtype == "RECEIPT" else "TRANSFER",
                "rnum": f"REF-{mv_counter:06d}",
                "notes": f"Auto-seeded {mtype} movement",
            })
            count += 1

        if day_offset % 3 == 0:
            await conn.commit()

    await conn.commit()
    print(f"  Created {count} stock movements")


async def seed_productivity_metrics(conn, tenant_id, warehouse_id, worker_ids):
    """Seed 45 days of productivity metrics."""
    print("\n=== Seeding Productivity Metrics (45 days) ===")

    # Check if already seeded
    r = await conn.execute(text("SELECT COUNT(*) FROM productivity_metrics WHERE warehouse_id = :wh"), {"wh": warehouse_id})
    existing = r.scalar() or 0
    if existing > 0:
        print(f"  {existing} productivity metrics already exist, skipping")
        return

    functions = ["PICKING", "PACKING", "PUTAWAY"]
    today = date.today()
    count = 0

    for day_offset in range(45):
        metric_date = today - timedelta(days=day_offset)
        if metric_date.weekday() == 6:
            continue

        for wid in worker_ids:
            func = random.choice(functions)
            hours = Decimal(str(round(random.uniform(6, 8.5), 2)))
            productive = Decimal(str(round(float(hours) * random.uniform(0.75, 0.92), 2)))
            idle = hours - productive
            units = random.randint(120, 320)
            lines = random.randint(30, 80)
            orders = random.randint(10, 35)
            tasks = random.randint(15, 45)
            std_uph = Decimal("30") if func == "PICKING" else Decimal("25") if func == "PACKING" else Decimal("20")
            actual_uph = Decimal(str(round(units / float(productive) if float(productive) > 0 else 0, 2)))
            perf_pct = Decimal(str(round(float(actual_uph) / float(std_uph) * 100, 2))) if float(std_uph) > 0 else Decimal("0")
            errors = random.randint(0, 4)
            acc = Decimal(str(round(100 - (errors / max(units, 1) * 100), 2)))

            await conn.execute(text("""
                INSERT INTO productivity_metrics (id, tenant_id, worker_id, warehouse_id, metric_date,
                                                   function, hours_worked, productive_hours, idle_hours,
                                                   units_processed, lines_processed, orders_processed,
                                                   tasks_completed, units_per_hour, lines_per_hour,
                                                   standard_units_per_hour, performance_percentage,
                                                   errors_count, accuracy_rate, labor_cost, cost_per_unit,
                                                   created_at, updated_at)
                VALUES (:id, :tid, :wid, :wh, :md, :func, :hw, :ph, :ih,
                        :up, :lp, :op, :tc, :uph, :lph, :suph, :pp,
                        :err, :acc, :lc, :cpu, NOW(), NOW())
            """), {
                "id": str(uuid.uuid4()), "tid": tenant_id, "wid": wid, "wh": warehouse_id,
                "md": metric_date.isoformat(), "func": func,
                "hw": str(hours), "ph": str(productive), "ih": str(idle),
                "up": units, "lp": lines, "op": orders, "tc": tasks,
                "uph": str(actual_uph), "lph": str(Decimal(str(round(lines / float(productive) if float(productive) > 0 else 0, 2)))),
                "suph": str(std_uph), "pp": str(perf_pct),
                "err": errors, "acc": str(acc),
                "lc": str(Decimal(str(round(float(hours) * random.uniform(150, 350), 2)))),
                "cpu": str(Decimal(str(round(random.uniform(2, 8), 4)))),
            })
            count += 1

        if day_offset % 5 == 0:
            await conn.commit()

    await conn.commit()
    print(f"  Created {count} productivity metrics")


async def seed_stock_items_in_bins(conn, warehouse_id, bin_ids):
    """Ensure stock items are assigned to bins for slotting analysis."""
    print("\n=== Seeding Stock Items in Bins ===")

    # Check if stock items already have bins
    r = await conn.execute(text("SELECT COUNT(*) FROM stock_items WHERE bin_id IS NOT NULL"))
    existing = r.scalar() or 0
    if existing > 20:
        print(f"  {existing} stock items already have bin assignments, skipping")
        return

    # Get unassigned stock items
    r = await conn.execute(text("""
        SELECT id FROM stock_items WHERE warehouse_id = :wh AND bin_id IS NULL AND status = 'AVAILABLE' LIMIT 100
    """), {"wh": warehouse_id})
    items = [str(row[0]) for row in r.fetchall()]

    if not items:
        print("  No unassigned stock items found, creating some...")
        # Create stock items in bins
        for i in range(50):
            prod = random.choice(PRODUCTS)
            bin_id = random.choice(bin_ids) if bin_ids else None
            await conn.execute(text("""
                INSERT INTO stock_items (id, product_id, warehouse_id, bin_id, serial_number,
                                          status, received_date, purchase_price, created_at, updated_at)
                VALUES (:id, :pid, :wh, :bid, :sn, 'AVAILABLE', NOW() - INTERVAL '30 days', :price, NOW(), NOW())
            """), {
                "id": str(uuid.uuid4()), "pid": prod[0], "wh": warehouse_id,
                "bid": bin_id, "sn": f"SN-AI-{i+1:05d}", "price": str(prod[3]),
            })
        await conn.commit()
        print(f"  Created 50 stock items in bins")
        return

    count = 0
    for item_id in items:
        bin_id = random.choice(bin_ids) if bin_ids else None
        if bin_id:
            await conn.execute(text("UPDATE stock_items SET bin_id = :bid WHERE id = :id"), {"bid": bin_id, "id": item_id})
            count += 1

    await conn.commit()
    print(f"  Assigned {count} stock items to bins")


async def update_bin_counts(conn, warehouse_id):
    """Update bin current_items counts based on stock_items."""
    print("\n=== Updating Bin Item Counts ===")

    await conn.execute(text("""
        UPDATE warehouse_bins SET current_items = sub.cnt
        FROM (
            SELECT bin_id, COUNT(*) as cnt FROM stock_items
            WHERE bin_id IS NOT NULL AND warehouse_id = :wh
            GROUP BY bin_id
        ) sub
        WHERE warehouse_bins.id = sub.bin_id
    """), {"wh": warehouse_id})

    await conn.commit()
    print("  Updated bin item counts")


async def main():
    random.seed(2026)
    print("=" * 60)
    print("ILMS.AI - Seed Data for OMS & WMS AI Agents")
    print("=" * 60)

    async with engine.connect() as conn:
        # 1. Seed public schema modules + subscriptions
        tenant_id = await seed_public_modules(conn)
        if not tenant_id:
            print("FAILED: No tenant found. Aborting.")
            return

        # Switch to tenant schema
        await conn.execute(text(f'SET search_path TO "{TENANT_SCHEMA}"'))

        # 2. Get existing data references
        r = await conn.execute(text("SELECT id FROM customers"))
        customers = [str(row[0]) for row in r.fetchall()]
        print(f"\n  Found {len(customers)} existing customers")

        r = await conn.execute(text("SELECT id FROM warehouses WHERE is_active = true"))
        warehouses = [str(row[0]) for row in r.fetchall()]
        warehouse_id = warehouses[0] if warehouses else None
        print(f"  Found {len(warehouses)} warehouses, using: {warehouse_id}")

        r = await conn.execute(text("SELECT id FROM warehouse_zones WHERE warehouse_id = :wh"), {"wh": warehouse_id})
        zone_ids = [str(row[0]) for row in r.fetchall()]
        print(f"  Found {len(zone_ids)} warehouse zones")

        r = await conn.execute(text("SELECT id FROM warehouse_bins WHERE warehouse_id = :wh"), {"wh": warehouse_id})
        bin_ids = [str(row[0]) for row in r.fetchall()]
        print(f"  Found {len(bin_ids)} warehouse bins")

        # Seed zones and bins if missing
        if not zone_ids or not bin_ids:
            zone_ids, bin_ids = await seed_zones_and_bins(conn, warehouse_id)

        # Get existing orders with details for return seeding
        r = await conn.execute(text("""
            SELECT id, customer_id, status, created_at FROM orders
            WHERE status = 'DELIVERED' ORDER BY created_at DESC LIMIT 100
        """))
        orders_with_items = [{"id": str(row[0]), "customer_id": str(row[1]), "status": row[2], "created_at": row[3]} for row in r.fetchall()]
        print(f"  Found {len(orders_with_items)} delivered orders for returns")

        # 3. Seed OMS AI data
        if orders_with_items:
            await seed_return_orders(conn, customers, orders_with_items)

        await seed_oms_fraud_orders(conn, customers, warehouses)

        # 4. Create missing WMS tables and seed WMS AI data
        await create_missing_tables(conn)
        await conn.execute(text(f'SET search_path TO "{TENANT_SCHEMA}"'))

        if not warehouse_id:
            print("ERROR: No warehouse found. Cannot seed WMS data.")
            return

        # Check if workers already exist
        r = await conn.execute(text("SELECT COUNT(*) FROM warehouse_workers WHERE primary_warehouse_id = :wh"), {"wh": warehouse_id})
        worker_count = r.scalar() or 0

        if worker_count > 0:
            print(f"\n  {worker_count} workers already exist, fetching IDs...")
            r = await conn.execute(text("SELECT id FROM warehouse_workers WHERE primary_warehouse_id = :wh AND status = 'ACTIVE'"), {"wh": warehouse_id})
            worker_ids = [str(row[0]) for row in r.fetchall()]
        else:
            worker_ids = await seed_wms_workers(conn, tenant_id, warehouse_id, zone_ids)

        await seed_labor_standards(conn, tenant_id, warehouse_id)
        await seed_work_shifts(conn, tenant_id, warehouse_id, worker_ids, zone_ids)
        await seed_warehouse_tasks(conn, tenant_id, warehouse_id, zone_ids, bin_ids, worker_ids)
        await seed_stock_movements(conn, warehouse_id, bin_ids)
        await seed_productivity_metrics(conn, tenant_id, warehouse_id, worker_ids)
        await seed_stock_items_in_bins(conn, warehouse_id, bin_ids)
        await update_bin_counts(conn, warehouse_id)

    print("\n" + "=" * 60)
    print("SEEDING COMPLETE!")
    print("=" * 60)
    print("\nAI agents should now have data to work with:")
    print("  OMS AI: Fraud Detection, Smart Routing, Delivery Promise, Order Prioritization, Returns Prediction")
    print("  WMS AI: Anomaly Detection, Smart Slotting, Labor Forecasting, Replenishment")
    print("\nRefresh the AI Command Center pages to see results.")


if __name__ == "__main__":
    asyncio.run(main())
