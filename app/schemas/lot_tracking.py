"""
Lot/Batch Tracking Schemas - Phase 13: Lot Tracking & Expiration Management.

Pydantic schemas for lot tracking and expiration management.
"""
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict

from app.models.lot_tracking import (
    LotStatus, HoldReason, AllocationStrategy,
    RecallType, RecallClass, RecallStatus, ExpirationAction
)


# ============================================================================
# LOT MASTER SCHEMAS
# ============================================================================

class LotMasterBase(BaseModel):
    """Base schema for lot master."""
    lot_number: str = Field(..., max_length=100)
    batch_number: Optional[str] = Field(None, max_length=100)
    lot_code: Optional[str] = Field(None, max_length=50)

    manufacture_date: Optional[date] = None
    expiration_date: Optional[date] = None
    best_before_date: Optional[date] = None
    receive_date: date

    shelf_life_days: Optional[int] = None

    supplier_id: Optional[UUID] = None
    supplier_lot_number: Optional[str] = Field(None, max_length=100)
    country_of_origin: Optional[str] = Field(None, max_length=3)
    po_number: Optional[str] = Field(None, max_length=50)
    grn_number: Optional[str] = Field(None, max_length=50)

    initial_quantity: Decimal
    uom: str = Field(default="EACH", max_length=20)

    unit_cost: Decimal = Field(default=Decimal("0"))

    qc_status: Optional[str] = Field(None, max_length=20)
    certificate_of_analysis: Optional[str] = Field(None, max_length=500)

    attributes: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None


class LotMasterCreate(LotMasterBase):
    """Schema for creating a lot master."""
    product_id: UUID
    variant_id: Optional[UUID] = None
    warehouse_id: UUID
    bin_id: Optional[UUID] = None


class LotMasterUpdate(BaseModel):
    """Schema for updating a lot master."""
    batch_number: Optional[str] = Field(None, max_length=100)
    expiration_date: Optional[date] = None
    best_before_date: Optional[date] = None
    shelf_life_days: Optional[int] = None
    supplier_lot_number: Optional[str] = None
    country_of_origin: Optional[str] = None
    qc_status: Optional[str] = None
    certificate_of_analysis: Optional[str] = None
    attributes: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None


class LotMasterResponse(LotMasterBase):
    """Schema for lot master response."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    product_id: UUID
    variant_id: Optional[UUID]

    current_quantity: Decimal
    reserved_quantity: Decimal
    allocated_quantity: Decimal

    remaining_shelf_life_days: Optional[int]
    shelf_life_percent: Optional[Decimal]

    status: str
    hold_reason: Optional[str]
    hold_notes: Optional[str]
    held_by: Optional[UUID]
    held_at: Optional[datetime]

    qc_date: Optional[date]
    qc_reference: Optional[str]

    total_cost: Decimal

    is_recalled: bool
    recall_id: Optional[UUID]

    created_by: Optional[UUID]
    created_at: datetime
    updated_at: datetime


# ============================================================================
# LOT HOLD SCHEMAS
# ============================================================================

class LotHoldCreate(BaseModel):
    """Schema for creating a lot hold."""
    lot_id: UUID
    hold_reason: HoldReason
    hold_description: Optional[str] = None
    quantity_held: Decimal
    investigation_required: bool = False
    reference_type: Optional[str] = Field(None, max_length=30)
    reference_id: Optional[UUID] = None


class LotHoldRelease(BaseModel):
    """Schema for releasing a lot hold."""
    release_notes: Optional[str] = None
    investigation_result: Optional[str] = Field(None, max_length=30)


class LotHoldResponse(BaseModel):
    """Schema for lot hold response."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    lot_id: UUID
    hold_number: str
    hold_reason: str
    hold_description: Optional[str]
    quantity_held: Decimal

    is_active: bool
    held_at: datetime
    held_by: UUID

    released_at: Optional[datetime]
    released_by: Optional[UUID]
    release_notes: Optional[str]

    investigation_required: bool
    investigation_notes: Optional[str]
    investigation_result: Optional[str]

    reference_type: Optional[str]
    reference_id: Optional[UUID]

    created_at: datetime
    updated_at: datetime


# ============================================================================
# LOT TRANSACTION SCHEMAS
# ============================================================================

class LotTransactionCreate(BaseModel):
    """Schema for creating a lot transaction."""
    lot_id: UUID
    transaction_type: str = Field(..., max_length=30)
    quantity: Decimal
    from_warehouse_id: Optional[UUID] = None
    from_bin_id: Optional[UUID] = None
    to_warehouse_id: Optional[UUID] = None
    to_bin_id: Optional[UUID] = None
    source_type: Optional[str] = Field(None, max_length=30)
    source_id: Optional[UUID] = None
    source_number: Optional[str] = Field(None, max_length=50)
    notes: Optional[str] = None


class LotTransactionResponse(BaseModel):
    """Schema for lot transaction response."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    lot_id: UUID
    transaction_number: str
    transaction_date: datetime
    transaction_type: str

    quantity: Decimal
    quantity_before: Decimal
    quantity_after: Decimal

    from_warehouse_id: Optional[UUID]
    from_bin_id: Optional[UUID]
    to_warehouse_id: Optional[UUID]
    to_bin_id: Optional[UUID]

    source_type: Optional[str]
    source_id: Optional[UUID]
    source_number: Optional[str]

    performed_by: UUID
    notes: Optional[str]

    created_at: datetime


# ============================================================================
# RECALL SCHEMAS
# ============================================================================

class LotRecallBase(BaseModel):
    """Base schema for lot recall."""
    recall_name: str = Field(..., max_length=200)
    description: Optional[str] = None
    recall_type: RecallType
    recall_class: Optional[RecallClass] = None

    lot_numbers: Optional[List[str]] = None
    manufacture_date_from: Optional[date] = None
    manufacture_date_to: Optional[date] = None
    expiration_date_from: Optional[date] = None
    expiration_date_to: Optional[date] = None

    recall_date: date
    effective_date: date
    completion_target_date: Optional[date] = None

    reason: str
    health_hazard: Optional[str] = None
    regulatory_reference: Optional[str] = Field(None, max_length=100)

    contact_name: Optional[str] = Field(None, max_length=100)
    contact_phone: Optional[str] = Field(None, max_length=20)
    contact_email: Optional[str] = Field(None, max_length=100)

    action_required: Optional[str] = None
    customer_notification: Optional[str] = None
    notes: Optional[str] = None


class LotRecallCreate(LotRecallBase):
    """Schema for creating a lot recall."""
    product_id: UUID


class LotRecallUpdate(BaseModel):
    """Schema for updating a lot recall."""
    recall_name: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    recall_class: Optional[RecallClass] = None
    completion_target_date: Optional[date] = None
    health_hazard: Optional[str] = None
    action_required: Optional[str] = None
    customer_notification: Optional[str] = None
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    notes: Optional[str] = None


class LotRecallResponse(LotRecallBase):
    """Schema for lot recall response."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    recall_number: str
    product_id: UUID

    status: str
    actual_completion_date: Optional[date]

    total_lots_affected: int
    total_quantity_affected: Decimal
    quantity_in_warehouse: Decimal
    quantity_in_transit: Decimal
    quantity_shipped: Decimal
    quantity_recovered: Decimal
    quantity_destroyed: Decimal

    initiated_by: UUID
    approved_by: Optional[UUID]
    approved_at: Optional[datetime]
    closed_by: Optional[UUID]
    closed_at: Optional[datetime]

    created_at: datetime
    updated_at: datetime


class RecallApprove(BaseModel):
    """Schema for approving a recall."""
    notes: Optional[str] = None


class RecallProgress(BaseModel):
    """Schema for updating recall progress."""
    quantity_recovered: Optional[Decimal] = None
    quantity_destroyed: Optional[Decimal] = None
    notes: Optional[str] = None


# ============================================================================
# EXPIRATION RULE SCHEMAS
# ============================================================================

class ExpirationRuleBase(BaseModel):
    """Base schema for expiration rule."""
    rule_name: str = Field(..., max_length=100)
    allocation_strategy: AllocationStrategy = AllocationStrategy.FEFO

    min_receiving_shelf_life_days: Optional[int] = None
    min_receiving_shelf_life_percent: Optional[Decimal] = None

    min_shipping_shelf_life_days: Optional[int] = None
    min_shipping_shelf_life_percent: Optional[Decimal] = None

    warning_days_before_expiry: int = Field(default=30, ge=1)
    critical_days_before_expiry: int = Field(default=7, ge=1)

    warning_action: ExpirationAction = ExpirationAction.NOTIFY
    critical_action: ExpirationAction = ExpirationAction.HOLD
    expiration_action: ExpirationAction = ExpirationAction.QUARANTINE

    notify_emails: Optional[List[str]] = None
    notify_roles: Optional[List[str]] = None

    notes: Optional[str] = None


class ExpirationRuleCreate(ExpirationRuleBase):
    """Schema for creating an expiration rule."""
    product_id: Optional[UUID] = None
    category_id: Optional[UUID] = None
    warehouse_id: Optional[UUID] = None


class ExpirationRuleUpdate(BaseModel):
    """Schema for updating an expiration rule."""
    rule_name: Optional[str] = Field(None, max_length=100)
    allocation_strategy: Optional[AllocationStrategy] = None
    min_receiving_shelf_life_days: Optional[int] = None
    min_receiving_shelf_life_percent: Optional[Decimal] = None
    min_shipping_shelf_life_days: Optional[int] = None
    min_shipping_shelf_life_percent: Optional[Decimal] = None
    warning_days_before_expiry: Optional[int] = None
    critical_days_before_expiry: Optional[int] = None
    warning_action: Optional[ExpirationAction] = None
    critical_action: Optional[ExpirationAction] = None
    expiration_action: Optional[ExpirationAction] = None
    notify_emails: Optional[List[str]] = None
    notify_roles: Optional[List[str]] = None
    is_active: Optional[bool] = None
    notes: Optional[str] = None


class ExpirationRuleResponse(ExpirationRuleBase):
    """Schema for expiration rule response."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    product_id: Optional[UUID]
    category_id: Optional[UUID]
    warehouse_id: Optional[UUID]
    is_active: bool

    created_by: Optional[UUID]
    created_at: datetime
    updated_at: datetime


# ============================================================================
# EXPIRATION ALERT SCHEMAS
# ============================================================================

class ExpirationAlertResponse(BaseModel):
    """Schema for expiration alert response."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    lot_id: UUID
    rule_id: Optional[UUID]

    alert_type: str
    alert_date: date
    expiration_date: date
    days_until_expiry: int

    product_id: UUID
    warehouse_id: UUID
    quantity_at_risk: Decimal
    value_at_risk: Decimal

    status: str
    action_taken: Optional[str]
    action_date: Optional[datetime]
    action_by: Optional[UUID]
    action_notes: Optional[str]

    notified_at: Optional[datetime]
    notified_to: Optional[List[str]]

    created_at: datetime
    updated_at: datetime


class AlertAcknowledge(BaseModel):
    """Schema for acknowledging an alert."""
    notes: Optional[str] = None


class AlertResolve(BaseModel):
    """Schema for resolving an alert."""
    action_taken: str = Field(..., max_length=50)
    action_notes: Optional[str] = None


# ============================================================================
# INVENTORY LOT SCHEMAS
# ============================================================================

class InventoryLotResponse(BaseModel):
    """Schema for inventory lot response."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    lot_id: UUID

    warehouse_id: UUID
    zone_id: Optional[UUID]
    bin_id: Optional[UUID]

    quantity: Decimal
    reserved_quantity: Decimal
    allocated_quantity: Decimal
    available_quantity: Decimal

    is_available: bool
    is_on_hold: bool
    lpn: Optional[str]

    received_at: datetime
    last_movement_at: Optional[datetime]

    created_at: datetime
    updated_at: datetime


# ============================================================================
# LOT ALLOCATION SCHEMAS
# ============================================================================

class LotAllocationRequest(BaseModel):
    """Schema for requesting lot allocation."""
    product_id: UUID
    warehouse_id: UUID
    quantity_needed: Decimal
    allocation_strategy: Optional[AllocationStrategy] = None
    min_shelf_life_days: Optional[int] = None
    exclude_lot_ids: Optional[List[UUID]] = None


class LotAllocationResult(BaseModel):
    """Schema for lot allocation result."""
    lot_id: UUID
    lot_number: str
    quantity_allocated: Decimal
    expiration_date: Optional[date]
    bin_id: Optional[UUID]
    bin_code: Optional[str]


class LotAllocationResponse(BaseModel):
    """Schema for lot allocation response."""
    product_id: UUID
    quantity_requested: Decimal
    quantity_allocated: Decimal
    fully_allocated: bool
    allocations: List[LotAllocationResult]


# ============================================================================
# DASHBOARD SCHEMAS
# ============================================================================

class LotTrackingDashboard(BaseModel):
    """Dashboard statistics for lot tracking."""
    # Lot Stats
    total_active_lots: int
    lots_on_hold: int
    lots_in_quarantine: int

    # Expiration Stats
    expiring_in_7_days: int
    expiring_in_30_days: int
    expired_lots: int
    value_expiring_30_days: Decimal

    # Alert Stats
    open_alerts: int
    critical_alerts: int
    unacknowledged_alerts: int

    # Recall Stats
    active_recalls: int
    total_quantity_recalled: Decimal

    # Recent Activity
    recent_lots: List[LotMasterResponse]
    recent_alerts: List[ExpirationAlertResponse]
    recent_holds: List[LotHoldResponse]


class ExpirationSummary(BaseModel):
    """Expiration summary by date range."""
    date_range: str
    lot_count: int
    total_quantity: Decimal
    total_value: Decimal
    by_product: List[Dict[str, Any]]
    by_warehouse: List[Dict[str, Any]]
