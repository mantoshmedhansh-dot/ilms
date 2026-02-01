#!/usr/bin/env python3
"""Test payment flow with journal entry generation."""

import asyncio
import sys
import logging
from decimal import Decimal
import uuid

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add project to path
sys.path.insert(0, '/Users/mantosh/Desktop/Consumer durable 2')

from app.database import async_session_factory
from app.services.order_service import OrderService
from app.models.order import Order, PaymentMethod
from sqlalchemy import select, desc


async def test_payment_flow():
    """Test adding a payment to an order and generating journal entry."""

    async with async_session_factory() as db:
        service = OrderService(db)

        # Step 1: Find a recent allocated order (COD, not yet paid)
        logger.info("Finding a recent allocated COD order...")

        result = await db.execute(
            select(Order)
            .where(Order.status == "ALLOCATED")
            .where(Order.payment_status == "PENDING")
            .where(Order.payment_method == "COD")
            .order_by(desc(Order.created_at))
            .limit(1)
        )
        order = result.scalar_one_or_none()

        if not order:
            logger.warning("No allocated COD order found. Creating a new one...")
            # Create a test order first
            from app.schemas.order import OrderCreate, OrderItemCreate, AddressInput
            from app.models.order import OrderSource

            # Get or create test customer
            phone = "9876543299"
            customer = await service.get_customer_by_phone(phone)
            if not customer:
                customer = await service.create_customer({
                    "first_name": "Payment",
                    "last_name": "Test",
                    "phone": phone,
                    "email": "payment.test@example.com",
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
                    address_line1="456 Payment Test Street",
                    address_line2="",
                    city="Mumbai",
                    state="Maharashtra",
                    pincode="400001",
                    contact_name="Payment Test",
                    contact_phone=phone,
                ),
                payment_method=PaymentMethod.COD,
            )

            order = await service.create_order(order_create)
            logger.info(f"Created order: {order.order_number}")

            # Confirm the order
            order.status = "CONFIRMED"
            order.payment_status = "PENDING"
            await db.commit()
            await db.refresh(order)

        order_id = order.id
        order_number = order.order_number
        total_amount = order.total_amount

        logger.info(f"Using order: {order_number}")
        logger.info(f"  ID: {order_id}")
        logger.info(f"  Status: {order.status}")
        logger.info(f"  Payment Status: {order.payment_status}")
        logger.info(f"  Total Amount: {total_amount}")

        # Step 2: Add a payment (simulating COD collection at delivery)
        logger.info("\nAdding COD payment...")

        payment = await service.add_payment(
            order_id=order_id,
            amount=total_amount,
            method=PaymentMethod.COD,
            transaction_id=None,  # COD doesn't have transaction ID
            gateway=None,
            reference_number=f"COD-{order_number}",
            notes="Payment collected at delivery",
        )

        logger.info(f"Payment recorded:")
        logger.info(f"  Payment ID: {payment.id}")
        logger.info(f"  Amount: {payment.amount}")
        logger.info(f"  Method: {payment.method}")
        logger.info(f"  Status: {payment.status}")

        # Refresh order to see updated payment status
        await db.refresh(order)
        logger.info(f"\nOrder updated:")
        logger.info(f"  Payment Status: {order.payment_status}")
        logger.info(f"  Amount Paid: {order.amount_paid}")

        # Step 3: Check if journal entry was created
        logger.info("\nChecking journal entry...")

        from sqlalchemy import text
        result = await db.execute(text("""
            SELECT
                je.id, je.entry_number, je.entry_type, je.source_type,
                je.narration, je.total_debit, je.total_credit, je.status
            FROM journal_entries je
            WHERE je.source_type = 'ORDER_PAYMENT' AND je.source_id = :order_id
            ORDER BY je.created_at DESC
            LIMIT 1
        """), {"order_id": order_id})
        journal = result.fetchone()

        if journal:
            logger.info(f"Journal Entry Created!")
            logger.info(f"  Entry Number: {journal[1]}")
            logger.info(f"  Type: {journal[2]}")
            logger.info(f"  Source: {journal[3]}")
            logger.info(f"  Narration: {journal[4]}")
            logger.info(f"  Total Debit: {journal[5]}")
            logger.info(f"  Total Credit: {journal[6]}")
            logger.info(f"  Status: {journal[7]}")

            # Get journal lines
            lines_result = await db.execute(text("""
                SELECT
                    jel.id, ca.account_code, ca.account_name,
                    jel.debit_amount, jel.credit_amount, jel.description
                FROM journal_entry_lines jel
                JOIN chart_of_accounts ca ON jel.account_id = ca.id
                WHERE jel.journal_entry_id = :journal_id
            """), {"journal_id": journal[0]})
            lines = lines_result.fetchall()

            logger.info(f"\nJournal Lines:")
            for line in lines:
                dr = line[3] if line[3] else Decimal("0")
                cr = line[4] if line[4] else Decimal("0")
                dr_cr = f"DR {dr}" if dr > 0 else f"CR {cr}"
                logger.info(f"  {line[1]} - {line[2]}: {dr_cr}")

            # Check if posted to General Ledger
            gl_result = await db.execute(text("""
                SELECT COUNT(*) FROM general_ledger WHERE journal_entry_id = :journal_id
            """), {"journal_id": journal[0]})
            gl_count = gl_result.scalar()
            logger.info(f"\nGeneral Ledger Entries: {gl_count}")

            logger.info("\n✅ PAYMENT FLOW TEST PASSED!")
        else:
            logger.error("\n❌ Journal entry was NOT created!")
            logger.info("Checking for any errors in the service...")

        return payment


if __name__ == "__main__":
    asyncio.run(test_payment_flow())
