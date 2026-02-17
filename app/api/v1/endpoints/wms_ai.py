"""
WMS AI API Endpoints

Provides WMS AI-powered capabilities:
- Command Center Dashboard (aggregated agent status/alerts)
- Individual Agent Run/Status/Recommendations
- WMS-specific NL Chatbot
"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import TenantDB, CurrentUser
from app.schemas.wms_ai import (
    WMSChatQuery,
    WMSAgentRunRequest,
    WMSLaborForecastRequest,
    WMSSlottingRequest,
    WMSReplenishmentRequest,
)
from app.services.ai.wms.command_center import WMSCommandCenter
from app.services.ai.wms.chatbot import WMSChatbotService
from app.core.module_decorators import require_module


router = APIRouter()


# ==================== Dashboard ====================

@router.get("/dashboard")
@require_module("wms_ai")
async def get_wms_ai_dashboard(
    db: TenantDB,
    current_user: CurrentUser,
    warehouse_id: Optional[UUID] = Query(None, description="Scope to specific warehouse"),
):
    """
    Get WMS AI Command Center dashboard.

    Includes:
    - All agent statuses
    - Severity summary
    - Combined alerts and recommendations
    """
    center = WMSCommandCenter(db)
    return await center.get_dashboard(warehouse_id)


# ==================== Agent Operations ====================

@router.post("/agents/{agent_name}/run")
@require_module("wms_ai")
async def run_wms_agent(
    agent_name: str,
    db: TenantDB,
    current_user: CurrentUser,
    request: Optional[WMSAgentRunRequest] = None,
):
    """
    Run a specific WMS AI agent.

    Available agents: anomaly-detection, smart-slotting, labor-forecasting, replenishment
    """
    valid_agents = ["anomaly-detection", "smart-slotting", "labor-forecasting", "replenishment"]
    if agent_name not in valid_agents:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown agent: {agent_name}. Available: {valid_agents}",
        )

    center = WMSCommandCenter(db)
    kwargs = {}
    if request:
        kwargs["warehouse_id"] = request.warehouse_id
        if agent_name != "labor-forecasting":
            kwargs["days"] = request.days

    return await center.run_agent(agent_name, **kwargs)


@router.post("/agents/labor-forecasting/run")
@require_module("wms_ai")
async def run_labor_forecasting(
    db: TenantDB,
    current_user: CurrentUser,
    request: Optional[WMSLaborForecastRequest] = None,
):
    """Run labor forecasting agent with specific parameters."""
    from app.services.ai.wms.labor_forecasting import WMSLaborForecastingAgent
    agent = WMSLaborForecastingAgent(db)

    warehouse_id = request.warehouse_id if request else None
    forecast_days = request.forecast_days if request else 14
    lookback_days = request.lookback_days if request else 90

    return await agent.analyze(
        warehouse_id=warehouse_id,
        forecast_days=forecast_days,
        lookback_days=lookback_days,
    )


@router.post("/agents/smart-slotting/run")
@require_module("wms_ai")
async def run_smart_slotting(
    db: TenantDB,
    current_user: CurrentUser,
    request: Optional[WMSSlottingRequest] = None,
):
    """Run smart slotting agent with specific parameters."""
    from app.services.ai.wms.smart_slotting import WMSSmartSlottingAgent
    agent = WMSSmartSlottingAgent(db)

    warehouse_id = request.warehouse_id if request else None
    days = request.days if request else 90

    return await agent.analyze(warehouse_id=warehouse_id, days=days)


@router.post("/agents/replenishment/run")
@require_module("wms_ai")
async def run_replenishment(
    db: TenantDB,
    current_user: CurrentUser,
    request: Optional[WMSReplenishmentRequest] = None,
):
    """Run replenishment agent with specific parameters."""
    from app.services.ai.wms.replenishment import WMSReplenishmentAgent
    agent = WMSReplenishmentAgent(db)

    warehouse_id = request.warehouse_id if request else None
    days = request.days if request else 30

    return await agent.analyze(warehouse_id=warehouse_id, days=days)


@router.get("/agents/{agent_name}/status")
@require_module("wms_ai")
async def get_wms_agent_status(
    agent_name: str,
    db: TenantDB,
    current_user: CurrentUser,
):
    """Get status of a specific WMS AI agent."""
    center = WMSCommandCenter(db)
    result = await center.get_agent_status(agent_name)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.get("/agents/{agent_name}/recommendations")
@require_module("wms_ai")
async def get_wms_agent_recommendations(
    agent_name: str,
    db: TenantDB,
    current_user: CurrentUser,
):
    """Get recommendations from a specific WMS AI agent."""
    center = WMSCommandCenter(db)
    return await center.get_agent_recommendations(agent_name)


# ==================== Chat ====================

@router.post("/chat")
@require_module("wms_ai")
async def wms_ai_chat(
    data: WMSChatQuery,
    db: TenantDB,
    current_user: CurrentUser,
):
    """
    WMS AI Chat endpoint.

    Supports natural language queries about:
    - Zone utilization
    - Pick performance
    - Anomaly detection
    - Slotting analysis
    - Replenishment status
    - Worker productivity
    """
    chatbot = WMSChatbotService(db)
    return await chatbot.query(data.query)


@router.get("/chat/quick-stats")
@require_module("wms_ai")
async def get_wms_quick_stats(
    db: TenantDB,
    current_user: CurrentUser,
):
    """Get quick WMS stats for chat interface."""
    chatbot = WMSChatbotService(db)
    return await chatbot.get_quick_stats()


# ==================== Capabilities ====================

@router.get("/capabilities")
@require_module("wms_ai")
async def get_wms_ai_capabilities(
    db: TenantDB,
    current_user: CurrentUser,
):
    """Get WMS AI module capabilities."""
    center = WMSCommandCenter(db)
    return await center.get_capabilities()
