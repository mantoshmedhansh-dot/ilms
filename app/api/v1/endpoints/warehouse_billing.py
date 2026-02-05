"""
Warehouse Billing API Endpoints - Phase 10: Storage & Operations Billing.

API endpoints for warehouse billing including:
- Billing contracts
- Rate cards
- Storage/handling/VAS charges
- Invoice generation and management
"""
from datetime import date
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.api.deps import get_current_user, require_permissions
from app.models.user import User
from app.models.warehouse_billing import ContractStatus, InvoiceStatus, ChargeCategory
from app.schemas.warehouse_billing import (
    BillingContractCreate, BillingContractUpdate, BillingContractResponse,
    BillingRateCardCreate, BillingRateCardUpdate, BillingRateCardResponse,
    StorageChargeCreate, StorageChargeResponse,
    HandlingChargeCreate, HandlingChargeResponse,
    VASChargeCreate, VASChargeResponse,
    BillingInvoiceCreate, BillingInvoiceUpdate, BillingInvoiceResponse,
    InvoiceSend, InvoicePayment, GenerateInvoice,
    BillingDashboard
)
from app.services.warehouse_billing_service import WarehouseBillingService

router = APIRouter()


# ============================================================================
# BILLING CONTRACTS
# ============================================================================

@router.post(
    "/contracts",
    response_model=BillingContractResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Billing Contract"
)
async def create_contract(
    data: BillingContractCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:manage"]))
):
    """Create a billing contract."""
    service = WarehouseBillingService(db, current_user.tenant_id)
    return await service.create_contract(data, current_user.id)


@router.get(
    "/contracts",
    response_model=List[BillingContractResponse],
    summary="List Billing Contracts"
)
async def list_contracts(
    customer_id: Optional[UUID] = None,
    warehouse_id: Optional[UUID] = None,
    status: Optional[ContractStatus] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:read"]))
):
    """List billing contracts."""
    service = WarehouseBillingService(db, current_user.tenant_id)
    contracts, _ = await service.list_contracts(
        customer_id=customer_id,
        warehouse_id=warehouse_id,
        status=status,
        skip=skip,
        limit=limit
    )
    return contracts


@router.get(
    "/contracts/{contract_id}",
    response_model=BillingContractResponse,
    summary="Get Billing Contract"
)
async def get_contract(
    contract_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:read"]))
):
    """Get billing contract details."""
    service = WarehouseBillingService(db, current_user.tenant_id)
    contract = await service.get_contract(contract_id)
    if not contract:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contract not found"
        )
    return contract


@router.patch(
    "/contracts/{contract_id}",
    response_model=BillingContractResponse,
    summary="Update Billing Contract"
)
async def update_contract(
    contract_id: UUID,
    data: BillingContractUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:manage"]))
):
    """Update billing contract."""
    service = WarehouseBillingService(db, current_user.tenant_id)
    contract = await service.update_contract(contract_id, data)
    if not contract:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contract not found"
        )
    return contract


@router.post(
    "/contracts/{contract_id}/activate",
    response_model=BillingContractResponse,
    summary="Activate Contract"
)
async def activate_contract(
    contract_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:manage"]))
):
    """Activate a billing contract."""
    service = WarehouseBillingService(db, current_user.tenant_id)
    contract = await service.activate_contract(contract_id, current_user.id)
    if not contract:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Contract not found or not in draft status"
        )
    return contract


# ============================================================================
# RATE CARDS
# ============================================================================

@router.post(
    "/contracts/{contract_id}/rate-cards",
    response_model=BillingRateCardResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add Rate Card"
)
async def add_rate_card(
    contract_id: UUID,
    data: BillingRateCardCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:manage"]))
):
    """Add rate card to contract."""
    service = WarehouseBillingService(db, current_user.tenant_id)
    rate_card = await service.add_rate_card(contract_id, data)
    if not rate_card:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contract not found"
        )
    return rate_card


@router.patch(
    "/rate-cards/{rate_card_id}",
    response_model=BillingRateCardResponse,
    summary="Update Rate Card"
)
async def update_rate_card(
    rate_card_id: UUID,
    data: BillingRateCardUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:manage"]))
):
    """Update rate card."""
    service = WarehouseBillingService(db, current_user.tenant_id)
    rate_card = await service.update_rate_card(rate_card_id, data)
    if not rate_card:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rate card not found"
        )
    return rate_card


# ============================================================================
# CHARGES
# ============================================================================

@router.post(
    "/charges/storage",
    response_model=StorageChargeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Storage Charge"
)
async def create_storage_charge(
    data: StorageChargeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:manage"]))
):
    """Create a storage charge."""
    service = WarehouseBillingService(db, current_user.tenant_id)
    return await service.create_storage_charge(data)


@router.post(
    "/charges/handling",
    response_model=HandlingChargeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Handling Charge"
)
async def create_handling_charge(
    data: HandlingChargeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:manage"]))
):
    """Create a handling charge."""
    service = WarehouseBillingService(db, current_user.tenant_id)
    return await service.create_handling_charge(data)


@router.post(
    "/charges/vas",
    response_model=VASChargeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create VAS Charge"
)
async def create_vas_charge(
    data: VASChargeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:manage"]))
):
    """Create a VAS charge."""
    service = WarehouseBillingService(db, current_user.tenant_id)
    return await service.create_vas_charge(data)


# ============================================================================
# INVOICES
# ============================================================================

@router.post(
    "/invoices/generate",
    response_model=BillingInvoiceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate Invoice"
)
async def generate_invoice(
    data: GenerateInvoice,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:manage"]))
):
    """Generate an invoice from unbilled charges."""
    service = WarehouseBillingService(db, current_user.tenant_id)
    return await service.generate_invoice(data, current_user.id)


@router.get(
    "/invoices",
    response_model=List[BillingInvoiceResponse],
    summary="List Invoices"
)
async def list_invoices(
    customer_id: Optional[UUID] = None,
    warehouse_id: Optional[UUID] = None,
    status: Optional[InvoiceStatus] = None,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:read"]))
):
    """List billing invoices."""
    service = WarehouseBillingService(db, current_user.tenant_id)
    invoices, _ = await service.list_invoices(
        customer_id=customer_id,
        warehouse_id=warehouse_id,
        status=status,
        from_date=from_date,
        to_date=to_date,
        skip=skip,
        limit=limit
    )
    return invoices


@router.get(
    "/invoices/{invoice_id}",
    response_model=BillingInvoiceResponse,
    summary="Get Invoice"
)
async def get_invoice(
    invoice_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:read"]))
):
    """Get invoice details."""
    service = WarehouseBillingService(db, current_user.tenant_id)
    invoice = await service.get_invoice(invoice_id)
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )
    return invoice


@router.post(
    "/invoices/{invoice_id}/send",
    response_model=BillingInvoiceResponse,
    summary="Send Invoice"
)
async def send_invoice(
    invoice_id: UUID,
    data: InvoiceSend,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:manage"]))
):
    """Send an invoice to customer."""
    service = WarehouseBillingService(db, current_user.tenant_id)
    invoice = await service.send_invoice(invoice_id, data)
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invoice not found or cannot be sent"
        )
    return invoice


@router.post(
    "/invoices/{invoice_id}/payment",
    response_model=BillingInvoiceResponse,
    summary="Record Payment"
)
async def record_payment(
    invoice_id: UUID,
    data: InvoicePayment,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:manage"]))
):
    """Record a payment for an invoice."""
    service = WarehouseBillingService(db, current_user.tenant_id)
    invoice = await service.record_payment(invoice_id, data)
    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invoice not found"
        )
    return invoice


# ============================================================================
# DASHBOARD
# ============================================================================

@router.get(
    "/dashboard",
    response_model=BillingDashboard,
    summary="Get Billing Dashboard"
)
async def get_dashboard(
    warehouse_id: Optional[UUID] = None,
    from_date: date = Query(default=None),
    to_date: date = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:read"]))
):
    """Get billing dashboard statistics."""
    if not from_date:
        from_date = date.today().replace(day=1)
    if not to_date:
        to_date = date.today()

    service = WarehouseBillingService(db, current_user.tenant_id)
    return await service.get_dashboard(warehouse_id, from_date, to_date)
