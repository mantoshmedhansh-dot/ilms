"""
Add popular pincodes for serviceability.
Quick script to add pincodes for major metro cities.
"""
import asyncio
import sys
from pathlib import Path
import uuid

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, text
from app.database import async_session_factory
from app.models.warehouse import Warehouse
from app.models.serviceability import WarehouseServiceability


# Popular pincodes matching cache_jobs.py
POPULAR_PINCODES = {
    # Delhi NCR
    "110001": {"city": "Delhi", "state": "Delhi", "zone": "METRO", "days": 2},
    "110002": {"city": "Delhi", "state": "Delhi", "zone": "METRO", "days": 2},
    "110003": {"city": "Delhi", "state": "Delhi", "zone": "METRO", "days": 2},
    "110005": {"city": "Delhi", "state": "Delhi", "zone": "METRO", "days": 2},
    "110006": {"city": "Delhi", "state": "Delhi", "zone": "METRO", "days": 2},
    # Gurgaon
    "122001": {"city": "Gurgaon", "state": "Haryana", "zone": "METRO", "days": 2},
    "122002": {"city": "Gurgaon", "state": "Haryana", "zone": "METRO", "days": 2},
    "122003": {"city": "Gurgaon", "state": "Haryana", "zone": "METRO", "days": 2},
    "122004": {"city": "Gurgaon", "state": "Haryana", "zone": "METRO", "days": 2},
    "122005": {"city": "Gurgaon", "state": "Haryana", "zone": "METRO", "days": 2},
    # Noida
    "201301": {"city": "Noida", "state": "Uttar Pradesh", "zone": "METRO", "days": 2},
    "201302": {"city": "Noida", "state": "Uttar Pradesh", "zone": "METRO", "days": 2},
    "201303": {"city": "Noida", "state": "Uttar Pradesh", "zone": "METRO", "days": 2},
    "201304": {"city": "Noida", "state": "Uttar Pradesh", "zone": "METRO", "days": 2},
    "201305": {"city": "Noida", "state": "Uttar Pradesh", "zone": "METRO", "days": 2},
    # Mumbai
    "400001": {"city": "Mumbai", "state": "Maharashtra", "zone": "METRO", "days": 2},
    "400002": {"city": "Mumbai", "state": "Maharashtra", "zone": "METRO", "days": 2},
    "400003": {"city": "Mumbai", "state": "Maharashtra", "zone": "METRO", "days": 2},
    "400050": {"city": "Mumbai", "state": "Maharashtra", "zone": "METRO", "days": 2},
    "400051": {"city": "Mumbai", "state": "Maharashtra", "zone": "METRO", "days": 2},
    "400053": {"city": "Mumbai", "state": "Maharashtra", "zone": "METRO", "days": 2},
    "400054": {"city": "Mumbai", "state": "Maharashtra", "zone": "METRO", "days": 2},
    "400055": {"city": "Mumbai", "state": "Maharashtra", "zone": "METRO", "days": 2},
    "400056": {"city": "Mumbai", "state": "Maharashtra", "zone": "METRO", "days": 2},
    "400057": {"city": "Mumbai", "state": "Maharashtra", "zone": "METRO", "days": 2},
    # Bangalore
    "560001": {"city": "Bangalore", "state": "Karnataka", "zone": "METRO", "days": 2},
    "560002": {"city": "Bangalore", "state": "Karnataka", "zone": "METRO", "days": 2},
    "560003": {"city": "Bangalore", "state": "Karnataka", "zone": "METRO", "days": 2},
    "560004": {"city": "Bangalore", "state": "Karnataka", "zone": "METRO", "days": 2},
    "560005": {"city": "Bangalore", "state": "Karnataka", "zone": "METRO", "days": 2},
    "560008": {"city": "Bangalore", "state": "Karnataka", "zone": "METRO", "days": 2},
    "560009": {"city": "Bangalore", "state": "Karnataka", "zone": "METRO", "days": 2},
    "560010": {"city": "Bangalore", "state": "Karnataka", "zone": "METRO", "days": 2},
    "560011": {"city": "Bangalore", "state": "Karnataka", "zone": "METRO", "days": 2},
    "560012": {"city": "Bangalore", "state": "Karnataka", "zone": "METRO", "days": 2},
    # Chennai
    "600001": {"city": "Chennai", "state": "Tamil Nadu", "zone": "METRO", "days": 3},
    "600002": {"city": "Chennai", "state": "Tamil Nadu", "zone": "METRO", "days": 3},
    "600003": {"city": "Chennai", "state": "Tamil Nadu", "zone": "METRO", "days": 3},
    "600004": {"city": "Chennai", "state": "Tamil Nadu", "zone": "METRO", "days": 3},
    "600005": {"city": "Chennai", "state": "Tamil Nadu", "zone": "METRO", "days": 3},
    # Kolkata
    "700001": {"city": "Kolkata", "state": "West Bengal", "zone": "METRO", "days": 3},
    "700002": {"city": "Kolkata", "state": "West Bengal", "zone": "METRO", "days": 3},
    "700003": {"city": "Kolkata", "state": "West Bengal", "zone": "METRO", "days": 3},
    "700004": {"city": "Kolkata", "state": "West Bengal", "zone": "METRO", "days": 3},
    "700005": {"city": "Kolkata", "state": "West Bengal", "zone": "METRO", "days": 3},
    # Hyderabad
    "500001": {"city": "Hyderabad", "state": "Telangana", "zone": "METRO", "days": 3},
    "500002": {"city": "Hyderabad", "state": "Telangana", "zone": "METRO", "days": 3},
    "500003": {"city": "Hyderabad", "state": "Telangana", "zone": "METRO", "days": 3},
    "500004": {"city": "Hyderabad", "state": "Telangana", "zone": "METRO", "days": 3},
    "500005": {"city": "Hyderabad", "state": "Telangana", "zone": "METRO", "days": 3},
    # Pune
    "411001": {"city": "Pune", "state": "Maharashtra", "zone": "METRO", "days": 2},
    "411002": {"city": "Pune", "state": "Maharashtra", "zone": "METRO", "days": 2},
    "411003": {"city": "Pune", "state": "Maharashtra", "zone": "METRO", "days": 2},
    "411004": {"city": "Pune", "state": "Maharashtra", "zone": "METRO", "days": 2},
    "411005": {"city": "Pune", "state": "Maharashtra", "zone": "METRO", "days": 2},
}


async def main():
    print("Adding popular pincodes for serviceability...")

    async with async_session_factory() as session:
        # Get the first warehouse (we need at least one)
        result = await session.execute(
            select(Warehouse).where(Warehouse.is_active == True).limit(1)
        )
        warehouse = result.scalar_one_or_none()

        if not warehouse:
            print("No active warehouse found. Creating a default warehouse...")
            # This shouldn't happen if OMS/WMS data is seeded
            return

        print(f"Using warehouse: {warehouse.code} ({warehouse.name})")

        added = 0
        skipped = 0

        for pincode, info in POPULAR_PINCODES.items():
            # Check if pincode already exists
            existing = await session.execute(
                select(WarehouseServiceability).where(
                    WarehouseServiceability.pincode == pincode
                )
            )
            if existing.scalar_one_or_none():
                skipped += 1
                continue

            ws = WarehouseServiceability(
                warehouse_id=warehouse.id,
                pincode=pincode,
                is_serviceable=True,
                cod_available=True,
                prepaid_available=True,
                estimated_days=info["days"],
                priority=10,
                shipping_cost=50.0,
                city=info["city"],
                state=info["state"],
                zone=info["zone"],
                is_active=True
            )
            session.add(ws)
            added += 1

        await session.commit()

        print(f"Added {added} new pincodes, skipped {skipped} existing ones.")

        # Show final count
        result = await session.execute(
            text("SELECT COUNT(*) FROM warehouse_serviceability")
        )
        total = result.scalar()
        print(f"Total pincodes in database: {total}")


if __name__ == "__main__":
    asyncio.run(main())
