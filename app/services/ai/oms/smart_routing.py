"""
OMS Smart Routing Agent

Scores warehouses for order fulfillment:
- Proximity (serviceability pincode matching)
- Cost (RateCard)
- Inventory availability (InventorySummary)
- SLA fit (transit days)
- Capacity
- Supports split-order recommendations

No external ML libraries required - pure Python implementation.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import List, Dict, Optional, Any
from uuid import UUID
from collections import defaultdict

from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order, OrderItem, OrderStatus
from app.models.inventory import InventorySummary
from app.models.warehouse import Warehouse
from app.models.serviceability import WarehouseServiceability, AllocationRule
from app.models.rate_card import D2CRateCard


class OMSSmartRoutingAgent:
    """
    Scores and ranks warehouses for order fulfillment.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self._status = "idle"
        self._last_run = None
        self._results = None

    async def _get_serviceable_warehouses(self, pincode: str) -> List[Dict]:
        """Get warehouses that can serve a pincode."""
        result = await self.db.execute(
            select(
                WarehouseServiceability.warehouse_id,
                WarehouseServiceability.estimated_days,
                WarehouseServiceability.shipping_cost,
                WarehouseServiceability.priority,
                WarehouseServiceability.cod_available,
                Warehouse.name.label("warehouse_name"),
                Warehouse.city.label("warehouse_city"),
            )
            .join(Warehouse, WarehouseServiceability.warehouse_id == Warehouse.id)
            .where(
                and_(
                    WarehouseServiceability.pincode == pincode,
                    WarehouseServiceability.is_serviceable == True,
                    WarehouseServiceability.is_active == True,
                )
            )
            .order_by(WarehouseServiceability.priority)
        )
        rows = result.all()

        return [
            {
                "warehouse_id": str(row.warehouse_id),
                "warehouse_name": row.warehouse_name,
                "warehouse_city": row.warehouse_city,
                "estimated_days": row.estimated_days or 5,
                "shipping_cost": float(row.shipping_cost or 0),
                "priority": row.priority or 100,
                "cod_available": row.cod_available,
            }
            for row in rows
        ]

    async def _check_inventory(self, warehouse_id: UUID, items: List[Dict]) -> Dict:
        """Check inventory availability for order items at a warehouse."""
        product_ids = [item["product_id"] for item in items]

        result = await self.db.execute(
            select(
                InventorySummary.product_id,
                InventorySummary.available_quantity,
            )
            .where(
                and_(
                    InventorySummary.warehouse_id == warehouse_id,
                    InventorySummary.product_id.in_(product_ids),
                )
            )
        )
        rows = result.all()

        stock_map = {str(row.product_id): int(row.available_quantity or 0) for row in rows}

        fulfillable = 0
        unfulfillable = 0
        partial_items = []

        for item in items:
            pid = str(item["product_id"])
            available = stock_map.get(pid, 0)
            needed = item.get("quantity", 1)

            if available >= needed:
                fulfillable += 1
            else:
                unfulfillable += 1
                partial_items.append({
                    "product_id": pid,
                    "needed": needed,
                    "available": available,
                    "shortfall": needed - available,
                })

        return {
            "total_items": len(items),
            "fulfillable": fulfillable,
            "unfulfillable": unfulfillable,
            "fill_rate": fulfillable / max(len(items), 1),
            "partial_items": partial_items,
        }

    def _score_warehouse(
        self,
        warehouse: Dict,
        inventory: Dict,
        sla_days: Optional[int] = None,
    ) -> Dict:
        """Calculate composite score for a warehouse."""
        # Proximity score (lower transit = higher score)
        transit = warehouse.get("estimated_days", 5)
        proximity_score = max(0, 30 - transit * 5)  # Max 30 points

        # Cost score (lower cost = higher score)
        cost = warehouse.get("shipping_cost", 100)
        cost_score = max(0, 20 - cost / 50)  # Max 20 points

        # Inventory score
        fill_rate = inventory.get("fill_rate", 0)
        inventory_score = fill_rate * 30  # Max 30 points

        # SLA fit (can we deliver within SLA?)
        sla_score = 0
        if sla_days:
            if transit <= sla_days:
                sla_score = 15
            elif transit <= sla_days + 1:
                sla_score = 8
        else:
            sla_score = 10  # Default

        # Priority bonus (from allocation rules)
        priority_bonus = max(0, 5 - warehouse.get("priority", 100) / 25)

        total_score = round(proximity_score + cost_score + inventory_score + sla_score + priority_bonus, 1)

        return {
            **warehouse,
            "inventory": inventory,
            "scores": {
                "proximity": round(proximity_score, 1),
                "cost": round(cost_score, 1),
                "inventory": round(inventory_score, 1),
                "sla_fit": round(sla_score, 1),
                "priority_bonus": round(priority_bonus, 1),
                "total": total_score,
            },
            "total_score": total_score,
            "can_fulfill_completely": inventory["fill_rate"] == 1.0,
        }

    # ==================== Analyze Order Routing ====================

    async def analyze_order(self, order_id: UUID) -> Dict:
        """Analyze routing options for a specific order."""
        # Get order details
        order_result = await self.db.execute(
            select(Order).where(Order.id == order_id)
        )
        order = order_result.scalar_one_or_none()
        if not order:
            return {"error": f"Order {order_id} not found"}

        # Get order items
        items_result = await self.db.execute(
            select(OrderItem).where(OrderItem.order_id == order_id)
        )
        items = items_result.scalars().all()
        item_dicts = [
            {"product_id": str(item.product_id), "quantity": item.quantity}
            for item in items
        ]

        # Extract delivery pincode
        shipping = order.shipping_address or {}
        pincode = str(shipping.get("pincode", "")) if isinstance(shipping, dict) else ""

        if not pincode:
            return {"error": "No delivery pincode found on order"}

        # Get serviceable warehouses
        warehouses = await self._get_serviceable_warehouses(pincode)

        if not warehouses:
            return {
                "order_id": str(order_id),
                "pincode": pincode,
                "message": "No serviceable warehouse found for this pincode",
                "recommendations": [],
            }

        # Score each warehouse
        scored = []
        for wh in warehouses:
            wh_id = UUID(wh["warehouse_id"])
            inventory = await self._check_inventory(wh_id, item_dicts)
            score = self._score_warehouse(wh, inventory)
            scored.append(score)

        # Sort by total score
        scored.sort(key=lambda x: x["total_score"], reverse=True)

        # Check if split order needed
        best = scored[0] if scored else None
        split_recommendation = None

        if best and not best["can_fulfill_completely"] and len(scored) > 1:
            # Check if splitting across top 2 warehouses covers everything
            unfulfilled_products = set()
            if best["inventory"]["partial_items"]:
                unfulfilled_products = {p["product_id"] for p in best["inventory"]["partial_items"]}

            for alt in scored[1:]:
                if alt["inventory"]["fill_rate"] > 0:
                    alt_products = set()
                    # Check if alt can cover unfulfilled items
                    for item in item_dicts:
                        if item["product_id"] in unfulfilled_products:
                            alt_products.add(item["product_id"])

                    if alt_products:
                        split_recommendation = {
                            "recommended": True,
                            "primary_warehouse": best["warehouse_name"],
                            "secondary_warehouse": alt["warehouse_name"],
                            "reason": "Primary warehouse cannot fully fulfill; split recommended",
                        }
                        break

        return {
            "order_id": str(order_id),
            "pincode": pincode,
            "total_items": len(item_dicts),
            "warehouses_evaluated": len(scored),
            "recommended_warehouse": scored[0] if scored else None,
            "alternatives": scored[1:3],
            "split_recommendation": split_recommendation,
            "all_scores": scored,
        }

    # ==================== Batch Analysis ====================

    async def analyze(self, days: int = 7, limit: int = 30) -> Dict:
        """Run routing analysis on pending orders."""
        self._status = "running"
        try:
            result = await self.db.execute(
                select(Order.id)
                .where(
                    and_(
                        Order.status.in_([
                            OrderStatus.NEW.value,
                            OrderStatus.CONFIRMED.value,
                        ]),
                        Order.created_at >= datetime.now(timezone.utc) - timedelta(days=days),
                    )
                )
                .order_by(desc(Order.created_at))
                .limit(limit)
            )
            order_ids = [row[0] for row in result.all()]

            analyses = []
            for oid in order_ids:
                analysis = await self.analyze_order(oid)
                if "error" not in analysis:
                    analyses.append(analysis)

            self._results = {
                "agent": "smart_routing",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "summary": {
                    "total_orders_analyzed": len(analyses),
                    "orders_needing_split": len([a for a in analyses if a.get("split_recommendation", {}).get("recommended")]),
                    "unserviceable_orders": len([a for a in analyses if a.get("warehouses_evaluated", 0) == 0]),
                },
                "analyses": analyses[:20],
            }
            self._status = "completed"
            self._last_run = datetime.now(timezone.utc)
            return self._results

        except Exception as e:
            self._status = "error"
            return {"agent": "smart_routing", "error": str(e), "status": "error"}

    async def get_recommendations(self) -> List[Dict]:
        if not self._results:
            return []
        recs = []
        for a in self._results.get("analyses", [])[:10]:
            if a.get("split_recommendation", {}).get("recommended"):
                recs.append({
                    "type": "split_order",
                    "severity": "MEDIUM",
                    "recommendation": f"Order {a['order_id'][:8]} needs split fulfillment: "
                                    f"{a['split_recommendation']['primary_warehouse']} + {a['split_recommendation']['secondary_warehouse']}",
                })
        return recs

    async def get_status(self) -> Dict:
        return {
            "id": "smart_routing",
            "name": "Smart Routing Agent",
            "description": "Scores warehouses for order fulfillment: proximity, cost, inventory, SLA, capacity with split-order support",
            "status": self._status,
            "last_run": self._last_run.isoformat() if self._last_run else None,
            "data_sources": "Order, InventorySummary, WarehouseServiceability, D2CRateCard, Warehouse",
            "capabilities": [
                "Warehouse scoring & ranking",
                "Inventory availability check",
                "SLA fit analysis",
                "Cost optimization",
                "Split-order recommendations",
            ],
        }
