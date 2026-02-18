"""
DMS AI API Endpoints

Provides DMS AI-powered capabilities:
- Command Center Dashboard (aggregated agent status/alerts)
- Dealer Performance (scoring, achievement analysis)
- Collection Optimizer (aging, payment prediction, priority)
- Scheme Effectiveness (ROI, budget utilization)
- Demand Sensing (trends, forecasting)
- DMS-specific NL Chatbot
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import TenantDB, CurrentUser
from app.schemas.dms_ai import DMSChatQuery, DMSAgentRunRequest
from app.services.ai.dms.command_center import DMSCommandCenter
from app.services.ai.dms.chatbot import DMSChatbotService
from app.core.module_decorators import require_module


router = APIRouter()


# ==================== Dashboard ====================

@router.get("/dashboard")
@require_module("dms")
async def get_dms_ai_dashboard(
    db: TenantDB,
    current_user: CurrentUser,
):
    """
    Get DMS AI Command Center dashboard.

    Includes:
    - All 4 agent statuses
    - Severity summary
    - Combined alerts and recommendations
    """
    center = DMSCommandCenter(db)
    return await center.get_dashboard()


# ==================== Dealer Performance ====================

@router.post("/agents/dealer-performance/run")
@require_module("dms")
async def run_dealer_performance(
    db: TenantDB,
    current_user: CurrentUser,
    request: Optional[DMSAgentRunRequest] = None,
):
    """Run dealer performance agent."""
    from app.services.ai.dms.dealer_performance import DMSDealerPerformanceAgent
    agent = DMSDealerPerformanceAgent(db)
    return await agent.analyze()


# ==================== Collection Optimizer ====================

@router.post("/agents/collection-optimizer/run")
@require_module("dms")
async def run_collection_optimizer(
    db: TenantDB,
    current_user: CurrentUser,
    request: Optional[DMSAgentRunRequest] = None,
):
    """Run collection optimizer agent."""
    from app.services.ai.dms.collection_optimizer import DMSCollectionOptimizerAgent
    agent = DMSCollectionOptimizerAgent(db)
    return await agent.analyze()


# ==================== Scheme Effectiveness ====================

@router.post("/agents/scheme-effectiveness/run")
@require_module("dms")
async def run_scheme_effectiveness(
    db: TenantDB,
    current_user: CurrentUser,
    request: Optional[DMSAgentRunRequest] = None,
):
    """Run scheme effectiveness agent."""
    from app.services.ai.dms.scheme_effectiveness import DMSSchemeEffectivenessAgent
    agent = DMSSchemeEffectivenessAgent(db)
    return await agent.analyze()


# ==================== Demand Sensing ====================

@router.post("/agents/demand-sensing/run")
@require_module("dms")
async def run_demand_sensing(
    db: TenantDB,
    current_user: CurrentUser,
    request: Optional[DMSAgentRunRequest] = None,
):
    """Run demand sensing agent."""
    from app.services.ai.dms.demand_sensing import DMSDemandSensingAgent
    agent = DMSDemandSensingAgent(db)
    return await agent.analyze()


# ==================== Agent Status & Recommendations ====================

@router.get("/agents/{name}/status")
@require_module("dms")
async def get_agent_status(
    name: str,
    db: TenantDB,
    current_user: CurrentUser,
):
    """Get status of a specific DMS AI agent."""
    center = DMSCommandCenter(db)
    result = await center.get_agent_status(name)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.get("/agents/{name}/recommendations")
@require_module("dms")
async def get_agent_recommendations(
    name: str,
    db: TenantDB,
    current_user: CurrentUser,
):
    """Get recommendations from a specific DMS AI agent."""
    center = DMSCommandCenter(db)
    return await center.get_agent_recommendations(name)


# ==================== Chat ====================

@router.post("/chat")
@require_module("dms")
async def dms_ai_chat(
    data: DMSChatQuery,
    db: TenantDB,
    current_user: CurrentUser,
):
    """
    DMS AI Chat endpoint.

    Supports natural language queries about:
    - Dealer info, DMS orders, collections, schemes
    - Claims, demand forecasts, performance rankings
    """
    chatbot = DMSChatbotService(db)
    return await chatbot.query(data.query)


@router.get("/chat/quick-stats")
@require_module("dms")
async def get_dms_quick_stats(
    db: TenantDB,
    current_user: CurrentUser,
):
    """Get quick stats for the DMS chat UI."""
    chatbot = DMSChatbotService(db)
    return await chatbot.get_quick_stats()


# ==================== Capabilities ====================

@router.get("/capabilities")
@require_module("dms")
async def get_dms_ai_capabilities(
    db: TenantDB,
    current_user: CurrentUser,
):
    """Get DMS AI module capabilities."""
    center = DMSCommandCenter(db)
    return await center.get_capabilities()
