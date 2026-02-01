import smtplib
import httpx
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, Dict, List
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class EmailService:
    """Email service for sending transactional emails via Gmail SMTP."""

    def __init__(
        self,
        smtp_host: str = "smtp.gmail.com",
        smtp_port: int = 587,
        smtp_user: str = "",
        smtp_password: str = "",
        from_email: str = "",
        from_name: str = "Aquapurite ERP"
    ):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        self.from_email = from_email or smtp_user
        self.from_name = from_name

    def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None
    ) -> bool:
        """
        Send an email using Gmail SMTP.

        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML body of the email
            text_content: Plain text body (optional fallback)

        Returns:
            True if email sent successfully, False otherwise
        """
        if not self.smtp_user or not self.smtp_password:
            logger.warning("Email not configured. SMTP credentials missing.")
            return False

        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = to_email

            # Add plain text version
            if text_content:
                part1 = MIMEText(text_content, 'plain')
                msg.attach(part1)

            # Add HTML version
            part2 = MIMEText(html_content, 'html')
            msg.attach(part2)

            # Connect and send with timeout
            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=10) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.sendmail(self.from_email, to_email, msg.as_string())

            logger.info(f"Email sent successfully to {to_email}")
            return True

        except smtplib.SMTPAuthenticationError:
            logger.error("SMTP Authentication failed. Check email credentials.")
            return False
        except smtplib.SMTPException as e:
            logger.error(f"SMTP error: {e}")
            return False
        except TimeoutError:
            logger.error("SMTP connection timed out")
            return False
        except OSError as e:
            logger.error(f"Network error sending email: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False

    def send_password_reset_email(
        self,
        to_email: str,
        reset_token: str,
        reset_url: str,
        user_name: str = "User"
    ) -> bool:
        """
        Send a password reset email.

        Args:
            to_email: User's email address
            reset_token: The password reset token
            reset_url: Full URL to reset password page
            user_name: User's name for personalization

        Returns:
            True if email sent successfully, False otherwise
        """
        subject = "Reset Your Password - Aquapurite ERP"

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #1a56db; color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 30px; background: #f9f9f9; }}
                .button {{ display: inline-block; padding: 12px 30px; background: #1a56db; color: white; text-decoration: none; border-radius: 5px; margin: 20px 0; }}
                .token-box {{ background: #e5e7eb; padding: 15px; border-radius: 5px; font-family: monospace; word-break: break-all; margin: 15px 0; }}
                .footer {{ padding: 20px; text-align: center; color: #666; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Aquapurite ERP</h1>
                </div>
                <div class="content">
                    <h2>Password Reset Request</h2>
                    <p>Hello {user_name},</p>
                    <p>We received a request to reset your password. Click the button below to create a new password:</p>

                    <p style="text-align: center;">
                        <a href="{reset_url}" class="button">Reset Password</a>
                    </p>

                    <p>Or copy and paste this link in your browser:</p>
                    <p style="word-break: break-all; color: #1a56db;">{reset_url}</p>

                    <p><strong>Your reset token:</strong></p>
                    <div class="token-box">{reset_token}</div>

                    <p>This link will expire in <strong>1 hour</strong>.</p>

                    <p>If you didn't request this password reset, please ignore this email or contact support if you have concerns.</p>

                    <p>Best regards,<br>Aquapurite ERP Team</p>
                </div>
                <div class="footer">
                    <p>This is an automated message from Aquapurite Private Limited's ERP System.</p>
                    <p>Please do not reply to this email.</p>
                </div>
            </div>
        </body>
        </html>
        """

        text_content = f"""
        Password Reset Request

        Hello {user_name},

        We received a request to reset your password.

        Click this link to reset your password:
        {reset_url}

        Or use this token: {reset_token}

        This link will expire in 1 hour.

        If you didn't request this password reset, please ignore this email.

        Best regards,
        Aquapurite ERP Team
        """

        return self.send_email(to_email, subject, html_content, text_content)


    # ==================== D2C ORDER NOTIFICATIONS ====================

    def send_order_confirmation_email(
        self,
        to_email: str,
        order_number: str,
        customer_name: str,
        total_amount: Decimal,
        items: List[Dict],
        shipping_address: Dict,
        payment_method: str,
        expected_delivery: Optional[str] = None,
        d2c_url: str = "https://www.aquapurite.com"
    ) -> bool:
        """
        Send order confirmation email for D2C storefront.

        Args:
            to_email: Customer email
            order_number: Order number
            customer_name: Customer's name
            total_amount: Order total
            items: List of order items with product_name, quantity, total_amount
            shipping_address: Delivery address dict
            payment_method: Payment method used
            expected_delivery: Expected delivery date string
            d2c_url: D2C storefront URL

        Returns:
            True if sent successfully
        """
        subject = f"Order Confirmed - {order_number} | Aquapurite"

        # Build items HTML
        items_html = ""
        for item in items:
            items_html += f"""
            <tr>
                <td style="padding: 12px; border-bottom: 1px solid #eee;">
                    <strong>{item.get('product_name', 'Product')}</strong>
                    {f"<br><small style='color: #666;'>{item.get('variant_name', '')}</small>" if item.get('variant_name') else ''}
                </td>
                <td style="padding: 12px; border-bottom: 1px solid #eee; text-align: center;">
                    {item.get('quantity', 1)}
                </td>
                <td style="padding: 12px; border-bottom: 1px solid #eee; text-align: right;">
                    ₹{float(item.get('total_amount', 0)):,.2f}
                </td>
            </tr>
            """

        # Build address string
        address_parts = [
            shipping_address.get('address_line1', ''),
            shipping_address.get('address_line2', ''),
            f"{shipping_address.get('city', '')}, {shipping_address.get('state', '')}",
            shipping_address.get('pincode', ''),
        ]
        address_str = "<br>".join([p for p in address_parts if p])

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; background: #f5f5f5;">
            <div style="background: linear-gradient(135deg, #0066cc 0%, #004d99 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
                <h1 style="color: white; margin: 0; font-size: 24px;">✓ Order Confirmed!</h1>
                <p style="color: #cce5ff; margin: 10px 0 0 0;">Thank you for your order</p>
            </div>

            <div style="background: white; padding: 30px; border: 1px solid #e9ecef;">
                <p style="margin: 0 0 20px 0;">Hi <strong>{customer_name}</strong>,</p>

                <p style="margin: 0 0 20px 0;">
                    Your order <strong style="color: #0066cc;">#{order_number}</strong> has been confirmed.
                    We're getting it ready for you!
                </p>

                <div style="background: #f8f9fa; border-radius: 8px; padding: 20px; margin: 20px 0;">
                    <h3 style="margin: 0 0 15px 0; color: #0066cc; border-bottom: 2px solid #0066cc; padding-bottom: 10px;">
                        Order Details
                    </h3>
                    <table style="width: 100%; border-collapse: collapse;">
                        <thead>
                            <tr style="background: #e9ecef;">
                                <th style="padding: 12px; text-align: left;">Item</th>
                                <th style="padding: 12px; text-align: center;">Qty</th>
                                <th style="padding: 12px; text-align: right;">Amount</th>
                            </tr>
                        </thead>
                        <tbody>
                            {items_html}
                        </tbody>
                        <tfoot>
                            <tr style="background: #0066cc; color: white;">
                                <td colspan="2" style="padding: 15px; font-weight: bold;">Total</td>
                                <td style="padding: 15px; text-align: right; font-weight: bold; font-size: 18px;">
                                    ₹{float(total_amount):,.2f}
                                </td>
                            </tr>
                        </tfoot>
                    </table>
                </div>

                <table style="width: 100%; margin: 20px 0;">
                    <tr>
                        <td style="width: 50%; vertical-align: top; padding-right: 10px;">
                            <div style="background: #f8f9fa; border-radius: 8px; padding: 15px;">
                                <h4 style="margin: 0 0 10px 0; color: #666; font-size: 12px; text-transform: uppercase;">
                                    📍 Delivery Address
                                </h4>
                                <p style="margin: 0; font-size: 14px;">{address_str}</p>
                            </div>
                        </td>
                        <td style="width: 50%; vertical-align: top; padding-left: 10px;">
                            <div style="background: #f8f9fa; border-radius: 8px; padding: 15px;">
                                <h4 style="margin: 0 0 10px 0; color: #666; font-size: 12px; text-transform: uppercase;">
                                    💳 Payment Method
                                </h4>
                                <p style="margin: 0; font-size: 14px;">{payment_method}</p>
                                {f'<p style="margin: 5px 0 0 0; font-size: 12px; color: #28a745;">📅 Expected: {expected_delivery}</p>' if expected_delivery else ''}
                            </div>
                        </td>
                    </tr>
                </table>

                <div style="text-align: center; margin: 30px 0;">
                    <a href="{d2c_url}/track?order={order_number}"
                       style="display: inline-block; background: #0066cc; color: white; padding: 15px 30px;
                              text-decoration: none; border-radius: 5px; font-weight: bold;">
                        Track Your Order
                    </a>
                </div>

                <p style="margin: 20px 0 0 0; font-size: 14px; color: #666;">
                    If you have any questions, feel free to contact us at
                    <a href="mailto:support@aquapurite.com" style="color: #0066cc;">support@aquapurite.com</a>
                    or call us at <strong>1800-XXX-XXXX</strong> (Toll Free).
                </p>
            </div>

            <div style="background: #333; color: #fff; padding: 20px; text-align: center; border-radius: 0 0 10px 10px;">
                <p style="margin: 0 0 10px 0;">
                    <strong>Aquapurite</strong> - Pure Water, Pure Life
                </p>
                <p style="margin: 0; font-size: 12px; color: #999;">
                    This is an automated email. Please do not reply directly to this message.
                </p>
            </div>
        </body>
        </html>
        """

        text_content = f"""
Order Confirmed - {order_number}

Hi {customer_name},

Your order #{order_number} has been confirmed!

Order Total: ₹{float(total_amount):,.2f}
Payment Method: {payment_method}

Delivery Address:
{shipping_address.get('address_line1', '')}
{shipping_address.get('city', '')}, {shipping_address.get('state', '')} - {shipping_address.get('pincode', '')}

Track your order: {d2c_url}/track?order={order_number}

Thank you for shopping with Aquapurite!

Questions? Contact us at support@aquapurite.com
        """

        return self.send_email(to_email, subject, html_content, text_content)

    def send_order_shipped_email(
        self,
        to_email: str,
        order_number: str,
        customer_name: str,
        tracking_number: str,
        courier_name: str,
        tracking_url: Optional[str] = None,
        expected_delivery: Optional[str] = None,
        d2c_url: str = "https://www.aquapurite.com"
    ) -> bool:
        """Send order shipped notification email."""
        subject = f"Your Order is Shipped - {order_number} | Aquapurite"

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
        </head>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; background: #f5f5f5;">
            <div style="background: #28a745; padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
                <h1 style="color: white; margin: 0;">🚚 Your Order is On The Way!</h1>
            </div>

            <div style="background: white; padding: 30px; border: 1px solid #e9ecef;">
                <p>Hi <strong>{customer_name}</strong>,</p>

                <p>Great news! Your order <strong>#{order_number}</strong> has been shipped.</p>

                <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <p style="margin: 0;"><strong>📦 Courier:</strong> {courier_name}</p>
                    <p style="margin: 10px 0 0 0;"><strong>🔢 Tracking Number:</strong> {tracking_number}</p>
                    {f'<p style="margin: 10px 0 0 0;"><strong>📅 Expected Delivery:</strong> {expected_delivery}</p>' if expected_delivery else ''}
                </div>

                <div style="text-align: center; margin: 20px 0;">
                    <a href="{tracking_url or f'{d2c_url}/track?order={order_number}'}"
                       style="display: inline-block; background: #28a745; color: white; padding: 15px 30px;
                              text-decoration: none; border-radius: 5px; font-weight: bold;">
                        Track Shipment
                    </a>
                </div>
            </div>

            <div style="background: #333; color: #fff; padding: 20px; text-align: center; border-radius: 0 0 10px 10px;">
                <p style="margin: 0;"><strong>Aquapurite</strong> - Pure Water, Pure Life</p>
            </div>
        </body>
        </html>
        """

        text_content = f"""
Your Order is Shipped - {order_number}

Hi {customer_name},

Great news! Your order #{order_number} has been shipped.

Courier: {courier_name}
Tracking Number: {tracking_number}
{f'Expected Delivery: {expected_delivery}' if expected_delivery else ''}

Track your shipment: {tracking_url or f'{d2c_url}/track?order={order_number}'}

Thank you for shopping with Aquapurite!
        """

        return self.send_email(to_email, subject, html_content, text_content)


# ==================== SMS SERVICE (MSG91) ====================

class SMSService:
    """SMS service using MSG91 API (India DLT compliant)."""

    def __init__(
        self,
        auth_key: str = "",
        sender_id: str = "AQUAPU"
    ):
        self.auth_key = auth_key
        self.sender_id = sender_id
        self.base_url = "https://control.msg91.com/api/v5/flow/"

    async def send_sms(
        self,
        phone: str,
        template_id: str,
        variables: Dict[str, str]
    ) -> bool:
        """
        Send SMS via MSG91.

        Args:
            phone: Phone number (10 digits)
            template_id: DLT registered template ID
            variables: Template variables (VAR1, VAR2, etc.)

        Returns:
            True if sent successfully
        """
        if not self.auth_key:
            logger.warning("MSG91 auth key not configured, skipping SMS")
            return False

        # Normalize phone number
        phone = phone.replace(" ", "").replace("-", "")
        if phone.startswith("+91"):
            phone = phone[3:]
        elif phone.startswith("91") and len(phone) == 12:
            phone = phone[2:]

        try:
            headers = {
                "authkey": self.auth_key,
                "Content-Type": "application/json"
            }
            payload = {
                "template_id": template_id,
                "sender": self.sender_id,
                "mobiles": f"91{phone}",
                **variables
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.base_url,
                    json=payload,
                    headers=headers,
                    timeout=10.0
                )

                if response.status_code == 200:
                    logger.info(f"SMS sent to {phone}")
                    return True
                else:
                    logger.error(f"SMS failed: {response.text}")
                    return False

        except Exception as e:
            logger.error(f"Failed to send SMS to {phone}: {e}")
            return False

    async def send_order_confirmation_sms(
        self,
        phone: str,
        template_id: str,
        order_number: str,
        amount: Decimal
    ) -> bool:
        """Send order confirmation SMS."""
        return await self.send_sms(
            phone,
            template_id,
            {
                "VAR1": order_number,
                "VAR2": f"{float(amount):,.0f}"
            }
        )

    async def send_order_shipped_sms(
        self,
        phone: str,
        template_id: str,
        order_number: str,
        tracking_number: str,
        courier_name: str
    ) -> bool:
        """Send order shipped SMS."""
        return await self.send_sms(
            phone,
            template_id,
            {
                "VAR1": order_number,
                "VAR2": courier_name,
                "VAR3": tracking_number
            }
        )

    async def send_otp_sms(
        self,
        phone: str,
        template_id: str,
        otp: str
    ) -> bool:
        """Send OTP SMS for customer authentication."""
        return await self.send_sms(
            phone,
            template_id,
            {"VAR1": otp}
        )


# Create a default instance (will be configured via environment variables)
def get_email_service() -> EmailService:
    """Get configured email service instance."""
    from app.config import settings

    return EmailService(
        smtp_host=getattr(settings, 'SMTP_HOST', 'smtp.gmail.com'),
        smtp_port=getattr(settings, 'SMTP_PORT', 587),
        smtp_user=getattr(settings, 'SMTP_USER', ''),
        smtp_password=getattr(settings, 'SMTP_PASSWORD', ''),
        from_email=getattr(settings, 'SMTP_FROM_EMAIL', ''),
        from_name=getattr(settings, 'SMTP_FROM_NAME', 'Aquapurite ERP')
    )


def get_sms_service() -> SMSService:
    """Get configured SMS service instance."""
    from app.config import settings

    return SMSService(
        auth_key=getattr(settings, 'MSG91_AUTH_KEY', ''),
        sender_id=getattr(settings, 'MSG91_SENDER_ID', 'AQUAPU')
    )


# ==================== NOTIFICATION HELPER ====================

async def send_order_notifications(
    order_number: str,
    customer_email: Optional[str],
    customer_phone: str,
    customer_name: str,
    total_amount: Decimal,
    items: List[Dict],
    shipping_address: Dict,
    payment_method: str,
    expected_delivery: Optional[str] = None
):
    """
    Send all order confirmation notifications (email + SMS).

    This is the main function to call after order creation/payment confirmation.
    """
    from app.config import settings

    email_service = get_email_service()
    sms_service = get_sms_service()

    d2c_url = getattr(settings, 'D2C_FRONTEND_URL', 'https://www.aquapurite.com')

    # Send email if provided
    if customer_email:
        email_service.send_order_confirmation_email(
            to_email=customer_email,
            order_number=order_number,
            customer_name=customer_name,
            total_amount=total_amount,
            items=items,
            shipping_address=shipping_address,
            payment_method=payment_method,
            expected_delivery=expected_delivery,
            d2c_url=d2c_url
        )

    # Send SMS
    template_id = getattr(settings, 'MSG91_TEMPLATE_ID_ORDER_CONFIRMED', '')
    if template_id:
        await sms_service.send_order_confirmation_sms(
            phone=customer_phone,
            template_id=template_id,
            order_number=order_number,
            amount=total_amount
        )


async def send_shipment_notifications(
    order_number: str,
    customer_email: Optional[str],
    customer_phone: str,
    customer_name: str,
    tracking_number: str,
    courier_name: str,
    tracking_url: Optional[str] = None,
    expected_delivery: Optional[str] = None
):
    """
    Send shipment notifications (email + SMS).
    """
    from app.config import settings

    email_service = get_email_service()
    sms_service = get_sms_service()

    d2c_url = getattr(settings, 'D2C_FRONTEND_URL', 'https://www.aquapurite.com')

    # Send email if provided
    if customer_email:
        email_service.send_order_shipped_email(
            to_email=customer_email,
            order_number=order_number,
            customer_name=customer_name,
            tracking_number=tracking_number,
            courier_name=courier_name,
            tracking_url=tracking_url,
            expected_delivery=expected_delivery,
            d2c_url=d2c_url
        )

    # Send SMS
    template_id = getattr(settings, 'MSG91_TEMPLATE_ID_ORDER_SHIPPED', '')
    if template_id:
        await sms_service.send_order_shipped_sms(
            phone=customer_phone,
            template_id=template_id,
            order_number=order_number,
            tracking_number=tracking_number,
            courier_name=courier_name
        )
