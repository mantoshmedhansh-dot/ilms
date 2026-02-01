"""Pydantic schemas for Rate Card models (D2C, B2B, FTL)."""
from pydantic import BaseModel, Field, field_validator

from app.schemas.base import BaseResponseSchema
from typing import Optional, List
from datetime import datetime, date
from decimal import Decimal
import uuid

from app.models.rate_card import (
    ServiceType, ZoneCode, SurchargeType, CalculationType,
    B2BServiceType, TransportMode, B2BRateType,
    FTLRateType, VehicleCategory,
)


# ============================================
# D2C RATE CARD SCHEMAS
# ============================================

class D2CWeightSlabCreate(BaseModel):
    """Create schema for D2C weight slab."""
    zone: str = Field(..., min_length=1, max_length=20)
    min_weight_kg: Decimal = Field(default=Decimal("0"), ge=0)
    max_weight_kg: Decimal = Field(..., gt=0)
    base_rate: Decimal = Field(..., gt=0)
    additional_rate_per_kg: Decimal = Field(default=Decimal("0"), ge=0)
    additional_weight_unit_kg: Decimal = Field(default=Decimal("0.5"), gt=0)
    cod_available: bool = True
    prepaid_available: bool = True
    estimated_days_min: Optional[int] = Field(default=None, ge=1)
    estimated_days_max: Optional[int] = Field(default=None, ge=1)
    is_active: bool = True


class D2CWeightSlabResponse(BaseResponseSchema):
    """Response schema for D2C weight slab."""
    id: uuid.UUID
    rate_card_id: uuid.UUID
    zone: str
    min_weight_kg: Decimal
    max_weight_kg: Decimal
    base_rate: Decimal
    additional_rate_per_kg: Decimal
    additional_weight_unit_kg: Decimal
    cod_available: bool
    prepaid_available: bool
    estimated_days_min: Optional[int] = None
    estimated_days_max: Optional[int] = None
    is_active: bool
    created_at: datetime

class D2CSurchargeCreate(BaseModel):
    """Create schema for D2C surcharge."""
    surcharge_type: SurchargeType
    calculation_type: CalculationType = CalculationType.PERCENTAGE
    value: Decimal = Field(..., ge=0)
    min_amount: Optional[Decimal] = Field(default=None, ge=0)
    max_amount: Optional[Decimal] = Field(default=None, ge=0)
    applies_to_cod: bool = True
    applies_to_prepaid: bool = True
    zone: Optional[str] = Field(default=None, max_length=20)
    is_active: bool = True
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None


class D2CSurchargeResponse(BaseResponseSchema):
    """Response schema for D2C surcharge."""
    id: uuid.UUID
    rate_card_id: uuid.UUID
    surcharge_type: SurchargeType
    calculation_type: CalculationType
    value: Decimal
    min_amount: Optional[Decimal] = None
    max_amount: Optional[Decimal] = None
    applies_to_cod: bool
    applies_to_prepaid: bool
    zone: Optional[str] = None
    is_active: bool
    effective_from: Optional[date] = None
    effective_to: Optional[date] = None

class D2CRateCardCreate(BaseModel):
    """Create schema for D2C rate card."""
    transporter_id: uuid.UUID
    code: str = Field(..., min_length=2, max_length=50)
    name: str = Field(..., min_length=2, max_length=200)
    description: Optional[str] = None
    service_type: ServiceType = ServiceType.STANDARD
    zone_type: str = Field(default="DISTANCE", max_length=20)
    effective_from: date
    effective_to: Optional[date] = None
    is_active: bool = True
    is_default: bool = False
    weight_slabs: Optional[List[D2CWeightSlabCreate]] = None
    surcharges: Optional[List[D2CSurchargeCreate]] = None


class D2CRateCardUpdate(BaseModel):
    """Update schema for D2C rate card."""
    name: Optional[str] = Field(default=None, min_length=2, max_length=200)
    description: Optional[str] = None
    service_type: Optional[ServiceType] = None
    zone_type: Optional[str] = Field(default=None, max_length=20)
    effective_to: Optional[date] = None
    is_active: Optional[bool] = None
    is_default: Optional[bool] = None


class D2CRateCardResponse(BaseResponseSchema):
    """Response schema for D2C rate card."""
    id: uuid.UUID
    transporter_id: uuid.UUID
    code: str
    name: str
    description: Optional[str] = None
    service_type: ServiceType
    zone_type: str
    effective_from: date
    effective_to: Optional[date] = None
    is_active: bool
    is_default: bool
    created_at: datetime
    updated_at: datetime
    transporter_name: Optional[str] = None
    transporter_code: Optional[str] = None

class D2CRateCardDetailResponse(D2CRateCardResponse):
    """Detailed response with weight slabs and surcharges."""
    weight_slabs: List[D2CWeightSlabResponse] = []
    surcharges: List[D2CSurchargeResponse] = []


class D2CRateCardListResponse(BaseModel):
    """Paginated D2C rate card list."""
    items: List[D2CRateCardResponse]
    total: int
    page: int
    size: int
    pages: int


class D2CWeightSlabBulkCreate(BaseModel):
    """Bulk create weight slabs."""
    slabs: List[D2CWeightSlabCreate]


class D2CSurchargeBulkCreate(BaseModel):
    """Bulk create surcharges."""
    surcharges: List[D2CSurchargeCreate]


# ============================================
# ZONE MAPPING SCHEMAS
# ============================================

class ZoneMappingCreate(BaseModel):
    """Create schema for zone mapping."""
    origin_pincode: Optional[str] = Field(default=None, max_length=10)
    origin_city: Optional[str] = Field(default=None, max_length=100)
    origin_state: Optional[str] = Field(default=None, max_length=100)
    destination_pincode: Optional[str] = Field(default=None, max_length=10)
    destination_city: Optional[str] = Field(default=None, max_length=100)
    destination_state: Optional[str] = Field(default=None, max_length=100)
    zone: str = Field(..., min_length=1, max_length=20)
    distance_km: Optional[int] = Field(default=None, ge=0)
    is_oda: bool = False


class ZoneMappingResponse(BaseResponseSchema):
    """Response schema for zone mapping."""
    id: uuid.UUID
    origin_pincode: Optional[str] = None
    origin_city: Optional[str] = None
    origin_state: Optional[str] = None
    destination_pincode: Optional[str] = None
    destination_city: Optional[str] = None
    destination_state: Optional[str] = None
    zone: str
    distance_km: Optional[int] = None
    is_oda: bool
    created_at: datetime

class ZoneMappingListResponse(BaseModel):
    """Paginated zone mapping list."""
    items: List[ZoneMappingResponse]
    total: int
    page: int
    size: int
    pages: int


class ZoneLookupRequest(BaseModel):
    """Zone lookup by origin-destination."""
    origin_pincode: str = Field(..., min_length=5, max_length=10)
    destination_pincode: str = Field(..., min_length=5, max_length=10)


class ZoneLookupResponse(BaseModel):
    """Zone lookup result."""
    origin_pincode: str
    destination_pincode: str
    zone: str
    distance_km: Optional[int] = None
    is_oda: bool = False
    found: bool = True


class ZoneMappingBulkCreate(BaseModel):
    """Bulk create zone mappings."""
    mappings: List[ZoneMappingCreate]


# ============================================
# B2B RATE CARD SCHEMAS
# ============================================

class B2BRateSlabCreate(BaseModel):
    """Create schema for B2B rate slab."""
    origin_city: Optional[str] = Field(default=None, max_length=100)
    origin_state: Optional[str] = Field(default=None, max_length=100)
    destination_city: Optional[str] = Field(default=None, max_length=100)
    destination_state: Optional[str] = Field(default=None, max_length=100)
    zone: Optional[str] = Field(default=None, max_length=20)
    min_weight_kg: Decimal = Field(default=Decimal("0"), ge=0)
    max_weight_kg: Optional[Decimal] = Field(default=None, ge=0)
    rate_type: B2BRateType = B2BRateType.PER_KG
    rate: Decimal = Field(..., gt=0)
    min_charge: Optional[Decimal] = Field(default=None, ge=0)
    transit_days_min: Optional[int] = Field(default=None, ge=1)
    transit_days_max: Optional[int] = Field(default=None, ge=1)
    is_active: bool = True


class B2BRateSlabResponse(BaseResponseSchema):
    """Response schema for B2B rate slab."""
    id: uuid.UUID
    rate_card_id: uuid.UUID
    origin_city: Optional[str] = None
    origin_state: Optional[str] = None
    destination_city: Optional[str] = None
    destination_state: Optional[str] = None
    zone: Optional[str] = None
    min_weight_kg: Decimal
    max_weight_kg: Optional[Decimal] = None
    rate_type: B2BRateType
    rate: Decimal
    min_charge: Optional[Decimal] = None
    transit_days_min: Optional[int] = None
    transit_days_max: Optional[int] = None
    is_active: bool
    created_at: datetime

class B2BAdditionalChargeCreate(BaseModel):
    """Create schema for B2B additional charge."""
    charge_type: SurchargeType
    calculation_type: CalculationType = CalculationType.FIXED
    value: Decimal = Field(..., ge=0)
    per_unit: Optional[str] = Field(default=None, max_length=20)
    is_active: bool = True


class B2BAdditionalChargeResponse(BaseResponseSchema):
    """Response schema for B2B additional charge."""
    id: uuid.UUID
    rate_card_id: uuid.UUID
    charge_type: SurchargeType
    calculation_type: CalculationType
    value: Decimal
    per_unit: Optional[str] = None
    is_active: bool

class B2BRateCardCreate(BaseModel):
    """Create schema for B2B rate card."""
    transporter_id: uuid.UUID
    code: str = Field(..., min_length=2, max_length=50)
    name: str = Field(..., min_length=2, max_length=200)
    description: Optional[str] = None
    service_type: B2BServiceType = B2BServiceType.LTL
    transport_mode: TransportMode = TransportMode.SURFACE
    min_chargeable_weight_kg: Decimal = Field(default=Decimal("25"), ge=0)
    min_invoice_value: Optional[Decimal] = Field(default=None, ge=0)
    effective_from: date
    effective_to: Optional[date] = None
    is_active: bool = True
    rate_slabs: Optional[List[B2BRateSlabCreate]] = None
    additional_charges: Optional[List[B2BAdditionalChargeCreate]] = None


class B2BRateCardUpdate(BaseModel):
    """Update schema for B2B rate card."""
    name: Optional[str] = Field(default=None, min_length=2, max_length=200)
    description: Optional[str] = None
    service_type: Optional[B2BServiceType] = None
    transport_mode: Optional[TransportMode] = None
    min_chargeable_weight_kg: Optional[Decimal] = Field(default=None, ge=0)
    min_invoice_value: Optional[Decimal] = Field(default=None, ge=0)
    effective_to: Optional[date] = None
    is_active: Optional[bool] = None


class B2BRateCardResponse(BaseResponseSchema):
    """Response schema for B2B rate card."""
    id: uuid.UUID
    transporter_id: uuid.UUID
    code: str
    name: str
    description: Optional[str] = None
    service_type: B2BServiceType
    transport_mode: TransportMode
    min_chargeable_weight_kg: Decimal
    min_invoice_value: Optional[Decimal] = None
    effective_from: date
    effective_to: Optional[date] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    transporter_name: Optional[str] = None
    transporter_code: Optional[str] = None

class B2BRateCardDetailResponse(B2BRateCardResponse):
    """Detailed response with rate slabs and additional charges."""
    rate_slabs: List[B2BRateSlabResponse] = []
    additional_charges: List[B2BAdditionalChargeResponse] = []


class B2BRateCardListResponse(BaseModel):
    """Paginated B2B rate card list."""
    items: List[B2BRateCardResponse]
    total: int
    page: int
    size: int
    pages: int


class B2BRateSlabBulkCreate(BaseModel):
    """Bulk create B2B rate slabs."""
    slabs: List[B2BRateSlabCreate]


# ============================================
# FTL RATE CARD SCHEMAS
# ============================================

class FTLLaneRateCreate(BaseModel):
    """Create schema for FTL lane rate."""
    origin_city: str = Field(..., min_length=2, max_length=100)
    origin_state: str = Field(..., min_length=2, max_length=100)
    origin_pincode: Optional[str] = Field(default=None, max_length=10)
    destination_city: str = Field(..., min_length=2, max_length=100)
    destination_state: str = Field(..., min_length=2, max_length=100)
    destination_pincode: Optional[str] = Field(default=None, max_length=10)
    distance_km: Optional[int] = Field(default=None, ge=0)
    vehicle_type: str = Field(..., min_length=2, max_length=50)
    vehicle_capacity_tons: Optional[Decimal] = Field(default=None, gt=0)
    vehicle_capacity_cft: Optional[int] = Field(default=None, gt=0)
    rate_per_trip: Decimal = Field(..., gt=0)
    rate_per_km: Optional[Decimal] = Field(default=None, ge=0)
    min_running_km: Optional[int] = Field(default=None, ge=0)
    extra_km_rate: Optional[Decimal] = Field(default=None, ge=0)
    transit_hours: Optional[int] = Field(default=None, ge=1)
    loading_points_included: int = Field(default=1, ge=1)
    unloading_points_included: int = Field(default=1, ge=1)
    extra_point_charge: Optional[Decimal] = Field(default=None, ge=0)
    is_active: bool = True


class FTLLaneRateResponse(BaseResponseSchema):
    """Response schema for FTL lane rate."""
    id: uuid.UUID
    rate_card_id: uuid.UUID
    origin_city: str
    origin_state: str
    origin_pincode: Optional[str] = None
    destination_city: str
    destination_state: str
    destination_pincode: Optional[str] = None
    distance_km: Optional[int] = None
    vehicle_type: str
    vehicle_capacity_tons: Optional[Decimal] = None
    vehicle_capacity_cft: Optional[int] = None
    rate_per_trip: Decimal
    rate_per_km: Optional[Decimal] = None
    min_running_km: Optional[int] = None
    extra_km_rate: Optional[Decimal] = None
    transit_hours: Optional[int] = None
    loading_points_included: int
    unloading_points_included: int
    extra_point_charge: Optional[Decimal] = None
    is_active: bool
    created_at: datetime

class FTLAdditionalChargeCreate(BaseModel):
    """Create schema for FTL additional charge."""
    charge_type: str = Field(..., min_length=2, max_length=50)
    calculation_type: CalculationType = CalculationType.FIXED
    value: Decimal = Field(..., ge=0)
    per_unit: Optional[str] = Field(default=None, max_length=20)
    free_hours: Optional[int] = Field(default=None, ge=0)
    is_active: bool = True


class FTLAdditionalChargeResponse(BaseResponseSchema):
    """Response schema for FTL additional charge."""
    id: uuid.UUID
    rate_card_id: uuid.UUID
    charge_type: str
    calculation_type: CalculationType
    value: Decimal
    per_unit: Optional[str] = None
    free_hours: Optional[int] = None
    is_active: bool

class FTLRateCardCreate(BaseModel):
    """Create schema for FTL rate card."""
    transporter_id: Optional[uuid.UUID] = None
    code: str = Field(..., min_length=2, max_length=50)
    name: str = Field(..., min_length=2, max_length=200)
    description: Optional[str] = None
    rate_type: FTLRateType = FTLRateType.CONTRACT
    payment_terms: Optional[str] = Field(default=None, max_length=100)
    effective_from: date
    effective_to: Optional[date] = None
    is_active: bool = True
    lane_rates: Optional[List[FTLLaneRateCreate]] = None
    additional_charges: Optional[List[FTLAdditionalChargeCreate]] = None


class FTLRateCardUpdate(BaseModel):
    """Update schema for FTL rate card."""
    transporter_id: Optional[uuid.UUID] = None
    name: Optional[str] = Field(default=None, min_length=2, max_length=200)
    description: Optional[str] = None
    rate_type: Optional[FTLRateType] = None
    payment_terms: Optional[str] = Field(default=None, max_length=100)
    effective_to: Optional[date] = None
    is_active: Optional[bool] = None


class FTLRateCardResponse(BaseResponseSchema):
    """Response schema for FTL rate card."""
    id: uuid.UUID
    transporter_id: Optional[uuid.UUID] = None
    code: str
    name: str
    description: Optional[str] = None
    rate_type: FTLRateType
    payment_terms: Optional[str] = None
    effective_from: date
    effective_to: Optional[date] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    transporter_name: Optional[str] = None
    transporter_code: Optional[str] = None

class FTLRateCardDetailResponse(FTLRateCardResponse):
    """Detailed response with lane rates and additional charges."""
    lane_rates: List[FTLLaneRateResponse] = []
    additional_charges: List[FTLAdditionalChargeResponse] = []


class FTLRateCardListResponse(BaseModel):
    """Paginated FTL rate card list."""
    items: List[FTLRateCardResponse]
    total: int
    page: int
    size: int
    pages: int


class FTLLaneRateBulkCreate(BaseModel):
    """Bulk create FTL lane rates."""
    lane_rates: List[FTLLaneRateCreate]


# ============================================
# FTL VEHICLE TYPE SCHEMAS
# ============================================

class FTLVehicleTypeCreate(BaseModel):
    """Create schema for FTL vehicle type."""
    code: str = Field(..., min_length=2, max_length=30)
    name: str = Field(..., min_length=2, max_length=100)
    length_ft: Optional[Decimal] = Field(default=None, gt=0)
    width_ft: Optional[Decimal] = Field(default=None, gt=0)
    height_ft: Optional[Decimal] = Field(default=None, gt=0)
    capacity_tons: Optional[Decimal] = Field(default=None, gt=0)
    capacity_cft: Optional[int] = Field(default=None, gt=0)
    category: Optional[VehicleCategory] = None
    is_active: bool = True


class FTLVehicleTypeUpdate(BaseModel):
    """Update schema for FTL vehicle type."""
    name: Optional[str] = Field(default=None, min_length=2, max_length=100)
    length_ft: Optional[Decimal] = Field(default=None, gt=0)
    width_ft: Optional[Decimal] = Field(default=None, gt=0)
    height_ft: Optional[Decimal] = Field(default=None, gt=0)
    capacity_tons: Optional[Decimal] = Field(default=None, gt=0)
    capacity_cft: Optional[int] = Field(default=None, gt=0)
    category: Optional[VehicleCategory] = None
    is_active: Optional[bool] = None


class FTLVehicleTypeResponse(BaseResponseSchema):
    """Response schema for FTL vehicle type."""
    id: uuid.UUID
    code: str
    name: str
    length_ft: Optional[Decimal] = None
    width_ft: Optional[Decimal] = None
    height_ft: Optional[Decimal] = None
    capacity_tons: Optional[Decimal] = None
    capacity_cft: Optional[int] = None
    category: Optional[str] = None
    is_active: bool
    created_at: datetime

class FTLVehicleTypeListResponse(BaseModel):
    """Paginated FTL vehicle type list."""
    items: List[FTLVehicleTypeResponse]
    total: int
    page: int
    size: int
    pages: int


# ============================================
# CARRIER PERFORMANCE SCHEMAS
# ============================================

class CarrierPerformanceResponse(BaseResponseSchema):
    """Response schema for carrier performance."""
    id: uuid.UUID
    transporter_id: uuid.UUID
    period_start: date
    period_end: date
    zone: Optional[str] = None
    origin_city: Optional[str] = None
    destination_city: Optional[str] = None
    total_shipments: int
    total_weight_kg: Decimal
    total_revenue: Decimal
    on_time_delivery_count: int
    on_time_pickup_count: int
    total_delivered: int
    rto_count: int
    damage_count: int
    lost_count: int
    ndr_count: int
    delivery_score: Optional[Decimal] = None
    pickup_score: Optional[Decimal] = None
    rto_score: Optional[Decimal] = None
    damage_score: Optional[Decimal] = None
    overall_score: Optional[Decimal] = None
    score_trend: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    transporter_name: Optional[str] = None
    transporter_code: Optional[str] = None

class CarrierPerformanceListResponse(BaseModel):
    """Paginated carrier performance list."""
    items: List[CarrierPerformanceResponse]
    total: int
    page: int
    size: int
    pages: int


class CarrierPerformanceRecalculateRequest(BaseModel):
    """Request to recalculate carrier performance."""
    transporter_id: uuid.UUID
    period_start: date
    period_end: date
    zone: Optional[str] = None


# ============================================
# RATE CALCULATION SCHEMAS
# ============================================

class RateCalculationRequest(BaseModel):
    """Request for rate calculation."""
    origin_pincode: str = Field(..., min_length=5, max_length=10)
    destination_pincode: str = Field(..., min_length=5, max_length=10)
    weight_kg: Decimal = Field(..., gt=0)
    length_cm: Optional[Decimal] = Field(default=None, gt=0)
    width_cm: Optional[Decimal] = Field(default=None, gt=0)
    height_cm: Optional[Decimal] = Field(default=None, gt=0)
    payment_mode: str = Field(default="PREPAID", pattern="^(COD|PREPAID)$")
    order_value: Optional[Decimal] = Field(default=None, ge=0)
    channel: Optional[str] = Field(default=None, max_length=50)
    carrier_ids: Optional[List[uuid.UUID]] = None


class CostBreakdown(BaseModel):
    """Cost breakdown for a rate calculation."""
    base_freight: Decimal
    fuel_surcharge: Decimal = Decimal("0")
    cod_charge: Decimal = Decimal("0")
    oda_charge: Decimal = Decimal("0")
    handling_charge: Decimal = Decimal("0")
    other_charges: Decimal = Decimal("0")
    gst: Decimal = Decimal("0")
    total: Decimal


class CarrierRateOption(BaseModel):
    """Single carrier rate option."""
    transporter_id: uuid.UUID
    transporter_code: str
    transporter_name: str
    rate_card_id: uuid.UUID
    rate_card_code: str
    zone: str
    chargeable_weight_kg: Decimal
    cost_breakdown: CostBreakdown
    estimated_days_min: Optional[int] = None
    estimated_days_max: Optional[int] = None
    cod_available: bool
    prepaid_available: bool
    performance_score: Optional[Decimal] = None
    allocation_score: Optional[Decimal] = None


class RateCalculationResponse(BaseModel):
    """Response for rate calculation."""
    origin_pincode: str
    destination_pincode: str
    zone: str
    actual_weight_kg: Decimal
    volumetric_weight_kg: Optional[Decimal] = None
    chargeable_weight_kg: Decimal
    payment_mode: str
    carriers: List[CarrierRateOption]
    recommended: Optional[CarrierRateOption] = None


class CarrierComparisonRequest(BaseModel):
    """Request for carrier comparison."""
    origin_pincode: str = Field(..., min_length=5, max_length=10)
    destination_pincode: str = Field(..., min_length=5, max_length=10)
    weight_kg: Decimal = Field(..., gt=0)
    dimensions: Optional[dict] = None
    payment_mode: str = Field(default="PREPAID", pattern="^(COD|PREPAID)$")
    sort_by: str = Field(default="cost", pattern="^(cost|tat|score)$")


class CarrierComparisonResponse(BaseModel):
    """Response for carrier comparison."""
    origin_pincode: str
    destination_pincode: str
    zone: str
    carriers: List[CarrierRateOption]


# ============================================
# ALLOCATION SCHEMAS
# ============================================

class AllocationRequest(BaseModel):
    """Request for carrier allocation."""
    order_id: Optional[uuid.UUID] = None
    shipment_id: Optional[uuid.UUID] = None
    origin_pincode: str = Field(..., min_length=5, max_length=10)
    origin_city: Optional[str] = None
    destination_pincode: str = Field(..., min_length=5, max_length=10)
    destination_city: Optional[str] = None
    weight_kg: Decimal = Field(..., gt=0)
    length_cm: Optional[Decimal] = None
    width_cm: Optional[Decimal] = None
    height_cm: Optional[Decimal] = None
    payment_mode: str = Field(default="PREPAID", pattern="^(COD|PREPAID)$")
    order_value: Optional[Decimal] = None
    channel: Optional[str] = None
    strategy: str = Field(
        default="BALANCED",
        pattern="^(CHEAPEST_FIRST|FASTEST_FIRST|BEST_SLA|BALANCED)$"
    )
    preferred_carriers: Optional[List[uuid.UUID]] = None
    excluded_carriers: Optional[List[uuid.UUID]] = None


class AllocationResponse(BaseModel):
    """Response for carrier allocation."""
    success: bool
    order_id: Optional[uuid.UUID] = None
    shipment_id: Optional[uuid.UUID] = None
    allocated_carrier: Optional[CarrierRateOption] = None
    alternatives: List[CarrierRateOption] = []
    zone: str
    strategy_used: str
    allocation_reason: str
    allocation_log_id: Optional[uuid.UUID] = None


class BulkAllocationRequest(BaseModel):
    """Request for bulk carrier allocation."""
    allocations: List[AllocationRequest]


class BulkAllocationResponse(BaseModel):
    """Response for bulk carrier allocation."""
    success_count: int
    failure_count: int
    results: List[AllocationResponse]


# ============================================
# DROPDOWN/BRIEF SCHEMAS
# ============================================

class RateCardBrief(BaseResponseSchema):
    """Brief rate card info for dropdowns."""
    id: uuid.UUID
    code: str
    name: str
    service_type: str
    is_active: bool
class TransporterRateCardSummary(BaseModel):
    """Summary of rate cards per transporter."""
    transporter_id: uuid.UUID
    transporter_code: str
    transporter_name: str
    d2c_rate_cards: int = 0
    b2b_rate_cards: int = 0
    ftl_rate_cards: int = 0
    active_d2c: int = 0
    active_b2b: int = 0
    active_ftl: int = 0


# ==================== Rate Calculation & Allocation Schemas ====================

class RateCalculationRequestSchema(BaseModel):
    """Request schema for rate calculation."""
    origin_pincode: str = Field(..., min_length=5, max_length=10, description="Origin pincode")
    destination_pincode: str = Field(..., min_length=5, max_length=10, description="Destination pincode")
    weight_kg: float = Field(..., gt=0, description="Weight in kg")
    length_cm: Optional[float] = Field(None, gt=0, description="Length in cm")
    width_cm: Optional[float] = Field(None, gt=0, description="Width in cm")
    height_cm: Optional[float] = Field(None, gt=0, description="Height in cm")
    payment_mode: str = Field("PREPAID", pattern="^(PREPAID|COD)$", description="Payment mode")
    order_value: float = Field(0, ge=0, description="Order value")
    channel: str = Field("D2C", description="Channel")
    declared_value: Optional[float] = Field(None, ge=0, description="Declared value")
    is_fragile: bool = Field(False, description="Whether item is fragile")
    num_packages: int = Field(1, ge=1, description="Number of packages")
    service_type: Optional[str] = Field(None, description="Service type filter")
    transporter_ids: Optional[List[uuid.UUID]] = Field(None, description="Filter by transporter IDs")


class AllocationRequestSchema(BaseModel):
    """Request schema for carrier allocation."""
    origin_pincode: str = Field(..., min_length=5, max_length=10, description="Origin pincode")
    destination_pincode: str = Field(..., min_length=5, max_length=10, description="Destination pincode")
    weight_kg: float = Field(..., gt=0, description="Weight in kg")
    length_cm: Optional[float] = Field(None, gt=0, description="Length in cm")
    width_cm: Optional[float] = Field(None, gt=0, description="Width in cm")
    height_cm: Optional[float] = Field(None, gt=0, description="Height in cm")
    payment_mode: str = Field("PREPAID", pattern="^(PREPAID|COD)$", description="Payment mode")
    order_value: float = Field(0, ge=0, description="Order value")
    channel: str = Field("D2C", description="Channel")
    declared_value: Optional[float] = Field(None, ge=0, description="Declared value")
    is_fragile: bool = Field(False, description="Whether item is fragile")
    num_packages: int = Field(1, ge=1, description="Number of packages")
    service_type: Optional[str] = Field(None, description="Service type filter")
    transporter_ids: Optional[List[uuid.UUID]] = Field(None, description="Filter by transporter IDs")
    strategy: str = Field(
        "BALANCED",
        pattern="^(CHEAPEST_FIRST|FASTEST_FIRST|BEST_SLA|BALANCED)$",
        description="Allocation strategy"
    )
