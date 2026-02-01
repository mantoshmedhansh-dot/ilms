"""API endpoints for Auto Journal Entry Generation."""
from typing import Optional, List
from uuid import UUID
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.user import User
from app.models.accounting import JournalEntry, JournalEntryStatus
from app.api.deps import DB, get_current_user
from app.schemas.auto_journal import (
    GenerateFromInvoiceRequest,
    GenerateFromReceiptRequest,
    GenerateFromBankTxnRequest,
    BulkGenerateRequest,
    JournalEntryResponse,
    GenerationResult,
)
from app.services.auto_journal_service import AutoJournalService, AutoJournalError
from app.core.module_decorators import require_module

router = APIRouter()


# ==================== Auto Generate Endpoints ====================

@router.post("/generate/from-invoice", response_model=GenerationResult)
@require_module("finance")
async def generate_from_sales_invoice(
    request: GenerateFromInvoiceRequest,
    db: DB,
    company_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_user),
):
    """
    Generate journal entry from a sales invoice.

    Creates:
    - Debit: Accounts Receivable (total amount)
    - Credit: Sales Revenue (taxable amount)
    - Credit: CGST/SGST/IGST Payable (tax amounts)

    The journal entry is created in DRAFT status unless auto_post is True.
    """
    effective_company_id = company_id or current_user.company_id

    if not effective_company_id:
        raise HTTPException(status_code=400, detail="Company ID is required")

    try:
        service = AutoJournalService(db, effective_company_id)
        journal = await service.generate_for_sales_invoice(
            invoice_id=request.invoice_id,
            user_id=current_user.id
        )

        if request.auto_post:
            journal = await service.post_journal_entry(journal.id)

        return GenerationResult(
            success=True,
            journal_id=journal.id,
            entry_number=journal.entry_number,
            message=f"Journal entry {journal.entry_number} created successfully"
        )

    except AutoJournalError as e:
        return GenerationResult(
            success=False,
            message="Journal generation failed",
            error=e.message
        )


@router.post("/generate/from-receipt", response_model=GenerationResult)
@require_module("finance")
async def generate_from_payment_receipt(
    request: GenerateFromReceiptRequest,
    db: DB,
    company_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_user),
):
    """
    Generate journal entry from a payment receipt.

    Creates:
    - Debit: Cash/Bank account
    - Credit: Accounts Receivable
    """
    effective_company_id = company_id or current_user.company_id

    if not effective_company_id:
        raise HTTPException(status_code=400, detail="Company ID is required")

    try:
        service = AutoJournalService(db, effective_company_id)
        journal = await service.generate_for_payment_receipt(
            receipt_id=request.receipt_id,
            bank_account_code=request.bank_account_code,
            user_id=current_user.id
        )

        if request.auto_post:
            journal = await service.post_journal_entry(journal.id)

        return GenerationResult(
            success=True,
            journal_id=journal.id,
            entry_number=journal.entry_number,
            message=f"Journal entry {journal.entry_number} created successfully"
        )

    except AutoJournalError as e:
        return GenerationResult(
            success=False,
            message="Journal generation failed",
            error=e.message
        )


@router.post("/generate/from-bank-transaction", response_model=GenerationResult)
@require_module("finance")
async def generate_from_bank_transaction(
    request: GenerateFromBankTxnRequest,
    db: DB,
    company_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_user),
):
    """
    Generate journal entry from a bank transaction.

    Requires specifying the contra account (the other side of the entry).

    For deposits: Debit Bank, Credit Contra
    For withdrawals: Debit Contra, Credit Bank
    """
    effective_company_id = company_id or current_user.company_id

    if not effective_company_id:
        raise HTTPException(status_code=400, detail="Company ID is required")

    try:
        service = AutoJournalService(db, effective_company_id)
        journal = await service.generate_for_bank_transaction(
            bank_transaction_id=request.bank_transaction_id,
            contra_account_code=request.contra_account_code,
            user_id=current_user.id
        )

        if request.auto_post:
            journal = await service.post_journal_entry(journal.id)

        return GenerationResult(
            success=True,
            journal_id=journal.id,
            entry_number=journal.entry_number,
            message=f"Journal entry {journal.entry_number} created successfully"
        )

    except AutoJournalError as e:
        return GenerationResult(
            success=False,
            message="Journal generation failed",
            error=e.message
        )


@router.post("/generate/bulk")
@require_module("finance")
async def generate_bulk_journal_entries(
    request: BulkGenerateRequest,
    db: DB,
    company_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_user),
):
    """
    Generate journal entries in bulk for multiple invoices/receipts.

    Returns summary of successful and failed generations.
    """
    effective_company_id = company_id or current_user.company_id

    if not effective_company_id:
        raise HTTPException(status_code=400, detail="Company ID is required")

    service = AutoJournalService(db, effective_company_id)
    results = {
        "invoices": {"success": 0, "failed": 0, "entries": [], "errors": []},
        "receipts": {"success": 0, "failed": 0, "entries": [], "errors": []}
    }

    # Process invoices
    if request.invoice_ids:
        for invoice_id in request.invoice_ids:
            try:
                journal = await service.generate_for_sales_invoice(
                    invoice_id=invoice_id,
                    user_id=current_user.id
                )
                if request.auto_post:
                    journal = await service.post_journal_entry(journal.id)

                results["invoices"]["success"] += 1
                results["invoices"]["entries"].append({
                    "invoice_id": str(invoice_id),
                    "journal_id": str(journal.id),
                    "entry_number": journal.entry_number
                })
            except AutoJournalError as e:
                results["invoices"]["failed"] += 1
                results["invoices"]["errors"].append({
                    "invoice_id": str(invoice_id),
                    "error": e.message
                })

    # Process receipts
    if request.receipt_ids:
        for receipt_id in request.receipt_ids:
            try:
                journal = await service.generate_for_payment_receipt(
                    receipt_id=receipt_id,
                    user_id=current_user.id
                )
                if request.auto_post:
                    journal = await service.post_journal_entry(journal.id)

                results["receipts"]["success"] += 1
                results["receipts"]["entries"].append({
                    "receipt_id": str(receipt_id),
                    "journal_id": str(journal.id),
                    "entry_number": journal.entry_number
                })
            except AutoJournalError as e:
                results["receipts"]["failed"] += 1
                results["receipts"]["errors"].append({
                    "receipt_id": str(receipt_id),
                    "error": e.message
                })

    total_success = results["invoices"]["success"] + results["receipts"]["success"]
    total_failed = results["invoices"]["failed"] + results["receipts"]["failed"]

    return {
        "success": True,
        "summary": {
            "total_processed": total_success + total_failed,
            "successful": total_success,
            "failed": total_failed
        },
        "details": results
    }


@router.post("/journals/{journal_id}/post", response_model=JournalEntryResponse)
@require_module("finance")
async def post_journal_entry(
    journal_id: UUID,
    db: DB,
    company_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_user),
):
    """Post a draft journal entry."""
    effective_company_id = company_id or current_user.company_id

    if not effective_company_id:
        raise HTTPException(status_code=400, detail="Company ID is required")

    try:
        service = AutoJournalService(db, effective_company_id)
        journal = await service.post_journal_entry(journal_id)

        return JournalEntryResponse(
            id=journal.id,
            entry_number=journal.entry_number,
            entry_date=journal.entry_date,
            journal_type=journal.entry_type if journal.entry_type else "GENERAL",
            narration=journal.narration or "",
            total_debit=float(journal.total_debit or 0),
            total_credit=float(journal.total_credit or 0),
            status=journal.status if journal.status else "DRAFT",
            reference_type=journal.source_type,
            reference_id=journal.source_id
        )

    except AutoJournalError as e:
        raise HTTPException(status_code=400, detail=e.message)


@router.get("/journals/pending")
@require_module("finance")
async def list_pending_journal_entries(
    db: DB,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    company_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_user),
):
    """List all draft/pending journal entries for review."""
    effective_company_id = company_id or current_user.company_id

    if not effective_company_id:
        raise HTTPException(status_code=400, detail="Company ID is required")

    result = await db.execute(
        select(JournalEntry)
        .options(selectinload(JournalEntry.lines))
        .where(
            and_(
                JournalEntry.company_id == effective_company_id,
                JournalEntry.status == JournalEntryStatus.DRAFT
            )
        )
        .order_by(JournalEntry.entry_date.desc())
        .offset(skip)
        .limit(limit)
    )
    journals = result.scalars().all()

    return [
        {
            "id": str(j.id),
            "entry_number": j.entry_number,
            "entry_date": str(j.entry_date),
            "journal_type": j.entry_type if j.entry_type else None,
            "narration": j.narration,
            "total_debit": float(j.total_debit or 0),
            "total_credit": float(j.total_credit or 0),
            "reference_type": j.source_type,
            "reference_id": str(j.source_id) if j.source_id else None,
            "lines_count": len(j.lines) if j.lines else 0
        }
        for j in journals
    ]


@router.post("/journals/post-all")
@require_module("finance")
async def post_all_pending_journals(
    db: DB,
    company_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_user),
):
    """Post all pending journal entries."""
    effective_company_id = company_id or current_user.company_id

    if not effective_company_id:
        raise HTTPException(status_code=400, detail="Company ID is required")

    result = await db.execute(
        select(JournalEntry)
        .options(selectinload(JournalEntry.lines))
        .where(
            and_(
                JournalEntry.company_id == effective_company_id,
                JournalEntry.status == JournalEntryStatus.DRAFT
            )
        )
    )
    journals = result.scalars().all()

    service = AutoJournalService(db, effective_company_id)
    posted = 0
    failed = 0
    errors = []

    for journal in journals:
        try:
            await service.post_journal_entry(journal.id)
            posted += 1
        except AutoJournalError as e:
            failed += 1
            errors.append({
                "journal_id": str(journal.id),
                "entry_number": journal.entry_number,
                "error": e.message
            })

    return {
        "success": True,
        "posted": posted,
        "failed": failed,
        "errors": errors if errors else None
    }
