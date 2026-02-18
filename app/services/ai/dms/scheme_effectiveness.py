"""
DMS AI - Scheme Effectiveness Agent

Analyzes:
- ROI: (order_value - discount) / discount x 100
- Budget utilization %, flag >90% or <20%
- Participation rate: participating dealers / eligible dealers
- Recommendations: low ROI -> retire; high ROI + near budget -> extend
"""

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import List, Dict, Optional
from uuid import UUID
from collections import defaultdict

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dealer import Dealer, DealerScheme, DealerSchemeApplication


class DMSSchemeEffectivenessAgent:
    """Analyzes scheme ROI, budget utilization, and participation rates."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self._status = "idle"
        self._last_run = None
        self._results = None

    async def analyze(self, **kwargs) -> Dict:
        """Run full scheme effectiveness analysis."""
        self._status = "running"
        try:
            scheme_scores = await self._score_schemes()
            recommendations = self._generate_recommendations(scheme_scores)

            severity_summary = defaultdict(int)
            for rec in recommendations:
                severity_summary[rec["severity"]] += 1

            active_schemes = [s for s in scheme_scores if s.get("is_active")]
            avg_roi = round(
                sum(s.get("roi", 0) for s in active_schemes) / max(len(active_schemes), 1), 1
            )

            self._results = {
                "agent": "scheme-effectiveness",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "summary": {
                    "total_schemes_analyzed": len(scheme_scores),
                    "active_schemes": len(active_schemes),
                    "avg_roi": avg_roi,
                    "by_severity": dict(severity_summary),
                    "total_budget": sum(s.get("total_budget", 0) for s in scheme_scores),
                    "total_utilized": sum(s.get("utilized_budget", 0) for s in scheme_scores),
                },
                "scheme_scores": scheme_scores[:50],
                "recommendations": recommendations[:30],
            }
            self._status = "completed"
            self._last_run = datetime.now(timezone.utc)
            return self._results

        except Exception as e:
            self._status = "error"
            return {"agent": "scheme-effectiveness", "error": str(e), "status": "error"}

    async def _score_schemes(self) -> List[Dict]:
        """Score all schemes on ROI, budget utilization, and participation."""
        today = date.today()

        # Get all schemes
        schemes_result = await self.db.execute(
            select(
                DealerScheme.id,
                DealerScheme.scheme_code,
                DealerScheme.scheme_name,
                DealerScheme.scheme_type,
                DealerScheme.start_date,
                DealerScheme.end_date,
                DealerScheme.is_active,
                DealerScheme.total_budget,
                DealerScheme.utilized_budget,
            )
        )
        schemes = schemes_result.all()

        if not schemes:
            return []

        scheme_ids = [s.id for s in schemes]

        # Get application stats per scheme
        app_result = await self.db.execute(
            select(
                DealerSchemeApplication.scheme_id,
                func.count(DealerSchemeApplication.id).label("app_count"),
                func.count(func.distinct(DealerSchemeApplication.dealer_id)).label("unique_dealers"),
                func.sum(DealerSchemeApplication.order_value).label("total_order_value"),
                func.sum(DealerSchemeApplication.discount_calculated).label("total_discount"),
            ).where(DealerSchemeApplication.scheme_id.in_(scheme_ids))
            .group_by(DealerSchemeApplication.scheme_id)
        )
        app_map = {}
        for row in app_result.all():
            app_map[row.scheme_id] = {
                "app_count": int(row.app_count or 0),
                "unique_dealers": int(row.unique_dealers or 0),
                "total_order_value": float(row.total_order_value or 0),
                "total_discount": float(row.total_discount or 0),
            }

        # Get total active dealers for participation rate
        active_dealers_result = await self.db.execute(
            select(func.count(Dealer.id)).where(Dealer.status == "ACTIVE")
        )
        total_active_dealers = active_dealers_result.scalar() or 1

        scores = []
        for s in schemes:
            apps = app_map.get(s.id, {})
            total_budget = float(s.total_budget or 0)
            utilized = float(s.utilized_budget or 0)
            total_discount = apps.get("total_discount", 0)
            total_order_value = apps.get("total_order_value", 0)
            unique_dealers = apps.get("unique_dealers", 0)

            # ROI calculation
            roi = 0
            if total_discount > 0:
                roi = ((total_order_value - total_discount) / total_discount) * 100

            # Budget utilization
            budget_util = (utilized / total_budget * 100) if total_budget > 0 else 0

            # Participation rate
            participation_rate = (unique_dealers / total_active_dealers * 100)

            # Determine severity
            severity = "LOW"
            if roi < 50 and s.is_active:
                severity = "HIGH"
            elif budget_util > 90 and s.is_active:
                severity = "MEDIUM"
            elif budget_util < 20 and s.is_active and (today - s.start_date).days > 30:
                severity = "MEDIUM"
            elif roi < 100 and s.is_active:
                severity = "MEDIUM"

            scores.append({
                "scheme_id": str(s.id),
                "scheme_code": s.scheme_code,
                "scheme_name": s.scheme_name,
                "scheme_type": s.scheme_type,
                "is_active": s.is_active,
                "start_date": s.start_date.isoformat(),
                "end_date": s.end_date.isoformat(),
                "total_budget": total_budget,
                "utilized_budget": utilized,
                "budget_utilization_pct": round(budget_util, 1),
                "roi": round(roi, 1),
                "total_order_value": total_order_value,
                "total_discount": total_discount,
                "applications": apps.get("app_count", 0),
                "participating_dealers": unique_dealers,
                "participation_rate_pct": round(participation_rate, 1),
                "severity": severity,
            })

        scores.sort(key=lambda x: x["roi"])
        return scores

    def _generate_recommendations(self, scores: List[Dict]) -> List[Dict]:
        """Generate scheme recommendations."""
        recommendations = []
        for s in scores:
            if not s["is_active"]:
                continue

            if s["roi"] < 50:
                recommendations.append({
                    "type": "scheme_effectiveness",
                    "severity": "HIGH",
                    "scheme_code": s["scheme_code"],
                    "recommendation": (
                        f"{s['scheme_code']} ({s['scheme_name']}): "
                        f"Very low ROI ({s['roi']}%). Consider retiring this scheme."
                    ),
                    "details": f"Budget util: {s['budget_utilization_pct']}%, Participation: {s['participation_rate_pct']}%",
                })
            elif s["budget_utilization_pct"] > 90:
                recommendations.append({
                    "type": "scheme_effectiveness",
                    "severity": "MEDIUM",
                    "scheme_code": s["scheme_code"],
                    "recommendation": (
                        f"{s['scheme_code']} ({s['scheme_name']}): "
                        f"Budget nearly exhausted ({s['budget_utilization_pct']}%). "
                        f"{'Extend budget (high ROI: ' + str(s['roi']) + '%)' if s['roi'] > 200 else 'Review before extending'}."
                    ),
                    "details": f"ROI: {s['roi']}%, Orders: {s['applications']}",
                })
            elif s["budget_utilization_pct"] < 20 and s["participation_rate_pct"] < 10:
                recommendations.append({
                    "type": "scheme_effectiveness",
                    "severity": "MEDIUM",
                    "scheme_code": s["scheme_code"],
                    "recommendation": (
                        f"{s['scheme_code']} ({s['scheme_name']}): "
                        f"Low adoption - only {s['participation_rate_pct']}% participation, "
                        f"{s['budget_utilization_pct']}% budget used. Improve promotion or revise terms."
                    ),
                    "details": f"ROI: {s['roi']}%, Dealers: {s['participating_dealers']}",
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
            "id": "scheme-effectiveness",
            "name": "Scheme Effectiveness Agent",
            "description": "Analyzes scheme ROI, budget utilization, and dealer participation rates",
            "status": self._status,
            "last_run": self._last_run.isoformat() if self._last_run else None,
            "data_sources": "dealer_schemes, dealer_scheme_applications, dealers",
            "capabilities": [
                "Scheme ROI calculation",
                "Budget utilization tracking",
                "Participation rate analysis",
                "Scheme lifecycle recommendations",
            ],
        }
