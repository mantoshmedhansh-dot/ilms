"""
Payment Service - Razorpay Integration

Handles payment processing for the D2C storefront:
- Create Razorpay orders
- Verify payment signatures
- Handle payment callbacks
- Refund processing
"""

import logging
import hmac
import hashlib
from typing import Optional, Dict, Any
from datetime import datetime
import uuid

import razorpay
from pydantic import BaseModel

from app.config import settings

logger = logging.getLogger(__name__)


class PaymentOrderRequest(BaseModel):
    """Request to create a payment order."""
    order_id: uuid.UUID
    amount: float  # In INR
    currency: str = "INR"
    customer_email: Optional[str] = None
    customer_phone: str
    customer_name: str
    notes: Optional[Dict[str, str]] = None


class PaymentOrderResponse(BaseModel):
    """Response after creating a payment order."""
    razorpay_order_id: str
    amount: int  # In paise
    currency: str
    key_id: str
    order_id: uuid.UUID
    customer_name: str
    customer_email: Optional[str] = None
    customer_phone: str
    notes: Dict[str, str]


class PaymentVerificationRequest(BaseModel):
    """Request to verify payment after completion."""
    razorpay_order_id: str
    razorpay_payment_id: str
    razorpay_signature: str
    order_id: uuid.UUID


class PaymentVerificationResponse(BaseModel):
    """Response after payment verification."""
    verified: bool
    order_id: uuid.UUID
    payment_id: str
    message: str
    amount: Optional[int] = None
    status: Optional[str] = None


class RefundRequest(BaseModel):
    """Request to initiate a refund."""
    payment_id: str
    amount: Optional[float] = None  # Partial refund amount in INR
    notes: Optional[Dict[str, str]] = None


class RefundResponse(BaseModel):
    """Response after refund initiation."""
    refund_id: str
    payment_id: str
    amount: int  # In paise
    status: str
    created_at: datetime


class PaymentService:
    """
    Service for handling Razorpay payments.
    """

    def __init__(self):
        """Initialize Razorpay client."""
        self.client = razorpay.Client(
            auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
        )
        self.key_id = settings.RAZORPAY_KEY_ID
        self.key_secret = settings.RAZORPAY_KEY_SECRET

    def create_order(self, request: PaymentOrderRequest) -> PaymentOrderResponse:
        """
        Create a Razorpay order for payment.

        Args:
            request: Payment order request with amount and customer details

        Returns:
            PaymentOrderResponse with Razorpay order details
        """
        try:
            # Convert amount to paise (Razorpay uses smallest currency unit)
            amount_in_paise = int(request.amount * 100)

            # Prepare order data
            notes = {
                "order_id": str(request.order_id),
                "customer_name": request.customer_name,
                **(request.notes or {})
            }
            if request.customer_email:
                notes["customer_email"] = request.customer_email

            order_data = {
                "amount": amount_in_paise,
                "currency": request.currency,
                "receipt": str(request.order_id),
                "notes": notes
            }

            # Create order with Razorpay
            razorpay_order = self.client.order.create(data=order_data)

            logger.info(
                f"Created Razorpay order {razorpay_order['id']} "
                f"for order {request.order_id}"
            )

            return PaymentOrderResponse(
                razorpay_order_id=razorpay_order["id"],
                amount=amount_in_paise,
                currency=request.currency,
                key_id=self.key_id,
                order_id=request.order_id,
                customer_name=request.customer_name,
                customer_email=request.customer_email,
                customer_phone=request.customer_phone,
                notes=razorpay_order.get("notes", {})
            )

        except Exception as e:
            logger.error(f"Failed to create Razorpay order: {e}")
            raise

    def verify_payment(self, request: PaymentVerificationRequest) -> PaymentVerificationResponse:
        """
        Verify payment signature from Razorpay.

        Args:
            request: Payment verification request with signature

        Returns:
            PaymentVerificationResponse indicating success/failure
        """
        try:
            # Construct the signature payload
            payload = f"{request.razorpay_order_id}|{request.razorpay_payment_id}"

            # Generate expected signature
            expected_signature = hmac.new(
                self.key_secret.encode(),
                payload.encode(),
                hashlib.sha256
            ).hexdigest()

            # Compare signatures
            signature_valid = hmac.compare_digest(
                expected_signature,
                request.razorpay_signature
            )

            if not signature_valid:
                logger.warning(
                    f"Invalid payment signature for order {request.order_id}"
                )
                return PaymentVerificationResponse(
                    verified=False,
                    order_id=request.order_id,
                    payment_id=request.razorpay_payment_id,
                    message="Invalid payment signature"
                )

            # Fetch payment details from Razorpay
            payment = self.client.payment.fetch(request.razorpay_payment_id)

            logger.info(
                f"Payment verified successfully: {request.razorpay_payment_id} "
                f"for order {request.order_id}"
            )

            return PaymentVerificationResponse(
                verified=True,
                order_id=request.order_id,
                payment_id=request.razorpay_payment_id,
                message="Payment verified successfully",
                amount=payment.get("amount"),
                status=payment.get("status")
            )

        except Exception as e:
            logger.error(f"Payment verification failed: {e}")
            return PaymentVerificationResponse(
                verified=False,
                order_id=request.order_id,
                payment_id=request.razorpay_payment_id,
                message=f"Verification failed: {str(e)}"
            )

    def capture_payment(self, payment_id: str, amount: int) -> Dict[str, Any]:
        """
        Capture an authorized payment.

        Args:
            payment_id: Razorpay payment ID
            amount: Amount to capture in paise

        Returns:
            Payment capture response
        """
        try:
            response = self.client.payment.capture(payment_id, amount)
            logger.info(f"Payment captured: {payment_id}")
            return response
        except Exception as e:
            logger.error(f"Payment capture failed: {e}")
            raise

    def initiate_refund(self, request: RefundRequest) -> RefundResponse:
        """
        Initiate a refund for a payment.

        Args:
            request: Refund request with payment ID and optional amount

        Returns:
            RefundResponse with refund details
        """
        try:
            refund_data = {
                "notes": request.notes or {}
            }

            if request.amount:
                # Partial refund
                refund_data["amount"] = int(request.amount * 100)

            refund = self.client.payment.refund(
                request.payment_id,
                refund_data
            )

            logger.info(
                f"Refund initiated: {refund['id']} for payment {request.payment_id}"
            )

            return RefundResponse(
                refund_id=refund["id"],
                payment_id=request.payment_id,
                amount=refund["amount"],
                status=refund["status"],
                created_at=datetime.fromtimestamp(refund["created_at"])
            )

        except Exception as e:
            logger.error(f"Refund initiation failed: {e}")
            raise

    def get_payment_status(self, payment_id: str) -> Dict[str, Any]:
        """
        Get current status of a payment.

        Args:
            payment_id: Razorpay payment ID

        Returns:
            Payment details from Razorpay
        """
        try:
            payment = self.client.payment.fetch(payment_id)
            return {
                "id": payment["id"],
                "amount": payment["amount"],
                "currency": payment["currency"],
                "status": payment["status"],
                "method": payment.get("method"),
                "email": payment.get("email"),
                "contact": payment.get("contact"),
                "created_at": datetime.fromtimestamp(payment["created_at"]),
                "captured": payment.get("captured", False),
                "order_id": payment.get("order_id"),
            }
        except Exception as e:
            logger.error(f"Failed to fetch payment status: {e}")
            raise

    def get_order_payments(self, razorpay_order_id: str) -> list:
        """
        Get all payments for a Razorpay order.

        Args:
            razorpay_order_id: Razorpay order ID

        Returns:
            List of payments for the order
        """
        try:
            payments = self.client.order.payments(razorpay_order_id)
            return payments.get("items", [])
        except Exception as e:
            logger.error(f"Failed to fetch order payments: {e}")
            raise

    def verify_webhook_signature(self, body: bytes, signature: str) -> bool:
        """
        Verify Razorpay webhook signature.

        Args:
            body: Raw request body bytes
            signature: X-Razorpay-Signature header value

        Returns:
            True if signature is valid, False otherwise
        """
        webhook_secret = settings.RAZORPAY_WEBHOOK_SECRET

        if not webhook_secret:
            logger.warning("Webhook secret not configured")
            return False

        try:
            # Generate expected signature
            expected_signature = hmac.new(
                webhook_secret.encode(),
                body,
                hashlib.sha256
            ).hexdigest()

            # Compare signatures (constant-time comparison)
            is_valid = hmac.compare_digest(expected_signature, signature)

            if not is_valid:
                logger.warning("Invalid webhook signature")

            return is_valid

        except Exception as e:
            logger.error(f"Webhook signature verification failed: {e}")
            return False

    def fetch_payment(self, payment_id: str) -> Dict[str, Any]:
        """
        Fetch full payment details from Razorpay.

        Args:
            payment_id: Razorpay payment ID

        Returns:
            Full payment details
        """
        try:
            return self.client.payment.fetch(payment_id)
        except Exception as e:
            logger.error(f"Failed to fetch payment {payment_id}: {e}")
            raise


# Webhook event types
class WebhookEvent:
    """Razorpay webhook event types."""
    PAYMENT_AUTHORIZED = "payment.authorized"
    PAYMENT_CAPTURED = "payment.captured"
    PAYMENT_FAILED = "payment.failed"
    ORDER_PAID = "order.paid"
    REFUND_CREATED = "refund.created"
    REFUND_PROCESSED = "refund.processed"
    REFUND_FAILED = "refund.failed"


class WebhookPayload(BaseModel):
    """Razorpay webhook payload structure."""
    entity: str
    account_id: str
    event: str
    contains: list
    payload: Dict[str, Any]
    created_at: int
