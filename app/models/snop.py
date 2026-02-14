"""
S&OP (Sales and Operations Planning) Database Models

Comprehensive demand forecasting and supply planning with:
- Multi-level forecasting (SKU daily, Category weekly, Region monthly)
- Ensemble AI models (Holt-Winters + Prophet + XGBoost + LSTM)
- External factors (promotions, weather, economic indicators)
- Formal approval workflow (draft → review → approve)
"""

import uuid
from datetime import datetime, date, timezone
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING, Optional, List

from sqlalchemy import String, Boolean, DateTime, ForeignKey, Integer, Text, Numeric, Float, Date
from sqlalchemy import UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.database import Base

if TYPE_CHECKING:
    from app.models.product import Product
    from app.models.category import Category
    from app.models.warehouse import Warehouse
    from app.models.region import Region
    from app.models.user import User
    from app.models.vendor import Vendor


# ==================== Enumerations ====================

class ForecastGranularity(str, Enum):
    """Forecast time granularity levels."""
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"
    QUARTERLY = "QUARTERLY"


class ForecastLevel(str, Enum):
    """Forecast aggregation levels."""
    SKU = "SKU"                 # Individual product level
    CATEGORY = "CATEGORY"       # Product category level
    REGION = "REGION"           # Geographic region level
    CHANNEL = "CHANNEL"         # Sales channel level
    COMPANY = "COMPANY"         # Company-wide aggregate


class ForecastStatus(str, Enum):
    """Forecast approval workflow status."""
    DRAFT = "DRAFT"             # AI-generated, pending review
    PENDING_REVIEW = "PENDING_REVIEW"  # Submitted for review
    UNDER_REVIEW = "UNDER_REVIEW"      # Being reviewed
    ADJUSTMENT_REQUESTED = "ADJUSTMENT_REQUESTED"  # Needs modification
    APPROVED = "APPROVED"       # Final approved forecast
    REJECTED = "REJECTED"       # Rejected forecast
    SUPERSEDED = "SUPERSEDED"   # Replaced by newer forecast


class ForecastAlgorithm(str, Enum):
    """Available forecasting algorithms."""
    HOLT_WINTERS = "HOLT_WINTERS"       # Triple Exponential Smoothing
    PROPHET = "PROPHET"                  # Facebook Prophet
    ARIMA = "ARIMA"                      # Auto-Regressive Integrated Moving Average
    XGBOOST = "XGBOOST"                  # XGBoost regression
    LIGHTGBM = "LIGHTGBM"                # LightGBM regression
    LSTM = "LSTM"                        # Long Short-Term Memory neural network
    ENSEMBLE = "ENSEMBLE"                # Weighted ensemble of models
    MANUAL = "MANUAL"                    # Manual override


class SupplyPlanStatus(str, Enum):
    """Supply plan status."""
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    APPROVED = "APPROVED"
    IN_EXECUTION = "IN_EXECUTION"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class ScenarioStatus(str, Enum):
    """Scenario planning status."""
    DRAFT = "DRAFT"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    ARCHIVED = "ARCHIVED"


class ExternalFactorType(str, Enum):
    """Types of external factors affecting demand."""
    PROMOTION = "PROMOTION"         # Marketing campaigns, discounts
    SEASONAL = "SEASONAL"           # Seasonal patterns
    WEATHER = "WEATHER"             # Weather conditions
    ECONOMIC = "ECONOMIC"           # Economic indicators (GDP, inflation)
    COMPETITOR = "COMPETITOR"       # Competitor actions
    EVENT = "EVENT"                 # Special events (festivals, holidays)
    PRICE_CHANGE = "PRICE_CHANGE"   # Price modifications
    SUPPLY_DISRUPTION = "SUPPLY_DISRUPTION"  # Supply chain issues


class DemandSignalType(str, Enum):
    """Types of demand signals for demand sensing."""
    POS_SPIKE = "POS_SPIKE"                 # Point-of-sale spike detected
    POS_DROP = "POS_DROP"                   # Point-of-sale drop detected
    STOCKOUT_ALERT = "STOCKOUT_ALERT"       # Imminent stockout signal
    PROMOTION_LAUNCH = "PROMOTION_LAUNCH"   # Promotion going live
    PROMOTION_END = "PROMOTION_END"         # Promotion ending
    WEATHER_EVENT = "WEATHER_EVENT"         # Extreme weather impact
    FESTIVAL_SEASON = "FESTIVAL_SEASON"     # Festival/holiday demand lift
    COMPETITOR_PRICE = "COMPETITOR_PRICE"   # Competitor price change
    MARKET_TREND = "MARKET_TREND"           # Market trend shift
    NEW_CHANNEL = "NEW_CHANNEL"             # New sales channel activated
    RETURNS_SPIKE = "RETURNS_SPIKE"         # Spike in product returns
    SOCIAL_BUZZ = "SOCIAL_BUZZ"             # Social media driven demand


class DemandSignalStatus(str, Enum):
    """Status of a demand signal."""
    ACTIVE = "ACTIVE"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    APPLIED = "APPLIED"             # Impact applied to forecast
    EXPIRED = "EXPIRED"
    DISMISSED = "DISMISSED"


# ==================== Main Models ====================

class DemandForecast(Base):
    """
    Stores demand forecasts at various granularity and aggregation levels.

    Supports multi-level hierarchy:
    - SKU + Daily: Individual product daily forecasts
    - Category + Weekly: Category-level weekly forecasts
    - Region + Monthly: Regional monthly forecasts
    """
    __tablename__ = "demand_forecasts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Forecast identification
    forecast_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    forecast_name: Mapped[str] = mapped_column(String(200), nullable=False)

    # Forecast scope
    forecast_level: Mapped[str] = mapped_column(
        String(50),
        default="SKU",
        comment="SKU, CATEGORY, REGION, CHANNEL, COMPANY"
    )
    granularity: Mapped[str] = mapped_column(
        String(50),
        default="WEEKLY",
        comment="DAILY, WEEKLY, MONTHLY, QUARTERLY"
    )

    # Target entities (nullable based on forecast_level)
    product_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id"),
        nullable=True
    )
    category_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id"),
        nullable=True
    )
    warehouse_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id"),
        nullable=True
    )
    region_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("regions.id"),
        nullable=True
    )
    channel: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    # Forecast period
    forecast_start_date: Mapped[date] = mapped_column(Date, nullable=False)
    forecast_end_date: Mapped[date] = mapped_column(Date, nullable=False)
    forecast_horizon_days: Mapped[int] = mapped_column(Integer, default=90)

    # Forecast values (stored as JSONB for flexibility)
    # Format: [{"date": "2024-01-01", "forecasted_qty": 100, "lower_bound": 80, "upper_bound": 120}, ...]
    forecast_data: Mapped[dict] = mapped_column(JSONB, nullable=False, default=list)

    # Aggregated metrics
    total_forecasted_qty: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        default=Decimal("0")
    )
    avg_daily_demand: Mapped[Decimal] = mapped_column(
        Numeric(15, 4),
        default=Decimal("0")
    )
    peak_demand: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        default=Decimal("0")
    )

    # Model information
    algorithm_used: Mapped[str] = mapped_column(
        String(50),
        default="ENSEMBLE",
        comment="HOLT_WINTERS, PROPHET, ARIMA, XGBOOST, LIGHTGBM, LSTM, ENSEMBLE, MANUAL"
    )
    model_parameters: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Accuracy metrics
    mape: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # Mean Absolute Percentage Error
    mae: Mapped[Optional[float]] = mapped_column(Float, nullable=True)   # Mean Absolute Error
    rmse: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # Root Mean Square Error
    forecast_bias: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Confidence
    confidence_level: Mapped[float] = mapped_column(Float, default=0.95)

    # External factors considered
    external_factors_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Approval workflow
    status: Mapped[str] = mapped_column(
        String(50),
        default="DRAFT",
        comment="DRAFT, PENDING_REVIEW, UNDER_REVIEW, ADJUSTMENT_REQUESTED, APPROVED, REJECTED, SUPERSEDED"
    )

    # Audit trail
    created_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True
    )
    reviewed_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True
    )
    approved_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Version control
    version: Mapped[int] = mapped_column(Integer, default=1)
    parent_forecast_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("demand_forecasts.id"),
        nullable=True
    )

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    product: Mapped[Optional["Product"]] = relationship("Product", foreign_keys=[product_id])
    category: Mapped[Optional["Category"]] = relationship("Category", foreign_keys=[category_id])
    warehouse: Mapped[Optional["Warehouse"]] = relationship("Warehouse", foreign_keys=[warehouse_id])
    region: Mapped[Optional["Region"]] = relationship("Region", foreign_keys=[region_id])
    created_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[created_by_id])
    reviewed_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[reviewed_by_id])
    approved_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[approved_by_id])
    adjustments: Mapped[List["ForecastAdjustment"]] = relationship("ForecastAdjustment", back_populates="forecast")
    parent_forecast: Mapped[Optional["DemandForecast"]] = relationship("DemandForecast", remote_side=[id])

    __table_args__ = (
        Index("ix_demand_forecasts_product_date", "product_id", "forecast_start_date"),
        Index("ix_demand_forecasts_category_date", "category_id", "forecast_start_date"),
        Index("ix_demand_forecasts_status", "status"),
        Index("ix_demand_forecasts_level_granularity", "forecast_level", "granularity"),
    )


class ForecastAdjustment(Base):
    """
    Manual adjustments to AI-generated forecasts with approval tracking.
    """
    __tablename__ = "forecast_adjustments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    forecast_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("demand_forecasts.id"),
        nullable=False
    )

    # Adjustment details
    adjustment_date: Mapped[date] = mapped_column(Date, nullable=False)
    original_qty: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    adjusted_qty: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    adjustment_pct: Mapped[float] = mapped_column(Float, nullable=False)  # Percentage change

    # Reason and justification
    adjustment_reason: Mapped[str] = mapped_column(String(100), nullable=False)
    justification: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Approval
    status: Mapped[str] = mapped_column(
        String(50),
        default="PENDING_REVIEW",
        comment="DRAFT, PENDING_REVIEW, UNDER_REVIEW, ADJUSTMENT_REQUESTED, APPROVED, REJECTED, SUPERSEDED"
    )

    adjusted_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False
    )
    approved_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    forecast: Mapped["DemandForecast"] = relationship("DemandForecast", back_populates="adjustments")
    adjusted_by: Mapped["User"] = relationship("User", foreign_keys=[adjusted_by_id])
    approved_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[approved_by_id])


class SupplyPlan(Base):
    """
    Supply planning with production and procurement schedules.
    """
    __tablename__ = "supply_plans"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Plan identification
    plan_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    plan_name: Mapped[str] = mapped_column(String(200), nullable=False)

    # Link to demand forecast
    forecast_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("demand_forecasts.id"),
        nullable=True
    )

    # Plan period
    plan_start_date: Mapped[date] = mapped_column(Date, nullable=False)
    plan_end_date: Mapped[date] = mapped_column(Date, nullable=False)

    # Target entity
    product_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id"),
        nullable=True
    )
    warehouse_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id"),
        nullable=True
    )

    # Supply quantities
    planned_production_qty: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        default=Decimal("0")
    )
    planned_procurement_qty: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        default=Decimal("0")
    )

    # Capacity analysis
    production_capacity: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        default=Decimal("0")
    )
    capacity_utilization_pct: Mapped[float] = mapped_column(Float, default=0.0)

    # Supplier information
    vendor_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vendors.id"),
        nullable=True
    )
    lead_time_days: Mapped[int] = mapped_column(Integer, default=0)

    # Detailed schedule (JSONB)
    # Format: [{"date": "2024-01-01", "production_qty": 50, "procurement_qty": 100}, ...]
    schedule_data: Mapped[dict] = mapped_column(JSONB, nullable=False, default=list)

    # Status
    status: Mapped[str] = mapped_column(
        String(50),
        default="DRAFT",
        comment="DRAFT, SUBMITTED, APPROVED, IN_EXECUTION, COMPLETED, CANCELLED"
    )

    # Audit
    created_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True
    )
    approved_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    forecast: Mapped[Optional["DemandForecast"]] = relationship("DemandForecast")
    product: Mapped[Optional["Product"]] = relationship("Product")
    warehouse: Mapped[Optional["Warehouse"]] = relationship("Warehouse")
    vendor: Mapped[Optional["Vendor"]] = relationship("Vendor")
    created_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[created_by_id])
    approved_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[approved_by_id])


class SNOPScenario(Base):
    """
    What-if scenario planning for demand/supply analysis.
    """
    __tablename__ = "snop_scenarios"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Scenario identification
    scenario_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    scenario_name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Base scenario (optional - for comparison)
    base_scenario_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("snop_scenarios.id"),
        nullable=True
    )

    # Scenario parameters
    demand_multiplier: Mapped[float] = mapped_column(Float, default=1.0)
    supply_constraint_pct: Mapped[float] = mapped_column(Float, default=100.0)  # % of normal capacity
    lead_time_multiplier: Mapped[float] = mapped_column(Float, default=1.0)
    price_change_pct: Mapped[float] = mapped_column(Float, default=0.0)

    # Detailed assumptions (JSONB)
    assumptions: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)

    # Simulation period
    simulation_start_date: Mapped[date] = mapped_column(Date, nullable=False)
    simulation_end_date: Mapped[date] = mapped_column(Date, nullable=False)

    # Results (JSONB)
    results: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Key metrics from simulation
    projected_revenue: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    projected_margin: Mapped[Optional[Decimal]] = mapped_column(Numeric(18, 2), nullable=True)
    stockout_probability: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    service_level_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Status
    status: Mapped[str] = mapped_column(
        String(50),
        default="DRAFT",
        comment="DRAFT, RUNNING, COMPLETED, FAILED, ARCHIVED"
    )

    # Audit
    created_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    created_by: Mapped[Optional["User"]] = relationship("User")
    base_scenario: Mapped[Optional["SNOPScenario"]] = relationship("SNOPScenario", remote_side=[id])


class ExternalFactor(Base):
    """
    External factors that influence demand forecasting.
    """
    __tablename__ = "external_factors"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Factor identification
    factor_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    factor_name: Mapped[str] = mapped_column(String(200), nullable=False)
    factor_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="PROMOTION, SEASONAL, WEATHER, ECONOMIC, COMPETITOR, EVENT, PRICE_CHANGE, SUPPLY_DISRUPTION"
    )

    # Scope (which products/categories this affects)
    product_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id"),
        nullable=True
    )
    category_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id"),
        nullable=True
    )
    region_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("regions.id"),
        nullable=True
    )
    applies_to_all: Mapped[bool] = mapped_column(Boolean, default=False)

    # Effect period
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)

    # Impact
    impact_multiplier: Mapped[float] = mapped_column(Float, default=1.0)  # e.g., 1.2 = 20% increase
    impact_absolute: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), nullable=True)  # Fixed qty change

    # Additional data (JSONB)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Audit
    created_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    product: Mapped[Optional["Product"]] = relationship("Product")
    category: Mapped[Optional["Category"]] = relationship("Category")
    region: Mapped[Optional["Region"]] = relationship("Region")
    created_by: Mapped[Optional["User"]] = relationship("User")

    __table_args__ = (
        Index("ix_external_factors_type_dates", "factor_type", "start_date", "end_date"),
        Index("ix_external_factors_product", "product_id"),
    )


class InventoryOptimization(Base):
    """
    AI-recommended inventory optimization parameters.
    """
    __tablename__ = "inventory_optimizations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Target
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id"),
        nullable=False
    )
    warehouse_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id"),
        nullable=False
    )

    # Recommended parameters
    recommended_safety_stock: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False
    )
    recommended_reorder_point: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False
    )
    recommended_order_qty: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        nullable=False
    )  # Economic Order Quantity

    # Current vs recommended comparison
    current_safety_stock: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        default=Decimal("0")
    )
    current_reorder_point: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        default=Decimal("0")
    )

    # Analysis inputs
    avg_daily_demand: Mapped[Decimal] = mapped_column(Numeric(15, 4), nullable=False)
    demand_std_dev: Mapped[Decimal] = mapped_column(Numeric(15, 4), nullable=False)
    lead_time_days: Mapped[int] = mapped_column(Integer, nullable=False)
    lead_time_std_dev: Mapped[float] = mapped_column(Float, default=0.0)
    service_level_target: Mapped[float] = mapped_column(Float, default=0.95)

    # Cost factors
    holding_cost_pct: Mapped[float] = mapped_column(Float, default=0.25)
    ordering_cost: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("100"))
    stockout_cost: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), nullable=True)

    # Expected outcomes
    expected_stockout_rate: Mapped[float] = mapped_column(Float, default=0.0)
    expected_inventory_turns: Mapped[float] = mapped_column(Float, default=0.0)
    expected_holding_cost: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        default=Decimal("0")
    )

    # Calculation details (JSONB)
    calculation_details: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Validity
    valid_from: Mapped[date] = mapped_column(Date, nullable=False)
    valid_until: Mapped[date] = mapped_column(Date, nullable=False)

    # Status
    is_applied: Mapped[bool] = mapped_column(Boolean, default=False)
    applied_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Audit
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    product: Mapped["Product"] = relationship("Product")
    warehouse: Mapped["Warehouse"] = relationship("Warehouse")

    __table_args__ = (
        UniqueConstraint("product_id", "warehouse_id", "valid_from", name="uq_inventory_opt_product_warehouse_date"),
        Index("ix_inventory_opt_product_warehouse", "product_id", "warehouse_id"),
    )


class SNOPMeeting(Base):
    """
    S&OP meeting records for consensus planning.
    """
    __tablename__ = "snop_meetings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Meeting details
    meeting_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    meeting_title: Mapped[str] = mapped_column(String(200), nullable=False)
    meeting_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    # Planning period covered
    planning_period_start: Mapped[date] = mapped_column(Date, nullable=False)
    planning_period_end: Mapped[date] = mapped_column(Date, nullable=False)

    # Participants (JSONB array of user IDs)
    participants: Mapped[dict] = mapped_column(JSONB, nullable=False, default=list)

    # Agenda and notes
    agenda: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    meeting_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Forecasts reviewed (JSONB array of forecast IDs)
    forecasts_reviewed: Mapped[dict] = mapped_column(JSONB, nullable=False, default=list)

    # Decisions made (JSONB)
    decisions: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Action items (JSONB)
    action_items: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Status
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)

    # Audit
    created_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships (SNOPMeeting)
    created_by: Mapped[Optional["User"]] = relationship("User")


class DemandSignal(Base):
    """
    Real-time demand signals for demand sensing.

    Captures short-term demand indicators that adjust forecasts:
    - POS spikes/drops from sales channels
    - Promotional events going live
    - Weather events impacting demand
    - Competitor actions and market trends
    - Social media buzz

    Each signal has a strength (0-1), decay rate, and directional impact.
    """
    __tablename__ = "demand_signals"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Signal identification
    signal_code: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    signal_name: Mapped[str] = mapped_column(String(200), nullable=False)
    signal_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="POS_SPIKE, POS_DROP, STOCKOUT_ALERT, PROMOTION_LAUNCH, etc."
    )

    # Scope (which products/categories this signal affects)
    product_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id"),
        nullable=True
    )
    category_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id"),
        nullable=True
    )
    region_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("regions.id"),
        nullable=True
    )
    channel: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    applies_to_all: Mapped[bool] = mapped_column(Boolean, default=False)

    # Signal characteristics
    signal_strength: Mapped[float] = mapped_column(
        Float, default=0.5,
        comment="0.0 to 1.0 — strength of the signal"
    )
    impact_direction: Mapped[str] = mapped_column(
        String(10), default="UP",
        comment="UP or DOWN — direction of demand impact"
    )
    impact_pct: Mapped[float] = mapped_column(
        Float, default=0.0,
        comment="Percentage impact on forecast (e.g., +15.0 or -10.0)"
    )
    confidence: Mapped[float] = mapped_column(
        Float, default=0.7,
        comment="Confidence in this signal (0.0 to 1.0)"
    )

    # Decay and timing
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    effective_start: Mapped[date] = mapped_column(Date, nullable=False)
    effective_end: Mapped[date] = mapped_column(Date, nullable=False)
    decay_rate: Mapped[float] = mapped_column(
        Float, default=0.1,
        comment="Daily decay rate of signal strength (0.0 to 1.0)"
    )

    # Source information
    source: Mapped[str] = mapped_column(
        String(100), default="MANUAL",
        comment="MANUAL, POS_SYSTEM, WEATHER_API, MARKET_INTEL, SOCIAL_MEDIA"
    )
    source_data: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Impact tracking
    forecast_ids_affected: Mapped[Optional[dict]] = mapped_column(
        JSONB, nullable=True, default=list,
        comment="List of forecast IDs this signal adjusted"
    )
    actual_impact: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True,
        comment="Post-event measured actual impact %"
    )

    # Status
    status: Mapped[str] = mapped_column(
        String(50),
        default="ACTIVE",
        comment="ACTIVE, ACKNOWLEDGED, APPLIED, EXPIRED, DISMISSED"
    )

    # Audit
    created_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True
    )
    acknowledged_by_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    product: Mapped[Optional["Product"]] = relationship("Product")
    category: Mapped[Optional["Category"]] = relationship("Category")
    region: Mapped[Optional["Region"]] = relationship("Region")
    created_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[created_by_id])
    acknowledged_by: Mapped[Optional["User"]] = relationship("User", foreign_keys=[acknowledged_by_id])

    __table_args__ = (
        Index("ix_demand_signals_type_status", "signal_type", "status"),
        Index("ix_demand_signals_effective", "effective_start", "effective_end"),
        Index("ix_demand_signals_product", "product_id"),
    )
