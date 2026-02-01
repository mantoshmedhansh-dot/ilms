"""AI service schemas for API requests/responses."""
from pydantic import BaseModel, Field


class ChatQuery(BaseModel):
    """Chat query request model."""
    query: str = Field(
        ...,
        min_length=2,
        max_length=500,
        description="Natural language query for the ERP chatbot"
    )


class ForecastRequest(BaseModel):
    """Forecast request model."""
    days_ahead: int = Field(
        30,
        ge=1,
        le=90,
        description="Number of days to forecast ahead"
    )
    lookback_days: int = Field(
        90,
        ge=30,
        le=365,
        description="Number of days of historical data to use"
    )
