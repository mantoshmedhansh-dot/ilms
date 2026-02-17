"""
AI-Powered Demand Forecasting Service

Uses time-series analysis to predict future demand:
- Triple Exponential Smoothing (Holt-Winters)
- Seasonal decomposition
- Trend analysis
- Confidence intervals

No external ML libraries required - pure Python implementation.
"""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import List, Dict, Optional, Tuple
from uuid import UUID
import math
from collections import defaultdict

from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order, OrderItem, OrderStatus
from app.models.product import Product
from app.models.inventory import InventorySummary


class DemandForecastingService:
    """
    Advanced demand forecasting using statistical time-series methods.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    # ==================== Core Forecasting Algorithms ====================

    def _triple_exponential_smoothing(
        self,
        data: List[float],
        season_length: int = 7,
        alpha: float = 0.3,
        beta: float = 0.1,
        gamma: float = 0.2,
        forecast_periods: int = 30
    ) -> Tuple[List[float], List[float], List[float]]:
        """
        Holt-Winters Triple Exponential Smoothing for seasonal data.

        Returns: (fitted_values, forecasts, confidence_intervals)
        """
        if len(data) < season_length * 2:
            # Not enough data for seasonal analysis, fall back to simple smoothing
            return self._simple_forecast(data, forecast_periods)

        n = len(data)

        # Initialize level, trend, and seasonality
        level = sum(data[:season_length]) / season_length
        trend = (sum(data[season_length:2*season_length]) - sum(data[:season_length])) / (season_length ** 2)

        # Initial seasonal indices
        seasonals = []
        for i in range(season_length):
            season_avg = sum(data[j] for j in range(i, min(n, i + season_length * 3), season_length)) / 3
            seasonals.append(data[i] / level if level > 0 else 1.0)

        fitted = []

        # Fit the model
        for i in range(n):
            if i >= season_length:
                old_level = level
                level = alpha * (data[i] / seasonals[i % season_length]) + (1 - alpha) * (level + trend)
                trend = beta * (level - old_level) + (1 - beta) * trend
                seasonals[i % season_length] = gamma * (data[i] / level) + (1 - gamma) * seasonals[i % season_length]

            fitted.append((level + trend) * seasonals[i % season_length])

        # Generate forecasts
        forecasts = []
        for i in range(forecast_periods):
            forecast = (level + (i + 1) * trend) * seasonals[(n + i) % season_length]
            forecasts.append(max(0, forecast))

        # Calculate confidence intervals (using historical variance)
        residuals = [abs(data[i] - fitted[i]) for i in range(len(fitted))]
        std_dev = (sum(r ** 2 for r in residuals) / len(residuals)) ** 0.5 if residuals else 0

        confidence = []
        for i, f in enumerate(forecasts):
            # Confidence interval widens with forecast horizon
            interval = std_dev * (1 + 0.1 * i) * 1.96  # 95% CI
            confidence.append(interval)

        return fitted, forecasts, confidence

    def _simple_forecast(
        self,
        data: List[float],
        forecast_periods: int
    ) -> Tuple[List[float], List[float], List[float]]:
        """
        Simple exponential smoothing fallback for limited data.
        """
        if not data:
            return [], [0] * forecast_periods, [0] * forecast_periods

        alpha = 0.3
        smoothed = [data[0]]

        for i in range(1, len(data)):
            smoothed.append(alpha * data[i] + (1 - alpha) * smoothed[-1])

        # Forecast is last smoothed value with trend
        if len(smoothed) >= 2:
            trend = (smoothed[-1] - smoothed[-7]) / 7 if len(smoothed) >= 7 else 0
        else:
            trend = 0

        forecasts = []
        for i in range(forecast_periods):
            forecasts.append(max(0, smoothed[-1] + trend * (i + 1)))

        # Simple confidence interval
        std_dev = (sum((data[i] - smoothed[i]) ** 2 for i in range(len(data))) / len(data)) ** 0.5 if data else 0
        confidence = [std_dev * 1.96 * (1 + 0.05 * i) for i in range(forecast_periods)]

        return smoothed, forecasts, confidence

    def _calculate_seasonality_indices(
        self,
        data: List[float],
        period: int = 7
    ) -> Dict[int, float]:
        """
        Calculate day-of-week seasonality indices.
        """
        if len(data) < period * 2:
            return {i: 1.0 for i in range(period)}

        # Group by day of week
        daily_sums = defaultdict(list)
        for i, val in enumerate(data):
            daily_sums[i % period].append(val)

        # Calculate average for each day
        overall_avg = sum(data) / len(data) if data else 1

        indices = {}
        for day, values in daily_sums.items():
            day_avg = sum(values) / len(values)
            indices[day] = day_avg / overall_avg if overall_avg > 0 else 1.0

        return indices

    # ==================== Product Demand Forecasting ====================

    async def forecast_product_demand(
        self,
        product_id: UUID,
        days_ahead: int = 30,
        lookback_days: int = 90
    ) -> Dict:
        """
        Forecast demand for a specific product.

        Returns comprehensive prediction with confidence intervals.
        """
        start_date = date.today() - timedelta(days=lookback_days)

        # Get historical sales data
        query = select(
            func.date(Order.created_at).label('sale_date'),
            func.sum(OrderItem.quantity).label('quantity')
        ).join(
            OrderItem, Order.id == OrderItem.order_id
        ).where(
            and_(
                OrderItem.product_id == product_id,
                Order.created_at >= start_date,
                Order.status.in_([
                    OrderStatus.DELIVERED,
                    OrderStatus.SHIPPED,
                    OrderStatus.CONFIRMED,
                    OrderStatus.IN_TRANSIT
                ])
            )
        ).group_by(
            func.date(Order.created_at)
        ).order_by(
            func.date(Order.created_at)
        )

        result = await self.db.execute(query)
        rows = result.all()

        # Build daily sales map
        daily_sales = {}
        for row in rows:
            daily_sales[row.sale_date] = row.quantity or 0

        # Fill in missing days with 0
        all_values = []
        current = start_date
        while current <= date.today():
            all_values.append(float(daily_sales.get(current, 0)))
            current += timedelta(days=1)

        # Apply forecasting algorithm
        fitted, forecasts, confidence = self._triple_exponential_smoothing(
            all_values,
            season_length=7,
            forecast_periods=days_ahead
        )

        # Calculate metrics
        total_historical = sum(all_values)
        avg_daily = total_historical / len(all_values) if all_values else 0
        total_forecast = sum(forecasts)

        # Determine trend
        if len(all_values) >= 14:
            recent_avg = sum(all_values[-7:]) / 7
            previous_avg = sum(all_values[-14:-7]) / 7
            if previous_avg > 0:
                trend_pct = ((recent_avg - previous_avg) / previous_avg) * 100
                trend = "increasing" if trend_pct > 5 else ("decreasing" if trend_pct < -5 else "stable")
            else:
                trend = "stable"
                trend_pct = 0
        else:
            trend = "insufficient_data"
            trend_pct = 0

        # Get product info
        product_query = select(Product).where(Product.id == product_id)
        product_result = await self.db.execute(product_query)
        product = product_result.scalar_one_or_none()

        # Get current stock
        stock_query = select(InventorySummary).where(
            InventorySummary.product_id == product_id
        )
        stock_result = await self.db.execute(stock_query)
        stock = stock_result.scalar_one_or_none()
        current_stock = stock.available_quantity if stock else 0

        # Calculate days until stockout
        days_until_stockout = int(current_stock / avg_daily) if avg_daily > 0 else 999

        # Calculate recommended reorder
        safety_stock_days = 7
        lead_time_days = 14
        recommended_qty = max(0, int(
            (avg_daily * (lead_time_days + safety_stock_days + days_ahead)) - current_stock
        ))

        # Build daily forecasts
        daily_forecasts = []
        for i in range(days_ahead):
            forecast_date = date.today() + timedelta(days=i+1)
            daily_forecasts.append({
                "date": forecast_date.isoformat(),
                "predicted_qty": round(forecasts[i], 1),
                "lower_bound": round(max(0, forecasts[i] - confidence[i]), 1),
                "upper_bound": round(forecasts[i] + confidence[i], 1)
            })

        # Calculate confidence score
        if len(all_values) >= 60:
            confidence_score = 0.85
        elif len(all_values) >= 30:
            confidence_score = 0.75
        elif len(all_values) >= 14:
            confidence_score = 0.60
        else:
            confidence_score = 0.40

        return {
            "product_id": str(product_id),
            "product_name": product.name if product else "Unknown",
            "sku": product.sku if product else "",
            "forecast_generated_at": datetime.now().isoformat(),
            "lookback_days": lookback_days,
            "forecast_days": days_ahead,

            # Historical metrics
            "historical_total": int(total_historical),
            "historical_avg_daily": round(avg_daily, 2),

            # Forecasts
            "forecasted_total": round(total_forecast, 1),
            "forecasted_avg_daily": round(total_forecast / days_ahead, 2),
            "daily_forecasts": daily_forecasts,

            # Trend analysis
            "trend": trend,
            "trend_percentage": round(trend_pct, 1),

            # Inventory recommendations
            "current_stock": current_stock,
            "days_until_stockout": days_until_stockout,
            "recommended_reorder_qty": recommended_qty,
            "stockout_risk": "HIGH" if days_until_stockout < 14 else ("MEDIUM" if days_until_stockout < 30 else "LOW"),

            # Confidence
            "confidence_score": confidence_score,
            "model_type": "holt_winters" if len(all_values) >= 14 else "exponential_smoothing",

            # Seasonality
            "seasonality_detected": len(all_values) >= 14,
            "peak_days": self._get_peak_days(all_values) if len(all_values) >= 7 else []
        }

    def _get_peak_days(self, data: List[float]) -> List[str]:
        """Identify peak demand days."""
        if len(data) < 7:
            return []

        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        day_totals = defaultdict(float)
        day_counts = defaultdict(int)

        for i, val in enumerate(data):
            day = i % 7
            day_totals[day] += val
            day_counts[day] += 1

        day_avgs = {day: day_totals[day] / day_counts[day] for day in day_totals}
        sorted_days = sorted(day_avgs.items(), key=lambda x: x[1], reverse=True)

        return [day_names[d[0]] for d in sorted_days[:3]]

    # ==================== Category & Overall Forecasting ====================

    async def forecast_category_demand(
        self,
        category_id: UUID,
        days_ahead: int = 30,
        lookback_days: int = 90
    ) -> Dict:
        """
        Forecast demand for an entire category.
        """
        start_date = date.today() - timedelta(days=lookback_days)

        query = select(
            func.date(Order.created_at).label('sale_date'),
            func.sum(OrderItem.quantity).label('quantity'),
            func.sum(OrderItem.total_amount).label('revenue')
        ).join(
            OrderItem, Order.id == OrderItem.order_id
        ).join(
            Product, OrderItem.product_id == Product.id
        ).where(
            and_(
                Product.category_id == category_id,
                Order.created_at >= start_date,
                Order.status != OrderStatus.CANCELLED
            )
        ).group_by(
            func.date(Order.created_at)
        ).order_by(
            func.date(Order.created_at)
        )

        result = await self.db.execute(query)
        rows = result.all()

        # Build daily data
        daily_qty = {}
        daily_revenue = {}
        for row in rows:
            daily_qty[row.sale_date] = row.quantity or 0
            daily_revenue[row.sale_date] = float(row.revenue or 0)

        # Fill missing days
        qty_values = []
        revenue_values = []
        current = start_date
        while current <= date.today():
            qty_values.append(float(daily_qty.get(current, 0)))
            revenue_values.append(daily_revenue.get(current, 0))
            current += timedelta(days=1)

        # Forecast both quantity and revenue
        _, qty_forecasts, qty_conf = self._triple_exponential_smoothing(
            qty_values, forecast_periods=days_ahead
        )
        _, rev_forecasts, rev_conf = self._triple_exponential_smoothing(
            revenue_values, forecast_periods=days_ahead
        )

        return {
            "category_id": str(category_id),
            "forecast_days": days_ahead,
            "quantity_forecast": {
                "total": round(sum(qty_forecasts), 1),
                "daily_avg": round(sum(qty_forecasts) / days_ahead, 2),
                "daily": [
                    {
                        "date": (date.today() + timedelta(days=i+1)).isoformat(),
                        "qty": round(qty_forecasts[i], 1)
                    }
                    for i in range(days_ahead)
                ]
            },
            "revenue_forecast": {
                "total": round(sum(rev_forecasts), 2),
                "daily_avg": round(sum(rev_forecasts) / days_ahead, 2),
                "daily": [
                    {
                        "date": (date.today() + timedelta(days=i+1)).isoformat(),
                        "revenue": round(rev_forecasts[i], 2)
                    }
                    for i in range(days_ahead)
                ]
            },
            "confidence_score": 0.75 if len(qty_values) >= 30 else 0.55
        }

    async def get_demand_dashboard(self) -> Dict:
        """
        Get overall demand forecasting dashboard.
        """
        # Get top products by recent sales
        thirty_days_ago = date.today() - timedelta(days=30)

        top_products_query = select(
            OrderItem.product_id,
            Product.name,
            Product.sku,
            func.sum(OrderItem.quantity).label('total_qty')
        ).join(
            Order, OrderItem.order_id == Order.id
        ).join(
            Product, OrderItem.product_id == Product.id
        ).where(
            and_(
                Order.created_at >= thirty_days_ago,
                Order.status != OrderStatus.CANCELLED
            )
        ).group_by(
            OrderItem.product_id, Product.name, Product.sku
        ).order_by(
            desc(func.sum(OrderItem.quantity))
        ).limit(10)

        result = await self.db.execute(top_products_query)
        top_products = result.all()

        # Generate forecasts for top products
        product_forecasts = []
        for p in top_products[:5]:  # Limit to top 5 for performance
            try:
                forecast = await self.forecast_product_demand(
                    p.product_id,
                    days_ahead=7,
                    lookback_days=30
                )
                product_forecasts.append({
                    "product_id": str(p.product_id),
                    "product_name": p.name,
                    "sku": p.sku,
                    "next_7_days_forecast": forecast["forecasted_total"],
                    "trend": forecast["trend"],
                    "stockout_risk": forecast["stockout_risk"],
                    "days_until_stockout": forecast["days_until_stockout"]
                })
            except Exception:
                continue

        # Overall sales forecast
        overall_query = select(
            func.date(Order.created_at).label('sale_date'),
            func.sum(Order.total_amount).label('revenue'),
            func.count(Order.id).label('order_count')
        ).where(
            and_(
                Order.created_at >= thirty_days_ago,
                Order.status != OrderStatus.CANCELLED
            )
        ).group_by(
            func.date(Order.created_at)
        ).order_by(
            func.date(Order.created_at)
        )

        result = await self.db.execute(overall_query)
        daily_data = result.all()

        revenue_values = []
        order_values = []
        current = thirty_days_ago
        daily_map = {d.sale_date: (float(d.revenue or 0), d.order_count or 0) for d in daily_data}

        while current <= date.today():
            rev, orders = daily_map.get(current, (0, 0))
            revenue_values.append(rev)
            order_values.append(float(orders))
            current += timedelta(days=1)

        _, rev_forecast, _ = self._simple_forecast(revenue_values, 7)
        _, order_forecast, _ = self._simple_forecast(order_values, 7)

        return {
            "generated_at": datetime.now().isoformat(),
            "forecast_horizon": "7 days",

            "overall_forecast": {
                "next_7_days_revenue": round(sum(rev_forecast), 2),
                "next_7_days_orders": round(sum(order_forecast)),
                "avg_daily_revenue": round(sum(rev_forecast) / 7, 2),
                "avg_daily_orders": round(sum(order_forecast) / 7, 1)
            },

            "product_forecasts": product_forecasts,

            "insights": [
                {
                    "type": "stockout_warning",
                    "message": f"{sum(1 for p in product_forecasts if p['stockout_risk'] == 'HIGH')} products at high stockout risk",
                    "severity": "high"
                },
                {
                    "type": "trend",
                    "message": f"{sum(1 for p in product_forecasts if p['trend'] == 'increasing')} products showing growth",
                    "severity": "info"
                }
            ],

            "confidence_level": "GOOD" if len(revenue_values) >= 30 else "MODERATE"
        }

    # ==================== Bulk Forecasting ====================

    async def forecast_all_products(
        self,
        days_ahead: int = 30,
        min_sales: int = 5
    ) -> List[Dict]:
        """
        Generate forecasts for all products with sufficient sales history.
        """
        # Get products with minimum sales
        thirty_days_ago = date.today() - timedelta(days=90)

        products_query = select(
            OrderItem.product_id,
            func.sum(OrderItem.quantity).label('total_qty')
        ).join(
            Order, OrderItem.order_id == Order.id
        ).where(
            and_(
                Order.created_at >= thirty_days_ago,
                Order.status != OrderStatus.CANCELLED
            )
        ).group_by(
            OrderItem.product_id
        ).having(
            func.sum(OrderItem.quantity) >= min_sales
        )

        result = await self.db.execute(products_query)
        products = result.all()

        forecasts = []
        for p in products:
            try:
                forecast = await self.forecast_product_demand(
                    p.product_id,
                    days_ahead=days_ahead,
                    lookback_days=90
                )
                forecasts.append(forecast)
            except Exception:
                continue

        # Sort by stockout risk
        risk_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        forecasts.sort(key=lambda x: (risk_order.get(x["stockout_risk"], 3), x["days_until_stockout"]))

        return forecasts
