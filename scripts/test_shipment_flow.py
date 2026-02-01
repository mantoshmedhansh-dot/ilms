#!/usr/bin/env python3
"""Test shipment creation and management flow."""

import asyncio
import sys
import logging
from decimal import Decimal
import uuid
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add project to path
sys.path.insert(0, '/Users/mantosh/Desktop/Consumer durable 2')

from app.database import async_session_factory
from app.services.order_service import OrderService
from app.services.shipment_service import ShipmentService
from app.models.order import Order, OrderItem, OrderStatus, PaymentMethod
from app.models.shipment import Shipment, ShipmentStatus
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload


async def test_shipment_flow():
    """Test creating and managing a shipment."""

    async with async_session_factory() as db:
        order_service = OrderService(db)
        shipment_service = ShipmentService(db)

        # Step 1: Find an allocated, paid order without shipment
        logger.info("Finding an allocated, paid order without shipment...")

        result = await db.execute(
            select(Order)
            .options(selectinload(Order.items).selectinload(OrderItem.product))
            .outerjoin(Shipment, Order.id == Shipment.order_id)
            .where(Order.status == "ALLOCATED")
            .where(Order.payment_status == "PAID")
            .where(Shipment.id.is_(None))
            .order_by(desc(Order.created_at))
            .limit(1)
        )
        order = result.scalar_one_or_none()

        if not order:
            # Try to find any allocated order
            result = await db.execute(
                select(Order)
                .options(selectinload(Order.items).selectinload(OrderItem.product))
                .outerjoin(Shipment, Order.id == Shipment.order_id)
                .where(Order.status.in_(["ALLOCATED", "CONFIRMED"]))
                .where(Shipment.id.is_(None))
                .order_by(desc(Order.created_at))
                .limit(1)
            )
            order = result.scalar_one_or_none()

        if not order:
            logger.warning("No suitable order found. Creating a new order...")
            # Create a test order
            from app.schemas.order import OrderCreate, OrderItemCreate, AddressInput
            from app.models.order import OrderSource
            from app.services.allocation_service import AllocationService
            from app.schemas.serviceability import OrderAllocationRequest

            phone = "9876543399"
            customer = await order_service.get_customer_by_phone(phone)
            if not customer:
                customer = await order_service.create_customer({
                    "first_name": "Shipment",
                    "last_name": "Test",
                    "phone": phone,
                    "email": "shipment.test@example.com",
                    "customer_type": "retail",
                    "is_active": True,
                })
                logger.info(f"Created test customer: {customer.id}")

            order_create = OrderCreate(
                customer_id=customer.id,
                source=OrderSource.WEBSITE,
                items=[
                    OrderItemCreate(
                        product_id=uuid.UUID('f54e3967-97c2-4e29-9971-f86934b2d548'),
                        quantity=1,
                        unit_price=Decimal('180.00'),
                    )
                ],
                shipping_address=AddressInput(
                    address_line1="789 Shipment Test Lane",
                    address_line2="",
                    city="Mumbai",
                    state="Maharashtra",
                    pincode="400001",
                    contact_name="Shipment Test",
                    contact_phone=phone,
                ),
                payment_method=PaymentMethod.COD,
            )

            order = await order_service.create_order(order_create)
            order.status = "CONFIRMED"
            await db.commit()

            # Allocate the order
            allocation_service = AllocationService(db)
            allocation_request = OrderAllocationRequest(
                order_id=order.id,
                customer_pincode="400001",
                items=[{"product_id": "f54e3967-97c2-4e29-9971-f86934b2d548", "quantity": 1}],
                payment_mode="COD",
                channel_code="D2C",
                order_value=float(order.total_amount),
            )
            allocation_result = await allocation_service.allocate_order(allocation_request)
            if allocation_result.is_allocated:
                order.status = "ALLOCATED"
                order.warehouse_id = allocation_result.warehouse_id
                order.allocated_at = datetime.utcnow()
                await db.commit()

            # Re-fetch order with items
            result = await db.execute(
                select(Order)
                .options(selectinload(Order.items).selectinload(OrderItem.product))
                .where(Order.id == order.id)
            )
            order = result.scalar_one()

        logger.info(f"Using order: {order.order_number}")
        logger.info(f"  ID: {order.id}")
        logger.info(f"  Status: {order.status}")
        logger.info(f"  Payment Status: {order.payment_status}")
        logger.info(f"  Warehouse ID: {order.warehouse_id}")

        # Step 2: Get transporter ID
        from sqlalchemy import text
        transporter_result = await db.execute(text(
            "SELECT id, name FROM transporters WHERE is_active = true LIMIT 1"
        ))
        transporter = transporter_result.fetchone()
        transporter_id = transporter[0] if transporter else None

        if not transporter_id:
            logger.error("No active transporter found!")
            return None

        logger.info(f"\nUsing transporter: {transporter[1]} (ID: {transporter_id})")

        # Step 3: Create shipment
        logger.info("\nCreating shipment from order...")

        shipment = await shipment_service.create_shipment_from_order(
            order=order,
            transporter_id=transporter_id,
        )

        logger.info(f"Shipment created:")
        logger.info(f"  Shipment Number: {shipment.shipment_number}")
        logger.info(f"  AWB Number: {shipment.awb_number}")
        logger.info(f"  Status: {shipment.status}")
        logger.info(f"  Payment Mode: {shipment.payment_mode}")
        logger.info(f"  COD Amount: {shipment.cod_amount}")
        logger.info(f"  Weight: {shipment.weight_kg} kg")
        logger.info(f"  Ship To: {shipment.ship_to_name}, {shipment.ship_to_city}")

        # Step 4: Pack shipment
        logger.info("\nPacking shipment...")
        shipment = await shipment_service.pack_shipment(
            shipment_id=shipment.id,
            packaging_type="BOX",
            no_of_boxes=1,
            weight_kg=1.5,
            length_cm=30,
            breadth_cm=20,
            height_cm=15,
            notes="Packed for dispatch"
        )
        logger.info(f"  Status after packing: {shipment.status}")

        # Step 5: Simulate dispatch by directly updating status
        logger.info("\nDispatching shipment (manual status update)...")
        shipment.status = "SHIPPED"
        shipment.shipped_at = datetime.utcnow()

        # Add tracking entry for dispatch
        from app.models.shipment import ShipmentTracking
        dispatch_tracking = ShipmentTracking(
            shipment_id=shipment.id,
            status="SHIPPED",
            remarks="Handed over to courier",
            source="MANUAL",
        )
        db.add(dispatch_tracking)

        # Update order status
        order.status = "SHIPPED"
        order.shipped_at = datetime.utcnow()

        await db.commit()
        await db.refresh(shipment)
        logger.info(f"  Status after dispatch: {shipment.status}")

        # Verify shipment in database
        result = await db.execute(
            select(Shipment)
            .options(selectinload(Shipment.tracking_history))
            .where(Shipment.id == shipment.id)
        )
        final_shipment = result.scalar_one()

        logger.info(f"\nFinal Shipment State:")
        logger.info(f"  Shipment Number: {final_shipment.shipment_number}")
        logger.info(f"  AWB: {final_shipment.awb_number}")
        logger.info(f"  Status: {final_shipment.status}")
        logger.info(f"  Tracking History: {len(final_shipment.tracking_history)} entries")

        for entry in final_shipment.tracking_history:
            logger.info(f"    - {entry.status}: {entry.remarks}")

        logger.info("\n✅ SHIPMENT FLOW TEST PASSED!")

        return shipment


if __name__ == "__main__":
    asyncio.run(test_shipment_flow())
