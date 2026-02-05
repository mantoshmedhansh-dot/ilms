"""
WMS Reporting Models - Phase 12: Reporting & Analytics.

Models for WMS reporting and analytics including:
- Report definitions and schedules
- Report execution history
- Custom KPIs and metrics
- Data snapshots for trending
"""
from datetime import datetime, date
from decimal import Decimal
from enum import Enum
from typing import Optional, List
from uuid import UUID, uuid4

from sqlalchemy import (
    String, Integer, DateTime, ForeignKey, Index, Text, Boolean,
    Numeric, Date, UniqueConstraint, JSON
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


# ============================================================================
# ENUMS
# ============================================================================

class ReportCategory(str, Enum):
    """Category of report."""
    INVENTORY = "inventory"
    OPERATIONS = "operations"
    FULFILLMENT = "fulfillment"
    RECEIVING = "receiving"
    SHIPPING = "shipping"
    LABOR = "labor"
    FINANCE = "finance"
    QUALITY = "quality"
    RETURNS = "returns"
    CAPACITY = "capacity"
    PERFORMANCE = "performance"
    COMPLIANCE = "compliance"
    CUSTOM = "custom"


class ReportType(str, Enum):
    """Type of report."""
    SUMMARY = "summary"
    DETAILED = "detailed"
    EXCEPTION = "exception"
    TREND = "trend"
    COMPARISON = "comparison"
    DASHBOARD = "dashboard"
    ADHOC = "adhoc"


class ReportFormat(str, Enum):
    """Output format for reports."""
    PDF = "pdf"
    EXCEL = "excel"
    CSV = "csv"
    JSON = "json"
    HTML = "html"


class ReportFrequency(str, Enum):
    """Frequency for scheduled reports."""
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ON_DEMAND = "on_demand"


class ReportStatus(str, Enum):
    """Status of report execution."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class KPICategory(str, Enum):
    """Category for KPI."""
    INVENTORY = "inventory"
    FULFILLMENT = "fulfillment"
    RECEIVING = "receiving"
    SHIPPING = "shipping"
    LABOR = "labor"
    QUALITY = "quality"
    FINANCE = "finance"
    CUSTOMER = "customer"


class TrendDirection(str, Enum):
    """Direction of trend."""
    UP = "up"
    DOWN = "down"
    STABLE = "stable"


# ============================================================================
# MODELS
# ============================================================================

class ReportDefinition(Base):
    """
    Report definition with query parameters and formatting.
    """
    __tablename__ = "report_definitions"
    __table_args__ = (
        Index("idx_rd_tenant_category", "tenant_id", "category"),
        Index("idx_rd_active", "tenant_id", "is_active"),
        {"schema": "public"}
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("public.tenants.id"), nullable=False
    )

    # Report Identity
    report_code: Mapped[str] = mapped_column(String(50), nullable=False)
    report_name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    category: Mapped[ReportCategory] = mapped_column(
        String(30), nullable=False, default=ReportCategory.OPERATIONS
    )
    report_type: Mapped[ReportType] = mapped_column(
        String(20), nullable=False, default=ReportType.SUMMARY
    )

    # Data Source
    data_source: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g., "inventory", "orders"
    base_query: Mapped[Optional[str]] = mapped_column(Text)  # SQL or query definition
    filters: Mapped[Optional[dict]] = mapped_column(JSONB)  # Available filter fields
    parameters: Mapped[Optional[dict]] = mapped_column(JSONB)  # Default parameters
    group_by: Mapped[Optional[List]] = mapped_column(JSONB)  # Grouping fields
    order_by: Mapped[Optional[List]] = mapped_column(JSONB)  # Sort fields

    # Columns/Fields
    columns: Mapped[List] = mapped_column(JSONB, nullable=False)  # Column definitions
    calculated_fields: Mapped[Optional[List]] = mapped_column(JSONB)  # Formula fields
    aggregations: Mapped[Optional[List]] = mapped_column(JSONB)  # Sum, avg, count, etc.

    # Formatting
    default_format: Mapped[ReportFormat] = mapped_column(
        String(10), nullable=False, default=ReportFormat.EXCEL
    )
    available_formats: Mapped[List] = mapped_column(
        JSONB, default=["pdf", "excel", "csv"]
    )
    page_size: Mapped[str] = mapped_column(String(10), default="A4")
    orientation: Mapped[str] = mapped_column(String(10), default="portrait")
    header_template: Mapped[Optional[str]] = mapped_column(Text)
    footer_template: Mapped[Optional[str]] = mapped_column(Text)

    # Charts/Visualizations
    include_charts: Mapped[bool] = mapped_column(Boolean, default=False)
    chart_config: Mapped[Optional[dict]] = mapped_column(JSONB)

    # Permissions
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)  # Available to all users
    roles: Mapped[Optional[List]] = mapped_column(JSONB)  # Roles that can access
    warehouse_ids: Mapped[Optional[List]] = mapped_column(JSONB)  # Limit to warehouses

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)  # Built-in report

    # Audit
    created_by: Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    schedules: Mapped[List["ReportSchedule"]] = relationship(back_populates="report")
    executions: Mapped[List["ReportExecution"]] = relationship(back_populates="report")


class ReportSchedule(Base):
    """
    Schedule for automatic report generation and distribution.
    """
    __tablename__ = "report_schedules"
    __table_args__ = (
        Index("idx_rs_tenant_report", "tenant_id", "report_id"),
        Index("idx_rs_next_run", "tenant_id", "next_run_at"),
        {"schema": "public"}
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("public.tenants.id"), nullable=False
    )
    report_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("public.report_definitions.id"), nullable=False
    )

    schedule_name: Mapped[str] = mapped_column(String(200), nullable=False)

    # Schedule Configuration
    frequency: Mapped[ReportFrequency] = mapped_column(
        String(20), nullable=False, default=ReportFrequency.DAILY
    )
    cron_expression: Mapped[Optional[str]] = mapped_column(String(100))  # For complex schedules
    run_time: Mapped[str] = mapped_column(String(10), default="06:00")  # HH:MM
    day_of_week: Mapped[Optional[int]] = mapped_column(Integer)  # 0=Monday, 6=Sunday
    day_of_month: Mapped[Optional[int]] = mapped_column(Integer)  # 1-31
    timezone: Mapped[str] = mapped_column(String(50), default="Asia/Kolkata")

    # Report Parameters
    parameters: Mapped[Optional[dict]] = mapped_column(JSONB)
    output_format: Mapped[ReportFormat] = mapped_column(
        String(10), nullable=False, default=ReportFormat.EXCEL
    )
    date_range: Mapped[str] = mapped_column(String(30), default="yesterday")  # yesterday, last_7_days, etc.

    # Distribution
    email_to: Mapped[Optional[List]] = mapped_column(JSONB)  # Email addresses
    email_cc: Mapped[Optional[List]] = mapped_column(JSONB)
    email_subject: Mapped[Optional[str]] = mapped_column(String(200))
    email_body: Mapped[Optional[str]] = mapped_column(Text)
    upload_to_sftp: Mapped[bool] = mapped_column(Boolean, default=False)
    sftp_config: Mapped[Optional[dict]] = mapped_column(JSONB)  # Host, path, etc.
    webhook_url: Mapped[Optional[str]] = mapped_column(String(500))

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    last_run_status: Mapped[Optional[str]] = mapped_column(String(20))
    next_run_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0)

    created_by: Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    report: Mapped["ReportDefinition"] = relationship(back_populates="schedules")


class ReportExecution(Base):
    """
    Record of report execution.
    """
    __tablename__ = "report_executions"
    __table_args__ = (
        Index("idx_re_tenant_report", "tenant_id", "report_id"),
        Index("idx_re_status", "tenant_id", "status"),
        Index("idx_re_date", "tenant_id", "started_at"),
        {"schema": "public"}
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("public.tenants.id"), nullable=False
    )
    report_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("public.report_definitions.id"), nullable=False
    )
    schedule_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("public.report_schedules.id")
    )

    # Execution Details
    execution_number: Mapped[str] = mapped_column(String(50), nullable=False)
    output_format: Mapped[ReportFormat] = mapped_column(String(10), nullable=False)
    parameters: Mapped[Optional[dict]] = mapped_column(JSONB)
    date_range_start: Mapped[Optional[date]] = mapped_column(Date)
    date_range_end: Mapped[Optional[date]] = mapped_column(Date)

    # Timing
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    duration_seconds: Mapped[Optional[int]] = mapped_column(Integer)

    # Results
    status: Mapped[ReportStatus] = mapped_column(
        String(20), nullable=False, default=ReportStatus.PENDING
    )
    row_count: Mapped[int] = mapped_column(Integer, default=0)
    file_size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    file_url: Mapped[Optional[str]] = mapped_column(String(500))
    file_name: Mapped[Optional[str]] = mapped_column(String(200))

    # Distribution
    emailed_to: Mapped[Optional[List]] = mapped_column(JSONB)
    emailed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    email_status: Mapped[Optional[str]] = mapped_column(String(20))

    # Errors
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    error_details: Mapped[Optional[dict]] = mapped_column(JSONB)

    # Who ran it
    triggered_by: Mapped[str] = mapped_column(String(20), default="manual")  # manual, schedule, api
    run_by: Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True))

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    report: Mapped["ReportDefinition"] = relationship(back_populates="executions")


class KPIDefinition(Base):
    """
    KPI (Key Performance Indicator) definition.
    """
    __tablename__ = "kpi_definitions"
    __table_args__ = (
        Index("idx_kpi_tenant_category", "tenant_id", "category"),
        Index("idx_kpi_active", "tenant_id", "is_active"),
        {"schema": "public"}
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("public.tenants.id"), nullable=False
    )
    warehouse_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("public.warehouses.id")
    )

    # KPI Identity
    kpi_code: Mapped[str] = mapped_column(String(50), nullable=False)
    kpi_name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    category: Mapped[KPICategory] = mapped_column(
        String(30), nullable=False, default=KPICategory.FULFILLMENT
    )

    # Calculation
    data_source: Mapped[str] = mapped_column(String(100), nullable=False)
    calculation_formula: Mapped[str] = mapped_column(Text, nullable=False)  # SQL or formula
    aggregation_type: Mapped[str] = mapped_column(String(20), default="sum")  # sum, avg, count, ratio
    unit: Mapped[str] = mapped_column(String(20), default="count")  # count, %, hours, etc.
    decimal_places: Mapped[int] = mapped_column(Integer, default=2)

    # Targets
    target_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 4))
    warning_threshold: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 4))
    critical_threshold: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 4))
    higher_is_better: Mapped[bool] = mapped_column(Boolean, default=True)

    # Benchmarks
    industry_benchmark: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 4))
    internal_benchmark: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 4))

    # Display
    display_order: Mapped[int] = mapped_column(Integer, default=0)
    show_on_dashboard: Mapped[bool] = mapped_column(Boolean, default=True)
    chart_type: Mapped[Optional[str]] = mapped_column(String(20))  # line, bar, gauge

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)

    created_by: Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationships
    snapshots: Mapped[List["KPISnapshot"]] = relationship(back_populates="kpi")


class KPISnapshot(Base):
    """
    Point-in-time snapshot of KPI value for trending.
    """
    __tablename__ = "kpi_snapshots"
    __table_args__ = (
        Index("idx_kpis_tenant_kpi", "tenant_id", "kpi_id"),
        Index("idx_kpis_date", "tenant_id", "snapshot_date"),
        UniqueConstraint("tenant_id", "kpi_id", "warehouse_id", "snapshot_date", "period_type",
                        name="uq_kpi_snapshot"),
        {"schema": "public"}
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("public.tenants.id"), nullable=False
    )
    kpi_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("public.kpi_definitions.id"), nullable=False
    )
    warehouse_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("public.warehouses.id")
    )

    # Snapshot Timing
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False)
    period_type: Mapped[str] = mapped_column(String(20), nullable=False, default="daily")  # daily, weekly, monthly

    # Values
    current_value: Mapped[Decimal] = mapped_column(Numeric(15, 4), nullable=False)
    previous_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 4))
    target_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 4))

    # Trend
    change_value: Mapped[Decimal] = mapped_column(Numeric(15, 4), default=Decimal("0"))
    change_percent: Mapped[Decimal] = mapped_column(Numeric(8, 4), default=Decimal("0"))
    trend_direction: Mapped[TrendDirection] = mapped_column(
        String(10), nullable=False, default=TrendDirection.STABLE
    )

    # Status
    is_on_target: Mapped[bool] = mapped_column(Boolean, default=True)
    is_warning: Mapped[bool] = mapped_column(Boolean, default=False)
    is_critical: Mapped[bool] = mapped_column(Boolean, default=False)

    # Details
    data_points: Mapped[int] = mapped_column(Integer, default=0)  # Number of data points used
    breakdown: Mapped[Optional[dict]] = mapped_column(JSONB)  # By zone, category, etc.

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    kpi: Mapped["KPIDefinition"] = relationship(back_populates="snapshots")


class InventorySnapshot(Base):
    """
    Daily inventory snapshot for historical analysis.
    """
    __tablename__ = "inventory_snapshots"
    __table_args__ = (
        Index("idx_invs_tenant_date", "tenant_id", "snapshot_date"),
        Index("idx_invs_warehouse", "tenant_id", "warehouse_id", "snapshot_date"),
        UniqueConstraint("tenant_id", "warehouse_id", "product_id", "snapshot_date",
                        name="uq_inventory_snapshot"),
        {"schema": "public"}
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("public.tenants.id"), nullable=False
    )
    warehouse_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("public.warehouses.id"), nullable=False
    )
    product_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("public.products.id"), nullable=False
    )

    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False)

    # Quantities
    on_hand_qty: Mapped[Decimal] = mapped_column(Numeric(15, 3), default=Decimal("0"))
    available_qty: Mapped[Decimal] = mapped_column(Numeric(15, 3), default=Decimal("0"))
    reserved_qty: Mapped[Decimal] = mapped_column(Numeric(15, 3), default=Decimal("0"))
    in_transit_qty: Mapped[Decimal] = mapped_column(Numeric(15, 3), default=Decimal("0"))
    backorder_qty: Mapped[Decimal] = mapped_column(Numeric(15, 3), default=Decimal("0"))

    # Values
    unit_cost: Mapped[Decimal] = mapped_column(Numeric(15, 4), default=Decimal("0"))
    total_value: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"))

    # Movement
    received_qty: Mapped[Decimal] = mapped_column(Numeric(15, 3), default=Decimal("0"))
    shipped_qty: Mapped[Decimal] = mapped_column(Numeric(15, 3), default=Decimal("0"))
    adjusted_qty: Mapped[Decimal] = mapped_column(Numeric(15, 3), default=Decimal("0"))
    returned_qty: Mapped[Decimal] = mapped_column(Numeric(15, 3), default=Decimal("0"))

    # Analysis
    days_of_supply: Mapped[Optional[int]] = mapped_column(Integer)
    turn_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 4))
    abc_class: Mapped[Optional[str]] = mapped_column(String(1))

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class OperationsSnapshot(Base):
    """
    Daily operations metrics snapshot.
    """
    __tablename__ = "operations_snapshots"
    __table_args__ = (
        Index("idx_ops_tenant_date", "tenant_id", "snapshot_date"),
        Index("idx_ops_warehouse", "tenant_id", "warehouse_id", "snapshot_date"),
        UniqueConstraint("tenant_id", "warehouse_id", "snapshot_date",
                        name="uq_operations_snapshot"),
        {"schema": "public"}
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("public.tenants.id"), nullable=False
    )
    warehouse_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("public.warehouses.id"), nullable=False
    )

    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False)

    # Receiving
    receipts_count: Mapped[int] = mapped_column(Integer, default=0)
    units_received: Mapped[int] = mapped_column(Integer, default=0)
    receiving_accuracy: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    avg_putaway_time_mins: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 2))

    # Picking
    orders_picked: Mapped[int] = mapped_column(Integer, default=0)
    lines_picked: Mapped[int] = mapped_column(Integer, default=0)
    units_picked: Mapped[int] = mapped_column(Integer, default=0)
    picks_per_hour: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 2))
    picking_accuracy: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))

    # Packing
    orders_packed: Mapped[int] = mapped_column(Integer, default=0)
    packages_created: Mapped[int] = mapped_column(Integer, default=0)
    packing_accuracy: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))

    # Shipping
    shipments_created: Mapped[int] = mapped_column(Integer, default=0)
    units_shipped: Mapped[int] = mapped_column(Integer, default=0)
    on_time_shipment_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    same_day_ship_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))

    # Returns
    returns_received: Mapped[int] = mapped_column(Integer, default=0)
    returns_processed: Mapped[int] = mapped_column(Integer, default=0)
    return_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))

    # Quality
    qc_passed: Mapped[int] = mapped_column(Integer, default=0)
    qc_failed: Mapped[int] = mapped_column(Integer, default=0)
    defect_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))

    # Labor
    total_labor_hours: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"))
    productive_hours: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0"))
    labor_utilization: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))

    # Capacity
    storage_utilization: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))
    dock_utilization: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2))

    # Costs
    cost_per_order: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    cost_per_line: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2))
    cost_per_unit: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4))

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class DashboardWidget(Base):
    """
    Dashboard widget configuration.
    """
    __tablename__ = "dashboard_widgets"
    __table_args__ = (
        Index("idx_dw_tenant_dashboard", "tenant_id", "dashboard_id"),
        {"schema": "public"}
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("public.tenants.id"), nullable=False
    )
    dashboard_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)

    # Widget Identity
    widget_type: Mapped[str] = mapped_column(String(30), nullable=False)  # kpi, chart, table, count
    title: Mapped[str] = mapped_column(String(200), nullable=False)

    # Data Source
    data_source: Mapped[str] = mapped_column(String(100), nullable=False)
    kpi_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("public.kpi_definitions.id")
    )
    report_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("public.report_definitions.id")
    )
    query: Mapped[Optional[str]] = mapped_column(Text)
    parameters: Mapped[Optional[dict]] = mapped_column(JSONB)

    # Layout
    position_x: Mapped[int] = mapped_column(Integer, default=0)
    position_y: Mapped[int] = mapped_column(Integer, default=0)
    width: Mapped[int] = mapped_column(Integer, default=4)  # Grid units
    height: Mapped[int] = mapped_column(Integer, default=2)

    # Visualization
    chart_type: Mapped[Optional[str]] = mapped_column(String(30))  # line, bar, pie, gauge, etc.
    chart_config: Mapped[Optional[dict]] = mapped_column(JSONB)
    color_scheme: Mapped[Optional[str]] = mapped_column(String(30))

    # Refresh
    refresh_interval_seconds: Mapped[int] = mapped_column(Integer, default=300)
    last_refreshed_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    is_visible: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class AlertRule(Base):
    """
    Alert rules for KPI thresholds and anomalies.
    """
    __tablename__ = "alert_rules"
    __table_args__ = (
        Index("idx_ar_tenant_active", "tenant_id", "is_active"),
        {"schema": "public"}
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid4
    )
    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("public.tenants.id"), nullable=False
    )
    warehouse_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("public.warehouses.id")
    )

    # Rule Identity
    rule_name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(30), nullable=False)

    # Trigger Condition
    kpi_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("public.kpi_definitions.id")
    )
    metric: Mapped[str] = mapped_column(String(100), nullable=False)
    condition: Mapped[str] = mapped_column(String(20), nullable=False)  # gt, lt, eq, gte, lte
    threshold_value: Mapped[Decimal] = mapped_column(Numeric(15, 4), nullable=False)
    evaluation_window_minutes: Mapped[int] = mapped_column(Integer, default=60)

    # Alert Configuration
    severity: Mapped[str] = mapped_column(String(20), nullable=False, default="warning")  # info, warning, critical
    notification_channels: Mapped[List] = mapped_column(JSONB, default=["email"])  # email, sms, slack
    notify_users: Mapped[Optional[List]] = mapped_column(JSONB)  # User IDs
    notify_emails: Mapped[Optional[List]] = mapped_column(JSONB)  # Email addresses

    # Cooldown
    cooldown_minutes: Mapped[int] = mapped_column(Integer, default=60)
    max_alerts_per_day: Mapped[int] = mapped_column(Integer, default=10)
    last_triggered_at: Mapped[Optional[datetime]] = mapped_column(DateTime)
    triggered_count_today: Mapped[int] = mapped_column(Integer, default=0)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    created_by: Mapped[Optional[UUID]] = mapped_column(PG_UUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
