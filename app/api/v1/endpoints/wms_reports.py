"""
WMS Reporting API Endpoints - Phase 12: Reporting & Analytics.

API endpoints for WMS reporting and analytics.
"""
from datetime import date
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_user, require_permissions
from app.models.user import User
from app.models.wms_reports import (
    ReportCategory, ReportType, ReportFormat, ReportFrequency, ReportStatus,
    KPICategory
)
from app.schemas.wms_reports import (
    ReportDefinitionCreate, ReportDefinitionUpdate, ReportDefinitionResponse,
    ReportScheduleCreate, ReportScheduleUpdate, ReportScheduleResponse,
    ReportExecuteRequest, ReportExecutionResponse,
    KPIDefinitionCreate, KPIDefinitionUpdate, KPIDefinitionResponse,
    KPISnapshotResponse, KPIWithCurrentValue,
    InventorySnapshotResponse, OperationsSnapshotResponse,
    DashboardWidgetCreate, DashboardWidgetUpdate, DashboardWidgetResponse,
    AlertRuleCreate, AlertRuleUpdate, AlertRuleResponse,
    AnalyticsDashboard, InventoryAnalytics, FulfillmentAnalytics, LaborAnalytics
)
from app.services.wms_reports_service import WMSReportsService

router = APIRouter()


# ============================================================================
# REPORT DEFINITIONS
# ============================================================================

@router.post(
    "/reports",
    response_model=ReportDefinitionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Report Definition"
)
async def create_report(
    data: ReportDefinitionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["reports:manage"]))
):
    """Create a new report definition."""
    service = WMSReportsService(db, current_user.tenant_id)
    return await service.create_report(data, current_user.id)


@router.get(
    "/reports",
    response_model=List[ReportDefinitionResponse],
    summary="List Report Definitions"
)
async def list_reports(
    category: Optional[ReportCategory] = None,
    report_type: Optional[ReportType] = None,
    is_active: Optional[bool] = True,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["reports:read"]))
):
    """List report definitions."""
    service = WMSReportsService(db, current_user.tenant_id)
    reports, _ = await service.list_reports(
        category=category,
        report_type=report_type,
        is_active=is_active,
        skip=skip,
        limit=limit
    )
    return reports


@router.get(
    "/reports/{report_id}",
    response_model=ReportDefinitionResponse,
    summary="Get Report Definition"
)
async def get_report(
    report_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["reports:read"]))
):
    """Get report definition details."""
    service = WMSReportsService(db, current_user.tenant_id)
    report = await service.get_report(report_id)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found"
        )
    return report


@router.patch(
    "/reports/{report_id}",
    response_model=ReportDefinitionResponse,
    summary="Update Report Definition"
)
async def update_report(
    report_id: UUID,
    data: ReportDefinitionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["reports:manage"]))
):
    """Update a report definition."""
    service = WMSReportsService(db, current_user.tenant_id)
    report = await service.update_report(report_id, data)
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found"
        )
    return report


@router.post(
    "/reports/execute",
    response_model=ReportExecutionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Execute Report"
)
async def execute_report(
    data: ReportExecuteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["reports:read"]))
):
    """Execute a report and generate output."""
    service = WMSReportsService(db, current_user.tenant_id)
    try:
        return await service.execute_report(data, current_user.id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get(
    "/reports/executions",
    response_model=List[ReportExecutionResponse],
    summary="List Report Executions"
)
async def list_executions(
    report_id: Optional[UUID] = None,
    status: Optional[ReportStatus] = None,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["reports:read"]))
):
    """List report executions."""
    service = WMSReportsService(db, current_user.tenant_id)
    executions, _ = await service.list_executions(
        report_id=report_id,
        status=status,
        from_date=from_date,
        to_date=to_date,
        skip=skip,
        limit=limit
    )
    return executions


# ============================================================================
# REPORT SCHEDULES
# ============================================================================

@router.post(
    "/schedules",
    response_model=ReportScheduleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Report Schedule"
)
async def create_schedule(
    data: ReportScheduleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["reports:manage"]))
):
    """Create a report schedule."""
    service = WMSReportsService(db, current_user.tenant_id)
    return await service.create_schedule(data, current_user.id)


@router.get(
    "/schedules",
    response_model=List[ReportScheduleResponse],
    summary="List Report Schedules"
)
async def list_schedules(
    report_id: Optional[UUID] = None,
    is_active: Optional[bool] = True,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["reports:read"]))
):
    """List report schedules."""
    service = WMSReportsService(db, current_user.tenant_id)
    schedules, _ = await service.list_schedules(
        report_id=report_id,
        is_active=is_active,
        skip=skip,
        limit=limit
    )
    return schedules


@router.get(
    "/schedules/{schedule_id}",
    response_model=ReportScheduleResponse,
    summary="Get Report Schedule"
)
async def get_schedule(
    schedule_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["reports:read"]))
):
    """Get report schedule details."""
    service = WMSReportsService(db, current_user.tenant_id)
    schedule = await service.get_schedule(schedule_id)
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Schedule not found"
        )
    return schedule


# ============================================================================
# KPIs
# ============================================================================

@router.post(
    "/kpis",
    response_model=KPIDefinitionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create KPI Definition"
)
async def create_kpi(
    data: KPIDefinitionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["reports:manage"]))
):
    """Create a KPI definition."""
    service = WMSReportsService(db, current_user.tenant_id)
    return await service.create_kpi(data, current_user.id)


@router.get(
    "/kpis",
    response_model=List[KPIDefinitionResponse],
    summary="List KPI Definitions"
)
async def list_kpis(
    category: Optional[KPICategory] = None,
    warehouse_id: Optional[UUID] = None,
    show_on_dashboard: Optional[bool] = None,
    is_active: Optional[bool] = True,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["reports:read"]))
):
    """List KPI definitions."""
    service = WMSReportsService(db, current_user.tenant_id)
    kpis, _ = await service.list_kpis(
        category=category,
        warehouse_id=warehouse_id,
        show_on_dashboard=show_on_dashboard,
        is_active=is_active,
        skip=skip,
        limit=limit
    )
    return kpis


@router.get(
    "/kpis/{kpi_id}",
    response_model=KPIDefinitionResponse,
    summary="Get KPI Definition"
)
async def get_kpi(
    kpi_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["reports:read"]))
):
    """Get KPI definition details."""
    service = WMSReportsService(db, current_user.tenant_id)
    kpi = await service.get_kpi(kpi_id)
    if not kpi:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="KPI not found"
        )
    return kpi


@router.get(
    "/kpis/{kpi_id}/current",
    response_model=KPIWithCurrentValue,
    summary="Get KPI with Current Value"
)
async def get_kpi_with_value(
    kpi_id: UUID,
    warehouse_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["reports:read"]))
):
    """Get KPI with current calculated value."""
    service = WMSReportsService(db, current_user.tenant_id)
    result = await service.get_kpi_with_value(kpi_id, warehouse_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="KPI not found"
        )
    return result


# ============================================================================
# DASHBOARD WIDGETS
# ============================================================================

@router.post(
    "/widgets",
    response_model=DashboardWidgetResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Dashboard Widget"
)
async def create_widget(
    data: DashboardWidgetCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["reports:manage"]))
):
    """Create a dashboard widget."""
    service = WMSReportsService(db, current_user.tenant_id)
    return await service.create_widget(data)


@router.get(
    "/widgets",
    response_model=List[DashboardWidgetResponse],
    summary="List Dashboard Widgets"
)
async def list_widgets(
    dashboard_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["reports:read"]))
):
    """List widgets for a dashboard."""
    service = WMSReportsService(db, current_user.tenant_id)
    return await service.list_widgets(dashboard_id)


# ============================================================================
# ALERT RULES
# ============================================================================

@router.post(
    "/alerts",
    response_model=AlertRuleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Alert Rule"
)
async def create_alert_rule(
    data: AlertRuleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["reports:manage"]))
):
    """Create an alert rule."""
    service = WMSReportsService(db, current_user.tenant_id)
    return await service.create_alert_rule(data, current_user.id)


@router.get(
    "/alerts",
    response_model=List[AlertRuleResponse],
    summary="List Alert Rules"
)
async def list_alert_rules(
    warehouse_id: Optional[UUID] = None,
    category: Optional[str] = None,
    is_active: Optional[bool] = True,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["reports:read"]))
):
    """List alert rules."""
    service = WMSReportsService(db, current_user.tenant_id)
    rules, _ = await service.list_alert_rules(
        warehouse_id=warehouse_id,
        category=category,
        is_active=is_active,
        skip=skip,
        limit=limit
    )
    return rules


# ============================================================================
# ANALYTICS DASHBOARDS
# ============================================================================

@router.get(
    "/analytics/dashboard",
    response_model=AnalyticsDashboard,
    summary="Get Analytics Dashboard"
)
async def get_analytics_dashboard(
    warehouse_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["reports:read"]))
):
    """Get main analytics dashboard data."""
    service = WMSReportsService(db, current_user.tenant_id)
    return await service.get_analytics_dashboard(warehouse_id)


@router.get(
    "/analytics/inventory",
    response_model=InventoryAnalytics,
    summary="Get Inventory Analytics"
)
async def get_inventory_analytics(
    warehouse_id: Optional[UUID] = None,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["reports:read"]))
):
    """Get inventory analytics data."""
    service = WMSReportsService(db, current_user.tenant_id)
    return await service.get_inventory_analytics(warehouse_id, from_date, to_date)


@router.get(
    "/analytics/fulfillment",
    response_model=FulfillmentAnalytics,
    summary="Get Fulfillment Analytics"
)
async def get_fulfillment_analytics(
    warehouse_id: Optional[UUID] = None,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["reports:read"]))
):
    """Get fulfillment analytics data."""
    service = WMSReportsService(db, current_user.tenant_id)
    return await service.get_fulfillment_analytics(warehouse_id, from_date, to_date)


@router.get(
    "/analytics/labor",
    response_model=LaborAnalytics,
    summary="Get Labor Analytics"
)
async def get_labor_analytics(
    warehouse_id: Optional[UUID] = None,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["reports:read"]))
):
    """Get labor analytics data."""
    service = WMSReportsService(db, current_user.tenant_id)
    return await service.get_labor_analytics(warehouse_id, from_date, to_date)


# ============================================================================
# SNAPSHOT GENERATION
# ============================================================================

@router.post(
    "/snapshots/generate",
    summary="Generate Daily Snapshots"
)
async def generate_snapshots(
    warehouse_id: UUID,
    snapshot_date: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["reports:manage"]))
):
    """Generate daily inventory and operations snapshots."""
    service = WMSReportsService(db, current_user.tenant_id)
    counts = await service.generate_daily_snapshots(warehouse_id, snapshot_date)
    return {"message": "Snapshots generated successfully", "counts": counts}
