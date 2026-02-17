"""
WMS Anomaly Detection Agent

Detects anomalies in warehouse operations using z-score analysis:
- Pick rate anomalies (unusually high/low pick rates per zone/worker)
- Inventory discrepancies (StockItem vs InventorySummary mismatches)
- Unusual StockMovement volumes (spikes or drops)
- Unexpected variances from cycle counts

No external ML libraries required - pure Python implementation.
"""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import List, Dict, Optional, Tuple, Any
from uuid import UUID
import math
from collections import defaultdict

from sqlalchemy import select, func, and_, or_, desc, text, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.inventory import StockItem, InventorySummary, StockMovement, StockMovementType
from app.models.wms_advanced import WarehouseTask, TaskType, TaskStatus, SlotScore
from app.models.wms import WarehouseZone, WarehouseBin
from app.models.warehouse import Warehouse
from app.models.cycle_count import InventoryVariance, CountTask
from app.models.labor import WarehouseWorker, ProductivityMetric


class WMSAnomalyDetectionAgent:
    """
    Detects anomalies in warehouse operations using statistical methods.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self._status = "idle"
        self._last_run = None
        self._results = None

    # ==================== Core Analysis ====================

    def _z_score(self, value: float, mean: float, std_dev: float) -> float:
        """Calculate z-score for a value."""
        if std_dev == 0:
            return 0.0
        return (value - mean) / std_dev

    def _detect_outliers(self, values: List[float], threshold: float = 2.5) -> List[Dict]:
        """Detect outliers using z-score method."""
        if len(values) < 3:
            return []

        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        std_dev = math.sqrt(variance) if variance > 0 else 0

        outliers = []
        for i, v in enumerate(values):
            z = self._z_score(v, mean, std_dev)
            if abs(z) > threshold:
                outliers.append({
                    "index": i,
                    "value": v,
                    "z_score": round(z, 2),
                    "mean": round(mean, 2),
                    "std_dev": round(std_dev, 2),
                    "direction": "high" if z > 0 else "low",
                })
        return outliers

    # ==================== Pick Rate Analysis ====================

    async def _analyze_pick_rates(self, warehouse_id: Optional[UUID] = None, days: int = 30) -> Dict:
        """Analyze pick rates for anomalies by zone and worker."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        # Get completed pick tasks with timing
        query = (
            select(
                WarehouseTask.zone_id,
                WarehouseTask.assigned_to,
                func.count(WarehouseTask.id).label("task_count"),
                func.sum(WarehouseTask.quantity_completed).label("total_picked"),
            )
            .where(
                and_(
                    WarehouseTask.task_type == TaskType.PICK.value,
                    WarehouseTask.status == TaskStatus.COMPLETED.value,
                    WarehouseTask.completed_at >= cutoff,
                )
            )
            .group_by(WarehouseTask.zone_id, WarehouseTask.assigned_to)
        )

        if warehouse_id:
            query = query.where(WarehouseTask.warehouse_id == warehouse_id)

        result = await self.db.execute(query)
        rows = result.all()

        # Group by zone for z-score analysis
        zone_picks = defaultdict(list)
        worker_picks = defaultdict(list)
        for row in rows:
            picks = float(row.total_picked or 0)
            if row.zone_id:
                zone_picks[str(row.zone_id)].append(picks)
            if row.assigned_to:
                worker_picks[str(row.assigned_to)].append(picks)

        anomalies = []

        # Detect zone-level anomalies
        all_zone_totals = [sum(picks) for picks in zone_picks.values()]
        zone_outliers = self._detect_outliers(all_zone_totals)
        zone_ids = list(zone_picks.keys())
        for outlier in zone_outliers:
            idx = outlier["index"]
            if idx < len(zone_ids):
                anomalies.append({
                    "type": "pick_rate_zone",
                    "severity": "HIGH" if abs(outlier["z_score"]) > 3 else "MEDIUM",
                    "zone_id": zone_ids[idx],
                    "details": f"Zone pick volume is {outlier['direction']} (z={outlier['z_score']}). "
                              f"Total: {outlier['value']:.0f}, Mean: {outlier['mean']:.0f}",
                    "z_score": outlier["z_score"],
                    "recommended_action": "Investigate zone workload distribution" if outlier["direction"] == "high"
                                        else "Check if zone has stock issues or access problems",
                })

        # Detect worker-level anomalies
        all_worker_totals = [sum(picks) for picks in worker_picks.values()]
        worker_outliers = self._detect_outliers(all_worker_totals)
        worker_ids = list(worker_picks.keys())
        for outlier in worker_outliers:
            idx = outlier["index"]
            if idx < len(worker_ids):
                anomalies.append({
                    "type": "pick_rate_worker",
                    "severity": "MEDIUM",
                    "worker_id": worker_ids[idx],
                    "details": f"Worker pick rate is {outlier['direction']} (z={outlier['z_score']}). "
                              f"Total: {outlier['value']:.0f}, Mean: {outlier['mean']:.0f}",
                    "z_score": outlier["z_score"],
                    "recommended_action": "Review worker performance or training needs" if outlier["direction"] == "low"
                                        else "Verify task accuracy - unusually high throughput",
                })

        return {
            "total_zones_analyzed": len(zone_picks),
            "total_workers_analyzed": len(worker_picks),
            "anomalies": anomalies,
            "period_days": days,
        }

    # ==================== Inventory Discrepancy Analysis ====================

    async def _analyze_inventory_discrepancies(self, warehouse_id: Optional[UUID] = None) -> Dict:
        """Compare StockItem counts vs InventorySummary for discrepancies."""
        # Get actual stock item counts by product + warehouse
        stock_query = (
            select(
                StockItem.product_id,
                StockItem.warehouse_id,
                func.count(StockItem.id).label("actual_count"),
            )
            .where(StockItem.status.in_(["AVAILABLE", "RESERVED", "ALLOCATED"]))
            .group_by(StockItem.product_id, StockItem.warehouse_id)
        )

        if warehouse_id:
            stock_query = stock_query.where(StockItem.warehouse_id == warehouse_id)

        stock_result = await self.db.execute(stock_query)
        stock_rows = stock_result.all()

        # Get inventory summary records
        inv_query = select(
            InventorySummary.product_id,
            InventorySummary.warehouse_id,
            InventorySummary.total_quantity,
            InventorySummary.available_quantity,
        )

        if warehouse_id:
            inv_query = inv_query.where(InventorySummary.warehouse_id == warehouse_id)

        inv_result = await self.db.execute(inv_query)
        inv_rows = inv_result.all()

        # Build lookup
        actual_map = {}
        for row in stock_rows:
            key = (str(row.product_id), str(row.warehouse_id))
            actual_map[key] = int(row.actual_count)

        summary_map = {}
        for row in inv_rows:
            key = (str(row.product_id), str(row.warehouse_id))
            summary_map[key] = {
                "total": int(row.total_quantity or 0),
                "available": int(row.available_quantity or 0),
            }

        # Find discrepancies
        discrepancies = []
        all_keys = set(actual_map.keys()) | set(summary_map.keys())

        for key in all_keys:
            actual = actual_map.get(key, 0)
            summary = summary_map.get(key, {"total": 0, "available": 0})
            diff = actual - summary["total"]

            if abs(diff) > 0:
                pct_diff = abs(diff) / max(summary["total"], 1) * 100
                severity = "CRITICAL" if pct_diff > 20 else "HIGH" if pct_diff > 10 else "MEDIUM" if pct_diff > 5 else "LOW"

                discrepancies.append({
                    "product_id": key[0],
                    "warehouse_id": key[1],
                    "actual_count": actual,
                    "summary_total": summary["total"],
                    "difference": diff,
                    "pct_difference": round(pct_diff, 1),
                    "severity": severity,
                })

        # Sort by severity
        severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        discrepancies.sort(key=lambda x: severity_order.get(x["severity"], 4))

        anomalies = []
        for d in discrepancies[:20]:  # Top 20 discrepancies
            anomalies.append({
                "type": "inventory_discrepancy",
                "severity": d["severity"],
                "product_id": d["product_id"],
                "warehouse_id": d["warehouse_id"],
                "details": f"Stock count mismatch: actual={d['actual_count']}, summary={d['summary_total']}, "
                          f"diff={d['difference']} ({d['pct_difference']}%)",
                "recommended_action": "Schedule immediate cycle count" if d["severity"] in ("CRITICAL", "HIGH")
                                    else "Include in next cycle count schedule",
            })

        return {
            "total_products_checked": len(all_keys),
            "total_discrepancies": len(discrepancies),
            "critical_discrepancies": len([d for d in discrepancies if d["severity"] == "CRITICAL"]),
            "anomalies": anomalies,
        }

    # ==================== Stock Movement Volume Analysis ====================

    async def _analyze_movement_volumes(self, warehouse_id: Optional[UUID] = None, days: int = 30) -> Dict:
        """Detect unusual spikes or drops in stock movement volumes."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        # Get daily movement counts by type
        query = (
            select(
                func.date_trunc('day', StockMovement.movement_date).label("day"),
                StockMovement.movement_type,
                func.count(StockMovement.id).label("count"),
                func.sum(StockMovement.quantity).label("total_qty"),
            )
            .where(StockMovement.movement_date >= cutoff)
            .group_by("day", StockMovement.movement_type)
            .order_by("day")
        )

        if warehouse_id:
            query = query.where(StockMovement.warehouse_id == warehouse_id)

        result = await self.db.execute(query)
        rows = result.all()

        # Group by movement type
        type_daily = defaultdict(list)
        for row in rows:
            type_daily[row.movement_type].append(float(row.total_qty or 0))

        anomalies = []
        for mvt_type, daily_volumes in type_daily.items():
            outliers = self._detect_outliers(daily_volumes, threshold=2.0)
            for outlier in outliers:
                anomalies.append({
                    "type": "movement_volume",
                    "severity": "HIGH" if abs(outlier["z_score"]) > 3 else "MEDIUM",
                    "movement_type": mvt_type,
                    "details": f"{mvt_type} volume anomaly on day {outlier['index']+1}: "
                              f"qty={outlier['value']:.0f} vs avg={outlier['mean']:.0f} (z={outlier['z_score']})",
                    "z_score": outlier["z_score"],
                    "recommended_action": f"Investigate {outlier['direction']} {mvt_type} volume - "
                                        f"possible {'unplanned activity' if outlier['direction'] == 'high' else 'operations bottleneck'}",
                })

        return {
            "movement_types_analyzed": len(type_daily),
            "period_days": days,
            "anomalies": anomalies,
        }

    # ==================== Cycle Count Variance Analysis ====================

    async def _analyze_cycle_count_variances(self, warehouse_id: Optional[UUID] = None, days: int = 90) -> Dict:
        """Analyze cycle count variances for patterns."""
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)

            query = (
                select(
                    InventoryVariance.product_id,
                    InventoryVariance.warehouse_id,
                    InventoryVariance.expected_quantity,
                    InventoryVariance.actual_quantity,
                    InventoryVariance.variance_quantity,
                    InventoryVariance.variance_percentage,
                    InventoryVariance.variance_status,
                    InventoryVariance.variance_reason,
                )
                .where(InventoryVariance.created_at >= cutoff)
            )

            if warehouse_id:
                query = query.where(InventoryVariance.warehouse_id == warehouse_id)

            result = await self.db.execute(query)
            rows = result.all()
        except Exception:
            return {"total_variances": 0, "anomalies": [], "period_days": days}

        if not rows:
            return {"total_variances": 0, "anomalies": [], "period_days": days}

        # Analyze variance percentages
        variance_pcts = [float(row.variance_percentage or 0) for row in rows]
        outliers = self._detect_outliers(variance_pcts, threshold=2.0)

        anomalies = []
        for outlier in outliers:
            idx = outlier["index"]
            if idx < len(rows):
                row = rows[idx]
                anomalies.append({
                    "type": "cycle_count_variance",
                    "severity": "CRITICAL" if abs(outlier["z_score"]) > 3 else "HIGH",
                    "product_id": str(row.product_id),
                    "warehouse_id": str(row.warehouse_id) if row.warehouse_id else None,
                    "details": f"Extreme variance: expected={row.expected_quantity}, actual={row.actual_quantity}, "
                              f"variance={row.variance_quantity} ({outlier['value']:.1f}%)",
                    "reason": row.variance_reason,
                    "recommended_action": "Investigate root cause - potential theft, misplacement, or receiving error",
                })

        # Aggregate by reason
        reason_counts = defaultdict(int)
        for row in rows:
            if row.variance_reason:
                reason_counts[row.variance_reason] += 1

        return {
            "total_variances": len(rows),
            "avg_variance_pct": round(sum(variance_pcts) / len(variance_pcts), 2) if variance_pcts else 0,
            "variance_by_reason": dict(reason_counts),
            "anomalies": anomalies,
            "period_days": days,
        }

    # ==================== Public Interface ====================

    async def analyze(self, warehouse_id: Optional[UUID] = None, days: int = 30) -> Dict:
        """Run full anomaly detection analysis."""
        self._status = "running"
        try:
            pick_rates = await self._analyze_pick_rates(warehouse_id, days)
            inventory = await self._analyze_inventory_discrepancies(warehouse_id)
            movements = await self._analyze_movement_volumes(warehouse_id, days)
            variances = await self._analyze_cycle_count_variances(warehouse_id, days * 3)

            # Combine all anomalies
            all_anomalies = (
                pick_rates["anomalies"] +
                inventory["anomalies"] +
                movements["anomalies"] +
                variances["anomalies"]
            )

            # Sort by severity
            severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
            all_anomalies.sort(key=lambda x: severity_order.get(x.get("severity", "LOW"), 4))

            severity_summary = defaultdict(int)
            for a in all_anomalies:
                severity_summary[a.get("severity", "LOW")] += 1

            self._results = {
                "agent": "anomaly_detection",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "warehouse_id": str(warehouse_id) if warehouse_id else "all",
                "analysis_period_days": days,
                "summary": {
                    "total_anomalies": len(all_anomalies),
                    "by_severity": dict(severity_summary),
                    "pick_rate_anomalies": len(pick_rates["anomalies"]),
                    "inventory_discrepancies": inventory["total_discrepancies"],
                    "movement_anomalies": len(movements["anomalies"]),
                    "cycle_count_anomalies": len(variances["anomalies"]),
                },
                "pick_rate_analysis": pick_rates,
                "inventory_analysis": inventory,
                "movement_analysis": movements,
                "variance_analysis": variances,
                "anomalies": all_anomalies[:50],  # Top 50
            }
            self._status = "completed"
            self._last_run = datetime.now(timezone.utc)
            return self._results

        except Exception as e:
            self._status = "error"
            return {
                "agent": "anomaly_detection",
                "error": str(e),
                "status": "error",
            }

    async def get_recommendations(self) -> List[Dict]:
        """Get recommendations from last analysis."""
        if not self._results:
            return []
        return [
            {
                "type": a["type"],
                "severity": a["severity"],
                "recommendation": a.get("recommended_action", ""),
                "details": a.get("details", ""),
            }
            for a in self._results.get("anomalies", [])[:20]
        ]

    async def get_status(self) -> Dict:
        """Get agent status."""
        return {
            "id": "anomaly_detection",
            "name": "Anomaly Detection Agent",
            "description": "Z-score analysis on pick rates, inventory discrepancies, movement volumes, and cycle count variances",
            "status": self._status,
            "last_run": self._last_run.isoformat() if self._last_run else None,
            "data_sources": "StockItem, InventorySummary, StockMovement, WarehouseTask, InventoryVariance",
            "capabilities": [
                "Pick rate anomaly detection",
                "Inventory discrepancy analysis",
                "Movement volume spike detection",
                "Cycle count variance patterns",
            ],
        }
