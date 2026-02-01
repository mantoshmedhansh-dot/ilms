"""Pydantic schemas for WMS (Warehouse Management System) models."""
from pydantic import BaseModel, Field

from app.schemas.base import BaseResponseSchema
from typing import Optional, List
from datetime import datetime
import uuid

from app.models.wms import ZoneType, BinType


# ==================== WAREHOUSE ZONE SCHEMAS ====================

class ZoneCreate(BaseModel):
    """Warehouse zone creation schema."""
    warehouse_id: uuid.UUID
    zone_code: str = Field(..., min_length=1, max_length=20)
    zone_name: str = Field(..., min_length=2, max_length=200)
    description: Optional[str] = None
    zone_type: ZoneType = ZoneType.STORAGE
    floor_number: Optional[int] = None
    area_sqft: Optional[float] = None
    max_capacity: Optional[int] = None
    is_active: bool = True
    is_pickable: bool = True
    is_receivable: bool = True
    sort_order: int = 0


class ZoneUpdate(BaseModel):
    """Warehouse zone update schema."""
    zone_name: Optional[str] = None
    description: Optional[str] = None
    zone_type: Optional[ZoneType] = None
    floor_number: Optional[int] = None
    area_sqft: Optional[float] = None
    max_capacity: Optional[int] = None
    is_active: Optional[bool] = None
    is_pickable: Optional[bool] = None
    is_receivable: Optional[bool] = None
    sort_order: Optional[int] = None


class ZoneResponse(BaseResponseSchema):
    """Warehouse zone response schema."""
    id: uuid.UUID
    warehouse_id: uuid.UUID
    zone_code: str
    zone_name: str
    description: Optional[str] = None
    zone_type: str  # VARCHAR in DB
    floor_number: Optional[int] = None
    area_sqft: Optional[float] = None
    max_capacity: Optional[int] = None
    current_capacity: int
    utilization_percent: float
    is_active: bool
    is_pickable: bool
    is_receivable: bool
    sort_order: int
    created_at: datetime
    updated_at: datetime

class ZoneBrief(BaseResponseSchema):
    """Brief zone info."""
    id: uuid.UUID
    zone_code: str
    zone_name: str
    zone_type: str  # VARCHAR in DB
class ZoneListResponse(BaseModel):
    """Paginated zone list."""
    items: List[ZoneResponse]
    total: int
    page: int
    size: int
    pages: int


# ==================== WAREHOUSE BIN SCHEMAS ====================

class BinCreate(BaseModel):
    """Warehouse bin creation schema."""
    warehouse_id: uuid.UUID
    zone_id: Optional[uuid.UUID] = None
    bin_code: str = Field(..., min_length=1, max_length=50)
    bin_name: Optional[str] = None
    barcode: Optional[str] = None
    aisle: Optional[str] = None
    rack: Optional[str] = None
    shelf: Optional[str] = None
    position: Optional[str] = None
    bin_type: BinType = BinType.SHELF
    length: Optional[float] = None
    width: Optional[float] = None
    height: Optional[float] = None
    max_capacity: Optional[int] = None
    max_weight_kg: Optional[float] = None
    is_active: bool = True
    is_reserved: bool = False
    is_pickable: bool = True
    is_receivable: bool = True
    reserved_product_id: Optional[uuid.UUID] = None
    pick_sequence: int = 0


class BinBulkCreate(BaseModel):
    """Bulk bin creation."""
    warehouse_id: uuid.UUID
    zone_id: Optional[uuid.UUID] = None
    bin_type: BinType = BinType.SHELF
    prefix: str = Field(..., min_length=1, max_length=10)
    aisle_start: str = "A"
    aisle_end: str = "A"
    rack_start: int = 1
    rack_end: int = 5
    shelf_start: int = 1
    shelf_end: int = 4
    max_capacity: Optional[int] = None


class BinUpdate(BaseModel):
    """Warehouse bin update schema."""
    zone_id: Optional[uuid.UUID] = None
    bin_name: Optional[str] = None
    barcode: Optional[str] = None
    bin_type: Optional[BinType] = None
    length: Optional[float] = None
    width: Optional[float] = None
    height: Optional[float] = None
    max_capacity: Optional[int] = None
    max_weight_kg: Optional[float] = None
    is_active: Optional[bool] = None
    is_reserved: Optional[bool] = None
    is_pickable: Optional[bool] = None
    is_receivable: Optional[bool] = None
    reserved_product_id: Optional[uuid.UUID] = None
    pick_sequence: Optional[int] = None


class BinResponse(BaseResponseSchema):
    """Warehouse bin response schema."""
    id: uuid.UUID
    warehouse_id: uuid.UUID
    zone_id: Optional[uuid.UUID] = None
    zone: Optional[ZoneBrief] = None
    bin_code: str
    bin_name: Optional[str] = None
    barcode: Optional[str] = None
    aisle: Optional[str] = None
    rack: Optional[str] = None
    shelf: Optional[str] = None
    position: Optional[str] = None
    bin_type: str  # VARCHAR in DB
    length: Optional[float] = None
    width: Optional[float] = None
    height: Optional[float] = None
    max_capacity: Optional[int] = None
    max_weight_kg: Optional[float] = None
    current_items: int
    current_weight_kg: float
    is_empty: bool
    is_full: bool
    available_capacity: Optional[int] = None
    is_active: bool
    is_reserved: bool
    is_pickable: bool
    is_receivable: bool
    pick_sequence: int
    last_activity_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

class BinBrief(BaseResponseSchema):
    """Brief bin info."""
    id: uuid.UUID
    bin_code: str
    bin_type: str  # VARCHAR in DB
    current_items: int
class BinListResponse(BaseModel):
    """Paginated bin list."""
    items: List[BinResponse]
    total: int
    page: int
    size: int
    pages: int


class BinStatsResponse(BaseModel):
    """Bin statistics response."""
    total_bins: int
    available_bins: int
    occupied_bins: int
    reserved_bins: int


class BinEnquiryRequest(BaseModel):
    """Bin enquiry request."""
    warehouse_id: uuid.UUID
    zone_id: Optional[uuid.UUID] = None
    bin_code: Optional[str] = None
    barcode: Optional[str] = None
    product_id: Optional[uuid.UUID] = None
    only_available: bool = False
    only_pickable: bool = False


class BinEnquiryResponse(BaseModel):
    """Bin enquiry response with contents."""
    bin: BinResponse
    contents: List["BinContentItem"]


class BinContentItem(BaseModel):
    """Single item in bin."""
    stock_item_id: uuid.UUID
    serial_number: Optional[str] = None
    product_id: uuid.UUID
    product_name: str
    sku: str
    variant_name: Optional[str] = None
    status: str
    received_date: Optional[datetime] = None


# ==================== PUTAWAY RULE SCHEMAS ====================

class PutAwayRuleCreate(BaseModel):
    """PutAway rule creation schema."""
    warehouse_id: uuid.UUID
    rule_name: str = Field(..., min_length=2, max_length=200)
    description: Optional[str] = None
    category_id: Optional[uuid.UUID] = None
    product_id: Optional[uuid.UUID] = None
    brand_id: Optional[uuid.UUID] = None
    target_zone_id: uuid.UUID
    target_bin_pattern: Optional[str] = None
    priority: int = 100
    is_active: bool = True


class PutAwayRuleUpdate(BaseModel):
    """PutAway rule update schema."""
    rule_name: Optional[str] = None
    description: Optional[str] = None
    category_id: Optional[uuid.UUID] = None
    product_id: Optional[uuid.UUID] = None
    brand_id: Optional[uuid.UUID] = None
    target_zone_id: Optional[uuid.UUID] = None
    target_bin_pattern: Optional[str] = None
    priority: Optional[int] = None
    is_active: Optional[bool] = None


class PutAwayRuleResponse(BaseResponseSchema):
    """PutAway rule response schema."""
    id: uuid.UUID
    warehouse_id: uuid.UUID
    rule_name: str
    description: Optional[str] = None
    category_id: Optional[uuid.UUID] = None
    product_id: Optional[uuid.UUID] = None
    brand_id: Optional[uuid.UUID] = None
    target_zone_id: uuid.UUID
    target_zone: Optional[ZoneBrief] = None
    target_bin_pattern: Optional[str] = None
    priority: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

class PutAwayRuleListResponse(BaseModel):
    """Paginated putaway rule list."""
    items: List[PutAwayRuleResponse]
    total: int
    page: int
    size: int
    pages: int


class PutAwayRuleStatsResponse(BaseModel):
    """PutAway rule statistics response."""
    total_rules: int
    active_rules: int
    items_processed_today: int
    unmatched_items: int


# ==================== PUTAWAY OPERATIONS ====================

class PutAwaySuggestRequest(BaseModel):
    """PutAway suggestion request."""
    warehouse_id: uuid.UUID
    product_id: uuid.UUID
    quantity: int = 1


class PutAwaySuggestResponse(BaseModel):
    """PutAway suggestion response."""
    suggested_bins: List["SuggestedBin"]
    matched_rule: Optional[PutAwayRuleResponse] = None


class SuggestedBin(BaseModel):
    """Suggested bin for putaway."""
    bin: BinBrief
    zone: Optional[ZoneBrief] = None
    available_capacity: Optional[int] = None
    pick_sequence: int


class PutAwayExecuteRequest(BaseModel):
    """Execute putaway request."""
    stock_item_id: uuid.UUID
    bin_id: uuid.UUID
    notes: Optional[str] = None


class PutAwayExecuteResponse(BaseModel):
    """Putaway execution response."""
    success: bool
    stock_item_id: uuid.UUID
    bin_id: uuid.UUID
    bin_code: str
    message: str


# ==================== INVENTORY MOVE ====================

class InventoryMoveRequest(BaseModel):
    """Move inventory between bins."""
    stock_item_id: uuid.UUID
    from_bin_id: uuid.UUID
    to_bin_id: uuid.UUID
    reason: Optional[str] = None


class InventoryMoveResponse(BaseModel):
    """Inventory move response."""
    success: bool
    stock_item_id: uuid.UUID
    from_bin_code: str
    to_bin_code: str
    message: str


# Update forward references
BinEnquiryResponse.model_rebuild()
PutAwaySuggestResponse.model_rebuild()
