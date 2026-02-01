from typing import Optional, List
import uuid
from math import ceil
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, HTTPException, status, Query, Depends
from sqlalchemy import select

from app.api.deps import DB, CurrentUser, Permissions, require_permissions
from app.models.order import Order, OrderItem, OrderStatus, PaymentStatus, PaymentMethod, OrderSource
from app.schemas.order import (
    OrderCreate,
    OrderUpdate,
    OrderStatusUpdate,
    OrderResponse,
    OrderDetailResponse,
    OrderListResponse,
    OrderItemResponse,
    PaymentCreate,
    PaymentResponse,
    StatusHistoryResponse,
    InvoiceResponse,
    OrderSummary,
    D2CAddressInfo,
    D2COrderItem,
    D2COrderCreate,
    D2COrderResponse,
)
from app.schemas.customer import CustomerBrief
from app.services.order_service import OrderService
from app.services.allocation_service import AllocationService
from app.schemas.serviceability import OrderAllocationRequest
from app.core.module_decorators import require_module


router = APIRouter(tags=["Orders"])


def _build_order_response(order) -> OrderResponse:
    """Build OrderResponse from Order model."""
    # Handle orders without customer
    customer_brief = None
    if order.customer:
        customer_brief = CustomerBrief(
            id=order.customer.id,
            customer_code=order.customer.customer_code,
            full_name=order.customer.full_name,
            phone=order.customer.phone,
            email=order.customer.email,
        )

    return OrderResponse(
        id=order.id,
        order_number=order.order_number,
        customer=customer_brief,
        status=order.status,
        source=order.source,
        subtotal=order.subtotal,
        tax_amount=order.tax_amount,
        discount_amount=order.discount_amount,
        shipping_amount=order.shipping_amount,
        total_amount=order.total_amount,
        discount_code=order.discount_code,
        payment_method=order.payment_method,
        payment_status=order.payment_status,
        amount_paid=order.amount_paid,
        balance_due=order.balance_due,
        shipping_address=order.shipping_address,
        billing_address=order.billing_address,
        expected_delivery_date=order.expected_delivery_date,
        delivered_at=order.delivered_at,
        customer_notes=order.customer_notes,
        item_count=order.item_count,
        created_at=order.created_at,
        updated_at=order.updated_at,
        confirmed_at=order.confirmed_at,
    )


def _build_order_detail_response(order) -> OrderDetailResponse:
    """Build OrderDetailResponse from Order model."""
    # Handle orders without customer
    customer_brief = None
    if order.customer:
        customer_brief = CustomerBrief(
            id=order.customer.id,
            customer_code=order.customer.customer_code,
            full_name=order.customer.full_name,
            phone=order.customer.phone,
            email=order.customer.email,
        )

    return OrderDetailResponse(
        id=order.id,
        order_number=order.order_number,
        customer=customer_brief,
        status=order.status,
        source=order.source,
        subtotal=order.subtotal,
        tax_amount=order.tax_amount,
        discount_amount=order.discount_amount,
        shipping_amount=order.shipping_amount,
        total_amount=order.total_amount,
        discount_code=order.discount_code,
        payment_method=order.payment_method,
        payment_status=order.payment_status,
        amount_paid=order.amount_paid,
        balance_due=order.balance_due,
        shipping_address=order.shipping_address,
        billing_address=order.billing_address,
        expected_delivery_date=order.expected_delivery_date,
        delivered_at=order.delivered_at,
        customer_notes=order.customer_notes,
        internal_notes=order.internal_notes,
        item_count=order.item_count,
        created_at=order.created_at,
        updated_at=order.updated_at,
        confirmed_at=order.confirmed_at,
        items=[OrderItemResponse.model_validate(item) for item in order.items],
        status_history=[StatusHistoryResponse.model_validate(h) for h in order.status_history],
        payments=[PaymentResponse.model_validate(p) for p in order.payments],
        invoice=InvoiceResponse.model_validate(order.invoice) if order.invoice else None,
    )


@router.get(
    "",
    response_model=OrderListResponse,
    dependencies=[Depends(require_permissions("orders:view"))]
)
async def list_orders(
    db: DB,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    customer_id: Optional[uuid.UUID] = Query(None),
    status: Optional[OrderStatus] = Query(None),
    payment_status: Optional[PaymentStatus] = Query(None),
    source: Optional[OrderSource] = Query(None),
    region_id: Optional[uuid.UUID] = Query(None),
    search: Optional[str] = Query(None, description="Search by order number"),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc", regex="^(asc|desc)$"),
):
    """
    Get paginated list of orders.
    Requires: orders:view permission
    """
    service = OrderService(db)
    skip = (page - 1) * size

    orders, total = await service.get_orders(
        customer_id=customer_id,
        status=status,
        payment_status=payment_status,
        source=source,
        region_id=region_id,
        search=search,
        date_from=date_from,
        date_to=date_to,
        skip=skip,
        limit=size,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    return OrderListResponse(
        items=[_build_order_response(o) for o in orders],
        total=total,
        page=page,
        size=size,
        pages=ceil(total / size) if total > 0 else 1,
    )


@router.get(
    "/stats",
    response_model=OrderSummary,
    dependencies=[Depends(require_permissions("orders:view"))]
)
async def get_order_stats(
    db: DB,
    region_id: Optional[uuid.UUID] = Query(None),
):
    """Get order statistics."""
    service = OrderService(db)
    stats = await service.get_order_stats(region_id=region_id)
    return OrderSummary(**stats)


@router.get(
    "/recent-activity",
    dependencies=[Depends(require_permissions("orders:view"))]
)
async def get_recent_activity(
    db: DB,
    limit: int = Query(10, ge=1, le=50),
):
    """Get recent activity for dashboard."""
    service = OrderService(db)
    activities = await service.get_recent_activity(limit=limit)
    return {"items": activities}


@router.get(
    "/{order_id}",
    response_model=OrderDetailResponse,
    dependencies=[Depends(require_permissions("orders:view"))]
)
async def get_order(
    order_id: uuid.UUID,
    db: DB,
):
    """Get order details by ID."""
    service = OrderService(db)
    order = await service.get_order_by_id(order_id, include_all=True)

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )

    return _build_order_detail_response(order)


@router.get(
    "/number/{order_number}",
    response_model=OrderDetailResponse,
    dependencies=[Depends(require_permissions("orders:view"))]
)
async def get_order_by_number(
    order_number: str,
    db: DB,
):
    """Get order details by order number."""
    service = OrderService(db)
    order = await service.get_order_by_number(order_number)

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )

    return _build_order_detail_response(order)


@router.post(
    "",
    response_model=OrderDetailResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions("orders:create"))]
)
async def create_order(
    data: OrderCreate,
    db: DB,
    current_user: CurrentUser,
):
    """
    Create a new order.
    Requires: orders:create permission
    """
    service = OrderService(db)

    try:
        order = await service.create_order(data, created_by=current_user.id)
        return _build_order_detail_response(order)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.put(
    "/{order_id}/status",
    response_model=OrderDetailResponse,
    dependencies=[Depends(require_permissions("orders:update"))]
)
async def update_order_status(
    order_id: uuid.UUID,
    data: OrderStatusUpdate,
    db: DB,
    current_user: CurrentUser,
):
    """
    Update order status.
    Requires: orders:update permission
    """
    service = OrderService(db)

    order = await service.update_order_status(
        order_id,
        data.status,
        changed_by=current_user.id,
        notes=data.notes,
    )

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )

    return _build_order_detail_response(order)


@router.post(
    "/{order_id}/approve",
    response_model=OrderDetailResponse,
    dependencies=[Depends(require_permissions("orders:approve"))]
)
async def approve_order(
    order_id: uuid.UUID,
    db: DB,
    current_user: CurrentUser,
):
    """
    Approve/confirm an order and trigger warehouse allocation.

    Flow:
    1. Validate order is in NEW status
    2. Update status to CONFIRMED
    3. Run AllocationService to select warehouse and transporter
    4. Update order with allocation (warehouse_id, status=ALLOCATED)

    Requires: orders:approve permission
    """
    service = OrderService(db)

    order = await service.get_order_by_id(order_id, include_all=True)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )

    if order.status != OrderStatus.NEW:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only new orders can be approved"
        )

    # Step 1: Update status to CONFIRMED
    order = await service.update_order_status(
        order_id,
        OrderStatus.CONFIRMED,
        changed_by=current_user.id,
        notes="Order approved",
    )

    # Step 2: Trigger warehouse allocation
    try:
        allocation_service = AllocationService(db)

        # Get pincode from shipping address
        pincode = order.shipping_address.get("pincode") if order.shipping_address else None

        if pincode:
            # Build allocation request
            allocation_request = OrderAllocationRequest(
                order_id=order.id,
                customer_pincode=pincode,
                items=[
                    {
                        "product_id": str(item.product_id),
                        "quantity": item.quantity,
                    }
                    for item in order.items
                ],
                payment_mode="COD" if order.payment_method == PaymentMethod.COD.value else "PREPAID",
                channel_code="D2C",  # Default to D2C for website orders
                order_value=float(order.total_amount),
            )

            # Run allocation
            allocation_decision = await allocation_service.allocate_order(allocation_request)

            if allocation_decision.is_allocated:
                # Update order with warehouse
                order.warehouse_id = allocation_decision.warehouse_id
                order.status = OrderStatus.ALLOCATED
                order.allocated_at = datetime.now(timezone.utc)

                # Add status history
                from app.models.order import OrderStatusHistory
                status_history = OrderStatusHistory(
                    order_id=order.id,
                    from_status=OrderStatus.CONFIRMED,
                    to_status=OrderStatus.ALLOCATED,
                    changed_by=current_user.id,
                    notes=f"Allocated to warehouse: {allocation_decision.warehouse_code}. "
                          f"Transporter: {allocation_decision.recommended_transporter_code or 'TBD'}",
                )
                db.add(status_history)
                await db.commit()

                # Refresh order to get latest state
                order = await service.get_order_by_id(order_id, include_all=True)
            else:
                # Allocation failed - log but don't fail the order approval
                from app.models.order import OrderStatusHistory
                status_history = OrderStatusHistory(
                    order_id=order.id,
                    from_status=OrderStatus.CONFIRMED,
                    to_status=OrderStatus.CONFIRMED,
                    changed_by=current_user.id,
                    notes=f"Allocation pending: {allocation_decision.failure_reason or 'No warehouse available'}",
                )
                db.add(status_history)
                await db.commit()

    except Exception as e:
        # Log allocation error but don't fail the order approval
        import logging
        logging.error(f"Allocation failed for order {order_id}: {str(e)}")

    return _build_order_detail_response(order)


@router.post(
    "/{order_id}/cancel",
    response_model=OrderDetailResponse,
    dependencies=[Depends(require_permissions("orders:cancel"))]
)
async def cancel_order(
    order_id: uuid.UUID,
    notes: Optional[str] = None,
    db: DB = None,
    current_user: CurrentUser = None,
):
    """
    Cancel an order.
    Requires: orders:cancel permission
    """
    service = OrderService(db)

    order = await service.get_order_by_id(order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )

    if order.status in [OrderStatus.DELIVERED, OrderStatus.CANCELLED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot cancel this order"
        )

    order = await service.update_order_status(
        order_id,
        OrderStatus.CANCELLED,
        changed_by=current_user.id,
        notes=notes or "Order cancelled",
    )

    return _build_order_detail_response(order)


@router.post(
    "/{order_id}/payments",
    response_model=PaymentResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions("orders:update"))]
)
async def add_payment(
    order_id: uuid.UUID,
    data: PaymentCreate,
    db: DB,
    current_user: CurrentUser,
):
    """
    Add a payment to an order.
    Requires: orders:update permission
    """
    service = OrderService(db)

    try:
        payment = await service.add_payment(
            order_id,
            amount=data.amount,
            method=data.method,
            transaction_id=data.transaction_id,
            gateway=data.gateway,
            reference_number=data.reference_number,
            notes=data.notes,
        )
        return PaymentResponse.model_validate(payment)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post(
    "/{order_id}/invoice",
    response_model=InvoiceResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions("orders:update"))]
)
async def generate_invoice(
    order_id: uuid.UUID,
    db: DB,
    current_user: CurrentUser,
):
    """
    Generate invoice for an order.
    Requires: orders:update permission
    """
    service = OrderService(db)

    try:
        invoice = await service.generate_invoice(order_id)
        return InvoiceResponse.model_validate(invoice)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# ==================== D2C PUBLIC ENDPOINTS ====================

@router.post(
    "/d2c",
    response_model=D2COrderResponse,
    status_code=status.HTTP_201_CREATED,
)
@require_module("oms_fulfillment")
async def create_d2c_order(
    data: D2COrderCreate,
    db: DB,
):
    """
    Create a D2C order from the website.
    No authentication required - creates guest customer if needed.
    """
    service = OrderService(db)

    try:
        # Find or create customer by phone (using flat fields from frontend)
        customer = await service.get_customer_by_phone(data.customer_phone)

        if not customer:
            # Parse name into first/last
            name_parts = data.customer_name.strip().split(" ", 1)
            first_name = name_parts[0]
            last_name = name_parts[1] if len(name_parts) > 1 else ""

            customer = await service.create_customer({
                "first_name": first_name,
                "last_name": last_name,
                "phone": data.customer_phone,
                "email": data.customer_email,
                "customer_type": "retail",
                "is_active": True,
            })

        # Map payment method (frontend sends RAZORPAY or COD)
        payment_method_map = {
            "cod": PaymentMethod.COD,
            "razorpay": PaymentMethod.UPI,  # Razorpay handles multiple methods
            "upi": PaymentMethod.UPI,
            "card": PaymentMethod.CARD,
            "netbanking": PaymentMethod.NET_BANKING,
        }
        payment_method = payment_method_map.get(data.payment_method.lower(), PaymentMethod.COD)

        # Build shipping address dict (using field names from frontend)
        shipping_addr = {
            "contact_name": data.shipping_address.full_name,
            "contact_phone": data.shipping_address.phone,
            "address_line1": data.shipping_address.address_line1,
            "address_line2": data.shipping_address.address_line2 or "",
            "city": data.shipping_address.city,
            "state": data.shipping_address.state,
            "pincode": data.shipping_address.pincode,
            "landmark": "",  # Not sent by frontend
            "country": data.shipping_address.country,
        }

        # No separate billing address from frontend - use shipping address
        billing_addr = None

        # Create order using service
        from app.schemas.order import OrderItemCreate, AddressInput

        order_items = [
            OrderItemCreate(
                product_id=item.product_id,
                quantity=item.quantity,
                unit_price=item.unit_price,
            )
            for item in data.items
        ]

        order_create = OrderCreate(
            customer_id=customer.id,
            source=OrderSource.WEBSITE,
            items=order_items,
            shipping_address=AddressInput(
                address_line1=shipping_addr["address_line1"],
                address_line2=shipping_addr["address_line2"],
                city=shipping_addr["city"],
                state=shipping_addr["state"],
                pincode=shipping_addr["pincode"],
                contact_name=shipping_addr["contact_name"],
                contact_phone=shipping_addr["contact_phone"],
                landmark=shipping_addr["landmark"],
            ),
            billing_address=AddressInput(
                address_line1=billing_addr["address_line1"] if billing_addr else shipping_addr["address_line1"],
                address_line2=billing_addr["address_line2"] if billing_addr else shipping_addr["address_line2"],
                city=billing_addr["city"] if billing_addr else shipping_addr["city"],
                state=billing_addr["state"] if billing_addr else shipping_addr["state"],
                pincode=billing_addr["pincode"] if billing_addr else shipping_addr["pincode"],
                contact_name=billing_addr["contact_name"] if billing_addr else shipping_addr["contact_name"],
                contact_phone=billing_addr["contact_phone"] if billing_addr else shipping_addr["contact_phone"],
            ) if billing_addr else None,
            payment_method=payment_method,
        )

        order = await service.create_order(order_create)

        # Store order_id and order_number immediately to avoid lazy loading issues
        order_id = order.id
        order_number = order.order_number
        order_total = order.total_amount

        # Handle partner attribution if partner_code provided
        if data.partner_code:
            try:
                from app.services.partner_service import PartnerService
                partner_service = PartnerService(db)
                await partner_service.create_partner_order(
                    partner_code=data.partner_code,
                    order_id=order_id,
                    order_amount=float(order_total),
                )
            except Exception as partner_error:
                # Log but don't fail order - partner attribution is optional
                import logging
                logging.warning(f"Failed to attribute order {order_id} to partner {data.partner_code}: {partner_error}")

        # Auto-confirm and allocate COD orders
        if payment_method == PaymentMethod.COD:
            try:
                # Update status to CONFIRMED - use string values for VARCHAR columns
                from app.models.order import OrderStatusHistory
                new_status = OrderStatus.NEW.value if hasattr(OrderStatus.NEW, 'value') else "NEW"
                confirmed_status = OrderStatus.CONFIRMED.value if hasattr(OrderStatus.CONFIRMED, 'value') else "CONFIRMED"
                allocated_status = OrderStatus.ALLOCATED.value if hasattr(OrderStatus.ALLOCATED, 'value') else "ALLOCATED"

                order.status = confirmed_status
                order.confirmed_at = datetime.now(timezone.utc)

                status_history = OrderStatusHistory(
                    order_id=order_id,  # Use stored value
                    from_status=new_status,
                    to_status=confirmed_status,
                    changed_by=None,  # System auto-confirm
                    notes="COD order auto-confirmed",
                )
                db.add(status_history)
                await db.commit()

                # Refresh order after commit to prevent lazy loading errors
                await db.refresh(order)

                # Trigger warehouse allocation
                allocation_service = AllocationService(db)
                allocation_request = OrderAllocationRequest(
                    order_id=order_id,  # Use stored value to avoid lazy loading
                    customer_pincode=data.shipping_address.pincode,
                    items=[
                        {
                            "product_id": str(item.product_id),
                            "quantity": item.quantity,
                        }
                        for item in data.items
                    ],
                    payment_mode="COD",
                    channel_code="D2C",
                    order_value=float(data.total_amount),
                )

                import logging
                logger = logging.getLogger(__name__)
                logger.info(f"D2C COD order {order_id}: Starting allocation for pincode {data.shipping_address.pincode}")

                allocation_decision = await allocation_service.allocate_order(allocation_request)

                logger.info(f"D2C COD order {order_id}: Allocation result - is_allocated={allocation_decision.is_allocated}, warehouse={allocation_decision.warehouse_code if allocation_decision.is_allocated else 'N/A'}, failure_reason={allocation_decision.failure_reason if not allocation_decision.is_allocated else 'N/A'}")

                # DEBUG: Store failure reason for response
                allocation_failure_reason = allocation_decision.failure_reason if not allocation_decision.is_allocated else None

                if allocation_decision.is_allocated:
                    # Refresh order after allocation service commits
                    await db.refresh(order)

                    order.warehouse_id = allocation_decision.warehouse_id
                    order.status = allocated_status
                    order.allocated_at = datetime.now(timezone.utc)

                    status_history = OrderStatusHistory(
                        order_id=order_id,  # Use stored value to avoid lazy loading
                        from_status=confirmed_status,
                        to_status=allocated_status,
                        changed_by=None,
                        notes=f"Auto-allocated to warehouse: {allocation_decision.warehouse_code}",
                    )
                    db.add(status_history)
                    await db.commit()

                    # Auto-create shipment for allocated order
                    try:
                        from app.services.shipment_service import ShipmentService
                        from sqlalchemy.orm import selectinload

                        shipment_service = ShipmentService(db)
                        # Fetch order with eager-loaded items and products for weight calculation
                        order_query = (
                            select(Order)
                            .options(
                                selectinload(Order.items).selectinload(OrderItem.product)
                            )
                            .where(Order.id == order_id)  # Use stored value
                        )
                        order_result = await db.execute(order_query)
                        order_with_items = order_result.scalar_one()

                        shipment = await shipment_service.create_shipment_from_order(
                            order=order_with_items,
                            transporter_id=allocation_decision.recommended_transporter_id,
                        )
                        import logging
                        logging.info(f"Auto-created shipment {shipment.shipment_number} for order {order.order_number}")
                    except Exception as ship_error:
                        import logging
                        logging.warning(f"Auto-shipment creation failed for order {order.id}: {str(ship_error)}")
                        # Don't fail order if shipment creation fails

            except Exception as alloc_error:
                # Log but don't fail order creation - rollback to clean state
                import logging
                import traceback

                logging.error(f"Auto-allocation failed for D2C order {order_id}: {str(alloc_error)}")
                logging.error(f"Allocation exception traceback: {traceback.format_exc()}")
                await db.rollback()
                # Store exception for debug response
                allocation_failure_reason = f"EXCEPTION: {str(alloc_error)}"

        # Refresh order to get latest status
        await db.refresh(order)

        # Get allocation failure reason if it was set
        failure_reason = allocation_failure_reason if 'allocation_failure_reason' in dir() else None

        return D2COrderResponse(
            id=order.id,
            order_number=order.order_number,
            total_amount=order.total_amount,
            status=order.status,
            allocation_failure_reason=failure_reason,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create order: {str(e)}"
        )


@router.get(
    "/track/{order_number}",
    response_model=OrderResponse,
)
@require_module("oms_fulfillment")
async def track_order_public(
    order_number: str,
    phone: str = Query(..., description="Customer phone for verification"),
    db: DB = None,
):
    """
    Public order tracking endpoint.
    Requires order number and customer phone for verification.
    """
    service = OrderService(db)

    order = await service.get_order_by_number(order_number)

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )

    # Verify customer phone
    if order.customer:
        if order.customer.phone != phone:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Phone number doesn't match order"
            )
    else:
        # Check shipping address phone
        shipping_phone = order.shipping_address.get("contact_phone", "")
        if shipping_phone != phone:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Phone number doesn't match order"
            )

    return _build_order_response(order)
