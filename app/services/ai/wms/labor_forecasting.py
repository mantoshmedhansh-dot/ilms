"""
WMS Labor Forecasting Agent

Forecasts warehouse labor requirements using time-series analysis:
- Holt-Winters on order volumes (reuses triple exponential smoothing pattern)
- Maps forecasted volume to labor hours via LaborStandard baselines
- Day-of-week seasonality patterns
- Shift staffing output with worker allocation

No external ML libraries required - pure Python implementation.
"""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import List, Dict, Optional, Tuple, Any
from uuid import UUID
import math
from collections import defaultdict

from sqlalchemy import select, func, and_, or_, desc, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order, OrderItem, OrderStatus
from app.models.wms_advanced import WarehouseTask, TaskType, TaskStatus
from app.models.labor import (
    WarehouseWorker, WorkShift, LaborStandard, ProductivityMetric,
    WorkerStatus, ShiftType, ShiftStatus,
)
from app.models.warehouse import Warehouse


class WMSLaborForecastingAgent:
    """
    Forecasts warehouse labor requirements using time-series methods.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self._status = "idle"
        self._last_run = None
        self._results = None

    # ==================== Triple Exponential Smoothing ====================

    def _triple_exponential_smoothing(
        self,
        data: List[float],
        season_length: int = 7,
        alpha: float = 0.3,
        beta: float = 0.1,
        gamma: float = 0.2,
        forecast_periods: int = 14,
    ) -> Tuple[List[float], List[float], List[float]]:
        """
        Holt-Winters Triple Exponential Smoothing for seasonal data.
        Returns: (fitted_values, forecasts, confidence_intervals)
        """
        if len(data) < season_length * 2:
            return self._simple_forecast(data, forecast_periods)

        n = len(data)

        # Initialize level, trend, and seasonality
        level = sum(data[:season_length]) / season_length
        trend = (
            sum(data[season_length:2 * season_length]) - sum(data[:season_length])
        ) / (season_length ** 2)

        # Initial seasonal indices
        seasonals = []
        for i in range(season_length):
            seasonals.append(data[i] / level if level > 0 else 1.0)

        fitted = []

        # Fit the model
        for i in range(n):
            if i >= season_length:
                old_level = level
                level = alpha * (data[i] / seasonals[i % season_length]) + (1 - alpha) * (level + trend)
                trend = beta * (level - old_level) + (1 - beta) * trend
                seasonals[i % season_length] = gamma * (data[i] / level) + (1 - gamma) * seasonals[i % season_length]

            fitted.append((level + trend) * seasonals[i % season_length])

        # Generate forecasts
        forecasts = []
        for i in range(forecast_periods):
            forecast = (level + (i + 1) * trend) * seasonals[(n + i) % season_length]
            forecasts.append(max(0, forecast))

        # Calculate confidence intervals
        residuals = [abs(data[i] - fitted[i]) for i in range(len(fitted))]
        std_dev = (sum(r ** 2 for r in residuals) / len(residuals)) ** 0.5 if residuals else 0

        confidence = []
        for i, f in enumerate(forecasts):
            interval = std_dev * (1 + 0.1 * i) * 1.96
            confidence.append(interval)

        return fitted, forecasts, confidence

    def _simple_forecast(
        self, data: List[float], forecast_periods: int
    ) -> Tuple[List[float], List[float], List[float]]:
        """Fallback for insufficient data."""
        if not data:
            return [], [0] * forecast_periods, [0] * forecast_periods

        avg = sum(data) / len(data)
        fitted = [avg] * len(data)
        forecasts = [avg] * forecast_periods

        std_dev = (sum((v - avg) ** 2 for v in data) / len(data)) ** 0.5 if len(data) > 1 else avg * 0.1
        confidence = [std_dev * 1.96 * (1 + 0.1 * i) for i in range(forecast_periods)]

        return fitted, forecasts, confidence

    # ==================== Historical Data Collection ====================

    async def _get_daily_order_volumes(
        self, warehouse_id: Optional[UUID] = None, days: int = 90
    ) -> List[Dict]:
        """Get daily order volumes for forecasting."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        query = (
            select(
                func.date_trunc('day', Order.created_at).label("day"),
                func.count(Order.id).label("order_count"),
                func.coalesce(func.sum(OrderItem.quantity), 0).label("total_items"),
            )
            .outerjoin(OrderItem, OrderItem.order_id == Order.id)
            .where(Order.created_at >= cutoff)
            .group_by("day")
            .order_by("day")
        )

        if warehouse_id:
            query = query.where(Order.warehouse_id == warehouse_id)

        result = await self.db.execute(query)
        rows = result.all()

        daily_data = []
        for row in rows:
            daily_data.append({
                "date": row.day,
                "order_count": int(row.order_count),
                "total_items": int(row.total_items or 0),
            })

        return daily_data

    async def _get_daily_task_volumes(
        self, warehouse_id: Optional[UUID] = None, days: int = 90
    ) -> Dict[str, List[float]]:
        """Get daily task volumes by type."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        query = (
            select(
                func.date_trunc('day', WarehouseTask.created_at).label("day"),
                WarehouseTask.task_type,
                func.count(WarehouseTask.id).label("count"),
            )
            .where(WarehouseTask.created_at >= cutoff)
            .group_by("day", WarehouseTask.task_type)
            .order_by("day")
        )

        if warehouse_id:
            query = query.where(WarehouseTask.warehouse_id == warehouse_id)

        result = await self.db.execute(query)
        rows = result.all()

        type_daily = defaultdict(list)
        for row in rows:
            type_daily[row.task_type].append(float(row.count))

        return dict(type_daily)

    # ==================== Labor Standards ====================

    async def _get_labor_standards(self, warehouse_id: Optional[UUID] = None) -> Dict[str, Dict]:
        """Get labor standards for converting volumes to hours."""
        query = select(LaborStandard)

        if warehouse_id:
            query = query.where(LaborStandard.warehouse_id == warehouse_id)

        result = await self.db.execute(query)
        standards = result.scalars().all()

        standards_map = {}
        for s in standards:
            task_type = s.task_type if hasattr(s, 'task_type') else "GENERAL"
            standards_map[task_type] = {
                "units_per_hour": float(s.units_per_hour) if hasattr(s, 'units_per_hour') and s.units_per_hour else 20.0,
                "standard_hours": float(s.standard_hours) if hasattr(s, 'standard_hours') and s.standard_hours else 8.0,
            }

        # Defaults if no standards found
        if not standards_map:
            standards_map = {
                "PICK": {"units_per_hour": 30.0, "standard_hours": 8.0},
                "PUTAWAY": {"units_per_hour": 20.0, "standard_hours": 8.0},
                "PACK": {"units_per_hour": 25.0, "standard_hours": 8.0},
                "REPLENISH": {"units_per_hour": 15.0, "standard_hours": 8.0},
                "GENERAL": {"units_per_hour": 20.0, "standard_hours": 8.0},
            }

        return standards_map

    # ==================== Workforce Analysis ====================

    async def _get_current_workforce(self, warehouse_id: Optional[UUID] = None) -> Dict:
        """Get current workforce capacity."""
        query = (
            select(
                func.count(WarehouseWorker.id).label("total_workers"),
                func.count(
                    func.nullif(WarehouseWorker.status == WorkerStatus.ACTIVE.value, False)
                ).label("active_workers"),
            )
        )

        if warehouse_id:
            query = query.where(WarehouseWorker.primary_warehouse_id == warehouse_id)

        result = await self.db.execute(query)
        row = result.one()

        return {
            "total_workers": int(row.total_workers),
            "active_workers": int(row.active_workers),
        }

    # ==================== Forecast Generation ====================

    async def _generate_labor_forecast(
        self,
        warehouse_id: Optional[UUID] = None,
        forecast_days: int = 14,
        lookback_days: int = 90,
    ) -> Dict:
        """Generate labor demand forecast."""
        daily_orders = await self._get_daily_order_volumes(warehouse_id, lookback_days)
        labor_standards = await self._get_labor_standards(warehouse_id)
        workforce = await self._get_current_workforce(warehouse_id)

        if not daily_orders:
            return {
                "forecast": [],
                "summary": {"message": "Insufficient historical data for forecasting"},
            }

        # Extract order counts for time-series
        order_counts = [d["order_count"] for d in daily_orders]
        item_counts = [d["total_items"] for d in daily_orders]

        # Run Holt-Winters
        _, order_forecast, order_ci = self._triple_exponential_smoothing(
            order_counts, season_length=7, forecast_periods=forecast_days
        )
        _, item_forecast, item_ci = self._triple_exponential_smoothing(
            item_counts, season_length=7, forecast_periods=forecast_days
        )

        # Day-of-week pattern (from historical data)
        dow_pattern = defaultdict(list)
        for d in daily_orders:
            if d["date"]:
                dow = d["date"].weekday() if hasattr(d["date"], 'weekday') else 0
                dow_pattern[dow].append(d["order_count"])

        dow_avg = {}
        for dow, counts in dow_pattern.items():
            dow_avg[dow] = sum(counts) / len(counts)

        # Map forecast to labor hours
        pick_standard = labor_standards.get("PICK", labor_standards.get("GENERAL", {}))
        units_per_hour = pick_standard.get("units_per_hour", 20.0)
        shift_hours = pick_standard.get("standard_hours", 8.0)

        forecast_data = []
        today = date.today()
        total_hours_needed = 0
        total_workers_needed = 0

        for i in range(forecast_days):
            forecast_date = today + timedelta(days=i + 1)
            dow = forecast_date.weekday()
            day_name = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][dow]

            forecasted_orders = max(0, order_forecast[i])
            forecasted_items = max(0, item_forecast[i])

            # Apply DOW adjustment
            overall_avg = sum(order_counts) / len(order_counts) if order_counts else 1
            dow_factor = dow_avg.get(dow, overall_avg) / overall_avg if overall_avg > 0 else 1.0
            adjusted_items = forecasted_items * dow_factor

            # Calculate labor hours needed
            pick_hours = adjusted_items / units_per_hour
            pack_hours = adjusted_items / labor_standards.get("PACK", {}).get("units_per_hour", 25.0)
            putaway_hours = adjusted_items * 0.3 / labor_standards.get("PUTAWAY", {}).get("units_per_hour", 20.0)
            total_hours = pick_hours + pack_hours + putaway_hours

            # Workers needed
            workers_needed = math.ceil(total_hours / shift_hours)
            total_hours_needed += total_hours
            total_workers_needed += workers_needed

            # Shift staffing
            morning_pct = 0.5 if dow < 5 else 0.6
            afternoon_pct = 0.35 if dow < 5 else 0.3
            night_pct = 0.15 if dow < 5 else 0.1

            forecast_data.append({
                "date": forecast_date.isoformat(),
                "day_of_week": day_name,
                "forecasted_orders": round(forecasted_orders),
                "forecasted_items": round(adjusted_items),
                "confidence_interval": round(item_ci[i], 1),
                "labor_hours_needed": round(total_hours, 1),
                "workers_needed": workers_needed,
                "shift_staffing": {
                    "morning": math.ceil(workers_needed * morning_pct),
                    "afternoon": math.ceil(workers_needed * afternoon_pct),
                    "night": math.ceil(workers_needed * night_pct),
                },
                "pick_hours": round(pick_hours, 1),
                "pack_hours": round(pack_hours, 1),
                "capacity_utilization": round(
                    workers_needed / max(workforce["active_workers"], 1) * 100, 1
                ),
            })

        return {
            "forecast": forecast_data,
            "summary": {
                "forecast_days": forecast_days,
                "avg_daily_orders": round(sum(order_forecast) / len(order_forecast), 1) if order_forecast else 0,
                "avg_daily_items": round(sum(item_forecast) / len(item_forecast), 1) if item_forecast else 0,
                "avg_daily_hours": round(total_hours_needed / forecast_days, 1),
                "avg_workers_needed": round(total_workers_needed / forecast_days, 1),
                "current_workforce": workforce["active_workers"],
                "gap": round(total_workers_needed / forecast_days - workforce["active_workers"], 1),
                "peak_day": max(forecast_data, key=lambda x: x["workers_needed"])["date"] if forecast_data else None,
                "peak_workers": max(f["workers_needed"] for f in forecast_data) if forecast_data else 0,
            },
            "day_of_week_pattern": {
                ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"][k]: round(v, 1)
                for k, v in dow_avg.items()
            },
        }

    # ==================== Public Interface ====================

    async def analyze(
        self,
        warehouse_id: Optional[UUID] = None,
        forecast_days: int = 14,
        lookback_days: int = 90,
    ) -> Dict:
        """Run labor forecasting analysis."""
        self._status = "running"
        try:
            forecast = await self._generate_labor_forecast(
                warehouse_id, forecast_days, lookback_days
            )

            self._results = {
                "agent": "labor_forecasting",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "warehouse_id": str(warehouse_id) if warehouse_id else "all",
                **forecast,
            }
            self._status = "completed"
            self._last_run = datetime.now(timezone.utc)
            return self._results

        except Exception as e:
            self._status = "error"
            return {"agent": "labor_forecasting", "error": str(e), "status": "error"}

    async def get_recommendations(self) -> List[Dict]:
        """Get staffing recommendations."""
        if not self._results or "summary" not in self._results:
            return []

        summary = self._results["summary"]
        recs = []

        gap = summary.get("gap", 0)
        if gap > 0:
            recs.append({
                "type": "understaffed",
                "severity": "HIGH" if gap > 5 else "MEDIUM",
                "recommendation": f"Hire or schedule {math.ceil(gap)} additional workers. "
                                f"Current: {summary['current_workforce']}, Needed: {round(summary['avg_workers_needed'])}",
            })
        elif gap < -3:
            recs.append({
                "type": "overstaffed",
                "severity": "LOW",
                "recommendation": f"Consider reducing shifts. "
                                f"Excess capacity: {abs(round(gap))} workers above forecast need",
            })

        peak = summary.get("peak_workers", 0)
        current = summary.get("current_workforce", 0)
        if peak > current:
            recs.append({
                "type": "peak_demand",
                "severity": "HIGH",
                "recommendation": f"Peak day ({summary.get('peak_day', 'N/A')}) needs {peak} workers "
                                f"but only {current} available. Plan overtime or temp workers.",
            })

        return recs

    async def get_status(self) -> Dict:
        """Get agent status."""
        return {
            "id": "labor_forecasting",
            "name": "Labor Forecasting Agent",
            "description": "Holt-Winters time-series forecasting for warehouse labor requirements with shift staffing output",
            "status": self._status,
            "last_run": self._last_run.isoformat() if self._last_run else None,
            "data_sources": "Order, WarehouseTask, LaborStandard, WarehouseWorker, WorkShift",
            "capabilities": [
                "Order volume forecasting",
                "Labor hours prediction",
                "Shift staffing recommendations",
                "Day-of-week seasonality",
                "Capacity gap analysis",
            ],
        }
