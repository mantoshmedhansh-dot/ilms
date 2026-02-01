"""Vendor Payments API endpoints for Finance module."""
from typing import Optional, List
from uuid import UUID
from datetime import date, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy import select, func, desc, and_, or_
from sqlalchemy.orm import selectinload
from pydantic import BaseModel, ConfigDict

from app.api.deps import DB, get_current_user
from app.models.user import User
from app.models.vendor import Vendor, VendorLedger, VendorTransactionType
from app.core.module_decorators import require_module

router = APIRouter()


# ==================== Response Schemas ====================

class VendorPaymentListItem(BaseModel):
    """Schema for vendor payment list item."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    vendor_id: UUID
    vendor_code: str
    vendor_name: str
    transaction_date: date
    reference_number: str
    payment_mode: Optional[str] = None
    payment_reference: Optional[str] = None
    bank_name: Optional[str] = None
    cheque_number: Optional[str] = None
    cheque_date: Optional[date] = None
    amount: Decimal  # debit_amount
    tds_amount: Decimal
    net_amount: Decimal  # amount - tds_amount
    tds_section: Optional[str] = None
    narration: Optional[str] = None
    running_balance: Decimal
    created_at: str


class VendorPaymentListResponse(BaseModel):
    """Response for listing vendor payments."""
    items: List[VendorPaymentListItem]
    total: int
    page: int
    size: int
    pages: int


class VendorPaymentStats(BaseModel):
    """Stats for vendor payments."""
    total_payments: int
    total_amount: Decimal
    total_tds: Decimal
    payments_this_month: int
    amount_this_month: Decimal
    payments_today: int
    amount_today: Decimal
    top_vendors: List[dict]


# ==================== Endpoints ====================

@router.get("", response_model=VendorPaymentListResponse)
@require_module("procurement")
async def list_vendor_payments(
    db: DB,
    current_user: User = Depends(get_current_user),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    vendor_id: Optional[UUID] = None,
    payment_mode: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    search: Optional[str] = None,
):
    """
    List all vendor payments with filtering.

    Payments are stored in VendorLedger with transaction_type = 'PAYMENT'.
    """
    # Base query for payments
    query = select(VendorLedger).options(
        selectinload(VendorLedger.vendor)
    ).where(
        VendorLedger.transaction_type == "PAYMENT"
    )

    conditions = []

    if vendor_id:
        conditions.append(VendorLedger.vendor_id == vendor_id)

    if payment_mode:
        conditions.append(VendorLedger.payment_mode == payment_mode.upper())

    if start_date:
        conditions.append(VendorLedger.transaction_date >= start_date)

    if end_date:
        conditions.append(VendorLedger.transaction_date <= end_date)

    if search:
        search_term = f"%{search}%"
        # Need to join with Vendor for name/code search
        query = query.join(Vendor, VendorLedger.vendor_id == Vendor.id)
        conditions.append(
            or_(
                VendorLedger.reference_number.ilike(search_term),
                VendorLedger.payment_reference.ilike(search_term),
                Vendor.name.ilike(search_term),
                Vendor.vendor_code.ilike(search_term),
            )
        )

    if conditions:
        query = query.where(and_(*conditions))

    # Count total
    count_query = select(func.count()).select_from(VendorLedger).where(
        VendorLedger.transaction_type == "PAYMENT"
    )
    if conditions:
        count_query = count_query.where(and_(*conditions))

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Order by transaction date descending
    query = query.order_by(desc(VendorLedger.transaction_date), desc(VendorLedger.created_at))

    # Paginate
    offset = (page - 1) * size
    query = query.offset(offset).limit(size)

    result = await db.execute(query)
    payments = result.scalars().all()

    items = []
    for payment in payments:
        vendor = payment.vendor
        items.append(VendorPaymentListItem(
            id=payment.id,
            vendor_id=payment.vendor_id,
            vendor_code=vendor.vendor_code if vendor else "N/A",
            vendor_name=vendor.name if vendor else "Unknown Vendor",
            transaction_date=payment.transaction_date,
            reference_number=payment.reference_number,
            payment_mode=payment.payment_mode,
            payment_reference=payment.payment_reference,
            bank_name=payment.bank_name,
            cheque_number=payment.cheque_number,
            cheque_date=payment.cheque_date,
            amount=payment.debit_amount,
            tds_amount=payment.tds_amount,
            net_amount=payment.debit_amount - payment.tds_amount,
            tds_section=payment.tds_section,
            narration=payment.narration,
            running_balance=payment.running_balance,
            created_at=payment.created_at.isoformat() if payment.created_at else "",
        ))

    pages = (total + size - 1) // size if total > 0 else 1

    return VendorPaymentListResponse(
        items=items,
        total=total,
        page=page,
        size=size,
        pages=pages
    )


@router.get("/stats", response_model=VendorPaymentStats)
@require_module("procurement")
async def get_payment_stats(
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Get vendor payment statistics."""
    today = date.today()
    first_of_month = today.replace(day=1)

    # Total payments
    total_query = select(
        func.count(VendorLedger.id).label("count"),
        func.coalesce(func.sum(VendorLedger.debit_amount), 0).label("amount"),
        func.coalesce(func.sum(VendorLedger.tds_amount), 0).label("tds"),
    ).where(VendorLedger.transaction_type == "PAYMENT")

    total_result = await db.execute(total_query)
    total_data = total_result.one()

    # Payments this month
    month_query = select(
        func.count(VendorLedger.id).label("count"),
        func.coalesce(func.sum(VendorLedger.debit_amount), 0).label("amount"),
    ).where(
        and_(
            VendorLedger.transaction_type == "PAYMENT",
            VendorLedger.transaction_date >= first_of_month,
            VendorLedger.transaction_date <= today
        )
    )

    month_result = await db.execute(month_query)
    month_data = month_result.one()

    # Payments today
    today_query = select(
        func.count(VendorLedger.id).label("count"),
        func.coalesce(func.sum(VendorLedger.debit_amount), 0).label("amount"),
    ).where(
        and_(
            VendorLedger.transaction_type == "PAYMENT",
            VendorLedger.transaction_date == today
        )
    )

    today_result = await db.execute(today_query)
    today_data = today_result.one()

    # Top 5 vendors by payment amount
    top_vendors_query = select(
        Vendor.id,
        Vendor.vendor_code,
        Vendor.name,
        func.sum(VendorLedger.debit_amount).label("total_paid")
    ).join(
        VendorLedger, VendorLedger.vendor_id == Vendor.id
    ).where(
        VendorLedger.transaction_type == "PAYMENT"
    ).group_by(
        Vendor.id, Vendor.vendor_code, Vendor.name
    ).order_by(
        desc(func.sum(VendorLedger.debit_amount))
    ).limit(5)

    top_vendors_result = await db.execute(top_vendors_query)
    top_vendors = [
        {
            "id": str(row.id),
            "vendor_code": row.vendor_code,
            "name": row.name,
            "total_paid": float(row.total_paid or 0)
        }
        for row in top_vendors_result.all()
    ]

    return VendorPaymentStats(
        total_payments=total_data.count or 0,
        total_amount=Decimal(str(total_data.amount or 0)),
        total_tds=Decimal(str(total_data.tds or 0)),
        payments_this_month=month_data.count or 0,
        amount_this_month=Decimal(str(month_data.amount or 0)),
        payments_today=today_data.count or 0,
        amount_today=Decimal(str(today_data.amount or 0)),
        top_vendors=top_vendors
    )


@router.get("/{payment_id}")
@require_module("procurement")
async def get_payment_detail(
    payment_id: UUID,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Get detailed information about a specific payment."""
    query = select(VendorLedger).options(
        selectinload(VendorLedger.vendor)
    ).where(
        and_(
            VendorLedger.id == payment_id,
            VendorLedger.transaction_type == "PAYMENT"
        )
    )

    result = await db.execute(query)
    payment = result.scalar_one_or_none()

    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )

    vendor = payment.vendor

    return {
        "id": str(payment.id),
        "vendor_id": str(payment.vendor_id),
        "vendor_code": vendor.vendor_code if vendor else "N/A",
        "vendor_name": vendor.name if vendor else "Unknown Vendor",
        "vendor_gstin": vendor.gstin if vendor else None,
        "vendor_pan": vendor.pan if vendor else None,
        "transaction_date": payment.transaction_date.isoformat(),
        "reference_number": payment.reference_number,
        "payment_mode": payment.payment_mode,
        "payment_reference": payment.payment_reference,
        "bank_name": payment.bank_name,
        "cheque_number": payment.cheque_number,
        "cheque_date": payment.cheque_date.isoformat() if payment.cheque_date else None,
        "amount": float(payment.debit_amount),
        "tds_amount": float(payment.tds_amount),
        "net_amount": float(payment.debit_amount - payment.tds_amount),
        "tds_section": payment.tds_section,
        "narration": payment.narration,
        "running_balance": float(payment.running_balance),
        "created_at": payment.created_at.isoformat() if payment.created_at else None,
        "created_by": str(payment.created_by) if payment.created_by else None,
    }
