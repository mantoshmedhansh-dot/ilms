"""
Script to link STOS Industrial Corporation vendor to ST supplier code.
Run this script to fix the "Supplier code not mapped" error.
"""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from app.database import async_session_maker
from app.models.vendor import Vendor
from app.models.serialization import SupplierCode
import uuid


async def link_stos_vendor():
    """Link STOS vendor to ST supplier code."""
    async with async_session_maker() as db:
        print("=" * 60)
        print("LINKING STOS VENDOR TO SUPPLIER CODE")
        print("=" * 60)

        # Find STOS vendor
        print("\n1. Finding STOS vendor...")
        vendor_result = await db.execute(
            select(Vendor).where(Vendor.name.ilike("%STOS%"))
        )
        vendor = vendor_result.scalar_one_or_none()

        if not vendor:
            print("   ERROR: STOS vendor not found!")
            print("   Looking for any vendor with 'STOS' in name...")

            # List all vendors
            all_vendors = await db.execute(select(Vendor).limit(10))
            vendors = all_vendors.scalars().all()
            print(f"   Found {len(vendors)} vendors:")
            for v in vendors:
                print(f"     - {v.name} (ID: {v.id})")
            return

        print(f"   Found: {vendor.name}")
        print(f"   Vendor ID: {vendor.id}")
        print(f"   Vendor Code: {vendor.code}")

        # Check if vendor already has a supplier code
        print("\n2. Checking if vendor already linked...")
        existing_link = await db.execute(
            select(SupplierCode).where(SupplierCode.vendor_id == str(vendor.id))
        )
        existing = existing_link.scalar_one_or_none()

        if existing:
            print(f"   Vendor already linked to supplier code: {existing.code}")
            print("   No action needed!")
            return

        # Find or create ST supplier code
        print("\n3. Finding ST supplier code...")
        st_result = await db.execute(
            select(SupplierCode).where(SupplierCode.code == "ST")
        )
        st_code = st_result.scalar_one_or_none()

        if st_code:
            print(f"   Found ST supplier code")
            print(f"   Current vendor_id: {st_code.vendor_id or 'None'}")

            if st_code.vendor_id:
                print(f"   ST code already linked to another vendor!")
                print("   Creating new supplier code for STOS...")

                # Create a new code for STOS
                new_code = SupplierCode(
                    id=str(uuid.uuid4()),
                    code="SO",  # Alternative code
                    name=vendor.name,
                    vendor_id=str(vendor.id),
                    description=f"Auto-linked to {vendor.name}",
                    is_active=True,
                )
                db.add(new_code)
                await db.commit()
                print(f"   Created new supplier code: SO")
            else:
                # Link ST to STOS vendor
                st_code.vendor_id = str(vendor.id)
                await db.commit()
                print(f"   Linked ST supplier code to {vendor.name}")
        else:
            print("   ST supplier code not found, creating...")
            new_st = SupplierCode(
                id=str(uuid.uuid4()),
                code="ST",
                name=vendor.name,
                vendor_id=str(vendor.id),
                description=f"STOS Industrial - Premium manufacturer",
                is_active=True,
            )
            db.add(new_st)
            await db.commit()
            print(f"   Created ST supplier code linked to {vendor.name}")

        # Verify
        print("\n4. Verifying link...")
        verify_result = await db.execute(
            select(SupplierCode).where(SupplierCode.vendor_id == str(vendor.id))
        )
        verified = verify_result.scalar_one_or_none()

        if verified:
            print(f"   SUCCESS: {vendor.name} linked to supplier code '{verified.code}'")
        else:
            print("   ERROR: Link verification failed!")

        print("\n" + "=" * 60)
        print("DONE - You can now approve POs for STOS vendor")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(link_stos_vendor())
