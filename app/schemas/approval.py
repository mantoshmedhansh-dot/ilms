"""
Approval Workflow Schemas.

Pydantic schemas for multi-level approval workflow.
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.base import BaseResponseSchema

from app.models.approval import ApprovalEntityType, ApprovalLevel, ApprovalStatus


# ============== Base Schemas ==============

class ApprovalRequestBase(BaseModel):
    """Base schema for approval request."""
    entity_type: ApprovalEntityType
    entity_id: UUID
    entity_number: str
    amount: Decimal
    priority: int = Field(default=5, ge=1, le=10)
    title: str = Field(..., max_length=200)
    description: Optional[str] = None


class ApprovalHistoryBase(BaseModel):
    """Base schema for approval history."""
    action: str
    from_status: Optional[str] = None
    to_status: str
    comments: Optional[str] = None


# ============== Create Schemas ==============

class ApprovalRequestCreate(BaseModel):
    """Schema for creating an approval request (used internally)."""
    entity_type: ApprovalEntityType
    entity_id: UUID
    entity_number: str
    amount: Decimal
    title: str
    description: Optional[str] = None
    priority: int = 5
    extra_info: Optional[dict] = None


# ============== Action Schemas ==============

class SubmitForApprovalRequest(BaseModel):
    """Schema for submitting an entity for approval."""
    comments: Optional[str] = Field(None, description="Optional comments when submitting")


class ApproveRequest(BaseModel):
    """Schema for approving a request."""
    comments: Optional[str] = Field(None, description="Approval comments")
    notes: Optional[str] = Field(None, description="Approval notes (alias for comments)")


class RejectRequest(BaseModel):
    """Schema for rejecting a request."""
    reason: str = Field(..., min_length=10, description="Rejection reason is required")


class EscalateRequest(BaseModel):
    """Schema for escalating a request."""
    escalate_to: Optional[UUID] = Field(None, description="Specific user to escalate to")
    reason: str = Field(..., min_length=10, description="Escalation reason")


class ReassignRequest(BaseModel):
    """Schema for reassigning a request to another approver."""
    assign_to: UUID = Field(..., description="User ID to assign the request to")
    comments: Optional[str] = None


# ============== Response Schemas ==============

class UserBrief(BaseResponseSchema):
    """Brief user info for responses."""
    id: UUID
    name: Optional[str] = None
    email: Optional[str] = None
class ApprovalHistoryResponse(BaseResponseSchema):
    """Response schema for approval history item."""
    id: UUID
    action: str
    from_status: Optional[str]
    to_status: str
    comments: Optional[str]
    performed_by: UUID
    actor_name: Optional[str] = None
    created_at: datetime

class ApprovalRequestResponse(BaseResponseSchema):
    """Response schema for approval request."""
    id: UUID
    request_number: str
    entity_type: str  # VARCHAR in DB
    entity_id: UUID
    entity_number: str
    amount: Decimal
    approval_level: str  # VARCHAR in DB
    approval_level_name: Optional[str] = None
    status: str
    priority: int
    title: str
    description: Optional[str]

    # Requester info
    requested_by: UUID
    requester_name: Optional[str] = None
    requested_at: datetime

    # Current approver
    current_approver_id: Optional[UUID]
    current_approver_name: Optional[str] = None

    # Approval info
    approved_by: Optional[UUID]
    approver_name: Optional[str] = None
    approved_at: Optional[datetime]
    approval_comments: Optional[str]

    # Rejection info
    rejected_by: Optional[UUID]
    rejecter_name: Optional[str] = None
    rejected_at: Optional[datetime]
    rejection_reason: Optional[str]

    # SLA
    due_date: Optional[datetime]
    is_overdue: bool = False

    # Escalation
    escalated_at: Optional[datetime]
    escalated_to: Optional[UUID]
    escalation_reason: Optional[str]

    # Extra Info
    extra_info: Optional[dict] = None

    # Timestamps
    created_at: datetime
    updated_at: datetime

    # History (optional, can be fetched separately)
    history: Optional[List[ApprovalHistoryResponse]] = None

class ApprovalRequestBrief(BaseResponseSchema):
    """Brief approval request for list views."""
    id: UUID
    request_number: str
    entity_type: ApprovalEntityType
    entity_number: str
    amount: Decimal
    approval_level: ApprovalLevel
    status: str
    title: str
    requester_name: Optional[str] = None
    requested_at: datetime
    is_overdue: bool = False
class ApprovalListResponse(BaseModel):
    """Response schema for listing approval requests."""
    items: List[ApprovalRequestBrief]
    total: int
    page: int
    size: int
    pages: int


# ============== Dashboard Schemas ==============

class ApprovalLevelCount(BaseModel):
    """Count of approvals per level."""
    level: ApprovalLevel
    level_name: str
    pending_count: int
    total_amount: Decimal


class ApprovalDashboardResponse(BaseModel):
    """Finance approvals dashboard response."""
    # Summary counts
    total_pending: int
    total_approved_today: int
    total_rejected_today: int
    total_overdue: int

    # By level
    by_level: List[ApprovalLevelCount]

    # By entity type
    by_entity_type: dict  # {"PURCHASE_ORDER": 5, "STOCK_TRANSFER": 2}

    # Recent activity
    recent_approvals: List[ApprovalRequestBrief]
    urgent_pending: List[ApprovalRequestBrief]


# ============== PO-specific Schemas ==============

class POSubmitForApprovalRequest(BaseModel):
    """Schema for submitting a PO for approval."""
    comments: Optional[str] = Field(None, description="Optional comments when submitting")


class POApprovalResponse(BaseModel):
    """Response after PO approval action."""
    po_id: UUID
    po_number: str
    po_status: str
    approval_request_id: UUID
    approval_status: ApprovalStatus
    approval_level: ApprovalLevel
    message: str


# ============== Bulk Action Schemas ==============

class BulkApproveRequest(BaseModel):
    """Schema for bulk approval."""
    request_ids: List[UUID]
    comments: Optional[str] = None


class BulkRejectRequest(BaseModel):
    """Schema for bulk rejection."""
    request_ids: List[UUID]
    reason: str


class BulkActionResponse(BaseModel):
    """Response for bulk actions."""
    successful: List[UUID]
    failed: List[dict]  # [{"id": UUID, "error": str}]
    total_processed: int
    total_successful: int
    total_failed: int
