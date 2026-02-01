"""Marketplace integration schemas for API requests/responses."""
from pydantic import BaseModel, Field

from app.schemas.base import BaseResponseSchema
from typing import Optional, List
from uuid import UUID
from datetime import datetime


class MarketplaceCredentials(BaseModel):
    """Marketplace credentials for setup."""
    marketplace_type: str = Field(..., description="Marketplace type: AMAZON, FLIPKART, MEESHO, SNAPDEAL")
    client_id: str = Field(..., description="Client/App ID")
    client_secret: str = Field(..., description="Client secret (will be encrypted)")
    refresh_token: Optional[str] = Field(None, description="For Amazon (will be encrypted)")
    api_key: Optional[str] = Field(None, description="API key (will be encrypted)")
    seller_id: Optional[str] = Field(None, description="Seller ID")
    is_sandbox: bool = Field(True, description="Whether to use sandbox mode")


class MarketplaceIntegrationResponse(BaseModel):
    """Response for marketplace integration."""
    id: UUID
    marketplace_type: str
    client_id: str
    seller_id: Optional[str] = None
    is_sandbox: bool
    is_active: bool
    last_sync_at: Optional[datetime] = None
    created_at: datetime


class SyncOrdersRequest(BaseModel):
    """Request for syncing orders from marketplace."""
    from_date: Optional[datetime] = Field(None, description="Sync orders from this date")
    order_statuses: Optional[List[str]] = Field(None, description="Filter by order statuses")


class SyncInventoryRequest(BaseModel):
    """Request for syncing inventory to marketplace."""
    products: List[dict] = Field(..., description="List of {sku, quantity} to sync")


class ShipmentUpdateRequest(BaseModel):
    """Request for updating shipment on marketplace."""
    order_id: str = Field(..., description="Marketplace order ID")
    tracking_id: str = Field(..., description="Tracking/AWB number")
    courier: str = Field(..., description="Courier/logistics partner name")


class SyncResult(BaseModel):
    """Result of sync operation."""
    success: bool = Field(..., description="Whether sync was successful")
    marketplace: str = Field(..., description="Marketplace name")
    message: str = Field(..., description="Result message")
    details: Optional[dict] = Field(None, description="Additional details")
