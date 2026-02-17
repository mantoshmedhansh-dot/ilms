"""
OMS AI API Endpoints

Provides OMS AI-powered capabilities:
- Command Center Dashboard (aggregated agent status/alerts)
- Fraud Detection (score orders, batch analysis)
- Smart Routing (warehouse scoring, order routing)
- Delivery Promise / ATP (date estimates)
- Order Prioritization (fulfillment queue)
- Returns Prediction (return probability)
- OMS-specific NL Chatbot
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import TenantDB, CurrentUser
from app.schemas.oms_ai import (
    OMSChatQuery,
    FraudScoringRequest,
    DeliveryPromiseRequest,
    SmartRoutingRequest,
    ReturnPredictionRequest,
    OMSAgentRunRequest,
)
from app.services.ai.oms.command_center import OMSCommandCenter
from app.services.ai.oms.chatbot import OMSChatbotService
from app.core.module_decorators import require_module


router = APIRouter()


# ==================== Dashboard ====================

@router.get("/dashboard")
@require_module("oms_ai")
async def get_oms_ai_dashboard(
    db: TenantDB,
    current_user: CurrentUser,
):
    """
    Get OMS AI Command Center dashboard.

    Includes:
    - All 5 agent statuses
    - Severity summary
    - Combined alerts and recommendations
    """
    center = OMSCommandCenter(db)
    return await center.get_dashboard()


# ==================== Fraud Detection ====================

@router.post("/agents/fraud-detection/run")
@require_module("oms_ai")
async def run_fraud_detection(
    db: TenantDB,
    current_user: CurrentUser,
    request: Optional[OMSAgentRunRequest] = None,
):
    """Run fraud detection agent on recent orders."""
    from app.services.ai.oms.fraud_detection import OMSFraudDetectionAgent
    agent = OMSFraudDetectionAgent(db)

    days = request.days if request else 7
    limit = request.limit if request else 50

    return await agent.analyze(days=days, limit=limit)


@router.get("/agents/fraud-detection/score/{order_id}")
@require_module("oms_ai")
async def get_fraud_score(
    order_id: UUID,
    db: TenantDB,
    current_user: CurrentUser,
):
    """Get fraud score for a specific order."""
    from app.services.ai.oms.fraud_detection import OMSFraudDetectionAgent
    agent = OMSFraudDetectionAgent(db)
    result = await agent.score_order(order_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


# ==================== Smart Routing ====================

@router.post("/agents/smart-routing/analyze/{order_id}")
@require_module("oms_ai")
async def analyze_order_routing(
    order_id: UUID,
    db: TenantDB,
    current_user: CurrentUser,
):
    """Analyze routing options for an order."""
    from app.services.ai.oms.smart_routing import OMSSmartRoutingAgent
    agent = OMSSmartRoutingAgent(db)
    result = await agent.analyze_order(order_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


# ==================== Delivery Promise ====================

@router.get("/agents/delivery-promise/check")
@require_module("oms_ai")
async def check_delivery_promise(
    db: TenantDB,
    current_user: CurrentUser,
    product_id: Optional[UUID] = Query(None, description="Product ID"),
    pincode: Optional[str] = Query(None, description="Delivery pincode"),
    quantity: int = Query(1, ge=1, description="Quantity"),
):
    """Check delivery promise for a product + pincode."""
    from app.services.ai.oms.delivery_promise import OMSDeliveryPromiseAgent
    agent = OMSDeliveryPromiseAgent(db)
    return await agent.analyze(
        product_id=product_id,
        pincode=pincode,
        quantity=quantity,
    )


# ==================== Order Prioritization ====================

@router.post("/agents/order-prioritization/run")
@require_module("oms_ai")
async def run_order_prioritization(
    db: TenantDB,
    current_user: CurrentUser,
    limit: int = Query(50, ge=1, le=200),
):
    """Run order prioritization agent."""
    from app.services.ai.oms.order_prioritization import OMSOrderPrioritizationAgent
    agent = OMSOrderPrioritizationAgent(db)
    return await agent.analyze(limit=limit)


@router.get("/agents/order-prioritization/queue")
@require_module("oms_ai")
async def get_priority_queue(
    db: TenantDB,
    current_user: CurrentUser,
):
    """Get current prioritized order queue."""
    from app.services.ai.oms.order_prioritization import OMSOrderPrioritizationAgent
    agent = OMSOrderPrioritizationAgent(db)
    return await agent.get_queue()


# ==================== Returns Prediction ====================

@router.post("/agents/returns-prediction/run")
@require_module("oms_ai")
async def run_returns_prediction(
    db: TenantDB,
    current_user: CurrentUser,
    request: Optional[OMSAgentRunRequest] = None,
):
    """Run returns prediction agent."""
    from app.services.ai.oms.returns_prediction import OMSReturnsPredictionAgent
    agent = OMSReturnsPredictionAgent(db)

    days = request.days if request else 7
    limit = request.limit if request else 50

    return await agent.analyze(days=days, limit=limit)


@router.get("/agents/returns-prediction/score/{order_id}")
@require_module("oms_ai")
async def get_return_prediction_score(
    order_id: UUID,
    db: TenantDB,
    current_user: CurrentUser,
):
    """Get return prediction for a specific order."""
    from app.services.ai.oms.returns_prediction import OMSReturnsPredictionAgent
    agent = OMSReturnsPredictionAgent(db)
    result = await agent.score_order(order_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


# ==================== Chat ====================

@router.post("/chat")
@require_module("oms_ai")
async def oms_ai_chat(
    data: OMSChatQuery,
    db: TenantDB,
    current_user: CurrentUser,
):
    """
    OMS AI Chat endpoint.

    Supports natural language queries about:
    - Order status, fraud detection, delivery promise
    - Routing, return risk, queue, SLA
    """
    chatbot = OMSChatbotService(db)
    return await chatbot.query(data.query)


# ==================== Capabilities ====================

@router.get("/capabilities")
@require_module("oms_ai")
async def get_oms_ai_capabilities(
    db: TenantDB,
    current_user: CurrentUser,
):
    """Get OMS AI module capabilities."""
    center = OMSCommandCenter(db)
    return await center.get_capabilities()
