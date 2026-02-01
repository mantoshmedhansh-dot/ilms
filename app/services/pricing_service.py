"""Pricing Service for Channel-Specific Pricing and Pricing Rules Engine.

Implements omnichannel pricing strategy:
- Channel-specific product pricing (ChannelPricing)
- Pricing rules engine (volume discounts, customer segments, promotions)
- Price validation against max discount thresholds
- Fallback to product master pricing if no channel pricing exists

Source of Truth:
- Product Master: Base MRP, HSN, GST Rate
- ChannelPricing: Channel-specific selling prices
- PricingRules: Dynamic pricing rules (volume, segment, promo)
"""
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
import uuid
import logging

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.channel import (
    SalesChannel, ChannelPricing, ChannelStatus, PricingRule
)
from app.models.product import Product, ProductVariant

logger = logging.getLogger(__name__)


class PricingService:
    """
    Service for calculating product prices across channels.

    Pricing Flow:
    1. Get ChannelPricing for product (if exists)
    2. Apply pricing rules (volume, segment, promo)
    3. Validate against max discount threshold
    4. Return final calculated price

    Example:
    - Product MRP: ₹25,999
    - Channel Selling Price: ₹21,999
    - Volume Discount (qty 5+): 5% → ₹20,899
    - Max Discount: 20% of MRP → min ₹20,799
    - Final Price: ₹20,899 (within threshold)
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    # ==================== CHANNEL PRICING METHODS ====================

    async def get_channel_pricing(
        self,
        product_id: uuid.UUID,
        channel_id: uuid.UUID,
        variant_id: Optional[uuid.UUID] = None,
    ) -> Optional[ChannelPricing]:
        """
        Get active channel pricing for a product.

        Checks:
        - Matching channel_id and product_id
        - is_active = True
        - Within effective_from/effective_to date range (if set)
        """
        now = datetime.now(timezone.utc)

        stmt = select(ChannelPricing).where(
            and_(
                ChannelPricing.channel_id == channel_id,
                ChannelPricing.product_id == product_id,
                ChannelPricing.is_active == True,
                or_(
                    ChannelPricing.effective_from.is_(None),
                    ChannelPricing.effective_from <= now
                ),
                or_(
                    ChannelPricing.effective_to.is_(None),
                    ChannelPricing.effective_to >= now
                ),
            )
        )

        if variant_id:
            stmt = stmt.where(ChannelPricing.variant_id == variant_id)
        else:
            stmt = stmt.where(ChannelPricing.variant_id.is_(None))

        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_product_base_price(
        self,
        product_id: uuid.UUID,
    ) -> Dict[str, Decimal]:
        """
        Get product's base pricing from Product Master.

        Returns:
        - mrp: Maximum Retail Price
        - selling_price: Default selling price
        - cost_price: Cost for margin calculation (if available)
        """
        stmt = select(Product).where(Product.id == product_id)
        result = await self.db.execute(stmt)
        product = result.scalar_one_or_none()

        if not product:
            raise ValueError(f"Product not found: {product_id}")

        return {
            "mrp": product.mrp or Decimal("0"),
            "selling_price": product.selling_price or product.mrp or Decimal("0"),
            "dealer_price": product.dealer_price or Decimal("0"),
            "gst_rate": product.gst_rate or Decimal("18"),
            "hsn_code": product.hsn_code,
        }

    async def calculate_price(
        self,
        product_id: uuid.UUID,
        channel_id: uuid.UUID,
        quantity: int = 1,
        variant_id: Optional[uuid.UUID] = None,
        customer_segment: str = "STANDARD",
        promo_code: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Calculate final price for a product on a channel.

        This is the main pricing calculation method used by order creation.

        Args:
            product_id: Product UUID
            channel_id: Sales Channel UUID
            quantity: Order quantity (for volume discounts)
            variant_id: Product variant (optional)
            customer_segment: Customer type (STANDARD, VIP, DEALER, etc.)
            promo_code: Promotional code (optional)

        Returns:
            Dictionary with:
            - base_price: Starting price (from ChannelPricing or Product)
            - final_price: After all rules applied
            - discount_amount: Total discount
            - discount_percentage: Discount as percentage
            - rules_applied: List of rules that were applied
            - price_source: 'CHANNEL_PRICING' or 'PRODUCT_MASTER'
        """
        # Step 1: Get channel pricing (or fallback to product)
        channel_pricing = await self.get_channel_pricing(
            product_id, channel_id, variant_id
        )

        if channel_pricing and channel_pricing.selling_price:
            base_price = channel_pricing.selling_price
            mrp = channel_pricing.mrp
            max_discount_pct = channel_pricing.max_discount_percentage
            price_source = "CHANNEL_PRICING"
            transfer_price = channel_pricing.transfer_price
        else:
            # Fallback to product master pricing
            product_pricing = await self.get_product_base_price(product_id)
            base_price = product_pricing["selling_price"]
            mrp = product_pricing["mrp"]
            max_discount_pct = Decimal("25")  # Default max discount
            price_source = "PRODUCT_MASTER"
            transfer_price = product_pricing["dealer_price"]

        # For dealer/B2B channels, use transfer price if available
        channel = await self._get_channel(channel_id)
        if channel and channel.channel_type in ["B2B", "DEALER", "DEALER_PORTAL", "DISTRIBUTOR"]:
            if transfer_price and transfer_price > 0:
                base_price = transfer_price

        # Step 2: Apply pricing rules
        rules_result = await self._apply_pricing_rules(
            base_price=base_price,
            product_id=product_id,
            channel_id=channel_id,
            quantity=quantity,
            customer_segment=customer_segment,
            promo_code=promo_code,
        )

        final_price = rules_result["final_price"]
        rules_applied = rules_result["rules_applied"]

        # Step 3: Validate against max discount threshold
        if max_discount_pct and mrp and mrp > 0:
            min_allowed_price = mrp * (1 - max_discount_pct / 100)
            if final_price < min_allowed_price:
                logger.warning(
                    f"Price {final_price} below min threshold {min_allowed_price} "
                    f"for product {product_id}, channel {channel_id}. "
                    f"Adjusting to minimum."
                )
                final_price = min_allowed_price.quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
                rules_applied.append({
                    "rule_type": "MAX_DISCOUNT_THRESHOLD",
                    "adjustment": "PRICE_RAISED_TO_MIN",
                    "min_price": float(min_allowed_price),
                })

        # Calculate discount
        discount_amount = base_price - final_price
        discount_percentage = (
            (discount_amount / base_price * 100).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            if base_price > 0 else Decimal("0")
        )

        return {
            "product_id": str(product_id),
            "channel_id": str(channel_id),
            "variant_id": str(variant_id) if variant_id else None,
            "quantity": quantity,
            "mrp": float(mrp) if mrp else None,
            "base_price": float(base_price),
            "final_price": float(final_price),
            "unit_price": float(final_price),  # Alias for order item
            "discount_amount": float(discount_amount),
            "discount_percentage": float(discount_percentage),
            "price_source": price_source,
            "rules_applied": rules_applied,
            "customer_segment": customer_segment,
        }

    async def _get_channel(self, channel_id: uuid.UUID) -> Optional[SalesChannel]:
        """Get channel by ID."""
        stmt = select(SalesChannel).where(SalesChannel.id == channel_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _apply_pricing_rules(
        self,
        base_price: Decimal,
        product_id: uuid.UUID,
        channel_id: uuid.UUID,
        quantity: int,
        customer_segment: str,
        promo_code: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Apply pricing rules to base price.

        Rule types (applied in order):
        1. Volume discounts (quantity-based)
        2. Customer segment discounts
        3. Promotional discounts (promo codes)
        4. Time-based discounts (weekend, festivals)

        Rules are combinable if is_combinable=True, otherwise
        only the highest priority rule is applied.
        """
        rules_applied = []
        final_price = base_price
        now = datetime.now(timezone.utc)

        # Query active pricing rules from database
        query = select(PricingRule).where(
            and_(
                PricingRule.is_active == True,
                or_(
                    PricingRule.channel_id == channel_id,
                    PricingRule.channel_id.is_(None)  # Global rules
                ),
                or_(
                    PricingRule.product_id == product_id,
                    PricingRule.product_id.is_(None)  # Category/all products
                ),
                or_(
                    PricingRule.effective_from.is_(None),
                    PricingRule.effective_from <= now
                ),
                or_(
                    PricingRule.effective_to.is_(None),
                    PricingRule.effective_to >= now
                ),
            )
        ).order_by(PricingRule.priority)

        result = await self.db.execute(query)
        db_rules = result.scalars().all()

        # Track which rule types have been applied (for non-combinable rules)
        applied_rule_types = set()

        for rule in db_rules:
            # Skip if this rule type already applied and rule is not combinable
            if rule.rule_type in applied_rule_types and not rule.is_combinable:
                continue

            discount_to_apply = Decimal("0")

            # Check rule conditions based on rule_type
            if rule.rule_type == "VOLUME_DISCOUNT":
                conditions = rule.conditions or {}
                min_qty = conditions.get("min_quantity", 0)
                if quantity >= min_qty:
                    if rule.discount_type == "PERCENTAGE":
                        discount_to_apply = rule.discount_value
                    else:  # FIXED_AMOUNT
                        discount_to_apply = (rule.discount_value / final_price) * 100 if final_price > 0 else Decimal("0")

            elif rule.rule_type == "CUSTOMER_SEGMENT":
                conditions = rule.conditions or {}
                applicable_segments = conditions.get("segments", [])
                if not applicable_segments or customer_segment.upper() in [s.upper() for s in applicable_segments]:
                    if rule.discount_type == "PERCENTAGE":
                        discount_to_apply = rule.discount_value
                    else:
                        discount_to_apply = (rule.discount_value / final_price) * 100 if final_price > 0 else Decimal("0")

            elif rule.rule_type == "PROMOTIONAL":
                conditions = rule.conditions or {}
                rule_promo_code = conditions.get("promo_code", "")
                if promo_code and promo_code.upper() == rule_promo_code.upper():
                    # Check max uses
                    if rule.max_uses and rule.current_uses >= rule.max_uses:
                        continue
                    if rule.discount_type == "PERCENTAGE":
                        discount_to_apply = rule.discount_value
                    else:
                        discount_to_apply = (rule.discount_value / final_price) * 100 if final_price > 0 else Decimal("0")

            # Apply discount if any
            if discount_to_apply > 0:
                discount_amount = final_price * (discount_to_apply / 100)
                final_price = final_price - discount_amount
                rules_applied.append({
                    "rule_id": str(rule.id),
                    "rule_code": rule.code,
                    "rule_type": rule.rule_type,
                    "discount_percentage": float(discount_to_apply),
                    "discount_amount": float(discount_amount),
                })
                applied_rule_types.add(rule.rule_type)

        # If no database rules found, fall back to built-in logic
        if not db_rules:
            # Volume Discount (built-in logic)
            volume_discount = self._calculate_volume_discount(quantity)
            if volume_discount > 0:
                discount_amount = final_price * (volume_discount / 100)
                final_price = final_price - discount_amount
                rules_applied.append({
                    "rule_type": "VOLUME_DISCOUNT",
                    "quantity": quantity,
                    "discount_percentage": float(volume_discount),
                    "discount_amount": float(discount_amount),
                })

            # Customer Segment Discount
            segment_discount = self._get_segment_discount(customer_segment)
            if segment_discount > 0:
                discount_amount = final_price * (segment_discount / 100)
                final_price = final_price - discount_amount
                rules_applied.append({
                    "rule_type": "CUSTOMER_SEGMENT",
                    "segment": customer_segment,
                    "discount_percentage": float(segment_discount),
                    "discount_amount": float(discount_amount),
                })

        # Round final price
        final_price = final_price.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        return {
            "final_price": final_price,
            "rules_applied": rules_applied,
        }

    def _calculate_volume_discount(self, quantity: int) -> Decimal:
        """
        Calculate volume-based discount.

        Default tiers (can be configured via pricing_rules table later):
        - 1-9 units: 0%
        - 10-24 units: 3%
        - 25-49 units: 5%
        - 50-99 units: 7%
        - 100+ units: 10%
        """
        if quantity >= 100:
            return Decimal("10")
        elif quantity >= 50:
            return Decimal("7")
        elif quantity >= 25:
            return Decimal("5")
        elif quantity >= 10:
            return Decimal("3")
        return Decimal("0")

    def _get_segment_discount(self, segment: str) -> Decimal:
        """
        Get discount based on customer segment.

        Default segments (can be configured via pricing_rules table later):
        - STANDARD: 0%
        - VIP: 5%
        - DEALER: 15%
        - DISTRIBUTOR: 20%
        - CORPORATE: 10%
        """
        segment_discounts = {
            "STANDARD": Decimal("0"),
            "RETAIL": Decimal("0"),
            "VIP": Decimal("5"),
            "DEALER": Decimal("15"),
            "DISTRIBUTOR": Decimal("20"),
            "CORPORATE": Decimal("10"),
            "GOVERNMENT": Decimal("8"),
        }
        return segment_discounts.get(segment.upper(), Decimal("0"))

    # ==================== BULK PRICING OPERATIONS ====================

    async def get_channel_pricing_list(
        self,
        channel_id: uuid.UUID,
        category_id: Optional[uuid.UUID] = None,
        brand_id: Optional[uuid.UUID] = None,
        is_active: bool = True,
        skip: int = 0,
        limit: int = 50,
    ) -> Dict[str, Any]:
        """
        Get list of channel pricing with filters.

        Used by the Channel Pricing management UI.
        """
        stmt = (
            select(ChannelPricing)
            .options(selectinload(ChannelPricing.product))
            .where(ChannelPricing.channel_id == channel_id)
        )

        if is_active:
            stmt = stmt.where(ChannelPricing.is_active == True)

        # Apply category/brand filters via product relationship
        # TODO: Add joins for category and brand filtering

        # Count total
        count_stmt = select(func.count(ChannelPricing.id)).where(
            ChannelPricing.channel_id == channel_id
        )
        if is_active:
            count_stmt = count_stmt.where(ChannelPricing.is_active == True)
        total_result = await self.db.execute(count_stmt)
        total = total_result.scalar() or 0

        # Paginate
        stmt = stmt.order_by(ChannelPricing.created_at.desc())
        stmt = stmt.offset(skip).limit(limit)

        result = await self.db.execute(stmt)
        items = result.scalars().all()

        return {
            "items": items,
            "total": total,
            "skip": skip,
            "limit": limit,
        }

    async def create_channel_pricing(
        self,
        channel_id: uuid.UUID,
        product_id: uuid.UUID,
        mrp: Decimal,
        selling_price: Decimal,
        variant_id: Optional[uuid.UUID] = None,
        transfer_price: Optional[Decimal] = None,
        discount_percentage: Optional[Decimal] = None,
        max_discount_percentage: Optional[Decimal] = None,
        effective_from: Optional[datetime] = None,
        effective_to: Optional[datetime] = None,
        is_active: bool = True,
        is_listed: bool = True,
    ) -> ChannelPricing:
        """
        Create or update channel pricing for a product.

        Uses upsert logic - if pricing exists for channel+product+variant,
        updates it; otherwise creates new.
        """
        # Check if exists
        existing = await self.get_channel_pricing(product_id, channel_id, variant_id)

        if existing:
            # Update existing
            existing.mrp = mrp
            existing.selling_price = selling_price
            existing.transfer_price = transfer_price
            existing.discount_percentage = discount_percentage
            existing.max_discount_percentage = max_discount_percentage
            existing.effective_from = effective_from
            existing.effective_to = effective_to
            existing.is_active = is_active
            existing.is_listed = is_listed
            existing.updated_at = datetime.now(timezone.utc)

            await self.db.commit()
            await self.db.refresh(existing)
            return existing

        # Create new
        pricing = ChannelPricing(
            channel_id=channel_id,
            product_id=product_id,
            variant_id=variant_id,
            mrp=mrp,
            selling_price=selling_price,
            transfer_price=transfer_price,
            discount_percentage=discount_percentage,
            max_discount_percentage=max_discount_percentage,
            effective_from=effective_from,
            effective_to=effective_to,
            is_active=is_active,
            is_listed=is_listed,
        )

        self.db.add(pricing)
        await self.db.commit()
        await self.db.refresh(pricing)

        return pricing

    async def bulk_create_channel_pricing(
        self,
        channel_id: uuid.UUID,
        pricing_data: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Bulk create/update channel pricing.

        pricing_data: List of dicts with keys:
        - product_id (required)
        - mrp (required)
        - selling_price (required)
        - variant_id, transfer_price, discount_percentage, etc. (optional)

        Returns:
        - created: count of new records
        - updated: count of updated records
        - errors: list of errors
        """
        created = 0
        updated = 0
        errors = []

        for idx, item in enumerate(pricing_data):
            try:
                product_id = uuid.UUID(str(item["product_id"]))
                mrp = Decimal(str(item["mrp"]))
                selling_price = Decimal(str(item["selling_price"]))

                existing = await self.get_channel_pricing(
                    product_id, channel_id,
                    uuid.UUID(str(item["variant_id"])) if item.get("variant_id") else None
                )

                if existing:
                    # Update
                    existing.mrp = mrp
                    existing.selling_price = selling_price
                    if item.get("transfer_price"):
                        existing.transfer_price = Decimal(str(item["transfer_price"]))
                    if item.get("max_discount_percentage"):
                        existing.max_discount_percentage = Decimal(str(item["max_discount_percentage"]))
                    existing.updated_at = datetime.now(timezone.utc)
                    updated += 1
                else:
                    # Create
                    pricing = ChannelPricing(
                        channel_id=channel_id,
                        product_id=product_id,
                        variant_id=uuid.UUID(str(item["variant_id"])) if item.get("variant_id") else None,
                        mrp=mrp,
                        selling_price=selling_price,
                        transfer_price=Decimal(str(item["transfer_price"])) if item.get("transfer_price") else None,
                        max_discount_percentage=Decimal(str(item["max_discount_percentage"])) if item.get("max_discount_percentage") else None,
                        is_active=item.get("is_active", True),
                        is_listed=item.get("is_listed", True),
                    )
                    self.db.add(pricing)
                    created += 1

            except Exception as e:
                errors.append({
                    "row": idx,
                    "product_id": item.get("product_id"),
                    "error": str(e),
                })

        await self.db.commit()

        return {
            "created": created,
            "updated": updated,
            "errors": errors,
            "total_processed": created + updated,
        }

    async def copy_pricing_between_channels(
        self,
        source_channel_id: uuid.UUID,
        destination_channel_id: uuid.UUID,
        overwrite: bool = False,
    ) -> Dict[str, Any]:
        """
        Copy all pricing from source channel to destination channel.

        Args:
            source_channel_id: Channel to copy FROM
            destination_channel_id: Channel to copy TO
            overwrite: If True, update existing pricing; if False, skip existing

        Returns:
            - copied: count of new records created
            - updated: count of existing records updated (if overwrite=True)
            - skipped: count of records skipped (if overwrite=False and pricing exists)
            - total_source: total pricing records in source channel
        """
        # Get all pricing from source channel
        stmt = select(ChannelPricing).where(
            and_(
                ChannelPricing.channel_id == source_channel_id,
                ChannelPricing.is_active == True,
            )
        )
        result = await self.db.execute(stmt)
        source_pricing = result.scalars().all()

        copied = 0
        updated = 0
        skipped = 0
        errors = []

        for source in source_pricing:
            try:
                # Check if destination already has pricing for this product
                existing = await self.get_channel_pricing(
                    source.product_id,
                    destination_channel_id,
                    source.variant_id,
                )

                if existing:
                    if overwrite:
                        # Update existing pricing
                        existing.mrp = source.mrp
                        existing.selling_price = source.selling_price
                        existing.transfer_price = source.transfer_price
                        existing.discount_percentage = source.discount_percentage
                        existing.max_discount_percentage = source.max_discount_percentage
                        existing.is_listed = source.is_listed
                        existing.updated_at = datetime.now(timezone.utc)
                        updated += 1
                    else:
                        skipped += 1
                else:
                    # Create new pricing for destination channel
                    new_pricing = ChannelPricing(
                        channel_id=destination_channel_id,
                        product_id=source.product_id,
                        variant_id=source.variant_id,
                        mrp=source.mrp,
                        selling_price=source.selling_price,
                        transfer_price=source.transfer_price,
                        discount_percentage=source.discount_percentage,
                        max_discount_percentage=source.max_discount_percentage,
                        is_active=True,
                        is_listed=source.is_listed,
                    )
                    self.db.add(new_pricing)
                    copied += 1

            except Exception as e:
                errors.append({
                    "product_id": str(source.product_id),
                    "error": str(e),
                })

        await self.db.commit()

        return {
            "copied": copied,
            "updated": updated,
            "skipped": skipped,
            "total_source": len(source_pricing),
            "errors": errors,
        }

    # ==================== PRICE COMPARISON ====================

    async def compare_prices_across_channels(
        self,
        product_id: uuid.UUID,
    ) -> List[Dict[str, Any]]:
        """
        Compare product pricing across all channels.

        Returns list of channel pricing with margin calculations.
        """
        # Get product base info
        product_pricing = await self.get_product_base_price(product_id)
        mrp = product_pricing["mrp"]

        # Get all channel pricing for this product
        stmt = (
            select(ChannelPricing)
            .options(selectinload(ChannelPricing.channel))
            .where(
                and_(
                    ChannelPricing.product_id == product_id,
                    ChannelPricing.is_active == True,
                )
            )
        )
        result = await self.db.execute(stmt)
        channel_pricings = result.scalars().all()

        comparisons = []
        for cp in channel_pricings:
            margin = (
                ((mrp - cp.selling_price) / mrp * 100).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
                if mrp and mrp > 0 else Decimal("0")
            )

            comparisons.append({
                "channel_id": str(cp.channel_id),
                "channel_name": cp.channel.name if cp.channel else "Unknown",
                "channel_type": cp.channel.channel_type if cp.channel else None,
                "mrp": float(mrp),
                "selling_price": float(cp.selling_price),
                "transfer_price": float(cp.transfer_price) if cp.transfer_price else None,
                "margin_percentage": float(margin),
                "max_discount_percentage": float(cp.max_discount_percentage) if cp.max_discount_percentage else None,
                "is_listed": cp.is_listed,
            })

        return comparisons

    # ==================== VALIDATION ====================

    async def validate_pricing(
        self,
        product_id: uuid.UUID,
        selling_price: Decimal,
        mrp: Optional[Decimal] = None,
        min_margin_percentage: Decimal = Decimal("10"),
    ) -> Dict[str, Any]:
        """
        Validate pricing against business rules.

        Checks:
        - Selling price <= MRP
        - Margin >= minimum threshold
        - Price > 0

        Returns:
        - is_valid: bool
        - errors: list of validation errors
        - warnings: list of warnings
        """
        errors = []
        warnings = []

        # Get product info if MRP not provided
        if not mrp:
            product_pricing = await self.get_product_base_price(product_id)
            mrp = product_pricing["mrp"]

        # Validate: Price > 0
        if selling_price <= 0:
            errors.append("Selling price must be greater than 0")

        # Validate: Selling price <= MRP
        if mrp and selling_price > mrp:
            errors.append(f"Selling price ({selling_price}) cannot be greater than MRP ({mrp})")

        # Calculate margin
        if mrp and mrp > 0:
            margin = ((mrp - selling_price) / mrp * 100).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )

            # Warning: Below minimum margin
            if margin < min_margin_percentage:
                warnings.append(
                    f"Margin ({margin}%) is below minimum threshold ({min_margin_percentage}%)"
                )

            # Warning: Very high margin (potential pricing error)
            if margin > 50:
                warnings.append(
                    f"Margin ({margin}%) is unusually high. Please verify pricing."
                )

        return {
            "is_valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "mrp": float(mrp) if mrp else None,
            "selling_price": float(selling_price),
            "margin_percentage": float(margin) if mrp and mrp > 0 else None,
        }

    async def get_pricing_alerts(
        self,
        channel_id: Optional[uuid.UUID] = None,
        min_margin_threshold: Decimal = Decimal("10"),
    ) -> List[Dict[str, Any]]:
        """
        Get products with pricing alerts (below margin threshold).

        Used for pricing dashboard alerts.
        """
        # Build query for channel pricing with product info
        stmt = (
            select(ChannelPricing)
            .options(selectinload(ChannelPricing.product))
            .options(selectinload(ChannelPricing.channel))
            .where(ChannelPricing.is_active == True)
        )

        if channel_id:
            stmt = stmt.where(ChannelPricing.channel_id == channel_id)

        result = await self.db.execute(stmt)
        channel_pricings = result.scalars().all()

        alerts = []
        for cp in channel_pricings:
            if cp.mrp and cp.mrp > 0:
                margin = ((cp.mrp - cp.selling_price) / cp.mrp * 100)

                if margin < min_margin_threshold:
                    alerts.append({
                        "product_id": str(cp.product_id),
                        "product_name": cp.product.name if cp.product else "Unknown",
                        "product_sku": cp.product.sku if cp.product else None,
                        "channel_id": str(cp.channel_id),
                        "channel_name": cp.channel.name if cp.channel else "Unknown",
                        "mrp": float(cp.mrp),
                        "selling_price": float(cp.selling_price),
                        "margin_percentage": float(margin.quantize(Decimal("0.01"))),
                        "threshold": float(min_margin_threshold),
                        "alert_type": "BELOW_MARGIN_THRESHOLD",
                    })

        # Sort by margin (lowest first)
        alerts.sort(key=lambda x: x["margin_percentage"])

        return alerts
