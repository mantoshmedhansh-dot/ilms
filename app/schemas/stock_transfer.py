"""Stock Transfer schemas for API requests/responses."""
from pydantic import BaseModel, Field

from app.schemas.base import BaseResponseSchema
from typing import Optional, List
from datetime import datetime
import uuid

from app.models.stock_transfer import TransferStatus, TransferType


# ==================== TRANSFER ITEM SCHEMAS ====================

class TransferItemCreate(BaseModel):
    """Transfer item creation schema."""
    product_id: uuid.UUID
    variant_id: Optional[uuid.UUID] = None
    requested_quantity: int = Field(..., ge=1)
    notes: Optional[str] = None


class TransferItemResponse(BaseResponseSchema):
    """Transfer item response schema."""
    id: uuid.UUID
    transfer_id: uuid.UUID
    product_id: uuid.UUID
    variant_id: Optional[uuid.UUID] = None
    requested_quantity: int
    approved_quantity: Optional[int] = None
    dispatched_quantity: Optional[int] = None
    received_quantity: int
    damaged_quantity: int
    unit_cost: float
    total_cost: float
    notes: Optional[str] = None
    created_at: datetime

class TransferItemDetail(TransferItemResponse):
    """Detailed transfer item with product info."""
    product_name: Optional[str] = None
    product_sku: Optional[str] = None
    variant_name: Optional[str] = None


# ==================== TRANSFER SCHEMAS ====================

class StockTransferCreate(BaseModel):
    """Stock transfer creation schema."""
    transfer_type: TransferType = TransferType.STOCK_TRANSFER
    from_warehouse_id: uuid.UUID
    to_warehouse_id: uuid.UUID
    expected_date: Optional[datetime] = None
    items: List[TransferItemCreate] = Field(..., min_length=1)
    notes: Optional[str] = None


class StockTransferUpdate(BaseModel):
    """Stock transfer update schema."""
    expected_date: Optional[datetime] = None
    vehicle_number: Optional[str] = None
    driver_name: Optional[str] = None
    driver_phone: Optional[str] = None
    challan_number: Optional[str] = None
    eway_bill_number: Optional[str] = None
    notes: Optional[str] = None
    internal_notes: Optional[str] = None


class TransferApproval(BaseModel):
    """Transfer approval request."""
    items: Optional[List[dict]] = None  # [{"item_id": uuid, "approved_quantity": int}]
    notes: Optional[str] = None


class TransferRejection(BaseModel):
    """Transfer rejection request."""
    reason: str = Field(..., min_length=10)


class TransferDispatch(BaseModel):
    """Transfer dispatch request."""
    vehicle_number: Optional[str] = None
    driver_name: Optional[str] = None
    driver_phone: Optional[str] = None
    challan_number: Optional[str] = None
    eway_bill_number: Optional[str] = None
    serial_items: Optional[List[uuid.UUID]] = None  # Stock item IDs to dispatch
    notes: Optional[str] = None


class TransferReceiveItem(BaseModel):
    """Single item receipt in transfer."""
    item_id: uuid.UUID
    received_quantity: int = Field(..., ge=0)
    damaged_quantity: int = Field(0, ge=0)
    damage_notes: Optional[str] = None
    serial_items: Optional[List[dict]] = None  # [{"stock_item_id": uuid, "is_damaged": bool}]


class TransferReceive(BaseModel):
    """Transfer receive request."""
    items: List[TransferReceiveItem]
    notes: Optional[str] = None


class StockTransferResponse(BaseResponseSchema):
    """Stock transfer response schema."""
    id: uuid.UUID
    transfer_number: str
    transfer_type: str  # VARCHAR in DB
    status: str
    from_warehouse_id: uuid.UUID
    to_warehouse_id: uuid.UUID
    request_date: datetime
    expected_date: Optional[datetime] = None
    dispatch_date: Optional[datetime] = None
    received_date: Optional[datetime] = None
    requested_by: Optional[uuid.UUID] = None
    approved_by: Optional[uuid.UUID] = None
    dispatched_by: Optional[uuid.UUID] = None
    received_by: Optional[uuid.UUID] = None
    approved_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    total_items: int
    total_quantity: int
    total_value: float
    received_quantity: int
    vehicle_number: Optional[str] = None
    driver_name: Optional[str] = None
    driver_phone: Optional[str] = None
    challan_number: Optional[str] = None
    eway_bill_number: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

class StockTransferDetail(StockTransferResponse):
    """Detailed transfer with items and warehouse info."""
    from_warehouse_name: Optional[str] = None
    from_warehouse_code: Optional[str] = None
    to_warehouse_name: Optional[str] = None
    to_warehouse_code: Optional[str] = None
    items: List[TransferItemDetail] = []


class StockTransferListResponse(BaseModel):
    """Paginated transfer list."""
    items: List[StockTransferResponse]
    total: int
    page: int
    size: int
    pages: int


class StockTransferBrief(BaseResponseSchema):
    """Brief transfer info."""
    id: uuid.UUID
    transfer_number: str
    status: str
    from_warehouse_code: str
    to_warehouse_code: str
    total_quantity: int
    request_date: datetime
