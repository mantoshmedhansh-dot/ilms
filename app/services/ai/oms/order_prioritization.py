"""
OMS Order Prioritization Agent

Scores and prioritizes pending orders:
- Order value (higher = more priority)
- SLA urgency (hours to breach)
- Customer tier (order history count)
- Order aging (older = more urgent)
- Channel priority
- Payment type (prepaid > COD)

Returns prioritized queue.
No external ML libraries required - pure Python implementation.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import List, Dict, Optional, Any, Tuple
from uuid import UUID
from collections import defaultdict

from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order, OrderItem, OrderStatus, PaymentMethod, OrderSource


class OMSOrderPrioritizationAgent:
    """
    Scores and prioritizes pending orders for fulfillment.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self._status = "idle"
        self._last_run = None
        self._results = None

    async def _get_customer_tier(self, customer_id: Optional[UUID]) -> Tuple[str, int]:
        """Get customer tier based on order history."""
        if not customer_id:
            return "NEW", 0

        result = await self.db.execute(
            select(func.count(Order.id))
            .where(
                and_(
                    Order.customer_id == customer_id,
                    Order.status.in_([
                        OrderStatus.DELIVERED.value,
                        OrderStatus.SHIPPED.value,
                    ]),
                )
            )
        )
        count = result.scalar() or 0

        if count >= 20:
            return "PLATINUM", count
        elif count >= 10:
            return "GOLD", count
        elif count >= 5:
            return "SILVER", count
        elif count >= 1:
            return "BRONZE", count
        return "NEW", count

    def _score_order(
        self,
        order: Any,
        customer_tier: str,
        order_count: int,
    ) -> Dict:
        """Calculate priority score for an order."""
        total_score = 0
        factors = []

        # 1. Value score (0-25 points)
        total_amount = float(order.total_amount or 0)
        if total_amount >= 50000:
            value_score = 25
        elif total_amount >= 20000:
            value_score = 20
        elif total_amount >= 10000:
            value_score = 15
        elif total_amount >= 5000:
            value_score = 10
        else:
            value_score = 5
        total_score += value_score
        factors.append({"factor": "order_value", "score": value_score, "detail": f"INR {total_amount:,.0f}"})

        # 2. SLA urgency (0-25 points)
        age_hours = 0
        if order.created_at:
            age_hours = (datetime.now(timezone.utc) - order.created_at.replace(tzinfo=timezone.utc if order.created_at.tzinfo is None else order.created_at.tzinfo)).total_seconds() / 3600

        if age_hours > 48:
            sla_score = 25
        elif age_hours > 24:
            sla_score = 20
        elif age_hours > 12:
            sla_score = 15
        elif age_hours > 6:
            sla_score = 10
        else:
            sla_score = 5
        total_score += sla_score
        factors.append({"factor": "sla_urgency", "score": sla_score, "detail": f"{age_hours:.1f}h old"})

        # 3. Customer tier (0-20 points)
        tier_scores = {"PLATINUM": 20, "GOLD": 16, "SILVER": 12, "BRONZE": 8, "NEW": 4}
        tier_score = tier_scores.get(customer_tier, 4)
        total_score += tier_score
        factors.append({"factor": "customer_tier", "score": tier_score, "detail": f"{customer_tier} ({order_count} orders)"})

        # 4. Channel priority (0-15 points)
        source = order.source or ""
        channel_scores = {
            OrderSource.WEBSITE.value: 12,
            OrderSource.MOBILE_APP.value: 12,
            OrderSource.AMAZON.value: 15,
            OrderSource.FLIPKART.value: 15,
            OrderSource.STORE.value: 10,
            OrderSource.DEALER.value: 8,
        }
        channel_score = channel_scores.get(source, 8)
        total_score += channel_score
        factors.append({"factor": "channel", "score": channel_score, "detail": source})

        # 5. Payment type (0-15 points)
        payment = order.payment_method or ""
        if payment in (PaymentMethod.COD.value, "COD"):
            payment_score = 5  # COD = lower priority (higher RTO risk)
        else:
            payment_score = 15  # Prepaid = higher priority
        total_score += payment_score
        factors.append({"factor": "payment_type", "score": payment_score, "detail": payment})

        return {
            "order_id": str(order.id),
            "order_number": order.order_number,
            "customer_id": str(order.customer_id) if order.customer_id else None,
            "customer_tier": customer_tier,
            "total_amount": total_amount,
            "status": order.status,
            "source": source,
            "payment_method": payment,
            "age_hours": round(age_hours, 1),
            "priority_score": total_score,
            "factors": factors,
            "created_at": order.created_at.isoformat() if order.created_at else None,
        }

    # ==================== Public Interface ====================

    async def analyze(self, limit: int = 50) -> Dict:
        """Prioritize pending orders."""
        self._status = "running"
        try:
            result = await self.db.execute(
                select(Order)
                .where(
                    Order.status.in_([
                        OrderStatus.NEW.value,
                        OrderStatus.CONFIRMED.value,
                        OrderStatus.ALLOCATED.value,
                    ])
                )
                .order_by(Order.created_at)
                .limit(limit)
            )
            orders = result.scalars().all()

            queue = []
            for order in orders:
                tier, count = await self._get_customer_tier(order.customer_id)
                scored = self._score_order(order, tier, count)
                queue.append(scored)

            # Sort by priority score descending
            queue.sort(key=lambda x: x["priority_score"], reverse=True)

            # Assign ranks
            for i, item in enumerate(queue):
                item["rank"] = i + 1

            self._results = {
                "agent": "order_prioritization",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "summary": {
                    "total_pending_orders": len(queue),
                    "avg_priority_score": round(sum(q["priority_score"] for q in queue) / max(len(queue), 1), 1),
                    "avg_age_hours": round(sum(q["age_hours"] for q in queue) / max(len(queue), 1), 1),
                    "sla_breach_risk": len([q for q in queue if q["age_hours"] > 24]),
                    "by_channel": dict(defaultdict(int, {q["source"]: 0 for q in queue})),
                },
                "queue": queue,
            }

            # Count by channel
            channel_counts = defaultdict(int)
            for q in queue:
                channel_counts[q["source"]] += 1
            self._results["summary"]["by_channel"] = dict(channel_counts)

            self._status = "completed"
            self._last_run = datetime.now(timezone.utc)
            return self._results

        except Exception as e:
            self._status = "error"
            return {"agent": "order_prioritization", "error": str(e), "status": "error"}

    async def get_queue(self) -> List[Dict]:
        """Get the current prioritized queue."""
        if not self._results:
            result = await self.analyze()
            return result.get("queue", [])
        return self._results.get("queue", [])

    async def get_recommendations(self) -> List[Dict]:
        if not self._results:
            return []
        recs = []
        breach_risk = [q for q in self._results.get("queue", []) if q["age_hours"] > 24]
        if breach_risk:
            recs.append({
                "type": "sla_breach_risk",
                "severity": "HIGH",
                "recommendation": f"{len(breach_risk)} orders at SLA breach risk (>24h old). "
                                f"Oldest: {max(q['age_hours'] for q in breach_risk):.0f}h. Process immediately.",
            })
        return recs

    async def get_status(self) -> Dict:
        return {
            "id": "order_prioritization",
            "name": "Order Prioritization Agent",
            "description": "Scores pending orders by value, SLA urgency, customer tier, channel, and payment type",
            "status": self._status,
            "last_run": self._last_run.isoformat() if self._last_run else None,
            "data_sources": "Order, Customer order history",
            "capabilities": [
                "Multi-factor priority scoring",
                "SLA breach detection",
                "Customer tier analysis",
                "Channel-aware prioritization",
                "Fulfillment queue ranking",
            ],
        }


# Need Tuple import
from typing import Tuple
