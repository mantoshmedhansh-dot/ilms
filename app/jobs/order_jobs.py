"""
Order Processing Jobs

Background jobs for managing order-related tasks:
- Payment status checks
- Abandoned cart processing
- Order status updates
"""

import logging
from typing import List, Dict, Any
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)


async def check_pending_payments():
    """
    Check status of pending payments with Razorpay.

    This job runs every 10 minutes to:
    1. Find orders with pending payment status
    2. Check payment status with Razorpay
    3. Update order status accordingly
    4. Handle failed/expired payments

    Payment states handled:
    - authorized -> Capture payment
    - captured -> Mark order as paid
    - failed -> Mark order as failed
    - expired -> Cancel order
    """
    logger.info("Starting pending payments check...")
    start_time = datetime.now(timezone.utc)
    processed_count = 0
    updated_count = 0

    try:
        from app.database import get_db_session
        from sqlalchemy import text
        import razorpay
        from app.config import settings

        # Initialize Razorpay client
        razorpay_client = razorpay.Client(
            auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
        )

        async with get_db_session() as session:
            # Find orders with pending payment (older than 5 minutes)
            cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=5)

            result = await session.execute(
                text("""
                    SELECT
                        id,
                        order_number,
                        razorpay_order_id,
                        razorpay_payment_id,
                        payment_status,
                        created_at
                    FROM orders
                    WHERE payment_status = 'PENDING'
                    AND razorpay_order_id IS NOT NULL
                    AND created_at < :cutoff_time
                    ORDER BY created_at ASC
                    LIMIT 100
                """),
                {"cutoff_time": cutoff_time}
            )
            pending_orders = result.fetchall()

            for order in pending_orders:
                processed_count += 1
                try:
                    # Check payment status with Razorpay
                    payments = razorpay_client.order.payments(order.razorpay_order_id)

                    if payments.get("items"):
                        payment = payments["items"][0]
                        payment_status = payment.get("status")

                        new_status = None
                        if payment_status == "captured":
                            new_status = "PAID"  # UPPERCASE per coding standards
                        elif payment_status == "authorized":
                            # Capture the payment
                            try:
                                razorpay_client.payment.capture(
                                    payment["id"],
                                    payment["amount"]
                                )
                                new_status = "PAID"  # UPPERCASE per coding standards
                            except Exception as e:
                                logger.error(f"Payment capture failed: {e}")
                                new_status = "FAILED"  # UPPERCASE per coding standards
                        elif payment_status == "failed":
                            new_status = "FAILED"  # UPPERCASE per coding standards

                        if new_status:
                            await session.execute(
                                text("""
                                    UPDATE orders
                                    SET
                                        payment_status = :status,
                                        razorpay_payment_id = :payment_id,
                                        updated_at = :updated_at
                                    WHERE id = :order_id
                                """),
                                {
                                    "status": new_status,
                                    "payment_id": payment["id"],
                                    "updated_at": datetime.now(timezone.utc),
                                    "order_id": order.id
                                }
                            )
                            updated_count += 1
                            logger.info(
                                f"Order {order.order_number}: "
                                f"payment status updated to {new_status}"
                            )

                    else:
                        # No payment attempts - check if order is expired
                        order_age = datetime.now(timezone.utc) - order.created_at
                        if order_age > timedelta(hours=24):
                            await session.execute(
                                text("""
                                    UPDATE orders
                                    SET
                                        payment_status = 'FAILED',
                                        status = 'CANCELLED',
                                        updated_at = :updated_at,
                                        cancelled_at = :updated_at,
                                        internal_notes = COALESCE(internal_notes, '') ||
                                            E'\n[Auto-Cancelled] Payment not received within 24 hours'
                                    WHERE id = :order_id
                                """),
                                {
                                    "updated_at": datetime.now(timezone.utc),
                                    "order_id": order.id
                                }
                            )
                            updated_count += 1
                            logger.info(
                                f"Order {order.order_number}: expired due to no payment"
                            )

                except Exception as e:
                    logger.error(
                        f"Error processing order {order.order_number}: {e}"
                    )

            await session.commit()

        elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
        logger.info(
            f"Pending payments check completed: "
            f"processed {processed_count}, updated {updated_count} "
            f"in {elapsed:.2f}s"
        )

    except Exception as e:
        logger.error(f"Pending payments check failed: {e}")
        raise


async def process_abandoned_carts():
    """
    Process abandoned shopping carts.

    This job runs every hour to:
    1. Identify carts abandoned for > 1 hour
    2. Send reminder notifications
    3. Release reserved inventory for very old carts
    4. Clean up expired cart data

    Cart states:
    - Active (< 1 hour): No action
    - Abandoned (1-24 hours): Send reminder
    - Expired (> 24 hours): Release inventory, delete cart
    """
    logger.info("Starting abandoned carts processing...")
    start_time = datetime.now(timezone.utc)
    reminder_count = 0
    cleaned_count = 0

    try:
        from app.database import get_db_session
        from sqlalchemy import text

        async with get_db_session() as session:
            # Find abandoned carts (1-24 hours old)
            abandoned_cutoff = datetime.now(timezone.utc) - timedelta(hours=1)
            expired_cutoff = datetime.now(timezone.utc) - timedelta(hours=24)

            # Get carts for reminder (1-24 hours old, reminder not sent)
            result = await session.execute(
                text("""
                    SELECT
                        c.id,
                        c.user_id,
                        c.session_id,
                        c.updated_at,
                        u.email,
                        u.first_name,
                        COUNT(ci.id) as item_count,
                        SUM(ci.quantity * ci.unit_price) as cart_total
                    FROM carts c
                    LEFT JOIN users u ON c.user_id = u.id
                    LEFT JOIN cart_items ci ON c.id = ci.cart_id
                    WHERE c.updated_at < :abandoned_cutoff
                    AND c.updated_at >= :expired_cutoff
                    AND c.reminder_sent = false
                    AND c.is_active = true
                    GROUP BY c.id, c.user_id, c.session_id, c.updated_at,
                             u.email, u.first_name
                    HAVING COUNT(ci.id) > 0
                    LIMIT 100
                """),
                {
                    "abandoned_cutoff": abandoned_cutoff,
                    "expired_cutoff": expired_cutoff
                }
            )
            abandoned_carts = result.fetchall()

            for cart in abandoned_carts:
                try:
                    if cart.email:
                        # Queue reminder email
                        await queue_cart_reminder_email(
                            email=cart.email,
                            first_name=cart.first_name or "Customer",
                            item_count=cart.item_count,
                            cart_total=cart.cart_total
                        )

                    # Mark reminder as sent
                    await session.execute(
                        text("""
                            UPDATE carts
                            SET reminder_sent = true, reminder_sent_at = :now
                            WHERE id = :cart_id
                        """),
                        {"now": datetime.now(timezone.utc), "cart_id": cart.id}
                    )
                    reminder_count += 1

                except Exception as e:
                    logger.error(f"Error sending cart reminder: {e}")

            # Clean up expired carts (> 24 hours old)
            result = await session.execute(
                text("""
                    SELECT
                        c.id,
                        ci.product_id,
                        ci.quantity
                    FROM carts c
                    JOIN cart_items ci ON c.id = ci.cart_id
                    WHERE c.updated_at < :expired_cutoff
                    AND c.is_active = true
                """),
                {"expired_cutoff": expired_cutoff}
            )
            expired_items = result.fetchall()

            # Release reserved inventory
            inventory_releases = {}
            for item in expired_items:
                if item.product_id not in inventory_releases:
                    inventory_releases[item.product_id] = 0
                inventory_releases[item.product_id] += item.quantity

            for product_id, quantity in inventory_releases.items():
                await session.execute(
                    text("""
                        UPDATE inventory
                        SET reserved_quantity = GREATEST(0, reserved_quantity - :quantity)
                        WHERE product_id = :product_id
                    """),
                    {"quantity": quantity, "product_id": product_id}
                )

            # Deactivate expired carts
            result = await session.execute(
                text("""
                    UPDATE carts
                    SET is_active = false, deactivated_at = :now
                    WHERE updated_at < :expired_cutoff
                    AND is_active = true
                    RETURNING id
                """),
                {"now": datetime.now(timezone.utc), "expired_cutoff": expired_cutoff}
            )
            cleaned_count = result.rowcount or 0

            await session.commit()

        elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
        logger.info(
            f"Abandoned carts processing completed: "
            f"sent {reminder_count} reminders, cleaned {cleaned_count} carts "
            f"in {elapsed:.2f}s"
        )

    except Exception as e:
        logger.error(f"Abandoned carts processing failed: {e}")
        raise


async def queue_cart_reminder_email(
    email: str,
    first_name: str,
    item_count: int,
    cart_total: float
):
    """
    Queue an abandoned cart reminder email.

    Args:
        email: Customer email address
        first_name: Customer first name
        item_count: Number of items in cart
        cart_total: Total cart value
    """
    try:
        from app.database import get_db_session
        from sqlalchemy import text
        import json

        async with get_db_session() as session:
            await session.execute(
                text("""
                    INSERT INTO email_queue (
                        recipient_email,
                        template_type,
                        template_data,
                        scheduled_for,
                        created_at
                    ) VALUES (
                        :email,
                        'cart_reminder',
                        :template_data,
                        :scheduled_for,
                        :created_at
                    )
                """),
                {
                    "email": email,
                    "template_data": json.dumps({
                        "first_name": first_name,
                        "item_count": item_count,
                        "cart_total": float(cart_total),
                        "cart_url": "https://aquapurite.com/cart"
                    }),
                    "scheduled_for": datetime.now(timezone.utc),
                    "created_at": datetime.now(timezone.utc)
                }
            )
            await session.commit()

        logger.info(f"Cart reminder email queued for {email}")

    except Exception as e:
        logger.error(f"Failed to queue cart reminder email: {e}")


async def update_order_tracking():
    """
    Update order tracking information from logistics partners.

    This is called by the scheduler to fetch latest tracking updates.
    """
    logger.info("Starting order tracking update...")

    try:
        from app.database import get_db_session
        from sqlalchemy import text

        async with get_db_session() as session:
            # Find orders in transit
            result = await session.execute(
                text("""
                    SELECT
                        id,
                        order_number,
                        awb_code,
                        courier_name
                    FROM orders
                    WHERE status IN ('SHIPPED', 'IN_TRANSIT')
                    AND awb_code IS NOT NULL
                    LIMIT 50
                """)
            )
            orders = result.fetchall()

            for order in orders:
                try:
                    # Call logistics partner API to get tracking update
                    tracking_info = await fetch_tracking_update(
                        order.courier_name,
                        order.awb_code
                    )

                    if tracking_info:
                        # Normalize tracking status to UPPERCASE before SQL
                        # (external APIs may return lowercase values)
                        raw_status = tracking_info.get("status", "")
                        normalized_status = raw_status.upper() if raw_status else ""
                        is_delivered = normalized_status == "DELIVERED"

                        await session.execute(
                            text("""
                                UPDATE orders
                                SET
                                    tracking_status = :tracking_status,
                                    last_tracking_update = :update_time,
                                    status = CASE
                                        WHEN :is_delivered THEN 'DELIVERED'
                                        ELSE status
                                    END,
                                    delivered_at = CASE
                                        WHEN :is_delivered THEN :update_time
                                        ELSE delivered_at
                                    END
                                WHERE id = :order_id
                            """),
                            {
                                "tracking_status": normalized_status,
                                "update_time": datetime.now(timezone.utc),
                                "order_id": order.id,
                                "is_delivered": is_delivered
                            }
                        )

                except Exception as e:
                    logger.error(
                        f"Tracking update failed for {order.order_number}: {e}"
                    )

            await session.commit()

    except Exception as e:
        logger.error(f"Order tracking update failed: {e}")


async def fetch_tracking_update(
    logistics_partner: str,
    tracking_number: str
) -> Dict[str, Any]:
    """
    Fetch tracking update from logistics partner.

    Args:
        logistics_partner: Name of the logistics partner
        tracking_number: Shipment tracking number

    Returns:
        Tracking information dict
    """
    # This would be replaced with actual API calls to logistics partners
    # For now, return None as placeholder
    logger.debug(
        f"Fetching tracking for {tracking_number} from {logistics_partner}"
    )
    return None
