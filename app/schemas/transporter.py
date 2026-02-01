"""Pydantic schemas for Transporter/Carrier models."""
from pydantic import BaseModel, Field

from app.schemas.base import BaseResponseSchema
from typing import Optional, List
from datetime import datetime
import uuid

from app.models.transporter import TransporterType


# ==================== TRANSPORTER SCHEMAS ====================

class TransporterCreate(BaseModel):
    """Transporter creation schema."""
    code: str = Field(..., min_length=2, max_length=20)
    name: str = Field(..., min_length=2, max_length=200)
    transporter_type: TransporterType = TransporterType.COURIER

    # API Integration
    api_endpoint: Optional[str] = None
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    webhook_url: Optional[str] = None

    # Capabilities
    supports_cod: bool = True
    supports_prepaid: bool = True
    supports_reverse_pickup: bool = False
    supports_surface: bool = True
    supports_express: bool = False

    # Weight limits
    max_weight_kg: Optional[float] = None
    min_weight_kg: float = 0.0

    # Pricing
    base_rate: Optional[float] = None
    rate_per_kg: Optional[float] = None
    cod_charges: Optional[float] = None
    cod_percentage: Optional[float] = None

    # Contact
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    address: Optional[str] = None

    # Tracking
    tracking_url_template: Optional[str] = None

    # AWB
    awb_prefix: Optional[str] = None
    awb_sequence_start: int = 1

    # Priority
    priority: int = 100


class TransporterUpdate(BaseModel):
    """Transporter update schema."""
    name: Optional[str] = None
    transporter_type: Optional[TransporterType] = None
    is_active: Optional[bool] = None

    # API Integration
    api_endpoint: Optional[str] = None
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    webhook_url: Optional[str] = None

    # Capabilities
    supports_cod: Optional[bool] = None
    supports_prepaid: Optional[bool] = None
    supports_reverse_pickup: Optional[bool] = None
    supports_surface: Optional[bool] = None
    supports_express: Optional[bool] = None

    # Weight limits
    max_weight_kg: Optional[float] = None
    min_weight_kg: Optional[float] = None

    # Pricing
    base_rate: Optional[float] = None
    rate_per_kg: Optional[float] = None
    cod_charges: Optional[float] = None
    cod_percentage: Optional[float] = None

    # Contact
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    address: Optional[str] = None

    # Tracking
    tracking_url_template: Optional[str] = None

    # Priority
    priority: Optional[int] = None


class TransporterResponse(BaseResponseSchema):
    """Transporter response schema."""
    id: uuid.UUID
    code: str
    name: str
    transporter_type: str  # VARCHAR in DB
    is_active: bool
    supports_cod: bool
    supports_prepaid: bool
    supports_reverse_pickup: bool
    supports_surface: bool
    supports_express: bool
    max_weight_kg: Optional[float] = None
    min_weight_kg: float
    base_rate: Optional[float] = None
    rate_per_kg: Optional[float] = None
    cod_charges: Optional[float] = None
    contact_name: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    tracking_url_template: Optional[str] = None
    priority: int
    created_at: datetime
    updated_at: datetime

class TransporterBrief(BaseResponseSchema):
    """Brief transporter info."""
    id: uuid.UUID
    code: str
    name: str
    transporter_type: TransporterType
class TransporterListResponse(BaseModel):
    """Paginated transporter list."""
    items: List[TransporterResponse]
    total: int
    page: int
    size: int
    pages: int


# ==================== SERVICEABILITY SCHEMAS ====================

class ServiceabilityCreate(BaseModel):
    """Transporter serviceability creation schema."""
    transporter_id: uuid.UUID
    origin_pincode: str = Field(..., min_length=5, max_length=10)
    destination_pincode: str = Field(..., min_length=5, max_length=10)
    is_serviceable: bool = True
    estimated_days: Optional[int] = None
    cod_available: bool = True
    prepaid_available: bool = True
    surface_available: bool = True
    express_available: bool = False
    rate: Optional[float] = None
    cod_charge: Optional[float] = None
    origin_state: Optional[str] = None
    destination_state: Optional[str] = None
    origin_city: Optional[str] = None
    destination_city: Optional[str] = None
    zone: Optional[str] = None


class ServiceabilityBulkCreate(BaseModel):
    """Bulk serviceability creation."""
    transporter_id: uuid.UUID
    items: List[ServiceabilityCreate]


class ServiceabilityResponse(BaseResponseSchema):
    """Serviceability response schema."""
    id: uuid.UUID
    transporter_id: uuid.UUID
    origin_pincode: str
    destination_pincode: str
    is_serviceable: bool
    estimated_days: Optional[int] = None
    cod_available: bool
    prepaid_available: bool
    surface_available: bool
    express_available: bool
    rate: Optional[float] = None
    cod_charge: Optional[float] = None
    zone: Optional[str] = None
    created_at: datetime

class ServiceabilityCheckRequest(BaseModel):
    """Check serviceability request."""
    from_pincode: str = Field(..., min_length=5, max_length=10)
    to_pincode: str = Field(..., min_length=5, max_length=10)
    payment_mode: Optional[str] = None  # COD or PREPAID
    weight_kg: Optional[float] = None


class ServiceabilityCheckResponse(BaseModel):
    """Serviceability check response."""
    is_serviceable: bool
    available_transporters: List["TransporterServiceabilityOption"]


class TransporterServiceabilityOption(BaseModel):
    """Available transporter option."""
    transporter: TransporterBrief
    estimated_days: Optional[int] = None
    cod_available: bool
    prepaid_available: bool
    rate: Optional[float] = None
    cod_charge: Optional[float] = None


# ==================== AWB GENERATION ====================

class AWBGenerateRequest(BaseModel):
    """AWB generation request."""
    transporter_id: uuid.UUID
    order_id: Optional[uuid.UUID] = None
    shipment_id: Optional[uuid.UUID] = None


class AWBGenerateResponse(BaseModel):
    """AWB generation response."""
    awb_number: str
    transporter_id: uuid.UUID
    transporter_code: str
    tracking_url: Optional[str] = None


# Update forward references
ServiceabilityCheckResponse.model_rebuild()
