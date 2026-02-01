"""
Shipping API endpoints.

Handles Shiprocket integration:
- Order push to Shiprocket
- AWB generation
- Shipment tracking
- Courier serviceability
- Webhook for status updates
"""
import uuid
import hmac
import hashlib
import logging
from typing import Optional, List
from datetime import datetime, timezone
from pydantic import BaseModel, Field

from fastapi import APIRouter, HTTPException, status, Query, Depends, Request, Header
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from app.api.deps import DB, CurrentUser, require_permissions
from app.models.order import Order, OrderStatus
from app.config import settings
from app.services.shiprocket_service import (

    ShiprocketService,
    ShiprocketAPIError,
    push_order_to_shiprocket,
    auto_ship_order,
)
from app.core.module_decorators import require_module

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Shipping"])


# ==================== SCHEMAS ====================

class PushToShiprocketRequest(BaseModel):
    """Request to push order to Shiprocket."""
    order_id: str = Field(..., description="Order ID (UUID)")
    auto_assign_courier: bool = Field(False, description="Auto-assign best courier and generate AWB")
    courier_strategy: str = Field("BALANCED", description="CHEAPEST, FASTEST, BALANCED, BEST_RATING")


class PushToShiprocketResponse(BaseModel):
    """Response from pushing order to Shiprocket."""
    success: bool
    shiprocket_order_id: Optional[int] = None
    shipment_id: Optional[int] = None
    awb_code: Optional[str] = None
    courier_name: Optional[str] = None
    label_url: Optional[str] = None
    message: str = ""


class GenerateAWBRequest(BaseModel):
    """Request to generate AWB."""
    shipment_id: int = Field(..., description="Shiprocket shipment ID")
    courier_id: Optional[int] = Field(None, description="Specific courier ID (optional, auto-assigns if not provided)")


class TrackingResponse(BaseModel):
    """Tracking information response."""
    awb_code: str
    courier_name: str
    current_status: str
    shipment_status: str
    delivered_date: Optional[str] = None
    pickup_date: Optional[str] = None
    etd: Optional[str] = None
    activities: List[dict] = []


class ServiceabilityRequest(BaseModel):
    """Courier serviceability check request."""
    pickup_pincode: str
    delivery_pincode: str
    weight_kg: float = 0.5
    cod: bool = False
    order_value: float = 0


class CourierOption(BaseModel):
    """Available courier option."""
    courier_id: int
    courier_name: str
    rate: float
    estimated_days: int
    cod_available: bool
    etd: str
    performance_score: float


class ServiceabilityResponse(BaseModel):
    """Courier serviceability response."""
    serviceable: bool
    couriers: List[CourierOption] = []
    recommended: Optional[CourierOption] = None
    message: str = ""


# ==================== PUBLIC ENDPOINTS (Storefront) ====================

@router.get(
    "/track/{awb_code}",
    response_model=TrackingResponse,
    summary="Track shipment by AWB",
    description="Get real-time tracking information for a shipment. No authentication required."
)
@require_module("oms_fulfillment")
async def track_shipment(awb_code: str):
    """
    Track a shipment by AWB code.

    This is a public endpoint for customers to track their orders.
    """
    try:
        service = ShiprocketService()
        tracking = await service.track_shipment(awb_code)

        return TrackingResponse(
            awb_code=tracking.awb_code,
            courier_name=tracking.courier_name,
            current_status=tracking.current_status,
            shipment_status=tracking.shipment_status,
            delivered_date=tracking.delivered_date,
            pickup_date=tracking.pickup_date,
            etd=tracking.etd,
            activities=tracking.activities
        )
    except ShiprocketAPIError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Tracking error for {awb_code}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch tracking information")


@router.post(
    "/check-serviceability",
    response_model=ServiceabilityResponse,
    summary="Check courier serviceability",
    description="Check available couriers for a delivery route. No authentication required."
)
@require_module("oms_fulfillment")
async def check_serviceability(data: ServiceabilityRequest):
    """
    Check which couriers can deliver to a pincode.

    Use this at checkout to show delivery options and estimated costs.
    """
    try:
        service = ShiprocketService()

        couriers = await service.check_serviceability(
            pickup_pincode=data.pickup_pincode,
            delivery_pincode=data.delivery_pincode,
            weight=data.weight_kg,
            cod=data.cod,
            order_value=data.order_value
        )

        if not couriers:
            return ServiceabilityResponse(
                serviceable=False,
                couriers=[],
                message=f"No courier available for delivery to {data.delivery_pincode}"
            )

        # Get recommended courier
        recommended = await service.get_recommended_courier(
            pickup_pincode=data.pickup_pincode,
            delivery_pincode=data.delivery_pincode,
            weight=data.weight_kg,
            cod=data.cod,
            order_value=data.order_value,
            strategy="BALANCED"
        )

        courier_options = [
            CourierOption(
                courier_id=c.courier_id,
                courier_name=c.courier_name,
                rate=c.rate,
                estimated_days=c.estimated_days,
                cod_available=c.cod_available,
                etd=c.etd,
                performance_score=c.performance_score
            )
            for c in couriers
        ]

        recommended_option = None
        if recommended:
            recommended_option = CourierOption(
                courier_id=recommended.courier_id,
                courier_name=recommended.courier_name,
                rate=recommended.rate,
                estimated_days=recommended.estimated_days,
                cod_available=recommended.cod_available,
                etd=recommended.etd,
                performance_score=recommended.performance_score
            )

        return ServiceabilityResponse(
            serviceable=True,
            couriers=courier_options,
            recommended=recommended_option,
            message=f"{len(couriers)} couriers available"
        )

    except ShiprocketAPIError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Serviceability check error: {e}")
        raise HTTPException(status_code=500, detail="Failed to check serviceability")


# ==================== ADMIN ENDPOINTS ====================

@router.post(
    "/push-to-shiprocket",
    response_model=PushToShiprocketResponse,
    summary="Push order to Shiprocket",
    description="Create order in Shiprocket for fulfillment.",
    dependencies=[Depends(require_permissions("orders:update"))]
)
async def push_order_to_shiprocket_endpoint(
    data: PushToShiprocketRequest,
    db: DB,
    current_user: CurrentUser
):
    """
    Push an order to Shiprocket for fulfillment.

    This creates the order in Shiprocket. Optionally auto-assigns
    the best courier and generates AWB.

    Requires: orders:update permission
    """
    # Get order from database
    try:
        order_uuid = uuid.UUID(data.order_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid order ID format")

    query = (
        select(Order)
        .where(Order.id == order_uuid)
        .options(selectinload(Order.items))
    )
    result = await db.execute(query)
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Check if already pushed
    if order.shiprocket_order_id:
        return PushToShiprocketResponse(
            success=True,
            shiprocket_order_id=order.shiprocket_order_id,
            shipment_id=order.shiprocket_shipment_id,
            awb_code=order.awb_code,
            courier_name=order.courier_name,
            message="Order already pushed to Shiprocket"
        )

    # Build shipping address
    shipping_address = order.shipping_address or {}

    # Build items
    items = []
    for item in order.items:
        items.append({
            "name": item.name,
            "sku": item.sku or f"SKU-{item.id}",
            "quantity": item.quantity,
            "price": float(item.unit_price),
            "hsn": item.hsn_code or "",
            "tax": float(item.tax_amount or 0),
            "discount": float(item.discount_amount or 0)
        })

    # Get pickup pincode from warehouse
    pickup_pincode = ""
    if order.warehouse:
        pickup_pincode = order.warehouse.pincode or ""

    try:
        if data.auto_assign_courier and pickup_pincode:
            # Auto-ship with best courier
            result = await auto_ship_order(
                order_id=str(order.id),
                order_number=order.order_number,
                order_date=order.created_at or datetime.now(timezone.utc),
                customer_name=order.customer_name or "Customer",
                customer_phone=order.customer_phone or "",
                customer_email=order.customer_email or "",
                shipping_address=shipping_address,
                items=items,
                payment_method=order.payment_method or "PREPAID",
                subtotal=float(order.subtotal or 0),
                pickup_pincode=pickup_pincode,
                weight_kg=float(order.weight_kg or 0.5),
                courier_strategy=data.courier_strategy
            )
        else:
            # Just create order (manual courier assignment)
            result = await push_order_to_shiprocket(
                order_id=str(order.id),
                order_number=order.order_number,
                order_date=order.created_at or datetime.now(timezone.utc),
                customer_name=order.customer_name or "Customer",
                customer_phone=order.customer_phone or "",
                customer_email=order.customer_email or "",
                shipping_address=shipping_address,
                billing_address=order.billing_address,
                items=items,
                payment_method=order.payment_method or "PREPAID",
                subtotal=float(order.subtotal or 0),
                weight_kg=float(order.weight_kg or 0.5)
            )

        # Update order with Shiprocket IDs
        order.shiprocket_order_id = result.get("order_id")
        order.shiprocket_shipment_id = result.get("shipment_id")
        order.awb_code = result.get("awb_code")
        order.courier_name = result.get("courier_name")
        order.courier_id = result.get("courier_company_id")

        if result.get("awb_code"):
            order.status = OrderStatus.SHIPPED

        await db.commit()

        return PushToShiprocketResponse(
            success=True,
            shiprocket_order_id=result.get("order_id"),
            shipment_id=result.get("shipment_id"),
            awb_code=result.get("awb_code"),
            courier_name=result.get("courier_name"),
            label_url=result.get("label_url"),
            message="Order pushed to Shiprocket successfully"
        )

    except ShiprocketAPIError as e:
        logger.error(f"Shiprocket API error: {e}")
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Error pushing order to Shiprocket: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/generate-awb",
    summary="Generate AWB for shipment",
    description="Generate AWB (airway bill) for an existing Shiprocket shipment.",
    dependencies=[Depends(require_permissions("orders:update"))]
)
async def generate_awb(data: GenerateAWBRequest, db: DB, current_user: CurrentUser):
    """
    Generate AWB for a shipment.

    The shipment must already exist in Shiprocket.
    Optionally specify a courier ID, otherwise auto-assigns best courier.

    Requires: orders:update permission
    """
    try:
        service = ShiprocketService()
        result = await service.generate_awb(data.shipment_id, data.courier_id)

        awb_data = result.get("response", {}).get("data", {})

        return {
            "success": True,
            "awb_code": awb_data.get("awb_code"),
            "courier_company_id": awb_data.get("courier_company_id"),
            "courier_name": awb_data.get("courier_name"),
            "applied_weight": awb_data.get("applied_weight"),
            "routing_code": awb_data.get("routing_code"),
        }

    except ShiprocketAPIError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Error generating AWB: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/request-pickup/{shipment_id}",
    summary="Request pickup for shipment",
    description="Request courier pickup for a shipment with AWB.",
    dependencies=[Depends(require_permissions("orders:update"))]
)
async def request_pickup(shipment_id: int, current_user: CurrentUser):
    """
    Request pickup for a shipment.

    Call this after AWB is generated to schedule pickup.

    Requires: orders:update permission
    """
    try:
        service = ShiprocketService()
        result = await service.request_pickup(shipment_id)

        return {
            "success": True,
            "pickup_scheduled_date": result.get("response", {}).get("pickup_scheduled_date"),
            "pickup_token_number": result.get("response", {}).get("pickup_token_number"),
        }

    except ShiprocketAPIError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Error requesting pickup: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/label/{shipment_id}",
    summary="Get shipping label",
    description="Get shipping label PDF URL for a shipment.",
    dependencies=[Depends(require_permissions("orders:view"))]
)
async def get_shipping_label(shipment_id: int, current_user: CurrentUser):
    """
    Get shipping label PDF URL.

    Requires: orders:view permission
    """
    try:
        service = ShiprocketService()
        result = await service.print_label([shipment_id])

        return {
            "success": True,
            "label_url": result.get("label_url"),
        }

    except ShiprocketAPIError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Error getting label: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/pickup-locations",
    summary="Get pickup locations",
    description="Get all configured pickup locations in Shiprocket.",
    dependencies=[Depends(require_permissions("settings:view"))]
)
async def get_pickup_locations(current_user: CurrentUser):
    """
    Get all pickup locations configured in Shiprocket.

    Requires: settings:view permission
    """
    try:
        service = ShiprocketService()
        locations = await service.get_pickup_locations()

        return {
            "success": True,
            "locations": locations
        }

    except ShiprocketAPIError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        logger.error(f"Error getting pickup locations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== WEBHOOK HANDLER ====================

@router.post(
    "/webhook/shiprocket",
    summary="Shiprocket webhook handler",
    description="Receives status updates from Shiprocket.",
    include_in_schema=False  # Hide from docs
)
@require_module("oms_fulfillment")
async def shiprocket_webhook(
    request: Request,
    db: DB,
    x_shiprocket_signature: Optional[str] = Header(None)
):
    """
    Handle Shiprocket webhook events.

    Shiprocket sends webhooks for:
    - Shipment status updates
    - Pickup status
    - Delivery confirmation
    - RTO updates
    - NDR updates

    Configure webhook URL in Shiprocket dashboard:
    https://your-domain.com/api/v1/shipping/webhook/shiprocket
    """
    body = await request.body()

    # Verify webhook signature if secret is configured
    if settings.SHIPROCKET_WEBHOOK_SECRET:
        if not x_shiprocket_signature:
            logger.warning("Shiprocket webhook missing signature")
            raise HTTPException(status_code=401, detail="Missing webhook signature")

        expected_signature = hmac.new(
            settings.SHIPROCKET_WEBHOOK_SECRET.encode(),
            body,
            hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(expected_signature, x_shiprocket_signature):
            logger.warning("Shiprocket webhook signature mismatch")
            raise HTTPException(status_code=401, detail="Invalid webhook signature")

    try:
        payload = await request.json()
    except Exception:
        logger.error("Invalid JSON in Shiprocket webhook")
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    # Extract event data
    event = payload.get("event") or payload.get("status")
    awb = payload.get("awb") or payload.get("awb_code")
    order_id = payload.get("order_id")  # Shiprocket order ID
    channel_order_id = payload.get("channel_order_id")  # Our order number
    current_status = payload.get("current_status") or payload.get("status")
    current_status_id = payload.get("current_status_id")
    courier_name = payload.get("courier_name")
    etd = payload.get("etd")
    scans = payload.get("scans", [])

    logger.info(f"Shiprocket webhook: AWB={awb}, Status={current_status}, Event={event}")

    # Find order by AWB or channel_order_id
    order = None

    if awb:
        query = select(Order).where(Order.awb_code == awb)
        result = await db.execute(query)
        order = result.scalar_one_or_none()

    if not order and channel_order_id:
        query = select(Order).where(Order.order_number == channel_order_id)
        result = await db.execute(query)
        order = result.scalar_one_or_none()

    if not order:
        logger.warning(f"Order not found for webhook: AWB={awb}, channel_order_id={channel_order_id}")
        # Still return 200 to acknowledge receipt
        return {"success": True, "message": "Order not found, webhook acknowledged"}

    # Map Shiprocket status to our order status
    status_mapping = {
        # Shiprocket status_id -> Our OrderStatus
        1: OrderStatus.CONFIRMED,  # AWB Assigned
        2: OrderStatus.CONFIRMED,  # Label Generated
        3: OrderStatus.CONFIRMED,  # Pickup Scheduled
        4: OrderStatus.CONFIRMED,  # Pickup Queued
        5: OrderStatus.CONFIRMED,  # Manifest Generated
        6: OrderStatus.SHIPPED,    # Shipped - Picked Up
        7: OrderStatus.SHIPPED,    # In Transit
        8: OrderStatus.SHIPPED,    # Reached Destination Hub
        9: OrderStatus.SHIPPED,    # Out For Delivery
        10: OrderStatus.DELIVERED, # Delivered
        11: OrderStatus.CANCELLED, # Canceled
        12: OrderStatus.SHIPPED,   # RTO Initiated
        13: OrderStatus.SHIPPED,   # RTO In-Transit
        14: OrderStatus.RETURNED,  # RTO Delivered
        15: OrderStatus.SHIPPED,   # Lost
        16: OrderStatus.SHIPPED,   # Damaged
        17: OrderStatus.SHIPPED,   # Shipment Delayed
        18: OrderStatus.SHIPPED,   # Contact Customer Care
        19: OrderStatus.SHIPPED,   # Shipment Held
        20: OrderStatus.SHIPPED,   # Undelivered
        21: OrderStatus.SHIPPED,   # RTO Acknowledged
        22: OrderStatus.SHIPPED,   # Pickup Exception
        23: OrderStatus.SHIPPED,   # Pickup Rescheduled
        24: OrderStatus.SHIPPED,   # Cancellation Requested
        25: OrderStatus.SHIPPED,   # Out For Pickup
        26: OrderStatus.SHIPPED,   # RTO NDR
        38: OrderStatus.SHIPPED,   # Reached At Destination Hub
        39: OrderStatus.SHIPPED,   # Misrouted
        40: OrderStatus.SHIPPED,   # RTO OFD
        41: OrderStatus.SHIPPED,   # Disposal
        42: OrderStatus.SHIPPED,   # Self Fulfilled
    }

    # Update order status
    new_status = status_mapping.get(current_status_id)
    if new_status:
        order.status = new_status

    # Update tracking info
    order.tracking_status = current_status
    order.tracking_status_id = current_status_id
    order.last_tracking_update = datetime.now(timezone.utc)

    if courier_name:
        order.courier_name = courier_name

    if etd:
        order.estimated_delivery = etd

    # Update timestamps based on status
    if current_status_id == 6:  # Picked Up
        order.shipped_at = datetime.now(timezone.utc)
    elif current_status_id == 10:  # Delivered
        order.delivered_at = datetime.now(timezone.utc)

    # Store latest scan/activity
    if scans:
        latest_scan = scans[0] if isinstance(scans, list) else scans
        order.last_tracking_location = latest_scan.get("location", "")
        order.last_tracking_activity = latest_scan.get("activity", current_status)

    await db.commit()

    logger.info(f"Order {order.order_number} updated: Status={new_status}, Tracking={current_status}")

    return {
        "success": True,
        "order_number": order.order_number,
        "new_status": str(new_status) if new_status else None,
        "tracking_status": current_status
    }


# ==================== BULK OPERATIONS ====================

@router.post(
    "/sync-tracking",
    summary="Sync tracking for all shipped orders",
    description="Fetch latest tracking for all orders with AWB but not delivered.",
    dependencies=[Depends(require_permissions("orders:update"))]
)
async def sync_all_tracking(db: DB, current_user: CurrentUser):
    """
    Sync tracking status for all shipped orders.

    This fetches the latest tracking info from Shiprocket
    for all orders that have an AWB but are not yet delivered.

    Requires: orders:update permission
    """
    # Get orders with AWB that are not delivered
    query = (
        select(Order)
        .where(
            Order.awb_code.isnot(None),
            Order.status.in_([
                OrderStatus.CONFIRMED,
                OrderStatus.PROCESSING,
                OrderStatus.ALLOCATED,
                OrderStatus.PACKED,
                OrderStatus.SHIPPED,
            ])
        )
    )
    result = await db.execute(query)
    orders = result.scalars().all()

    if not orders:
        return {"success": True, "message": "No orders to sync", "updated": 0}

    service = ShiprocketService()
    updated_count = 0
    errors = []

    for order in orders:
        try:
            tracking = await service.track_shipment(order.awb_code)

            # Update order
            order.tracking_status = tracking.current_status
            order.tracking_status_id = tracking.current_status_id

            if tracking.delivered_date:
                order.delivered_at = datetime.fromisoformat(tracking.delivered_date.replace("Z", "+00:00"))
                order.status = OrderStatus.DELIVERED

            if tracking.pickup_date:
                order.shipped_at = datetime.fromisoformat(tracking.pickup_date.replace("Z", "+00:00"))

            if tracking.activities:
                latest = tracking.activities[0]
                order.last_tracking_location = latest.get("location", "")
                order.last_tracking_activity = latest.get("activity", "")

            order.last_tracking_update = datetime.now(timezone.utc)
            updated_count += 1

        except Exception as e:
            errors.append({"order": order.order_number, "error": str(e)})
            logger.error(f"Error syncing tracking for {order.order_number}: {e}")

    await db.commit()

    return {
        "success": True,
        "total_orders": len(orders),
        "updated": updated_count,
        "errors": errors
    }
