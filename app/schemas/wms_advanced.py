"""
Pydantic schemas for Advanced WMS - Phase 2: Wave Picking & Task Interleaving.
"""
import uuid
from datetime import datetime, time, date
from decimal import Decimal
from typing import Optional, List, Dict, Any
from enum import Enum

from pydantic import BaseModel, Field, ConfigDict


# ============================================================================
# ENUMS
# ============================================================================

class WaveType(str, Enum):
    CARRIER_CUTOFF = "CARRIER_CUTOFF"
    PRIORITY = "PRIORITY"
    ZONE = "ZONE"
    PRODUCT = "PRODUCT"
    CHANNEL = "CHANNEL"
    CUSTOMER = "CUSTOMER"
    CUSTOM = "CUSTOM"


class WaveStatus(str, Enum):
    DRAFT = "DRAFT"
    PLANNED = "PLANNED"
    RELEASED = "RELEASED"
    IN_PROGRESS = "IN_PROGRESS"
    PARTIALLY_COMPLETE = "PARTIALLY_COMPLETE"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class TaskType(str, Enum):
    PICK = "PICK"
    PUTAWAY = "PUTAWAY"
    REPLENISH = "REPLENISH"
    CYCLE_COUNT = "CYCLE_COUNT"
    TRANSFER = "TRANSFER"
    RELOCATE = "RELOCATE"
    AUDIT = "AUDIT"
    PACK = "PACK"
    LOAD = "LOAD"


class TaskStatus(str, Enum):
    PENDING = "PENDING"
    ASSIGNED = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class TaskPriority(str, Enum):
    URGENT = "URGENT"
    HIGH = "HIGH"
    NORMAL = "NORMAL"
    LOW = "LOW"


class SlotClass(str, Enum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"


class CrossDockType(str, Enum):
    FLOW_THROUGH = "FLOW_THROUGH"
    MERGE_IN_TRANSIT = "MERGE_IN_TRANSIT"
    BREAK_BULK = "BREAK_BULK"
    OPPORTUNISTIC = "OPPORTUNISTIC"


# ============================================================================
# WAVE SCHEMAS
# ============================================================================

class WaveConfigBase(BaseModel):
    """Base configuration for wave creation."""
    wave_type: WaveType = WaveType.CARRIER_CUTOFF
    name: Optional[str] = None
    carrier_id: Optional[uuid.UUID] = None
    cutoff_time: Optional[time] = None
    cutoff_date: Optional[date] = None
    zone_ids: Optional[List[uuid.UUID]] = None
    channel_ids: Optional[List[uuid.UUID]] = None
    customer_types: Optional[List[str]] = None
    min_priority: Optional[int] = Field(None, ge=1, le=10)
    max_priority: Optional[int] = Field(None, ge=1, le=10)
    optimize_route: bool = True
    group_by_zone: bool = True
    max_picks_per_trip: Optional[int] = Field(None, ge=1)
    max_weight_per_trip: Optional[Decimal] = None


class WaveCreate(WaveConfigBase):
    """Create a new picking wave."""
    warehouse_id: uuid.UUID
    order_ids: Optional[List[uuid.UUID]] = Field(
        None,
        description="Specific orders to include (if not auto-selecting)"
    )
    auto_select_orders: bool = Field(
        True,
        description="Auto-select eligible orders based on config"
    )
    auto_release: bool = Field(
        False,
        description="Immediately release wave after creation"
    )


class WaveUpdate(BaseModel):
    """Update wave configuration."""
    name: Optional[str] = None
    cutoff_time: Optional[time] = None
    cutoff_date: Optional[date] = None
    optimize_route: Optional[bool] = None
    group_by_zone: Optional[bool] = None
    max_picks_per_trip: Optional[int] = None
    max_weight_per_trip: Optional[Decimal] = None
    notes: Optional[str] = None


class WavePicklistInfo(BaseModel):
    """Picklist info within a wave."""
    model_config = ConfigDict(from_attributes=True)

    picklist_id: uuid.UUID
    picklist_number: str
    sequence: int
    status: str
    total_items: int
    picked_items: int
    assigned_to: Optional[uuid.UUID] = None
    zone_id: Optional[uuid.UUID] = None


class WaveResponse(BaseModel):
    """Wave response with full details."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    wave_number: str
    name: Optional[str] = None
    warehouse_id: uuid.UUID
    wave_type: str
    status: str
    carrier_id: Optional[uuid.UUID] = None
    cutoff_time: Optional[time] = None
    cutoff_date: Optional[date] = None

    # Metrics
    total_orders: int
    total_picklists: int
    total_items: int
    total_quantity: int
    completed_picklists: int
    picked_quantity: int
    progress_percentage: float = 0.0

    # Settings
    optimize_route: bool
    group_by_zone: bool
    max_picks_per_trip: Optional[int] = None

    # Timestamps
    created_at: datetime
    released_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Status flags
    is_past_cutoff: bool = False


class WaveListResponse(BaseModel):
    """Paginated wave list."""
    items: List[WaveResponse]
    total: int
    page: int
    size: int
    pages: int


class WaveReleaseRequest(BaseModel):
    """Request to release a wave."""
    assign_pickers: Optional[List[uuid.UUID]] = Field(
        None,
        description="Picker user IDs to assign"
    )
    notify_pickers: bool = True


class WaveReleaseResponse(BaseModel):
    """Response after releasing a wave."""
    wave_id: uuid.UUID
    wave_number: str
    status: str
    picklists_created: int
    tasks_created: int
    pickers_assigned: int
    released_at: datetime


# ============================================================================
# TASK SCHEMAS
# ============================================================================

class TaskCreate(BaseModel):
    """Create a warehouse task."""
    task_type: TaskType
    warehouse_id: uuid.UUID
    priority: TaskPriority = TaskPriority.NORMAL

    # Location
    zone_id: Optional[uuid.UUID] = None
    source_bin_id: Optional[uuid.UUID] = None
    destination_bin_id: Optional[uuid.UUID] = None

    # Product (for item-specific tasks)
    product_id: Optional[uuid.UUID] = None
    variant_id: Optional[uuid.UUID] = None
    sku: Optional[str] = None
    quantity_required: int = 1

    # References
    wave_id: Optional[uuid.UUID] = None
    picklist_id: Optional[uuid.UUID] = None
    grn_id: Optional[uuid.UUID] = None
    cross_dock_id: Optional[uuid.UUID] = None

    # Assignment
    assigned_to: Optional[uuid.UUID] = None
    equipment_type: Optional[str] = None

    # SLA
    due_at: Optional[datetime] = None

    # Notes
    instruction: Optional[str] = None
    notes: Optional[str] = None


class TaskUpdate(BaseModel):
    """Update task details."""
    priority: Optional[TaskPriority] = None
    assigned_to: Optional[uuid.UUID] = None
    destination_bin_id: Optional[uuid.UUID] = None
    due_at: Optional[datetime] = None
    instruction: Optional[str] = None
    notes: Optional[str] = None


class TaskStartRequest(BaseModel):
    """Request to start a task."""
    equipment_type: Optional[str] = None
    equipment_id: Optional[str] = None


class TaskCompleteRequest(BaseModel):
    """Request to complete a task."""
    quantity_completed: int
    quantity_exception: int = 0
    exception_reason: Optional[str] = None
    picked_serials: Optional[List[str]] = None
    destination_bin_id: Optional[uuid.UUID] = None
    notes: Optional[str] = None


class TaskResponse(BaseModel):
    """Task response with full details."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    task_number: str
    task_type: str
    status: str
    priority: str

    # Location
    warehouse_id: uuid.UUID
    zone_id: Optional[uuid.UUID] = None
    source_bin_id: Optional[uuid.UUID] = None
    source_bin_code: Optional[str] = None
    destination_bin_id: Optional[uuid.UUID] = None
    destination_bin_code: Optional[str] = None

    # Product
    product_id: Optional[uuid.UUID] = None
    sku: Optional[str] = None
    product_name: Optional[str] = None

    # Quantities
    quantity_required: int
    quantity_completed: int
    quantity_exception: int

    # References
    wave_id: Optional[uuid.UUID] = None
    picklist_id: Optional[uuid.UUID] = None

    # Assignment
    assigned_to: Optional[uuid.UUID] = None
    assigned_at: Optional[datetime] = None

    # SLA
    due_at: Optional[datetime] = None
    is_overdue: bool = False

    # Timestamps
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Performance
    travel_time_seconds: Optional[int] = None
    execution_time_seconds: Optional[int] = None
    efficiency_score: Optional[float] = None

    # Notes
    instruction: Optional[str] = None
    notes: Optional[str] = None


class TaskListResponse(BaseModel):
    """Paginated task list."""
    items: List[TaskResponse]
    total: int
    page: int
    size: int
    pages: int


class NextTaskRequest(BaseModel):
    """Request for next interleaved task."""
    worker_id: uuid.UUID
    current_bin_code: Optional[str] = None
    current_zone_id: Optional[uuid.UUID] = None
    equipment_type: Optional[str] = None
    task_types: Optional[List[TaskType]] = Field(
        None,
        description="Filter by task types (default: all)"
    )


class NextTaskResponse(BaseModel):
    """Response with optimally interleaved next task."""
    task: Optional[TaskResponse] = None
    travel_distance_meters: Optional[int] = None
    estimated_travel_time_seconds: Optional[int] = None
    reason: str = Field(
        ...,
        description="Why this task was selected"
    )
    alternative_tasks: Optional[List[TaskResponse]] = None


# ============================================================================
# SLOT OPTIMIZATION SCHEMAS
# ============================================================================

class SlotScoreResponse(BaseModel):
    """Slot optimization score for a product."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    product_id: uuid.UUID
    sku: str
    warehouse_id: uuid.UUID

    # Classification
    velocity_class: str
    pick_frequency: int
    pick_quantity: int

    # Scores
    velocity_score: Decimal
    affinity_score: Decimal
    ergonomic_score: Decimal
    seasonality_score: Decimal
    total_score: Decimal

    # Current vs Recommended
    current_bin_id: Optional[uuid.UUID] = None
    recommended_bin_id: Optional[uuid.UUID] = None
    needs_relocation: bool = False
    relocation_priority: Optional[int] = None
    relocation_reason: Optional[str] = None

    # Analysis
    analysis_start: Optional[date] = None
    analysis_end: Optional[date] = None
    last_analyzed_at: Optional[datetime] = None


class SlotOptimizationRequest(BaseModel):
    """Request to run slot optimization."""
    warehouse_id: uuid.UUID
    analysis_days: int = Field(30, ge=7, le=365)
    include_categories: Optional[List[uuid.UUID]] = None
    exclude_categories: Optional[List[uuid.UUID]] = None
    min_picks_threshold: int = Field(5, ge=1)
    abc_thresholds: Optional[Dict[str, float]] = Field(
        None,
        description="Custom ABC thresholds e.g., {'A': 0.8, 'B': 0.95}"
    )


class SlotOptimizationResult(BaseModel):
    """Result of slot optimization analysis."""
    warehouse_id: uuid.UUID
    analysis_period_days: int
    total_products_analyzed: int
    products_needing_relocation: int

    # ABC Distribution
    class_a_count: int
    class_b_count: int
    class_c_count: int
    class_d_count: int

    # Recommendations
    high_priority_relocations: List[SlotScoreResponse]
    estimated_pick_time_reduction_percent: float

    analyzed_at: datetime


class RelocationTaskCreate(BaseModel):
    """Create relocation tasks from optimization."""
    slot_score_ids: List[uuid.UUID]
    priority: TaskPriority = TaskPriority.LOW
    schedule_for: Optional[datetime] = None


# ============================================================================
# CROSS-DOCK SCHEMAS
# ============================================================================

class CrossDockCreate(BaseModel):
    """Create a cross-dock workflow."""
    warehouse_id: uuid.UUID
    cross_dock_type: CrossDockType = CrossDockType.FLOW_THROUGH

    # Inbound
    inbound_grn_id: Optional[uuid.UUID] = None
    inbound_po_id: Optional[uuid.UUID] = None
    inbound_dock: Optional[str] = None
    expected_arrival: Optional[datetime] = None

    # Outbound
    outbound_order_ids: Optional[List[uuid.UUID]] = None
    outbound_dock: Optional[str] = None
    scheduled_departure: Optional[datetime] = None

    # Items
    items: Optional[List[Dict[str, Any]]] = None

    notes: Optional[str] = None


class CrossDockResponse(BaseModel):
    """Cross-dock workflow response."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    cross_dock_number: str
    cross_dock_type: str
    status: str
    warehouse_id: uuid.UUID

    # Inbound
    inbound_grn_id: Optional[uuid.UUID] = None
    inbound_dock: Optional[str] = None
    expected_arrival: Optional[datetime] = None
    actual_arrival: Optional[datetime] = None

    # Outbound
    outbound_order_ids: Optional[List[uuid.UUID]] = None
    outbound_dock: Optional[str] = None
    scheduled_departure: Optional[datetime] = None
    actual_departure: Optional[datetime] = None

    # Progress
    total_quantity: int
    processed_quantity: int
    is_complete: bool = False

    # Timestamps
    created_at: datetime
    completed_at: Optional[datetime] = None


# ============================================================================
# WORKER LOCATION SCHEMAS
# ============================================================================

class WorkerLocationUpdate(BaseModel):
    """Update worker location (from RF scan)."""
    warehouse_id: uuid.UUID
    bin_code: Optional[str] = None
    zone_id: Optional[uuid.UUID] = None
    equipment_type: Optional[str] = None
    equipment_id: Optional[str] = None


class WorkerLocationResponse(BaseModel):
    """Worker location and status."""
    model_config = ConfigDict(from_attributes=True)

    user_id: uuid.UUID
    warehouse_id: uuid.UUID
    current_zone_id: Optional[uuid.UUID] = None
    current_bin_code: Optional[str] = None
    current_task_id: Optional[uuid.UUID] = None

    is_active: bool
    is_on_break: bool

    # Today's performance
    tasks_completed_today: int
    items_picked_today: int
    distance_traveled_meters: int

    last_scan_at: datetime


# ============================================================================
# STATISTICS SCHEMAS
# ============================================================================

class WaveStats(BaseModel):
    """Wave picking statistics."""
    total_waves_today: int
    waves_in_progress: int
    waves_completed: int
    waves_past_cutoff: int

    total_orders_in_waves: int
    total_items_to_pick: int
    total_items_picked: int

    average_wave_completion_minutes: Optional[float] = None
    on_time_completion_rate: float


class TaskInterleavingStats(BaseModel):
    """Task interleaving performance stats."""
    total_tasks_today: int
    tasks_by_type: Dict[str, int]
    tasks_completed: int
    tasks_in_progress: int

    # Efficiency metrics
    average_travel_time_seconds: Optional[float] = None
    average_execution_time_seconds: Optional[float] = None
    average_efficiency_score: Optional[float] = None

    # Worker metrics
    active_workers: int
    tasks_per_worker_avg: float


class WMSAdvancedStats(BaseModel):
    """Combined advanced WMS statistics."""
    wave_stats: WaveStats
    task_stats: TaskInterleavingStats

    # Slot optimization
    products_needing_relocation: int
    pending_relocation_tasks: int

    # Cross-dock
    active_cross_docks: int
    cross_docks_completed_today: int
