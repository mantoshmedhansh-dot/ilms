"""
Create Purchase Order for STOS Industrial - Spare Parts.

Based on email: Material Procurement Cost 15th Jan - 15th March '26

Total Items: 16 spare part categories
First delivery: 15th-25th Jan 2026
"""
import asyncio
import sys
import os
from datetime import datetime, date, timedelta
from decimal import Decimal
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select, func
from app.database import async_session_factory
from app.models.vendor import Vendor, VendorStatus
from app.models.warehouse import Warehouse
from app.models.purchase import PurchaseOrder, PurchaseOrderItem, POStatus
from app.models.approval import (
    ApprovalRequest, ApprovalHistory, ApprovalEntityType,
    ApprovalLevel, ApprovalStatus, get_approval_level, get_approval_level_name
)
from app.models.user import User


# Spare Parts Order Items with pricing (estimated based on market rates)
SPARE_PARTS_ORDER = [
    {
        "name": "Sediment Filter (PP Yarn Wound)",
        "sku": "SP-SDF-YRN-001",
        "hsn": "84219900",
        "qty_jan": 1500,
        "qty_feb": 1500,
        "unit_price": Decimal("45.00"),
        "description": "PP Yarn Wound Sediment Filter for RO systems"
    },
    {
        "name": "Sediment Filter (Spun Filter)",
        "sku": "SP-SDF-SPN-001",
        "hsn": "84219900",
        "qty_jan": 1500,
        "qty_feb": 1500,
        "unit_price": Decimal("35.00"),
        "description": "Spun Filter Sediment for RO systems"
    },
    {
        "name": "Pre Carbon Block (Premium)",
        "sku": "SP-PCB-PRM-001",
        "hsn": "84219900",
        "qty_jan": 1500,
        "qty_feb": 1500,
        "unit_price": Decimal("120.00"),
        "description": "Premium grade Pre Carbon Block filter"
    },
    {
        "name": "Pre Carbon Block (Regular)",
        "sku": "SP-PCB-REG-001",
        "hsn": "84219900",
        "qty_jan": 1500,
        "qty_feb": 1500,
        "unit_price": Decimal("85.00"),
        "description": "Regular grade Pre Carbon Block filter"
    },
    {
        "name": "Alkaline Mineral Block (Premium)",
        "sku": "SP-ALK-PRM-001",
        "hsn": "84219900",
        "qty_jan": 1000,
        "qty_feb": 1000,
        "unit_price": Decimal("180.00"),
        "description": "Premium Alkaline Mineral Block cartridge"
    },
    {
        "name": "Post Carbon with Copper (Regular)",
        "sku": "SP-POC-COP-001",
        "hsn": "84219900",
        "qty_jan": 1000,
        "qty_feb": 1000,
        "unit_price": Decimal("150.00"),
        "description": "Post Carbon Block with Copper infusion"
    },
    {
        "name": "Membrane (Premium)",
        "sku": "SP-MBR-PRM-001",
        "hsn": "84219900",
        "qty_jan": 1000,
        "qty_feb": 1000,
        "unit_price": Decimal("850.00"),
        "description": "Premium RO Membrane 75/80 GPD"
    },
    {
        "name": "Membrane (Regular)",
        "sku": "SP-MBR-REG-001",
        "hsn": "84219900",
        "qty_jan": 1000,
        "qty_feb": 1000,
        "unit_price": Decimal("550.00"),
        "description": "Regular RO Membrane 75/80 GPD"
    },
    {
        "name": "Pre-Filter Multi Layer Candle",
        "sku": "SP-PFC-MLT-001",
        "hsn": "84219900",
        "qty_jan": 1000,
        "qty_feb": 1000,
        "unit_price": Decimal("95.00"),
        "description": "Multi-layer ceramic candle for pre-filtration"
    },
    # Iron Remover - qty 0, skipping
    {
        "name": "HMR Cartridge",
        "sku": "SP-HMR-001",
        "hsn": "84219900",
        "qty_jan": 200,
        "qty_feb": 500,
        "unit_price": Decimal("220.00"),
        "description": "Heavy Metal Remover Cartridge"
    },
    {
        "name": "Prefilter with Multilayer Candle",
        "sku": "SP-PFA-MLC-001",
        "hsn": "84219900",
        "qty_jan": 500,
        "qty_feb": 1000,
        "unit_price": Decimal("280.00"),
        "description": "Pre-filter assembly with Multi-layer Candle"
    },
    {
        "name": "Prefilter with Spun Filter",
        "sku": "SP-PFA-SPN-001",
        "hsn": "84219900",
        "qty_jan": 500,
        "qty_feb": 1000,
        "unit_price": Decimal("180.00"),
        "description": "Pre-filter assembly with Spun Filter"
    },
    {
        "name": "Heavy Metal Remover",
        "sku": "SP-HMR-BLK-001",
        "hsn": "84219900",
        "qty_jan": 200,
        "qty_feb": 200,
        "unit_price": Decimal("350.00"),
        "description": "Heavy Metal Remover Block cartridge"
    },
    {
        "name": "Plastic PRV",
        "sku": "SP-PRV-PLS-001",
        "hsn": "84819090",
        "qty_jan": 200,
        "qty_feb": 500,
        "unit_price": Decimal("65.00"),
        "description": "Plastic Pressure Reducing Valve"
    },
    {
        "name": "Brass Diverter Valve",
        "sku": "SP-DVV-BRS-001",
        "hsn": "84819090",
        "qty_jan": 500,
        "qty_feb": 500,
        "unit_price": Decimal("125.00"),
        "description": "Brass Diverter Valve for tap connection"
    },
]


async def create_stos_spare_parts_po():
    """Create PO for STOS spare parts with approval workflow."""

    async with async_session_factory() as db:
        try:
            print("=" * 70)
            print("PURCHASE ORDER CREATION - STOS SPARE PARTS")
            print("=" * 70)

            # ==================== Step 1: Find/Create STOS Vendor ====================
            print("\n[1/6] Finding/Creating STOS Vendor...")
            result = await db.execute(
                select(Vendor).where(Vendor.name.ilike("%stos%"))
            )
            vendor = result.scalar_one_or_none()

            if not vendor:
                print("  Creating STOS vendor...")
                # Generate vendor code
                result = await db.execute(select(func.count(Vendor.id)))
                vendor_count = result.scalar() or 0

                vendor = Vendor(
                    id=uuid.uuid4(),
                    vendor_code=f"VND-{vendor_count + 1:05d}",
                    name="STOS Industrial Corporation",
                    legal_name="STOS Industrial Corporation Pvt. Ltd.",
                    vendor_type="MANUFACTURER",
                    status=VendorStatus.ACTIVE,
                    grade="A",
                    gst_registered=True,
                    gstin="07AABCS1234R1ZP",
                    gst_state_code="07",
                    pan="AABCS1234R",
                    contact_person="Saurabh Sharma",
                    designation="Sales Manager",
                    email="saurabh@stosindustrial.com",
                    phone="011-45678901",
                    mobile="9876543210",
                    address_line1="Plot No. 45, Industrial Area",
                    address_line2="Sector 63",
                    city="Noida",
                    state="Uttar Pradesh",
                    state_code="09",
                    pincode="201301",
                    country="India",
                    payment_terms="30 Days Net",
                    credit_days=30,
                    advance_percentage=Decimal("25"),
                    product_categories=["Spare Parts", "Filters", "Valves", "Membranes"],
                    primary_products="RO Spare Parts - Filters, Membranes, Valves",
                    default_lead_days=15,
                    is_verified=True,
                    verified_at=datetime.utcnow(),
                )
                db.add(vendor)
                await db.flush()
                print(f"  ✓ Created: {vendor.name} ({vendor.vendor_code})")
            else:
                print(f"  ✓ Found: {vendor.name} ({vendor.vendor_code})")

            # ==================== Step 2: Find Warehouse ====================
            print("\n[2/6] Finding Delivery Warehouse...")
            result = await db.execute(select(Warehouse).limit(1))
            warehouse = result.scalar_one_or_none()

            if not warehouse:
                print("ERROR: No warehouse found!")
                return None

            print(f"  ✓ Warehouse: {warehouse.name} ({warehouse.code})")

            # ==================== Step 3: Find Admin User ====================
            print("\n[3/6] Finding Admin User...")
            result = await db.execute(
                select(User).where(User.email == "admin@consumer.com")
            )
            admin_user = result.scalar_one_or_none()

            if not admin_user:
                print("ERROR: Admin user not found!")
                return None

            print(f"  ✓ User: {admin_user.email}")

            # ==================== Step 4: Check Existing PO ====================
            print("\n[4/6] Checking for existing PO...")
            result = await db.execute(
                select(PurchaseOrder).where(
                    PurchaseOrder.quotation_reference == "STOS-SPARE-JAN-MAR-2026"
                )
            )
            existing_po = result.scalar_one_or_none()

            if existing_po:
                print(f"  ⚠ PO already exists: {existing_po.po_number}")
                print(f"    Status: {existing_po.status.value}")
                print(f"    Total: ₹{existing_po.grand_total:,.2f}")
                return existing_po

            # ==================== Step 5: Generate PO Number ====================
            print("\n[5/6] Generating PO Number...")
            result = await db.execute(
                select(func.count(PurchaseOrder.id))
            )
            po_count = result.scalar() or 0
            po_number = f"PO-2026-{po_count + 1:05d}"
            print(f"  ✓ PO Number: {po_number}")

            # ==================== Step 6: Create PO ====================
            print("\n[6/6] Creating Purchase Order...")

            # Calculate totals - using TOTAL quantities (Jan + Feb)
            order_items = []
            for item in SPARE_PARTS_ORDER:
                total_qty = item["qty_jan"] + item["qty_feb"]
                if total_qty > 0:
                    order_items.append({
                        **item,
                        "qty": total_qty
                    })

            subtotal = sum(item["qty"] * item["unit_price"] for item in order_items)

            # Inter-state supply (UP to Delhi) = IGST
            # But if same state = CGST + SGST
            # Assuming intra-state for now (both in UP/Delhi NCR)
            gst_rate = Decimal("18.00")
            cgst_rate = Decimal("9.00")
            sgst_rate = Decimal("9.00")

            cgst_amount = subtotal * cgst_rate / 100
            sgst_amount = subtotal * sgst_rate / 100
            total_tax = cgst_amount + sgst_amount
            grand_total = subtotal + total_tax

            advance_percent = Decimal("25.00")
            advance_amount = subtotal * advance_percent / 100

            # Determine approval level
            approval_level = get_approval_level(grand_total)
            approval_level_name = get_approval_level_name(approval_level)

            print(f"\n  Order Summary (Jan + Feb 2026 Combined):")
            print(f"  {'-' * 70}")
            print(f"  {'Item':<40} {'Qty':>8} {'Unit':>10} {'Total':>12}")
            print(f"  {'-' * 70}")

            total_items = 0
            for item in order_items:
                line_total = item["qty"] * item["unit_price"]
                total_items += item["qty"]
                print(f"  {item['name']:<40} {item['qty']:>8} ₹{item['unit_price']:>8,.2f} ₹{line_total:>10,.2f}")

            print(f"  {'-' * 70}")
            print(f"  {'Total Items:':<40} {total_items:>8}")
            print(f"  {'Subtotal:':<60} ₹{subtotal:>10,.2f}")
            print(f"  {'CGST @ 9%:':<60} ₹{cgst_amount:>10,.2f}")
            print(f"  {'SGST @ 9%:':<60} ₹{sgst_amount:>10,.2f}")
            print(f"  {'GRAND TOTAL:':<60} ₹{grand_total:>10,.2f}")
            print(f"  {'-' * 70}")
            print(f"  {'25% Advance:':<60} ₹{advance_amount:>10,.2f}")
            print(f"  {'Balance Due:':<60} ₹{grand_total - advance_amount:>10,.2f}")
            print(f"  {'-' * 70}")
            print(f"\n  Approval Required: {approval_level.value}")
            print(f"  Approval Level: {approval_level_name}")

            # Create PO
            po_id = uuid.uuid4()
            po = PurchaseOrder(
                id=po_id,
                po_number=po_number,
                po_date=date.today(),

                # Vendor
                vendor_id=vendor.id,
                vendor_name=vendor.name,
                vendor_gstin=vendor.gstin,
                vendor_address={
                    "address_line1": vendor.address_line1,
                    "address_line2": vendor.address_line2,
                    "city": vendor.city,
                    "state": vendor.state,
                    "pincode": vendor.pincode,
                },

                # Delivery
                delivery_warehouse_id=warehouse.id,
                expected_delivery_date=date(2026, 1, 25),  # First batch by 25th Jan

                # Status
                status=POStatus.DRAFT,

                # Amounts
                subtotal=subtotal,
                discount_amount=Decimal("0"),
                taxable_amount=subtotal,

                # GST
                cgst_amount=cgst_amount,
                sgst_amount=sgst_amount,
                igst_amount=Decimal("0"),
                cess_amount=Decimal("0"),
                total_tax=total_tax,

                # Charges
                freight_charges=Decimal("0"),
                packing_charges=Decimal("0"),
                other_charges=Decimal("0"),

                # Grand Total
                grand_total=grand_total,

                # Payment
                payment_terms="25% Advance, Balance on Delivery",
                credit_days=30,
                advance_required=advance_amount,
                advance_paid=Decimal("0"),  # Not paid yet

                # Reference
                quotation_reference="STOS-SPARE-JAN-MAR-2026",
                quotation_date=date.today(),

                # Terms
                terms_and_conditions="""1. DELIVERY SCHEDULE:
   - 1st Batch: 15th-25th Jan 2026 (as per Jan quantities)
   - 2nd Batch: 15th Feb 2026 (as per Feb quantities)
2. QUALITY: All items must meet ILMS.AI quality standards
3. PACKAGING: Individual packaging with barcode labels
4. WARRANTY: 6 months from date of delivery
5. RENDER IMAGES: Vendor to provide render photos of all spares for marketing material
6. This is a LONG TERM STRATEGIC PARTNERSHIP - exclusive supplier arrangement""",

                special_instructions="""URGENT: Project already delayed by 1 month.
Need samples for sales partners ASAP.
Please provide render photos for PDPs and marketing material.""",

                # Approval
                approval_level=approval_level.value,

                # Created by
                created_by=admin_user.id,

                internal_notes=f"""Spare Parts PO for Jan-Mar 2026

DELIVERY SCHEDULE:
- Batch 1 (Jan): {sum(item['qty_jan'] for item in SPARE_PARTS_ORDER)} items by 25th Jan 2026
- Batch 2 (Feb): {sum(item['qty_feb'] for item in SPARE_PARTS_ORDER)} items by 15th Feb 2026

STRATEGIC NOTES:
- Long term partnership with STOS
- Exclusive supplier for these spare parts
- Need render images for marketing

PAYMENT:
- 25% Advance: ₹{advance_amount:,.2f}
- Balance on each delivery""",

                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            db.add(po)
            await db.flush()

            # Create PO Items
            for idx, item in enumerate(order_items, 1):
                line_total = item["qty"] * item["unit_price"]
                line_cgst = line_total * cgst_rate / 100
                line_sgst = line_total * sgst_rate / 100
                line_tax = line_cgst + line_sgst
                line_grand = line_total + line_tax

                po_item = PurchaseOrderItem(
                    id=uuid.uuid4(),
                    purchase_order_id=po.id,
                    product_name=item["name"],
                    sku=item["sku"],
                    hsn_code=item["hsn"],
                    line_number=idx,
                    quantity_ordered=item["qty"],
                    quantity_received=0,
                    quantity_accepted=0,
                    quantity_rejected=0,
                    quantity_pending=item["qty"],
                    uom="PCS",
                    unit_price=item["unit_price"],
                    discount_percentage=Decimal("0"),
                    discount_amount=Decimal("0"),
                    taxable_amount=line_total,
                    gst_rate=gst_rate,
                    cgst_rate=cgst_rate,
                    sgst_rate=sgst_rate,
                    igst_rate=Decimal("0"),
                    cgst_amount=line_cgst,
                    sgst_amount=line_sgst,
                    igst_amount=Decimal("0"),
                    cess_amount=Decimal("0"),
                    total_amount=line_grand,
                    notes=item.get("description", ""),
                )
                db.add(po_item)

            print(f"\n  ✓ PO Created in DRAFT status")

            # ==================== Create Approval Request ====================
            print("\n" + "=" * 70)
            print("APPROVAL WORKFLOW")
            print("=" * 70)

            # Generate approval request number
            result = await db.execute(
                select(func.count(ApprovalRequest.id))
            )
            apr_count = result.scalar() or 0
            apr_number = f"APR-{datetime.now().strftime('%Y%m%d')}-{apr_count + 1:04d}"

            # Create approval request
            approval_request = ApprovalRequest(
                id=uuid.uuid4(),
                request_number=apr_number,

                # Entity
                entity_type=ApprovalEntityType.PURCHASE_ORDER,
                entity_id=po_id,
                entity_number=po_number,

                # Amount and Level
                amount=grand_total,
                approval_level=approval_level,

                # Status
                status=ApprovalStatus.PENDING,
                priority=7,  # High priority - project delayed

                # Title/Description
                title=f"URGENT PO Approval: {vendor.name} - Spare Parts - ₹{grand_total:,.2f}",
                description=f"""Purchase Order for STOS Industrial - Spare Parts Division

URGENCY: Project delayed by 1 month - need immediate approval

Items: {len(order_items)} spare part categories
Total Quantity: {total_items:,} pieces

Subtotal: ₹{subtotal:,.2f}
GST (18%): ₹{total_tax:,.2f}
Grand Total: ₹{grand_total:,.2f}

Delivery Schedule:
- Batch 1: 15th-25th Jan 2026
- Batch 2: 15th Feb 2026

Strategic Partnership: Long-term exclusive supplier arrangement""",

                # Requester
                requested_by=admin_user.id,
                requested_at=datetime.utcnow(),

                # SLA - URGENT: 1 business day
                due_date=datetime.utcnow() + timedelta(days=1),

                # Extra info
                extra_info={
                    "vendor_name": vendor.name,
                    "vendor_code": vendor.vendor_code,
                    "po_number": po_number,
                    "reference": "STOS-SPARE-JAN-MAR-2026",
                    "items_count": len(order_items),
                    "total_quantity": total_items,
                    "urgency": "HIGH - Project delayed",
                },

                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            db.add(approval_request)
            await db.flush()

            # Link approval request to PO
            po.approval_request_id = approval_request.id
            po.submitted_for_approval_at = datetime.utcnow()

            # Create approval history entry
            history = ApprovalHistory(
                id=uuid.uuid4(),
                approval_request_id=approval_request.id,
                action="SUBMITTED",
                from_status=None,
                to_status=ApprovalStatus.PENDING.value,
                performed_by=admin_user.id,
                comments=f"URGENT: PO submitted for {approval_level_name}. Project delayed - need immediate approval.",
                created_at=datetime.utcnow(),
            )
            db.add(history)

            # Update PO status
            po.status = POStatus.PENDING_APPROVAL
            po.updated_at = datetime.utcnow()

            await db.commit()

            print(f"\n  Approval Request: {apr_number}")
            print(f"  Status: {ApprovalStatus.PENDING.value}")
            print(f"  Level: {approval_level.value}")
            print(f"  Required: {approval_level_name}")
            print(f"  Priority: HIGH (Project Delayed)")
            print(f"  Due Date: {(datetime.utcnow() + timedelta(days=1)).strftime('%Y-%m-%d')}")

            print("\n" + "=" * 70)
            print("PO CREATED SUCCESSFULLY")
            print("=" * 70)
            print(f"""
  PO Number: {po_number}
  Vendor: {vendor.name}
  Status: {POStatus.PENDING_APPROVAL.value}

  Items: {len(order_items)} categories
  Total Quantity: {total_items:,} pieces

  Subtotal: ₹{subtotal:,.2f}
  CGST (9%): ₹{cgst_amount:,.2f}
  SGST (9%): ₹{sgst_amount:,.2f}
  Grand Total: ₹{grand_total:,.2f}

  25% Advance Required: ₹{advance_amount:,.2f}
  Balance Due: ₹{grand_total - advance_amount:,.2f}

  Approval Request: {apr_number}
  Approval Level: {approval_level.value} - {approval_level_name}

  Delivery Schedule:
  - Batch 1: 15th-25th Jan 2026
  - Batch 2: 15th Feb 2026

  Next Steps:
  1. Finance Head reviews and approves the PO
  2. Pay 25% advance to vendor
  3. Send PO to STOS (SENT_TO_VENDOR)
  4. Receive Batch 1 by 25th Jan 2026
  5. Receive Batch 2 by 15th Feb 2026
            """)
            print("=" * 70)

            return po

        except Exception as e:
            await db.rollback()
            print(f"\nERROR: {e}")
            import traceback
            traceback.print_exc()
            return None


if __name__ == "__main__":
    asyncio.run(create_stos_spare_parts_po())
