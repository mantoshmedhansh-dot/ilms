"""
Inventory Network Service — Stepping-ladder geo drill-down for inventory optimization.

Provides aggregated KPIs at Enterprise → Region → Cluster → Warehouse → SKU levels
with traffic-light health indicators, forecast accuracy, and availability matrices.
"""

import uuid
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any

from sqlalchemy import select, func, and_, case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.snop import InventoryOptimization, DemandForecast
from app.models.inventory import InventorySummary
from app.models.warehouse import Warehouse
from app.models.product import Product
from app.models.region import Region


# ── Helper: resolve warehouse IDs from geo params (copied from channel_reports) ──

async def _get_warehouse_ids_for_geo(
    db: AsyncSession,
    region_id: Optional[uuid.UUID] = None,
    cluster_id: Optional[uuid.UUID] = None,
    warehouse_id: Optional[uuid.UUID] = None,
) -> Optional[List[uuid.UUID]]:
    """Resolve geographic filter to a list of warehouse IDs.

    Returns None if no geo filter is applied (means: don't filter by warehouse).
    Returns a list of warehouse UUIDs when a filter is active.
    """
    if warehouse_id:
        return [warehouse_id]

    if cluster_id:
        wh_query = select(Warehouse.id).where(
            and_(Warehouse.region_id == cluster_id, Warehouse.is_active == True)
        )
        result = await db.execute(wh_query)
        return [row[0] for row in result.all()]

    if region_id:
        children_query = select(Region.id).where(Region.parent_id == region_id)
        children_result = await db.execute(children_query)
        cluster_ids = [row[0] for row in children_result.all()]
        all_region_ids = [region_id] + cluster_ids
        wh_query = select(Warehouse.id).where(
            and_(Warehouse.region_id.in_(all_region_ids), Warehouse.is_active == True)
        )
        result = await db.execute(wh_query)
        return [row[0] for row in result.all()]

    return None


class InventoryNetworkService:
    """Stepping-ladder aggregation engine for inventory network health."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ──────────────────────────────────────────────────────────────────────
    # 1. get_network_health
    # ──────────────────────────────────────────────────────────────────────
    async def get_network_health(
        self,
        region_id: Optional[uuid.UUID] = None,
        cluster_id: Optional[uuid.UUID] = None,
        warehouse_id: Optional[uuid.UUID] = None,
    ) -> Dict[str, Any]:
        """Return KPIs for the current level and children at the next level."""

        # Determine level
        if warehouse_id:
            level, level_name = "WAREHOUSE", "Warehouse"
        elif cluster_id:
            level, level_name = "CLUSTER", "Cluster"
        elif region_id:
            level, level_name = "REGION", "Region"
        else:
            level, level_name = "ENTERPRISE", "Enterprise"

        # Resolve warehouse IDs for current scope
        wh_ids = await _get_warehouse_ids_for_geo(
            self.db, region_id=region_id, cluster_id=cluster_id, warehouse_id=warehouse_id
        )

        kpis = await self._compute_kpis(wh_ids)
        children = await self._get_children(level, region_id, cluster_id, warehouse_id)
        breadcrumb = await self._build_breadcrumb(region_id, cluster_id, warehouse_id)

        return {
            "level": level,
            "level_name": level_name,
            "kpis": kpis,
            "children": children,
            "breadcrumb": breadcrumb,
        }

    # ──────────────────────────────────────────────────────────────────────
    # 2. get_warehouse_detail
    # ──────────────────────────────────────────────────────────────────────
    async def get_warehouse_detail(
        self,
        warehouse_id: uuid.UUID,
        product_id: Optional[uuid.UUID] = None,
    ) -> Dict[str, Any]:
        """Per-SKU detail for a single warehouse."""

        # Fetch warehouse info
        wh_result = await self.db.execute(
            select(Warehouse).where(Warehouse.id == warehouse_id)
        )
        warehouse = wh_result.scalar_one_or_none()
        wh_info = {
            "id": str(warehouse.id) if warehouse else str(warehouse_id),
            "name": warehouse.name if warehouse else "Unknown",
            "code": warehouse.code if warehouse else None,
        }

        # Get optimizations for this warehouse
        opt_query = select(InventoryOptimization).where(
            InventoryOptimization.warehouse_id == warehouse_id
        )
        if product_id:
            opt_query = opt_query.where(InventoryOptimization.product_id == product_id)

        opt_result = await self.db.execute(opt_query)
        optimizations = list(opt_result.scalars().all())

        if not optimizations:
            return {
                "warehouse": wh_info,
                "summary_kpis": self._empty_kpis(),
                "sku_details": [],
            }

        # Batch fetch products
        product_ids = list({o.product_id for o in optimizations})
        prod_result = await self.db.execute(
            select(Product.id, Product.name, Product.sku).where(Product.id.in_(product_ids))
        )
        product_map = {r[0]: {"name": r[1], "sku": r[2]} for r in prod_result.all()}

        # Batch fetch current stock
        stock_result = await self.db.execute(
            select(
                InventorySummary.product_id,
                func.coalesce(func.sum(InventorySummary.available_quantity), 0),
            )
            .where(
                and_(
                    InventorySummary.warehouse_id == warehouse_id,
                    InventorySummary.product_id.in_(product_ids),
                )
            )
            .group_by(InventorySummary.product_id)
        )
        stock_map = {r[0]: float(r[1]) for r in stock_result.all()}

        # Batch fetch forecast accuracy
        forecast_result = await self.db.execute(
            select(
                DemandForecast.product_id,
                func.avg(DemandForecast.mape),
                func.sum(DemandForecast.total_forecasted_qty),
            )
            .where(
                and_(
                    DemandForecast.warehouse_id == warehouse_id,
                    DemandForecast.product_id.in_(product_ids),
                    DemandForecast.is_active == True,
                )
            )
            .group_by(DemandForecast.product_id)
        )
        forecast_map = {r[0]: {"mape": float(r[1]) if r[1] else None, "qty": float(r[2] or 0)} for r in forecast_result.all()}

        sku_details = []
        stockout_count = 0
        overstock_count = 0
        healthy_count = 0
        total_dos = 0.0
        total_fill = 0.0

        for o in optimizations:
            pid = o.product_id
            prod = product_map.get(pid, {"name": "Unknown", "sku": None})
            current_stock = stock_map.get(pid, 0)
            safety = float(o.recommended_safety_stock)
            rop = float(o.recommended_reorder_point)
            eoq = float(o.recommended_order_qty)
            avg_dd = float(o.avg_daily_demand) if o.avg_daily_demand else 0
            dos = current_stock / avg_dd if avg_dd > 0 else 999
            fill_rate = 1 - float(o.expected_stockout_rate or 0)
            fc = forecast_map.get(pid, {"mape": None, "qty": 0})
            fc_qty = fc["qty"]
            gap = current_stock - fc_qty
            gap_pct = (gap / fc_qty * 100) if fc_qty > 0 else 0

            # Status classification
            if current_stock == 0 or current_stock < safety / 2:
                s = "CRITICAL"
                action = "Urgent: Place emergency order immediately"
                stockout_count += 1
            elif current_stock < rop:
                s = "REORDER"
                action = f"Place order for {eoq:.0f} units (EOQ)"
                stockout_count += 1
            elif current_stock > rop * 1.5:
                s = "OVERSTOCK"
                action = "Reduce incoming orders; consider promotions"
                overstock_count += 1
            else:
                s = "OPTIMAL"
                action = None
                healthy_count += 1

            total_dos += min(dos, 999)
            total_fill += fill_rate

            sku_details.append({
                "product_id": str(pid),
                "product_name": prod["name"],
                "sku": prod["sku"],
                "current_stock": current_stock,
                "safety_stock": safety,
                "reorder_point": rop,
                "eoq": eoq,
                "days_of_supply": round(min(dos, 999), 1),
                "stockout_risk_pct": round(float(o.expected_stockout_rate or 0) * 100, 1),
                "is_overstock": s == "OVERSTOCK",
                "forecast_accuracy_mape": round(fc["mape"], 1) if fc["mape"] else None,
                "forecast_qty": fc_qty,
                "available_qty": current_stock,
                "gap": round(gap, 0),
                "gap_pct": round(gap_pct, 1),
                "status": s,
                "recommended_action": action,
            })

        n = len(optimizations)
        total = n
        stockout_rate = stockout_count / total * 100 if total > 0 else 0

        if stockout_rate > 10:
            health = "RED"
        elif stockout_rate > 5 or (total_dos / n if n else 999) < 7:
            health = "AMBER"
        else:
            health = "GREEN"

        summary_kpis = {
            "total_skus": total,
            "stockout_count": stockout_count,
            "overstock_count": overstock_count,
            "healthy_count": healthy_count,
            "avg_days_of_supply": round(total_dos / n, 1) if n else 0,
            "avg_fill_rate": round(total_fill / n * 100, 1) if n else 0,
            "forecast_accuracy_mape": None,
            "forecast_accuracy_wmape": None,
            "forecast_bias": None,
            "demand_supply_gap_pct": 0,
            "total_exceptions": stockout_count + overstock_count,
            "health_status": health,
        }

        return {
            "warehouse": wh_info,
            "summary_kpis": summary_kpis,
            "sku_details": sku_details,
        }

    # ──────────────────────────────────────────────────────────────────────
    # 3. get_forecast_accuracy_by_geo
    # ──────────────────────────────────────────────────────────────────────
    async def get_forecast_accuracy_by_geo(
        self,
        start_date: date,
        end_date: date,
        region_id: Optional[uuid.UUID] = None,
        cluster_id: Optional[uuid.UUID] = None,
        warehouse_id: Optional[uuid.UUID] = None,
    ) -> Dict[str, Any]:
        """Forecast accuracy aggregated by geography."""

        if warehouse_id:
            level = "WAREHOUSE"
        elif cluster_id:
            level = "CLUSTER"
        elif region_id:
            level = "REGION"
        else:
            level = "ENTERPRISE"

        wh_ids = await _get_warehouse_ids_for_geo(
            self.db, region_id=region_id, cluster_id=cluster_id, warehouse_id=warehouse_id
        )

        # Build base filter
        base_filter = and_(
            DemandForecast.is_active == True,
            DemandForecast.forecast_start_date >= start_date,
            DemandForecast.forecast_end_date <= end_date,
        )
        if wh_ids is not None:
            base_filter = and_(base_filter, DemandForecast.warehouse_id.in_(wh_ids))

        # Overall metrics
        overall_result = await self.db.execute(
            select(
                func.avg(DemandForecast.mape),
                func.avg(DemandForecast.mae),
                func.avg(DemandForecast.rmse),
                func.avg(DemandForecast.forecast_bias),
                func.count(DemandForecast.id),
                func.sum(DemandForecast.total_forecasted_qty),
            ).where(base_filter)
        )
        row = overall_result.one()
        total_volume = float(row[5] or 0)

        # WMAPE: weighted by volume
        wmape = None
        if total_volume > 0:
            wmape_result = await self.db.execute(
                select(
                    func.sum(
                        func.abs(DemandForecast.mape) * DemandForecast.total_forecasted_qty
                    ) / func.nullif(func.sum(DemandForecast.total_forecasted_qty), 0)
                ).where(and_(base_filter, DemandForecast.mape.isnot(None)))
            )
            wmape_val = wmape_result.scalar()
            wmape = round(float(wmape_val), 2) if wmape_val else None

        overall = {
            "mape": round(float(row[0]), 2) if row[0] else None,
            "wmape": wmape,
            "mae": round(float(row[1]), 2) if row[1] else None,
            "rmse": round(float(row[2]), 2) if row[2] else None,
            "bias": round(float(row[3]), 2) if row[3] else None,
            "forecast_count": row[4] or 0,
        }

        # By SKU — top 20 worst MAPE
        by_sku_result = await self.db.execute(
            select(
                DemandForecast.product_id,
                func.avg(DemandForecast.mape).label("avg_mape"),
                func.avg(DemandForecast.forecast_bias).label("avg_bias"),
                func.count(DemandForecast.id),
            )
            .where(and_(base_filter, DemandForecast.product_id.isnot(None), DemandForecast.mape.isnot(None)))
            .group_by(DemandForecast.product_id)
            .order_by(func.avg(DemandForecast.mape).desc())
            .limit(20)
        )
        by_sku_rows = by_sku_result.all()

        # Fetch product names
        sku_product_ids = [r[0] for r in by_sku_rows if r[0]]
        prod_map = {}
        if sku_product_ids:
            prod_result = await self.db.execute(
                select(Product.id, Product.name, Product.sku).where(Product.id.in_(sku_product_ids))
            )
            prod_map = {r[0]: {"name": r[1], "sku": r[2]} for r in prod_result.all()}

        by_sku = [
            {
                "product_id": str(r[0]),
                "product_name": prod_map.get(r[0], {}).get("name", "Unknown"),
                "sku": prod_map.get(r[0], {}).get("sku"),
                "mape": round(float(r[1]), 2) if r[1] else None,
                "bias": round(float(r[2]), 2) if r[2] else None,
                "count": r[3],
            }
            for r in by_sku_rows
        ]

        # By algorithm
        algo_result = await self.db.execute(
            select(
                DemandForecast.algorithm_used,
                func.avg(DemandForecast.mape),
                func.count(DemandForecast.id),
            )
            .where(and_(base_filter, DemandForecast.mape.isnot(None)))
            .group_by(DemandForecast.algorithm_used)
        )
        by_algorithm = {
            r[0]: {"mape": round(float(r[1]), 2) if r[1] else None, "count": r[2]}
            for r in algo_result.all()
        }

        # Monthly trend
        trend_result = await self.db.execute(
            select(
                func.date_trunc("month", DemandForecast.forecast_start_date).label("month"),
                func.avg(DemandForecast.mape),
                func.count(DemandForecast.id),
            )
            .where(and_(base_filter, DemandForecast.mape.isnot(None)))
            .group_by(func.date_trunc("month", DemandForecast.forecast_start_date))
            .order_by(func.date_trunc("month", DemandForecast.forecast_start_date))
        )
        trend = [
            {
                "month": r[0].isoformat() if r[0] else None,
                "mape": round(float(r[1]), 2) if r[1] else None,
                "count": r[2],
            }
            for r in trend_result.all()
        ]

        # Children accuracy (same logic as _get_children)
        children_accuracy = []
        if level == "ENTERPRISE":
            regions_result = await self.db.execute(
                select(Region).where(
                    and_(Region.is_active == True, Region.parent_id.is_(None))
                )
            )
            for reg in regions_result.scalars().all():
                child_wh_ids = await _get_warehouse_ids_for_geo(self.db, region_id=reg.id)
                if not child_wh_ids:
                    continue
                child_filter = and_(
                    base_filter,
                    DemandForecast.warehouse_id.in_(child_wh_ids),
                    DemandForecast.mape.isnot(None),
                )
                cr = await self.db.execute(
                    select(func.avg(DemandForecast.mape), func.count(DemandForecast.id)).where(child_filter)
                )
                c = cr.one()
                children_accuracy.append({
                    "id": str(reg.id), "name": reg.name, "code": reg.code, "type": "REGION",
                    "mape": round(float(c[0]), 2) if c[0] else None, "count": c[1] or 0,
                })
        elif level == "REGION":
            clusters_result = await self.db.execute(
                select(Region).where(and_(Region.parent_id == region_id, Region.is_active == True))
            )
            for cl in clusters_result.scalars().all():
                child_wh_ids = await _get_warehouse_ids_for_geo(self.db, cluster_id=cl.id)
                if not child_wh_ids:
                    continue
                child_filter = and_(
                    base_filter,
                    DemandForecast.warehouse_id.in_(child_wh_ids),
                    DemandForecast.mape.isnot(None),
                )
                cr = await self.db.execute(
                    select(func.avg(DemandForecast.mape), func.count(DemandForecast.id)).where(child_filter)
                )
                c = cr.one()
                children_accuracy.append({
                    "id": str(cl.id), "name": cl.name, "code": cl.code, "type": "CLUSTER",
                    "mape": round(float(c[0]), 2) if c[0] else None, "count": c[1] or 0,
                })
        elif level == "CLUSTER":
            whs_result = await self.db.execute(
                select(Warehouse).where(
                    and_(Warehouse.region_id == cluster_id, Warehouse.is_active == True)
                )
            )
            for wh in whs_result.scalars().all():
                child_filter = and_(
                    base_filter,
                    DemandForecast.warehouse_id == wh.id,
                    DemandForecast.mape.isnot(None),
                )
                cr = await self.db.execute(
                    select(func.avg(DemandForecast.mape), func.count(DemandForecast.id)).where(child_filter)
                )
                c = cr.one()
                children_accuracy.append({
                    "id": str(wh.id), "name": wh.name, "code": wh.code, "type": "WAREHOUSE",
                    "mape": round(float(c[0]), 2) if c[0] else None, "count": c[1] or 0,
                })

        return {
            "level": level,
            "overall": overall,
            "by_sku": by_sku,
            "by_algorithm": by_algorithm,
            "trend": trend,
            "children_accuracy": children_accuracy,
        }

    # ──────────────────────────────────────────────────────────────────────
    # 4. get_availability_vs_forecast
    # ──────────────────────────────────────────────────────────────────────
    async def get_availability_vs_forecast(
        self,
        warehouse_id: uuid.UUID,
        product_id: Optional[uuid.UUID] = None,
        horizon_days: int = 30,
    ) -> Dict[str, Any]:
        """Compare available inventory vs forecasted demand over time."""

        # Warehouse name
        wh_result = await self.db.execute(
            select(Warehouse.name).where(Warehouse.id == warehouse_id)
        )
        wh_name = wh_result.scalar() or "Unknown"

        today = date.today()
        end = today + timedelta(days=horizon_days)

        # Get forecasts with time-series data
        fc_query = select(DemandForecast).where(
            and_(
                DemandForecast.warehouse_id == warehouse_id,
                DemandForecast.is_active == True,
                DemandForecast.forecast_start_date <= end,
                DemandForecast.forecast_end_date >= today,
            )
        )
        if product_id:
            fc_query = fc_query.where(DemandForecast.product_id == product_id)

        fc_result = await self.db.execute(fc_query)
        forecasts = list(fc_result.scalars().all())

        # Get current available stock
        stock_query = select(
            func.coalesce(func.sum(InventorySummary.available_quantity), 0)
        ).where(InventorySummary.warehouse_id == warehouse_id)
        if product_id:
            stock_query = stock_query.where(InventorySummary.product_id == product_id)
        stock_result = await self.db.execute(stock_query)
        current_stock = float(stock_result.scalar() or 0)

        # Aggregate forecast_data into daily time-series
        daily_forecast: Dict[str, float] = {}
        for fc in forecasts:
            if not fc.forecast_data or not isinstance(fc.forecast_data, list):
                continue
            for entry in fc.forecast_data:
                d = entry.get("date", "")
                qty = float(entry.get("forecasted_qty", 0))
                if d:
                    daily_forecast[d] = daily_forecast.get(d, 0) + qty

        # Build comparison time-series
        comparison = []
        running_stock = current_stock
        total_forecast = 0.0
        total_available = 0.0

        current = today
        while current <= end:
            d_str = current.isoformat()
            fc_qty = daily_forecast.get(d_str, 0)
            running_stock = max(0, running_stock - fc_qty)
            total_forecast += fc_qty
            total_available += running_stock

            gap = running_stock - fc_qty
            gap_pct = (gap / fc_qty * 100) if fc_qty > 0 else 0

            if running_stock <= 0:
                day_status = "STOCKOUT"
            elif running_stock < fc_qty * 0.5:
                day_status = "CRITICAL"
            elif running_stock < fc_qty:
                day_status = "LOW"
            else:
                day_status = "OK"

            comparison.append({
                "date": d_str,
                "forecasted_qty": round(fc_qty, 1),
                "available_qty": round(running_stock, 1),
                "gap": round(gap, 1),
                "gap_pct": round(gap_pct, 1),
                "status": day_status,
            })

            current += timedelta(days=1)

        days = len(comparison)
        net_gap = current_stock - total_forecast
        avg_fulfillment = (total_available / (total_forecast * days) * 100) if (total_forecast > 0 and days > 0) else 100

        return {
            "warehouse_name": wh_name,
            "comparison": comparison,
            "summary": {
                "total_forecast": round(total_forecast, 0),
                "total_available_start": current_stock,
                "net_gap": round(net_gap, 0),
                "avg_fulfillment_rate": round(min(avg_fulfillment, 100), 1),
                "horizon_days": horizon_days,
                "stockout_days": len([c for c in comparison if c["status"] == "STOCKOUT"]),
            },
        }

    # ──────────────────────────────────────────────────────────────────────
    # Private helpers
    # ──────────────────────────────────────────────────────────────────────

    async def _compute_kpis(self, wh_ids: Optional[List[uuid.UUID]]) -> Dict[str, Any]:
        """Compute KPIs for a set of warehouse IDs (or all if None)."""

        # Get all optimizations in scope
        opt_query = select(InventoryOptimization)
        if wh_ids is not None:
            opt_query = opt_query.where(InventoryOptimization.warehouse_id.in_(wh_ids))
        opt_result = await self.db.execute(opt_query)
        optimizations = list(opt_result.scalars().all())

        if not optimizations:
            return self._empty_kpis()

        # Batch fetch current stock
        product_warehouse_pairs = [(o.product_id, o.warehouse_id) for o in optimizations]
        pw_ids = list({o.product_id for o in optimizations})
        wh_scope = list({o.warehouse_id for o in optimizations})

        stock_result = await self.db.execute(
            select(
                InventorySummary.product_id,
                InventorySummary.warehouse_id,
                func.coalesce(func.sum(InventorySummary.available_quantity), 0),
            )
            .where(
                and_(
                    InventorySummary.product_id.in_(pw_ids),
                    InventorySummary.warehouse_id.in_(wh_scope),
                )
            )
            .group_by(InventorySummary.product_id, InventorySummary.warehouse_id)
        )
        stock_map = {(r[0], r[1]): float(r[2]) for r in stock_result.all()}

        # Forecast accuracy
        fc_filter = and_(DemandForecast.is_active == True, DemandForecast.mape.isnot(None))
        if wh_ids is not None:
            fc_filter = and_(fc_filter, DemandForecast.warehouse_id.in_(wh_ids))
        fc_result = await self.db.execute(
            select(
                func.avg(DemandForecast.mape),
                func.avg(DemandForecast.forecast_bias),
                func.sum(DemandForecast.total_forecasted_qty),
            ).where(fc_filter)
        )
        fc_row = fc_result.one()
        fc_mape = round(float(fc_row[0]), 2) if fc_row[0] else None
        fc_bias = round(float(fc_row[1]), 2) if fc_row[1] else None
        total_fc_vol = float(fc_row[2] or 0)

        # WMAPE
        wmape = None
        if total_fc_vol > 0:
            wmape_result = await self.db.execute(
                select(
                    func.sum(
                        func.abs(DemandForecast.mape) * DemandForecast.total_forecasted_qty
                    ) / func.nullif(func.sum(DemandForecast.total_forecasted_qty), 0)
                ).where(fc_filter)
            )
            wmape_val = wmape_result.scalar()
            wmape = round(float(wmape_val), 2) if wmape_val else None

        stockout_count = 0
        overstock_count = 0
        healthy_count = 0
        total_dos = 0.0
        total_fill = 0.0
        total_gap = 0.0
        total_demand = 0.0

        for o in optimizations:
            current_stock = stock_map.get((o.product_id, o.warehouse_id), 0)
            rop = float(o.recommended_reorder_point)
            safety = float(o.recommended_safety_stock)
            avg_dd = float(o.avg_daily_demand) if o.avg_daily_demand else 0
            dos = current_stock / avg_dd if avg_dd > 0 else 999

            if current_stock == 0 or current_stock < safety / 2:
                stockout_count += 1
            elif current_stock < rop:
                stockout_count += 1
            elif current_stock > rop * 1.5:
                overstock_count += 1
            else:
                healthy_count += 1

            total_dos += min(dos, 999)
            total_fill += (1 - float(o.expected_stockout_rate or 0))

            demand_30 = avg_dd * 30
            total_demand += demand_30
            if demand_30 > current_stock:
                total_gap += (demand_30 - current_stock)

        n = len(optimizations)
        total = n
        stockout_rate = stockout_count / total * 100 if total > 0 else 0
        gap_pct = (total_gap / total_demand * 100) if total_demand > 0 else 0

        if stockout_rate > 10:
            health = "RED"
        elif stockout_rate > 5 or (total_dos / n if n else 999) < 7:
            health = "AMBER"
        else:
            health = "GREEN"

        return {
            "total_skus": total,
            "stockout_count": stockout_count,
            "overstock_count": overstock_count,
            "healthy_count": healthy_count,
            "avg_days_of_supply": round(total_dos / n, 1) if n else 0,
            "avg_fill_rate": round(total_fill / n * 100, 1) if n else 0,
            "forecast_accuracy_mape": fc_mape,
            "forecast_accuracy_wmape": wmape,
            "forecast_bias": fc_bias,
            "demand_supply_gap_pct": round(gap_pct, 1),
            "total_exceptions": stockout_count + overstock_count,
            "health_status": health,
        }

    async def _get_children(
        self,
        level: str,
        region_id: Optional[uuid.UUID],
        cluster_id: Optional[uuid.UUID],
        warehouse_id: Optional[uuid.UUID],
    ) -> List[Dict[str, Any]]:
        """Get child entities with KPIs for the next drill-down level."""

        children = []

        if level == "ENTERPRISE":
            # Children = top-level regions (zones)
            regions_result = await self.db.execute(
                select(Region).where(
                    and_(Region.is_active == True, Region.parent_id.is_(None))
                )
            )
            for reg in regions_result.scalars().all():
                child_wh_ids = await _get_warehouse_ids_for_geo(self.db, region_id=reg.id)
                kpis = await self._compute_kpis(child_wh_ids) if child_wh_ids else self._empty_kpis()
                children.append({
                    "id": str(reg.id), "name": reg.name, "code": reg.code,
                    "type": "REGION", "kpis": kpis,
                })

        elif level == "REGION":
            # Children = clusters (child regions)
            clusters_result = await self.db.execute(
                select(Region).where(
                    and_(Region.parent_id == region_id, Region.is_active == True)
                )
            )
            for cl in clusters_result.scalars().all():
                child_wh_ids = await _get_warehouse_ids_for_geo(self.db, cluster_id=cl.id)
                kpis = await self._compute_kpis(child_wh_ids) if child_wh_ids else self._empty_kpis()
                children.append({
                    "id": str(cl.id), "name": cl.name, "code": cl.code,
                    "type": "CLUSTER", "kpis": kpis,
                })

        elif level == "CLUSTER":
            # Children = warehouses
            whs_result = await self.db.execute(
                select(Warehouse).where(
                    and_(Warehouse.region_id == cluster_id, Warehouse.is_active == True)
                )
            )
            for wh in whs_result.scalars().all():
                kpis = await self._compute_kpis([wh.id])
                children.append({
                    "id": str(wh.id), "name": wh.name, "code": wh.code,
                    "type": "WAREHOUSE", "kpis": kpis,
                })

        # WAREHOUSE level: no children (SKUs shown via get_warehouse_detail)

        return children

    async def _build_breadcrumb(
        self,
        region_id: Optional[uuid.UUID],
        cluster_id: Optional[uuid.UUID],
        warehouse_id: Optional[uuid.UUID],
    ) -> List[Dict[str, Any]]:
        """Build breadcrumb trail for navigation."""

        breadcrumb = [{"level": "ENTERPRISE", "name": "Enterprise", "id": None}]

        if region_id:
            reg_result = await self.db.execute(
                select(Region.name, Region.code).where(Region.id == region_id)
            )
            reg = reg_result.one_or_none()
            if reg:
                breadcrumb.append({
                    "level": "REGION", "name": reg[0], "id": str(region_id), "code": reg[1],
                })

        if cluster_id:
            cl_result = await self.db.execute(
                select(Region.name, Region.code).where(Region.id == cluster_id)
            )
            cl = cl_result.one_or_none()
            if cl:
                breadcrumb.append({
                    "level": "CLUSTER", "name": cl[0], "id": str(cluster_id), "code": cl[1],
                })

        if warehouse_id:
            wh_result = await self.db.execute(
                select(Warehouse.name, Warehouse.code).where(Warehouse.id == warehouse_id)
            )
            wh = wh_result.one_or_none()
            if wh:
                breadcrumb.append({
                    "level": "WAREHOUSE", "name": wh[0], "id": str(warehouse_id), "code": wh[1],
                })

        return breadcrumb

    @staticmethod
    def _empty_kpis() -> Dict[str, Any]:
        return {
            "total_skus": 0,
            "stockout_count": 0,
            "overstock_count": 0,
            "healthy_count": 0,
            "avg_days_of_supply": 0,
            "avg_fill_rate": 0,
            "forecast_accuracy_mape": None,
            "forecast_accuracy_wmape": None,
            "forecast_bias": None,
            "demand_supply_gap_pct": 0,
            "total_exceptions": 0,
            "health_status": "GREEN",
        }
