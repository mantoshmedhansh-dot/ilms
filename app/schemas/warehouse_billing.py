"""
Warehouse Billing Schemas - Phase 10: Storage & Operations Billing.

Pydantic schemas for warehouse billing operations.
"""
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict

from app.models.warehouse_billing import (
    BillingType, StorageBillingModel, HandlingBillingModel,
    ChargeCategory, ChargeType, ContractStatus, InvoiceStatus, BillingPeriod
)


# ============================================================================
# BILLING CONTRACT SCHEMAS
# ============================================================================

class BillingRateCardBase(BaseModel):
    """Base schema for billing rate card."""
    charge_category: ChargeCategory
    charge_type: str = Field(..., max_length=50)
    charge_name: str = Field(..., max_length=100)
    description: Optional[str] = None
    billing_model: str = Field(..., max_length=30)
    uom: str = Field(..., max_length=20)
    base_rate: Decimal
    min_charge: Decimal = Field(default=Decimal("0"))
    max_charge: Optional[Decimal] = None
    tiered_rates: Optional[List[Dict[str, Any]]] = None
    time_based_rates: Optional[List[Dict[str, Any]]] = None
    effective_from: date
    effective_to: Optional[date] = None
    notes: Optional[str] = None


class BillingRateCardCreate(BillingRateCardBase):
    """Schema for creating a billing rate card."""
    pass


class BillingRateCardUpdate(BaseModel):
    """Schema for updating a billing rate card."""
    charge_name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    base_rate: Optional[Decimal] = None
    min_charge: Optional[Decimal] = None
    max_charge: Optional[Decimal] = None
    tiered_rates: Optional[List[Dict[str, Any]]] = None
    time_based_rates: Optional[List[Dict[str, Any]]] = None
    effective_to: Optional[date] = None
    is_active: Optional[bool] = None
    notes: Optional[str] = None


class BillingRateCardResponse(BillingRateCardBase):
    """Schema for billing rate card response."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    contract_id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime


class BillingContractBase(BaseModel):
    """Base schema for billing contract."""
    contract_name: str = Field(..., max_length=200)
    description: Optional[str] = None
    customer_id: UUID
    warehouse_id: Optional[UUID] = None
    billing_type: BillingType = BillingType.HYBRID
    billing_period: BillingPeriod = BillingPeriod.MONTHLY
    billing_day: int = Field(default=1, ge=1, le=31)
    start_date: date
    end_date: Optional[date] = None
    auto_renew: bool = False
    minimum_storage_fee: Decimal = Field(default=Decimal("0"))
    minimum_handling_fee: Decimal = Field(default=Decimal("0"))
    minimum_monthly_fee: Decimal = Field(default=Decimal("0"))
    payment_terms_days: int = Field(default=30, ge=0, le=180)
    currency: str = Field(default="INR", max_length=3)
    late_fee_percent: Decimal = Field(default=Decimal("1.5"))
    grace_period_days: int = Field(default=5, ge=0)
    volume_discounts: Optional[List[Dict[str, Any]]] = None
    special_terms: Optional[str] = None
    notes: Optional[str] = None


class BillingContractCreate(BillingContractBase):
    """Schema for creating a billing contract."""
    rate_cards: Optional[List[BillingRateCardCreate]] = None


class BillingContractUpdate(BaseModel):
    """Schema for updating a billing contract."""
    contract_name: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = None
    warehouse_id: Optional[UUID] = None
    billing_type: Optional[BillingType] = None
    billing_period: Optional[BillingPeriod] = None
    billing_day: Optional[int] = Field(None, ge=1, le=31)
    end_date: Optional[date] = None
    renewal_date: Optional[date] = None
    auto_renew: Optional[bool] = None
    minimum_storage_fee: Optional[Decimal] = None
    minimum_handling_fee: Optional[Decimal] = None
    minimum_monthly_fee: Optional[Decimal] = None
    payment_terms_days: Optional[int] = Field(None, ge=0, le=180)
    late_fee_percent: Optional[Decimal] = None
    grace_period_days: Optional[int] = Field(None, ge=0)
    volume_discounts: Optional[List[Dict[str, Any]]] = None
    special_terms: Optional[str] = None
    notes: Optional[str] = None


class BillingContractResponse(BillingContractBase):
    """Schema for billing contract response."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    contract_number: str
    status: ContractStatus
    renewal_date: Optional[date]
    created_by: Optional[UUID]
    approved_by: Optional[UUID]
    approved_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    rate_cards: Optional[List[BillingRateCardResponse]] = None


class ContractActivate(BaseModel):
    """Schema for activating a contract."""
    notes: Optional[str] = None


# ============================================================================
# CHARGE SCHEMAS
# ============================================================================

class StorageChargeCreate(BaseModel):
    """Schema for creating a storage charge."""
    contract_id: UUID
    customer_id: UUID
    warehouse_id: UUID
    rate_card_id: Optional[UUID] = None
    charge_date: date
    storage_type: str = Field(..., max_length=50)
    zone_id: Optional[UUID] = None
    quantity: Decimal
    uom: str = Field(..., max_length=20)
    rate: Decimal
    breakdown: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None


class StorageChargeResponse(BaseModel):
    """Schema for storage charge response."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    contract_id: UUID
    customer_id: UUID
    warehouse_id: UUID
    rate_card_id: Optional[UUID]
    charge_date: date
    storage_type: str
    zone_id: Optional[UUID]
    quantity: Decimal
    uom: str
    rate: Decimal
    amount: Decimal
    breakdown: Optional[Dict[str, Any]]
    invoice_id: Optional[UUID]
    is_billed: bool
    notes: Optional[str]
    created_at: datetime


class HandlingChargeCreate(BaseModel):
    """Schema for creating a handling charge."""
    contract_id: UUID
    customer_id: UUID
    warehouse_id: UUID
    rate_card_id: Optional[UUID] = None
    charge_date: date
    charge_category: ChargeCategory
    charge_type: str = Field(..., max_length=50)
    charge_description: str = Field(..., max_length=200)
    source_type: Optional[str] = Field(None, max_length=30)
    source_id: Optional[UUID] = None
    source_number: Optional[str] = Field(None, max_length=50)
    quantity: Decimal
    uom: str = Field(..., max_length=20)
    rate: Decimal
    labor_hours: Optional[Decimal] = None
    labor_rate: Optional[Decimal] = None
    notes: Optional[str] = None


class HandlingChargeResponse(BaseModel):
    """Schema for handling charge response."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    contract_id: UUID
    customer_id: UUID
    warehouse_id: UUID
    rate_card_id: Optional[UUID]
    charge_date: date
    charge_category: str
    charge_type: str
    charge_description: str
    source_type: Optional[str]
    source_id: Optional[UUID]
    source_number: Optional[str]
    quantity: Decimal
    uom: str
    rate: Decimal
    amount: Decimal
    labor_hours: Optional[Decimal]
    labor_rate: Optional[Decimal]
    labor_amount: Decimal
    invoice_id: Optional[UUID]
    is_billed: bool
    notes: Optional[str]
    created_at: datetime


class VASChargeCreate(BaseModel):
    """Schema for creating a VAS charge."""
    contract_id: UUID
    customer_id: UUID
    warehouse_id: UUID
    rate_card_id: Optional[UUID] = None
    charge_date: date
    service_type: str = Field(..., max_length=50)
    service_name: str = Field(..., max_length=100)
    service_description: Optional[str] = None
    source_type: Optional[str] = Field(None, max_length=30)
    source_id: Optional[UUID] = None
    source_number: Optional[str] = Field(None, max_length=50)
    quantity: Decimal
    uom: str = Field(..., max_length=20)
    rate: Decimal
    materials_cost: Decimal = Field(default=Decimal("0"))
    materials_detail: Optional[List[Dict[str, Any]]] = None
    notes: Optional[str] = None


class VASChargeResponse(BaseModel):
    """Schema for VAS charge response."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    contract_id: UUID
    customer_id: UUID
    warehouse_id: UUID
    rate_card_id: Optional[UUID]
    charge_date: date
    service_type: str
    service_name: str
    service_description: Optional[str]
    source_type: Optional[str]
    source_id: Optional[UUID]
    source_number: Optional[str]
    quantity: Decimal
    uom: str
    rate: Decimal
    amount: Decimal
    materials_cost: Decimal
    materials_detail: Optional[List[Dict[str, Any]]]
    invoice_id: Optional[UUID]
    is_billed: bool
    notes: Optional[str]
    created_at: datetime


# ============================================================================
# INVOICE SCHEMAS
# ============================================================================

class BillingInvoiceItemBase(BaseModel):
    """Base schema for billing invoice item."""
    charge_category: str = Field(..., max_length=30)
    charge_type: str = Field(..., max_length=50)
    description: str = Field(..., max_length=500)
    quantity: Decimal
    uom: str = Field(..., max_length=20)
    rate: Decimal
    amount: Decimal
    line_number: int
    notes: Optional[str] = None


class BillingInvoiceItemCreate(BillingInvoiceItemBase):
    """Schema for creating a billing invoice item."""
    pass


class BillingInvoiceItemResponse(BillingInvoiceItemBase):
    """Schema for billing invoice item response."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    invoice_id: UUID
    created_at: datetime


class BillingInvoiceCreate(BaseModel):
    """Schema for creating a billing invoice."""
    contract_id: UUID
    customer_id: UUID
    warehouse_id: Optional[UUID] = None
    period_start: date
    period_end: date
    invoice_date: date
    discount_amount: Decimal = Field(default=Decimal("0"))
    discount_reason: Optional[str] = Field(None, max_length=200)
    adjustment_amount: Decimal = Field(default=Decimal("0"))
    adjustment_reason: Optional[str] = Field(None, max_length=200)
    tax_rate: Decimal = Field(default=Decimal("18"))
    notes: Optional[str] = None


class BillingInvoiceUpdate(BaseModel):
    """Schema for updating a billing invoice."""
    discount_amount: Optional[Decimal] = None
    discount_reason: Optional[str] = Field(None, max_length=200)
    adjustment_amount: Optional[Decimal] = None
    adjustment_reason: Optional[str] = Field(None, max_length=200)
    notes: Optional[str] = None
    internal_notes: Optional[str] = None


class BillingInvoiceResponse(BaseModel):
    """Schema for billing invoice response."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    invoice_number: str
    status: InvoiceStatus
    contract_id: UUID
    customer_id: UUID
    warehouse_id: Optional[UUID]
    period_start: date
    period_end: date
    invoice_date: date
    due_date: date
    storage_amount: Decimal
    handling_amount: Decimal
    vas_amount: Decimal
    labor_amount: Decimal
    subtotal: Decimal
    discount_amount: Decimal
    discount_reason: Optional[str]
    adjustment_amount: Decimal
    adjustment_reason: Optional[str]
    tax_amount: Decimal
    tax_rate: Decimal
    total_amount: Decimal
    paid_amount: Decimal
    balance_due: Decimal
    late_fee: Decimal
    currency: str
    summary: Optional[Dict[str, Any]]
    sent_at: Optional[datetime]
    sent_to: Optional[str]
    last_payment_date: Optional[date]
    payment_reference: Optional[str]
    notes: Optional[str]
    internal_notes: Optional[str]
    disputed_at: Optional[datetime]
    dispute_reason: Optional[str]
    dispute_resolved_at: Optional[datetime]
    created_by: Optional[UUID]
    approved_by: Optional[UUID]
    approved_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    line_items: Optional[List[BillingInvoiceItemResponse]] = None


class InvoiceSend(BaseModel):
    """Schema for sending an invoice."""
    email: str = Field(..., max_length=200)
    cc: Optional[List[str]] = None
    message: Optional[str] = None


class InvoicePayment(BaseModel):
    """Schema for recording a payment."""
    amount: Decimal
    payment_date: date
    payment_reference: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None


class InvoiceDispute(BaseModel):
    """Schema for disputing an invoice."""
    reason: str


class GenerateInvoice(BaseModel):
    """Schema for generating an invoice."""
    contract_id: UUID
    period_start: date
    period_end: date
    include_storage: bool = True
    include_handling: bool = True
    include_vas: bool = True
    apply_minimums: bool = True


# ============================================================================
# DASHBOARD SCHEMAS
# ============================================================================

class BillingDashboard(BaseModel):
    """Dashboard statistics for billing."""
    # Contract Stats
    active_contracts: int
    total_contracts: int

    # Invoice Stats
    pending_invoices: int
    sent_invoices: int
    overdue_invoices: int
    disputed_invoices: int

    # Financial MTD
    total_billed_mtd: Decimal
    total_collected_mtd: Decimal
    total_outstanding: Decimal

    # Breakdown MTD
    storage_revenue_mtd: Decimal
    handling_revenue_mtd: Decimal
    vas_revenue_mtd: Decimal

    # Unbilled Charges
    unbilled_storage: Decimal
    unbilled_handling: Decimal
    unbilled_vas: Decimal

    # Recent Activity
    recent_invoices: List[BillingInvoiceResponse]
    recent_payments: List[Dict[str, Any]]
