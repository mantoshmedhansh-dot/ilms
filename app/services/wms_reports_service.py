"""
WMS Reporting Service - Phase 12: Reporting & Analytics.

Business logic for WMS reporting and analytics.
"""
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Optional, List, Tuple, Dict, Any
from uuid import UUID, uuid4

from sqlalchemy import select, func, and_, or_, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.wms_reports import (
    ReportDefinition, ReportSchedule, ReportExecution,
    KPIDefinition, KPISnapshot, InventorySnapshot, OperationsSnapshot,
    DashboardWidget, AlertRule,
    ReportCategory, ReportType, ReportFormat, ReportFrequency, ReportStatus,
    KPICategory, TrendDirection
)
from app.models.inventory import InventorySummary
from app.models.order import Order, OrderStatus
from app.models.shipment import Shipment, ShipmentStatus
from app.models.picklist import Picklist, PicklistStatus
from app.schemas.wms_reports import (
    ReportDefinitionCreate, ReportDefinitionUpdate,
    ReportScheduleCreate, ReportScheduleUpdate,
    ReportExecuteRequest,
    KPIDefinitionCreate, KPIDefinitionUpdate,
    DashboardWidgetCreate, DashboardWidgetUpdate,
    AlertRuleCreate, AlertRuleUpdate
)


class WMSReportsService:
    """Service for WMS reporting and analytics."""

    def __init__(self, db: AsyncSession, tenant_id: UUID):
        self.db = db
        self.tenant_id = tenant_id

    # ========================================================================
    # REPORT DEFINITIONS
    # ========================================================================

    async def create_report(
        self,
        data: ReportDefinitionCreate,
        created_by: UUID
    ) -> ReportDefinition:
        """Create a report definition."""
        report = ReportDefinition(
            tenant_id=self.tenant_id,
            report_code=data.report_code,
            report_name=data.report_name,
            description=data.description,
            category=data.category,
            report_type=data.report_type,
            data_source=data.data_source,
            base_query=data.base_query,
            filters=data.filters,
            parameters=data.parameters,
            group_by=data.group_by,
            order_by=data.order_by,
            columns=[col.model_dump() for col in data.columns],
            calculated_fields=data.calculated_fields,
            aggregations=data.aggregations,
            default_format=data.default_format,
            available_formats=data.available_formats,
            page_size=data.page_size,
            orientation=data.orientation,
            header_template=data.header_template,
            footer_template=data.footer_template,
            include_charts=data.include_charts,
            chart_config=data.chart_config,
            is_public=data.is_public,
            roles=data.roles,
            warehouse_ids=data.warehouse_ids,
            created_by=created_by
        )

        self.db.add(report)
        await self.db.commit()
        await self.db.refresh(report)
        return report

    async def get_report(self, report_id: UUID) -> Optional[ReportDefinition]:
        """Get a report definition by ID."""
        result = await self.db.execute(
            select(ReportDefinition).where(
                ReportDefinition.id == report_id,
                ReportDefinition.tenant_id == self.tenant_id
            )
        )
        return result.scalar_one_or_none()

    async def list_reports(
        self,
        category: Optional[ReportCategory] = None,
        report_type: Optional[ReportType] = None,
        is_active: Optional[bool] = True,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[ReportDefinition], int]:
        """List report definitions."""
        query = select(ReportDefinition).where(
            ReportDefinition.tenant_id == self.tenant_id
        )

        if category:
            query = query.where(ReportDefinition.category == category)
        if report_type:
            query = query.where(ReportDefinition.report_type == report_type)
        if is_active is not None:
            query = query.where(ReportDefinition.is_active == is_active)

        # Count
        count_query = select(func.count()).select_from(query.subquery())
        total = await self.db.scalar(count_query)

        # Paginate
        query = query.order_by(ReportDefinition.report_name)
        query = query.offset(skip).limit(limit)

        result = await self.db.execute(query)
        reports = result.scalars().all()

        return list(reports), total or 0

    async def update_report(
        self,
        report_id: UUID,
        data: ReportDefinitionUpdate
    ) -> Optional[ReportDefinition]:
        """Update a report definition."""
        report = await self.get_report(report_id)
        if not report:
            return None

        update_data = data.model_dump(exclude_unset=True)
        if 'columns' in update_data:
            update_data['columns'] = [col.model_dump() for col in data.columns]

        for field, value in update_data.items():
            setattr(report, field, value)

        await self.db.commit()
        await self.db.refresh(report)
        return report

    # ========================================================================
    # REPORT SCHEDULES
    # ========================================================================

    async def create_schedule(
        self,
        data: ReportScheduleCreate,
        created_by: UUID
    ) -> ReportSchedule:
        """Create a report schedule."""
        # Calculate next run time
        next_run = self._calculate_next_run(data)

        schedule = ReportSchedule(
            tenant_id=self.tenant_id,
            report_id=data.report_id,
            schedule_name=data.schedule_name,
            frequency=data.frequency,
            cron_expression=data.cron_expression,
            run_time=data.run_time,
            day_of_week=data.day_of_week,
            day_of_month=data.day_of_month,
            timezone=data.timezone,
            parameters=data.parameters,
            output_format=data.output_format,
            date_range=data.date_range,
            email_to=data.email_to,
            email_cc=data.email_cc,
            email_subject=data.email_subject,
            email_body=data.email_body,
            upload_to_sftp=data.upload_to_sftp,
            sftp_config=data.sftp_config,
            webhook_url=data.webhook_url,
            next_run_at=next_run,
            created_by=created_by
        )

        self.db.add(schedule)
        await self.db.commit()
        await self.db.refresh(schedule)
        return schedule

    async def get_schedule(self, schedule_id: UUID) -> Optional[ReportSchedule]:
        """Get a report schedule by ID."""
        result = await self.db.execute(
            select(ReportSchedule).where(
                ReportSchedule.id == schedule_id,
                ReportSchedule.tenant_id == self.tenant_id
            )
        )
        return result.scalar_one_or_none()

    async def list_schedules(
        self,
        report_id: Optional[UUID] = None,
        is_active: Optional[bool] = True,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[ReportSchedule], int]:
        """List report schedules."""
        query = select(ReportSchedule).where(
            ReportSchedule.tenant_id == self.tenant_id
        )

        if report_id:
            query = query.where(ReportSchedule.report_id == report_id)
        if is_active is not None:
            query = query.where(ReportSchedule.is_active == is_active)

        # Count
        count_query = select(func.count()).select_from(query.subquery())
        total = await self.db.scalar(count_query)

        # Paginate
        query = query.order_by(ReportSchedule.next_run_at)
        query = query.offset(skip).limit(limit)

        result = await self.db.execute(query)
        schedules = result.scalars().all()

        return list(schedules), total or 0

    def _calculate_next_run(self, data: ReportScheduleCreate) -> datetime:
        """Calculate next run time for a schedule."""
        now = datetime.utcnow()
        hour, minute = map(int, data.run_time.split(':'))
        next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

        if next_run <= now:
            next_run += timedelta(days=1)

        if data.frequency == ReportFrequency.WEEKLY and data.day_of_week is not None:
            days_ahead = data.day_of_week - next_run.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            next_run += timedelta(days=days_ahead)
        elif data.frequency == ReportFrequency.MONTHLY and data.day_of_month is not None:
            next_run = next_run.replace(day=min(data.day_of_month, 28))
            if next_run <= now:
                if next_run.month == 12:
                    next_run = next_run.replace(year=next_run.year + 1, month=1)
                else:
                    next_run = next_run.replace(month=next_run.month + 1)

        return next_run

    # ========================================================================
    # REPORT EXECUTION
    # ========================================================================

    async def execute_report(
        self,
        data: ReportExecuteRequest,
        run_by: UUID
    ) -> ReportExecution:
        """Execute a report."""
        report = await self.get_report(data.report_id)
        if not report:
            raise ValueError("Report not found")

        # Generate execution number
        today = date.today()
        count_result = await self.db.execute(
            select(func.count()).select_from(ReportExecution).where(
                ReportExecution.tenant_id == self.tenant_id,
                func.date(ReportExecution.created_at) == today
            )
        )
        count = count_result.scalar() or 0
        execution_number = f"RPT-{today.strftime('%Y%m%d')}-{count + 1:04d}"

        execution = ReportExecution(
            tenant_id=self.tenant_id,
            report_id=data.report_id,
            execution_number=execution_number,
            output_format=data.output_format,
            parameters=data.parameters,
            date_range_start=data.date_range_start,
            date_range_end=data.date_range_end,
            status=ReportStatus.RUNNING,
            triggered_by="manual",
            run_by=run_by
        )

        self.db.add(execution)
        await self.db.commit()

        # Execute report generation (simplified - in production would be async job)
        try:
            # In real implementation, this would generate the actual report
            execution.status = ReportStatus.COMPLETED
            execution.completed_at = datetime.utcnow()
            execution.duration_seconds = int(
                (execution.completed_at - execution.started_at).total_seconds()
            )
            execution.row_count = 0  # Would be actual count
            execution.file_name = f"{report.report_code}_{execution_number}.{data.output_format.value}"

            # Send email if requested
            if data.email_to:
                execution.emailed_to = data.email_to
                execution.emailed_at = datetime.utcnow()
                execution.email_status = "sent"

        except Exception as e:
            execution.status = ReportStatus.FAILED
            execution.error_message = str(e)

        await self.db.commit()
        await self.db.refresh(execution)
        return execution

    async def list_executions(
        self,
        report_id: Optional[UUID] = None,
        status: Optional[ReportStatus] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[ReportExecution], int]:
        """List report executions."""
        query = select(ReportExecution).where(
            ReportExecution.tenant_id == self.tenant_id
        )

        if report_id:
            query = query.where(ReportExecution.report_id == report_id)
        if status:
            query = query.where(ReportExecution.status == status)
        if from_date:
            query = query.where(func.date(ReportExecution.started_at) >= from_date)
        if to_date:
            query = query.where(func.date(ReportExecution.started_at) <= to_date)

        # Count
        count_query = select(func.count()).select_from(query.subquery())
        total = await self.db.scalar(count_query)

        # Paginate
        query = query.order_by(ReportExecution.started_at.desc())
        query = query.offset(skip).limit(limit)

        result = await self.db.execute(query)
        executions = result.scalars().all()

        return list(executions), total or 0

    # ========================================================================
    # KPIs
    # ========================================================================

    async def create_kpi(
        self,
        data: KPIDefinitionCreate,
        created_by: UUID
    ) -> KPIDefinition:
        """Create a KPI definition."""
        kpi = KPIDefinition(
            tenant_id=self.tenant_id,
            warehouse_id=data.warehouse_id,
            kpi_code=data.kpi_code,
            kpi_name=data.kpi_name,
            description=data.description,
            category=data.category,
            data_source=data.data_source,
            calculation_formula=data.calculation_formula,
            aggregation_type=data.aggregation_type,
            unit=data.unit,
            decimal_places=data.decimal_places,
            target_value=data.target_value,
            warning_threshold=data.warning_threshold,
            critical_threshold=data.critical_threshold,
            higher_is_better=data.higher_is_better,
            industry_benchmark=data.industry_benchmark,
            internal_benchmark=data.internal_benchmark,
            display_order=data.display_order,
            show_on_dashboard=data.show_on_dashboard,
            chart_type=data.chart_type,
            created_by=created_by
        )

        self.db.add(kpi)
        await self.db.commit()
        await self.db.refresh(kpi)
        return kpi

    async def get_kpi(self, kpi_id: UUID) -> Optional[KPIDefinition]:
        """Get a KPI definition by ID."""
        result = await self.db.execute(
            select(KPIDefinition).where(
                KPIDefinition.id == kpi_id,
                KPIDefinition.tenant_id == self.tenant_id
            )
        )
        return result.scalar_one_or_none()

    async def list_kpis(
        self,
        category: Optional[KPICategory] = None,
        warehouse_id: Optional[UUID] = None,
        show_on_dashboard: Optional[bool] = None,
        is_active: Optional[bool] = True,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[KPIDefinition], int]:
        """List KPI definitions."""
        query = select(KPIDefinition).where(
            KPIDefinition.tenant_id == self.tenant_id
        )

        if category:
            query = query.where(KPIDefinition.category == category)
        if warehouse_id:
            query = query.where(
                or_(
                    KPIDefinition.warehouse_id == warehouse_id,
                    KPIDefinition.warehouse_id.is_(None)
                )
            )
        if show_on_dashboard is not None:
            query = query.where(KPIDefinition.show_on_dashboard == show_on_dashboard)
        if is_active is not None:
            query = query.where(KPIDefinition.is_active == is_active)

        # Count
        count_query = select(func.count()).select_from(query.subquery())
        total = await self.db.scalar(count_query)

        # Paginate
        query = query.order_by(KPIDefinition.display_order, KPIDefinition.kpi_name)
        query = query.offset(skip).limit(limit)

        result = await self.db.execute(query)
        kpis = result.scalars().all()

        return list(kpis), total or 0

    async def get_kpi_with_value(
        self,
        kpi_id: UUID,
        warehouse_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """Get KPI with current value."""
        kpi = await self.get_kpi(kpi_id)
        if not kpi:
            return None

        # Get latest snapshot
        snapshot_query = select(KPISnapshot).where(
            KPISnapshot.kpi_id == kpi_id,
            KPISnapshot.tenant_id == self.tenant_id
        )
        if warehouse_id:
            snapshot_query = snapshot_query.where(KPISnapshot.warehouse_id == warehouse_id)
        snapshot_query = snapshot_query.order_by(KPISnapshot.snapshot_date.desc()).limit(1)

        snapshot_result = await self.db.execute(snapshot_query)
        snapshot = snapshot_result.scalar_one_or_none()

        result = {
            **kpi.__dict__,
            "current_value": snapshot.current_value if snapshot else None,
            "previous_value": snapshot.previous_value if snapshot else None,
            "change_percent": snapshot.change_percent if snapshot else None,
            "trend_direction": snapshot.trend_direction if snapshot else None,
            "is_on_target": snapshot.is_on_target if snapshot else None,
            "is_warning": snapshot.is_warning if snapshot else None,
            "is_critical": snapshot.is_critical if snapshot else None
        }
        return result

    # ========================================================================
    # DASHBOARD WIDGETS
    # ========================================================================

    async def create_widget(self, data: DashboardWidgetCreate) -> DashboardWidget:
        """Create a dashboard widget."""
        widget = DashboardWidget(
            tenant_id=self.tenant_id,
            dashboard_id=data.dashboard_id,
            widget_type=data.widget_type,
            title=data.title,
            data_source=data.data_source,
            kpi_id=data.kpi_id,
            report_id=data.report_id,
            query=data.query,
            parameters=data.parameters,
            position_x=data.position_x,
            position_y=data.position_y,
            width=data.width,
            height=data.height,
            chart_type=data.chart_type,
            chart_config=data.chart_config,
            color_scheme=data.color_scheme,
            refresh_interval_seconds=data.refresh_interval_seconds
        )

        self.db.add(widget)
        await self.db.commit()
        await self.db.refresh(widget)
        return widget

    async def list_widgets(
        self,
        dashboard_id: UUID
    ) -> List[DashboardWidget]:
        """List widgets for a dashboard."""
        result = await self.db.execute(
            select(DashboardWidget).where(
                DashboardWidget.tenant_id == self.tenant_id,
                DashboardWidget.dashboard_id == dashboard_id,
                DashboardWidget.is_visible == True
            ).order_by(DashboardWidget.position_y, DashboardWidget.position_x)
        )
        return list(result.scalars().all())

    # ========================================================================
    # ALERT RULES
    # ========================================================================

    async def create_alert_rule(
        self,
        data: AlertRuleCreate,
        created_by: UUID
    ) -> AlertRule:
        """Create an alert rule."""
        rule = AlertRule(
            tenant_id=self.tenant_id,
            warehouse_id=data.warehouse_id,
            rule_name=data.rule_name,
            description=data.description,
            category=data.category,
            kpi_id=data.kpi_id,
            metric=data.metric,
            condition=data.condition,
            threshold_value=data.threshold_value,
            evaluation_window_minutes=data.evaluation_window_minutes,
            severity=data.severity,
            notification_channels=data.notification_channels,
            notify_users=data.notify_users,
            notify_emails=data.notify_emails,
            cooldown_minutes=data.cooldown_minutes,
            max_alerts_per_day=data.max_alerts_per_day,
            created_by=created_by
        )

        self.db.add(rule)
        await self.db.commit()
        await self.db.refresh(rule)
        return rule

    async def list_alert_rules(
        self,
        warehouse_id: Optional[UUID] = None,
        category: Optional[str] = None,
        is_active: Optional[bool] = True,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[AlertRule], int]:
        """List alert rules."""
        query = select(AlertRule).where(AlertRule.tenant_id == self.tenant_id)

        if warehouse_id:
            query = query.where(
                or_(
                    AlertRule.warehouse_id == warehouse_id,
                    AlertRule.warehouse_id.is_(None)
                )
            )
        if category:
            query = query.where(AlertRule.category == category)
        if is_active is not None:
            query = query.where(AlertRule.is_active == is_active)

        # Count
        count_query = select(func.count()).select_from(query.subquery())
        total = await self.db.scalar(count_query)

        # Paginate
        query = query.order_by(AlertRule.rule_name)
        query = query.offset(skip).limit(limit)

        result = await self.db.execute(query)
        rules = result.scalars().all()

        return list(rules), total or 0

    # ========================================================================
    # ANALYTICS DASHBOARDS
    # ========================================================================

    async def get_analytics_dashboard(
        self,
        warehouse_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """Get analytics dashboard data."""
        today = date.today()
        month_start = today.replace(day=1)

        # Get KPIs
        kpis, _ = await self.list_kpis(
            warehouse_id=warehouse_id,
            show_on_dashboard=True
        )
        kpi_data = []
        for kpi in kpis:
            kpi_with_value = await self.get_kpi_with_value(kpi.id, warehouse_id)
            if kpi_with_value:
                kpi_data.append(kpi_with_value)

        # Get operations summary
        ops_result = await self.db.execute(
            select(OperationsSnapshot).where(
                OperationsSnapshot.tenant_id == self.tenant_id,
                OperationsSnapshot.snapshot_date == today,
                OperationsSnapshot.warehouse_id == warehouse_id if warehouse_id else True
            ).limit(1)
        )
        ops_today = ops_result.scalar_one_or_none()

        # Get inventory summary
        inv_result = await self.db.execute(
            select(
                func.sum(InventorySummary.available_quantity * InventorySummary.available_quantity).label('total_value'),
                func.count(func.distinct(InventorySummary.product_id)).label('sku_count')
            ).where(
                InventorySummary.tenant_id == self.tenant_id,
                InventorySummary.warehouse_id == warehouse_id if warehouse_id else True
            )
        )
        inv_stats = inv_result.one()

        # Get order counts
        orders_result = await self.db.execute(
            select(
                func.count().filter(Order.status == OrderStatus.PENDING).label('pending'),
                func.count().filter(Order.status == OrderStatus.PROCESSING).label('in_progress'),
                func.count().filter(
                    and_(
                        Order.status == OrderStatus.DELIVERED,
                        func.date(Order.updated_at) == today
                    )
                ).label('completed_today')
            ).where(
                Order.tenant_id == self.tenant_id
            )
        )
        order_stats = orders_result.one()

        return {
            "kpis": kpi_data,
            "operations_today": ops_today,
            "operations_mtd": {},
            "total_inventory_value": inv_stats.total_value or Decimal("0"),
            "total_sku_count": inv_stats.sku_count or 0,
            "low_stock_items": 0,
            "overstock_items": 0,
            "orders_pending": order_stats.pending or 0,
            "orders_in_progress": order_stats.in_progress or 0,
            "orders_completed_today": order_stats.completed_today or 0,
            "fulfillment_rate": None,
            "orders_trend": [],
            "inventory_trend": [],
            "picking_trend": [],
            "top_moving_items": [],
            "slowest_moving_items": [],
            "active_alerts": []
        }

    async def get_inventory_analytics(
        self,
        warehouse_id: Optional[UUID] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """Get inventory analytics."""
        if not from_date:
            from_date = date.today() - timedelta(days=30)
        if not to_date:
            to_date = date.today()

        # Basic inventory stats
        inv_result = await self.db.execute(
            select(
                func.sum(InventorySummary.available_quantity).label('total_units'),
                func.count(func.distinct(InventorySummary.product_id)).label('sku_count')
            ).where(
                InventorySummary.tenant_id == self.tenant_id,
                InventorySummary.warehouse_id == warehouse_id if warehouse_id else True
            )
        )
        inv_stats = inv_result.one()

        return {
            "total_value": Decimal("0"),
            "total_sku_count": inv_stats.sku_count or 0,
            "total_units": inv_stats.total_units or 0,
            "healthy_stock": 0,
            "low_stock": 0,
            "out_of_stock": 0,
            "overstock": 0,
            "aging_0_30": Decimal("0"),
            "aging_31_60": Decimal("0"),
            "aging_61_90": Decimal("0"),
            "aging_over_90": Decimal("0"),
            "abc_distribution": {"A": 0, "B": 0, "C": 0},
            "average_turn_rate": None,
            "turn_rate_by_category": [],
            "by_warehouse": [],
            "by_category": []
        }

    async def get_fulfillment_analytics(
        self,
        warehouse_id: Optional[UUID] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """Get fulfillment analytics."""
        if not to_date:
            to_date = date.today()
        if not from_date:
            from_date = to_date

        # Order stats for today
        orders_result = await self.db.execute(
            select(
                func.count().filter(func.date(Order.created_at) == to_date).label('received'),
                func.count().filter(Order.status == OrderStatus.PENDING).label('pending'),
                func.count().filter(
                    and_(
                        Order.status == OrderStatus.DELIVERED,
                        func.date(Order.updated_at) == to_date
                    )
                ).label('shipped')
            ).where(Order.tenant_id == self.tenant_id)
        )
        order_stats = orders_result.one()

        return {
            "orders_received": order_stats.received or 0,
            "orders_shipped": order_stats.shipped or 0,
            "orders_pending": order_stats.pending or 0,
            "on_time_rate": None,
            "avg_cycle_time_hours": None,
            "pick_to_ship_hours": None,
            "picking_accuracy": None,
            "shipping_accuracy": None,
            "by_channel": [],
            "by_carrier": [],
            "exceptions_count": 0,
            "exceptions_by_type": {},
            "daily_volume": [],
            "hourly_volume": []
        }

    async def get_labor_analytics(
        self,
        warehouse_id: Optional[UUID] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """Get labor analytics."""
        return {
            "total_workers": 0,
            "workers_present": 0,
            "attendance_rate": None,
            "picks_per_hour": None,
            "units_per_hour": None,
            "orders_per_hour": None,
            "labor_utilization": None,
            "productive_hours": Decimal("0"),
            "idle_hours": Decimal("0"),
            "by_task_type": [],
            "top_performers": [],
            "productivity_trend": []
        }

    # ========================================================================
    # SNAPSHOT GENERATION
    # ========================================================================

    async def generate_daily_snapshots(
        self,
        warehouse_id: UUID,
        snapshot_date: Optional[date] = None
    ) -> Dict[str, int]:
        """Generate daily inventory and operations snapshots."""
        if not snapshot_date:
            snapshot_date = date.today() - timedelta(days=1)

        counts = {
            "inventory_snapshots": 0,
            "operations_snapshots": 0,
            "kpi_snapshots": 0
        }

        # Generate inventory snapshots
        inventory_result = await self.db.execute(
            select(InventorySummary).where(
                InventorySummary.tenant_id == self.tenant_id,
                InventorySummary.warehouse_id == warehouse_id
            )
        )
        for inv in inventory_result.scalars():
            snapshot = InventorySnapshot(
                tenant_id=self.tenant_id,
                warehouse_id=warehouse_id,
                product_id=inv.product_id,
                snapshot_date=snapshot_date,
                on_hand_qty=inv.available_quantity + inv.reserved_quantity,
                available_qty=inv.available_quantity,
                reserved_qty=inv.reserved_quantity
            )
            self.db.add(snapshot)
            counts["inventory_snapshots"] += 1

        # Generate operations snapshot (simplified)
        ops_snapshot = OperationsSnapshot(
            tenant_id=self.tenant_id,
            warehouse_id=warehouse_id,
            snapshot_date=snapshot_date
        )
        self.db.add(ops_snapshot)
        counts["operations_snapshots"] = 1

        await self.db.commit()
        return counts
