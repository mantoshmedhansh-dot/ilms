"""
OMS Fraud Detection Agent

Weighted scoring (0-100) for order fraud risk:
- Address mismatch (billing vs shipping)
- High-value COD orders
- Velocity checks (orders/24h from same customer)
- New customer + high value
- Return history rate
- Quantity anomaly
- Time-of-day pattern

Output: risk_score, risk_level (LOW/MEDIUM/HIGH/CRITICAL), factors[]

No external ML libraries required - pure Python implementation.
"""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import List, Dict, Optional, Tuple, Any
from uuid import UUID
import math
from collections import defaultdict

from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order, OrderItem, OrderStatus, PaymentMethod
from app.models.customer import Customer
from app.models.return_order import ReturnOrder


class OMSFraudDetectionAgent:
    """
    Scores orders for fraud risk using multi-factor weighted analysis.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self._status = "idle"
        self._last_run = None
        self._results = None

    # ==================== Factor Scoring ====================

    def _score_address_mismatch(self, order: Any) -> Tuple[float, Optional[str]]:
        """Score based on billing/shipping address mismatch."""
        shipping = order.shipping_address or {}
        billing = order.billing_address or {}

        if not billing or not shipping:
            return 0, None

        # Compare key fields
        if isinstance(shipping, dict) and isinstance(billing, dict):
            ship_pin = str(shipping.get("pincode", "")).strip()
            bill_pin = str(billing.get("pincode", "")).strip()
            ship_city = str(shipping.get("city", "")).strip().lower()
            bill_city = str(billing.get("city", "")).strip().lower()

            if ship_pin and bill_pin and ship_pin != bill_pin:
                if ship_city != bill_city:
                    return 15, "Shipping and billing addresses in different cities"
                return 8, "Shipping and billing pincodes differ"

        return 0, None

    def _score_high_value_cod(self, order: Any) -> Tuple[float, Optional[str]]:
        """Score for high-value COD orders."""
        total = float(order.total_amount or 0)
        payment = order.payment_method

        if payment == PaymentMethod.COD.value or payment == "COD":
            if total > 50000:
                return 25, f"Very high value COD order: INR {total:,.0f}"
            elif total > 25000:
                return 18, f"High value COD order: INR {total:,.0f}"
            elif total > 10000:
                return 10, f"Moderately high COD order: INR {total:,.0f}"
        return 0, None

    async def _score_velocity(self, customer_id: UUID) -> Tuple[float, Optional[str]]:
        """Check order velocity from same customer in 24h."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)

        result = await self.db.execute(
            select(func.count(Order.id))
            .where(
                and_(
                    Order.customer_id == customer_id,
                    Order.created_at >= cutoff,
                )
            )
        )
        count = result.scalar() or 0

        if count > 5:
            return 20, f"Customer placed {count} orders in 24h - very unusual velocity"
        elif count > 3:
            return 12, f"Customer placed {count} orders in 24h - elevated velocity"
        elif count > 2:
            return 5, f"Customer placed {count} orders in 24h"
        return 0, None

    async def _score_new_customer_high_value(self, order: Any) -> Tuple[float, Optional[str]]:
        """Score for new customer placing high-value order."""
        if not order.customer_id:
            return 0, None

        # Check customer order history
        result = await self.db.execute(
            select(func.count(Order.id))
            .where(
                and_(
                    Order.customer_id == order.customer_id,
                    Order.id != order.id,
                )
            )
        )
        prev_orders = result.scalar() or 0
        total = float(order.total_amount or 0)

        if prev_orders == 0 and total > 20000:
            return 18, f"First-time customer with high-value order: INR {total:,.0f}"
        elif prev_orders <= 1 and total > 15000:
            return 10, f"New customer (only {prev_orders} prior orders) with order value INR {total:,.0f}"
        return 0, None

    async def _score_return_history(self, customer_id: UUID) -> Tuple[float, Optional[str]]:
        """Score based on customer return rate."""
        if not customer_id:
            return 0, None

        order_count_result = await self.db.execute(
            select(func.count(Order.id)).where(Order.customer_id == customer_id)
        )
        total_orders = order_count_result.scalar() or 0

        return_count_result = await self.db.execute(
            select(func.count(ReturnOrder.id)).where(ReturnOrder.customer_id == customer_id)
        )
        total_returns = return_count_result.scalar() or 0

        if total_orders == 0:
            return 0, None

        return_rate = total_returns / total_orders
        if return_rate > 0.5:
            return 15, f"Very high return rate: {return_rate:.0%} ({total_returns}/{total_orders})"
        elif return_rate > 0.3:
            return 8, f"Elevated return rate: {return_rate:.0%} ({total_returns}/{total_orders})"
        return 0, None

    def _score_quantity_anomaly(self, order: Any, items: List[Any]) -> Tuple[float, Optional[str]]:
        """Score for unusual quantity patterns."""
        if not items:
            return 0, None

        total_qty = sum(getattr(item, 'quantity', 0) for item in items)
        max_single = max((getattr(item, 'quantity', 0) for item in items), default=0)

        if max_single > 50:
            return 12, f"Single item quantity of {max_single} - unusually high"
        elif total_qty > 100:
            return 8, f"Total order quantity of {total_qty} - above normal"
        return 0, None

    def _score_time_of_day(self, order: Any) -> Tuple[float, Optional[str]]:
        """Score based on order time (late night orders are riskier)."""
        created = order.created_at
        if not created:
            return 0, None

        hour = created.hour if hasattr(created, 'hour') else 0
        if 1 <= hour <= 5:
            return 8, f"Order placed at unusual hour: {hour}:00"
        return 0, None

    # ==================== Score an Order ====================

    async def score_order(self, order_id: UUID) -> Dict:
        """Score a single order for fraud risk."""
        result = await self.db.execute(
            select(Order).where(Order.id == order_id)
        )
        order = result.scalar_one_or_none()

        if not order:
            return {"error": f"Order {order_id} not found"}

        # Get order items
        items_result = await self.db.execute(
            select(OrderItem).where(OrderItem.order_id == order_id)
        )
        items = items_result.scalars().all()

        # Calculate all factor scores
        factors = []
        total_score = 0

        # 1. Address mismatch
        score, reason = self._score_address_mismatch(order)
        if score > 0:
            factors.append({"factor": "address_mismatch", "score": score, "reason": reason})
            total_score += score

        # 2. High-value COD
        score, reason = self._score_high_value_cod(order)
        if score > 0:
            factors.append({"factor": "high_value_cod", "score": score, "reason": reason})
            total_score += score

        # 3. Velocity
        if order.customer_id:
            score, reason = await self._score_velocity(order.customer_id)
            if score > 0:
                factors.append({"factor": "velocity", "score": score, "reason": reason})
                total_score += score

        # 4. New customer + high value
        score, reason = await self._score_new_customer_high_value(order)
        if score > 0:
            factors.append({"factor": "new_customer_high_value", "score": score, "reason": reason})
            total_score += score

        # 5. Return history
        if order.customer_id:
            score, reason = await self._score_return_history(order.customer_id)
            if score > 0:
                factors.append({"factor": "return_history", "score": score, "reason": reason})
                total_score += score

        # 6. Quantity anomaly
        score, reason = self._score_quantity_anomaly(order, items)
        if score > 0:
            factors.append({"factor": "quantity_anomaly", "score": score, "reason": reason})
            total_score += score

        # 7. Time of day
        score, reason = self._score_time_of_day(order)
        if score > 0:
            factors.append({"factor": "time_of_day", "score": score, "reason": reason})
            total_score += score

        # Cap at 100
        risk_score = min(100, total_score)

        # Determine risk level
        if risk_score >= 70:
            risk_level = "CRITICAL"
        elif risk_score >= 50:
            risk_level = "HIGH"
        elif risk_score >= 25:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"

        return {
            "order_id": str(order_id),
            "risk_score": risk_score,
            "risk_level": risk_level,
            "factors": factors,
            "recommendation": "Hold order for manual review" if risk_level in ("CRITICAL", "HIGH")
                            else "Monitor order" if risk_level == "MEDIUM"
                            else "Auto-approve",
            "scored_at": datetime.now(timezone.utc).isoformat(),
        }

    # ==================== Batch Analysis ====================

    async def analyze(self, days: int = 7, limit: int = 50) -> Dict:
        """Run fraud detection on recent orders."""
        self._status = "running"
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)

            result = await self.db.execute(
                select(Order.id)
                .where(Order.created_at >= cutoff)
                .order_by(desc(Order.created_at))
                .limit(limit)
            )
            order_ids = [row[0] for row in result.all()]

            scored_orders = []
            risk_counts = defaultdict(int)

            for oid in order_ids:
                score = await self.score_order(oid)
                if "error" not in score:
                    scored_orders.append(score)
                    risk_counts[score["risk_level"]] += 1

            # Sort by risk score descending
            scored_orders.sort(key=lambda x: x["risk_score"], reverse=True)

            self._results = {
                "agent": "fraud_detection",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "analysis_period_days": days,
                "summary": {
                    "total_orders_scored": len(scored_orders),
                    "by_risk_level": dict(risk_counts),
                    "high_risk_orders": len([o for o in scored_orders if o["risk_level"] in ("CRITICAL", "HIGH")]),
                    "avg_risk_score": round(sum(o["risk_score"] for o in scored_orders) / max(len(scored_orders), 1), 1),
                },
                "scored_orders": scored_orders[:30],
            }
            self._status = "completed"
            self._last_run = datetime.now(timezone.utc)
            return self._results

        except Exception as e:
            self._status = "error"
            return {"agent": "fraud_detection", "error": str(e), "status": "error"}

    async def get_recommendations(self) -> List[Dict]:
        """Get fraud-related recommendations."""
        if not self._results:
            return []
        recs = []
        for order in self._results.get("scored_orders", [])[:10]:
            if order["risk_level"] in ("CRITICAL", "HIGH"):
                recs.append({
                    "type": "fraud_risk",
                    "severity": order["risk_level"],
                    "order_id": order["order_id"],
                    "recommendation": f"Order {order['order_id'][:8]} has risk score {order['risk_score']}/100. "
                                    f"{order['recommendation']}. "
                                    f"Factors: {', '.join(f['factor'] for f in order['factors'])}",
                })
        return recs

    async def get_status(self) -> Dict:
        """Get agent status."""
        return {
            "id": "fraud_detection",
            "name": "Fraud Detection Agent",
            "description": "Multi-factor fraud scoring for orders: address mismatch, high-value COD, velocity, new customer risk, return history",
            "status": self._status,
            "last_run": self._last_run.isoformat() if self._last_run else None,
            "data_sources": "Order, Customer, ReturnOrder, OrderItem",
            "capabilities": [
                "Order fraud scoring (0-100)",
                "Address mismatch detection",
                "Velocity anomaly detection",
                "Return abuse detection",
                "Auto-hold high-risk orders",
            ],
        }
