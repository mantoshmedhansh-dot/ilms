"""Pydantic schemas for Manifest models."""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import uuid

from app.models.manifest import ManifestStatus, BusinessType
from app.schemas.transporter import TransporterBrief
from app.schemas.base import BaseResponseSchema


# ==================== MANIFEST ITEM SCHEMAS ====================

class ManifestItemResponse(BaseResponseSchema):
    """Manifest item response schema."""
    id: uuid.UUID
    manifest_id: uuid.UUID
    shipment_id: uuid.UUID
    awb_number: str
    tracking_number: Optional[str] = None
    order_number: str
    weight_kg: float
    no_of_boxes: int
    is_scanned: bool
    scanned_at: Optional[datetime] = None
    scanned_by: Optional[uuid.UUID] = None
    is_handed_over: bool
    handed_over_at: Optional[datetime] = None
    destination_pincode: Optional[str] = None
    destination_city: Optional[str] = None
    created_at: datetime

class ManifestItemBrief(BaseResponseSchema):
    """Brief manifest item info."""
    id: uuid.UUID
    awb_number: str
    order_number: str
    is_scanned: bool
    is_handed_over: bool
# ==================== MANIFEST SCHEMAS ====================

class ManifestCreate(BaseModel):
    """Manifest creation schema."""
    warehouse_id: uuid.UUID
    transporter_id: uuid.UUID
    business_type: BusinessType = BusinessType.B2C
    manifest_date: Optional[datetime] = None
    vehicle_number: Optional[str] = None
    driver_name: Optional[str] = None
    driver_phone: Optional[str] = None
    remarks: Optional[str] = None


class ManifestUpdate(BaseModel):
    """Manifest update schema."""
    transporter_id: Optional[uuid.UUID] = None
    business_type: Optional[BusinessType] = None
    vehicle_number: Optional[str] = None
    driver_name: Optional[str] = None
    driver_phone: Optional[str] = None
    remarks: Optional[str] = None


class ManifestResponse(BaseResponseSchema):
    """Manifest response schema."""
    id: uuid.UUID
    manifest_number: str
    warehouse_id: uuid.UUID
    transporter_id: uuid.UUID
    transporter: Optional[TransporterBrief] = None
    status: str
    business_type: str  # VARCHAR in DB
    manifest_date: datetime
    total_shipments: int
    scanned_shipments: int
    scan_progress: float
    all_scanned: bool
    total_weight_kg: float
    total_boxes: int
    vehicle_number: Optional[str] = None
    driver_name: Optional[str] = None
    driver_phone: Optional[str] = None
    remarks: Optional[str] = None
    created_by: Optional[uuid.UUID] = None
    confirmed_by: Optional[uuid.UUID] = None
    confirmed_at: Optional[datetime] = None
    handover_at: Optional[datetime] = None
    handover_by: Optional[uuid.UUID] = None
    cancelled_at: Optional[datetime] = None
    cancellation_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime

class ManifestDetailResponse(ManifestResponse):
    """Detailed manifest response with items."""
    items: List[ManifestItemResponse] = []


class ManifestListResponse(BaseModel):
    """Paginated manifest list."""
    items: List[ManifestResponse]
    total: int
    page: int
    size: int
    pages: int


class ManifestBrief(BaseResponseSchema):
    """Brief manifest info."""
    id: uuid.UUID
    manifest_number: str
    status: str
    total_shipments: int
# ==================== MANIFEST OPERATIONS ====================

class ManifestAddShipmentRequest(BaseModel):
    """Add shipment to manifest."""
    shipment_ids: List[uuid.UUID] = Field(..., min_length=1)


class ManifestRemoveShipmentRequest(BaseModel):
    """Remove shipment from manifest."""
    shipment_ids: List[uuid.UUID] = Field(..., min_length=1)


class ManifestScanRequest(BaseModel):
    """Scan shipment for handover."""
    awb_number: Optional[str] = None
    shipment_id: Optional[uuid.UUID] = None
    barcode: Optional[str] = None


class ManifestScanResponse(BaseModel):
    """Scan response."""
    success: bool
    message: str
    item: Optional[ManifestItemBrief] = None
    total_scanned: int
    total_pending: int


class ManifestConfirmRequest(BaseModel):
    """Confirm manifest for handover."""
    manifest_id: uuid.UUID
    vehicle_number: Optional[str] = None
    driver_name: Optional[str] = None
    driver_phone: Optional[str] = None
    remarks: Optional[str] = None


class ManifestConfirmResponse(BaseModel):
    """Manifest confirmation response."""
    success: bool
    manifest_id: uuid.UUID
    manifest_number: str
    status: str
    total_shipments: int
    message: str


class ManifestHandoverRequest(BaseModel):
    """Complete handover to transporter."""
    manifest_id: uuid.UUID
    handover_remarks: Optional[str] = None


class ManifestHandoverResponse(BaseModel):
    """Handover completion response."""
    success: bool
    manifest_id: uuid.UUID
    manifest_number: str
    status: str
    shipped_orders: int
    message: str


class ManifestCancelRequest(BaseModel):
    """Cancel manifest."""
    manifest_id: uuid.UUID
    reason: str


# ==================== MANIFEST PRINT ====================

class ManifestPrintResponse(BaseModel):
    """Manifest print data."""
    manifest: ManifestDetailResponse
    company_name: str
    company_address: str
    company_phone: str
    company_gstin: Optional[str] = None
    print_date: datetime
    print_url: Optional[str] = None
