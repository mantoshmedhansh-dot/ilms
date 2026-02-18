"""
DMS AI - Collection Optimizer Agent

Analyzes:
- Aging buckets: 0-30 / 31-60 / 61-90 / 90+ days from unsettled INVOICE entries
- Payment prediction: avg historical payment days -> predicted dates
- Priority ranking: score = overdue_amount x days_overdue_weight x (1/payment_rating)
- Strategy: 90+ -> credit hold + field visit; 60+ -> escalate; 30+ -> call; 0+ -> auto reminder
"""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import List, Dict, Optional
from uuid import UUID
from collections import defaultdict

from sqlalchemy import select, func, and_, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dealer import Dealer, DealerCreditLedger


class DMSCollectionOptimizerAgent:
    """Optimizes collection strategies using aging analysis and payment prediction."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self._status = "idle"
        self._last_run = None
        self._results = None

    async def analyze(self, **kwargs) -> Dict:
        """Run full collection optimization analysis."""
        self._status = "running"
        try:
            aging = await self._analyze_aging_buckets()
            predictions = await self._predict_payments()
            priority = await self._rank_priority()
            recommendations = self._generate_recommendations(priority)

            severity_summary = defaultdict(int)
            for rec in recommendations:
                severity_summary[rec["severity"]] += 1

            self._results = {
                "agent": "collection-optimizer",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "summary": {
                    "total_outstanding": aging["total_outstanding"],
                    "total_overdue_dealers": aging["total_overdue_dealers"],
                    "by_severity": dict(severity_summary),
                    "aging_buckets": aging["buckets"],
                },
                "aging_analysis": aging,
                "payment_predictions": predictions[:30],
                "priority_ranking": priority[:30],
                "recommendations": recommendations[:30],
            }
            self._status = "completed"
            self._last_run = datetime.now(timezone.utc)
            return self._results

        except Exception as e:
            self._status = "error"
            return {"agent": "collection-optimizer", "error": str(e), "status": "error"}

    async def _analyze_aging_buckets(self) -> Dict:
        """Analyze outstanding invoices into aging buckets."""
        today = date.today()

        # Get unsettled invoices
        result = await self.db.execute(
            select(
                DealerCreditLedger.dealer_id,
                DealerCreditLedger.transaction_date,
                DealerCreditLedger.due_date,
                DealerCreditLedger.debit_amount,
                DealerCreditLedger.credit_amount,
                DealerCreditLedger.days_overdue,
            ).where(
                and_(
                    DealerCreditLedger.is_settled == False,
                    DealerCreditLedger.transaction_type == "INVOICE",
                )
            )
        )
        rows = result.all()

        buckets = {"0-30": 0, "31-60": 0, "61-90": 0, "90+": 0}
        bucket_counts = {"0-30": 0, "31-60": 0, "61-90": 0, "90+": 0}
        dealer_overdue = set()
        total_outstanding = 0

        for row in rows:
            amount = float(row.debit_amount or 0) - float(row.credit_amount or 0)
            if amount <= 0:
                continue
            total_outstanding += amount

            days = row.days_overdue or 0
            if days <= 0 and row.due_date:
                days = max(0, (today - row.due_date).days)

            if days > 0:
                dealer_overdue.add(row.dealer_id)

            if days <= 30:
                buckets["0-30"] += amount
                bucket_counts["0-30"] += 1
            elif days <= 60:
                buckets["31-60"] += amount
                bucket_counts["31-60"] += 1
            elif days <= 90:
                buckets["61-90"] += amount
                bucket_counts["61-90"] += 1
            else:
                buckets["90+"] += amount
                bucket_counts["90+"] += 1

        return {
            "total_outstanding": round(total_outstanding, 2),
            "total_overdue_dealers": len(dealer_overdue),
            "buckets": {k: round(v, 2) for k, v in buckets.items()},
            "bucket_counts": bucket_counts,
            "total_invoices": len(rows),
        }

    async def _predict_payments(self) -> List[Dict]:
        """Predict payment dates based on historical payment behavior."""
        # Get average payment days per dealer from settled invoices
        result = await self.db.execute(
            select(
                DealerCreditLedger.dealer_id,
                func.avg(DealerCreditLedger.days_overdue).label("avg_payment_days"),
                func.count(DealerCreditLedger.id).label("settled_count"),
            ).where(
                and_(
                    DealerCreditLedger.is_settled == True,
                    DealerCreditLedger.transaction_type == "INVOICE",
                )
            ).group_by(DealerCreditLedger.dealer_id)
        )
        history = {row.dealer_id: float(row.avg_payment_days or 0) for row in result.all()}

        # Get unsettled invoices
        unsettled = await self.db.execute(
            select(
                DealerCreditLedger.id,
                DealerCreditLedger.dealer_id,
                DealerCreditLedger.transaction_date,
                DealerCreditLedger.due_date,
                DealerCreditLedger.debit_amount,
                DealerCreditLedger.reference_number,
            ).where(
                and_(
                    DealerCreditLedger.is_settled == False,
                    DealerCreditLedger.transaction_type == "INVOICE",
                )
            )
        )

        # Get dealer names
        dealers_result = await self.db.execute(
            select(Dealer.id, Dealer.dealer_code, Dealer.name)
            .where(Dealer.status == "ACTIVE")
        )
        dealer_names = {d.id: {"code": d.dealer_code, "name": d.name} for d in dealers_result.all()}

        predictions = []
        today = date.today()
        for row in unsettled.all():
            avg_days = history.get(row.dealer_id, 30)
            predicted_date = row.transaction_date + timedelta(days=int(avg_days))
            days_until = (predicted_date - today).days

            info = dealer_names.get(row.dealer_id, {})
            predictions.append({
                "dealer_id": str(row.dealer_id),
                "dealer_code": info.get("code", ""),
                "dealer_name": info.get("name", ""),
                "invoice_ref": row.reference_number,
                "invoice_date": row.transaction_date.isoformat(),
                "due_date": row.due_date.isoformat() if row.due_date else None,
                "amount": float(row.debit_amount or 0),
                "avg_payment_days": round(avg_days, 1),
                "predicted_payment_date": predicted_date.isoformat(),
                "days_until_predicted": days_until,
                "likely_late": days_until < 0,
            })

        predictions.sort(key=lambda x: x["days_until_predicted"])
        return predictions

    async def _rank_priority(self) -> List[Dict]:
        """Rank dealers by collection priority."""
        result = await self.db.execute(
            select(
                Dealer.id, Dealer.dealer_code, Dealer.name,
                Dealer.outstanding_amount, Dealer.overdue_amount,
                Dealer.credit_limit, Dealer.payment_rating,
            ).where(
                and_(
                    Dealer.status == "ACTIVE",
                    Dealer.outstanding_amount > 0,
                )
            )
        )
        dealers = result.all()

        # Get max overdue days per dealer
        overdue_result = await self.db.execute(
            select(
                DealerCreditLedger.dealer_id,
                func.max(DealerCreditLedger.days_overdue).label("max_days"),
                func.avg(DealerCreditLedger.days_overdue).label("avg_days"),
            ).where(
                and_(
                    DealerCreditLedger.is_settled == False,
                    DealerCreditLedger.transaction_type == "INVOICE",
                )
            ).group_by(DealerCreditLedger.dealer_id)
        )
        overdue_map = {
            row.dealer_id: {
                "max_days": int(row.max_days or 0),
                "avg_days": float(row.avg_days or 0),
            }
            for row in overdue_result.all()
        }

        rankings = []
        for d in dealers:
            overdue_info = overdue_map.get(d.id, {"max_days": 0, "avg_days": 0})
            overdue_amt = float(d.overdue_amount or 0)
            max_days = overdue_info["max_days"]
            payment_rating = float(d.payment_rating or 3.0)

            # Priority score: higher = more urgent
            days_weight = 1 + (max_days / 30)
            rating_factor = 1 / max(payment_rating, 0.5)
            priority_score = overdue_amt * days_weight * rating_factor / 1000

            # Strategy based on max overdue days
            if max_days > 90:
                strategy = "Credit hold + field visit"
                severity = "CRITICAL"
            elif max_days > 60:
                strategy = "Escalate to ASM + call"
                severity = "HIGH"
            elif max_days > 30:
                strategy = "Phone call follow-up"
                severity = "MEDIUM"
            else:
                strategy = "Auto payment reminder"
                severity = "LOW"

            rankings.append({
                "dealer_id": str(d.id),
                "dealer_code": d.dealer_code,
                "name": d.name,
                "outstanding": float(d.outstanding_amount or 0),
                "overdue": overdue_amt,
                "credit_limit": float(d.credit_limit or 0),
                "max_days_overdue": max_days,
                "avg_days_overdue": round(overdue_info["avg_days"], 1),
                "payment_rating": payment_rating,
                "priority_score": round(priority_score, 2),
                "strategy": strategy,
                "severity": severity,
            })

        rankings.sort(key=lambda x: -x["priority_score"])
        return rankings

    def _generate_recommendations(self, priority: List[Dict]) -> List[Dict]:
        """Generate collection recommendations."""
        recommendations = []
        for p in priority:
            if p["severity"] in ("CRITICAL", "HIGH", "MEDIUM"):
                recommendations.append({
                    "type": "collection_priority",
                    "severity": p["severity"],
                    "dealer_code": p["dealer_code"],
                    "recommendation": (
                        f"{p['dealer_code']} ({p['name']}): "
                        f"Outstanding {p['outstanding']:,.0f}, "
                        f"overdue {p['overdue']:,.0f}, "
                        f"max {p['max_days_overdue']} days. "
                        f"Action: {p['strategy']}."
                    ),
                    "details": f"Priority score: {p['priority_score']}, Rating: {p['payment_rating']}",
                })

        severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        recommendations.sort(key=lambda x: severity_order.get(x["severity"], 4))
        return recommendations

    async def get_recommendations(self) -> List[Dict]:
        if not self._results:
            return []
        return self._results.get("recommendations", [])[:20]

    async def get_status(self) -> Dict:
        return {
            "id": "collection-optimizer",
            "name": "Collection Optimizer Agent",
            "description": "Aging bucket analysis, payment prediction, priority ranking, and collection strategies",
            "status": self._status,
            "last_run": self._last_run.isoformat() if self._last_run else None,
            "data_sources": "dealers, dealer_credit_ledger",
            "capabilities": [
                "Aging bucket analysis",
                "Payment date prediction",
                "Priority-based collection ranking",
                "Strategy recommendation",
            ],
        }
