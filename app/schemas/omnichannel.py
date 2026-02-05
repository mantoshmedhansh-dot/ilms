"""
Pydantic schemas for Omnichannel - Phase 3: BOPIS/BORIS & Ship-from-Store.
"""
import uuid
from datetime import datetime, date, time
from decimal import Decimal
from typing import Optional, List, Dict, Any
from enum import Enum

from pydantic import BaseModel, Field, ConfigDict


# ============================================================================
# ENUMS
# ============================================================================

class StoreType(str, Enum):
    FLAGSHIP = "FLAGSHIP"
    STANDARD = "STANDARD"
    EXPRESS = "EXPRESS"
    OUTLET = "OUTLET"
    FRANCHISE = "FRANCHISE"
    SHOP_IN_SHOP = "SHOP_IN_SHOP"
    POP_UP = "POP_UP"


class StoreStatus(str, Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    TEMPORARILY_CLOSED = "TEMPORARILY_CLOSED"
    COMING_SOON = "COMING_SOON"
    PERMANENTLY_CLOSED = "PERMANENTLY_CLOSED"


class BOPISStatus(str, Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    PICKING = "PICKING"
    READY = "READY"
    NOTIFIED = "NOTIFIED"
    PICKED_UP = "PICKED_UP"
    PARTIALLY_PICKED_UP = "PARTIALLY_PICKED_UP"
    EXPIRED = "EXPIRED"
    CANCELLED = "CANCELLED"


class ShipFromStoreStatus(str, Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    PICKING = "PICKING"
    PACKED = "PACKED"
    SHIPPED = "SHIPPED"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"


class StoreReturnStatus(str, Enum):
    INITIATED = "INITIATED"
    SCHEDULED = "SCHEDULED"
    RECEIVED = "RECEIVED"
    INSPECTING = "INSPECTING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    REFUNDED = "REFUNDED"
    COMPLETED = "COMPLETED"


class PickupLocationType(str, Enum):
    IN_STORE = "IN_STORE"
    CURBSIDE = "CURBSIDE"
    LOCKER = "LOCKER"
    DRIVE_THRU = "DRIVE_THRU"


class ReservationType(str, Enum):
    BOPIS = "BOPIS"
    SHIP_FROM_STORE = "SHIP_FROM_STORE"
    ENDLESS_AISLE = "ENDLESS_AISLE"
    HOLD = "HOLD"


# ============================================================================
# STORE LOCATION SCHEMAS
# ============================================================================

class OperatingHours(BaseModel):
    """Store operating hours for a day."""
    open: str = Field(..., pattern=r"^\d{2}:\d{2}$", description="Opening time HH:MM")
    close: str = Field(..., pattern=r"^\d{2}:\d{2}$", description="Closing time HH:MM")
    is_closed: bool = False


class StoreLocationCreate(BaseModel):
    """Create a store location."""
    store_code: str = Field(..., min_length=3, max_length=30)
    name: str = Field(..., min_length=2, max_length=200)
    store_type: StoreType = StoreType.STANDARD

    # Link to warehouse (optional)
    warehouse_id: Optional[uuid.UUID] = None

    # Contact
    phone: Optional[str] = None
    email: Optional[str] = None
    manager_name: Optional[str] = None
    manager_phone: Optional[str] = None

    # Address
    address_line1: str = Field(..., max_length=255)
    address_line2: Optional[str] = None
    city: str = Field(..., max_length=100)
    state: str = Field(..., max_length=100)
    pincode: str = Field(..., pattern=r"^\d{6}$")
    country: str = "India"

    # Geo
    latitude: Optional[Decimal] = None
    longitude: Optional[Decimal] = None

    # Hours
    operating_hours: Optional[Dict[str, OperatingHours]] = None
    holiday_schedule: Optional[Dict[str, Any]] = None

    # Capabilities
    bopis_enabled: bool = False
    ship_from_store_enabled: bool = False
    boris_enabled: bool = False
    endless_aisle_enabled: bool = False

    # Pickup Options
    curbside_pickup: bool = False
    locker_pickup: bool = False
    drive_thru: bool = False

    # BOPIS Settings
    bopis_prep_time_minutes: int = Field(120, ge=15, le=480)
    bopis_pickup_window_hours: int = Field(72, ge=24, le=168)
    bopis_max_items: Optional[int] = Field(None, ge=1, le=100)

    # Ship-from-Store Settings
    sfs_max_orders_per_day: Optional[int] = Field(None, ge=1)
    sfs_priority: int = Field(50, ge=1, le=100)
    sfs_serviceable_pincodes: Optional[List[str]] = None


class StoreLocationUpdate(BaseModel):
    """Update a store location."""
    name: Optional[str] = None
    store_type: Optional[StoreType] = None
    status: Optional[StoreStatus] = None
    warehouse_id: Optional[uuid.UUID] = None

    phone: Optional[str] = None
    email: Optional[str] = None
    manager_name: Optional[str] = None
    manager_phone: Optional[str] = None

    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None

    latitude: Optional[Decimal] = None
    longitude: Optional[Decimal] = None

    operating_hours: Optional[Dict[str, OperatingHours]] = None
    holiday_schedule: Optional[Dict[str, Any]] = None

    bopis_enabled: Optional[bool] = None
    ship_from_store_enabled: Optional[bool] = None
    boris_enabled: Optional[bool] = None
    endless_aisle_enabled: Optional[bool] = None

    curbside_pickup: Optional[bool] = None
    locker_pickup: Optional[bool] = None
    drive_thru: Optional[bool] = None

    bopis_prep_time_minutes: Optional[int] = None
    bopis_pickup_window_hours: Optional[int] = None
    bopis_max_items: Optional[int] = None

    sfs_max_orders_per_day: Optional[int] = None
    sfs_priority: Optional[int] = None
    sfs_serviceable_pincodes: Optional[List[str]] = None


class StoreLocationResponse(BaseModel):
    """Store location response."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    store_code: str
    name: str
    store_type: str
    status: str

    warehouse_id: Optional[uuid.UUID] = None

    phone: Optional[str] = None
    email: Optional[str] = None
    manager_name: Optional[str] = None

    address_line1: str
    address_line2: Optional[str] = None
    city: str
    state: str
    pincode: str
    country: str
    full_address: str

    latitude: Optional[Decimal] = None
    longitude: Optional[Decimal] = None

    operating_hours: Optional[Dict[str, Any]] = None

    bopis_enabled: bool
    ship_from_store_enabled: bool
    boris_enabled: bool
    endless_aisle_enabled: bool

    curbside_pickup: bool
    locker_pickup: bool
    drive_thru: bool

    bopis_prep_time_minutes: int
    bopis_pickup_window_hours: int
    bopis_max_items: Optional[int] = None

    sfs_max_orders_per_day: Optional[int] = None
    sfs_priority: int

    # Performance
    avg_bopis_prep_time_minutes: Optional[int] = None
    bopis_completion_rate: Optional[Decimal] = None
    sfs_completion_rate: Optional[Decimal] = None
    customer_rating: Optional[Decimal] = None

    created_at: datetime
    updated_at: datetime


class StoreLocationListResponse(BaseModel):
    """Paginated store list."""
    items: List[StoreLocationResponse]
    total: int
    page: int
    size: int
    pages: int


class NearbyStoresRequest(BaseModel):
    """Find stores near a location."""
    latitude: Decimal
    longitude: Decimal
    radius_km: float = Field(10.0, ge=1, le=100)
    bopis_enabled: Optional[bool] = None
    ship_from_store_enabled: Optional[bool] = None
    limit: int = Field(10, ge=1, le=50)


class StoreWithDistance(StoreLocationResponse):
    """Store with distance from search point."""
    distance_km: float


# ============================================================================
# BOPIS ORDER SCHEMAS
# ============================================================================

class BOPISItemCreate(BaseModel):
    """Item for BOPIS order."""
    product_id: uuid.UUID
    variant_id: Optional[uuid.UUID] = None
    sku: str
    quantity: int = Field(..., ge=1)
    unit_price: Decimal


class BOPISOrderCreate(BaseModel):
    """Create a BOPIS order."""
    order_id: uuid.UUID
    store_id: uuid.UUID
    customer_id: uuid.UUID

    pickup_location_type: PickupLocationType = PickupLocationType.IN_STORE
    pickup_instructions: Optional[str] = None

    items: List[BOPISItemCreate]


class BOPISOrderUpdate(BaseModel):
    """Update BOPIS order."""
    pickup_location_type: Optional[PickupLocationType] = None
    pickup_instructions: Optional[str] = None
    storage_location: Optional[str] = None
    notes: Optional[str] = None


class BOPISPickupRequest(BaseModel):
    """Mark BOPIS order as picked up."""
    picked_up_by_name: str = Field(..., min_length=2)
    picked_up_by_phone: Optional[str] = None
    id_verification_type: Optional[str] = None
    id_verification_number: Optional[str] = None
    notes: Optional[str] = None


class BOPISOrderResponse(BaseModel):
    """BOPIS order response."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    order_id: uuid.UUID
    store_id: uuid.UUID
    customer_id: uuid.UUID
    status: str

    pickup_code: str
    pickup_location_type: str
    pickup_instructions: Optional[str] = None

    estimated_ready_at: Optional[datetime] = None
    actual_ready_at: Optional[datetime] = None
    pickup_deadline: Optional[datetime] = None
    picked_up_at: Optional[datetime] = None

    ready_notification_sent: bool
    reminder_sent: bool

    items: Optional[Dict[str, Any]] = None
    total_items: int
    picked_items: int

    picked_up_by_name: Optional[str] = None
    storage_location: Optional[str] = None

    is_expired: bool

    created_at: datetime
    updated_at: datetime
    notes: Optional[str] = None


class BOPISOrderListResponse(BaseModel):
    """Paginated BOPIS order list."""
    items: List[BOPISOrderResponse]
    total: int
    page: int
    size: int
    pages: int


# ============================================================================
# SHIP-FROM-STORE SCHEMAS
# ============================================================================

class SFSItemCreate(BaseModel):
    """Item for ship-from-store order."""
    product_id: uuid.UUID
    variant_id: Optional[uuid.UUID] = None
    sku: str
    quantity: int = Field(..., ge=1)


class ShipFromStoreCreate(BaseModel):
    """Create ship-from-store order."""
    order_id: uuid.UUID
    store_id: uuid.UUID
    items: List[SFSItemCreate]
    shipping_address: Dict[str, Any]
    sla_deadline: Optional[datetime] = None


class SFSAcceptRequest(BaseModel):
    """Accept ship-from-store request."""
    notes: Optional[str] = None


class SFSRejectRequest(BaseModel):
    """Reject ship-from-store request."""
    rejection_reason: str = Field(..., min_length=10)


class SFSShipRequest(BaseModel):
    """Mark SFS order as shipped."""
    carrier_id: uuid.UUID
    tracking_number: str
    notes: Optional[str] = None


class ShipFromStoreResponse(BaseModel):
    """Ship-from-store order response."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    order_id: uuid.UUID
    store_id: uuid.UUID
    status: str
    sfs_number: str

    items: Optional[Dict[str, Any]] = None
    total_items: int
    picked_items: int
    packed_items: int

    shipping_address: Optional[Dict[str, Any]] = None
    carrier_id: Optional[uuid.UUID] = None
    tracking_number: Optional[str] = None
    shipment_id: Optional[uuid.UUID] = None

    rejection_reason: Optional[str] = None
    rejected_at: Optional[datetime] = None

    accepted_at: Optional[datetime] = None
    picking_started_at: Optional[datetime] = None
    packed_at: Optional[datetime] = None
    shipped_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None

    sla_deadline: Optional[datetime] = None

    created_at: datetime
    updated_at: datetime
    notes: Optional[str] = None


class SFSListResponse(BaseModel):
    """Paginated SFS order list."""
    items: List[ShipFromStoreResponse]
    total: int
    page: int
    size: int
    pages: int


# ============================================================================
# STORE RETURN (BORIS) SCHEMAS
# ============================================================================

class ReturnItemCreate(BaseModel):
    """Item being returned."""
    product_id: uuid.UUID
    variant_id: Optional[uuid.UUID] = None
    sku: str
    quantity: int = Field(..., ge=1)
    reason: str


class StoreReturnCreate(BaseModel):
    """Create in-store return (BORIS)."""
    order_id: uuid.UUID
    store_id: uuid.UUID
    customer_id: uuid.UUID
    items: List[ReturnItemCreate]
    return_reason: str
    return_comments: Optional[str] = None
    scheduled_date: Optional[date] = None
    scheduled_time_slot: Optional[str] = None


class ReturnInspectionRequest(BaseModel):
    """Complete return inspection."""
    item_condition: str = Field(..., description="NEW, GOOD, DAMAGED, DEFECTIVE")
    inspection_notes: Optional[str] = None
    approved_items: int
    rejected_items: int


class ReturnRefundRequest(BaseModel):
    """Process refund for return."""
    refund_amount: Decimal = Field(..., gt=0)
    refund_method: str = Field(..., description="ORIGINAL_PAYMENT, STORE_CREDIT, CASH")
    notes: Optional[str] = None


class StoreReturnResponse(BaseModel):
    """Store return response."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    return_number: str
    order_id: uuid.UUID
    store_id: uuid.UUID
    customer_id: uuid.UUID
    original_channel: Optional[str] = None
    status: str

    items: Optional[Dict[str, Any]] = None
    total_items: int
    inspected_items: int
    approved_items: int
    rejected_items: int

    return_reason: Optional[str] = None
    return_comments: Optional[str] = None

    refund_amount: Decimal
    refund_method: Optional[str] = None
    refunded_at: Optional[datetime] = None

    inspection_notes: Optional[str] = None
    item_condition: Optional[str] = None

    restock_decision: Optional[str] = None

    scheduled_date: Optional[date] = None
    scheduled_time_slot: Optional[str] = None

    received_at: Optional[datetime] = None
    inspected_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    created_at: datetime
    updated_at: datetime
    notes: Optional[str] = None


class StoreReturnListResponse(BaseModel):
    """Paginated return list."""
    items: List[StoreReturnResponse]
    total: int
    page: int
    size: int
    pages: int


# ============================================================================
# STORE INVENTORY RESERVATION SCHEMAS
# ============================================================================

class ReservationCreate(BaseModel):
    """Create inventory reservation."""
    store_id: uuid.UUID
    product_id: uuid.UUID
    variant_id: Optional[uuid.UUID] = None
    sku: Optional[str] = None
    quantity_reserved: int = Field(..., ge=1)
    reservation_type: ReservationType
    order_id: Optional[uuid.UUID] = None
    expires_at: Optional[datetime] = None


class ReservationResponse(BaseModel):
    """Reservation response."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    store_id: uuid.UUID
    product_id: uuid.UUID
    variant_id: Optional[uuid.UUID] = None
    sku: Optional[str] = None

    quantity_reserved: int
    quantity_fulfilled: int
    quantity_released: int

    reservation_type: str
    order_id: Optional[uuid.UUID] = None
    bopis_order_id: Optional[uuid.UUID] = None
    sfs_order_id: Optional[uuid.UUID] = None

    is_active: bool
    expires_at: Optional[datetime] = None

    created_at: datetime
    fulfilled_at: Optional[datetime] = None
    released_at: Optional[datetime] = None


# ============================================================================
# STATISTICS SCHEMAS
# ============================================================================

class StoreOmnichannelStats(BaseModel):
    """Omnichannel stats for a store."""
    store_id: uuid.UUID
    store_code: str
    store_name: str

    # BOPIS Stats
    bopis_orders_today: int
    bopis_pending: int
    bopis_ready: int
    bopis_picked_up_today: int
    bopis_expired_today: int
    avg_bopis_prep_time_minutes: Optional[int] = None

    # SFS Stats
    sfs_orders_today: int
    sfs_pending: int
    sfs_shipped_today: int
    sfs_rejected_today: int

    # Return Stats
    returns_today: int
    returns_pending: int
    returns_completed_today: int

    # Inventory
    total_reservations: int
    active_reservations: int


class OmnichannelDashboardStats(BaseModel):
    """Overall omnichannel dashboard stats."""
    # Stores
    total_stores: int
    bopis_enabled_stores: int
    sfs_enabled_stores: int
    boris_enabled_stores: int

    # BOPIS
    total_bopis_today: int
    bopis_ready_for_pickup: int
    bopis_picked_up_today: int
    bopis_expired_today: int
    avg_bopis_time_to_ready_minutes: Optional[int] = None

    # Ship-from-Store
    total_sfs_today: int
    sfs_pending: int
    sfs_shipped_today: int
    sfs_fulfillment_rate: Optional[Decimal] = None

    # Returns
    total_store_returns_today: int
    returns_pending_inspection: int
    returns_completed_today: int
    returns_refunded_today: Decimal
