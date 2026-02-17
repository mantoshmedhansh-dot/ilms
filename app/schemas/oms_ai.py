"""OMS AI service schemas for API requests/responses."""
from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID


class OMSChatQuery(BaseModel):
    """OMS Chat query request model."""
    query: str = Field(
        ...,
        min_length=2,
        max_length=500,
        description="Natural language query for the OMS AI chatbot",
    )


class FraudScoringRequest(BaseModel):
    """Request to score an order for fraud."""
    order_id: UUID = Field(..., description="Order ID to score")


class DeliveryPromiseRequest(BaseModel):
    """Request for delivery promise check."""
    product_id: UUID = Field(..., description="Product ID")
    pincode: str = Field(..., min_length=5, max_length=10, description="Delivery pincode")
    quantity: int = Field(1, ge=1, le=1000, description="Quantity requested")


class SmartRoutingRequest(BaseModel):
    """Request for smart routing analysis."""
    order_id: UUID = Field(..., description="Order ID to analyze routing for")


class ReturnPredictionRequest(BaseModel):
    """Request for return prediction."""
    order_id: UUID = Field(..., description="Order ID to predict returns for")


class OMSAgentRunRequest(BaseModel):
    """Generic request to run an OMS AI agent."""
    days: int = Field(7, ge=1, le=90, description="Days of data to analyze")
    limit: int = Field(50, ge=1, le=200, description="Max orders to analyze")
