"""Seed script to add Fastrack Filtration Pvt. Ltd. as vendor.

Extracted from Proforma Invoice PI NO./FF/25-26/005 dated 19.11.2025
"""
import asyncio
import sys
import os
from decimal import Decimal

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select, func
from app.database import async_session_factory
from app.models.vendor import Vendor, VendorType, VendorStatus, VendorGrade, PaymentTerms


async def seed_fastrack_vendor():
    """Seed Fastrack Filtration Pvt. Ltd. as vendor."""
    async with async_session_factory() as db:
        try:
            # Check if vendor already exists
            existing = await db.execute(
                select(Vendor).where(Vendor.name.ilike("%fastrack%filtration%"))
            )
            if existing.scalar_one_or_none():
                print("Vendor 'Fastrack Filtration' already exists!")
                return False

            # Get next vendor code
            result = await db.execute(
                select(func.count(Vendor.id))
            )
            count = result.scalar() or 0
            vendor_code = f"VND-{str(count + 1).zfill(5)}"

            # Create vendor from PI details
            vendor = Vendor(
                # Identification
                vendor_code=vendor_code,
                name="Fastrack Filtration Pvt. Ltd.",
                legal_name="FASTRACK FILTRATION PVT. LTD.",
                trade_name="Fastrack Filtration",

                # Type & Status
                vendor_type=VendorType.MANUFACTURER,
                status=VendorStatus.ACTIVE,
                grade=VendorGrade.A,  # Primary vendor

                # GST Compliance (from invoice header area - Delhi based)
                gst_registered=True,
                gst_state_code="07",  # Delhi
                # GSTIN not shown in PI, will need to be updated later

                # Contact Details (to be updated with actual contact)
                contact_person="Accounts Department",

                # Address (Delhi based from bank branch location)
                address_line1="Peeragarhi",
                address_line2="",
                city="New Delhi",
                state="Delhi",
                state_code="07",
                pincode="110087",
                country="India",

                # Bank Details (from PI)
                bank_name="HDFC BANK",
                bank_branch="PEERAGARHI, DELHI",
                bank_account_number="50200076691896",
                bank_ifsc="HDFC0001127",
                bank_account_type="CURRENT",
                beneficiary_name="FASTRACK FILTRATION PVT. LTD.",

                # Payment Terms (from PI: 25% advance, 25% dispatch, 50% PDC)
                payment_terms=PaymentTerms.PARTIAL_ADVANCE,
                credit_days=30,  # 50% PDC from dispatch date
                advance_percentage=Decimal("25.00"),  # 25% advance

                # TDS (standard for contractors/manufacturers)
                tds_applicable=True,
                tds_section="194C",
                tds_rate=Decimal("2.00"),

                # Products they supply
                primary_products="""Water Purifier Manufacturing:
- AQUAPURITE BLITZ (RO+UV) @ ₹2,304/unit
- AQUAPURITE NEURA (RO+UV) @ ₹2,509/unit
- AQUAPURITE PREMIO (Hot/Ambient) @ ₹12,185/unit
- AQUAPURITE ELITZ (Hot/Cold/Ambient) @ ₹8,321/unit

Notes:
- Neura: Alkaline 4", RO Membrane & Housing provided by buyer
- Blitz: RO Membrane & Housing, Pre & Post Carbon, Sediment Spun provided by buyer
- All Models: UV LED provided by buyer

Warranty: 18 months on electronic parts, 1 year general warranty
Delivery: Within 30 days from advance payment receipt""",

                # Lead Time
                default_lead_days=30,

                # Internal Notes
                internal_notes=f"""First vendor onboarded from PI NO./FF/25-26/005 dated 19.11.2025

Payment Terms:
- 25% Advance against PI
- 25% at the time of dispatch
- Balance 50% PDC from the date of dispatch

First PI Value: ₹13,84,937 (including 18% GST)
- Blitz x 150 @ ₹2,304 = ₹3,45,600
- Neura x 150 @ ₹2,509 = ₹3,76,350
- Premio x 20 @ ₹12,185 = ₹2,43,700
- Elitz x 25 @ ₹8,321 = ₹2,08,025
- Subtotal: ₹11,73,675
- CGST 9%: ₹1,05,631
- SGST 9%: ₹1,05,631
- Grand Total: ₹13,84,937

Terms & Conditions:
1. WARRANTY: 18 months on electronic parts, 1 year SV warranty
2. DELIVERY: Within 30 days from receipt of advance payment and packing material design from buyer""",

                # Verification (mark as verified since we have PI)
                is_verified=True,
            )

            db.add(vendor)
            await db.commit()
            await db.refresh(vendor)

            print("=" * 60)
            print("VENDOR CREATED SUCCESSFULLY")
            print("=" * 60)
            print(f"Vendor Code: {vendor.vendor_code}")
            print(f"Name: {vendor.name}")
            print(f"Type: {vendor.vendor_type.value}")
            print(f"Status: {vendor.status.value}")
            print(f"Grade: {vendor.grade.value}")
            print("-" * 60)
            print("BANK DETAILS:")
            print(f"  Bank: {vendor.bank_name}")
            print(f"  A/c No: {vendor.bank_account_number}")
            print(f"  IFSC: {vendor.bank_ifsc}")
            print(f"  Branch: {vendor.bank_branch}")
            print("-" * 60)
            print("PAYMENT TERMS:")
            print(f"  Terms: {vendor.payment_terms.value}")
            print(f"  Advance: {vendor.advance_percentage}%")
            print(f"  Credit Days: {vendor.credit_days}")
            print("-" * 60)
            print(f"Lead Time: {vendor.default_lead_days} days")
            print("=" * 60)

            return True

        except Exception as e:
            await db.rollback()
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
            return False


if __name__ == "__main__":
    asyncio.run(seed_fastrack_vendor())
