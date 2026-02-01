"""API endpoints for Accounting & Finance module."""
from typing import Optional, List
from uuid import UUID
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from sqlalchemy import select, func, and_, or_, case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.accounting import (
    ChartOfAccount, AccountType, AccountSubType,
    FinancialPeriod, FinancialPeriodStatus as PeriodStatus,
    CostCenter,
    JournalEntry, JournalEntryLine, JournalEntryStatus as JournalStatus,
    GeneralLedger,
    TaxConfiguration,
)
from app.models.user import User
from app.schemas.accounting import (
    # Chart of Accounts
    ChartOfAccountCreate, ChartOfAccountUpdate, ChartOfAccountResponse,
    ChartOfAccountTree, AccountListResponse,
    # Financial Period
    FinancialPeriodCreate, FinancialPeriodUpdate, FinancialPeriodResponse, PeriodListResponse,
    # Cost Center
    CostCenterCreate, CostCenterUpdate, CostCenterResponse,
    # Journal Entry
    JournalEntryCreate, JournalEntryUpdate, JournalEntryResponse, JournalListResponse,
    JournalEntryLineCreate, JournalReverseRequest,
    # Maker-Checker Approval
    JournalSubmitRequest, JournalApproveRequest, JournalRejectRequest,
    JournalApprovalResponse, PendingApprovalResponse,
    ApprovalHistoryItem, ApprovalHistoryResponse,
    # General Ledger
    GeneralLedgerResponse, LedgerListResponse,
    # Reports
    TrialBalanceResponse, TrialBalanceItem,
    BalanceSheetResponse, ProfitLossResponse,
    # Tax
    TaxConfigurationCreate, TaxConfigurationUpdate, TaxConfigurationResponse,
)
from app.models.accounting import ApprovalLevel
from app.api.deps import DB, CurrentUser, get_current_user, require_permissions
from app.services.audit_service import AuditService

router = APIRouter()


# ==================== Chart of Accounts ====================

@router.post(
    "/accounts",
    response_model=ChartOfAccountResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions("accounts:create"))]
)
async def create_account(
    account_in: ChartOfAccountCreate,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Create a new account in Chart of Accounts."""
    # Check for duplicate code
    existing = await db.execute(
        select(ChartOfAccount).where(ChartOfAccount.account_code == account_in.account_code)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail=f"Account code {account_in.account_code} already exists"
        )

    # Validate parent if provided
    if account_in.parent_id:
        parent = await db.execute(
            select(ChartOfAccount).where(ChartOfAccount.id == account_in.parent_id)
        )
        if not parent.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Parent account not found")

    account = ChartOfAccount(
        **account_in.model_dump(by_alias=False, exclude_unset=False),
    )

    db.add(account)
    await db.commit()
    await db.refresh(account)

    return account


@router.get(
    "/accounts",
    response_model=AccountListResponse,
    dependencies=[Depends(require_permissions("accounts:view"))]
)
async def list_accounts(
    db: DB,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    account_type: Optional[AccountType] = None,
    sub_type: Optional[AccountSubType] = None,
    parent_id: Optional[UUID] = None,
    search: Optional[str] = None,
    is_active: Optional[bool] = True,
    current_user: User = Depends(get_current_user),
):
    """List accounts from Chart of Accounts."""
    query = select(ChartOfAccount)
    count_query = select(func.count(ChartOfAccount.id))

    filters = []
    if account_type:
        filters.append(ChartOfAccount.account_type == account_type)
    if sub_type:
        filters.append(ChartOfAccount.sub_type == sub_type)
    if parent_id:
        filters.append(ChartOfAccount.parent_id == parent_id)
    if is_active is not None:
        filters.append(ChartOfAccount.is_active == is_active)
    if search:
        filters.append(or_(
            ChartOfAccount.account_code.ilike(f"%{search}%"),
            ChartOfAccount.name.ilike(f"%{search}%"),
        ))

    if filters:
        query = query.where(and_(*filters))
        count_query = count_query.where(and_(*filters))

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(ChartOfAccount.account_code).offset(skip).limit(limit)
    result = await db.execute(query)
    accounts = result.scalars().all()

    return AccountListResponse(
        items=[ChartOfAccountResponse.model_validate(a) for a in accounts],
        total=total,
        skip=skip,
        limit=limit
    )


@router.get(
    "/accounts/tree",
    response_model=List[ChartOfAccountTree],
    dependencies=[Depends(require_permissions("accounts:view"))]
)
async def get_accounts_tree(
    db: DB,
    account_type: Optional[AccountType] = None,
    current_user: User = Depends(get_current_user),
):
    """Get Chart of Accounts as a hierarchical tree."""
    query = select(ChartOfAccount).where(ChartOfAccount.is_active == True)

    if account_type:
        query = query.where(ChartOfAccount.account_type == account_type)

    query = query.order_by(ChartOfAccount.account_code)
    result = await db.execute(query)
    accounts = result.scalars().all()

    # Build tree structure
    account_map = {a.id: a for a in accounts}
    root_accounts = []

    for account in accounts:
        if account.parent_id is None:
            root_accounts.append(account)

    def build_tree(account) -> ChartOfAccountTree:
        children = [a for a in accounts if a.parent_id == account.id]
        return ChartOfAccountTree(
            id=account.id,
            account_code=account.account_code,
            name=account.name,
            account_type=account.account_type,
            sub_type=account.sub_type,
            is_group=account.is_group,
            current_balance=account.current_balance,
            children=[build_tree(c) for c in children] if children else []
        )

    return [build_tree(a) for a in root_accounts]


@router.get(
    "/accounts/dropdown",
    dependencies=[Depends(require_permissions("accounts:view"))]
)
async def get_accounts_dropdown(
    db: DB,
    account_type: Optional[AccountType] = None,
    postable_only: bool = True,
    include_vendors: bool = True,
    include_dealers: bool = True,
    current_user: User = Depends(get_current_user),
):
    """Get accounts for dropdown selection including vendor/dealer subledgers.

    Args:
        account_type: Filter by account type
        postable_only: Only return non-group accounts (default: True)
        include_vendors: Include vendor subledger accounts (default: True)
        include_dealers: Include dealer subledger accounts (default: True)
    """
    from app.models.vendor import Vendor
    from app.models.dealer import Dealer

    # Get regular GL accounts
    query = select(ChartOfAccount).where(ChartOfAccount.is_active == True)

    if account_type:
        query = query.where(ChartOfAccount.account_type == account_type)
    if postable_only:
        query = query.where(ChartOfAccount.is_group == False)

    query = query.order_by(ChartOfAccount.account_code)
    result = await db.execute(query)
    accounts = result.scalars().all()

    dropdown_items = [
        {
            "id": str(a.id),
            "code": a.account_code,
            "name": a.account_name,
            "full_name": f"{a.account_code} - {a.account_name}",
            "type": a.account_type,
            "subledger_type": None,
        }
        for a in accounts
    ]

    # Include vendor subledger accounts if requested
    # Note: Only vendors with linked GL accounts are included.
    # Use POST /accounts/sync-vendor-subledgers to create GL accounts for vendors.
    if include_vendors and (account_type is None or account_type == AccountType.LIABILITY):
        vendor_result = await db.execute(
            select(Vendor).where(
                Vendor.status == "ACTIVE",
                Vendor.gl_account_id.isnot(None)
            ).order_by(Vendor.name)
        )
        vendors = vendor_result.scalars().all()

        for v in vendors:
            # Get the linked GL account details
            gl_result = await db.execute(
                select(ChartOfAccount).where(ChartOfAccount.id == v.gl_account_id)
            )
            gl_account = gl_result.scalar_one_or_none()

            if gl_account:
                dropdown_items.append({
                    "id": str(gl_account.id),
                    "code": gl_account.account_code,
                    "name": f"Vendor: {v.name}",
                    "full_name": f"{gl_account.account_code} - Vendor: {v.name}",
                    "type": "LIABILITY",
                    "subledger_type": "VENDOR",
                    "entity_id": str(v.id),
                })

    # Include dealer subledger accounts if requested
    # Note: Only dealers with linked GL accounts are included.
    # Dealers need a gl_account_id column linked to a Trade Debtors subledger.
    if include_dealers and (account_type is None or account_type == AccountType.ASSET):
        # Check if Dealer model has gl_account_id attribute
        if hasattr(Dealer, 'gl_account_id'):
            dealer_result = await db.execute(
                select(Dealer).where(
                    Dealer.status == "ACTIVE",
                    Dealer.gl_account_id.isnot(None)
                ).order_by(Dealer.name)
            )
            dealers = dealer_result.scalars().all()

            for d in dealers:
                # Get the linked GL account details
                gl_result = await db.execute(
                    select(ChartOfAccount).where(ChartOfAccount.id == d.gl_account_id)
                )
                gl_account = gl_result.scalar_one_or_none()

                if gl_account:
                    dropdown_items.append({
                        "id": str(gl_account.id),
                        "code": gl_account.account_code,
                        "name": f"Dealer: {d.name}",
                        "full_name": f"{gl_account.account_code} - Dealer: {d.name}",
                        "type": "ASSET",
                        "subledger_type": "DEALER",
                        "entity_id": str(d.id),
                    })

    return dropdown_items


@router.post(
    "/accounts/sync-vendor-subledgers",
    dependencies=[Depends(require_permissions("accounts:create"))]
)
async def sync_vendor_subledger_accounts(
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Auto-create GL subledger accounts for all active vendors.

    This creates a child account under Sundry Creditors (2101) for each vendor
    and links it via the vendor's gl_account_id field.

    Returns:
        dict with count of accounts created
    """
    from app.models.vendor import Vendor
    import uuid as uuid_module

    # Get Sundry Creditors parent account (2101)
    parent_result = await db.execute(
        select(ChartOfAccount).where(ChartOfAccount.account_code == "2101")
    )
    parent_account = parent_result.scalar_one_or_none()

    if not parent_account:
        raise HTTPException(
            status_code=400,
            detail="Sundry Creditors (2101) account not found. Please create it first."
        )

    # Get active vendors without GL account linked
    vendor_result = await db.execute(
        select(Vendor).where(
            Vendor.status == "ACTIVE",
            Vendor.gl_account_id.is_(None)
        ).order_by(Vendor.name)
    )
    vendors = vendor_result.scalars().all()

    created = []
    for vendor in vendors:
        # Generate account code: 2101-VND001, 2101-VND002, etc.
        # Use vendor code suffix for readability
        vendor_suffix = vendor.vendor_code.replace("VND-", "").replace("-", "")[:6]
        account_code = f"2101-{vendor_suffix}"

        # Check if account code already exists
        existing = await db.execute(
            select(ChartOfAccount).where(ChartOfAccount.account_code == account_code)
        )
        if existing.scalar_one_or_none():
            # Code exists, add UUID suffix
            account_code = f"2101-{vendor_suffix[:4]}{str(vendor.id)[:4].upper()}"

        # Create the GL account
        gl_account = ChartOfAccount(
            id=uuid_module.uuid4(),
            account_code=account_code,
            account_name=f"Vendor: {vendor.name[:100]}",
            account_type=AccountType.LIABILITY,
            description=f"Subledger account for vendor {vendor.vendor_code}",
            parent_id=parent_account.id,
            level=parent_account.level + 1 if hasattr(parent_account, 'level') else 3,
            is_group=False,
            is_system=False,
            is_active=True,
            allow_direct_posting=True,
        )
        db.add(gl_account)

        # Link vendor to this GL account
        vendor.gl_account_id = gl_account.id

        created.append({
            "vendor_code": vendor.vendor_code,
            "vendor_name": vendor.name,
            "gl_account_code": account_code,
            "gl_account_id": str(gl_account.id),
        })

    await db.commit()

    return {
        "success": True,
        "total_created": len(created),
        "accounts": created,
        "message": f"Created {len(created)} GL subledger accounts for vendors"
    }


@router.get(
    "/accounts/{account_id}",
    response_model=ChartOfAccountResponse,
    dependencies=[Depends(require_permissions("accounts:view"))]
)
async def get_account(
    account_id: UUID,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Get account by ID."""
    result = await db.execute(
        select(ChartOfAccount).where(ChartOfAccount.id == account_id)
    )
    account = result.scalar_one_or_none()

    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    return account


@router.put(
    "/accounts/{account_id}",
    response_model=ChartOfAccountResponse,
    dependencies=[Depends(require_permissions("accounts:update"))]
)
async def update_account(
    account_id: UUID,
    account_in: ChartOfAccountUpdate,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Update account details."""
    result = await db.execute(
        select(ChartOfAccount).where(ChartOfAccount.id == account_id)
    )
    account = result.scalar_one_or_none()

    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    update_data = account_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(account, field, value)

    account.updated_by = current_user.id

    await db.commit()
    await db.refresh(account)

    return account


@router.delete(
    "/accounts/{account_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permissions("accounts:delete"))]
)
async def delete_account(
    account_id: UUID,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Delete an account from Chart of Accounts.

    Restrictions:
    - System accounts cannot be deleted
    - Accounts with non-zero balance cannot be deleted
    - Accounts with journal entries cannot be deleted
    """
    result = await db.execute(
        select(ChartOfAccount).where(ChartOfAccount.id == account_id)
    )
    account = result.scalar_one_or_none()

    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    # Check if it's a system account
    if account.is_system:
        raise HTTPException(
            status_code=400,
            detail="System accounts cannot be deleted"
        )

    # Check if account has non-zero balance
    if account.current_balance != 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete account with non-zero balance (₹{account.current_balance})"
        )

    # Check if account has journal entries
    journal_entries = await db.execute(
        select(func.count(JournalEntryLine.id)).where(
            JournalEntryLine.account_id == account_id
        )
    )
    entry_count = journal_entries.scalar() or 0
    if entry_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete account with {entry_count} journal entries"
        )

    # Check if account has children
    children = await db.execute(
        select(func.count(ChartOfAccount.id)).where(
            ChartOfAccount.parent_id == account_id
        )
    )
    child_count = children.scalar() or 0
    if child_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete account with {child_count} child accounts"
        )

    await db.delete(account)
    await db.commit()

    return None


# ==================== Financial Periods ====================

@router.post(
    "/periods",
    response_model=FinancialPeriodResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions("periods:create"))]
)
async def create_financial_period(
    period_in: FinancialPeriodCreate,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Create a new financial period."""
    # Check for overlapping periods
    overlap = await db.execute(
        select(FinancialPeriod).where(
            and_(
                FinancialPeriod.start_date <= period_in.end_date,
                FinancialPeriod.end_date >= period_in.start_date,
            )
        )
    )
    if overlap.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail="Period overlaps with existing financial period"
        )

    period = FinancialPeriod(
        **period_in.model_dump(by_alias=False, exclude_unset=False),
    )

    db.add(period)
    await db.commit()
    await db.refresh(period)

    return period


@router.get(
    "/periods",
    response_model=PeriodListResponse,
    dependencies=[Depends(require_permissions("periods:view"))]
)
async def list_financial_periods(
    db: DB,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=50),
    status: Optional[PeriodStatus] = None,
    current_user: User = Depends(get_current_user),
):
    """List financial periods."""
    query = select(FinancialPeriod)
    count_query = select(func.count(FinancialPeriod.id))

    if status:
        query = query.where(FinancialPeriod.status == status)
        count_query = count_query.where(FinancialPeriod.status == status)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(FinancialPeriod.start_date.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    periods = result.scalars().all()

    return PeriodListResponse(
        items=[FinancialPeriodResponse.model_validate(p) for p in periods],
        total=total,
        skip=skip,
        limit=limit
    )


@router.get(
    "/periods/current",
    response_model=FinancialPeriodResponse,
    dependencies=[Depends(require_permissions("periods:view"))]
)
async def get_current_period(
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Get the current open financial period."""
    today = date.today()
    result = await db.execute(
        select(FinancialPeriod).where(
            and_(
                FinancialPeriod.start_date <= today,
                FinancialPeriod.end_date >= today,
                FinancialPeriod.status == PeriodStatus.OPEN,
            )
        )
    )
    period = result.scalar_one_or_none()

    if not period:
        raise HTTPException(
            status_code=404,
            detail="No open financial period for current date"
        )

    return period


@router.post(
    "/periods/{period_id}/close",
    response_model=FinancialPeriodResponse,
    dependencies=[Depends(require_permissions("periods:close"))]
)
async def close_financial_period(
    period_id: UUID,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Close a financial period (year-end closing)."""
    result = await db.execute(
        select(FinancialPeriod).where(FinancialPeriod.id == period_id)
    )
    period = result.scalar_one_or_none()

    if not period:
        raise HTTPException(status_code=404, detail="Period not found")

    if period.status != PeriodStatus.OPEN:
        raise HTTPException(status_code=400, detail="Period is not open")

    # Check for unposted journal entries
    unposted = await db.execute(
        select(func.count(JournalEntry.id)).where(
            and_(
                JournalEntry.entry_date >= period.start_date,
                JournalEntry.entry_date <= period.end_date,
                JournalEntry.status != JournalStatus.POSTED,
            )
        )
    )
    unposted_count = unposted.scalar() or 0

    if unposted_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot close period with {unposted_count} unposted journal entries"
        )

    # TODO: Generate closing entries (transfer P&L to Retained Earnings)

    period.status = PeriodStatus.CLOSED.value
    period.closed_at = datetime.now(timezone.utc)
    period.closed_by = current_user.id

    await db.commit()
    await db.refresh(period)

    return period


@router.post(
    "/periods/{period_id}/reopen",
    response_model=FinancialPeriodResponse,
    dependencies=[Depends(require_permissions("periods:close"))]
)
async def reopen_financial_period(
    period_id: UUID,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Reopen a closed financial period."""
    result = await db.execute(
        select(FinancialPeriod).where(FinancialPeriod.id == period_id)
    )
    period = result.scalar_one_or_none()

    if not period:
        raise HTTPException(status_code=404, detail="Period not found")

    if period.status == PeriodStatus.LOCKED:
        raise HTTPException(status_code=400, detail="Cannot reopen a locked period")

    if period.status == PeriodStatus.OPEN:
        raise HTTPException(status_code=400, detail="Period is already open")

    period.status = PeriodStatus.OPEN.value
    period.closed_at = None
    period.closed_by = None

    await db.commit()
    await db.refresh(period)

    return period


@router.post(
    "/periods/{period_id}/lock",
    response_model=FinancialPeriodResponse,
    dependencies=[Depends(require_permissions("periods:close"))]
)
async def lock_financial_period(
    period_id: UUID,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Permanently lock a financial period. This action is irreversible."""
    result = await db.execute(
        select(FinancialPeriod).where(FinancialPeriod.id == period_id)
    )
    period = result.scalar_one_or_none()

    if not period:
        raise HTTPException(status_code=404, detail="Period not found")

    if period.status == PeriodStatus.LOCKED:
        raise HTTPException(status_code=400, detail="Period is already locked")

    if period.status == PeriodStatus.OPEN:
        raise HTTPException(status_code=400, detail="Cannot lock an open period. Close it first.")

    period.status = PeriodStatus.LOCKED.value

    await db.commit()
    await db.refresh(period)

    return period


@router.get(
    "/periods/{period_id}",
    response_model=FinancialPeriodResponse,
    dependencies=[Depends(require_permissions("periods:view"))]
)
async def get_financial_period(
    period_id: UUID,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Get financial period by ID."""
    result = await db.execute(
        select(FinancialPeriod).where(FinancialPeriod.id == period_id)
    )
    period = result.scalar_one_or_none()

    if not period:
        raise HTTPException(status_code=404, detail="Period not found")

    return period


@router.put(
    "/periods/{period_id}",
    response_model=FinancialPeriodResponse,
    dependencies=[Depends(require_permissions("periods:update"))]
)
async def update_financial_period(
    period_id: UUID,
    period_in: FinancialPeriodUpdate,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Update financial period.

    Note: Only status can be updated. Use close/reopen/lock endpoints for status changes.
    """
    result = await db.execute(
        select(FinancialPeriod).where(FinancialPeriod.id == period_id)
    )
    period = result.scalar_one_or_none()

    if not period:
        raise HTTPException(status_code=404, detail="Period not found")

    if period.status == PeriodStatus.LOCKED:
        raise HTTPException(status_code=400, detail="Cannot update a locked period")

    update_data = period_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "status" and value:
            setattr(period, field, value.value if hasattr(value, 'value') else value)
        else:
            setattr(period, field, value)

    await db.commit()
    await db.refresh(period)

    return period


@router.delete(
    "/periods/{period_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permissions("periods:delete"))]
)
async def delete_financial_period(
    period_id: UUID,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Delete a financial period.

    Restrictions:
    - Locked periods cannot be deleted
    - Periods with journal entries cannot be deleted
    """
    result = await db.execute(
        select(FinancialPeriod).where(FinancialPeriod.id == period_id)
    )
    period = result.scalar_one_or_none()

    if not period:
        raise HTTPException(status_code=404, detail="Period not found")

    # Check if period is locked
    if period.status == PeriodStatus.LOCKED:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete a locked period"
        )

    # Check if period has journal entries
    journal_entries = await db.execute(
        select(func.count(JournalEntry.id)).where(
            JournalEntry.period_id == period_id
        )
    )
    entry_count = journal_entries.scalar() or 0
    if entry_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete period with {entry_count} journal entries"
        )

    await db.delete(period)
    await db.commit()

    return None


# ==================== Fiscal Years ====================

@router.get(
    "/fiscal-years",
    dependencies=[Depends(require_permissions("periods:view"))]
)
async def list_fiscal_years(
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """List all fiscal years with their period counts."""
    # Get distinct fiscal years from periods
    query = select(
        FinancialPeriod.financial_year,
        func.min(FinancialPeriod.start_date).label("start_date"),
        func.max(FinancialPeriod.end_date).label("end_date"),
        func.count(FinancialPeriod.id).label("periods_count"),
        func.sum(
            case(
                (FinancialPeriod.status == PeriodStatus.OPEN, 1),
                else_=0
            )
        ).label("open_periods"),
    ).where(
        FinancialPeriod.financial_year.isnot(None)
    ).group_by(
        FinancialPeriod.financial_year
    ).order_by(
        func.min(FinancialPeriod.start_date).desc()
    )

    result = await db.execute(query)
    rows = result.all()

    items = []
    for row in rows:
        # Determine status: ACTIVE if any periods are open, CLOSED otherwise
        status = "ACTIVE" if row.open_periods > 0 else "CLOSED"
        items.append({
            "id": row.financial_year,  # Use financial_year as ID for simplicity
            "name": f"FY {row.financial_year}" if row.financial_year else "Unknown",
            "start_date": row.start_date.isoformat() if row.start_date else None,
            "end_date": row.end_date.isoformat() if row.end_date else None,
            "status": status,
            "periods_count": row.periods_count,
            "open_periods": row.open_periods or 0,
        })

    return {"items": items, "total": len(items)}


@router.post(
    "/fiscal-years",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions("periods:create"))]
)
async def create_fiscal_year(
    year_data: dict,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """
    Create a new fiscal year with auto-generated monthly periods.

    Expected payload:
    {
        "name": "FY 2025-26",
        "start_date": "2025-04-01",
        "end_date": "2026-03-31"
    }
    """
    from dateutil.relativedelta import relativedelta
    from calendar import monthrange

    name = year_data.get("name", "")
    start_date_str = year_data.get("start_date")
    end_date_str = year_data.get("end_date")

    if not start_date_str or not end_date_str:
        raise HTTPException(status_code=400, detail="start_date and end_date are required")

    try:
        start_date = date.fromisoformat(start_date_str)
        end_date = date.fromisoformat(end_date_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    if end_date <= start_date:
        raise HTTPException(status_code=400, detail="end_date must be after start_date")

    # Extract financial year code (e.g., "2025-2026" from dates)
    financial_year = f"{start_date.year}-{end_date.year}"

    # Check if fiscal year already exists
    existing = await db.execute(
        select(FinancialPeriod).where(
            FinancialPeriod.financial_year == financial_year
        ).limit(1)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail=f"Fiscal year {financial_year} already exists"
        )

    # Generate monthly periods
    periods_created = []
    current_month_start = start_date

    while current_month_start <= end_date:
        # Calculate month end
        _, last_day = monthrange(current_month_start.year, current_month_start.month)
        month_end = date(current_month_start.year, current_month_start.month, last_day)

        # Don't exceed the fiscal year end date
        if month_end > end_date:
            month_end = end_date

        # Month code (APR-2025, MAY-2025, etc.)
        month_code = current_month_start.strftime("%b-%Y").upper()
        month_name = current_month_start.strftime("%B %Y")

        period = FinancialPeriod(
            period_name=month_name,
            period_code=month_code,
            financial_year=financial_year,
            period_type="MONTHLY",
            start_date=current_month_start,
            end_date=month_end,
            status=PeriodStatus.OPEN.value,
            is_current=(date.today() >= current_month_start and date.today() <= month_end),
        )

        db.add(period)
        periods_created.append({
            "name": month_name,
            "code": month_code,
            "start_date": current_month_start.isoformat(),
            "end_date": month_end.isoformat(),
        })

        # Move to next month
        current_month_start = current_month_start + relativedelta(months=1)
        # Reset to first day of month
        current_month_start = date(current_month_start.year, current_month_start.month, 1)

    await db.commit()

    return {
        "message": f"Fiscal year {financial_year} created with {len(periods_created)} monthly periods",
        "financial_year": financial_year,
        "name": name,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "periods_created": len(periods_created),
    }


# ==================== Cost Centers ====================

@router.post(
    "/cost-centers",
    response_model=CostCenterResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions("cost_centers:create"))]
)
async def create_cost_center(
    cc_in: CostCenterCreate,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Create a new cost center."""
    cost_center = CostCenter(
        **cc_in.model_dump(),
        created_by=current_user.id,
    )

    db.add(cost_center)
    await db.commit()
    await db.refresh(cost_center)

    return cost_center


@router.get(
    "/cost-centers",
    response_model=List[CostCenterResponse],
    dependencies=[Depends(require_permissions("cost_centers:view"))]
)
async def list_cost_centers(
    db: DB,
    is_active: bool = True,
    current_user: User = Depends(get_current_user),
):
    """List all cost centers."""
    query = select(CostCenter)
    if is_active is not None:
        query = query.where(CostCenter.is_active == is_active)

    query = query.order_by(CostCenter.code)
    result = await db.execute(query)
    cost_centers = result.scalars().all()

    return [CostCenterResponse.model_validate(cc) for cc in cost_centers]


@router.get(
    "/cost-centers/{cost_center_id}",
    response_model=CostCenterResponse,
    dependencies=[Depends(require_permissions("cost_centers:view"))]
)
async def get_cost_center(
    cost_center_id: UUID,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Get cost center by ID."""
    result = await db.execute(
        select(CostCenter).where(CostCenter.id == cost_center_id)
    )
    cost_center = result.scalar_one_or_none()

    if not cost_center:
        raise HTTPException(status_code=404, detail="Cost center not found")

    return cost_center


@router.put(
    "/cost-centers/{cost_center_id}",
    response_model=CostCenterResponse,
    dependencies=[Depends(require_permissions("cost_centers:update"))]
)
async def update_cost_center(
    cost_center_id: UUID,
    cc_in: CostCenterUpdate,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Update cost center details."""
    result = await db.execute(
        select(CostCenter).where(CostCenter.id == cost_center_id)
    )
    cost_center = result.scalar_one_or_none()

    if not cost_center:
        raise HTTPException(status_code=404, detail="Cost center not found")

    update_data = cc_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(cost_center, field, value)

    cost_center.updated_by = current_user.id

    await db.commit()
    await db.refresh(cost_center)

    return cost_center


@router.delete(
    "/cost-centers/{cost_center_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permissions("cost_centers:delete"))]
)
async def delete_cost_center(
    cost_center_id: UUID,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Delete a cost center.

    Restrictions:
    - Cost centers with journal entries cannot be deleted
    - Cost centers with child cost centers cannot be deleted
    """
    result = await db.execute(
        select(CostCenter).where(CostCenter.id == cost_center_id)
    )
    cost_center = result.scalar_one_or_none()

    if not cost_center:
        raise HTTPException(status_code=404, detail="Cost center not found")

    # Check if cost center has journal entries
    journal_entries = await db.execute(
        select(func.count(JournalEntryLine.id)).where(
            JournalEntryLine.cost_center_id == cost_center_id
        )
    )
    entry_count = journal_entries.scalar() or 0
    if entry_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete cost center with {entry_count} journal entries"
        )

    # Check if cost center has children
    children = await db.execute(
        select(func.count(CostCenter.id)).where(
            CostCenter.parent_id == cost_center_id
        )
    )
    child_count = children.scalar() or 0
    if child_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete cost center with {child_count} child cost centers"
        )

    await db.delete(cost_center)
    await db.commit()

    return None


# ==================== Journal Entries ====================

@router.post(
    "/journals",
    response_model=JournalEntryResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions("journals:create"))]
)
async def create_journal_entry(
    journal_in: JournalEntryCreate,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Create a new journal entry."""
    # Validate the current period
    period_result = await db.execute(
        select(FinancialPeriod).where(
            and_(
                FinancialPeriod.start_date <= journal_in.entry_date,
                FinancialPeriod.end_date >= journal_in.entry_date,
                FinancialPeriod.status == PeriodStatus.OPEN,
            )
        ).limit(1)
    )
    period = period_result.scalar_one_or_none()

    if not period:
        raise HTTPException(
            status_code=400,
            detail="No open financial period for the entry date"
        )

    # Validate debit = credit
    total_debit = sum(line.debit_amount for line in journal_in.lines)
    total_credit = sum(line.credit_amount for line in journal_in.lines)

    if total_debit != total_credit:
        raise HTTPException(
            status_code=400,
            detail=f"Debits ({total_debit}) must equal Credits ({total_credit})"
        )

    if total_debit == 0:
        raise HTTPException(status_code=400, detail="Journal entry cannot have zero amount")

    # Generate journal number
    today = date.today()
    count_result = await db.execute(
        select(func.count(JournalEntry.id)).where(
            func.date(JournalEntry.created_at) == today
        )
    )
    count = count_result.scalar() or 0
    entry_number = f"JV-{today.strftime('%Y%m%d')}-{str(count + 1).zfill(4)}"

    # Create journal entry
    journal = JournalEntry(
        entry_number=entry_number,
        entry_type=journal_in.entry_type,
        entry_date=journal_in.entry_date,
        period_id=period.id,
        narration=journal_in.narration,
        source_type=journal_in.source_type,
        source_number=journal_in.source_number,
        source_id=journal_in.source_id,
        total_debit=total_debit,
        total_credit=total_credit,
        created_by=current_user.id,
    )

    db.add(journal)
    await db.flush()

    # Create journal lines
    line_number = 0
    for line_data in journal_in.lines:
        line_number += 1

        # Verify account exists
        account_result = await db.execute(
            select(ChartOfAccount).where(ChartOfAccount.id == line_data.account_id)
        )
        account = account_result.scalar_one_or_none()
        if not account:
            raise HTTPException(
                status_code=400,
                detail=f"Account {line_data.account_id} not found"
            )
        if account.is_group:
            raise HTTPException(
                status_code=400,
                detail=f"Cannot post to group account: {account.account_name}"
            )

        line = JournalEntryLine(
            journal_entry_id=journal.id,
            line_number=line_number,
            account_id=line_data.account_id,
            debit_amount=line_data.debit_amount,
            credit_amount=line_data.credit_amount,
            cost_center_id=line_data.cost_center_id,
            description=line_data.description,
        )
        db.add(line)

    await db.commit()

    # Load full journal with lines and their accounts
    result = await db.execute(
        select(JournalEntry)
        .options(
            selectinload(JournalEntry.lines).selectinload(JournalEntryLine.account)
        )
        .where(JournalEntry.id == journal.id)
    )
    journal = result.scalar_one()

    # Build response with account info
    lines_response = []
    for line in journal.lines:
        lines_response.append({
            "id": line.id,
            "account_id": line.account_id,
            "description": line.description,
            "debit_amount": line.debit_amount,
            "credit_amount": line.credit_amount,
            "cost_center_id": line.cost_center_id,
            "line_number": line.line_number,
            "account_code": line.account.account_code if line.account else None,
            "account_name": line.account.account_name if line.account else None,
        })

    return {
        "id": journal.id,
        "entry_number": journal.entry_number,
        "entry_type": journal.entry_type,
        "entry_date": journal.entry_date,
        "period_id": journal.period_id,
        "narration": journal.narration,
        "source_type": journal.source_type,
        "source_id": journal.source_id,
        "source_number": journal.source_number,
        "status": journal.status,
        "total_debit": journal.total_debit,
        "total_credit": journal.total_credit,
        "is_auto_generated": False,  # Manual entries are not auto-generated
        "created_by": journal.created_by,
        "posted_by": journal.posted_by,
        "posted_at": journal.posted_at,
        "reversed_by": None,
        "reversed_at": None,
        "reversal_entry_id": None,
        "lines": lines_response,
        "created_at": journal.created_at,
        "updated_at": journal.updated_at,
    }


@router.get(
    "/journals",
    response_model=JournalListResponse,
    dependencies=[Depends(require_permissions("journals:view"))]
)
async def list_journal_entries(
    db: DB,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    entry_type: Optional[str] = None,
    status: Optional[JournalStatus] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    search: Optional[str] = None,
    current_user: User = Depends(get_current_user),
):
    """List journal entries."""
    query = select(JournalEntry).options(selectinload(JournalEntry.lines))
    count_query = select(func.count(JournalEntry.id))

    filters = []
    if entry_type:
        filters.append(JournalEntry.entry_type == entry_type)
    if status:
        filters.append(JournalEntry.status == status)
    if start_date:
        filters.append(JournalEntry.entry_date >= start_date)
    if end_date:
        filters.append(JournalEntry.entry_date <= end_date)
    if search:
        filters.append(or_(
            JournalEntry.entry_number.ilike(f"%{search}%"),
            JournalEntry.narration.ilike(f"%{search}%"),
        ))

    if filters:
        query = query.where(and_(*filters))
        count_query = count_query.where(and_(*filters))

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(JournalEntry.entry_date.desc(), JournalEntry.created_at.desc())
    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    journals = result.scalars().all()

    return JournalListResponse(
        items=[JournalEntryResponse.model_validate(j) for j in journals],
        total=total,
        skip=skip,
        limit=limit
    )


@router.get(
    "/journals/pending-approval",
    response_model=PendingApprovalResponse,
    dependencies=[Depends(require_permissions("journals:approve"))]
)
async def get_pending_approvals(
    db: DB,
    approval_level: Optional[str] = Query(None, description="Filter by LEVEL_1, LEVEL_2, LEVEL_3"),
    current_user: User = Depends(get_current_user),
):
    """
    Get list of journal entries pending approval.

    Returns entries grouped by approval level with counts.
    """
    # Base query for pending approvals
    query = (
        select(JournalEntry)
        .options(selectinload(JournalEntry.creator))
        .where(JournalEntry.status == JournalStatus.PENDING_APPROVAL)
        .order_by(JournalEntry.submitted_at.desc())
    )

    if approval_level:
        query = query.where(JournalEntry.approval_level == approval_level)

    result = await db.execute(query)
    entries = result.scalars().all()

    # Build response items
    items = []
    level_counts = {"LEVEL_1": 0, "LEVEL_2": 0, "LEVEL_3": 0}

    for entry in entries:
        # Count by level
        if entry.approval_level in level_counts:
            level_counts[entry.approval_level] += 1

        items.append(JournalApprovalResponse(
            id=entry.id,
            entry_number=entry.entry_number,
            status=entry.status,
            total_debit=entry.total_debit,
            total_credit=entry.total_credit,
            narration=entry.narration,
            created_by=entry.created_by,
            created_at=entry.created_at,
            creator_name=_get_user_name(entry.creator),
            submitted_by=entry.submitted_by,
            submitted_at=entry.submitted_at,
            approval_level=entry.approval_level,
        ))

    return PendingApprovalResponse(
        items=items,
        total=len(items),
        level_1_count=level_counts["LEVEL_1"],
        level_2_count=level_counts["LEVEL_2"],
        level_3_count=level_counts["LEVEL_3"],
    )


@router.get(
    "/journals/{journal_id}",
    response_model=JournalEntryResponse,
    dependencies=[Depends(require_permissions("journals:view"))]
)
async def get_journal_entry(
    journal_id: UUID,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Get journal entry by ID with full line details including account info."""
    result = await db.execute(
        select(JournalEntry)
        .options(
            selectinload(JournalEntry.lines).selectinload(JournalEntryLine.account)
        )
        .where(JournalEntry.id == journal_id)
    )
    journal = result.scalar_one_or_none()

    if not journal:
        raise HTTPException(status_code=404, detail="Journal entry not found")

    # Build response with account info for each line
    lines_with_account = []
    for line in journal.lines:
        lines_with_account.append({
            "id": line.id,
            "line_number": line.line_number,
            "account_id": line.account_id,
            "account_code": line.account.account_code if line.account else None,
            "account_name": line.account.account_name if line.account else None,
            "description": line.description,
            "debit_amount": line.debit_amount,
            "credit_amount": line.credit_amount,
            "cost_center_id": line.cost_center_id,
        })

    return {
        "id": journal.id,
        "entry_number": journal.entry_number,
        "entry_type": journal.entry_type,
        "entry_date": journal.entry_date,
        "period_id": journal.period_id,
        "narration": journal.narration,
        "status": journal.status,
        "total_debit": journal.total_debit,
        "total_credit": journal.total_credit,
        "source_type": journal.source_type,
        "source_id": journal.source_id,
        "source_number": journal.source_number,
        "is_reversed": journal.is_reversed,
        "reversed_by_id": journal.reversed_by_id,
        "reversal_of_id": journal.reversal_of_id,
        "created_by": journal.created_by,
        "approved_by": journal.approved_by,
        "approved_at": journal.approved_at,
        "posted_at": journal.posted_at,
        "rejection_reason": journal.rejection_reason,
        "created_at": journal.created_at,
        "updated_at": journal.updated_at,
        "lines": lines_with_account,
    }


@router.put(
    "/journals/{journal_id}",
    response_model=JournalEntryResponse,
    dependencies=[Depends(require_permissions("journals:edit"))]
)
async def update_journal_entry(
    journal_id: UUID,
    update_data: JournalEntryUpdate,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """
    Update a draft journal entry.

    Only DRAFT entries can be updated. Once submitted for approval,
    entries cannot be modified.
    """
    # Fetch the journal entry
    result = await db.execute(
        select(JournalEntry)
        .options(selectinload(JournalEntry.lines))
        .where(JournalEntry.id == journal_id)
    )
    journal = result.scalar_one_or_none()

    if not journal:
        raise HTTPException(status_code=404, detail="Journal entry not found")

    # Only DRAFT entries can be updated
    if journal.status != JournalStatus.DRAFT:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot update journal entry with status '{journal.status}'. Only DRAFT entries can be updated."
        )

    # Update basic fields if provided
    if update_data.entry_date is not None:
        journal.entry_date = update_data.entry_date
    if update_data.narration is not None:
        journal.narration = update_data.narration
    if update_data.source_number is not None:
        journal.source_number = update_data.source_number

    # Update lines if provided
    if update_data.lines is not None:
        # Delete existing lines
        for line in journal.lines:
            await db.delete(line)

        # Create new lines
        total_debit = Decimal("0")
        total_credit = Decimal("0")

        for idx, line_data in enumerate(update_data.lines, start=1):
            new_line = JournalEntryLine(
                journal_entry_id=journal.id,
                account_id=line_data.account_id,
                debit_amount=line_data.debit_amount,
                credit_amount=line_data.credit_amount,
                description=line_data.description,
                line_number=idx,
            )
            db.add(new_line)
            total_debit += line_data.debit_amount
            total_credit += line_data.credit_amount

        journal.total_debit = total_debit
        journal.total_credit = total_credit

    journal.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(journal)

    return journal


@router.delete(
    "/journals/{journal_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permissions("journals:delete"))]
)
async def delete_journal_entry(
    journal_id: UUID,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """
    Delete a draft journal entry.

    Only DRAFT entries can be deleted. Once submitted for approval,
    entries cannot be deleted - they must be rejected instead.
    """
    # Fetch the journal entry
    result = await db.execute(
        select(JournalEntry)
        .options(selectinload(JournalEntry.lines))
        .where(JournalEntry.id == journal_id)
    )
    journal = result.scalar_one_or_none()

    if not journal:
        raise HTTPException(status_code=404, detail="Journal entry not found")

    # Only DRAFT entries can be deleted
    if journal.status != JournalStatus.DRAFT:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete journal entry with status '{journal.status}'. Only DRAFT entries can be deleted."
        )

    # Delete journal lines first (cascade should handle this, but being explicit)
    for line in journal.lines:
        await db.delete(line)

    # Delete the journal entry
    await db.delete(journal)

    await db.commit()

    return None


# ==================== Maker-Checker Approval Workflow ====================


def _get_approval_level(amount: Decimal) -> str:
    """Determine approval level based on amount thresholds."""
    if amount <= Decimal("50000"):
        return ApprovalLevel.LEVEL_1.value  # Up to 50,000 - Manager approval
    elif amount <= Decimal("500000"):
        return ApprovalLevel.LEVEL_2.value  # 50,001 to 5,00,000 - Senior Manager
    else:
        return ApprovalLevel.LEVEL_3.value  # Above 5,00,000 - Finance Head


def _get_user_name(user: Optional[User]) -> Optional[str]:
    """Get formatted user name."""
    if not user:
        return None
    return f"{user.first_name} {user.last_name or ''}".strip()


@router.post(
    "/journals/{journal_id}/submit",
    response_model=JournalApprovalResponse,
    dependencies=[Depends(require_permissions("journals:create"))]
)
async def submit_journal_for_approval(
    journal_id: UUID,
    request: JournalSubmitRequest,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """
    Submit a draft journal entry for approval (Maker action).

    This moves the entry from DRAFT to PENDING_APPROVAL status.
    The entry will be assigned an approval level based on the amount.
    """
    result = await db.execute(
        select(JournalEntry)
        .options(selectinload(JournalEntry.lines))
        .options(selectinload(JournalEntry.creator))
        .where(JournalEntry.id == journal_id)
    )
    journal = result.scalar_one_or_none()

    if not journal:
        raise HTTPException(status_code=404, detail="Journal entry not found")

    if journal.status != JournalStatus.DRAFT:
        raise HTTPException(
            status_code=400,
            detail=f"Only DRAFT entries can be submitted. Current status: {journal.status}"
        )

    # Determine approval level based on amount
    approval_level = _get_approval_level(journal.total_debit)

    # Update journal for submission
    journal.status = JournalStatus.PENDING_APPROVAL.value
    journal.submitted_by = current_user.id
    journal.submitted_at = datetime.now(timezone.utc)
    journal.approval_level = approval_level

    await db.commit()
    await db.refresh(journal)

    # Get creator name
    creator_name = _get_user_name(journal.creator) if journal.creator else None

    return JournalApprovalResponse(
        id=journal.id,
        entry_number=journal.entry_number,
        status=journal.status,
        total_debit=journal.total_debit,
        total_credit=journal.total_credit,
        narration=journal.narration,
        created_by=journal.created_by,
        created_at=journal.created_at,
        creator_name=creator_name,
        submitted_by=journal.submitted_by,
        submitted_at=journal.submitted_at,
        submitter_name=_get_user_name(current_user),
        approval_level=journal.approval_level,
        message=f"Journal entry submitted for {approval_level} approval"
    )


@router.post(
    "/journals/{journal_id}/approve",
    response_model=JournalApprovalResponse,
    dependencies=[Depends(require_permissions("journals:approve"))]
)
async def approve_journal_entry(
    journal_id: UUID,
    request: JournalApproveRequest,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """
    Approve a pending journal entry (Checker action).

    The approver (checker) must be different from the maker (creator).
    If auto_post is True, the entry will be automatically posted to GL.
    """
    result = await db.execute(
        select(JournalEntry)
        .options(selectinload(JournalEntry.lines))
        .options(selectinload(JournalEntry.creator))
        .where(JournalEntry.id == journal_id)
    )
    journal = result.scalar_one_or_none()

    if not journal:
        raise HTTPException(status_code=404, detail="Journal entry not found")

    if journal.status != JournalStatus.PENDING_APPROVAL:
        raise HTTPException(
            status_code=400,
            detail=f"Only PENDING_APPROVAL entries can be approved. Current status: {journal.status}"
        )

    # Maker-Checker validation: Approver must be different from creator
    if journal.created_by == current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Maker-Checker violation: You cannot approve your own journal entry"
        )

    # Update journal for approval
    journal.status = JournalStatus.APPROVED.value
    journal.approved_by = current_user.id
    journal.approved_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(journal)

    message = "Journal entry approved successfully"

    # Auto-post if requested
    if request.auto_post:
        # Post to General Ledger
        for line in journal.lines:
            # Get account for running balance
            acc_result = await db.execute(
                select(ChartOfAccount).where(ChartOfAccount.id == line.account_id)
            )
            account = acc_result.scalar_one()

            # Update account balance
            if account.account_type in [AccountType.ASSET, AccountType.EXPENSE]:
                account.current_balance += (line.debit_amount - line.credit_amount)
            else:
                account.current_balance += (line.credit_amount - line.debit_amount)

            # Create GL entry
            gl_entry = GeneralLedger(
                account_id=line.account_id,
                period_id=journal.period_id,
                transaction_date=journal.entry_date,
                journal_entry_id=journal.id,
                journal_line_id=line.id,
                debit_amount=line.debit_amount,
                credit_amount=line.credit_amount,
                running_balance=account.current_balance,
                narration=line.description or journal.narration,
                cost_center_id=line.cost_center_id,
                channel_id=journal.channel_id,
            )
            db.add(gl_entry)

        # Update journal to POSTED
        journal.status = JournalStatus.POSTED.value
        journal.posted_by = current_user.id
        journal.posted_at = datetime.now(timezone.utc)

        await db.commit()
        await db.refresh(journal)
        message = "Journal entry approved and posted to General Ledger"

    return JournalApprovalResponse(
        id=journal.id,
        entry_number=journal.entry_number,
        status=journal.status,
        total_debit=journal.total_debit,
        total_credit=journal.total_credit,
        narration=journal.narration,
        created_by=journal.created_by,
        created_at=journal.created_at,
        creator_name=_get_user_name(journal.creator),
        submitted_by=journal.submitted_by,
        submitted_at=journal.submitted_at,
        approval_level=journal.approval_level,
        approved_by=journal.approved_by,
        approved_at=journal.approved_at,
        approver_name=_get_user_name(current_user),
        posted_by=journal.posted_by,
        posted_at=journal.posted_at,
        poster_name=_get_user_name(current_user) if journal.posted_by else None,
        message=message
    )


@router.post(
    "/journals/{journal_id}/reject",
    response_model=JournalApprovalResponse,
    dependencies=[Depends(require_permissions("journals:approve"))]
)
async def reject_journal_entry(
    journal_id: UUID,
    request: JournalRejectRequest,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """
    Reject a pending journal entry (Checker action).

    A rejection reason is required. The entry will move back to REJECTED status
    and can be edited and resubmitted by the maker.
    """
    result = await db.execute(
        select(JournalEntry)
        .options(selectinload(JournalEntry.lines))
        .options(selectinload(JournalEntry.creator))
        .where(JournalEntry.id == journal_id)
    )
    journal = result.scalar_one_or_none()

    if not journal:
        raise HTTPException(status_code=404, detail="Journal entry not found")

    if journal.status != JournalStatus.PENDING_APPROVAL:
        raise HTTPException(
            status_code=400,
            detail=f"Only PENDING_APPROVAL entries can be rejected. Current status: {journal.status}"
        )

    # Maker-Checker validation
    if journal.created_by == current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Maker-Checker violation: You cannot reject your own journal entry"
        )

    # Update journal for rejection
    journal.status = JournalStatus.REJECTED.value
    journal.approved_by = current_user.id  # Record who rejected
    journal.approved_at = datetime.now(timezone.utc)
    journal.rejection_reason = request.reason

    await db.commit()
    await db.refresh(journal)

    return JournalApprovalResponse(
        id=journal.id,
        entry_number=journal.entry_number,
        status=journal.status,
        total_debit=journal.total_debit,
        total_credit=journal.total_credit,
        narration=journal.narration,
        created_by=journal.created_by,
        created_at=journal.created_at,
        creator_name=_get_user_name(journal.creator),
        submitted_by=journal.submitted_by,
        submitted_at=journal.submitted_at,
        approval_level=journal.approval_level,
        approved_by=journal.approved_by,
        approved_at=journal.approved_at,
        approver_name=_get_user_name(current_user),
        rejection_reason=journal.rejection_reason,
        message=f"Journal entry rejected: {request.reason}"
    )


@router.post(
    "/journals/{journal_id}/resubmit",
    response_model=JournalApprovalResponse,
    dependencies=[Depends(require_permissions("journals:create"))]
)
async def resubmit_rejected_journal(
    journal_id: UUID,
    request: JournalSubmitRequest,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """
    Resubmit a rejected journal entry for approval.

    Only the original maker can resubmit after making necessary corrections.
    """
    result = await db.execute(
        select(JournalEntry)
        .options(selectinload(JournalEntry.creator))
        .where(JournalEntry.id == journal_id)
    )
    journal = result.scalar_one_or_none()

    if not journal:
        raise HTTPException(status_code=404, detail="Journal entry not found")

    if journal.status != JournalStatus.REJECTED:
        raise HTTPException(
            status_code=400,
            detail=f"Only REJECTED entries can be resubmitted. Current status: {journal.status}"
        )

    # Only original maker can resubmit
    if journal.created_by != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="Only the original maker can resubmit a rejected entry"
        )

    # Reset approval fields and resubmit
    approval_level = _get_approval_level(journal.total_debit)
    journal.status = JournalStatus.PENDING_APPROVAL.value
    journal.submitted_by = current_user.id
    journal.submitted_at = datetime.now(timezone.utc)
    journal.approval_level = approval_level
    journal.approved_by = None
    journal.approved_at = None
    journal.rejection_reason = None

    await db.commit()
    await db.refresh(journal)

    return JournalApprovalResponse(
        id=journal.id,
        entry_number=journal.entry_number,
        status=journal.status,
        total_debit=journal.total_debit,
        total_credit=journal.total_credit,
        narration=journal.narration,
        created_by=journal.created_by,
        created_at=journal.created_at,
        creator_name=_get_user_name(journal.creator),
        submitted_by=journal.submitted_by,
        submitted_at=journal.submitted_at,
        submitter_name=_get_user_name(current_user),
        approval_level=journal.approval_level,
        message=f"Journal entry resubmitted for {approval_level} approval"
    )


@router.post(
    "/journals/{journal_id}/post",
    response_model=JournalEntryResponse,
    dependencies=[Depends(require_permissions("journals:approve"))]
)
async def post_journal_entry(
    journal_id: UUID,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Post an approved journal entry to the General Ledger."""
    result = await db.execute(
        select(JournalEntry)
        .options(selectinload(JournalEntry.lines))
        .where(JournalEntry.id == journal_id)
    )
    journal = result.scalar_one_or_none()

    if not journal:
        raise HTTPException(status_code=404, detail="Journal entry not found")

    if journal.status != JournalStatus.APPROVED:
        raise HTTPException(
            status_code=400,
            detail="Only approved journals can be posted"
        )

    # Create General Ledger entries for each line
    for line in journal.lines:
        gl_entry = GeneralLedger(
            account_id=line.account_id,
            period_id=journal.period_id,
            entry_date=journal.entry_date,
            journal_id=journal.id,
            entry_number=journal.entry_number,
            journal_type=journal.journal_type,
            debit_amount=line.debit_amount,
            credit_amount=line.credit_amount,
            balance=line.debit_amount - line.credit_amount,
            narration=line.narration or journal.narration,
            cost_center_id=line.cost_center_id,
            reference_type=journal.reference_type,
            reference_number=journal.reference_number,
            created_by=current_user.id,
        )
        db.add(gl_entry)

        # Update account balance
        account_result = await db.execute(
            select(ChartOfAccount).where(ChartOfAccount.id == line.account_id)
        )
        account = account_result.scalar_one()

        # For Assets and Expenses, debit increases; for Liabilities, Equity, Revenue, credit increases
        if account.account_type in [AccountType.ASSET, AccountType.EXPENSE]:
            account.current_balance += (line.debit_amount - line.credit_amount)
        else:  # LIABILITY, EQUITY, REVENUE
            account.current_balance += (line.credit_amount - line.debit_amount)

    # Update journal status
    journal.status = JournalStatus.POSTED.value
    journal.posted_by = current_user.id
    journal.posted_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(journal)

    return journal


class JournalReversalBody(BaseModel):
    """Request body for journal reversal."""
    reversal_date: date
    reason: Optional[str] = None


@router.post(
    "/journals/{journal_id}/reverse",
    response_model=JournalEntryResponse,
    dependencies=[Depends(require_permissions("journals:reverse"))]
)
async def reverse_journal_entry(
    journal_id: UUID,
    body: JournalReversalBody,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Create a reversal journal entry."""
    reversal_date = body.reversal_date
    reason = body.reason
    result = await db.execute(
        select(JournalEntry)
        .options(selectinload(JournalEntry.lines))
        .where(JournalEntry.id == journal_id)
    )
    original = result.scalar_one_or_none()

    if not original:
        raise HTTPException(status_code=404, detail="Journal entry not found")

    if original.status != JournalStatus.POSTED:
        raise HTTPException(status_code=400, detail="Only posted journals can be reversed")

    if original.is_reversed:
        raise HTTPException(status_code=400, detail="Journal already reversed")

    # Verify period is open
    period_result = await db.execute(
        select(FinancialPeriod).where(
            and_(
                FinancialPeriod.start_date <= reversal_date,
                FinancialPeriod.end_date >= reversal_date,
                FinancialPeriod.status == PeriodStatus.OPEN,
            )
        )
    )
    period = period_result.scalar_one_or_none()

    if not period:
        raise HTTPException(status_code=400, detail="No open period for reversal date")

    # Generate reversal journal number
    today = date.today()
    count_result = await db.execute(
        select(func.count(JournalEntry.id)).where(
            func.date(JournalEntry.created_at) == today
        )
    )
    count = count_result.scalar() or 0
    reversal_number = f"JV-{today.strftime('%Y%m%d')}-{str(count + 1).zfill(4)}"

    # Create reversal journal
    narration_text = f"Reversal of {original.entry_number}"
    if reason:
        narration_text += f" - {reason}"

    reversal = JournalEntry(
        entry_number=reversal_number,
        entry_type="REVERSAL",
        entry_date=reversal_date,
        period_id=period.id,
        narration=narration_text,
        source_type="REVERSAL",
        source_number=original.entry_number,
        source_id=original.id,
        total_debit=original.total_credit,  # Swap
        total_credit=original.total_debit,
        reversal_of_id=original.id,
        status=JournalStatus.APPROVED,
        approved_by=current_user.id,
        approved_at=datetime.now(timezone.utc),
        created_by=current_user.id,
    )

    db.add(reversal)
    await db.flush()

    # Create reversed lines (swap debit/credit)
    line_number = 0
    for orig_line in original.lines:
        line_number += 1
        line = JournalEntryLine(
            journal_entry_id=reversal.id,
            line_number=line_number,
            account_id=orig_line.account_id,
            debit_amount=orig_line.credit_amount,  # Swap
            credit_amount=orig_line.debit_amount,
            cost_center_id=orig_line.cost_center_id,
            description=f"Reversal: {orig_line.description or ''}",
        )
        db.add(line)

    # Mark original as reversed
    original.is_reversed = True
    original.reversed_by_id = reversal.id

    await db.commit()

    # Load full reversal
    result = await db.execute(
        select(JournalEntry)
        .options(selectinload(JournalEntry.lines))
        .where(JournalEntry.id == reversal.id)
    )
    reversal = result.scalar_one()

    return reversal


# ==================== General Ledger ====================

@router.get(
    "/ledger/{account_id}",
    dependencies=[Depends(require_permissions("finance:view"))]
)
async def get_account_ledger(
    account_id: UUID,
    db: DB,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    current_user: User = Depends(get_current_user),
):
    """Get General Ledger entries for an account."""
    # Verify account
    account_result = await db.execute(
        select(ChartOfAccount).where(ChartOfAccount.id == account_id)
    )
    account = account_result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    # Build query with join to get entry_number from journal_entries
    query = (
        select(GeneralLedger, JournalEntry.entry_number)
        .join(JournalEntry, GeneralLedger.journal_entry_id == JournalEntry.id)
        .where(GeneralLedger.account_id == account_id)
    )
    count_query = select(func.count(GeneralLedger.id)).where(
        GeneralLedger.account_id == account_id
    )

    if start_date:
        query = query.where(GeneralLedger.transaction_date >= start_date)
        count_query = count_query.where(GeneralLedger.transaction_date >= start_date)
    if end_date:
        query = query.where(GeneralLedger.transaction_date <= end_date)
        count_query = count_query.where(GeneralLedger.transaction_date <= end_date)

    # Get totals
    totals_query = select(
        func.coalesce(func.sum(GeneralLedger.debit_amount), 0).label("total_debit"),
        func.coalesce(func.sum(GeneralLedger.credit_amount), 0).label("total_credit"),
    ).where(GeneralLedger.account_id == account_id)

    if start_date:
        totals_query = totals_query.where(GeneralLedger.transaction_date >= start_date)
    if end_date:
        totals_query = totals_query.where(GeneralLedger.transaction_date <= end_date)

    totals_result = await db.execute(totals_query)
    totals = totals_result.one()

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(GeneralLedger.transaction_date, GeneralLedger.created_at)
    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    rows = result.all()

    # Build response items matching frontend LedgerEntry interface
    items = []
    for gl, entry_number in rows:
        items.append({
            "id": str(gl.id),
            "entry_date": gl.transaction_date.isoformat(),
            "entry_number": entry_number or "",
            "narration": gl.narration or "",
            "debit": float(gl.debit_amount or 0),
            "credit": float(gl.credit_amount or 0),
            "running_balance": float(gl.running_balance or 0),
            "reference": None,
        })

    # Calculate pages
    pages = (total + limit - 1) // limit if limit > 0 else 0

    return {
        "account_id": str(account_id),
        "account_code": account.account_code,
        "account_name": account.account_name,
        "items": items,
        "total": total,
        "pages": pages,
        "total_debit": float(totals.total_debit),
        "total_credit": float(totals.total_credit),
        "opening_balance": float(account.opening_balance or 0),
        "closing_balance": float(account.current_balance or 0),
    }


# ==================== Reports ====================

@router.get(
    "/reports/trial-balance",
    response_model=TrialBalanceResponse,
    dependencies=[Depends(require_permissions("finance:view"))]
)
async def get_trial_balance(
    db: DB,
    as_of_date: date = Query(default_factory=date.today),
    current_user: User = Depends(get_current_user),
):
    """Get Trial Balance report."""
    # Get all accounts with balances
    query = select(ChartOfAccount).where(
        and_(
            ChartOfAccount.is_active == True,
            ChartOfAccount.is_group == False,
        )
    ).order_by(ChartOfAccount.account_code)

    result = await db.execute(query)
    accounts = result.scalars().all()

    items = []
    total_debit = Decimal("0")
    total_credit = Decimal("0")

    for account in accounts:
        balance = account.current_balance

        if balance == 0:
            continue

        debit = Decimal("0")
        credit = Decimal("0")

        # Assets and Expenses have debit balances
        if account.account_type in [AccountType.ASSET, AccountType.EXPENSE]:
            if balance > 0:
                debit = balance
            else:
                credit = abs(balance)
        else:  # Liabilities, Equity, Revenue have credit balances
            if balance > 0:
                credit = balance
            else:
                debit = abs(balance)

        total_debit += debit
        total_credit += credit

        items.append(TrialBalanceItem(
            account_id=account.id,
            account_code=account.account_code,
            account_name=account.name,
            account_type=account.account_type,
            debit_balance=debit,
            credit_balance=credit,
        ))

    return TrialBalanceResponse(
        as_of_date=as_of_date,
        items=items,
        total_debit=total_debit,
        total_credit=total_credit,
        is_balanced=total_debit == total_credit,
    )


@router.get(
    "/reports/balance-sheet",
    dependencies=[Depends(require_permissions("finance:view"))]
)
async def get_balance_sheet(
    db: DB,
    as_of_date: date = Query(default_factory=date.today),
    current_user: User = Depends(get_current_user),
):
    """Get Balance Sheet report."""
    # Assets
    assets_query = select(
        ChartOfAccount.account_sub_type,
        func.sum(ChartOfAccount.current_balance).label("total")
    ).where(
        and_(
            ChartOfAccount.account_type == AccountType.ASSET,
            ChartOfAccount.is_group == False,
        )
    ).group_by(ChartOfAccount.account_sub_type)

    assets_result = await db.execute(assets_query)
    assets_data = {row.account_sub_type if row.account_sub_type else "other": float(row.total or 0) for row in assets_result.all()}

    # Liabilities
    liabilities_query = select(
        ChartOfAccount.account_sub_type,
        func.sum(ChartOfAccount.current_balance).label("total")
    ).where(
        and_(
            ChartOfAccount.account_type == AccountType.LIABILITY,
            ChartOfAccount.is_group == False,
        )
    ).group_by(ChartOfAccount.account_sub_type)

    liabilities_result = await db.execute(liabilities_query)
    liabilities_data = {row.account_sub_type if row.account_sub_type else "other": float(row.total or 0) for row in liabilities_result.all()}

    # Equity
    equity_query = select(
        func.sum(ChartOfAccount.current_balance)
    ).where(
        and_(
            ChartOfAccount.account_type == AccountType.EQUITY,
            ChartOfAccount.is_group == False,
        )
    )
    equity_result = await db.execute(equity_query)
    total_equity = float(equity_result.scalar() or 0)

    total_assets = sum(assets_data.values())
    total_liabilities = sum(liabilities_data.values())

    return {
        "as_of_date": as_of_date.isoformat(),
        "assets": {
            "breakdown": assets_data,
            "total": total_assets,
        },
        "liabilities": {
            "breakdown": liabilities_data,
            "total": total_liabilities,
        },
        "equity": {
            "total": total_equity,
        },
        "total_liabilities_and_equity": total_liabilities + total_equity,
        "is_balanced": abs(total_assets - (total_liabilities + total_equity)) < 0.01,
    }


@router.get(
    "/reports/profit-loss",
    dependencies=[Depends(require_permissions("finance:view"))]
)
async def get_profit_loss(
    start_date: date,
    end_date: date,
    db: DB,
    channel_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_user),
):
    """
    Get Profit & Loss statement.

    Args:
        start_date: Start date for P&L period
        end_date: End date for P&L period
        channel_id: Optional - filter by sales channel for channel-wise P&L

    Returns overall P&L and channel breakdown if no channel_id specified.
    """
    from app.models.channel import SalesChannel

    # Build base conditions
    date_filter = and_(
        GeneralLedger.transaction_date >= start_date,
        GeneralLedger.transaction_date <= end_date,
    )

    # Add channel filter if specified
    channel_filter = GeneralLedger.channel_id == channel_id if channel_id else True

    # Revenue query
    revenue_query = select(
        ChartOfAccount.account_sub_type,
        func.sum(GeneralLedger.credit_amount - GeneralLedger.debit_amount).label("total")
    ).join(
        GeneralLedger, GeneralLedger.account_id == ChartOfAccount.id
    ).where(
        and_(
            ChartOfAccount.account_type == AccountType.REVENUE,
            date_filter,
            channel_filter,
        )
    ).group_by(ChartOfAccount.account_sub_type)

    revenue_result = await db.execute(revenue_query)
    revenue_data = {row.account_sub_type if row.account_sub_type else "other": float(row.total or 0) for row in revenue_result.all()}

    # Expenses query (COGS - 5xxx accounts)
    cogs_query = select(
        func.sum(GeneralLedger.debit_amount - GeneralLedger.credit_amount).label("total")
    ).join(
        ChartOfAccount, GeneralLedger.account_id == ChartOfAccount.id
    ).where(
        and_(
            ChartOfAccount.account_type == AccountType.EXPENSE,
            ChartOfAccount.account_code.like("5%"),  # COGS accounts
            date_filter,
            channel_filter,
        )
    )
    cogs_result = await db.execute(cogs_query)
    cogs_total = float(cogs_result.scalar() or 0)

    # Operating expenses (6xxx accounts)
    opex_query = select(
        ChartOfAccount.account_sub_type,
        func.sum(GeneralLedger.debit_amount - GeneralLedger.credit_amount).label("total")
    ).join(
        GeneralLedger, GeneralLedger.account_id == ChartOfAccount.id
    ).where(
        and_(
            ChartOfAccount.account_type == AccountType.EXPENSE,
            ChartOfAccount.account_code.like("6%"),  # Operating expense accounts
            date_filter,
            channel_filter,
        )
    ).group_by(ChartOfAccount.account_sub_type)

    opex_result = await db.execute(opex_query)
    opex_data = {row.account_sub_type if row.account_sub_type else "other": float(row.total or 0) for row in opex_result.all()}
    opex_total = sum(opex_data.values())

    # Other expenses (7xxx accounts)
    other_exp_query = select(
        func.sum(GeneralLedger.debit_amount - GeneralLedger.credit_amount).label("total")
    ).join(
        ChartOfAccount, GeneralLedger.account_id == ChartOfAccount.id
    ).where(
        and_(
            ChartOfAccount.account_type == AccountType.EXPENSE,
            ChartOfAccount.account_code.like("7%"),  # Other expense accounts
            date_filter,
            channel_filter,
        )
    )
    other_exp_result = await db.execute(other_exp_query)
    other_exp_total = float(other_exp_result.scalar() or 0)

    total_revenue = sum(revenue_data.values())
    gross_profit = total_revenue - cogs_total
    operating_profit = gross_profit - opex_total
    net_income = operating_profit - other_exp_total

    # Get channel-wise breakdown if no specific channel requested
    channel_breakdown = []
    if not channel_id:
        channel_pl_query = select(
            SalesChannel.id,
            SalesChannel.code,
            SalesChannel.name,
            func.sum(
                case(
                    (ChartOfAccount.account_type == AccountType.REVENUE,
                     GeneralLedger.credit_amount - GeneralLedger.debit_amount),
                    else_=0
                )
            ).label("revenue"),
            func.sum(
                case(
                    (ChartOfAccount.account_type == AccountType.EXPENSE,
                     GeneralLedger.debit_amount - GeneralLedger.credit_amount),
                    else_=0
                )
            ).label("expenses")
        ).select_from(GeneralLedger).join(
            ChartOfAccount, GeneralLedger.account_id == ChartOfAccount.id
        ).join(
            SalesChannel, GeneralLedger.channel_id == SalesChannel.id
        ).where(
            date_filter
        ).group_by(
            SalesChannel.id, SalesChannel.code, SalesChannel.name
        )

        channel_result = await db.execute(channel_pl_query)
        for row in channel_result.all():
            channel_breakdown.append({
                "channel_id": str(row.id),
                "channel_code": row.code,
                "channel_name": row.name,
                "revenue": float(row.revenue or 0),
                "expenses": float(row.expenses or 0),
                "net_profit": float((row.revenue or 0) - (row.expenses or 0)),
            })

    return {
        "period_start": start_date.isoformat(),
        "period_end": end_date.isoformat(),
        "channel_id": str(channel_id) if channel_id else None,
        "revenue": {
            "breakdown": revenue_data,
            "total": total_revenue,
        },
        "cost_of_goods_sold": cogs_total,
        "gross_profit": gross_profit,
        "operating_expenses": {
            "breakdown": opex_data,
            "total": opex_total,
        },
        "operating_profit": operating_profit,
        "other_expenses": other_exp_total,
        "net_income": net_income,
        "channel_breakdown": channel_breakdown if not channel_id else None,
    }


@router.get(
    "/reports/cash-flow",
    dependencies=[Depends(require_permissions("finance:view"))]
)
async def get_cash_flow_statement(
    start_date: date,
    end_date: date,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """
    Get Cash Flow Statement (Indirect Method).

    Shows cash movements categorized into:
    - Operating Activities: Cash from normal business operations
    - Investing Activities: Cash from buying/selling assets
    - Financing Activities: Cash from loans, equity, dividends

    Uses the indirect method starting with Net Income and adjusting for non-cash items.
    """
    from app.models.banking import BankAccount, BankTransaction

    # Date filter
    date_filter = and_(
        GeneralLedger.transaction_date >= start_date,
        GeneralLedger.transaction_date <= end_date,
    )

    # ========== 1. OPERATING ACTIVITIES (Indirect Method) ==========

    # Start with Net Income (Revenue - Expenses)
    # Revenue
    revenue_query = select(
        func.sum(GeneralLedger.credit_amount - GeneralLedger.debit_amount)
    ).select_from(GeneralLedger).join(
        ChartOfAccount, GeneralLedger.account_id == ChartOfAccount.id
    ).where(
        and_(
            ChartOfAccount.account_type == AccountType.REVENUE,
            date_filter
        )
    )
    revenue_result = await db.execute(revenue_query)
    total_revenue = revenue_result.scalar() or Decimal("0")

    # Expenses
    expense_query = select(
        func.sum(GeneralLedger.debit_amount - GeneralLedger.credit_amount)
    ).select_from(GeneralLedger).join(
        ChartOfAccount, GeneralLedger.account_id == ChartOfAccount.id
    ).where(
        and_(
            ChartOfAccount.account_type == AccountType.EXPENSE,
            date_filter
        )
    )
    expense_result = await db.execute(expense_query)
    total_expenses = expense_result.scalar() or Decimal("0")

    net_income = total_revenue - total_expenses

    # Adjustments for non-cash items
    # 1. Depreciation (add back - it's a non-cash expense)
    depreciation_query = select(
        func.sum(GeneralLedger.debit_amount - GeneralLedger.credit_amount)
    ).select_from(GeneralLedger).join(
        ChartOfAccount, GeneralLedger.account_id == ChartOfAccount.id
    ).where(
        and_(
            ChartOfAccount.sub_type == AccountSubType.DEPRECIATION,
            date_filter
        )
    )
    dep_result = await db.execute(depreciation_query)
    depreciation = dep_result.scalar() or Decimal("0")

    # 2. Change in Accounts Receivable
    ar_start = await _get_account_balance_at_date(
        db, AccountSubType.ACCOUNTS_RECEIVABLE, start_date - timedelta(days=1)
    )
    ar_end = await _get_account_balance_at_date(
        db, AccountSubType.ACCOUNTS_RECEIVABLE, end_date
    )
    change_in_ar = ar_end - ar_start  # Increase = cash outflow (negative)

    # 3. Change in Inventory
    inv_start = await _get_account_balance_at_date(
        db, AccountSubType.INVENTORY, start_date - timedelta(days=1)
    )
    inv_end = await _get_account_balance_at_date(
        db, AccountSubType.INVENTORY, end_date
    )
    change_in_inventory = inv_end - inv_start  # Increase = cash outflow

    # 4. Change in Accounts Payable
    ap_start = await _get_account_balance_at_date(
        db, AccountSubType.ACCOUNTS_PAYABLE, start_date - timedelta(days=1)
    )
    ap_end = await _get_account_balance_at_date(
        db, AccountSubType.ACCOUNTS_PAYABLE, end_date
    )
    change_in_ap = ap_end - ap_start  # Increase = cash inflow (positive)

    # 5. Change in Tax Payable
    tax_start = await _get_account_balance_at_date(
        db, AccountSubType.TAX_PAYABLE, start_date - timedelta(days=1)
    )
    tax_end = await _get_account_balance_at_date(
        db, AccountSubType.TAX_PAYABLE, end_date
    )
    change_in_tax = tax_end - tax_start

    operating_cash_flow = (
        net_income
        + depreciation  # Add back non-cash expense
        - change_in_ar  # Increase in AR = cash used
        - change_in_inventory  # Increase in inventory = cash used
        + change_in_ap  # Increase in AP = cash provided
        + change_in_tax  # Increase in tax payable = cash provided
    )

    # ========== 2. INVESTING ACTIVITIES ==========

    # Change in Fixed Assets (purchases/sales)
    fa_query = select(
        func.sum(GeneralLedger.debit_amount - GeneralLedger.credit_amount)
    ).select_from(GeneralLedger).join(
        ChartOfAccount, GeneralLedger.account_id == ChartOfAccount.id
    ).where(
        and_(
            ChartOfAccount.sub_type == AccountSubType.FIXED_ASSETS,
            date_filter
        )
    )
    fa_result = await db.execute(fa_query)
    fixed_asset_change = fa_result.scalar() or Decimal("0")

    # Investments
    inv_query = select(
        func.sum(GeneralLedger.debit_amount - GeneralLedger.credit_amount)
    ).select_from(GeneralLedger).join(
        ChartOfAccount, GeneralLedger.account_id == ChartOfAccount.id
    ).where(
        and_(
            ChartOfAccount.sub_type == AccountSubType.INVESTMENTS,
            date_filter
        )
    )
    inv_result = await db.execute(inv_query)
    investment_change = inv_result.scalar() or Decimal("0")

    investing_cash_flow = -(fixed_asset_change + investment_change)  # Purchases are negative

    # ========== 3. FINANCING ACTIVITIES ==========

    # Change in Loans Payable
    loan_start = await _get_account_balance_at_date(
        db, AccountSubType.LOANS_PAYABLE, start_date - timedelta(days=1)
    )
    loan_end = await _get_account_balance_at_date(
        db, AccountSubType.LOANS_PAYABLE, end_date
    )
    change_in_loans = loan_end - loan_start  # Increase = cash inflow

    # Change in Equity/Capital
    equity_query = select(
        func.sum(GeneralLedger.credit_amount - GeneralLedger.debit_amount)
    ).select_from(GeneralLedger).join(
        ChartOfAccount, GeneralLedger.account_id == ChartOfAccount.id
    ).where(
        and_(
            ChartOfAccount.account_type == AccountType.EQUITY,
            date_filter
        )
    )
    equity_result = await db.execute(equity_query)
    equity_change = equity_result.scalar() or Decimal("0")

    financing_cash_flow = change_in_loans + equity_change

    # ========== 4. TOTAL & RECONCILIATION ==========

    net_change_in_cash = operating_cash_flow + investing_cash_flow + financing_cash_flow

    # Get actual cash balance change from bank accounts
    cash_start = await _get_account_balance_at_date(
        db, AccountSubType.CASH, start_date - timedelta(days=1)
    )
    bank_start = await _get_account_balance_at_date(
        db, AccountSubType.BANK, start_date - timedelta(days=1)
    )
    cash_end = await _get_account_balance_at_date(
        db, AccountSubType.CASH, end_date
    )
    bank_end = await _get_account_balance_at_date(
        db, AccountSubType.BANK, end_date
    )

    beginning_cash = cash_start + bank_start
    ending_cash = cash_end + bank_end
    actual_cash_change = ending_cash - beginning_cash

    return {
        "period_start": start_date.isoformat(),
        "period_end": end_date.isoformat(),

        "operating_activities": {
            "net_income": float(net_income),
            "adjustments": {
                "depreciation": float(depreciation),
                "change_in_accounts_receivable": float(-change_in_ar),
                "change_in_inventory": float(-change_in_inventory),
                "change_in_accounts_payable": float(change_in_ap),
                "change_in_taxes_payable": float(change_in_tax),
            },
            "total": float(operating_cash_flow),
        },

        "investing_activities": {
            "fixed_asset_purchases": float(-fixed_asset_change) if fixed_asset_change > 0 else 0,
            "fixed_asset_sales": float(-fixed_asset_change) if fixed_asset_change < 0 else 0,
            "investment_changes": float(-investment_change),
            "total": float(investing_cash_flow),
        },

        "financing_activities": {
            "loan_proceeds": float(change_in_loans) if change_in_loans > 0 else 0,
            "loan_repayments": float(-change_in_loans) if change_in_loans < 0 else 0,
            "equity_changes": float(equity_change),
            "total": float(financing_cash_flow),
        },

        "net_change_in_cash": float(net_change_in_cash),
        "beginning_cash_balance": float(beginning_cash),
        "ending_cash_balance": float(ending_cash),
        "actual_cash_change": float(actual_cash_change),
        "reconciliation_difference": float(net_change_in_cash - actual_cash_change),
    }


async def _get_account_balance_at_date(
    db: AsyncSession,
    sub_type: AccountSubType,
    as_of_date: date
) -> Decimal:
    """Helper to get account balance for a subtype as of a date."""
    query = select(
        func.coalesce(
            func.sum(ChartOfAccount.current_balance),
            0
        )
    ).where(
        ChartOfAccount.sub_type == sub_type
    )
    result = await db.execute(query)
    return result.scalar() or Decimal("0")


# ==================== Tax Configuration ====================

@router.get(
    "/tax-configs",
    response_model=List[TaxConfigurationResponse],
    dependencies=[Depends(require_permissions("tax_configs:view"))]
)
async def list_tax_configurations(
    db: DB,
    is_active: bool = True,
    current_user: User = Depends(get_current_user),
):
    """List tax configurations."""
    query = select(TaxConfiguration)
    if is_active is not None:
        query = query.where(TaxConfiguration.is_active == is_active)

    query = query.order_by(TaxConfiguration.tax_name)
    result = await db.execute(query)
    configs = result.scalars().all()

    return [TaxConfigurationResponse.model_validate(c) for c in configs]


@router.post(
    "/tax-configs",
    response_model=TaxConfigurationResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions("tax_configs:create"))]
)
async def create_tax_configuration(
    config_in: TaxConfigurationCreate,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Create a new tax configuration."""
    config = TaxConfiguration(
        **config_in.model_dump(),
        created_by=current_user.id,
    )

    db.add(config)
    await db.commit()
    await db.refresh(config)

    return config


@router.get(
    "/tax-configs/{tax_config_id}",
    response_model=TaxConfigurationResponse,
    dependencies=[Depends(require_permissions("tax_configs:view"))]
)
async def get_tax_configuration(
    tax_config_id: UUID,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Get tax configuration by ID."""
    result = await db.execute(
        select(TaxConfiguration).where(TaxConfiguration.id == tax_config_id)
    )
    config = result.scalar_one_or_none()

    if not config:
        raise HTTPException(status_code=404, detail="Tax configuration not found")

    return config


@router.put(
    "/tax-configs/{tax_config_id}",
    response_model=TaxConfigurationResponse,
    dependencies=[Depends(require_permissions("tax_configs:update"))]
)
async def update_tax_configuration(
    tax_config_id: UUID,
    config_in: TaxConfigurationUpdate,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Update tax configuration details."""
    result = await db.execute(
        select(TaxConfiguration).where(TaxConfiguration.id == tax_config_id)
    )
    config = result.scalar_one_or_none()

    if not config:
        raise HTTPException(status_code=404, detail="Tax configuration not found")

    update_data = config_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(config, field, value)

    config.updated_by = current_user.id

    await db.commit()
    await db.refresh(config)

    return config


@router.delete(
    "/tax-configs/{tax_config_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permissions("tax_configs:delete"))]
)
async def delete_tax_configuration(
    tax_config_id: UUID,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Delete a tax configuration.

    Note: Tax configurations that are in use by products or invoices
    should be deactivated instead of deleted.
    """
    result = await db.execute(
        select(TaxConfiguration).where(TaxConfiguration.id == tax_config_id)
    )
    config = result.scalar_one_or_none()

    if not config:
        raise HTTPException(status_code=404, detail="Tax configuration not found")

    await db.delete(config)
    await db.commit()

    return None
