"""
DMS AI Chatbot Service

Natural language interface for distribution management queries:
- Dealer info (status, tier, region counts)
- Order status (DMS orders summary)
- Collection status (aging, overdue)
- Scheme info (active schemes, ROI, budget)
- Claim status (counts by type/status)
- Demand forecast (delegate to demand sensing agent)
- Performance ranking (top/bottom dealers by achievement)

Follows the same pattern as OMSChatbotService.
"""

from datetime import date, datetime, timedelta, timezone
from typing import List, Dict, Optional, Tuple
from uuid import UUID
import re
from collections import defaultdict

from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dealer import (
    Dealer, DealerTarget, DealerCreditLedger, DealerClaim,
    DealerScheme, DealerSchemeApplication, RetailerOutlet,
)
from app.models.order import Order


DMS_INTENT_PATTERNS = {
    "dealer_info": [
        r"(dealer|distributor|distributors|dealers).*(status|count|how many|info|list)",
        r"(how many|count|number).*(dealer|distributor)",
        r"(which|show).*(dealer|distributor)",
        r"(active|inactive|suspended).*(dealer|distributor)",
    ],
    "order_status": [
        r"(dms|dealer).*(order|orders)",
        r"(order|orders).*(count|status|trend|summary)",
        r"(how many|count|number).*(order|pending|shipped)",
    ],
    "collection_status": [
        r"(outstanding|overdue|aging|collection|collections)",
        r"(payment|payments).*(pending|overdue|due)",
        r"(credit|receivable|receivables)",
        r"(how much|total).*(outstanding|overdue|due)",
    ],
    "scheme_info": [
        r"(scheme|schemes).*(active|roi|budget|performance|status)",
        r"(active|running).*(scheme|promotion)",
        r"(scheme|discount).*(roi|return|effective)",
    ],
    "claim_status": [
        r"(claim|claims).*(pending|status|count|type|submitted)",
        r"(pending|open).*(claim|claims)",
        r"(how many|count).*(claim|claims)",
    ],
    "demand_forecast": [
        r"(demand|forecast|predict|projection|next month)",
        r"(sales|revenue).*(forecast|predict|trend|next)",
        r"(what|show).*(demand|forecast)",
    ],
    "performance_ranking": [
        r"(ranking|rank|top|best|worst|bottom).*(dealer|distributor|performer)",
        r"(dealer|distributor).*(ranking|performance|score|achievement)",
        r"(best|top|worst|bottom).*(performer|performing)",
    ],
    "help": [
        r"(help|what can|how to|capabilities)",
    ],
}

DMS_TIME_PATTERNS = {
    "today": lambda: (date.today(), date.today()),
    "yesterday": lambda: (date.today() - timedelta(days=1), date.today() - timedelta(days=1)),
    "this week": lambda: (date.today() - timedelta(days=date.today().weekday()), date.today()),
    "this month": lambda: (date.today().replace(day=1), date.today()),
    "last 7 days": lambda: (date.today() - timedelta(days=7), date.today()),
    "last 30 days": lambda: (date.today() - timedelta(days=30), date.today()),
}


class DMSChatbotService:
    """Natural language interface for DMS queries."""

    def __init__(self, db: AsyncSession):
        self.db = db

    def _classify_intent(self, query: str) -> Tuple[str, float]:
        query_lower = query.lower()
        best_intent = "unknown"
        best_score = 0
        for intent, patterns in DMS_INTENT_PATTERNS.items():
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
        for period_name, date_func in DMS_TIME_PATTERNS.items():
            if period_name in query_lower:
                return date_func()
        return date.today() - timedelta(days=7), date.today()

    async def _handle_dealer_info(self, query: str, start: date, end: date) -> Dict:
        """Handle dealer info queries."""
        # Count by status
        status_result = await self.db.execute(
            select(Dealer.status, func.count(Dealer.id).label("count"))
            .group_by(Dealer.status)
        )
        status_counts = {row.status: int(row.count) for row in status_result.all()}
        total = sum(status_counts.values())

        # Count by tier
        tier_result = await self.db.execute(
            select(Dealer.tier, func.count(Dealer.id).label("count"))
            .where(Dealer.status == "ACTIVE")
            .group_by(Dealer.tier)
        )
        tier_counts = {row.tier: int(row.count) for row in tier_result.all()}

        # Count by region
        region_result = await self.db.execute(
            select(Dealer.region, func.count(Dealer.id).label("count"))
            .where(Dealer.status == "ACTIVE")
            .group_by(Dealer.region)
        )
        region_counts = {row.region: int(row.count) for row in region_result.all()}

        active = status_counts.get("ACTIVE", 0)

        return {
            "response": (
                f"Dealer overview: {total} total dealers, {active} active. "
                f"By tier: {', '.join(f'{t}: {c}' for t, c in tier_counts.items())}. "
                f"By region: {', '.join(f'{r}: {c}' for r, c in region_counts.items())}."
            ),
            "data": {
                "total_dealers": total,
                "by_status": status_counts,
                "by_tier": tier_counts,
                "by_region": region_counts,
            },
            "suggestions": [
                "Show dealer performance rankings",
                "What is total outstanding?",
                "Show active schemes",
            ],
        }

    async def _handle_order_status(self, query: str, start: date, end: date) -> Dict:
        """Handle DMS order status queries."""
        # Orders with dealer_id (DMS orders)
        result = await self.db.execute(
            select(
                Order.status,
                func.count(Order.id).label("count"),
                func.sum(Order.total_amount).label("total_value"),
            ).where(Order.dealer_id.isnot(None))
            .group_by(Order.status)
        )
        rows = result.all()
        status_counts = {row.status: int(row.count) for row in rows}
        status_values = {row.status: float(row.total_value or 0) for row in rows}
        total = sum(status_counts.values())
        total_value = sum(status_values.values())

        # Recent period
        start_dt = datetime.combine(start, datetime.min.time()).replace(tzinfo=timezone.utc)
        end_dt = datetime.combine(end, datetime.max.time()).replace(tzinfo=timezone.utc)
        recent_result = await self.db.execute(
            select(func.count(Order.id))
            .where(and_(
                Order.dealer_id.isnot(None),
                Order.created_at >= start_dt,
                Order.created_at <= end_dt,
            ))
        )
        recent = recent_result.scalar() or 0

        return {
            "response": (
                f"DMS Orders: {total} total orders worth {total_value:,.0f}. "
                f"{recent} orders in the selected period. "
                f"By status: {', '.join(f'{s}: {c}' for s, c in status_counts.items())}."
            ),
            "data": {
                "total_orders": total,
                "total_value": total_value,
                "recent_orders": recent,
                "by_status": status_counts,
            },
            "suggestions": [
                "Show dealer rankings",
                "What is total outstanding?",
                "Show demand forecast",
            ],
        }

    async def _handle_collection_status(self, query: str, start: date, end: date) -> Dict:
        """Handle collection/outstanding queries."""
        # Total outstanding and overdue
        result = await self.db.execute(
            select(
                func.sum(Dealer.outstanding_amount).label("total_outstanding"),
                func.sum(Dealer.overdue_amount).label("total_overdue"),
                func.count(Dealer.id).label("dealer_count"),
            ).where(
                and_(Dealer.status == "ACTIVE", Dealer.outstanding_amount > 0)
            )
        )
        row = result.one()
        total_outstanding = float(row.total_outstanding or 0)
        total_overdue = float(row.total_overdue or 0)
        overdue_dealers = int(row.dealer_count or 0)

        # Aging buckets from collection optimizer
        from app.services.ai.dms.collection_optimizer import DMSCollectionOptimizerAgent
        agent = DMSCollectionOptimizerAgent(self.db)
        aging = await agent._analyze_aging_buckets()

        return {
            "response": (
                f"Collection Status: Total outstanding {total_outstanding:,.0f}, "
                f"overdue {total_overdue:,.0f} across {overdue_dealers} dealers. "
                f"Aging: 0-30d: {aging['buckets'].get('0-30', 0):,.0f}, "
                f"31-60d: {aging['buckets'].get('31-60', 0):,.0f}, "
                f"61-90d: {aging['buckets'].get('61-90', 0):,.0f}, "
                f"90+d: {aging['buckets'].get('90+', 0):,.0f}."
            ),
            "data": {
                "total_outstanding": total_outstanding,
                "total_overdue": total_overdue,
                "overdue_dealers": overdue_dealers,
                "aging_buckets": aging["buckets"],
            },
            "suggestions": [
                "Show dealer rankings",
                "Which dealers are overdue?",
                "Show active schemes",
            ],
        }

    async def _handle_scheme_info(self, query: str, start: date, end: date) -> Dict:
        """Handle scheme queries."""
        today = date.today()

        # Active schemes
        result = await self.db.execute(
            select(
                DealerScheme.scheme_code,
                DealerScheme.scheme_name,
                DealerScheme.scheme_type,
                DealerScheme.total_budget,
                DealerScheme.utilized_budget,
                DealerScheme.end_date,
            ).where(
                and_(
                    DealerScheme.is_active == True,
                    DealerScheme.start_date <= today,
                    DealerScheme.end_date >= today,
                )
            )
        )
        schemes = result.all()

        scheme_list = []
        total_budget = 0
        total_utilized = 0
        for s in schemes:
            budget = float(s.total_budget or 0)
            utilized = float(s.utilized_budget or 0)
            total_budget += budget
            total_utilized += utilized
            scheme_list.append({
                "code": s.scheme_code,
                "name": s.scheme_name,
                "type": s.scheme_type,
                "budget": budget,
                "utilized": utilized,
                "utilization_pct": round(utilized / budget * 100, 1) if budget > 0 else 0,
                "ends": s.end_date.isoformat(),
            })

        return {
            "response": (
                f"Active Schemes: {len(schemes)} schemes running. "
                f"Total budget: {total_budget:,.0f}, utilized: {total_utilized:,.0f} "
                f"({round(total_utilized / total_budget * 100, 1) if total_budget > 0 else 0}%)."
            ),
            "data": {
                "active_schemes": len(schemes),
                "total_budget": total_budget,
                "total_utilized": total_utilized,
                "schemes": scheme_list,
            },
            "suggestions": [
                "Show scheme ROI analysis",
                "Show dealer rankings",
                "What is total outstanding?",
            ],
        }

    async def _handle_claim_status(self, query: str, start: date, end: date) -> Dict:
        """Handle claim queries."""
        # Claims by status
        status_result = await self.db.execute(
            select(
                DealerClaim.status,
                func.count(DealerClaim.id).label("count"),
                func.sum(DealerClaim.amount_claimed).label("total_claimed"),
            ).group_by(DealerClaim.status)
        )
        status_counts = {}
        total_claimed = 0
        for row in status_result.all():
            status_counts[row.status] = int(row.count)
            total_claimed += float(row.total_claimed or 0)

        # Claims by type
        type_result = await self.db.execute(
            select(
                DealerClaim.claim_type,
                func.count(DealerClaim.id).label("count"),
            ).group_by(DealerClaim.claim_type)
        )
        type_counts = {row.claim_type: int(row.count) for row in type_result.all()}

        total = sum(status_counts.values())
        pending = status_counts.get("SUBMITTED", 0) + status_counts.get("UNDER_REVIEW", 0)

        return {
            "response": (
                f"Claims: {total} total claims worth {total_claimed:,.0f}. "
                f"Pending: {pending}. "
                f"By type: {', '.join(f'{t}: {c}' for t, c in type_counts.items())}."
            ),
            "data": {
                "total_claims": total,
                "total_claimed": total_claimed,
                "pending": pending,
                "by_status": status_counts,
                "by_type": type_counts,
            },
            "suggestions": [
                "Show dealer rankings",
                "What is total outstanding?",
                "Show active schemes",
            ],
        }

    async def _handle_demand_forecast(self, query: str, start: date, end: date) -> Dict:
        """Handle demand forecast queries by delegating to the demand sensing agent."""
        from app.services.ai.dms.demand_sensing import DMSDemandSensingAgent
        agent = DMSDemandSensingAgent(self.db)
        result = await agent.analyze()

        forecasts = result.get("forecasts", [])[:10]
        summary = result.get("summary", {})

        forecast_lines = []
        for f in forecasts[:5]:
            forecast_lines.append(
                f"{f['dealer_code']}: forecast {f['forecast_revenue']:,.0f} "
                f"(trend: {f['trend']}, confidence: {f['confidence']:.0%})"
            )

        return {
            "response": (
                f"Demand Forecast: Analyzed {summary.get('dealers_analyzed', 0)} dealers. "
                f"Inactive retailers: {summary.get('inactive_retailers', 0)}. "
                f"Top forecasts:\n" + "\n".join(forecast_lines)
            ),
            "data": {
                "dealers_analyzed": summary.get("dealers_analyzed", 0),
                "inactive_retailers": summary.get("inactive_retailers", 0),
                "forecasts": forecasts,
            },
            "suggestions": [
                "Show dealer rankings",
                "Which dealers are declining?",
                "Show dealer info",
            ],
        }

    async def _handle_performance_ranking(self, query: str, start: date, end: date) -> Dict:
        """Handle performance ranking queries."""
        # Get current month targets with achievements
        now = datetime.now(timezone.utc)
        result = await self.db.execute(
            select(
                Dealer.dealer_code,
                Dealer.name,
                Dealer.tier,
                Dealer.region,
                DealerTarget.revenue_target,
                DealerTarget.revenue_achieved,
            ).join(DealerTarget, DealerTarget.dealer_id == Dealer.id)
            .where(
                and_(
                    Dealer.status == "ACTIVE",
                    DealerTarget.target_year == now.year,
                    DealerTarget.target_month == now.month,
                    DealerTarget.target_period == "MONTHLY",
                )
            ).order_by(desc(DealerTarget.revenue_achieved))
        )
        rows = result.all()

        rankings = []
        for r in rows:
            target = float(r.revenue_target or 0)
            achieved = float(r.revenue_achieved or 0)
            pct = (achieved / target * 100) if target > 0 else 0
            rankings.append({
                "dealer_code": r.dealer_code,
                "name": r.name,
                "tier": r.tier,
                "region": r.region,
                "target": target,
                "achieved": achieved,
                "achievement_pct": round(pct, 1),
            })

        top5 = rankings[:5]
        bottom5 = sorted(rankings, key=lambda x: x["achievement_pct"])[:5]

        top_msg = ", ".join(f"{r['dealer_code']} ({r['achievement_pct']}%)" for r in top5)
        bottom_msg = ", ".join(f"{r['dealer_code']} ({r['achievement_pct']}%)" for r in bottom5)

        return {
            "response": (
                f"Dealer Performance Rankings ({now.strftime('%B %Y')}):\n"
                f"Top 5: {top_msg}\n"
                f"Bottom 5: {bottom_msg}\n"
                f"Total dealers with targets: {len(rankings)}."
            ),
            "data": {
                "total_ranked": len(rankings),
                "top_performers": top5,
                "bottom_performers": bottom5,
            },
            "suggestions": [
                "What is total outstanding?",
                "Show demand forecast",
                "Show active schemes",
            ],
        }

    async def _handle_help(self, query: str, start: date, end: date) -> Dict:
        return {
            "response": (
                "I'm your DMS AI Assistant. I can help with:\n\n"
                "- **Dealer Info**: \"How many active dealers?\"\n"
                "- **DMS Orders**: \"Show DMS order status\"\n"
                "- **Collections**: \"What is total outstanding?\"\n"
                "- **Schemes**: \"How are active schemes performing?\"\n"
                "- **Claims**: \"Any pending claims?\"\n"
                "- **Demand Forecast**: \"Show demand forecast\"\n"
                "- **Rankings**: \"Show dealer performance rankings\""
            ),
            "data": None,
            "suggestions": [
                "Show dealer performance rankings",
                "What is total outstanding?",
                "How are active schemes performing?",
                "Any pending claims?",
            ],
        }

    async def _handle_unknown(self, query: str, start: date, end: date) -> Dict:
        return {
            "response": (
                "I'm not sure how to answer that. I specialize in distribution management queries "
                "like dealer info, DMS orders, collections, schemes, claims, demand forecasts, "
                "and dealer performance rankings."
            ),
            "data": None,
            "suggestions": [
                "Show dealer performance rankings",
                "Help",
                "What is total outstanding?",
            ],
        }

    async def query(self, user_query: str) -> Dict:
        """Process a natural language DMS query."""
        intent, confidence = self._classify_intent(user_query)
        start_date, end_date = self._extract_time_period(user_query)

        handlers = {
            "dealer_info": self._handle_dealer_info,
            "order_status": self._handle_order_status,
            "collection_status": self._handle_collection_status,
            "scheme_info": self._handle_scheme_info,
            "claim_status": self._handle_claim_status,
            "demand_forecast": self._handle_demand_forecast,
            "performance_ranking": self._handle_performance_ranking,
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
                "suggestions": ["Help", "Show dealer info"],
            }

    async def get_quick_stats(self) -> Dict:
        """Get quick stats for the chat UI."""
        # Active dealers
        dealers_result = await self.db.execute(
            select(func.count(Dealer.id)).where(Dealer.status == "ACTIVE")
        )
        active_dealers = dealers_result.scalar() or 0

        # Active DMS orders
        orders_result = await self.db.execute(
            select(func.count(Order.id)).where(
                and_(
                    Order.dealer_id.isnot(None),
                    Order.status.notin_(["DELIVERED", "CANCELLED"]),
                )
            )
        )
        active_orders = orders_result.scalar() or 0

        # Total outstanding
        outstanding_result = await self.db.execute(
            select(func.sum(Dealer.outstanding_amount)).where(Dealer.status == "ACTIVE")
        )
        total_outstanding = float(outstanding_result.scalar() or 0)

        # Overdue dealer count
        overdue_result = await self.db.execute(
            select(func.count(Dealer.id)).where(
                and_(Dealer.status == "ACTIVE", Dealer.overdue_amount > 0)
            )
        )
        overdue_count = overdue_result.scalar() or 0

        return {
            "active_dealers": active_dealers,
            "active_dms_orders": active_orders,
            "total_outstanding": total_outstanding,
            "overdue_dealer_count": overdue_count,
        }
