"""
Seed Serviceability Data.

Creates:
1. Warehouse Serviceability - Pincode mappings for each warehouse
2. Transporter Serviceability - Route mappings for each transporter
3. Allocation Rules - Channel-wise allocation rules

Usage:
    python -m scripts.seed_serviceability
"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, and_
from app.database import async_session_factory
from app.models.warehouse import Warehouse
from app.models.transporter import Transporter, TransporterServiceability
from app.models.serviceability import (
    WarehouseServiceability,
    AllocationRule,
    AllocationType,
    ChannelCode,
)


# Mumbai Pincodes (400001-400099)
MUMBAI_PINCODES = [str(p) for p in range(400001, 400100)]

# Delhi Pincodes (110001-110099)
DELHI_PINCODES = [str(p) for p in range(110001, 110100)]

# Bangalore Pincodes (560001-560099)
BANGALORE_PINCODES = [str(p) for p in range(560001, 560100)]

# Chennai Pincodes (600001-600099)
CHENNAI_PINCODES = [str(p) for p in range(600001, 600100)]

# Kolkata Pincodes (700001-700099)
KOLKATA_PINCODES = [str(p) for p in range(700001, 700100)]

# Hyderabad Pincodes (500001-500099)
HYDERABAD_PINCODES = [str(p) for p in range(500001, 500100)]

# Pune Pincodes (411001-411099)
PUNE_PINCODES = [str(p) for p in range(411001, 411100)]

# Gurgaon/Gurugram Pincodes (122001-122099)
GURGAON_PINCODES = [str(p) for p in range(122001, 122100)]

# Noida Pincodes (201301-201399)
NOIDA_PINCODES = [str(p) for p in range(201301, 201400)]


ALLOCATION_RULES = [
    {
        "name": "Amazon FBA Orders",
        "description": "Route all Amazon orders to Amazon FBA warehouse",
        "channel_code": ChannelCode.AMAZON,
        "priority": 10,
        "allocation_type": AllocationType.FIXED,
        "priority_factors": "INVENTORY",
    },
    {
        "name": "Flipkart Orders",
        "description": "Route Flipkart orders to nearest warehouse with stock",
        "channel_code": ChannelCode.FLIPKART,
        "priority": 20,
        "allocation_type": AllocationType.NEAREST,
        "priority_factors": "PROXIMITY,INVENTORY",
    },
    {
        "name": "D2C Default - Nearest Warehouse",
        "description": "Route D2C orders to nearest warehouse with available stock",
        "channel_code": ChannelCode.D2C,
        "priority": 50,
        "allocation_type": AllocationType.NEAREST,
        "priority_factors": "PROXIMITY,INVENTORY,COST",
    },
    {
        "name": "D2C High Value - Premium Shipping",
        "description": "High value D2C orders get priority fulfillment",
        "channel_code": ChannelCode.D2C,
        "priority": 40,
        "allocation_type": AllocationType.NEAREST,
        "priority_factors": "SLA,INVENTORY",
        "min_order_value": 50000,
    },
    {
        "name": "Dealer Orders",
        "description": "Route dealer orders to regional warehouses",
        "channel_code": ChannelCode.DEALER,
        "priority": 60,
        "allocation_type": AllocationType.NEAREST,
        "priority_factors": "PROXIMITY,INVENTORY",
    },
    {
        "name": "Default Fallback",
        "description": "Fallback rule for all other channels",
        "channel_code": ChannelCode.ALL,
        "priority": 999,
        "allocation_type": AllocationType.NEAREST,
        "priority_factors": "PROXIMITY,INVENTORY,COST",
    },
]


async def seed_warehouse_serviceability(db):
    """Seed warehouse-pincode mappings."""
    print("\n=== Seeding Warehouse Serviceability ===")

    # Get warehouses
    result = await db.execute(select(Warehouse).where(Warehouse.is_active == True))
    warehouses = result.scalars().all()

    if not warehouses:
        print("No warehouses found. Please seed warehouses first.")
        return

    print(f"Found {len(warehouses)} warehouses")

    # Pincode mapping by city
    city_pincodes = {
        "Mumbai": {"pincodes": MUMBAI_PINCODES, "state": "Maharashtra", "zone": "METRO"},
        "Delhi": {"pincodes": DELHI_PINCODES, "state": "Delhi", "zone": "METRO"},
        "Bangalore": {"pincodes": BANGALORE_PINCODES, "state": "Karnataka", "zone": "METRO"},
        "Bengaluru": {"pincodes": BANGALORE_PINCODES, "state": "Karnataka", "zone": "METRO"},
        "Chennai": {"pincodes": CHENNAI_PINCODES, "state": "Tamil Nadu", "zone": "METRO"},
        "Kolkata": {"pincodes": KOLKATA_PINCODES, "state": "West Bengal", "zone": "METRO"},
        "Hyderabad": {"pincodes": HYDERABAD_PINCODES, "state": "Telangana", "zone": "METRO"},
        "Pune": {"pincodes": PUNE_PINCODES, "state": "Maharashtra", "zone": "METRO"},
        "Gurgaon": {"pincodes": GURGAON_PINCODES, "state": "Haryana", "zone": "METRO"},
        "Gurugram": {"pincodes": GURGAON_PINCODES, "state": "Haryana", "zone": "METRO"},
        "Noida": {"pincodes": NOIDA_PINCODES, "state": "Uttar Pradesh", "zone": "METRO"},
    }

    total_created = 0

    for warehouse in warehouses:
        # Get pincodes for this warehouse based on city
        wh_city = warehouse.city
        pincodes_info = None

        for city, info in city_pincodes.items():
            if city.lower() in wh_city.lower():
                pincodes_info = info
                break

        if not pincodes_info:
            # Default - assign some pincodes based on warehouse pincode prefix
            if warehouse.pincode:
                prefix = warehouse.pincode[:3]
                pincodes_info = {
                    "pincodes": [f"{prefix}{str(i).zfill(3)}" for i in range(1, 100)],
                    "state": warehouse.state,
                    "zone": "REGIONAL"
                }
            else:
                continue

        pincodes = pincodes_info["pincodes"]
        state = pincodes_info["state"]
        zone = pincodes_info["zone"]

        created = 0
        for pincode in pincodes:
            # Check if already exists
            existing = await db.execute(
                select(WarehouseServiceability).where(
                    and_(
                        WarehouseServiceability.warehouse_id == warehouse.id,
                        WarehouseServiceability.pincode == pincode
                    )
                )
            )
            if existing.scalar_one_or_none():
                continue

            ws = WarehouseServiceability(
                warehouse_id=warehouse.id,
                pincode=pincode,
                is_serviceable=True,
                cod_available=True,
                prepaid_available=True,
                estimated_days=2 if zone == "METRO" else 4,
                priority=10 if zone == "METRO" else 50,
                shipping_cost=50.0 if zone == "METRO" else 80.0,
                city=wh_city,
                state=state,
                zone=zone,
                is_active=True
            )
            db.add(ws)
            created += 1

        if created > 0:
            await db.commit()
            total_created += created
            print(f"  {warehouse.code} ({warehouse.city}): {created} pincodes added")

    print(f"Total warehouse serviceability records created: {total_created}")


async def seed_transporter_serviceability(db):
    """Seed transporter route mappings."""
    print("\n=== Seeding Transporter Serviceability ===")

    # Get transporters
    result = await db.execute(select(Transporter).where(Transporter.is_active == True))
    transporters = result.scalars().all()

    if not transporters:
        print("No transporters found. Please seed transporters first.")
        return

    print(f"Found {len(transporters)} transporters")

    # Get warehouses for origin pincodes
    wh_result = await db.execute(select(Warehouse).where(Warehouse.is_active == True))
    warehouses = wh_result.scalars().all()
    origin_pincodes = list(set(wh.pincode for wh in warehouses if wh.pincode))

    if not origin_pincodes:
        print("No warehouse pincodes found.")
        return

    # All destination pincodes
    all_destinations = (
        MUMBAI_PINCODES[:50] +  # First 50 from each city
        DELHI_PINCODES[:50] +
        BANGALORE_PINCODES[:50] +
        CHENNAI_PINCODES[:50] +
        KOLKATA_PINCODES[:50] +
        HYDERABAD_PINCODES[:50] +
        PUNE_PINCODES[:50] +
        GURGAON_PINCODES[:50] +
        NOIDA_PINCODES[:50]
    )

    total_created = 0

    for transporter in transporters:
        created = 0

        for origin in origin_pincodes:
            # Each transporter covers different destinations
            # Courier types cover more pincodes
            if transporter.transporter_type.value == "COURIER":
                destinations = all_destinations
            elif transporter.transporter_type.value == "SELF_SHIP":
                # Self-ship covers local pincodes
                destinations = all_destinations[:100]
            else:
                destinations = all_destinations[:50]

            for dest in destinations:
                # Check if already exists
                existing = await db.execute(
                    select(TransporterServiceability).where(
                        and_(
                            TransporterServiceability.transporter_id == transporter.id,
                            TransporterServiceability.origin_pincode == origin,
                            TransporterServiceability.destination_pincode == dest
                        )
                    )
                )
                if existing.scalar_one_or_none():
                    continue

                # Calculate estimated days based on zones
                is_same_zone = origin[:3] == dest[:3]
                est_days = 1 if is_same_zone else 3

                # Calculate rate
                rate = 40.0 if is_same_zone else 80.0
                if transporter.rate_per_kg:
                    rate = transporter.base_rate or rate

                ts = TransporterServiceability(
                    transporter_id=transporter.id,
                    origin_pincode=origin,
                    destination_pincode=dest,
                    is_serviceable=True,
                    estimated_days=est_days,
                    cod_available=transporter.supports_cod,
                    prepaid_available=transporter.supports_prepaid,
                    surface_available=transporter.supports_surface,
                    express_available=transporter.supports_express,
                    rate=rate,
                    zone="LOCAL" if is_same_zone else "NATIONAL"
                )
                db.add(ts)
                created += 1

        if created > 0:
            await db.commit()
            total_created += created
            print(f"  {transporter.code}: {created} routes added")

    print(f"Total transporter serviceability records created: {total_created}")


async def seed_allocation_rules(db):
    """Seed allocation rules."""
    print("\n=== Seeding Allocation Rules ===")

    created = 0
    for rule_data in ALLOCATION_RULES:
        # Check if rule with same name exists
        existing = await db.execute(
            select(AllocationRule).where(AllocationRule.name == rule_data["name"])
        )
        if existing.scalar_one_or_none():
            print(f"  Rule '{rule_data['name']}' already exists, skipping")
            continue

        rule = AllocationRule(
            name=rule_data["name"],
            description=rule_data.get("description"),
            channel_code=rule_data["channel_code"],
            priority=rule_data["priority"],
            allocation_type=rule_data["allocation_type"],
            priority_factors=rule_data.get("priority_factors"),
            min_order_value=rule_data.get("min_order_value"),
            max_order_value=rule_data.get("max_order_value"),
            allow_split=rule_data.get("allow_split", False),
            is_active=True
        )
        db.add(rule)
        created += 1
        print(f"  Created rule: {rule_data['name']}")

    if created > 0:
        await db.commit()

    print(f"Total allocation rules created: {created}")


async def main():
    """Main seed function."""
    print("=" * 60)
    print("SERVICEABILITY DATA SEEDING")
    print("=" * 60)

    async with async_session_factory() as db:
        # Seed in order
        await seed_allocation_rules(db)
        await seed_warehouse_serviceability(db)
        await seed_transporter_serviceability(db)

    print("\n" + "=" * 60)
    print("SEEDING COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
