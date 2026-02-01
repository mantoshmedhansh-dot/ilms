"""
Post-Delivery Workflow Service

This service handles the complete automation flow after a shipment is delivered:
1. Create Installation record
2. Create ServiceRequest for installation
3. Link serial numbers from OrderItem to Installation
4. Auto-assign technician/franchisee based on region/pincode
5. Trigger customer notifications
"""
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
from uuid import uuid4, UUID
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    Order, OrderItem, OrderStatus,
    Shipment, ShipmentStatus,
    Customer, CustomerAddress,
    Installation, InstallationStatus,
    ServiceRequest, ServiceType, ServicePriority, ServiceStatus, ServiceSource,
    StockItem, StockItemStatus,
    Technician, TechnicianStatus,
    Franchisee, FranchiseeStatus, FranchiseeTerritory, TerritoryStatus,
    FranchiseeServiceability, ServiceCapability,
    Region,
)


class PostDeliveryService:
    """
    Handles post-delivery workflow automation.
    Triggered when a shipment is marked as DELIVERED with POD.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def process_delivery(
        self,
        shipment_id: str,
        pod_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Main entry point - processes a delivery and triggers all downstream actions.

        Args:
            shipment_id: ID of the delivered shipment
            pod_data: POD details (signature_url, image_urls, gps_coordinates, received_by)

        Returns:
            Dict containing created records (installation, service_request, notifications)
        """
        result = {
            "shipment_id": shipment_id,
            "installation_id": None,
            "service_request_id": None,
            "technician_id": None,
            "franchisee_id": None,
            "notifications_sent": [],
            "serial_numbers_linked": [],
        }

        # 1. Get shipment with order details
        shipment = await self._get_shipment_with_details(shipment_id)
        if not shipment:
            raise ValueError(f"Shipment {shipment_id} not found")

        order = shipment.order
        if not order:
            raise ValueError(f"Order not found for shipment {shipment_id}")

        # 2. Update shipment with POD data
        await self._update_shipment_pod(shipment, pod_data)

        # 3. Update order status to DELIVERED
        await self._update_order_status(order)

        # 4. Get customer and delivery address
        customer = await self._get_customer(order.customer_id)
        delivery_address = await self._get_delivery_address(order)

        # 5. Link serial numbers from order items
        serial_numbers = await self._link_serial_numbers(order)
        result["serial_numbers_linked"] = serial_numbers

        # 6. Create Installation record
        installation = await self._create_installation(
            order=order,
            customer=customer,
            delivery_address=delivery_address,
            serial_numbers=serial_numbers,
            pod_data=pod_data
        )
        result["installation_id"] = installation.id

        # 7. Create ServiceRequest for installation
        service_request = await self._create_service_request(
            installation=installation,
            order=order,
            customer=customer,
            delivery_address=delivery_address
        )
        result["service_request_id"] = service_request.id

        # 8. Auto-assign technician or franchisee based on pincode
        assignment = await self._auto_assign_service(
            service_request=service_request,
            delivery_address=delivery_address
        )
        result["technician_id"] = assignment.get("technician_id")
        result["franchisee_id"] = assignment.get("franchisee_id")
        result["franchisee_assigned"] = assignment.get("franchisee_id") is not None

        # Also update Installation with the assigned franchisee/technician
        if assignment.get("franchisee_id"):
            installation.franchisee_id = assignment["franchisee_id"]  # Already a string (VARCHAR in production)
            installation.assigned_at = datetime.now(timezone.utc)
        elif assignment.get("technician_id"):
            installation.technician_id = UUID(assignment["technician_id"])
            installation.assigned_at = datetime.now(timezone.utc)

        # 9. Queue customer notifications
        notifications = await self._queue_notifications(
            customer=customer,
            order=order,
            installation=installation,
            service_request=service_request,
            assignment=assignment
        )
        result["notifications_sent"] = notifications

        # Commit all changes
        await self.db.commit()

        return result

    async def _get_shipment_with_details(self, shipment_id: str) -> Optional[Shipment]:
        """Get shipment with related order and items."""
        import uuid
        # Convert string to UUID if needed
        if isinstance(shipment_id, str):
            shipment_uuid = uuid.UUID(shipment_id)
        else:
            shipment_uuid = shipment_id

        stmt = (
            select(Shipment)
            .options(selectinload(Shipment.order).selectinload(Order.items))
            .where(Shipment.id == shipment_uuid)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _update_shipment_pod(
        self,
        shipment: Shipment,
        pod_data: Dict[str, Any]
    ) -> None:
        """Update shipment with POD details."""
        shipment.status = ShipmentStatus.DELIVERED.value
        shipment.delivered_at = datetime.now(timezone.utc)
        shipment.pod_signature_url = pod_data.get("signature_url")
        shipment.pod_image_url = pod_data.get("image_url")
        shipment.delivered_to = pod_data.get("received_by")
        shipment.delivery_remarks = pod_data.get("remarks")

        # Store GPS coordinates if available
        if pod_data.get("latitude") and pod_data.get("longitude"):
            shipment.delivery_latitude = pod_data["latitude"]
            shipment.delivery_longitude = pod_data["longitude"]

    async def _update_order_status(self, order: Order) -> None:
        """Update order status to DELIVERED."""
        order.status = OrderStatus.DELIVERED.value
        order.delivered_at = datetime.now(timezone.utc)

    async def _get_customer(self, customer_id) -> Customer:
        """Get customer by ID."""
        import uuid as uuid_mod
        # Convert string to UUID if needed
        if isinstance(customer_id, str):
            customer_uuid = uuid_mod.UUID(customer_id)
        else:
            customer_uuid = customer_id

        stmt = select(Customer).where(Customer.id == customer_uuid)
        result = await self.db.execute(stmt)
        customer = result.scalar_one_or_none()
        if not customer:
            raise ValueError(f"Customer {customer_id} not found")
        return customer

    async def _get_delivery_address(self, order: Order) -> Optional[Dict[str, Any]]:
        """
        Get delivery address for order.
        Returns a dict-like object with address fields.
        """
        # The order stores shipping_address as JSON, not as FK
        if order.shipping_address:
            # shipping_address is already a dict (JSON field)
            return order.shipping_address
        return None

    async def _link_serial_numbers(self, order: Order) -> List[str]:
        """
        Link serial numbers from StockItems to OrderItems.
        Returns list of serial numbers linked.
        """
        serial_numbers = []

        for item in order.items:
            # Find stock items allocated to this order item
            stmt = select(StockItem).where(
                and_(
                    StockItem.order_id == order.id,
                    StockItem.product_id == item.product_id,
                    StockItem.status == StockItemStatus.SOLD
                )
            )
            result = await self.db.execute(stmt)
            stock_items = result.scalars().all()

            for stock_item in stock_items:
                if stock_item.serial_number:
                    serial_numbers.append(stock_item.serial_number)
                    # Update order item with serial number if not already set
                    if not item.serial_number:
                        item.serial_number = stock_item.serial_number

        return serial_numbers

    async def _create_installation(
        self,
        order: Order,
        customer: Customer,
        delivery_address: Optional[Dict[str, Any]],
        serial_numbers: List[str],
        pod_data: Dict[str, Any]
    ) -> Installation:
        """Create Installation record for delivered products."""
        # Generate installation number
        inst_number = f"INST-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{str(uuid4())[:8].upper()}"

        # Build address JSON - delivery_address is already a dict
        address_json = delivery_address or {}
        pincode = address_json.get("pincode", "") or address_json.get("postal_code", "")
        city = address_json.get("city", "")

        # Get primary product from order
        primary_item = order.items[0] if order.items else None
        product_id = primary_item.product_id if primary_item else None
        serial_number = serial_numbers[0] if serial_numbers else None

        installation = Installation(
            installation_number=inst_number,
            order_id=order.id,
            customer_id=customer.id,
            product_id=product_id,
            serial_number=serial_number,  # First serial number
            status=InstallationStatus.PENDING,
            installation_address=address_json,
            installation_pincode=pincode,
            installation_city=city,
            preferred_date=(datetime.now(timezone.utc) + timedelta(days=2)).date(),  # Default: 2 days from delivery
            customer_signature_url=pod_data.get("signature_url"),
            notes=f"Auto-created after delivery. POD received by: {pod_data.get('received_by', 'N/A')}",
        )

        self.db.add(installation)
        await self.db.flush()

        return installation

    async def _create_service_request(
        self,
        installation: Installation,
        order: Order,
        customer: Customer,
        delivery_address: Optional[Dict[str, Any]]
    ) -> ServiceRequest:
        """Create ServiceRequest for installation."""
        # Generate service request number
        sr_number = f"SR-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{str(uuid4())[:8].upper()}"

        # Get primary product
        primary_item = order.items[0] if order.items else None
        product_id = primary_item.product_id if primary_item else None

        # Build address - delivery_address is a dict
        address_str = ""
        city = ""
        state = ""
        pincode = ""
        if delivery_address:
            addr_line1 = delivery_address.get("address_line1", "") or delivery_address.get("street", "")
            addr_line2 = delivery_address.get("address_line2", "")
            address_str = addr_line1
            if addr_line2:
                address_str += f", {addr_line2}"
            city = delivery_address.get("city", "")
            state = delivery_address.get("state", "")
            pincode = delivery_address.get("pincode", "") or delivery_address.get("postal_code", "")

        # Customer name - handle different formats
        customer_name = customer.first_name or ""
        if customer.last_name:
            customer_name += f" {customer.last_name}"
        if not customer_name:
            customer_name = "Customer"

        service_request = ServiceRequest(
            ticket_number=sr_number,
            customer_id=customer.id,
            order_id=order.id,
            installation_id=installation.id,
            product_id=product_id,
            serial_number=installation.serial_number,
            service_type=ServiceType.INSTALLATION,
            priority=ServicePriority.NORMAL,
            status=ServiceStatus.PENDING,
            source=ServiceSource.SYSTEM,  # Auto-generated
            title=f"Installation for Order #{order.order_number}",
            description=f"Installation request for {customer_name}. Order #{order.order_number}",
            service_address=delivery_address,  # Full address JSON
            service_pincode=pincode,
            service_city=city,
            service_state=state,
            preferred_date=installation.preferred_date,
            preferred_time_slot="10:00 AM - 12:00 PM",  # Default slot
        )

        self.db.add(service_request)
        await self.db.flush()

        return service_request

    async def _auto_assign_service(
        self,
        service_request: ServiceRequest,
        delivery_address: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Auto-assign service request to technician or franchisee based on:
        1. Pincode-based serviceability lookup
        2. Load balancing (current_load vs max_daily_capacity)
        3. Priority-based selection (lower priority = higher rank)
        4. Service type capability matching
        """
        assignment = {
            "technician_id": None,
            "franchisee_id": None,
            "assigned_to": None,
            "serviceability_id": None,
        }

        if not delivery_address:
            return assignment

        pincode = delivery_address.get("pincode", "") or delivery_address.get("postal_code", "")
        if not pincode:
            return assignment

        # Determine service type for capability matching
        service_type = service_request.service_type if service_request.service_type else "INSTALLATION"

        # Try to find available technician in the area
        technician = await self._find_available_technician(pincode)
        if technician:
            service_request.technician_id = technician.id
            service_request.status = ServiceStatus.ASSIGNED.value
            service_request.assigned_at = datetime.now(timezone.utc)
            assignment["technician_id"] = str(technician.id)
            assignment["assigned_to"] = "technician"
            return assignment

        # If no technician, use franchisee serviceability lookup
        franchisee, serviceability = await self._find_franchisee_by_pincode(pincode, service_type)
        if franchisee and serviceability:
            # Convert franchisee.id to UUID if it's a string (SQLite stores UUIDs as strings)
            franchisee_uuid = UUID(str(franchisee.id)) if isinstance(franchisee.id, str) else franchisee.id
            service_request.franchisee_id = franchisee_uuid
            service_request.status = ServiceStatus.ASSIGNED.value
            service_request.assigned_at = datetime.now(timezone.utc)
            assignment["franchisee_id"] = str(franchisee.id)
            assignment["serviceability_id"] = str(serviceability.id)
            assignment["assigned_to"] = "franchisee"

            # Update load counter (increment current_load)
            await self._increment_franchisee_load(serviceability)

            return assignment

        # No assignment - will need manual assignment
        return assignment

    async def _find_available_technician(self, pincode: str) -> Optional[Technician]:
        """Find available technician serving the pincode area."""
        # First 3 digits of pincode represent the region
        region_prefix = pincode[:3] if len(pincode) >= 3 else pincode

        stmt = (
            select(Technician)
            .where(
                and_(
                    Technician.status == TechnicianStatus.ACTIVE,
                    Technician.is_available == True,
                )
            )
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _find_franchisee_by_pincode(
        self,
        pincode: str,
        service_type: str = "INSTALLATION"
    ) -> tuple[Optional[Franchisee], Optional[FranchiseeServiceability]]:
        """
        Find the best franchisee for a pincode using serviceability mapping.

        Selection criteria:
        1. Pincode match (exact)
        2. Is active
        3. Has capacity (current_load < max_daily_capacity)
        4. Supports the required service type
        5. Ordered by priority (lower = higher rank), then by current_load
        """
        from datetime import date

        # Query franchisee_serviceability for this pincode
        stmt = (
            select(FranchiseeServiceability)
            .where(
                and_(
                    FranchiseeServiceability.pincode == pincode,
                    FranchiseeServiceability.is_active == True,
                    # Effective date check
                    FranchiseeServiceability.effective_from <= date.today(),
                    # Not expired (effective_to is null or in future)
                )
            )
            .order_by(
                FranchiseeServiceability.priority.asc(),  # Lower priority = higher rank
                FranchiseeServiceability.current_load.asc(),  # Less loaded first
            )
        )
        result = await self.db.execute(stmt)
        serviceability_records = result.scalars().all()

        # Find the first franchisee with capacity and matching service type
        for serviceability in serviceability_records:
            # Check capacity
            if serviceability.current_load >= serviceability.max_daily_capacity:
                continue

            # Check service type capability (service_types is JSON array)
            service_types = serviceability.service_types or []
            # Case-insensitive service type check
            service_types_upper = [st.upper() for st in service_types] if service_types else []
            service_type_upper = service_type.upper() if service_type else ""
            if service_types_upper and service_type_upper not in service_types_upper:
                # If FULL_SERVICE is in list, accept all service types
                if "FULL_SERVICE" not in service_types_upper:
                    continue

            # Check if franchisee is active
            # franchisee_id is already a string (VARCHAR in production)
            franchisee_id = serviceability.franchisee_id

            franchisee_stmt = (
                select(Franchisee)
                .where(
                    and_(
                        Franchisee.id == franchisee_id,
                        Franchisee.status == FranchiseeStatus.ACTIVE,
                    )
                )
            )
            franchisee_result = await self.db.execute(franchisee_stmt)
            franchisee = franchisee_result.scalar_one_or_none()

            if franchisee:
                return franchisee, serviceability

        return None, None

    async def _increment_franchisee_load(self, serviceability: FranchiseeServiceability) -> None:
        """Increment the current_load counter for the serviceability record."""
        serviceability.current_load = (serviceability.current_load or 0) + 1
        serviceability.updated_at = datetime.now(timezone.utc)

    async def _queue_notifications(
        self,
        customer: Customer,
        order: Order,
        installation: Installation,
        service_request: ServiceRequest,
        assignment: Dict[str, Any]
    ) -> List[str]:
        """
        Send notifications to customer about:
        1. Delivery confirmation
        2. Installation scheduled
        3. Technician/Franchisee assigned
        """
        notifications_sent = []

        try:
            from app.services.notification_service import NotificationService

            notification_service = NotificationService(self.db)

            # Get customer name
            cust_name = customer.first_name or ""
            if customer.last_name:
                cust_name += f" {customer.last_name}"
            if not cust_name:
                cust_name = "Customer"

            # 1. Order Delivered notification
            await notification_service.send_order_delivered_notifications(
                customer_phone=customer.phone,
                customer_email=customer.email,
                customer_name=cust_name,
                order_number=order.order_number,
                installation_number=installation.installation_number,
            )
            notifications_sent.append("ORDER_DELIVERED")

            # 2. Installation scheduled notification
            scheduled_date = installation.preferred_date.strftime("%d-%b-%Y") if installation.preferred_date else "within 2 days"
            await notification_service.send_installation_scheduled_notification(
                customer_phone=customer.phone,
                customer_email=customer.email,
                installation_number=installation.installation_number,
                scheduled_date=scheduled_date,
                time_slot="10:00 AM - 12:00 PM",  # Default time slot
            )
            notifications_sent.append("INSTALLATION_SCHEDULED")

            # 3. Technician assigned notification (if assigned)
            if assignment.get("technician_id"):
                # Get technician details
                from app.models import Technician
                tech_stmt = select(Technician).where(Technician.id == assignment["technician_id"])
                tech_result = await self.db.execute(tech_stmt)
                technician = tech_result.scalar_one_or_none()

                if technician:
                    await notification_service.send_installation_scheduled_notification(
                        customer_phone=customer.phone,
                        customer_email=customer.email,
                        installation_number=installation.installation_number,
                        scheduled_date=scheduled_date,
                        time_slot="10:00 AM - 12:00 PM",
                        technician_name=technician.name,
                        technician_phone=technician.phone,
                    )
                    notifications_sent.append("TECHNICIAN_ASSIGNED")

        except Exception as e:
            import logging
            logging.warning(f"Failed to send notifications: {e}")
            # Don't fail the workflow if notifications fail

        return notifications_sent


# Convenience function for use in endpoints
async def process_pod_delivery(
    db: AsyncSession,
    shipment_id: str,
    pod_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Process POD delivery and trigger post-delivery workflow.

    Usage in endpoint:
        from app.services.post_delivery_service import process_pod_delivery

        result = await process_pod_delivery(
            db=db,
            shipment_id=shipment_id,
            pod_data={
                "signature_url": "https://...",
                "image_url": "https://...",
                "received_by": "John Doe",
                "latitude": 28.6139,
                "longitude": 77.2090,
                "remarks": "Delivered successfully"
            }
        )
    """
    service = PostDeliveryService(db)
    return await service.process_delivery(shipment_id, pod_data)
