"""Inventory schemas for API requests/responses."""
from pydantic import BaseModel, Field

from app.schemas.base import BaseResponseSchema
from typing import Optional, List
from datetime import datetime, date
from decimal import Decimal
import uuid

from app.models.inventory import StockItemStatus, StockMovementType


# ==================== STOCK VERIFICATION SCHEMAS (Phase 2) ====================

class StockVerificationRequest(BaseModel):
    """Request model for stock verification."""
    product_id: uuid.UUID
    quantity: int = 1
    pincode: Optional[str] = None
    warehouse_id: Optional[uuid.UUID] = None


class StockVerificationResponse(BaseModel):
    """Response model for stock verification."""
    product_id: uuid.UUID
    in_stock: bool
    available_quantity: int
    requested_quantity: int
    warehouse_id: Optional[uuid.UUID] = None
    delivery_estimate: Optional[str] = None
    message: Optional[str] = None


class BulkStockVerificationRequest(BaseModel):
    """Request for bulk stock verification."""
    items: List[StockVerificationRequest]


class BulkStockVerificationResponse(BaseModel):
    """Response for bulk stock verification."""
    all_in_stock: bool
    items: List[StockVerificationResponse]


# ==================== STOCK ITEM SCHEMAS ====================

class StockItemCreate(BaseModel):
    """Stock item creation schema."""
    product_id: uuid.UUID
    variant_id: Optional[uuid.UUID] = None
    warehouse_id: uuid.UUID
    serial_number: Optional[str] = Field(None, max_length=100)
    batch_number: Optional[str] = Field(None, max_length=50)
    barcode: Optional[str] = Field(None, max_length=100)
    purchase_price: float = 0
    landed_cost: float = 0
    manufacturing_date: Optional[date] = None
    expiry_date: Optional[date] = None
    warranty_start_date: Optional[date] = None
    warranty_end_date: Optional[date] = None
    rack_location: Optional[str] = Field(None, max_length=50)
    bin_number: Optional[str] = Field(None, max_length=50)
    quality_grade: Optional[str] = Field(None, max_length=20)
    notes: Optional[str] = None


class StockItemUpdate(BaseModel):
    """Stock item update schema."""
    status: Optional[StockItemStatus] = None
    warehouse_id: Optional[uuid.UUID] = None
    rack_location: Optional[str] = None
    bin_number: Optional[str] = None
    quality_grade: Optional[str] = None
    inspection_status: Optional[str] = None
    inspection_notes: Optional[str] = None
    notes: Optional[str] = None


class StockItemResponse(BaseResponseSchema):
    """Stock item response schema."""
    id: uuid.UUID
    product_id: uuid.UUID
    variant_id: Optional[uuid.UUID] = None
    warehouse_id: uuid.UUID
    serial_number: Optional[str] = None
    batch_number: Optional[str] = None
    barcode: Optional[str] = None
    status: str
    purchase_price: float
    landed_cost: float
    manufacturing_date: Optional[date] = None
    expiry_date: Optional[date] = None
    warranty_start_date: Optional[date] = None
    warranty_end_date: Optional[date] = None
    received_date: Optional[datetime] = None
    order_id: Optional[uuid.UUID] = None
    allocated_at: Optional[datetime] = None
    rack_location: Optional[str] = None
    bin_number: Optional[str] = None
    quality_grade: Optional[str] = None
    inspection_status: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

class StockItemDetailResponse(StockItemResponse):
    """Detailed stock item with product and warehouse info."""
    product_name: Optional[str] = None
    product_sku: Optional[str] = None
    variant_name: Optional[str] = None
    warehouse_name: Optional[str] = None
    warehouse_code: Optional[str] = None


class StockItemListResponse(BaseModel):
    """Paginated stock item list."""
    items: List[StockItemResponse]
    total: int
    page: int
    size: int
    pages: int


# ==================== INVENTORY SUMMARY SCHEMAS ====================

class InventorySummaryResponse(BaseResponseSchema):
    """Inventory summary response."""
    id: uuid.UUID
    warehouse_id: uuid.UUID
    product_id: uuid.UUID
    variant_id: Optional[uuid.UUID] = None
    total_quantity: int
    available_quantity: int
    reserved_quantity: int
    allocated_quantity: int
    damaged_quantity: int
    in_transit_quantity: int
    reorder_level: int
    minimum_stock: int
    maximum_stock: int
    average_cost: float
    total_value: float
    is_low_stock: bool
    is_out_of_stock: bool
    last_stock_in_date: Optional[datetime] = None
    last_stock_out_date: Optional[datetime] = None

class InventorySummaryDetail(InventorySummaryResponse):
    """Detailed inventory summary with product/warehouse info."""
    product_name: Optional[str] = None
    product_sku: Optional[str] = None
    variant_name: Optional[str] = None
    warehouse_name: Optional[str] = None
    warehouse_code: Optional[str] = None


class InventorySummaryListResponse(BaseModel):
    """Paginated inventory summary list."""
    items: List[InventorySummaryDetail]
    total: int
    page: int
    size: int
    pages: int


class InventoryThresholdUpdate(BaseModel):
    """Update inventory thresholds."""
    reorder_level: Optional[int] = Field(None, ge=0)
    minimum_stock: Optional[int] = Field(None, ge=0)
    maximum_stock: Optional[int] = Field(None, ge=0)


# ==================== STOCK MOVEMENT SCHEMAS ====================

class StockMovementCreate(BaseModel):
    """Stock movement creation (usually auto-generated)."""
    movement_type: StockMovementType
    warehouse_id: uuid.UUID
    product_id: uuid.UUID
    variant_id: Optional[uuid.UUID] = None
    stock_item_id: Optional[uuid.UUID] = None
    quantity: int
    reference_type: Optional[str] = None
    reference_id: Optional[uuid.UUID] = None
    reference_number: Optional[str] = None
    unit_cost: float = 0
    notes: Optional[str] = None


class StockMovementResponse(BaseResponseSchema):
    """Stock movement response."""
    id: uuid.UUID
    movement_number: str
    movement_type: str  # VARCHAR in DB
    movement_date: datetime
    warehouse_id: uuid.UUID
    product_id: uuid.UUID
    variant_id: Optional[uuid.UUID] = None
    stock_item_id: Optional[uuid.UUID] = None
    quantity: int
    balance_before: int
    balance_after: int
    reference_type: Optional[str] = None
    reference_id: Optional[uuid.UUID] = None
    reference_number: Optional[str] = None
    unit_cost: float
    total_cost: float
    created_by: Optional[uuid.UUID] = None
    notes: Optional[str] = None
    created_at: datetime

class StockMovementDetail(StockMovementResponse):
    """Detailed stock movement with product/warehouse info."""
    product_name: Optional[str] = None
    product_sku: Optional[str] = None
    warehouse_name: Optional[str] = None
    serial_number: Optional[str] = None


class StockMovementListResponse(BaseModel):
    """Paginated stock movement list."""
    items: List[StockMovementDetail]
    total: int
    page: int
    size: int
    pages: int


# ==================== BULK OPERATIONS ====================

class BulkStockReceiptItem(BaseModel):
    """Item for bulk stock receipt."""
    product_id: uuid.UUID
    variant_id: Optional[uuid.UUID] = None
    quantity: int = Field(..., ge=1)
    serial_numbers: List[str] = []  # Optional list of serial numbers
    batch_number: Optional[str] = None
    purchase_price: float = 0
    manufacturing_date: Optional[date] = None
    expiry_date: Optional[date] = None


class BulkStockReceipt(BaseModel):
    """Bulk stock receipt (GRN)."""
    warehouse_id: uuid.UUID
    grn_number: str = Field(..., max_length=50)
    purchase_order_id: Optional[uuid.UUID] = None
    vendor_id: Optional[uuid.UUID] = None
    items: List[BulkStockReceiptItem] = Field(..., min_length=1)
    notes: Optional[str] = None


class StockAllocation(BaseModel):
    """Stock allocation for order."""
    order_id: uuid.UUID
    items: List[uuid.UUID]  # List of stock_item_ids to allocate


# ==================== DASHBOARD/STATS ====================

class InventoryStats(BaseModel):
    """Inventory dashboard statistics for Stock Items page."""
    # Backend field names with frontend aliases
    total_products: int = Field(alias="total_skus", serialization_alias="total_skus")
    total_stock_items: int = Field(alias="in_stock", serialization_alias="in_stock")
    total_stock_value: float
    low_stock_products: int = Field(alias="low_stock", serialization_alias="low_stock")
    out_of_stock_products: int = Field(alias="out_of_stock", serialization_alias="out_of_stock")
    warehouses_count: int
    pending_transfers: int
    pending_adjustments: int

    model_config = {"populate_by_name": True}


class InventoryDashboardStats(BaseModel):
    """Inventory dashboard statistics for Summary page."""
    total_items: int
    total_warehouses: int
    pending_transfers: int
    low_stock_items: int
    total_value: float = 0


class WarehouseStock(BaseModel):
    """Stock summary per warehouse."""
    warehouse_id: uuid.UUID
    warehouse_name: str
    warehouse_code: str
    total_items: int
    total_value: float
    utilization_percent: float


class BulkStockReceiptResponse(BaseModel):
    """Response for bulk stock receipt (GRN)."""
    message: str
    grn_number: str
    items_count: int
