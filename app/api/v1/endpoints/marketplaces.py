"""API endpoints for Marketplace Integration (Amazon, Flipkart, etc.)."""
from typing import Optional, List
from uuid import UUID
from datetime import datetime, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.api.deps import DB, get_current_user
from app.schemas.marketplace import (
    MarketplaceCredentials,
    MarketplaceIntegrationResponse,
    SyncOrdersRequest,
    SyncInventoryRequest,
    ShipmentUpdateRequest,
    SyncResult,
)
from app.services.marketplace_service import (
    MarketplaceService,
    MarketplaceType,
    MarketplaceError
)
from app.services.encryption_service import encrypt_value
from app.core.module_decorators import require_module

router = APIRouter()


# ==================== Marketplace Configuration ====================

@router.post("/integrations", status_code=status.HTTP_201_CREATED)
@require_module("sales_distribution")
async def create_marketplace_integration(
    credentials: MarketplaceCredentials,
    db: DB,
    company_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_user),
):
    """
    Set up a new marketplace integration.

    Supported marketplaces:
    - AMAZON: Requires client_id, client_secret, refresh_token
    - FLIPKART: Requires client_id, client_secret
    - MEESHO: Requires api_key
    - SNAPDEAL: Requires client_id, client_secret
    """
    from app.models.channel import MarketplaceIntegration

    effective_company_id = company_id or current_user.company_id

    if not effective_company_id:
        raise HTTPException(status_code=400, detail="Company ID is required")

    # Validate marketplace type
    try:
        marketplace = MarketplaceType(credentials.marketplace_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid marketplace type. Supported: {[m.value for m in MarketplaceType]}"
        )

    # Check if integration already exists
    existing = await db.execute(
        select(MarketplaceIntegration).where(
            and_(
                MarketplaceIntegration.company_id == effective_company_id,
                MarketplaceIntegration.marketplace_type == marketplace.value
            )
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail=f"{marketplace.value} integration already exists. Use PUT to update."
        )

    # Create integration with encrypted credentials
    integration = MarketplaceIntegration(
        company_id=effective_company_id,
        marketplace_type=marketplace.value,
        client_id=credentials.client_id,
        client_secret=encrypt_value(credentials.client_secret) if credentials.client_secret else None,
        refresh_token=encrypt_value(credentials.refresh_token) if credentials.refresh_token else None,
        api_key=encrypt_value(credentials.api_key) if credentials.api_key else None,
        seller_id=credentials.seller_id,
        is_sandbox=credentials.is_sandbox,
        is_active=True,
        created_by=current_user.id,
    )

    db.add(integration)
    await db.commit()
    await db.refresh(integration)

    return {
        "success": True,
        "message": f"{marketplace.value} integration created successfully",
        "integration_id": str(integration.id),
        "is_sandbox": integration.is_sandbox
    }


@router.get("/integrations")
@require_module("sales_distribution")
async def list_marketplace_integrations(
    db: DB,
    company_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_user),
):
    """List all marketplace integrations for a company."""
    from app.models.channel import MarketplaceIntegration

    effective_company_id = company_id or current_user.company_id

    if not effective_company_id:
        raise HTTPException(status_code=400, detail="Company ID is required")

    result = await db.execute(
        select(MarketplaceIntegration).where(
            MarketplaceIntegration.company_id == effective_company_id
        )
    )
    integrations = result.scalars().all()

    return [
        {
            "id": str(i.id),
            "marketplace_type": i.marketplace_type,
            "client_id": i.client_id,
            "seller_id": i.seller_id,
            "is_sandbox": i.is_sandbox,
            "is_active": i.is_active,
            "last_sync_at": i.last_sync_at,
            "created_at": i.created_at,
        }
        for i in integrations
    ]


@router.put("/integrations/{marketplace_type}")
@require_module("sales_distribution")
async def update_marketplace_integration(
    marketplace_type: str,
    credentials: MarketplaceCredentials,
    db: DB,
    company_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_user),
):
    """Update marketplace integration credentials."""
    from app.models.channel import MarketplaceIntegration

    effective_company_id = company_id or current_user.company_id

    if not effective_company_id:
        raise HTTPException(status_code=400, detail="Company ID is required")

    result = await db.execute(
        select(MarketplaceIntegration).where(
            and_(
                MarketplaceIntegration.company_id == effective_company_id,
                MarketplaceIntegration.marketplace_type == marketplace_type.upper()
            )
        )
    )
    integration = result.scalar_one_or_none()

    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")

    # Update credentials
    if credentials.client_id:
        integration.client_id = credentials.client_id
    if credentials.client_secret:
        integration.client_secret = encrypt_value(credentials.client_secret)
    if credentials.refresh_token:
        integration.refresh_token = encrypt_value(credentials.refresh_token)
    if credentials.api_key:
        integration.api_key = encrypt_value(credentials.api_key)
    if credentials.seller_id:
        integration.seller_id = credentials.seller_id

    integration.is_sandbox = credentials.is_sandbox

    await db.commit()

    return {"success": True, "message": "Integration updated successfully"}


@router.delete("/integrations/{marketplace_type}")
@require_module("sales_distribution")
async def delete_marketplace_integration(
    marketplace_type: str,
    db: DB,
    company_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_user),
):
    """Delete marketplace integration."""
    from app.models.channel import MarketplaceIntegration

    effective_company_id = company_id or current_user.company_id

    if not effective_company_id:
        raise HTTPException(status_code=400, detail="Company ID is required")

    result = await db.execute(
        select(MarketplaceIntegration).where(
            and_(
                MarketplaceIntegration.company_id == effective_company_id,
                MarketplaceIntegration.marketplace_type == marketplace_type.upper()
            )
        )
    )
    integration = result.scalar_one_or_none()

    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")

    await db.delete(integration)
    await db.commit()

    return {"success": True, "message": f"{marketplace_type} integration deleted"}


@router.post("/integrations/{marketplace_type}/toggle")
@require_module("sales_distribution")
async def toggle_marketplace_integration(
    marketplace_type: str,
    db: DB,
    is_active: bool = True,
    company_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_user),
):
    """Enable or disable marketplace integration."""
    from app.models.channel import MarketplaceIntegration

    effective_company_id = company_id or current_user.company_id

    if not effective_company_id:
        raise HTTPException(status_code=400, detail="Company ID is required")

    result = await db.execute(
        select(MarketplaceIntegration).where(
            and_(
                MarketplaceIntegration.company_id == effective_company_id,
                MarketplaceIntegration.marketplace_type == marketplace_type.upper()
            )
        )
    )
    integration = result.scalar_one_or_none()

    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")

    integration.is_active = is_active
    await db.commit()

    return {
        "success": True,
        "message": f"{marketplace_type} integration {'enabled' if is_active else 'disabled'}"
    }


# ==================== Order Sync ====================

@router.post("/orders/sync/{marketplace_type}", response_model=SyncResult)
@require_module("sales_distribution")
async def sync_marketplace_orders(
    marketplace_type: str,
    sync_request: SyncOrdersRequest,
    db: DB,
    background_tasks: BackgroundTasks,
    company_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_user),
):
    """
    Sync orders from marketplace.

    Orders are imported and mapped to internal Order model.
    """
    try:
        marketplace = MarketplaceType(marketplace_type.upper())
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid marketplace. Supported: {[m.value for m in MarketplaceType]}"
        )

    effective_company_id = company_id or current_user.company_id

    if not effective_company_id:
        raise HTTPException(status_code=400, detail="Company ID is required")

    try:
        service = MarketplaceService(db, effective_company_id)
        result = await service.sync_orders(
            marketplace=marketplace,
            from_date=sync_request.from_date
        )

        return SyncResult(
            success=True,
            marketplace=marketplace.value,
            message=f"Synced {result['total_orders']} orders from {marketplace.value}",
            details=result
        )

    except MarketplaceError as e:
        return SyncResult(
            success=False,
            marketplace=marketplace.value,
            message=f"Order sync failed: {e.message}",
            details=e.details
        )


# ==================== Inventory Sync ====================

@router.post("/inventory/sync/{marketplace_type}", response_model=SyncResult)
@require_module("sales_distribution")
async def sync_inventory_to_marketplace(
    marketplace_type: str,
    sync_request: SyncInventoryRequest,
    db: DB,
    company_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_user),
):
    """
    Sync inventory levels to marketplace.

    Updates stock quantities for listed products.
    """
    try:
        marketplace = MarketplaceType(marketplace_type.upper())
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid marketplace. Supported: {[m.value for m in MarketplaceType]}"
        )

    effective_company_id = company_id or current_user.company_id

    if not effective_company_id:
        raise HTTPException(status_code=400, detail="Company ID is required")

    try:
        service = MarketplaceService(db, effective_company_id)
        result = await service.sync_inventory(
            marketplace=marketplace,
            products=sync_request.products
        )

        return SyncResult(
            success=True,
            marketplace=marketplace.value,
            message=f"Updated inventory for {result['products_updated']} products",
            details=result
        )

    except MarketplaceError as e:
        return SyncResult(
            success=False,
            marketplace=marketplace.value,
            message=f"Inventory sync failed: {e.message}",
            details=e.details
        )


# ==================== Shipment Updates ====================

@router.post("/shipments/update/{marketplace_type}", response_model=SyncResult)
@require_module("sales_distribution")
async def update_marketplace_shipment(
    marketplace_type: str,
    shipment_request: ShipmentUpdateRequest,
    db: DB,
    company_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_user),
):
    """
    Update shipment tracking on marketplace.

    Marks orders as shipped with tracking information.
    """
    try:
        marketplace = MarketplaceType(marketplace_type.upper())
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid marketplace. Supported: {[m.value for m in MarketplaceType]}"
        )

    effective_company_id = company_id or current_user.company_id

    if not effective_company_id:
        raise HTTPException(status_code=400, detail="Company ID is required")

    try:
        service = MarketplaceService(db, effective_company_id)
        result = await service.update_shipment(
            marketplace=marketplace,
            order_id=shipment_request.order_id,
            tracking_id=shipment_request.tracking_id,
            courier=shipment_request.courier
        )

        return SyncResult(
            success=True,
            marketplace=marketplace.value,
            message=f"Shipment updated for order {shipment_request.order_id}",
            details=result
        )

    except MarketplaceError as e:
        return SyncResult(
            success=False,
            marketplace=marketplace.value,
            message=f"Shipment update failed: {e.message}",
            details=e.details
        )


# ==================== Test Connection ====================

@router.post("/integrations/{marketplace_type}/test")
@require_module("sales_distribution")
async def test_marketplace_connection(
    marketplace_type: str,
    db: DB,
    company_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_user),
):
    """
    Test connection to marketplace.

    Attempts to authenticate with stored credentials.
    """
    try:
        marketplace = MarketplaceType(marketplace_type.upper())
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid marketplace. Supported: {[m.value for m in MarketplaceType]}"
        )

    effective_company_id = company_id or current_user.company_id

    if not effective_company_id:
        raise HTTPException(status_code=400, detail="Company ID is required")

    try:
        service = MarketplaceService(db, effective_company_id)

        if marketplace == MarketplaceType.AMAZON:
            client = await service.get_amazon_client()
            # Test by getting access token
            await client._get_access_token()
            return {
                "success": True,
                "marketplace": "AMAZON",
                "message": "Successfully authenticated with Amazon SP-API",
                "is_sandbox": client.is_sandbox
            }

        elif marketplace == MarketplaceType.FLIPKART:
            client = await service.get_flipkart_client()
            await client._get_access_token()
            return {
                "success": True,
                "marketplace": "FLIPKART",
                "message": "Successfully authenticated with Flipkart Seller API",
                "is_sandbox": client.is_sandbox
            }

        else:
            return {
                "success": False,
                "marketplace": marketplace.value,
                "message": f"Test connection not implemented for {marketplace.value}"
            }

    except MarketplaceError as e:
        return {
            "success": False,
            "marketplace": marketplace.value,
            "message": f"Connection test failed: {e.message}",
            "error": str(e)
        }
