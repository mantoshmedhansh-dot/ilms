"""
WMS Reporting Schemas - Phase 12: Reporting & Analytics.

Pydantic schemas for WMS reporting and analytics.
"""
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict

from app.models.wms_reports import (
    ReportCategory, ReportType, ReportFormat, ReportFrequency, ReportStatus,
    KPICategory, TrendDirection
)


# ============================================================================
# REPORT DEFINITION SCHEMAS
# ============================================================================

class ReportColumnDef(BaseModel):
    """Column definition for a report."""
    field: str
    header: str
    type: str = "string"  # string, number, date, currency, percent
    width: Optional[int] = None
    format: Optional[str] = None
    aggregate: Optional[str] = None  # sum, avg, count


class ReportDefinitionBase(BaseModel):
    """Base schema for report definition."""
    report_code: str = Field(..., max_length=50)
    report_name: str = Field(..., max_length=200)
    description: Optional[str] = None
    category: ReportCategory = ReportCategory.OPERATIONS
    report_type: ReportType = ReportType.SUMMARY

    data_source: str = Field(..., max_length=100)
    base_query: Optional[str] = None
    filters: Optional[Dict[str, Any]] = None
    parameters: Optional[Dict[str, Any]] = None
    group_by: Optional[List[str]] = None
    order_by: Optional[List[str]] = None

    columns: List[ReportColumnDef]
    calculated_fields: Optional[List[Dict[str, Any]]] = None
    aggregations: Optional[List[str]] = None

    default_format: ReportFormat = ReportFormat.EXCEL
    available_formats: List[str] = ["pdf", "excel", "csv"]
    page_size: str = "A4"
    orientation: str = "portrait"
    header_template: Optional[str] = None
    footer_template: Optional[str] = None

    include_charts: bool = False
    chart_config: Optional[Dict[str, Any]] = None

    is_public: bool = False
    roles: Optional[List[str]] = None
    warehouse_ids: Optional[List[UUID]] = None


class ReportDefinitionCreate(ReportDefinitionBase):
    """Schema for creating a report definition."""
    pass


class ReportDefinitionUpdate(BaseModel):
    """Schema for updating a report definition."""
    report_name: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    filters: Optional[Dict[str, Any]] = None
    parameters: Optional[Dict[str, Any]] = None
    columns: Optional[List[ReportColumnDef]] = None
    default_format: Optional[ReportFormat] = None
    include_charts: Optional[bool] = None
    chart_config: Optional[Dict[str, Any]] = None
    is_public: Optional[bool] = None
    roles: Optional[List[str]] = None
    is_active: Optional[bool] = None


class ReportDefinitionResponse(ReportDefinitionBase):
    """Schema for report definition response."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    is_active: bool
    is_system: bool
    created_by: Optional[UUID]
    created_at: datetime
    updated_at: datetime


# ============================================================================
# REPORT SCHEDULE SCHEMAS
# ============================================================================

class ReportScheduleBase(BaseModel):
    """Base schema for report schedule."""
    schedule_name: str = Field(..., max_length=200)
    frequency: ReportFrequency = ReportFrequency.DAILY
    cron_expression: Optional[str] = Field(None, max_length=100)
    run_time: str = Field(default="06:00", max_length=10)
    day_of_week: Optional[int] = Field(None, ge=0, le=6)
    day_of_month: Optional[int] = Field(None, ge=1, le=31)
    timezone: str = Field(default="Asia/Kolkata", max_length=50)

    parameters: Optional[Dict[str, Any]] = None
    output_format: ReportFormat = ReportFormat.EXCEL
    date_range: str = Field(default="yesterday", max_length=30)

    email_to: Optional[List[str]] = None
    email_cc: Optional[List[str]] = None
    email_subject: Optional[str] = Field(None, max_length=200)
    email_body: Optional[str] = None
    upload_to_sftp: bool = False
    sftp_config: Optional[Dict[str, Any]] = None
    webhook_url: Optional[str] = Field(None, max_length=500)


class ReportScheduleCreate(ReportScheduleBase):
    """Schema for creating a report schedule."""
    report_id: UUID


class ReportScheduleUpdate(BaseModel):
    """Schema for updating a report schedule."""
    schedule_name: Optional[str] = Field(None, max_length=200)
    frequency: Optional[ReportFrequency] = None
    cron_expression: Optional[str] = None
    run_time: Optional[str] = None
    day_of_week: Optional[int] = None
    day_of_month: Optional[int] = None
    parameters: Optional[Dict[str, Any]] = None
    output_format: Optional[ReportFormat] = None
    date_range: Optional[str] = None
    email_to: Optional[List[str]] = None
    email_cc: Optional[List[str]] = None
    email_subject: Optional[str] = None
    is_active: Optional[bool] = None


class ReportScheduleResponse(ReportScheduleBase):
    """Schema for report schedule response."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    report_id: UUID
    is_active: bool
    last_run_at: Optional[datetime]
    last_run_status: Optional[str]
    next_run_at: Optional[datetime]
    consecutive_failures: int
    created_by: Optional[UUID]
    created_at: datetime
    updated_at: datetime


# ============================================================================
# REPORT EXECUTION SCHEMAS
# ============================================================================

class ReportExecuteRequest(BaseModel):
    """Schema for executing a report."""
    report_id: UUID
    output_format: ReportFormat = ReportFormat.EXCEL
    parameters: Optional[Dict[str, Any]] = None
    date_range_start: Optional[date] = None
    date_range_end: Optional[date] = None
    email_to: Optional[List[str]] = None


class ReportExecutionResponse(BaseModel):
    """Schema for report execution response."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    report_id: UUID
    schedule_id: Optional[UUID]
    execution_number: str
    output_format: str
    parameters: Optional[Dict[str, Any]]
    date_range_start: Optional[date]
    date_range_end: Optional[date]

    started_at: datetime
    completed_at: Optional[datetime]
    duration_seconds: Optional[int]

    status: str
    row_count: int
    file_size_bytes: int
    file_url: Optional[str]
    file_name: Optional[str]

    emailed_to: Optional[List[str]]
    emailed_at: Optional[datetime]
    email_status: Optional[str]

    error_message: Optional[str]
    triggered_by: str
    run_by: Optional[UUID]

    created_at: datetime


# ============================================================================
# KPI SCHEMAS
# ============================================================================

class KPIDefinitionBase(BaseModel):
    """Base schema for KPI definition."""
    kpi_code: str = Field(..., max_length=50)
    kpi_name: str = Field(..., max_length=200)
    description: Optional[str] = None
    category: KPICategory = KPICategory.FULFILLMENT

    data_source: str = Field(..., max_length=100)
    calculation_formula: str
    aggregation_type: str = Field(default="sum", max_length=20)
    unit: str = Field(default="count", max_length=20)
    decimal_places: int = Field(default=2, ge=0, le=6)

    target_value: Optional[Decimal] = None
    warning_threshold: Optional[Decimal] = None
    critical_threshold: Optional[Decimal] = None
    higher_is_better: bool = True

    industry_benchmark: Optional[Decimal] = None
    internal_benchmark: Optional[Decimal] = None

    display_order: int = 0
    show_on_dashboard: bool = True
    chart_type: Optional[str] = Field(None, max_length=20)


class KPIDefinitionCreate(KPIDefinitionBase):
    """Schema for creating a KPI definition."""
    warehouse_id: Optional[UUID] = None


class KPIDefinitionUpdate(BaseModel):
    """Schema for updating a KPI definition."""
    kpi_name: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    target_value: Optional[Decimal] = None
    warning_threshold: Optional[Decimal] = None
    critical_threshold: Optional[Decimal] = None
    industry_benchmark: Optional[Decimal] = None
    internal_benchmark: Optional[Decimal] = None
    display_order: Optional[int] = None
    show_on_dashboard: Optional[bool] = None
    chart_type: Optional[str] = None
    is_active: Optional[bool] = None


class KPIDefinitionResponse(KPIDefinitionBase):
    """Schema for KPI definition response."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    warehouse_id: Optional[UUID]
    is_active: bool
    is_system: bool
    created_by: Optional[UUID]
    created_at: datetime
    updated_at: datetime


class KPISnapshotResponse(BaseModel):
    """Schema for KPI snapshot response."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    kpi_id: UUID
    warehouse_id: Optional[UUID]
    snapshot_date: date
    period_type: str

    current_value: Decimal
    previous_value: Optional[Decimal]
    target_value: Optional[Decimal]

    change_value: Decimal
    change_percent: Decimal
    trend_direction: str

    is_on_target: bool
    is_warning: bool
    is_critical: bool
    data_points: int
    breakdown: Optional[Dict[str, Any]]

    created_at: datetime


class KPIWithCurrentValue(KPIDefinitionResponse):
    """KPI definition with current value."""
    current_value: Optional[Decimal] = None
    previous_value: Optional[Decimal] = None
    change_percent: Optional[Decimal] = None
    trend_direction: Optional[str] = None
    is_on_target: Optional[bool] = None
    is_warning: Optional[bool] = None
    is_critical: Optional[bool] = None


# ============================================================================
# SNAPSHOT SCHEMAS
# ============================================================================

class InventorySnapshotResponse(BaseModel):
    """Schema for inventory snapshot response."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    warehouse_id: UUID
    product_id: UUID
    snapshot_date: date

    on_hand_qty: Decimal
    available_qty: Decimal
    reserved_qty: Decimal
    in_transit_qty: Decimal
    backorder_qty: Decimal

    unit_cost: Decimal
    total_value: Decimal

    received_qty: Decimal
    shipped_qty: Decimal
    adjusted_qty: Decimal
    returned_qty: Decimal

    days_of_supply: Optional[int]
    turn_rate: Optional[Decimal]
    abc_class: Optional[str]

    created_at: datetime


class OperationsSnapshotResponse(BaseModel):
    """Schema for operations snapshot response."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    warehouse_id: UUID
    snapshot_date: date

    # Receiving
    receipts_count: int
    units_received: int
    receiving_accuracy: Optional[Decimal]
    avg_putaway_time_mins: Optional[Decimal]

    # Picking
    orders_picked: int
    lines_picked: int
    units_picked: int
    picks_per_hour: Optional[Decimal]
    picking_accuracy: Optional[Decimal]

    # Packing
    orders_packed: int
    packages_created: int
    packing_accuracy: Optional[Decimal]

    # Shipping
    shipments_created: int
    units_shipped: int
    on_time_shipment_rate: Optional[Decimal]
    same_day_ship_rate: Optional[Decimal]

    # Returns
    returns_received: int
    returns_processed: int
    return_rate: Optional[Decimal]

    # Quality
    qc_passed: int
    qc_failed: int
    defect_rate: Optional[Decimal]

    # Labor
    total_labor_hours: Decimal
    productive_hours: Decimal
    labor_utilization: Optional[Decimal]

    # Capacity
    storage_utilization: Optional[Decimal]
    dock_utilization: Optional[Decimal]

    # Costs
    cost_per_order: Optional[Decimal]
    cost_per_line: Optional[Decimal]
    cost_per_unit: Optional[Decimal]

    created_at: datetime


# ============================================================================
# DASHBOARD WIDGET SCHEMAS
# ============================================================================

class DashboardWidgetBase(BaseModel):
    """Base schema for dashboard widget."""
    widget_type: str = Field(..., max_length=30)
    title: str = Field(..., max_length=200)
    data_source: str = Field(..., max_length=100)
    kpi_id: Optional[UUID] = None
    report_id: Optional[UUID] = None
    query: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None

    position_x: int = Field(default=0, ge=0)
    position_y: int = Field(default=0, ge=0)
    width: int = Field(default=4, ge=1, le=12)
    height: int = Field(default=2, ge=1, le=12)

    chart_type: Optional[str] = Field(None, max_length=30)
    chart_config: Optional[Dict[str, Any]] = None
    color_scheme: Optional[str] = Field(None, max_length=30)

    refresh_interval_seconds: int = Field(default=300, ge=60)


class DashboardWidgetCreate(DashboardWidgetBase):
    """Schema for creating a dashboard widget."""
    dashboard_id: UUID


class DashboardWidgetUpdate(BaseModel):
    """Schema for updating a dashboard widget."""
    title: Optional[str] = Field(None, max_length=200)
    query: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    position_x: Optional[int] = None
    position_y: Optional[int] = None
    width: Optional[int] = None
    height: Optional[int] = None
    chart_type: Optional[str] = None
    chart_config: Optional[Dict[str, Any]] = None
    refresh_interval_seconds: Optional[int] = None
    is_visible: Optional[bool] = None


class DashboardWidgetResponse(DashboardWidgetBase):
    """Schema for dashboard widget response."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    dashboard_id: UUID
    is_visible: bool
    last_refreshed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


# ============================================================================
# ALERT RULE SCHEMAS
# ============================================================================

class AlertRuleBase(BaseModel):
    """Base schema for alert rule."""
    rule_name: str = Field(..., max_length=200)
    description: Optional[str] = None
    category: str = Field(..., max_length=30)

    kpi_id: Optional[UUID] = None
    metric: str = Field(..., max_length=100)
    condition: str = Field(..., max_length=20)  # gt, lt, eq, gte, lte
    threshold_value: Decimal
    evaluation_window_minutes: int = Field(default=60, ge=5)

    severity: str = Field(default="warning", max_length=20)
    notification_channels: List[str] = ["email"]
    notify_users: Optional[List[UUID]] = None
    notify_emails: Optional[List[str]] = None

    cooldown_minutes: int = Field(default=60, ge=5)
    max_alerts_per_day: int = Field(default=10, ge=1)


class AlertRuleCreate(AlertRuleBase):
    """Schema for creating an alert rule."""
    warehouse_id: Optional[UUID] = None


class AlertRuleUpdate(BaseModel):
    """Schema for updating an alert rule."""
    rule_name: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    threshold_value: Optional[Decimal] = None
    severity: Optional[str] = None
    notification_channels: Optional[List[str]] = None
    notify_users: Optional[List[UUID]] = None
    notify_emails: Optional[List[str]] = None
    cooldown_minutes: Optional[int] = None
    max_alerts_per_day: Optional[int] = None
    is_active: Optional[bool] = None


class AlertRuleResponse(AlertRuleBase):
    """Schema for alert rule response."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    warehouse_id: Optional[UUID]
    is_active: bool
    last_triggered_at: Optional[datetime]
    triggered_count_today: int
    created_by: Optional[UUID]
    created_at: datetime
    updated_at: datetime


# ============================================================================
# ANALYTICS DASHBOARD SCHEMAS
# ============================================================================

class AnalyticsDashboard(BaseModel):
    """Analytics dashboard data."""
    # KPIs
    kpis: List[KPIWithCurrentValue]

    # Operations Summary
    operations_today: Optional[OperationsSnapshotResponse]
    operations_mtd: Dict[str, Any]

    # Inventory Summary
    total_inventory_value: Decimal
    total_sku_count: int
    low_stock_items: int
    overstock_items: int

    # Order Fulfillment
    orders_pending: int
    orders_in_progress: int
    orders_completed_today: int
    fulfillment_rate: Optional[Decimal]

    # Trends
    orders_trend: List[Dict[str, Any]]  # 7-day trend
    inventory_trend: List[Dict[str, Any]]
    picking_trend: List[Dict[str, Any]]

    # Top Items
    top_moving_items: List[Dict[str, Any]]
    slowest_moving_items: List[Dict[str, Any]]

    # Alerts
    active_alerts: List[Dict[str, Any]]


class InventoryAnalytics(BaseModel):
    """Inventory analytics data."""
    # Summary
    total_value: Decimal
    total_sku_count: int
    total_units: int

    # Health
    healthy_stock: int
    low_stock: int
    out_of_stock: int
    overstock: int

    # Aging
    aging_0_30: Decimal
    aging_31_60: Decimal
    aging_61_90: Decimal
    aging_over_90: Decimal

    # ABC Distribution
    abc_distribution: Dict[str, int]

    # Turnover
    average_turn_rate: Optional[Decimal]
    turn_rate_by_category: List[Dict[str, Any]]

    # By Warehouse
    by_warehouse: List[Dict[str, Any]]

    # By Category
    by_category: List[Dict[str, Any]]


class FulfillmentAnalytics(BaseModel):
    """Fulfillment analytics data."""
    # Today
    orders_received: int
    orders_shipped: int
    orders_pending: int
    on_time_rate: Optional[Decimal]

    # Cycle Time
    avg_cycle_time_hours: Optional[Decimal]
    pick_to_ship_hours: Optional[Decimal]

    # Accuracy
    picking_accuracy: Optional[Decimal]
    shipping_accuracy: Optional[Decimal]

    # By Channel
    by_channel: List[Dict[str, Any]]

    # By Carrier
    by_carrier: List[Dict[str, Any]]

    # Exceptions
    exceptions_count: int
    exceptions_by_type: Dict[str, int]

    # Trends
    daily_volume: List[Dict[str, Any]]
    hourly_volume: List[Dict[str, Any]]


class LaborAnalytics(BaseModel):
    """Labor analytics data."""
    # Headcount
    total_workers: int
    workers_present: int
    attendance_rate: Optional[Decimal]

    # Productivity
    picks_per_hour: Optional[Decimal]
    units_per_hour: Optional[Decimal]
    orders_per_hour: Optional[Decimal]

    # Utilization
    labor_utilization: Optional[Decimal]
    productive_hours: Decimal
    idle_hours: Decimal

    # By Task Type
    by_task_type: List[Dict[str, Any]]

    # Top Performers
    top_performers: List[Dict[str, Any]]

    # Trends
    productivity_trend: List[Dict[str, Any]]
