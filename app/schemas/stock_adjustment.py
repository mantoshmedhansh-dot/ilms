"""Stock Adjustment schemas for API requests/responses."""
from pydantic import BaseModel, Field

from app.schemas.base import BaseResponseSchema
from typing import Optional, List
from datetime import datetime
import uuid

from app.models.stock_adjustment import AdjustmentType, AdjustmentStatus


# ==================== ADJUSTMENT ITEM SCHEMAS ====================

class AdjustmentItemCreate(BaseModel):
    """Adjustment item creation schema."""
    product_id: uuid.UUID
    variant_id: Optional[uuid.UUID] = None
    stock_item_id: Optional[uuid.UUID] = None  # For serial tracked items
    serial_number: Optional[str] = None
    system_quantity: int = Field(..., ge=0)
    physical_quantity: int = Field(..., ge=0)
    unit_cost: float = 0
    reason: Optional[str] = None


class AdjustmentItemResponse(BaseResponseSchema):
    """Adjustment item response schema."""
    id: uuid.UUID
    adjustment_id: uuid.UUID
    product_id: uuid.UUID
    variant_id: Optional[uuid.UUID] = None
    stock_item_id: Optional[uuid.UUID] = None
    serial_number: Optional[str] = None
    system_quantity: int
    physical_quantity: int
    adjustment_quantity: int
    unit_cost: float
    value_impact: float
    reason: Optional[str] = None
    created_at: datetime

class AdjustmentItemDetail(AdjustmentItemResponse):
    """Detailed adjustment item with product info."""
    product_name: Optional[str] = None
    product_sku: Optional[str] = None
    variant_name: Optional[str] = None


# ==================== ADJUSTMENT SCHEMAS ====================

class StockAdjustmentCreate(BaseModel):
    """Stock adjustment creation schema."""
    adjustment_type: AdjustmentType
    warehouse_id: uuid.UUID
    reason: str = Field(..., min_length=10, max_length=500)
    reference_document: Optional[str] = None
    items: List[AdjustmentItemCreate] = Field(..., min_length=1)
    requires_approval: bool = True
    notes: Optional[str] = None


class StockAdjustmentUpdate(BaseModel):
    """Stock adjustment update schema."""
    reason: Optional[str] = None
    reference_document: Optional[str] = None
    notes: Optional[str] = None


class AdjustmentApproval(BaseModel):
    """Adjustment approval request."""
    notes: Optional[str] = None


class AdjustmentRejection(BaseModel):
    """Adjustment rejection request."""
    reason: str = Field(..., min_length=10)


class StockAdjustmentResponse(BaseResponseSchema):
    """Stock adjustment response schema."""
    id: uuid.UUID
    adjustment_number: str
    adjustment_type: str  # VARCHAR in DB
    status: str
    warehouse_id: uuid.UUID
    adjustment_date: datetime
    approved_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_by: uuid.UUID
    approved_by: Optional[uuid.UUID] = None
    requires_approval: bool
    rejection_reason: Optional[str] = None
    total_items: int
    total_quantity_adjusted: int
    total_value_impact: float
    reason: str
    reference_document: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

class StockAdjustmentDetail(StockAdjustmentResponse):
    """Detailed adjustment with items and warehouse info."""
    warehouse_name: Optional[str] = None
    warehouse_code: Optional[str] = None
    items: List[AdjustmentItemDetail] = []


class StockAdjustmentListResponse(BaseModel):
    """Paginated adjustment list."""
    items: List[StockAdjustmentResponse]
    total: int
    page: int
    size: int
    pages: int


# ==================== INVENTORY AUDIT SCHEMAS ====================

class InventoryAuditCreate(BaseModel):
    """Inventory audit creation schema."""
    audit_name: str = Field(..., max_length=200)
    warehouse_id: uuid.UUID
    category_id: Optional[uuid.UUID] = None
    scheduled_date: Optional[datetime] = None
    assigned_to: Optional[uuid.UUID] = None
    notes: Optional[str] = None


class InventoryAuditUpdate(BaseModel):
    """Inventory audit update schema."""
    audit_name: Optional[str] = None
    scheduled_date: Optional[datetime] = None
    assigned_to: Optional[uuid.UUID] = None
    status: Optional[str] = None
    notes: Optional[str] = None


class InventoryAuditResponse(BaseResponseSchema):
    """Inventory audit response schema."""
    id: uuid.UUID
    audit_number: str
    audit_name: Optional[str] = None
    warehouse_id: uuid.UUID
    category_id: Optional[uuid.UUID] = None
    scheduled_date: Optional[datetime] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    status: str
    assigned_to: Optional[uuid.UUID] = None
    created_by: Optional[uuid.UUID] = None
    total_items_counted: int
    variance_items: int
    total_variance_value: float
    adjustment_id: Optional[uuid.UUID] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

class InventoryAuditDetail(InventoryAuditResponse):
    """Detailed audit with warehouse info."""
    warehouse_name: Optional[str] = None
    warehouse_code: Optional[str] = None
    category_name: Optional[str] = None


class InventoryAuditListResponse(BaseModel):
    """Paginated audit list."""
    items: List[InventoryAuditResponse]
    total: int
    page: int
    size: int
    pages: int
