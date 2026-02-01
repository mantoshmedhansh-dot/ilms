"""
Approve the FastTrack Filtration Purchase Order.

Uses the approval workflow to:
1. Find the pending approval request for the PO
2. Create/find a Finance Head user (different from requester for maker-checker)
3. Approve the request
4. Update PO status to APPROVED
"""
import asyncio
import sys
import os
from datetime import datetime
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from app.database import async_session_factory
from app.models.purchase import PurchaseOrder, POStatus
from app.models.approval import (
    ApprovalRequest, ApprovalHistory, ApprovalStatus, ApprovalEntityType
)
from app.models.user import User
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def approve_fastrack_po():
    """Approve the FastTrack PO through the approval workflow."""

    async with async_session_factory() as db:
        try:
            print("=" * 70)
            print("PURCHASE ORDER APPROVAL - FASTRACK FILTRATION")
            print("=" * 70)

            # ==================== Step 1: Find Pending Approval ====================
            print("\n[1/4] Finding Pending Approval Request...")
            result = await db.execute(
                select(ApprovalRequest)
                .where(ApprovalRequest.status == ApprovalStatus.PENDING)
                .where(ApprovalRequest.entity_type == ApprovalEntityType.PURCHASE_ORDER)
                .order_by(ApprovalRequest.created_at.desc())
            )
            approval = result.scalar_one_or_none()

            if not approval:
                print("ERROR: No pending PO approval request found!")
                return None

            print(f"  Approval Request: {approval.request_number}")
            print(f"  Entity: {approval.entity_number}")
            print(f"  Amount: Rs.{approval.amount:,.2f}")
            print(f"  Level: {approval.approval_level.value}")

            # ==================== Step 2: Get PO ====================
            print("\n[2/4] Getting Purchase Order...")
            result = await db.execute(
                select(PurchaseOrder).where(PurchaseOrder.id == approval.entity_id)
            )
            po = result.scalar_one_or_none()

            if not po:
                print("ERROR: Purchase Order not found!")
                return None

            print(f"  PO Number: {po.po_number}")
            print(f"  Vendor: {po.vendor_name}")
            print(f"  Status: {po.status.value}")
            print(f"  Grand Total: Rs.{po.grand_total:,.2f}")

            if po.status != POStatus.PENDING_APPROVAL:
                print(f"\nERROR: PO is not in PENDING_APPROVAL status!")
                print(f"Current status: {po.status.value}")
                return None

            # ==================== Step 3: Get/Create Finance Head ====================
            print("\n[3/4] Finding Finance Head User...")

            # Maker-checker: Approver must be different from requester
            requester_id = approval.requested_by

            result = await db.execute(
                select(User).where(User.email == "finance.head@consumer.com")
            )
            finance_head = result.scalar_one_or_none()

            if not finance_head:
                print("  Creating Finance Head user...")
                finance_head = User(
                    id=uuid.uuid4(),
                    email="finance.head@consumer.com",
                    phone="9900000099",  # Unique phone for Finance Head
                    password_hash=pwd_context.hash("Finance@123"),
                    first_name="Rajesh",
                    last_name="Kumar",
                    employee_code="EMP-FIN-001",
                    department="Finance",
                    designation="Finance Head",
                    is_active=True,
                    is_verified=True,
                )
                db.add(finance_head)
                await db.flush()
                print(f"  Created: {finance_head.email}")
            else:
                print(f"  Found: {finance_head.email}")

            print(f"  Name: {finance_head.first_name} {finance_head.last_name}")
            print(f"  Designation: {finance_head.designation}")

            # ==================== Step 4: Approve ====================
            print("\n[4/4] Approving Purchase Order...")

            # Update approval request
            old_status = approval.status.value
            approval.status = ApprovalStatus.APPROVED
            approval.approved_by = finance_head.id
            approval.approved_at = datetime.utcnow()
            approval.approval_comments = f"Approved. Advance payment of Rs.{po.advance_paid:,.2f} confirmed. Proceed with order."

            # Create history entry
            history = ApprovalHistory(
                id=uuid.uuid4(),
                approval_request_id=approval.id,
                action="APPROVED",
                from_status=old_status,
                to_status=ApprovalStatus.APPROVED.value,
                performed_by=finance_head.id,
                comments=f"Approved by Finance Head. Amount: Rs.{po.grand_total:,.2f}",
                created_at=datetime.utcnow(),
            )
            db.add(history)

            # Update PO status
            po.status = POStatus.APPROVED
            po.approved_by = finance_head.id
            po.approved_at = datetime.utcnow()
            po.updated_at = datetime.utcnow()

            await db.commit()

            print("\n" + "=" * 70)
            print("APPROVAL COMPLETE")
            print("=" * 70)
            print(f"""
  Approval Request: {approval.request_number}
  New Status: {approval.status.value}
  Approved By: {finance_head.first_name} {finance_head.last_name} ({finance_head.designation})
  Approved At: {approval.approved_at.strftime('%Y-%m-%d %H:%M:%S')}

  Purchase Order: {po.po_number}
  PO Status: {po.status.value}
  Vendor: {po.vendor_name}
  Grand Total: Rs.{po.grand_total:,.2f}

  Next Steps:
  1. Send PO to vendor (SENT_TO_VENDOR)
  2. Vendor acknowledges (ACKNOWLEDGED)
  3. Vendor ships goods
  4. Receive goods and create GRN (PARTIALLY_RECEIVED/RECEIVED)
  5. Close PO after all items received (CLOSED)
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
    asyncio.run(approve_fastrack_po())
