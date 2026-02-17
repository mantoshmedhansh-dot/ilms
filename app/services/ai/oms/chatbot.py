"""
OMS AI Chatbot Service

Natural language interface for order management queries:
- Order status
- Fraud check
- Delivery promise
- Routing status
- Return risk
- Queue status
- SLA report

Follows the same pattern as ERPChatbotService.
"""

from datetime import date, datetime, timedelta, timezone
from typing import List, Dict, Optional, Tuple
from uuid import UUID
import re
from collections import defaultdict

from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order, OrderItem, OrderStatus, PaymentMethod
from app.models.return_order import ReturnOrder
from app.models.shipment import Shipment


OMS_INTENT_PATTERNS = {
    "order_status": [
        r"(order|orders).*(status|state|where|track)",
        r"(how many|count|number).*(orders|pending|shipped|delivered)",
        r"(pending|open|processing|shipped|delivered).*(orders)",
    ],
    "fraud_check": [
        r"(fraud|suspicious|risk|risky).*(order|check|detect|score)",
        r"(high risk|flag|hold).*(order)",
        r"(check|detect|find).*(fraud|suspicious)",
    ],
    "delivery_promise": [
        r"(deliver|delivery).*(promise|date|when|estimate|time)",
        r"(when|how long|eta).*(deliver|ship|arrive)",
        r"(atp|available to promise)",
    ],
    "routing_status": [
        r"(route|routing|allocat|assign).*(order|warehouse|status)",
        r"(which warehouse|where).*(fulfill|ship|allocat)",
        r"(split|multi).*(order|shipment|warehouse)",
    ],
    "return_risk": [
        r"(return|rto|reverse).*(risk|predict|probability|rate)",
        r"(which|what).*(orders|items).*(return|rto)",
        r"(return rate|rto rate)",
    ],
    "queue_status": [
        r"(queue|priorit|backlog).*(order|status|pending)",
        r"(what|show).*(priority|queue|fulfillment)",
        r"(order|fulfillment).*(queue|priority|ranking)",
    ],
    "sla_report": [
        r"(sla|service level|on.?time).*(report|status|breach|compliance)",
        r"(breach|late|delay|overdue).*(order|delivery|sla)",
        r"(delivery|shipping).*(performance|metric)",
    ],
    "help": [
        r"(help|what can|how to|capabilities)",
    ],
}

OMS_TIME_PATTERNS = {
    "today": lambda: (date.today(), date.today()),
    "yesterday": lambda: (date.today() - timedelta(days=1), date.today() - timedelta(days=1)),
    "this week": lambda: (date.today() - timedelta(days=date.today().weekday()), date.today()),
    "this month": lambda: (date.today().replace(day=1), date.today()),
    "last 7 days": lambda: (date.today() - timedelta(days=7), date.today()),
    "last 30 days": lambda: (date.today() - timedelta(days=30), date.today()),
}


class OMSChatbotService:
    """
    Natural language interface for OMS queries.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    def _classify_intent(self, query: str) -> Tuple[str, float]:
        query_lower = query.lower()
        best_intent = "unknown"
        best_score = 0
        for intent, patterns in OMS_INTENT_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    score = len(re.findall(pattern, query_lower))
                    if score > best_score:
                        best_score = score
                        best_intent = intent
        confidence = min(0.95, 0.5 + best_score * 0.15) if best_score > 0 else 0.2
        return best_intent, confidence

    def _extract_time_period(self, query: str) -> Tuple[date, date]:
        query_lower = query.lower()
        for period_name, date_func in OMS_TIME_PATTERNS.items():
            if period_name in query_lower:
                return date_func()
        return date.today() - timedelta(days=7), date.today()

    async def _handle_order_status(self, query: str, start: date, end: date) -> Dict:
        """Handle order status queries."""
        result = await self.db.execute(
            select(
                Order.status,
                func.count(Order.id).label("count"),
            )
            .group_by(Order.status)
        )
        rows = result.all()
        status_counts = {row.status: int(row.count) for row in rows}
        total = sum(status_counts.values())

        # Recent orders
        start_dt = datetime.combine(start, datetime.min.time()).replace(tzinfo=timezone.utc)
        end_dt = datetime.combine(end, datetime.max.time()).replace(tzinfo=timezone.utc)

        recent_result = await self.db.execute(
            select(func.count(Order.id))
            .where(and_(Order.created_at >= start_dt, Order.created_at <= end_dt))
        )
        recent_count = recent_result.scalar() or 0

        pending = status_counts.get(OrderStatus.NEW.value, 0) + status_counts.get(OrderStatus.CONFIRMED.value, 0)

        return {
            "response": f"Order overview: {total} total orders. {recent_count} created in the selected period. "
                       f"Currently pending: {pending}. "
                       f"Shipped: {status_counts.get(OrderStatus.SHIPPED.value, 0)}. "
                       f"Delivered: {status_counts.get(OrderStatus.DELIVERED.value, 0)}.",
            "data": {
                "total_orders": total,
                "recent_orders": recent_count,
                "by_status": status_counts,
            },
            "suggestions": [
                "Show order queue priorities",
                "Any fraud risks?",
                "Show SLA report",
            ],
        }

    async def _handle_fraud_check(self, query: str, start: date, end: date) -> Dict:
        """Handle fraud check queries."""
        from app.services.ai.oms.fraud_detection import OMSFraudDetectionAgent
        agent = OMSFraudDetectionAgent(self.db)
        result = await agent.analyze(days=7, limit=20)

        summary = result.get("summary", {})
        high_risk = [o for o in result.get("scored_orders", []) if o["risk_level"] in ("CRITICAL", "HIGH")]

        top_risk_msg = ""
        if high_risk:
            top = high_risk[0]
            top_risk_msg = f" Top risk: Order {top['order_id'][:8]} (score: {top['risk_score']})"

        return {
            "response": f"Fraud analysis: {summary.get('total_orders_scored', 0)} orders scored. "
                       f"High/Critical risk: {summary.get('high_risk_orders', 0)}. "
                       f"Average risk score: {summary.get('avg_risk_score', 0)}/100.{top_risk_msg}",
            "data": {
                "total_scored": summary.get("total_orders_scored", 0),
                "by_risk_level": summary.get("by_risk_level", {}),
                "avg_score": summary.get("avg_risk_score", 0),
                "high_risk_orders": [
                    {"order": o["order_id"][:8], "score": o["risk_score"], "level": o["risk_level"]}
                    for o in high_risk[:5]
                ],
            },
            "suggestions": [
                "Show order status",
                "Show return risk predictions",
                "Show order queue",
            ],
        }

    async def _handle_delivery_promise(self, query: str, start: date, end: date) -> Dict:
        from app.services.ai.oms.delivery_promise import OMSDeliveryPromiseAgent
        agent = OMSDeliveryPromiseAgent(self.db)
        result = await agent.analyze()
        processing = result.get("processing_time", {})

        return {
            "response": f"Delivery promise analysis: Average processing time is {processing.get('avg_processing_days', 'N/A')} days "
                       f"(min: {processing.get('min_processing_days', 'N/A')}, max: {processing.get('max_processing_days', 'N/A')}). "
                       f"Provide a product_id and pincode for specific delivery estimates.",
            "data": {"processing_time": processing},
            "suggestions": [
                "Show order status",
                "Show routing analysis",
                "Check delivery for a specific order",
            ],
        }

    async def _handle_routing_status(self, query: str, start: date, end: date) -> Dict:
        from app.services.ai.oms.smart_routing import OMSSmartRoutingAgent
        agent = OMSSmartRoutingAgent(self.db)
        result = await agent.analyze(days=7, limit=10)
        summary = result.get("summary", {})

        return {
            "response": f"Routing analysis: {summary.get('total_orders_analyzed', 0)} orders analyzed. "
                       f"Split orders needed: {summary.get('orders_needing_split', 0)}. "
                       f"Unserviceable: {summary.get('unserviceable_orders', 0)}.",
            "data": summary,
            "suggestions": [
                "Show order queue",
                "Any fraud risks?",
                "Show delivery promise",
            ],
        }

    async def _handle_return_risk(self, query: str, start: date, end: date) -> Dict:
        from app.services.ai.oms.returns_prediction import OMSReturnsPredictionAgent
        agent = OMSReturnsPredictionAgent(self.db)
        result = await agent.analyze(days=7, limit=20)
        summary = result.get("summary", {})

        return {
            "response": f"Return risk analysis: {summary.get('total_orders_scored', 0)} orders analyzed. "
                       f"High risk: {summary.get('high_risk_orders', 0)}. "
                       f"Estimated return rate: {summary.get('estimated_return_rate', 'N/A')}.",
            "data": {
                "total_scored": summary.get("total_orders_scored", 0),
                "by_risk_level": summary.get("by_risk_level", {}),
                "avg_probability": summary.get("avg_return_probability", 0),
            },
            "suggestions": [
                "Show fraud analysis",
                "Show order status",
                "Show order queue priorities",
            ],
        }

    async def _handle_queue_status(self, query: str, start: date, end: date) -> Dict:
        from app.services.ai.oms.order_prioritization import OMSOrderPrioritizationAgent
        agent = OMSOrderPrioritizationAgent(self.db)
        result = await agent.analyze(limit=20)
        summary = result.get("summary", {})
        queue = result.get("queue", [])[:5]

        return {
            "response": f"Fulfillment queue: {summary.get('total_pending_orders', 0)} orders pending. "
                       f"SLA breach risk: {summary.get('sla_breach_risk', 0)} orders. "
                       f"Average age: {summary.get('avg_age_hours', 0):.1f}h.",
            "data": {
                "total_pending": summary.get("total_pending_orders", 0),
                "sla_breach_risk": summary.get("sla_breach_risk", 0),
                "avg_age_hours": summary.get("avg_age_hours", 0),
                "top_priority_orders": [
                    {"order": q["order_number"], "score": q["priority_score"], "age": f"{q['age_hours']:.0f}h"}
                    for q in queue
                ],
            },
            "suggestions": [
                "Show order status",
                "Show fraud risks",
                "Show SLA report",
            ],
        }

    async def _handle_sla_report(self, query: str, start: date, end: date) -> Dict:
        start_dt = datetime.combine(start, datetime.min.time()).replace(tzinfo=timezone.utc)
        end_dt = datetime.combine(end, datetime.max.time()).replace(tzinfo=timezone.utc)

        # Delivered orders in period
        delivered = await self.db.execute(
            select(func.count(Order.id))
            .where(
                and_(
                    Order.delivered_at >= start_dt,
                    Order.delivered_at <= end_dt,
                    Order.status == OrderStatus.DELIVERED.value,
                )
            )
        )
        delivered_count = delivered.scalar() or 0

        # Average delivery time
        avg_time = await self.db.execute(
            select(
                func.avg(
                    func.extract('epoch', Order.delivered_at) -
                    func.extract('epoch', Order.created_at)
                ).label("avg_secs")
            )
            .where(
                and_(
                    Order.delivered_at.isnot(None),
                    Order.delivered_at >= start_dt,
                )
            )
        )
        avg_secs = float(avg_time.scalar() or 0)
        avg_days = avg_secs / 86400 if avg_secs > 0 else 0

        # Overdue orders
        overdue = await self.db.execute(
            select(func.count(Order.id))
            .where(
                and_(
                    Order.status.in_([OrderStatus.CONFIRMED.value, OrderStatus.ALLOCATED.value]),
                    Order.created_at <= datetime.now(timezone.utc) - timedelta(hours=48),
                )
            )
        )
        overdue_count = overdue.scalar() or 0

        return {
            "response": f"SLA Report ({start} to {end}): {delivered_count} orders delivered. "
                       f"Average delivery time: {avg_days:.1f} days. "
                       f"Overdue (>48h processing): {overdue_count} orders.",
            "data": {
                "delivered_orders": delivered_count,
                "avg_delivery_days": round(avg_days, 1),
                "overdue_orders": overdue_count,
                "period": f"{start} to {end}",
            },
            "suggestions": [
                "Show order queue",
                "Show order status",
                "Any fraud risks?",
            ],
        }

    async def _handle_help(self, query: str, start: date, end: date) -> Dict:
        return {
            "response": "I'm your OMS AI Assistant. I can help with:\n\n"
                       "- **Order Status**: \"How many orders are pending?\"\n"
                       "- **Fraud Detection**: \"Any suspicious orders?\"\n"
                       "- **Delivery Promise**: \"When will the order arrive?\"\n"
                       "- **Routing**: \"Which warehouse should fulfill this?\"\n"
                       "- **Return Risk**: \"Which orders might be returned?\"\n"
                       "- **Order Queue**: \"Show me fulfillment priorities\"\n"
                       "- **SLA Report**: \"What's our delivery performance?\"",
            "data": None,
            "suggestions": [
                "Show order status",
                "Any fraud risks?",
                "Show fulfillment queue",
                "Show SLA report",
            ],
        }

    async def _handle_unknown(self, query: str, start: date, end: date) -> Dict:
        return {
            "response": "I'm not sure how to answer that. I specialize in order management queries "
                       "like order status, fraud detection, delivery promises, routing, return risks, and SLA reporting.",
            "data": None,
            "suggestions": ["Show order status", "Help", "Any fraud risks?"],
        }

    async def query(self, user_query: str) -> Dict:
        """Process a natural language OMS query."""
        intent, confidence = self._classify_intent(user_query)
        start_date, end_date = self._extract_time_period(user_query)

        handlers = {
            "order_status": self._handle_order_status,
            "fraud_check": self._handle_fraud_check,
            "delivery_promise": self._handle_delivery_promise,
            "routing_status": self._handle_routing_status,
            "return_risk": self._handle_return_risk,
            "queue_status": self._handle_queue_status,
            "sla_report": self._handle_sla_report,
            "help": self._handle_help,
            "unknown": self._handle_unknown,
        }

        handler = handlers.get(intent, self._handle_unknown)

        try:
            result = await handler(user_query, start_date, end_date)
            result["intent"] = intent
            result["confidence"] = confidence
            result["time_period"] = {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
            }
            return result
        except Exception as e:
            return {
                "response": f"I encountered an error: {str(e)}",
                "intent": intent,
                "confidence": confidence,
                "data": None,
                "suggestions": ["Help", "Show order status"],
            }
