from typing import Optional, List
import uuid
from math import ceil
from datetime import date, datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, HTTPException, status, Query, Depends
from sqlalchemy import select, func, and_

from app.api.deps import DB, CurrentUser, Permissions, require_permissions
from app.models.customer import Customer, CustomerType, CustomerLedger, CustomerTransactionType
from app.schemas.customer import (
    CustomerCreate,
    CustomerUpdate,
    CustomerResponse,
    CustomerListResponse,
    Customer360Response,
    AddressCreate,
    AddressUpdate,
    AddressResponse,
    # Customer Ledger schemas
    CustomerLedgerCreate,
    CustomerLedgerResponse,
    CustomerLedgerListResponse,
    CustomerPaymentCreate,
    # AR Aging schemas
    ARAgingBucket,
    CustomerAgingResponse,
    ARAgingReport,
    ARAgingSummary,
)
from app.services.order_service import OrderService
from app.services.customer360_service import Customer360Service


router = APIRouter(tags=["Customers"])


@router.get(
    "",
    response_model=CustomerListResponse,
    dependencies=[Depends(require_permissions("crm:view"))]
)
async def list_customers(
    db: DB,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None, description="Search by name, phone, email"),
    customer_type: Optional[CustomerType] = Query(None),
    is_active: bool = Query(True),
):
    """
    Get paginated list of customers.
    Requires: crm:view permission
    """
    service = OrderService(db)
    skip = (page - 1) * size

    customers, total = await service.get_customers(
        search=search,
        customer_type=customer_type.value if customer_type else None,
        is_active=is_active,
        skip=skip,
        limit=size,
    )

    return CustomerListResponse(
        items=[CustomerResponse.model_validate(c) for c in customers],
        total=total,
        page=page,
        size=size,
        pages=ceil(total / size) if total > 0 else 1,
    )


@router.get(
    "/{customer_id}",
    response_model=CustomerResponse,
    dependencies=[Depends(require_permissions("crm:view"))]
)
async def get_customer(
    customer_id: uuid.UUID,
    db: DB,
):
    """Get a customer by ID."""
    service = OrderService(db)
    customer = await service.get_customer_by_id(customer_id)

    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )

    return CustomerResponse.model_validate(customer)


@router.get(
    "/phone/{phone}",
    response_model=CustomerResponse,
    dependencies=[Depends(require_permissions("crm:view"))]
)
async def get_customer_by_phone(
    phone: str,
    db: DB,
):
    """Get a customer by phone number."""
    service = OrderService(db)
    customer = await service.get_customer_by_phone(phone)

    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )

    return CustomerResponse.model_validate(customer)


@router.post(
    "",
    response_model=CustomerResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions("crm:create"))]
)
async def create_customer(
    data: CustomerCreate,
    db: DB,
    current_user: CurrentUser,
):
    """
    Create a new customer.
    Requires: crm:create permission
    """
    service = OrderService(db)

    # Check if phone already exists
    existing = await service.get_customer_by_phone(data.phone)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Customer with this phone number already exists"
        )

    customer = await service.create_customer(data.model_dump())
    return CustomerResponse.model_validate(customer)


@router.put(
    "/{customer_id}",
    response_model=CustomerResponse,
    dependencies=[Depends(require_permissions("crm:update"))]
)
async def update_customer(
    customer_id: uuid.UUID,
    data: CustomerUpdate,
    db: DB,
    current_user: CurrentUser,
):
    """
    Update a customer.
    Requires: crm:update permission
    """
    service = OrderService(db)

    customer = await service.get_customer_by_id(customer_id)
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )

    updated = await service.update_customer(
        customer_id,
        data.model_dump(exclude_unset=True)
    )
    return CustomerResponse.model_validate(updated)


@router.delete(
    "/{customer_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permissions("crm:delete"))]
)
async def delete_customer(
    customer_id: uuid.UUID,
    db: DB,
    current_user: CurrentUser,
):
    """
    Deactivate a customer.
    Requires: crm:delete permission
    """
    service = OrderService(db)

    customer = await service.get_customer_by_id(customer_id)
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )

    await service.update_customer(customer_id, {"is_active": False})


# ==================== CUSTOMER 360 ENDPOINT ====================

@router.get(
    "/{customer_id}/360",
    response_model=Customer360Response,
    dependencies=[Depends(require_permissions("crm:view"))],
    summary="Get Customer 360 View",
    description="""
    Get a comprehensive 360-degree view of the customer including:

    - **Customer Profile**: Basic info and addresses
    - **Statistics**: Order totals, service counts, ratings
    - **Timeline**: Chronological journey events
    - **Orders**: All orders with status history
    - **Shipments**: Delivery tracking
    - **Installations**: Product installations and warranty
    - **Service Requests**: Support tickets and repairs
    - **Calls**: Call center interactions
    - **Payments**: Payment history
    - **AMC Contracts**: Active maintenance contracts
    - **Lead Info**: Original lead data if converted
    """
)
async def get_customer_360(
    customer_id: uuid.UUID,
    db: DB,
    include_timeline: bool = Query(True, description="Include chronological timeline"),
    limit: int = Query(50, ge=1, le=200, description="Max records per section"),
):
    """
    Get complete Customer 360 view with all journey data.

    Requires: crm:view permission
    """
    import logging
    logger = logging.getLogger(__name__)

    try:
        service = Customer360Service(db)

        result = await service.get_customer_360(
            customer_id=customer_id,
            include_timeline=include_timeline,
            limit_per_section=limit,
        )

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Customer not found"
            )

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Customer 360 error for {customer_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching customer data: {str(e)}"
        )


@router.get(
    "/phone/{phone}/360",
    response_model=Customer360Response,
    dependencies=[Depends(require_permissions("crm:view"))],
    summary="Get Customer 360 View by Phone",
)
async def get_customer_360_by_phone(
    phone: str,
    db: DB,
    include_timeline: bool = Query(True, description="Include chronological timeline"),
    limit: int = Query(50, ge=1, le=200, description="Max records per section"),
):
    """
    Get complete Customer 360 view by phone number.

    Requires: crm:view permission
    """
    # First find customer by phone
    order_service = OrderService(db)
    customer = await order_service.get_customer_by_phone(phone)

    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )

    service = Customer360Service(db)
    result = await service.get_customer_360(
        customer_id=customer.id,
        include_timeline=include_timeline,
        limit_per_section=limit,
    )

    return result


# ==================== CUSTOMER LEDGER ENDPOINTS ====================

@router.get(
    "/{customer_id}/ledger",
    response_model=CustomerLedgerListResponse,
    dependencies=[Depends(require_permissions("finance:view"))],
    summary="Get Customer Ledger",
)
async def get_customer_ledger(
    customer_id: uuid.UUID,
    db: DB,
    start_date: Optional[date] = Query(None, description="Filter from date"),
    end_date: Optional[date] = Query(None, description="Filter to date"),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
):
    """
    Get customer ledger (Accounts Receivable) entries.

    Shows all transactions: invoices, payments, credit notes, debit notes, etc.

    Requires: finance:view permission
    """
    # Verify customer exists
    customer = await db.get(Customer, customer_id)
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )

    # Build query
    query = select(CustomerLedger).where(CustomerLedger.customer_id == customer_id)
    count_query = select(func.count(CustomerLedger.id)).where(
        CustomerLedger.customer_id == customer_id
    )

    if start_date:
        query = query.where(CustomerLedger.transaction_date >= start_date)
        count_query = count_query.where(CustomerLedger.transaction_date >= start_date)
    if end_date:
        query = query.where(CustomerLedger.transaction_date <= end_date)
        count_query = count_query.where(CustomerLedger.transaction_date <= end_date)

    # Get totals
    totals_query = select(
        func.coalesce(func.sum(CustomerLedger.debit_amount), 0).label("total_debit"),
        func.coalesce(func.sum(CustomerLedger.credit_amount), 0).label("total_credit"),
    ).where(CustomerLedger.customer_id == customer_id)

    if start_date:
        totals_query = totals_query.where(CustomerLedger.transaction_date >= start_date)
    if end_date:
        totals_query = totals_query.where(CustomerLedger.transaction_date <= end_date)

    # Execute queries
    total = (await db.execute(count_query)).scalar() or 0
    totals = (await db.execute(totals_query)).one()

    # Get opening balance (before start_date if provided)
    opening_balance = Decimal("0")
    if start_date:
        opening_query = select(
            func.coalesce(
                func.sum(CustomerLedger.debit_amount) - func.sum(CustomerLedger.credit_amount),
                0
            )
        ).where(
            CustomerLedger.customer_id == customer_id,
            CustomerLedger.transaction_date < start_date
        )
        opening_balance = (await db.execute(opening_query)).scalar() or Decimal("0")

    # Calculate closing balance
    closing_balance = opening_balance + totals.total_debit - totals.total_credit

    # Get paginated entries
    offset = (page - 1) * size
    query = query.order_by(
        CustomerLedger.transaction_date.desc(),
        CustomerLedger.created_at.desc()
    ).offset(offset).limit(size)

    result = await db.execute(query)
    entries = result.scalars().all()

    return CustomerLedgerListResponse(
        items=[CustomerLedgerResponse.model_validate(e) for e in entries],
        total=total,
        opening_balance=opening_balance,
        total_debit=totals.total_debit,
        total_credit=totals.total_credit,
        closing_balance=closing_balance,
    )


@router.post(
    "/{customer_id}/payment",
    response_model=CustomerLedgerResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions("finance:create"))],
    summary="Record Customer Payment",
)
async def record_customer_payment(
    customer_id: uuid.UUID,
    payment_in: CustomerPaymentCreate,
    db: DB,
    current_user: CurrentUser,
):
    """
    Record a payment received from customer.

    Creates a ledger entry and updates running balance.

    Requires: finance:create permission
    """
    # Verify customer exists
    customer = await db.get(Customer, customer_id)
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer not found"
        )

    # Verify customer_id matches
    if payment_in.customer_id != customer_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Customer ID mismatch"
        )

    # Get current balance
    balance_query = select(
        func.coalesce(
            func.sum(CustomerLedger.debit_amount) - func.sum(CustomerLedger.credit_amount),
            0
        )
    ).where(CustomerLedger.customer_id == customer_id)
    current_balance = (await db.execute(balance_query)).scalar() or Decimal("0")

    # Calculate new balance (payment reduces outstanding)
    new_balance = current_balance - payment_in.amount

    # Create ledger entry
    ledger_entry = CustomerLedger(
        customer_id=customer_id,
        transaction_type="PAYMENT",
        transaction_date=payment_in.payment_date,
        reference_type="PAYMENT_RECEIPT",
        reference_number=payment_in.reference_number,
        order_id=payment_in.order_id,
        debit_amount=Decimal("0"),
        credit_amount=payment_in.amount,
        balance=new_balance,
        description=f"Payment received via {payment_in.payment_mode}",
        notes=payment_in.remarks,
        created_by=current_user.id,
    )

    db.add(ledger_entry)
    await db.commit()
    await db.refresh(ledger_entry)

    return CustomerLedgerResponse.model_validate(ledger_entry)


# ==================== AR AGING REPORT ENDPOINTS ====================

@router.get(
    "/reports/ar-aging",
    response_model=ARAgingReport,
    dependencies=[Depends(require_permissions("finance:view"))],
    summary="Get AR Aging Report",
)
async def get_ar_aging_report(
    db: DB,
    as_of_date: Optional[date] = Query(None, description="Report as of date (default: today)"),
    customer_type: Optional[str] = Query(None, description="Filter by customer type"),
    min_outstanding: Optional[Decimal] = Query(None, description="Minimum outstanding amount"),
):
    """
    Get Accounts Receivable Aging Report.

    Shows outstanding amounts grouped by aging buckets:
    - Current (not yet due)
    - 1-30 days overdue
    - 31-60 days overdue
    - 61-90 days overdue
    - Over 90 days overdue

    Requires: finance:view permission
    """
    report_date = as_of_date or date.today()

    # Build customer query with filter
    customer_query = select(Customer).where(Customer.is_active == True)
    if customer_type:
        customer_query = customer_query.where(Customer.customer_type == customer_type)

    customers_result = await db.execute(customer_query)
    customers = customers_result.scalars().all()

    customer_aging_list: List[CustomerAgingResponse] = []
    summary_totals = {
        "CURRENT": Decimal("0"),
        "1_30": Decimal("0"),
        "31_60": Decimal("0"),
        "61_90": Decimal("0"),
        "OVER_90": Decimal("0"),
    }
    summary_counts = {
        "CURRENT": 0,
        "1_30": 0,
        "31_60": 0,
        "61_90": 0,
        "OVER_90": 0,
    }

    for customer in customers:
        # Get unsettled ledger entries (only invoices/debits)
        ledger_query = select(CustomerLedger).where(
            and_(
                CustomerLedger.customer_id == customer.id,
                CustomerLedger.is_settled == False,
                CustomerLedger.debit_amount > 0,  # Only debits (invoices)
            )
        )
        ledger_result = await db.execute(ledger_query)
        entries = ledger_result.scalars().all()

        if not entries:
            continue

        # Calculate aging buckets
        buckets = {
            "CURRENT": Decimal("0"),
            "1_30": Decimal("0"),
            "31_60": Decimal("0"),
            "61_90": Decimal("0"),
            "OVER_90": Decimal("0"),
        }

        for entry in entries:
            # Calculate outstanding amount (debit - any partial credits applied)
            outstanding = entry.debit_amount - entry.credit_amount
            if outstanding <= 0:
                continue

            # Determine aging bucket based on due_date
            if entry.due_date:
                days_overdue = (report_date - entry.due_date).days
            else:
                # If no due date, use transaction date + 30 days
                days_overdue = (report_date - entry.transaction_date).days - 30

            if days_overdue <= 0:
                buckets["CURRENT"] += outstanding
            elif days_overdue <= 30:
                buckets["1_30"] += outstanding
            elif days_overdue <= 60:
                buckets["31_60"] += outstanding
            elif days_overdue <= 90:
                buckets["61_90"] += outstanding
            else:
                buckets["OVER_90"] += outstanding

        total_outstanding = sum(buckets.values())

        # Filter by minimum outstanding if specified
        if min_outstanding and total_outstanding < min_outstanding:
            continue

        if total_outstanding > 0:
            customer_aging_list.append(CustomerAgingResponse(
                customer_id=customer.id,
                customer_code=customer.customer_code,
                customer_name=customer.full_name,
                customer_type=customer.customer_type,
                total_outstanding=total_outstanding,
                current=buckets["CURRENT"],
                days_1_30=buckets["1_30"],
                days_31_60=buckets["31_60"],
                days_61_90=buckets["61_90"],
                over_90_days=buckets["OVER_90"],
                buckets=[
                    ARAgingBucket(bucket=k, amount=v, count=1 if v > 0 else 0)
                    for k, v in buckets.items()
                ],
            ))

            # Update summary totals
            for k, v in buckets.items():
                summary_totals[k] += v
                if v > 0:
                    summary_counts[k] += 1

    # Sort by total outstanding descending
    customer_aging_list.sort(key=lambda x: x.total_outstanding, reverse=True)

    return ARAgingReport(
        as_of_date=report_date,
        total_outstanding=sum(summary_totals.values()),
        total_current=summary_totals["CURRENT"],
        total_1_30=summary_totals["1_30"],
        total_31_60=summary_totals["31_60"],
        total_61_90=summary_totals["61_90"],
        total_over_90=summary_totals["OVER_90"],
        customers=customer_aging_list,
        summary_buckets=[
            ARAgingBucket(bucket=k, amount=v, count=summary_counts.get(k, 0))
            for k, v in summary_totals.items()
        ],
    )


@router.get(
    "/reports/ar-aging/summary",
    response_model=ARAgingSummary,
    dependencies=[Depends(require_permissions("finance:view"))],
    summary="Get AR Aging Summary",
)
async def get_ar_aging_summary(
    db: DB,
    as_of_date: Optional[date] = Query(None, description="Report as of date (default: today)"),
    top_n: int = Query(5, ge=1, le=20, description="Number of top overdue customers"),
):
    """
    Get AR Aging summary for dashboard.

    Shows total outstanding by aging bucket and top overdue customers.

    Requires: finance:view permission
    """
    report_date = as_of_date or date.today()

    # Get unsettled ledger entries grouped
    query = select(
        CustomerLedger.customer_id,
        CustomerLedger.due_date,
        CustomerLedger.transaction_date,
        CustomerLedger.debit_amount,
        CustomerLedger.credit_amount,
    ).where(
        and_(
            CustomerLedger.is_settled == False,
            CustomerLedger.debit_amount > 0,
        )
    )

    result = await db.execute(query)
    entries = result.all()

    # Calculate aging buckets
    buckets = {
        "CURRENT": Decimal("0"),
        "1_30": Decimal("0"),
        "31_60": Decimal("0"),
        "61_90": Decimal("0"),
        "OVER_90": Decimal("0"),
    }
    bucket_counts = {k: 0 for k in buckets.keys()}
    customer_totals: dict = {}

    for entry in entries:
        outstanding = entry.debit_amount - entry.credit_amount
        if outstanding <= 0:
            continue

        # Determine aging bucket
        if entry.due_date:
            days_overdue = (report_date - entry.due_date).days
        else:
            days_overdue = (report_date - entry.transaction_date).days - 30

        if days_overdue <= 0:
            bucket = "CURRENT"
        elif days_overdue <= 30:
            bucket = "1_30"
        elif days_overdue <= 60:
            bucket = "31_60"
        elif days_overdue <= 90:
            bucket = "61_90"
        else:
            bucket = "OVER_90"

        buckets[bucket] += outstanding
        bucket_counts[bucket] += 1

        # Track customer totals
        cid = str(entry.customer_id)
        if cid not in customer_totals:
            customer_totals[cid] = Decimal("0")
        customer_totals[cid] += outstanding

    # Get top N customers
    top_customer_ids = sorted(
        customer_totals.keys(),
        key=lambda x: customer_totals[x],
        reverse=True
    )[:top_n]

    top_customers = []
    for cid in top_customer_ids:
        customer = await db.get(Customer, uuid.UUID(cid))
        if customer:
            top_customers.append(CustomerAgingResponse(
                customer_id=customer.id,
                customer_code=customer.customer_code,
                customer_name=customer.full_name,
                customer_type=customer.customer_type,
                total_outstanding=customer_totals[cid],
                buckets=[],
            ))

    return ARAgingSummary(
        as_of_date=report_date,
        total_outstanding=sum(buckets.values()),
        total_customers_with_outstanding=len(customer_totals),
        buckets=[
            ARAgingBucket(bucket=k, amount=v, count=bucket_counts[k])
            for k, v in buckets.items()
        ],
        top_overdue_customers=top_customers,
    )
