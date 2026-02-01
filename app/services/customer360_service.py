"""
Customer 360 Service - Aggregates complete customer journey data.
"""
from datetime import datetime, timezone
from typing import Optional, List
from uuid import UUID

from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.customer import Customer, CustomerAddress
from app.models.order import Order, OrderStatusHistory, Payment
from app.models.shipment import Shipment, ShipmentTracking
from app.models.installation import Installation
from app.models.service_request import ServiceRequest, ServiceStatusHistory
from app.models.call_center import Call
from app.models.amc import AMCContract
from app.models.lead import Lead, LeadActivity
from app.models.franchisee import Franchisee
from app.models.product import Product

from app.schemas.customer import (
    CustomerResponse,
    Customer360Response,
    Customer360Stats,
    Customer360Timeline,
    Customer360OrderSummary,
    Customer360OrderStatusHistory,
    Customer360ShipmentSummary,
    Customer360ShipmentTracking,
    Customer360InstallationSummary,
    Customer360ServiceRequestSummary,
    Customer360ServiceStatusHistory,
    Customer360CallSummary,
    Customer360PaymentSummary,
    Customer360AMCSummary,
    Customer360LeadSummary,
    Customer360LeadActivity,
)
from app.core.enum_utils import get_enum_value


class Customer360Service:
    """Service for aggregating Customer 360 data."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_customer_360(
        self,
        customer_id: UUID,
        include_timeline: bool = True,
        limit_per_section: int = 50,
    ) -> Optional[Customer360Response]:
        """
        Get complete Customer 360 view.

        Args:
            customer_id: The customer UUID
            include_timeline: Whether to include chronological timeline
            limit_per_section: Max records per section (orders, shipments, etc.)

        Returns:
            Customer360Response with all journey data
        """
        # Get customer with addresses
        customer = await self._get_customer(customer_id)
        if not customer:
            return None

        # Fetch all related data concurrently
        orders = await self._get_orders(customer_id, limit_per_section)
        shipments = await self._get_shipments(customer_id, limit_per_section)
        installations = await self._get_installations(customer_id, limit_per_section)
        service_requests = await self._get_service_requests(customer_id, limit_per_section)
        calls = await self._get_calls(customer_id, limit_per_section)
        payments = await self._get_payments(customer_id, limit_per_section)
        amc_contracts = await self._get_amc_contracts(customer_id, limit_per_section)
        lead_info = await self._get_lead_info(customer_id)

        # Get recent history items
        recent_order_history = await self._get_recent_order_history(customer_id, limit=20)
        recent_shipment_tracking = await self._get_recent_shipment_tracking(customer_id, limit=20)
        recent_service_history = await self._get_recent_service_history(customer_id, limit=20)

        # Calculate stats
        stats = await self._calculate_stats(
            customer=customer,
            orders=orders,
            installations=installations,
            service_requests=service_requests,
            calls=calls,
            amc_contracts=amc_contracts,
        )

        # Build timeline
        timeline = []
        if include_timeline:
            timeline = self._build_timeline(
                orders=orders,
                shipments=shipments,
                installations=installations,
                service_requests=service_requests,
                calls=calls,
                payments=payments,
            )

        return Customer360Response(
            customer=CustomerResponse.model_validate(customer),
            stats=stats,
            timeline=timeline,
            orders=[self._map_order(o) for o in orders],
            recent_order_history=recent_order_history,
            shipments=[self._map_shipment(s) for s in shipments],
            recent_shipment_tracking=recent_shipment_tracking,
            installations=[self._map_installation(i) for i in installations],
            service_requests=[self._map_service_request(sr) for sr in service_requests],
            recent_service_history=recent_service_history,
            calls=[self._map_call(c) for c in calls],
            payments=[self._map_payment(p) for p in payments],
            amc_contracts=[self._map_amc(a) for a in amc_contracts],
            lead=lead_info.get("lead") if lead_info else None,
            lead_activities=lead_info.get("activities", []) if lead_info else [],
        )

    async def _get_customer(self, customer_id: UUID) -> Optional[Customer]:
        """Get customer with addresses."""
        result = await self.db.execute(
            select(Customer)
            .options(selectinload(Customer.addresses))
            .where(Customer.id == customer_id)
        )
        return result.scalar_one_or_none()

    async def _get_orders(self, customer_id: UUID, limit: int) -> List[Order]:
        """Get customer orders."""
        result = await self.db.execute(
            select(Order)
            .where(Order.customer_id == customer_id)
            .order_by(desc(Order.created_at))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def _get_shipments(self, customer_id: UUID, limit: int) -> List[Shipment]:
        """Get customer shipments via orders."""
        # Get order IDs first
        order_ids_result = await self.db.execute(
            select(Order.id).where(Order.customer_id == customer_id)
        )
        order_ids = [oid for oid in order_ids_result.scalars().all()]

        if not order_ids:
            return []

        result = await self.db.execute(
            select(Shipment)
            .where(Shipment.order_id.in_(order_ids))
            .order_by(desc(Shipment.created_at))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def _get_installations(self, customer_id: UUID, limit: int) -> List[Installation]:
        """Get customer installations."""
        result = await self.db.execute(
            select(Installation)
            .where(Installation.customer_id == customer_id)
            .order_by(desc(Installation.created_at))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def _get_service_requests(self, customer_id: UUID, limit: int) -> List[ServiceRequest]:
        """Get customer service requests."""
        result = await self.db.execute(
            select(ServiceRequest)
            .where(ServiceRequest.customer_id == customer_id)
            .order_by(desc(ServiceRequest.assigned_at))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def _get_calls(self, customer_id: UUID, limit: int) -> List[Call]:
        """Get customer calls."""
        result = await self.db.execute(
            select(Call)
            .where(Call.customer_id == customer_id)
            .order_by(desc(Call.call_start_time))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def _get_payments(self, customer_id: UUID, limit: int) -> List[Payment]:
        """Get customer payments via orders."""
        # Get order IDs first
        order_ids_result = await self.db.execute(
            select(Order.id).where(Order.customer_id == customer_id)
        )
        order_ids = [oid for oid in order_ids_result.scalars().all()]

        if not order_ids:
            return []

        result = await self.db.execute(
            select(Payment)
            .where(Payment.order_id.in_(order_ids))
            .order_by(desc(Payment.created_at))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def _get_amc_contracts(self, customer_id: UUID, limit: int) -> List[AMCContract]:
        """Get customer AMC contracts."""
        result = await self.db.execute(
            select(AMCContract)
            .where(AMCContract.customer_id == customer_id)
            .order_by(desc(AMCContract.start_date))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def _get_lead_info(self, customer_id: UUID) -> Optional[dict]:
        """Get lead info if customer was converted from a lead."""
        # Get customer phone
        customer = await self.db.get(Customer, customer_id)
        if not customer:
            return None

        # Find lead with same phone that was converted
        result = await self.db.execute(
            select(Lead)
            .where(Lead.phone == customer.phone)
            .where(Lead.converted_customer_id == customer_id)
        )
        lead = result.scalar_one_or_none()

        if not lead:
            return None

        # Get lead activities
        activities_result = await self.db.execute(
            select(LeadActivity)
            .where(LeadActivity.lead_id == lead.id)
            .order_by(LeadActivity.activity_date)
        )
        activities = activities_result.scalars().all()

        return {
            "lead": Customer360LeadSummary(
                id=lead.id,
                lead_number=lead.lead_number,
                status=get_enum_value(lead.status),
                source=get_enum_value(lead.source),
                converted_at=lead.converted_at,
            ),
            "activities": [
                Customer360LeadActivity(
                    activity_type=get_enum_value(a.activity_type),
                    subject=a.subject,
                    outcome=a.outcome,
                    old_status=get_enum_value(a.old_status) if a.old_status else None,
                    new_status=get_enum_value(a.new_status) if a.new_status else None,
                    activity_date=a.activity_date,
                )
                for a in activities
            ]
        }

    async def _get_recent_order_history(self, customer_id: UUID, limit: int) -> List[Customer360OrderStatusHistory]:
        """Get recent order status history."""
        # Get order IDs
        order_ids_result = await self.db.execute(
            select(Order.id).where(Order.customer_id == customer_id)
        )
        order_ids = [oid for oid in order_ids_result.scalars().all()]

        if not order_ids:
            return []

        result = await self.db.execute(
            select(OrderStatusHistory)
            .where(OrderStatusHistory.order_id.in_(order_ids))
            .order_by(desc(OrderStatusHistory.created_at))
            .limit(limit)
        )
        histories = result.scalars().all()

        return [
            Customer360OrderStatusHistory(
                from_status=get_enum_value(h.from_status) if h.from_status else None,
                to_status=get_enum_value(h.to_status),
                notes=h.notes,
                changed_by=str(h.changed_by) if h.changed_by else None,
                created_at=h.created_at,
            )
            for h in histories
        ]

    async def _get_recent_shipment_tracking(self, customer_id: UUID, limit: int) -> List[Customer360ShipmentTracking]:
        """Get recent shipment tracking."""
        # Get order IDs, then shipment IDs
        order_ids_result = await self.db.execute(
            select(Order.id).where(Order.customer_id == customer_id)
        )
        order_ids = [oid for oid in order_ids_result.scalars().all()]

        if not order_ids:
            return []

        shipment_ids_result = await self.db.execute(
            select(Shipment.id).where(Shipment.order_id.in_(order_ids))
        )
        shipment_ids = [sid for sid in shipment_ids_result.scalars().all()]

        if not shipment_ids:
            return []

        result = await self.db.execute(
            select(ShipmentTracking)
            .where(ShipmentTracking.shipment_id.in_(shipment_ids))
            .order_by(desc(ShipmentTracking.event_time))
            .limit(limit)
        )
        trackings = result.scalars().all()

        return [
            Customer360ShipmentTracking(
                status=get_enum_value(t.status),
                location=t.location,
                city=t.city,
                remarks=t.remarks,
                event_time=t.event_time,
            )
            for t in trackings
        ]

    async def _get_recent_service_history(self, customer_id: UUID, limit: int) -> List[Customer360ServiceStatusHistory]:
        """Get recent service request status history."""
        # Get service request IDs
        sr_ids_result = await self.db.execute(
            select(ServiceRequest.id).where(ServiceRequest.customer_id == customer_id)
        )
        sr_ids = [sid for sid in sr_ids_result.scalars().all()]

        if not sr_ids:
            return []

        result = await self.db.execute(
            select(ServiceStatusHistory)
            .where(ServiceStatusHistory.service_request_id.in_(sr_ids))
            .order_by(desc(ServiceStatusHistory.id))  # Order by ID as proxy for time
            .limit(limit)
        )
        histories = result.scalars().all()

        return [
            Customer360ServiceStatusHistory(
                from_status=get_enum_value(h.from_status) if h.from_status else None,
                to_status=get_enum_value(h.to_status),
                notes=h.notes,
                changed_by=str(h.changed_by) if h.changed_by else None,
                created_at=datetime.now(timezone.utc),  # No created_at in model, use current time
            )
            for h in histories
        ]

    async def _calculate_stats(
        self,
        customer: Customer,
        orders: List[Order],
        installations: List[Installation],
        service_requests: List[ServiceRequest],
        calls: List[Call],
        amc_contracts: List[AMCContract],
    ) -> Customer360Stats:
        """Calculate customer statistics."""
        # Order stats
        total_order_value = sum(float(o.total_amount or 0) for o in orders)
        delivered_orders = len([o for o in orders if str(o.status).upper() == "DELIVERED"])
        pending_orders = len([o for o in orders if str(o.status).upper() not in ["DELIVERED", "CANCELLED", "REFUNDED"]])

        # Installation stats
        completed_installations = len([i for i in installations if str(i.status).upper() == "COMPLETED"])

        # Service request stats
        open_statuses = ["PENDING", "ASSIGNED", "SCHEDULED", "IN_PROGRESS", "PARTS_REQUIRED", "ON_HOLD"]
        open_service_requests = len([sr for sr in service_requests if str(sr.status).upper() in open_statuses])

        # AMC stats
        active_amc = len([a for a in amc_contracts if str(a.status).upper() == "ACTIVE"])

        # Average rating from installations and service requests
        ratings = []
        for i in installations:
            if i.customer_rating:
                ratings.append(i.customer_rating)
        for sr in service_requests:
            if sr.customer_rating:
                ratings.append(sr.customer_rating)
        avg_rating = sum(ratings) / len(ratings) if ratings else None

        # Customer age in days
        customer_since_days = (datetime.now(timezone.utc) - customer.created_at).days

        return Customer360Stats(
            total_orders=len(orders),
            total_order_value=total_order_value,
            delivered_orders=delivered_orders,
            pending_orders=pending_orders,
            total_installations=len(installations),
            completed_installations=completed_installations,
            total_service_requests=len(service_requests),
            open_service_requests=open_service_requests,
            total_calls=len(calls),
            active_amc_contracts=active_amc,
            average_rating=round(avg_rating, 2) if avg_rating else None,
            customer_since_days=customer_since_days,
        )

    def _build_timeline(
        self,
        orders: List[Order],
        shipments: List[Shipment],
        installations: List[Installation],
        service_requests: List[ServiceRequest],
        calls: List[Call],
        payments: List[Payment],
    ) -> List[Customer360Timeline]:
        """Build chronological timeline of events."""
        events = []

        # Add orders
        for o in orders:
            if o.created_at:  # Skip if no timestamp
                events.append(Customer360Timeline(
                    event_type="ORDER",
                    event_id=o.id,
                    title=f"Order {o.order_number}",
                    description=f"Amount: Rs.{o.total_amount}",
                    status=get_enum_value(o.status),
                    timestamp=o.created_at,
                    metadata={"order_number": o.order_number, "amount": float(o.total_amount or 0)},
                ))

        # Add shipments
        for s in shipments:
            if s.created_at:  # Skip if no timestamp
                events.append(Customer360Timeline(
                    event_type="SHIPMENT",
                    event_id=s.id,
                    title=f"Shipment {s.shipment_number}",
                    description=f"AWB: {s.awb_number}" if s.awb_number else None,
                    status=get_enum_value(s.status),
                    timestamp=s.created_at,
                    metadata={"shipment_number": s.shipment_number, "awb": s.awb_number},
                ))

        # Add installations
        for i in installations:
            if i.created_at:  # Skip if no timestamp
                events.append(Customer360Timeline(
                    event_type="INSTALLATION",
                    event_id=i.id,
                    title=f"Installation {i.installation_number}",
                    description=f"Pincode: {i.installation_pincode}",
                    status=get_enum_value(i.status),
                    timestamp=i.created_at,
                    metadata={"installation_number": i.installation_number, "rating": i.customer_rating},
                ))

        # Add service requests
        for sr in service_requests:
            # Use assigned_at as the timestamp since ServiceRequest doesn't have created_at
            sr_timestamp = sr.assigned_at or sr.scheduled_date or datetime.now(timezone.utc)
            events.append(Customer360Timeline(
                event_type="SERVICE",
                event_id=sr.id,
                title=f"Service {sr.ticket_number}",
                description=sr.title,
                status=get_enum_value(sr.status),
                timestamp=sr_timestamp if isinstance(sr_timestamp, datetime) else datetime.combine(sr_timestamp, datetime.min.time()),
                metadata={"ticket_number": sr.ticket_number, "service_type": get_enum_value(sr.service_type)},
            ))

        # Add calls
        for c in calls:
            if c.call_start_time:  # Skip if no timestamp
                events.append(Customer360Timeline(
                    event_type="CALL",
                    event_id=c.id,
                    title=f"Call {c.call_id}",
                    description=f"{get_enum_value(c.call_type)} - {get_enum_value(c.category)}",
                    status=get_enum_value(c.status),
                    timestamp=c.call_start_time,
                    metadata={"call_id": c.call_id, "duration": c.duration_seconds},
                ))

        # Add payments
        for p in payments:
            if p.created_at:  # Skip if no timestamp
                events.append(Customer360Timeline(
                    event_type="PAYMENT",
                    event_id=p.id,
                    title=f"Payment Rs.{p.amount}",
                    description=f"Method: {get_enum_value(p.method)}",
                    status=get_enum_value(p.status),
                    timestamp=p.created_at,
                    metadata={"amount": float(p.amount or 0), "method": get_enum_value(p.method)},
                ))

        # Sort by timestamp descending (most recent first)
        events.sort(key=lambda e: e.timestamp, reverse=True)

        return events[:100]  # Limit to 100 events

    def _map_order(self, order: Order) -> Customer360OrderSummary:
        """Map Order to summary schema."""
        return Customer360OrderSummary(
            id=order.id,
            order_number=order.order_number,
            status=get_enum_value(order.status),
            total_amount=float(order.total_amount or 0),
            payment_status=get_enum_value(order.payment_status) if order.payment_status else None,
            items_count=0,  # Avoid lazy loading - would need selectinload
            created_at=order.created_at,
        )

    def _map_shipment(self, shipment: Shipment) -> Customer360ShipmentSummary:
        """Map Shipment to summary schema."""
        return Customer360ShipmentSummary(
            id=shipment.id,
            shipment_number=shipment.shipment_number,
            order_number=None,  # Would need to join
            status=get_enum_value(shipment.status),
            awb_number=shipment.awb_number,
            transporter_name=None,  # Would need to join
            delivered_to=shipment.delivered_to,
            delivered_at=shipment.delivered_at,
            created_at=shipment.created_at,
        )

    def _map_installation(self, installation: Installation) -> Customer360InstallationSummary:
        """Map Installation to summary schema."""
        return Customer360InstallationSummary(
            id=installation.id,
            installation_number=installation.installation_number,
            status=get_enum_value(installation.status),
            product_name=None,  # Would need to join
            installation_pincode=installation.installation_pincode,
            franchisee_name=None,  # Would need to join
            scheduled_date=installation.scheduled_date,
            completed_at=installation.completed_at,
            customer_rating=installation.customer_rating,
            warranty_end_date=installation.warranty_end_date,
            created_at=installation.created_at,
        )

    def _map_service_request(self, sr: ServiceRequest) -> Customer360ServiceRequestSummary:
        """Map ServiceRequest to summary schema."""
        # Use assigned_at as created_at since ServiceRequest doesn't have created_at
        sr_created = sr.assigned_at or datetime.now(timezone.utc)
        return Customer360ServiceRequestSummary(
            id=sr.id,
            ticket_number=sr.ticket_number,
            service_type=get_enum_value(sr.service_type),
            status=get_enum_value(sr.status),
            priority=get_enum_value(sr.priority) if sr.priority else None,
            title=sr.title,
            franchisee_name=None,  # Would need to join
            technician_name=None,  # Would need to join
            scheduled_date=sr.scheduled_date,
            completed_at=sr.completed_at,
            customer_rating=sr.customer_rating,
            created_at=sr_created,
        )

    def _map_call(self, call: Call) -> Customer360CallSummary:
        """Map Call to summary schema."""
        return Customer360CallSummary(
            id=call.id,
            call_id=call.call_id,
            call_type=get_enum_value(call.call_type),
            category=get_enum_value(call.category),
            status=get_enum_value(call.status),
            outcome=get_enum_value(call.outcome) if call.outcome else None,
            duration_seconds=call.duration_seconds,
            agent_name=None,  # Would need to join
            call_start_time=call.call_start_time,
            sentiment=get_enum_value(call.sentiment) if call.sentiment else None,
        )

    def _map_payment(self, payment: Payment) -> Customer360PaymentSummary:
        """Map Payment to summary schema."""
        return Customer360PaymentSummary(
            id=payment.id,
            order_number=None,  # Would need to join
            amount=float(payment.amount or 0),
            method=get_enum_value(payment.method),
            status=get_enum_value(payment.status),
            transaction_id=payment.transaction_id,
            gateway=payment.gateway,
            completed_at=payment.completed_at,
            created_at=payment.created_at,
        )

    def _map_amc(self, amc: AMCContract) -> Customer360AMCSummary:
        """Map AMCContract to summary schema."""
        return Customer360AMCSummary(
            id=amc.id,
            contract_number=amc.contract_number,
            plan_name=getattr(amc, 'plan_name', "AMC Plan"),
            status=get_enum_value(amc.status),
            start_date=amc.start_date,
            end_date=amc.end_date,
            total_services=amc.total_services or 0,
            services_used=amc.services_used or 0,
            services_remaining=amc.services_remaining or 0,
            next_service_due=amc.next_service_due,
        )
