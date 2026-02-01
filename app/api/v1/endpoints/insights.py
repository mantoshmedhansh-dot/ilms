"""
AI-powered Insights API endpoints.

Provides predictive analytics for:
- Sales forecasting and trends
- Inventory recommendations
- Customer intelligence
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.insights_service import InsightsService
from app.schemas.insights import (

    RevenueForecast,
    SalesTrends,
    TopPerformers,
    OrderPredictions,
    ReorderRecommendation,
    StockoutRisk,
    SlowMovingItem,
    DemandForecast,
    ChurnRiskCustomer,
    CustomerSegments,
    HighValueCustomer,
    CustomerCLV,
    InsightsDashboard,
    ReorderListResponse,
    StockoutRiskListResponse,
    SlowMovingListResponse,
    ChurnRiskListResponse,
    HighValueCustomerListResponse,
)
from app.core.module_decorators import require_module

router = APIRouter()


# ==================== Dashboard ====================

@router.get("/dashboard", response_model=InsightsDashboard)
@require_module("scm_ai")
async def get_insights_dashboard(
    db: AsyncSession = Depends(get_db)
):
    """
    Get aggregated AI insights dashboard data.

    Returns all key metrics, alerts, and chart data for the insights overview.
    """
    service = InsightsService(db)
    return await service.get_insights_dashboard()


# ==================== Sales Insights ====================

@router.get("/sales/revenue-forecast", response_model=RevenueForecast)
@require_module("scm_ai")
async def get_revenue_forecast(
    days_ahead: int = Query(30, ge=1, le=90, description="Days to forecast"),
    lookback_days: int = Query(90, ge=30, le=365, description="Historical days to analyze"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get revenue forecast using linear regression on historical data.

    - Analyzes past revenue patterns
    - Applies day-of-week seasonality
    - Returns predictions with confidence intervals
    """
    service = InsightsService(db)
    return await service.get_revenue_forecast(days_ahead, lookback_days)


@router.get("/sales/trends", response_model=SalesTrends)
@require_module("scm_ai")
async def get_sales_trends(
    lookback_days: int = Query(90, ge=30, le=365, description="Days to analyze"),
    db: AsyncSession = Depends(get_db)
):
    """
    Analyze sales patterns and trends.

    Returns:
    - Daily averages
    - Weekly patterns (which days perform best)
    - Peak hours
    - Monthly growth rate
    """
    service = InsightsService(db)
    return await service.get_sales_trends(lookback_days)


@router.get("/sales/top-performers", response_model=TopPerformers)
@require_module("scm_ai")
async def get_top_performers(
    period_days: int = Query(30, ge=7, le=365, description="Period to analyze"),
    limit: int = Query(10, ge=1, le=50, description="Number of items per category"),
    db: AsyncSession = Depends(get_db)
):
    """
    Identify top performing products, categories, and channels.

    Also identifies fastest growing and declining items.
    """
    service = InsightsService(db)
    return await service.get_top_performers(period_days, limit)


@router.get("/sales/order-predictions", response_model=OrderPredictions)
@require_module("scm_ai")
async def get_order_predictions(
    days_ahead: int = Query(7, ge=1, le=30, description="Days to predict"),
    db: AsyncSession = Depends(get_db)
):
    """
    Predict order volumes for upcoming days.

    Uses historical patterns and seasonality to forecast daily order counts.
    """
    service = InsightsService(db)
    return await service.get_order_predictions(days_ahead)


# ==================== Inventory Insights ====================

@router.get("/inventory/reorder", response_model=ReorderListResponse)
@require_module("scm_ai")
async def get_reorder_recommendations(
    limit: int = Query(20, ge=1, le=100, description="Maximum items to return"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get smart reorder recommendations.

    Analyzes:
    - Current stock levels
    - Historical sales velocity
    - Days until stockout
    - Urgency (CRITICAL, HIGH, MEDIUM, LOW)
    """
    service = InsightsService(db)
    items = await service.get_reorder_recommendations(limit)
    return ReorderListResponse(items=items, total=len(items))


@router.get("/inventory/stockout-risks", response_model=StockoutRiskListResponse)
@require_module("scm_ai")
async def get_stockout_risks(
    limit: int = Query(20, ge=1, le=100, description="Maximum items to return"),
    db: AsyncSession = Depends(get_db)
):
    """
    Identify products at immediate risk of stockout.

    Returns products with CRITICAL or HIGH urgency that need immediate attention.
    """
    service = InsightsService(db)
    items = await service.get_stockout_risks(limit)
    return StockoutRiskListResponse(items=items, total=len(items))


@router.get("/inventory/slow-moving", response_model=SlowMovingListResponse)
@require_module("scm_ai")
async def get_slow_moving_inventory(
    days_threshold: int = Query(60, ge=30, le=365, description="Days since last sale"),
    limit: int = Query(20, ge=1, le=100, description="Maximum items to return"),
    db: AsyncSession = Depends(get_db)
):
    """
    Identify slow-moving or dead stock.

    Returns products not sold within the threshold period with recommendations:
    - WRITE_OFF: >180 days
    - HEAVY_DISCOUNT: >120 days
    - DISCOUNT: >90 days
    - PROMOTION: >60 days
    """
    service = InsightsService(db)
    items = await service.get_slow_moving_inventory(days_threshold, limit)
    return SlowMovingListResponse(items=items, total=len(items))


# ==================== Customer Insights ====================

@router.get("/customers/churn-risk", response_model=ChurnRiskListResponse)
@require_module("scm_ai")
async def get_churn_risk_customers(
    threshold: float = Query(0.6, ge=0, le=1, description="Minimum risk score"),
    limit: int = Query(20, ge=1, le=100, description="Maximum items to return"),
    db: AsyncSession = Depends(get_db)
):
    """
    Identify customers at high risk of churning.

    Uses RFM-based scoring:
    - Recency: Days since last order
    - Frequency: Order count
    - Monetary: Total spend

    Returns recommended actions for each customer.
    """
    service = InsightsService(db)
    items = await service.get_churn_risk_customers(threshold, limit)
    return ChurnRiskListResponse(items=items, total=len(items))


@router.get("/customers/segments", response_model=CustomerSegments)
@require_module("scm_ai")
async def get_customer_segments(
    db: AsyncSession = Depends(get_db)
):
    """
    Get customer segmentation based on RFM analysis.

    Segments:
    - Champions: Best customers (high RFM)
    - Loyal Customers: Frequent buyers
    - Potential Loyalists: Recent with good frequency
    - New Customers: First-time buyers
    - At Risk: Declining activity
    - Hibernating: Long time no order
    - Lost: Very long inactive
    """
    service = InsightsService(db)
    return await service.get_customer_segments()


@router.get("/customers/high-value", response_model=HighValueCustomerListResponse)
@require_module("scm_ai")
async def get_high_value_customers(
    limit: int = Query(20, ge=1, le=100, description="Maximum items to return"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get top customers by total spend and predicted lifetime value (CLV).
    """
    service = InsightsService(db)
    items = await service.get_high_value_customers(limit)
    return HighValueCustomerListResponse(items=items, total=len(items))
