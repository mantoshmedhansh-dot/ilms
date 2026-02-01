"""
Approval Workflow Service.

Handles creation and management of approval requests across modules.
"""
from datetime import datetime, date, timedelta, timezone
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.approval import (
    ApprovalRequest,
    ApprovalHistory,
    ApprovalEntityType,
    ApprovalStatus,
    get_approval_level,
)


class ApprovalService:
    """Service for managing approval workflow."""

    @staticmethod
    async def generate_request_number(db: AsyncSession) -> str:
        """Generate unique approval request number."""
        today = date.today()
        prefix = f"APR-{today.strftime('%Y%m%d')}"

        # Get max number for today
        result = await db.execute(
            select(func.max(ApprovalRequest.request_number))
            .where(ApprovalRequest.request_number.like(f"{prefix}%"))
        )
        max_number = result.scalar()

        if max_number:
            # Extract sequence and increment
            seq = int(max_number.split("-")[-1]) + 1
        else:
            seq = 1

        return f"{prefix}-{seq:04d}"

    @staticmethod
    async def create_approval_request(
        db: AsyncSession,
        entity_type: ApprovalEntityType,
        entity_id: UUID,
        entity_number: str,
        amount: Decimal,
        title: str,
        requested_by: UUID,
        description: Optional[str] = None,
        extra_info: Optional[dict] = None,
        priority: int = 5,
    ) -> ApprovalRequest:
        """
        Create a new approval request.

        Args:
            db: Database session
            entity_type: Type of entity (PURCHASE_ORDER, VENDOR_ONBOARDING, etc.)
            entity_id: UUID of the entity
            entity_number: Reference number (PO number, Vendor code, etc.)
            amount: Amount for approval level calculation
            title: Title for the approval request
            requested_by: User ID who submitted the request
            description: Optional description
            extra_info: Optional additional data as JSON
            priority: Priority (1=Urgent, 5=Normal, 10=Low)

        Returns:
            Created ApprovalRequest instance
        """
        request_number = await ApprovalService.generate_request_number(db)
        approval_level = get_approval_level(amount)

        # Calculate due date based on priority (1=1 day, 5=3 days, 10=7 days)
        days_map = {1: 1, 2: 1, 3: 2, 4: 2, 5: 3, 6: 4, 7: 5, 8: 5, 9: 6, 10: 7}
        due_days = days_map.get(priority, 3)
        due_date = datetime.now(timezone.utc) + timedelta(days=due_days)

        approval = ApprovalRequest(
            request_number=request_number,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_number=entity_number,
            amount=amount,
            approval_level=approval_level,
            status=ApprovalStatus.PENDING,
            priority=priority,
            title=title,
            description=description,
            requested_by=requested_by,
            requested_at=datetime.now(timezone.utc),
            due_date=due_date,
            extra_info=extra_info,
        )
        db.add(approval)
        await db.flush()  # Flush to get the ID

        # Create history entry
        history = ApprovalHistory(
            approval_request_id=approval.id,
            action="SUBMITTED",
            from_status=None,
            to_status=ApprovalStatus.PENDING.value,
            performed_by=requested_by,
            comments="Submitted for approval",
        )
        db.add(history)

        return approval

    @staticmethod
    async def get_pending_approval_for_entity(
        db: AsyncSession,
        entity_type: ApprovalEntityType,
        entity_id: UUID,
    ) -> Optional[ApprovalRequest]:
        """Check if there's a pending approval for an entity."""
        result = await db.execute(
            select(ApprovalRequest).where(
                ApprovalRequest.entity_type == entity_type,
                ApprovalRequest.entity_id == entity_id,
                ApprovalRequest.status == ApprovalStatus.PENDING,
            )
        )
        return result.scalar_one_or_none()
