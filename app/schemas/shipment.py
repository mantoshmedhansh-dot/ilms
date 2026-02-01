"""Pydantic schemas for Shipment models."""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, date
import uuid

from app.models.shipment import ShipmentStatus, PaymentMode, PackagingType
from app.schemas.transporter import TransporterBrief
from app.schemas.base import BaseResponseSchema


# ==================== TRACKING SCHEMAS ====================

class ShipmentTrackingResponse(BaseResponseSchema):
    """Shipment tracking history entry."""
    id: uuid.UUID
    shipment_id: uuid.UUID
    status: str
    status_code: Optional[str] = None
    location: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    remarks: Optional[str] = None
    transporter_remarks: Optional[str] = None
    event_time: datetime
    source: Optional[str] = None
    updated_by: Optional[uuid.UUID] = None
    created_at: datetime
# ==================== SHIPMENT SCHEMAS ====================

class ShippingAddress(BaseModel):
    """Shipping address input."""
    name: str = Field(..., min_length=2, max_length=200)
    phone: str = Field(..., min_length=10, max_length=20)
    email: Optional[str] = None
    address_line1: str
    address_line2: Optional[str] = None
    landmark: Optional[str] = None
    city: str
    state: str
    pincode: str = Field(..., min_length=5, max_length=10)
    country: str = "India"


class ShipmentCreate(BaseModel):
    """Shipment creation schema."""
    order_id: uuid.UUID
    warehouse_id: uuid.UUID
    transporter_id: Optional[uuid.UUID] = None
    payment_mode: PaymentMode = PaymentMode.PREPAID
    cod_amount: Optional[float] = None
    packaging_type: PackagingType = PackagingType.BOX
    no_of_boxes: int = 1
    weight_kg: float = Field(..., gt=0)
    length_cm: Optional[float] = None
    breadth_cm: Optional[float] = None
    height_cm: Optional[float] = None
    ship_to_name: str
    ship_to_phone: str
    ship_to_email: Optional[str] = None
    ship_to_address: dict
    ship_to_pincode: str
    ship_to_city: Optional[str] = None
    ship_to_state: Optional[str] = None
    expected_delivery_date: Optional[date] = None


class ShipmentUpdate(BaseModel):
    """Shipment update schema."""
    transporter_id: Optional[uuid.UUID] = None
    packaging_type: Optional[PackagingType] = None
    no_of_boxes: Optional[int] = None
    weight_kg: Optional[float] = None
    length_cm: Optional[float] = None
    breadth_cm: Optional[float] = None
    height_cm: Optional[float] = None
    expected_delivery_date: Optional[date] = None


class ShipmentResponse(BaseResponseSchema):
    """Shipment response schema."""
    id: uuid.UUID
    shipment_number: str
    order_id: uuid.UUID
    warehouse_id: uuid.UUID
    transporter_id: Optional[uuid.UUID] = None
    transporter: Optional[TransporterBrief] = None
    manifest_id: Optional[uuid.UUID] = None
    awb_number: Optional[str] = None
    tracking_number: Optional[str] = None
    status: str
    payment_mode: str  # VARCHAR in DB
    cod_amount: Optional[float] = None
    cod_collected: bool
    packaging_type: str  # VARCHAR in DB
    no_of_boxes: int
    weight_kg: float
    volumetric_weight_kg: Optional[float] = None
    chargeable_weight_kg: Optional[float] = None
    length_cm: Optional[float] = None
    breadth_cm: Optional[float] = None
    height_cm: Optional[float] = None
    ship_to_name: str
    ship_to_phone: str
    ship_to_email: Optional[str] = None
    ship_to_address: dict
    ship_to_pincode: str
    ship_to_city: Optional[str] = None
    ship_to_state: Optional[str] = None
    expected_delivery_date: Optional[date] = None
    promised_delivery_date: Optional[date] = None
    actual_delivery_date: Optional[date] = None
    delivery_attempts: int
    max_delivery_attempts: int
    delivered_to: Optional[str] = None
    delivery_relation: Optional[str] = None
    delivery_remarks: Optional[str] = None
    pod_image_url: Optional[str] = None
    pod_signature_url: Optional[str] = None
    shipping_label_url: Optional[str] = None
    invoice_url: Optional[str] = None
    shipping_charge: float
    cod_charge: float
    insurance_charge: float
    total_shipping_cost: float

    # Goods Issue tracking (SAP VL09 equivalent)
    goods_issue_at: Optional[datetime] = None
    goods_issue_by: Optional[uuid.UUID] = None
    goods_issue_reference: Optional[str] = None
    is_goods_issued: bool = False

    # Computed properties
    is_delivered: bool
    is_in_transit: bool
    is_rto: bool
    can_reattempt_delivery: bool
    packed_at: Optional[datetime] = None
    shipped_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    cancellation_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime

class ShipmentDetailResponse(ShipmentResponse):
    """Detailed shipment response with tracking history."""
    tracking_history: List[ShipmentTrackingResponse] = []


class ShipmentListResponse(BaseModel):
    """Paginated shipment list."""
    items: List[ShipmentResponse]
    total: int
    page: int
    size: int
    pages: int


class ShipmentBrief(BaseResponseSchema):
    """Brief shipment info."""
    id: uuid.UUID
    shipment_number: str
    awb_number: Optional[str] = None
    status: str
# ==================== SHIPMENT OPERATIONS ====================

class ShipmentPackRequest(BaseModel):
    """Pack shipment request."""
    shipment_id: uuid.UUID
    packaging_type: PackagingType = PackagingType.BOX
    no_of_boxes: int = 1
    weight_kg: float
    length_cm: Optional[float] = None
    breadth_cm: Optional[float] = None
    height_cm: Optional[float] = None
    notes: Optional[str] = None


class ShipmentPackResponse(BaseModel):
    """Pack response."""
    success: bool
    shipment_id: uuid.UUID
    shipment_number: str
    status: str
    message: str


class ShipmentTrackingUpdate(BaseModel):
    """Update shipment tracking."""
    shipment_id: uuid.UUID
    status: ShipmentStatus
    status_code: Optional[str] = None
    location: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    remarks: Optional[str] = None
    event_time: Optional[datetime] = None
    source: str = "MANUAL"


class ShipmentDeliveryMarkRequest(BaseModel):
    """Mark shipment as delivered."""
    shipment_id: uuid.UUID
    delivered_to: str
    delivery_relation: Optional[str] = None
    delivery_remarks: Optional[str] = None
    pod_image_url: Optional[str] = None
    pod_signature_url: Optional[str] = None
    pod_latitude: Optional[float] = None
    pod_longitude: Optional[float] = None
    cod_collected: bool = False


class ShipmentDeliveryMarkResponse(BaseModel):
    """Delivery mark response."""
    success: bool
    shipment_id: uuid.UUID
    shipment_number: str
    order_id: uuid.UUID
    status: str
    delivered_at: datetime
    message: str


class ShipmentRTOInitiateRequest(BaseModel):
    """Initiate RTO for shipment."""
    shipment_id: uuid.UUID
    reason: str


class ShipmentRTOResponse(BaseModel):
    """RTO initiation response."""
    success: bool
    shipment_id: uuid.UUID
    shipment_number: str
    status: str
    rto_reason: str
    message: str


class ShipmentCancelRequest(BaseModel):
    """Cancel shipment."""
    shipment_id: uuid.UUID
    reason: str


# ==================== LABEL & INVOICE ====================

class ShipmentLabelRequest(BaseModel):
    """Generate shipping label."""
    shipment_id: uuid.UUID
    format: str = "PDF"  # PDF, ZPL, PNG


class ShipmentLabelResponse(BaseModel):
    """Shipping label response."""
    shipment_id: uuid.UUID
    shipment_number: str
    awb_number: Optional[str] = None
    label_url: str
    format: str


class ShipmentInvoiceRequest(BaseModel):
    """Generate shipment invoice."""
    shipment_id: uuid.UUID


class ShipmentInvoiceResponse(BaseModel):
    """Shipment invoice response."""
    shipment_id: uuid.UUID
    shipment_number: str
    invoice_url: str


# ==================== BULK OPERATIONS ====================

class BulkShipmentCreate(BaseModel):
    """Bulk create shipments from orders."""
    order_ids: List[uuid.UUID] = Field(..., min_length=1)
    warehouse_id: uuid.UUID
    transporter_id: Optional[uuid.UUID] = None
    default_weight_kg: float = 1.0


class BulkShipmentResponse(BaseModel):
    """Bulk shipment creation response."""
    total_requested: int
    successful: int
    failed: int
    shipments: List[ShipmentBrief]
    errors: List[dict]


# ==================== TRACKING PUBLIC ====================

class TrackShipmentRequest(BaseModel):
    """Public tracking request."""
    awb_number: Optional[str] = None
    order_number: Optional[str] = None


class TrackShipmentResponse(BaseModel):
    """Public tracking response."""
    awb_number: str
    order_number: str
    status: str
    status_description: str
    current_location: Optional[str] = None
    expected_delivery: Optional[date] = None
    delivered_at: Optional[datetime] = None
    delivered_to: Optional[str] = None
    tracking_history: List[ShipmentTrackingResponse] = []
