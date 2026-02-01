"""API endpoints for Company/Business Entity management.

This is the central configuration for the ERP system.
All invoices, POs, GST filings reference this company.
"""
from typing import Optional, List
import uuid
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.company import (
    Company, CompanyType, GSTRegistrationType,
    CompanyBranch, CompanyBankAccount
)
from app.models.user import User
from app.models.accounting import ChartOfAccount, AccountType, AccountSubType
from app.schemas.company import (
    CompanyCreate, CompanyUpdate, CompanyResponse, CompanyBrief, CompanyListResponse,
    CompanyFullResponse,
    CompanyBranchCreate, CompanyBranchUpdate, CompanyBranchResponse, CompanyBranchBrief,
    CompanyBankAccountCreate, CompanyBankAccountUpdate, CompanyBankAccountResponse,
    EInvoiceConfigUpdate, EWayBillConfigUpdate,
)
from app.api.deps import DB, CurrentUser, get_current_user
from app.services.audit_service import AuditService
from app.services.cache_service import get_cache
from app.core.module_decorators import require_module

router = APIRouter()


# ==================== Company CRUD ====================

@router.post("", response_model=CompanyResponse, status_code=status.HTTP_201_CREATED)
@require_module("d2c_storefront")
async def create_company(
    company_in: CompanyCreate,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """
    Create a new company/business entity.

    Only SUPER_ADMIN should typically create companies.
    For single-company ERP, usually only one company exists.
    """
    # Check for duplicate code
    existing = await db.execute(
        select(Company).where(Company.code == company_in.code)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Company with code '{company_in.code}' already exists"
        )

    # Check for duplicate GSTIN
    existing_gstin = await db.execute(
        select(Company).where(Company.gstin == company_in.gstin)
    )
    if existing_gstin.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Company with GSTIN '{company_in.gstin}' already exists"
        )

    # If this is first company or marked as primary, ensure only one primary
    if company_in.is_primary:
        await db.execute(
            select(Company).where(Company.is_primary == True)
        )
        # Unset existing primary if setting new one
        result = await db.execute(select(Company).where(Company.is_primary == True))
        existing_primary = result.scalar_one_or_none()
        if existing_primary:
            existing_primary.is_primary = False

    # Handle password encryption (in production, use proper encryption)
    company_data = company_in.model_dump(exclude={"einvoice_password", "ewb_password"})
    if company_in.einvoice_password:
        company_data["einvoice_password_encrypted"] = company_in.einvoice_password  # TODO: encrypt
    if company_in.ewb_password:
        company_data["ewb_password_encrypted"] = company_in.ewb_password  # TODO: encrypt

    company = Company(**company_data)

    db.add(company)
    await db.commit()
    await db.refresh(company)

    # Audit log
    audit_service = AuditService(db)
    await audit_service.log(
        action="CREATE",
        entity_type="Company",
        entity_id=company.id,
        user_id=current_user.id,
        new_values={"code": company.code, "legal_name": company.legal_name}
    )

    return company


@router.get("", response_model=CompanyListResponse)
@require_module("d2c_storefront")
async def list_companies(
    db: DB,
    current_user: User = Depends(get_current_user),
    is_active: Optional[bool] = None,
):
    """
    List all companies.

    For single-company ERP, this will return only one company.
    Multi-company setup allows multiple entities.
    """
    query = select(Company)

    if is_active is not None:
        query = query.where(Company.is_active == is_active)

    query = query.order_by(Company.is_primary.desc(), Company.created_at.asc())

    result = await db.execute(query)
    companies = result.scalars().all()

    return CompanyListResponse(
        items=companies,
        total=len(companies)
    )


@router.get("/primary", response_model=CompanyFullResponse)
@require_module("d2c_storefront")
async def get_primary_company(
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """
    Get the primary company details.

    This is the most commonly used endpoint to get company info
    for invoices, POs, and other documents.
    """
    query = (
        select(Company)
        .options(
            selectinload(Company.branches),
            selectinload(Company.bank_accounts),
        )
        .where(Company.is_primary == True)
    )

    result = await db.execute(query)
    company = result.scalar_one_or_none()

    if not company:
        # If no primary set, get the first active company
        query = (
            select(Company)
            .options(
                selectinload(Company.branches),
                selectinload(Company.bank_accounts),
            )
            .where(Company.is_active == True)
            .order_by(Company.created_at.asc())
        )
        result = await db.execute(query)
        company = result.scalar_one_or_none()

    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No company configured. Please create a company first."
        )

    return company


@router.put("/primary", response_model=CompanyResponse)
@require_module("d2c_storefront")
async def update_primary_company(
    company_in: CompanyUpdate,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """
    Update the primary company details.

    This is a convenience endpoint that automatically finds and updates
    the primary company without needing to know its ID.
    """
    # Find the primary company
    query = select(Company).where(Company.is_primary == True)
    result = await db.execute(query)
    company = result.scalar_one_or_none()

    if not company:
        # If no primary, get first active company
        query = select(Company).where(Company.is_active == True).order_by(Company.created_at.asc())
        result = await db.execute(query)
        company = result.scalar_one_or_none()

    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No company configured. Please create a company first."
        )

    # Check for duplicate GSTIN if changing
    if company_in.gstin and company_in.gstin != company.gstin:
        existing = await db.execute(
            select(Company).where(
                and_(Company.gstin == company_in.gstin, Company.id != company.id)
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Another company with GSTIN '{company_in.gstin}' already exists"
            )

    # Update fields
    update_data = company_in.model_dump(exclude_unset=True, exclude={"einvoice_password", "ewb_password"})

    # Handle password updates
    if company_in.einvoice_password:
        update_data["einvoice_password_encrypted"] = company_in.einvoice_password
    if company_in.ewb_password:
        update_data["ewb_password_encrypted"] = company_in.ewb_password

    for field, value in update_data.items():
        setattr(company, field, value)

    await db.commit()
    await db.refresh(company)

    # Invalidate storefront company cache so changes appear immediately
    cache = get_cache()
    await cache.delete("company:info")

    # Audit log
    audit_service = AuditService(db)
    await audit_service.log(
        action="UPDATE",
        entity_type="Company",
        entity_id=company.id,
        user_id=current_user.id,
        new_values=update_data
    )

    return company


@router.get("/{company_id}", response_model=CompanyFullResponse)
@require_module("d2c_storefront")
async def get_company(
    company_id: UUID,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Get company details by ID."""
    query = (
        select(Company)
        .options(
            selectinload(Company.branches),
            selectinload(Company.bank_accounts),
        )
        .where(Company.id == company_id)
    )

    result = await db.execute(query)
    company = result.scalar_one_or_none()

    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found"
        )

    return company


@router.put("/{company_id}", response_model=CompanyResponse)
@require_module("d2c_storefront")
async def update_company(
    company_id: UUID,
    company_in: CompanyUpdate,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Update company details."""
    result = await db.execute(
        select(Company).where(Company.id == company_id)
    )
    company = result.scalar_one_or_none()

    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found"
        )

    # Check for duplicate GSTIN if changing
    if company_in.gstin and company_in.gstin != company.gstin:
        existing = await db.execute(
            select(Company).where(
                and_(Company.gstin == company_in.gstin, Company.id != company_id)
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Another company with GSTIN '{company_in.gstin}' already exists"
            )

    # If setting as primary, unset existing primary
    if company_in.is_primary and not company.is_primary:
        result = await db.execute(
            select(Company).where(
                and_(Company.is_primary == True, Company.id != company_id)
            )
        )
        existing_primary = result.scalar_one_or_none()
        if existing_primary:
            existing_primary.is_primary = False

    # Update fields
    update_data = company_in.model_dump(exclude_unset=True, exclude={"einvoice_password", "ewb_password"})

    # Handle password updates
    if company_in.einvoice_password:
        update_data["einvoice_password_encrypted"] = company_in.einvoice_password  # TODO: encrypt
    if company_in.ewb_password:
        update_data["ewb_password_encrypted"] = company_in.ewb_password  # TODO: encrypt

    for field, value in update_data.items():
        setattr(company, field, value)

    await db.commit()
    await db.refresh(company)

    # Invalidate storefront company cache so changes appear immediately
    cache = get_cache()
    await cache.delete("company:info")

    # Audit log
    audit_service = AuditService(db)
    await audit_service.log(
        action="UPDATE",
        entity_type="Company",
        entity_id=company.id,
        user_id=current_user.id,
        new_values=update_data
    )

    return company


@router.delete("/{company_id}", status_code=status.HTTP_204_NO_CONTENT)
@require_module("d2c_storefront")
async def delete_company(
    company_id: UUID,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """
    Delete a company.

    CAUTION: This should only be allowed for companies with no transactions.
    In production, consider soft delete instead.
    """
    result = await db.execute(
        select(Company).where(Company.id == company_id)
    )
    company = result.scalar_one_or_none()

    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found"
        )

    if company.is_primary:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete the primary company. Set another company as primary first."
        )

    # Audit log before deletion
    audit_service = AuditService(db)
    await audit_service.log(
        action="DELETE",
        entity_type="Company",
        entity_id=company.id,
        user_id=current_user.id,
        old_values={"code": company.code, "legal_name": company.legal_name}
    )

    await db.delete(company)
    await db.commit()


# ==================== E-Invoice / E-Way Bill Config ====================

@router.put("/{company_id}/einvoice-config", response_model=CompanyResponse)
@require_module("d2c_storefront")
async def update_einvoice_config(
    company_id: UUID,
    config: EInvoiceConfigUpdate,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Update E-Invoice configuration for a company."""
    result = await db.execute(
        select(Company).where(Company.id == company_id)
    )
    company = result.scalar_one_or_none()

    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found"
        )

    company.einvoice_enabled = config.einvoice_enabled
    company.einvoice_username = config.einvoice_username
    company.einvoice_api_mode = config.einvoice_api_mode
    if config.einvoice_password:
        company.einvoice_password_encrypted = config.einvoice_password  # TODO: encrypt

    await db.commit()
    await db.refresh(company)

    return company


@router.put("/{company_id}/ewb-config", response_model=CompanyResponse)
@require_module("d2c_storefront")
async def update_ewb_config(
    company_id: UUID,
    config: EWayBillConfigUpdate,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Update E-Way Bill configuration for a company."""
    result = await db.execute(
        select(Company).where(Company.id == company_id)
    )
    company = result.scalar_one_or_none()

    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found"
        )

    company.ewb_enabled = config.ewb_enabled
    company.ewb_username = config.ewb_username
    company.ewb_api_mode = config.ewb_api_mode
    if config.ewb_password:
        company.ewb_password_encrypted = config.ewb_password  # TODO: encrypt

    await db.commit()
    await db.refresh(company)

    return company


# ==================== Company Branch CRUD ====================

@router.post("/{company_id}/branches", response_model=CompanyBranchResponse, status_code=status.HTTP_201_CREATED)
@require_module("d2c_storefront")
async def create_company_branch(
    company_id: UUID,
    branch_in: CompanyBranchCreate,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Create a new branch for a company."""
    # Verify company exists
    result = await db.execute(
        select(Company).where(Company.id == company_id)
    )
    company = result.scalar_one_or_none()

    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found"
        )

    # Check for duplicate code within company
    existing = await db.execute(
        select(CompanyBranch).where(
            and_(
                CompanyBranch.company_id == company_id,
                CompanyBranch.code == branch_in.code
            )
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Branch with code '{branch_in.code}' already exists for this company"
        )

    branch = CompanyBranch(
        **branch_in.model_dump(exclude={"company_id"}),
        company_id=company_id
    )

    db.add(branch)
    await db.commit()
    await db.refresh(branch)

    return branch


@router.get("/{company_id}/branches", response_model=List[CompanyBranchBrief])
@require_module("d2c_storefront")
async def list_company_branches(
    company_id: UUID,
    db: DB,
    current_user: User = Depends(get_current_user),
    is_active: Optional[bool] = None,
    branch_type: Optional[str] = None,
):
    """List all branches for a company."""
    query = select(CompanyBranch).where(CompanyBranch.company_id == company_id)

    if is_active is not None:
        query = query.where(CompanyBranch.is_active == is_active)
    if branch_type:
        query = query.where(CompanyBranch.branch_type == branch_type)

    query = query.order_by(CompanyBranch.created_at.asc())

    result = await db.execute(query)
    branches = result.scalars().all()

    return branches


@router.get("/{company_id}/branches/{branch_id}", response_model=CompanyBranchResponse)
@require_module("d2c_storefront")
async def get_company_branch(
    company_id: UUID,
    branch_id: UUID,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Get branch details."""
    result = await db.execute(
        select(CompanyBranch).where(
            and_(
                CompanyBranch.id == branch_id,
                CompanyBranch.company_id == company_id
            )
        )
    )
    branch = result.scalar_one_or_none()

    if not branch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Branch not found"
        )

    return branch


@router.put("/{company_id}/branches/{branch_id}", response_model=CompanyBranchResponse)
@require_module("d2c_storefront")
async def update_company_branch(
    company_id: UUID,
    branch_id: UUID,
    branch_in: CompanyBranchUpdate,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Update branch details."""
    result = await db.execute(
        select(CompanyBranch).where(
            and_(
                CompanyBranch.id == branch_id,
                CompanyBranch.company_id == company_id
            )
        )
    )
    branch = result.scalar_one_or_none()

    if not branch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Branch not found"
        )

    update_data = branch_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(branch, field, value)

    await db.commit()
    await db.refresh(branch)

    return branch


@router.delete("/{company_id}/branches/{branch_id}", status_code=status.HTTP_204_NO_CONTENT)
@require_module("d2c_storefront")
async def delete_company_branch(
    company_id: UUID,
    branch_id: UUID,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Delete a branch."""
    result = await db.execute(
        select(CompanyBranch).where(
            and_(
                CompanyBranch.id == branch_id,
                CompanyBranch.company_id == company_id
            )
        )
    )
    branch = result.scalar_one_or_none()

    if not branch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Branch not found"
        )

    await db.delete(branch)
    await db.commit()


# ==================== Company Bank Account CRUD ====================

@router.post("/{company_id}/bank-accounts", response_model=CompanyBankAccountResponse, status_code=status.HTTP_201_CREATED)
@require_module("d2c_storefront")
async def create_bank_account(
    company_id: UUID,
    account_in: CompanyBankAccountCreate,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Add a bank account to a company.

    Automatically creates a corresponding entry in Chart of Accounts
    for use in Journal Entries.
    """
    # Verify company exists
    result = await db.execute(
        select(Company).where(Company.id == company_id)
    )
    company = result.scalar_one_or_none()

    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found"
        )

    # If setting as primary, unset existing primary
    if account_in.is_primary:
        result = await db.execute(
            select(CompanyBankAccount).where(
                and_(
                    CompanyBankAccount.company_id == company_id,
                    CompanyBankAccount.is_primary == True
                )
            )
        )
        existing_primary = result.scalar_one_or_none()
        if existing_primary:
            existing_primary.is_primary = False

    # Try to auto-create a ledger account in Chart of Accounts
    ledger_account_id = None
    try:
        # Generate a unique account code for the ledger account
        # Format: BANK-{last 4 digits of account number}
        account_suffix = account_in.account_number[-4:] if len(account_in.account_number) >= 4 else account_in.account_number
        base_code = f"BANK-{account_suffix}"

        # Check if code exists and add suffix if needed
        existing_code = await db.execute(
            select(ChartOfAccount).where(ChartOfAccount.account_code == base_code)
        )
        if existing_code.scalar_one_or_none():
            # Add a unique suffix
            base_code = f"BANK-{account_suffix}-{uuid.uuid4().hex[:4].upper()}"

        # Create corresponding Chart of Account entry (ledger account)
        # Use string values for enum fields (database uses VARCHAR)
        ledger_account = ChartOfAccount(
            account_code=base_code,
            account_name=f"{account_in.bank_name} - {account_in.branch_name}",
            account_type="ASSET",  # String value, not enum
            account_sub_type="BANK",  # String value, not enum
            description=f"Bank Account: {account_in.account_number} | IFSC: {account_in.ifsc_code}",
            is_group=False,
            is_system=False,
            is_active=True,
            allow_direct_posting=True,
            bank_name=account_in.bank_name,
            bank_account_number=account_in.account_number,
            bank_ifsc=account_in.ifsc_code,
        )
        db.add(ledger_account)
        await db.flush()  # Get the ledger_account.id
        ledger_account_id = ledger_account.id
    except Exception as e:
        # Log error but don't fail bank account creation
        import logging

        logging.warning(f"Failed to create ledger account for bank: {e}")

    # Create bank account (with optional link to ledger account)
    account_data = account_in.model_dump(exclude={"company_id"})
    account = CompanyBankAccount(
        **account_data,
        company_id=company_id,
    )
    # Only set ledger_account_id if we have it and the column exists
    if ledger_account_id:
        try:
            account.ledger_account_id = ledger_account_id
        except AttributeError:
            pass  # Column doesn't exist yet

    db.add(account)
    await db.commit()
    await db.refresh(account)

    return account


@router.get("/{company_id}/bank-accounts", response_model=List[CompanyBankAccountResponse])
@require_module("d2c_storefront")
async def list_bank_accounts(
    company_id: UUID,
    db: DB,
    current_user: User = Depends(get_current_user),
    is_active: Optional[bool] = None,
    purpose: Optional[str] = None,
):
    """List all bank accounts for a company."""
    query = select(CompanyBankAccount).where(CompanyBankAccount.company_id == company_id)

    if is_active is not None:
        query = query.where(CompanyBankAccount.is_active == is_active)
    if purpose:
        query = query.where(CompanyBankAccount.purpose == purpose)

    query = query.order_by(CompanyBankAccount.is_primary.desc(), CompanyBankAccount.created_at.asc())

    result = await db.execute(query)
    accounts = result.scalars().all()

    return accounts


@router.put("/{company_id}/bank-accounts/{account_id}", response_model=CompanyBankAccountResponse)
@require_module("d2c_storefront")
async def update_bank_account(
    company_id: UUID,
    account_id: UUID,
    account_in: CompanyBankAccountUpdate,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Update bank account details."""
    result = await db.execute(
        select(CompanyBankAccount).where(
            and_(
                CompanyBankAccount.id == account_id,
                CompanyBankAccount.company_id == company_id
            )
        )
    )
    account = result.scalar_one_or_none()

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bank account not found"
        )

    # If setting as primary, unset existing primary
    if account_in.is_primary and not account.is_primary:
        result = await db.execute(
            select(CompanyBankAccount).where(
                and_(
                    CompanyBankAccount.company_id == company_id,
                    CompanyBankAccount.is_primary == True,
                    CompanyBankAccount.id != account_id
                )
            )
        )
        existing_primary = result.scalar_one_or_none()
        if existing_primary:
            existing_primary.is_primary = False

    update_data = account_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(account, field, value)

    await db.commit()
    await db.refresh(account)

    return account


@router.delete("/{company_id}/bank-accounts/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
@require_module("d2c_storefront")
async def delete_bank_account(
    company_id: UUID,
    account_id: UUID,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Delete a bank account."""
    result = await db.execute(
        select(CompanyBankAccount).where(
            and_(
                CompanyBankAccount.id == account_id,
                CompanyBankAccount.company_id == company_id
            )
        )
    )
    account = result.scalar_one_or_none()

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bank account not found"
        )

    if account.is_primary:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete primary bank account. Set another account as primary first."
        )

    await db.delete(account)
    await db.commit()
