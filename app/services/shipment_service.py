"""Service for managing shipments and delivery tracking."""
from typing import List, Optional, Tuple
from datetime import datetime, date, timezone
from math import ceil
import uuid

from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.shipment import Shipment, ShipmentTracking, ShipmentStatus, PaymentMode, PackagingType
from app.models.order import Order, OrderItem, OrderStatus
from app.models.product import Product
from app.models.transporter import Transporter
from app.schemas.shipment import ShipmentCreate, ShipmentUpdate, ShipmentTrackingUpdate


class ShipmentService:
    """Service for shipment management and tracking."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ==================== SHIPMENT NUMBER GENERATION ====================

    async def generate_shipment_number(self) -> str:
        """Generate unique shipment number: SH-YYYYMMDD-XXXX"""
        today = datetime.now(timezone.utc).strftime("%Y%m%d")
        prefix = f"SH-{today}-"

        stmt = select(func.count(Shipment.id)).where(
            Shipment.shipment_number.like(f"{prefix}%")
        )
        count = (await self.db.execute(stmt)).scalar() or 0

        return f"{prefix}{(count + 1):04d}"

    # ==================== SHIPMENT CRUD ====================

    async def get_shipment(self, shipment_id: uuid.UUID) -> Optional[Shipment]:
        """Get shipment by ID with tracking history."""
        stmt = (
            select(Shipment)
            .options(
                selectinload(Shipment.tracking_history),
                selectinload(Shipment.transporter),
                selectinload(Shipment.warehouse),
            )
            .where(Shipment.id == shipment_id)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_shipment_by_awb(self, awb_number: str) -> Optional[Shipment]:
        """Get shipment by AWB number."""
        stmt = (
            select(Shipment)
            .options(selectinload(Shipment.tracking_history))
            .where(Shipment.awb_number == awb_number)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_shipments(
        self,
        warehouse_id: Optional[uuid.UUID] = None,
        transporter_id: Optional[uuid.UUID] = None,
        order_id: Optional[uuid.UUID] = None,
        status: Optional[ShipmentStatus] = None,
        payment_mode: Optional[PaymentMode] = None,
        pincode: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 20
    ) -> Tuple[List[Shipment], int]:
        """Get paginated shipments with filters."""
        stmt = (
            select(Shipment)
            .options(selectinload(Shipment.transporter))
            .order_by(Shipment.created_at.desc())
        )

        filters = []
        if warehouse_id:
            filters.append(Shipment.warehouse_id == warehouse_id)
        if transporter_id:
            filters.append(Shipment.transporter_id == transporter_id)
        if order_id:
            filters.append(Shipment.order_id == order_id)
        if status:
            filters.append(Shipment.status == status)
        if payment_mode:
            filters.append(Shipment.payment_mode == payment_mode)
        if pincode:
            filters.append(Shipment.ship_to_pincode == pincode)
        if date_from:
            filters.append(Shipment.created_at >= date_from)
        if date_to:
            filters.append(Shipment.created_at <= date_to)

        if filters:
            stmt = stmt.where(and_(*filters))

        # Count
        count_stmt = select(func.count(Shipment.id))
        if filters:
            count_stmt = count_stmt.where(and_(*filters))
        total = (await self.db.execute(count_stmt)).scalar() or 0

        # Paginate
        stmt = stmt.offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        items = list(result.scalars().all())

        return items, total

    async def create_shipment(
        self,
        data: ShipmentCreate,
        created_by: Optional[uuid.UUID] = None
    ) -> Shipment:
        """Create new shipment from order."""
        # Verify order exists with items
        stmt = (
            select(Order)
            .options(selectinload(Order.items).selectinload(OrderItem.product))
            .where(Order.id == data.order_id)
        )
        result = await self.db.execute(stmt)
        order = result.scalar_one_or_none()

        if not order:
            raise ValueError("Order not found")

        if order.status not in [OrderStatus.PICKED, OrderStatus.PACKED, OrderStatus.PACKING]:
            raise ValueError(f"Cannot create shipment for order in {order.status} status")

        # Generate shipment number
        shipment_number = await self.generate_shipment_number()

        # Calculate weight - use provided values or calculate from products
        weight_kg = data.weight_kg
        volumetric_weight = None
        chargeable_weight = 0.0

        if data.length_cm and data.breadth_cm and data.height_cm:
            # Calculate volumetric weight from provided dimensions
            volumetric_weight = (data.length_cm * data.breadth_cm * data.height_cm) / 5000
            chargeable_weight = max(weight_kg, volumetric_weight or 0)
        elif not weight_kg or weight_kg == 0:
            # Calculate weight from Master Product File (sum of all items)
            total_chargeable_weight = 0.0
            for item in order.items:
                if item.product:
                    # Use product's chargeable_weight_kg (computed property)
                    product_weight = item.product.chargeable_weight_kg or 0.0
                    total_chargeable_weight += product_weight * item.quantity

            if total_chargeable_weight > 0:
                chargeable_weight = total_chargeable_weight
                weight_kg = total_chargeable_weight  # Use as dead weight approximation
        else:
            chargeable_weight = weight_kg

        shipment = Shipment(
            shipment_number=shipment_number,
            order_id=data.order_id,
            warehouse_id=data.warehouse_id,
            transporter_id=data.transporter_id,
            payment_mode=data.payment_mode,
            cod_amount=data.cod_amount if data.payment_mode == PaymentMode.COD else None,
            packaging_type=data.packaging_type,
            no_of_boxes=data.no_of_boxes,
            weight_kg=data.weight_kg,
            volumetric_weight_kg=volumetric_weight,
            chargeable_weight_kg=chargeable_weight,
            length_cm=data.length_cm,
            breadth_cm=data.breadth_cm,
            height_cm=data.height_cm,
            ship_to_name=data.ship_to_name,
            ship_to_phone=data.ship_to_phone,
            ship_to_email=data.ship_to_email,
            ship_to_address=data.ship_to_address,
            ship_to_pincode=data.ship_to_pincode,
            ship_to_city=data.ship_to_city,
            ship_to_state=data.ship_to_state,
            expected_delivery_date=data.expected_delivery_date,
            created_by=created_by,
            status=ShipmentStatus.CREATED,
        )

        self.db.add(shipment)
        await self.db.flush()  # Flush to get shipment.id assigned

        # Add initial tracking entry
        tracking = ShipmentTracking(
            shipment_id=shipment.id,
            status=ShipmentStatus.CREATED,
            remarks="Shipment created",
            source="SYSTEM",
        )
        self.db.add(tracking)

        await self.db.commit()
        await self.db.refresh(shipment)

        return shipment

    # ==================== PACKING ====================

    async def pack_shipment(
        self,
        shipment_id: uuid.UUID,
        packaging_type: PackagingType = PackagingType.BOX,
        no_of_boxes: int = 1,
        weight_kg: float = None,
        length_cm: float = None,
        breadth_cm: float = None,
        height_cm: float = None,
        packed_by: Optional[uuid.UUID] = None,
        notes: Optional[str] = None
    ) -> Shipment:
        """Mark shipment as packed."""
        shipment = await self.get_shipment(shipment_id)
        if not shipment:
            raise ValueError("Shipment not found")

        if shipment.status != ShipmentStatus.CREATED:
            raise ValueError(f"Cannot pack shipment in {shipment.status} status")

        shipment.packaging_type = packaging_type
        shipment.no_of_boxes = no_of_boxes
        if weight_kg:
            shipment.weight_kg = weight_kg
        if length_cm:
            shipment.length_cm = length_cm
        if breadth_cm:
            shipment.breadth_cm = breadth_cm
        if height_cm:
            shipment.height_cm = height_cm

        # Recalculate volumetric weight
        if shipment.length_cm and shipment.breadth_cm and shipment.height_cm:
            shipment.volumetric_weight_kg = (
                shipment.length_cm * shipment.breadth_cm * shipment.height_cm
            ) / 5000
            shipment.chargeable_weight_kg = max(
                shipment.weight_kg, shipment.volumetric_weight_kg
            )

        shipment.status = ShipmentStatus.PACKED.value
        shipment.packed_at = datetime.now(timezone.utc)
        shipment.packed_by = packed_by

        # Add tracking entry
        tracking = ShipmentTracking(
            shipment_id=shipment.id,
            status=ShipmentStatus.PACKED,
            remarks=notes or "Shipment packed",
            source="MANUAL",
            updated_by=packed_by,
        )
        self.db.add(tracking)

        # Update order status
        stmt = select(Order).where(Order.id == shipment.order_id)
        result = await self.db.execute(stmt)
        order = result.scalar_one_or_none()
        if order:
            order.status = OrderStatus.PACKED.value
            order.packed_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(shipment)
        return shipment

    # ==================== AWB GENERATION ====================

    async def generate_awb(
        self,
        shipment_id: uuid.UUID,
        transporter_id: Optional[uuid.UUID] = None
    ) -> Shipment:
        """Generate AWB number for shipment."""
        shipment = await self.get_shipment(shipment_id)
        if not shipment:
            raise ValueError("Shipment not found")

        if shipment.awb_number:
            raise ValueError("AWB already generated for this shipment")

        # Get transporter
        t_id = transporter_id or shipment.transporter_id
        if not t_id:
            raise ValueError("No transporter specified")

        stmt = select(Transporter).where(Transporter.id == t_id)
        result = await self.db.execute(stmt)
        transporter = result.scalar_one_or_none()

        if not transporter:
            raise ValueError("Transporter not found")

        # Generate AWB
        prefix = transporter.awb_prefix or transporter.code[:3].upper()
        sequence = transporter.awb_sequence_current

        awb_number = f"{prefix}{sequence:010d}"

        # Update transporter sequence
        transporter.awb_sequence_current = sequence + 1

        # Update shipment
        shipment.awb_number = awb_number
        shipment.transporter_id = t_id

        await self.db.commit()
        await self.db.refresh(shipment)
        return shipment

    # ==================== TRACKING ====================

    async def add_tracking_update(
        self,
        data: ShipmentTrackingUpdate,
        updated_by: Optional[uuid.UUID] = None
    ) -> ShipmentTracking:
        """Add tracking update to shipment."""
        shipment = await self.get_shipment(data.shipment_id)
        if not shipment:
            raise ValueError("Shipment not found")

        # Update shipment status
        shipment.status = data.status

        # Create tracking entry
        tracking = ShipmentTracking(
            shipment_id=data.shipment_id,
            status=data.status,
            status_code=data.status_code,
            location=data.location,
            city=data.city,
            state=data.state,
            pincode=data.pincode,
            remarks=data.remarks,
            event_time=data.event_time or datetime.now(timezone.utc),
            source=data.source,
            updated_by=updated_by,
        )
        self.db.add(tracking)

        await self.db.commit()
        await self.db.refresh(tracking)
        return tracking

    # ==================== DELIVERY ====================

    async def mark_out_for_delivery(
        self,
        shipment_id: uuid.UUID,
        remarks: Optional[str] = None
    ) -> Shipment:
        """Mark shipment as out for delivery."""
        shipment = await self.get_shipment(shipment_id)
        if not shipment:
            raise ValueError("Shipment not found")

        if shipment.status not in [ShipmentStatus.IN_TRANSIT, ShipmentStatus.DELIVERY_FAILED]:
            raise ValueError(f"Cannot mark as out for delivery from {shipment.status} status")

        shipment.status = ShipmentStatus.OUT_FOR_DELIVERY.value
        shipment.delivery_attempts += 1

        # Add tracking
        tracking = ShipmentTracking(
            shipment_id=shipment.id,
            status=ShipmentStatus.OUT_FOR_DELIVERY,
            remarks=remarks or f"Out for delivery (Attempt {shipment.delivery_attempts})",
            source="SYSTEM",
        )
        self.db.add(tracking)

        # Update order
        stmt = select(Order).where(Order.id == shipment.order_id)
        result = await self.db.execute(stmt)
        order = result.scalar_one_or_none()
        if order:
            order.status = OrderStatus.OUT_FOR_DELIVERY.value

        await self.db.commit()
        await self.db.refresh(shipment)
        return shipment

    async def mark_delivered(
        self,
        shipment_id: uuid.UUID,
        delivered_to: str,
        delivery_relation: Optional[str] = None,
        delivery_remarks: Optional[str] = None,
        pod_image_url: Optional[str] = None,
        pod_signature_url: Optional[str] = None,
        pod_latitude: Optional[float] = None,
        pod_longitude: Optional[float] = None,
        cod_collected: bool = False
    ) -> Shipment:
        """Mark shipment as delivered."""
        shipment = await self.get_shipment(shipment_id)
        if not shipment:
            raise ValueError("Shipment not found")

        if shipment.status != ShipmentStatus.OUT_FOR_DELIVERY:
            raise ValueError(f"Cannot mark as delivered from {shipment.status} status")

        now = datetime.now(timezone.utc)

        shipment.status = ShipmentStatus.DELIVERED.value
        shipment.delivered_at = now
        shipment.actual_delivery_date = now.date()
        shipment.delivered_to = delivered_to
        shipment.delivery_relation = delivery_relation
        shipment.delivery_remarks = delivery_remarks
        shipment.pod_image_url = pod_image_url
        shipment.pod_signature_url = pod_signature_url
        shipment.pod_latitude = pod_latitude
        shipment.pod_longitude = pod_longitude

        if shipment.payment_mode == PaymentMode.COD:
            shipment.cod_collected = cod_collected
            if cod_collected:
                shipment.cod_collected_at = now

        # Add tracking
        tracking = ShipmentTracking(
            shipment_id=shipment.id,
            status=ShipmentStatus.DELIVERED,
            remarks=f"Delivered to {delivered_to}",
            source="MANUAL",
        )
        self.db.add(tracking)

        # Update order
        stmt = select(Order).where(Order.id == shipment.order_id)
        result = await self.db.execute(stmt)
        order = result.scalar_one_or_none()
        if order:
            order.status = OrderStatus.DELIVERED.value
            order.delivered_at = now

        await self.db.commit()
        await self.db.refresh(shipment)
        return shipment

    async def mark_delivery_failed(
        self,
        shipment_id: uuid.UUID,
        reason: str
    ) -> Shipment:
        """Mark delivery attempt as failed."""
        shipment = await self.get_shipment(shipment_id)
        if not shipment:
            raise ValueError("Shipment not found")

        if shipment.status != ShipmentStatus.OUT_FOR_DELIVERY:
            raise ValueError(f"Cannot mark delivery failed from {shipment.status} status")

        shipment.status = ShipmentStatus.DELIVERY_FAILED.value

        # Add tracking
        tracking = ShipmentTracking(
            shipment_id=shipment.id,
            status=ShipmentStatus.DELIVERY_FAILED,
            remarks=f"Delivery failed: {reason}",
            source="MANUAL",
        )
        self.db.add(tracking)

        await self.db.commit()
        await self.db.refresh(shipment)
        return shipment

    # ==================== RTO ====================

    async def initiate_rto(
        self,
        shipment_id: uuid.UUID,
        reason: str
    ) -> Shipment:
        """Initiate Return to Origin."""
        shipment = await self.get_shipment(shipment_id)
        if not shipment:
            raise ValueError("Shipment not found")

        if shipment.status not in [ShipmentStatus.DELIVERY_FAILED, ShipmentStatus.IN_TRANSIT]:
            raise ValueError(f"Cannot initiate RTO from {shipment.status} status")

        if shipment.delivery_attempts < shipment.max_delivery_attempts:
            raise ValueError(f"RTO requires {shipment.max_delivery_attempts} failed attempts. Current: {shipment.delivery_attempts}")

        shipment.status = ShipmentStatus.RTO_INITIATED.value
        shipment.rto_reason = reason
        shipment.rto_initiated_at = datetime.now(timezone.utc)

        # Add tracking
        tracking = ShipmentTracking(
            shipment_id=shipment.id,
            status=ShipmentStatus.RTO_INITIATED,
            remarks=f"RTO initiated: {reason}",
            source="MANUAL",
        )
        self.db.add(tracking)

        # Update order
        stmt = select(Order).where(Order.id == shipment.order_id)
        result = await self.db.execute(stmt)
        order = result.scalar_one_or_none()
        if order:
            order.status = OrderStatus.RTO_INITIATED.value

        await self.db.commit()
        await self.db.refresh(shipment)
        return shipment

    async def complete_rto(
        self,
        shipment_id: uuid.UUID,
        remarks: Optional[str] = None
    ) -> Shipment:
        """Complete RTO - shipment returned to warehouse."""
        shipment = await self.get_shipment(shipment_id)
        if not shipment:
            raise ValueError("Shipment not found")

        if shipment.status not in [ShipmentStatus.RTO_INITIATED, ShipmentStatus.RTO_IN_TRANSIT]:
            raise ValueError(f"Cannot complete RTO from {shipment.status} status")

        shipment.status = ShipmentStatus.RTO_DELIVERED.value
        shipment.rto_delivered_at = datetime.now(timezone.utc)

        # Add tracking
        tracking = ShipmentTracking(
            shipment_id=shipment.id,
            status=ShipmentStatus.RTO_DELIVERED,
            remarks=remarks or "RTO completed - returned to warehouse",
            source="MANUAL",
        )
        self.db.add(tracking)

        # Update order
        stmt = select(Order).where(Order.id == shipment.order_id)
        result = await self.db.execute(stmt)
        order = result.scalar_one_or_none()
        if order:
            order.status = OrderStatus.RTO_DELIVERED.value

        await self.db.commit()
        await self.db.refresh(shipment)
        return shipment

    # ==================== CANCEL ====================

    async def cancel_shipment(
        self,
        shipment_id: uuid.UUID,
        reason: str
    ) -> Shipment:
        """Cancel shipment."""
        shipment = await self.get_shipment(shipment_id)
        if not shipment:
            raise ValueError("Shipment not found")

        if shipment.status in [ShipmentStatus.DELIVERED, ShipmentStatus.RTO_DELIVERED, ShipmentStatus.CANCELLED]:
            raise ValueError(f"Cannot cancel shipment in {shipment.status} status")

        shipment.status = ShipmentStatus.CANCELLED.value
        shipment.cancelled_at = datetime.now(timezone.utc)
        shipment.cancellation_reason = reason

        # Add tracking
        tracking = ShipmentTracking(
            shipment_id=shipment.id,
            status=ShipmentStatus.CANCELLED,
            remarks=f"Cancelled: {reason}",
            source="MANUAL",
        )
        self.db.add(tracking)

        await self.db.commit()
        await self.db.refresh(shipment)
        return shipment

    # ==================== AUTO-CREATE FROM ORDER ====================

    async def create_shipment_from_order(
        self,
        order: Order,
        transporter_id: Optional[uuid.UUID] = None,
        created_by: Optional[uuid.UUID] = None
    ) -> Shipment:
        """
        Auto-create shipment directly from order (for allocated orders).
        This method bypasses the normal picking/packing workflow for testing/demo purposes.
        """
        # Generate shipment number
        shipment_number = await self.generate_shipment_number()

        # Get shipping address from order
        ship_addr = order.shipping_address or {}
        ship_to_name = ship_addr.get('contact_name', ship_addr.get('name', ''))
        ship_to_phone = ship_addr.get('contact_phone', ship_addr.get('phone', ''))
        ship_to_email = ship_addr.get('email', '')
        ship_to_pincode = ship_addr.get('pincode', '')
        ship_to_city = ship_addr.get('city', '')
        ship_to_state = ship_addr.get('state', '')

        # Calculate payment mode
        payment_mode_str = "PREPAID"
        cod_amount = None
        if order.payment_method == "COD" or str(order.payment_method) == "COD":
            payment_mode_str = "COD"
            cod_amount = float(order.total_amount)

        # Calculate weight from order items if order has items
        total_weight = 0.0
        if order.items:
            for item in order.items:
                if item.product:
                    product_weight = getattr(item.product, 'chargeable_weight_kg', 0) or 0
                    total_weight += product_weight * item.quantity

        # Default weight if no products
        if total_weight <= 0:
            total_weight = 1.0  # Default 1 kg

        # Generate AWB number (internal format until transporter assigns real one)
        awb_prefix = "AQ"
        today = datetime.now(timezone.utc).strftime("%Y%m%d")
        import random
        awb_number = f"{awb_prefix}{today}{random.randint(100000, 999999)}"

        shipment = Shipment(
            shipment_number=shipment_number,
            order_id=order.id,
            warehouse_id=order.warehouse_id,
            transporter_id=transporter_id,
            awb_number=awb_number,
            status="CREATED",  # Database uses VARCHAR, not Enum
            payment_mode=payment_mode_str,
            cod_amount=cod_amount,
            packaging_type="BOX",
            no_of_boxes=1,
            weight_kg=total_weight,
            chargeable_weight_kg=total_weight,
            ship_to_name=ship_to_name,
            ship_to_phone=ship_to_phone,
            ship_to_email=ship_to_email,
            ship_to_address=ship_addr,
            ship_to_pincode=ship_to_pincode,
            ship_to_city=ship_to_city,
            ship_to_state=ship_to_state,
            created_by=created_by,
        )

        self.db.add(shipment)
        await self.db.flush()  # Flush to get shipment.id assigned

        # Add initial tracking entry
        tracking = ShipmentTracking(
            shipment_id=shipment.id,
            status="CREATED",  # Database uses VARCHAR, not Enum
            remarks="Shipment auto-created from order allocation",
            source="SYSTEM",
        )
        self.db.add(tracking)

        await self.db.commit()
        await self.db.refresh(shipment)

        return shipment
