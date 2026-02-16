"""
S&OP (Sales and Operations Planning) Pydantic Schemas

Request/Response schemas for:
- Demand Forecasting
- Supply Planning
- Scenario Analysis
- Inventory Optimization
- Consensus Planning
"""

from pydantic import BaseModel, Field

from app.schemas.base import BaseResponseSchema
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from decimal import Decimal
import uuid

from app.models.snop import (
    ForecastGranularity,
    ForecastLevel,
    ForecastStatus,
    ForecastAlgorithm,
    SupplyPlanStatus,
    ScenarioStatus,
    ExternalFactorType,
    DemandSignalType,
    DemandSignalStatus,
)


# ==================== FORECAST DATA SCHEMAS ====================

class ForecastDataPoint(BaseModel):
    """Individual forecast data point."""
    date: date
    forecasted_qty: Decimal
    lower_bound: Decimal
    upper_bound: Decimal


class ForecastAccuracyMetrics(BaseModel):
    """Forecast accuracy metrics."""
    mape: Optional[float] = Field(None, description="Mean Absolute Percentage Error")
    mae: Optional[float] = Field(None, description="Mean Absolute Error")
    rmse: Optional[float] = Field(None, description="Root Mean Square Error")
    forecast_bias: Optional[float] = Field(None, description="Forecast bias (positive=over, negative=under)")


# ==================== DEMAND FORECAST SCHEMAS ====================

class DemandForecastCreate(BaseModel):
    """Create a new demand forecast request."""
    forecast_name: str = Field(..., min_length=1, max_length=200)
    forecast_level: ForecastLevel = ForecastLevel.SKU
    granularity: ForecastGranularity = ForecastGranularity.WEEKLY

    # Target entities (based on forecast_level)
    product_id: Optional[uuid.UUID] = None
    category_id: Optional[uuid.UUID] = None
    warehouse_id: Optional[uuid.UUID] = None
    region_id: Optional[uuid.UUID] = None
    channel: Optional[str] = None

    # Forecast period
    forecast_start_date: date
    forecast_end_date: date
    forecast_horizon_days: int = Field(90, ge=7, le=365)

    # AI settings
    algorithm: ForecastAlgorithm = ForecastAlgorithm.ENSEMBLE
    confidence_level: float = Field(0.95, ge=0.5, le=0.99)

    # Consider external factors
    include_promotions: bool = True
    include_seasonality: bool = True
    include_weather: bool = False
    include_economic: bool = False

    notes: Optional[str] = None


class DemandForecastGenerateRequest(BaseModel):
    """Request to generate AI-powered demand forecast."""
    product_ids: Optional[List[uuid.UUID]] = Field(None, description="Specific products, or None for all")
    category_ids: Optional[List[uuid.UUID]] = Field(None, description="Specific categories")
    warehouse_ids: Optional[List[uuid.UUID]] = Field(None, description="Specific warehouses")

    forecast_level: ForecastLevel = ForecastLevel.SKU
    granularity: ForecastGranularity = ForecastGranularity.WEEKLY

    forecast_start_date: date
    forecast_horizon_days: int = Field(90, ge=7, le=365)

    # AI configuration
    algorithm: ForecastAlgorithm = ForecastAlgorithm.ENSEMBLE

    # Model parameters (optional - use defaults if not specified)
    model_params: Optional[Dict[str, Any]] = None

    # External factors to include
    external_factors: List[ExternalFactorType] = Field(
        default_factory=lambda: [ExternalFactorType.SEASONAL, ExternalFactorType.PROMOTION]
    )

    # Historical data range for training
    lookback_days: int = Field(365, ge=90, le=1095)


class DemandForecastResponse(BaseResponseSchema):
    """Demand forecast response."""
    id: uuid.UUID
    forecast_code: str
    forecast_name: str

    forecast_level: ForecastLevel
    granularity: ForecastGranularity

    # Target entities
    product_id: Optional[uuid.UUID] = None
    product_name: Optional[str] = None
    category_id: Optional[uuid.UUID] = None
    category_name: Optional[str] = None
    warehouse_id: Optional[uuid.UUID] = None
    warehouse_name: Optional[str] = None
    region_id: Optional[uuid.UUID] = None
    region_name: Optional[str] = None
    channel: Optional[str] = None

    # Period
    forecast_start_date: date
    forecast_end_date: date
    forecast_horizon_days: int

    # Forecast data
    forecast_data: List[ForecastDataPoint] = []

    # Aggregated metrics
    total_forecasted_qty: Decimal
    avg_daily_demand: Decimal
    peak_demand: Decimal

    # Model info
    algorithm_used: ForecastAlgorithm
    confidence_level: float

    # Accuracy
    accuracy_metrics: Optional[ForecastAccuracyMetrics] = None

    # Workflow
    status: str
    version: int

    # Audit
    created_by_name: Optional[str] = None
    reviewed_by_name: Optional[str] = None
    approved_by_name: Optional[str] = None
    created_at: datetime
    submitted_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None

    notes: Optional[str] = None

class DemandForecastBrief(BaseResponseSchema):
    """Brief forecast info for listings."""
    id: uuid.UUID
    forecast_code: str
    forecast_name: str
    forecast_level: ForecastLevel
    granularity: ForecastGranularity
    product_name: Optional[str] = None
    category_name: Optional[str] = None
    forecast_start_date: date
    forecast_end_date: date
    total_forecasted_qty: Decimal
    algorithm_used: ForecastAlgorithm
    status: str
    created_at: datetime
# ==================== FORECAST ADJUSTMENT SCHEMAS ====================

class ForecastAdjustmentCreate(BaseModel):
    """Create manual adjustment to forecast."""
    forecast_id: uuid.UUID
    adjustment_date: date
    adjusted_qty: Decimal = Field(..., ge=0)
    adjustment_reason: str = Field(..., min_length=1, max_length=100)
    justification: Optional[str] = None


class ForecastAdjustmentResponse(BaseResponseSchema):
    """Forecast adjustment response."""
    id: uuid.UUID
    forecast_id: uuid.UUID
    adjustment_date: date
    original_qty: Decimal
    adjusted_qty: Decimal
    adjustment_pct: float
    adjustment_reason: str
    justification: Optional[str] = None
    status: str
    adjusted_by_name: str
    approved_by_name: Optional[str] = None
    created_at: datetime
    approved_at: Optional[datetime] = None

class ForecastApprovalRequest(BaseModel):
    """Request to approve/reject a forecast or adjustment."""
    action: str = Field(..., pattern="^(approve|reject|request_changes)$")
    comments: Optional[str] = None
    auto_generate_supply_plan: bool = Field(False, description="Auto-generate supply plan on approval")


# ==================== SUPPLY PLAN SCHEMAS ====================

class SupplyPlanScheduleItem(BaseModel):
    """Individual supply schedule item."""
    date: date
    production_qty: Decimal = Field(default=Decimal("0"), ge=0)
    procurement_qty: Decimal = Field(default=Decimal("0"), ge=0)


class SupplyPlanCreate(BaseModel):
    """Create supply plan request."""
    plan_name: str = Field(..., min_length=1, max_length=200)
    forecast_id: Optional[uuid.UUID] = None

    plan_start_date: date
    plan_end_date: date

    product_id: Optional[uuid.UUID] = None
    warehouse_id: Optional[uuid.UUID] = None
    vendor_id: Optional[uuid.UUID] = None

    planned_production_qty: Decimal = Field(default=Decimal("0"), ge=0)
    planned_procurement_qty: Decimal = Field(default=Decimal("0"), ge=0)

    production_capacity: Decimal = Field(default=Decimal("0"), ge=0)
    lead_time_days: int = Field(0, ge=0)

    schedule_data: List[SupplyPlanScheduleItem] = []

    notes: Optional[str] = None


class SupplyPlanOptimizeRequest(BaseModel):
    """Request AI-optimized supply plan."""
    forecast_id: uuid.UUID
    product_ids: Optional[List[uuid.UUID]] = None
    warehouse_ids: Optional[List[uuid.UUID]] = None

    # Optimization objectives
    minimize_cost: bool = True
    maximize_service_level: bool = True
    target_service_level: float = Field(0.95, ge=0.8, le=0.99)

    # Constraints
    max_capacity_utilization: float = Field(0.9, ge=0.5, le=1.0)
    min_safety_stock_days: int = Field(7, ge=0)


class SupplyPlanResponse(BaseResponseSchema):
    """Supply plan response."""
    id: uuid.UUID
    plan_code: str
    plan_name: str

    forecast_id: Optional[uuid.UUID] = None
    forecast_name: Optional[str] = None

    plan_start_date: date
    plan_end_date: date

    product_id: Optional[uuid.UUID] = None
    product_name: Optional[str] = None
    warehouse_id: Optional[uuid.UUID] = None
    warehouse_name: Optional[str] = None
    vendor_id: Optional[uuid.UUID] = None
    vendor_name: Optional[str] = None

    planned_production_qty: Decimal
    planned_procurement_qty: Decimal
    production_capacity: Decimal
    capacity_utilization_pct: float
    lead_time_days: int

    schedule_data: List[SupplyPlanScheduleItem] = []

    status: str

    created_by_name: Optional[str] = None
    approved_by_name: Optional[str] = None
    created_at: datetime
    approved_at: Optional[datetime] = None

    notes: Optional[str] = None
# ==================== SCENARIO PLANNING SCHEMAS ====================

class ScenarioAssumptions(BaseModel):
    """Scenario planning assumptions."""
    demand_change_pct: float = Field(0.0, ge=-100, le=500)
    supply_constraint_pct: float = Field(100.0, ge=0, le=100)
    lead_time_change_pct: float = Field(0.0, ge=-50, le=200)
    price_change_pct: float = Field(0.0, ge=-50, le=100)

    # Additional parameters
    new_product_launch: bool = False
    competitor_action: Optional[str] = None
    economic_scenario: Optional[str] = None  # e.g., "recession", "growth", "stable"
    seasonal_adjustment: Optional[float] = None


class SNOPScenarioCreate(BaseModel):
    """Create what-if scenario."""
    scenario_name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None

    base_scenario_id: Optional[uuid.UUID] = None

    # Simulation period
    simulation_start_date: date
    simulation_end_date: date

    # Scenario parameters
    assumptions: ScenarioAssumptions


class SNOPScenarioRunRequest(BaseModel):
    """Request to run scenario simulation."""
    scenario_id: uuid.UUID
    include_inventory_impact: bool = True
    include_financial_impact: bool = True
    include_service_level_impact: bool = True


class ScenarioResults(BaseModel):
    """Scenario simulation results."""
    projected_revenue: Decimal
    projected_margin: Decimal
    projected_units_sold: Decimal
    stockout_probability: float
    service_level_pct: float
    inventory_turns: float
    avg_inventory_value: Decimal

    # Comparison to base
    revenue_change_pct: Optional[float] = None
    margin_change_pct: Optional[float] = None

    # Detailed breakdown
    monthly_projections: Optional[List[Dict[str, Any]]] = None


class SNOPScenarioResponse(BaseResponseSchema):
    """Scenario response."""
    id: uuid.UUID
    scenario_code: str
    scenario_name: str
    description: Optional[str] = None

    base_scenario_id: Optional[uuid.UUID] = None
    base_scenario_name: Optional[str] = None

    simulation_start_date: date
    simulation_end_date: date

    assumptions: ScenarioAssumptions

    # Results (populated after simulation)
    results: Optional[ScenarioResults] = None

    status: str

    created_by_name: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

class ScenarioCompareRequest(BaseModel):
    """Request to compare multiple scenarios."""
    scenario_ids: List[uuid.UUID] = Field(..., min_length=2, max_length=5)
    comparison_metrics: List[str] = Field(
        default_factory=lambda: ["revenue", "margin", "service_level", "stockout_risk"]
    )


class ScenarioCompareResponse(BaseModel):
    """Scenario comparison response."""
    scenarios: List[SNOPScenarioResponse]
    comparison_table: Dict[str, Dict[str, Any]]
    recommendation: Optional[str] = None


# ==================== EXTERNAL FACTOR SCHEMAS ====================

class ExternalFactorCreate(BaseModel):
    """Create external factor affecting demand."""
    factor_name: str = Field(..., min_length=1, max_length=200)
    factor_type: ExternalFactorType

    # Scope
    product_id: Optional[uuid.UUID] = None
    category_id: Optional[uuid.UUID] = None
    region_id: Optional[uuid.UUID] = None
    applies_to_all: bool = False

    # Effect period
    start_date: date
    end_date: date

    # Impact
    impact_multiplier: float = Field(1.0, ge=0.1, le=5.0)
    impact_absolute: Optional[Decimal] = None

    # Additional metadata
    metadata_json: Optional[Dict[str, Any]] = None


class ExternalFactorResponse(BaseResponseSchema):
    """External factor response."""
    id: uuid.UUID
    factor_code: str
    factor_name: str
    factor_type: ExternalFactorType

    product_id: Optional[uuid.UUID] = None
    product_name: Optional[str] = None
    category_id: Optional[uuid.UUID] = None
    category_name: Optional[str] = None
    region_id: Optional[uuid.UUID] = None
    region_name: Optional[str] = None
    applies_to_all: bool

    start_date: date
    end_date: date

    impact_multiplier: float
    impact_absolute: Optional[Decimal] = None

    is_active: bool
    created_at: datetime
# ==================== INVENTORY OPTIMIZATION SCHEMAS ====================

class InventoryOptimizationRequest(BaseModel):
    """Request inventory optimization recommendations."""
    product_ids: Optional[List[uuid.UUID]] = None
    warehouse_ids: Optional[List[uuid.UUID]] = None

    service_level_target: float = Field(0.95, ge=0.8, le=0.99)
    holding_cost_pct: float = Field(0.25, ge=0.05, le=0.5)
    ordering_cost: Decimal = Field(default=Decimal("100"), ge=0)

    # Analysis period
    analysis_start_date: Optional[date] = None
    analysis_end_date: Optional[date] = None


class InventoryOptimizationResponse(BaseResponseSchema):
    """Inventory optimization recommendations."""
    id: uuid.UUID

    product_id: uuid.UUID
    product_name: str
    product_sku: str
    warehouse_id: uuid.UUID
    warehouse_name: str

    # Current values
    current_safety_stock: Decimal
    current_reorder_point: Decimal

    # Recommended values
    recommended_safety_stock: Decimal
    recommended_reorder_point: Decimal
    recommended_order_qty: Decimal

    # Analysis inputs
    avg_daily_demand: Decimal
    demand_std_dev: Decimal
    lead_time_days: int
    service_level_target: float

    # Expected outcomes
    expected_stockout_rate: float
    expected_inventory_turns: float
    expected_holding_cost: Decimal

    # Validity
    valid_from: date
    valid_until: date

    is_applied: bool

class ApplyOptimizationRequest(BaseModel):
    """Apply inventory optimization recommendations."""
    optimization_ids: List[uuid.UUID]
    apply_safety_stock: bool = True
    apply_reorder_point: bool = True


# ==================== S&OP MEETING SCHEMAS ====================

class SNOPMeetingCreate(BaseModel):
    """Create S&OP meeting record."""
    meeting_title: str = Field(..., min_length=1, max_length=200)
    meeting_date: datetime

    planning_period_start: date
    planning_period_end: date

    participant_ids: List[uuid.UUID] = []
    agenda: Optional[str] = None
    forecasts_to_review: List[uuid.UUID] = []


class SNOPMeetingUpdate(BaseModel):
    """Update S&OP meeting with notes and decisions."""
    meeting_notes: Optional[str] = None
    decisions: Optional[Dict[str, Any]] = None
    action_items: Optional[List[Dict[str, Any]]] = None
    is_completed: bool = False


class SNOPMeetingResponse(BaseResponseSchema):
    """S&OP meeting response."""
    id: uuid.UUID
    meeting_code: str
    meeting_title: str
    meeting_date: datetime

    planning_period_start: date
    planning_period_end: date

    participants: List[Dict[str, Any]]
    agenda: Optional[str] = None
    meeting_notes: Optional[str] = None

    forecasts_reviewed: List[uuid.UUID]
    decisions: Optional[Dict[str, Any]] = None
    action_items: Optional[List[Dict[str, Any]]] = None

    is_completed: bool

    created_by_name: Optional[str] = None
    created_at: datetime
# ==================== DASHBOARD SCHEMAS ====================

class SNOPDashboardSummary(BaseModel):
    """S&OP dashboard summary."""
    # Forecast metrics (field names match frontend expectations)
    total_forecasts: int = 0
    active_forecasts: int = 0
    pending_review: int = 0
    pending_approval_count: int = 0
    forecast_accuracy: Optional[float] = None
    forecast_accuracy_avg: Optional[float] = None
    mape: Optional[float] = None

    # Demand vs Supply
    total_forecasted_demand: Decimal = Decimal("0")
    total_planned_supply: Decimal = Decimal("0")
    demand_supply_gap: Decimal = Decimal("0")
    demand_supply_gap_pct: float = 0

    # Inventory health
    inventory_health_score: Optional[float] = None
    items_below_safety: int = 0
    products_below_safety_stock: int = 0
    products_above_reorder_point: int = 0
    avg_inventory_turns: float = 0

    # Top risks
    stockout_risk_products: List[Dict[str, Any]] = []
    overstock_risk_products: List[Dict[str, Any]] = []

    # Recent activity
    recent_forecasts: List[Dict[str, Any]] = []

    # Upcoming meetings
    upcoming_meetings: List[Dict[str, Any]] = []


class ForecastAccuracyReport(BaseModel):
    """Forecast accuracy report."""
    period_start: date
    period_end: date

    overall_mape: float
    overall_mae: float
    overall_bias: float

    # By product/category
    accuracy_by_product: List[Dict[str, Any]]
    accuracy_by_category: List[Dict[str, Any]]

    # By algorithm
    accuracy_by_algorithm: Dict[str, float]

    # Trend
    accuracy_trend: List[Dict[str, Any]]


class DemandSupplyGapAnalysis(BaseModel):
    """Demand vs Supply gap analysis."""
    analysis_date: date
    horizon_days: int

    # Overall summary
    total_demand: Decimal = Decimal("0")
    total_supply: Decimal = Decimal("0")
    net_gap: Decimal = Decimal("0")
    total_gap_units: Decimal = Decimal("0")
    gap_pct: float = 0

    # By product - "gaps" for frontend, "gaps_by_product" for backward compat
    gaps: List[Dict[str, Any]] = []
    gaps_by_product: List[Dict[str, Any]] = []

    # By period
    gaps_by_period: List[Dict[str, Any]] = []

    # Recommendations
    recommendations: List[str] = []


# ==================== DEMAND SIGNAL SCHEMAS ====================

class DemandSignalCreate(BaseModel):
    """Create a demand signal."""
    signal_name: str = Field(..., min_length=1, max_length=200)
    signal_type: DemandSignalType

    # Scope
    product_id: Optional[uuid.UUID] = None
    category_id: Optional[uuid.UUID] = None
    region_id: Optional[uuid.UUID] = None
    channel: Optional[str] = None
    applies_to_all: bool = False

    # Signal characteristics
    signal_strength: float = Field(0.5, ge=0.0, le=1.0)
    impact_direction: str = Field("UP", pattern="^(UP|DOWN)$")
    impact_pct: float = Field(0.0, ge=-100, le=500)
    confidence: float = Field(0.7, ge=0.0, le=1.0)

    # Timing
    effective_start: date
    effective_end: date
    decay_rate: float = Field(0.1, ge=0.0, le=1.0)

    # Source
    source: str = Field("MANUAL", max_length=100)
    source_data: Optional[Dict[str, Any]] = None

    notes: Optional[str] = None


class DemandSignalUpdate(BaseModel):
    """Update a demand signal."""
    signal_strength: Optional[float] = Field(None, ge=0.0, le=1.0)
    impact_pct: Optional[float] = Field(None, ge=-100, le=500)
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    effective_end: Optional[date] = None
    status: Optional[DemandSignalStatus] = None
    actual_impact: Optional[float] = None
    notes: Optional[str] = None


class DemandSignalResponse(BaseModel):
    """Demand signal response."""
    id: uuid.UUID
    signal_code: str
    signal_name: str
    signal_type: str

    # Scope
    product_id: Optional[uuid.UUID] = None
    product_name: Optional[str] = None
    category_id: Optional[uuid.UUID] = None
    category_name: Optional[str] = None
    region_id: Optional[uuid.UUID] = None
    channel: Optional[str] = None
    applies_to_all: bool

    # Signal characteristics
    signal_strength: float
    current_strength: float  # After decay
    impact_direction: str
    impact_pct: float
    confidence: float

    # Timing
    detected_at: datetime
    effective_start: date
    effective_end: date
    decay_rate: float
    days_active: int
    days_remaining: int

    # Source & tracking
    source: str
    forecast_ids_affected: Optional[List[str]] = None
    actual_impact: Optional[float] = None

    # Status
    status: str

    created_at: datetime
    notes: Optional[str] = None


class DemandSensingAnalysis(BaseModel):
    """Result of demand sensing analysis."""
    analysis_date: date
    active_signals_count: int
    total_signals_count: int

    # Net impact by signal type
    impact_by_type: Dict[str, float]

    # Aggregate forecast adjustment
    net_forecast_adjustment_pct: float
    weighted_confidence: float

    # Signal timeline
    signal_timeline: List[Dict[str, Any]]

    # Top signals by strength
    top_signals: List[Dict[str, Any]]

    # Recommendations
    recommendations: List[str]


# ==================== SUPPLY OPTIMIZER SCHEMAS ====================

class SupplyOptimizeAdvancedRequest(BaseModel):
    """Request for constraint-based supply optimization."""
    forecast_id: uuid.UUID
    max_production_capacity: float = Field(1000, ge=0)
    max_budget: float = Field(1_000_000, ge=0)
    min_order_qty: float = Field(10, ge=0)
    max_lead_time_days: int = Field(30, ge=1)
    target_service_level: float = Field(0.95, ge=0.5, le=0.999)
    holding_cost_per_unit: float = Field(0.5, ge=0)
    stockout_penalty_per_unit: float = Field(50, ge=0)
    production_cost_per_unit: float = Field(100, ge=0)
    procurement_cost_per_unit: float = Field(120, ge=0)


class MultiSourceRequest(BaseModel):
    """Request for multi-source procurement analysis."""
    product_id: uuid.UUID
    required_qty: float = Field(..., ge=1)
    max_lead_time_days: int = Field(30, ge=1)


# ==================== ADVANCED SCENARIO SCHEMAS ====================

class MonteCarloRequest(BaseModel):
    """Request for Monte Carlo simulation."""
    scenario_id: uuid.UUID
    num_simulations: int = Field(1000, ge=100, le=10000)
    demand_cv: float = Field(0.15, ge=0.01, le=0.5, description="Demand coefficient of variation")
    supply_cv: float = Field(0.10, ge=0.01, le=0.5, description="Supply coefficient of variation")
    lead_time_cv: float = Field(0.20, ge=0.01, le=0.5, description="Lead time coefficient of variation")
    price_cv: float = Field(0.05, ge=0.01, le=0.3, description="Price coefficient of variation")


class FinancialPLRequest(BaseModel):
    """Request for financial P&L projection."""
    scenario_id: uuid.UUID
    avg_unit_price: float = Field(1000.0, ge=1)
    cogs_pct: float = Field(60.0, ge=10, le=95, description="COGS as % of revenue")
    operating_expense_pct: float = Field(15.0, ge=1, le=50, description="OpEx as % of revenue")
    tax_rate_pct: float = Field(25.0, ge=0, le=50)
    working_capital_days: int = Field(45, ge=0, le=180)


class SensitivityRequest(BaseModel):
    """Request for sensitivity analysis (tornado chart)."""
    scenario_id: uuid.UUID
    parameters: Optional[List[str]] = Field(
        None,
        description="Parameters to analyze. Default: demand, price, cogs, supply_capacity, lead_time, operating_expenses, holding_cost"
    )
    variation_pct: float = Field(20.0, ge=5, le=50, description="% variation to test (+/-)")


class QuickWhatIfRequest(BaseModel):
    """Request for quick what-if analysis without saving."""
    demand_change_pct: float = Field(0, ge=-100, le=500)
    price_change_pct: float = Field(0, ge=-50, le=200)
    supply_change_pct: float = Field(0, ge=-100, le=500)
    lead_time_change_pct: float = Field(0, ge=-50, le=200)
    cogs_change_pct: float = Field(0, ge=-50, le=100)


class ScenarioCompareAdvancedRequest(BaseModel):
    """Request for advanced scenario comparison with ranking."""
    scenario_ids: List[uuid.UUID] = Field(..., min_length=2, max_length=10)
    ranking_weights: Optional[Dict[str, float]] = Field(
        None,
        description="Custom weights for ranking (revenue, net_income, service_level, risk_score, efficiency)"
    )
