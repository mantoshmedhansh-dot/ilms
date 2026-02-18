"""
WMS Replenishment Agent

Monitors forward-pick bins and triggers replenishment:
- Monitors PICKING zone bin levels
- Consumption rate from WarehouseTask history
- Lead-time from REPLENISH task durations
- Trigger-based suggestions with source bin recommendations

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

from app.models.inventory import StockItem, InventorySummary
from app.models.wms_advanced import WarehouseTask, TaskType, TaskStatus
from app.models.wms import WarehouseZone, WarehouseBin, ZoneType
from app.models.warehouse import Warehouse
from app.models.product import Product


class WMSReplenishmentAgent:
    """
    Monitors forward-pick bins and recommends replenishment.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self._status = "idle"
        self._last_run = None
        self._results = None

    # ==================== Consumption Rate Analysis ====================

    async def _calculate_consumption_rates(
        self, warehouse_id: Optional[UUID] = None, days: int = 30
    ) -> Dict[str, Dict]:
        """Calculate consumption rates from pick task history."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        query = (
            select(
                WarehouseTask.product_id,
                WarehouseTask.source_bin_id,
                func.count(WarehouseTask.id).label("pick_count"),
                func.sum(WarehouseTask.quantity_completed).label("total_consumed"),
            )
            .where(
                and_(
                    WarehouseTask.task_type == TaskType.PICK.value,
                    WarehouseTask.status == TaskStatus.COMPLETED.value,
                    WarehouseTask.completed_at >= cutoff,
                    WarehouseTask.product_id.isnot(None),
                )
            )
            .group_by(WarehouseTask.product_id, WarehouseTask.source_bin_id)
        )

        if warehouse_id:
            query = query.where(WarehouseTask.warehouse_id == warehouse_id)

        result = await self.db.execute(query)
        rows = result.all()

        rates = {}
        for row in rows:
            pid = str(row.product_id)
            total = float(row.total_consumed or 0)
            daily_rate = total / days

            if pid not in rates:
                rates[pid] = {
                    "total_consumed": 0,
                    "daily_rate": 0,
                    "pick_count": 0,
                    "bins": [],
                }
            rates[pid]["total_consumed"] += total
            rates[pid]["daily_rate"] += daily_rate
            rates[pid]["pick_count"] += int(row.pick_count)
            if row.source_bin_id:
                rates[pid]["bins"].append(str(row.source_bin_id))

        return rates

    # ==================== Replenishment Lead Time ====================

    async def _calculate_replenishment_lead_times(
        self, warehouse_id: Optional[UUID] = None, days: int = 90
    ) -> Dict:
        """Calculate average replenishment task durations."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        query = (
            select(
                WarehouseTask.product_id,
                func.avg(
                    func.extract('epoch', WarehouseTask.completed_at) -
                    func.extract('epoch', WarehouseTask.started_at)
                ).label("avg_duration_secs"),
                func.count(WarehouseTask.id).label("task_count"),
            )
            .where(
                and_(
                    WarehouseTask.task_type == TaskType.REPLENISH.value,
                    WarehouseTask.status == TaskStatus.COMPLETED.value,
                    WarehouseTask.completed_at >= cutoff,
                    WarehouseTask.started_at.isnot(None),
                )
            )
            .group_by(WarehouseTask.product_id)
        )

        if warehouse_id:
            query = query.where(WarehouseTask.warehouse_id == warehouse_id)

        result = await self.db.execute(query)
        rows = result.all()

        lead_times = {}
        all_durations = []
        for row in rows:
            duration_mins = float(row.avg_duration_secs or 0) / 60
            all_durations.append(duration_mins)
            if row.product_id:
                lead_times[str(row.product_id)] = {
                    "avg_minutes": round(duration_mins, 1),
                    "task_count": int(row.task_count),
                }

        avg_lead_time = sum(all_durations) / len(all_durations) if all_durations else 30.0

        return {
            "product_lead_times": lead_times,
            "overall_avg_minutes": round(avg_lead_time, 1),
        }

    # ==================== Forward Pick Bin Status ====================

    async def _get_picking_bin_levels(self, warehouse_id: Optional[UUID] = None) -> List[Dict]:
        """Get current stock levels in PICKING zone bins."""
        # Get bins in PICKING zone
        query = (
            select(
                WarehouseBin.id.label("bin_id"),
                WarehouseBin.bin_code,
                WarehouseBin.max_capacity,
                WarehouseZone.id.label("zone_id"),
                WarehouseZone.zone_name.label("zone_name"),
                StockItem.product_id,
                func.count(StockItem.id).label("current_qty"),
            )
            .join(WarehouseZone, WarehouseBin.zone_id == WarehouseZone.id)
            .outerjoin(
                StockItem,
                and_(
                    StockItem.bin_id == WarehouseBin.id,
                    StockItem.status.in_(["AVAILABLE", "RESERVED"]),
                ),
            )
            .where(WarehouseZone.zone_type == ZoneType.PICKING.value)
            .group_by(
                WarehouseBin.id,
                WarehouseBin.bin_code,
                WarehouseBin.max_capacity,
                WarehouseZone.id,
                WarehouseZone.zone_name,
                StockItem.product_id,
            )
        )

        if warehouse_id:
            query = query.where(WarehouseZone.warehouse_id == warehouse_id)

        result = await self.db.execute(query)
        rows = result.all()

        bins = []
        for row in rows:
            max_qty = int(row.max_capacity or 100)
            current = int(row.current_qty or 0)
            fill_pct = (current / max_qty * 100) if max_qty > 0 else 0

            bins.append({
                "bin_id": str(row.bin_id),
                "bin_code": row.bin_code,
                "zone_id": str(row.zone_id),
                "zone_name": row.zone_name,
                "product_id": str(row.product_id) if row.product_id else None,
                "current_qty": current,
                "max_qty": max_qty,
                "fill_percentage": round(fill_pct, 1),
            })

        return bins

    # ==================== Source Bin Recommendations ====================

    async def _find_source_bins(
        self, product_id: str, warehouse_id: Optional[UUID] = None
    ) -> List[Dict]:
        """Find best source bins for replenishment (from STORAGE zone)."""
        query = (
            select(
                WarehouseBin.id.label("bin_id"),
                WarehouseBin.bin_code,
                WarehouseZone.zone_type,
                func.count(StockItem.id).label("available_qty"),
            )
            .join(WarehouseZone, WarehouseBin.zone_id == WarehouseZone.id)
            .join(
                StockItem,
                and_(
                    StockItem.bin_id == WarehouseBin.id,
                    StockItem.product_id == product_id,
                    StockItem.status == "AVAILABLE",
                ),
            )
            .where(WarehouseZone.zone_type == ZoneType.STORAGE.value)
            .group_by(WarehouseBin.id, WarehouseBin.bin_code, WarehouseZone.zone_type)
            .order_by(desc("available_qty"))
            .limit(5)
        )

        if warehouse_id:
            query = query.where(WarehouseZone.warehouse_id == warehouse_id)

        result = await self.db.execute(query)
        rows = result.all()

        return [
            {
                "bin_id": str(row.bin_id),
                "bin_code": row.bin_code,
                "available_qty": int(row.available_qty),
            }
            for row in rows
        ]

    # ==================== Replenishment Suggestions ====================

    async def _generate_suggestions(
        self,
        bins: List[Dict],
        consumption_rates: Dict[str, Dict],
        lead_times: Dict,
        warehouse_id: Optional[UUID] = None,
    ) -> List[Dict]:
        """Generate replenishment suggestions."""
        avg_lead_mins = lead_times.get("overall_avg_minutes", 30.0)
        product_lead_times = lead_times.get("product_lead_times", {})

        suggestions = []
        for bin_info in bins:
            pid = bin_info.get("product_id")
            if not pid:
                continue

            current = bin_info["current_qty"]
            max_qty = bin_info["max_qty"]
            fill_pct = bin_info["fill_percentage"]

            rate_info = consumption_rates.get(pid, {})
            daily_rate = rate_info.get("daily_rate", 0)

            # Calculate hours of stock remaining
            if daily_rate > 0:
                hours_remaining = (current / daily_rate) * 24
            else:
                hours_remaining = float('inf')

            # Get product-specific lead time
            lead_mins = product_lead_times.get(pid, {}).get("avg_minutes", avg_lead_mins)
            lead_hours = lead_mins / 60

            # Trigger: below 30% OR less than 2x lead time of stock
            needs_replenishment = fill_pct < 30 or hours_remaining < (lead_hours * 2)

            if not needs_replenishment:
                continue

            # Calculate replenishment qty (fill to 80% capacity)
            target_qty = int(max_qty * 0.8)
            replenish_qty = max(0, target_qty - current)

            if replenish_qty <= 0:
                continue

            # Determine urgency
            if fill_pct < 10 or hours_remaining < lead_hours:
                urgency = "CRITICAL"
            elif fill_pct < 20 or hours_remaining < lead_hours * 1.5:
                urgency = "HIGH"
            elif fill_pct < 30:
                urgency = "MEDIUM"
            else:
                urgency = "LOW"

            # Find source bins
            source_bins = await self._find_source_bins(pid, warehouse_id)

            suggestions.append({
                "product_id": pid,
                "destination_bin": bin_info["bin_code"],
                "destination_bin_id": bin_info["bin_id"],
                "zone_name": bin_info["zone_name"],
                "current_qty": current,
                "max_qty": max_qty,
                "fill_percentage": fill_pct,
                "daily_consumption_rate": round(daily_rate, 1),
                "hours_of_stock_remaining": round(hours_remaining, 1) if hours_remaining != float('inf') else None,
                "replenish_qty": replenish_qty,
                "urgency": urgency,
                "source_bins": source_bins,
                "estimated_lead_time_mins": round(lead_mins, 1),
            })

        # Sort by urgency
        urgency_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        suggestions.sort(key=lambda x: urgency_order.get(x["urgency"], 4))

        return suggestions

    # ==================== Public Interface ====================

    async def analyze(self, warehouse_id: Optional[UUID] = None, days: int = 30) -> Dict:
        """Run replenishment analysis."""
        self._status = "running"
        try:
            consumption_rates = await self._calculate_consumption_rates(warehouse_id, days)
            lead_times = await self._calculate_replenishment_lead_times(warehouse_id)
            bins = await self._get_picking_bin_levels(warehouse_id)
            suggestions = await self._generate_suggestions(
                bins, consumption_rates, lead_times, warehouse_id
            )

            # Summary
            urgency_counts = defaultdict(int)
            for s in suggestions:
                urgency_counts[s["urgency"]] += 1

            self._results = {
                "agent": "replenishment",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "warehouse_id": str(warehouse_id) if warehouse_id else "all",
                "analysis_period_days": days,
                "summary": {
                    "total_picking_bins": len(bins),
                    "bins_needing_replenishment": len(suggestions),
                    "by_urgency": dict(urgency_counts),
                    "avg_replenishment_lead_time_mins": lead_times["overall_avg_minutes"],
                    "products_tracked": len(consumption_rates),
                },
                "suggestions": suggestions[:30],
                "consumption_rates": {
                    k: {"daily_rate": v["daily_rate"], "total_consumed": v["total_consumed"]}
                    for k, v in list(consumption_rates.items())[:20]
                },
            }
            self._status = "completed"
            self._last_run = datetime.now(timezone.utc)
            return self._results

        except Exception as e:
            self._status = "error"
            return {"agent": "replenishment", "error": str(e), "status": "error"}

    async def get_recommendations(self) -> List[Dict]:
        """Get replenishment recommendations."""
        if not self._results:
            return []
        return [
            {
                "type": "replenishment",
                "severity": s["urgency"],
                "product_id": s["product_id"],
                "recommendation": f"Replenish {s['replenish_qty']} units to bin {s['destination_bin']}. "
                                f"Current: {s['current_qty']}/{s['max_qty']} ({s['fill_percentage']}%). "
                                f"{'Stock out imminent!' if s['urgency'] == 'CRITICAL' else ''}",
            }
            for s in self._results.get("suggestions", [])[:20]
        ]

    async def get_status(self) -> Dict:
        """Get agent status."""
        return {
            "id": "replenishment",
            "name": "Replenishment Agent",
            "description": "Monitors forward-pick bins, tracks consumption rates, and triggers replenishment with source bin recommendations",
            "status": self._status,
            "last_run": self._last_run.isoformat() if self._last_run else None,
            "data_sources": "WarehouseTask, StockItem, WarehouseBin, WarehouseZone",
            "capabilities": [
                "Forward-pick bin monitoring",
                "Consumption rate tracking",
                "Replenishment lead-time analysis",
                "Source bin recommendations",
                "Urgency-based prioritization",
            ],
        }
