"""
Order Tracking API Endpoints

Provides detailed order tracking with timeline, shipment updates, and status history.
For both admin and customer-facing use.
"""

import logging
from datetime import datetime, timezone
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, HTTPException, status, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.order import Order, OrderStatusHistory, Payment
from app.models.shipment import Shipment, ShipmentTracking
from app.models.return_order import ReturnOrder
from app.models.customer import Customer
from app.api.v1.endpoints.d2c_auth import get_current_customer, require_customer
from app.core.module_decorators import require_module

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/order-tracking", tags=["Order Tracking"])


# ==================== Schemas ====================

class TimelineEvent(BaseModel):
    """A single event in the order timeline."""
    event_type: str  # ORDER, PAYMENT, SHIPMENT, DELIVERY, RETURN
    status: str
    title: str
    description: Optional[str] = None
    timestamp: datetime
    location: Optional[str] = None
    metadata: Optional[dict] = None


class ShipmentInfo(BaseModel):
    """Shipment tracking information."""
    shipment_id: str
    tracking_number: Optional[str]
    courier_name: Optional[str]
    status: str
    status_message: str
    shipped_at: Optional[datetime]
    estimated_delivery: Optional[datetime]
    delivered_at: Optional[datetime]
    current_location: Optional[str]
    tracking_url: Optional[str]
    tracking_events: List[dict] = []


class OrderTrackingResponse(BaseModel):
    """Complete order tracking response."""
    order_number: str
    order_id: str
    status: str
    status_message: str
    payment_status: str
    payment_method: str
    placed_at: datetime
    confirmed_at: Optional[datetime]
    shipped_at: Optional[datetime]
    delivered_at: Optional[datetime]
    cancelled_at: Optional[datetime]

    # Amounts
    subtotal: float
    tax_amount: float
    shipping_amount: float
    discount_amount: float
    total_amount: float
    amount_paid: float

    # Shipping Address
    shipping_address: dict

    # Items
    items: List[dict]

    # Timeline
    timeline: List[TimelineEvent]

    # Shipments
    shipments: List[ShipmentInfo] = []

    # Returns
    active_return: Optional[dict] = None

    # Flags
    can_cancel: bool = False
    can_return: bool = False


# ==================== Helper Functions ====================

def get_status_message(status: str) -> str:
    """Get human-readable status message."""
    messages = {
        "NEW": "Order received",
        "PENDING_PAYMENT": "Awaiting payment",
        "CONFIRMED": "Order confirmed",
        "ALLOCATED": "Items allocated from warehouse",
        "PICKLIST_CREATED": "Preparing for shipment",
        "PICKING": "Items being picked",
        "PICKED": "Items picked",
        "PACKING": "Packing in progress",
        "PACKED": "Packed and ready",
        "MANIFESTED": "Shipment manifested",
        "READY_TO_SHIP": "Ready for dispatch",
        "SHIPPED": "Shipped",
        "IN_TRANSIT": "In transit",
        "OUT_FOR_DELIVERY": "Out for delivery",
        "DELIVERED": "Delivered",
        "PARTIALLY_DELIVERED": "Partially delivered",
        "RTO_INITIATED": "Return to origin initiated",
        "RTO_IN_TRANSIT": "Returning to warehouse",
        "RTO_DELIVERED": "Returned to warehouse",
        "RETURNED": "Returned",
        "CANCELLED": "Cancelled",
        "REFUNDED": "Refunded",
        "ON_HOLD": "On hold",
    }
    return messages.get(status, status)


def get_shipment_status_message(status: str) -> str:
    """Get human-readable shipment status message."""
    messages = {
        "CREATED": "Shipment created",
        "PACKED": "Package ready",
        "READY_FOR_PICKUP": "Ready for pickup",
        "MANIFESTED": "Added to manifest",
        "PICKED_UP": "Picked up by courier",
        "IN_TRANSIT": "In transit",
        "REACHED_HUB": "At sorting hub",
        "OUT_FOR_DELIVERY": "Out for delivery",
        "DELIVERED": "Delivered",
        "DELIVERY_ATTEMPTED": "Delivery attempted",
        "RTO_INITIATED": "Return initiated",
        "RTO_IN_TRANSIT": "Returning to sender",
        "RTO_DELIVERED": "Returned to sender",
    }
    return messages.get(status, status)


def build_timeline(order: Order, shipments: List[Shipment], returns: List[ReturnOrder]) -> List[TimelineEvent]:
    """Build a comprehensive timeline of order events."""
    events = []

    # Order status history
    if order.status_history:
        for history in order.status_history:
            events.append(TimelineEvent(
                event_type="ORDER",
                status=history.to_status,
                title=get_status_message(history.to_status),
                description=history.notes,
                timestamp=history.created_at,
                metadata={"from_status": history.from_status},
            ))

    # Payment events
    if order.payments:
        for payment in order.payments:
            if payment.status == "PAID" or payment.status == "CAPTURED":
                events.append(TimelineEvent(
                    event_type="PAYMENT",
                    status="PAID",
                    title="Payment received",
                    description=f"Payment of ₹{payment.amount:.0f} via {payment.payment_method}",
                    timestamp=payment.paid_at or payment.created_at,
                    metadata={
                        "amount": float(payment.amount),
                        "method": payment.payment_method,
                        "transaction_id": payment.transaction_id,
                    },
                ))
            elif payment.status == "FAILED":
                events.append(TimelineEvent(
                    event_type="PAYMENT",
                    status="FAILED",
                    title="Payment failed",
                    description=payment.failure_reason,
                    timestamp=payment.updated_at,
                ))
            elif payment.status == "REFUNDED":
                events.append(TimelineEvent(
                    event_type="PAYMENT",
                    status="REFUNDED",
                    title="Refund processed",
                    description=f"Refund of ₹{payment.refund_amount:.0f}",
                    timestamp=payment.refunded_at or payment.updated_at,
                    metadata={"refund_amount": float(payment.refund_amount or 0)},
                ))

    # Shipment tracking events
    for shipment in shipments:
        # Shipment created
        events.append(TimelineEvent(
            event_type="SHIPMENT",
            status="CREATED",
            title="Shipment created",
            description=f"AWB: {shipment.awb_number}" if shipment.awb_number else None,
            timestamp=shipment.created_at,
            metadata={
                "shipment_id": str(shipment.id),
                "awb_number": shipment.awb_number,
            },
        ))

        # Shipped
        if shipment.shipped_at:
            events.append(TimelineEvent(
                event_type="SHIPMENT",
                status="SHIPPED",
                title="Package shipped",
                description=f"Via {shipment.transporter.name}" if shipment.transporter else None,
                timestamp=shipment.shipped_at,
                location=shipment.origin_city,
            ))

        # Tracking events
        if shipment.tracking_events:
            for tracking in shipment.tracking_events:
                events.append(TimelineEvent(
                    event_type="DELIVERY",
                    status=tracking.status,
                    title=get_shipment_status_message(tracking.status),
                    description=tracking.remarks,
                    timestamp=tracking.event_time,
                    location=tracking.location,
                ))

        # Delivered
        if shipment.delivered_at:
            events.append(TimelineEvent(
                event_type="DELIVERY",
                status="DELIVERED",
                title="Package delivered",
                description=f"Delivered to {shipment.delivered_to}" if shipment.delivered_to else "Successfully delivered",
                timestamp=shipment.delivered_at,
                location=shipment.destination_city,
                metadata={
                    "delivered_to": shipment.delivered_to,
                    "relation": shipment.delivery_relation,
                },
            ))

    # Return events
    for return_order in returns:
        events.append(TimelineEvent(
            event_type="RETURN",
            status=return_order.status,
            title=f"Return {return_order.status.lower().replace('_', ' ')}",
            description=f"RMA: {return_order.rma_number}",
            timestamp=return_order.requested_at if return_order.status == "INITIATED" else return_order.updated_at,
            metadata={
                "rma_number": return_order.rma_number,
                "return_reason": return_order.return_reason,
            },
        ))

    # Sort by timestamp
    events.sort(key=lambda e: e.timestamp, reverse=True)

    return events


# ==================== Endpoints ====================

@router.get("/track/{order_number}")
@require_module("oms_fulfillment")
async def track_order_public(
    order_number: str,
    phone: str = Query(..., description="Phone number for verification"),
    db: AsyncSession = Depends(get_db),
) -> OrderTrackingResponse:
    """
    Track order by order number (public endpoint).
    Requires phone verification.
    """
    # Find order
    result = await db.execute(
        select(Order).options(
            selectinload(Order.items),
            selectinload(Order.status_history),
            selectinload(Order.payments),
            selectinload(Order.shipments).selectinload(Shipment.tracking_events),
            selectinload(Order.shipments).selectinload(Shipment.transporter),
            selectinload(Order.returns),
        ).where(Order.order_number == order_number.upper())
    )
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )

    # Verify phone
    shipping_phone = order.shipping_address.get("phone", "") if order.shipping_address else ""
    if shipping_phone.replace("+91", "").replace(" ", "") != phone.replace("+91", "").replace(" ", ""):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Phone number doesn't match order"
        )

    return build_tracking_response(order)


@router.get("/my-order/{order_number}")
@require_module("oms_fulfillment")
async def track_my_order(
    order_number: str,
    customer: Customer = Depends(require_customer),
    db: AsyncSession = Depends(get_db),
) -> OrderTrackingResponse:
    """
    Track order for logged-in customer.
    """
    result = await db.execute(
        select(Order).options(
            selectinload(Order.items),
            selectinload(Order.status_history),
            selectinload(Order.payments),
            selectinload(Order.shipments).selectinload(Shipment.tracking_events),
            selectinload(Order.shipments).selectinload(Shipment.transporter),
            selectinload(Order.returns),
        ).where(
            Order.order_number == order_number.upper(),
            Order.customer_id == customer.id,
        )
    )
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )

    return build_tracking_response(order)


def build_tracking_response(order: Order) -> OrderTrackingResponse:
    """Build the tracking response from order data."""
    # Build timeline
    timeline = build_timeline(
        order,
        list(order.shipments) if order.shipments else [],
        list(order.returns) if order.returns else [],
    )

    # Build shipments info
    shipments_info = []
    for shipment in (order.shipments or []):
        tracking_events = []
        if shipment.tracking_events:
            for event in shipment.tracking_events:
                tracking_events.append({
                    "status": event.status,
                    "message": get_shipment_status_message(event.status),
                    "location": event.location,
                    "remarks": event.remarks,
                    "timestamp": event.event_time.isoformat() if event.event_time else None,
                })

        shipments_info.append(ShipmentInfo(
            shipment_id=str(shipment.id),
            tracking_number=shipment.awb_number,
            courier_name=shipment.transporter.name if shipment.transporter else None,
            status=shipment.status,
            status_message=get_shipment_status_message(shipment.status),
            shipped_at=shipment.shipped_at,
            estimated_delivery=shipment.estimated_delivery_date,
            delivered_at=shipment.delivered_at,
            current_location=shipment.current_location,
            tracking_url=shipment.tracking_url,
            tracking_events=tracking_events,
        ))

    # Check for active return
    active_return = None
    for ret in (order.returns or []):
        if ret.status not in ["CLOSED", "CANCELLED", "REFUND_PROCESSED"]:
            active_return = {
                "rma_number": ret.rma_number,
                "status": ret.status,
                "requested_at": ret.requested_at.isoformat(),
                "refund_amount": float(ret.net_refund_amount),
            }
            break

    # Determine flags
    can_cancel = order.status in ["NEW", "PENDING_PAYMENT", "CONFIRMED"]
    can_return = order.status in ["DELIVERED", "PARTIALLY_DELIVERED"] and not active_return

    return OrderTrackingResponse(
        order_number=order.order_number,
        order_id=str(order.id),
        status=order.status,
        status_message=get_status_message(order.status),
        payment_status=order.payment_status,
        payment_method=order.payment_method,
        placed_at=order.created_at,
        confirmed_at=order.confirmed_at,
        shipped_at=order.shipped_at,
        delivered_at=order.delivered_at,
        cancelled_at=order.cancelled_at,
        subtotal=float(order.subtotal),
        tax_amount=float(order.tax_amount),
        shipping_amount=float(order.shipping_amount),
        discount_amount=float(order.discount_amount),
        total_amount=float(order.total_amount),
        amount_paid=float(order.amount_paid),
        shipping_address=order.shipping_address or {},
        items=[
            {
                "id": str(item.id),
                "product_id": str(item.product_id),
                "product_name": item.product_name,
                "sku": item.sku,
                "quantity": item.quantity,
                "unit_price": float(item.unit_price),
                "total_price": float(item.total_price),
            }
            for item in (order.items or [])
        ],
        timeline=[event.model_dump() for event in timeline],
        shipments=shipments_info,
        active_return=active_return,
        can_cancel=can_cancel,
        can_return=can_return,
    )
