"""
Distributed Order Management (DOM) Schemas.

Pydantic models for DOM API request/response validation.
"""
from datetime import datetime, date
from decimal import Decimal
from enum import Enum
from typing import Optional, List, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


# ============================================================================
# ENUMS
# ============================================================================

class FulfillmentNodeType(str, Enum):
    WAREHOUSE = "WAREHOUSE"
    STORE = "STORE"
    DEALER = "DEALER"
    THIRD_PARTY_LOGISTICS = "3PL"
    DROPSHIP = "DROPSHIP"
    VIRTUAL = "VIRTUAL"


class RoutingStrategy(str, Enum):
    NEAREST = "NEAREST"
    CHEAPEST = "CHEAPEST"
    FASTEST = "FASTEST"
    SPECIFIC_NODE = "SPECIFIC_NODE"
    ROUND_ROBIN = "ROUND_ROBIN"
    INVENTORY_PRIORITY = "INVENTORY"
    FIFO = "FIFO"
    COST_OPTIMIZED = "COST_OPTIMIZED"


class SplitReason(str, Enum):
    INVENTORY_SHORTAGE = "INVENTORY_SHORTAGE"
    COST_OPTIMIZATION = "COST_OPTIMIZATION"
    SLA_REQUIREMENT = "SLA_REQUIREMENT"
    CHANNEL_ROUTING = "CHANNEL_ROUTING"
    MANUAL_SPLIT = "MANUAL_SPLIT"


class BackorderStatus(str, Enum):
    PENDING = "PENDING"
    PARTIALLY_AVAILABLE = "PARTIALLY_AVAILABLE"
    AVAILABLE = "AVAILABLE"
    ALLOCATED = "ALLOCATED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


class PreorderStatus(str, Enum):
    ACTIVE = "ACTIVE"
    READY = "READY"
    CONVERTED = "CONVERTED"
    CANCELLED = "CANCELLED"
    REFUNDED = "REFUNDED"


class OrchestrationStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    ROUTED = "ROUTED"
    SPLIT = "SPLIT"
    BACKORDER = "BACKORDER"
    FAILED = "FAILED"
    MANUAL_REQUIRED = "MANUAL_REQUIRED"


# ============================================================================
# FULFILLMENT NODE SCHEMAS
# ============================================================================

class FulfillmentNodeBase(BaseModel):
    """Base schema for fulfillment node."""
    node_code: str = Field(..., min_length=1, max_length=50)
    node_name: str = Field(..., min_length=1, max_length=200)
    node_type: FulfillmentNodeType

    # References
    warehouse_id: Optional[UUID] = None
    dealer_id: Optional[UUID] = None
    external_reference: Optional[str] = None

    # Location
    region_id: Optional[UUID] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    pincode: Optional[str] = Field(None, max_length=10)
    city: Optional[str] = Field(None, max_length=100)
    state: Optional[str] = Field(None, max_length=100)

    # Capabilities
    can_fulfill_b2c: bool = True
    can_fulfill_b2b: bool = True
    supports_cod: bool = True
    supports_prepaid: bool = True
    supports_bopis: bool = False
    supports_boris: bool = False
    supports_ship_from_store: bool = False
    supports_same_day: bool = False
    supports_next_day: bool = True

    # Capacity
    daily_order_capacity: int = Field(1000, ge=0)
    max_concurrent_picks: int = Field(50, ge=0)

    # Priority
    priority: int = Field(100, ge=0)

    # Operating config
    operating_hours: Optional[Dict[str, Any]] = None
    cutoff_times: Optional[Dict[str, Any]] = None

    # Status
    is_active: bool = True
    is_accepting_orders: bool = True


class FulfillmentNodeCreate(FulfillmentNodeBase):
    """Schema for creating fulfillment node."""
    pass


class FulfillmentNodeUpdate(BaseModel):
    """Schema for updating fulfillment node."""
    node_name: Optional[str] = Field(None, min_length=1, max_length=200)
    region_id: Optional[UUID] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    pincode: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None

    can_fulfill_b2c: Optional[bool] = None
    can_fulfill_b2b: Optional[bool] = None
    supports_cod: Optional[bool] = None
    supports_prepaid: Optional[bool] = None
    supports_bopis: Optional[bool] = None
    supports_boris: Optional[bool] = None
    supports_ship_from_store: Optional[bool] = None
    supports_same_day: Optional[bool] = None
    supports_next_day: Optional[bool] = None

    daily_order_capacity: Optional[int] = None
    max_concurrent_picks: Optional[int] = None
    priority: Optional[int] = None

    operating_hours: Optional[Dict[str, Any]] = None
    cutoff_times: Optional[Dict[str, Any]] = None

    is_active: Optional[bool] = None
    is_accepting_orders: Optional[bool] = None


class FulfillmentNodeResponse(FulfillmentNodeBase):
    """Schema for fulfillment node response."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    current_day_orders: int = 0
    fulfillment_score: float = 100.0
    created_at: datetime
    updated_at: datetime


class FulfillmentNodeListResponse(BaseModel):
    """Paginated list of fulfillment nodes."""
    items: List[FulfillmentNodeResponse]
    total: int
    page: int
    size: int
    pages: int


# ============================================================================
# ROUTING RULE SCHEMAS
# ============================================================================

class RoutingRuleBase(BaseModel):
    """Base schema for routing rule."""
    rule_name: str = Field(..., min_length=1, max_length=200)
    rule_code: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = None
    priority: int = Field(100, ge=0)

    # Conditions
    channel_id: Optional[UUID] = None
    channel_codes: Optional[List[str]] = None
    region_id: Optional[UUID] = None
    pincode_patterns: Optional[List[str]] = None
    product_category_id: Optional[UUID] = None
    product_ids: Optional[List[UUID]] = None
    brand_ids: Optional[List[UUID]] = None
    min_order_value: Optional[Decimal] = None
    max_order_value: Optional[Decimal] = None
    payment_methods: Optional[List[str]] = None
    customer_segments: Optional[List[str]] = None

    # Actions
    routing_strategy: RoutingStrategy = RoutingStrategy.NEAREST
    target_node_id: Optional[UUID] = None
    preferred_node_ids: Optional[List[UUID]] = None
    excluded_node_ids: Optional[List[UUID]] = None

    # Split config
    allow_split: bool = True
    max_splits: int = Field(3, ge=1, le=10)
    min_split_value: Optional[Decimal] = None

    # SLA
    max_delivery_days: Optional[int] = None

    # Backorder config
    allow_backorder: bool = False
    max_backorder_days: int = Field(7, ge=1)

    # Status
    is_active: bool = True
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None


class RoutingRuleCreate(RoutingRuleBase):
    """Schema for creating routing rule."""
    pass


class RoutingRuleUpdate(BaseModel):
    """Schema for updating routing rule."""
    rule_name: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[int] = None

    channel_id: Optional[UUID] = None
    channel_codes: Optional[List[str]] = None
    region_id: Optional[UUID] = None
    pincode_patterns: Optional[List[str]] = None
    product_category_id: Optional[UUID] = None
    product_ids: Optional[List[UUID]] = None
    brand_ids: Optional[List[UUID]] = None
    min_order_value: Optional[Decimal] = None
    max_order_value: Optional[Decimal] = None
    payment_methods: Optional[List[str]] = None
    customer_segments: Optional[List[str]] = None

    routing_strategy: Optional[RoutingStrategy] = None
    target_node_id: Optional[UUID] = None
    preferred_node_ids: Optional[List[UUID]] = None
    excluded_node_ids: Optional[List[UUID]] = None

    allow_split: Optional[bool] = None
    max_splits: Optional[int] = None
    min_split_value: Optional[Decimal] = None

    max_delivery_days: Optional[int] = None
    allow_backorder: Optional[bool] = None
    max_backorder_days: Optional[int] = None

    is_active: Optional[bool] = None
    valid_from: Optional[datetime] = None
    valid_until: Optional[datetime] = None


class RoutingRuleResponse(RoutingRuleBase):
    """Schema for routing rule response."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_by: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime


class RoutingRuleListResponse(BaseModel):
    """Paginated list of routing rules."""
    items: List[RoutingRuleResponse]
    total: int
    page: int
    size: int
    pages: int


# ============================================================================
# ORDER ORCHESTRATION SCHEMAS
# ============================================================================

class OrchestrationRequest(BaseModel):
    """Request to orchestrate an order."""
    order_id: UUID
    force_node_id: Optional[UUID] = Field(None, description="Force allocation to specific node")
    allow_split: Optional[bool] = Field(None, description="Override split setting")
    allow_backorder: Optional[bool] = Field(None, description="Override backorder setting")
    dry_run: bool = Field(False, description="Simulate without making changes")


class NodeScore(BaseModel):
    """Score breakdown for a fulfillment node."""
    node_id: UUID
    node_code: str
    node_name: str
    total_score: float

    # Score components
    distance_score: float = 0.0
    cost_score: float = 0.0
    sla_score: float = 0.0
    inventory_score: float = 0.0
    capacity_score: float = 0.0

    # Availability
    available_quantity: int = 0
    can_fulfill_complete: bool = False

    # Estimated values
    estimated_shipping_cost: Optional[Decimal] = None
    estimated_delivery_days: Optional[int] = None


class SplitDecision(BaseModel):
    """Decision for order split."""
    node_id: UUID
    node_code: str
    item_ids: List[UUID]
    quantity_map: Dict[str, int]  # product_id -> quantity
    subtotal: Decimal
    estimated_shipping: Decimal


class OrchestrationResult(BaseModel):
    """Result of order orchestration."""
    order_id: UUID
    order_number: str
    status: OrchestrationStatus

    # Selected node (if single fulfillment)
    selected_node_id: Optional[UUID] = None
    selected_node_code: Optional[str] = None

    # Split decisions (if order was split)
    splits: List[SplitDecision] = []
    split_count: int = 0

    # Routing details
    routing_rule_id: Optional[UUID] = None
    routing_rule_name: Optional[str] = None
    routing_strategy: str

    # Node evaluation
    evaluated_nodes: List[NodeScore] = []

    # Decision factors
    decision_factors: Dict[str, Any] = {}

    # If backorder
    backorder_items: List[UUID] = []

    # If failed
    failure_reason: Optional[str] = None

    # Processing
    processing_time_ms: int = 0
    is_dry_run: bool = False


class BulkOrchestrationRequest(BaseModel):
    """Request to orchestrate multiple orders."""
    order_ids: List[UUID]
    allow_split: Optional[bool] = None
    allow_backorder: Optional[bool] = None
    dry_run: bool = False


class BulkOrchestrationResponse(BaseModel):
    """Response for bulk orchestration."""
    total_orders: int
    successful: int
    failed: int
    results: List[OrchestrationResult]


# ============================================================================
# ORDER SPLIT SCHEMAS
# ============================================================================

class OrderSplitCreate(BaseModel):
    """Request to manually split an order."""
    order_id: UUID
    splits: List[SplitDecision]
    reason: SplitReason = SplitReason.MANUAL_SPLIT


class OrderSplitResponse(BaseModel):
    """Response for order split."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    parent_order_id: UUID
    child_order_id: UUID
    split_number: int
    split_reason: str
    fulfillment_node_id: Optional[UUID] = None
    split_subtotal: Decimal
    split_shipping: Decimal
    split_total: Decimal
    item_ids: List[UUID]
    created_at: datetime


# ============================================================================
# BACKORDER SCHEMAS
# ============================================================================

class BackorderCreate(BaseModel):
    """Request to create backorder."""
    order_id: UUID
    order_item_id: UUID
    product_id: UUID
    variant_id: Optional[UUID] = None
    quantity_ordered: int = Field(..., gt=0)
    expected_date: Optional[date] = None
    customer_consent: bool = True
    priority: int = Field(100, ge=0)


class BackorderUpdate(BaseModel):
    """Request to update backorder."""
    status: Optional[BackorderStatus] = None
    expected_date: Optional[date] = None
    customer_notified: Optional[bool] = None
    priority: Optional[int] = None
    cancellation_reason: Optional[str] = None


class BackorderResponse(BaseModel):
    """Backorder response."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    order_id: UUID
    order_item_id: UUID
    product_id: UUID
    variant_id: Optional[UUID] = None
    quantity_ordered: int
    quantity_available: int
    quantity_allocated: int
    status: str
    expected_date: Optional[date] = None
    customer_notified: bool
    customer_consent: bool
    priority: int
    created_at: datetime
    updated_at: datetime
    available_at: Optional[datetime] = None
    allocated_at: Optional[datetime] = None


class BackorderListResponse(BaseModel):
    """Paginated list of backorders."""
    items: List[BackorderResponse]
    total: int
    page: int
    size: int
    pages: int


class BackorderAllocateRequest(BaseModel):
    """Request to allocate inventory to backorders."""
    product_id: UUID
    variant_id: Optional[UUID] = None
    quantity: int = Field(..., gt=0)
    fulfillment_node_id: Optional[UUID] = None


class BackorderAllocateResponse(BaseModel):
    """Response for backorder allocation."""
    total_allocated: int
    backorders_fulfilled: int
    backorders_partial: int
    allocations: List[Dict[str, Any]]


# ============================================================================
# PREORDER SCHEMAS
# ============================================================================

class PreorderCreate(BaseModel):
    """Request to create pre-order."""
    product_id: UUID
    variant_id: Optional[UUID] = None
    customer_id: UUID
    quantity: int = Field(1, gt=0)
    unit_price: Decimal
    deposit_required: bool = False
    deposit_percentage: Optional[float] = Field(None, ge=0, le=100)
    expected_release_date: Optional[date] = None
    channel_id: Optional[UUID] = None
    source: str = "WEBSITE"


class PreorderUpdate(BaseModel):
    """Request to update pre-order."""
    quantity: Optional[int] = Field(None, gt=0)
    expected_release_date: Optional[date] = None
    status: Optional[PreorderStatus] = None
    cancellation_reason: Optional[str] = None


class PreorderResponse(BaseModel):
    """Pre-order response."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    preorder_number: str
    product_id: UUID
    variant_id: Optional[UUID] = None
    customer_id: UUID
    quantity: int
    unit_price: Decimal
    total_amount: Decimal
    deposit_required: bool
    deposit_percentage: Optional[float] = None
    deposit_amount: Decimal
    deposit_paid: bool
    expected_release_date: Optional[date] = None
    actual_release_date: Optional[date] = None
    status: str
    converted_order_id: Optional[UUID] = None
    queue_position: int
    channel_id: Optional[UUID] = None
    source: str
    created_at: datetime
    updated_at: datetime


class PreorderListResponse(BaseModel):
    """Paginated list of pre-orders."""
    items: List[PreorderResponse]
    total: int
    page: int
    size: int
    pages: int


class PreorderConvertRequest(BaseModel):
    """Request to convert pre-order to order."""
    preorder_id: UUID
    shipping_address_id: Optional[UUID] = None
    payment_method: Optional[str] = None


class PreorderConvertResponse(BaseModel):
    """Response for pre-order conversion."""
    preorder_id: UUID
    order_id: UUID
    order_number: str
    remaining_amount: Decimal


# ============================================================================
# GLOBAL INVENTORY SCHEMAS
# ============================================================================

class GlobalInventoryQuery(BaseModel):
    """Query for global inventory."""
    product_ids: Optional[List[UUID]] = None
    skus: Optional[List[str]] = None
    fulfillment_node_ids: Optional[List[UUID]] = None
    include_zero_stock: bool = False


class GlobalInventoryItem(BaseModel):
    """Global inventory item."""
    model_config = ConfigDict(from_attributes=True)

    product_id: UUID
    variant_id: Optional[UUID] = None
    sku: str
    fulfillment_node_id: UUID
    node_code: Optional[str] = None
    node_name: Optional[str] = None

    total_quantity: int
    available_quantity: int
    reserved_quantity: int
    allocated_quantity: int
    in_transit_quantity: int
    backorder_quantity: int

    atp: int  # Available to Promise
    atf: int  # Available to Fulfill

    safety_stock: int
    reorder_point: int
    is_in_stock: bool
    is_low_stock: bool

    last_updated: datetime


class GlobalInventoryResponse(BaseModel):
    """Global inventory response."""
    items: List[GlobalInventoryItem]
    total_atp: int
    total_atf: int
    nodes_with_stock: int


class ATPCheckRequest(BaseModel):
    """Request to check ATP for products."""
    items: List[Dict[str, Any]]  # [{product_id, variant_id, quantity}]
    customer_pincode: Optional[str] = None
    channel_code: Optional[str] = None


class ATPCheckItem(BaseModel):
    """ATP check result for a single item."""
    product_id: UUID
    variant_id: Optional[UUID] = None
    requested_quantity: int
    total_atp: int
    is_available: bool
    available_nodes: List[Dict[str, Any]]  # [{node_id, node_code, atp}]
    best_node_id: Optional[UUID] = None
    best_node_code: Optional[str] = None


class ATPCheckResponse(BaseModel):
    """ATP check response."""
    all_available: bool
    items: List[ATPCheckItem]
    recommended_node_id: Optional[UUID] = None
    recommended_node_code: Optional[str] = None
    requires_split: bool = False


# ============================================================================
# ORCHESTRATION LOG SCHEMAS
# ============================================================================

class OrchestrationLogResponse(BaseModel):
    """Orchestration log response."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    order_id: UUID
    order_number: str
    status: str
    routing_rule_id: Optional[UUID] = None
    routing_rule_name: Optional[str] = None
    routing_strategy: str
    selected_node_id: Optional[UUID] = None
    selected_node_code: Optional[str] = None
    split_count: int
    evaluated_nodes: Optional[List[Dict[str, Any]]] = None
    decision_factors: Optional[Dict[str, Any]] = None
    failure_reason: Optional[str] = None
    processing_time_ms: Optional[int] = None
    created_at: datetime


class OrchestrationLogListResponse(BaseModel):
    """Paginated list of orchestration logs."""
    items: List[OrchestrationLogResponse]
    total: int
    page: int
    size: int
    pages: int


# ============================================================================
# STATS SCHEMAS
# ============================================================================

class DOMStats(BaseModel):
    """DOM statistics."""
    total_fulfillment_nodes: int
    active_fulfillment_nodes: int
    total_routing_rules: int
    active_routing_rules: int

    # Today's metrics
    orders_orchestrated_today: int
    orders_split_today: int
    orders_backordered_today: int
    average_orchestration_time_ms: float

    # Pending
    pending_backorders: int
    pending_preorders: int

    # Performance
    orchestration_success_rate: float
    split_rate: float


class NodePerformanceStats(BaseModel):
    """Performance stats for a fulfillment node."""
    node_id: UUID
    node_code: str
    node_name: str

    # Volume
    orders_today: int
    orders_this_week: int
    orders_this_month: int

    # Capacity
    daily_capacity: int
    current_utilization: float

    # Performance
    fulfillment_score: float
    average_ship_time_hours: float
    sla_adherence_rate: float

    # Inventory
    total_skus: int
    low_stock_skus: int
    out_of_stock_skus: int
