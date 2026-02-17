"""
OMS Returns Prediction Agent

Predicts return probability (0-1) for orders:
- Product return rate (historical)
- Category return rate
- Customer return history
- COD flag (COD has higher return rate)
- First-time buyer flag
- Seasonal patterns

Output: return_probability, risk_level, top_risk_items[]
No external ML libraries required - pure Python implementation.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import List, Dict, Optional, Tuple, Any
from uuid import UUID
import math
from collections import defaultdict

from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order, OrderItem, OrderStatus, PaymentMethod
from app.models.product import Product
from app.models.customer import Customer
from app.models.return_order import ReturnOrder


class OMSReturnsPredictionAgent:
    """
    Predicts return probability for orders.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self._status = "idle"
        self._last_run = None
        self._results = None

    async def _get_product_return_rates(self, days: int = 180) -> Dict[str, float]:
        """Calculate historical return rates by product."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        # Total orders per product
        order_result = await self.db.execute(
            select(
                OrderItem.product_id,
                func.count(OrderItem.id).label("order_count"),
            )
            .join(Order, OrderItem.order_id == Order.id)
            .where(Order.created_at >= cutoff)
            .group_by(OrderItem.product_id)
        )
        order_rows = order_result.all()
        order_map = {str(r.product_id): int(r.order_count) for r in order_rows}

        # Returns per product (from return_orders -> return_items)
        # Simplified: count return orders per product from order items
        return_result = await self.db.execute(
            select(
                OrderItem.product_id,
                func.count(ReturnOrder.id).label("return_count"),
            )
            .join(Order, OrderItem.order_id == Order.id)
            .join(ReturnOrder, ReturnOrder.order_id == Order.id)
            .where(Order.created_at >= cutoff)
            .group_by(OrderItem.product_id)
        )
        return_rows = return_result.all()
        return_map = {str(r.product_id): int(r.return_count) for r in return_rows}

        rates = {}
        for pid, total in order_map.items():
            returns = return_map.get(pid, 0)
            rates[pid] = returns / total if total > 0 else 0

        return rates

    async def _get_customer_return_rate(self, customer_id: UUID) -> float:
        """Get customer's historical return rate."""
        if not customer_id:
            return 0.0

        order_count_result = await self.db.execute(
            select(func.count(Order.id)).where(Order.customer_id == customer_id)
        )
        total_orders = order_count_result.scalar() or 0

        return_count_result = await self.db.execute(
            select(func.count(ReturnOrder.id)).where(ReturnOrder.customer_id == customer_id)
        )
        total_returns = return_count_result.scalar() or 0

        return total_returns / total_orders if total_orders > 0 else 0.0

    async def _is_first_time_buyer(self, customer_id: Optional[UUID], order_id: UUID) -> bool:
        """Check if this is a first-time buyer."""
        if not customer_id:
            return True

        result = await self.db.execute(
            select(func.count(Order.id))
            .where(
                and_(
                    Order.customer_id == customer_id,
                    Order.id != order_id,
                    Order.status != OrderStatus.CANCELLED.value,
                )
            )
        )
        return (result.scalar() or 0) == 0

    def _get_seasonal_factor(self) -> float:
        """Get seasonal return rate factor."""
        month = datetime.now().month
        # Post-holiday months have higher return rates
        seasonal_factors = {
            1: 1.3,   # Post-Xmas/NY returns
            2: 1.1,
            3: 1.0,
            4: 1.0,
            5: 1.0,
            6: 0.9,
            7: 0.9,
            8: 1.0,
            9: 1.0,
            10: 1.1,  # Pre-Diwali
            11: 1.2,  # Post-Diwali
            12: 1.1,
        }
        return seasonal_factors.get(month, 1.0)

    # ==================== Score an Order ====================

    async def score_order(self, order_id: UUID) -> Dict:
        """Predict return probability for a single order."""
        order_result = await self.db.execute(
            select(Order).where(Order.id == order_id)
        )
        order = order_result.scalar_one_or_none()
        if not order:
            return {"error": f"Order {order_id} not found"}

        items_result = await self.db.execute(
            select(OrderItem).where(OrderItem.order_id == order_id)
        )
        items = items_result.scalars().all()

        product_rates = await self._get_product_return_rates()

        # Factor weights
        weights = {
            "product_rate": 0.30,
            "customer_history": 0.20,
            "cod_flag": 0.15,
            "first_time": 0.10,
            "seasonal": 0.10,
            "value": 0.10,
            "quantity": 0.05,
        }

        # 1. Product return rate (weighted avg)
        item_risks = []
        total_product_prob = 0
        for item in items:
            pid = str(item.product_id)
            rate = product_rates.get(pid, 0.05)  # Default 5%
            item_risks.append({
                "product_id": pid,
                "return_rate": round(rate, 3),
                "quantity": item.quantity,
            })
            total_product_prob += rate

        avg_product_rate = total_product_prob / max(len(items), 1)

        # 2. Customer return history
        customer_rate = 0
        if order.customer_id:
            customer_rate = await self._get_customer_return_rate(order.customer_id)

        # 3. COD flag
        is_cod = order.payment_method in (PaymentMethod.COD.value, "COD")
        cod_factor = 0.15 if is_cod else 0

        # 4. First-time buyer
        first_time = await self._is_first_time_buyer(order.customer_id, order.id)
        first_time_factor = 0.08 if first_time else 0

        # 5. Seasonal factor
        seasonal = self._get_seasonal_factor()

        # 6. Value factor (very high or very low value = higher return risk)
        total_amount = float(order.total_amount or 0)
        if total_amount > 50000:
            value_factor = 0.05
        elif total_amount < 500:
            value_factor = 0.08
        else:
            value_factor = 0

        # 7. Quantity (many items = higher return chance)
        total_qty = sum(item.quantity for item in items)
        qty_factor = min(0.1, total_qty * 0.01)

        # Calculate weighted probability
        return_probability = (
            avg_product_rate * weights["product_rate"] / 0.30 * weights["product_rate"] +
            customer_rate * weights["customer_history"] +
            cod_factor * weights["cod_flag"] / 0.15 * weights["cod_flag"] +
            first_time_factor * weights["first_time"] / 0.10 * weights["first_time"] +
            (seasonal - 1.0) * 0.1 +
            value_factor +
            qty_factor
        )

        # Normalize to 0-1
        return_probability = max(0, min(1, return_probability * seasonal))

        # Risk level
        if return_probability >= 0.6:
            risk_level = "HIGH"
        elif return_probability >= 0.3:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        # Sort items by risk
        item_risks.sort(key=lambda x: x["return_rate"], reverse=True)

        return {
            "order_id": str(order_id),
            "return_probability": round(return_probability, 3),
            "risk_level": risk_level,
            "factors": {
                "avg_product_return_rate": round(avg_product_rate, 3),
                "customer_return_rate": round(customer_rate, 3),
                "is_cod": is_cod,
                "is_first_time_buyer": first_time,
                "seasonal_factor": seasonal,
                "order_value": total_amount,
            },
            "top_risk_items": item_risks[:5],
            "recommendation": "Flag for quality inspection before shipping" if risk_level == "HIGH"
                            else "Standard processing" if risk_level == "LOW"
                            else "Include return label in package",
        }

    # ==================== Batch Analysis ====================

    async def analyze(self, days: int = 7, limit: int = 50) -> Dict:
        """Run returns prediction on recent orders."""
        self._status = "running"
        try:
            result = await self.db.execute(
                select(Order.id)
                .where(
                    and_(
                        Order.created_at >= datetime.now(timezone.utc) - timedelta(days=days),
                        Order.status.in_([
                            OrderStatus.NEW.value,
                            OrderStatus.CONFIRMED.value,
                            OrderStatus.ALLOCATED.value,
                            OrderStatus.SHIPPED.value,
                        ]),
                    )
                )
                .order_by(desc(Order.created_at))
                .limit(limit)
            )
            order_ids = [row[0] for row in result.all()]

            scored = []
            risk_counts = defaultdict(int)

            for oid in order_ids:
                score = await self.score_order(oid)
                if "error" not in score:
                    scored.append(score)
                    risk_counts[score["risk_level"]] += 1

            scored.sort(key=lambda x: x["return_probability"], reverse=True)

            avg_prob = sum(s["return_probability"] for s in scored) / max(len(scored), 1)

            self._results = {
                "agent": "returns_prediction",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "analysis_period_days": days,
                "summary": {
                    "total_orders_scored": len(scored),
                    "by_risk_level": dict(risk_counts),
                    "avg_return_probability": round(avg_prob, 3),
                    "high_risk_orders": risk_counts.get("HIGH", 0),
                    "estimated_return_rate": f"{avg_prob:.1%}",
                },
                "scored_orders": scored[:30],
            }
            self._status = "completed"
            self._last_run = datetime.now(timezone.utc)
            return self._results

        except Exception as e:
            self._status = "error"
            return {"agent": "returns_prediction", "error": str(e), "status": "error"}

    async def get_recommendations(self) -> List[Dict]:
        if not self._results:
            return []
        recs = []
        high_risk = [s for s in self._results.get("scored_orders", []) if s["risk_level"] == "HIGH"]
        if high_risk:
            recs.append({
                "type": "return_risk",
                "severity": "MEDIUM",
                "recommendation": f"{len(high_risk)} orders flagged as high return risk. "
                                f"Consider quality checks before shipping.",
            })
        return recs

    async def get_status(self) -> Dict:
        return {
            "id": "returns_prediction",
            "name": "Returns Prediction Agent",
            "description": "Predicts return probability using product rates, customer history, COD, seasonality, and buyer profile",
            "status": self._status,
            "last_run": self._last_run.isoformat() if self._last_run else None,
            "data_sources": "Order, OrderItem, ReturnOrder, Customer, Product",
            "capabilities": [
                "Order return probability (0-1)",
                "Product return rate analysis",
                "Customer return history",
                "COD risk assessment",
                "Seasonal pattern detection",
            ],
        }
