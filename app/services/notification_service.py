"""
Customer Notification Service

Handles sending notifications to customers via various channels:
- SMS (via provider like MSG91, Twilio, etc.)
- Email (via SMTP or provider like SendGrid, SES)
- Push Notifications (via Firebase FCM)
- WhatsApp (via provider API)

This is a placeholder implementation that logs notifications.
In production, integrate with actual providers.
"""
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from enum import Enum
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession


logger = logging.getLogger(__name__)


class NotificationChannel(str, Enum):
    """Notification delivery channels."""
    SMS = "sms"
    EMAIL = "email"
    PUSH = "push"
    WHATSAPP = "whatsapp"


class NotificationType(str, Enum):
    """Types of notifications."""
    # Order related
    ORDER_CONFIRMED = "order_confirmed"
    ORDER_SHIPPED = "order_shipped"
    ORDER_DELIVERED = "order_delivered"

    # Installation related
    INSTALLATION_SCHEDULED = "installation_scheduled"
    INSTALLATION_REMINDER = "installation_reminder"
    INSTALLATION_COMPLETED = "installation_completed"
    TECHNICIAN_ASSIGNED = "technician_assigned"
    TECHNICIAN_ON_THE_WAY = "technician_on_the_way"

    # Service related
    SERVICE_REQUEST_CREATED = "service_request_created"
    SERVICE_REQUEST_ASSIGNED = "service_request_assigned"
    SERVICE_COMPLETED = "service_completed"

    # Warranty related
    WARRANTY_EXPIRY_REMINDER = "warranty_expiry_reminder"
    AMC_RENEWAL_REMINDER = "amc_renewal_reminder"

    # Marketing
    PROMOTIONAL = "promotional"
    CAMPAIGN = "campaign"

    # Inventory alerts (internal notifications)
    LOW_STOCK_ALERT = "low_stock_alert"
    OUT_OF_STOCK_ALERT = "out_of_stock_alert"
    REORDER_REQUIRED = "reorder_required"


# SMS Templates
SMS_TEMPLATES = {
    NotificationType.ORDER_CONFIRMED: (
        "Dear {customer_name}, your order #{order_number} has been confirmed. "
        "Total: Rs.{amount}. Thank you for shopping with Aquapurite!"
    ),
    NotificationType.ORDER_SHIPPED: (
        "Your order #{order_number} has been shipped via {transporter}. "
        "Track: {tracking_url}"
    ),
    NotificationType.ORDER_DELIVERED: (
        "Dear {customer_name}, your order #{order_number} has been delivered. "
        "Installation will be scheduled within 2 days. Installation ID: {installation_number}"
    ),
    NotificationType.INSTALLATION_SCHEDULED: (
        "Your installation #{installation_number} is scheduled for {scheduled_date} "
        "between {time_slot}. Our technician will contact you before arriving."
    ),
    NotificationType.INSTALLATION_REMINDER: (
        "Reminder: Your installation is scheduled for tomorrow ({scheduled_date}). "
        "Please ensure someone is available at the installation address."
    ),
    NotificationType.INSTALLATION_COMPLETED: (
        "Installation complete! Your {product_name} has been installed. "
        "Warranty valid until {warranty_end_date}. Rate your experience: {feedback_link}"
    ),
    NotificationType.TECHNICIAN_ASSIGNED: (
        "Technician {technician_name} ({technician_phone}) has been assigned "
        "for your installation/service. They will contact you shortly."
    ),
    NotificationType.TECHNICIAN_ON_THE_WAY: (
        "Our technician {technician_name} is on the way to your location. "
        "Expected arrival: {eta}"
    ),
    NotificationType.SERVICE_REQUEST_CREATED: (
        "Your service request #{request_number} has been created. "
        "We will assign a technician shortly."
    ),
    NotificationType.SERVICE_COMPLETED: (
        "Your service request #{request_number} has been completed. "
        "Rate your experience: {feedback_link}"
    ),
    NotificationType.WARRANTY_EXPIRY_REMINDER: (
        "Reminder: Your warranty for {product_name} (S/N: {serial_number}) "
        "expires on {expiry_date}. Extend your warranty now!"
    ),
    # Inventory alerts (internal)
    NotificationType.LOW_STOCK_ALERT: (
        "[LOW STOCK] {product_name} (SKU: {product_sku}) in {warehouse_name}: "
        "{current_qty} units (Reorder level: {reorder_level})"
    ),
    NotificationType.OUT_OF_STOCK_ALERT: (
        "[OUT OF STOCK] {product_name} (SKU: {product_sku}) in {warehouse_name}: "
        "Stock depleted. Immediate reorder required."
    ),
    NotificationType.REORDER_REQUIRED: (
        "[REORDER] {product_count} products in {warehouse_name} need reordering. "
        "Please review the inventory dashboard."
    ),
}


class NotificationService:
    """
    Service for sending notifications to customers.

    In production, this would integrate with:
    - MSG91/Twilio for SMS
    - SendGrid/SES for Email
    - Firebase FCM for Push
    - WhatsApp Business API
    """

    def __init__(self, db: AsyncSession = None):
        self.db = db

    async def send_notification(
        self,
        recipient_phone: str,
        recipient_email: Optional[str],
        notification_type: NotificationType,
        channel: NotificationChannel,
        template_data: Dict[str, Any],
        custom_message: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Send a notification to a customer.

        Args:
            recipient_phone: Customer phone number
            recipient_email: Customer email address
            notification_type: Type of notification
            channel: Delivery channel (SMS, Email, etc.)
            template_data: Data to populate the template
            custom_message: Optional custom message override

        Returns:
            Dict with send status and message ID
        """
        notification_id = str(uuid4())

        # Get message content
        if custom_message:
            message = custom_message
        else:
            template = SMS_TEMPLATES.get(notification_type, "")
            try:
                message = template.format(**template_data)
            except KeyError as e:
                logger.warning(f"Missing template variable: {e}")
                message = template

        # Log the notification (in production, send via actual provider)
        log_entry = {
            "notification_id": notification_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "channel": channel.value,
            "type": notification_type.value,
            "recipient_phone": recipient_phone,
            "recipient_email": recipient_email,
            "message": message,
            "status": "sent",  # In production, track actual delivery status
        }

        logger.info(f"[NOTIFICATION] {channel.value.upper()} to {recipient_phone}: {message[:100]}...")

        # In production, call actual provider APIs here
        if channel == NotificationChannel.SMS:
            await self._send_sms(recipient_phone, message)
        elif channel == NotificationChannel.EMAIL:
            await self._send_email(recipient_email, notification_type.value, message)
        elif channel == NotificationChannel.WHATSAPP:
            await self._send_whatsapp(recipient_phone, message)
        elif channel == NotificationChannel.PUSH:
            await self._send_push_notification(recipient_phone, notification_type.value, message)

        return {
            "success": True,
            "notification_id": notification_id,
            "channel": channel.value,
            "message": message,
        }

    async def send_order_delivered_notifications(
        self,
        customer_phone: str,
        customer_email: Optional[str],
        customer_name: str,
        order_number: str,
        installation_number: str,
    ) -> List[Dict[str, Any]]:
        """
        Send all notifications for order delivered event.
        """
        results = []

        # SMS notification
        sms_result = await self.send_notification(
            recipient_phone=customer_phone,
            recipient_email=customer_email,
            notification_type=NotificationType.ORDER_DELIVERED,
            channel=NotificationChannel.SMS,
            template_data={
                "customer_name": customer_name,
                "order_number": order_number,
                "installation_number": installation_number,
            }
        )
        results.append(sms_result)

        # Email notification (if email available)
        if customer_email:
            email_result = await self.send_notification(
                recipient_phone=customer_phone,
                recipient_email=customer_email,
                notification_type=NotificationType.ORDER_DELIVERED,
                channel=NotificationChannel.EMAIL,
                template_data={
                    "customer_name": customer_name,
                    "order_number": order_number,
                    "installation_number": installation_number,
                }
            )
            results.append(email_result)

        return results

    async def send_installation_scheduled_notification(
        self,
        customer_phone: str,
        customer_email: Optional[str],
        installation_number: str,
        scheduled_date: str,
        time_slot: str,
        technician_name: Optional[str] = None,
        technician_phone: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Send notifications when installation is scheduled.
        """
        results = []

        # Installation scheduled SMS
        sms_result = await self.send_notification(
            recipient_phone=customer_phone,
            recipient_email=customer_email,
            notification_type=NotificationType.INSTALLATION_SCHEDULED,
            channel=NotificationChannel.SMS,
            template_data={
                "installation_number": installation_number,
                "scheduled_date": scheduled_date,
                "time_slot": time_slot,
            }
        )
        results.append(sms_result)

        # Technician assigned SMS (if assigned)
        if technician_name and technician_phone:
            tech_result = await self.send_notification(
                recipient_phone=customer_phone,
                recipient_email=customer_email,
                notification_type=NotificationType.TECHNICIAN_ASSIGNED,
                channel=NotificationChannel.SMS,
                template_data={
                    "technician_name": technician_name,
                    "technician_phone": technician_phone,
                }
            )
            results.append(tech_result)

        return results

    async def send_installation_completed_notification(
        self,
        customer_phone: str,
        customer_email: Optional[str],
        product_name: str,
        warranty_end_date: str,
        feedback_link: str = "https://aquapurite.com/feedback",
    ) -> List[Dict[str, Any]]:
        """
        Send notifications when installation is completed.
        """
        results = []

        sms_result = await self.send_notification(
            recipient_phone=customer_phone,
            recipient_email=customer_email,
            notification_type=NotificationType.INSTALLATION_COMPLETED,
            channel=NotificationChannel.SMS,
            template_data={
                "product_name": product_name,
                "warranty_end_date": warranty_end_date,
                "feedback_link": feedback_link,
            }
        )
        results.append(sms_result)

        return results

    # ==================== Provider Integration Stubs ====================

    async def _send_sms(self, phone: str, message: str) -> bool:
        """
        Send SMS via provider (MSG91, Twilio, etc.)

        In production, implement actual API call:
        - MSG91: POST to https://api.msg91.com/api/v5/flow/
        - Twilio: POST to https://api.twilio.com/2010-04-01/Accounts/{AccountSid}/Messages.json
        """
        logger.info(f"[SMS] Sending to {phone}: {message[:50]}...")
        # Placeholder - in production, call actual API
        return True

    async def _send_email(self, email: str, subject: str, body: str) -> bool:
        """
        Send email via provider (SendGrid, SES, SMTP).

        In production, implement actual API call:
        - SendGrid: POST to https://api.sendgrid.com/v3/mail/send
        - SES: Use boto3 ses.send_email()
        """
        logger.info(f"[EMAIL] Sending to {email}: Subject={subject}")
        # Placeholder - in production, call actual API
        return True

    async def _send_whatsapp(self, phone: str, message: str) -> bool:
        """
        Send WhatsApp message via Business API.

        In production, implement actual API call to WhatsApp Business API
        or providers like Gupshup, Twilio, etc.
        """
        logger.info(f"[WHATSAPP] Sending to {phone}: {message[:50]}...")
        # Placeholder - in production, call actual API
        return True

    async def _send_push_notification(
        self,
        device_token: str,
        title: str,
        body: str
    ) -> bool:
        """
        Send push notification via Firebase FCM.

        In production, implement actual Firebase Admin SDK call.
        """
        logger.info(f"[PUSH] Sending: Title={title}, Body={body[:50]}...")
        # Placeholder - in production, call Firebase Admin SDK
        return True


# Convenience functions for use in other services
async def notify_order_delivered(
    db: AsyncSession,
    customer_phone: str,
    customer_email: Optional[str],
    customer_name: str,
    order_number: str,
    installation_number: str,
) -> List[Dict[str, Any]]:
    """Send order delivered notifications."""
    service = NotificationService(db)
    return await service.send_order_delivered_notifications(
        customer_phone=customer_phone,
        customer_email=customer_email,
        customer_name=customer_name,
        order_number=order_number,
        installation_number=installation_number,
    )


async def notify_installation_scheduled(
    db: AsyncSession,
    customer_phone: str,
    customer_email: Optional[str],
    installation_number: str,
    scheduled_date: str,
    time_slot: str,
    technician_name: Optional[str] = None,
    technician_phone: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Send installation scheduled notifications."""
    service = NotificationService(db)
    return await service.send_installation_scheduled_notification(
        customer_phone=customer_phone,
        customer_email=customer_email,
        installation_number=installation_number,
        scheduled_date=scheduled_date,
        time_slot=time_slot,
        technician_name=technician_name,
        technician_phone=technician_phone,
    )


# ==================== INVENTORY ALERT NOTIFICATIONS ====================


class StockAlertItem:
    """Stock alert item data."""
    def __init__(
        self,
        product_id: str,
        product_name: str,
        product_sku: str,
        warehouse_name: str,
        current_qty: int,
        reorder_level: int,
    ):
        self.product_id = product_id
        self.product_name = product_name
        self.product_sku = product_sku
        self.warehouse_name = warehouse_name
        self.current_qty = current_qty
        self.reorder_level = reorder_level


async def send_low_stock_alert(
    db: AsyncSession,
    recipient_email: str,
    recipient_phone: Optional[str],
    alert_item: StockAlertItem,
) -> Dict[str, Any]:
    """
    Send low stock alert notification to warehouse/inventory managers.

    Args:
        db: Database session
        recipient_email: Manager email for notification
        recipient_phone: Manager phone for SMS alert
        alert_item: Stock alert item details
    """
    service = NotificationService(db)

    # Send email notification
    result = await service.send_notification(
        recipient_phone=recipient_phone or "",
        recipient_email=recipient_email,
        notification_type=NotificationType.LOW_STOCK_ALERT,
        channel=NotificationChannel.EMAIL,
        template_data={
            "product_name": alert_item.product_name,
            "product_sku": alert_item.product_sku,
            "warehouse_name": alert_item.warehouse_name,
            "current_qty": alert_item.current_qty,
            "reorder_level": alert_item.reorder_level,
        }
    )

    logger.warning(
        f"LOW STOCK ALERT: {alert_item.product_name} ({alert_item.product_sku}) "
        f"in {alert_item.warehouse_name}: {alert_item.current_qty} units "
        f"(reorder level: {alert_item.reorder_level})"
    )

    return result


async def send_out_of_stock_alert(
    db: AsyncSession,
    recipient_email: str,
    recipient_phone: Optional[str],
    alert_item: StockAlertItem,
) -> Dict[str, Any]:
    """
    Send out of stock alert notification to warehouse/inventory managers.
    """
    service = NotificationService(db)

    # Send both email and SMS for out-of-stock (critical)
    results = []

    # Email
    email_result = await service.send_notification(
        recipient_phone=recipient_phone or "",
        recipient_email=recipient_email,
        notification_type=NotificationType.OUT_OF_STOCK_ALERT,
        channel=NotificationChannel.EMAIL,
        template_data={
            "product_name": alert_item.product_name,
            "product_sku": alert_item.product_sku,
            "warehouse_name": alert_item.warehouse_name,
        }
    )
    results.append(email_result)

    # SMS if phone available
    if recipient_phone:
        sms_result = await service.send_notification(
            recipient_phone=recipient_phone,
            recipient_email=recipient_email,
            notification_type=NotificationType.OUT_OF_STOCK_ALERT,
            channel=NotificationChannel.SMS,
            template_data={
                "product_name": alert_item.product_name,
                "product_sku": alert_item.product_sku,
                "warehouse_name": alert_item.warehouse_name,
            }
        )
        results.append(sms_result)

    logger.critical(
        f"OUT OF STOCK ALERT: {alert_item.product_name} ({alert_item.product_sku}) "
        f"in {alert_item.warehouse_name}: Stock depleted!"
    )

    return {"notifications": results, "count": len(results)}


async def check_and_send_stock_alerts(
    db: AsyncSession,
    warehouse_id: Optional[str] = None,
    manager_email: str = "inventory@aquapurite.com",
    manager_phone: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Check inventory levels and send alerts for low/out of stock items.

    This function should be called periodically (e.g., daily via cron job)
    or after significant inventory movements.

    Returns summary of alerts sent.
    """
    from app.services.inventory_service import InventoryService
    from app.models.inventory import InventorySummary
    from app.models.product import Product
    from app.models.warehouse import Warehouse
    from sqlalchemy import select, and_
    from sqlalchemy.orm import joinedload

    # Get low stock items
    query = select(InventorySummary).options(
        joinedload(InventorySummary.product),
        joinedload(InventorySummary.warehouse),
    ).where(
        and_(
            InventorySummary.available_quantity <= InventorySummary.reorder_level,
        )
    )

    if warehouse_id:
        query = query.where(InventorySummary.warehouse_id == warehouse_id)

    result = await db.execute(query)
    low_stock_items = result.scalars().unique().all()

    alerts_sent = {"low_stock": 0, "out_of_stock": 0}

    for item in low_stock_items:
        alert_item = StockAlertItem(
            product_id=str(item.product_id),
            product_name=item.product.name if item.product else "Unknown",
            product_sku=item.product.sku if item.product else "N/A",
            warehouse_name=item.warehouse.name if item.warehouse else "Unknown",
            current_qty=item.available_quantity,
            reorder_level=item.reorder_level or 10,
        )

        if item.available_quantity == 0:
            await send_out_of_stock_alert(
                db=db,
                recipient_email=manager_email,
                recipient_phone=manager_phone,
                alert_item=alert_item,
            )
            alerts_sent["out_of_stock"] += 1
        else:
            await send_low_stock_alert(
                db=db,
                recipient_email=manager_email,
                recipient_phone=manager_phone,
                alert_item=alert_item,
            )
            alerts_sent["low_stock"] += 1

    logger.info(
        f"Stock alerts processed: {alerts_sent['low_stock']} low stock, "
        f"{alerts_sent['out_of_stock']} out of stock"
    )

    return {
        "success": True,
        "alerts_sent": alerts_sent,
        "total_items_checked": len(low_stock_items),
    }
