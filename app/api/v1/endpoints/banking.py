"""API endpoints for Banking module - Statement Import, Reconciliation & Cash Book."""
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import date, timedelta
from decimal import Decimal
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Form
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.models.user import User
from app.models.banking import BankAccount, BankTransaction, TransactionType
from app.api.deps import DB, get_current_user
from app.schemas.banking import (
    BankAccountCreate,
    BankAccountResponse,
    BankTransactionResponse,
    ImportResult,
    ReconciliationMatch,
)
from app.services.bank_import_service import BankImportService, BankImportError
from app.core.module_decorators import require_module


# ==================== Cash Book Schemas ====================

class CashBookEntry(BaseModel):
    """Single cash book entry."""
    id: UUID
    date: date
    description: str
    reference: Optional[str] = None
    receipt: Decimal = Decimal("0")
    payment: Decimal = Decimal("0")
    balance: Decimal
    transaction_type: Optional[str] = None
    is_reconciled: bool = False


class CashBookDailySummary(BaseModel):
    """Daily summary for cash book."""
    date: date
    opening_balance: Decimal
    total_receipts: Decimal
    total_payments: Decimal
    closing_balance: Decimal
    transaction_count: int


class CashBookResponse(BaseModel):
    """Cash Book report response."""
    account_id: UUID
    account_name: str
    bank_name: str
    period_start: date
    period_end: date
    opening_balance: Decimal
    total_receipts: Decimal
    total_payments: Decimal
    closing_balance: Decimal
    entries: List[CashBookEntry]
    daily_summary: Optional[List[CashBookDailySummary]] = None


class PettyCashEntry(BaseModel):
    """Petty cash entry."""
    id: UUID
    date: date
    description: str
    voucher_number: str
    category: str
    amount: Decimal
    is_receipt: bool
    balance: Decimal
    approved_by: Optional[str] = None


class PettyCashResponse(BaseModel):
    """Petty cash report."""
    period_start: date
    period_end: date
    opening_balance: Decimal
    total_receipts: Decimal
    total_payments: Decimal
    closing_balance: Decimal
    entries: List[PettyCashEntry]
    category_summary: Dict[str, Decimal]

router = APIRouter()


# ==================== Bank Accounts ====================

@router.post("/accounts", response_model=BankAccountResponse, status_code=status.HTTP_201_CREATED)
@require_module("finance")
async def create_bank_account(
    account_in: BankAccountCreate,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Create a new bank account."""
    # Check for duplicate account number
    existing = await db.execute(
        select(BankAccount).where(BankAccount.account_number == account_in.account_number)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail="Bank account with this account number already exists"
        )

    account = BankAccount(
        account_name=account_in.account_name,
        account_number=account_in.account_number,
        bank_name=account_in.bank_name,
        branch_name=account_in.branch_name,
        ifsc_code=account_in.ifsc_code,
        account_type=account_in.account_type,
        opening_balance=account_in.opening_balance,
        current_balance=account_in.opening_balance,
        ledger_account_id=account_in.ledger_account_id,
        created_by=current_user.id,
    )

    db.add(account)
    await db.commit()
    await db.refresh(account)

    return account


@router.get("/accounts", response_model=List[BankAccountResponse])
@require_module("finance")
async def list_bank_accounts(
    db: DB,
    is_active: Optional[bool] = True,
    current_user: User = Depends(get_current_user),
):
    """List all bank accounts."""
    query = select(BankAccount)
    if is_active is not None:
        query = query.where(BankAccount.is_active == is_active)

    query = query.order_by(BankAccount.bank_name, BankAccount.account_name)

    result = await db.execute(query)
    accounts = result.scalars().all()

    return accounts


@router.get("/accounts/{account_id}", response_model=BankAccountResponse)
@require_module("finance")
async def get_bank_account(
    account_id: UUID,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Get bank account by ID."""
    result = await db.execute(
        select(BankAccount).where(BankAccount.id == account_id)
    )
    account = result.scalar_one_or_none()

    if not account:
        raise HTTPException(status_code=404, detail="Bank account not found")

    return account


# ==================== Statement Import ====================

@router.post("/accounts/{account_id}/import-statement", response_model=ImportResult)
@require_module("finance")
async def import_bank_statement(
    account_id: UUID,
    file: UploadFile = File(...),
    bank_format: str = Form(default="AUTO"),
    skip_duplicates: bool = Form(default=True),
    db: DB = None,
    current_user: User = Depends(get_current_user),
):
    """
    Import bank statement from CSV or Excel file.

    Supported formats:
    - AUTO: Auto-detect bank format
    - HDFC: HDFC Bank statement format
    - ICICI: ICICI Bank statement format
    - SBI: State Bank of India format
    - GENERIC: Generic CSV with standard columns

    Expected columns:
    - Date: Transaction date
    - Description/Narration: Transaction description
    - Debit/Withdrawal: Debit amount
    - Credit/Deposit: Credit amount
    - Balance: Running balance (optional)
    - Reference: Transaction reference (optional)
    """
    # Validate file type
    filename = file.filename or ""
    if not (filename.endswith('.csv') or filename.endswith('.xlsx') or filename.endswith('.xls')):
        raise HTTPException(
            status_code=400,
            detail="Unsupported file format. Please upload CSV or Excel file."
        )

    # Verify bank account exists
    result = await db.execute(
        select(BankAccount).where(BankAccount.id == account_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Bank account not found")

    try:
        import_service = BankImportService(db)

        # Read file content
        file_content = await file.read()

        if filename.endswith('.csv'):
            # Decode CSV content
            try:
                content_str = file_content.decode('utf-8')
            except UnicodeDecodeError:
                # Try other encodings
                try:
                    content_str = file_content.decode('latin-1')
                except UnicodeDecodeError:
                    content_str = file_content.decode('cp1252')

            result = await import_service.import_csv_statement(
                bank_account_id=account_id,
                file_content=content_str,
                filename=filename,
                bank_format=bank_format,
                skip_duplicates=skip_duplicates,
                user_id=current_user.id
            )
        else:
            # Excel file
            result = await import_service.import_excel_statement(
                bank_account_id=account_id,
                file_bytes=file_content,
                filename=filename,
                bank_format=bank_format,
                skip_duplicates=skip_duplicates,
                user_id=current_user.id
            )

        return result

    except BankImportError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Import failed: {e.message}",
            headers={"X-Row-Number": str(e.row_number) if e.row_number else None}
        )


# ==================== Transactions ====================

@router.get("/accounts/{account_id}/transactions", response_model=List[BankTransactionResponse])
@require_module("finance")
async def list_bank_transactions(
    account_id: UUID,
    db: DB,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    is_reconciled: Optional[bool] = None,
    transaction_type: Optional[str] = None,
    current_user: User = Depends(get_current_user),
):
    """List bank transactions for an account."""
    query = select(BankTransaction).where(BankTransaction.bank_account_id == account_id)

    filters = []
    if start_date:
        filters.append(BankTransaction.transaction_date >= start_date)
    if end_date:
        filters.append(BankTransaction.transaction_date <= end_date)
    if is_reconciled is not None:
        filters.append(BankTransaction.is_reconciled == is_reconciled)
    if transaction_type:
        filters.append(BankTransaction.transaction_type == TransactionType(transaction_type))

    if filters:
        query = query.where(and_(*filters))

    query = query.order_by(BankTransaction.transaction_date.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    transactions = result.scalars().all()

    return [
        BankTransactionResponse(
            id=t.id,
            transaction_date=t.transaction_date,
            description=t.description,
            reference_number=t.reference_number,
            transaction_type=t.transaction_type if t.transaction_type else "UNKNOWN",
            amount=t.amount,
            debit_amount=t.debit_amount or Decimal("0"),
            credit_amount=t.credit_amount or Decimal("0"),
            running_balance=t.running_balance,
            is_reconciled=t.is_reconciled
        )
        for t in transactions
    ]


@router.get("/accounts/{account_id}/transactions/summary")
@require_module("finance")
async def get_transaction_summary(
    account_id: UUID,
    db: DB,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    current_user: User = Depends(get_current_user),
):
    """Get summary of bank transactions."""
    filters = [BankTransaction.bank_account_id == account_id]

    if start_date:
        filters.append(BankTransaction.transaction_date >= start_date)
    if end_date:
        filters.append(BankTransaction.transaction_date <= end_date)

    # Total count
    count_query = select(func.count(BankTransaction.id)).where(and_(*filters))
    count_result = await db.execute(count_query)
    total_count = count_result.scalar() or 0

    # Total debit
    debit_query = select(func.coalesce(func.sum(BankTransaction.debit_amount), 0)).where(and_(*filters))
    debit_result = await db.execute(debit_query)
    total_debit = debit_result.scalar() or Decimal("0")

    # Total credit
    credit_query = select(func.coalesce(func.sum(BankTransaction.credit_amount), 0)).where(and_(*filters))
    credit_result = await db.execute(credit_query)
    total_credit = credit_result.scalar() or Decimal("0")

    # Reconciled count
    reconciled_filters = filters + [BankTransaction.is_reconciled == True]
    reconciled_query = select(func.count(BankTransaction.id)).where(and_(*reconciled_filters))
    reconciled_result = await db.execute(reconciled_query)
    reconciled_count = reconciled_result.scalar() or 0

    return {
        "total_transactions": total_count,
        "total_debit": float(total_debit),
        "total_credit": float(total_credit),
        "net_change": float(total_credit - total_debit),
        "reconciled_count": reconciled_count,
        "unreconciled_count": total_count - reconciled_count,
        "reconciliation_percentage": round((reconciled_count / total_count * 100), 2) if total_count > 0 else 0
    }


# ==================== Reconciliation ====================

@router.get("/accounts/{account_id}/unreconciled")
@require_module("finance")
async def get_unreconciled_transactions(
    account_id: UUID,
    db: DB,
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
):
    """Get unreconciled bank transactions for matching."""
    import_service = BankImportService(db)
    transactions = await import_service.get_unreconciled_transactions(
        bank_account_id=account_id,
        limit=limit
    )

    return [
        {
            "id": str(t.id),
            "date": str(t.transaction_date),
            "description": t.description,
            "reference": t.reference_number,
            "type": t.transaction_type if t.transaction_type else None,
            "amount": float(t.amount),
            "debit": float(t.debit_amount) if t.debit_amount else 0,
            "credit": float(t.credit_amount) if t.credit_amount else 0,
        }
        for t in transactions
    ]


@router.post("/reconcile/match")
@require_module("finance")
async def match_transaction_with_journal(
    match_request: ReconciliationMatch,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Match a bank transaction with a journal entry for reconciliation."""
    import_service = BankImportService(db)

    try:
        result = await import_service.match_with_journal_entries(
            bank_transaction_id=match_request.bank_transaction_id,
            journal_entry_id=match_request.journal_entry_id
        )
        return result

    except BankImportError as e:
        raise HTTPException(status_code=400, detail=e.message)


@router.get("/transactions/{transaction_id}/suggest-matches")
@require_module("finance")
async def suggest_journal_matches(
    transaction_id: UUID,
    db: DB,
    tolerance_days: int = Query(3, ge=0, le=30),
    tolerance_amount: float = Query(1.0, ge=0),
    current_user: User = Depends(get_current_user),
):
    """
    Get suggested journal entry matches for a bank transaction.

    Uses fuzzy matching on date and amount to find potential matches.
    """
    import_service = BankImportService(db)

    suggestions = await import_service.suggest_matches(
        bank_transaction_id=transaction_id,
        tolerance_days=tolerance_days,
        tolerance_amount=Decimal(str(tolerance_amount))
    )

    return {"suggestions": suggestions}


@router.post("/transactions/{transaction_id}/unreconcile")
@require_module("finance")
async def unreconcile_transaction(
    transaction_id: UUID,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Mark a transaction as unreconciled."""
    result = await db.execute(
        select(BankTransaction).where(BankTransaction.id == transaction_id)
    )
    transaction = result.scalar_one_or_none()

    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")

    transaction.is_reconciled = False
    transaction.reconciled_at = None
    transaction.matched_journal_entry_id = None

    await db.commit()

    return {"success": True, "message": "Transaction marked as unreconciled"}


# ==================== Cash Book ====================

@router.get("/accounts/{account_id}/cash-book", response_model=CashBookResponse)
@require_module("finance")
async def get_cash_book(
    account_id: UUID,
    db: DB,
    start_date: date = Query(..., description="Start date for cash book"),
    end_date: date = Query(..., description="End date for cash book"),
    include_daily_summary: bool = Query(False, description="Include daily summary breakdown"),
    current_user: User = Depends(get_current_user),
):
    """
    Get Cash Book report for a bank account.

    Shows all receipts and payments in a day-book format with:
    - Opening balance
    - All transactions (receipts and payments)
    - Running balance
    - Closing balance
    - Optional daily summary breakdown
    """
    # Get bank account
    account_result = await db.execute(
        select(BankAccount).where(BankAccount.id == account_id)
    )
    account = account_result.scalar_one_or_none()

    if not account:
        raise HTTPException(status_code=404, detail="Bank account not found")

    # Calculate opening balance (balance before start_date)
    # Get the last transaction before start_date for opening balance
    opening_query = select(BankTransaction.running_balance).where(
        and_(
            BankTransaction.bank_account_id == account_id,
            BankTransaction.transaction_date < start_date
        )
    ).order_by(BankTransaction.transaction_date.desc()).limit(1)

    opening_result = await db.execute(opening_query)
    opening_balance = opening_result.scalar()

    if opening_balance is None:
        # No transactions before start_date, use account opening balance
        opening_balance = account.opening_balance or Decimal("0")

    # Get transactions in the period
    txn_query = select(BankTransaction).where(
        and_(
            BankTransaction.bank_account_id == account_id,
            BankTransaction.transaction_date >= start_date,
            BankTransaction.transaction_date <= end_date
        )
    ).order_by(BankTransaction.transaction_date, BankTransaction.created_at)

    txn_result = await db.execute(txn_query)
    transactions = txn_result.scalars().all()

    # Build cash book entries
    entries: List[CashBookEntry] = []
    running_balance = opening_balance
    total_receipts = Decimal("0")
    total_payments = Decimal("0")
    daily_data: Dict[date, Dict[str, Any]] = defaultdict(
        lambda: {
            "opening": Decimal("0"),
            "receipts": Decimal("0"),
            "payments": Decimal("0"),
            "closing": Decimal("0"),
            "count": 0
        }
    )

    current_date = None
    for txn in transactions:
        receipt = txn.credit_amount or Decimal("0")
        payment = txn.debit_amount or Decimal("0")
        running_balance = running_balance + receipt - payment

        total_receipts += receipt
        total_payments += payment

        entries.append(CashBookEntry(
            id=txn.id,
            date=txn.transaction_date,
            description=txn.description or "",
            reference=txn.reference_number,
            receipt=receipt,
            payment=payment,
            balance=running_balance,
            transaction_type=txn.transaction_type if txn.transaction_type else None,
            is_reconciled=txn.is_reconciled,
        ))

        # Track daily data
        if include_daily_summary:
            day = txn.transaction_date
            if current_date != day:
                if current_date is not None:
                    daily_data[current_date]["closing"] = running_balance - receipt + payment
                daily_data[day]["opening"] = running_balance - receipt + payment
                current_date = day

            daily_data[day]["receipts"] += receipt
            daily_data[day]["payments"] += payment
            daily_data[day]["count"] += 1
            daily_data[day]["closing"] = running_balance

    # Build daily summary
    daily_summary = None
    if include_daily_summary and daily_data:
        daily_summary = [
            CashBookDailySummary(
                date=d,
                opening_balance=data["opening"],
                total_receipts=data["receipts"],
                total_payments=data["payments"],
                closing_balance=data["closing"],
                transaction_count=data["count"],
            )
            for d, data in sorted(daily_data.items())
        ]

    closing_balance = opening_balance + total_receipts - total_payments

    return CashBookResponse(
        account_id=account.id,
        account_name=account.account_name,
        bank_name=account.bank_name,
        period_start=start_date,
        period_end=end_date,
        opening_balance=opening_balance,
        total_receipts=total_receipts,
        total_payments=total_payments,
        closing_balance=closing_balance,
        entries=entries,
        daily_summary=daily_summary,
    )


@router.get("/cash-book/all-accounts")
@require_module("finance")
async def get_consolidated_cash_book(
    db: DB,
    start_date: date = Query(..., description="Start date"),
    end_date: date = Query(..., description="End date"),
    current_user: User = Depends(get_current_user),
):
    """
    Get consolidated Cash Book across all active bank accounts.

    Returns summary by account with totals.
    """
    # Get all active bank accounts
    accounts_result = await db.execute(
        select(BankAccount).where(BankAccount.is_active == True)
    )
    accounts = accounts_result.scalars().all()

    account_summaries = []
    grand_total_receipts = Decimal("0")
    grand_total_payments = Decimal("0")
    grand_opening = Decimal("0")
    grand_closing = Decimal("0")

    for account in accounts:
        # Get opening balance
        opening_query = select(BankTransaction.running_balance).where(
            and_(
                BankTransaction.bank_account_id == account.id,
                BankTransaction.transaction_date < start_date
            )
        ).order_by(BankTransaction.transaction_date.desc()).limit(1)

        opening_result = await db.execute(opening_query)
        opening_balance = opening_result.scalar() or account.opening_balance or Decimal("0")

        # Get period totals
        totals_query = select(
            func.coalesce(func.sum(BankTransaction.credit_amount), 0).label("receipts"),
            func.coalesce(func.sum(BankTransaction.debit_amount), 0).label("payments"),
            func.count(BankTransaction.id).label("count"),
        ).where(
            and_(
                BankTransaction.bank_account_id == account.id,
                BankTransaction.transaction_date >= start_date,
                BankTransaction.transaction_date <= end_date
            )
        )

        totals_result = await db.execute(totals_query)
        totals = totals_result.one()

        closing_balance = opening_balance + totals.receipts - totals.payments

        account_summaries.append({
            "account_id": str(account.id),
            "account_name": account.account_name,
            "bank_name": account.bank_name,
            "account_type": account.account_type,
            "opening_balance": float(opening_balance),
            "total_receipts": float(totals.receipts),
            "total_payments": float(totals.payments),
            "closing_balance": float(closing_balance),
            "transaction_count": totals.count,
        })

        grand_opening += opening_balance
        grand_total_receipts += totals.receipts
        grand_total_payments += totals.payments
        grand_closing += closing_balance

    return {
        "period_start": str(start_date),
        "period_end": str(end_date),
        "accounts": account_summaries,
        "totals": {
            "opening_balance": float(grand_opening),
            "total_receipts": float(grand_total_receipts),
            "total_payments": float(grand_total_payments),
            "closing_balance": float(grand_closing),
        }
    }


@router.get("/cash-book/petty-cash", response_model=PettyCashResponse)
@require_module("finance")
async def get_petty_cash_book(
    db: DB,
    start_date: date = Query(..., description="Start date"),
    end_date: date = Query(..., description="End date"),
    current_user: User = Depends(get_current_user),
):
    """
    Get Petty Cash book.

    Shows small cash transactions categorized by expense type.
    Uses transactions from accounts marked as petty cash (account_type = 'PETTY_CASH').
    """
    # Find petty cash accounts
    petty_query = select(BankAccount).where(
        and_(
            BankAccount.is_active == True,
            or_(
                BankAccount.account_type == "PETTY_CASH",
                BankAccount.account_name.ilike("%petty%")
            )
        )
    )
    petty_result = await db.execute(petty_query)
    petty_accounts = petty_result.scalars().all()

    if not petty_accounts:
        # Return empty response if no petty cash account
        return PettyCashResponse(
            period_start=start_date,
            period_end=end_date,
            opening_balance=Decimal("0"),
            total_receipts=Decimal("0"),
            total_payments=Decimal("0"),
            closing_balance=Decimal("0"),
            entries=[],
            category_summary={},
        )

    petty_account_ids = [a.id for a in petty_accounts]

    # Get opening balance
    opening_balance = Decimal("0")
    for account in petty_accounts:
        opening_query = select(BankTransaction.running_balance).where(
            and_(
                BankTransaction.bank_account_id == account.id,
                BankTransaction.transaction_date < start_date
            )
        ).order_by(BankTransaction.transaction_date.desc()).limit(1)

        opening_result = await db.execute(opening_query)
        ob = opening_result.scalar()
        opening_balance += ob if ob else (account.opening_balance or Decimal("0"))

    # Get transactions
    txn_query = select(BankTransaction).where(
        and_(
            BankTransaction.bank_account_id.in_(petty_account_ids),
            BankTransaction.transaction_date >= start_date,
            BankTransaction.transaction_date <= end_date
        )
    ).order_by(BankTransaction.transaction_date)

    txn_result = await db.execute(txn_query)
    transactions = txn_result.scalars().all()

    entries: List[PettyCashEntry] = []
    category_summary: Dict[str, Decimal] = defaultdict(Decimal)
    running_balance = opening_balance
    total_receipts = Decimal("0")
    total_payments = Decimal("0")

    for txn in transactions:
        is_receipt = (txn.credit_amount or Decimal("0")) > 0
        amount = txn.credit_amount if is_receipt else txn.debit_amount
        amount = amount or Decimal("0")

        if is_receipt:
            running_balance += amount
            total_receipts += amount
        else:
            running_balance -= amount
            total_payments += amount

        # Extract category from description (simple heuristic)
        description = txn.description or ""
        category = "MISCELLANEOUS"
        categories = {
            "TRAVEL": ["travel", "taxi", "uber", "ola", "petrol", "fuel", "diesel"],
            "OFFICE": ["stationery", "office", "supplies", "printer", "paper"],
            "REFRESHMENT": ["tea", "coffee", "snacks", "refreshment", "meal", "food"],
            "COURIER": ["courier", "post", "delivery", "shipping"],
            "MAINTENANCE": ["repair", "maintenance", "cleaning", "plumber", "electrician"],
            "COMMUNICATION": ["mobile", "phone", "internet", "recharge"],
        }
        desc_lower = description.lower()
        for cat, keywords in categories.items():
            if any(kw in desc_lower for kw in keywords):
                category = cat
                break

        if not is_receipt:
            category_summary[category] += amount

        entries.append(PettyCashEntry(
            id=txn.id,
            date=txn.transaction_date,
            description=description,
            voucher_number=txn.reference_number or f"PV-{txn.id.hex[:8]}",
            category=category,
            amount=amount,
            is_receipt=is_receipt,
            balance=running_balance,
            approved_by=None,
        ))

    return PettyCashResponse(
        period_start=start_date,
        period_end=end_date,
        opening_balance=opening_balance,
        total_receipts=total_receipts,
        total_payments=total_payments,
        closing_balance=running_balance,
        entries=entries,
        category_summary=dict(category_summary),
    )


# ==================== ML-Based Auto-Reconciliation ====================

class ReconciliationSuggestion(BaseModel):
    """ML reconciliation suggestion."""
    bank_transaction_id: str
    bank_transaction_date: str
    bank_description: str
    bank_amount: float
    journal_entry_id: str
    journal_entry_number: str
    journal_entry_date: str
    journal_narration: Optional[str] = None
    confidence_score: float
    is_auto_match: bool
    features: Dict[str, float]


class AutoReconcileResponse(BaseModel):
    """Auto reconciliation result."""
    auto_matched_count: int
    skipped_count: int
    auto_matched: List[Dict[str, Any]]
    requires_review: List[Dict[str, Any]]
    low_confidence: List[Dict[str, Any]]


class ReconciliationStatsResponse(BaseModel):
    """Reconciliation statistics."""
    total_transactions: int
    reconciled_count: int
    unreconciled_count: int
    auto_matched_count: int
    manual_matched_count: int
    reconciliation_rate: float
    auto_match_rate: float


@router.get(
    "/accounts/{account_id}/reconciliation-suggestions",
    response_model=List[ReconciliationSuggestion],
    summary="Get ML-powered reconciliation suggestions",
    description="""
    Get AI-powered suggestions for matching bank transactions with journal entries.

    Uses machine learning features:
    - TF-IDF text similarity for description matching
    - Date proximity analysis
    - Party name extraction and matching
    - Reference number detection

    Suggestions are ranked by confidence score (0-1).
    """,
)
async def get_reconciliation_suggestions(
    account_id: UUID,
    limit: int = Query(50, ge=1, le=200),
    db: DB = None,
    current_user: User = Depends(get_current_user),
):
    """Get ML-powered reconciliation suggestions."""
    from app.services.bank_reconciliation_ml import BankReconciliationMLService

    # Verify account exists
    account_result = await db.execute(
        select(BankAccount).where(BankAccount.id == account_id)
    )
    account = account_result.scalar_one_or_none()

    if not account:
        raise HTTPException(status_code=404, detail="Bank account not found")

    ml_service = BankReconciliationMLService(db)
    suggestions = await ml_service.get_reconciliation_suggestions(account_id, limit)

    return [ReconciliationSuggestion(**s) for s in suggestions]


@router.post(
    "/accounts/{account_id}/auto-reconcile",
    response_model=AutoReconcileResponse,
    summary="Run auto-reconciliation",
    description="""
    Automatically reconcile transactions above the confidence threshold.

    **Thresholds:**
    - Auto-match: >= 0.85 confidence
    - Requires review: 0.60 - 0.85 confidence
    - Low confidence: < 0.60 confidence

    Only transactions with confidence >= threshold are auto-matched.
    """,
)
@require_module("finance")
async def auto_reconcile(
    account_id: UUID,
    threshold: float = Query(0.85, ge=0.5, le=1.0, description="Confidence threshold for auto-matching"),
    db: DB = None,
    current_user: User = Depends(get_current_user),
):
    """Run ML-based auto-reconciliation."""
    from app.services.bank_reconciliation_ml import BankReconciliationMLService

    # Verify account exists
    account_result = await db.execute(
        select(BankAccount).where(BankAccount.id == account_id)
    )
    account = account_result.scalar_one_or_none()

    if not account:
        raise HTTPException(status_code=404, detail="Bank account not found")

    ml_service = BankReconciliationMLService(db)
    result = await ml_service.auto_reconcile(account_id, threshold)

    return AutoReconcileResponse(**result)


@router.get(
    "/accounts/{account_id}/reconciliation-stats",
    response_model=ReconciliationStatsResponse,
    summary="Get reconciliation statistics",
    description="Get reconciliation statistics for a bank account.",
)
@require_module("finance")
async def get_reconciliation_stats(
    account_id: UUID,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: DB = None,
    current_user: User = Depends(get_current_user),
):
    """Get reconciliation statistics."""
    from app.services.bank_reconciliation_ml import BankReconciliationMLService

    # Verify account exists
    account_result = await db.execute(
        select(BankAccount).where(BankAccount.id == account_id)
    )
    account = account_result.scalar_one_or_none()

    if not account:
        raise HTTPException(status_code=404, detail="Bank account not found")

    ml_service = BankReconciliationMLService(db)
    stats = await ml_service.get_reconciliation_stats(account_id, start_date, end_date)

    return ReconciliationStatsResponse(**stats)


@router.post(
    "/accounts/{account_id}/train-reconciliation-model",
    summary="Train reconciliation model on historical matches",
    description="""
    Analyze historical successful matches to optimize matching weights.

    Requires at least 10 historical matches for training.
    Returns optimized weights based on past reconciliation patterns.
    """,
)
@require_module("finance")
async def train_reconciliation_model(
    account_id: UUID,
    limit: int = Query(1000, ge=100, le=5000),
    db: DB = None,
    current_user: User = Depends(get_current_user),
):
    """Train ML model on historical matches."""
    from app.services.bank_reconciliation_ml import BankReconciliationMLService

    # Verify account exists
    account_result = await db.execute(
        select(BankAccount).where(BankAccount.id == account_id)
    )
    account = account_result.scalar_one_or_none()

    if not account:
        raise HTTPException(status_code=404, detail="Bank account not found")

    ml_service = BankReconciliationMLService(db)
    result = await ml_service.train_on_historical_matches(account_id, limit)

    return result