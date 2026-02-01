"""
Serviceability and Allocation Schemas.

Covers:
1. WarehouseServiceability - Pincode mapping for warehouses
2. AllocationRule - Order routing rules
3. Serviceability Check - API request/response
4. Allocation Decision - Order allocation response
"""
from datetime import datetime
from typing import Optional, List
from uuid import UUID
from decimal import Decimal

from pydantic import BaseModel, Field, ConfigDict

from app.schemas.base import BaseResponseSchema


# ==================== Enums ====================

class AllocationType(str):
    NEAREST = "NEAREST"
    ROUND_ROBIN = "ROUND_ROBIN"
    FIFO = "FIFO"
    FIXED = "FIXED"
    PRIORITY = "PRIORITY"
    COST_OPTIMIZED = "COST_OPTIMIZED"


class ChannelCode(str):
    D2C = "D2C"
    AMAZON = "AMAZON"
    FLIPKART = "FLIPKART"
    MYNTRA = "MYNTRA"
    MEESHO = "MEESHO"
    TATACLIQ = "TATACLIQ"
    DEALER = "DEALER"
    STORE = "STORE"
    ALL = "ALL"


# ==================== Warehouse Serviceability ====================

class WarehouseServiceabilityBase(BaseModel):
    """Base schema for warehouse serviceability."""
    pincode: str = Field(..., min_length=6, max_length=6, description="6-digit pincode")
    is_serviceable: bool = True
    cod_available: bool = True
    prepaid_available: bool = True
    estimated_days: Optional[int] = Field(None, ge=1, le=30)
    priority: int = Field(default=100, ge=1, le=1000)
    shipping_cost: Optional[float] = Field(None, ge=0)
    city: Optional[str] = None
    state: Optional[str] = None
    zone: Optional[str] = Field(None, description="LOCAL, REGIONAL, NATIONAL, METRO")
    is_active: bool = True


class WarehouseServiceabilityCreate(WarehouseServiceabilityBase):
    """Schema for creating warehouse serviceability."""
    warehouse_id: UUID


class WarehouseServiceabilityBulkCreate(BaseModel):
    """Schema for bulk creating warehouse serviceability."""
    warehouse_id: UUID
    pincodes: List[str] = Field(..., min_length=1, description="List of pincodes to add")
    cod_available: bool = True
    prepaid_available: bool = True
    estimated_days: Optional[int] = None
    zone: Optional[str] = None


class WarehouseServiceabilityUpdate(BaseModel):
    """Schema for updating warehouse serviceability."""
    is_serviceable: Optional[bool] = None
    cod_available: Optional[bool] = None
    prepaid_available: Optional[bool] = None
    estimated_days: Optional[int] = None
    priority: Optional[int] = None
    shipping_cost: Optional[float] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zone: Optional[str] = None
    is_active: Optional[bool] = None


class WarehouseServiceabilityResponse(BaseResponseSchema):
    """Response schema for warehouse serviceability."""
    id: UUID
    warehouse_id: UUID
    warehouse_name: Optional[str] = None
    warehouse_code: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class WarehouseServiceabilityList(BaseModel):
    """List response for warehouse serviceability."""
    items: List[WarehouseServiceabilityResponse]
    total: int
    page: int
    page_size: int


# ==================== Allocation Rule ====================

class AllocationRuleBase(BaseModel):
    """Base schema for allocation rule."""
    name: str = Field(..., min_length=3, max_length=200)
    description: Optional[str] = None
    channel_code: str = Field(default="ALL")
    priority: int = Field(default=100, ge=1, le=1000)
    allocation_type: str = Field(default="NEAREST")
    priority_factors: Optional[str] = Field(
        None,
        description="Comma-separated: PROXIMITY,INVENTORY,COST,SLA"
    )
    min_order_value: Optional[float] = None
    max_order_value: Optional[float] = None
    payment_mode: Optional[str] = Field(None, description="COD, PREPAID, or null for all")
    allow_split: bool = False
    max_splits: int = Field(default=2, ge=1, le=5)
    is_active: bool = True


class AllocationRuleCreate(AllocationRuleBase):
    """Schema for creating allocation rule."""
    channel_id: Optional[UUID] = None
    fixed_warehouse_id: Optional[UUID] = Field(
        None,
        description="Required if allocation_type is FIXED"
    )


class AllocationRuleUpdate(BaseModel):
    """Schema for updating allocation rule."""
    name: Optional[str] = None
    description: Optional[str] = None
    channel_code: Optional[str] = None
    channel_id: Optional[UUID] = None
    priority: Optional[int] = None
    allocation_type: Optional[str] = None
    fixed_warehouse_id: Optional[UUID] = None
    priority_factors: Optional[str] = None
    min_order_value: Optional[float] = None
    max_order_value: Optional[float] = None
    payment_mode: Optional[str] = None
    allow_split: Optional[bool] = None
    max_splits: Optional[int] = None
    is_active: Optional[bool] = None


class AllocationRuleResponse(BaseResponseSchema):
    """Response schema for allocation rule."""
    id: UUID
    channel_id: Optional[UUID] = None
    fixed_warehouse_id: Optional[UUID] = None
    fixed_warehouse_name: Optional[str] = None
    channel_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    created_by: Optional[UUID] = None


class AllocationRuleList(BaseModel):
    """List response for allocation rules."""
    items: List[AllocationRuleResponse]
    total: int


# ==================== Serviceability Check ====================

class ServiceabilityCheckRequest(BaseModel):
    """Request to check if a pincode is serviceable."""
    pincode: str = Field(..., min_length=6, max_length=6)
    product_ids: Optional[List[UUID]] = Field(
        None,
        description="Products to check availability"
    )
    payment_mode: Optional[str] = Field(None, description="COD or PREPAID")
    channel_code: Optional[str] = Field(default="D2C")


class WarehouseCandidate(BaseModel):
    """A warehouse that can serve the pincode."""
    warehouse_id: UUID
    warehouse_code: str
    warehouse_name: str
    city: str
    estimated_days: Optional[int] = None
    shipping_cost: Optional[float] = None
    priority: int
    cod_available: bool
    prepaid_available: bool
    stock_available: Optional[bool] = None
    available_quantity: Optional[int] = None


class TransporterOption(BaseModel):
    """Available transporter for the route."""
    transporter_id: UUID
    transporter_code: str
    transporter_name: str
    estimated_days: Optional[int] = None
    shipping_cost: Optional[float] = None
    cod_available: bool
    prepaid_available: bool
    express_available: bool


class ServiceabilityCheckResponse(BaseModel):
    """Response for serviceability check."""
    pincode: str
    is_serviceable: bool
    message: str
    cod_available: bool = False
    prepaid_available: bool = True
    estimated_delivery_days: Optional[int] = None
    minimum_shipping_cost: Optional[float] = None

    # Warehouse options (sorted by priority)
    warehouse_options: List[WarehouseCandidate] = []

    # Transporter options
    transporter_options: List[TransporterOption] = []

    # Stock availability (if product_ids provided)
    stock_available: Optional[bool] = None


# ==================== Order Allocation ====================

class OrderAllocationRequest(BaseModel):
    """Request to allocate warehouse for an order."""
    order_id: UUID
    customer_pincode: str = Field(..., min_length=6, max_length=6)
    channel_code: Optional[str] = Field(default="D2C")
    payment_mode: Optional[str] = None
    order_value: Optional[Decimal] = None
    items: Optional[List[dict]] = Field(
        None,
        description="Order items with product_id and quantity"
    )
    # Pricing engine parameters
    weight_kg: Optional[float] = Field(
        default=1.0,
        description="Total weight in kg for shipping cost calculation"
    )
    dimensions: Optional[dict] = Field(
        None,
        description="Package dimensions (length, width, height in cm)"
    )
    allocation_strategy: Optional[str] = Field(
        default="BALANCED",
        description="Carrier allocation strategy: CHEAPEST_FIRST, FASTEST_FIRST, BEST_SLA, BALANCED"
    )


class AllocationDecision(BaseModel):
    """Result of warehouse allocation."""
    order_id: UUID
    is_allocated: bool
    warehouse_id: Optional[UUID] = None
    warehouse_code: Optional[str] = None
    warehouse_name: Optional[str] = None

    # If split order
    is_split: bool = False
    split_allocations: Optional[List[dict]] = None

    # Decision info
    rule_applied: Optional[str] = None
    allocation_type: Optional[str] = None
    decision_factors: Optional[dict] = None

    # If failed
    failure_reason: Optional[str] = None
    alternatives: Optional[List[WarehouseCandidate]] = None

    # Transporter recommendation
    recommended_transporter_id: Optional[UUID] = None
    recommended_transporter_code: Optional[str] = None
    recommended_transporter_name: Optional[str] = None
    estimated_delivery_days: Optional[int] = None
    estimated_delivery_days_min: Optional[int] = None
    estimated_shipping_cost: Optional[float] = None

    # Pricing engine details
    cost_breakdown: Optional[dict] = Field(
        None,
        description="Detailed cost breakdown (base, fuel, COD, GST, etc.)"
    )
    rate_card_id: Optional[str] = None
    rate_card_code: Optional[str] = None
    allocation_score: Optional[float] = None
    segment: Optional[str] = Field(
        None,
        description="Logistics segment: D2C, B2B, or FTL"
    )
    zone: Optional[str] = Field(
        None,
        description="Delivery zone (A-F)"
    )
    allocation_strategy: Optional[str] = None
    alternative_carriers: Optional[List[dict]] = Field(
        None,
        description="Alternative carrier options with costs"
    )


class AllocationLogResponse(BaseResponseSchema):
    """Response for allocation log entry."""
    id: UUID
    order_id: UUID
    rule_id: Optional[UUID] = None
    warehouse_id: Optional[UUID] = None
    customer_pincode: str
    is_successful: bool
    failure_reason: Optional[str] = None
    decision_factors: Optional[str] = None
    candidates_considered: Optional[str] = None
    created_at: datetime


# ==================== Bulk Operations ====================

class BulkPincodeUploadRequest(BaseModel):
    """Request to upload pincodes in bulk for a warehouse."""
    warehouse_id: UUID
    pincodes: List[dict] = Field(
        ...,
        description="List of pincode objects with optional fields",
        example=[
            {"pincode": "400001", "city": "Mumbai", "state": "Maharashtra"},
            {"pincode": "400002", "city": "Mumbai", "state": "Maharashtra"}
        ]
    )
    default_estimated_days: int = Field(default=3, ge=1, le=30)
    default_cod_available: bool = True


class BulkPincodeUploadResponse(BaseModel):
    """Response for bulk pincode upload."""
    warehouse_id: UUID
    total_uploaded: int
    successful: int
    failed: int
    errors: List[dict] = []


class PincodeRangeRequest(BaseModel):
    """Request to add a range of pincodes."""
    warehouse_id: UUID
    start_pincode: str = Field(..., min_length=6, max_length=6)
    end_pincode: str = Field(..., min_length=6, max_length=6)
    cod_available: bool = True
    prepaid_available: bool = True
    estimated_days: Optional[int] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zone: Optional[str] = None


# ==================== Dashboard/Stats ====================

class ServiceabilityDashboard(BaseModel):
    """Dashboard stats for serviceability."""
    total_warehouses: int
    total_pincodes_covered: int
    total_allocation_rules: int

    # By warehouse
    warehouse_coverage: List[dict] = Field(
        default=[],
        description="Pincodes per warehouse"
    )

    # By zone
    zone_coverage: dict = Field(
        default={},
        description="Pincodes by zone (LOCAL, REGIONAL, etc.)"
    )

    # Allocation stats
    recent_allocations: int
    successful_allocations: int
    failed_allocations: int
    allocation_success_rate: float
