"""Vendor Invoice API endpoints for 3-way matching."""
from typing import Optional, List
from uuid import UUID
from datetime import datetime, date, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, Query, HTTPException, status, Body
from sqlalchemy import select, func, desc, and_, or_
from sqlalchemy.orm import selectinload
from pydantic import BaseModel

from app.api.deps import DB, get_current_user
from app.models.user import User
from app.models.purchase import (
    VendorInvoice, VendorInvoiceStatus,
    PurchaseOrder, GoodsReceiptNote
)
from app.models.vendor import Vendor
from uuid import uuid4
from datetime import date as date_type
from app.services.auto_journal_service import AutoJournalService, AutoJournalError
from app.core.module_decorators import require_module

router = APIRouter()


# ==================== Schemas ====================

class VendorInvoiceCreate(BaseModel):
    vendor_id: UUID
    invoice_number: str
    invoice_date: date
    purchase_order_id: Optional[UUID] = None
    grn_id: Optional[UUID] = None
    subtotal: Decimal
    discount_amount: Decimal = Decimal("0")
    taxable_amount: Decimal
    cgst_amount: Decimal = Decimal("0")
    sgst_amount: Decimal = Decimal("0")
    igst_amount: Decimal = Decimal("0")
    cess_amount: Decimal = Decimal("0")
    freight_charges: Decimal = Decimal("0")
    other_charges: Decimal = Decimal("0")
    round_off: Decimal = Decimal("0")
    grand_total: Decimal
    due_date: date
    tds_applicable: bool = True
    tds_section: Optional[str] = None
    tds_rate: Decimal = Decimal("0")
    vendor_irn: Optional[str] = None
    invoice_pdf_url: Optional[str] = None
    internal_notes: Optional[str] = None


class ThreeWayMatchRequest(BaseModel):
    invoice_id: UUID
    po_id: UUID
    grn_id: UUID
    tolerance_percentage: Decimal = Decimal("1")  # Allow 1% variance


# ==================== Endpoints ====================

@router.get("/next-reference")
@require_module("procurement")
async def get_next_reference(
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Get the next vendor invoice reference number."""
    today = date_type.today()
    random_suffix = str(uuid4())[:8].upper()
    next_ref = f"VI-{today.strftime('%Y%m%d')}-{random_suffix}"
    return {"reference": next_ref}


@router.get("")
@require_module("procurement")
async def list_vendor_invoices(
    db: DB,
    current_user: User = Depends(get_current_user),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    vendor_id: Optional[UUID] = None,
    is_matched: Optional[bool] = None,
    is_overdue: Optional[bool] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    search: Optional[str] = None,
):
    """List vendor invoices with filtering."""
    query = select(VendorInvoice).options(
        selectinload(VendorInvoice.vendor),
        selectinload(VendorInvoice.purchase_order),
        selectinload(VendorInvoice.grn),
    )

    conditions = []

    if status:
        conditions.append(VendorInvoice.status == status.upper())

    if vendor_id:
        conditions.append(VendorInvoice.vendor_id == vendor_id)

    if is_matched is not None:
        conditions.append(VendorInvoice.is_fully_matched == is_matched)

    if is_overdue:
        conditions.append(
            and_(
                VendorInvoice.due_date < date.today(),
                VendorInvoice.balance_due > 0
            )
        )

    if start_date:
        conditions.append(VendorInvoice.invoice_date >= start_date)

    if end_date:
        conditions.append(VendorInvoice.invoice_date <= end_date)

    if search:
        conditions.append(
            or_(
                VendorInvoice.our_reference.ilike(f"%{search}%"),
                VendorInvoice.invoice_number.ilike(f"%{search}%"),
            )
        )

    if conditions:
        query = query.where(and_(*conditions))

    # Count
    count_query = select(func.count()).select_from(VendorInvoice)
    if conditions:
        count_query = count_query.where(and_(*conditions))
    total = await db.scalar(count_query) or 0

    # Paginate
    query = query.order_by(desc(VendorInvoice.created_at))
    query = query.offset((page - 1) * size).limit(size)

    result = await db.execute(query)
    invoices = result.scalars().all()

    return {
        "items": [
            {
                "id": str(inv.id),
                "our_reference": inv.our_reference,
                "invoice_number": inv.invoice_number,
                "invoice_date": inv.invoice_date.isoformat() if inv.invoice_date else None,
                "status": inv.status,
                "vendor_id": str(inv.vendor_id),
                "vendor_name": inv.vendor.name if inv.vendor else None,
                "po_number": inv.purchase_order.po_number if inv.purchase_order else None,
                "grn_number": inv.grn.grn_number if inv.grn else None,
                "grand_total": float(inv.grand_total),
                "amount_paid": float(inv.amount_paid),
                "balance_due": float(inv.balance_due),
                "due_date": inv.due_date.isoformat() if inv.due_date else None,
                "is_overdue": inv.is_overdue,
                "days_overdue": inv.days_overdue,
                "is_fully_matched": inv.is_fully_matched,
                "po_matched": inv.po_matched,
                "grn_matched": inv.grn_matched,
                "created_at": inv.created_at.isoformat() if inv.created_at else None,
            }
            for inv in invoices
        ],
        "total": total,
        "page": page,
        "size": size,
        "pages": (total + size - 1) // size,
    }


@router.get("/stats")
@require_module("procurement")
async def get_invoice_stats(
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Get vendor invoice statistics."""
    today = date.today()

    # Total invoices count
    total_query = select(func.count()).select_from(VendorInvoice)
    total_invoices = await db.scalar(total_query) or 0

    # Pending review (RECEIVED + UNDER_VERIFICATION)
    pending_review_query = select(func.count()).select_from(VendorInvoice).where(
        VendorInvoice.status.in_(["RECEIVED", "UNDER_VERIFICATION"])
    )
    pending_review = await db.scalar(pending_review_query) or 0

    # Matched count
    matched_query = select(func.count()).select_from(VendorInvoice).where(
        VendorInvoice.status == "MATCHED"
    )
    matched = await db.scalar(matched_query) or 0

    # Mismatch count
    mismatch_query = select(func.count()).select_from(VendorInvoice).where(
        VendorInvoice.status == "MISMATCH"
    )
    mismatch = await db.scalar(mismatch_query) or 0

    # Overdue count (due_date < today and balance_due > 0)
    overdue_count_query = select(func.count()).select_from(VendorInvoice).where(
        and_(
            VendorInvoice.due_date < today,
            VendorInvoice.balance_due > 0
        )
    )
    overdue = await db.scalar(overdue_count_query) or 0

    # Total pending amount
    pending_query = select(func.sum(VendorInvoice.balance_due)).where(
        VendorInvoice.balance_due > 0
    )
    pending_amount = await db.scalar(pending_query) or Decimal("0")

    # Total overdue amount
    overdue_query = select(func.sum(VendorInvoice.balance_due)).where(
        and_(
            VendorInvoice.due_date < today,
            VendorInvoice.balance_due > 0
        )
    )
    overdue_amount = await db.scalar(overdue_query) or Decimal("0")

    return {
        "total_invoices": total_invoices,
        "pending_review": pending_review,
        "matched": matched,
        "mismatch": mismatch,
        "overdue": overdue,
        "total_pending_amount": float(pending_amount),
        "total_overdue_amount": float(overdue_amount),
    }


@router.get("/{invoice_id}")
@require_module("procurement")
async def get_vendor_invoice(
    invoice_id: UUID,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Get vendor invoice details."""
    query = select(VendorInvoice).options(
        selectinload(VendorInvoice.vendor),
        selectinload(VendorInvoice.purchase_order),
        selectinload(VendorInvoice.grn),
        selectinload(VendorInvoice.received_by_user),
        selectinload(VendorInvoice.verified_by_user),
        selectinload(VendorInvoice.approved_by_user),
    ).where(VendorInvoice.id == invoice_id)

    result = await db.execute(query)
    inv = result.scalar_one_or_none()

    if not inv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vendor invoice not found"
        )

    return {
        "id": str(inv.id),
        "our_reference": inv.our_reference,
        "invoice_number": inv.invoice_number,
        "invoice_date": inv.invoice_date.isoformat() if inv.invoice_date else None,
        "status": inv.status,
        "vendor": {
            "id": str(inv.vendor_id),
            "name": inv.vendor.name if inv.vendor else None,
        },
        "purchase_order": {
            "id": str(inv.purchase_order_id) if inv.purchase_order_id else None,
            "po_number": inv.purchase_order.po_number if inv.purchase_order else None,
        } if inv.purchase_order_id else None,
        "grn": {
            "id": str(inv.grn_id) if inv.grn_id else None,
            "grn_number": inv.grn.grn_number if inv.grn else None,
        } if inv.grn_id else None,
        "subtotal": float(inv.subtotal),
        "discount_amount": float(inv.discount_amount),
        "taxable_amount": float(inv.taxable_amount),
        "cgst_amount": float(inv.cgst_amount),
        "sgst_amount": float(inv.sgst_amount),
        "igst_amount": float(inv.igst_amount),
        "cess_amount": float(inv.cess_amount),
        "total_tax": float(inv.total_tax),
        "freight_charges": float(inv.freight_charges),
        "other_charges": float(inv.other_charges),
        "round_off": float(inv.round_off),
        "grand_total": float(inv.grand_total),
        "due_date": inv.due_date.isoformat() if inv.due_date else None,
        "amount_paid": float(inv.amount_paid),
        "balance_due": float(inv.balance_due),
        "is_overdue": inv.is_overdue,
        "days_overdue": inv.days_overdue,
        "tds_applicable": inv.tds_applicable,
        "tds_section": inv.tds_section,
        "tds_rate": float(inv.tds_rate),
        "tds_amount": float(inv.tds_amount),
        "net_payable": float(inv.net_payable),
        "po_matched": inv.po_matched,
        "grn_matched": inv.grn_matched,
        "is_fully_matched": inv.is_fully_matched,
        "matching_variance": float(inv.matching_variance),
        "variance_reason": inv.variance_reason,
        "vendor_irn": inv.vendor_irn,
        "vendor_ack_number": inv.vendor_ack_number,
        "invoice_pdf_url": inv.invoice_pdf_url,
        "internal_notes": inv.internal_notes,
        "received_by": inv.received_by_user.email if inv.received_by_user else None,
        "received_at": inv.received_at.isoformat() if inv.received_at else None,
        "verified_by": inv.verified_by_user.email if inv.verified_by_user else None,
        "verified_at": inv.verified_at.isoformat() if inv.verified_at else None,
        "approved_by": inv.approved_by_user.email if inv.approved_by_user else None,
        "approved_at": inv.approved_at.isoformat() if inv.approved_at else None,
        "created_at": inv.created_at.isoformat() if inv.created_at else None,
    }


@router.post("", status_code=status.HTTP_201_CREATED)
@require_module("procurement")
async def create_vendor_invoice(
    data: VendorInvoiceCreate,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Create a new vendor invoice."""
    # Validate vendor
    vendor = await db.get(Vendor, data.vendor_id)
    if not vendor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vendor not found"
        )

    # Check for duplicate
    existing_query = select(VendorInvoice).where(
        and_(
            VendorInvoice.vendor_id == data.vendor_id,
            VendorInvoice.invoice_number == data.invoice_number
        )
    )
    existing = await db.execute(existing_query)
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invoice with this number already exists for this vendor"
        )

    # Get next reference
    today = date_type.today()
    random_suffix = str(uuid4())[:8].upper()
    our_reference = f"VI-{today.strftime('%Y%m%d')}-{random_suffix}"

    # Calculate TDS and net payable
    tds_amount = (data.grand_total * data.tds_rate / 100) if data.tds_applicable else Decimal("0")
    net_payable = data.grand_total - tds_amount
    total_tax = data.cgst_amount + data.sgst_amount + data.igst_amount + data.cess_amount

    invoice = VendorInvoice(
        our_reference=our_reference,
        invoice_number=data.invoice_number,
        invoice_date=data.invoice_date,
        status="RECEIVED",
        vendor_id=data.vendor_id,
        purchase_order_id=data.purchase_order_id,
        grn_id=data.grn_id,
        subtotal=data.subtotal,
        discount_amount=data.discount_amount,
        taxable_amount=data.taxable_amount,
        cgst_amount=data.cgst_amount,
        sgst_amount=data.sgst_amount,
        igst_amount=data.igst_amount,
        cess_amount=data.cess_amount,
        total_tax=total_tax,
        freight_charges=data.freight_charges,
        other_charges=data.other_charges,
        round_off=data.round_off,
        grand_total=data.grand_total,
        due_date=data.due_date,
        balance_due=net_payable,  # Initially balance = net payable
        tds_applicable=data.tds_applicable,
        tds_section=data.tds_section,
        tds_rate=data.tds_rate,
        tds_amount=tds_amount,
        net_payable=net_payable,
        vendor_irn=data.vendor_irn,
        invoice_pdf_url=data.invoice_pdf_url,
        internal_notes=data.internal_notes,
        received_by=current_user.id,
    )
    db.add(invoice)
    await db.commit()
    await db.refresh(invoice)

    return {
        "id": str(invoice.id),
        "our_reference": invoice.our_reference,
        "message": "Vendor invoice created successfully",
    }


@router.post("/three-way-match")
@require_module("procurement")
async def perform_three_way_match(
    data: ThreeWayMatchRequest,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """
    Perform 3-way matching between PO, GRN, and Vendor Invoice.

    Checks:
    1. PO amount vs Invoice amount
    2. GRN received quantity/value vs Invoice amount
    3. Variance within tolerance
    """
    # Get all documents
    invoice = await db.get(VendorInvoice, data.invoice_id)
    po = await db.get(PurchaseOrder, data.po_id)
    grn = await db.get(GoodsReceiptNote, data.grn_id)

    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if not po:
        raise HTTPException(status_code=404, detail="Purchase Order not found")
    if not grn:
        raise HTTPException(status_code=404, detail="GRN not found")

    # Verify relationships
    if grn.purchase_order_id != po.id:
        raise HTTPException(
            status_code=400,
            detail="GRN is not linked to the specified PO"
        )

    # Calculate matching
    po_amount = po.grand_total
    grn_value = grn.total_value
    invoice_amount = invoice.grand_total

    # Check PO match
    po_variance = abs(invoice_amount - po_amount)
    po_variance_pct = (po_variance / po_amount * 100) if po_amount > 0 else Decimal("0")
    po_matched = po_variance_pct <= data.tolerance_percentage

    # Check GRN match
    grn_variance = abs(invoice_amount - grn_value)
    grn_variance_pct = (grn_variance / grn_value * 100) if grn_value > 0 else Decimal("0")
    grn_matched = grn_variance_pct <= data.tolerance_percentage

    # Overall match
    is_fully_matched = po_matched and grn_matched
    total_variance = max(po_variance, grn_variance)

    # Update invoice
    invoice.purchase_order_id = po.id
    invoice.grn_id = grn.id
    invoice.po_matched = po_matched
    invoice.grn_matched = grn_matched
    invoice.is_fully_matched = is_fully_matched
    invoice.matching_variance = total_variance

    if is_fully_matched:
        invoice.status = "MATCHED"
    elif po_matched or grn_matched:
        invoice.status = "PARTIALLY_MATCHED"
        invoice.variance_reason = f"PO variance: {po_variance_pct:.2f}%, GRN variance: {grn_variance_pct:.2f}%"
    else:
        invoice.status = "MISMATCH"
        invoice.variance_reason = f"PO variance: {po_variance_pct:.2f}%, GRN variance: {grn_variance_pct:.2f}%"

    invoice.verified_by = current_user.id
    invoice.verified_at = datetime.now(timezone.utc)

    await db.commit()

    return {
        "invoice_id": str(invoice.id),
        "po_id": str(po.id),
        "grn_id": str(grn.id),
        "matching_result": {
            "po_matched": po_matched,
            "po_amount": float(po_amount),
            "po_variance": float(po_variance),
            "po_variance_pct": float(po_variance_pct),
            "grn_matched": grn_matched,
            "grn_value": float(grn_value),
            "grn_variance": float(grn_variance),
            "grn_variance_pct": float(grn_variance_pct),
            "invoice_amount": float(invoice_amount),
            "is_fully_matched": is_fully_matched,
            "status": invoice.status,
        },
    }


@router.post("/{invoice_id}/approve")
@require_module("procurement")
async def approve_invoice(
    invoice_id: UUID,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Approve a matched invoice for payment."""
    invoice = await db.get(VendorInvoice, invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    if invoice.status not in ["MATCHED", "PARTIALLY_MATCHED"]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot approve invoice with status {invoice.status}"
        )

    invoice.status = "APPROVED"
    invoice.approved_by = current_user.id
    invoice.approved_at = datetime.now(timezone.utc)

    # Auto-generate journal entry for purchase invoice approval
    journal_entry = None
    try:
        auto_journal_service = AutoJournalService(db)
        journal_entry = await auto_journal_service.generate_for_purchase_bill(
            purchase_invoice_id=invoice_id,
            user_id=current_user.id,
            auto_post=False  # Purchase invoices need separate approval
        )
    except AutoJournalError as e:
        # Log the error but don't fail the approval
        import logging

        logging.warning(f"Failed to auto-generate journal for vendor invoice {invoice.invoice_number}: {e.message}")

    await db.commit()

    return {
        "message": "Invoice approved",
        "status": invoice.status,
        "journal_entry_id": str(journal_entry.id) if journal_entry else None
    }


@router.post("/{invoice_id}/record-payment")
@require_module("procurement")
async def record_payment(
    invoice_id: UUID,
    amount: Decimal = Body(..., embed=True),
    payment_reference: Optional[str] = Body(None, embed=True),
    db: DB = None,
    current_user: User = Depends(get_current_user),
):
    """Record a payment against the invoice."""
    invoice = await db.get(VendorInvoice, invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    if invoice.status not in ["APPROVED", "PAYMENT_INITIATED"]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot record payment for invoice with status {invoice.status}"
        )

    invoice.amount_paid += amount
    invoice.balance_due = invoice.net_payable - invoice.amount_paid

    if invoice.balance_due <= 0:
        invoice.status = "PAID"
        invoice.balance_due = Decimal("0")
    else:
        invoice.status = "PAYMENT_INITIATED"

    await db.commit()

    return {
        "message": "Payment recorded",
        "amount_paid": float(invoice.amount_paid),
        "balance_due": float(invoice.balance_due),
        "status": invoice.status,
    }
