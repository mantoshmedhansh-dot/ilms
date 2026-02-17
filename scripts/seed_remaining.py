"""
Seed remaining WMS AI data (warehouse_tasks, stock_movements, productivity_metrics, stock_items).
Uses bulk multi-row inserts to reduce round-trips to Supabase.
"""
import asyncio
import sys
import uuid
import random
import logging
from pathlib import Path
from datetime import datetime, timedelta, timezone, date
from decimal import Decimal

sys.path.insert(0, str(Path(__file__).parent.parent))

# Disable SQLAlchemy logging to reduce I/O
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)

from sqlalchemy import text, create_engine
from app.database import engine

TENANT_SCHEMA = "tenant_finaltest2026"

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


async def bulk_insert(conn, sql_template, rows, batch_size=50):
    """Insert rows in batches."""
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i+batch_size]
        for row in batch:
            await conn.execute(text(sql_template), row)
        await conn.commit()
    return len(rows)


async def seed_warehouse_tasks(conn, tenant_id, warehouse_id, zone_ids, bin_ids):
    """Seed warehouse tasks."""
    print("\n=== Seeding Warehouse Tasks ===")

    r = await conn.execute(text("SELECT COUNT(*) FROM warehouse_tasks WHERE warehouse_id = :wh"), {"wh": warehouse_id})
    existing = r.scalar() or 0
    if existing > 100:
        print(f"  {existing} tasks exist, skipping")
        return

    if existing > 0:
        await conn.execute(text("DELETE FROM warehouse_tasks WHERE warehouse_id = :wh"), {"wh": warehouse_id})
        await conn.commit()
        print(f"  Cleared {existing} partial tasks")

    task_types = ["PICK", "PICK", "PICK", "PUTAWAY", "PUTAWAY", "PACK", "PACK", "REPLENISH"]
    priorities = ["NORMAL", "NORMAL", "NORMAL", "HIGH", "URGENT", "LOW"]
    today = datetime.now(timezone.utc)
    rows = []
    tc = 0

    random.seed(2026)

    for day_offset in range(30):  # 30 days instead of 45
        day = today - timedelta(days=day_offset)
        for _ in range(random.randint(10, 20)):  # 10-20 per day
            tc += 1
            ttype = random.choice(task_types)
            status = "COMPLETED" if day_offset > 0 else random.choice(["COMPLETED", "IN_PROGRESS", "PENDING"])
            created = day.replace(hour=random.randint(6, 22), minute=random.randint(0, 59))
            started = created + timedelta(minutes=random.randint(1, 30)) if status in ("COMPLETED", "IN_PROGRESS") else None
            completed = started + timedelta(minutes=random.randint(3, 45)) if status == "COMPLETED" and started else None
            prod = random.choice(PRODUCTS)
            qty_req = random.randint(1, 20)

            rows.append({
                "id": str(uuid.uuid4()), "tid": tenant_id,
                "num": f"TK-{day.strftime('%Y%m%d')}-{tc:04d}",
                "ttype": ttype, "status": status, "prio": random.choice(priorities),
                "wh": warehouse_id,
                "zone": random.choice(zone_ids) if zone_ids else None,
                "src": random.choice(bin_ids) if bin_ids else None,
                "dst": random.choice(bin_ids) if bin_ids else None,
                "pid": prod[0], "pname": prod[1], "sku": prod[2],
                "qreq": qty_req,
                "qdone": qty_req if status == "COMPLETED" else random.randint(0, qty_req),
                "created": created.isoformat(),
                "started": started.isoformat() if started else None,
                "completed": completed.isoformat() if completed else None,
            })

    sql = """INSERT INTO warehouse_tasks (id, tenant_id, task_number, task_type, status, priority,
                warehouse_id, zone_id, source_bin_id, destination_bin_id,
                product_id, product_name, sku, quantity_required, quantity_completed,
                created_at, updated_at, started_at, completed_at)
             VALUES (:id, :tid, :num, :ttype, :status, :prio,
                     :wh, :zone, :src, :dst, :pid, :pname, :sku, :qreq, :qdone,
                     :created, :created, :started, :completed)"""

    n = await bulk_insert(conn, sql, rows, batch_size=30)
    print(f"  Created {n} warehouse tasks")


async def seed_stock_movements(conn, warehouse_id, bin_ids):
    """Seed stock movements."""
    print("\n=== Seeding Stock Movements ===")

    r = await conn.execute(text("SELECT COUNT(*) FROM stock_movements WHERE warehouse_id = :wh AND notes LIKE 'Auto-seeded%'"), {"wh": warehouse_id})
    existing = r.scalar() or 0
    if existing > 50:
        print(f"  {existing} movements exist, skipping")
        return

    movement_types = ["RECEIPT", "ISSUE", "ISSUE", "TRANSFER_IN", "TRANSFER_OUT", "ADJUSTMENT_PLUS", "RETURN_IN"]
    today = datetime.now(timezone.utc)
    rows = []
    mc = 0

    for day_offset in range(30):
        day = today - timedelta(days=day_offset)
        for _ in range(random.randint(5, 12)):
            mc += 1
            prod = random.choice(PRODUCTS)
            mtype = random.choice(movement_types)
            qty = random.randint(1, 20) if mtype != "ISSUE" else -random.randint(1, 15)
            bb = random.randint(10, 200)

            rows.append({
                "id": str(uuid.uuid4()),
                "num": f"SM-{day.strftime('%Y%m%d')}-{mc:04d}",
                "mtype": mtype,
                "mdate": day.replace(hour=random.randint(6, 20)).isoformat(),
                "wh": warehouse_id, "pid": prod[0], "qty": qty,
                "bb": bb, "ba": bb + qty,
                "uc": str(prod[3]), "tc": str(abs(qty) * prod[3]),
                "rtype": "ORDER" if mtype == "ISSUE" else "GRN" if mtype == "RECEIPT" else "TRANSFER",
                "rnum": f"REF-{mc:06d}",
                "notes": f"Auto-seeded {mtype} movement",
            })

    sql = """INSERT INTO stock_movements (id, movement_number, movement_type, movement_date,
                warehouse_id, product_id, quantity, balance_before, balance_after,
                unit_cost, total_cost, reference_type, reference_number, notes)
             VALUES (:id, :num, :mtype, :mdate, :wh, :pid, :qty, :bb, :ba,
                     :uc, :tc, :rtype, :rnum, :notes)"""

    n = await bulk_insert(conn, sql, rows, batch_size=30)
    print(f"  Created {n} stock movements")


async def seed_productivity_metrics(conn, tenant_id, warehouse_id, worker_ids):
    """Seed productivity metrics."""
    print("\n=== Seeding Productivity Metrics ===")

    r = await conn.execute(text("SELECT COUNT(*) FROM productivity_metrics WHERE warehouse_id = :wh"), {"wh": warehouse_id})
    existing = r.scalar() or 0
    if existing > 50:
        print(f"  {existing} metrics exist, skipping")
        return

    functions = ["PICKING", "PACKING", "PUTAWAY"]
    today = date.today()
    rows = []

    for day_offset in range(30):
        metric_date = today - timedelta(days=day_offset)
        if metric_date.weekday() == 6:
            continue

        for wid in worker_ids:
            func = random.choice(functions)
            hours = round(random.uniform(6, 8.5), 2)
            productive = round(hours * random.uniform(0.75, 0.92), 2)
            idle = round(hours - productive, 2)
            units = random.randint(120, 320)
            std_uph = 30 if func == "PICKING" else 25 if func == "PACKING" else 20
            actual_uph = round(units / productive if productive > 0 else 0, 2)
            perf_pct = round(actual_uph / std_uph * 100, 2) if std_uph > 0 else 0
            errors = random.randint(0, 4)

            rows.append({
                "id": str(uuid.uuid4()), "tid": tenant_id, "wid": wid, "wh": warehouse_id,
                "md": metric_date.isoformat(), "func": func,
                "hw": str(hours), "ph": str(productive), "ih": str(idle),
                "up": units, "lp": random.randint(30, 80), "op": random.randint(10, 35),
                "tc": random.randint(15, 45),
                "uph": str(actual_uph),
                "lph": str(round(random.randint(30, 80) / productive if productive > 0 else 0, 2)),
                "suph": str(std_uph), "pp": str(perf_pct),
                "err": errors, "acc": str(round(100 - (errors / max(units, 1) * 100), 2)),
                "lc": str(round(hours * random.uniform(150, 350), 2)),
                "cpu": str(round(random.uniform(2, 8), 4)),
            })

    sql = """INSERT INTO productivity_metrics (id, tenant_id, worker_id, warehouse_id, metric_date,
                function, hours_worked, productive_hours, idle_hours,
                units_processed, lines_processed, orders_processed, tasks_completed,
                units_per_hour, lines_per_hour, standard_units_per_hour, performance_percentage,
                errors_count, accuracy_rate, labor_cost, cost_per_unit,
                created_at, updated_at)
             VALUES (:id, :tid, :wid, :wh, :md, :func, :hw, :ph, :ih,
                     :up, :lp, :op, :tc, :uph, :lph, :suph, :pp,
                     :err, :acc, :lc, :cpu, NOW(), NOW())"""

    n = await bulk_insert(conn, sql, rows, batch_size=30)
    print(f"  Created {n} productivity metrics")


async def seed_stock_items_in_bins(conn, warehouse_id, bin_ids):
    """Seed stock items in bins."""
    print("\n=== Seeding Stock Items in Bins ===")

    r = await conn.execute(text("SELECT COUNT(*) FROM stock_items WHERE bin_id IS NOT NULL AND warehouse_id = :wh"), {"wh": warehouse_id})
    existing = r.scalar() or 0
    if existing > 20:
        print(f"  {existing} stock items in bins, skipping")
        return

    rows = []
    for i in range(50):
        prod = random.choice(PRODUCTS)
        rows.append({
            "id": str(uuid.uuid4()), "pid": prod[0], "wh": warehouse_id,
            "bid": random.choice(bin_ids) if bin_ids else None,
            "sn": f"SN-AI-{i+1:05d}", "price": str(prod[3]),
        })

    sql = """INSERT INTO stock_items (id, product_id, warehouse_id, bin_id, serial_number,
                status, received_date, purchase_price, created_at, updated_at)
             VALUES (:id, :pid, :wh, :bid, :sn, 'AVAILABLE', NOW() - INTERVAL '30 days', :price, NOW(), NOW())"""

    n = await bulk_insert(conn, sql, rows, batch_size=25)
    print(f"  Created {n} stock items in bins")

    # Update bin counts
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
    print("ILMS.AI - Seed Remaining WMS AI Data")
    print("=" * 60)

    async with engine.connect() as conn:
        await conn.execute(text(f'SET search_path TO "{TENANT_SCHEMA}"'))

        # Get references
        r = await conn.execute(text("SELECT id FROM warehouses WHERE is_active = true LIMIT 1"))
        warehouse_id = str(r.fetchone()[0])
        print(f"  Warehouse: {warehouse_id}")

        r = await conn.execute(text("SELECT id FROM warehouse_zones WHERE warehouse_id = :wh"), {"wh": warehouse_id})
        zone_ids = [str(row[0]) for row in r.fetchall()]
        print(f"  Zones: {len(zone_ids)}")

        r = await conn.execute(text("SELECT id FROM warehouse_bins WHERE warehouse_id = :wh"), {"wh": warehouse_id})
        bin_ids = [str(row[0]) for row in r.fetchall()]
        print(f"  Bins: {len(bin_ids)}")

        r = await conn.execute(text("SELECT id FROM warehouse_workers WHERE primary_warehouse_id = :wh AND status = 'ACTIVE'"), {"wh": warehouse_id})
        worker_ids = [str(row[0]) for row in r.fetchall()]
        print(f"  Workers: {len(worker_ids)}")

        tenant_id = "a1b2c3d4-e5f6-7890-abcd-ef1234567890"

        # Seed remaining data
        await seed_warehouse_tasks(conn, tenant_id, warehouse_id, zone_ids, bin_ids)
        await seed_stock_movements(conn, warehouse_id, bin_ids)
        await seed_productivity_metrics(conn, tenant_id, warehouse_id, worker_ids)
        await seed_stock_items_in_bins(conn, warehouse_id, bin_ids)

    print("\n" + "=" * 60)
    print("REMAINING SEEDING COMPLETE!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
