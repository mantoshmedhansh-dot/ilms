"""
Natural Language Planning Interface

Provides conversational AI interface for S&OP queries:
- Intent classification via pattern matching
- Query routing to appropriate S&OP services
- Structured response generation with data + narrative
- Quick action suggestions

Supports queries like:
- "What's the demand forecast for next quarter?"
- "Show me stockout risks"
- "Compare our scenarios"
- "How accurate are our forecasts?"
- "Generate a supply plan for product X"

Competitive with: o9 Solutions AI Assistant, Kinaxis Maestro NLQ, SAP IBP Joule
"""

import re
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum

from sqlalchemy import select, func, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.snop import (
    DemandForecast,
    SupplyPlan,
    SNOPScenario,
    DemandSignal,
    InventoryOptimization,
    ForecastGranularity,
    ForecastStatus,
    SupplyPlanStatus,
    ScenarioStatus,
)
from app.models.product import Product


class QueryIntent(str, Enum):
    """Classified intent of a natural language query."""
    FORECAST_STATUS = "FORECAST_STATUS"
    FORECAST_ACCURACY = "FORECAST_ACCURACY"
    DEMAND_SUMMARY = "DEMAND_SUMMARY"
    SUPPLY_STATUS = "SUPPLY_STATUS"
    STOCKOUT_RISK = "STOCKOUT_RISK"
    OVERSTOCK_CHECK = "OVERSTOCK_CHECK"
    SCENARIO_COMPARE = "SCENARIO_COMPARE"
    SIGNAL_STATUS = "SIGNAL_STATUS"
    INVENTORY_HEALTH = "INVENTORY_HEALTH"
    GAP_ANALYSIS = "GAP_ANALYSIS"
    AGENT_ALERTS = "AGENT_ALERTS"
    HELP = "HELP"
    UNKNOWN = "UNKNOWN"


# Intent classification patterns
INTENT_PATTERNS = {
    QueryIntent.FORECAST_STATUS: [
        r"forecast", r"demand\s*forecast", r"prediction", r"what.*(demand|forecast)",
        r"how\s*many.*sell", r"projected\s*demand", r"next\s*(quarter|month|week)",
    ],
    QueryIntent.FORECAST_ACCURACY: [
        r"accuracy", r"mape", r"how\s*accurate", r"forecast\s*quality",
        r"forecast\s*performance", r"bias", r"error\s*rate",
    ],
    QueryIntent.DEMAND_SUMMARY: [
        r"demand\s*summary", r"total\s*demand", r"demand\s*overview",
        r"what.*demand", r"demand\s*trend",
    ],
    QueryIntent.SUPPLY_STATUS: [
        r"supply\s*plan", r"supply\s*status", r"production", r"procurement",
        r"supply\s*schedule", r"how.*supply",
    ],
    QueryIntent.STOCKOUT_RISK: [
        r"stockout", r"stock\s*out", r"out\s*of\s*stock", r"low\s*stock",
        r"running\s*low", r"safety\s*stock", r"shortage",
    ],
    QueryIntent.OVERSTOCK_CHECK: [
        r"overstock", r"excess\s*inventory", r"too\s*much\s*stock",
        r"surplus", r"dead\s*stock", r"slow\s*moving",
    ],
    QueryIntent.SCENARIO_COMPARE: [
        r"scenario", r"compare", r"what\s*if", r"simulation",
        r"best\s*scenario", r"monte\s*carlo",
    ],
    QueryIntent.SIGNAL_STATUS: [
        r"signal", r"demand\s*signal", r"sensing", r"real.time",
        r"pos\s*data", r"spike", r"drop",
    ],
    QueryIntent.INVENTORY_HEALTH: [
        r"inventor", r"reorder", r"safety\s*stock\s*level",
        r"inventory\s*turn", r"warehouse", r"stock\s*level",
    ],
    QueryIntent.GAP_ANALYSIS: [
        r"gap", r"demand.*supply", r"supply.*demand", r"shortfall",
        r"deficit", r"unmet\s*demand",
    ],
    QueryIntent.AGENT_ALERTS: [
        r"alert", r"agent", r"exception", r"warning",
        r"critical", r"attention\s*needed", r"action\s*item",
    ],
    QueryIntent.HELP: [
        r"help", r"what\s*can\s*you", r"capabilities", r"how\s*to",
        r"guide", r"tutorial",
    ],
}


class NLPlanner:
    """
    Natural Language Planning Interface for S&OP.

    Classifies user intent, queries the appropriate service,
    and returns a structured response with narrative + data.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def process_query(
        self,
        query: str,
        user_id: Optional[uuid.UUID] = None,
    ) -> Dict[str, Any]:
        """
        Process a natural language query.

        Returns:
        - intent: classified intent
        - response: natural language answer
        - data: structured data to display
        - suggestions: follow-up query suggestions
        - actions: quick actions the user can take
        """
        intent = self._classify_intent(query)

        handler_map = {
            QueryIntent.FORECAST_STATUS: self._handle_forecast_status,
            QueryIntent.FORECAST_ACCURACY: self._handle_forecast_accuracy,
            QueryIntent.DEMAND_SUMMARY: self._handle_demand_summary,
            QueryIntent.SUPPLY_STATUS: self._handle_supply_status,
            QueryIntent.STOCKOUT_RISK: self._handle_stockout_risk,
            QueryIntent.OVERSTOCK_CHECK: self._handle_overstock_check,
            QueryIntent.SCENARIO_COMPARE: self._handle_scenario_compare,
            QueryIntent.SIGNAL_STATUS: self._handle_signal_status,
            QueryIntent.INVENTORY_HEALTH: self._handle_inventory_health,
            QueryIntent.GAP_ANALYSIS: self._handle_gap_analysis,
            QueryIntent.AGENT_ALERTS: self._handle_agent_alerts,
            QueryIntent.HELP: self._handle_help,
        }

        handler = handler_map.get(intent, self._handle_unknown)
        result = await handler(query)

        return {
            "query": query,
            "intent": intent.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **result,
        }

    def _classify_intent(self, query: str) -> QueryIntent:
        """Classify query intent using pattern matching."""
        query_lower = query.lower().strip()
        scores: Dict[QueryIntent, int] = {}

        for intent, patterns in INTENT_PATTERNS.items():
            score = 0
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    score += 1
            if score > 0:
                scores[intent] = score

        if not scores:
            return QueryIntent.UNKNOWN

        return max(scores, key=scores.get)

    # ==================== Intent Handlers ====================

    async def _handle_forecast_status(self, query: str) -> Dict[str, Any]:
        """Handle forecast-related queries."""
        # Get latest forecasts
        result = await self.db.execute(
            select(DemandForecast)
            .where(DemandForecast.is_active == True)
            .order_by(desc(DemandForecast.created_at))
            .limit(10)
        )
        forecasts = list(result.scalars().all())

        total = len(forecasts)
        approved = len([f for f in forecasts if f.status == ForecastStatus.APPROVED])
        pending = len([f for f in forecasts if f.status == ForecastStatus.PENDING_REVIEW])
        draft = len([f for f in forecasts if f.status == ForecastStatus.DRAFT.value or f.status == "DRAFT"])

        total_demand = sum(float(f.total_forecasted_qty) for f in forecasts)
        avg_mape = 0
        mape_forecasts = [f for f in forecasts if f.mape]
        if mape_forecasts:
            avg_mape = sum(f.mape for f in mape_forecasts) / len(mape_forecasts)

        response = (
            f"You have {total} active forecasts. "
            f"{approved} are approved, {pending} pending review, and {draft} in draft. "
            f"Total forecasted demand across all forecasts is {total_demand:,.0f} units"
        )

        if avg_mape > 0:
            accuracy = 100 - avg_mape
            response += f" with an average accuracy of {accuracy:.1f}% (MAPE: {avg_mape:.1f}%)."
        else:
            response += "."

        return {
            "response": response,
            "data": {
                "type": "forecast_summary",
                "total_forecasts": total,
                "approved": approved,
                "pending_review": pending,
                "draft": draft,
                "total_demand": round(total_demand, 0),
                "avg_accuracy": round(100 - avg_mape, 1) if avg_mape else None,
                "recent_forecasts": [
                    {
                        "id": str(f.id),
                        "name": f.forecast_name,
                        "status": f.status,
                        "total_qty": float(f.total_forecasted_qty),
                        "algorithm": f.algorithm_used,
                        "mape": f.mape,
                    }
                    for f in forecasts[:5]
                ],
            },
            "suggestions": [
                "How accurate are our forecasts?",
                "Show me demand-supply gap",
                "Any stockout risks?",
            ],
            "actions": [
                {"label": "Generate New Forecast", "endpoint": "/snop/forecast/generate"},
                {"label": "View All Forecasts", "href": "/dashboard/snop/forecasts"},
            ],
        }

    async def _handle_forecast_accuracy(self, query: str) -> Dict[str, Any]:
        """Handle accuracy-related queries."""
        result = await self.db.execute(
            select(DemandForecast)
            .where(
                and_(
                    DemandForecast.is_active == True,
                    DemandForecast.mape.isnot(None),
                )
            )
            .order_by(desc(DemandForecast.created_at))
            .limit(50)
        )
        forecasts = list(result.scalars().all())

        if not forecasts:
            return {
                "response": "No forecasts with accuracy metrics available yet. Generate and complete some forecasts first.",
                "data": {"type": "empty"},
                "suggestions": ["Generate a forecast", "What forecasts do we have?"],
                "actions": [],
            }

        avg_mape = sum(f.mape for f in forecasts) / len(forecasts)
        best = min(forecasts, key=lambda f: f.mape)
        worst = max(forecasts, key=lambda f: f.mape)

        # By algorithm
        algo_performance: Dict[str, List[float]] = {}
        for f in forecasts:
            algo = f.algorithm_used or "ENSEMBLE"
            if algo not in algo_performance:
                algo_performance[algo] = []
            algo_performance[algo].append(f.mape)

        algo_avg = {
            algo: round(sum(mapes) / len(mapes), 2)
            for algo, mapes in algo_performance.items()
        }
        best_algo = min(algo_avg, key=algo_avg.get) if algo_avg else "N/A"

        # Bias
        biased = [f for f in forecasts if f.forecast_bias and abs(f.forecast_bias) > 10]

        response = (
            f"Across {len(forecasts)} forecasts, the average accuracy is {100-avg_mape:.1f}% "
            f"(MAPE: {avg_mape:.1f}%). "
            f"The best performing algorithm is {best_algo} with {100-algo_avg.get(best_algo, 0):.1f}% accuracy. "
        )

        if biased:
            response += f"Warning: {len(biased)} forecasts show significant bias (>10%) that may need correction."

        return {
            "response": response,
            "data": {
                "type": "accuracy_report",
                "total_analyzed": len(forecasts),
                "avg_mape": round(avg_mape, 2),
                "avg_accuracy": round(100 - avg_mape, 1),
                "best_forecast": {"name": best.forecast_name, "mape": best.mape},
                "worst_forecast": {"name": worst.forecast_name, "mape": worst.mape},
                "by_algorithm": algo_avg,
                "best_algorithm": best_algo,
                "biased_count": len(biased),
            },
            "suggestions": [
                "Run forecast bias agent",
                "Compare all forecast models",
                "Show forecasts with high bias",
            ],
            "actions": [
                {"label": "Run Bias Analysis", "href": "/dashboard/snop/ai-agents"},
                {"label": "Compare Models", "endpoint": "/snop/forecast/compare-models"},
            ],
        }

    async def _handle_demand_summary(self, query: str) -> Dict[str, Any]:
        """Handle demand summary queries."""
        total_result = await self.db.execute(
            select(func.sum(DemandForecast.total_forecasted_qty))
            .where(
                and_(
                    DemandForecast.is_active == True,
                    DemandForecast.status == ForecastStatus.APPROVED,
                )
            )
        )
        total_demand = float(total_result.scalar() or 0)

        count_result = await self.db.execute(
            select(func.count(DemandForecast.id))
            .where(DemandForecast.is_active == True)
        )
        count = count_result.scalar() or 0

        return {
            "response": f"Total approved demand forecast is {total_demand:,.0f} units across {count} active forecasts.",
            "data": {
                "type": "demand_summary",
                "total_demand": round(total_demand, 0),
                "forecast_count": count,
            },
            "suggestions": ["Show forecast accuracy", "Any supply gaps?", "Check stockout risks"],
            "actions": [{"label": "View Forecasts", "href": "/dashboard/snop/forecasts"}],
        }

    async def _handle_supply_status(self, query: str) -> Dict[str, Any]:
        """Handle supply planning queries."""
        result = await self.db.execute(
            select(SupplyPlan)
            .where(SupplyPlan.is_active == True)
            .order_by(desc(SupplyPlan.created_at))
            .limit(10)
        )
        plans = list(result.scalars().all())

        total_production = sum(float(p.planned_production_qty) for p in plans)
        total_procurement = sum(float(p.planned_procurement_qty) for p in plans)

        response = (
            f"You have {len(plans)} active supply plans. "
            f"Total planned production: {total_production:,.0f} units. "
            f"Total planned procurement: {total_procurement:,.0f} units. "
            f"Combined supply: {total_production + total_procurement:,.0f} units."
        )

        return {
            "response": response,
            "data": {
                "type": "supply_summary",
                "total_plans": len(plans),
                "total_production": round(total_production, 0),
                "total_procurement": round(total_procurement, 0),
                "total_supply": round(total_production + total_procurement, 0),
                "plans": [
                    {
                        "name": p.plan_name,
                        "status": p.status,
                        "production": float(p.planned_production_qty),
                        "procurement": float(p.planned_procurement_qty),
                    }
                    for p in plans[:5]
                ],
            },
            "suggestions": ["Show demand-supply gap", "Run capacity analysis", "Check DDMRP buffers"],
            "actions": [{"label": "View Supply Plans", "href": "/dashboard/snop/supply-plans"}],
        }

    async def _handle_stockout_risk(self, query: str) -> Dict[str, Any]:
        """Handle stockout risk queries."""
        from app.models.inventory import InventorySummary

        result = await self.db.execute(
            select(InventorySummary)
            .where(InventorySummary.available_quantity <= InventorySummary.safety_stock)
        )
        at_risk = list(result.scalars().all())

        critical = [i for i in at_risk if float(i.available_quantity or 0) <= 0]
        low = [i for i in at_risk if float(i.available_quantity or 0) > 0]

        if not at_risk:
            response = "No stockout risks detected. All products are above safety stock levels."
        else:
            response = (
                f"Stockout alert: {len(at_risk)} products below safety stock. "
                f"{len(critical)} are completely out of stock and {len(low)} are critically low. "
                f"Immediate action recommended."
            )

        return {
            "response": response,
            "data": {
                "type": "stockout_risk",
                "total_at_risk": len(at_risk),
                "out_of_stock": len(critical),
                "critically_low": len(low),
                "products": [
                    {
                        "product_id": str(i.product_id),
                        "warehouse_id": str(i.warehouse_id),
                        "available": float(i.available_quantity or 0),
                        "safety_stock": float(i.safety_stock or 0),
                    }
                    for i in at_risk[:10]
                ],
            },
            "suggestions": [
                "Run reorder agent",
                "Show supply plans",
                "Generate PO suggestions",
            ],
            "actions": [
                {"label": "Run Reorder Agent", "href": "/dashboard/snop/ai-agents"},
                {"label": "View Inventory", "href": "/dashboard/snop/inventory-optimization"},
            ],
        }

    async def _handle_overstock_check(self, query: str) -> Dict[str, Any]:
        """Handle overstock queries."""
        from app.models.inventory import InventorySummary

        result = await self.db.execute(
            select(InventorySummary)
            .where(InventorySummary.available_quantity > 0)
            .order_by(desc(InventorySummary.available_quantity))
            .limit(20)
        )
        items = list(result.scalars().all())

        overstock = []
        for inv in items:
            available = float(inv.available_quantity or 0)
            rop = float(inv.reorder_point or 1)
            avg_daily = rop / 14 if rop > 0 else 1
            dos = available / avg_daily if avg_daily > 0 else 0

            if dos > 90:
                overstock.append({
                    "product_id": str(inv.product_id),
                    "available": round(available, 0),
                    "days_of_supply": round(dos, 0),
                })

        if overstock:
            response = f"Found {len(overstock)} products with >90 days of supply on hand. Consider promotional pricing or redistribution."
        else:
            response = "No overstock issues detected. Inventory levels are within normal range."

        return {
            "response": response,
            "data": {
                "type": "overstock_check",
                "overstock_count": len(overstock),
                "products": overstock[:10],
            },
            "suggestions": ["Show stockout risks", "Check inventory health", "Run exception agent"],
            "actions": [],
        }

    async def _handle_scenario_compare(self, query: str) -> Dict[str, Any]:
        """Handle scenario comparison queries."""
        result = await self.db.execute(
            select(SNOPScenario)
            .where(SNOPScenario.is_active == True)
            .order_by(desc(SNOPScenario.created_at))
            .limit(10)
        )
        scenarios = list(result.scalars().all())

        completed = [s for s in scenarios if s.status == ScenarioStatus.COMPLETED.value]

        if not scenarios:
            response = "No scenarios found. Create what-if scenarios to compare strategic options."
        elif not completed:
            response = f"You have {len(scenarios)} scenarios but none are completed yet. Run simulations first."
        else:
            best = max(completed, key=lambda s: float(s.projected_revenue or 0))
            response = (
                f"You have {len(scenarios)} scenarios ({len(completed)} completed). "
                f"Best performing: '{best.scenario_name}' with projected revenue of "
                f"INR {float(best.projected_revenue or 0):,.0f}."
            )

        return {
            "response": response,
            "data": {
                "type": "scenario_summary",
                "total": len(scenarios),
                "completed": len(completed),
                "scenarios": [
                    {
                        "name": s.scenario_name,
                        "status": s.status,
                        "revenue": float(s.projected_revenue or 0),
                        "service_level": s.service_level_pct,
                    }
                    for s in scenarios
                ],
            },
            "suggestions": [
                "Run Monte Carlo simulation",
                "Generate P&L projection",
                "Run sensitivity analysis",
            ],
            "actions": [{"label": "View Scenarios", "href": "/dashboard/snop/scenarios"}],
        }

    async def _handle_signal_status(self, query: str) -> Dict[str, Any]:
        """Handle demand signal queries."""
        result = await self.db.execute(
            select(DemandSignal)
            .where(DemandSignal.status == "ACTIVE")
            .order_by(desc(DemandSignal.created_at))
            .limit(10)
        )
        signals = list(result.scalars().all())

        up_signals = [s for s in signals if s.impact_direction == "UP"]
        down_signals = [s for s in signals if s.impact_direction == "DOWN"]

        if signals:
            response = (
                f"There are {len(signals)} active demand signals. "
                f"{len(up_signals)} indicate increased demand (UP) and "
                f"{len(down_signals)} indicate decreased demand (DOWN)."
            )
        else:
            response = "No active demand signals at the moment."

        return {
            "response": response,
            "data": {
                "type": "signal_status",
                "total_active": len(signals),
                "up_signals": len(up_signals),
                "down_signals": len(down_signals),
                "signals": [
                    {
                        "name": s.signal_name,
                        "type": s.signal_type,
                        "direction": s.impact_direction,
                        "impact_pct": s.impact_pct,
                        "strength": s.signal_strength,
                    }
                    for s in signals
                ],
            },
            "suggestions": [
                "Run demand sensing analysis",
                "Detect POS signals",
                "Apply signals to forecast",
            ],
            "actions": [{"label": "View Signals", "href": "/dashboard/snop/forecasts"}],
        }

    async def _handle_inventory_health(self, query: str) -> Dict[str, Any]:
        """Handle inventory health queries."""
        from app.models.inventory import InventorySummary

        total_result = await self.db.execute(
            select(func.count(InventorySummary.id))
        )
        total = total_result.scalar() or 0

        below_safety = await self.db.execute(
            select(func.count(InventorySummary.id))
            .where(InventorySummary.available_quantity <= InventorySummary.safety_stock)
        )
        below = below_safety.scalar() or 0

        response = (
            f"Inventory health: {total} product-warehouse combinations tracked. "
            f"{below} are below safety stock ({below/total*100:.0f}% at risk)."
            if total > 0 else "No inventory data available."
        )

        return {
            "response": response,
            "data": {
                "type": "inventory_health",
                "total_skus": total,
                "below_safety_stock": below,
                "at_risk_pct": round(below / total * 100, 1) if total > 0 else 0,
            },
            "suggestions": ["Show stockout risks", "Run reorder agent", "Optimize inventory"],
            "actions": [{"label": "View Inventory", "href": "/dashboard/snop/inventory-optimization"}],
        }

    async def _handle_gap_analysis(self, query: str) -> Dict[str, Any]:
        """Handle demand-supply gap queries."""
        today = date.today()
        end = today + timedelta(days=90)

        demand_result = await self.db.execute(
            select(func.sum(DemandForecast.total_forecasted_qty))
            .where(
                and_(
                    DemandForecast.is_active == True,
                    DemandForecast.status == ForecastStatus.APPROVED,
                    DemandForecast.forecast_start_date <= end,
                    DemandForecast.forecast_end_date >= today,
                )
            )
        )
        total_demand = float(demand_result.scalar() or 0)

        supply_result = await self.db.execute(
            select(func.sum(SupplyPlan.planned_production_qty + SupplyPlan.planned_procurement_qty))
            .where(
                and_(
                    SupplyPlan.is_active == True,
                    SupplyPlan.plan_start_date <= end,
                    SupplyPlan.plan_end_date >= today,
                )
            )
        )
        total_supply = float(supply_result.scalar() or 0)

        gap = total_demand - total_supply
        gap_pct = (gap / total_demand * 100) if total_demand > 0 else 0

        if gap > 0:
            response = (
                f"Demand-supply gap: {gap:,.0f} units short ({gap_pct:.1f}%). "
                f"Total 90-day demand: {total_demand:,.0f} units. "
                f"Total planned supply: {total_supply:,.0f} units. "
                f"Action needed to close the gap."
            )
        elif gap < 0:
            response = (
                f"Supply exceeds demand by {abs(gap):,.0f} units. "
                f"Consider adjusting procurement to avoid overstock."
            )
        else:
            response = "Demand and supply are balanced for the next 90 days."

        return {
            "response": response,
            "data": {
                "type": "gap_analysis",
                "total_demand": round(total_demand, 0),
                "total_supply": round(total_supply, 0),
                "gap": round(gap, 0),
                "gap_pct": round(gap_pct, 1),
                "horizon_days": 90,
            },
            "suggestions": ["Show supply plans", "Run supply optimization", "Check capacity"],
            "actions": [{"label": "View Gap Analysis", "href": "/dashboard/snop"}],
        }

    async def _handle_agent_alerts(self, query: str) -> Dict[str, Any]:
        """Handle agent/alert queries."""
        from app.services.snop.planning_agents import PlanningAgents

        agents = PlanningAgents(self.db)
        alert_data = await agents.get_alert_center(max_alerts=5)

        summary = alert_data.get("summary", {})
        alerts = alert_data.get("alerts", [])

        critical = summary.get("by_severity", {}).get("CRITICAL", 0)
        high = summary.get("by_severity", {}).get("HIGH", 0)
        total = summary.get("total_alerts", 0)

        if total == 0:
            response = "All clear! No active alerts from AI agents."
        else:
            response = (
                f"AI agents detected {total} alerts: "
                f"{critical} critical, {high} high priority. "
            )
            if alerts:
                response += f"Top alert: {alerts[0].get('title', 'Unknown')} — {alerts[0].get('message', '')}."

        return {
            "response": response,
            "data": {
                "type": "agent_alerts",
                "total": total,
                "critical": critical,
                "high": high,
                "top_alerts": [
                    {
                        "title": a.get("title"),
                        "severity": a.get("severity"),
                        "message": a.get("message"),
                        "action": a.get("recommended_action"),
                    }
                    for a in alerts
                ],
            },
            "suggestions": [
                "Run exception agent",
                "Show reorder suggestions",
                "Check forecast bias",
            ],
            "actions": [{"label": "AI Command Center", "href": "/dashboard/snop/ai-agents"}],
        }

    async def _handle_help(self, query: str) -> Dict[str, Any]:
        """Handle help queries."""
        return {
            "response": (
                "I can help you with S&OP planning queries. Try asking:\n\n"
                "- **Demand**: \"What's the demand forecast?\" or \"How accurate are our forecasts?\"\n"
                "- **Supply**: \"Show supply plans\" or \"Any demand-supply gaps?\"\n"
                "- **Inventory**: \"Check stockout risks\" or \"Any overstock issues?\"\n"
                "- **Scenarios**: \"Compare our scenarios\" or \"What-if analysis\"\n"
                "- **Signals**: \"Show active demand signals\"\n"
                "- **AI Agents**: \"Any alerts?\" or \"Run the exception agent\"\n"
            ),
            "data": {"type": "help"},
            "suggestions": [
                "What's the demand forecast?",
                "Any stockout risks?",
                "Show me demand-supply gap",
                "Compare scenarios",
            ],
            "actions": [],
        }

    async def _handle_unknown(self, query: str) -> Dict[str, Any]:
        """Handle unrecognized queries."""
        return {
            "response": (
                "I'm not sure what you're asking about. "
                "Try asking about forecasts, supply plans, inventory, scenarios, or alerts. "
                "Type 'help' for a full list of what I can help with."
            ),
            "data": {"type": "unknown"},
            "suggestions": [
                "Help",
                "What's the demand forecast?",
                "Any stockout risks?",
                "Show alerts",
            ],
            "actions": [],
        }
