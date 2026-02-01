"""
AI-powered Insights Service

Statistical algorithms for predictive analytics:
- Revenue forecasting (linear regression, moving averages)
- Inventory recommendations (demand forecasting, stockout prediction)
- Customer intelligence (RFM segmentation, churn risk scoring)

No external AI APIs - all computations done locally.
"""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import List, Dict, Optional, Tuple
from uuid import UUID
import statistics
from collections import defaultdict

from sqlalchemy import select, func, and_, or_, desc, asc, extract
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.order import Order, OrderItem, OrderStatus
from app.models.product import Product
from app.models.category import Category
from app.models.customer import Customer
from app.models.inventory import StockItem, InventorySummary
from app.models.channel import SalesChannel


# ==================== Statistical Utility Functions ====================

def moving_average(data: List[float], window: int = 7) -> List[float]:
    """Calculate simple moving average for trend smoothing."""
    if len(data) < window:
        return data

    result = []
    for i in range(len(data)):
        if i < window - 1:
            result.append(sum(data[:i+1]) / (i+1))
        else:
            result.append(sum(data[i-window+1:i+1]) / window)
    return result


def linear_regression(x_values: List[float], y_values: List[float]) -> Tuple[float, float]:
    """
    Simple linear regression: y = mx + b
    Returns: (slope, intercept)
    """
    if len(x_values) != len(y_values) or len(x_values) < 2:
        return (0.0, 0.0)

    n = len(x_values)
    sum_x = sum(x_values)
    sum_y = sum(y_values)
    sum_xy = sum(x * y for x, y in zip(x_values, y_values))
    sum_x2 = sum(x ** 2 for x in x_values)

    denominator = n * sum_x2 - sum_x ** 2
    if denominator == 0:
        return (0.0, sum_y / n if n > 0 else 0.0)

    slope = (n * sum_xy - sum_x * sum_y) / denominator
    intercept = (sum_y - slope * sum_x) / n

    return (slope, intercept)


def exponential_smoothing(data: List[float], alpha: float = 0.3) -> List[float]:
    """Apply exponential smoothing for seasonal data."""
    if not data:
        return []

    result = [data[0]]
    for i in range(1, len(data)):
        smoothed = alpha * data[i] + (1 - alpha) * result[-1]
        result.append(smoothed)
    return result


def calculate_trend_direction(values: List[float]) -> Tuple[str, float]:
    """
    Calculate trend direction and percentage change.
    Returns: (direction, percentage)
    """
    if len(values) < 2:
        return ("STABLE", 0.0)

    # Compare last 7 days to previous 7 days
    recent = values[-7:] if len(values) >= 7 else values[-len(values)//2:]
    previous = values[-14:-7] if len(values) >= 14 else values[:len(values)//2]

    if not recent or not previous:
        return ("STABLE", 0.0)

    recent_avg = sum(recent) / len(recent)
    previous_avg = sum(previous) / len(previous)

    if previous_avg == 0:
        return ("UP" if recent_avg > 0 else "STABLE", 0.0)

    change = ((recent_avg - previous_avg) / previous_avg) * 100

    if change > 5:
        return ("UP", round(change, 1))
    elif change < -5:
        return ("DOWN", round(abs(change), 1))
    else:
        return ("STABLE", round(change, 1))


# Day-of-week seasonality factors (based on typical retail patterns)
DAY_SEASONALITY = {
    0: 0.85,   # Monday
    1: 0.90,   # Tuesday
    2: 0.95,   # Wednesday
    3: 1.00,   # Thursday
    4: 1.10,   # Friday
    5: 1.25,   # Saturday
    6: 1.20,   # Sunday
}


class InsightsService:
    """
    AI-powered insights service providing predictive analytics
    across sales, inventory, and customer domains.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    # ==================== SALES INSIGHTS ====================

    async def get_revenue_forecast(
        self,
        days_ahead: int = 30,
        lookback_days: int = 90
    ) -> Dict:
        """
        Forecast revenue using linear regression on historical data.
        """
        # Get historical daily revenue
        start_date = date.today() - timedelta(days=lookback_days)

        query = select(
            func.date(Order.created_at).label('order_date'),
            func.sum(Order.total_amount).label('revenue')
        ).where(
            and_(
                Order.created_at >= start_date,
                Order.status.in_([OrderStatus.DELIVERED, OrderStatus.SHIPPED, OrderStatus.CONFIRMED, OrderStatus.IN_TRANSIT])
            )
        ).group_by(
            func.date(Order.created_at)
        ).order_by(
            func.date(Order.created_at)
        )

        result = await self.db.execute(query)
        rows = result.all()

        # Build daily revenue map
        daily_revenue = {}
        for row in rows:
            daily_revenue[row.order_date] = float(row.revenue or 0)

        # Fill in missing days with 0
        all_dates = []
        all_values = []
        current = start_date
        while current <= date.today():
            all_dates.append(current)
            all_values.append(daily_revenue.get(current, 0))
            current += timedelta(days=1)

        # Apply moving average smoothing
        smoothed = moving_average(all_values, window=7)

        # Linear regression for trend
        x_values = list(range(len(smoothed)))
        slope, intercept = linear_regression(x_values, smoothed)

        # Generate predictions
        predictions = []
        for i in range(days_ahead):
            future_date = date.today() + timedelta(days=i+1)
            x = len(all_values) + i
            base_prediction = slope * x + intercept

            # Apply day-of-week seasonality
            day_factor = DAY_SEASONALITY.get(future_date.weekday(), 1.0)
            predicted = max(0, base_prediction * day_factor)

            # Confidence interval (±15%)
            lower = predicted * 0.85
            upper = predicted * 1.15

            predictions.append({
                "date": future_date.isoformat(),
                "predicted_value": round(predicted, 2),
                "lower_bound": round(lower, 2),
                "upper_bound": round(upper, 2)
            })

        # Calculate current month actual
        current_month_start = date.today().replace(day=1)
        current_month_revenue = sum(
            v for d, v in zip(all_dates, all_values)
            if d >= current_month_start
        )

        # Trend analysis
        direction, percentage = calculate_trend_direction(all_values)

        # Predicted totals
        next_30_total = sum(p["predicted_value"] for p in predictions[:30])

        return {
            "current_month_actual": round(current_month_revenue, 2),
            "current_month_predicted": round(next_30_total * 0.5, 2),  # Rough estimate
            "next_month_predicted": round(next_30_total, 2),
            "next_quarter_predicted": round(next_30_total * 3, 2),
            "trend_direction": direction,
            "trend_percentage": percentage,
            "confidence_score": 0.75,  # Fixed confidence for now
            "daily_predictions": predictions
        }

    async def get_sales_trends(self, lookback_days: int = 90) -> Dict:
        """
        Analyze sales patterns: daily averages, weekly patterns, peak hours.
        """
        start_date = date.today() - timedelta(days=lookback_days)

        # Daily orders with hour extraction
        query = select(
            func.date(Order.created_at).label('order_date'),
            extract('dow', Order.created_at).label('day_of_week'),
            extract('hour', Order.created_at).label('hour'),
            func.count(Order.id).label('order_count'),
            func.sum(Order.total_amount).label('revenue')
        ).where(
            and_(
                Order.created_at >= start_date,
                Order.status != OrderStatus.CANCELLED
            )
        ).group_by(
            func.date(Order.created_at),
            extract('dow', Order.created_at),
            extract('hour', Order.created_at)
        )

        result = await self.db.execute(query)
        rows = result.all()

        # Aggregate by day of week
        daily_revenue = defaultdict(list)
        hourly_orders = defaultdict(int)
        day_names = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']

        total_revenue = 0
        total_days = set()

        for row in rows:
            dow = int(row.day_of_week)
            daily_revenue[day_names[dow]].append(float(row.revenue or 0))
            hourly_orders[int(row.hour)] += row.order_count
            total_revenue += float(row.revenue or 0)
            total_days.add(row.order_date)

        # Calculate weekly pattern (relative to average)
        weekly_pattern = {}
        avg_daily = total_revenue / len(total_days) if total_days else 0

        for day_name in day_names:
            day_avg = sum(daily_revenue[day_name]) / len(daily_revenue[day_name]) if daily_revenue[day_name] else 0
            weekly_pattern[day_name] = round(day_avg / avg_daily, 2) if avg_daily > 0 else 1.0

        # Peak hours (top 4)
        sorted_hours = sorted(hourly_orders.items(), key=lambda x: x[1], reverse=True)
        peak_hours = [h for h, _ in sorted_hours[:4]]

        # Best days
        best_days = sorted(weekly_pattern.items(), key=lambda x: x[1], reverse=True)[:3]

        # Monthly growth
        mid_date = start_date + timedelta(days=lookback_days // 2)
        first_half = sum(
            r for d, r in [(row.order_date, float(row.revenue or 0)) for row in rows]
            if d < mid_date
        )
        second_half = sum(
            r for d, r in [(row.order_date, float(row.revenue or 0)) for row in rows]
            if d >= mid_date
        )

        monthly_growth = ((second_half - first_half) / first_half * 100) if first_half > 0 else 0

        return {
            "daily_average": round(avg_daily, 2),
            "weekly_pattern": weekly_pattern,
            "monthly_growth": round(monthly_growth, 1),
            "peak_hours": peak_hours,
            "best_days": [d for d, _ in best_days],
            "seasonality_index": DAY_SEASONALITY
        }

    async def get_top_performers(self, period_days: int = 30, limit: int = 10) -> Dict:
        """
        Identify best and worst performing products/categories/channels.
        """
        start_date = date.today() - timedelta(days=period_days)
        prev_start = start_date - timedelta(days=period_days)

        # Top products by revenue
        product_query = select(
            Product.id,
            Product.name,
            Product.sku,
            func.sum(OrderItem.total_price).label('revenue'),
            func.sum(OrderItem.quantity).label('quantity')
        ).join(
            OrderItem, Product.id == OrderItem.product_id
        ).join(
            Order, OrderItem.order_id == Order.id
        ).where(
            and_(
                Order.created_at >= start_date,
                Order.status != OrderStatus.CANCELLED
            )
        ).group_by(
            Product.id, Product.name, Product.sku
        ).order_by(
            desc(func.sum(OrderItem.total_price))
        ).limit(limit)

        result = await self.db.execute(product_query)
        top_products = [
            {
                "id": str(r.id),
                "name": r.name,
                "sku": r.sku,
                "revenue": float(r.revenue or 0),
                "quantity": r.quantity or 0
            }
            for r in result.all()
        ]

        # Top categories
        category_query = select(
            Category.id,
            Category.name,
            func.sum(OrderItem.total_price).label('revenue')
        ).join(
            Product, Category.id == Product.category_id
        ).join(
            OrderItem, Product.id == OrderItem.product_id
        ).join(
            Order, OrderItem.order_id == Order.id
        ).where(
            and_(
                Order.created_at >= start_date,
                Order.status != OrderStatus.CANCELLED
            )
        ).group_by(
            Category.id, Category.name
        ).order_by(
            desc(func.sum(OrderItem.total_price))
        ).limit(5)

        result = await self.db.execute(category_query)
        top_categories = [
            {
                "id": str(r.id),
                "name": r.name,
                "revenue": float(r.revenue or 0)
            }
            for r in result.all()
        ]

        # Top channels
        channel_query = select(
            Order.source.label('channel'),
            func.sum(Order.total_amount).label('revenue'),
            func.count(Order.id).label('order_count')
        ).where(
            and_(
                Order.created_at >= start_date,
                Order.status != OrderStatus.CANCELLED
            )
        ).group_by(
            Order.source
        ).order_by(
            desc(func.sum(Order.total_amount))
        ).limit(5)

        result = await self.db.execute(channel_query)
        top_channels = [
            {
                "channel": r.channel or "Direct",
                "revenue": float(r.revenue or 0),
                "order_count": r.order_count or 0
            }
            for r in result.all()
        ]

        return {
            "top_products": top_products,
            "top_categories": top_categories,
            "top_channels": top_channels,
            "fastest_growing": [],  # Would need previous period comparison
            "declining": []
        }

    async def get_order_predictions(self, days_ahead: int = 7) -> Dict:
        """
        Predict order volumes for upcoming days.
        """
        # Get last 30 days of orders
        start_date = date.today() - timedelta(days=30)

        query = select(
            func.date(Order.created_at).label('order_date'),
            func.count(Order.id).label('order_count')
        ).where(
            and_(
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

        # Build daily order counts
        daily_orders = {}
        for row in rows:
            daily_orders[row.order_date] = row.order_count

        # Fill missing days
        all_counts = []
        current = start_date
        while current <= date.today():
            all_counts.append(daily_orders.get(current, 0))
            current += timedelta(days=1)

        # Linear regression
        x_values = list(range(len(all_counts)))
        slope, intercept = linear_regression(x_values, [float(c) for c in all_counts])

        # Generate predictions
        predictions = []
        total_predicted = 0

        for i in range(days_ahead):
            future_date = date.today() + timedelta(days=i+1)
            x = len(all_counts) + i
            base_prediction = slope * x + intercept

            # Apply seasonality
            day_factor = DAY_SEASONALITY.get(future_date.weekday(), 1.0)
            predicted = max(0, int(base_prediction * day_factor))
            total_predicted += predicted

            predictions.append({
                "date": future_date.isoformat(),
                "predicted_orders": predicted
            })

        return {
            "daily_predictions": predictions,
            "expected_total": total_predicted,
            "confidence": 0.7
        }

    # ==================== INVENTORY INSIGHTS ====================

    async def get_reorder_recommendations(self, limit: int = 20) -> List[Dict]:
        """
        Generate smart reorder recommendations based on stock levels and velocity.
        """
        # Get products with low stock and their sales velocity
        thirty_days_ago = date.today() - timedelta(days=30)

        # Calculate sales velocity per product
        velocity_query = select(
            OrderItem.product_id,
            func.sum(OrderItem.quantity).label('total_sold')
        ).join(
            Order, OrderItem.order_id == Order.id
        ).where(
            and_(
                Order.created_at >= thirty_days_ago,
                Order.status != OrderStatus.CANCELLED
            )
        ).group_by(
            OrderItem.product_id
        )

        result = await self.db.execute(velocity_query)
        velocity_map = {str(r.product_id): r.total_sold / 30.0 for r in result.all()}

        # Get current stock levels
        stock_query = select(
            InventorySummary.product_id,
            InventorySummary.available_quantity,
            InventorySummary.reorder_level,
            Product.name,
            Product.sku,
            Product.mrp
        ).join(
            Product, InventorySummary.product_id == Product.id
        ).where(
            Product.is_active == True
        )

        result = await self.db.execute(stock_query)
        rows = result.all()

        recommendations = []
        for row in rows:
            product_id = str(row.product_id)
            current_stock = row.available_quantity or 0
            reorder_level = row.reorder_level or 10
            daily_velocity = velocity_map.get(product_id, 0.1)  # Default low velocity

            # Calculate days until stockout
            days_until_stockout = int(current_stock / daily_velocity) if daily_velocity > 0 else 999

            # Determine urgency
            if days_until_stockout <= 3:
                urgency = "CRITICAL"
            elif days_until_stockout <= 7:
                urgency = "HIGH"
            elif days_until_stockout <= 14:
                urgency = "MEDIUM"
            else:
                urgency = "LOW"

            # Only include items that need reorder
            if current_stock <= reorder_level or days_until_stockout <= 14:
                # Calculate recommended quantity (30-day supply + safety stock)
                recommended_qty = max(
                    int(daily_velocity * 30 + daily_velocity * 7 - current_stock),
                    reorder_level
                )

                recommendations.append({
                    "product_id": product_id,
                    "product_name": row.name,
                    "sku": row.sku,
                    "current_stock": current_stock,
                    "reorder_level": reorder_level,
                    "recommended_qty": recommended_qty,
                    "urgency": urgency,
                    "days_until_stockout": days_until_stockout,
                    "daily_velocity": round(daily_velocity, 2),
                    "estimated_cost": float(row.mrp or 0) * recommended_qty
                })

        # Sort by urgency
        urgency_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        recommendations.sort(key=lambda x: (urgency_order.get(x["urgency"], 4), x["days_until_stockout"]))

        return recommendations[:limit]

    async def get_stockout_risks(self, limit: int = 20) -> List[Dict]:
        """
        Identify products at immediate risk of stockout.
        """
        recommendations = await self.get_reorder_recommendations(limit=50)

        # Filter to only critical and high urgency
        risks = [
            {
                "product_id": r["product_id"],
                "product_name": r["product_name"],
                "sku": r["sku"],
                "current_stock": r["current_stock"],
                "reserved_stock": 0,  # Would need to calculate from orders
                "daily_velocity": r["daily_velocity"],
                "days_until_stockout": r["days_until_stockout"],
                "risk_level": r["urgency"],
                "potential_revenue_loss": r["estimated_cost"],
                "pending_orders": 0
            }
            for r in recommendations
            if r["urgency"] in ["CRITICAL", "HIGH"]
        ]

        return risks[:limit]

    async def get_slow_moving_inventory(self, days_threshold: int = 60, limit: int = 20) -> List[Dict]:
        """
        Identify slow-moving or dead stock.
        """
        cutoff_date = date.today() - timedelta(days=days_threshold)

        # Get last sale date per product
        last_sale_query = select(
            OrderItem.product_id,
            func.max(Order.created_at).label('last_sale_date')
        ).join(
            Order, OrderItem.order_id == Order.id
        ).where(
            Order.status != OrderStatus.CANCELLED
        ).group_by(
            OrderItem.product_id
        )

        result = await self.db.execute(last_sale_query)
        last_sale_map = {str(r.product_id): r.last_sale_date for r in result.all()}

        # Get products with stock
        stock_query = select(
            InventorySummary.product_id,
            InventorySummary.available_quantity,
            InventorySummary.total_value,
            Product.name,
            Product.sku,
            Product.mrp
        ).join(
            Product, InventorySummary.product_id == Product.id
        ).where(
            and_(
                Product.is_active == True,
                InventorySummary.available_quantity > 0
            )
        )

        result = await self.db.execute(stock_query)
        rows = result.all()

        slow_movers = []
        for row in rows:
            product_id = str(row.product_id)
            last_sale = last_sale_map.get(product_id)

            if last_sale:
                days_since_sale = (datetime.now(timezone.utc) - last_sale).days
            else:
                days_since_sale = 365  # Never sold

            if days_since_sale >= days_threshold:
                stock_value = float(row.mrp or 0) * (row.available_quantity or 0)

                # Recommendation based on age
                if days_since_sale > 180:
                    recommendation = "WRITE_OFF"
                elif days_since_sale > 120:
                    recommendation = "HEAVY_DISCOUNT"
                elif days_since_sale > 90:
                    recommendation = "DISCOUNT"
                else:
                    recommendation = "PROMOTION"

                slow_movers.append({
                    "product_id": product_id,
                    "product_name": row.name,
                    "sku": row.sku,
                    "current_stock": row.available_quantity,
                    "days_since_last_sale": days_since_sale,
                    "stock_value": round(stock_value, 2),
                    "recommendation": recommendation
                })

        # Sort by stock value (highest first)
        slow_movers.sort(key=lambda x: x["stock_value"], reverse=True)

        return slow_movers[:limit]

    # ==================== CUSTOMER INSIGHTS ====================

    async def get_customer_rfm_data(self) -> List[Dict]:
        """
        Calculate RFM (Recency, Frequency, Monetary) scores for all customers.
        """
        # Get customer order summary
        query = select(
            Customer.id,
            Customer.name,
            Customer.email,
            Customer.phone,
            func.max(Order.created_at).label('last_order_date'),
            func.count(Order.id).label('order_count'),
            func.sum(Order.total_amount).label('total_spent')
        ).join(
            Order, Customer.id == Order.customer_id
        ).where(
            Order.status != OrderStatus.CANCELLED
        ).group_by(
            Customer.id, Customer.name, Customer.email, Customer.phone
        )

        result = await self.db.execute(query)
        rows = result.all()

        if not rows:
            return []

        # Calculate RFM scores
        customers_data = []
        for row in rows:
            days_since_order = (datetime.now(timezone.utc) - row.last_order_date).days if row.last_order_date else 365

            customers_data.append({
                "id": str(row.id),
                "name": row.name,
                "email": row.email,
                "phone": row.phone,
                "days_since_last_order": days_since_order,
                "order_count": row.order_count,
                "total_spent": float(row.total_spent or 0)
            })

        # Calculate percentiles for scoring
        all_recency = [c["days_since_last_order"] for c in customers_data]
        all_frequency = [c["order_count"] for c in customers_data]
        all_monetary = [c["total_spent"] for c in customers_data]

        def get_percentile_score(value: float, values: List[float], reverse: bool = False) -> int:
            """Get score 1-5 based on percentile."""
            sorted_vals = sorted(values, reverse=reverse)
            if not sorted_vals:
                return 3

            position = sum(1 for v in sorted_vals if v <= value) / len(sorted_vals)
            return min(5, max(1, int(position * 5) + 1))

        for customer in customers_data:
            # Recency: lower days = higher score
            customer["r_score"] = 6 - get_percentile_score(
                customer["days_since_last_order"], all_recency
            )
            # Frequency: higher = higher score
            customer["f_score"] = get_percentile_score(
                customer["order_count"], all_frequency
            )
            # Monetary: higher = higher score
            customer["m_score"] = get_percentile_score(
                customer["total_spent"], all_monetary
            )

            # Combined RFM score
            customer["rfm_score"] = customer["r_score"] + customer["f_score"] + customer["m_score"]

        return customers_data

    async def get_churn_risk_customers(
        self,
        threshold: float = 0.6,
        limit: int = 20
    ) -> List[Dict]:
        """
        Identify customers at high risk of churning.
        """
        customers = await self.get_customer_rfm_data()

        at_risk = []
        for customer in customers:
            # Churn risk scoring
            recency_risk = 0
            if customer["days_since_last_order"] > 90:
                recency_risk = 40
            elif customer["days_since_last_order"] > 60:
                recency_risk = 25
            elif customer["days_since_last_order"] > 30:
                recency_risk = 10

            frequency_risk = 0
            if customer["order_count"] <= 1:
                frequency_risk = 30
            elif customer["order_count"] <= 3:
                frequency_risk = 20
            elif customer["order_count"] <= 6:
                frequency_risk = 10

            monetary_risk = 30 - (customer["m_score"] * 6)  # Lower monetary = higher risk

            risk_score = (recency_risk + frequency_risk + monetary_risk) / 100.0

            if risk_score >= threshold:
                # Determine recommended action
                if risk_score >= 0.8:
                    action = "URGENT_CALL"
                elif risk_score >= 0.7:
                    action = "PERSONAL_EMAIL"
                elif risk_score >= 0.6:
                    action = "SPECIAL_OFFER"
                else:
                    action = "LOYALTY_PROGRAM"

                avg_order_value = customer["total_spent"] / customer["order_count"] if customer["order_count"] > 0 else 0

                at_risk.append({
                    "customer_id": customer["id"],
                    "customer_name": customer["name"],
                    "email": customer["email"],
                    "phone": customer["phone"],
                    "risk_score": round(risk_score, 2),
                    "days_since_last_order": customer["days_since_last_order"],
                    "total_orders": customer["order_count"],
                    "total_spent": customer["total_spent"],
                    "avg_order_value": round(avg_order_value, 2),
                    "recommended_action": action
                })

        # Sort by risk score
        at_risk.sort(key=lambda x: x["risk_score"], reverse=True)

        return at_risk[:limit]

    async def get_customer_segments(self) -> Dict:
        """
        Segment customers using RFM analysis.
        """
        customers = await self.get_customer_rfm_data()

        if not customers:
            return self._empty_segments()

        segments = {
            "champions": {"customers": [], "description": "Best customers - high RFM scores"},
            "loyal_customers": {"customers": [], "description": "Frequent buyers"},
            "potential_loyalists": {"customers": [], "description": "Recent with good frequency"},
            "new_customers": {"customers": [], "description": "Recent first-time buyers"},
            "at_risk": {"customers": [], "description": "Haven't ordered recently"},
            "hibernating": {"customers": [], "description": "Long time no order"},
            "lost": {"customers": [], "description": "No activity for very long"}
        }

        for customer in customers:
            r, f, m = customer["r_score"], customer["f_score"], customer["m_score"]

            if r >= 4 and f >= 4 and m >= 4:
                segments["champions"]["customers"].append(customer)
            elif f >= 4:
                segments["loyal_customers"]["customers"].append(customer)
            elif r >= 4 and f >= 2:
                segments["potential_loyalists"]["customers"].append(customer)
            elif r >= 4 and f == 1:
                segments["new_customers"]["customers"].append(customer)
            elif r <= 2 and f >= 2:
                segments["at_risk"]["customers"].append(customer)
            elif r <= 2 and f <= 2 and customer["days_since_last_order"] < 180:
                segments["hibernating"]["customers"].append(customer)
            else:
                segments["lost"]["customers"].append(customer)

        # Calculate segment stats
        total_customers = len(customers)
        result = {"total_customers": total_customers}

        for segment_name, segment_data in segments.items():
            segment_customers = segment_data["customers"]
            count = len(segment_customers)

            result[segment_name] = {
                "segment_name": segment_name.replace("_", " ").title(),
                "description": segment_data["description"],
                "customer_count": count,
                "percentage": round((count / total_customers) * 100, 1) if total_customers > 0 else 0,
                "avg_order_value": round(
                    sum(c["total_spent"] / c["order_count"] for c in segment_customers if c["order_count"] > 0) / count, 2
                ) if count > 0 else 0,
                "total_revenue": round(sum(c["total_spent"] for c in segment_customers), 2),
                "characteristics": self._get_segment_characteristics(segment_name)
            }

        return result

    def _empty_segments(self) -> Dict:
        """Return empty segment structure."""
        segment_template = {
            "segment_name": "",
            "description": "",
            "customer_count": 0,
            "percentage": 0,
            "avg_order_value": 0,
            "total_revenue": 0,
            "characteristics": []
        }
        return {
            "total_customers": 0,
            "champions": {**segment_template, "segment_name": "Champions"},
            "loyal_customers": {**segment_template, "segment_name": "Loyal Customers"},
            "potential_loyalists": {**segment_template, "segment_name": "Potential Loyalists"},
            "new_customers": {**segment_template, "segment_name": "New Customers"},
            "at_risk": {**segment_template, "segment_name": "At Risk"},
            "hibernating": {**segment_template, "segment_name": "Hibernating"},
            "lost": {**segment_template, "segment_name": "Lost"}
        }

    def _get_segment_characteristics(self, segment: str) -> List[str]:
        """Get characteristics for each segment."""
        characteristics = {
            "champions": ["Highest spenders", "Most frequent buyers", "Recent purchases"],
            "loyal_customers": ["Regular buyers", "Good spending pattern", "Brand advocates"],
            "potential_loyalists": ["Recent activity", "Growing frequency", "Upsell potential"],
            "new_customers": ["First-time buyers", "Need nurturing", "High potential"],
            "at_risk": ["Declining activity", "Need re-engagement", "Win-back campaigns"],
            "hibernating": ["Inactive for months", "Need reactivation", "Special offers"],
            "lost": ["Very long inactive", "May need removal", "Last attempt offers"]
        }
        return characteristics.get(segment, [])

    async def get_high_value_customers(self, limit: int = 20) -> List[Dict]:
        """
        Get top customers by total spend and predicted lifetime value.
        """
        customers = await self.get_customer_rfm_data()

        # Calculate CLV (simplified: avg order value * predicted orders per year)
        for customer in customers:
            orders_per_year = (customer["order_count"] /
                              max(1, customer["days_since_last_order"] / 365) * 365 /
                              max(1, customer["days_since_last_order"]))
            orders_per_year = min(orders_per_year, 52)  # Cap at weekly

            avg_order = customer["total_spent"] / customer["order_count"] if customer["order_count"] > 0 else 0
            customer["predicted_annual_value"] = round(avg_order * orders_per_year, 2)
            customer["predicted_lifetime_value"] = round(customer["predicted_annual_value"] * 3, 2)  # 3 year CLV

            # Assign segment based on RFM
            if customer["rfm_score"] >= 12:
                customer["segment"] = "Champion"
            elif customer["rfm_score"] >= 9:
                customer["segment"] = "Loyal"
            elif customer["rfm_score"] >= 6:
                customer["segment"] = "Potential"
            else:
                customer["segment"] = "At Risk"

        # Sort by total spent
        customers.sort(key=lambda x: x["total_spent"], reverse=True)

        return [
            {
                "customer_id": c["id"],
                "customer_name": c["name"],
                "email": c["email"],
                "total_orders": c["order_count"],
                "total_spent": c["total_spent"],
                "predicted_clv": c["predicted_lifetime_value"],
                "segment": c["segment"]
            }
            for c in customers[:limit]
        ]

    # ==================== DASHBOARD SUMMARY ====================

    async def get_insights_dashboard(self) -> Dict:
        """
        Get aggregated insights dashboard data.
        """
        # Get all insights in parallel-ish manner
        revenue_forecast = await self.get_revenue_forecast(days_ahead=30)
        order_predictions = await self.get_order_predictions(days_ahead=7)
        stockout_risks = await self.get_stockout_risks(limit=10)
        reorder_items = await self.get_reorder_recommendations(limit=10)
        churn_customers = await self.get_churn_risk_customers(threshold=0.6, limit=10)
        slow_moving = await self.get_slow_moving_inventory(limit=10)
        segments = await self.get_customer_segments()

        # Calculate alerts
        critical_stockouts = len([r for r in stockout_risks if r["risk_level"] == "CRITICAL"])
        reorder_needed = len(reorder_items)
        high_churn = len(churn_customers)
        slow_moving_value = sum(s["stock_value"] for s in slow_moving)

        # Generate insight messages
        trend = revenue_forecast["trend_direction"]
        trend_pct = revenue_forecast["trend_percentage"]

        if trend == "UP":
            sales_insight = f"Revenue up {trend_pct}% from last period"
        elif trend == "DOWN":
            sales_insight = f"Revenue down {trend_pct}% - needs attention"
        else:
            sales_insight = "Revenue stable, consider growth initiatives"

        inventory_insight = f"{reorder_needed} products need reorder" if reorder_needed > 0 else "Inventory levels optimal"
        customer_insight = f"{high_churn} high-value customers at risk" if high_churn > 0 else "Customer retention looking good"

        return {
            "revenue_trend": f"{trend} {trend_pct}%",
            "predicted_monthly_revenue": revenue_forecast["next_month_predicted"],
            "order_trend": f"Expected {order_predictions['expected_total']} orders this week",
            "predicted_monthly_orders": order_predictions["expected_total"] * 4,

            "critical_stockouts": critical_stockouts,
            "reorder_needed": reorder_needed,
            "high_churn_risk": high_churn,
            "slow_moving_value": round(slow_moving_value, 2),

            "top_insight_sales": sales_insight,
            "top_insight_inventory": inventory_insight,
            "top_insight_customers": customer_insight,

            "revenue_forecast_chart": revenue_forecast["daily_predictions"][:14],
            "order_forecast_chart": order_predictions["daily_predictions"],
            "customer_segments_chart": [
                {"name": k.replace("_", " ").title(), "value": v["customer_count"]}
                for k, v in segments.items()
                if k != "total_customers" and isinstance(v, dict)
            ],
            "stockout_timeline": [
                {"product": r["product_name"], "days": r["days_until_stockout"]}
                for r in stockout_risks[:5]
            ]
        }
