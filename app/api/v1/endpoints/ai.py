"""
AI-powered API endpoints.

Provides AI capabilities:
- Demand Forecasting
- Payment Prediction
- Predictive Maintenance
- Natural Language Chatbot
"""

from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.ai import ChatQuery, ForecastRequest
from app.services.ai.demand_forecasting import DemandForecastingService
from app.services.ai.payment_prediction import PaymentPredictionService
from app.services.ai.predictive_maintenance import PredictiveMaintenanceService
from app.services.ai.chatbot import ERPChatbotService
from app.core.module_decorators import require_module

router = APIRouter()


# ==================== AI Dashboard ====================

@router.get("/dashboard")
@require_module("scm_ai")
async def get_ai_dashboard(
    db: AsyncSession = Depends(get_db)
):
    """
    Get comprehensive AI dashboard data.

    Includes:
    - Demand forecasts
    - Payment predictions
    - Maintenance alerts
    - Quick chatbot stats
    """
    demand_service = DemandForecastingService(db)
    maintenance_service = PredictiveMaintenanceService(db)
    chatbot_service = ERPChatbotService(db)

    # Get all dashboard data
    demand_dashboard = await demand_service.get_demand_dashboard()
    maintenance_dashboard = await maintenance_service.get_maintenance_dashboard()
    quick_stats = await chatbot_service.get_quick_stats()

    return {
        "generated_at": demand_dashboard["generated_at"],

        "demand_intelligence": {
            "next_7_days_revenue": demand_dashboard["overall_forecast"]["next_7_days_revenue"],
            "next_7_days_orders": demand_dashboard["overall_forecast"]["next_7_days_orders"],
            "top_products": demand_dashboard["product_forecasts"][:5],
            "confidence": demand_dashboard["confidence_level"]
        },

        "maintenance_intelligence": {
            "total_installations": maintenance_dashboard["summary"]["total_active_installations"],
            "needs_attention": maintenance_dashboard["summary"]["needs_attention"],
            "critical": maintenance_dashboard["summary"]["critical"],
            "this_week_services": maintenance_dashboard["service_schedule"]["this_week"],
            "revenue_opportunity": maintenance_dashboard["revenue_opportunity"]["estimated_service_revenue"]
        },

        "quick_stats": quick_stats,

        "insights": [
            *demand_dashboard["insights"],
            *maintenance_dashboard["insights"]
        ]
    }


# ==================== Demand Forecasting ====================

@router.get("/forecast/demand/dashboard")
@require_module("scm_ai")
async def get_demand_dashboard(
    db: AsyncSession = Depends(get_db)
):
    """
    Get demand forecasting dashboard.

    Shows:
    - Overall sales forecast
    - Top product forecasts
    - Stockout risks
    """
    service = DemandForecastingService(db)
    return await service.get_demand_dashboard()


@router.get("/forecast/demand/product/{product_id}")
@require_module("scm_ai")
async def get_product_demand_forecast(
    product_id: UUID,
    days_ahead: int = Query(30, ge=1, le=90, description="Days to forecast"),
    lookback_days: int = Query(90, ge=30, le=365, description="Historical days to analyze"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get demand forecast for a specific product.

    Uses Holt-Winters triple exponential smoothing for seasonal data.
    Returns predictions with confidence intervals.
    """
    service = DemandForecastingService(db)
    result = await service.forecast_product_demand(product_id, days_ahead, lookback_days)

    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    return result


@router.get("/forecast/demand/category/{category_id}")
@require_module("scm_ai")
async def get_category_demand_forecast(
    category_id: UUID,
    days_ahead: int = Query(30, ge=1, le=90),
    lookback_days: int = Query(90, ge=30, le=365),
    db: AsyncSession = Depends(get_db)
):
    """
    Get demand forecast for a product category.
    """
    service = DemandForecastingService(db)
    return await service.forecast_category_demand(category_id, days_ahead, lookback_days)


@router.get("/forecast/demand/all")
@require_module("scm_ai")
async def get_all_product_forecasts(
    days_ahead: int = Query(30, ge=1, le=90),
    min_sales: int = Query(5, ge=1, description="Minimum historical sales to include"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get demand forecasts for all products with sufficient history.

    Products are sorted by stockout risk (highest risk first).
    """
    service = DemandForecastingService(db)
    return await service.forecast_all_products(days_ahead, min_sales)


# ==================== Payment Prediction ====================

@router.get("/predict/payment/invoice/{invoice_id}")
@require_module("scm_ai")
async def predict_invoice_payment(
    invoice_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Predict when a specific invoice will be paid.

    Returns:
    - Predicted payment date
    - Delay probability
    - Risk category
    - Recommended action
    """
    service = PaymentPredictionService(db)
    result = await service.predict_invoice_payment(invoice_id)

    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    return result


@router.get("/predict/payment/collection-priority")
@require_module("scm_ai")
async def get_collection_priority(
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """
    Get prioritized list of invoices for collection.

    Sorted by priority score (combination of amount, days overdue, and risk).
    """
    service = PaymentPredictionService(db)
    return await service.get_collection_priority_list(limit)


@router.get("/predict/payment/cash-flow")
@require_module("scm_ai")
async def predict_cash_flow(
    days_ahead: int = Query(30, ge=7, le=90),
    db: AsyncSession = Depends(get_db)
):
    """
    Predict cash flow based on pending invoices.

    Returns expected, optimistic, and pessimistic scenarios.
    """
    service = PaymentPredictionService(db)
    return await service.predict_cash_flow(days_ahead)


@router.get("/predict/payment/customer-credit/{customer_id}")
@require_module("scm_ai")
async def get_customer_credit_score(
    customer_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Get credit score for a customer.

    Based on payment history, consistency, and transaction volume.
    """
    service = PaymentPredictionService(db)
    result = await service.get_customer_credit_score(customer_id)

    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    return result


# ==================== Predictive Maintenance ====================

@router.get("/predict/maintenance/dashboard")
@require_module("scm_ai")
async def get_maintenance_dashboard(
    db: AsyncSession = Depends(get_db)
):
    """
    Get predictive maintenance dashboard.

    Shows:
    - Installations needing attention
    - Critical alerts
    - Service schedule
    - Revenue opportunity
    """
    service = PredictiveMaintenanceService(db)
    return await service.get_maintenance_dashboard()


@router.get("/predict/maintenance/installation/{installation_id}")
@require_module("scm_ai")
async def predict_installation_health(
    installation_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Get health prediction for a specific installation.

    Analyzes all components and predicts maintenance needs.
    """
    service = PredictiveMaintenanceService(db)
    result = await service.predict_installation_health(installation_id)

    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])

    return result


@router.get("/predict/maintenance/proactive-list")
@require_module("scm_ai")
async def get_proactive_service_list(
    health_threshold: int = Query(80, ge=0, le=100, description="Include items below this health score"),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """
    Get list of installations that need proactive service.

    Sorted by priority score (combination of health, warranty, and component status).
    """
    service = PredictiveMaintenanceService(db)
    return await service.get_proactive_service_list(health_threshold, limit)


@router.get("/predict/maintenance/failure-analysis")
@require_module("scm_ai")
async def get_component_failure_analysis(
    days_back: int = Query(365, ge=30, le=730),
    db: AsyncSession = Depends(get_db)
):
    """
    Analyze historical component failures.

    Identifies most common failures and trends.
    """
    service = PredictiveMaintenanceService(db)
    return await service.analyze_component_failures(days_back)


# ==================== AI Chatbot ====================

@router.post("/chat")
@require_module("scm_ai")
async def chat_query(
    request: ChatQuery,
    db: AsyncSession = Depends(get_db)
):
    """
    Natural language query interface for ERP data.

    Examples:
    - "What were sales this month?"
    - "Show top selling products"
    - "Stock for 'RO Filter'"
    - "Pending orders"
    - "Open service tickets"
    """
    service = ERPChatbotService(db)
    return await service.query(request.query)


@router.get("/chat/quick-stats")
@require_module("scm_ai")
async def get_chat_quick_stats(
    db: AsyncSession = Depends(get_db)
):
    """
    Get quick stats for chatbot initial display.

    Shows today's stats, month stats, and suggested queries.
    """
    service = ERPChatbotService(db)
    return await service.get_quick_stats()


# ==================== AI Capabilities Info ====================

@router.get("/capabilities")
@require_module("scm_ai")
async def get_ai_capabilities():
    """
    Get information about available AI capabilities.
    """
    return {
        "version": "1.0.0",
        "capabilities": [
            {
                "name": "Demand Forecasting",
                "description": "Predict future demand using time-series analysis",
                "endpoints": [
                    "/api/v1/ai/forecast/demand/dashboard",
                    "/api/v1/ai/forecast/demand/product/{id}",
                    "/api/v1/ai/forecast/demand/category/{id}",
                    "/api/v1/ai/forecast/demand/all"
                ],
                "features": [
                    "Holt-Winters triple exponential smoothing",
                    "Seasonal pattern detection",
                    "Confidence intervals",
                    "Stockout prediction"
                ]
            },
            {
                "name": "Payment Prediction",
                "description": "Predict customer payment behavior and optimize collections",
                "endpoints": [
                    "/api/v1/ai/predict/payment/invoice/{id}",
                    "/api/v1/ai/predict/payment/collection-priority",
                    "/api/v1/ai/predict/payment/cash-flow",
                    "/api/v1/ai/predict/payment/customer-credit/{id}"
                ],
                "features": [
                    "Payment date prediction",
                    "Delay probability scoring",
                    "Collection prioritization",
                    "Customer credit scoring"
                ]
            },
            {
                "name": "Predictive Maintenance",
                "description": "Predict maintenance needs for installed products",
                "endpoints": [
                    "/api/v1/ai/predict/maintenance/dashboard",
                    "/api/v1/ai/predict/maintenance/installation/{id}",
                    "/api/v1/ai/predict/maintenance/proactive-list",
                    "/api/v1/ai/predict/maintenance/failure-analysis"
                ],
                "features": [
                    "Component health scoring",
                    "Failure prediction",
                    "TDS-adjusted lifecycle",
                    "Proactive service scheduling"
                ]
            },
            {
                "name": "AI Chatbot",
                "description": "Natural language interface for ERP queries",
                "endpoints": [
                    "/api/v1/ai/chat",
                    "/api/v1/ai/chat/quick-stats"
                ],
                "features": [
                    "Intent classification",
                    "Time period extraction",
                    "Sales queries",
                    "Inventory queries",
                    "Customer queries",
                    "Service queries"
                ]
            }
        ],
        "models_used": [
            "Holt-Winters Triple Exponential Smoothing",
            "Linear Regression",
            "Rule-based Intent Classification",
            "Statistical Scoring Algorithms"
        ],
        "note": "All AI computations are performed locally without external API dependencies."
    }
