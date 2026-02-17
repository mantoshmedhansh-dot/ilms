"""WMS AI service schemas for API requests/responses."""
from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID


class WMSChatQuery(BaseModel):
    """WMS Chat query request model."""
    query: str = Field(
        ...,
        min_length=2,
        max_length=500,
        description="Natural language query for the WMS AI chatbot",
    )


class WMSAgentRunRequest(BaseModel):
    """Request to run a WMS AI agent."""
    warehouse_id: Optional[UUID] = Field(
        None, description="Optional warehouse ID to scope the analysis"
    )
    days: int = Field(
        30, ge=1, le=365, description="Number of days of historical data to analyze"
    )


class WMSLaborForecastRequest(BaseModel):
    """Request for labor forecasting."""
    warehouse_id: Optional[UUID] = Field(
        None, description="Optional warehouse ID to scope the forecast"
    )
    forecast_days: int = Field(
        14, ge=1, le=90, description="Number of days to forecast ahead"
    )
    lookback_days: int = Field(
        90, ge=14, le=365, description="Number of days of historical data to use"
    )


class WMSSlottingRequest(BaseModel):
    """Request for smart slotting analysis."""
    warehouse_id: Optional[UUID] = Field(
        None, description="Optional warehouse ID to scope the analysis"
    )
    days: int = Field(
        90, ge=7, le=365, description="Number of days of pick history to analyze"
    )


class WMSReplenishmentRequest(BaseModel):
    """Request for replenishment analysis."""
    warehouse_id: Optional[UUID] = Field(
        None, description="Optional warehouse ID to scope the analysis"
    )
    days: int = Field(
        30, ge=1, le=90, description="Number of days for consumption rate calculation"
    )
