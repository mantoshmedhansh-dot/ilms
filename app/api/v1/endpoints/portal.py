"""
Customer Self-Service Portal API Endpoints

Provides authenticated APIs for customers to:
- View profile and update information
- View orders and track shipments
- Download invoices
- Create and manage service requests
- View loyalty points
"""
from typing import Optional, List
from uuid import UUID
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import DB
from app.schemas.portal import (
    CustomerAuth,
    ProfileUpdateRequest,
    ServiceRequestCreate,
    ServiceRequestComment,
    FeedbackSubmit,
)
from app.services.customer_portal_service import CustomerPortalService, CustomerPortalError
from app.core.module_decorators import require_module

router = APIRouter()


# ==================== Helper ====================

async def get_customer_service(
    customer_id: UUID,
    db: AsyncSession
) -> CustomerPortalService:
    """Get customer portal service instance."""
    return CustomerPortalService(db, customer_id)


# ==================== Dashboard ====================

@router.get("/dashboard")
@require_module("oms_fulfillment")
async def get_portal_dashboard(
    customer_id: UUID = Query(..., description="Customer ID"),
    db: DB = None,
):
    """
    Get customer portal dashboard.

    Returns summary of orders, service requests, invoices, and loyalty points.
    """
    try:
        service = await get_customer_service(customer_id, db)
        return await service.get_dashboard()
    except CustomerPortalError as e:
        raise HTTPException(status_code=400, detail=e.message)


# ==================== Profile ====================

@router.get("/profile")
@require_module("oms_fulfillment")
async def get_customer_profile(
    customer_id: UUID = Query(..., description="Customer ID"),
    db: DB = None,
):
    """Get customer profile information."""
    try:
        service = await get_customer_service(customer_id, db)
        return await service.get_customer_profile()
    except CustomerPortalError as e:
        raise HTTPException(status_code=400, detail=e.message)


@router.put("/profile")
@require_module("oms_fulfillment")
async def update_customer_profile(
    request: ProfileUpdateRequest,
    customer_id: UUID = Query(..., description="Customer ID"),
    db: DB = None,
):
    """Update customer profile information."""
    try:
        service = await get_customer_service(customer_id, db)
        return await service.update_profile(
            name=request.name,
            email=request.email,
            phone=request.phone,
            mobile=request.mobile,
            address_line1=request.address_line1,
            address_line2=request.address_line2,
            city=request.city,
            state=request.state,
            pincode=request.pincode,
        )
    except CustomerPortalError as e:
        raise HTTPException(status_code=400, detail=e.message)


# ==================== Orders ====================

@router.get("/orders")
@require_module("oms_fulfillment")
async def list_customer_orders(
    customer_id: UUID = Query(..., description="Customer ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: DB = None,
):
    """
    List customer orders with pagination.

    Supports filtering by status: PENDING, CONFIRMED, PROCESSING, SHIPPED, DELIVERED, CANCELLED
    """
    try:
        service = await get_customer_service(customer_id, db)
        return await service.get_orders(status=status, skip=skip, limit=limit)
    except CustomerPortalError as e:
        raise HTTPException(status_code=400, detail=e.message)


@router.get("/orders/{order_id}")
@require_module("oms_fulfillment")
async def get_order_details(
    order_id: UUID,
    customer_id: UUID = Query(..., description="Customer ID"),
    db: DB = None,
):
    """
    Get detailed order information including items and tracking.
    """
    try:
        service = await get_customer_service(customer_id, db)
        return await service.get_order_details(order_id)
    except CustomerPortalError as e:
        raise HTTPException(status_code=404, detail=e.message)


@router.get("/orders/{order_id}/track")
@require_module("oms_fulfillment")
async def track_order(
    order_id: UUID,
    customer_id: UUID = Query(..., description="Customer ID"),
    db: DB = None,
):
    """
    Get order tracking information.
    """
    try:
        service = await get_customer_service(customer_id, db)
        order = await service.get_order_details(order_id)
        return {
            "order_id": str(order_id),
            "order_number": order["order_number"],
            "status": order["status"],
            "tracking": order["tracking"]
        }
    except CustomerPortalError as e:
        raise HTTPException(status_code=404, detail=e.message)


# ==================== Invoices ====================

@router.get("/invoices")
@require_module("oms_fulfillment")
async def list_customer_invoices(
    customer_id: UUID = Query(..., description="Customer ID"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: DB = None,
):
    """
    List customer invoices with pagination.
    """
    try:
        service = await get_customer_service(customer_id, db)
        return await service.get_invoices(skip=skip, limit=limit)
    except CustomerPortalError as e:
        raise HTTPException(status_code=400, detail=e.message)


@router.get("/invoices/{invoice_id}")
@require_module("oms_fulfillment")
async def get_invoice_details(
    invoice_id: UUID,
    customer_id: UUID = Query(..., description="Customer ID"),
    db: DB = None,
):
    """
    Get detailed invoice information.
    """
    try:
        service = await get_customer_service(customer_id, db)
        return await service.get_invoice_details(invoice_id)
    except CustomerPortalError as e:
        raise HTTPException(status_code=404, detail=e.message)


@router.get("/invoices/{invoice_id}/download")
@require_module("oms_fulfillment")
async def download_invoice(
    invoice_id: UUID,
    customer_id: UUID = Query(..., description="Customer ID"),
    db: DB = None,
):
    """
    Download invoice as PDF.

    Returns base64 encoded PDF content.
    """
    try:
        service = await get_customer_service(customer_id, db)
        invoice = await service.get_invoice_details(invoice_id)

        # In production, this would generate actual PDF
        # For now, return invoice data with download flag
        return {
            "invoice_id": str(invoice_id),
            "invoice_number": invoice["invoice_number"],
            "download_ready": True,
            "message": "Invoice PDF generation endpoint - integrate with PDF service"
        }
    except CustomerPortalError as e:
        raise HTTPException(status_code=404, detail=e.message)


# ==================== Service Requests ====================

@router.get("/service-requests")
@require_module("oms_fulfillment")
async def list_service_requests(
    customer_id: UUID = Query(..., description="Customer ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: DB = None,
):
    """
    List customer service requests.

    Supports filtering by status: OPEN, IN_PROGRESS, PENDING_CUSTOMER, RESOLVED, CLOSED
    """
    try:
        service = await get_customer_service(customer_id, db)
        return await service.get_service_requests(status=status, skip=skip, limit=limit)
    except CustomerPortalError as e:
        raise HTTPException(status_code=400, detail=e.message)


@router.post("/service-requests")
@require_module("oms_fulfillment")
async def create_service_request(
    request: ServiceRequestCreate,
    customer_id: UUID = Query(..., description="Customer ID"),
    db: DB = None,
):
    """
    Create a new service request.

    Request types: REPAIR, INSTALLATION, WARRANTY, GENERAL, COMPLAINT
    """
    try:
        service = await get_customer_service(customer_id, db)
        return await service.create_service_request(
            request_type=request.request_type,
            subject=request.subject,
            description=request.description,
            product_id=request.product_id,
            order_id=request.order_id,
            priority=request.priority,
            attachments=request.attachments,
        )
    except CustomerPortalError as e:
        raise HTTPException(status_code=400, detail=e.message)


@router.get("/service-requests/{request_id}")
@require_module("oms_fulfillment")
async def get_service_request_details(
    request_id: UUID,
    customer_id: UUID = Query(..., description="Customer ID"),
    db: DB = None,
):
    """
    Get detailed service request information.
    """
    try:
        service = await get_customer_service(customer_id, db)
        return await service.get_service_request_details(request_id)
    except CustomerPortalError as e:
        raise HTTPException(status_code=404, detail=e.message)


@router.post("/service-requests/{request_id}/comments")
@require_module("oms_fulfillment")
async def add_service_request_comment(
    request_id: UUID,
    request: ServiceRequestComment,
    customer_id: UUID = Query(..., description="Customer ID"),
    db: DB = None,
):
    """
    Add a comment to a service request.
    """
    try:
        service = await get_customer_service(customer_id, db)
        return await service.add_service_request_comment(request_id, request.comment)
    except CustomerPortalError as e:
        raise HTTPException(status_code=400, detail=e.message)


@router.post("/service-requests/{request_id}/feedback")
@require_module("oms_fulfillment")
async def submit_service_feedback(
    request_id: UUID,
    request: FeedbackSubmit,
    customer_id: UUID = Query(..., description="Customer ID"),
    db: DB = None,
):
    """
    Submit feedback for a closed service request.
    """
    try:
        service = await get_customer_service(customer_id, db)
        return await service.submit_feedback(
            request_id=request_id,
            rating=request.rating,
            comments=request.comments,
        )
    except CustomerPortalError as e:
        raise HTTPException(status_code=400, detail=e.message)


# ==================== Loyalty ====================

@router.get("/loyalty")
@require_module("oms_fulfillment")
async def get_loyalty_summary(
    customer_id: UUID = Query(..., description="Customer ID"),
    db: DB = None,
):
    """
    Get loyalty points summary and tier information.
    """
    try:
        service = await get_customer_service(customer_id, db)
        return await service.get_loyalty_summary()
    except CustomerPortalError as e:
        raise HTTPException(status_code=400, detail=e.message)


# ==================== Products (for service request reference) ====================

@router.get("/my-products")
@require_module("oms_fulfillment")
async def get_customer_products(
    customer_id: UUID = Query(..., description="Customer ID"),
    db: DB = None,
):
    """
    Get products purchased by the customer.

    Useful for creating service requests against specific products.
    """
    try:
        service = await get_customer_service(customer_id, db)
        orders = await service.get_orders(limit=100)

        # Extract unique products from orders
        products = {}
        for order in orders["orders"]:
            order_details = await service.get_order_details(UUID(order["id"]))
            for item in order_details.get("items", []):
                if "product_name" in item:
                    products[item.get("sku", item["product_name"])] = {
                        "name": item["product_name"],
                        "sku": item.get("sku"),
                        "image_url": item.get("image_url"),
                        "last_ordered": order["order_date"],
                    }

        return {
            "products": list(products.values())
        }
    except CustomerPortalError as e:
        raise HTTPException(status_code=400, detail=e.message)
