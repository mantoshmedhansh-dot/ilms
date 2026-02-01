"""
Update Purchase Orders with Bill To and Ship To addresses.
"""
import asyncio
import sys
import os
import json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select, update
from app.database import async_session_factory
from app.models.purchase import PurchaseOrder

# Aquapurite company addresses
AQUAPURITE_BILL_TO = {
    "name": "Aquapurite Private Limited",
    "address_line1": "PLOT 36-A KH NO 181, DINDAPUR EXT",
    "address_line2": "PH-1, SHYAM VIHAR, Najafgarh",
    "city": "New Delhi",
    "district": "West Delhi",
    "state": "Delhi",
    "pincode": "110043",
    "gstin": "07ABDCA6170C1Z0",
    "state_code": "07",
    "phone": "+91-11-12345678",
    "email": "purchase@aquapurite.com"
}

# Default Ship To is same as Bill To unless specified
AQUAPURITE_SHIP_TO = {
    "name": "Aquapurite Private Limited",
    "address_line1": "PLOT 36-A KH NO 181, DINDAPUR EXT",
    "address_line2": "PH-1, SHYAM VIHAR, Najafgarh",
    "city": "New Delhi",
    "district": "West Delhi",
    "state": "Delhi",
    "pincode": "110043",
    "gstin": "07ABDCA6170C1Z0",
    "state_code": "07",
    "phone": "+91-11-12345678",
    "contact_person": "Store Manager"
}


async def update_po_addresses():
    """Update all POs with Bill To and Ship To addresses."""
    async with async_session_factory() as db:
        # Get all POs
        result = await db.execute(select(PurchaseOrder))
        pos = result.scalars().all()

        print(f"Found {len(pos)} Purchase Orders\n")

        for po in pos:
            po.bill_to = AQUAPURITE_BILL_TO
            po.ship_to = AQUAPURITE_SHIP_TO
            print(f"  Updated: {po.po_number}")

        await db.commit()
        print(f"\n✓ Updated {len(pos)} POs with Bill To and Ship To addresses")


if __name__ == "__main__":
    asyncio.run(update_po_addresses())
