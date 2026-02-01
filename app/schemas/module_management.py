"""Schemas for module management (subscribe/unsubscribe)"""

from pydantic import BaseModel, Field
from typing import List, Optional
from uuid import UUID
from datetime import datetime


class ModuleSubscribeRequest(BaseModel):
    """Request to subscribe to additional modules"""
    module_codes: List[str] = Field(..., min_items=1, description="Module codes to subscribe to")
    billing_cycle: str = Field(default="monthly", description="Billing cycle: monthly or yearly")


class ModuleUnsubscribeRequest(BaseModel):
    """Request to unsubscribe from modules"""
    module_codes: List[str] = Field(..., min_items=1, description="Module codes to unsubscribe from")
    reason: Optional[str] = Field(None, description="Reason for unsubscribing")


class ModuleSubscriptionDetail(BaseModel):
    """Detailed module subscription info"""
    id: UUID
    module_id: UUID
    module_code: str
    module_name: str
    status: str
    billing_cycle: str
    price_paid: float
    starts_at: datetime
    expires_at: Optional[datetime]
    is_trial: bool
    trial_ends_at: Optional[datetime]
    auto_renew: bool


class SubscriptionChangeResponse(BaseModel):
    """Response after subscription change"""
    success: bool
    message: str
    subscriptions: List[ModuleSubscriptionDetail]
    total_monthly_cost: float
    total_yearly_cost: float
    changes_applied: int


class TenantModulesResponse(BaseModel):
    """Current tenant module subscriptions"""
    tenant_id: UUID
    tenant_name: str
    subscriptions: List[ModuleSubscriptionDetail]
    total_modules: int
    active_modules: int
    total_monthly_cost: float
    total_yearly_cost: float


class PricingCalculationRequest(BaseModel):
    """Request to calculate pricing for module changes"""
    add_modules: Optional[List[str]] = Field(default=None, description="Modules to add")
    remove_modules: Optional[List[str]] = Field(default=None, description="Modules to remove")
    billing_cycle: str = Field(default="monthly", description="Billing cycle")


class PricingCalculationResponse(BaseModel):
    """Pricing calculation result"""
    current_monthly_cost: float
    new_monthly_cost: float
    difference: float
    modules_to_add: List[str]
    modules_to_remove: List[str]
    billing_cycle: str
    yearly_cost: Optional[float] = None
    savings_yearly: Optional[float] = None
