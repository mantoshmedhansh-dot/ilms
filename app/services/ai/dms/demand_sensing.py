"""
DMS AI - Demand Sensing Agent

Analyzes:
- Dealer order trends: monthly values over 6 months, moving average
- Retailer velocity: orders per outlet, flag inactive (30+ days no order)
- Seasonal patterns: z-score on monthly aggregates
- Forecast: weighted moving average (alpha=0.3) -> next month per dealer
"""

from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional
from uuid import UUID
from collections import defaultdict
import math

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dealer import Dealer, RetailerOutlet
from app.models.order import Order


class DMSDemandSensingAgent:
    """Dealer/retailer demand trends, seasonal patterns, and forecasts."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self._status = "idle"
        self._last_run = None
        self._results = None

    async def analyze(self, **kwargs) -> Dict:
        """Run full demand sensing analysis."""
        self._status = "running"
        try:
            dealer_trends = await self._analyze_dealer_trends()
            retailer_velocity = await self._analyze_retailer_velocity()
            seasonal = self._detect_seasonal_patterns(dealer_trends)
            forecasts = self._generate_forecasts(dealer_trends)
            recommendations = self._generate_recommendations(
                dealer_trends, retailer_velocity, forecasts
            )

            severity_summary = defaultdict(int)
            for rec in recommendations:
                severity_summary[rec["severity"]] += 1

            self._results = {
                "agent": "demand-sensing",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "summary": {
                    "dealers_analyzed": len(dealer_trends),
                    "retailers_analyzed": retailer_velocity.get("total_outlets", 0),
                    "inactive_retailers": retailer_velocity.get("inactive_count", 0),
                    "seasonal_anomalies": len(seasonal),
                    "by_severity": dict(severity_summary),
                },
                "dealer_trends": dealer_trends[:30],
                "retailer_velocity": retailer_velocity,
                "seasonal_patterns": seasonal[:20],
                "forecasts": forecasts[:30],
                "recommendations": recommendations[:30],
            }
            self._status = "completed"
            self._last_run = datetime.now(timezone.utc)
            return self._results

        except Exception as e:
            self._status = "error"
            return {"agent": "demand-sensing", "error": str(e), "status": "error"}

    async def _analyze_dealer_trends(self) -> List[Dict]:
        """Analyze monthly order trends per dealer over 6 months."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=180)

        result = await self.db.execute(
            select(
                Order.dealer_id,
                func.date_trunc("month", Order.created_at).label("month"),
                func.count(Order.id).label("order_count"),
                func.sum(Order.total_amount).label("revenue"),
            ).where(
                and_(
                    Order.dealer_id.isnot(None),
                    Order.created_at >= cutoff,
                )
            ).group_by(Order.dealer_id, "month")
            .order_by(Order.dealer_id, "month")
        )
        rows = result.all()

        # Get dealer info
        dealers_result = await self.db.execute(
            select(Dealer.id, Dealer.dealer_code, Dealer.name, Dealer.region)
            .where(Dealer.status == "ACTIVE")
        )
        dealer_info = {
            d.id: {"code": d.dealer_code, "name": d.name, "region": d.region}
            for d in dealers_result.all()
        }

        # Group by dealer
        dealer_monthly = defaultdict(list)
        for row in rows:
            dealer_monthly[row.dealer_id].append({
                "month": row.month.strftime("%Y-%m") if row.month else "",
                "order_count": int(row.order_count or 0),
                "revenue": float(row.revenue or 0),
            })

        trends = []
        for dealer_id, months in dealer_monthly.items():
            info = dealer_info.get(dealer_id, {})
            revenues = [m["revenue"] for m in months]

            # Moving average
            ma = []
            for i in range(len(revenues)):
                window = revenues[max(0, i - 2):i + 1]
                ma.append(round(sum(window) / len(window), 2))

            # Trend direction
            if len(revenues) >= 2:
                recent = sum(revenues[-2:]) / 2
                earlier = sum(revenues[:2]) / max(len(revenues[:2]), 1)
                if recent > earlier * 1.1:
                    trend = "GROWING"
                elif recent < earlier * 0.9:
                    trend = "DECLINING"
                else:
                    trend = "STABLE"
            else:
                trend = "INSUFFICIENT_DATA"

            trends.append({
                "dealer_id": str(dealer_id),
                "dealer_code": info.get("code", ""),
                "dealer_name": info.get("name", ""),
                "region": info.get("region", ""),
                "monthly_data": months,
                "moving_average": ma,
                "trend": trend,
                "total_revenue_6m": round(sum(revenues), 2),
                "avg_monthly_revenue": round(sum(revenues) / max(len(revenues), 1), 2),
            })

        trends.sort(key=lambda x: -x["total_revenue_6m"])
        return trends

    async def _analyze_retailer_velocity(self) -> Dict:
        """Analyze order velocity per retailer outlet."""
        now = datetime.now(timezone.utc)
        cutoff_30 = now - timedelta(days=30)

        # Get all active outlets
        outlets_result = await self.db.execute(
            select(
                RetailerOutlet.id,
                RetailerOutlet.outlet_code,
                RetailerOutlet.name,
                RetailerOutlet.dealer_id,
                RetailerOutlet.total_orders,
                RetailerOutlet.total_revenue,
                RetailerOutlet.last_order_date,
            ).where(RetailerOutlet.status == "ACTIVE")
        )
        outlets = outlets_result.all()

        active_outlets = []
        inactive_outlets = []

        for o in outlets:
            is_inactive = (
                o.last_order_date is None
                or o.last_order_date < cutoff_30
            )

            entry = {
                "outlet_id": str(o.id),
                "outlet_code": o.outlet_code,
                "name": o.name,
                "dealer_id": str(o.dealer_id),
                "total_orders": o.total_orders or 0,
                "total_revenue": float(o.total_revenue or 0),
                "last_order_date": o.last_order_date.isoformat() if o.last_order_date else None,
                "days_since_last_order": (
                    (now - o.last_order_date).days if o.last_order_date else 999
                ),
            }

            if is_inactive:
                inactive_outlets.append(entry)
            else:
                active_outlets.append(entry)

        return {
            "total_outlets": len(outlets),
            "active_count": len(active_outlets),
            "inactive_count": len(inactive_outlets),
            "inactive_outlets": sorted(
                inactive_outlets, key=lambda x: -x["days_since_last_order"]
            )[:20],
            "top_performers": sorted(
                active_outlets, key=lambda x: -x["total_revenue"]
            )[:10],
        }

    def _detect_seasonal_patterns(self, trends: List[Dict]) -> List[Dict]:
        """Detect seasonal anomalies using z-score on monthly aggregates."""
        # Aggregate all revenues by month
        monthly_totals = defaultdict(float)
        for t in trends:
            for m in t.get("monthly_data", []):
                monthly_totals[m["month"]] += m["revenue"]

        if len(monthly_totals) < 3:
            return []

        values = list(monthly_totals.values())
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        std_dev = math.sqrt(variance) if variance > 0 else 0

        anomalies = []
        for month, total in sorted(monthly_totals.items()):
            if std_dev > 0:
                z = (total - mean) / std_dev
                if abs(z) > 1.5:
                    anomalies.append({
                        "month": month,
                        "total_revenue": round(total, 2),
                        "z_score": round(z, 2),
                        "direction": "high" if z > 0 else "low",
                        "mean": round(mean, 2),
                        "severity": "HIGH" if abs(z) > 2.5 else "MEDIUM",
                    })

        return anomalies

    def _generate_forecasts(self, trends: List[Dict]) -> List[Dict]:
        """Generate next-month forecasts using weighted moving average (alpha=0.3)."""
        alpha = 0.3
        forecasts = []

        for t in trends:
            revenues = [m["revenue"] for m in t.get("monthly_data", [])]
            if len(revenues) < 2:
                continue

            # Exponential weighted moving average
            ewma = revenues[0]
            for r in revenues[1:]:
                ewma = alpha * r + (1 - alpha) * ewma

            # Confidence based on data points
            confidence = min(0.95, 0.5 + len(revenues) * 0.08)

            forecasts.append({
                "dealer_id": t["dealer_id"],
                "dealer_code": t["dealer_code"],
                "dealer_name": t["dealer_name"],
                "region": t["region"],
                "forecast_revenue": round(ewma, 2),
                "last_month_revenue": round(revenues[-1], 2),
                "trend": t["trend"],
                "confidence": round(confidence, 2),
                "data_points": len(revenues),
            })

        forecasts.sort(key=lambda x: -x["forecast_revenue"])
        return forecasts

    def _generate_recommendations(
        self, trends: List[Dict], velocity: Dict, forecasts: List[Dict]
    ) -> List[Dict]:
        """Generate demand sensing recommendations."""
        recommendations = []

        # Declining dealers
        for t in trends:
            if t["trend"] == "DECLINING":
                recommendations.append({
                    "type": "demand_trend",
                    "severity": "HIGH",
                    "recommendation": (
                        f"{t['dealer_code']} ({t['dealer_name']}): "
                        f"Declining demand trend over 6 months. "
                        f"Avg monthly: {t['avg_monthly_revenue']:,.0f}. Investigate root cause."
                    ),
                    "details": f"Region: {t['region']}, Total 6M: {t['total_revenue_6m']:,.0f}",
                })

        # Inactive retailers
        inactive = velocity.get("inactive_outlets", [])
        if len(inactive) > 5:
            recommendations.append({
                "type": "retailer_velocity",
                "severity": "MEDIUM",
                "recommendation": (
                    f"{len(inactive)} retailer outlets inactive (30+ days no order). "
                    f"Review beat plan coverage and outlet engagement."
                ),
                "details": f"Total outlets: {velocity.get('total_outlets', 0)}",
            })

        # Seasonal anomalies already covered via patterns

        severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        recommendations.sort(key=lambda x: severity_order.get(x["severity"], 4))
        return recommendations

    async def get_recommendations(self) -> List[Dict]:
        if not self._results:
            return []
        return self._results.get("recommendations", [])[:20]

    async def get_status(self) -> Dict:
        return {
            "id": "demand-sensing",
            "name": "Demand Sensing Agent",
            "description": "Dealer/retailer demand trends, seasonal patterns, and demand forecasting",
            "status": self._status,
            "last_run": self._last_run.isoformat() if self._last_run else None,
            "data_sources": "dealers, orders (dealer_id IS NOT NULL), retailer_outlets",
            "capabilities": [
                "Dealer order trend analysis",
                "Retailer velocity tracking",
                "Seasonal pattern detection",
                "Weighted moving average forecasting",
            ],
        }
