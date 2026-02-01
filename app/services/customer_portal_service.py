"""
Customer Self-Service Portal Service

Provides APIs for customers to:
- View and manage their profile
- View order history and track shipments
- Download invoices
- Raise service/support requests
- View loyalty points
- Manage addresses
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List
from uuid import UUID
from decimal import Decimal

from sqlalchemy import select, and_, or_, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.customer import Customer
from app.models.order import Order, OrderItem, OrderStatus
from app.models.billing import TaxInvoice
from app.models.service_request import ServiceRequest, ServiceStatus
from app.models.product import Product


class CustomerPortalError(Exception):
    """Custom exception for customer portal errors."""
    def __init__(self, message: str, details: Dict = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class CustomerPortalService:
    """
    Service for customer self-service portal operations.
    """

    def __init__(self, db: AsyncSession, customer_id: UUID):
        self.db = db
        self.customer_id = customer_id

    async def get_customer_profile(self) -> Dict:
        """Get customer profile information."""
        result = await self.db.execute(
            select(Customer).where(Customer.id == self.customer_id)
        )
        customer = result.scalar_one_or_none()

        if not customer:
            raise CustomerPortalError("Customer not found")

        return {
            "id": str(customer.id),
            "name": customer.name,
            "email": customer.email,
            "phone": customer.phone,
            "mobile": getattr(customer, 'mobile', None),
            "gstin": getattr(customer, 'gstin', None),
            "customer_type": getattr(customer, 'customer_type', 'RETAIL'),
            "address": {
                "line1": getattr(customer, 'address_line1', ''),
                "line2": getattr(customer, 'address_line2', ''),
                "city": getattr(customer, 'city', ''),
                "state": getattr(customer, 'state', ''),
                "pincode": getattr(customer, 'pincode', ''),
                "country": getattr(customer, 'country', 'India'),
            },
            "loyalty_points": getattr(customer, 'loyalty_points', 0),
            "total_orders": await self._get_order_count(),
            "member_since": customer.created_at.strftime("%B %Y") if customer.created_at else None,
        }

    async def update_profile(
        self,
        name: Optional[str] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        mobile: Optional[str] = None,
        address_line1: Optional[str] = None,
        address_line2: Optional[str] = None,
        city: Optional[str] = None,
        state: Optional[str] = None,
        pincode: Optional[str] = None,
    ) -> Dict:
        """Update customer profile."""
        result = await self.db.execute(
            select(Customer).where(Customer.id == self.customer_id)
        )
        customer = result.scalar_one_or_none()

        if not customer:
            raise CustomerPortalError("Customer not found")

        # Update fields if provided
        if name:
            customer.name = name
        if email:
            customer.email = email
        if phone:
            customer.phone = phone
        if mobile and hasattr(customer, 'mobile'):
            customer.mobile = mobile
        if address_line1 and hasattr(customer, 'address_line1'):
            customer.address_line1 = address_line1
        if address_line2 and hasattr(customer, 'address_line2'):
            customer.address_line2 = address_line2
        if city and hasattr(customer, 'city'):
            customer.city = city
        if state and hasattr(customer, 'state'):
            customer.state = state
        if pincode and hasattr(customer, 'pincode'):
            customer.pincode = pincode

        customer.updated_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(customer)

        return await self.get_customer_profile()

    async def _get_order_count(self) -> int:
        """Get total order count for customer."""
        result = await self.db.execute(
            select(func.count(Order.id)).where(
                Order.customer_id == self.customer_id
            )
        )
        return result.scalar() or 0

    # ==================== Orders ====================

    async def get_orders(
        self,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 20
    ) -> Dict:
        """Get customer orders with pagination."""
        query = select(Order).where(
            Order.customer_id == self.customer_id
        )

        if status:
            query = query.where(Order.status == OrderStatus(status))

        # Get total count
        count_query = select(func.count(Order.id)).where(
            Order.customer_id == self.customer_id
        )
        if status:
            count_query = count_query.where(Order.status == OrderStatus(status))

        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        # Get orders
        query = query.options(
            selectinload(Order.items)
        ).order_by(desc(Order.created_at)).offset(skip).limit(limit)

        result = await self.db.execute(query)
        orders = result.scalars().all()

        return {
            "orders": [
                {
                    "id": str(order.id),
                    "order_number": order.order_number,
                    "order_date": order.created_at.isoformat() if order.created_at else None,
                    "status": order.status if order.status else "PENDING",
                    "total_amount": float(order.total_amount or 0),
                    "items_count": len(order.items) if order.items else 0,
                    "payment_status": getattr(order, 'payment_status', 'PENDING'),
                    "delivery_date": order.delivered_at.isoformat() if order.delivered_at else None,
                }
                for order in orders
            ],
            "total": total,
            "skip": skip,
            "limit": limit
        }

    async def get_order_details(self, order_id: UUID) -> Dict:
        """Get detailed order information."""
        result = await self.db.execute(
            select(Order)
            .options(selectinload(Order.items).selectinload(OrderItem.product))
            .where(
                and_(
                    Order.id == order_id,
                    Order.customer_id == self.customer_id
                )
            )
        )
        order = result.scalar_one_or_none()

        if not order:
            raise CustomerPortalError("Order not found")

        return {
            "id": str(order.id),
            "order_number": order.order_number,
            "order_date": order.created_at.isoformat() if order.created_at else None,
            "status": order.status if order.status else "PENDING",
            "payment_status": getattr(order, 'payment_status', 'PENDING'),
            "payment_method": getattr(order, 'payment_method', None),
            "subtotal": float(getattr(order, 'subtotal', 0) or 0),
            "tax_amount": float(getattr(order, 'tax_amount', 0) or 0),
            "discount_amount": float(getattr(order, 'discount_amount', 0) or 0),
            "shipping_amount": float(getattr(order, 'shipping_amount', 0) or 0),
            "total_amount": float(order.total_amount or 0),
            "shipping_address": {
                "name": getattr(order, 'shipping_name', ''),
                "line1": getattr(order, 'shipping_address_line1', ''),
                "line2": getattr(order, 'shipping_address_line2', ''),
                "city": getattr(order, 'shipping_city', ''),
                "state": getattr(order, 'shipping_state', ''),
                "pincode": getattr(order, 'shipping_pincode', ''),
                "phone": getattr(order, 'shipping_phone', ''),
            },
            "items": [
                {
                    "id": str(item.id),
                    "product_name": item.product.name if item.product else item.product_name,
                    "sku": item.product.sku if item.product else getattr(item, 'sku', ''),
                    "quantity": item.quantity,
                    "unit_price": float(item.unit_price or 0),
                    "total_price": float(item.total_price or 0),
                    "image_url": item.product.image_url if item.product and hasattr(item.product, 'image_url') else None,
                }
                for item in (order.items or [])
            ],
            "tracking": await self._get_order_tracking(order_id),
            "notes": getattr(order, 'notes', ''),
        }

    async def _get_order_tracking(self, order_id: UUID) -> List[Dict]:
        """Get tracking history for an order."""
        # This would integrate with shipments table
        # For now, return order status history
        result = await self.db.execute(
            select(Order).where(Order.id == order_id)
        )
        order = result.scalar_one_or_none()

        if not order:
            return []

        tracking = [
            {
                "status": "ORDER_PLACED",
                "timestamp": order.created_at.isoformat() if order.created_at else None,
                "description": "Order has been placed"
            }
        ]

        if order.status in [OrderStatus.CONFIRMED, OrderStatus.PROCESSING, OrderStatus.SHIPPED, OrderStatus.DELIVERED]:
            tracking.append({
                "status": "ORDER_CONFIRMED",
                "timestamp": order.updated_at.isoformat() if order.updated_at else None,
                "description": "Order has been confirmed"
            })

        if order.status in [OrderStatus.SHIPPED, OrderStatus.DELIVERED]:
            tracking.append({
                "status": "SHIPPED",
                "timestamp": order.updated_at.isoformat() if order.updated_at else None,
                "description": "Order has been shipped"
            })

        if order.status == OrderStatus.DELIVERED:
            tracking.append({
                "status": "DELIVERED",
                "timestamp": order.updated_at.isoformat() if order.updated_at else None,
                "description": "Order has been delivered"
            })

        return tracking

    # ==================== TaxInvoices ====================

    async def get_invoices(
        self,
        skip: int = 0,
        limit: int = 20
    ) -> Dict:
        """Get customer invoices."""
        query = select(TaxInvoice).where(
            TaxInvoice.customer_id == self.customer_id
        ).order_by(desc(TaxInvoice.invoice_date)).offset(skip).limit(limit)

        result = await self.db.execute(query)
        invoices = result.scalars().all()

        count_result = await self.db.execute(
            select(func.count(TaxInvoice.id)).where(
                TaxInvoice.customer_id == self.customer_id
            )
        )
        total = count_result.scalar() or 0

        return {
            "invoices": [
                {
                    "id": str(inv.id),
                    "invoice_number": inv.invoice_number,
                    "invoice_date": inv.invoice_date.isoformat() if inv.invoice_date else None,
                    "due_date": inv.due_date.isoformat() if hasattr(inv, 'due_date') and inv.due_date else None,
                    "total_amount": float(inv.total_amount or 0),
                    "paid_amount": float(getattr(inv, 'paid_amount', 0) or 0),
                    "balance": float(getattr(inv, 'balance_due', 0) or 0),
                    "status": getattr(inv, 'status', 'ISSUED'),
                    "irn": getattr(inv, 'irn', None),  # E-TaxInvoice IRN
                    "can_download": True,
                }
                for inv in invoices
            ],
            "total": total,
            "skip": skip,
            "limit": limit
        }

    async def get_invoice_details(self, invoice_id: UUID) -> Dict:
        """Get detailed invoice information."""
        result = await self.db.execute(
            select(TaxInvoice)
            .options(selectinload(TaxInvoice.items))
            .where(
                and_(
                    TaxInvoice.id == invoice_id,
                    TaxInvoice.customer_id == self.customer_id
                )
            )
        )
        invoice = result.scalar_one_or_none()

        if not invoice:
            raise CustomerPortalError("TaxInvoice not found")

        return {
            "id": str(invoice.id),
            "invoice_number": invoice.invoice_number,
            "invoice_date": invoice.invoice_date.isoformat() if invoice.invoice_date else None,
            "due_date": invoice.due_date.isoformat() if hasattr(invoice, 'due_date') and invoice.due_date else None,
            "subtotal": float(getattr(invoice, 'subtotal', 0) or 0),
            "cgst": float(getattr(invoice, 'cgst_amount', 0) or 0),
            "sgst": float(getattr(invoice, 'sgst_amount', 0) or 0),
            "igst": float(getattr(invoice, 'igst_amount', 0) or 0),
            "total_tax": float(getattr(invoice, 'tax_amount', 0) or 0),
            "total_amount": float(invoice.total_amount or 0),
            "paid_amount": float(getattr(invoice, 'paid_amount', 0) or 0),
            "balance": float(getattr(invoice, 'balance_due', 0) or 0),
            "status": getattr(invoice, 'status', 'ISSUED'),
            "irn": getattr(invoice, 'irn', None),
            "ack_number": getattr(invoice, 'ack_number', None),
            "qr_code": getattr(invoice, 'qr_code', None),
            "items": [
                {
                    "description": getattr(item, 'description', ''),
                    "hsn_code": getattr(item, 'hsn_code', ''),
                    "quantity": getattr(item, 'quantity', 0),
                    "unit_price": float(getattr(item, 'unit_price', 0) or 0),
                    "tax_rate": float(getattr(item, 'tax_rate', 0) or 0),
                    "total": float(getattr(item, 'total_amount', 0) or 0),
                }
                for item in (invoice.items or [])
            ],
        }

    # ==================== Service Requests ====================

    async def get_service_requests(
        self,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 20
    ) -> Dict:
        """Get customer service requests."""
        query = select(ServiceRequest).where(
            ServiceRequest.customer_id == self.customer_id
        )

        if status:
            query = query.where(ServiceRequest.status == ServiceStatus(status))

        count_query = select(func.count(ServiceRequest.id)).where(
            ServiceRequest.customer_id == self.customer_id
        )
        if status:
            count_query = count_query.where(ServiceRequest.status == ServiceStatus(status))

        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        query = query.order_by(desc(ServiceRequest.created_at)).offset(skip).limit(limit)

        result = await self.db.execute(query)
        requests = result.scalars().all()

        return {
            "service_requests": [
                {
                    "id": str(sr.id),
                    "ticket_number": sr.ticket_number,
                    "request_type": sr.request_type.value if hasattr(sr, 'request_type') and sr.request_type else "GENERAL",
                    "subject": getattr(sr, 'subject', ''),
                    "description": getattr(sr, 'description', ''),
                    "status": sr.status if sr.status else "OPEN",
                    "priority": getattr(sr, 'priority', 'NORMAL'),
                    "created_at": sr.created_at.isoformat() if sr.created_at else None,
                    "updated_at": sr.updated_at.isoformat() if sr.updated_at else None,
                    "resolution": getattr(sr, 'resolution', None),
                }
                for sr in requests
            ],
            "total": total,
            "skip": skip,
            "limit": limit
        }

    async def create_service_request(
        self,
        request_type: str,
        subject: str,
        description: str,
        product_id: Optional[UUID] = None,
        order_id: Optional[UUID] = None,
        priority: str = "NORMAL",
        attachments: List[str] = None
    ) -> Dict:
        """Create a new service request."""
        # Generate ticket number
        count_result = await self.db.execute(
            select(func.count(ServiceRequest.id))
        )
        count = (count_result.scalar() or 0) + 1
        ticket_number = f"SR{datetime.now(timezone.utc).strftime('%Y%m')}{count:05d}"

        # Get customer company_id
        cust_result = await self.db.execute(
            select(Customer).where(Customer.id == self.customer_id)
        )
        customer = cust_result.scalar_one_or_none()

        if not customer:
            raise CustomerPortalError("Customer not found")

        service_request = ServiceRequest(
            company_id=customer.company_id,
            customer_id=self.customer_id,
            ticket_number=ticket_number,
            request_type=request_type,
            subject=subject,
            description=description,
            product_id=product_id,
            order_id=order_id,
            priority=priority,
            status=ServiceStatus.OPEN,
            source="CUSTOMER_PORTAL",
            attachments=attachments or [],
        )

        self.db.add(service_request)
        await self.db.commit()
        await self.db.refresh(service_request)

        return {
            "id": str(service_request.id),
            "ticket_number": service_request.ticket_number,
            "message": "Service request created successfully"
        }

    async def get_service_request_details(self, request_id: UUID) -> Dict:
        """Get detailed service request information."""
        result = await self.db.execute(
            select(ServiceRequest).where(
                and_(
                    ServiceRequest.id == request_id,
                    ServiceRequest.customer_id == self.customer_id
                )
            )
        )
        sr = result.scalar_one_or_none()

        if not sr:
            raise CustomerPortalError("Service request not found")

        return {
            "id": str(sr.id),
            "ticket_number": sr.ticket_number,
            "request_type": sr.request_type.value if hasattr(sr, 'request_type') and sr.request_type else "GENERAL",
            "subject": getattr(sr, 'subject', ''),
            "description": getattr(sr, 'description', ''),
            "status": sr.status if sr.status else "OPEN",
            "priority": getattr(sr, 'priority', 'NORMAL'),
            "product_id": str(sr.product_id) if sr.product_id else None,
            "order_id": str(sr.order_id) if hasattr(sr, 'order_id') and sr.order_id else None,
            "assigned_to": str(sr.assigned_to) if sr.assigned_to else None,
            "scheduled_date": sr.scheduled_date.isoformat() if hasattr(sr, 'scheduled_date') and sr.scheduled_date else None,
            "resolution": getattr(sr, 'resolution', None),
            "resolution_date": sr.resolution_date.isoformat() if hasattr(sr, 'resolution_date') and sr.resolution_date else None,
            "feedback_rating": getattr(sr, 'feedback_rating', None),
            "feedback_comments": getattr(sr, 'feedback_comments', None),
            "attachments": getattr(sr, 'attachments', []),
            "created_at": sr.created_at.isoformat() if sr.created_at else None,
            "updated_at": sr.updated_at.isoformat() if sr.updated_at else None,
        }

    async def add_service_request_comment(
        self,
        request_id: UUID,
        comment: str
    ) -> Dict:
        """Add a comment to a service request."""
        result = await self.db.execute(
            select(ServiceRequest).where(
                and_(
                    ServiceRequest.id == request_id,
                    ServiceRequest.customer_id == self.customer_id
                )
            )
        )
        sr = result.scalar_one_or_none()

        if not sr:
            raise CustomerPortalError("Service request not found")

        # Add comment to history
        if not hasattr(sr, 'comments') or sr.comments is None:
            sr.comments = []

        sr.comments.append({
            "by": "CUSTOMER",
            "comment": comment,
            "at": datetime.now(timezone.utc).isoformat()
        })

        sr.updated_at = datetime.now(timezone.utc)

        await self.db.commit()

        return {
            "success": True,
            "message": "Comment added successfully"
        }

    async def submit_feedback(
        self,
        request_id: UUID,
        rating: int,
        comments: Optional[str] = None
    ) -> Dict:
        """Submit feedback for a completed service request."""
        result = await self.db.execute(
            select(ServiceRequest).where(
                and_(
                    ServiceRequest.id == request_id,
                    ServiceRequest.customer_id == self.customer_id,
                    ServiceRequest.status == ServiceStatus.CLOSED
                )
            )
        )
        sr = result.scalar_one_or_none()

        if not sr:
            raise CustomerPortalError("Service request not found or not closed")

        if rating < 1 or rating > 5:
            raise CustomerPortalError("Rating must be between 1 and 5")

        sr.feedback_rating = rating
        sr.feedback_comments = comments
        sr.feedback_date = datetime.now(timezone.utc)

        await self.db.commit()

        return {
            "success": True,
            "message": "Thank you for your feedback!"
        }

    # ==================== Dashboard ====================

    async def get_dashboard(self) -> Dict:
        """Get customer portal dashboard data."""
        profile = await self.get_customer_profile()

        # Recent orders
        recent_orders = await self.get_orders(limit=5)

        # Open service requests
        open_requests = await self.get_service_requests(status="OPEN", limit=5)

        # Pending invoices
        invoices_result = await self.db.execute(
            select(TaxInvoice).where(
                and_(
                    TaxInvoice.customer_id == self.customer_id,
                    TaxInvoice.status.in_(["ISSUED", "PARTIALLY_PAID"])
                )
            ).limit(5)
        )
        pending_invoices = invoices_result.scalars().all()

        return {
            "customer": {
                "name": profile["name"],
                "loyalty_points": profile["loyalty_points"],
                "member_since": profile["member_since"],
            },
            "stats": {
                "total_orders": profile["total_orders"],
                "open_tickets": open_requests["total"],
                "pending_invoices": len(pending_invoices),
            },
            "recent_orders": recent_orders["orders"][:5],
            "open_service_requests": open_requests["service_requests"][:5],
            "pending_invoices": [
                {
                    "id": str(inv.id),
                    "invoice_number": inv.invoice_number,
                    "amount": float(inv.total_amount or 0),
                    "due_date": inv.due_date.isoformat() if hasattr(inv, 'due_date') and inv.due_date else None,
                }
                for inv in pending_invoices
            ],
        }

    # ==================== Loyalty ====================

    async def get_loyalty_summary(self) -> Dict:
        """Get loyalty points summary."""
        result = await self.db.execute(
            select(Customer).where(Customer.id == self.customer_id)
        )
        customer = result.scalar_one_or_none()

        if not customer:
            raise CustomerPortalError("Customer not found")

        points = getattr(customer, 'loyalty_points', 0)
        tier = "BRONZE"
        if points >= 10000:
            tier = "PLATINUM"
        elif points >= 5000:
            tier = "GOLD"
        elif points >= 2000:
            tier = "SILVER"

        return {
            "current_points": points,
            "tier": tier,
            "points_to_next_tier": self._points_to_next_tier(points),
            "redemption_value": points / 100,  # 100 points = ₹1
            "expiring_soon": 0,  # Would calculate from points history
        }

    def _points_to_next_tier(self, current_points: int) -> Dict:
        """Calculate points needed for next tier."""
        if current_points >= 10000:
            return {"tier": "PLATINUM", "points_needed": 0, "message": "You're at the highest tier!"}
        elif current_points >= 5000:
            return {"tier": "PLATINUM", "points_needed": 10000 - current_points, "message": f"Earn {10000 - current_points} more points for Platinum"}
        elif current_points >= 2000:
            return {"tier": "GOLD", "points_needed": 5000 - current_points, "message": f"Earn {5000 - current_points} more points for Gold"}
        else:
            return {"tier": "SILVER", "points_needed": 2000 - current_points, "message": f"Earn {2000 - current_points} more points for Silver"}
