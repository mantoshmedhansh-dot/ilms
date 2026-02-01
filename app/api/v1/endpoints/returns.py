"""
Return Order API Endpoints

Handles return requests, inspections, and approvals.
Includes both admin and customer-facing endpoints.
"""

import logging
import uuid
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Optional, List

from fastapi import APIRouter, HTTPException, status, Depends, Query
from sqlalchemy import select, func, or_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.return_order import ReturnOrder, ReturnItem, ReturnStatusHistory, Refund
from app.models.order import Order, OrderItem
from app.models.customer import Customer
from app.schemas.return_order import (
    ReturnOrderCreate,
    ReturnOrderUpdate,
    ReturnOrderResponse,
    ReturnOrderListResponse,
    ReturnInspectionRequest,
    CustomerReturnRequest,
    CustomerReturnStatus,
    PaginatedReturnOrdersResponse,
    ReturnStatus,
    RefundCreate,
    RefundResponse,
    RefundListResponse,
    PaginatedRefundsResponse,
    RefundType,
    RefundMethod,
    RefundStatus,
)
from app.api.v1.endpoints.d2c_auth import get_current_customer, require_customer
from app.api.deps import get_current_user
from app.models.user import User
from app.core.module_decorators import require_module

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/returns", tags=["Returns"])


# ==================== Helper Functions ====================

def generate_rma_number() -> str:
    """Generate a unique RMA number."""
    import random
    import string
    timestamp = datetime.now().strftime("%y%m%d")
    random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"RMA{timestamp}{random_part}"


def generate_refund_number() -> str:
    """Generate a unique refund number."""
    import random
    import string

    timestamp = datetime.now().strftime("%y%m%d")
    random_part = ''.join(random.choices(string.digits, k=6))
    return f"REF{timestamp}{random_part}"


def get_status_message(status: str) -> str:
    """Get human-readable status message."""
    messages = {
        "INITIATED": "Return request submitted",
        "AUTHORIZED": "Return authorized - awaiting pickup",
        "PICKUP_SCHEDULED": "Pickup scheduled",
        "PICKED_UP": "Items picked up",
        "IN_TRANSIT": "Return shipment in transit",
        "RECEIVED": "Items received at warehouse",
        "UNDER_INSPECTION": "Items under inspection",
        "APPROVED": "Return approved - refund initiated",
        "REJECTED": "Return rejected",
        "REFUND_INITIATED": "Refund processing",
        "REFUND_PROCESSED": "Refund completed",
        "CLOSED": "Return closed",
        "CANCELLED": "Return cancelled",
    }
    return messages.get(status, status)


async def add_status_history(
    db: AsyncSession,
    return_order: ReturnOrder,
    to_status: str,
    notes: Optional[str] = None,
    changed_by: Optional[uuid.UUID] = None
):
    """Add a status history entry."""
    history = ReturnStatusHistory(
        return_order_id=return_order.id,
        from_status=return_order.status,
        to_status=to_status,
        notes=notes,
        changed_by=changed_by,
    )
    db.add(history)


# ==================== Customer-Facing Endpoints (D2C) ====================

@router.post("/request", response_model=CustomerReturnStatus)
@require_module("oms_fulfillment")
async def request_return(
    request: CustomerReturnRequest,
    db: AsyncSession = Depends(get_db),
    customer: Optional[Customer] = Depends(get_current_customer),
):
    """
    Customer initiates a return request.
    Requires order number and phone for verification.
    """
    # Find the order
    query = select(Order).options(
        selectinload(Order.items)
    ).where(
        Order.order_number == request.order_number.upper(),
    )

    # Verify phone
    result = await db.execute(query)
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )

    # Verify phone matches
    shipping_phone = order.shipping_address.get("phone", "") if order.shipping_address else ""
    if shipping_phone.replace("+91", "").replace(" ", "") != request.phone.replace("+91", "").replace(" ", ""):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Phone number doesn't match order"
        )

    # Check if order is eligible for return (delivered and within return window)
    if order.status not in ["DELIVERED", "PARTIALLY_DELIVERED"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Order cannot be returned. Current status: {order.status}"
        )

    # Check return window (e.g., 7 days from delivery)
    if order.delivered_at:
        return_deadline = order.delivered_at + timedelta(days=7)
        if datetime.now(timezone.utc) > return_deadline:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Return window has expired (7 days from delivery)"
            )

    # Validate items
    order_item_ids = {str(item.id) for item in order.items}
    for item in request.items:
        if str(item.order_item_id) not in order_item_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Item {item.order_item_id} not found in order"
            )

    # Check if items are already in a return
    for item in request.items:
        existing_return = await db.execute(
            select(ReturnItem).where(
                ReturnItem.order_item_id == item.order_item_id,
            )
        )
        if existing_return.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Item {item.order_item_id} is already in a return request"
            )

    # Create return order
    return_order = ReturnOrder(
        rma_number=generate_rma_number(),
        order_id=order.id,
        customer_id=customer.id if customer else order.customer_id,
        return_type="RETURN",
        return_reason=request.return_reason.value,
        return_reason_details=request.return_reason_details,
        status="INITIATED",
        pickup_address=request.pickup_address.model_dump() if request.pickup_address else order.shipping_address,
    )
    db.add(return_order)
    await db.flush()

    # Add return items
    total_return_amount = Decimal("0.00")
    for item_request in request.items:
        # Get order item details
        order_item = next(
            (oi for oi in order.items if str(oi.id) == str(item_request.order_item_id)),
            None
        )
        if not order_item:
            continue

        item_amount = order_item.unit_price * item_request.quantity_returned
        total_return_amount += item_amount

        return_item = ReturnItem(
            return_order_id=return_order.id,
            order_item_id=order_item.id,
            product_id=order_item.product_id,
            product_name=order_item.product_name,
            sku=order_item.sku,
            quantity_ordered=order_item.quantity,
            quantity_returned=item_request.quantity_returned,
            condition=item_request.condition.value,
            condition_notes=item_request.condition_notes,
            unit_price=order_item.unit_price,
            total_amount=item_amount,
            customer_images=item_request.customer_images,
        )
        db.add(return_item)

    # Update amounts
    return_order.total_return_amount = total_return_amount
    return_order.net_refund_amount = total_return_amount  # Will be adjusted during inspection

    # Add initial status history
    await add_status_history(
        db, return_order, "INITIATED",
        notes=f"Return requested: {request.return_reason.value}"
    )

    await db.commit()
    await db.refresh(return_order)

    # Load items for response
    items_result = await db.execute(
        select(ReturnItem).where(ReturnItem.return_order_id == return_order.id)
    )
    return_items = items_result.scalars().all()

    # Load status history
    history_result = await db.execute(
        select(ReturnStatusHistory)
        .where(ReturnStatusHistory.return_order_id == return_order.id)
        .order_by(ReturnStatusHistory.created_at)
    )
    status_history = history_result.scalars().all()

    logger.info(f"Return request created: {return_order.rma_number} for order {order.order_number}")

    return CustomerReturnStatus(
        rma_number=return_order.rma_number,
        status=return_order.status,
        status_message=get_status_message(return_order.status),
        requested_at=return_order.requested_at,
        refund_amount=return_order.net_refund_amount,
        items=[
            {
                "id": item.id,
                "order_item_id": item.order_item_id,
                "product_id": item.product_id,
                "product_name": item.product_name,
                "sku": item.sku,
                "quantity_ordered": item.quantity_ordered,
                "quantity_returned": item.quantity_returned,
                "condition": item.condition,
                "condition_notes": item.condition_notes,
                "inspection_result": item.inspection_result,
                "inspection_notes": item.inspection_notes,
                "accepted_quantity": item.accepted_quantity,
                "unit_price": item.unit_price,
                "total_amount": item.total_amount,
                "refund_amount": item.refund_amount,
                "serial_number": item.serial_number,
                "customer_images": item.customer_images,
            }
            for item in return_items
        ],
        timeline=[
            {
                "id": h.id,
                "from_status": h.from_status,
                "to_status": h.to_status,
                "notes": h.notes,
                "created_at": h.created_at,
            }
            for h in status_history
        ],
    )


@router.get("/track/{rma_number}", response_model=CustomerReturnStatus)
@require_module("oms_fulfillment")
async def track_return(
    rma_number: str,
    phone: str = Query(..., description="Phone for verification"),
    db: AsyncSession = Depends(get_db),
):
    """
    Track return status by RMA number (customer-facing).
    """
    # Find return order
    result = await db.execute(
        select(ReturnOrder)
        .options(
            selectinload(ReturnOrder.items),
            selectinload(ReturnOrder.status_history),
            selectinload(ReturnOrder.order),
            selectinload(ReturnOrder.refund),
        )
        .where(ReturnOrder.rma_number == rma_number.upper())
    )
    return_order = result.scalar_one_or_none()

    if not return_order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Return not found"
        )

    # Verify phone
    if return_order.order and return_order.order.shipping_address:
        shipping_phone = return_order.order.shipping_address.get("phone", "")
        if shipping_phone.replace("+91", "").replace(" ", "") != phone.replace("+91", "").replace(" ", ""):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Phone number doesn't match"
            )

    # Calculate estimated refund date
    estimated_refund_date = None
    if return_order.status in ["APPROVED", "REFUND_INITIATED"]:
        estimated_refund_date = datetime.now(timezone.utc) + timedelta(days=5)

    return CustomerReturnStatus(
        rma_number=return_order.rma_number,
        status=return_order.status,
        status_message=get_status_message(return_order.status),
        requested_at=return_order.requested_at,
        estimated_refund_date=estimated_refund_date,
        refund_amount=return_order.net_refund_amount,
        refund_status=return_order.refund.status if return_order.refund else None,
        tracking_number=return_order.return_tracking_number,
        courier=return_order.return_courier,
        items=[
            {
                "id": item.id,
                "order_item_id": item.order_item_id,
                "product_id": item.product_id,
                "product_name": item.product_name,
                "sku": item.sku,
                "quantity_ordered": item.quantity_ordered,
                "quantity_returned": item.quantity_returned,
                "condition": item.condition,
                "condition_notes": item.condition_notes,
                "inspection_result": item.inspection_result,
                "inspection_notes": item.inspection_notes,
                "accepted_quantity": item.accepted_quantity,
                "unit_price": item.unit_price,
                "total_amount": item.total_amount,
                "refund_amount": item.refund_amount,
                "serial_number": item.serial_number,
                "customer_images": item.customer_images,
            }
            for item in return_order.items
        ],
        timeline=[
            {
                "id": h.id,
                "from_status": h.from_status,
                "to_status": h.to_status,
                "notes": h.notes,
                "created_at": h.created_at,
            }
            for h in return_order.status_history
        ],
    )


@router.get("/my-returns")
@require_module("oms_fulfillment")
async def get_my_returns(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=50),
    customer: Customer = Depends(require_customer),
    db: AsyncSession = Depends(get_db),
):
    """
    Get returns for logged-in customer.
    """
    # Count total
    count_query = select(func.count(ReturnOrder.id)).where(
        ReturnOrder.customer_id == customer.id
    )
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Get returns
    query = select(ReturnOrder).options(
        selectinload(ReturnOrder.items),
        selectinload(ReturnOrder.order),
    ).where(
        ReturnOrder.customer_id == customer.id
    ).order_by(
        ReturnOrder.created_at.desc()
    ).offset((page - 1) * size).limit(size)

    result = await db.execute(query)
    returns = result.scalars().all()

    return {
        "items": [
            {
                "id": r.id,
                "rma_number": r.rma_number,
                "order_id": r.order_id,
                "order_number": r.order.order_number if r.order else None,
                "return_type": r.return_type,
                "return_reason": r.return_reason,
                "status": r.status,
                "status_message": get_status_message(r.status),
                "requested_at": r.requested_at,
                "total_return_amount": r.total_return_amount,
                "net_refund_amount": r.net_refund_amount,
                "items_count": len(r.items),
            }
            for r in returns
        ],
        "total": total,
        "page": page,
        "size": size,
        "pages": (total + size - 1) // size if total else 0,
    }


@router.post("/{rma_number}/cancel")
@require_module("oms_fulfillment")
async def cancel_return(
    rma_number: str,
    customer: Customer = Depends(require_customer),
    db: AsyncSession = Depends(get_db),
):
    """
    Cancel a return request (only if not yet picked up).
    """
    result = await db.execute(
        select(ReturnOrder).where(
            ReturnOrder.rma_number == rma_number.upper(),
            ReturnOrder.customer_id == customer.id,
        )
    )
    return_order = result.scalar_one_or_none()

    if not return_order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Return not found"
        )

    if not return_order.can_be_cancelled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Return cannot be cancelled. Current status: {return_order.status}"
        )

    await add_status_history(db, return_order, "CANCELLED", notes="Cancelled by customer")
    return_order.status = "CANCELLED"
    return_order.closed_at = datetime.now(timezone.utc)

    await db.commit()

    return {"message": "Return cancelled successfully", "rma_number": rma_number}


# ==================== Admin Endpoints ====================

@router.get("", response_model=PaginatedReturnOrdersResponse)
@require_module("oms_fulfillment")
async def list_returns(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    search: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List all return orders (admin).
    """
    query = select(ReturnOrder).options(
        selectinload(ReturnOrder.items),
        selectinload(ReturnOrder.order),
    )

    # Filters
    if status:
        query = query.where(ReturnOrder.status == status)

    if search:
        query = query.where(
            or_(
                ReturnOrder.rma_number.ilike(f"%{search}%"),
                ReturnOrder.order.has(Order.order_number.ilike(f"%{search}%")),
            )
        )

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Paginate
    query = query.order_by(ReturnOrder.created_at.desc()).offset((page - 1) * size).limit(size)

    result = await db.execute(query)
    returns = result.scalars().all()

    return PaginatedReturnOrdersResponse(
        items=[
            ReturnOrderListResponse(
                id=r.id,
                rma_number=r.rma_number,
                order_id=r.order_id,
                order_number=r.order.order_number if r.order else None,
                return_type=r.return_type,
                return_reason=r.return_reason,
                status=r.status,
                requested_at=r.requested_at,
                total_return_amount=r.total_return_amount,
                net_refund_amount=r.net_refund_amount,
                items_count=len(r.items),
            )
            for r in returns
        ],
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size if total else 0,
    )


@router.get("/{return_id}", response_model=ReturnOrderResponse)
@require_module("oms_fulfillment")
async def get_return(
    return_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get return order details (admin).
    """
    result = await db.execute(
        select(ReturnOrder).options(
            selectinload(ReturnOrder.items),
            selectinload(ReturnOrder.status_history),
            selectinload(ReturnOrder.refund),
        ).where(ReturnOrder.id == return_id)
    )
    return_order = result.scalar_one_or_none()

    if not return_order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Return not found"
        )

    return return_order


@router.put("/{return_id}/authorize")
@require_module("oms_fulfillment")
async def authorize_return(
    return_id: uuid.UUID,
    notes: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Authorize a return request (admin).
    """
    result = await db.execute(
        select(ReturnOrder).where(ReturnOrder.id == return_id)
    )
    return_order = result.scalar_one_or_none()

    if not return_order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Return not found"
        )

    if return_order.status != "INITIATED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot authorize return with status: {return_order.status}"
        )

    await add_status_history(
        db, return_order, "AUTHORIZED",
        notes=notes or "Return authorized",
        changed_by=current_user.id
    )
    return_order.status = "AUTHORIZED"
    return_order.authorized_at = datetime.now(timezone.utc)

    await db.commit()

    logger.info(f"Return {return_order.rma_number} authorized by {current_user.email}")

    return {"message": "Return authorized", "rma_number": return_order.rma_number}


@router.put("/{return_id}/receive")
@require_module("oms_fulfillment")
async def receive_return(
    return_id: uuid.UUID,
    notes: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Mark return as received at warehouse (admin).
    """
    result = await db.execute(
        select(ReturnOrder).where(ReturnOrder.id == return_id)
    )
    return_order = result.scalar_one_or_none()

    if not return_order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Return not found"
        )

    await add_status_history(
        db, return_order, "RECEIVED",
        notes=notes or "Items received at warehouse",
        changed_by=current_user.id
    )
    return_order.status = "RECEIVED"
    return_order.received_at = datetime.now(timezone.utc)

    await db.commit()

    return {"message": "Return marked as received", "rma_number": return_order.rma_number}


@router.post("/{return_id}/inspect")
@require_module("oms_fulfillment")
async def inspect_return(
    return_id: uuid.UUID,
    inspection: ReturnInspectionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Submit inspection results for a return (admin).
    """
    result = await db.execute(
        select(ReturnOrder).options(
            selectinload(ReturnOrder.items)
        ).where(ReturnOrder.id == return_id)
    )
    return_order = result.scalar_one_or_none()

    if not return_order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Return not found"
        )

    if return_order.status not in ["RECEIVED", "UNDER_INSPECTION"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot inspect return with status: {return_order.status}"
        )

    # Update items with inspection results
    total_refund = Decimal("0.00")
    all_accepted = True
    all_rejected = True

    for item_inspection in inspection.items:
        item = next(
            (i for i in return_order.items if i.id == item_inspection.return_item_id),
            None
        )
        if not item:
            continue

        item.inspection_result = item_inspection.inspection_result.value
        item.inspection_notes = item_inspection.inspection_notes

        if item_inspection.inspection_result.value == "ACCEPTED":
            item.accepted_quantity = item.quantity_returned
            item.refund_amount = item.total_amount
            total_refund += item.refund_amount
            all_rejected = False
        elif item_inspection.inspection_result.value == "PARTIAL":
            item.accepted_quantity = item_inspection.accepted_quantity or 0
            item.refund_amount = item.unit_price * item.accepted_quantity
            total_refund += item.refund_amount
            all_accepted = False
            all_rejected = False
        else:  # REJECTED
            item.accepted_quantity = 0
            item.refund_amount = Decimal("0.00")
            all_accepted = False

    # Determine overall status
    if all_rejected:
        new_status = "REJECTED"
        return_order.rejection_reason = inspection.overall_notes or "Items rejected after inspection"
        return_order.resolution_type = None
    else:
        new_status = "APPROVED"
        return_order.resolution_type = "FULL_REFUND" if all_accepted else "PARTIAL_REFUND"

    # Update return order
    return_order.net_refund_amount = total_refund
    return_order.inspection_notes = inspection.overall_notes
    return_order.inspected_by = current_user.id
    return_order.inspected_at = datetime.now(timezone.utc)

    await add_status_history(
        db, return_order, new_status,
        notes=inspection.overall_notes,
        changed_by=current_user.id
    )
    return_order.status = new_status

    await db.commit()

    logger.info(f"Return {return_order.rma_number} inspected: {new_status}")

    return {
        "message": f"Inspection complete - {new_status}",
        "rma_number": return_order.rma_number,
        "net_refund_amount": float(total_refund),
    }


@router.post("/{return_id}/refund")
@require_module("oms_fulfillment")
async def initiate_refund(
    return_id: uuid.UUID,
    refund_method: RefundMethod = RefundMethod.ORIGINAL_PAYMENT,
    notes: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Initiate refund for an approved return (admin).
    """
    result = await db.execute(
        select(ReturnOrder).options(
            selectinload(ReturnOrder.order)
        ).where(ReturnOrder.id == return_id)
    )
    return_order = result.scalar_one_or_none()

    if not return_order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Return not found"
        )

    if return_order.status != "APPROVED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot initiate refund for return with status: {return_order.status}"
        )

    if return_order.net_refund_amount <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No refund amount"
        )

    # Create refund record
    refund = Refund(
        refund_number=generate_refund_number(),
        order_id=return_order.order_id,
        return_order_id=return_order.id,
        customer_id=return_order.customer_id,
        refund_type="RETURN",
        refund_method=refund_method.value,
        order_amount=return_order.order.total_amount if return_order.order else return_order.total_return_amount,
        refund_amount=return_order.net_refund_amount,
        net_refund=return_order.net_refund_amount,
        reason=f"Return {return_order.rma_number}: {return_order.return_reason}",
        notes=notes,
        initiated_by=current_user.id,
    )
    db.add(refund)

    await add_status_history(
        db, return_order, "REFUND_INITIATED",
        notes=f"Refund initiated: {refund.refund_number}",
        changed_by=current_user.id
    )
    return_order.status = "REFUND_INITIATED"

    await db.commit()
    await db.refresh(refund)

    logger.info(f"Refund {refund.refund_number} initiated for return {return_order.rma_number}")

    return {
        "message": "Refund initiated",
        "refund_number": refund.refund_number,
        "amount": float(refund.net_refund),
    }


# ==================== Refund Endpoints ====================

@router.get("/refunds/list", response_model=PaginatedRefundsResponse)
@require_module("oms_fulfillment")
async def list_refunds(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List all refunds (admin).
    """
    query = select(Refund).options(selectinload(Refund.order))

    if status:
        query = query.where(Refund.status == status)

    # Count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Paginate
    query = query.order_by(Refund.created_at.desc()).offset((page - 1) * size).limit(size)

    result = await db.execute(query)
    refunds = result.scalars().all()

    return PaginatedRefundsResponse(
        items=[
            RefundListResponse(
                id=r.id,
                refund_number=r.refund_number,
                order_id=r.order_id,
                order_number=r.order.order_number if r.order else None,
                refund_type=r.refund_type,
                net_refund=r.net_refund,
                status=r.status,
                initiated_at=r.initiated_at,
                completed_at=r.completed_at,
            )
            for r in refunds
        ],
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size if total else 0,
    )


@router.put("/refunds/{refund_id}/process")
@require_module("oms_fulfillment")
async def process_refund(
    refund_id: uuid.UUID,
    transaction_id: Optional[str] = None,
    notes: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Mark refund as processed (admin).
    """
    result = await db.execute(
        select(Refund).options(
            selectinload(Refund.return_order)
        ).where(Refund.id == refund_id)
    )
    refund = result.scalar_one_or_none()

    if not refund:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Refund not found"
        )

    if refund.status not in ["PENDING", "PROCESSING"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot process refund with status: {refund.status}"
        )

    refund.status = "COMPLETED"
    refund.refund_transaction_id = transaction_id
    refund.processed_at = datetime.now(timezone.utc)
    refund.completed_at = datetime.now(timezone.utc)
    refund.notes = (refund.notes or "") + f"\n{notes}" if notes else refund.notes
    refund.approved_by = current_user.id

    # Update return order status
    if refund.return_order:
        await add_status_history(
            db, refund.return_order, "REFUND_PROCESSED",
            notes=f"Refund completed: {transaction_id or refund.refund_number}",
            changed_by=current_user.id
        )
        refund.return_order.status = "REFUND_PROCESSED"
        refund.return_order.closed_at = datetime.now(timezone.utc)

    await db.commit()

    logger.info(f"Refund {refund.refund_number} processed")

    return {"message": "Refund processed", "refund_number": refund.refund_number}
