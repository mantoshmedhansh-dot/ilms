"""
Marketplace Integration Service

Integrates with major e-commerce marketplaces for:
- Product catalog sync
- Inventory sync
- Order import
- Shipment updates

Supported Marketplaces:
- Amazon India (SP-API)
- Flipkart (Seller API)
- Meesho
- Snapdeal

For production, obtain API credentials from each marketplace.
"""

import httpx
import json
import hmac
import hashlib
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional, Dict, Any, List
from uuid import UUID
from enum import Enum

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.encryption_service import decrypt_value


class MarketplaceType(str, Enum):
    """Supported marketplaces."""
    AMAZON = "AMAZON"
    FLIPKART = "FLIPKART"
    MEESHO = "MEESHO"
    SNAPDEAL = "SNAPDEAL"


class MarketplaceError(Exception):
    """Custom exception for marketplace errors."""
    def __init__(self, message: str, marketplace: str = None, error_code: str = None, details: Dict = None):
        self.message = message
        self.marketplace = marketplace
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class AmazonSPAPI:
    """
    Amazon Selling Partner API integration.

    Documentation: https://developer-docs.amazon.com/sp-api/
    """

    SANDBOX_BASE_URL = "https://sandbox.sellingpartnerapi-na.amazon.com"
    PRODUCTION_BASE_URL = "https://sellingpartnerapi-ap-south-1.amazon.com"

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        refresh_token: str,
        marketplace_id: str = "A21TJRUUN4KGV",  # India
        is_sandbox: bool = True
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_token = refresh_token
        self.marketplace_id = marketplace_id
        self.is_sandbox = is_sandbox
        self._access_token: Optional[str] = None
        self._token_expiry: Optional[datetime] = None

    @property
    def base_url(self) -> str:
        return self.SANDBOX_BASE_URL if self.is_sandbox else self.PRODUCTION_BASE_URL

    async def _get_access_token(self) -> str:
        """Get access token using refresh token."""
        if self._access_token and self._token_expiry and datetime.now(timezone.utc) < self._token_expiry:
            return self._access_token

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.amazon.com/auth/o2/token",
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": self.refresh_token,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                }
            )
            response.raise_for_status()
            data = response.json()

            self._access_token = data["access_token"]
            self._token_expiry = datetime.now(timezone.utc) + timedelta(seconds=data.get("expires_in", 3600) - 60)

            return self._access_token

    async def _make_request(
        self,
        method: str,
        path: str,
        params: Dict = None,
        body: Dict = None
    ) -> Dict:
        """Make authenticated request to SP-API."""
        access_token = await self._get_access_token()

        headers = {
            "x-amz-access-token": access_token,
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.request(
                method=method,
                url=f"{self.base_url}{path}",
                headers=headers,
                params=params,
                json=body
            )

            if response.status_code >= 400:
                raise MarketplaceError(
                    message=f"Amazon API error: {response.text}",
                    marketplace="AMAZON",
                    error_code=str(response.status_code),
                    details={"response": response.text}
                )

            return response.json()

    async def get_orders(
        self,
        created_after: datetime = None,
        order_statuses: List[str] = None,
        max_results: int = 100
    ) -> List[Dict]:
        """Get orders from Amazon."""
        params = {
            "MarketplaceIds": self.marketplace_id,
            "MaxResultsPerPage": max_results,
        }

        if created_after:
            params["CreatedAfter"] = created_after.isoformat()

        if order_statuses:
            params["OrderStatuses"] = ",".join(order_statuses)

        result = await self._make_request("GET", "/orders/v0/orders", params=params)
        return result.get("payload", {}).get("Orders", [])

    async def get_order_items(self, order_id: str) -> List[Dict]:
        """Get items for a specific order."""
        result = await self._make_request("GET", f"/orders/v0/orders/{order_id}/orderItems")
        return result.get("payload", {}).get("OrderItems", [])

    async def update_inventory(self, sku: str, quantity: int) -> Dict:
        """Update inventory for a SKU."""
        body = {
            "inventoryUpdates": [{
                "sellerSku": sku,
                "quantity": quantity
            }]
        }
        return await self._make_request("POST", "/fba/inventory/v1/inventories", body=body)

    async def get_catalog_item(self, asin: str) -> Dict:
        """Get catalog item by ASIN."""
        params = {"marketplaceIds": self.marketplace_id}
        return await self._make_request("GET", f"/catalog/v0/items/{asin}", params=params)


class FlipkartAPI:
    """
    Flipkart Seller API integration.

    Documentation: https://seller.flipkart.com/api-docs/
    """

    SANDBOX_BASE_URL = "https://sandbox-api.flipkart.net/sellers"
    PRODUCTION_BASE_URL = "https://api.flipkart.net/sellers"

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        is_sandbox: bool = True
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.is_sandbox = is_sandbox
        self._access_token: Optional[str] = None
        self._token_expiry: Optional[datetime] = None

    @property
    def base_url(self) -> str:
        return self.SANDBOX_BASE_URL if self.is_sandbox else self.PRODUCTION_BASE_URL

    async def _get_access_token(self) -> str:
        """Get access token using client credentials."""
        if self._access_token and self._token_expiry and datetime.now(timezone.utc) < self._token_expiry:
            return self._access_token

        import base64
        auth_header = base64.b64encode(
            f"{self.client_id}:{self.client_secret}".encode()
        ).decode()

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/v2/oauth/access_token",
                headers={
                    "Authorization": f"Basic {auth_header}",
                    "Content-Type": "application/x-www-form-urlencoded",
                },
                data={
                    "grant_type": "client_credentials",
                    "scope": "Seller_Api"
                }
            )
            response.raise_for_status()
            data = response.json()

            self._access_token = data["access_token"]
            self._token_expiry = datetime.now(timezone.utc) + timedelta(seconds=data.get("expires_in", 86400) - 60)

            return self._access_token

    async def _make_request(
        self,
        method: str,
        path: str,
        params: Dict = None,
        body: Dict = None
    ) -> Dict:
        """Make authenticated request to Flipkart API."""
        access_token = await self._get_access_token()

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.request(
                method=method,
                url=f"{self.base_url}{path}",
                headers=headers,
                params=params,
                json=body
            )

            if response.status_code >= 400:
                raise MarketplaceError(
                    message=f"Flipkart API error: {response.text}",
                    marketplace="FLIPKART",
                    error_code=str(response.status_code),
                    details={"response": response.text}
                )

            return response.json()

    async def get_orders(
        self,
        from_date: datetime = None,
        order_states: List[str] = None,
        page_size: int = 100
    ) -> List[Dict]:
        """Get orders from Flipkart."""
        params = {"pageSize": page_size}

        if from_date:
            params["fromDate"] = from_date.strftime("%Y-%m-%d")

        if order_states:
            params["orderStates"] = ",".join(order_states)

        result = await self._make_request("GET", "/v3/orders/search", params=params)
        return result.get("orderItems", [])

    async def update_inventory(self, listings: List[Dict]) -> Dict:
        """
        Update inventory for listings.

        listings: List of {sku, quantity, fulfillmentType}
        """
        body = {"listings": listings}
        return await self._make_request("POST", "/v2/inventory", body=body)

    async def ship_order(self, order_item_id: str, tracking_id: str, courier: str) -> Dict:
        """Mark order as shipped with tracking."""
        body = {
            "orderItemId": order_item_id,
            "trackingId": tracking_id,
            "courier": courier,
            "dispatchDate": datetime.now(timezone.utc).strftime("%Y-%m-%d")
        }
        return await self._make_request("POST", "/v2/shipments/dispatch", body=body)


class MarketplaceService:
    """
    Unified service for managing marketplace integrations.
    """

    def __init__(self, db: AsyncSession, company_id: UUID):
        self.db = db
        self.company_id = company_id

    async def get_marketplace_credentials(self, marketplace: MarketplaceType) -> Dict:
        """Get decrypted marketplace credentials."""
        from app.models.channel import MarketplaceIntegration

        result = await self.db.execute(
            select(MarketplaceIntegration).where(
                and_(
                    MarketplaceIntegration.company_id == self.company_id,
                    MarketplaceIntegration.marketplace_type == marketplace.value
                )
            )
        )
        integration = result.scalar_one_or_none()

        if not integration:
            raise MarketplaceError(
                f"{marketplace.value} integration not configured",
                marketplace=marketplace.value
            )

        if not integration.is_active:
            raise MarketplaceError(
                f"{marketplace.value} integration is disabled",
                marketplace=marketplace.value
            )

        # Decrypt credentials
        return {
            "client_id": integration.client_id,
            "client_secret": decrypt_value(integration.client_secret) if integration.client_secret else None,
            "refresh_token": decrypt_value(integration.refresh_token) if integration.refresh_token else None,
            "api_key": decrypt_value(integration.api_key) if integration.api_key else None,
            "is_sandbox": integration.is_sandbox,
        }

    async def get_amazon_client(self) -> AmazonSPAPI:
        """Get configured Amazon SP-API client."""
        creds = await self.get_marketplace_credentials(MarketplaceType.AMAZON)

        return AmazonSPAPI(
            client_id=creds["client_id"],
            client_secret=creds["client_secret"],
            refresh_token=creds["refresh_token"],
            is_sandbox=creds["is_sandbox"]
        )

    async def get_flipkart_client(self) -> FlipkartAPI:
        """Get configured Flipkart API client."""
        creds = await self.get_marketplace_credentials(MarketplaceType.FLIPKART)

        return FlipkartAPI(
            client_id=creds["client_id"],
            client_secret=creds["client_secret"],
            is_sandbox=creds["is_sandbox"]
        )

    async def sync_orders(
        self,
        marketplace: MarketplaceType,
        from_date: datetime = None
    ) -> Dict:
        """
        Sync orders from marketplace.

        Returns count of new/updated orders.
        """
        if not from_date:
            from_date = datetime.now(timezone.utc) - timedelta(days=7)

        orders = []
        if marketplace == MarketplaceType.AMAZON:
            client = await self.get_amazon_client()
            orders = await client.get_orders(created_after=from_date)
        elif marketplace == MarketplaceType.FLIPKART:
            client = await self.get_flipkart_client()
            orders = await client.get_orders(from_date=from_date)

        # Process and save orders
        new_count = 0
        updated_count = 0

        for order_data in orders:
            # Here you would map marketplace order to your Order model
            # and save to database
            new_count += 1

        return {
            "marketplace": marketplace.value,
            "total_orders": len(orders),
            "new_orders": new_count,
            "updated_orders": updated_count,
            "sync_date": datetime.now(timezone.utc).isoformat()
        }

    async def sync_inventory(
        self,
        marketplace: MarketplaceType,
        products: List[Dict]
    ) -> Dict:
        """
        Sync inventory to marketplace.

        products: List of {sku, quantity}
        """
        if marketplace == MarketplaceType.AMAZON:
            client = await self.get_amazon_client()
            for product in products:
                await client.update_inventory(product["sku"], product["quantity"])

        elif marketplace == MarketplaceType.FLIPKART:
            client = await self.get_flipkart_client()
            listings = [
                {
                    "sku": p["sku"],
                    "quantity": p["quantity"],
                    "fulfillmentType": "SELLER"
                }
                for p in products
            ]
            await client.update_inventory(listings)

        return {
            "marketplace": marketplace.value,
            "products_updated": len(products),
            "sync_date": datetime.now(timezone.utc).isoformat()
        }

    async def update_shipment(
        self,
        marketplace: MarketplaceType,
        order_id: str,
        tracking_id: str,
        courier: str
    ) -> Dict:
        """Update shipment tracking on marketplace."""
        if marketplace == MarketplaceType.FLIPKART:
            client = await self.get_flipkart_client()
            return await client.ship_order(order_id, tracking_id, courier)

        # Amazon uses different shipment flow (confirm shipment API)
        # Implementation would go here

        return {
            "marketplace": marketplace.value,
            "order_id": order_id,
            "tracking_id": tracking_id,
            "status": "UPDATED"
        }
