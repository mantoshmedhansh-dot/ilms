"""Seed OMS/WMS data - Transporters and Warehouse Zones."""
import asyncio
import uuid
from datetime import datetime

from sqlalchemy import select
from app.database import async_session_factory
from app.models.transporter import Transporter, TransporterType
from app.models.wms import WarehouseZone, WarehouseBin, ZoneType, BinType
from app.models.warehouse import Warehouse


async def seed_transporters(db):
    """Seed transporter data."""
    print("\n=== Seeding Transporters ===")

    transporters = [
        {
            "code": "DELHIVERY",
            "name": "Delhivery Logistics",
            "transporter_type": TransporterType.COURIER,
            "supports_cod": True,
            "supports_prepaid": True,
            "supports_reverse_pickup": True,
            "supports_express": True,
            "tracking_url_template": "https://www.delhivery.com/track/package/{awb}",
            "contact_name": "Delhivery Support",
            "contact_phone": "1800-103-0100",
            "base_rate": 48.0,
            "rate_per_kg": 14.0,
            "cod_charges": 35.0,
            "cod_percentage": 2.0,
            "awb_prefix": "DEL",
            "priority": 1,
        },
        {
            "code": "BLUEDART",
            "name": "BlueDart Express",
            "transporter_type": TransporterType.COURIER,
            "supports_cod": True,
            "supports_prepaid": True,
            "supports_reverse_pickup": True,
            "supports_express": True,
            "tracking_url_template": "https://www.bluedart.com/tracking/{awb}",
            "contact_phone": "1860-233-1234",
            "base_rate": 55.0,
            "rate_per_kg": 18.0,
            "cod_charges": 40.0,
            "cod_percentage": 2.5,
            "awb_prefix": "BD",
            "priority": 2,
        },
        {
            "code": "DTDC",
            "name": "DTDC Courier",
            "transporter_type": TransporterType.COURIER,
            "supports_cod": True,
            "supports_prepaid": True,
            "supports_surface": True,
            "tracking_url_template": "https://www.dtdc.in/tracking/{awb}",
            "contact_phone": "1800-209-1234",
            "base_rate": 40.0,
            "rate_per_kg": 12.0,
            "cod_charges": 25.0,
            "awb_prefix": "DTDC",
            "priority": 3,
        },
        {
            "code": "ECOM",
            "name": "Ecom Express",
            "transporter_type": TransporterType.COURIER,
            "supports_cod": True,
            "supports_prepaid": True,
            "supports_reverse_pickup": True,
            "tracking_url_template": "https://www.ecomexpress.in/tracking/{awb}",
            "contact_phone": "1800-123-0000",
            "base_rate": 45.0,
            "rate_per_kg": 14.0,
            "cod_charges": 30.0,
            "awb_prefix": "ECOM",
            "priority": 4,
        },
        {
            "code": "XPRESSBEES",
            "name": "Xpressbees Logistics",
            "transporter_type": TransporterType.COURIER,
            "supports_cod": True,
            "supports_prepaid": True,
            "supports_reverse_pickup": True,
            "tracking_url_template": "https://www.xpressbees.com/track/{awb}",
            "contact_phone": "1800-123-5555",
            "base_rate": 42.0,
            "rate_per_kg": 13.0,
            "cod_charges": 28.0,
            "awb_prefix": "XB",
            "priority": 5,
        },
        {
            "code": "SHADOWFAX",
            "name": "Shadowfax Technologies",
            "transporter_type": TransporterType.COURIER,
            "supports_cod": True,
            "supports_prepaid": True,
            "supports_express": True,
            "tracking_url_template": "https://tracker.shadowfax.in/{awb}",
            "base_rate": 38.0,
            "rate_per_kg": 11.0,
            "cod_charges": 25.0,
            "awb_prefix": "SF",
            "priority": 6,
        },
        {
            "code": "SELF",
            "name": "Aquapurite Own Fleet",
            "transporter_type": TransporterType.SELF_SHIP,
            "supports_cod": True,
            "supports_prepaid": True,
            "base_rate": 0.0,
            "rate_per_kg": 0.0,
            "cod_charges": 0.0,
            "awb_prefix": "AP",
            "priority": 0,
        },
        {
            "code": "INDIAPOST",
            "name": "India Post (Speed Post)",
            "transporter_type": TransporterType.COURIER,
            "supports_cod": False,
            "supports_prepaid": True,
            "supports_surface": True,
            "tracking_url_template": "https://www.indiapost.gov.in/track/{awb}",
            "base_rate": 30.0,
            "rate_per_kg": 8.0,
            "awb_prefix": "EE",
            "priority": 10,
        },
    ]

    created = 0
    for t_data in transporters:
        # Check if exists
        existing = await db.execute(
            select(Transporter).where(Transporter.code == t_data["code"])
        )
        if existing.scalar_one_or_none():
            print(f"  - {t_data['name']}: Already exists")
            continue

        transporter = Transporter(**t_data)
        db.add(transporter)
        print(f"  + {t_data['name']}: Created")
        created += 1

    await db.commit()
    print(f"\nTransporters: {created} created")
    return created


async def seed_warehouse_zones(db):
    """Seed warehouse zones for existing warehouses."""
    print("\n=== Seeding Warehouse Zones ===")

    # Get existing warehouses
    result = await db.execute(select(Warehouse).where(Warehouse.is_active == True))
    warehouses = result.scalars().all()

    if not warehouses:
        print("  No warehouses found. Creating default warehouse...")
        warehouse = Warehouse(
            code="DELHI-WH",
            name="Delhi Main Warehouse",
            address_line1="Plot 36-A, Najafgarh",
            city="Delhi",
            state="Delhi",
            pincode="110043",
            is_active=True,
        )
        db.add(warehouse)
        await db.flush()
        warehouses = [warehouse]

    zones_template = [
        {
            "zone_code": "RCV",
            "zone_name": "Receiving Area",
            "zone_type": ZoneType.RECEIVING,
            "description": "Inbound goods receiving and inspection area",
            "is_pickable": False,
            "is_receivable": True,
            "max_capacity": 500,
            "sort_order": 1,
        },
        {
            "zone_code": "STG-A",
            "zone_name": "Storage Zone A - Water Purifiers",
            "zone_type": ZoneType.STORAGE,
            "description": "Main storage for finished goods - Water Purifiers",
            "is_pickable": True,
            "is_receivable": True,
            "max_capacity": 1000,
            "sort_order": 2,
        },
        {
            "zone_code": "STG-B",
            "zone_name": "Storage Zone B - Spare Parts",
            "zone_type": ZoneType.STORAGE,
            "description": "Storage for spare parts and consumables",
            "is_pickable": True,
            "is_receivable": True,
            "max_capacity": 2000,
            "sort_order": 3,
        },
        {
            "zone_code": "STG-C",
            "zone_name": "Storage Zone C - Filters",
            "zone_type": ZoneType.STORAGE,
            "description": "Storage for filters and membranes",
            "is_pickable": True,
            "is_receivable": True,
            "max_capacity": 1500,
            "sort_order": 4,
        },
        {
            "zone_code": "PICK",
            "zone_name": "Picking Zone",
            "zone_type": ZoneType.PICKING,
            "description": "Active picking area for order fulfillment",
            "is_pickable": True,
            "is_receivable": True,
            "max_capacity": 500,
            "sort_order": 5,
        },
        {
            "zone_code": "PACK",
            "zone_name": "Packing Station",
            "zone_type": ZoneType.PACKING,
            "description": "Order packing and labeling area",
            "is_pickable": False,
            "is_receivable": False,
            "max_capacity": 100,
            "sort_order": 6,
        },
        {
            "zone_code": "SHIP",
            "zone_name": "Shipping Dock",
            "zone_type": ZoneType.SHIPPING,
            "description": "Outbound shipping and dispatch area",
            "is_pickable": False,
            "is_receivable": False,
            "max_capacity": 200,
            "sort_order": 7,
        },
        {
            "zone_code": "RTN",
            "zone_name": "Returns Processing",
            "zone_type": ZoneType.RETURNS,
            "description": "Returns inspection and processing area",
            "is_pickable": False,
            "is_receivable": True,
            "max_capacity": 300,
            "sort_order": 8,
        },
        {
            "zone_code": "QC",
            "zone_name": "Quality Control / Quarantine",
            "zone_type": ZoneType.QUARANTINE,
            "description": "Quality hold and inspection area",
            "is_pickable": False,
            "is_receivable": True,
            "max_capacity": 200,
            "sort_order": 9,
        },
    ]

    zones_created = 0
    bins_created = 0

    for warehouse in warehouses:
        print(f"\n  Warehouse: {warehouse.name}")

        for zone_data in zones_template:
            # Check if exists
            existing = await db.execute(
                select(WarehouseZone).where(
                    WarehouseZone.warehouse_id == warehouse.id,
                    WarehouseZone.zone_code == zone_data["zone_code"]
                )
            )
            if existing.scalar_one_or_none():
                print(f"    - Zone {zone_data['zone_code']}: Already exists")
                continue

            zone = WarehouseZone(
                warehouse_id=warehouse.id,
                **zone_data
            )
            db.add(zone)
            await db.flush()
            print(f"    + Zone {zone_data['zone_code']}: Created")
            zones_created += 1

            # Create bins for storage zones
            if zone_data["zone_type"] == ZoneType.STORAGE:
                bin_count = await create_bins_for_zone(db, warehouse.id, zone)
                bins_created += bin_count

    await db.commit()
    print(f"\nZones: {zones_created} created, Bins: {bins_created} created")
    return zones_created, bins_created


async def create_bins_for_zone(db, warehouse_id: uuid.UUID, zone: WarehouseZone) -> int:
    """Create bins for a storage zone."""
    aisles = ["A", "B", "C"]
    racks = range(1, 6)  # 5 racks
    shelves = range(1, 5)  # 4 shelves

    count = 0
    pick_seq = 0

    for aisle in aisles:
        for rack in racks:
            for shelf in shelves:
                bin_code = f"{zone.zone_code}-{aisle}{rack:02d}-{shelf:02d}"

                # Check if exists by bin_code OR barcode
                existing = await db.execute(
                    select(WarehouseBin).where(
                        WarehouseBin.warehouse_id == warehouse_id,
                        WarehouseBin.bin_code == bin_code
                    )
                )
                if existing.scalar_one_or_none():
                    pick_seq += 1
                    continue

                # Also check barcode uniqueness
                barcode_check = await db.execute(
                    select(WarehouseBin).where(WarehouseBin.barcode == bin_code)
                )
                if barcode_check.scalar_one_or_none():
                    pick_seq += 1
                    continue

                bin = WarehouseBin(
                    warehouse_id=warehouse_id,
                    zone_id=zone.id,
                    bin_code=bin_code,
                    barcode=bin_code,
                    aisle=aisle,
                    rack=f"{rack:02d}",
                    shelf=f"{shelf:02d}",
                    bin_type=BinType.SHELF,
                    max_capacity=20,
                    is_active=True,
                    is_pickable=zone.is_pickable,
                    is_receivable=zone.is_receivable,
                    pick_sequence=pick_seq,
                )
                db.add(bin)
                await db.flush()  # Flush each bin to avoid batch constraint violations
                count += 1
                pick_seq += 1

    return count


async def main():
    """Run seed."""
    print("=" * 50)
    print("  OMS/WMS Data Seeding")
    print("=" * 50)

    async with async_session_factory() as db:
        await seed_transporters(db)
        await seed_warehouse_zones(db)

    print("\n" + "=" * 50)
    print("  Seeding Complete!")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
