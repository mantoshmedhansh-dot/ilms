#!/usr/bin/env python3
"""Test D2C order creation with auto allocation."""

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
from app.services.allocation_service import AllocationService
from app.schemas.order import OrderCreate, OrderItemCreate, AddressInput
from app.schemas.serviceability import OrderAllocationRequest
from app.models.order import OrderSource, PaymentMethod, OrderStatus, OrderStatusHistory


async def test_d2c_order():
    """Test creating a D2C COD order with auto allocation."""

    async with async_session_factory() as db:
        service = OrderService(db)

        # Step 1: Find or create customer by phone
        phone = "9876543211"  # Unique phone for testing
        customer = await service.get_customer_by_phone(phone)

        if not customer:
            logger.info("Creating new customer...")
            customer = await service.create_customer({
                "first_name": "Test",
                "last_name": "Customer",
                "phone": phone,
                "email": "test@example.com",
                "customer_type": "retail",
                "is_active": True,
            })
            logger.info(f"Created customer: {customer.id}")
        else:
            logger.info(f"Found existing customer: {customer.id}")

        # Step 2: Create order
        logger.info("Creating D2C COD order...")

        order_create = OrderCreate(
            customer_id=customer.id,
            source=OrderSource.WEBSITE,
            items=[
                OrderItemCreate(
                    product_id=uuid.UUID('f54e3967-97c2-4e29-9971-f86934b2d548'),
                    quantity=2,
                    unit_price=Decimal('180.00'),
                )
            ],
            shipping_address=AddressInput(
                address_line1="123 Test Street",
                address_line2="Near Test Landmark",
                city="Mumbai",
                state="Maharashtra",
                pincode="400001",  # Serviceable pincode
                contact_name="Test Customer",
                contact_phone=phone,
            ),
            payment_method=PaymentMethod.COD,
        )

        order = await service.create_order(order_create)
        order_id = order.id
        order_number = order.order_number

        logger.info(f"Order created: {order_number} (ID: {order_id})")
        logger.info(f"  Status: {order.status}")
        logger.info(f"  Payment Status: {order.payment_status}")
        logger.info(f"  Total Amount: {order.total_amount}")

        # Step 3: Auto-confirm COD order
        logger.info("Auto-confirming COD order...")

        new_status = "NEW"
        confirmed_status = "CONFIRMED"
        allocated_status = "ALLOCATED"

        order.status = confirmed_status
        order.confirmed_at = datetime.utcnow()

        status_history = OrderStatusHistory(
            order_id=order_id,
            from_status=new_status,
            to_status=confirmed_status,
            changed_by=None,
            notes="COD order auto-confirmed",
        )
        db.add(status_history)
        await db.commit()
        await db.refresh(order)

        logger.info(f"  Order confirmed: {order.status}")

        # Step 4: Auto-allocate
        logger.info("Triggering warehouse allocation...")

        allocation_service = AllocationService(db)
        allocation_request = OrderAllocationRequest(
            order_id=order_id,
            customer_pincode="400001",
            items=[
                {
                    "product_id": "f54e3967-97c2-4e29-9971-f86934b2d548",
                    "quantity": 2,
                }
            ],
            payment_mode="COD",
            channel_code="D2C",
            order_value=float(order.total_amount),
        )

        allocation_decision = await allocation_service.allocate_order(allocation_request)

        logger.info(f"Allocation Result:")
        logger.info(f"  Is Allocated: {allocation_decision.is_allocated}")

        if allocation_decision.is_allocated:
            logger.info(f"  Warehouse ID: {allocation_decision.warehouse_id}")
            logger.info(f"  Warehouse Code: {allocation_decision.warehouse_code}")
            logger.info(f"  Transporter ID: {allocation_decision.transporter_id}")
            logger.info(f"  Transporter Name: {allocation_decision.transporter_name}")
            logger.info(f"  Estimated Delivery Days: {allocation_decision.estimated_delivery_days}")

            # Update order with allocation
            await db.refresh(order)
            order.warehouse_id = allocation_decision.warehouse_id
            order.transporter_id = allocation_decision.transporter_id
            order.status = allocated_status
            order.allocated_at = datetime.utcnow()

            status_history = OrderStatusHistory(
                order_id=order_id,
                from_status=confirmed_status,
                to_status=allocated_status,
                changed_by=None,
                notes=f"Auto-allocated to warehouse: {allocation_decision.warehouse_code}",
            )
            db.add(status_history)
            await db.commit()

            logger.info(f"\n✅ ORDER ALLOCATED SUCCESSFULLY!")
            logger.info(f"   Order: {order_number}")
            logger.info(f"   Status: {order.status}")
            logger.info(f"   Warehouse: {allocation_decision.warehouse_code}")
            logger.info(f"   Transporter: {allocation_decision.transporter_name}")
        else:
            logger.error(f"  Failure Reason: {allocation_decision.failure_reason}")
            logger.error(f"\n❌ ALLOCATION FAILED: {allocation_decision.failure_reason}")

        return order, allocation_decision


if __name__ == "__main__":
    asyncio.run(test_d2c_order())
