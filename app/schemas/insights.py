"""Schemas for AI-powered Insights module."""

from datetime import date
from decimal import Decimal
from typing import List, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.base import BaseResponseSchema


# ==================== Common Models ====================

class DailyPrediction(BaseModel):
    """Daily prediction with confidence bounds."""
    date: str
    predicted_value: float
    lower_bound: float
    upper_bound: float


class OrderPrediction(BaseModel):
    """Daily order count prediction."""
    date: str
    predicted_orders: int


# ==================== Sales Insights ====================

class RevenueForecast(BaseModel):
    """Revenue forecast response."""
    current_month_actual: float
    current_month_predicted: float
    next_month_predicted: float
    next_quarter_predicted: float
    trend_direction: str = Field(description="UP, DOWN, or STABLE")
    trend_percentage: float
    confidence_score: float = Field(ge=0, le=1)
    daily_predictions: List[DailyPrediction]


class SalesTrends(BaseModel):
    """Sales trend analysis response."""
    daily_average: float
    weekly_pattern: Dict[str, float]
    monthly_growth: float
    peak_hours: List[int]
    best_days: List[str]
    seasonality_index: Dict[int, float]


class ProductPerformance(BaseModel):
    """Product performance data."""
    id: str
    name: str
    sku: str
    revenue: float
    quantity: int


class CategoryPerformance(BaseModel):
    """Category performance data."""
    id: str
    name: str
    revenue: float


class ChannelPerformance(BaseModel):
    """Channel performance data."""
    channel: str
    revenue: float
    order_count: int


class GrowthItem(BaseModel):
    """Item with growth rate."""
    id: str
    name: str
    growth_rate: float


class TopPerformers(BaseModel):
    """Top performers response."""
    top_products: List[ProductPerformance]
    top_categories: List[CategoryPerformance]
    top_channels: List[ChannelPerformance]
    fastest_growing: List[GrowthItem]
    declining: List[GrowthItem]


class OrderPredictions(BaseModel):
    """Order volume predictions response."""
    daily_predictions: List[OrderPrediction]
    expected_total: int
    confidence: float


# ==================== Inventory Insights ====================

class ReorderRecommendation(BaseModel):
    """Reorder recommendation item."""
    product_id: str
    product_name: str
    sku: str
    current_stock: int
    reorder_level: int
    recommended_qty: int
    urgency: str = Field(description="CRITICAL, HIGH, MEDIUM, LOW")
    days_until_stockout: int
    daily_velocity: float
    vendor_id: Optional[str] = None
    vendor_name: Optional[str] = None
    estimated_cost: float


class StockoutRisk(BaseModel):
    """Stockout risk item."""
    product_id: str
    product_name: str
    sku: str
    current_stock: int
    reserved_stock: int
    daily_velocity: float
    days_until_stockout: int
    risk_level: str = Field(description="CRITICAL, HIGH, MEDIUM")
    potential_revenue_loss: float
    pending_orders: int


class SlowMovingItem(BaseModel):
    """Slow-moving inventory item."""
    product_id: str
    product_name: str
    sku: str
    current_stock: int
    days_since_last_sale: int
    stock_value: float
    recommendation: str = Field(description="WRITE_OFF, HEAVY_DISCOUNT, DISCOUNT, PROMOTION")


class DemandForecast(BaseModel):
    """Product demand forecast."""
    product_id: str
    product_name: str
    daily_predictions: List[OrderPrediction]
    total_predicted: int
    seasonal_factor: float


# ==================== Customer Insights ====================

class ChurnRiskCustomer(BaseModel):
    """Customer at risk of churning."""
    customer_id: str
    customer_name: str
    email: Optional[str]
    phone: Optional[str]
    risk_score: float = Field(ge=0, le=1)
    days_since_last_order: int
    total_orders: int
    total_spent: float
    avg_order_value: float
    recommended_action: str = Field(
        description="URGENT_CALL, PERSONAL_EMAIL, SPECIAL_OFFER, LOYALTY_PROGRAM"
    )


class CustomerSegment(BaseModel):
    """Customer segment data."""
    segment_name: str
    description: str
    customer_count: int
    percentage: float
    avg_order_value: float
    total_revenue: float
    characteristics: List[str]


class CustomerSegments(BaseModel):
    """All customer segments."""
    total_customers: int
    champions: CustomerSegment
    loyal_customers: CustomerSegment
    potential_loyalists: CustomerSegment
    new_customers: CustomerSegment
    at_risk: CustomerSegment
    hibernating: CustomerSegment
    lost: CustomerSegment


class HighValueCustomer(BaseModel):
    """High value customer data."""
    customer_id: str
    customer_name: str
    email: Optional[str]
    total_orders: int
    total_spent: float
    predicted_clv: float
    segment: str


class CustomerCLV(BaseModel):
    """Customer lifetime value."""
    customer_id: str
    customer_name: str
    historical_value: float
    predicted_annual: float
    predicted_lifetime: float
    segment: str


# ==================== Dashboard Summary ====================

class SegmentChart(BaseModel):
    """Segment chart data point."""
    name: str
    value: int


class StockoutTimeline(BaseModel):
    """Stockout timeline item."""
    product: str
    days: int


class InsightsDashboard(BaseModel):
    """Complete insights dashboard response."""
    # Summary KPIs
    revenue_trend: str
    predicted_monthly_revenue: float
    order_trend: str
    predicted_monthly_orders: int

    # Alerts
    critical_stockouts: int
    reorder_needed: int
    high_churn_risk: int
    slow_moving_value: float

    # Top Insights
    top_insight_sales: str
    top_insight_inventory: str
    top_insight_customers: str

    # Charts Data
    revenue_forecast_chart: List[DailyPrediction]
    order_forecast_chart: List[OrderPrediction]
    customer_segments_chart: List[SegmentChart]
    stockout_timeline: List[StockoutTimeline]


# ==================== List Responses ====================

class ReorderListResponse(BaseModel):
    """Paginated reorder recommendations."""
    items: List[ReorderRecommendation]
    total: int


class StockoutRiskListResponse(BaseModel):
    """Paginated stockout risks."""
    items: List[StockoutRisk]
    total: int


class SlowMovingListResponse(BaseModel):
    """Paginated slow-moving inventory."""
    items: List[SlowMovingItem]
    total: int


class ChurnRiskListResponse(BaseModel):
    """Paginated churn risk customers."""
    items: List[ChurnRiskCustomer]
    total: int


class HighValueCustomerListResponse(BaseModel):
    """Paginated high value customers."""
    items: List[HighValueCustomer]
    total: int
