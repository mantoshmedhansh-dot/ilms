"""
Create Purchase Order for FastTrack Filtration with Approval Workflow.

Based on:
- PI NO./FF/25-26/005 dated 19.11.2025
- Email confirmation with 25% advance payment

PO Amount: ₹11,39,467 (including 18% GST)
Approval Level Required: LEVEL_3 (Finance Head) - Amount above ₹5,00,000
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
from app.models.vendor import Vendor
from app.models.warehouse import Warehouse
from app.models.purchase import PurchaseOrder, PurchaseOrderItem, POStatus
from app.models.product import Product
from app.models.approval import (
    ApprovalRequest, ApprovalHistory, ApprovalEntityType,
    ApprovalLevel, ApprovalStatus, get_approval_level, get_approval_level_name
)
from app.models.user import User


async def create_fastrack_po():
    """Create PO for FastTrack Filtration with approval workflow."""

    async with async_session_factory() as db:
        try:
            print("=" * 70)
            print("PURCHASE ORDER CREATION - FASTRACK FILTRATION")
            print("=" * 70)

            # ==================== Step 1: Find Vendor ====================
            print("\n[1/6] Finding Vendor...")
            result = await db.execute(
                select(Vendor).where(Vendor.name.ilike("%fastrack%"))
            )
            vendor = result.scalar_one_or_none()

            if not vendor:
                print("ERROR: FastTrack vendor not found!")
                print("Please run: python scripts/seed_fastrack_vendor.py")
                return None

            print(f"  ✓ Vendor: {vendor.name} ({vendor.vendor_code})")

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
                    PurchaseOrder.quotation_reference == "PI NO./FF/25-26/005"
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

            # Order items from email
            order_items = [
                {
                    "name": "ILMS.AI BLITZ",
                    "sku": "AP-BLT-001",
                    "hsn": "842121",
                    "qty": 150,
                    "unit_price": Decimal("2304.00"),
                    "description": "RO+UV Water Purifier - Blitz Model"
                },
                {
                    "name": "ILMS.AI NEURA",
                    "sku": "AP-NEU-001",
                    "hsn": "842121",
                    "qty": 150,
                    "unit_price": Decimal("2509.00"),
                    "description": "RO+UV Water Purifier - Neura Model (Alkaline)"
                },
                {
                    "name": "ILMS.AI ELITZ",
                    "sku": "AP-ELT-001",
                    "hsn": "842121",
                    "qty": 20,
                    "unit_price": Decimal("12185.00"),
                    "description": "Hot/Cold/Ambient Water Purifier - Elitz Model"
                },
            ]

            # Calculate totals
            subtotal = sum(item["qty"] * item["unit_price"] for item in order_items)
            gst_rate = Decimal("18.00")
            cgst_rate = Decimal("9.00")
            sgst_rate = Decimal("9.00")

            # Delhi vendor to Delhi warehouse = CGST + SGST (intra-state)
            cgst_amount = subtotal * cgst_rate / 100
            sgst_amount = subtotal * sgst_rate / 100
            total_tax = cgst_amount + sgst_amount
            grand_total = subtotal + total_tax

            advance_percent = Decimal("25.00")
            advance_amount = subtotal * advance_percent / 100

            # Determine approval level
            approval_level = get_approval_level(grand_total)
            approval_level_name = get_approval_level_name(approval_level)

            print(f"\n  Order Summary:")
            print(f"  {'-' * 60}")
            print(f"  {'Item':<30} {'Qty':>6} {'Unit Price':>12} {'Total':>12}")
            print(f"  {'-' * 60}")
            for item in order_items:
                line_total = item["qty"] * item["unit_price"]
                print(f"  {item['name']:<30} {item['qty']:>6} ₹{item['unit_price']:>10,.2f} ₹{line_total:>10,.2f}")
            print(f"  {'-' * 60}")
            print(f"  {'Subtotal':<50} ₹{subtotal:>10,.2f}")
            print(f"  {'CGST @ 9%':<50} ₹{cgst_amount:>10,.2f}")
            print(f"  {'SGST @ 9%':<50} ₹{sgst_amount:>10,.2f}")
            print(f"  {'GRAND TOTAL':<50} ₹{grand_total:>10,.2f}")
            print(f"  {'-' * 60}")
            print(f"  {'25% Advance Paid':<50} ₹{advance_amount:>10,.2f}")
            print(f"  {'Balance Due':<50} ₹{grand_total - advance_amount:>10,.2f}")
            print(f"  {'-' * 60}")
            print(f"\n  Approval Required: {approval_level.value}")
            print(f"  Approval Level: {approval_level_name}")

            # Create PO
            po_id = uuid.uuid4()
            po = PurchaseOrder(
                id=po_id,
                po_number=po_number,
                po_date=date(2025, 11, 19),

                # Vendor
                vendor_id=vendor.id,
                vendor_name=vendor.name,
                vendor_gstin=vendor.gstin,
                vendor_address={
                    "address_line1": vendor.address_line1,
                    "city": vendor.city,
                    "state": vendor.state,
                    "pincode": vendor.pincode,
                },

                # Delivery
                delivery_warehouse_id=warehouse.id,
                expected_delivery_date=date(2025, 12, 19),  # 30 days from PI

                # Status - Start as DRAFT, then submit for approval
                status=POStatus.DRAFT,

                # Amounts
                subtotal=subtotal,
                discount_amount=Decimal("0"),
                taxable_amount=subtotal,

                # GST (Intra-state: CGST + SGST)
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

                # Payment tracking
                payment_terms="25% Advance, 25% at Dispatch, 50% PDC from Dispatch",
                credit_days=30,
                advance_required=advance_amount,
                advance_paid=advance_amount,  # Already paid

                # Reference
                quotation_reference="PI NO./FF/25-26/005",
                quotation_date=date(2025, 11, 19),

                # Terms
                terms_and_conditions="""1. WARRANTY: 18 months on electronic parts, 1 year general warranty
2. DELIVERY: Within 30 days from receipt of advance payment
3. Buyer to provide: UV LED for all models
4. Buyer to provide: RO Membrane & Housing for BLITZ/NEURA
5. Buyer to provide: Alkaline 4", RO Membrane & Housing for NEURA""",

                special_instructions="Packing material design to be provided by buyer",

                # Approval Level
                approval_level=approval_level.value,

                # Created by
                created_by=admin_user.id,

                internal_notes=f"""Purchase Order based on PI NO./FF/25-26/005 dated 19.11.2025

ORDER CONFIRMATION:
- 25% Advance transferred: ₹{advance_amount:,.2f}
- Models ordered: BLITZ (150), NEURA (150), ELITZ (20)
- PREMIO model not included in this order

PAYMENT SCHEDULE:
- 25% Advance: ₹{advance_amount:,.2f} (PAID)
- 25% at Dispatch: ₹{advance_amount:,.2f}
- 50% PDC from Dispatch: ₹{advance_amount * 2:,.2f}""",

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
                priority=5,  # Normal priority

                # Title/Description
                title=f"PO Approval: {vendor.name} - ₹{grand_total:,.2f}",
                description=f"""Purchase Order for FastTrack Filtration Pvt. Ltd.

Items:
- ILMS.AI BLITZ x 150 @ ₹2,304 = ₹3,45,600
- ILMS.AI NEURA x 150 @ ₹2,509 = ₹3,76,350
- ILMS.AI ELITZ x 20 @ ₹12,185 = ₹2,43,700

Subtotal: ₹{subtotal:,.2f}
CGST (9%): ₹{cgst_amount:,.2f}
SGST (9%): ₹{sgst_amount:,.2f}
Grand Total: ₹{grand_total:,.2f}

25% Advance already paid: ₹{advance_amount:,.2f}

Reference: PI NO./FF/25-26/005 dated 19.11.2025""",

                # Requester
                requested_by=admin_user.id,
                requested_at=datetime.utcnow(),

                # SLA - 2 business days for approval
                due_date=datetime.utcnow() + timedelta(days=2),

                # Extra info
                extra_info={
                    "vendor_name": vendor.name,
                    "vendor_code": vendor.vendor_code,
                    "po_number": po_number,
                    "reference": "PI NO./FF/25-26/005",
                    "items_count": len(order_items),
                    "advance_paid": float(advance_amount),
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
                comments=f"PO submitted for {approval_level_name}",
                created_at=datetime.utcnow(),
            )
            db.add(history)

            # Update PO status to PENDING_APPROVAL
            po.status = POStatus.PENDING_APPROVAL
            po.updated_at = datetime.utcnow()

            await db.commit()

            print(f"\n  Approval Request: {apr_number}")
            print(f"  Status: {ApprovalStatus.PENDING.value}")
            print(f"  Level: {approval_level.value}")
            print(f"  Required: {approval_level_name}")
            print(f"  Due Date: {(datetime.utcnow() + timedelta(days=2)).strftime('%Y-%m-%d')}")

            print("\n" + "=" * 70)
            print("APPROVAL THRESHOLDS")
            print("=" * 70)
            print("""
  LEVEL_1: Up to ₹50,000      → Manager Approval
  LEVEL_2: ₹50,001 - ₹5,00,000 → Senior Manager Approval
  LEVEL_3: Above ₹5,00,000     → Finance Head Approval ← THIS PO
            """)

            print("=" * 70)
            print("PO CREATED SUCCESSFULLY")
            print("=" * 70)
            print(f"""
  PO Number: {po_number}
  Vendor: {vendor.name}
  Status: {POStatus.PENDING_APPROVAL.value}

  Subtotal: ₹{subtotal:,.2f}
  CGST (9%): ₹{cgst_amount:,.2f}
  SGST (9%): ₹{sgst_amount:,.2f}
  Grand Total: ₹{grand_total:,.2f}

  Advance Paid: ₹{advance_amount:,.2f}
  Balance Due: ₹{grand_total - advance_amount:,.2f}

  Approval Request: {apr_number}
  Approval Level: {approval_level.value} - {approval_level_name}

  Next Steps:
  1. Finance Head reviews and approves the PO
  2. PO status changes to APPROVED
  3. PO is sent to vendor (SENT_TO_VENDOR)
  4. Vendor acknowledges (ACKNOWLEDGED)
  5. Goods received and GRN created
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
    asyncio.run(create_fastrack_po())
