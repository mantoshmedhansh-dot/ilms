"""
Shiprocket Integration Service.

Handles all Shiprocket API interactions:
- Authentication (token management with auto-refresh)
- Order creation and management
- AWB generation
- Shipment tracking
- Courier serviceability check
- Webhook processing

API Docs: https://apidocs.shiprocket.in/
"""
import httpx
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass
from enum import Enum

from app.config import settings
from app.services.cache_service import get_cache

logger = logging.getLogger(__name__)

# Cache key for Shiprocket auth token
SHIPROCKET_TOKEN_CACHE_KEY = "shiprocket:auth_token"
SHIPROCKET_TOKEN_TTL = 86400  # 24 hours (token valid for 10 days, refresh daily)


class ShiprocketOrderStatus(str, Enum):
    """Shiprocket order/shipment status codes."""
    NEW = "NEW"
    AWB_ASSIGNED = "AWB Assigned"
    PICKUP_SCHEDULED = "Pickup Scheduled"
    PICKUP_QUEUED = "Pickup Queued"
    PICKUP_GENERATED = "Pickup Generated"
    PICKUP_PENDING = "Pickup Pending"
    PICKED_UP = "Picked Up"
    IN_TRANSIT = "In Transit"
    OUT_FOR_DELIVERY = "Out For Delivery"
    DELIVERED = "Delivered"
    CANCELLED = "Canceled"
    RTO_INITIATED = "RTO Initiated"
    RTO_IN_TRANSIT = "RTO In-Transit"
    RTO_DELIVERED = "RTO Delivered"
    LOST = "Lost"
    DAMAGED = "Damaged"
    UNDELIVERED = "Undelivered"


@dataclass
class ShiprocketAddress:
    """Address structure for Shiprocket API."""
    name: str
    phone: str
    address: str
    city: str
    state: str
    pincode: str
    country: str = "India"
    address_2: str = ""
    email: str = ""
    company_name: str = ""


@dataclass
class ShiprocketOrderItem:
    """Order item structure for Shiprocket API."""
    name: str
    sku: str
    units: int
    selling_price: float
    hsn: str = ""
    discount: float = 0
    tax: float = 0


@dataclass
class ShiprocketOrderRequest:
    """Order creation request for Shiprocket."""
    order_id: str
    order_date: str  # YYYY-MM-DD HH:MM
    billing_address: ShiprocketAddress
    shipping_address: ShiprocketAddress
    items: List[ShiprocketOrderItem]
    payment_method: str  # "Prepaid" or "COD"
    sub_total: float
    shipping_charges: float = 0
    giftwrap_charges: float = 0
    transaction_charges: float = 0
    total_discount: float = 0
    pickup_location: str = ""
    channel_id: str = ""
    comment: str = ""
    length: float = 10  # cm
    breadth: float = 10  # cm
    height: float = 10  # cm
    weight: float = 0.5  # kg


@dataclass
class CourierServiceability:
    """Courier serviceability result."""
    courier_id: int
    courier_name: str
    courier_code: str
    rate: float
    estimated_days: int
    cod_available: bool
    city: str
    state: str
    postcode: str
    region: str
    zone: str
    etd: str  # Estimated delivery date
    performance_score: float = 0


@dataclass
class TrackingInfo:
    """Shipment tracking information."""
    awb_code: str
    courier_name: str
    current_status: str
    current_status_id: int
    shipment_status: str
    delivered_date: Optional[str] = None
    pickup_date: Optional[str] = None
    etd: Optional[str] = None
    activities: List[Dict] = None

    def __post_init__(self):
        if self.activities is None:
            self.activities = []


class ShiprocketService:
    """
    Service for Shiprocket API integration.

    Usage:
        service = ShiprocketService()

        # Create order
        order = await service.create_order(order_request)

        # Generate AWB
        awb = await service.generate_awb(shipment_id, courier_id)

        # Track shipment
        tracking = await service.track_shipment(awb_code)
    """

    def __init__(self):
        self.base_url = settings.SHIPROCKET_API_URL
        self.email = settings.SHIPROCKET_EMAIL
        self.password = settings.SHIPROCKET_PASSWORD
        self.cache = get_cache()
        self._token: Optional[str] = None

    async def _get_token(self) -> str:
        """
        Get authentication token (with caching).

        Shiprocket tokens are valid for 10 days.
        We cache for 24 hours and refresh automatically.
        """
        # Check cache first
        cached_token = await self.cache.get(SHIPROCKET_TOKEN_CACHE_KEY)
        if cached_token:
            return cached_token

        # Generate new token
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/auth/login",
                json={
                    "email": self.email,
                    "password": self.password
                },
                timeout=30.0
            )

            if response.status_code != 200:
                logger.error(f"Shiprocket auth failed: {response.text}")
                raise Exception(f"Shiprocket authentication failed: {response.status_code}")

            data = response.json()
            token = data.get("token")

            if not token:
                raise Exception("No token in Shiprocket auth response")

            # Cache the token
            await self.cache.set(SHIPROCKET_TOKEN_CACHE_KEY, token, ttl=SHIPROCKET_TOKEN_TTL)

            return token

    async def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None
    ) -> Dict:
        """Make authenticated request to Shiprocket API."""
        token = await self._get_token()

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        async with httpx.AsyncClient() as client:
            if method.upper() == "GET":
                response = await client.get(url, headers=headers, params=params, timeout=30.0)
            elif method.upper() == "POST":
                response = await client.post(url, headers=headers, json=data, timeout=30.0)
            elif method.upper() == "PUT":
                response = await client.put(url, headers=headers, json=data, timeout=30.0)
            elif method.upper() == "PATCH":
                response = await client.patch(url, headers=headers, json=data, timeout=30.0)
            elif method.upper() == "DELETE":
                response = await client.delete(url, headers=headers, timeout=30.0)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            # Handle errors
            if response.status_code >= 400:
                logger.error(f"Shiprocket API error: {response.status_code} - {response.text}")
                error_data = response.json() if response.text else {}
                raise ShiprocketAPIError(
                    status_code=response.status_code,
                    message=error_data.get("message", response.text),
                    errors=error_data.get("errors", {})
                )

            return response.json() if response.text else {}

    # ==================== ORDER MANAGEMENT ====================

    async def create_order(self, order: ShiprocketOrderRequest) -> Dict:
        """
        Create a new order in Shiprocket.

        Returns:
            Dict with order_id, shipment_id, status, etc.
        """
        # Build order items
        order_items = []
        for item in order.items:
            order_items.append({
                "name": item.name,
                "sku": item.sku,
                "units": item.units,
                "selling_price": str(item.selling_price),
                "discount": str(item.discount),
                "tax": str(item.tax),
                "hsn": item.hsn or ""
            })

        payload = {
            "order_id": order.order_id,
            "order_date": order.order_date,
            "pickup_location": order.pickup_location or settings.SHIPROCKET_DEFAULT_PICKUP_LOCATION,
            "billing_customer_name": order.billing_address.name,
            "billing_last_name": "",
            "billing_address": order.billing_address.address,
            "billing_address_2": order.billing_address.address_2,
            "billing_city": order.billing_address.city,
            "billing_pincode": order.billing_address.pincode,
            "billing_state": order.billing_address.state,
            "billing_country": order.billing_address.country,
            "billing_email": order.billing_address.email,
            "billing_phone": order.billing_address.phone,
            "shipping_is_billing": self._is_same_address(order.billing_address, order.shipping_address),
            "shipping_customer_name": order.shipping_address.name,
            "shipping_last_name": "",
            "shipping_address": order.shipping_address.address,
            "shipping_address_2": order.shipping_address.address_2,
            "shipping_city": order.shipping_address.city,
            "shipping_pincode": order.shipping_address.pincode,
            "shipping_state": order.shipping_address.state,
            "shipping_country": order.shipping_address.country,
            "shipping_email": order.shipping_address.email,
            "shipping_phone": order.shipping_address.phone,
            "order_items": order_items,
            "payment_method": order.payment_method,
            "sub_total": order.sub_total,
            "length": order.length,
            "breadth": order.breadth,
            "height": order.height,
            "weight": order.weight,
        }

        # Add optional fields
        if order.shipping_charges:
            payload["shipping_charges"] = order.shipping_charges
        if order.giftwrap_charges:
            payload["giftwrap_charges"] = order.giftwrap_charges
        if order.total_discount:
            payload["total_discount"] = order.total_discount
        if order.comment:
            payload["comment"] = order.comment
        if order.channel_id:
            payload["channel_id"] = order.channel_id

        result = await self._request("POST", "/orders/create/adhoc", data=payload)

        logger.info(f"Shiprocket order created: {result.get('order_id')} -> Shipment: {result.get('shipment_id')}")

        return result

    async def get_order(self, order_id: str) -> Dict:
        """Get order details by Shiprocket order ID."""
        return await self._request("GET", f"/orders/show/{order_id}")

    async def cancel_order(self, order_ids: List[int]) -> Dict:
        """
        Cancel orders in Shiprocket.

        Args:
            order_ids: List of Shiprocket order IDs (not your order numbers)
        """
        return await self._request("POST", "/orders/cancel", data={"ids": order_ids})

    # ==================== AWB & SHIPMENT ====================

    async def generate_awb(self, shipment_id: int, courier_id: Optional[int] = None) -> Dict:
        """
        Generate AWB for a shipment.

        Args:
            shipment_id: Shiprocket shipment ID
            courier_id: Optional courier ID. If not provided, auto-assigns best courier.

        Returns:
            Dict with awb_code, courier_name, etc.
        """
        payload = {"shipment_id": shipment_id}

        if courier_id:
            payload["courier_id"] = courier_id

        result = await self._request("POST", "/courier/assign/awb", data=payload)

        logger.info(f"AWB generated for shipment {shipment_id}: {result.get('response', {}).get('data', {}).get('awb_code')}")

        return result

    async def request_pickup(self, shipment_id: int) -> Dict:
        """
        Request pickup for a shipment.

        Call this after AWB is generated.
        """
        return await self._request("POST", "/courier/generate/pickup", data={
            "shipment_id": [shipment_id]
        })

    async def generate_manifest(self, shipment_ids: List[int]) -> Dict:
        """Generate manifest for multiple shipments."""
        return await self._request("POST", "/manifests/generate", data={
            "shipment_id": shipment_ids
        })

    async def print_label(self, shipment_ids: List[int]) -> Dict:
        """Get shipping label PDF URL for shipments."""
        return await self._request("POST", "/courier/generate/label", data={
            "shipment_id": shipment_ids
        })

    async def print_invoice(self, order_ids: List[int]) -> Dict:
        """Get invoice PDF URL for orders."""
        return await self._request("POST", "/orders/print/invoice", data={
            "ids": order_ids
        })

    # ==================== TRACKING ====================

    async def track_shipment(self, awb_code: str) -> TrackingInfo:
        """
        Track shipment by AWB code.

        Returns:
            TrackingInfo with current status and activities
        """
        result = await self._request("GET", f"/courier/track/awb/{awb_code}")

        tracking_data = result.get("tracking_data", {})
        shipment_track = tracking_data.get("shipment_track", [{}])[0] if tracking_data.get("shipment_track") else {}
        activities = tracking_data.get("shipment_track_activities", [])

        return TrackingInfo(
            awb_code=awb_code,
            courier_name=shipment_track.get("courier_name", ""),
            current_status=shipment_track.get("current_status", ""),
            current_status_id=shipment_track.get("current_status_id", 0),
            shipment_status=tracking_data.get("track_status", ""),
            delivered_date=shipment_track.get("delivered_date"),
            pickup_date=shipment_track.get("pickup_date"),
            etd=shipment_track.get("etd"),
            activities=[
                {
                    "date": act.get("date"),
                    "activity": act.get("activity"),
                    "location": act.get("location"),
                    "sr_status": act.get("sr-status"),
                    "sr_status_label": act.get("sr-status-label"),
                }
                for act in activities
            ]
        )

    async def track_by_order_id(self, order_id: str) -> Dict:
        """Track shipment by your order ID (channel order ID)."""
        return await self._request("GET", f"/courier/track", params={"order_id": order_id})

    async def track_multiple(self, awb_codes: List[str]) -> Dict:
        """Track multiple shipments at once."""
        return await self._request("GET", "/courier/track/awbs", params={
            "awbs": ",".join(awb_codes)
        })

    # ==================== COURIER SERVICEABILITY ====================

    async def check_serviceability(
        self,
        pickup_pincode: str,
        delivery_pincode: str,
        weight: float = 0.5,
        cod: bool = False,
        order_value: float = 0
    ) -> List[CourierServiceability]:
        """
        Check courier serviceability for a route.

        Args:
            pickup_pincode: Origin pincode
            delivery_pincode: Destination pincode
            weight: Package weight in kg
            cod: Whether COD is required
            order_value: Order value (for COD)

        Returns:
            List of available couriers sorted by rate
        """
        params = {
            "pickup_postcode": pickup_pincode,
            "delivery_postcode": delivery_pincode,
            "weight": weight,
            "cod": 1 if cod else 0,
        }

        if cod and order_value:
            params["declared_value"] = order_value

        result = await self._request("GET", "/courier/serviceability/", params=params)

        couriers = []
        available = result.get("data", {}).get("available_courier_companies", [])

        for courier in available:
            couriers.append(CourierServiceability(
                courier_id=courier.get("courier_company_id"),
                courier_name=courier.get("courier_name"),
                courier_code=courier.get("courier_code", ""),
                rate=float(courier.get("rate", 0)),
                estimated_days=int(courier.get("estimated_delivery_days", 5)),
                cod_available=courier.get("cod", 0) == 1,
                city=courier.get("city", ""),
                state=courier.get("state", ""),
                postcode=courier.get("postcode", ""),
                region=courier.get("region", ""),
                zone=courier.get("zone", ""),
                etd=courier.get("etd", ""),
                performance_score=float(courier.get("rating", 0))
            ))

        # Sort by rate (cheapest first)
        couriers.sort(key=lambda x: x.rate)

        return couriers

    async def get_recommended_courier(
        self,
        pickup_pincode: str,
        delivery_pincode: str,
        weight: float = 0.5,
        cod: bool = False,
        order_value: float = 0,
        strategy: str = "BALANCED"
    ) -> Optional[CourierServiceability]:
        """
        Get recommended courier based on strategy.

        Strategies:
            - CHEAPEST: Lowest rate
            - FASTEST: Shortest delivery time
            - BALANCED: Best price/performance ratio
            - BEST_RATING: Highest performance score
        """
        couriers = await self.check_serviceability(
            pickup_pincode=pickup_pincode,
            delivery_pincode=delivery_pincode,
            weight=weight,
            cod=cod,
            order_value=order_value
        )

        if not couriers:
            return None

        if strategy == "CHEAPEST":
            return min(couriers, key=lambda x: x.rate)
        elif strategy == "FASTEST":
            return min(couriers, key=lambda x: x.estimated_days)
        elif strategy == "BEST_RATING":
            return max(couriers, key=lambda x: x.performance_score)
        else:  # BALANCED
            # Score = (1/rate) * 100 + (1/days) * 50 + rating * 10
            def score(c):
                rate_score = (1 / max(c.rate, 1)) * 100
                speed_score = (1 / max(c.estimated_days, 1)) * 50
                rating_score = c.performance_score * 10
                return rate_score + speed_score + rating_score

            return max(couriers, key=score)

    # ==================== PICKUP LOCATIONS ====================

    async def get_pickup_locations(self) -> List[Dict]:
        """Get all configured pickup locations."""
        result = await self._request("GET", "/settings/company/pickup")
        return result.get("data", {}).get("shipping_address", [])

    async def add_pickup_location(
        self,
        pickup_location: str,
        name: str,
        email: str,
        phone: str,
        address: str,
        city: str,
        state: str,
        pincode: str,
        country: str = "India"
    ) -> Dict:
        """Add a new pickup location."""
        return await self._request("POST", "/settings/company/addpickup", data={
            "pickup_location": pickup_location,
            "name": name,
            "email": email,
            "phone": phone,
            "address": address,
            "city": city,
            "state": state,
            "pin_code": pincode,
            "country": country
        })

    # ==================== RETURNS (NDR/RTO) ====================

    async def get_ndr_shipments(self) -> List[Dict]:
        """Get shipments in NDR (Non-Delivery Report) status."""
        result = await self._request("GET", "/orders/ndr")
        return result.get("data", [])

    async def submit_ndr_action(
        self,
        awb: str,
        action: str,  # "re-attempt", "return", "fake-delivery"
        comments: str = ""
    ) -> Dict:
        """
        Submit NDR action for a shipment.

        Args:
            awb: AWB code
            action: "re-attempt", "return", or "fake-delivery"
            comments: Optional comments
        """
        return await self._request("POST", "/orders/ndr/action", data={
            "awb": awb,
            "action": action,
            "comments": comments
        })

    # ==================== HELPERS ====================

    def _is_same_address(self, addr1: ShiprocketAddress, addr2: ShiprocketAddress) -> bool:
        """Check if two addresses are the same."""
        return (
            addr1.address == addr2.address and
            addr1.city == addr2.city and
            addr1.pincode == addr2.pincode
        )


class ShiprocketAPIError(Exception):
    """Shiprocket API error."""

    def __init__(self, status_code: int, message: str, errors: Dict = None):
        self.status_code = status_code
        self.message = message
        self.errors = errors or {}
        super().__init__(f"Shiprocket API Error ({status_code}): {message}")


# ==================== HELPER FUNCTIONS ====================

async def push_order_to_shiprocket(
    order_id: str,
    order_number: str,
    order_date: datetime,
    customer_name: str,
    customer_phone: str,
    customer_email: str,
    shipping_address: Dict,
    billing_address: Optional[Dict],
    items: List[Dict],
    payment_method: str,
    subtotal: float,
    shipping_charges: float = 0,
    discount: float = 0,
    weight_kg: float = 0.5,
    dimensions: Optional[Dict] = None,
    pickup_location: str = ""
) -> Dict:
    """
    Helper function to push an order to Shiprocket.

    Args:
        order_id: Your internal order ID
        order_number: Order number to display
        order_date: Order creation datetime
        customer_name: Customer full name
        customer_phone: Customer phone (10 digits)
        customer_email: Customer email
        shipping_address: {address, city, state, pincode}
        billing_address: Optional billing address (defaults to shipping)
        items: List of {name, sku, quantity, price, hsn}
        payment_method: "PREPAID" or "COD"
        subtotal: Order subtotal
        shipping_charges: Shipping charges
        discount: Total discount
        weight_kg: Package weight
        dimensions: {length, breadth, height} in cm
        pickup_location: Pickup location name

    Returns:
        Shiprocket response with order_id, shipment_id
    """
    service = ShiprocketService()

    # Use shipping as billing if not provided
    if not billing_address:
        billing_address = shipping_address

    # Build addresses
    ship_addr = ShiprocketAddress(
        name=customer_name,
        phone=customer_phone,
        email=customer_email,
        address=shipping_address.get("address_line1", "") + " " + shipping_address.get("address_line2", ""),
        city=shipping_address.get("city", ""),
        state=shipping_address.get("state", ""),
        pincode=shipping_address.get("pincode", ""),
        country=shipping_address.get("country", "India")
    )

    bill_addr = ShiprocketAddress(
        name=customer_name,
        phone=customer_phone,
        email=customer_email,
        address=billing_address.get("address_line1", "") + " " + billing_address.get("address_line2", ""),
        city=billing_address.get("city", ""),
        state=billing_address.get("state", ""),
        pincode=billing_address.get("pincode", ""),
        country=billing_address.get("country", "India")
    )

    # Build order items
    order_items = [
        ShiprocketOrderItem(
            name=item.get("name", "Product"),
            sku=item.get("sku", f"SKU-{i}"),
            units=item.get("quantity", 1),
            selling_price=float(item.get("price", 0)),
            hsn=item.get("hsn", ""),
            tax=float(item.get("tax", 0)),
            discount=float(item.get("discount", 0))
        )
        for i, item in enumerate(items)
    ]

    # Build dimensions
    dims = dimensions or {}

    # Create order request
    order_request = ShiprocketOrderRequest(
        order_id=order_number,
        order_date=order_date.strftime("%Y-%m-%d %H:%M"),
        billing_address=bill_addr,
        shipping_address=ship_addr,
        items=order_items,
        payment_method="Prepaid" if payment_method.upper() == "PREPAID" else "COD",
        sub_total=subtotal,
        shipping_charges=shipping_charges,
        total_discount=discount,
        pickup_location=pickup_location or settings.SHIPROCKET_DEFAULT_PICKUP_LOCATION,
        length=dims.get("length", 20),
        breadth=dims.get("breadth", 15),
        height=dims.get("height", 10),
        weight=weight_kg
    )

    return await service.create_order(order_request)


async def auto_ship_order(
    order_id: str,
    order_number: str,
    order_date: datetime,
    customer_name: str,
    customer_phone: str,
    customer_email: str,
    shipping_address: Dict,
    items: List[Dict],
    payment_method: str,
    subtotal: float,
    pickup_pincode: str,
    weight_kg: float = 0.5,
    courier_strategy: str = "BALANCED"
) -> Dict:
    """
    Create order, auto-assign best courier, and generate AWB in one call.

    Returns:
        Dict with order_id, shipment_id, awb_code, courier_name
    """
    service = ShiprocketService()

    # 1. Create order
    order_result = await push_order_to_shiprocket(
        order_id=order_id,
        order_number=order_number,
        order_date=order_date,
        customer_name=customer_name,
        customer_phone=customer_phone,
        customer_email=customer_email,
        shipping_address=shipping_address,
        billing_address=None,
        items=items,
        payment_method=payment_method,
        subtotal=subtotal,
        weight_kg=weight_kg
    )

    shipment_id = order_result.get("shipment_id")

    if not shipment_id:
        return order_result

    # 2. Get recommended courier
    delivery_pincode = shipping_address.get("pincode", "")
    recommended = await service.get_recommended_courier(
        pickup_pincode=pickup_pincode,
        delivery_pincode=delivery_pincode,
        weight=weight_kg,
        cod=payment_method.upper() == "COD",
        order_value=subtotal if payment_method.upper() == "COD" else 0,
        strategy=courier_strategy
    )

    courier_id = recommended.courier_id if recommended else None

    # 3. Generate AWB
    awb_result = await service.generate_awb(shipment_id, courier_id)

    awb_data = awb_result.get("response", {}).get("data", {})

    return {
        "order_id": order_result.get("order_id"),
        "shipment_id": shipment_id,
        "awb_code": awb_data.get("awb_code"),
        "courier_company_id": awb_data.get("courier_company_id"),
        "courier_name": awb_data.get("courier_name"),
        "applied_weight": awb_data.get("applied_weight"),
        "label_url": awb_result.get("label_url"),
    }
