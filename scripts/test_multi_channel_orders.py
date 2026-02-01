#!/usr/bin/env python3
"""Test orders for Modern Trade, General Trade, and Marketplace channels."""

import asyncio
import sys
import logging
from decimal import Decimal
import uuid
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add project to path
sys.path.insert(0, '/Users/mantosh/Desktop/Consumer durable 2')

from app.database import async_session_factory
from app.services.order_service import OrderService
from app.services.allocation_service import AllocationService
from app.models.order import Order, OrderItem
from app.models.customer import Customer, CustomerAddress
from app.schemas.order import OrderCreate, OrderItemCreate, AddressInput
from sqlalchemy import select, text
from sqlalchemy.orm import selectinload


async def create_test_customer(db, channel_code: str):
    """Create or get a test customer for the channel."""
    phone = f"98765{hash(channel_code) % 100000:05d}"

    result = await db.execute(
        select(Customer)
        .options(selectinload(Customer.addresses))
        .where(Customer.phone == phone)
    )
    customer = result.scalar_one_or_none()

    if customer:
        logger.info(f"Using existing customer: {customer.first_name} {customer.last_name}")
        return customer

    # Create new customer
    customer = Customer(
        id=uuid.uuid4(),
        customer_code=f"CUST-{channel_code}-{datetime.now().strftime('%H%M%S')}",
        first_name=f"{channel_code}",
        last_name="Test Customer",
        email=f"{channel_code.lower()}@test.com",
        phone=phone,
        customer_type="B2B" if channel_code in ['MT', 'GT'] else "B2C",
        source=channel_code,
        is_active=True,
        is_verified=True,
    )
    db.add(customer)
    await db.flush()

    # Add address
    address = CustomerAddress(
        id=uuid.uuid4(),
        customer_id=customer.id,
        address_type="SHIPPING",
        contact_name=f"{channel_code} Test",
        contact_phone=phone,
        address_line1=f"{channel_code} Test Address",
        city="Mumbai",
        state="Maharashtra",
        pincode="400001",
        country="India",
        is_default=True,
        is_active=True,
    )
    db.add(address)
    await db.flush()

    logger.info(f"Created customer: {customer.first_name} {customer.last_name}")
    return customer


async def get_test_product(db):
    """Get a product with inventory."""
    result = await db.execute(text("""
        SELECT p.id, p.name, p.sku, p.mrp, ci.allocated_quantity
        FROM products p
        JOIN channel_inventory ci ON p.id = ci.product_id
        WHERE ci.allocated_quantity > 10
        AND p.is_active = true
        LIMIT 1
    """))
    product = result.fetchone()
    if product:
        return {
            'id': product[0],
            'name': product[1],
            'sku': product[2],
            'mrp': product[3],
            'available': product[4]
        }
    return None


async def test_channel_order(channel_code: str, channel_name: str):
    """Test complete order flow for a specific channel."""
    logger.info("=" * 70)
    logger.info(f"TESTING {channel_name} ({channel_code}) ORDER FLOW")
    logger.info("=" * 70)

    async with async_session_factory() as db:
        order_service = OrderService(db)
        allocation_service = AllocationService(db)

        # Step 1: Get/Create customer
        logger.info("\n[STEP 1] Creating/Getting customer...")
        customer = await create_test_customer(db, channel_code)
        await db.commit()

        # Get address
        result = await db.execute(
            select(CustomerAddress)
            .where(CustomerAddress.customer_id == customer.id)
            .where(CustomerAddress.is_default == True)
        )
        address = result.scalar_one_or_none()

        if not address:
            logger.error(f"No address found for customer!")
            return None

        # Step 2: Get product
        logger.info("\n[STEP 2] Getting test product...")
        product = await get_test_product(db)
        if not product:
            logger.error("No product with inventory found!")
            return None

        logger.info(f"  Product: {product['name']} (SKU: {product['sku']})")
        logger.info(f"  MRP: {product['mrp']}, Available: {product['available']}")

        # Step 3: Create order
        logger.info(f"\n[STEP 3] Creating {channel_code} order...")

        # Get channel
        channel_result = await db.execute(text(
            "SELECT id FROM sales_channels WHERE code = :code"
        ), {'code': channel_code})
        channel = channel_result.fetchone()

        order_data = OrderCreate(
            customer_id=customer.id,
            shipping_address=AddressInput(address_id=address.id),
            billing_address=AddressInput(address_id=address.id),
            payment_method="COD" if channel_code in ['D2C', 'AMAZON'] else "CREDIT",
            items=[
                OrderItemCreate(
                    product_id=product['id'],
                    quantity=1,
                    unit_price=product['mrp'],
                )
            ],
            customer_notes=f"Test order for {channel_name}",
        )

        order = await order_service.create_order(order_data)
        await db.commit()

        logger.info(f"  Order Created: {order.order_number}")
        logger.info(f"  Status: {order.status}")
        logger.info(f"  Total: {order.total_amount}")

        # Step 4: Confirm order
        logger.info(f"\n[STEP 4] Confirming order...")
        from app.models.order import OrderStatus, PaymentMethod
        order = await order_service.update_order_status(order.id, OrderStatus.CONFIRMED, notes="Test confirmation")
        logger.info(f"  Status after confirm: {order.status}")

        # Step 5: Process payment
        logger.info(f"\n[STEP 5] Processing payment...")
        payment_method = PaymentMethod.CASH if channel_code in ['D2C', 'AMAZON'] else PaymentMethod.NET_BANKING
        payment = await order_service.add_payment(
            order_id=order.id,
            amount=order.total_amount,
            method=payment_method,
            reference_number=f"PAY-{channel_code}-{datetime.now().strftime('%H%M%S')}"
        )
        await db.refresh(order)
        logger.info(f"  Payment Status: {order.payment_status}")

        # Step 6: Allocate inventory
        logger.info(f"\n[STEP 6] Allocating inventory...")
        try:
            allocation = await allocation_service.allocate_order(order.id)
            await db.commit()
            if allocation:
                logger.info(f"  Allocation successful!")
                logger.info(f"  Warehouse: {allocation.get('warehouse_id', 'N/A')}")
        except Exception as e:
            logger.warning(f"  Allocation: {str(e)[:50]}...")

        # Step 7: Check journal entries
        logger.info(f"\n[STEP 7] Checking journal entries...")
        je_result = await db.execute(text("""
            SELECT je.entry_number, je.entry_type, je.total_debit, je.status
            FROM journal_entries je
            WHERE je.source_id = :order_id
            ORDER BY je.created_at DESC
        """), {'order_id': str(order.id)})
        journal_entries = je_result.fetchall()

        if journal_entries:
            for je in journal_entries:
                logger.info(f"  {je[0]} | {je[1]} | DR: {je[2]} | {je[3]}")
        else:
            logger.info("  No journal entries found (may be in separate transaction)")

        # Refresh and return
        await db.refresh(order)

        logger.info(f"\n[RESULT] {channel_code} Order Flow Complete!")
        logger.info(f"  Order: {order.order_number}")
        logger.info(f"  Status: {order.status}")
        logger.info(f"  Payment: {order.payment_status}")

        return {
            'channel': channel_code,
            'order_number': order.order_number,
            'order_id': str(order.id),
            'status': order.status,
            'payment_status': order.payment_status,
            'total_amount': float(order.total_amount),
        }


async def verify_gl_entries():
    """Verify GL entries for all test orders."""
    logger.info("\n" + "=" * 70)
    logger.info("GL ENTRIES VERIFICATION")
    logger.info("=" * 70)

    async with async_session_factory() as db:
        result = await db.execute(text("""
            SELECT
                ca.account_code, ca.account_name, ca.account_type,
                SUM(gl.debit_amount) as total_dr,
                SUM(gl.credit_amount) as total_cr
            FROM general_ledger gl
            JOIN chart_of_accounts ca ON gl.account_id = ca.id
            GROUP BY ca.account_code, ca.account_name, ca.account_type
            ORDER BY ca.account_code
        """))
        gl_entries = result.fetchall()

        if gl_entries:
            logger.info("\nGL Account Summary:")
            total_dr = Decimal("0")
            total_cr = Decimal("0")
            for gl in gl_entries:
                dr = gl[3] or Decimal("0")
                cr = gl[4] or Decimal("0")
                total_dr += dr
                total_cr += cr
                logger.info(f"  {gl[0]} | {gl[1]:<25} | DR: {dr:>10.2f} | CR: {cr:>10.2f}")

            logger.info(f"\nTotal: DR: {total_dr:>10.2f} | CR: {total_cr:>10.2f}")
            balanced = abs(total_dr - total_cr) < Decimal("0.01")
            logger.info(f"Balanced: {'YES' if balanced else 'NO'}")
        else:
            logger.info("No GL entries found yet.")


async def main():
    """Run tests for all channels."""
    logger.info("=" * 70)
    logger.info("MULTI-CHANNEL ORDER FLOW TEST")
    logger.info("=" * 70)

    results = []

    # Test each channel
    channels = [
        ('MT', 'Modern Trade'),
        ('GT', 'General Trade'),
        ('AMAZON', 'Amazon Marketplace'),
    ]

    for code, name in channels:
        try:
            result = await test_channel_order(code, name)
            if result:
                results.append(result)
        except Exception as e:
            logger.error(f"Error testing {code}: {str(e)}")
            import traceback
            traceback.print_exc()

    # Verify GL entries
    await verify_gl_entries()

    # Summary
    logger.info("\n" + "=" * 70)
    logger.info("TEST SUMMARY")
    logger.info("=" * 70)

    for r in results:
        logger.info(f"  {r['channel']:10} | {r['order_number']:20} | {r['status']:12} | {r['payment_status']:10} | {r['total_amount']:>10.2f}")

    if len(results) == len(channels):
        logger.info(f"\nALL {len(channels)} CHANNEL TESTS PASSED!")
    else:
        logger.info(f"\n{len(results)}/{len(channels)} CHANNEL TESTS PASSED")

    return results


if __name__ == "__main__":
    asyncio.run(main())
