"""Seed script to add STOS Industrial Corporation Pvt. Ltd. as vendor.

Extracted from:
- Quotation for Spare Parts dated November 06, 2025
- Cancelled Cheque - ICICI Bank
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


async def seed_stos_vendor():
    """Seed STOS Industrial Corporation Pvt. Ltd. as vendor."""
    async with async_session_factory() as db:
        try:
            # Check if vendor already exists
            existing = await db.execute(
                select(Vendor).where(Vendor.gstin == "09AACCO4091J1Z6")
            )
            if existing.scalar_one_or_none():
                print("Vendor 'STOS Industrial Corporation' already exists!")
                return False

            # Get next vendor code
            result = await db.execute(
                select(func.count(Vendor.id))
            )
            count = result.scalar() or 0
            vendor_code = f"VND-{str(count + 1).zfill(5)}"

            # Create vendor from quotation and cheque details
            vendor = Vendor(
                # Identification
                vendor_code=vendor_code,
                name="STOS Industrial Corporation Pvt. Ltd.",
                legal_name="STOS INDUSTRIAL CORPORATION PRIVATE LIMITED",
                trade_name="STOS Industrial (formerly Oxytek Components Pvt. Ltd.)",

                # Type & Status
                vendor_type=VendorType.SPARE_PARTS,
                status=VendorStatus.ACTIVE,
                grade=VendorGrade.A,

                # GST Compliance
                gstin="09AACCO4091J1Z6",
                gst_registered=True,
                gst_state_code="09",  # Uttar Pradesh

                # MSME Registration
                msme_registered=True,
                msme_number="UDYAM-UP-29-0014615",

                # Contact Details
                contact_person="Saurabh Garg",
                designation="Head – Operations",
                email="ssindustries.mfg@gmail.com",
                mobile="9810416309",

                # Factory/Works Address (Ghaziabad)
                address_line1="E-180, Sector-17, Kavi Nagar Industrial Area",
                address_line2="",
                city="Ghaziabad",
                state="Uttar Pradesh",
                state_code="09",
                pincode="201002",
                country="India",

                # Head Office Address (Delhi) - stored in warehouse_address
                warehouse_address={
                    "type": "HEAD_OFFICE",
                    "address_line1": "9/98, II Floor, Near Karan Street",
                    "address_line2": "Vishwas Nagar, Shadara",
                    "city": "East Delhi",
                    "state": "Delhi",
                    "pincode": "110032"
                },

                # Bank Details (from Cancelled Cheque - ICICI)
                bank_name="ICICI Bank",
                bank_branch="Ghaziabad - Choudhary More Branch",
                bank_account_number="125605002916",
                bank_ifsc="ICIC0001256",
                bank_account_type="CURRENT",
                beneficiary_name="STOS INDUSTRIAL CORPORATION PRIVATE LIMITED",

                # Payment Terms (45 days from invoice)
                payment_terms=PaymentTerms.NET_45,
                credit_days=45,
                advance_percentage=Decimal("0"),

                # TDS (standard for spare parts supplier)
                tds_applicable=True,
                tds_section="194C",
                tds_rate=Decimal("2.00"),

                # MOQ
                min_order_quantity=2000,

                # Products they supply
                primary_products="""Water Purifier Spare Parts (Ex-Works + 18% GST):

GREY FILTER ASSEMBLIES:
- SDGR01045861: Sediment Filter Assy (Grey) @ ₹97
- PRGR01045862: Pre Carbon Filter Assy (Grey) @ ₹114
- MBFA01045863: Membrane Filter Assy (Grey) @ ₹398
- PCBA01045864: Post Carbon Block Assy (Grey) @ ₹61

WHITE FILTER ASSEMBLIES:
- SDWH01048691: Sediment Spun Filter Assy (White) @ ₹76
- PRWH01048692: Pre Carbon Filter Assy (White) @ ₹111
- MBWH01048693: Membrane Filter Assy (White) @ ₹375
- PCWH01048694: Post Carbon Block Assy (White) @ ₹58

OTHER COMPONENTS:
- PFAS01045860: Pre Filter Assembly with Silicon Seal & Connectors (Grey) @ ₹245
- SPRV02068640: Plastic PRV @ ₹180
- SDVL01040035: Brass Diverter Valve @ ₹150

Note: Prices are ex-works, freight charged as actual.""",

                # Lead Time
                default_lead_days=14,

                # Internal Notes
                internal_notes="""Vendor onboarded from Quotation dated November 06, 2025

Company Background:
- Formerly known as "Oxytek Components Pvt. Ltd."
- MSME Registered: UDYAM-UP-29-0014615
- Specializes in water purifier spare parts and filter assemblies

Terms and Conditions:
1. Prices are basic + 18% GST extra
2. Ex-works pricing, freight charged as actual
3. Payment Terms: 45 days from date of invoice
4. Minimum Order Quantity: 2000 No.'s per item

Bank Details (from Cancelled Cheque):
- ICICI Bank, Ghaziabad - Choudhary More Branch
- Plot No.270, Ambedkar Road, Opp. Nehru Yuvakendra
- Choudhary More, Ghaziabad -201001

Contact:
- Saurabh Garg (Head – Operations)
- Mobile: 9810416309
- Email: ssindustries.mfg@gmail.com""",

                # Verification
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
            print(f"Legal Name: {vendor.legal_name}")
            print(f"Type: {vendor.vendor_type.value}")
            print(f"Status: {vendor.status.value}")
            print(f"Grade: {vendor.grade.value}")
            print("-" * 60)
            print("GST & COMPLIANCE:")
            print(f"  GSTIN: {vendor.gstin}")
            print(f"  State Code: {vendor.gst_state_code} (Uttar Pradesh)")
            print(f"  MSME: {vendor.msme_number}")
            print("-" * 60)
            print("CONTACT:")
            print(f"  Person: {vendor.contact_person}")
            print(f"  Designation: {vendor.designation}")
            print(f"  Mobile: {vendor.mobile}")
            print(f"  Email: {vendor.email}")
            print("-" * 60)
            print("ADDRESS:")
            print(f"  {vendor.address_line1}")
            print(f"  {vendor.city}, {vendor.state} - {vendor.pincode}")
            print("-" * 60)
            print("BANK DETAILS:")
            print(f"  Bank: {vendor.bank_name}")
            print(f"  A/c No: {vendor.bank_account_number}")
            print(f"  IFSC: {vendor.bank_ifsc}")
            print(f"  Branch: {vendor.bank_branch}")
            print("-" * 60)
            print("PAYMENT TERMS:")
            print(f"  Terms: {vendor.payment_terms.value}")
            print(f"  Credit Days: {vendor.credit_days}")
            print(f"  MOQ: {vendor.min_order_quantity} units per item")
            print("=" * 60)

            return True

        except Exception as e:
            await db.rollback()
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
            return False


if __name__ == "__main__":
    asyncio.run(seed_stos_vendor())
