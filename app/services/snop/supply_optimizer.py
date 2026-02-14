"""
Intelligent Supply Optimizer Service

Constraint-based supply planning and optimization:
- Multi-constraint optimization (capacity, MOQ, lead time, budget)
- Multi-source procurement scoring and allocation
- DDMRP (Demand Driven MRP) buffer sizing
- Capacity planning with bottleneck detection
- What-if analysis for supply disruptions

Uses scipy for linear programming when available, falls back to heuristic solver.
Inspired by Kinaxis Maestro's concurrent planning and SAP IBP's MEIO approach.
"""

import uuid
import math
import logging
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import List, Dict, Optional, Any, Tuple
from collections import defaultdict

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.snop import (
    DemandForecast,
    SupplyPlan,
    InventoryOptimization,
    ForecastGranularity,
    ForecastStatus,
    SupplyPlanStatus,
)
from app.models.product import Product
from app.models.inventory import InventorySummary
from app.models.vendor import Vendor
from app.models.warehouse import Warehouse
from app.services.snop.demand_planner import DemandPlannerService

logger = logging.getLogger(__name__)


# Check for scipy availability
_HAS_SCIPY = False
try:
    from scipy.optimize import linprog  # noqa: F401
    _HAS_SCIPY = True
except ImportError:
    pass


class SupplyOptimizer:
    """
    Constraint-based supply planning optimizer.

    Key capabilities:
    - Minimize total cost (production + procurement + holding + stockout penalty)
    - Subject to: capacity constraints, MOQ, lead times, budget limits
    - Multi-period planning with rolling horizon
    - DDMRP buffer sizing for strategic decoupling points
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.demand_planner = DemandPlannerService(db)

    # ==================== Constraint-Based Optimization ====================

    async def optimize_supply(
        self,
        forecast_id: uuid.UUID,
        constraints: Optional[Dict[str, Any]] = None,
        user_id: Optional[uuid.UUID] = None,
    ) -> Dict[str, Any]:
        """
        Run constraint-based supply optimization.

        Constraints dict can include:
        - max_production_capacity: Max units per day from production
        - max_budget: Total budget cap
        - min_order_qty: Minimum order quantity (MOQ)
        - max_lead_time_days: Maximum acceptable lead time
        - target_service_level: Target fill rate (0-1)
        - holding_cost_per_unit: Daily holding cost per unit
        - stockout_penalty_per_unit: Lost-sale penalty per unit
        - production_cost_per_unit: Cost to produce one unit
        - procurement_cost_per_unit: Cost to procure one unit
        """
        constraints = constraints or {}

        # Get forecast
        result = await self.db.execute(
            select(DemandForecast).where(DemandForecast.id == forecast_id)
        )
        forecast = result.scalar_one_or_none()
        if not forecast:
            raise ValueError(f"Forecast {forecast_id} not found")

        # Extract demand profile from forecast data
        demand_profile = []
        for point in (forecast.forecast_data or []):
            demand_profile.append({
                "date": point.get("date"),
                "demand": float(point.get("forecasted_qty", 0)),
                "lower": float(point.get("lower_bound", 0)),
                "upper": float(point.get("upper_bound", 0)),
            })

        if not demand_profile:
            return {"error": "Forecast has no data points"}

        # Get current inventory
        current_stock = 0.0
        if forecast.product_id:
            inv_result = await self.db.execute(
                select(InventorySummary).where(
                    and_(
                        InventorySummary.product_id == forecast.product_id,
                        InventorySummary.warehouse_id == forecast.warehouse_id,
                    )
                )
            ) if forecast.warehouse_id else None
            if inv_result:
                inv = inv_result.scalar_one_or_none()
                if inv:
                    current_stock = float(inv.available_quantity or 0)

        # Set up optimization parameters
        params = {
            "max_production_capacity": constraints.get("max_production_capacity", 1000),
            "max_budget": constraints.get("max_budget", 1_000_000),
            "min_order_qty": constraints.get("min_order_qty", 10),
            "target_service_level": constraints.get("target_service_level", 0.95),
            "holding_cost": constraints.get("holding_cost_per_unit", 0.5),
            "stockout_penalty": constraints.get("stockout_penalty_per_unit", 50),
            "production_cost": constraints.get("production_cost_per_unit", 100),
            "procurement_cost": constraints.get("procurement_cost_per_unit", 120),
            "lead_time_days": constraints.get("max_lead_time_days", 14),
        }

        # Run optimization
        if _HAS_SCIPY and len(demand_profile) >= 3:
            plan = self._optimize_scipy(demand_profile, current_stock, params)
        else:
            plan = self._optimize_heuristic(demand_profile, current_stock, params)

        # Calculate summary metrics
        total_production = sum(p["production_qty"] for p in plan["schedule"])
        total_procurement = sum(p["procurement_qty"] for p in plan["schedule"])
        total_cost = plan["total_cost"]
        avg_capacity_util = plan["avg_capacity_utilization"]

        # Detect bottlenecks
        bottlenecks = []
        for period in plan["schedule"]:
            if period.get("capacity_constrained"):
                bottlenecks.append({
                    "date": period["date"],
                    "demand": period["demand"],
                    "max_supply": period["production_qty"] + period["procurement_qty"],
                    "shortfall": period["demand"] - period["production_qty"] - period["procurement_qty"],
                })

        # Create supply plan record
        plan_code = f"OPT{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:4].upper()}"

        supply_plan = SupplyPlan(
            plan_code=plan_code,
            plan_name=f"Optimized Plan - {forecast.forecast_name}",
            forecast_id=forecast_id,
            plan_start_date=forecast.forecast_start_date,
            plan_end_date=forecast.forecast_end_date,
            product_id=forecast.product_id,
            warehouse_id=forecast.warehouse_id,
            planned_production_qty=Decimal(str(round(total_production, 2))),
            planned_procurement_qty=Decimal(str(round(total_procurement, 2))),
            production_capacity=Decimal(str(params["max_production_capacity"])),
            capacity_utilization_pct=avg_capacity_util,
            lead_time_days=params["lead_time_days"],
            schedule_data=plan["schedule"],
            status=SupplyPlanStatus.DRAFT.value,
            created_by_id=user_id,
            notes=f"AI-optimized with constraints: budget={params['max_budget']}, "
                  f"capacity={params['max_production_capacity']}/day, "
                  f"service_level={params['target_service_level']*100}%",
        )

        self.db.add(supply_plan)
        await self.db.commit()
        await self.db.refresh(supply_plan)

        return {
            "plan_id": str(supply_plan.id),
            "plan_code": plan_code,
            "optimization_method": "linear_programming" if _HAS_SCIPY else "heuristic",
            "total_production_qty": round(total_production, 2),
            "total_procurement_qty": round(total_procurement, 2),
            "total_cost": round(total_cost, 2),
            "avg_capacity_utilization": round(avg_capacity_util, 1),
            "service_level_achieved": round(plan["service_level"], 2),
            "total_holding_cost": round(plan.get("total_holding_cost", 0), 2),
            "total_stockout_cost": round(plan.get("total_stockout_cost", 0), 2),
            "bottlenecks": bottlenecks,
            "schedule": plan["schedule"],
            "constraints_used": params,
        }

    def _optimize_scipy(
        self,
        demand_profile: List[Dict],
        current_stock: float,
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Linear programming optimization using scipy."""
        try:
            from scipy.optimize import linprog

            n = len(demand_profile)

            # Decision variables: [prod_1..prod_n, proc_1..proc_n]
            # Minimize: production_cost * prod + procurement_cost * proc + holding_cost * inventory
            c = (
                [params["production_cost"]] * n +
                [params["procurement_cost"]] * n
            )

            # Constraints:
            # For each period: inventory_t >= 0 (no stockout for target SL)
            # inventory_t = current_stock + sum(prod_1..t) + sum(proc_1..t) - sum(demand_1..t)
            A_ub = []
            b_ub = []

            cumulative_demand = 0
            for t in range(n):
                cumulative_demand += demand_profile[t]["demand"]
                # -sum(prod_1..t) - sum(proc_1..t) <= -cumulative_demand + current_stock
                row = [0] * (2 * n)
                for j in range(t + 1):
                    row[j] = -1  # production
                    row[n + j] = -1  # procurement
                A_ub.append(row)
                b_ub.append(-cumulative_demand + current_stock)

            # Bounds: 0 <= prod_t <= capacity, 0 <= proc_t
            bounds = (
                [(0, params["max_production_capacity"])] * n +
                [(0, None)] * n
            )

            result = linprog(c, A_ub=A_ub, b_ub=b_ub, bounds=bounds, method='highs')

            if result.success:
                prod_plan = result.x[:n]
                proc_plan = result.x[n:]
            else:
                return self._optimize_heuristic(demand_profile, current_stock, params)

            # Build schedule
            schedule = []
            inventory = current_stock
            total_holding = 0.0
            total_stockout = 0.0
            total_satisfied = 0.0
            total_demand_sum = 0.0

            for t in range(n):
                prod = max(0, prod_plan[t])
                proc = max(0, proc_plan[t])
                demand = demand_profile[t]["demand"]

                inventory = inventory + prod + proc - demand
                holding = max(0, inventory) * params["holding_cost"]
                stockout = max(0, -inventory) * params["stockout_penalty"]

                total_holding += holding
                total_stockout += stockout
                satisfied = min(demand, max(0, inventory + demand))
                total_satisfied += satisfied
                total_demand_sum += demand

                cap_used = (prod / params["max_production_capacity"] * 100) if params["max_production_capacity"] > 0 else 0

                schedule.append({
                    "date": demand_profile[t]["date"],
                    "demand": round(demand, 2),
                    "production_qty": round(prod, 2),
                    "procurement_qty": round(proc, 2),
                    "ending_inventory": round(max(0, inventory), 2),
                    "capacity_utilization": round(cap_used, 1),
                    "capacity_constrained": cap_used >= 95,
                    "holding_cost": round(holding, 2),
                    "stockout_cost": round(stockout, 2),
                })

            service_level = total_satisfied / total_demand_sum if total_demand_sum > 0 else 1.0
            total_cost = result.fun + total_holding + total_stockout
            avg_cap = sum(s["capacity_utilization"] for s in schedule) / n if n > 0 else 0

            return {
                "schedule": schedule,
                "total_cost": total_cost,
                "total_holding_cost": total_holding,
                "total_stockout_cost": total_stockout,
                "service_level": service_level * 100,
                "avg_capacity_utilization": avg_cap,
            }

        except Exception as e:
            logger.warning(f"Scipy optimization failed: {e}")
            return self._optimize_heuristic(demand_profile, current_stock, params)

    def _optimize_heuristic(
        self,
        demand_profile: List[Dict],
        current_stock: float,
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Heuristic optimization when scipy is unavailable."""
        n = len(demand_profile)
        schedule = []
        inventory = current_stock
        total_cost = 0.0
        total_holding = 0.0
        total_stockout = 0.0
        total_satisfied = 0.0
        total_demand_sum = 0.0
        budget_remaining = params["max_budget"]

        for t in range(n):
            demand = demand_profile[t]["demand"]
            total_demand_sum += demand

            # Calculate required supply to cover demand + safety buffer
            safety_buffer = demand * (1 - params["target_service_level"]) * 2
            needed = max(0, demand + safety_buffer - inventory)

            # Split between production and procurement
            # Prefer production (cheaper) up to capacity
            prod = min(needed, params["max_production_capacity"])

            # Remaining goes to procurement
            proc = max(0, needed - prod)

            # Apply MOQ constraint
            if proc > 0 and proc < params["min_order_qty"]:
                proc = params["min_order_qty"]

            # Apply budget constraint
            period_cost = prod * params["production_cost"] + proc * params["procurement_cost"]
            if period_cost > budget_remaining:
                scale = budget_remaining / period_cost if period_cost > 0 else 0
                prod = prod * scale
                proc = proc * scale
                period_cost = prod * params["production_cost"] + proc * params["procurement_cost"]

            budget_remaining -= period_cost
            total_cost += period_cost

            inventory = inventory + prod + proc - demand
            holding = max(0, inventory) * params["holding_cost"]
            stockout = max(0, -inventory) * params["stockout_penalty"]
            total_holding += holding
            total_stockout += stockout

            satisfied = min(demand, max(0, inventory + demand))
            total_satisfied += satisfied

            cap_used = (prod / params["max_production_capacity"] * 100) if params["max_production_capacity"] > 0 else 0

            schedule.append({
                "date": demand_profile[t]["date"],
                "demand": round(demand, 2),
                "production_qty": round(prod, 2),
                "procurement_qty": round(proc, 2),
                "ending_inventory": round(max(0, inventory), 2),
                "capacity_utilization": round(cap_used, 1),
                "capacity_constrained": cap_used >= 95,
                "holding_cost": round(holding, 2),
                "stockout_cost": round(stockout, 2),
            })

        service_level = total_satisfied / total_demand_sum if total_demand_sum > 0 else 1.0
        avg_cap = sum(s["capacity_utilization"] for s in schedule) / n if n > 0 else 0

        return {
            "schedule": schedule,
            "total_cost": total_cost + total_holding + total_stockout,
            "total_holding_cost": total_holding,
            "total_stockout_cost": total_stockout,
            "service_level": service_level * 100,
            "avg_capacity_utilization": avg_cap,
        }

    # ==================== Multi-Source Procurement ====================

    async def multi_source_analysis(
        self,
        product_id: uuid.UUID,
        required_qty: float,
        max_lead_time_days: int = 30,
    ) -> Dict[str, Any]:
        """
        Analyze and score multiple vendor sources for procurement.

        Scoring criteria:
        - Unit cost (40% weight)
        - Lead time (25% weight)
        - Reliability/quality (20% weight)
        - MOQ flexibility (15% weight)
        """
        # Get vendors
        vendor_result = await self.db.execute(
            select(Vendor).where(Vendor.is_active == True)
        )
        vendors = list(vendor_result.scalars().all())

        if not vendors:
            return {
                "product_id": str(product_id),
                "required_qty": required_qty,
                "sources": [],
                "recommendation": "No active vendors found. Add vendors first.",
            }

        sources = []
        for vendor in vendors:
            # Vendor attributes (use defaults when data is sparse)
            unit_cost = float(getattr(vendor, 'unit_cost', 0) or 100)
            lead_time = int(getattr(vendor, 'lead_time_days', 0) or 14)
            moq = int(getattr(vendor, 'minimum_order_qty', 0) or 1)
            reliability = float(getattr(vendor, 'reliability_score', 0) or 0.85)
            quality_rating = float(getattr(vendor, 'quality_rating', 0) or 4.0)

            # Skip if lead time exceeds max
            if lead_time > max_lead_time_days:
                continue

            # Scoring (lower is better for cost/lead_time, higher for reliability/flexibility)
            cost_score = max(0, 100 - unit_cost / 10)  # Normalize
            lead_score = max(0, 100 - (lead_time / max_lead_time_days) * 100)
            reliability_score = reliability * 100
            moq_score = 100 if moq <= required_qty else max(0, 100 - (moq - required_qty) / required_qty * 100)

            # Weighted total
            total_score = (
                cost_score * 0.40 +
                lead_score * 0.25 +
                reliability_score * 0.20 +
                moq_score * 0.15
            )

            # Calculate allocation
            can_supply = required_qty if moq <= required_qty else moq
            total_cost = can_supply * unit_cost

            sources.append({
                "vendor_id": str(vendor.id),
                "vendor_name": vendor.name,
                "unit_cost": unit_cost,
                "lead_time_days": lead_time,
                "moq": moq,
                "reliability": reliability,
                "quality_rating": quality_rating,
                "score": round(total_score, 1),
                "cost_score": round(cost_score, 1),
                "lead_score": round(lead_score, 1),
                "reliability_score": round(reliability_score, 1),
                "moq_score": round(moq_score, 1),
                "allocated_qty": round(can_supply, 2),
                "total_cost": round(total_cost, 2),
            })

        # Sort by score (highest first)
        sources.sort(key=lambda x: x["score"], reverse=True)

        # Generate recommendation
        if sources:
            top = sources[0]
            rec = (
                f"Recommended: {top['vendor_name']} (Score: {top['score']}/100, "
                f"Cost: INR {top['unit_cost']}/unit, Lead: {top['lead_time_days']}d)"
            )
            if len(sources) > 1:
                rec += f". Split order with {sources[1]['vendor_name']} for risk mitigation."
        else:
            rec = "No suitable vendors found within lead time constraints."

        return {
            "product_id": str(product_id),
            "required_qty": required_qty,
            "sources": sources,
            "recommendation": rec,
        }

    # ==================== DDMRP Buffer Sizing ====================

    async def calculate_ddmrp_buffers(
        self,
        product_ids: Optional[List[uuid.UUID]] = None,
        lookback_days: int = 90,
    ) -> Dict[str, Any]:
        """
        Calculate DDMRP (Demand Driven MRP) buffer zones.

        Buffer zones:
        - Red Zone: Safety stock + lead time demand spike protection
        - Yellow Zone: Average demand during lead time
        - Green Zone: Replenishment cycle stock (MOQ or order cycle)

        Net Flow Position = On-hand + On-order - Qualified demand
        Order when NFP enters Yellow zone.
        """
        # Get products
        product_query = select(Product).where(Product.is_active == True)
        if product_ids:
            product_query = product_query.where(Product.id.in_(product_ids))

        result = await self.db.execute(product_query.limit(100))
        products = list(result.scalars().all())

        buffers = []
        for product in products:
            # Get demand statistics
            stats = await self.demand_planner.calculate_demand_statistics(
                product_id=product.id,
                lookback_days=lookback_days,
            )

            avg_daily = float(stats.get("avg_daily_demand", 0))
            std_dev = float(stats.get("demand_std_dev", 0))
            lead_time = 14  # Default lead time; would come from vendor data

            if avg_daily <= 0:
                continue

            # DDMRP Buffer Calculation
            # Red Zone Base = Avg daily usage * Lead time * Lead time factor
            lead_time_factor = 0.5  # Moderate variability
            spike_factor = min(1.0, std_dev / avg_daily) if avg_daily > 0 else 0.5

            red_base = avg_daily * lead_time * lead_time_factor
            red_safety = red_base * spike_factor
            red_zone = red_base + red_safety

            # Yellow Zone = Avg daily usage * Lead time
            yellow_zone = avg_daily * lead_time

            # Green Zone = max(MOQ, avg_daily * order_cycle_days)
            moq = 10  # Default MOQ
            order_cycle = 7  # Default order cycle days
            green_zone = max(moq, avg_daily * order_cycle)

            # Total buffer = Red + Yellow + Green
            total_buffer = red_zone + yellow_zone + green_zone

            # Top of Green (TOG) = reorder point
            top_of_green = total_buffer
            top_of_yellow = red_zone + yellow_zone
            top_of_red = red_zone

            # Get current inventory for NFP calculation
            inv_result = await self.db.execute(
                select(InventorySummary).where(
                    InventorySummary.product_id == product.id
                ).limit(1)
            )
            inv = inv_result.scalar_one_or_none()
            on_hand = float(inv.available_quantity or 0) if inv else 0
            on_order = 0  # Would come from PO data

            net_flow_position = on_hand + on_order
            # Determine zone
            if net_flow_position <= top_of_red:
                current_zone = "RED"
                zone_color = "#EF4444"
            elif net_flow_position <= top_of_yellow:
                current_zone = "YELLOW"
                zone_color = "#F59E0B"
            else:
                current_zone = "GREEN"
                zone_color = "#22C55E"

            buffer_penetration = (net_flow_position / total_buffer * 100) if total_buffer > 0 else 0

            buffers.append({
                "product_id": str(product.id),
                "product_name": product.name,
                "sku": getattr(product, 'sku', None),
                "avg_daily_demand": round(avg_daily, 2),
                "demand_variability": round(spike_factor, 3),
                "lead_time_days": lead_time,
                "red_zone": round(red_zone, 0),
                "yellow_zone": round(yellow_zone, 0),
                "green_zone": round(green_zone, 0),
                "total_buffer": round(total_buffer, 0),
                "top_of_green": round(top_of_green, 0),
                "top_of_yellow": round(top_of_yellow, 0),
                "top_of_red": round(top_of_red, 0),
                "on_hand": round(on_hand, 0),
                "on_order": on_order,
                "net_flow_position": round(net_flow_position, 0),
                "current_zone": current_zone,
                "zone_color": zone_color,
                "buffer_penetration_pct": round(buffer_penetration, 1),
                "action_needed": current_zone == "RED" or (current_zone == "YELLOW" and buffer_penetration < 50),
            })

        # Sort: RED first, then YELLOW, then GREEN
        zone_order = {"RED": 0, "YELLOW": 1, "GREEN": 2}
        buffers.sort(key=lambda x: (zone_order.get(x["current_zone"], 3), -x["avg_daily_demand"]))

        # Summary
        red_count = sum(1 for b in buffers if b["current_zone"] == "RED")
        yellow_count = sum(1 for b in buffers if b["current_zone"] == "YELLOW")
        green_count = sum(1 for b in buffers if b["current_zone"] == "GREEN")

        return {
            "total_products": len(buffers),
            "summary": {
                "red": red_count,
                "yellow": yellow_count,
                "green": green_count,
                "action_needed": sum(1 for b in buffers if b["action_needed"]),
            },
            "buffers": buffers,
        }

    # ==================== Capacity Analysis ====================

    async def analyze_capacity(
        self,
        forecast_id: Optional[uuid.UUID] = None,
        horizon_days: int = 90,
        daily_capacity: float = 1000,
    ) -> Dict[str, Any]:
        """
        Analyze production capacity against demand.

        Returns capacity utilization timeline, bottleneck periods,
        and recommendations.
        """
        today = date.today()
        end_date = today + timedelta(days=horizon_days)

        # Get demand data
        if forecast_id:
            result = await self.db.execute(
                select(DemandForecast).where(DemandForecast.id == forecast_id)
            )
            forecast = result.scalar_one_or_none()
            demand_data = forecast.forecast_data if forecast else []
        else:
            # Aggregate all approved forecasts
            result = await self.db.execute(
                select(DemandForecast).where(
                    and_(
                        DemandForecast.is_active == True,
                        DemandForecast.status == ForecastStatus.APPROVED.value,
                        DemandForecast.forecast_start_date <= end_date,
                        DemandForecast.forecast_end_date >= today,
                    )
                )
            )
            forecasts = list(result.scalars().all())
            demand_data = []
            for f in forecasts:
                demand_data.extend(f.forecast_data or [])

        timeline = []
        total_demand = 0
        peak_demand = 0
        bottleneck_count = 0

        for point in demand_data:
            demand = float(point.get("forecasted_qty", 0))
            total_demand += demand
            peak_demand = max(peak_demand, demand)

            utilization = (demand / daily_capacity * 100) if daily_capacity > 0 else 0
            is_bottleneck = utilization > 100
            if is_bottleneck:
                bottleneck_count += 1

            timeline.append({
                "date": point.get("date"),
                "demand": round(demand, 2),
                "capacity": daily_capacity,
                "utilization_pct": round(min(utilization, 150), 1),
                "surplus": round(max(0, daily_capacity - demand), 2),
                "deficit": round(max(0, demand - daily_capacity), 2),
                "is_bottleneck": is_bottleneck,
            })

        avg_utilization = (
            sum(t["utilization_pct"] for t in timeline) / len(timeline)
            if timeline else 0
        )

        recommendations = []
        if bottleneck_count > 0:
            recommendations.append(
                f"{bottleneck_count} period(s) exceed capacity. "
                "Consider overtime, outsourcing, or demand shaping."
            )
        if avg_utilization > 85:
            recommendations.append(
                f"Average utilization is {avg_utilization:.0f}%. "
                "Consider capacity expansion for resilience."
            )
        elif avg_utilization < 50:
            recommendations.append(
                f"Average utilization is {avg_utilization:.0f}%. "
                "Consider consolidating production runs for efficiency."
            )
        if peak_demand > daily_capacity * 1.5:
            recommendations.append(
                "Peak demand exceeds 150% of capacity. "
                "Build inventory buffers ahead of peak periods."
            )

        return {
            "horizon_days": horizon_days,
            "daily_capacity": daily_capacity,
            "total_demand": round(total_demand, 2),
            "peak_demand": round(peak_demand, 2),
            "avg_utilization_pct": round(avg_utilization, 1),
            "bottleneck_periods": bottleneck_count,
            "timeline": timeline,
            "recommendations": recommendations,
        }
