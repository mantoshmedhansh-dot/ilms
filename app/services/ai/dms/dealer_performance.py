"""
DMS AI - Dealer Performance Agent

Scores dealers on:
- Sales achievement: revenue_achieved / revenue_target %
- Payment compliance: avg days_overdue, overdue vs credit_limit
- Growth trajectory: MoM revenue trend, flag 3+ declining months
- Claim rate: claims / total_orders, flag >10%

Severity: CRITICAL (<50%), HIGH (<70%), MEDIUM (<85%)
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import List, Dict, Optional
from uuid import UUID
from collections import defaultdict

from sqlalchemy import select, func, and_, desc, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dealer import (
    Dealer, DealerTarget, DealerCreditLedger, DealerClaim,
)
from app.models.order import Order


class DMSDealerPerformanceAgent:
    """Scores dealers on achievement, payment, growth, and claims."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self._status = "idle"
        self._last_run = None
        self._results = None

    async def analyze(self, **kwargs) -> Dict:
        """Run full dealer performance analysis."""
        self._status = "running"
        try:
            scores = await self._score_all_dealers()
            recommendations = self._generate_recommendations(scores)

            severity_summary = defaultdict(int)
            for rec in recommendations:
                severity_summary[rec["severity"]] += 1

            self._results = {
                "agent": "dealer-performance",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "summary": {
                    "total_dealers_scored": len(scores),
                    "by_severity": dict(severity_summary),
                    "avg_achievement": round(
                        sum(s.get("achievement_pct", 0) for s in scores) / max(len(scores), 1), 1
                    ),
                    "critical_dealers": len([s for s in scores if s.get("severity") == "CRITICAL"]),
                    "high_risk_dealers": len([s for s in scores if s.get("severity") == "HIGH"]),
                },
                "dealer_scores": scores[:50],
                "recommendations": recommendations[:30],
            }
            self._status = "completed"
            self._last_run = datetime.now(timezone.utc)
            return self._results

        except Exception as e:
            self._status = "error"
            return {"agent": "dealer-performance", "error": str(e), "status": "error"}

    async def _score_all_dealers(self) -> List[Dict]:
        """Score all active dealers."""
        # Get active dealers
        dealers_result = await self.db.execute(
            select(
                Dealer.id, Dealer.dealer_code, Dealer.name, Dealer.tier,
                Dealer.region, Dealer.total_orders, Dealer.total_revenue,
                Dealer.outstanding_amount, Dealer.overdue_amount,
                Dealer.credit_limit, Dealer.payment_rating,
                Dealer.last_order_date,
            ).where(Dealer.status == "ACTIVE")
        )
        dealers = dealers_result.all()

        if not dealers:
            return []

        dealer_ids = [d.id for d in dealers]

        # Get current month targets
        now = datetime.now(timezone.utc)
        targets_result = await self.db.execute(
            select(
                DealerTarget.dealer_id,
                DealerTarget.revenue_target,
                DealerTarget.revenue_achieved,
                DealerTarget.quantity_target,
                DealerTarget.quantity_achieved,
            ).where(
                and_(
                    DealerTarget.dealer_id.in_(dealer_ids),
                    DealerTarget.target_year == now.year,
                    DealerTarget.target_month == now.month,
                    DealerTarget.target_period == "MONTHLY",
                )
            )
        )
        targets_map = {}
        for t in targets_result.all():
            targets_map[t.dealer_id] = {
                "revenue_target": float(t.revenue_target or 0),
                "revenue_achieved": float(t.revenue_achieved or 0),
                "quantity_target": int(t.quantity_target or 0),
                "quantity_achieved": int(t.quantity_achieved or 0),
            }

        # Get overdue ledger entries
        overdue_result = await self.db.execute(
            select(
                DealerCreditLedger.dealer_id,
                func.avg(DealerCreditLedger.days_overdue).label("avg_days_overdue"),
                func.count(DealerCreditLedger.id).label("overdue_count"),
            ).where(
                and_(
                    DealerCreditLedger.dealer_id.in_(dealer_ids),
                    DealerCreditLedger.is_settled == False,
                    DealerCreditLedger.transaction_type == "INVOICE",
                )
            ).group_by(DealerCreditLedger.dealer_id)
        )
        overdue_map = {}
        for row in overdue_result.all():
            overdue_map[row.dealer_id] = {
                "avg_days_overdue": float(row.avg_days_overdue or 0),
                "overdue_count": int(row.overdue_count or 0),
            }

        # Get claim counts (last 90 days)
        cutoff_90 = now - timedelta(days=90)
        claims_result = await self.db.execute(
            select(
                DealerClaim.dealer_id,
                func.count(DealerClaim.id).label("claim_count"),
            ).where(
                and_(
                    DealerClaim.dealer_id.in_(dealer_ids),
                    DealerClaim.created_at >= cutoff_90,
                )
            ).group_by(DealerClaim.dealer_id)
        )
        claims_map = {row.dealer_id: int(row.claim_count) for row in claims_result.all()}

        # Get MoM revenue (last 6 months)
        cutoff_6m = now - timedelta(days=180)
        mom_result = await self.db.execute(
            select(
                Order.dealer_id,
                func.date_trunc("month", Order.created_at).label("month"),
                func.sum(Order.total_amount).label("revenue"),
            ).where(
                and_(
                    Order.dealer_id.in_(dealer_ids),
                    Order.created_at >= cutoff_6m,
                    Order.dealer_id.isnot(None),
                )
            ).group_by(Order.dealer_id, "month")
            .order_by(Order.dealer_id, "month")
        )
        mom_map = defaultdict(list)
        for row in mom_result.all():
            mom_map[row.dealer_id].append(float(row.revenue or 0))

        # Score each dealer
        scores = []
        for d in dealers:
            target = targets_map.get(d.id, {})
            overdue = overdue_map.get(d.id, {})
            claim_count = claims_map.get(d.id, 0)
            monthly_revenues = mom_map.get(d.id, [])

            # Achievement %
            rev_target = target.get("revenue_target", 0)
            rev_achieved = target.get("revenue_achieved", 0)
            achievement_pct = (rev_achieved / rev_target * 100) if rev_target > 0 else 0

            # Payment compliance score (0-100)
            avg_overdue = overdue.get("avg_days_overdue", 0)
            payment_score = max(0, 100 - avg_overdue * 2)

            # Growth trajectory
            declining_months = 0
            if len(monthly_revenues) >= 2:
                for i in range(1, len(monthly_revenues)):
                    if monthly_revenues[i] < monthly_revenues[i - 1]:
                        declining_months += 1

            # Claim rate
            total_orders = max(d.total_orders or 1, 1)
            claim_rate = (claim_count / total_orders) * 100

            # Composite score
            composite = (
                achievement_pct * 0.4
                + payment_score * 0.3
                + (100 - min(declining_months * 20, 100)) * 0.15
                + (100 - min(claim_rate * 10, 100)) * 0.15
            )

            # Severity
            if achievement_pct < 50:
                severity = "CRITICAL"
            elif achievement_pct < 70:
                severity = "HIGH"
            elif achievement_pct < 85:
                severity = "MEDIUM"
            else:
                severity = "LOW"

            scores.append({
                "dealer_id": str(d.id),
                "dealer_code": d.dealer_code,
                "name": d.name,
                "tier": d.tier,
                "region": d.region,
                "achievement_pct": round(achievement_pct, 1),
                "payment_score": round(payment_score, 1),
                "avg_days_overdue": round(avg_overdue, 1),
                "declining_months": declining_months,
                "claim_rate": round(claim_rate, 1),
                "claim_count": claim_count,
                "composite_score": round(composite, 1),
                "severity": severity,
                "outstanding": float(d.outstanding_amount or 0),
                "overdue": float(d.overdue_amount or 0),
                "credit_limit": float(d.credit_limit or 0),
            })

        scores.sort(key=lambda x: x["composite_score"])
        return scores

    def _generate_recommendations(self, scores: List[Dict]) -> List[Dict]:
        """Generate recommendations from dealer scores."""
        recommendations = []
        for s in scores:
            if s["severity"] in ("CRITICAL", "HIGH", "MEDIUM"):
                reasons = []
                if s["achievement_pct"] < 70:
                    reasons.append(f"achievement at {s['achievement_pct']}%")
                if s["avg_days_overdue"] > 30:
                    reasons.append(f"avg {s['avg_days_overdue']} days overdue")
                if s["declining_months"] >= 3:
                    reasons.append(f"{s['declining_months']} declining months")
                if s["claim_rate"] > 10:
                    reasons.append(f"claim rate {s['claim_rate']}%")

                action = "Review and intervene immediately" if s["severity"] == "CRITICAL" else \
                         "Schedule performance review" if s["severity"] == "HIGH" else \
                         "Monitor closely"

                recommendations.append({
                    "type": "dealer_performance",
                    "severity": s["severity"],
                    "dealer_code": s["dealer_code"],
                    "dealer_name": s["name"],
                    "recommendation": f"{s['dealer_code']} ({s['name']}): {', '.join(reasons)}. {action}.",
                    "details": f"Composite score: {s['composite_score']}/100",
                })

        severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        recommendations.sort(key=lambda x: severity_order.get(x["severity"], 4))
        return recommendations

    async def get_recommendations(self) -> List[Dict]:
        """Get recommendations from last analysis."""
        if not self._results:
            return []
        return self._results.get("recommendations", [])[:20]

    async def get_status(self) -> Dict:
        """Get agent status."""
        return {
            "id": "dealer-performance",
            "name": "Dealer Performance Agent",
            "description": "Scores dealers on achievement, payment compliance, growth trajectory, and claim rates",
            "status": self._status,
            "last_run": self._last_run.isoformat() if self._last_run else None,
            "data_sources": "dealers, dealer_targets, dealer_credit_ledger, dealer_claims, orders",
            "capabilities": [
                "Sales achievement scoring",
                "Payment compliance analysis",
                "Growth trajectory tracking",
                "Claim rate monitoring",
            ],
        }
