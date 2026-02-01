"""
D2C Customer Authentication API Endpoints

OTP-based authentication for D2C storefront customers.
Supports both:
- httpOnly cookie-based auth (secure, recommended)
- Bearer token auth (for backward compatibility)
"""

import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, HTTPException, status, Depends, Response, Request, Cookie
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
import jwt

from app.database import get_db
from app.config import settings
from app.models.customer import Customer, CustomerAddress
from app.models.customer_otp import CustomerOTP
from app.models.order import Order
from app.models.wishlist import WishlistItem
from app.models.product import Product, ProductImage
from app.services.otp_service import OTPService, send_otp_sms
from app.services.captcha_service import verify_turnstile_token
from app.schemas.d2c_auth import (
    SendOTPRequest,
    SendOTPResponse,
    VerifyOTPRequest,
    VerifyOTPResponse,
    CustomerProfile,
    CustomerAddress as CustomerAddressSchema,
    UpdateProfileRequest,
    AddAddressRequest,
    CustomerOrderSummary,
    CustomerOrdersResponse,
    WishlistItemResponse,
    WishlistResponse,
    AddToWishlistRequest,
    ChangePhoneRequest,
    VerifyPhoneChangeRequest,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/d2c/auth", tags=["D2C Authentication"])
security = HTTPBearer(auto_error=False)

# JWT Configuration for D2C customers
D2C_TOKEN_EXPIRE_HOURS = 24 * 7  # 7 days
D2C_REFRESH_TOKEN_EXPIRE_DAYS = 30

# Cookie Configuration
ACCESS_TOKEN_COOKIE = "d2c_access_token"
REFRESH_TOKEN_COOKIE = "d2c_refresh_token"
COOKIE_DOMAIN = None  # Set via settings in production
COOKIE_SECURE = True  # Always use secure in production
COOKIE_SAMESITE = "lax"  # Allows cookie to be sent on top-level navigations


def set_auth_cookies(response: Response, access_token: str, refresh_token: str):
    """Set httpOnly authentication cookies."""
    # Access token cookie - shorter expiry
    response.set_cookie(
        key=ACCESS_TOKEN_COOKIE,
        value=access_token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        max_age=D2C_TOKEN_EXPIRE_HOURS * 3600,
        path="/",
    )
    # Refresh token cookie - longer expiry
    response.set_cookie(
        key=REFRESH_TOKEN_COOKIE,
        value=refresh_token,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite=COOKIE_SAMESITE,
        max_age=D2C_REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600,
        path="/api/v1/d2c/auth",  # Only sent to auth endpoints
    )


def clear_auth_cookies(response: Response):
    """Clear authentication cookies on logout."""
    response.delete_cookie(
        key=ACCESS_TOKEN_COOKIE,
        path="/",
    )
    response.delete_cookie(
        key=REFRESH_TOKEN_COOKIE,
        path="/api/v1/d2c/auth",
    )


def create_customer_token(customer_id: str) -> str:
    """Create JWT access token for customer."""
    payload = {
        "sub": customer_id,
        "type": "d2c_customer",
        "exp": datetime.now(timezone.utc) + timedelta(hours=D2C_TOKEN_EXPIRE_HOURS),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(customer_id: str) -> str:
    """Create JWT refresh token for customer."""
    payload = {
        "sub": customer_id,
        "type": "d2c_refresh",
        "exp": datetime.now(timezone.utc) + timedelta(days=D2C_REFRESH_TOKEN_EXPIRE_DAYS),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_customer_token(token: str) -> Optional[str]:
    """Decode and validate customer token."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") not in ("d2c_customer", "d2c_refresh"):
            return None
        return payload.get("sub")
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


async def get_current_customer(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> Optional[Customer]:
    """
    Get current authenticated customer.
    Supports both:
    1. httpOnly cookie (preferred, more secure)
    2. Bearer token in Authorization header (backward compatible)
    """
    token = None

    # Priority 1: Check httpOnly cookie
    cookie_token = request.cookies.get(ACCESS_TOKEN_COOKIE)
    if cookie_token:
        token = cookie_token

    # Priority 2: Fall back to Authorization header
    if not token and credentials:
        token = credentials.credentials

    if not token:
        return None

    customer_id = decode_customer_token(token)
    if not customer_id:
        return None

    try:
        result = await db.execute(
            select(Customer)
            .where(Customer.id == uuid.UUID(customer_id))
            .options(selectinload(Customer.addresses))
        )
        return result.scalar_one_or_none()
    except Exception:
        return None


async def require_customer(
    customer: Optional[Customer] = Depends(get_current_customer),
) -> Customer:
    """Require authenticated customer."""
    if not customer:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return customer


def generate_customer_code(phone: str) -> str:
    """Generate unique customer code from phone."""
    # Use last 6 digits of phone + random suffix
    return f"C{phone[-6:]}{uuid.uuid4().hex[:4].upper()}"


@router.post("/send-otp", response_model=SendOTPResponse)
async def send_otp(
    request: SendOTPRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Send OTP to customer phone number.
    Works for both login and registration.
    Requires CAPTCHA verification to prevent SMS bombing.
    """
    # Verify CAPTCHA token first (prevents SMS bombing attacks)
    client_ip = http_request.client.host if http_request.client else None
    captcha_valid = await verify_turnstile_token(request.captcha_token, client_ip)

    if not captcha_valid:
        logger.warning(f"CAPTCHA verification failed for phone {request.phone[-4:].rjust(10, '*')}")
        return SendOTPResponse(
            success=False,
            message="CAPTCHA verification failed. Please try again.",
            expires_in_seconds=0,
            resend_in_seconds=0,
        )

    otp_service = OTPService(db)

    # Check cooldown
    can_resend, remaining = await otp_service.can_resend_otp(request.phone)
    if not can_resend:
        return SendOTPResponse(
            success=False,
            message=f"Please wait {remaining} seconds before requesting a new OTP",
            expires_in_seconds=0,
            resend_in_seconds=remaining,
        )

    # Create and send OTP
    otp_code, otp_record = await otp_service.create_otp(request.phone, purpose="LOGIN")

    # Send via SMS
    sms_sent = await send_otp_sms(request.phone, otp_code)

    if not sms_sent:
        logger.error(f"Failed to send OTP SMS to {request.phone[-4:].rjust(10, '*')}")
        # Still return success since OTP was created (SMS might be delayed)

    return SendOTPResponse(
        success=True,
        message="OTP sent successfully",
        expires_in_seconds=otp_service.OTP_EXPIRY_MINUTES * 60,
        resend_in_seconds=otp_service.RESEND_COOLDOWN_SECONDS,
    )


@router.post("/verify-otp", response_model=VerifyOTPResponse)
async def verify_otp(
    request: VerifyOTPRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """
    Verify OTP and authenticate customer.
    Creates a new customer if phone is not registered.
    """
    otp_service = OTPService(db)

    # Verify OTP
    success, message = await otp_service.verify_otp(request.phone, request.otp, purpose="LOGIN")

    if not success:
        return VerifyOTPResponse(
            success=False,
            message=message,
        )

    # Check if customer exists
    result = await db.execute(
        select(Customer)
        .where(Customer.phone == request.phone)
        .options(selectinload(Customer.addresses))
    )
    customer = result.scalar_one_or_none()

    is_new_customer = False

    if not customer:
        # Create new customer
        customer = Customer(
            customer_code=generate_customer_code(request.phone),
            first_name="Customer",  # Will be updated by user
            phone=request.phone,
            source="WEBSITE",
            customer_type="INDIVIDUAL",
            is_verified=True,
            is_active=True,
        )
        db.add(customer)
        await db.commit()
        await db.refresh(customer)
        is_new_customer = True
        logger.info(f"New D2C customer created: {customer.customer_code}")
    else:
        # Update verification status if needed
        if not customer.is_verified:
            customer.is_verified = True
            await db.commit()

    # Generate tokens
    access_token = create_customer_token(str(customer.id))
    refresh_token = create_refresh_token(str(customer.id))

    # Set httpOnly cookies for secure authentication
    set_auth_cookies(response, access_token, refresh_token)

    # Also return tokens in response for backward compatibility
    # Frontend can choose to use cookies (secure) or tokens (legacy)
    return VerifyOTPResponse(
        success=True,
        message="Login successful",
        access_token=access_token,
        refresh_token=refresh_token,
        customer=CustomerProfile(
            id=str(customer.id),
            phone=customer.phone,
            email=customer.email,
            first_name=customer.first_name,
            last_name=customer.last_name,
            is_verified=customer.is_verified,
        ),
        is_new_customer=is_new_customer,
    )


@router.post("/refresh-token")
async def refresh_access_token(
    request: Request,
    response: Response,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
):
    """
    Refresh access token using refresh token.
    Supports both cookie and header-based refresh tokens.
    """
    token = None

    # Priority 1: Check httpOnly cookie
    cookie_token = request.cookies.get(REFRESH_TOKEN_COOKIE)
    if cookie_token:
        token = cookie_token

    # Priority 2: Fall back to Authorization header
    if not token and credentials:
        token = credentials.credentials

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token required",
        )

    customer_id = decode_customer_token(token)
    if not customer_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    # Verify customer exists
    result = await db.execute(
        select(Customer).where(Customer.id == uuid.UUID(customer_id))
    )
    customer = result.scalar_one_or_none()

    if not customer or not customer.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Customer not found or inactive",
        )

    # Generate new tokens
    access_token = create_customer_token(str(customer.id))
    new_refresh_token = create_refresh_token(str(customer.id))

    # Set new cookies
    set_auth_cookies(response, access_token, new_refresh_token)

    # Also return token in response for backward compatibility
    return {
        "access_token": access_token,
        "token_type": "bearer",
    }


@router.get("/me", response_model=CustomerProfile)
async def get_profile(
    customer: Customer = Depends(require_customer),
):
    """Get current customer profile."""
    return CustomerProfile(
        id=str(customer.id),
        phone=customer.phone,
        email=customer.email,
        first_name=customer.first_name,
        last_name=customer.last_name,
        is_verified=customer.is_verified,
    )


@router.put("/me", response_model=CustomerProfile)
async def update_profile(
    request: UpdateProfileRequest,
    customer: Customer = Depends(require_customer),
    db: AsyncSession = Depends(get_db),
):
    """Update customer profile."""
    if request.first_name is not None:
        customer.first_name = request.first_name
    if request.last_name is not None:
        customer.last_name = request.last_name
    if request.email is not None:
        customer.email = request.email

    await db.commit()
    await db.refresh(customer)

    return CustomerProfile(
        id=str(customer.id),
        phone=customer.phone,
        email=customer.email,
        first_name=customer.first_name,
        last_name=customer.last_name,
        is_verified=customer.is_verified,
    )


@router.post("/change-phone/request", response_model=SendOTPResponse)
async def request_phone_change(
    request: ChangePhoneRequest,
    customer: Customer = Depends(require_customer),
    db: AsyncSession = Depends(get_db),
):
    """
    Request to change phone number - Step 1.
    Sends OTP to the new phone number for verification.
    """
    # Check if new phone is same as current
    if request.new_phone == customer.phone:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New phone number must be different from current",
        )

    # Check if new phone is already registered to another customer
    existing = await db.execute(
        select(Customer).where(
            Customer.phone == request.new_phone,
            Customer.id != customer.id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This phone number is already registered to another account",
        )

    otp_service = OTPService(db)

    # Check cooldown
    can_resend, remaining = await otp_service.can_resend_otp(request.new_phone)
    if not can_resend:
        return SendOTPResponse(
            success=False,
            message=f"Please wait {remaining} seconds before requesting a new OTP",
            expires_in_seconds=0,
            resend_in_seconds=remaining,
        )

    # Create and send OTP with PHONE_CHANGE purpose
    otp_code, otp_record = await otp_service.create_otp(request.new_phone, purpose="PHONE_CHANGE")

    # Send via SMS
    sms_sent = await send_otp_sms(request.new_phone, otp_code)

    if not sms_sent:
        logger.error(f"Failed to send phone change OTP SMS to {request.new_phone[-4:].rjust(10, '*')}")

    return SendOTPResponse(
        success=True,
        message="OTP sent to new phone number",
        expires_in_seconds=otp_service.OTP_EXPIRY_MINUTES * 60,
        resend_in_seconds=otp_service.RESEND_COOLDOWN_SECONDS,
    )


@router.post("/change-phone/verify", response_model=CustomerProfile)
async def verify_phone_change(
    request: VerifyPhoneChangeRequest,
    customer: Customer = Depends(require_customer),
    db: AsyncSession = Depends(get_db),
):
    """
    Verify phone change - Step 2.
    Verifies OTP and updates customer's phone number.
    """
    otp_service = OTPService(db)

    # Verify OTP
    success, message = await otp_service.verify_otp(
        request.new_phone, request.otp, purpose="PHONE_CHANGE"
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message,
        )

    # Check again that new phone isn't already registered
    existing = await db.execute(
        select(Customer).where(
            Customer.phone == request.new_phone,
            Customer.id != customer.id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This phone number is already registered to another account",
        )

    # Update phone number
    old_phone = customer.phone
    customer.phone = request.new_phone
    await db.commit()
    await db.refresh(customer)

    logger.info(f"Customer {customer.customer_code} changed phone from {old_phone[-4:].rjust(10, '*')} to {request.new_phone[-4:].rjust(10, '*')}")

    return CustomerProfile(
        id=str(customer.id),
        phone=customer.phone,
        email=customer.email,
        first_name=customer.first_name,
        last_name=customer.last_name,
        is_verified=customer.is_verified,
    )


@router.get("/addresses", response_model=list[CustomerAddressSchema])
async def get_addresses(
    customer: Customer = Depends(require_customer),
    db: AsyncSession = Depends(get_db),
):
    """Get customer addresses."""
    result = await db.execute(
        select(CustomerAddress)
        .where(
            CustomerAddress.customer_id == customer.id,
            CustomerAddress.is_active == True,
        )
        .order_by(CustomerAddress.is_default.desc(), CustomerAddress.created_at.desc())
    )
    addresses = result.scalars().all()

    return [
        CustomerAddressSchema(
            id=str(addr.id),
            address_type=addr.address_type,
            contact_name=addr.contact_name,
            contact_phone=addr.contact_phone,
            address_line1=addr.address_line1,
            address_line2=addr.address_line2,
            landmark=addr.landmark,
            city=addr.city,
            state=addr.state,
            pincode=addr.pincode,
            country=addr.country,
            is_default=addr.is_default,
        )
        for addr in addresses
    ]


@router.post("/addresses", response_model=CustomerAddressSchema)
async def add_address(
    request: AddAddressRequest,
    customer: Customer = Depends(require_customer),
    db: AsyncSession = Depends(get_db),
):
    """Add a new address."""
    # If this is set as default, unset other defaults
    if request.is_default:
        await db.execute(
            select(CustomerAddress)
            .where(CustomerAddress.customer_id == customer.id)
        )
        result = await db.execute(
            select(CustomerAddress)
            .where(CustomerAddress.customer_id == customer.id, CustomerAddress.is_default == True)
        )
        for addr in result.scalars().all():
            addr.is_default = False

    # Create new address
    address = CustomerAddress(
        customer_id=customer.id,
        address_type=request.address_type,
        contact_name=request.contact_name,
        contact_phone=request.contact_phone,
        address_line1=request.address_line1,
        address_line2=request.address_line2,
        landmark=request.landmark,
        city=request.city,
        state=request.state,
        pincode=request.pincode,
        country=request.country,
        is_default=request.is_default,
    )

    db.add(address)
    await db.commit()
    await db.refresh(address)

    return CustomerAddressSchema(
        id=str(address.id),
        address_type=address.address_type,
        contact_name=address.contact_name,
        contact_phone=address.contact_phone,
        address_line1=address.address_line1,
        address_line2=address.address_line2,
        landmark=address.landmark,
        city=address.city,
        state=address.state,
        pincode=address.pincode,
        country=address.country,
        is_default=address.is_default,
    )


@router.put("/addresses/{address_id}", response_model=CustomerAddressSchema)
async def update_address(
    address_id: uuid.UUID,
    request: AddAddressRequest,
    customer: Customer = Depends(require_customer),
    db: AsyncSession = Depends(get_db),
):
    """Update an existing address."""
    result = await db.execute(
        select(CustomerAddress)
        .where(
            CustomerAddress.id == address_id,
            CustomerAddress.customer_id == customer.id,
            CustomerAddress.is_active == True,
        )
    )
    address = result.scalar_one_or_none()

    if not address:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Address not found",
        )

    # If setting as default, unset other defaults
    if request.is_default and not address.is_default:
        other_result = await db.execute(
            select(CustomerAddress)
            .where(
                CustomerAddress.customer_id == customer.id,
                CustomerAddress.is_default == True,
                CustomerAddress.id != address_id,
            )
        )
        for addr in other_result.scalars().all():
            addr.is_default = False

    # Update fields
    address.address_type = request.address_type
    address.contact_name = request.contact_name
    address.contact_phone = request.contact_phone
    address.address_line1 = request.address_line1
    address.address_line2 = request.address_line2
    address.landmark = request.landmark
    address.city = request.city
    address.state = request.state
    address.pincode = request.pincode
    address.country = request.country
    address.is_default = request.is_default

    await db.commit()
    await db.refresh(address)

    return CustomerAddressSchema(
        id=str(address.id),
        address_type=address.address_type,
        contact_name=address.contact_name,
        contact_phone=address.contact_phone,
        address_line1=address.address_line1,
        address_line2=address.address_line2,
        landmark=address.landmark,
        city=address.city,
        state=address.state,
        pincode=address.pincode,
        country=address.country,
        is_default=address.is_default,
    )


@router.put("/addresses/{address_id}/default", response_model=CustomerAddressSchema)
async def set_default_address(
    address_id: uuid.UUID,
    customer: Customer = Depends(require_customer),
    db: AsyncSession = Depends(get_db),
):
    """Set an address as the default."""
    result = await db.execute(
        select(CustomerAddress)
        .where(
            CustomerAddress.id == address_id,
            CustomerAddress.customer_id == customer.id,
            CustomerAddress.is_active == True,
        )
    )
    address = result.scalar_one_or_none()

    if not address:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Address not found",
        )

    # Unset other defaults
    other_result = await db.execute(
        select(CustomerAddress)
        .where(
            CustomerAddress.customer_id == customer.id,
            CustomerAddress.is_default == True,
            CustomerAddress.id != address_id,
        )
    )
    for addr in other_result.scalars().all():
        addr.is_default = False

    # Set this as default
    address.is_default = True
    await db.commit()
    await db.refresh(address)

    return CustomerAddressSchema(
        id=str(address.id),
        address_type=address.address_type,
        contact_name=address.contact_name,
        contact_phone=address.contact_phone,
        address_line1=address.address_line1,
        address_line2=address.address_line2,
        landmark=address.landmark,
        city=address.city,
        state=address.state,
        pincode=address.pincode,
        country=address.country,
        is_default=address.is_default,
    )


@router.delete("/addresses/{address_id}")
async def delete_address(
    address_id: uuid.UUID,
    customer: Customer = Depends(require_customer),
    db: AsyncSession = Depends(get_db),
):
    """Delete an address."""
    result = await db.execute(
        select(CustomerAddress)
        .where(
            CustomerAddress.id == address_id,
            CustomerAddress.customer_id == customer.id,
        )
    )
    address = result.scalar_one_or_none()

    if not address:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Address not found",
        )

    address.is_active = False
    await db.commit()

    return {"message": "Address deleted"}


@router.get("/orders", response_model=CustomerOrdersResponse)
async def get_orders(
    page: int = 1,
    size: int = 10,
    customer: Customer = Depends(require_customer),
    db: AsyncSession = Depends(get_db),
):
    """Get customer orders."""
    offset = (page - 1) * size

    # Get total count
    count_result = await db.execute(
        select(func.count(Order.id))
        .where(Order.customer_id == customer.id)
    )
    total = count_result.scalar() or 0

    # Get orders
    result = await db.execute(
        select(Order)
        .where(Order.customer_id == customer.id)
        .order_by(Order.created_at.desc())
        .offset(offset)
        .limit(size)
    )
    orders = result.scalars().all()

    return CustomerOrdersResponse(
        orders=[
            CustomerOrderSummary(
                id=str(order.id),
                order_number=order.order_number,
                status=order.status,
                total_amount=float(order.grand_total),
                created_at=order.created_at,
                items_count=len(order.items) if order.items else 0,
            )
            for order in orders
        ],
        total=total,
        page=page,
        size=size,
    )


@router.get("/orders/{order_number}")
async def get_order_detail(
    order_number: str,
    customer: Customer = Depends(require_customer),
    db: AsyncSession = Depends(get_db),
):
    """Get order details by order number."""
    from sqlalchemy.orm import selectinload

    result = await db.execute(
        select(Order)
        .where(
            Order.order_number == order_number,
            Order.customer_id == customer.id,
        )
        .options(selectinload(Order.items))
    )
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    return {
        "id": str(order.id),
        "order_number": order.order_number,
        "status": order.status,
        "payment_status": order.payment_status,
        "payment_method": order.payment_method,
        "subtotal": float(order.subtotal),
        "tax_amount": float(order.tax_amount),
        "shipping_amount": float(order.shipping_amount) if order.shipping_amount else 0,
        "discount_amount": float(order.discount_amount) if order.discount_amount else 0,
        "grand_total": float(order.grand_total),
        "created_at": order.created_at.isoformat(),
        "shipped_at": order.shipped_at.isoformat() if order.shipped_at else None,
        "delivered_at": order.delivered_at.isoformat() if order.delivered_at else None,
        "shipping_address": order.shipping_address if order.shipping_address else {},
        "items": [
            {
                "id": str(item.id),
                "product_name": item.product_name,
                "sku": item.sku,
                "quantity": item.quantity,
                "unit_price": float(item.unit_price),
                "total_price": float(item.total_amount),
            }
            for item in (order.items or [])
        ],
        "tracking_number": order.awb_code,  # AWB code is the tracking number
        "courier_name": order.courier_name,
    }


@router.get("/wishlist", response_model=WishlistResponse)
async def get_wishlist(
    customer: Customer = Depends(require_customer),
    db: AsyncSession = Depends(get_db),
):
    """Get customer's wishlist."""
    result = await db.execute(
        select(WishlistItem)
        .where(WishlistItem.customer_id == customer.id)
        .options(
            selectinload(WishlistItem.product).selectinload(Product.images)
        )
        .order_by(WishlistItem.created_at.desc())
    )
    items = result.scalars().all()

    wishlist_items = []
    for item in items:
        product = item.product
        if not product or not product.is_active:
            continue

        # Get primary image
        primary_image = None
        if product.images:
            for img in product.images:
                if img.is_primary:
                    primary_image = img.image_url
                    break
            if not primary_image and product.images:
                primary_image = product.images[0].image_url

        # Check if price dropped
        price_dropped = False
        if item.price_when_added and product.selling_price:
            price_dropped = float(product.selling_price) < float(item.price_when_added)

        wishlist_items.append(WishlistItemResponse(
            id=str(item.id),
            product_id=str(product.id),
            product_name=product.name,
            product_slug=product.slug,
            product_image=primary_image,
            product_price=float(product.selling_price) if product.selling_price else 0,
            product_mrp=float(product.mrp) if product.mrp else 0,
            variant_id=str(item.variant_id) if item.variant_id else None,
            variant_name=None,  # TODO: Load variant name if needed
            price_when_added=item.price_when_added,
            is_in_stock=product.is_active,  # Simplified stock check
            price_dropped=price_dropped,
            created_at=item.created_at,
        ))

    return WishlistResponse(
        items=wishlist_items,
        total=len(wishlist_items),
    )


@router.post("/wishlist", response_model=WishlistItemResponse)
async def add_to_wishlist(
    request: AddToWishlistRequest,
    customer: Customer = Depends(require_customer),
    db: AsyncSession = Depends(get_db),
):
    """Add a product to wishlist."""
    # Check if product exists
    product_result = await db.execute(
        select(Product)
        .where(Product.id == uuid.UUID(request.product_id), Product.is_active == True)
        .options(selectinload(Product.images))
    )
    product = product_result.scalar_one_or_none()

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    # Check if already in wishlist
    existing = await db.execute(
        select(WishlistItem)
        .where(
            WishlistItem.customer_id == customer.id,
            WishlistItem.product_id == product.id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Product already in wishlist",
        )

    # Create wishlist item
    wishlist_item = WishlistItem(
        customer_id=customer.id,
        product_id=product.id,
        variant_id=uuid.UUID(request.variant_id) if request.variant_id else None,
        price_when_added=float(product.selling_price) if product.selling_price else None,
    )

    db.add(wishlist_item)
    await db.commit()
    await db.refresh(wishlist_item)

    # Get primary image
    primary_image = None
    if product.images:
        for img in product.images:
            if img.is_primary:
                primary_image = img.image_url
                break
        if not primary_image and product.images:
            primary_image = product.images[0].image_url

    return WishlistItemResponse(
        id=str(wishlist_item.id),
        product_id=str(product.id),
        product_name=product.name,
        product_slug=product.slug,
        product_image=primary_image,
        product_price=float(product.selling_price) if product.selling_price else 0,
        product_mrp=float(product.mrp) if product.mrp else 0,
        variant_id=request.variant_id,
        variant_name=None,
        price_when_added=wishlist_item.price_when_added,
        is_in_stock=True,
        price_dropped=False,
        created_at=wishlist_item.created_at,
    )


@router.delete("/wishlist/{product_id}")
async def remove_from_wishlist(
    product_id: uuid.UUID,
    customer: Customer = Depends(require_customer),
    db: AsyncSession = Depends(get_db),
):
    """Remove a product from wishlist."""
    result = await db.execute(
        select(WishlistItem)
        .where(
            WishlistItem.customer_id == customer.id,
            WishlistItem.product_id == product_id,
        )
    )
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not in wishlist",
        )

    await db.delete(item)
    await db.commit()

    return {"message": "Removed from wishlist"}


@router.get("/wishlist/check/{product_id}")
async def check_wishlist(
    product_id: uuid.UUID,
    customer: Optional[Customer] = Depends(get_current_customer),
    db: AsyncSession = Depends(get_db),
):
    """Check if a product is in the customer's wishlist."""
    if not customer:
        return {"in_wishlist": False}

    result = await db.execute(
        select(WishlistItem)
        .where(
            WishlistItem.customer_id == customer.id,
            WishlistItem.product_id == product_id,
        )
    )
    item = result.scalar_one_or_none()

    return {"in_wishlist": item is not None}


@router.post("/logout")
async def logout(
    response: Response,
    customer: Customer = Depends(require_customer),
):
    """
    Logout customer.
    Clears httpOnly authentication cookies.
    """
    clear_auth_cookies(response)
    return {"message": "Logged out successfully"}
