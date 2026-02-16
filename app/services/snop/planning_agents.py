"""
AI Planning Agents — Autonomous Supply Chain Intelligence

Provides agent-based autonomous planning capabilities:
- ExceptionAgent: Detects anomalies in demand/supply gaps, inventory breaches
- ReorderAgent: Auto-generates purchase order suggestions based on inventory position
- ForecastBiasAgent: Detects systematic forecast errors and suggests corrections
- AlertCenter: Aggregates all agent outputs into prioritized, actionable alerts

Competitive with: o9 Solutions AI Agents, Kinaxis Maestro RapidResponse, Blue Yonder Luminate
"""

import uuid
import math
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import List, Dict, Optional, Any
from enum import Enum

from sqlalchemy import select, func, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.snop import (
    DemandForecast,
    SupplyPlan,
    SNOPScenario,
    InventoryOptimization,
    ForecastGranularity,
    ForecastStatus,
    SupplyPlanStatus,
)
from app.models.product import Product
from app.models.inventory import InventorySummary


class AlertSeverity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


class AlertCategory(str, Enum):
    STOCKOUT_RISK = "STOCKOUT_RISK"
    OVERSTOCK = "OVERSTOCK"
    DEMAND_SPIKE = "DEMAND_SPIKE"
    DEMAND_DROP = "DEMAND_DROP"
    SUPPLY_GAP = "SUPPLY_GAP"
    FORECAST_BIAS = "FORECAST_BIAS"
    REORDER_NEEDED = "REORDER_NEEDED"
    CAPACITY_BREACH = "CAPACITY_BREACH"
    LEAD_TIME_RISK = "LEAD_TIME_RISK"
    EXPIRY_RISK = "EXPIRY_RISK"


class PlanningAgents:
    """
    Suite of autonomous AI planning agents.

    Each agent monitors a specific aspect of the supply chain and generates
    actionable alerts and recommendations without human intervention.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    # ==================== Exception Detection Agent ====================

    async def run_exception_agent(
        self,
        safety_stock_threshold: float = 1.0,
        overstock_days_threshold: int = 90,
        gap_pct_threshold: float = 10.0,
    ) -> Dict[str, Any]:
        """
        Detect supply chain exceptions and anomalies.

        Scans:
        1. Products below safety stock
        2. Products with excess inventory (>N days of supply)
        3. Demand-supply gaps exceeding threshold
        4. Products with no recent orders (potential obsolescence)
        """
        alerts: List[Dict[str, Any]] = []

        # 1. Products below safety stock
        stockout_alerts = await self._detect_stockout_risks(safety_stock_threshold)
        alerts.extend(stockout_alerts)

        # 2. Overstock detection
        overstock_alerts = await self._detect_overstock(overstock_days_threshold)
        alerts.extend(overstock_alerts)

        # 3. Demand-supply gaps
        gap_alerts = await self._detect_supply_gaps(gap_pct_threshold)
        alerts.extend(gap_alerts)

        # Sort by severity
        severity_order = {
            AlertSeverity.CRITICAL: 0,
            AlertSeverity.HIGH: 1,
            AlertSeverity.MEDIUM: 2,
            AlertSeverity.LOW: 3,
            AlertSeverity.INFO: 4,
        }
        alerts.sort(key=lambda a: severity_order.get(a["severity"], 5))

        return {
            "agent": "exception_detection",
            "run_at": datetime.now(timezone.utc).isoformat(),
            "total_alerts": len(alerts),
            "by_severity": {
                sev.value: len([a for a in alerts if a["severity"] == sev.value])
                for sev in AlertSeverity
            },
            "alerts": alerts,
        }

    async def _detect_stockout_risks(self, threshold: float) -> List[Dict[str, Any]]:
        """Find products at risk of stockout."""
        alerts = []

        result = await self.db.execute(
            select(InventorySummary)
            .where(InventorySummary.available_quantity <= InventorySummary.minimum_stock * Decimal(str(threshold)))
        )
        low_stock = list(result.scalars().all())

        for inv in low_stock:
            available = float(inv.available_quantity or 0)
            safety = float(inv.minimum_stock or 0)
            reorder_point = float(inv.reorder_level or 0)

            if available <= 0:
                severity = AlertSeverity.CRITICAL.value
                message = f"OUT OF STOCK — zero available inventory"
            elif available <= safety * 0.5:
                severity = AlertSeverity.CRITICAL.value
                message = f"Critically low: {available:.0f} units (safety stock: {safety:.0f})"
            elif available <= safety:
                severity = AlertSeverity.HIGH.value
                message = f"Below safety stock: {available:.0f} units (safety: {safety:.0f})"
            else:
                severity = AlertSeverity.MEDIUM.value
                message = f"Approaching safety stock: {available:.0f} units (threshold: {safety * threshold:.0f})"

            alerts.append({
                "id": str(uuid.uuid4()),
                "category": AlertCategory.STOCKOUT_RISK.value,
                "severity": severity,
                "title": f"Stockout Risk — Product {inv.product_id}",
                "message": message,
                "product_id": str(inv.product_id),
                "warehouse_id": str(inv.warehouse_id),
                "data": {
                    "available_qty": available,
                    "safety_stock": safety,
                    "reorder_point": reorder_point,
                    "deficit": max(0, safety - available),
                },
                "recommended_action": f"Reorder at least {max(0, reorder_point - available):.0f} units immediately",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

        return alerts

    async def _detect_overstock(self, days_threshold: int) -> List[Dict[str, Any]]:
        """Find overstocked products."""
        alerts = []

        result = await self.db.execute(
            select(InventorySummary)
            .where(InventorySummary.available_quantity > 0)
        )
        inventories = list(result.scalars().all())

        for inv in inventories:
            available = float(inv.available_quantity or 0)
            # Estimate daily demand from recent forecasts
            avg_daily = float(inv.reorder_level or 1) / 14  # Rough estimate
            if avg_daily <= 0:
                avg_daily = 1

            days_of_supply = available / avg_daily

            if days_of_supply > days_threshold:
                severity = AlertSeverity.HIGH.value if days_of_supply > days_threshold * 2 else AlertSeverity.MEDIUM.value

                alerts.append({
                    "id": str(uuid.uuid4()),
                    "category": AlertCategory.OVERSTOCK.value,
                    "severity": severity,
                    "title": f"Overstock — Product {inv.product_id}",
                    "message": f"{days_of_supply:.0f} days of supply on hand (threshold: {days_threshold} days)",
                    "product_id": str(inv.product_id),
                    "warehouse_id": str(inv.warehouse_id),
                    "data": {
                        "available_qty": available,
                        "days_of_supply": round(days_of_supply, 1),
                        "avg_daily_demand": round(avg_daily, 2),
                        "excess_qty": round(available - avg_daily * days_threshold, 0),
                    },
                    "recommended_action": f"Consider promotional pricing or redistribution",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })

        return alerts

    async def _detect_supply_gaps(self, gap_pct_threshold: float) -> List[Dict[str, Any]]:
        """Detect demand-supply gaps exceeding threshold."""
        alerts = []

        today = date.today()
        end_date = today + timedelta(days=90)

        # Get approved forecasts
        fc_result = await self.db.execute(
            select(
                DemandForecast.product_id,
                func.sum(DemandForecast.total_forecasted_qty).label("total_demand")
            )
            .where(
                and_(
                    DemandForecast.is_active == True,
                    DemandForecast.status == ForecastStatus.APPROVED,
                    DemandForecast.forecast_start_date <= end_date,
                    DemandForecast.forecast_end_date >= today,
                    DemandForecast.product_id.isnot(None),
                )
            )
            .group_by(DemandForecast.product_id)
        )
        demand_by_product = {str(row.product_id): float(row.total_demand) for row in fc_result}

        # Get supply plans
        sp_result = await self.db.execute(
            select(
                SupplyPlan.product_id,
                func.sum(SupplyPlan.planned_production_qty + SupplyPlan.planned_procurement_qty).label("total_supply")
            )
            .where(
                and_(
                    SupplyPlan.is_active == True,
                    SupplyPlan.plan_start_date <= end_date,
                    SupplyPlan.plan_end_date >= today,
                    SupplyPlan.product_id.isnot(None),
                )
            )
            .group_by(SupplyPlan.product_id)
        )
        supply_by_product = {str(row.product_id): float(row.total_supply) for row in sp_result}

        for product_id, demand in demand_by_product.items():
            supply = supply_by_product.get(product_id, 0)
            if demand > 0:
                gap = demand - supply
                gap_pct = (gap / demand) * 100

                if gap_pct > gap_pct_threshold:
                    severity = AlertSeverity.CRITICAL.value if gap_pct > 30 else AlertSeverity.HIGH.value

                    alerts.append({
                        "id": str(uuid.uuid4()),
                        "category": AlertCategory.SUPPLY_GAP.value,
                        "severity": severity,
                        "title": f"Supply Gap — Product {product_id[:8]}",
                        "message": f"Demand-supply gap of {gap_pct:.1f}% ({gap:.0f} units short)",
                        "product_id": product_id,
                        "data": {
                            "forecasted_demand": round(demand, 0),
                            "planned_supply": round(supply, 0),
                            "gap_units": round(gap, 0),
                            "gap_pct": round(gap_pct, 1),
                        },
                        "recommended_action": f"Increase supply by {gap:.0f} units or expedite procurement",
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })

        return alerts

    # ==================== Reorder Agent ====================

    async def run_reorder_agent(
        self,
        lead_time_buffer_pct: float = 20.0,
    ) -> Dict[str, Any]:
        """
        Auto-generate purchase order suggestions.

        For each product below reorder point:
        1. Calculate order quantity (EOQ or to reach target stock)
        2. Factor in lead time with safety buffer
        3. Suggest vendor based on existing PO history
        4. Assign urgency level
        """
        suggestions: List[Dict[str, Any]] = []

        result = await self.db.execute(
            select(InventorySummary)
            .where(
                and_(
                    InventorySummary.available_quantity <= InventorySummary.reorder_level,
                    InventorySummary.available_quantity >= 0,
                )
            )
        )
        below_reorder = list(result.scalars().all())

        for inv in below_reorder:
            available = float(inv.available_quantity or 0)
            reorder_point = float(inv.reorder_level or 0)
            safety_stock = float(inv.minimum_stock or 0)

            # Target stock = 2x reorder point (simplified EOQ)
            target_stock = reorder_point * 2
            order_qty = max(0, target_stock - available)

            if order_qty <= 0:
                continue

            # Urgency
            if available <= 0:
                urgency = "EMERGENCY"
                severity = AlertSeverity.CRITICAL.value
            elif available <= safety_stock:
                urgency = "URGENT"
                severity = AlertSeverity.HIGH.value
            else:
                urgency = "NORMAL"
                severity = AlertSeverity.MEDIUM.value

            # Lead time (default 14 days + buffer)
            estimated_lead_time = 14
            buffered_lead_time = int(estimated_lead_time * (1 + lead_time_buffer_pct / 100))
            expected_delivery = date.today() + timedelta(days=buffered_lead_time)

            # Days of supply remaining
            avg_daily = reorder_point / 14 if reorder_point > 0 else 1
            days_remaining = available / avg_daily if avg_daily > 0 else 0

            suggestions.append({
                "id": str(uuid.uuid4()),
                "product_id": str(inv.product_id),
                "warehouse_id": str(inv.warehouse_id),
                "urgency": urgency,
                "severity": severity,
                "current_stock": round(available, 0),
                "reorder_point": round(reorder_point, 0),
                "safety_stock": round(safety_stock, 0),
                "suggested_order_qty": round(order_qty, 0),
                "target_stock": round(target_stock, 0),
                "days_of_supply_remaining": round(days_remaining, 1),
                "estimated_lead_time_days": buffered_lead_time,
                "expected_delivery_date": expected_delivery.isoformat(),
                "estimated_cost": round(order_qty * 500, 2),  # Placeholder unit cost
                "status": "SUGGESTED",
                "created_at": datetime.now(timezone.utc).isoformat(),
            })

        # Sort by urgency
        urgency_order = {"EMERGENCY": 0, "URGENT": 1, "NORMAL": 2}
        suggestions.sort(key=lambda s: urgency_order.get(s["urgency"], 3))

        return {
            "agent": "reorder",
            "run_at": datetime.now(timezone.utc).isoformat(),
            "total_suggestions": len(suggestions),
            "by_urgency": {
                u: len([s for s in suggestions if s["urgency"] == u])
                for u in ["EMERGENCY", "URGENT", "NORMAL"]
            },
            "total_estimated_cost": round(sum(s["estimated_cost"] for s in suggestions), 2),
            "suggestions": suggestions,
        }

    # ==================== Convert Suggestion to PR ====================

    async def create_purchase_requisition_from_suggestion(
        self,
        suggestion: Dict[str, Any],
        user_id: uuid.UUID,
    ) -> Dict[str, Any]:
        """
        Convert a reorder suggestion into a DRAFT Purchase Requisition.

        Args:
            suggestion: Dict from run_reorder_agent() with product_id, warehouse_id, etc.
            user_id: User triggering the conversion
        Returns:
            Dict with created PR details
        """
        from app.models.purchase import PurchaseRequisition, PurchaseRequisitionItem

        product_id = uuid.UUID(suggestion["product_id"])
        warehouse_id = uuid.UUID(suggestion["warehouse_id"])

        # Get product info for snapshot
        product = await self.db.get(Product, product_id)
        if not product:
            raise ValueError(f"Product {product_id} not found")

        # Generate PR number
        today = date.today().strftime("%Y%m%d")
        count_result = await self.db.execute(
            select(func.count(PurchaseRequisition.id)).where(
                PurchaseRequisition.requisition_number.like(f"PR-{today}%")
            )
        )
        count = count_result.scalar() or 0
        pr_number = f"PR-{today}-{count + 1:04d}"

        order_qty = int(suggestion.get("suggested_order_qty", 0))
        estimated_cost = Decimal(str(suggestion.get("estimated_cost", 0)))
        urgency = suggestion.get("urgency", "NORMAL")

        # Map urgency to priority
        priority_map = {"EMERGENCY": 1, "URGENT": 2, "NORMAL": 5}
        priority = priority_map.get(urgency, 5)

        pr = PurchaseRequisition(
            requisition_number=pr_number,
            status="DRAFT",
            requesting_department="SNOP_REORDER_AGENT",
            requested_by=user_id,
            request_date=date.today(),
            required_by_date=date.fromisoformat(suggestion["expected_delivery_date"])
            if suggestion.get("expected_delivery_date") else None,
            delivery_warehouse_id=warehouse_id,
            priority=priority,
            estimated_total=estimated_cost,
            reason=f"Auto-generated by S&OP Reorder Agent. Urgency: {urgency}. "
                   f"Current stock: {suggestion.get('current_stock', 'N/A')}, "
                   f"Reorder point: {suggestion.get('reorder_point', 'N/A')}",
        )
        self.db.add(pr)
        await self.db.flush()

        unit_price = estimated_cost / Decimal(str(order_qty)) if order_qty > 0 else Decimal("0")
        pr_item = PurchaseRequisitionItem(
            requisition_id=pr.id,
            product_id=product_id,
            product_name=product.name,
            sku=product.sku,
            quantity_requested=order_qty,
            estimated_unit_price=unit_price,
            estimated_total=estimated_cost,
            notes=f"Reorder agent suggestion: {urgency}",
        )
        self.db.add(pr_item)

        await self.db.commit()

        return {
            "pr_id": str(pr.id),
            "pr_number": pr_number,
            "product_id": str(product_id),
            "product_name": product.name,
            "quantity": order_qty,
            "estimated_cost": float(estimated_cost),
            "urgency": urgency,
            "status": "DRAFT",
        }

    # ==================== Forecast Bias Agent ====================

    async def run_bias_agent(
        self,
        bias_threshold_pct: float = 10.0,
        min_forecasts: int = 3,
    ) -> Dict[str, Any]:
        """
        Detect systematic forecast bias.

        Analyzes completed forecasts to find:
        1. Consistent over-forecasting (positive bias)
        2. Consistent under-forecasting (negative bias)
        3. Accuracy degradation trends
        4. Algorithm performance comparison
        """
        findings: List[Dict[str, Any]] = []

        # Get forecasts with accuracy metrics
        result = await self.db.execute(
            select(DemandForecast)
            .where(
                and_(
                    DemandForecast.is_active == True,
                    DemandForecast.mape.isnot(None),
                    DemandForecast.forecast_bias.isnot(None),
                )
            )
            .order_by(desc(DemandForecast.created_at))
            .limit(200)
        )
        forecasts = list(result.scalars().all())

        if len(forecasts) < min_forecasts:
            return {
                "agent": "forecast_bias",
                "run_at": datetime.now(timezone.utc).isoformat(),
                "total_findings": 0,
                "message": f"Insufficient forecasts for bias analysis (need {min_forecasts}, have {len(forecasts)})",
                "findings": [],
            }

        # Aggregate bias by algorithm
        algo_stats: Dict[str, List[Dict[str, float]]] = {}
        for f in forecasts:
            algo = f.algorithm_used or "ENSEMBLE"
            if algo not in algo_stats:
                algo_stats[algo] = []
            algo_stats[algo].append({
                "bias": float(f.forecast_bias or 0),
                "mape": float(f.mape or 0),
                "forecast_id": str(f.id),
            })

        for algo, stats in algo_stats.items():
            avg_bias = sum(s["bias"] for s in stats) / len(stats)
            avg_mape = sum(s["mape"] for s in stats) / len(stats)

            if abs(avg_bias) > bias_threshold_pct:
                direction = "over-forecasting" if avg_bias > 0 else "under-forecasting"

                findings.append({
                    "id": str(uuid.uuid4()),
                    "type": "SYSTEMATIC_BIAS",
                    "severity": AlertSeverity.HIGH.value if abs(avg_bias) > bias_threshold_pct * 2 else AlertSeverity.MEDIUM.value,
                    "algorithm": algo,
                    "avg_bias_pct": round(avg_bias, 2),
                    "avg_mape": round(avg_mape, 2),
                    "direction": direction,
                    "sample_size": len(stats),
                    "message": f"{algo} algorithm shows systematic {direction} with avg bias of {avg_bias:.1f}%",
                    "recommendation": (
                        f"Apply {-avg_bias:.1f}% correction factor to {algo} forecasts"
                        if abs(avg_bias) > bias_threshold_pct
                        else f"Monitor {algo} bias trend"
                    ),
                })

            # Accuracy check
            if avg_mape > 30:
                findings.append({
                    "id": str(uuid.uuid4()),
                    "type": "LOW_ACCURACY",
                    "severity": AlertSeverity.HIGH.value,
                    "algorithm": algo,
                    "avg_mape": round(avg_mape, 2),
                    "sample_size": len(stats),
                    "message": f"{algo} shows poor accuracy (MAPE: {avg_mape:.1f}%)",
                    "recommendation": f"Consider switching from {algo} to a different algorithm or retraining",
                })

        # Overall bias direction
        overall_bias = sum(float(f.forecast_bias or 0) for f in forecasts) / len(forecasts)

        # Best/worst performing algorithms
        algo_mape = {
            algo: sum(s["mape"] for s in stats) / len(stats)
            for algo, stats in algo_stats.items()
            if len(stats) >= 2
        }
        best_algo = min(algo_mape, key=algo_mape.get) if algo_mape else None
        worst_algo = max(algo_mape, key=algo_mape.get) if algo_mape else None

        return {
            "agent": "forecast_bias",
            "run_at": datetime.now(timezone.utc).isoformat(),
            "total_findings": len(findings),
            "overall_stats": {
                "total_forecasts_analyzed": len(forecasts),
                "overall_avg_bias": round(overall_bias, 2),
                "overall_direction": "over-forecasting" if overall_bias > 0 else "under-forecasting",
                "algorithms_analyzed": list(algo_stats.keys()),
                "best_algorithm": best_algo,
                "worst_algorithm": worst_algo,
                "algorithm_mape": {k: round(v, 2) for k, v in algo_mape.items()},
            },
            "findings": findings,
        }

    # ==================== Alert Center ====================

    async def get_alert_center(
        self,
        include_exceptions: bool = True,
        include_reorder: bool = True,
        include_bias: bool = True,
        max_alerts: int = 50,
    ) -> Dict[str, Any]:
        """
        Aggregated alert center — runs all agents and combines results.

        Returns prioritized, deduplicated alerts across all agents
        with severity scoring and recommended actions.
        """
        all_alerts: List[Dict[str, Any]] = []

        if include_exceptions:
            exc_result = await self.run_exception_agent()
            for alert in exc_result.get("alerts", []):
                alert["agent_source"] = "exception_detection"
                all_alerts.append(alert)

        if include_reorder:
            reorder_result = await self.run_reorder_agent()
            for suggestion in reorder_result.get("suggestions", []):
                all_alerts.append({
                    "id": suggestion["id"],
                    "category": AlertCategory.REORDER_NEEDED.value,
                    "severity": suggestion["severity"],
                    "title": f"Reorder Needed — Product {suggestion['product_id'][:8]}",
                    "message": f"Order {suggestion['suggested_order_qty']:.0f} units ({suggestion['urgency']}). {suggestion['days_of_supply_remaining']:.0f} days supply remaining.",
                    "product_id": suggestion["product_id"],
                    "warehouse_id": suggestion["warehouse_id"],
                    "data": suggestion,
                    "recommended_action": f"Create PO for {suggestion['suggested_order_qty']:.0f} units, expected delivery: {suggestion['expected_delivery_date']}",
                    "agent_source": "reorder",
                    "timestamp": suggestion["created_at"],
                })

        if include_bias:
            bias_result = await self.run_bias_agent()
            for finding in bias_result.get("findings", []):
                all_alerts.append({
                    "id": finding["id"],
                    "category": AlertCategory.FORECAST_BIAS.value,
                    "severity": finding["severity"],
                    "title": f"Forecast Bias — {finding.get('algorithm', 'Unknown')}",
                    "message": finding["message"],
                    "data": finding,
                    "recommended_action": finding.get("recommendation", "Review forecast settings"),
                    "agent_source": "forecast_bias",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })

        # Sort by severity then timestamp
        severity_score = {
            AlertSeverity.CRITICAL.value: 0,
            AlertSeverity.HIGH.value: 1,
            AlertSeverity.MEDIUM.value: 2,
            AlertSeverity.LOW.value: 3,
            AlertSeverity.INFO.value: 4,
        }
        all_alerts.sort(key=lambda a: severity_score.get(a.get("severity", "INFO"), 5))

        # Limit
        trimmed = all_alerts[:max_alerts]

        # Summary
        summary = {
            "total_alerts": len(all_alerts),
            "displayed": len(trimmed),
            "by_severity": {
                sev.value: len([a for a in all_alerts if a.get("severity") == sev.value])
                for sev in AlertSeverity
            },
            "by_category": {},
            "by_agent": {},
        }

        for alert in all_alerts:
            cat = alert.get("category", "UNKNOWN")
            agent = alert.get("agent_source", "unknown")
            summary["by_category"][cat] = summary["by_category"].get(cat, 0) + 1
            summary["by_agent"][agent] = summary["by_agent"].get(agent, 0) + 1

        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "summary": summary,
            "alerts": trimmed,
            "agents_status": {
                "exception_detection": "completed" if include_exceptions else "skipped",
                "reorder": "completed" if include_reorder else "skipped",
                "forecast_bias": "completed" if include_bias else "skipped",
            },
        }

    # ==================== Agent Status ====================

    async def get_agent_status(self) -> Dict[str, Any]:
        """Get the status overview of all planning agents."""

        # Count data points for each agent
        forecast_count = await self.db.execute(
            select(func.count(DemandForecast.id))
            .where(DemandForecast.is_active == True)
        )
        inventory_count = await self.db.execute(
            select(func.count(InventorySummary.id))
        )
        supply_count = await self.db.execute(
            select(func.count(SupplyPlan.id))
            .where(SupplyPlan.is_active == True)
        )

        fc = forecast_count.scalar() or 0
        ic = inventory_count.scalar() or 0
        sc = supply_count.scalar() or 0

        return {
            "agents": [
                {
                    "name": "Exception Detection",
                    "id": "exception_detection",
                    "description": "Monitors stockout risks, overstock, and supply gaps",
                    "status": "ready",
                    "data_sources": f"{ic} inventory records, {fc} forecasts, {sc} supply plans",
                    "last_run": None,
                    "capabilities": ["Stockout risk detection", "Overstock detection", "Supply gap analysis"],
                },
                {
                    "name": "Reorder Agent",
                    "id": "reorder",
                    "description": "Auto-generates purchase order suggestions",
                    "status": "ready",
                    "data_sources": f"{ic} inventory records",
                    "last_run": None,
                    "capabilities": ["EOQ calculation", "Urgency classification", "Delivery date estimation"],
                },
                {
                    "name": "Forecast Bias Agent",
                    "id": "forecast_bias",
                    "description": "Detects systematic forecast errors",
                    "status": "ready" if fc >= 3 else "insufficient_data",
                    "data_sources": f"{fc} forecasts with accuracy metrics",
                    "last_run": None,
                    "capabilities": ["Bias detection", "Algorithm comparison", "Correction suggestions"],
                },
            ],
            "summary": {
                "total_agents": 3,
                "ready": 3 if fc >= 3 else 2,
                "insufficient_data": 0 if fc >= 3 else 1,
            },
        }
