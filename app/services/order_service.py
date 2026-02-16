from typing import List, Optional, Tuple
from datetime import datetime, timezone
from decimal import Decimal
from math import ceil
import uuid
import logging

from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.models.customer import Customer, CustomerAddress
from app.models.order import (
    Order, OrderItem, OrderStatus, OrderStatusHistory,
    Payment, PaymentStatus, PaymentMethod, OrderSource, Invoice
)
from app.models.product import Product, ProductVariant
from app.models.community_partner import CommunityPartner, PartnerOrder, PartnerCommission
from app.schemas.order import OrderCreate, OrderUpdate, OrderItemCreate
from app.services.pricing_service import PricingService

logger = logging.getLogger(__name__)


class OrderService:
    """Service for managing orders and related operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ==================== ORDER NUMBER GENERATION ====================

    async def generate_order_number(self) -> str:
        """Generate unique order number: ORD-YYYYMMDD-XXXX"""
        today = datetime.now(timezone.utc).strftime("%Y%m%d")
        prefix = f"ORD-{today}-"

        # Get count of orders today
        stmt = select(func.count(Order.id)).where(
            Order.order_number.like(f"{prefix}%")
        )
        count = (await self.db.execute(stmt)).scalar() or 0

        return f"{prefix}{(count + 1):04d}"

    async def generate_invoice_number(self) -> str:
        """Generate unique invoice number: INV-YYYYMMDD-XXXX"""
        today = datetime.now(timezone.utc).strftime("%Y%m%d")
        prefix = f"INV-{today}-"

        stmt = select(func.count(Invoice.id)).where(
            Invoice.invoice_number.like(f"{prefix}%")
        )
        count = (await self.db.execute(stmt)).scalar() or 0

        return f"{prefix}{(count + 1):04d}"

    # ==================== CUSTOMER METHODS ====================

    async def generate_customer_code(self) -> str:
        """Generate unique customer code: CUST-XXXXX"""
        stmt = select(func.count(Customer.id))
        count = (await self.db.execute(stmt)).scalar() or 0
        return f"CUST-{(count + 1):05d}"

    async def get_customers(
        self,
        search: Optional[str] = None,
        customer_type: Optional[str] = None,
        is_active: bool = True,
        skip: int = 0,
        limit: int = 20
    ) -> Tuple[List[Customer], int]:
        """Get paginated customers."""
        stmt = (
            select(Customer)
            .options(selectinload(Customer.addresses))
            .order_by(Customer.created_at.desc())
        )

        filters = []
        if is_active is not None:
            filters.append(Customer.is_active == is_active)

        if customer_type:
            filters.append(Customer.customer_type == customer_type)

        if search:
            search_filter = f"%{search}%"
            filters.append(
                or_(
                    Customer.first_name.ilike(search_filter),
                    Customer.last_name.ilike(search_filter),
                    Customer.phone.ilike(search_filter),
                    Customer.email.ilike(search_filter),
                    Customer.customer_code.ilike(search_filter),
                )
            )

        if filters:
            stmt = stmt.where(and_(*filters))

        # Count
        count_stmt = select(func.count(Customer.id))
        if filters:
            count_stmt = count_stmt.where(and_(*filters))
        total = (await self.db.execute(count_stmt)).scalar()

        # Paginate
        stmt = stmt.offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        customers = result.scalars().unique().all()

        return list(customers), total

    async def get_customer_by_id(self, customer_id: uuid.UUID) -> Optional[Customer]:
        """Get customer by ID."""
        stmt = (
            select(Customer)
            .options(selectinload(Customer.addresses))
            .where(Customer.id == customer_id)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_customer_by_phone(self, phone: str) -> Optional[Customer]:
        """Get customer by phone."""
        stmt = (
            select(Customer)
            .options(selectinload(Customer.addresses))
            .where(Customer.phone == phone)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_customer(self, data: dict) -> Customer:
        """Create a new customer."""
        addresses_data = data.pop("addresses", [])
        customer_code = await self.generate_customer_code()

        customer = Customer(customer_code=customer_code, **data)
        self.db.add(customer)
        await self.db.flush()

        # Add addresses
        for addr_data in addresses_data:
            address = CustomerAddress(customer_id=customer.id, **addr_data)
            self.db.add(address)

        await self.db.commit()
        return await self.get_customer_by_id(customer.id)

    async def update_customer(
        self,
        customer_id: uuid.UUID,
        data: dict
    ) -> Optional[Customer]:
        """Update a customer."""
        customer = await self.get_customer_by_id(customer_id)
        if not customer:
            return None

        for key, value in data.items():
            if value is not None:
                setattr(customer, key, value)

        await self.db.commit()
        return await self.get_customer_by_id(customer_id)

    # ==================== ORDER METHODS ====================

    async def get_orders(
        self,
        customer_id: Optional[uuid.UUID] = None,
        status: Optional[OrderStatus] = None,
        payment_status: Optional[PaymentStatus] = None,
        source: Optional[OrderSource] = None,
        region_id: Optional[uuid.UUID] = None,
        search: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 20,
        sort_by: str = "created_at",
        sort_order: str = "desc"
    ) -> Tuple[List[Order], int]:
        """Get paginated orders with filters."""
        stmt = (
            select(Order)
            .options(
                selectinload(Order.customer),
                selectinload(Order.items),
            )
        )

        filters = []

        if customer_id:
            filters.append(Order.customer_id == customer_id)

        if status:
            filters.append(Order.status == status)

        if payment_status:
            filters.append(Order.payment_status == payment_status)

        if source:
            filters.append(Order.source == source)

        if region_id:
            filters.append(Order.region_id == region_id)

        if date_from:
            filters.append(Order.created_at >= date_from)

        if date_to:
            filters.append(Order.created_at <= date_to)

        if search:
            search_filter = f"%{search}%"
            filters.append(
                or_(
                    Order.order_number.ilike(search_filter),
                )
            )

        if filters:
            stmt = stmt.where(and_(*filters))

        # Count
        count_stmt = select(func.count(Order.id))
        if filters:
            count_stmt = count_stmt.where(and_(*filters))
        total = (await self.db.execute(count_stmt)).scalar()

        # Sort
        sort_column = getattr(Order, sort_by, Order.created_at)
        if sort_order == "desc":
            stmt = stmt.order_by(sort_column.desc())
        else:
            stmt = stmt.order_by(sort_column.asc())

        # Paginate
        stmt = stmt.offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        orders = result.scalars().unique().all()

        return list(orders), total

    async def get_order_by_id(
        self,
        order_id: uuid.UUID,
        include_all: bool = False
    ) -> Optional[Order]:
        """Get order by ID."""
        stmt = select(Order).where(Order.id == order_id)

        if include_all:
            stmt = stmt.options(
                selectinload(Order.customer),
                selectinload(Order.items).selectinload(OrderItem.product),
                selectinload(Order.status_history),
                selectinload(Order.payments),
                selectinload(Order.invoice),
            )
        else:
            stmt = stmt.options(
                selectinload(Order.customer),
                selectinload(Order.items),
            )

        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_order_by_number(self, order_number: str) -> Optional[Order]:
        """Get order by order number."""
        stmt = (
            select(Order)
            .options(
                selectinload(Order.customer),
                selectinload(Order.items),
                selectinload(Order.status_history),
                selectinload(Order.payments),
                selectinload(Order.invoice),
            )
            .where(Order.order_number == order_number)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_order(
        self,
        data: OrderCreate,
        created_by: Optional[uuid.UUID] = None
    ) -> Order:
        """Create a new order."""
        # Generate order number
        order_number = await self.generate_order_number()

        # Get customer
        customer = await self.get_customer_by_id(data.customer_id)
        if not customer:
            raise ValueError("Customer not found")

        # Process shipping address
        shipping_address = await self._process_address(
            data.shipping_address,
            customer
        )

        # Process billing address
        billing_address = None
        if data.billing_address:
            billing_address = await self._process_address(
                data.billing_address,
                customer
            )

        # Initialize pricing service for channel-specific pricing
        pricing_service = PricingService(self.db)
        customer_segment = data.customer_segment or "STANDARD"

        # Calculate totals
        subtotal = Decimal("0.00")
        tax_amount = Decimal("0.00")
        items_data = []

        for item_data in data.items:
            product = await self._get_product(item_data.product_id)
            if not product:
                raise ValueError(f"Product {item_data.product_id} not found")

            variant = None
            if item_data.variant_id:
                variant = await self._get_variant(item_data.variant_id)

            # Determine prices using PricingService (if channel_id provided)
            unit_price = item_data.unit_price  # Use explicit price if provided
            unit_mrp = product.mrp
            pricing_rules_applied = []

            if not unit_price:
                if data.channel_id:
                    # Use channel-specific pricing with rules
                    try:
                        price_result = await pricing_service.calculate_price(
                            product_id=item_data.product_id,
                            channel_id=data.channel_id,
                            quantity=item_data.quantity,
                            variant_id=item_data.variant_id,
                            customer_segment=customer_segment,
                        )
                        unit_price = Decimal(str(price_result["unit_price"]))
                        if price_result.get("mrp"):
                            unit_mrp = Decimal(str(price_result["mrp"]))
                        pricing_rules_applied = price_result.get("rules_applied", [])
                        logger.info(
                            f"Channel pricing applied for product {item_data.product_id}: "
                            f"price={unit_price}, source={price_result['price_source']}"
                        )
                    except Exception as e:
                        logger.warning(f"Channel pricing failed, using product price: {e}")
                        unit_price = product.selling_price or product.mrp
                else:
                    # Fallback to product master pricing
                    unit_price = product.selling_price or product.mrp

            # Override with variant pricing if applicable
            if variant:
                if variant.mrp:
                    unit_mrp = variant.mrp
                # Note: Variant pricing is already considered in PricingService if variant_id passed

            # Calculate item totals
            item_subtotal = unit_price * item_data.quantity
            item_tax_rate = product.gst_rate or Decimal("18.00")
            item_tax = (item_subtotal * item_tax_rate) / 100
            item_total = item_subtotal + item_tax

            items_data.append({
                "product": product,
                "variant": variant,
                "quantity": item_data.quantity,
                "unit_price": unit_price,
                "unit_mrp": unit_mrp,
                "tax_rate": item_tax_rate,
                "tax_amount": item_tax,
                "total_amount": item_total,
                "pricing_rules_applied": pricing_rules_applied,
            })

            subtotal += item_subtotal
            tax_amount += item_tax

        total_amount = subtotal + tax_amount

        # Credit limit check
        if customer.credit_limit is not None:
            current_used = getattr(customer, 'credit_used', None) or Decimal("0")
            new_exposure = current_used + total_amount
            if new_exposure > customer.credit_limit:
                raise ValueError(
                    f"Credit limit exceeded. Limit: {customer.credit_limit}, "
                    f"Used: {current_used}, Order: {total_amount}"
                )

        # Create order - use string values for VARCHAR columns (per CLAUDE.md standards)
        from app.core.enum_utils import get_enum_value

        try:
            order = Order(
                order_number=order_number,
                customer_id=data.customer_id,
                channel_id=data.channel_id,  # Sales channel for pricing
                source=get_enum_value(data.source),  # Convert enum to string
                status="NEW",  # VARCHAR column - use string directly
                subtotal=subtotal,
                tax_amount=tax_amount,
                discount_amount=Decimal("0.00"),
                shipping_amount=Decimal("0.00"),
                total_amount=total_amount,
                discount_code=data.discount_code,
                payment_method=get_enum_value(data.payment_method),  # Convert enum to string
                payment_status="PENDING",  # VARCHAR column - use string directly
                shipping_address=shipping_address,
                billing_address=billing_address,
                customer_notes=data.customer_notes,
                internal_notes=data.internal_notes,
                region_id=data.region_id,
                created_by=created_by,
            )
            self.db.add(order)
            await self.db.flush()

            # Create order items
            for item in items_data:
                order_item = OrderItem(
                    order_id=order.id,
                    product_id=item["product"].id,
                    variant_id=item["variant"].id if item["variant"] else None,
                    product_name=item["product"].name,
                    product_sku=item["product"].sku,
                    variant_name=item["variant"].name if item["variant"] else None,
                    quantity=item["quantity"],
                    unit_price=item["unit_price"],
                    unit_mrp=item["unit_mrp"],
                    tax_rate=item["tax_rate"],
                    tax_amount=item["tax_amount"],
                    total_amount=item["total_amount"],
                    hsn_code=item["product"].hsn_code,
                    warranty_months=item["product"].warranty_months,
                )
                self.db.add(order_item)

            # Create initial status history - use string value for VARCHAR column
            status_history = OrderStatusHistory(
                order_id=order.id,
                from_status=None,
                to_status="NEW",  # VARCHAR column - use string directly
                changed_by=created_by,
                notes="Order created",
            )
            self.db.add(status_history)

            # Handle Community Partner attribution if partner_code provided
            if data.partner_code:
                await self._attribute_order_to_partner(
                    order=order,
                    partner_code=data.partner_code,
                    order_amount=total_amount,
                    customer_id=data.customer_id
                )

            await self.db.commit()
            return await self.get_order_by_id(order.id, include_all=True)

        except IntegrityError as e:
            await self.db.rollback()
            logger.error(f"Database integrity error creating order: {e}")
            raise ValueError(f"Order creation failed: Invalid data reference")
        except SQLAlchemyError as e:
            await self.db.rollback()
            logger.error(f"Database error creating order: {e}")
            raise ValueError(f"Order creation failed: Database error")
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Unexpected error creating order: {e}")
            raise

    async def update_order_status(
        self,
        order_id: uuid.UUID,
        new_status: OrderStatus,
        changed_by: Optional[uuid.UUID] = None,
        notes: Optional[str] = None
    ) -> Optional[Order]:
        """Update order status."""
        order = await self.get_order_by_id(order_id)
        if not order:
            return None

        old_status = order.status
        order.status = new_status

        # Update timestamps based on status
        if new_status == OrderStatus.CONFIRMED:
            order.confirmed_at = datetime.now(timezone.utc)
        elif new_status == OrderStatus.DELIVERED:
            order.delivered_at = datetime.now(timezone.utc)
            # Calculate partner commission on delivery
            await self.calculate_partner_commission(order_id)
        elif new_status == OrderStatus.CANCELLED:
            order.cancelled_at = datetime.now(timezone.utc)

        # Create status history
        status_history = OrderStatusHistory(
            order_id=order.id,
            from_status=old_status,
            to_status=new_status,
            changed_by=changed_by,
            notes=notes,
        )
        self.db.add(status_history)

        await self.db.commit()
        return await self.get_order_by_id(order_id, include_all=True)

    async def add_payment(
        self,
        order_id: uuid.UUID,
        amount: Decimal,
        method: PaymentMethod,
        transaction_id: Optional[str] = None,
        gateway: Optional[str] = None,
        reference_number: Optional[str] = None,
        notes: Optional[str] = None,
        user_id: Optional[uuid.UUID] = None
    ) -> Payment:
        """Add a payment to an order and create accounting entry."""
        order = await self.get_order_by_id(order_id)
        if not order:
            raise ValueError("Order not found")

        payment = Payment(
            order_id=order_id,
            amount=amount,
            method=method,
            status="CAPTURED",  # Use string directly, not enum.value
            transaction_id=transaction_id,
            gateway=gateway,
            reference_number=reference_number,
            notes=notes,
            completed_at=datetime.now(timezone.utc),
        )
        self.db.add(payment)

        # Update order payment status
        order.amount_paid += amount
        if order.amount_paid >= order.total_amount:
            order.payment_status = "PAID"  # Use string directly
        elif order.amount_paid > 0:
            order.payment_status = "PARTIALLY_PAID"  # Use string directly

        await self.db.commit()
        await self.db.refresh(payment)

        # ============ ACCOUNTING INTEGRATION ============
        # Create journal entry: DR Bank/Cash, CR Accounts Receivable
        try:
            from app.services.auto_journal_service import AutoJournalService, AutoJournalError
            auto_journal = AutoJournalService(self.db)

            # Determine payment account based on method
            # CASH methods go to Cash account, others to Bank
            payment_method_str = method if isinstance(method, str) else method.value
            is_cash = payment_method_str.upper() in ["CASH", "COD"]

            await auto_journal.generate_for_order_payment(
                order_id=order_id,
                amount=amount,
                payment_method=payment_method_str,
                reference_number=reference_number or transaction_id or str(payment.id),
                user_id=user_id,
                auto_post=True,  # Auto-post to GL immediately
                is_cash=is_cash,
            )
            # Commit the journal entry and GL entries
            await self.db.commit()
            logger.info(f"Accounting entry created for payment on order {order.order_number}")
        except AutoJournalError as e:
            # Log but don't fail the payment - accounting can be reconciled later
            logger.warning(f"Failed to create accounting entry for order {order.order_number}: {e.message}")
        except Exception as e:
            logger.warning(f"Unexpected error creating accounting entry for order {order.order_number}: {str(e)}")

        return payment

    async def generate_invoice(self, order_id: uuid.UUID) -> Invoice:
        """Generate invoice for an order."""
        order = await self.get_order_by_id(order_id, include_all=True)
        if not order:
            raise ValueError("Order not found")

        if order.invoice:
            return order.invoice

        invoice_number = await self.generate_invoice_number()

        # Calculate tax split (assuming same state = CGST+SGST, else IGST)
        cgst = order.tax_amount / 2
        sgst = order.tax_amount / 2
        igst = Decimal("0.00")

        invoice = Invoice(
            order_id=order.id,
            invoice_number=invoice_number,
            subtotal=order.subtotal,
            tax_amount=order.tax_amount,
            discount_amount=order.discount_amount,
            total_amount=order.total_amount,
            cgst_amount=cgst,
            sgst_amount=sgst,
            igst_amount=igst,
            invoice_date=datetime.now(timezone.utc),
        )
        self.db.add(invoice)
        await self.db.commit()
        await self.db.refresh(invoice)
        return invoice

    # ==================== HELPER METHODS ====================

    async def _process_address(self, address_input, customer: Customer) -> dict:
        """Process address input and return address dict."""
        if address_input.address_id:
            # Find existing address
            for addr in customer.addresses:
                if addr.id == address_input.address_id:
                    return {
                        "contact_name": addr.contact_name or customer.full_name,
                        "contact_phone": addr.contact_phone or customer.phone,
                        "address_line1": addr.address_line1,
                        "address_line2": addr.address_line2,
                        "landmark": addr.landmark,
                        "city": addr.city,
                        "state": addr.state,
                        "pincode": addr.pincode,
                        "country": addr.country,
                    }

        # Use provided address data
        return {
            "contact_name": address_input.contact_name or customer.full_name,
            "contact_phone": address_input.contact_phone or customer.phone,
            "address_line1": address_input.address_line1,
            "address_line2": address_input.address_line2,
            "landmark": address_input.landmark,
            "city": address_input.city,
            "state": address_input.state,
            "pincode": address_input.pincode,
            "country": "India",
        }

    async def _get_product(self, product_id: uuid.UUID) -> Optional[Product]:
        """Get product by ID."""
        stmt = select(Product).where(Product.id == product_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _get_variant(self, variant_id: uuid.UUID) -> Optional[ProductVariant]:
        """Get variant by ID."""
        stmt = select(ProductVariant).where(ProductVariant.id == variant_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    # ==================== STATISTICS ====================

    async def get_order_stats(
        self,
        region_id: Optional[uuid.UUID] = None
    ) -> dict:
        """Get order statistics."""
        from datetime import datetime, timezone, timedelta
        from sqlalchemy import or_

        base_filter = []
        if region_id:
            base_filter.append(Order.region_id == region_id)

        # Total orders
        total_stmt = select(func.count(Order.id))
        if base_filter:
            total_stmt = total_stmt.where(and_(*base_filter))
        total_orders = (await self.db.execute(total_stmt)).scalar() or 0

        # Unique customers
        customers_stmt = select(func.count(func.distinct(Order.customer_id)))
        if base_filter:
            customers_stmt = customers_stmt.where(and_(*base_filter))
        total_customers = (await self.db.execute(customers_stmt)).scalar() or 0

        # By status (check both enum values and string values)
        status_counts = {}
        for status in ["NEW", "CONFIRMED", "PROCESSING", "SHIPPED", "DELIVERED", "CANCELLED", "PENDING"]:
            stmt = select(func.count(Order.id)).where(
                or_(Order.status == status, Order.status == status.lower())
            )
            if base_filter:
                stmt = stmt.where(and_(*base_filter))
            status_counts[status] = (await self.db.execute(stmt)).scalar() or 0

        # Shipments in transit (SHIPPED status)
        shipments_in_transit = status_counts.get("SHIPPED", 0)

        # Revenue - include both 'PAID' and 'paid' (case variations)
        revenue_stmt = select(func.sum(Order.total_amount)).where(
            or_(
                Order.payment_status == "PAID",
                Order.payment_status == "paid",
                func.upper(Order.payment_status) == "PAID"
            )
        )
        if base_filter:
            revenue_stmt = revenue_stmt.where(and_(*base_filter))
        total_revenue = (await self.db.execute(revenue_stmt)).scalar() or Decimal("0.00")

        # Average order value
        avg_stmt = select(func.avg(Order.total_amount))
        if base_filter:
            avg_stmt = avg_stmt.where(and_(*base_filter))
        avg_order_value = (await self.db.execute(avg_stmt)).scalar() or Decimal("0.00")

        # Calculate month-over-month change
        now = datetime.now(timezone.utc)
        this_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        last_month_start = (this_month_start - timedelta(days=1)).replace(day=1)

        # This month orders
        this_month_stmt = select(func.count(Order.id)).where(Order.created_at >= this_month_start)
        if base_filter:
            this_month_stmt = this_month_stmt.where(and_(*base_filter))
        this_month_orders = (await self.db.execute(this_month_stmt)).scalar() or 0

        # Last month orders
        last_month_stmt = select(func.count(Order.id)).where(
            Order.created_at >= last_month_start,
            Order.created_at < this_month_start
        )
        if base_filter:
            last_month_stmt = last_month_stmt.where(and_(*base_filter))
        last_month_orders = (await self.db.execute(last_month_stmt)).scalar() or 0

        # Calculate change percentages
        orders_change = 0
        if last_month_orders > 0:
            orders_change = round(((this_month_orders - last_month_orders) / last_month_orders) * 100, 1)
        elif this_month_orders > 0:
            orders_change = 100

        return {
            "total_orders": total_orders,
            "total_customers": total_customers,
            "pending_orders": status_counts.get("PENDING", 0) + status_counts.get("NEW", 0),
            "processing_orders": status_counts.get("PROCESSING", 0) + status_counts.get("CONFIRMED", 0),
            "shipped_orders": status_counts.get("SHIPPED", 0),
            "delivered_orders": status_counts.get("DELIVERED", 0),
            "cancelled_orders": status_counts.get("CANCELLED", 0),
            "shipments_in_transit": shipments_in_transit,
            "total_revenue": float(total_revenue),
            "average_order_value": float(avg_order_value),
            "orders_change": orders_change,
            "revenue_change": 0,  # Would need last month revenue calculation
            "customers_change": 0,  # Would need last month customer calculation
        }

    async def get_recent_activity(self, limit: int = 10) -> List[dict]:
        """Get recent activity across orders, service requests, and POs."""
        activities = []

        # Recent orders
        orders_stmt = (
            select(Order)
            .options(selectinload(Order.customer))
            .order_by(Order.created_at.desc())
            .limit(limit)
        )
        orders_result = await self.db.execute(orders_stmt)
        orders = orders_result.scalars().all()

        for order in orders:
            activities.append({
                "type": "order",
                "color": "green",
                "title": f"New order {order.order_number}",
                "description": order.customer.first_name if order.customer else "Guest",
                "timestamp": order.created_at.isoformat(),
                "created_at": order.created_at,
            })

        # Sort by timestamp
        activities.sort(key=lambda x: x["created_at"], reverse=True)

        # Remove created_at from output (used only for sorting)
        for activity in activities:
            del activity["created_at"]

        return activities[:limit]

    # ==================== COMMUNITY PARTNER ATTRIBUTION ====================

    async def _attribute_order_to_partner(
        self,
        order: Order,
        partner_code: str,
        order_amount: Decimal,
        customer_id: uuid.UUID
    ) -> Optional[PartnerOrder]:
        """
        Attribute an order to a Community Partner.
        Creates PartnerOrder record for tracking.
        Commission is calculated when order is delivered.
        """
        # Look up partner by referral code or partner code
        partner_result = await self.db.execute(
            select(CommunityPartner).where(
                or_(
                    CommunityPartner.referral_code == partner_code,
                    CommunityPartner.partner_code == partner_code
                )
            )
        )
        partner = partner_result.scalar_one_or_none()

        if not partner:
            logger.warning(f"Partner not found for code: {partner_code}")
            return None

        if partner.status != "ACTIVE":
            logger.warning(f"Partner {partner_code} is not active (status: {partner.status})")
            return None

        # Create partner order attribution
        partner_order = PartnerOrder(
            id=uuid.uuid4(),
            partner_id=partner.id,
            order_id=order.id,
            customer_id=customer_id,
            order_amount=order_amount,
            attribution_source="REFERRAL_CODE",
        )
        self.db.add(partner_order)

        # Update partner order count (commission calculated on delivery)
        partner.total_orders = (partner.total_orders or 0) + 1
        partner.total_sales = (partner.total_sales or Decimal("0")) + order_amount
        partner.last_active_at = datetime.now(timezone.utc)

        logger.info(f"Order {order.order_number} attributed to partner {partner.partner_code}")

        return partner_order

    async def calculate_partner_commission(
        self,
        order_id: uuid.UUID
    ) -> Optional[PartnerCommission]:
        """
        Calculate and record commission for a partner's order.
        Called when order status changes to DELIVERED.
        """
        from app.models.community_partner import PartnerTier

        # Get partner order
        po_result = await self.db.execute(
            select(PartnerOrder).where(PartnerOrder.order_id == order_id)
        )
        partner_order = po_result.scalar_one_or_none()

        if not partner_order:
            return None  # Order not attributed to any partner

        if partner_order.commission_id:
            logger.info(f"Commission already calculated for order {order_id}")
            return None

        # Get partner with tier
        partner_result = await self.db.execute(
            select(CommunityPartner)
            .options(selectinload(CommunityPartner.tier))
            .where(CommunityPartner.id == partner_order.partner_id)
        )
        partner = partner_result.scalar_one_or_none()

        if not partner:
            return None

        # Get commission rate from tier
        commission_rate = Decimal("10.00")  # Default Bronze rate
        bonus_rate = Decimal("0")
        if partner.tier:
            commission_rate = partner.tier.commission_rate
            bonus_rate = partner.tier.bonus_rate

        order_amount = partner_order.order_amount
        commission_amount = (order_amount * commission_rate / Decimal("100")).quantize(Decimal("0.01"))
        bonus_amount = (order_amount * bonus_rate / Decimal("100")).quantize(Decimal("0.01"))

        # TDS calculation (5% if total commission > 15000 in FY)
        tds_rate = Decimal("0")
        tds_amount = Decimal("0")

        # Check total commission this FY
        fy_start = datetime(
            datetime.now(timezone.utc).year if datetime.now(timezone.utc).month >= 4 else datetime.now(timezone.utc).year - 1,
            4, 1
        )
        fy_total_result = await self.db.execute(
            select(func.coalesce(func.sum(PartnerCommission.commission_amount), 0))
            .where(
                PartnerCommission.partner_id == partner.id,
                PartnerCommission.created_at >= fy_start
            )
        )
        fy_total = fy_total_result.scalar() or Decimal("0")

        if fy_total + commission_amount > Decimal("15000"):
            tds_rate = Decimal("5.00")
            tds_amount = (commission_amount * tds_rate / Decimal("100")).quantize(Decimal("0.01"))

        net_amount = commission_amount + bonus_amount - tds_amount

        # Create commission record
        commission = PartnerCommission(
            id=uuid.uuid4(),
            partner_id=partner.id,
            order_id=order_id,
            order_amount=order_amount,
            commission_rate=commission_rate,
            commission_amount=commission_amount,
            bonus_amount=bonus_amount,
            tds_rate=tds_rate,
            tds_amount=tds_amount,
            net_amount=net_amount,
            status="PENDING",
        )
        self.db.add(commission)
        await self.db.flush()

        # Link commission to partner order
        partner_order.commission_id = commission.id

        # Update partner totals
        partner.total_commission_earned = (partner.total_commission_earned or Decimal("0")) + net_amount
        partner.pending_commission = (partner.pending_commission or Decimal("0")) + net_amount

        logger.info(
            f"Commission created for partner {partner.partner_code}: "
            f"Order {order_id}, Amount: {net_amount} (Rate: {commission_rate}%)"
        )

        # Check for tier upgrade
        await self._check_partner_tier_upgrade(partner)

        return commission

    async def _check_partner_tier_upgrade(self, partner: CommunityPartner) -> None:
        """Check if partner qualifies for tier upgrade."""
        from app.models.community_partner import PartnerTier

        # Get all tiers ordered by commission rate (descending)
        tiers_result = await self.db.execute(
            select(PartnerTier)
            .where(PartnerTier.is_active == True)
            .order_by(PartnerTier.commission_rate.desc())
        )
        tiers = tiers_result.scalars().all()

        for tier in tiers:
            if (partner.total_orders >= tier.min_orders and
                (partner.total_sales or Decimal("0")) >= tier.min_revenue):
                if partner.tier_id != tier.id:
                    old_tier = partner.tier.name if partner.tier else "None"
                    partner.tier_id = tier.id
                    logger.info(f"Partner {partner.partner_code} upgraded from {old_tier} to {tier.name}")
                break
