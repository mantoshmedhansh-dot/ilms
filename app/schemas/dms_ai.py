"""DMS AI service schemas for API requests/responses."""
from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID


class DMSChatQuery(BaseModel):
    """DMS Chat query request model."""
    query: str = Field(
        ...,
        min_length=2,
        max_length=500,
        description="Natural language query for the DMS AI chatbot",
    )


class DMSAgentRunRequest(BaseModel):
    """Generic request to run a DMS AI agent."""
    days: int = Field(7, ge=1, le=90, description="Days of data to analyze")
    limit: int = Field(50, ge=1, le=200, description="Max items to analyze")
