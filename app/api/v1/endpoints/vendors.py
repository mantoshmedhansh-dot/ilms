"""API endpoints for Vendor/Supplier management."""
from typing import Optional, List
import uuid
from uuid import UUID
from datetime import date, timezone
from decimal import Decimal
import logging

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.vendor import (
    Vendor, VendorType, VendorStatus, VendorGrade,
    VendorLedger, VendorTransactionType, VendorContact
)
from app.models.user import User
from app.models.accounting import ChartOfAccount, AccountType, AccountSubType
from app.schemas.vendor import (
    VendorCreate, VendorUpdate, VendorResponse, VendorBrief, VendorListResponse,
    VendorLedgerCreate, VendorLedgerResponse, VendorLedgerListResponse,
    VendorContactCreate, VendorContactResponse,
    VendorPaymentCreate, VendorPaymentResponse,
    VendorAgingResponse, VendorAgingReport, VendorAgingBucket,
)
from app.api.deps import DB, CurrentUser, get_current_user, require_permissions
from app.services.audit_service import AuditService
from app.services.approval_service import ApprovalService
from app.models.approval import ApprovalEntityType
from app.core.module_decorators import require_module

# Sundry Creditors parent account ID (2101)
SUNDRY_CREDITORS_PARENT_ID = "a8178c89-9c40-49c7-85cb-4fbd879660f5"

router = APIRouter()


# ==================== Next Code Generation ====================

# Type prefix mapping for vendor codes
VENDOR_TYPE_PREFIX_MAP = {
    VendorType.MANUFACTURER: "MFR",
    VendorType.IMPORTER: "IMP",
    VendorType.DISTRIBUTOR: "DST",
    VendorType.TRADER: "TRD",
    VendorType.SERVICE_PROVIDER: "SVC",
    VendorType.RAW_MATERIAL: "RAW",
    VendorType.SPARE_PARTS: "SPR",
    VendorType.CONSUMABLES: "CNS",
    VendorType.TRANSPORTER: "TRN",
    VendorType.CONTRACTOR: "CTR",
}


async def get_next_global_vendor_number(db: DB) -> int:
    """Get the next global vendor sequence number across ALL vendor types."""
    # Find the highest number from ALL vendor codes (format: VND-XXX-NNNNN)
    result = await db.execute(
        select(Vendor.vendor_code)
        .where(Vendor.vendor_code.like("VND-%"))
        .order_by(Vendor.vendor_code.desc())
    )
    all_codes = result.scalars().all()

    max_num = 0
    for code in all_codes:
        try:
            # Extract the number part from VND-XXX-NNNNN format
            parts = code.split("-")
            if len(parts) >= 3:
                num = int(parts[2])
                if num > max_num:
                    max_num = num
        except (IndexError, ValueError):
            continue

    return max_num + 1


async def get_next_vendor_gl_account_code(db: DB) -> str:
    """Get the next available GL account code for vendors (under 2101 Sundry Creditors).

    Format: 21XX where XX starts from 12 (since 2111 is Trade Creditors)
    """
    # Find the highest vendor GL account code in 21XX range
    result = await db.execute(
        select(ChartOfAccount.account_code)
        .where(
            and_(
                ChartOfAccount.account_code.like("21%"),
                ChartOfAccount.parent_id == uuid.UUID(SUNDRY_CREDITORS_PARENT_ID)
            )
        )
        .order_by(ChartOfAccount.account_code.desc())
    )
    existing_codes = result.scalars().all()

    max_num = 2111  # Start after Trade Creditors (2111)
    for code in existing_codes:
        try:
            num = int(code)
            if num > max_num:
                max_num = num
        except ValueError:
            continue

    return str(max_num + 1)


async def create_vendor_gl_account(db: DB, vendor: Vendor) -> ChartOfAccount:
    """Create a GL account for a vendor under Sundry Creditors (2101).

    This allows the vendor to appear in journal entries for payments.
    """
    # Get next account code
    account_code = await get_next_vendor_gl_account_code(db)

    # Create GL account
    gl_account = ChartOfAccount(
        account_code=account_code,
        account_name=vendor.legal_name or vendor.name,
        description=f"Vendor: {vendor.vendor_code} - {vendor.name}",
        account_type=AccountType.LIABILITY.value,
        account_sub_type=AccountSubType.ACCOUNTS_PAYABLE.value,
        parent_id=uuid.UUID(SUNDRY_CREDITORS_PARENT_ID),
        level=2,  # Child of Sundry Creditors
        is_group=False,
        opening_balance=vendor.opening_balance or Decimal("0"),
        current_balance=vendor.current_balance or Decimal("0"),
    )

    db.add(gl_account)
    await db.flush()  # Get the ID without committing

    # Link GL account to vendor
    vendor.gl_account_id = gl_account.id

    logging.info(f"Created GL account {account_code} - {gl_account.account_name} for vendor {vendor.vendor_code}")

    return gl_account


@router.get("/next-code")
@require_module("procurement")
async def get_next_vendor_code(
    db: DB,
    vendor_type: VendorType = Query(VendorType.MANUFACTURER, description="Vendor type for code prefix"),
):
    """Get the next available vendor code based on vendor type.

    Format: VND-{TYPE}-{GLOBAL_NUMBER}
    Example: VND-MFR-00001, VND-SPR-00002, VND-DST-00003

    The number is a SINGLE GLOBAL SEQUENCE across all vendor types.
    """
    type_prefix = VENDOR_TYPE_PREFIX_MAP.get(vendor_type, "OTH")
    next_num = await get_next_global_vendor_number(db)
    next_code = f"VND-{type_prefix}-{str(next_num).zfill(5)}"

    return {"next_code": next_code, "prefix": f"VND-{type_prefix}"}


# ==================== Vendor CRUD ====================

@router.post("", response_model=VendorResponse, status_code=status.HTTP_201_CREATED)
@require_module("procurement")
async def create_vendor(
    vendor_in: VendorCreate,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Create a new vendor/supplier."""
    # Check for duplicate GSTIN
    if vendor_in.gstin:
        existing = await db.execute(
            select(Vendor).where(Vendor.gstin == vendor_in.gstin)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Vendor with GSTIN {vendor_in.gstin} already exists"
            )

    # Generate vendor code with global sequence
    # Format: VND-{TYPE}-{GLOBAL_NUMBER} (e.g., VND-MFR-00001, VND-SPR-00002)
    type_prefix = VENDOR_TYPE_PREFIX_MAP.get(vendor_in.vendor_type, "OTH")
    next_num = await get_next_global_vendor_number(db)
    vendor_code = f"VND-{type_prefix}-{str(next_num).zfill(5)}"

    # Extract state code from GSTIN
    gst_state_code = vendor_in.gstin[:2] if vendor_in.gstin else None

    vendor = Vendor(
        **vendor_in.model_dump(exclude={"opening_balance"}),
        vendor_code=vendor_code,
        gst_state_code=gst_state_code,
        opening_balance=vendor_in.opening_balance,
        current_balance=vendor_in.opening_balance,
    )

    db.add(vendor)
    await db.flush()  # Get vendor ID without committing

    # Auto-create GL account for vendor under Sundry Creditors
    try:
        gl_account = await create_vendor_gl_account(db, vendor)
        logging.info(f"Auto-created GL account {gl_account.account_code} for vendor {vendor_code}")
    except Exception as e:
        logging.warning(f"Failed to create GL account for vendor {vendor_code}: {e}")
        # Continue without GL account - can be linked later

    await db.commit()
    await db.refresh(vendor)

    # Create opening balance ledger entry if provided
    if vendor_in.opening_balance > 0:
        ledger_entry = VendorLedger(
            vendor_id=vendor.id,
            transaction_type=VendorTransactionType.OPENING_BALANCE,
            transaction_date=date.today(),
            reference_type="OPENING",
            reference_number=vendor_code,
            credit_amount=vendor_in.opening_balance,
            running_balance=vendor_in.opening_balance,
            narration="Opening balance",
            created_by=current_user.id,
        )
        db.add(ledger_entry)
        await db.commit()

    # Create approval request for vendor onboarding
    if vendor.status == VendorStatus.PENDING_APPROVAL:
        approval = await ApprovalService.create_approval_request(
            db=db,
            entity_type=ApprovalEntityType.VENDOR_ONBOARDING,
            entity_id=vendor.id,
            entity_number=vendor_code,
            amount=vendor_in.opening_balance or Decimal("0"),
            title=f"Vendor Onboarding: {vendor.name}",
            requested_by=current_user.id,
            description=f"New vendor registration - {vendor.vendor_type if vendor.vendor_type else 'General'}",
            priority=5,
        )
        await db.commit()

    # Audit log
    audit_service = AuditService(db)
    await audit_service.log(
        action="CREATE",
        entity_type="Vendor",
        entity_id=vendor.id,
        user_id=current_user.id,
        new_values={"vendor_code": vendor_code, "name": vendor.name}
    )

    return vendor


@router.get("", response_model=VendorListResponse)
@require_module("procurement")
async def list_vendors(
    db: DB,
    current_user: User = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    search: Optional[str] = None,
    vendor_type: Optional[VendorType] = None,
    status: Optional[VendorStatus] = None,
    city: Optional[str] = None,
    state: Optional[str] = None,
):
    """List all vendors with filtering."""
    query = select(Vendor)
    count_query = select(func.count(Vendor.id))

    # Apply filters
    filters = []
    if search:
        search_filter = or_(
            Vendor.name.ilike(f"%{search}%"),
            Vendor.vendor_code.ilike(f"%{search}%"),
            Vendor.gstin.ilike(f"%{search}%"),
        )
        filters.append(search_filter)

    if vendor_type:
        filters.append(Vendor.vendor_type == vendor_type)
    if status:
        filters.append(Vendor.status == status)
    if city:
        filters.append(Vendor.city.ilike(f"%{city}%"))
    if state:
        filters.append(Vendor.state.ilike(f"%{state}%"))

    if filters:
        query = query.where(and_(*filters))
        count_query = count_query.where(and_(*filters))

    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Get paginated results
    query = query.order_by(Vendor.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    vendors = result.scalars().all()

    return VendorListResponse(
        items=[VendorBrief.model_validate(v) for v in vendors],
        total=total,
        page=(skip // limit) + 1 if limit > 0 else 1,
        size=limit,
        pages=(total + limit - 1) // limit if limit > 0 else 1
    )


@router.get("/dropdown", response_model=List[VendorBrief])
@require_module("procurement")
async def get_vendors_dropdown(
    db: DB,
    vendor_type: Optional[VendorType] = None,
    active_only: bool = True,
    current_user: User = Depends(get_current_user),
):
    """Get vendors for dropdown selection."""
    query = select(Vendor)

    if active_only:
        query = query.where(Vendor.status == VendorStatus.ACTIVE)
    if vendor_type:
        query = query.where(Vendor.vendor_type == vendor_type)

    query = query.order_by(Vendor.name)
    result = await db.execute(query)
    vendors = result.scalars().all()

    return [VendorBrief.model_validate(v) for v in vendors]


@router.get("/{vendor_id}", response_model=VendorResponse)
@require_module("procurement")
async def get_vendor(
    vendor_id: UUID,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Get vendor by ID."""
    result = await db.execute(
        select(Vendor).where(Vendor.id == vendor_id)
    )
    vendor = result.scalar_one_or_none()

    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vendor not found"
        )

    return vendor


@router.put("/{vendor_id}", response_model=VendorResponse)
@require_module("procurement")
async def update_vendor(
    vendor_id: UUID,
    vendor_in: VendorUpdate,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Update vendor details."""
    result = await db.execute(
        select(Vendor).where(Vendor.id == vendor_id)
    )
    vendor = result.scalar_one_or_none()

    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vendor not found"
        )

    update_data = vendor_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(vendor, field, value)

    vendor.updated_by = current_user.id

    await db.commit()
    await db.refresh(vendor)

    # Audit log
    audit_service = AuditService(db)
    await audit_service.log(
        action="UPDATE",
        entity_type="Vendor",
        entity_id=vendor.id,
        user_id=current_user.id,
        new_values={"updated_fields": list(update_data.keys())}
    )

    return vendor


@router.delete("/{vendor_id}", status_code=status.HTTP_204_NO_CONTENT)
@require_module("procurement")
async def delete_vendor(
    vendor_id: UUID,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Soft delete vendor (mark as inactive)."""
    result = await db.execute(
        select(Vendor).where(Vendor.id == vendor_id)
    )
    vendor = result.scalar_one_or_none()

    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vendor not found"
        )

    # Check for outstanding balance
    if vendor.current_balance != 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete vendor with outstanding balance of {vendor.current_balance}"
        )

    vendor.status = VendorStatus.INACTIVE.value
    vendor.updated_by = current_user.id

    await db.commit()

    # Audit log
    audit_service = AuditService(db)
    await audit_service.log(
        action="DELETE",
        entity_type="Vendor",
        entity_id=vendor.id,
        user_id=current_user.id,
        new_values={"vendor_code": vendor.vendor_code}
    
    )


# ==================== Vendor Verification ====================

@router.post("/{vendor_id}/verify", response_model=VendorResponse)
@require_module("procurement")
async def verify_vendor(
    vendor_id: UUID,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Verify vendor details (GSTIN, Bank, etc.)."""
    result = await db.execute(
        select(Vendor).where(Vendor.id == vendor_id)
    )
    vendor = result.scalar_one_or_none()

    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vendor not found"
        )

    # TODO: Add actual GSTIN verification via GST Portal API
    # TODO: Add bank account verification via penny drop

    from datetime import date, timezonetime
    vendor.is_verified = True
    vendor.verified_at = datetime.now(timezone.utc)
    vendor.verified_by = current_user.id
    vendor.status = VendorStatus.ACTIVE.value

    await db.commit()
    await db.refresh(vendor)

    return vendor


# ==================== Vendor Ledger ====================

@router.get("/{vendor_id}/ledger", response_model=VendorLedgerListResponse)
@require_module("procurement")
async def get_vendor_ledger(
    vendor_id: UUID,
    db: DB,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    current_user: User = Depends(get_current_user),
):
    """Get vendor ledger entries."""
    # Verify vendor exists
    vendor_result = await db.execute(
        select(Vendor).where(Vendor.id == vendor_id)
    )
    vendor = vendor_result.scalar_one_or_none()
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vendor not found"
        )

    query = select(VendorLedger).where(VendorLedger.vendor_id == vendor_id)
    count_query = select(func.count(VendorLedger.id)).where(
        VendorLedger.vendor_id == vendor_id
    )

    if start_date:
        query = query.where(VendorLedger.transaction_date >= start_date)
        count_query = count_query.where(VendorLedger.transaction_date >= start_date)
    if end_date:
        query = query.where(VendorLedger.transaction_date <= end_date)
        count_query = count_query.where(VendorLedger.transaction_date <= end_date)

    # Get totals
    totals_query = select(
        func.coalesce(func.sum(VendorLedger.debit_amount), 0).label("total_debit"),
        func.coalesce(func.sum(VendorLedger.credit_amount), 0).label("total_credit"),
    ).where(VendorLedger.vendor_id == vendor_id)

    if start_date:
        totals_query = totals_query.where(VendorLedger.transaction_date >= start_date)
    if end_date:
        totals_query = totals_query.where(VendorLedger.transaction_date <= end_date)

    totals_result = await db.execute(totals_query)
    totals = totals_result.one()

    # Get count
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Get paginated entries
    query = query.order_by(
        VendorLedger.transaction_date.desc(),
        VendorLedger.created_at.desc()
    ).offset(skip).limit(limit)

    result = await db.execute(query)
    entries = result.scalars().all()

    return VendorLedgerListResponse(
        items=[VendorLedgerResponse.model_validate(e) for e in entries],
        total=total,
        total_debit=totals.total_debit,
        total_credit=totals.total_credit,
        closing_balance=vendor.current_balance,
        skip=skip,
        limit=limit
    )


@router.post("/{vendor_id}/payment", response_model=VendorPaymentResponse)
@require_module("procurement")
async def record_vendor_payment(
    vendor_id: UUID,
    payment_in: VendorPaymentCreate,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Record payment to vendor."""
    # Verify vendor
    vendor_result = await db.execute(
        select(Vendor).where(Vendor.id == vendor_id)
    )
    vendor = vendor_result.scalar_one_or_none()
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vendor not found"
        )

    # Calculate net amount after TDS
    net_amount = payment_in.amount - payment_in.tds_amount

    # Create ledger entry
    new_balance = vendor.current_balance - payment_in.amount

    ledger_entry = VendorLedger(
        vendor_id=vendor_id,
        transaction_type=VendorTransactionType.PAYMENT,
        transaction_date=payment_in.payment_date,
        reference_type="PAYMENT",
        reference_number=f"PAY-{date.today().strftime('%Y%m%d')}-{str(vendor.total_po_count + 1).zfill(4)}",
        debit_amount=payment_in.amount,
        tds_amount=payment_in.tds_amount,
        tds_section=payment_in.tds_section,
        payment_mode=payment_in.payment_mode,
        payment_reference=payment_in.payment_reference,
        bank_name=payment_in.bank_name,
        cheque_number=payment_in.cheque_number,
        cheque_date=payment_in.cheque_date,
        narration=payment_in.narration,
        running_balance=new_balance,
        created_by=current_user.id,
    )

    db.add(ledger_entry)

    # Update vendor balance
    vendor.current_balance = new_balance
    vendor.last_payment_date = payment_in.payment_date

    await db.commit()
    await db.refresh(ledger_entry)

    # Audit log
    audit_service = AuditService(db)
    await audit_service.log(
        action="CREATE",
        entity_type="VendorPayment",
        entity_id=ledger_entry.id,
        user_id=current_user.id,
        new_values={
            "vendor_id": str(vendor_id),
            "amount": str(payment_in.amount),
            "payment_mode": payment_in.payment_mode
        }
    )

    return VendorPaymentResponse(
        id=ledger_entry.id,
        vendor_id=vendor_id,
        vendor_name=vendor.name,
        amount=payment_in.amount,
        tds_amount=payment_in.tds_amount,
        net_amount=net_amount,
        payment_date=payment_in.payment_date,
        payment_mode=payment_in.payment_mode,
        payment_reference=payment_in.payment_reference,
        ledger_entry_id=ledger_entry.id,
        created_at=ledger_entry.created_at
    )


# ==================== Vendor Contacts ====================

@router.get("/{vendor_id}/contacts", response_model=List[VendorContactResponse])
@require_module("procurement")
async def get_vendor_contacts(
    vendor_id: UUID,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Get all contacts for a vendor."""
    result = await db.execute(
        select(VendorContact)
        .where(VendorContact.vendor_id == vendor_id)
        .order_by(VendorContact.is_primary.desc(), VendorContact.name)
    )
    contacts = result.scalars().all()
    return [VendorContactResponse.model_validate(c) for c in contacts]


@router.post("/{vendor_id}/contacts", response_model=VendorContactResponse, status_code=status.HTTP_201_CREATED)
@require_module("procurement")
async def add_vendor_contact(
    vendor_id: UUID,
    contact_in: VendorContactCreate,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Add a contact to vendor."""
    # Verify vendor exists
    vendor_result = await db.execute(
        select(Vendor).where(Vendor.id == vendor_id)
    )
    if not vendor_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vendor not found"
        )

    # If this is primary, unset other primary contacts
    if contact_in.is_primary:
        await db.execute(
            select(VendorContact)
            .where(VendorContact.vendor_id == vendor_id)
        )
        existing_contacts = await db.execute(
            select(VendorContact).where(
                and_(
                    VendorContact.vendor_id == vendor_id,
                    VendorContact.is_primary == True
                )
            )
        )
        for contact in existing_contacts.scalars().all():
            contact.is_primary = False

    contact = VendorContact(
        **contact_in.model_dump(),
        vendor_id=vendor_id,
    )

    db.add(contact)
    await db.commit()
    await db.refresh(contact)

    return contact


# ==================== Vendor GL Account Management ====================

@router.post("/create-gl-accounts", status_code=status.HTTP_200_OK)
@require_module("procurement")
async def create_gl_accounts_for_existing_vendors(
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """
    One-time migration: Create GL accounts for all existing vendors that don't have one.

    This creates a GL account under Sundry Creditors (2101) for each vendor,
    allowing them to appear in journal entries for payment tracking.
    """
    # Find vendors without GL accounts
    result = await db.execute(
        select(Vendor).where(Vendor.gl_account_id.is_(None))
    )
    vendors_without_gl = result.scalars().all()

    if not vendors_without_gl:
        return {"message": "All vendors already have GL accounts", "created": 0}

    created_count = 0
    errors = []

    for vendor in vendors_without_gl:
        try:
            gl_account = await create_vendor_gl_account(db, vendor)
            created_count += 1
            logging.info(f"Created GL account {gl_account.account_code} for vendor {vendor.vendor_code}")
        except Exception as e:
            errors.append({"vendor_code": vendor.vendor_code, "error": str(e)})
            logging.error(f"Failed to create GL account for vendor {vendor.vendor_code}: {e}")

    await db.commit()

    return {
        "message": f"Created GL accounts for {created_count} vendors",
        "created": created_count,
        "errors": errors if errors else None
    }


@router.get("/{vendor_id}/gl-account")
@require_module("procurement")
async def get_vendor_gl_account(
    vendor_id: UUID,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Get the GL account details for a vendor including bank information."""
    result = await db.execute(
        select(Vendor)
        .options(selectinload(Vendor.gl_account))
        .where(Vendor.id == vendor_id)
    )
    vendor = result.scalar_one_or_none()

    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")

    gl_info = None
    if vendor.gl_account:
        gl_info = {
            "account_code": vendor.gl_account.account_code,
            "account_name": vendor.gl_account.account_name,
            "current_balance": float(vendor.gl_account.current_balance or 0),
        }

    return {
        "vendor_code": vendor.vendor_code,
        "vendor_name": vendor.name,
        "gl_account": gl_info,
        "bank_details": {
            "bank_name": vendor.bank_name,
            "bank_branch": vendor.bank_branch,
            "account_number": vendor.bank_account_number,
            "ifsc_code": vendor.bank_ifsc,
            "account_type": vendor.bank_account_type,
            "beneficiary_name": vendor.beneficiary_name,
        } if vendor.bank_name else None
    }


# ==================== Vendor Aging Report ====================

@router.get("/reports/aging", response_model=VendorAgingReport)
@require_module("procurement")
async def get_vendor_aging_report(
    db: DB,
    as_of_date: date = Query(default_factory=date.today),
    vendor_type: Optional[VendorType] = None,
    current_user: User = Depends(get_current_user),
):
    """Get vendor aging report (Accounts Payable aging)."""
    query = select(Vendor).where(Vendor.current_balance > 0)

    if vendor_type:
        query = query.where(Vendor.vendor_type == vendor_type)

    result = await db.execute(query)
    vendors = result.scalars().all()

    vendor_aging_list = []
    summary_buckets = {
        "0-30": Decimal("0"),
        "31-60": Decimal("0"),
        "61-90": Decimal("0"),
        "90+": Decimal("0"),
    }
    summary_counts = {
        "0-30": 0,
        "31-60": 0,
        "61-90": 0,
        "90+": 0,
    }
    total_outstanding = Decimal("0")

    for vendor in vendors:
        # Get unpaid invoices/entries for this vendor
        ledger_query = select(VendorLedger).where(
            and_(
                VendorLedger.vendor_id == vendor.id,
                VendorLedger.is_settled == False,
                VendorLedger.credit_amount > 0  # Only invoices (credits)
            )
        )
        ledger_result = await db.execute(ledger_query)
        entries = ledger_result.scalars().all()

        buckets = {
            "0-30": Decimal("0"),
            "31-60": Decimal("0"),
            "61-90": Decimal("0"),
            "90+": Decimal("0"),
        }

        for entry in entries:
            days = (as_of_date - entry.transaction_date).days
            amount = entry.credit_amount - entry.debit_amount

            if amount <= 0:
                continue

            if days <= 30:
                buckets["0-30"] += amount
                summary_buckets["0-30"] += amount
            elif days <= 60:
                buckets["31-60"] += amount
                summary_buckets["31-60"] += amount
            elif days <= 90:
                buckets["61-90"] += amount
                summary_buckets["61-90"] += amount
            else:
                buckets["90+"] += amount
                summary_buckets["90+"] += amount

        vendor_total = sum(buckets.values())
        if vendor_total > 0:
            total_outstanding += vendor_total

            vendor_aging_list.append(VendorAgingResponse(
                vendor_id=vendor.id,
                vendor_code=vendor.vendor_code,
                vendor_name=vendor.name,
                total_outstanding=vendor_total,
                buckets=[
                    VendorAgingBucket(bucket=k, amount=v, count=1 if v > 0 else 0)
                    for k, v in buckets.items()
                ]
            ))

    return VendorAgingReport(
        as_of_date=as_of_date,
        vendors=vendor_aging_list,
        summary=[
            VendorAgingBucket(bucket=k, amount=v, count=summary_counts.get(k, 0))
            for k, v in summary_buckets.items()
        ],
        total_outstanding=total_outstanding
    )


# ==================== Vendor Statistics ====================

@router.get("/stats/summary")
@require_module("procurement")
async def get_vendor_stats(
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Get vendor statistics summary."""
    # Total vendors by status
    status_query = select(
        Vendor.status,
        func.count(Vendor.id).label("count")
    ).group_by(Vendor.status)

    status_result = await db.execute(status_query)
    status_counts = {row.status: row.count for row in status_result.all()}

    # Total vendors by type
    type_query = select(
        Vendor.vendor_type,
        func.count(Vendor.id).label("count")
    ).group_by(Vendor.vendor_type)

    type_result = await db.execute(type_query)
    type_counts = {row.vendor_type: row.count for row in type_result.all()}

    # Total outstanding
    outstanding_query = select(
        func.coalesce(func.sum(Vendor.current_balance), 0)
    )
    outstanding_result = await db.execute(outstanding_query)
    total_outstanding = outstanding_result.scalar() or 0

    # Total advances
    advance_query = select(
        func.coalesce(func.sum(Vendor.advance_balance), 0)
    )
    advance_result = await db.execute(advance_query)
    total_advances = advance_result.scalar() or 0

    return {
        "by_status": status_counts,
        "by_type": type_counts,
        "total_outstanding": float(total_outstanding),
        "total_advances": float(total_advances),
        "total_vendors": sum(status_counts.values()),
    }


# ==================== Vendor Orchestration Sync ====================

@router.post("/sync-supplier-codes")
@require_module("procurement")
async def sync_vendor_supplier_codes(
    db: DB,
    current_user: User = Depends(require_permissions("vendor:manage")),
):
    """
    Sync supplier codes for existing approved vendors.

    This is a one-time utility to fix vendors that were approved
    before the orchestration service was implemented.

    Only SPARE_PARTS, MANUFACTURER, and RAW_MATERIAL vendors get supplier codes.
    """
    from app.services.vendor_orchestration_service import VendorOrchestrationService

    orchestration = VendorOrchestrationService(db)
    result = await orchestration.sync_existing_vendors()

    return {
        "success": True,
        "message": f"Synced {result['total_synced']} vendors with supplier codes",
        "details": result
    }
