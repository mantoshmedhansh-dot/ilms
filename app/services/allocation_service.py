"""
Allocation Service.

Order Allocation Engine that handles:
1. Channel-specific routing (Amazon → Amazon FBA warehouse)
2. Proximity-based allocation (nearest warehouse)
3. Inventory-based allocation (warehouse with stock)
4. Cost-optimized allocation (lowest shipping cost)
5. SLA-based allocation (fastest delivery)
6. Rate card-based carrier selection with pricing engine

Priority-Based Flow:
1. Get applicable allocation rules for the channel
2. For each rule (by priority), find matching warehouse
3. Check inventory availability
4. Select best transporter using pricing engine
5. Log allocation decision with cost breakdown
"""
import uuid
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timezone
from decimal import Decimal
import json

from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.serviceability import (
    WarehouseServiceability,
    AllocationRule,
    AllocationLog,
    AllocationType,
    ChannelCode,
    AllocationPriority,
)
from app.models.transporter import Transporter, TransporterServiceability
from app.models.warehouse import Warehouse
from app.models.inventory import InventorySummary, StockItem, StockItemStatus
from app.models.order import Order, OrderItem, OrderStatus
from app.models.channel import ChannelInventory, SalesChannel
from app.services.cache_service import get_cache
from app.services.channel_inventory_service import ChannelInventoryService
from app.config import settings
from app.schemas.serviceability import (
    OrderAllocationRequest,
    AllocationDecision,
    WarehouseCandidate,
    AllocationRuleCreate,
    AllocationRuleUpdate,
    AllocationRuleResponse,
)

# Import pricing engine for rate card-based allocation
try:
    from app.services.pricing_engine import (
        PricingEngine,
        RateCalculationRequest,
        AllocationStrategy,
        CarrierQuote,
    )
    PRICING_ENGINE_AVAILABLE = True
except ImportError:
    PRICING_ENGINE_AVAILABLE = False


class AllocationService:
    """Service for allocating orders to warehouses."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def allocate_order(
        self,
        request: OrderAllocationRequest
    ) -> AllocationDecision:
        """
        Main allocation engine.

        Flow:
        1. Get order details
        2. Check pincode serviceability
        3. Get applicable allocation rules
        4. For each rule, find matching warehouse
        5. Check stock availability
        6. Select transporter
        7. Log and return decision
        """
        order_id = request.order_id
        pincode = request.customer_pincode
        channel_code = request.channel_code or "D2C"

        try:
            # 1. Get order if exists
            order = await self._get_order(order_id)
            order_items = request.items or []
            product_ids = [item.get("product_id") for item in order_items if item.get("product_id")]

            # Build quantities dict: {product_id: quantity}
            quantities: Dict[str, int] = {}
            for item in order_items:
                pid = item.get("product_id")
                qty = item.get("quantity", 1)
                if pid:
                    quantities[pid] = quantities.get(pid, 0) + qty

            if order:
                # Get product IDs and quantities from order items
                order_items_query = select(OrderItem).where(OrderItem.order_id == order_id)
                items_result = await self.db.execute(order_items_query)
                order_items_db = items_result.scalars().all()
                product_ids = [str(item.product_id) for item in order_items_db]
                # Update quantities from database
                quantities = {}
                for item in order_items_db:
                    pid = str(item.product_id)
                    quantities[pid] = quantities.get(pid, 0) + item.quantity

            # 2. Get applicable allocation rules
            rules = await self._get_allocation_rules(channel_code, request.payment_mode, request.order_value)

            if not rules:
                # Use default rule (NEAREST) - use string values for VARCHAR columns
                rules = [AllocationRule(
                    name="Default",
                    channel_code=ChannelCode.ALL.value if hasattr(ChannelCode.ALL, 'value') else "ALL",
                    allocation_type=AllocationType.NEAREST.value if hasattr(AllocationType.NEAREST, 'value') else "NEAREST",
                    priority=999
                )]

            # 3. Find serviceable warehouses
            serviceable_warehouses = await self._get_serviceable_warehouses(pincode)

            if not serviceable_warehouses:
                return await self._create_failed_allocation(
                    order_id,
                    pincode,
                    None,
                    "Location not serviceable - no warehouse covers this pincode"
                )

            # 4. Apply allocation rules
            selected_warehouse = None
            applied_rule = None
            decision_factors = {}

            for rule in rules:
                selected_warehouse, decision_factors = await self._apply_rule(
                    rule,
                    serviceable_warehouses,
                    product_ids,
                    pincode,
                    request.payment_mode,
                    quantities,
                    channel_code=channel_code  # Pass channel for channel-specific inventory check
                )

                if selected_warehouse:
                    applied_rule = rule
                    break

            if not selected_warehouse:
                # No warehouse found with available stock
                # Build candidates list before any potential commits
                candidates_list = [self._ws_to_candidate(ws) for ws in serviceable_warehouses[:5]]
                return await self._create_failed_allocation(
                    order_id,
                    pincode,
                    rules[0].id if rules else None,
                    "No warehouse has sufficient inventory",
                    candidates_list
                )

            # Extract ALL warehouse info NOW, before any operations that might commit
            # This prevents lazy loading issues after commits expire the objects
            warehouse_id = selected_warehouse.warehouse_id
            warehouse_code = selected_warehouse.warehouse.code
            warehouse_name = selected_warehouse.warehouse.name
            ws_estimated_days = selected_warehouse.estimated_days
            ws_shipping_cost = selected_warehouse.shipping_cost
            origin_pincode = selected_warehouse.warehouse.pincode

            # Build candidates list before any commits
            candidates_list = [self._ws_to_candidate(ws) for ws in serviceable_warehouses[:5]]

            # 5. Find best transporter using pricing engine
            transporter, shipping_info = await self._select_transporter(
                selected_warehouse,
                pincode,
                payment_mode=request.payment_mode,
                weight_kg=request.weight_kg if hasattr(request, 'weight_kg') and request.weight_kg else 1.0,
                order_value=float(request.order_value) if request.order_value else 0,
                dimensions=request.dimensions if hasattr(request, 'dimensions') else None,
                allocation_strategy=request.allocation_strategy if hasattr(request, 'allocation_strategy') else "BALANCED"
            )

            # Extract transporter info BEFORE any commits to avoid lazy loading
            transporter_id = transporter.id if transporter else None
            transporter_code = transporter.code if transporter else (shipping_info.get("carrier_code") if shipping_info else None)
            transporter_name = transporter.name if transporter else (shipping_info.get("carrier_name") if shipping_info else None)

            # Extract rule info BEFORE any commits to avoid lazy loading
            rule_id = applied_rule.id if applied_rule and hasattr(applied_rule, 'id') else None
            rule_name = applied_rule.name if applied_rule else "Default"
            rule_allocation_type = applied_rule.allocation_type if applied_rule and hasattr(applied_rule.allocation_type, 'value') else "NEAREST"

            # 6. Log allocation
            await self._log_allocation(
                order_id=order_id,
                rule_id=rule_id,
                warehouse_id=warehouse_id,
                customer_pincode=pincode,
                is_successful=True,
                decision_factors=decision_factors,
                candidates=candidates_list
            )

            # 7. Update order if exists and consume channel inventory
            if order:
                await self._update_order_warehouse(order, warehouse_id, channel_code)

            return AllocationDecision(
                order_id=order_id,
                is_allocated=True,
                warehouse_id=warehouse_id,
                warehouse_code=warehouse_code,
                warehouse_name=warehouse_name,
                is_split=False,
                rule_applied=rule_name,
                allocation_type=rule_allocation_type,
                decision_factors=decision_factors,
                recommended_transporter_id=transporter_id,
                recommended_transporter_code=transporter_code,
                recommended_transporter_name=transporter_name,
                estimated_delivery_days=shipping_info.get("estimated_days") if shipping_info else ws_estimated_days,
                estimated_delivery_days_min=shipping_info.get("estimated_days_min") if shipping_info else None,
                estimated_shipping_cost=shipping_info.get("rate") if shipping_info else ws_shipping_cost,
                # Pricing engine details
                cost_breakdown=shipping_info.get("cost_breakdown") if shipping_info else None,
                rate_card_id=shipping_info.get("rate_card_id") if shipping_info else None,
                rate_card_code=shipping_info.get("rate_card_code") if shipping_info else None,
                allocation_score=shipping_info.get("allocation_score") if shipping_info else None,
                segment=shipping_info.get("segment") if shipping_info else None,
                zone=shipping_info.get("zone") if shipping_info else None,
                allocation_strategy=shipping_info.get("strategy") if shipping_info else None,
                alternative_carriers=shipping_info.get("alternatives") if shipping_info else None,
            )
        except Exception as e:
            # Rollback transaction on any error to clean the session state
            await self.db.rollback()
            # Re-raise to let caller handle
            raise

    async def _get_order(self, order_id: uuid.UUID) -> Optional[Order]:
        """Get order by ID."""
        query = select(Order).where(Order.id == order_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def _get_allocation_rules(
        self,
        channel_code: str,
        payment_mode: Optional[str] = None,
        order_value: Optional[Decimal] = None
    ) -> List[AllocationRule]:
        """Get applicable allocation rules sorted by priority."""
        # Use string values for comparison (database columns are VARCHAR)
        channel_all = ChannelCode.ALL.value if hasattr(ChannelCode.ALL, 'value') else "ALL"
        query = (
            select(AllocationRule)
            .where(
                and_(
                    AllocationRule.is_active == True,
                    or_(
                        AllocationRule.channel_code == channel_code,
                        AllocationRule.channel_code == channel_all
                    )
                )
            )
            .order_by(AllocationRule.priority)
        )
        result = await self.db.execute(query)
        rules = result.scalars().all()

        # Filter by additional conditions
        filtered_rules = []
        for rule in rules:
            # Check payment mode
            if rule.payment_mode and payment_mode:
                if rule.payment_mode != payment_mode:
                    continue

            # Check order value range
            if order_value:
                if rule.min_order_value and order_value < Decimal(str(rule.min_order_value)):
                    continue
                if rule.max_order_value and order_value > Decimal(str(rule.max_order_value)):
                    continue

            filtered_rules.append(rule)

        return filtered_rules

    async def _get_serviceable_warehouses(
        self,
        pincode: str
    ) -> List[WarehouseServiceability]:
        """Get all serviceable warehouses for a pincode."""
        import logging
        logger = logging.getLogger(__name__)

        query = (
            select(WarehouseServiceability)
            .join(Warehouse)
            .where(
                and_(
                    WarehouseServiceability.pincode == pincode,
                    WarehouseServiceability.is_serviceable == True,
                    WarehouseServiceability.is_active == True,
                    Warehouse.is_active == True,
                    Warehouse.can_fulfill_orders == True
                )
            )
            .options(selectinload(WarehouseServiceability.warehouse))
            .order_by(WarehouseServiceability.priority)
        )
        result = await self.db.execute(query)
        warehouses = list(result.scalars().all())

        logger.info(f"_get_serviceable_warehouses: pincode={pincode}, found {len(warehouses)} warehouses")
        for ws in warehouses:
            logger.info(f"  - warehouse_id={ws.warehouse_id}, warehouse_code={ws.warehouse.code if ws.warehouse else 'N/A'}, cod_available={ws.cod_available}, prepaid_available={ws.prepaid_available}")

        return warehouses

    async def _apply_rule(
        self,
        rule: AllocationRule,
        serviceable_warehouses: List[WarehouseServiceability],
        product_ids: List[str],
        customer_pincode: str,
        payment_mode: Optional[str] = None,
        quantities: Optional[Dict[str, int]] = None,
        channel_code: Optional[str] = None
    ) -> Tuple[Optional[WarehouseServiceability], Dict]:
        """
        Apply allocation rule and return selected warehouse.

        Args:
            rule: Allocation rule to apply
            serviceable_warehouses: List of warehouses that service the pincode
            product_ids: List of product IDs to check
            customer_pincode: Customer's delivery pincode
            payment_mode: PREPAID or COD
            quantities: Dict of {product_id: quantity_needed}
            channel_code: Channel code for channel-specific inventory check
        """
        decision_factors = {
            "rule_name": rule.name,
            "allocation_type": rule.allocation_type if hasattr(rule.allocation_type, 'value') else str(rule.allocation_type),
            "candidates_count": len(serviceable_warehouses),
            "channel_code": channel_code or "SHARED",
        }

        # Filter by payment mode
        candidates = serviceable_warehouses
        if payment_mode == "COD":
            candidates = [ws for ws in candidates if ws.cod_available]
        elif payment_mode == "PREPAID":
            candidates = [ws for ws in candidates if ws.prepaid_available]

        if not candidates:
            decision_factors["failure"] = "No warehouse supports payment mode"
            return None, decision_factors

        # Handle FIXED allocation
        if rule.allocation_type == AllocationType.FIXED and rule.fixed_warehouse_id:
            for ws in candidates:
                if ws.warehouse_id == rule.fixed_warehouse_id:
                    # Check stock with quantities and channel
                    has_stock = await self._check_stock(ws.warehouse_id, product_ids, quantities, channel_code)
                    if has_stock:
                        decision_factors["selected_by"] = "FIXED_WAREHOUSE"
                        return ws, decision_factors
            decision_factors["failure"] = "Fixed warehouse doesn't have stock"
            return None, decision_factors

        # Get priority factors
        priority_factors = rule.get_priority_factors() if hasattr(rule, 'get_priority_factors') else ["PROXIMITY", "INVENTORY"]

        # Score each warehouse
        scored_candidates = []
        for ws in candidates:
            score = 0

            for factor in priority_factors:
                if factor == "PROXIMITY":
                    # Use priority (lower = better, so invert for scoring)
                    score += (1000 - ws.priority)
                elif factor == "INVENTORY":
                    has_stock = await self._check_stock(ws.warehouse_id, product_ids, quantities, channel_code)
                    if has_stock:
                        score += 500
                elif factor == "COST":
                    if ws.shipping_cost:
                        # Lower cost = better
                        score += max(0, 100 - ws.shipping_cost)
                elif factor == "SLA":
                    if ws.estimated_days:
                        # Fewer days = better
                        score += max(0, 50 - (ws.estimated_days * 5))

            scored_candidates.append((ws, score))

        # Sort by score descending
        scored_candidates.sort(key=lambda x: x[1], reverse=True)

        # Select best candidate with stock
        for ws, score in scored_candidates:
            has_stock = await self._check_stock(ws.warehouse_id, product_ids, quantities, channel_code)
            if has_stock or not product_ids:  # If no products specified, any warehouse works
                decision_factors["selected_by"] = priority_factors[0] if priority_factors else "PRIORITY"
                decision_factors["score"] = score
                return ws, decision_factors

        decision_factors["failure"] = "No candidate has sufficient inventory"
        return None, decision_factors

    async def _get_channel_by_code(self, channel_code: str) -> Optional[SalesChannel]:
        """Get sales channel by code."""
        result = await self.db.execute(
            select(SalesChannel).where(
                and_(
                    or_(
                        SalesChannel.code == channel_code,
                        SalesChannel.channel_type == channel_code,
                    ),
                    SalesChannel.status == "ACTIVE",
                )
            ).order_by(SalesChannel.created_at)
        )
        return result.scalars().first()

    async def _check_stock(
        self,
        warehouse_id: uuid.UUID,
        product_ids: List[str],
        quantities: Optional[Dict[str, int]] = None,
        channel_code: Optional[str] = None
    ) -> bool:
        """
        Check if warehouse has stock for all products.

        Now channel-aware: if channel_code is provided and CHANNEL_INVENTORY_ENABLED,
        checks ChannelInventory for that channel instead of InventorySummary.

        Args:
            warehouse_id: Warehouse to check
            product_ids: List of product IDs to check
            quantities: Optional dict of {product_id: quantity_needed}
            channel_code: Optional channel code for channel-specific inventory check

        Returns:
            True if warehouse has sufficient stock for all products
        """
        if not product_ids:
            return True

        import logging
        logger = logging.getLogger(__name__)

        # Check if channel-specific inventory should be used
        use_channel_inventory = False
        channel_obj = None

        logger.info(f"_check_stock: warehouse_id={warehouse_id}, product_ids={product_ids}, channel_code={channel_code}")

        if channel_code and getattr(settings, 'CHANNEL_INVENTORY_ENABLED', True):
            channel_obj = await self._get_channel_by_code(channel_code)
            logger.info(f"_check_stock: D2C channel lookup result: {channel_obj.id if channel_obj else 'NOT FOUND'}")
            if channel_obj:
                use_channel_inventory = True

        logger.info(f"_check_stock: use_channel_inventory={use_channel_inventory}")

        for product_id in product_ids:
            try:
                pid = uuid.UUID(str(product_id))
            except ValueError:
                continue

            # Get required quantity (default 1 if not specified)
            required_qty = quantities.get(product_id, 1) if quantities else 1

            if use_channel_inventory:
                # Check channel-specific inventory
                logger.info(f"_check_stock: Checking ChannelInventory for channel_id={channel_obj.id}, warehouse_id={warehouse_id}, product_id={pid}")
                query = select(ChannelInventory).where(
                    and_(
                        ChannelInventory.channel_id == channel_obj.id,
                        ChannelInventory.warehouse_id == warehouse_id,
                        ChannelInventory.product_id == pid,
                        ChannelInventory.is_active == True,
                    )
                )
                result = await self.db.execute(query)
                channel_inv = result.scalar_one_or_none()
                logger.info(f"_check_stock: ChannelInventory result: {channel_inv.id if channel_inv else 'NOT FOUND'}")

                if not channel_inv:
                    # No channel inventory - check fallback strategy
                    fallback = getattr(settings, 'D2C_FALLBACK_STRATEGY', 'SHARED_POOL')
                    logger.info(f"_check_stock: No ChannelInventory, fallback strategy={fallback}")
                    if fallback == 'NO_FALLBACK':
                        return False
                    # Fall through to shared pool check
                else:
                    # Channel inventory exists - check availability
                    # Available = allocated - buffer - reserved
                    channel_available = max(0,
                        (channel_inv.allocated_quantity or 0) -
                        (channel_inv.buffer_quantity or 0) -
                        (channel_inv.reserved_quantity or 0)
                    )

                    # Get channel-specific soft reserved
                    soft_reserved = await self._get_channel_soft_reserved(str(channel_obj.id), product_id)
                    actual_available = channel_available - soft_reserved

                    if actual_available >= required_qty:
                        continue  # This product is available, check next
                    else:
                        # Check fallback strategy
                        fallback = getattr(settings, 'D2C_FALLBACK_STRATEGY', 'SHARED_POOL')
                        if fallback == 'NO_FALLBACK':
                            return False
                        # Fall through to shared pool check

            # Legacy/fallback: check InventorySummary (shared pool)
            logger.info(f"_check_stock: Checking InventorySummary for warehouse_id={warehouse_id}, product_id={pid}")
            query = select(InventorySummary).where(
                and_(
                    InventorySummary.warehouse_id == warehouse_id,
                    InventorySummary.product_id == pid
                )
            )
            result = await self.db.execute(query)
            inventory = result.scalar_one_or_none()

            if not inventory:
                logger.warning(f"_check_stock: NO InventorySummary found for warehouse_id={warehouse_id}, product_id={pid} - RETURNING FALSE")
                return False

            # Calculate actual available = DB available - DB reserved - soft reserved
            db_available = inventory.available_quantity or 0
            db_reserved = inventory.reserved_quantity or 0
            soft_reserved = await self._get_soft_reserved(product_id)

            actual_available = db_available - db_reserved - soft_reserved
            logger.info(f"_check_stock: InventorySummary found - db_available={db_available}, db_reserved={db_reserved}, soft_reserved={soft_reserved}, actual_available={actual_available}, required_qty={required_qty}")

            if actual_available < required_qty:
                logger.warning(f"_check_stock: Insufficient stock - actual_available ({actual_available}) < required_qty ({required_qty}) - RETURNING FALSE")
                return False

        logger.info(f"_check_stock: All products have sufficient stock - RETURNING TRUE")
        return True

    async def _get_channel_soft_reserved(self, channel_id: str, product_id: str) -> int:
        """Get channel-specific soft-reserved quantity from cache."""
        try:
            cache = get_cache()
            key = f"channel:soft_reserved:{channel_id}:{product_id}"
            value = await cache.get(key)
            return int(value) if value else 0
        except Exception:
            return 0

    async def _get_soft_reserved(self, product_id: str) -> int:
        """Get total soft-reserved quantity from cache (checkout reservations)."""
        try:
            cache = get_cache()
            key = f"stock:reserved:{product_id}"
            value = await cache.get(key)
            return int(value) if value else 0
        except Exception:
            return 0

    async def check_inventory_availability(
        self,
        warehouse_id: uuid.UUID,
        items: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Detailed inventory check with availability breakdown.

        Args:
            warehouse_id: Warehouse to check
            items: List of {product_id, quantity} dicts

        Returns:
            Detailed availability info including:
            - is_available: bool
            - items: List of item-level availability
            - total_available: int
            - total_requested: int
        """
        result = {
            "is_available": True,
            "warehouse_id": str(warehouse_id),
            "items": [],
            "total_available": 0,
            "total_requested": 0
        }

        for item in items:
            product_id = item.get("product_id")
            requested_qty = item.get("quantity", 1)
            result["total_requested"] += requested_qty

            try:
                pid = uuid.UUID(str(product_id))
            except ValueError:
                result["items"].append({
                    "product_id": product_id,
                    "requested": requested_qty,
                    "available": 0,
                    "is_available": False,
                    "reason": "Invalid product ID"
                })
                result["is_available"] = False
                continue

            # Get inventory from database
            query = select(InventorySummary).where(
                and_(
                    InventorySummary.warehouse_id == warehouse_id,
                    InventorySummary.product_id == pid
                )
            )
            db_result = await self.db.execute(query)
            inventory = db_result.scalar_one_or_none()

            if not inventory:
                result["items"].append({
                    "product_id": product_id,
                    "requested": requested_qty,
                    "available": 0,
                    "db_available": 0,
                    "db_reserved": 0,
                    "soft_reserved": 0,
                    "is_available": False,
                    "reason": "Product not in warehouse inventory"
                })
                result["is_available"] = False
                continue

            # Calculate availability
            db_available = inventory.available_quantity or 0
            db_reserved = inventory.reserved_quantity or 0
            soft_reserved = await self._get_soft_reserved(product_id)

            actual_available = max(0, db_available - db_reserved - soft_reserved)
            is_item_available = actual_available >= requested_qty

            result["items"].append({
                "product_id": product_id,
                "requested": requested_qty,
                "available": actual_available,
                "db_available": db_available,
                "db_reserved": db_reserved,
                "soft_reserved": soft_reserved,
                "is_available": is_item_available,
                "reason": None if is_item_available else f"Only {actual_available} available, {requested_qty} requested"
            })

            result["total_available"] += actual_available

            if not is_item_available:
                result["is_available"] = False

        return result

    async def find_best_warehouse_for_items(
        self,
        pincode: str,
        items: List[Dict[str, Any]],
        payment_mode: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Find the best warehouse that can fulfill all items.

        Args:
            pincode: Customer pincode
            items: List of {product_id, quantity} dicts
            payment_mode: PREPAID or COD

        Returns:
            Best warehouse with availability details, or None if not found
        """
        # Get serviceable warehouses
        serviceable = await self._get_serviceable_warehouses(pincode)

        if not serviceable:
            return {
                "found": False,
                "reason": "No warehouse services this pincode",
                "warehouses_checked": 0
            }

        # Filter by payment mode
        candidates = serviceable
        if payment_mode == "COD":
            candidates = [ws for ws in candidates if ws.cod_available]
        elif payment_mode == "PREPAID":
            candidates = [ws for ws in candidates if ws.prepaid_available]

        if not candidates:
            return {
                "found": False,
                "reason": f"No warehouse supports {payment_mode} payment mode",
                "warehouses_checked": len(serviceable)
            }

        # Check each warehouse for availability
        best_warehouse = None
        best_score = -1
        warehouse_results = []

        for ws in candidates:
            availability = await self.check_inventory_availability(
                warehouse_id=ws.warehouse_id,
                items=items
            )

            warehouse_result = {
                "warehouse_id": str(ws.warehouse_id),
                "warehouse_code": ws.warehouse.code,
                "warehouse_name": ws.warehouse.name,
                "is_available": availability["is_available"],
                "priority": ws.priority,
                "estimated_days": ws.estimated_days,
                "shipping_cost": ws.shipping_cost,
                "items": availability["items"]
            }
            warehouse_results.append(warehouse_result)

            if availability["is_available"]:
                # Score: lower priority is better, more available stock is better
                score = (1000 - ws.priority) + availability["total_available"]
                if score > best_score:
                    best_score = score
                    best_warehouse = {
                        **warehouse_result,
                        "serviceability": ws
                    }

        if best_warehouse:
            return {
                "found": True,
                "warehouse": best_warehouse,
                "warehouses_checked": len(candidates),
                "all_results": warehouse_results
            }
        else:
            return {
                "found": False,
                "reason": "No warehouse has sufficient inventory for all items",
                "warehouses_checked": len(candidates),
                "all_results": warehouse_results
            }

    async def _select_transporter(
        self,
        warehouse_serviceability: WarehouseServiceability,
        destination_pincode: str,
        payment_mode: Optional[str] = None,
        weight_kg: float = 1.0,
        order_value: float = 0,
        dimensions: Optional[Dict] = None,
        allocation_strategy: str = "BALANCED"
    ) -> Tuple[Optional[Transporter], Optional[Dict]]:
        """
        Select best transporter for the route.

        Uses pricing engine if available for rate card-based selection,
        falls back to TransporterServiceability otherwise.
        """
        warehouse = warehouse_serviceability.warehouse
        origin_pincode = warehouse.pincode

        # Try pricing engine first for rate card-based selection
        if PRICING_ENGINE_AVAILABLE:
            transporter, shipping_info = await self._select_transporter_with_pricing_engine(
                origin_pincode=origin_pincode,
                destination_pincode=destination_pincode,
                payment_mode=payment_mode,
                weight_kg=weight_kg,
                order_value=order_value,
                dimensions=dimensions,
                allocation_strategy=allocation_strategy
            )
            if transporter or shipping_info:
                return transporter, shipping_info

        # Fallback to TransporterServiceability
        return await self._select_transporter_legacy(
            origin_pincode=origin_pincode,
            destination_pincode=destination_pincode,
            payment_mode=payment_mode
        )

    async def _select_transporter_with_pricing_engine(
        self,
        origin_pincode: str,
        destination_pincode: str,
        payment_mode: Optional[str] = None,
        weight_kg: float = 1.0,
        order_value: float = 0,
        dimensions: Optional[Dict] = None,
        allocation_strategy: str = "BALANCED"
    ) -> Tuple[Optional[Transporter], Optional[Dict]]:
        """
        Select transporter using pricing engine and rate cards.

        Returns carrier with full cost breakdown and performance data.
        """
        try:
            engine = PricingEngine(self.db)

            # Build rate calculation request
            request = RateCalculationRequest(
                origin_pincode=origin_pincode,
                destination_pincode=destination_pincode,
                weight_kg=weight_kg,
                length_cm=dimensions.get("length") if dimensions else None,
                width_cm=dimensions.get("width") if dimensions else None,
                height_cm=dimensions.get("height") if dimensions else None,
                payment_mode=payment_mode or "PREPAID",
                order_value=order_value,
            )

            # Get allocation strategy enum
            strategy = AllocationStrategy.BALANCED
            if allocation_strategy == "CHEAPEST_FIRST":
                strategy = AllocationStrategy.CHEAPEST_FIRST
            elif allocation_strategy == "FASTEST_FIRST":
                strategy = AllocationStrategy.FASTEST_FIRST
            elif allocation_strategy == "BEST_SLA":
                strategy = AllocationStrategy.BEST_SLA

            # Allocate carrier
            result = await engine.allocate(request, strategy)

            if not result.get("success") or not result.get("allocation"):
                return None, None

            allocation = result["allocation"]
            carrier = allocation.get("carrier", {})

            # Get transporter from database
            transporter = None
            if carrier.get("id"):
                try:
                    transporter_id = uuid.UUID(carrier["id"])
                    query = select(Transporter).where(Transporter.id == transporter_id)
                    db_result = await self.db.execute(query)
                    transporter = db_result.scalar_one_or_none()
                except (ValueError, Exception):
                    pass

            # Build shipping info with full cost breakdown
            shipping_info = {
                "estimated_days": allocation.get("estimated_delivery", {}).get("max_days", 5),
                "estimated_days_min": allocation.get("estimated_delivery", {}).get("min_days", 2),
                "rate": allocation.get("total_cost", 0),
                "cost_breakdown": allocation.get("cost_breakdown", {}),
                "rate_card_id": allocation.get("rate_card_id"),
                "rate_card_code": allocation.get("rate_card_code"),
                "carrier_code": carrier.get("code"),
                "carrier_name": carrier.get("name"),
                "allocation_score": allocation.get("score", 0),
                "segment": result.get("segment"),
                "zone": result.get("zone"),
                "strategy": result.get("strategy"),
                "cod_available": payment_mode == "COD",
                "alternatives": result.get("alternatives", []),
            }

            return transporter, shipping_info

        except Exception as e:
            # Log error and fall back to legacy method
            import logging
            logging.warning(f"Pricing engine error: {e}, falling back to legacy method")
            return None, None

    async def _select_transporter_legacy(
        self,
        origin_pincode: str,
        destination_pincode: str,
        payment_mode: Optional[str] = None
    ) -> Tuple[Optional[Transporter], Optional[Dict]]:
        """Legacy transporter selection using TransporterServiceability."""
        query = (
            select(TransporterServiceability)
            .join(Transporter)
            .where(
                and_(
                    TransporterServiceability.origin_pincode == origin_pincode,
                    TransporterServiceability.destination_pincode == destination_pincode,
                    TransporterServiceability.is_serviceable == True,
                    Transporter.is_active == True
                )
            )
            .options(selectinload(TransporterServiceability.transporter))
            .order_by(TransporterServiceability.rate)  # Cheapest first
        )

        # Filter by payment mode
        if payment_mode == "COD":
            query = query.where(TransporterServiceability.cod_available == True)

        result = await self.db.execute(query)
        ts = result.scalars().first()

        if ts:
            return ts.transporter, {
                "estimated_days": ts.estimated_days,
                "rate": ts.rate,
                "cod_available": ts.cod_available,
                "source": "legacy_serviceability"
            }

        return None, None

    async def _log_allocation(
        self,
        order_id: uuid.UUID,
        rule_id: Optional[uuid.UUID],
        warehouse_id: Optional[uuid.UUID],
        customer_pincode: str,
        is_successful: bool,
        decision_factors: Dict = None,
        candidates: List[WarehouseCandidate] = None,
        failure_reason: str = None
    ):
        """Log allocation decision."""
        log = AllocationLog(
            order_id=order_id,
            rule_id=rule_id,
            warehouse_id=warehouse_id,
            customer_pincode=customer_pincode,
            is_successful=is_successful,
            failure_reason=failure_reason,
            decision_factors=json.dumps(decision_factors) if decision_factors else None,
            candidates_considered=json.dumps([c.model_dump(mode='json') for c in candidates]) if candidates else None
        )
        self.db.add(log)
        await self.db.commit()

    async def _update_order_warehouse(
        self,
        order: Order,
        warehouse_id: uuid.UUID,
        channel_code: Optional[str] = None
    ):
        """
        Update order with allocated warehouse and consume channel inventory.

        Args:
            order: The order being allocated
            warehouse_id: The warehouse fulfilling the order
            channel_code: The sales channel (D2C, AMAZON, etc.) for inventory deduction
        """
        import logging
        logger = logging.getLogger(__name__)

        # Refresh order to prevent lazy loading errors after _log_allocation commit
        await self.db.refresh(order)

        order.warehouse_id = warehouse_id
        order.allocated_at = datetime.now(timezone.utc)
        # Update status to ALLOCATED for orders in NEW or CONFIRMED status
        # Use string values for comparison (database column is VARCHAR)
        new_status = OrderStatus.NEW.value if hasattr(OrderStatus.NEW, 'value') else "NEW"
        confirmed_status = OrderStatus.CONFIRMED.value if hasattr(OrderStatus.CONFIRMED, 'value') else "CONFIRMED"
        allocated_status = OrderStatus.ALLOCATED.value if hasattr(OrderStatus.ALLOCATED, 'value') else "ALLOCATED"

        if order.status in [new_status, confirmed_status]:
            order.status = allocated_status
            # Also mark as confirmed if it wasn't
            if not order.confirmed_at:
                order.confirmed_at = datetime.now(timezone.utc)

        # Consume channel inventory for D2C and marketplace orders
        # This is critical for preventing overselling in D2C channels
        channel_consumption_success = True
        if channel_code and getattr(settings, 'CHANNEL_INVENTORY_ENABLED', True):
            try:
                # Load order items to get product_id and quantity
                order_items_query = select(OrderItem).where(OrderItem.order_id == order.id)
                items_result = await self.db.execute(order_items_query)
                order_items = items_result.scalars().all()

                if order_items:
                    # Prepare items list for consumption
                    items_to_consume = [
                        {"product_id": str(item.product_id), "quantity": item.quantity}
                        for item in order_items
                    ]

                    # Consume from channel inventory
                    channel_service = ChannelInventoryService(self.db)
                    result = await channel_service.consume_for_order(
                        channel_code=channel_code,
                        order_id=order.id,
                        items=items_to_consume,
                        warehouse_id=warehouse_id
                    )

                    if result.get("success"):
                        logger.info(
                            f"Channel inventory consumed for order {order.order_number}: "
                            f"channel={channel_code}, items={result.get('consumed_items')}"
                        )
                    else:
                        # Channel not found or other soft error - log but continue
                        # This handles cases where channel inventory isn't set up for this product
                        logger.warning(
                            f"Channel inventory not consumed for order {order.order_number}: "
                            f"{result.get('error')} - proceeding with allocation"
                        )
            except Exception as e:
                # Log the error - channel inventory consumption failed
                # For strict D2C mode, this could be made to fail the allocation
                logger.error(f"Error consuming channel inventory for order {order.order_number}: {e}")
                channel_consumption_success = False

                # Check if we should fail hard on channel inventory errors
                if getattr(settings, 'CHANNEL_INVENTORY_STRICT_MODE', False):
                    # Rollback and re-raise to fail the allocation
                    await self.db.rollback()
                    raise

        # Commit the transaction (order update + channel inventory consumption)
        await self.db.commit()

        if not channel_consumption_success:
            logger.warning(
                f"Order {order.order_number} allocated but channel inventory may be inconsistent"
            )

    async def _create_failed_allocation(
        self,
        order_id: uuid.UUID,
        pincode: str,
        rule_id: Optional[uuid.UUID],
        failure_reason: str,
        alternatives: List[WarehouseCandidate] = None
    ) -> AllocationDecision:
        """Create failed allocation response and log."""
        await self._log_allocation(
            order_id=order_id,
            rule_id=rule_id,
            warehouse_id=None,
            customer_pincode=pincode,
            is_successful=False,
            failure_reason=failure_reason,
            candidates=alternatives
        )

        return AllocationDecision(
            order_id=order_id,
            is_allocated=False,
            failure_reason=failure_reason,
            alternatives=alternatives
        )

    def _ws_to_candidate(self, ws: WarehouseServiceability) -> WarehouseCandidate:
        """Convert WarehouseServiceability to WarehouseCandidate."""
        return WarehouseCandidate(
            warehouse_id=ws.warehouse_id,
            warehouse_code=ws.warehouse.code,
            warehouse_name=ws.warehouse.name,
            city=ws.warehouse.city,
            estimated_days=ws.estimated_days,
            shipping_cost=ws.shipping_cost,
            priority=ws.priority,
            cod_available=ws.cod_available,
            prepaid_available=ws.prepaid_available
        )

    # ==================== Allocation Rule CRUD ====================

    async def create_rule(
        self,
        data: AllocationRuleCreate,
        created_by: Optional[uuid.UUID] = None
    ) -> AllocationRule:
        """Create an allocation rule."""
        rule = AllocationRule(
            name=data.name,
            description=data.description,
            channel_code=ChannelCode(data.channel_code) if data.channel_code else ChannelCode.ALL,
            channel_id=data.channel_id,
            priority=data.priority,
            allocation_type=AllocationType(data.allocation_type) if data.allocation_type else AllocationType.NEAREST,
            fixed_warehouse_id=data.fixed_warehouse_id,
            priority_factors=data.priority_factors,
            min_order_value=data.min_order_value,
            max_order_value=data.max_order_value,
            payment_mode=data.payment_mode,
            allow_split=data.allow_split,
            max_splits=data.max_splits,
            is_active=data.is_active,
            created_by=created_by
        )
        self.db.add(rule)
        await self.db.commit()
        await self.db.refresh(rule)
        return rule

    async def get_rules(
        self,
        channel_code: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> List[AllocationRule]:
        """Get allocation rules."""
        query = select(AllocationRule)

        conditions = []
        if channel_code:
            conditions.append(AllocationRule.channel_code == ChannelCode(channel_code))
        if is_active is not None:
            conditions.append(AllocationRule.is_active == is_active)

        if conditions:
            query = query.where(and_(*conditions))

        query = query.order_by(AllocationRule.priority)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_rule(self, rule_id: uuid.UUID) -> Optional[AllocationRule]:
        """Get allocation rule by ID."""
        query = select(AllocationRule).where(AllocationRule.id == rule_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def update_rule(
        self,
        rule_id: uuid.UUID,
        data: AllocationRuleUpdate
    ) -> Optional[AllocationRule]:
        """Update an allocation rule."""
        rule = await self.get_rule(rule_id)
        if not rule:
            return None

        update_data = data.model_dump(exclude_unset=True)

        # Handle enum conversions
        if "channel_code" in update_data and update_data["channel_code"]:
            update_data["channel_code"] = ChannelCode(update_data["channel_code"])
        if "allocation_type" in update_data and update_data["allocation_type"]:
            update_data["allocation_type"] = AllocationType(update_data["allocation_type"])

        for key, value in update_data.items():
            setattr(rule, key, value)

        await self.db.commit()
        await self.db.refresh(rule)
        return rule

    async def delete_rule(self, rule_id: uuid.UUID) -> bool:
        """Delete an allocation rule."""
        rule = await self.get_rule(rule_id)
        if not rule:
            return False

        await self.db.delete(rule)
        await self.db.commit()
        return True

    # ==================== Allocation Logs ====================

    async def get_allocation_logs(
        self,
        order_id: Optional[uuid.UUID] = None,
        is_successful: Optional[bool] = None,
        limit: int = 100
    ) -> List[AllocationLog]:
        """Get allocation logs."""
        query = select(AllocationLog)

        conditions = []
        if order_id:
            conditions.append(AllocationLog.order_id == order_id)
        if is_successful is not None:
            conditions.append(AllocationLog.is_successful == is_successful)

        if conditions:
            query = query.where(and_(*conditions))

        query = query.order_by(desc(AllocationLog.created_at)).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())
