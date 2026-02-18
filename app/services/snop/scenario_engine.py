"""
Advanced Scenario Engine & Digital Twin

Provides sophisticated scenario analysis capabilities:
- Monte Carlo simulation for demand/supply uncertainty
- Financial P&L projection with revenue, COGS, margin analysis
- Sensitivity analysis for tornado charts
- Scenario comparison and ranking
- Risk quantification with confidence intervals

Competitive with: o9 Solutions Digital Twin, SAP IBP Scenario Planning, Anaplan Models
"""

import uuid
import math
import random
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import List, Dict, Optional, Any, Tuple
from collections import defaultdict

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.snop import (
    DemandForecast,
    SupplyPlan,
    SNOPScenario,
    ForecastGranularity,
    ForecastStatus,
    ScenarioStatus,
)
from app.models.product import Product
from app.models.inventory import InventorySummary


class ScenarioEngine:
    """
    Advanced scenario planning engine with Monte Carlo simulation and Digital Twin.

    Capabilities:
    1. Monte Carlo: N random simulations varying demand, supply, lead time
    2. Financial P&L: Revenue, COGS, gross margin, working capital projection
    3. Sensitivity (Tornado): Vary one parameter at a time, measure output impact
    4. Scenario Comparison: Side-by-side ranking across KPIs
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    # ==================== Monte Carlo Simulation ====================

    async def run_monte_carlo(
        self,
        scenario_id: uuid.UUID,
        num_simulations: int = 1000,
        demand_cv: float = 0.15,
        supply_cv: float = 0.10,
        lead_time_cv: float = 0.20,
        price_cv: float = 0.05,
    ) -> Dict[str, Any]:
        """
        Run Monte Carlo simulation for a scenario.

        Each iteration randomly samples:
        - Demand variation (normal distribution around forecast)
        - Supply availability (normal with supply constraints)
        - Lead time variation (lognormal)
        - Price fluctuation (normal around base price)

        Returns distribution statistics and percentile-based confidence intervals.
        """
        # Load scenario
        result = await self.db.execute(
            select(SNOPScenario).where(SNOPScenario.id == scenario_id)
        )
        scenario = result.scalar_one_or_none()
        if not scenario:
            raise ValueError(f"Scenario {scenario_id} not found")

        # Update status
        scenario.status = ScenarioStatus.RUNNING.value
        await self.db.commit()

        try:
            # Get baseline data
            baseline = await self._get_baseline_data(scenario)

            base_demand = baseline["daily_demand"]
            base_revenue_per_unit = baseline["revenue_per_unit"]
            base_cost_per_unit = baseline["cost_per_unit"]
            base_supply_capacity = baseline["supply_capacity"]
            base_lead_time = baseline["lead_time_days"]
            simulation_days = baseline["simulation_days"]

            # Apply scenario multipliers
            base_demand *= scenario.demand_multiplier
            supply_pct = scenario.supply_constraint_pct if scenario.supply_constraint_pct > 0 else 100.0
            base_supply_capacity *= supply_pct / 100.0
            base_lead_time *= scenario.lead_time_multiplier
            base_revenue_per_unit *= (1 + scenario.price_change_pct / 100.0)

            # Run simulations
            sim_results = []
            random.seed(42)  # Reproducibility

            for _ in range(num_simulations):
                sim = self._run_single_simulation(
                    base_demand=base_demand,
                    base_revenue_per_unit=base_revenue_per_unit,
                    base_cost_per_unit=base_cost_per_unit,
                    base_supply_capacity=base_supply_capacity,
                    base_lead_time=base_lead_time,
                    simulation_days=simulation_days,
                    demand_cv=demand_cv,
                    supply_cv=supply_cv,
                    lead_time_cv=lead_time_cv,
                    price_cv=price_cv,
                )
                sim_results.append(sim)

            # Aggregate results
            mc_result = self._aggregate_monte_carlo(sim_results, num_simulations)

            # Update scenario with results
            scenario.results = {
                **(scenario.results or {}),
                "monte_carlo": mc_result,
            }
            scenario.projected_revenue = Decimal(str(round(mc_result["revenue"]["mean"], 2)))
            scenario.projected_margin = Decimal(str(round(mc_result["gross_margin"]["mean"], 2)))
            scenario.stockout_probability = mc_result["stockout_probability"]
            scenario.service_level_pct = mc_result["service_level"]["mean"]
            scenario.status = ScenarioStatus.COMPLETED.value
            scenario.completed_at = datetime.now(timezone.utc)

            await self.db.commit()
            await self.db.refresh(scenario)

            return mc_result

        except Exception as e:
            scenario.status = ScenarioStatus.FAILED.value
            scenario.results = {**(scenario.results or {}), "error": str(e)}
            await self.db.commit()
            raise

    def _run_single_simulation(
        self,
        base_demand: float,
        base_revenue_per_unit: float,
        base_cost_per_unit: float,
        base_supply_capacity: float,
        base_lead_time: float,
        simulation_days: int,
        demand_cv: float,
        supply_cv: float,
        lead_time_cv: float,
        price_cv: float,
    ) -> Dict[str, float]:
        """Run a single Monte Carlo iteration."""

        # Sample demand (normal, clamp >=0)
        demand_std = base_demand * demand_cv
        simulated_demand = max(0, random.gauss(base_demand, demand_std)) * simulation_days

        # Sample supply capacity
        supply_std = base_supply_capacity * supply_cv
        simulated_supply = max(0, random.gauss(base_supply_capacity, supply_std)) * simulation_days

        # Sample lead time (lognormal to ensure positive)
        lt_sigma = math.sqrt(math.log(1 + lead_time_cv ** 2))
        lt_mu = math.log(base_lead_time) - lt_sigma ** 2 / 2
        simulated_lead_time = random.lognormvariate(lt_mu, lt_sigma)

        # Sample price
        price_std = base_revenue_per_unit * price_cv
        simulated_price = max(0.01, random.gauss(base_revenue_per_unit, price_std))

        # Calculate outcomes
        units_sold = min(simulated_demand, simulated_supply)
        lost_sales = max(0, simulated_demand - simulated_supply)
        excess_inventory = max(0, simulated_supply - simulated_demand)

        revenue = units_sold * simulated_price
        cogs = units_sold * base_cost_per_unit
        gross_margin = revenue - cogs
        margin_pct = (gross_margin / revenue * 100) if revenue > 0 else 0

        # Holding cost for excess inventory
        holding_cost = excess_inventory * base_cost_per_unit * 0.25 / 12  # Monthly holding
        lost_sales_cost = lost_sales * simulated_price * 0.5  # Opportunity cost

        net_profit = gross_margin - holding_cost - lost_sales_cost

        # Service level
        service_level = (units_sold / simulated_demand * 100) if simulated_demand > 0 else 100
        stockout = 1 if lost_sales > 0 else 0

        # Working capital (average inventory value)
        avg_inventory = (simulated_supply - units_sold / 2) * base_cost_per_unit
        inventory_turns = (cogs / avg_inventory) if avg_inventory > 0 else 0

        return {
            "revenue": revenue,
            "cogs": cogs,
            "gross_margin": gross_margin,
            "margin_pct": margin_pct,
            "net_profit": net_profit,
            "units_sold": units_sold,
            "lost_sales": lost_sales,
            "excess_inventory": excess_inventory,
            "holding_cost": holding_cost,
            "lost_sales_cost": lost_sales_cost,
            "service_level": service_level,
            "stockout": stockout,
            "lead_time": simulated_lead_time,
            "inventory_turns": inventory_turns,
            "working_capital": max(0, avg_inventory),
        }

    def _aggregate_monte_carlo(
        self, results: List[Dict[str, float]], n: int
    ) -> Dict[str, Any]:
        """Aggregate Monte Carlo simulation results into statistics."""

        metrics = [
            "revenue", "cogs", "gross_margin", "margin_pct", "net_profit",
            "units_sold", "lost_sales", "excess_inventory", "holding_cost",
            "lost_sales_cost", "service_level", "lead_time",
            "inventory_turns", "working_capital",
        ]

        stats = {}
        for metric in metrics:
            values = sorted([r[metric] for r in results])
            n_vals = len(values)

            mean_val = sum(values) / n_vals
            variance = sum((v - mean_val) ** 2 for v in values) / n_vals
            std_val = math.sqrt(variance)

            stats[metric] = {
                "mean": round(mean_val, 2),
                "std": round(std_val, 2),
                "min": round(values[0], 2),
                "max": round(values[-1], 2),
                "p5": round(values[int(n_vals * 0.05)], 2),
                "p25": round(values[int(n_vals * 0.25)], 2),
                "p50": round(values[int(n_vals * 0.50)], 2),
                "p75": round(values[int(n_vals * 0.75)], 2),
                "p95": round(values[int(n_vals * 0.95)], 2),
            }

        # Stockout probability
        stockout_count = sum(1 for r in results if r["stockout"] == 1)
        stockout_prob = round(stockout_count / n, 4)

        # Revenue distribution histogram (10 buckets)
        rev_values = sorted([r["revenue"] for r in results])
        rev_min, rev_max = rev_values[0], rev_values[-1]
        bucket_size = (rev_max - rev_min) / 10 if rev_max > rev_min else 1
        histogram = []
        for i in range(10):
            lo = rev_min + i * bucket_size
            hi = lo + bucket_size
            count = sum(1 for v in rev_values if lo <= v < hi) if i < 9 else sum(1 for v in rev_values if v >= lo)
            histogram.append({
                "range_start": round(lo, 0),
                "range_end": round(hi, 0),
                "count": count,
                "probability": round(count / n, 4),
            })

        return {
            **stats,
            "stockout_probability": stockout_prob,
            "num_simulations": n,
            "revenue_histogram": histogram,
        }

    # ==================== Financial P&L Projection ====================

    async def project_financial_pl(
        self,
        scenario_id: uuid.UUID,
        avg_unit_price: float = 1000.0,
        cogs_pct: float = 60.0,
        operating_expense_pct: float = 15.0,
        tax_rate_pct: float = 25.0,
        working_capital_days: int = 45,
    ) -> Dict[str, Any]:
        """
        Generate financial P&L projection for a scenario.

        Returns monthly breakdown of:
        - Revenue, COGS, Gross Margin
        - Operating Expenses, EBITDA
        - Tax, Net Income
        - Working Capital, Cash Flow
        """
        result = await self.db.execute(
            select(SNOPScenario).where(SNOPScenario.id == scenario_id)
        )
        scenario = result.scalar_one_or_none()
        if not scenario:
            raise ValueError(f"Scenario {scenario_id} not found")

        baseline = await self._get_baseline_data(scenario)
        base_daily_demand = baseline["daily_demand"] * scenario.demand_multiplier

        start = scenario.simulation_start_date
        end = scenario.simulation_end_date

        # Generate monthly projections
        monthly = []
        current = date(start.year, start.month, 1)

        while current <= end:
            # Days in this month within simulation window
            month_end = date(
                current.year + (current.month // 12),
                (current.month % 12) + 1,
                1
            ) - timedelta(days=1)
            effective_start = max(current, start)
            effective_end = min(month_end, end)
            days_in_period = (effective_end - effective_start).days + 1

            if days_in_period <= 0:
                current = month_end + timedelta(days=1)
                continue

            # Apply seasonal factor (simplified)
            month_num = current.month
            seasonal_factors = {
                1: 0.85, 2: 0.80, 3: 0.90, 4: 0.95,
                5: 1.00, 6: 1.05, 7: 1.10, 8: 1.05,
                9: 1.15, 10: 1.20, 11: 1.25, 12: 1.10,
            }
            seasonal = seasonal_factors.get(month_num, 1.0)

            units = base_daily_demand * days_in_period * seasonal
            price = avg_unit_price * (1 + scenario.price_change_pct / 100)

            revenue = units * price
            cogs = revenue * cogs_pct / 100
            gross_margin = revenue - cogs
            opex = revenue * operating_expense_pct / 100
            ebitda = gross_margin - opex
            tax = max(0, ebitda * tax_rate_pct / 100)
            net_income = ebitda - tax

            # Working capital
            wc = revenue * working_capital_days / 365

            monthly.append({
                "month": current.strftime("%Y-%m"),
                "month_label": current.strftime("%b %Y"),
                "days": days_in_period,
                "units_sold": round(units, 0),
                "avg_price": round(price, 2),
                "revenue": round(revenue, 2),
                "cogs": round(cogs, 2),
                "gross_margin": round(gross_margin, 2),
                "gross_margin_pct": round((gross_margin / revenue * 100) if revenue > 0 else 0, 1),
                "operating_expenses": round(opex, 2),
                "ebitda": round(ebitda, 2),
                "ebitda_pct": round((ebitda / revenue * 100) if revenue > 0 else 0, 1),
                "tax": round(tax, 2),
                "net_income": round(net_income, 2),
                "net_margin_pct": round((net_income / revenue * 100) if revenue > 0 else 0, 1),
                "working_capital": round(wc, 2),
            })

            current = month_end + timedelta(days=1)

        # Totals
        total_revenue = sum(m["revenue"] for m in monthly)
        total_cogs = sum(m["cogs"] for m in monthly)
        total_gross_margin = sum(m["gross_margin"] for m in monthly)
        total_opex = sum(m["operating_expenses"] for m in monthly)
        total_ebitda = sum(m["ebitda"] for m in monthly)
        total_tax = sum(m["tax"] for m in monthly)
        total_net = sum(m["net_income"] for m in monthly)
        total_units = sum(m["units_sold"] for m in monthly)

        # Waterfall data for chart
        waterfall = [
            {"label": "Revenue", "value": round(total_revenue, 2), "type": "total"},
            {"label": "COGS", "value": round(-total_cogs, 2), "type": "negative"},
            {"label": "Gross Margin", "value": round(total_gross_margin, 2), "type": "subtotal"},
            {"label": "OpEx", "value": round(-total_opex, 2), "type": "negative"},
            {"label": "EBITDA", "value": round(total_ebitda, 2), "type": "subtotal"},
            {"label": "Tax", "value": round(-total_tax, 2), "type": "negative"},
            {"label": "Net Income", "value": round(total_net, 2), "type": "total"},
        ]

        pl_result = {
            "scenario_id": str(scenario_id),
            "scenario_name": scenario.scenario_name,
            "period": f"{start.isoformat()} to {end.isoformat()}",
            "summary": {
                "total_revenue": round(total_revenue, 2),
                "total_cogs": round(total_cogs, 2),
                "total_gross_margin": round(total_gross_margin, 2),
                "gross_margin_pct": round((total_gross_margin / total_revenue * 100) if total_revenue > 0 else 0, 1),
                "total_operating_expenses": round(total_opex, 2),
                "total_ebitda": round(total_ebitda, 2),
                "ebitda_pct": round((total_ebitda / total_revenue * 100) if total_revenue > 0 else 0, 1),
                "total_tax": round(total_tax, 2),
                "total_net_income": round(total_net, 2),
                "net_margin_pct": round((total_net / total_revenue * 100) if total_revenue > 0 else 0, 1),
                "total_units": round(total_units, 0),
            },
            "monthly_projections": monthly,
            "waterfall": waterfall,
        }

        # Store in scenario results
        scenario.results = {**(scenario.results or {}), "financial_pl": pl_result}
        scenario.projected_revenue = Decimal(str(round(total_revenue, 2)))
        scenario.projected_margin = Decimal(str(round(total_gross_margin, 2)))
        await self.db.commit()

        return pl_result

    # ==================== Sensitivity Analysis (Tornado Chart) ====================

    async def sensitivity_analysis(
        self,
        scenario_id: uuid.UUID,
        parameters: Optional[List[str]] = None,
        variation_pct: float = 20.0,
    ) -> Dict[str, Any]:
        """
        Run sensitivity analysis for tornado chart visualization.

        Varies each parameter independently by +/- variation_pct while
        holding all others constant, measuring impact on revenue and margin.
        """
        result = await self.db.execute(
            select(SNOPScenario).where(SNOPScenario.id == scenario_id)
        )
        scenario = result.scalar_one_or_none()
        if not scenario:
            raise ValueError(f"Scenario {scenario_id} not found")

        baseline = await self._get_baseline_data(scenario)

        all_params = parameters or [
            "demand", "price", "cogs", "supply_capacity",
            "lead_time", "operating_expenses", "holding_cost",
        ]

        # Calculate baseline outcome
        base_outcome = self._calculate_scenario_outcome(scenario, baseline, {})

        tornado_data = []

        for param in all_params:
            # Low variation
            low_override = {param: -variation_pct}
            low_outcome = self._calculate_scenario_outcome(scenario, baseline, low_override)

            # High variation
            high_override = {param: variation_pct}
            high_outcome = self._calculate_scenario_outcome(scenario, baseline, high_override)

            revenue_impact_low = low_outcome["revenue"] - base_outcome["revenue"]
            revenue_impact_high = high_outcome["revenue"] - base_outcome["revenue"]

            margin_impact_low = low_outcome["net_income"] - base_outcome["net_income"]
            margin_impact_high = high_outcome["net_income"] - base_outcome["net_income"]

            # The "spread" (range) tells us sensitivity
            revenue_spread = abs(revenue_impact_high - revenue_impact_low)

            tornado_data.append({
                "parameter": param,
                "parameter_label": param.replace("_", " ").title(),
                "variation_pct": variation_pct,
                "revenue": {
                    "base": round(base_outcome["revenue"], 2),
                    "low": round(low_outcome["revenue"], 2),
                    "high": round(high_outcome["revenue"], 2),
                    "impact_low": round(revenue_impact_low, 2),
                    "impact_high": round(revenue_impact_high, 2),
                    "spread": round(revenue_spread, 2),
                },
                "net_income": {
                    "base": round(base_outcome["net_income"], 2),
                    "low": round(low_outcome["net_income"], 2),
                    "high": round(high_outcome["net_income"], 2),
                    "impact_low": round(margin_impact_low, 2),
                    "impact_high": round(margin_impact_high, 2),
                    "spread": round(abs(margin_impact_high - margin_impact_low), 2),
                },
            })

        # Sort by revenue spread (most sensitive first)
        tornado_data.sort(key=lambda x: x["revenue"]["spread"], reverse=True)

        sensitivity_result = {
            "scenario_id": str(scenario_id),
            "scenario_name": scenario.scenario_name,
            "variation_pct": variation_pct,
            "base_revenue": round(base_outcome["revenue"], 2),
            "base_net_income": round(base_outcome["net_income"], 2),
            "tornado_data": tornado_data,
            "most_sensitive": tornado_data[0]["parameter"] if tornado_data else None,
            "least_sensitive": tornado_data[-1]["parameter"] if tornado_data else None,
        }

        # Store
        scenario.results = {**(scenario.results or {}), "sensitivity": sensitivity_result}
        await self.db.commit()

        return sensitivity_result

    def _calculate_scenario_outcome(
        self,
        scenario: SNOPScenario,
        baseline: Dict[str, float],
        overrides: Dict[str, float],
    ) -> Dict[str, float]:
        """Calculate financial outcome with parameter overrides (% change)."""

        days = baseline["simulation_days"]

        # Base values with scenario multipliers
        demand = baseline["daily_demand"] * scenario.demand_multiplier * days
        price = baseline["revenue_per_unit"] * (1 + scenario.price_change_pct / 100)
        cost_pct = 60.0  # COGS as % of revenue
        supply_pct = scenario.supply_constraint_pct if scenario.supply_constraint_pct > 0 else 100.0
        supply_cap = baseline["supply_capacity"] * (supply_pct / 100) * days
        lead_time = baseline["lead_time_days"] * scenario.lead_time_multiplier
        opex_pct = 15.0
        holding_cost_rate = 0.25

        # Apply overrides
        for param, pct in overrides.items():
            factor = 1 + pct / 100
            if param == "demand":
                demand *= factor
            elif param == "price":
                price *= factor
            elif param == "cogs":
                cost_pct *= factor
            elif param == "supply_capacity":
                supply_cap *= factor
            elif param == "lead_time":
                lead_time *= factor
            elif param == "operating_expenses":
                opex_pct *= factor
            elif param == "holding_cost":
                holding_cost_rate *= factor

        # Lead time impact: longer lead time causes customer defection (lost demand)
        base_lt = baseline["lead_time_days"]
        if base_lt > 0 and lead_time > 0:
            lt_ratio = lead_time / base_lt
            # Each 10% increase in lead time reduces effective demand by 3%
            service_penalty = max(0.5, 1 - (lt_ratio - 1) * 0.3)
        else:
            service_penalty = 1.0
        effective_demand = demand * service_penalty

        # Outcomes
        units_sold = min(effective_demand, supply_cap)
        revenue = units_sold * price
        cogs = revenue * cost_pct / 100
        gross_margin = revenue - cogs
        opex = revenue * opex_pct / 100
        ebitda = gross_margin - opex

        excess = max(0, supply_cap - effective_demand)
        holding_cost = excess * baseline["cost_per_unit"] * holding_cost_rate / 12

        net_income = ebitda - holding_cost
        service_level = (units_sold / demand * 100) if demand > 0 else 100

        return {
            "revenue": revenue,
            "cogs": cogs,
            "gross_margin": gross_margin,
            "opex": opex,
            "ebitda": ebitda,
            "holding_cost": holding_cost,
            "net_income": net_income,
            "units_sold": units_sold,
            "service_level": service_level,
        }

    # ==================== Scenario Comparison ====================

    async def compare_scenarios_advanced(
        self,
        scenario_ids: List[uuid.UUID],
        ranking_weights: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """
        Advanced scenario comparison with weighted scoring.

        Ranks scenarios across multiple KPIs:
        - Revenue (weight: 30%)
        - Net Income (weight: 25%)
        - Service Level (weight: 20%)
        - Risk (inverse stockout prob) (weight: 15%)
        - Working Capital efficiency (weight: 10%)
        """
        weights = ranking_weights or {
            "revenue": 0.30,
            "net_income": 0.25,
            "service_level": 0.20,
            "risk_score": 0.15,
            "efficiency": 0.10,
        }

        result = await self.db.execute(
            select(SNOPScenario).where(SNOPScenario.id.in_(scenario_ids))
        )
        scenarios = list(result.scalars().all())

        if len(scenarios) < 2:
            raise ValueError("Need at least 2 scenarios to compare")

        comparison = []
        for sc in scenarios:
            mc = (sc.results or {}).get("monte_carlo", {})
            pl = (sc.results or {}).get("financial_pl", {})

            revenue = mc.get("revenue", {}).get("mean", 0) or (pl.get("summary", {}).get("total_revenue", 0))
            net_income = mc.get("net_profit", {}).get("mean", 0) or (pl.get("summary", {}).get("total_net_income", 0))
            service_level = mc.get("service_level", {}).get("mean", 95)
            stockout_prob = mc.get("stockout_probability", 0.05)
            inv_turns = mc.get("inventory_turns", {}).get("mean", 8)

            comparison.append({
                "scenario_id": str(sc.id),
                "scenario_name": sc.scenario_name,
                "status": sc.status,
                "assumptions": sc.assumptions,
                "metrics": {
                    "revenue": round(revenue, 2),
                    "net_income": round(net_income, 2),
                    "gross_margin_pct": round(mc.get("margin_pct", {}).get("mean", 25), 1),
                    "service_level": round(service_level, 2),
                    "stockout_probability": round(stockout_prob, 4),
                    "inventory_turns": round(inv_turns, 2),
                    "risk_score": round((1 - stockout_prob) * 100, 2),
                },
                "revenue_range": {
                    "p5": mc.get("revenue", {}).get("p5", revenue * 0.85),
                    "p95": mc.get("revenue", {}).get("p95", revenue * 1.15),
                },
            })

        # Normalize and score
        if comparison:
            # Find min/max for normalization
            metrics_to_norm = ["revenue", "net_income", "service_level", "risk_score"]
            ranges = {}
            for m in metrics_to_norm:
                vals = [c["metrics"].get(m, 0) for c in comparison]
                ranges[m] = {"min": min(vals), "max": max(vals)}

            for c in comparison:
                score = 0
                scores_breakdown = {}
                for m in metrics_to_norm:
                    r = ranges[m]
                    spread = r["max"] - r["min"]
                    if spread > 0:
                        normalized = (c["metrics"].get(m, 0) - r["min"]) / spread
                    else:
                        normalized = 1.0
                    weighted = normalized * weights.get(m, 0)
                    score += weighted
                    scores_breakdown[m] = round(weighted, 4)

                # Efficiency: higher inventory turns = better
                inv_vals = [c2["metrics"].get("inventory_turns", 8) for c2 in comparison]
                inv_spread = max(inv_vals) - min(inv_vals)
                if inv_spread > 0:
                    eff_norm = (c["metrics"]["inventory_turns"] - min(inv_vals)) / inv_spread
                else:
                    eff_norm = 1.0
                eff_score = eff_norm * weights.get("efficiency", 0.1)
                score += eff_score
                scores_breakdown["efficiency"] = round(eff_score, 4)

                c["composite_score"] = round(score, 4)
                c["score_breakdown"] = scores_breakdown

            # Rank by composite score
            comparison.sort(key=lambda x: x["composite_score"], reverse=True)
            for i, c in enumerate(comparison):
                c["rank"] = i + 1

        # Recommendation
        best = comparison[0] if comparison else None
        recommendation = None
        if best:
            recommendation = (
                f"'{best['scenario_name']}' ranks highest with a composite score of "
                f"{best['composite_score']:.2f}. It projects revenue of "
                f"INR {best['metrics']['revenue']:,.0f} with {best['metrics']['service_level']:.1f}% "
                f"service level and {best['metrics']['stockout_probability']:.1%} stockout risk."
            )

        return {
            "scenarios": comparison,
            "ranking_weights": weights,
            "recommendation": recommendation,
            "best_scenario_id": best["scenario_id"] if best else None,
        }

    # ==================== What-If Quick Analysis ====================

    async def quick_what_if(
        self,
        demand_change_pct: float = 0,
        price_change_pct: float = 0,
        supply_change_pct: float = 0,
        lead_time_change_pct: float = 0,
        cogs_change_pct: float = 0,
    ) -> Dict[str, Any]:
        """
        Quick what-if analysis without creating a scenario record.

        Returns instant impact assessment for parameter changes.
        """
        # Get current baseline from recent data
        today = date.today()
        start = today - timedelta(days=90)

        from app.services.snop.demand_planner import DemandPlannerService
        planner = DemandPlannerService(self.db)

        hist = await planner.get_historical_demand(
            start_date=start, end_date=today,
            granularity=ForecastGranularity.DAILY,
        )

        if hist:
            avg_daily_revenue = sum(float(d["revenue"]) for d in hist) / len(hist)
            avg_daily_qty = sum(float(d["quantity"]) for d in hist) / len(hist)
        else:
            avg_daily_revenue = 50000
            avg_daily_qty = 50

        base_price = avg_daily_revenue / avg_daily_qty if avg_daily_qty > 0 else 1000
        base_cogs_pct = 60
        base_opex_pct = 15

        # Apply changes
        adj_demand = avg_daily_qty * (1 + demand_change_pct / 100)
        adj_price = base_price * (1 + price_change_pct / 100)
        adj_supply = avg_daily_qty * 1.1 * (1 + supply_change_pct / 100)  # 10% buffer
        adj_cogs_pct = base_cogs_pct * (1 + cogs_change_pct / 100)

        # 90-day projection
        projection_days = 90
        units = min(adj_demand, adj_supply) * projection_days
        revenue = units * adj_price
        cogs = revenue * adj_cogs_pct / 100
        gross_margin = revenue - cogs
        opex = revenue * base_opex_pct / 100
        net_income = gross_margin - opex

        base_units = avg_daily_qty * projection_days
        base_revenue = base_units * base_price
        base_cogs = base_revenue * base_cogs_pct / 100
        base_gross = base_revenue - base_cogs
        base_opex = base_revenue * base_opex_pct / 100
        base_net = base_gross - base_opex

        return {
            "projection_days": projection_days,
            "baseline": {
                "units": round(base_units, 0),
                "revenue": round(base_revenue, 2),
                "cogs": round(base_cogs, 2),
                "gross_margin": round(base_gross, 2),
                "net_income": round(base_net, 2),
            },
            "projected": {
                "units": round(units, 0),
                "revenue": round(revenue, 2),
                "cogs": round(cogs, 2),
                "gross_margin": round(gross_margin, 2),
                "net_income": round(net_income, 2),
            },
            "impact": {
                "revenue_change": round(revenue - base_revenue, 2),
                "revenue_change_pct": round((revenue / base_revenue - 1) * 100, 2) if base_revenue > 0 else 0,
                "margin_change": round(net_income - base_net, 2),
                "margin_change_pct": round((net_income / base_net - 1) * 100, 2) if base_net > 0 else 0,
                "units_change": round(units - base_units, 0),
            },
            "parameters_applied": {
                "demand_change_pct": demand_change_pct,
                "price_change_pct": price_change_pct,
                "supply_change_pct": supply_change_pct,
                "lead_time_change_pct": lead_time_change_pct,
                "cogs_change_pct": cogs_change_pct,
            },
        }

    # ==================== Helpers ====================

    async def _get_baseline_data(self, scenario: SNOPScenario) -> Dict[str, float]:
        """Get baseline data for scenario simulation."""

        from app.services.snop.demand_planner import DemandPlannerService
        planner = DemandPlannerService(self.db)

        # Get historical demand for baseline
        lookback_start = scenario.simulation_start_date - timedelta(days=365)
        lookback_end = scenario.simulation_start_date

        hist = await planner.get_historical_demand(
            start_date=lookback_start,
            end_date=lookback_end,
            granularity=ForecastGranularity.DAILY,
        )

        if hist:
            avg_daily_revenue = sum(float(d["revenue"]) for d in hist) / len(hist)
            avg_daily_qty = sum(float(d["quantity"]) for d in hist) / len(hist)
        else:
            avg_daily_revenue = 50000
            avg_daily_qty = 50

        revenue_per_unit = avg_daily_revenue / avg_daily_qty if avg_daily_qty > 0 else 1000
        cost_per_unit = revenue_per_unit * 0.6  # 60% COGS assumption

        simulation_days = (scenario.simulation_end_date - scenario.simulation_start_date).days + 1

        # Get supply capacity from recent supply plans
        supply_result = await self.db.execute(
            select(func.avg(SupplyPlan.production_capacity))
            .where(SupplyPlan.is_active == True)
        )
        avg_capacity = supply_result.scalar() or 0
        daily_capacity = float(avg_capacity) if avg_capacity > 0 else avg_daily_qty * 1.1

        return {
            "daily_demand": avg_daily_qty,
            "daily_revenue": avg_daily_revenue,
            "revenue_per_unit": revenue_per_unit,
            "cost_per_unit": cost_per_unit,
            "supply_capacity": daily_capacity,
            "lead_time_days": 14,
            "simulation_days": simulation_days,
        }
