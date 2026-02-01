"""Pydantic schemas for Picklist models."""
from pydantic import BaseModel, Field

from app.schemas.base import BaseResponseSchema
from typing import Optional, List
from datetime import datetime
import uuid

from app.models.picklist import PicklistStatus, PicklistType


# ==================== PICKLIST ITEM SCHEMAS ====================

class PicklistItemResponse(BaseResponseSchema):
    """Picklist item response schema."""
    id: uuid.UUID
    picklist_id: uuid.UUID
    order_id: uuid.UUID
    order_item_id: uuid.UUID
    product_id: uuid.UUID
    variant_id: Optional[uuid.UUID] = None
    sku: str
    product_name: str
    variant_name: Optional[str] = None
    bin_id: Optional[uuid.UUID] = None
    bin_location: Optional[str] = None
    quantity_required: int
    quantity_picked: int
    quantity_short: int
    pending_quantity: int
    is_picked: bool
    is_short: bool
    is_complete: bool
    picked_serials: Optional[str] = None
    pick_sequence: int
    picked_by: Optional[uuid.UUID] = None
    picked_at: Optional[datetime] = None
    notes: Optional[str] = None
    short_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime

class PicklistItemBrief(BaseResponseSchema):
    """Brief picklist item info."""
    id: uuid.UUID
    sku: str
    product_name: str
    bin_location: Optional[str] = None
    quantity_required: int
    quantity_picked: int
    is_picked: bool
# ==================== PICKLIST SCHEMAS ====================

class PicklistGenerateRequest(BaseModel):
    """Request to generate picklist from orders."""
    warehouse_id: uuid.UUID
    order_ids: List[uuid.UUID] = Field(..., min_length=1)
    picklist_type: PicklistType = PicklistType.BATCH
    priority: int = Field(5, ge=1, le=10)
    notes: Optional[str] = None


class PicklistCreate(BaseModel):
    """Manual picklist creation schema."""
    warehouse_id: uuid.UUID
    picklist_type: PicklistType = PicklistType.SINGLE_ORDER
    priority: int = Field(5, ge=1, le=10)
    notes: Optional[str] = None


class PicklistUpdate(BaseModel):
    """Picklist update schema."""
    status: Optional[PicklistStatus] = None
    priority: Optional[int] = Field(None, ge=1, le=10)
    notes: Optional[str] = None


class PicklistAssignRequest(BaseModel):
    """Assign picker to picklist."""
    assigned_to: uuid.UUID


class PicklistResponse(BaseResponseSchema):
    """Picklist response schema."""
    id: uuid.UUID
    picklist_number: str
    warehouse_id: uuid.UUID
    status: str
    picklist_type: str  # VARCHAR in DB
    priority: int
    total_orders: int
    total_items: int
    total_quantity: int
    picked_quantity: int
    pending_quantity: int
    pick_progress: float
    is_complete: bool
    assigned_to: Optional[uuid.UUID] = None
    assigned_at: Optional[datetime] = None
    created_by: Optional[uuid.UUID] = None
    notes: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    cancellation_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime

class PicklistDetailResponse(PicklistResponse):
    """Detailed picklist response with items."""
    items: List[PicklistItemResponse] = []


class PicklistListResponse(BaseModel):
    """Paginated picklist list."""
    items: List[PicklistResponse]
    total: int
    page: int
    size: int
    pages: int


class PicklistBrief(BaseResponseSchema):
    """Brief picklist info."""
    id: uuid.UUID
    picklist_number: str
    status: str
    total_items: int
    pick_progress: float
# ==================== PICK OPERATIONS ====================

class PickScanRequest(BaseModel):
    """Scan item during picking."""
    picklist_id: uuid.UUID
    sku: Optional[str] = None
    serial_number: Optional[str] = None
    barcode: Optional[str] = None
    bin_code: Optional[str] = None
    quantity: int = 1


class PickScanResponse(BaseModel):
    """Pick scan response."""
    success: bool
    message: str
    item: Optional[PicklistItemBrief] = None
    remaining_quantity: int


class PickConfirmRequest(BaseModel):
    """Confirm picked item."""
    picklist_item_id: uuid.UUID
    quantity_picked: int
    serial_numbers: Optional[List[str]] = None
    notes: Optional[str] = None


class PickShortRequest(BaseModel):
    """Mark item as short (not found)."""
    picklist_item_id: uuid.UUID
    quantity_short: int
    reason: str


class PickCompleteRequest(BaseModel):
    """Complete picking for picklist."""
    picklist_id: uuid.UUID
    notes: Optional[str] = None


class PickCompleteResponse(BaseModel):
    """Pick completion response."""
    success: bool
    picklist_id: uuid.UUID
    picklist_number: str
    status: str
    total_picked: int
    total_short: int
    message: str


# ==================== WAVE PICKING ====================

class WavePicklistGenerateRequest(BaseModel):
    """Generate wave picklist (by product/zone)."""
    warehouse_id: uuid.UUID
    zone_id: Optional[uuid.UUID] = None
    product_ids: Optional[List[uuid.UUID]] = None
    max_orders: int = 50
    priority: int = Field(5, ge=1, le=10)


class WavePicklistResponse(BaseModel):
    """Wave picklist with grouped items."""
    picklist: PicklistResponse
    items_by_zone: dict  # zone_code -> List[PicklistItemResponse]
    items_by_product: dict  # sku -> List[PicklistItemResponse]
