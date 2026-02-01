"""Warehouse schemas for API requests/responses."""
from pydantic import BaseModel, Field, ConfigDict

from app.schemas.base import BaseResponseSchema
from typing import Optional, List
from datetime import datetime
import uuid

from app.models.warehouse import WarehouseType


class WarehouseBase(BaseModel):
    """Base warehouse schema."""
    name: str = Field(..., max_length=200)
    warehouse_type: WarehouseType = WarehouseType.REGIONAL
    address_line1: str = Field(..., max_length=255)
    address_line2: Optional[str] = Field(None, max_length=255)
    city: str = Field(..., max_length=100)
    state: str = Field(..., max_length=100)
    pincode: str = Field(..., max_length=10)
    country: str = Field(default="India", max_length=100)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    contact_name: Optional[str] = Field(None, max_length=100)
    contact_phone: Optional[str] = Field(None, max_length=20)
    contact_email: Optional[str] = Field(None, max_length=100)
    region_id: Optional[uuid.UUID] = None
    manager_id: Optional[uuid.UUID] = None
    total_capacity: float = 0
    can_fulfill_orders: bool = True
    can_receive_transfers: bool = True
    notes: Optional[str] = None


class WarehouseCreate(WarehouseBase):
    """Warehouse creation schema."""
    code: Optional[str] = Field(None, max_length=20)  # Auto-generate if not provided


class WarehouseUpdate(BaseModel):
    """Warehouse update schema."""
    name: Optional[str] = Field(None, max_length=200)
    warehouse_type: Optional[WarehouseType] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    region_id: Optional[uuid.UUID] = None
    manager_id: Optional[uuid.UUID] = None
    total_capacity: Optional[float] = None
    current_utilization: Optional[float] = None
    can_fulfill_orders: Optional[bool] = None
    can_receive_transfers: Optional[bool] = None
    is_active: Optional[bool] = None
    is_default: Optional[bool] = None
    notes: Optional[str] = None


class WarehouseResponse(BaseResponseSchema):
    """Warehouse response schema."""
    id: uuid.UUID
    code: str
    name: str
    warehouse_type: str  # VARCHAR in DB
    address_line1: str
    address_line2: Optional[str] = None
    city: str
    state: str
    pincode: str
    country: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    region_id: Optional[uuid.UUID] = None
    manager_id: Optional[uuid.UUID] = None
    total_capacity: float
    current_utilization: float
    is_active: bool
    is_default: bool
    can_fulfill_orders: bool
    can_receive_transfers: bool
    full_address: str
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

class WarehouseBrief(BaseResponseSchema):
    """Brief warehouse info for dropdowns."""
    id: uuid.UUID
    code: str
    name: str
    warehouse_type: str  # VARCHAR in DB
    city: str
    state: str
    is_active: bool
class WarehouseListResponse(BaseModel):
    """Paginated warehouse list."""
    items: List[WarehouseResponse]
    total: int
    page: int
    size: int
    pages: int
