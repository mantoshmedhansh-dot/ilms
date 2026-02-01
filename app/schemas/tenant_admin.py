"""Schemas for tenant administration (super admin)"""

from pydantic import BaseModel, Field
from typing import List, Optional
from uuid import UUID
from datetime import datetime


class TenantListItem(BaseModel):
    """Tenant list item for admin dashboard"""
    id: UUID
    name: str
    subdomain: str
    status: str
    plan_name: Optional[str] = None
    total_subscriptions: int
    monthly_cost: float
    onboarded_at: datetime
    last_active: Optional[datetime] = None


class TenantListResponse(BaseModel):
    """Response for listing all tenants"""
    tenants: List[TenantListItem]
    total: int
    active: int
    pending: int
    suspended: int


class TenantDetailResponse(BaseModel):
    """Detailed tenant information"""
    id: UUID
    name: str
    subdomain: str
    database_schema: str
    status: str
    plan_id: Optional[UUID]
    plan_name: Optional[str]
    onboarded_at: datetime
    trial_ends_at: Optional[datetime]
    settings: dict
    tenant_metadata: dict
    subscriptions: List[dict]
    total_monthly_cost: float
    total_users: int
    storage_used_mb: Optional[float] = None
    api_calls_monthly: Optional[int] = None


class TenantStatusUpdateRequest(BaseModel):
    """Request to update tenant status"""
    status: str = Field(..., description="New status: active, suspended, cancelled")
    reason: Optional[str] = Field(None, description="Reason for status change")


class TenantStatusUpdateResponse(BaseModel):
    """Response after status update"""
    success: bool
    message: str
    tenant_id: UUID
    new_status: str


class UsageMetricsSummary(BaseModel):
    """Tenant usage metrics summary"""
    tenant_id: UUID
    tenant_name: str
    period_start: datetime
    period_end: datetime
    total_users: int
    active_users: int
    api_calls: int
    storage_mb: float
    transactions: int
    modules_used: List[str]


class PlatformStatistics(BaseModel):
    """Platform-wide statistics"""
    total_tenants: int
    active_tenants: int
    pending_tenants: int
    suspended_tenants: int
    total_revenue_monthly: float
    total_revenue_yearly: float
    total_users: int
    avg_modules_per_tenant: float
    most_popular_modules: List[dict]
    growth_rate: Optional[float] = None


class BillingHistoryItem(BaseModel):
    """Billing history item"""
    id: UUID
    tenant_id: UUID
    tenant_name: str
    invoice_number: str
    billing_period_start: datetime
    billing_period_end: datetime
    amount: float
    tax_amount: float
    total_amount: float
    status: str
    payment_method: Optional[str]
    paid_at: Optional[datetime]


class BillingHistoryResponse(BaseModel):
    """Billing history response"""
    invoices: List[BillingHistoryItem]
    total: int
    total_revenue: float
    pending_amount: float
