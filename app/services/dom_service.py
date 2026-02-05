"""
Distributed Order Management (DOM) Service.

The brain of order fulfillment - handles:
1. Order Orchestration - Routing orders to optimal fulfillment nodes
2. Inventory Aggregation - Global ATP/ATF calculations
3. Order Splitting - Splitting orders across nodes when needed
4. Backorder Management - Capturing demand for OOS items
5. Pre-order Management - Taking orders for upcoming products

Architecture inspired by Unicommerce, Vinculum, and Oracle DOM.
"""
import uuid
import math
import time
from datetime import datetime, date, timezone, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy import select, func, and_, or_, case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.dom import (
    FulfillmentNode,
    RoutingRule,
    OrderSplit,
    OrchestrationLog,
    Backorder,
    Preorder,
    GlobalInventoryView,
    FulfillmentNodeType,
    RoutingStrategy,
    SplitReason,
    BackorderStatus,
    PreorderStatus,
    OrchestrationStatus,
)
from app.models.order import Order, OrderItem, OrderStatus
from app.models.inventory import InventorySummary, StockItem
from app.models.warehouse import Warehouse
from app.models.serviceability import WarehouseServiceability
from app.schemas.dom import (
    FulfillmentNodeCreate,
    FulfillmentNodeUpdate,
    RoutingRuleCreate,
    RoutingRuleUpdate,
    OrchestrationRequest,
    OrchestrationResult,
    NodeScore,
    SplitDecision,
    BackorderCreate,
    BackorderUpdate,
    PreorderCreate,
    PreorderUpdate,
    ATPCheckRequest,
    ATPCheckResponse,
    ATPCheckItem,
    GlobalInventoryItem,
    DOMStats,
)


class DOMService:
    """
    Distributed Order Management Service.

    Core orchestration engine for order fulfillment decisions.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    # ========================================================================
    # FULFILLMENT NODE MANAGEMENT
    # ========================================================================

    async def create_fulfillment_node(
        self,
        data: FulfillmentNodeCreate
    ) -> FulfillmentNode:
        """Create a new fulfillment node."""
        node = FulfillmentNode(
            **data.model_dump()
        )
        self.db.add(node)
        await self.db.commit()
        await self.db.refresh(node)
        return node

    async def get_fulfillment_node(self, node_id: uuid.UUID) -> Optional[FulfillmentNode]:
        """Get fulfillment node by ID."""
        result = await self.db.execute(
            select(FulfillmentNode).where(FulfillmentNode.id == node_id)
        )
        return result.scalar_one_or_none()

    async def get_fulfillment_node_by_code(self, node_code: str) -> Optional[FulfillmentNode]:
        """Get fulfillment node by code."""
        result = await self.db.execute(
            select(FulfillmentNode).where(FulfillmentNode.node_code == node_code)
        )
        return result.scalar_one_or_none()

    async def get_fulfillment_nodes(
        self,
        node_type: Optional[str] = None,
        is_active: Optional[bool] = True,
        region_id: Optional[uuid.UUID] = None,
        page: int = 1,
        size: int = 20,
    ) -> Tuple[List[FulfillmentNode], int]:
        """Get list of fulfillment nodes with filters."""
        query = select(FulfillmentNode)

        if node_type:
            query = query.where(FulfillmentNode.node_type == node_type)
        if is_active is not None:
            query = query.where(FulfillmentNode.is_active == is_active)
        if region_id:
            query = query.where(FulfillmentNode.region_id == region_id)

        # Count
        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar() or 0

        # Paginate
        query = query.order_by(FulfillmentNode.priority, FulfillmentNode.node_name)
        query = query.offset((page - 1) * size).limit(size)

        result = await self.db.execute(query)
        return list(result.scalars().all()), total

    async def update_fulfillment_node(
        self,
        node_id: uuid.UUID,
        data: FulfillmentNodeUpdate
    ) -> Optional[FulfillmentNode]:
        """Update fulfillment node."""
        node = await self.get_fulfillment_node(node_id)
        if not node:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(node, field, value)

        await self.db.commit()
        await self.db.refresh(node)
        return node

    async def sync_nodes_from_warehouses(self) -> int:
        """
        Sync fulfillment nodes from existing warehouses.
        Creates nodes for warehouses that don't have corresponding nodes.
        """
        # Get all warehouses
        warehouses_result = await self.db.execute(
            select(Warehouse).where(Warehouse.is_active == True)
        )
        warehouses = list(warehouses_result.scalars().all())

        created = 0
        for warehouse in warehouses:
            # Check if node exists
            existing = await self.db.execute(
                select(FulfillmentNode).where(
                    FulfillmentNode.warehouse_id == warehouse.id
                )
            )
            if existing.scalar_one_or_none():
                continue

            # Create node
            node = FulfillmentNode(
                node_code=f"WH-{warehouse.code}",
                node_name=warehouse.name,
                node_type=FulfillmentNodeType.WAREHOUSE.value,
                warehouse_id=warehouse.id,
                region_id=warehouse.region_id,
                latitude=warehouse.latitude,
                longitude=warehouse.longitude,
                pincode=warehouse.pincode,
                city=warehouse.city,
                state=warehouse.state,
                is_active=warehouse.is_active,
                can_fulfill_b2c=warehouse.can_fulfill_orders,
                can_fulfill_b2b=True,
            )
            self.db.add(node)
            created += 1

        await self.db.commit()
        return created

    # ========================================================================
    # ROUTING RULE MANAGEMENT
    # ========================================================================

    async def create_routing_rule(
        self,
        data: RoutingRuleCreate,
        created_by: Optional[uuid.UUID] = None
    ) -> RoutingRule:
        """Create a new routing rule."""
        rule = RoutingRule(
            **data.model_dump(),
            created_by=created_by
        )
        self.db.add(rule)
        await self.db.commit()
        await self.db.refresh(rule)
        return rule

    async def get_routing_rule(self, rule_id: uuid.UUID) -> Optional[RoutingRule]:
        """Get routing rule by ID."""
        result = await self.db.execute(
            select(RoutingRule).where(RoutingRule.id == rule_id)
        )
        return result.scalar_one_or_none()

    async def get_routing_rules(
        self,
        is_active: Optional[bool] = True,
        channel_id: Optional[uuid.UUID] = None,
        page: int = 1,
        size: int = 20,
    ) -> Tuple[List[RoutingRule], int]:
        """Get list of routing rules with filters."""
        query = select(RoutingRule)

        if is_active is not None:
            query = query.where(RoutingRule.is_active == is_active)
        if channel_id:
            query = query.where(
                or_(
                    RoutingRule.channel_id == channel_id,
                    RoutingRule.channel_id.is_(None)
                )
            )

        # Count
        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar() or 0

        # Paginate
        query = query.order_by(RoutingRule.priority, RoutingRule.rule_name)
        query = query.offset((page - 1) * size).limit(size)

        result = await self.db.execute(query)
        return list(result.scalars().all()), total

    async def update_routing_rule(
        self,
        rule_id: uuid.UUID,
        data: RoutingRuleUpdate
    ) -> Optional[RoutingRule]:
        """Update routing rule."""
        rule = await self.get_routing_rule(rule_id)
        if not rule:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(rule, field, value)

        await self.db.commit()
        await self.db.refresh(rule)
        return rule

    async def delete_routing_rule(self, rule_id: uuid.UUID) -> bool:
        """Delete (deactivate) routing rule."""
        rule = await self.get_routing_rule(rule_id)
        if not rule:
            return False

        rule.is_active = False
        await self.db.commit()
        return True

    # ========================================================================
    # ORDER ORCHESTRATION - THE BRAIN
    # ========================================================================

    async def orchestrate_order(
        self,
        request: OrchestrationRequest
    ) -> OrchestrationResult:
        """
        Main entry point for order orchestration.

        This is the brain of the DOM - it decides:
        1. Which fulfillment node(s) should fulfill the order
        2. Whether to split the order
        3. Whether to backorder items

        Returns:
            OrchestrationResult with routing decision
        """
        start_time = time.time()

        # Get order with items
        order = await self._get_order_with_items(request.order_id)
        if not order:
            return OrchestrationResult(
                order_id=request.order_id,
                order_number="",
                status=OrchestrationStatus.FAILED,
                routing_strategy="NONE",
                failure_reason="Order not found"
            )

        result = OrchestrationResult(
            order_id=order.id,
            order_number=order.order_number,
            status=OrchestrationStatus.PENDING,
            routing_strategy="NEAREST",
        )

        try:
            # 1. Check global availability
            availability = await self._check_global_availability(order)

            # 2. Find applicable routing rule
            rule = await self._find_matching_rule(order)
            if rule:
                result.routing_rule_id = rule.id
                result.routing_rule_name = rule.rule_name
                result.routing_strategy = rule.routing_strategy

                # Apply rule overrides
                allow_split = rule.allow_split if request.allow_split is None else request.allow_split
                allow_backorder = rule.allow_backorder if request.allow_backorder is None else request.allow_backorder
            else:
                allow_split = request.allow_split if request.allow_split is not None else True
                allow_backorder = request.allow_backorder if request.allow_backorder is not None else False

            # 3. Get and score eligible nodes
            nodes = await self._get_eligible_nodes(order, rule)
            scored_nodes = await self._score_nodes(order, nodes, availability, rule)
            result.evaluated_nodes = scored_nodes

            # 4. Find best fulfillment strategy
            if request.force_node_id:
                # Force specific node
                selected = next((n for n in scored_nodes if n.node_id == request.force_node_id), None)
                if selected and selected.can_fulfill_complete:
                    result.selected_node_id = selected.node_id
                    result.selected_node_code = selected.node_code
                    result.status = OrchestrationStatus.ROUTED
                else:
                    result.status = OrchestrationStatus.FAILED
                    result.failure_reason = "Forced node cannot fulfill order"
            else:
                # Find best option
                best_node = self._find_best_node(scored_nodes)

                if best_node and best_node.can_fulfill_complete:
                    # Single node can fulfill entire order
                    result.selected_node_id = best_node.node_id
                    result.selected_node_code = best_node.node_code
                    result.status = OrchestrationStatus.ROUTED
                elif allow_split and len(scored_nodes) > 1:
                    # Try to split across multiple nodes
                    splits = await self._plan_order_split(
                        order, scored_nodes, availability, rule
                    )
                    if splits:
                        result.splits = splits
                        result.split_count = len(splits)
                        result.status = OrchestrationStatus.SPLIT
                    elif allow_backorder:
                        result.status = OrchestrationStatus.BACKORDER
                    else:
                        result.status = OrchestrationStatus.FAILED
                        result.failure_reason = "Cannot fulfill order - insufficient inventory"
                elif allow_backorder:
                    result.status = OrchestrationStatus.BACKORDER
                else:
                    result.status = OrchestrationStatus.FAILED
                    result.failure_reason = "No node can fulfill the complete order"

            # 5. Execute (unless dry run)
            if not request.dry_run and result.status in [
                OrchestrationStatus.ROUTED,
                OrchestrationStatus.SPLIT,
                OrchestrationStatus.BACKORDER
            ]:
                await self._execute_orchestration(order, result)

            result.is_dry_run = request.dry_run

        except Exception as e:
            result.status = OrchestrationStatus.FAILED
            result.failure_reason = str(e)

        # Record processing time
        result.processing_time_ms = int((time.time() - start_time) * 1000)

        # Log the decision
        await self._log_orchestration(result)

        return result

    async def _get_order_with_items(self, order_id: uuid.UUID) -> Optional[Order]:
        """Get order with items loaded."""
        result = await self.db.execute(
            select(Order)
            .options(selectinload(Order.items))
            .where(Order.id == order_id)
        )
        return result.scalar_one_or_none()

    async def _check_global_availability(
        self,
        order: Order
    ) -> Dict[uuid.UUID, Dict[uuid.UUID, int]]:
        """
        Check inventory availability across all nodes.

        Returns:
            Dict[product_id, Dict[node_id, available_qty]]
        """
        availability: Dict[uuid.UUID, Dict[uuid.UUID, int]] = {}

        for item in order.items:
            product_id = item.product_id

            # Get inventory across all nodes
            query = select(
                InventorySummary.warehouse_id,
                InventorySummary.available_quantity
            ).where(
                InventorySummary.product_id == product_id,
                InventorySummary.available_quantity > 0
            )

            result = await self.db.execute(query)
            rows = result.all()

            # Map warehouse_id to node_id
            availability[product_id] = {}
            for warehouse_id, qty in rows:
                # Get node for this warehouse
                node_result = await self.db.execute(
                    select(FulfillmentNode.id).where(
                        FulfillmentNode.warehouse_id == warehouse_id,
                        FulfillmentNode.is_active == True
                    )
                )
                node_id = node_result.scalar_one_or_none()
                if node_id:
                    availability[product_id][node_id] = qty

        return availability

    async def _find_matching_rule(self, order: Order) -> Optional[RoutingRule]:
        """Find the first matching routing rule for the order."""
        now = datetime.now(timezone.utc)

        # Get active rules ordered by priority
        result = await self.db.execute(
            select(RoutingRule)
            .where(
                RoutingRule.is_active == True,
                or_(RoutingRule.valid_from.is_(None), RoutingRule.valid_from <= now),
                or_(RoutingRule.valid_until.is_(None), RoutingRule.valid_until >= now),
            )
            .order_by(RoutingRule.priority)
        )
        rules = list(result.scalars().all())

        for rule in rules:
            if self._rule_matches_order(rule, order):
                return rule

        return None

    def _rule_matches_order(self, rule: RoutingRule, order: Order) -> bool:
        """Check if routing rule matches order conditions."""
        # Channel condition
        if rule.channel_id and hasattr(order, 'channel_id'):
            if order.channel_id != rule.channel_id:
                return False

        if rule.channel_codes:
            order_source = order.source if hasattr(order, 'source') else None
            if order_source not in rule.channel_codes:
                return False

        # Order value condition
        if rule.min_order_value and order.total_amount < rule.min_order_value:
            return False
        if rule.max_order_value and order.total_amount > rule.max_order_value:
            return False

        # Payment method condition
        if rule.payment_methods:
            payment_method = order.payment_method if hasattr(order, 'payment_method') else None
            if payment_method not in rule.payment_methods:
                return False

        # Pincode condition
        if rule.pincode_patterns and hasattr(order, 'shipping_address'):
            shipping_pincode = order.shipping_address.get('pincode', '') if order.shipping_address else ''
            if not self._matches_pincode_pattern(shipping_pincode, rule.pincode_patterns):
                return False

        return True

    def _matches_pincode_pattern(self, pincode: str, patterns: List[str]) -> bool:
        """Check if pincode matches any pattern."""
        if not pincode:
            return False

        for pattern in patterns:
            if '-' in pattern:
                # Range pattern: 110001-110099
                start, end = pattern.split('-')
                if start <= pincode <= end:
                    return True
            elif '*' in pattern:
                # Wildcard pattern: 110*
                prefix = pattern.replace('*', '')
                if pincode.startswith(prefix):
                    return True
            elif pincode == pattern:
                return True

        return False

    async def _get_eligible_nodes(
        self,
        order: Order,
        rule: Optional[RoutingRule]
    ) -> List[FulfillmentNode]:
        """Get fulfillment nodes eligible for this order."""
        query = select(FulfillmentNode).where(
            FulfillmentNode.is_active == True,
            FulfillmentNode.is_accepting_orders == True
        )

        # Filter by B2C/B2B capability
        source = order.source if hasattr(order, 'source') else 'WEBSITE'
        if source in ['DEALER', 'STORE']:
            query = query.where(FulfillmentNode.can_fulfill_b2b == True)
        else:
            query = query.where(FulfillmentNode.can_fulfill_b2c == True)

        # Apply rule filters
        if rule:
            if rule.target_node_id:
                query = query.where(FulfillmentNode.id == rule.target_node_id)
            elif rule.preferred_node_ids:
                # Prefer these but don't exclude others
                pass
            if rule.excluded_node_ids:
                query = query.where(~FulfillmentNode.id.in_(rule.excluded_node_ids))

        # Check serviceability
        if hasattr(order, 'shipping_address') and order.shipping_address:
            pincode = order.shipping_address.get('pincode')
            if pincode:
                # Get serviceable warehouse IDs for this pincode
                serviceable = await self.db.execute(
                    select(WarehouseServiceability.warehouse_id).where(
                        WarehouseServiceability.pincode == pincode,
                        WarehouseServiceability.is_serviceable == True,
                        WarehouseServiceability.is_active == True
                    )
                )
                serviceable_warehouse_ids = [r[0] for r in serviceable.all()]

                if serviceable_warehouse_ids:
                    query = query.where(
                        or_(
                            FulfillmentNode.warehouse_id.in_(serviceable_warehouse_ids),
                            FulfillmentNode.node_type != FulfillmentNodeType.WAREHOUSE.value
                        )
                    )

        result = await self.db.execute(query.order_by(FulfillmentNode.priority))
        return list(result.scalars().all())

    async def _score_nodes(
        self,
        order: Order,
        nodes: List[FulfillmentNode],
        availability: Dict[uuid.UUID, Dict[uuid.UUID, int]],
        rule: Optional[RoutingRule]
    ) -> List[NodeScore]:
        """Score each node for this order."""
        scored: List[NodeScore] = []

        # Get customer location
        customer_lat = customer_lng = None
        if hasattr(order, 'shipping_address') and order.shipping_address:
            customer_lat = order.shipping_address.get('latitude')
            customer_lng = order.shipping_address.get('longitude')

        for node in nodes:
            score = NodeScore(
                node_id=node.id,
                node_code=node.node_code,
                node_name=node.node_name,
                total_score=0.0,
            )

            # Calculate inventory score
            can_fulfill_all = True
            total_available = 0
            for item in order.items:
                product_avail = availability.get(item.product_id, {})
                node_qty = product_avail.get(node.id, 0)
                if node_qty < item.quantity:
                    can_fulfill_all = False
                total_available += node_qty

            score.can_fulfill_complete = can_fulfill_all
            score.available_quantity = total_available
            score.inventory_score = 40.0 if can_fulfill_all else (total_available / sum(i.quantity for i in order.items)) * 40

            # Calculate distance score (if coordinates available)
            if customer_lat and customer_lng and node.latitude and node.longitude:
                distance_km = self._haversine_distance(
                    customer_lat, customer_lng,
                    node.latitude, node.longitude
                )
                # Score: closer = higher score (max 30 for <10km, min 0 for >500km)
                score.distance_score = max(0, 30 - (distance_km / 500) * 30)
            else:
                score.distance_score = 15  # Default middle score

            # Capacity score
            utilization = node.current_day_orders / max(node.daily_order_capacity, 1)
            score.capacity_score = max(0, 15 * (1 - utilization))

            # Performance score (based on fulfillment_score)
            score.sla_score = (node.fulfillment_score / 100) * 15

            # Calculate total
            score.total_score = (
                score.inventory_score +
                score.distance_score +
                score.capacity_score +
                score.sla_score
            )

            # Apply preferred node bonus
            if rule and rule.preferred_node_ids and node.id in rule.preferred_node_ids:
                score.total_score += 10  # Bonus for preferred nodes

            scored.append(score)

        # Sort by total score (descending)
        scored.sort(key=lambda x: x.total_score, reverse=True)

        return scored

    def _haversine_distance(
        self,
        lat1: float, lon1: float,
        lat2: float, lon2: float
    ) -> float:
        """Calculate distance between two points in km."""
        R = 6371  # Earth's radius in km

        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lon = math.radians(lon2 - lon1)

        a = (math.sin(delta_lat / 2) ** 2 +
             math.cos(lat1_rad) * math.cos(lat2_rad) *
             math.sin(delta_lon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return R * c

    def _find_best_node(self, scored_nodes: List[NodeScore]) -> Optional[NodeScore]:
        """Find the best node from scored list."""
        # Prefer nodes that can fulfill complete order
        complete_nodes = [n for n in scored_nodes if n.can_fulfill_complete]
        if complete_nodes:
            return complete_nodes[0]  # Already sorted by score

        # Return highest scored node even if partial
        return scored_nodes[0] if scored_nodes else None

    async def _plan_order_split(
        self,
        order: Order,
        scored_nodes: List[NodeScore],
        availability: Dict[uuid.UUID, Dict[uuid.UUID, int]],
        rule: Optional[RoutingRule]
    ) -> List[SplitDecision]:
        """Plan how to split order across multiple nodes."""
        max_splits = rule.max_splits if rule else 3
        min_split_value = rule.min_split_value if rule else Decimal("100.00")

        splits: List[SplitDecision] = []
        remaining_items: Dict[uuid.UUID, int] = {
            item.id: item.quantity for item in order.items
        }
        item_prices: Dict[uuid.UUID, Decimal] = {
            item.id: item.unit_price for item in order.items
        }
        item_products: Dict[uuid.UUID, uuid.UUID] = {
            item.id: item.product_id for item in order.items
        }

        # Greedy allocation to nodes
        for node in scored_nodes:
            if len(splits) >= max_splits:
                break
            if not any(remaining_items.values()):
                break

            node_items: List[uuid.UUID] = []
            quantity_map: Dict[str, int] = {}
            split_subtotal = Decimal("0.00")

            for item_id, remaining_qty in list(remaining_items.items()):
                if remaining_qty <= 0:
                    continue

                product_id = item_products[item_id]
                node_avail = availability.get(product_id, {}).get(node.node_id, 0)

                if node_avail > 0:
                    allocate_qty = min(remaining_qty, node_avail)
                    remaining_items[item_id] -= allocate_qty
                    availability[product_id][node.node_id] -= allocate_qty

                    node_items.append(item_id)
                    quantity_map[str(product_id)] = allocate_qty
                    split_subtotal += item_prices[item_id] * allocate_qty

            if node_items and split_subtotal >= min_split_value:
                splits.append(SplitDecision(
                    node_id=node.node_id,
                    node_code=node.node_code,
                    item_ids=node_items,
                    quantity_map=quantity_map,
                    subtotal=split_subtotal,
                    estimated_shipping=Decimal("0.00")  # Would calculate from rate cards
                ))

        # Check if we fulfilled everything
        if any(remaining_items.values()):
            return []  # Can't fully fulfill even with splits

        return splits

    async def _execute_orchestration(
        self,
        order: Order,
        result: OrchestrationResult
    ) -> None:
        """Execute the orchestration decision."""
        if result.status == OrchestrationStatus.ROUTED:
            # Update order with assigned node
            if result.selected_node_id:
                # Get the warehouse_id from the node
                node = await self.get_fulfillment_node(result.selected_node_id)
                if node and node.warehouse_id:
                    order.warehouse_id = node.warehouse_id
                    order.status = OrderStatus.ALLOCATED.value

                # Increment node's daily order count
                if node:
                    node.current_day_orders += 1

        elif result.status == OrchestrationStatus.SPLIT:
            # Create child orders for each split
            for i, split in enumerate(result.splits):
                # In a real implementation, you would:
                # 1. Create a child order with the split items
                # 2. Record the split in order_splits table
                # 3. Update inventory allocations
                pass

            order.status = "SPLIT"  # Custom status for split orders

        elif result.status == OrchestrationStatus.BACKORDER:
            # Create backorder records
            for item in order.items:
                backorder = Backorder(
                    order_id=order.id,
                    order_item_id=item.id,
                    product_id=item.product_id,
                    variant_id=item.variant_id if hasattr(item, 'variant_id') else None,
                    quantity_ordered=item.quantity,
                    status=BackorderStatus.PENDING.value,
                    customer_consent=True,
                )
                self.db.add(backorder)
                result.backorder_items.append(item.id)

            order.status = "BACKORDER"  # Custom status

        await self.db.commit()

    async def _log_orchestration(self, result: OrchestrationResult) -> None:
        """Log orchestration decision."""
        log = OrchestrationLog(
            order_id=result.order_id,
            order_number=result.order_number,
            status=result.status.value,
            routing_rule_id=result.routing_rule_id,
            routing_rule_name=result.routing_rule_name,
            routing_strategy=result.routing_strategy,
            selected_node_id=result.selected_node_id,
            selected_node_code=result.selected_node_code,
            split_count=result.split_count,
            evaluated_nodes=[n.model_dump() for n in result.evaluated_nodes] if result.evaluated_nodes else None,
            decision_factors=result.decision_factors,
            failure_reason=result.failure_reason,
            processing_time_ms=result.processing_time_ms,
        )
        self.db.add(log)
        await self.db.commit()

    # ========================================================================
    # ATP/ATF CHECK
    # ========================================================================

    async def check_atp(self, request: ATPCheckRequest) -> ATPCheckResponse:
        """
        Check Available to Promise (ATP) for products.

        Used during checkout to verify inventory availability.
        """
        all_available = True
        items: List[ATPCheckItem] = []
        best_node_id = None
        best_node_code = None
        requires_split = False

        # Track which nodes can fulfill each item
        node_fulfillment: Dict[uuid.UUID, int] = {}  # node_id -> items it can fulfill

        for item_data in request.items:
            product_id = item_data.get('product_id')
            variant_id = item_data.get('variant_id')
            quantity = item_data.get('quantity', 1)

            # Get ATP across nodes
            query = select(
                InventorySummary.warehouse_id,
                InventorySummary.available_quantity
            ).where(
                InventorySummary.product_id == product_id,
                InventorySummary.available_quantity > 0
            )

            result = await self.db.execute(query)
            rows = result.all()

            total_atp = sum(r[1] for r in rows)
            is_available = total_atp >= quantity

            if not is_available:
                all_available = False

            # Get node details for available warehouses
            available_nodes = []
            for warehouse_id, qty in rows:
                node_result = await self.db.execute(
                    select(FulfillmentNode).where(
                        FulfillmentNode.warehouse_id == warehouse_id,
                        FulfillmentNode.is_active == True
                    )
                )
                node = node_result.scalar_one_or_none()
                if node:
                    available_nodes.append({
                        'node_id': node.id,
                        'node_code': node.node_code,
                        'atp': qty
                    })

                    # Track fulfillment capability
                    if qty >= quantity:
                        node_fulfillment[node.id] = node_fulfillment.get(node.id, 0) + 1

            items.append(ATPCheckItem(
                product_id=product_id,
                variant_id=variant_id,
                requested_quantity=quantity,
                total_atp=total_atp,
                is_available=is_available,
                available_nodes=available_nodes,
                best_node_id=available_nodes[0]['node_id'] if available_nodes else None,
                best_node_code=available_nodes[0]['node_code'] if available_nodes else None,
            ))

        # Find node that can fulfill all items
        total_items = len(request.items)
        for node_id, count in node_fulfillment.items():
            if count == total_items:
                # This node can fulfill all items
                node = await self.get_fulfillment_node(node_id)
                if node:
                    best_node_id = node_id
                    best_node_code = node.node_code
                    break

        if not best_node_id and all_available:
            requires_split = True

        return ATPCheckResponse(
            all_available=all_available,
            items=items,
            recommended_node_id=best_node_id,
            recommended_node_code=best_node_code,
            requires_split=requires_split,
        )

    # ========================================================================
    # BACKORDER MANAGEMENT
    # ========================================================================

    async def create_backorder(self, data: BackorderCreate) -> Backorder:
        """Create a backorder record."""
        backorder = Backorder(**data.model_dump())
        self.db.add(backorder)
        await self.db.commit()
        await self.db.refresh(backorder)
        return backorder

    async def get_backorders(
        self,
        status: Optional[str] = None,
        product_id: Optional[uuid.UUID] = None,
        order_id: Optional[uuid.UUID] = None,
        page: int = 1,
        size: int = 20,
    ) -> Tuple[List[Backorder], int]:
        """Get backorders with filters."""
        query = select(Backorder)

        if status:
            query = query.where(Backorder.status == status)
        if product_id:
            query = query.where(Backorder.product_id == product_id)
        if order_id:
            query = query.where(Backorder.order_id == order_id)

        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar() or 0

        query = query.order_by(Backorder.priority, Backorder.created_at)
        query = query.offset((page - 1) * size).limit(size)

        result = await self.db.execute(query)
        return list(result.scalars().all()), total

    async def allocate_to_backorders(
        self,
        product_id: uuid.UUID,
        variant_id: Optional[uuid.UUID],
        quantity: int
    ) -> Dict[str, Any]:
        """Allocate incoming inventory to backorders."""
        # Get pending backorders for this product, ordered by priority
        query = select(Backorder).where(
            Backorder.product_id == product_id,
            Backorder.status.in_([
                BackorderStatus.PENDING.value,
                BackorderStatus.PARTIALLY_AVAILABLE.value
            ])
        ).order_by(Backorder.priority, Backorder.created_at)

        result = await self.db.execute(query)
        backorders = list(result.scalars().all())

        remaining_qty = quantity
        allocations = []
        fulfilled = 0
        partial = 0

        for backorder in backorders:
            if remaining_qty <= 0:
                break

            needed = backorder.quantity_ordered - backorder.quantity_allocated
            allocate = min(needed, remaining_qty)

            backorder.quantity_available += allocate
            backorder.quantity_allocated += allocate
            remaining_qty -= allocate

            if backorder.quantity_allocated >= backorder.quantity_ordered:
                backorder.status = BackorderStatus.ALLOCATED.value
                backorder.allocated_at = datetime.now(timezone.utc)
                fulfilled += 1
            else:
                backorder.status = BackorderStatus.PARTIALLY_AVAILABLE.value
                partial += 1

            allocations.append({
                'backorder_id': str(backorder.id),
                'order_id': str(backorder.order_id),
                'allocated_quantity': allocate
            })

        await self.db.commit()

        return {
            'total_allocated': quantity - remaining_qty,
            'backorders_fulfilled': fulfilled,
            'backorders_partial': partial,
            'allocations': allocations
        }

    # ========================================================================
    # PREORDER MANAGEMENT
    # ========================================================================

    async def create_preorder(self, data: PreorderCreate) -> Preorder:
        """Create a pre-order."""
        # Generate preorder number
        today = date.today()
        count_result = await self.db.execute(
            select(func.count()).where(
                Preorder.created_at >= datetime.combine(today, datetime.min.time())
            )
        )
        count = (count_result.scalar() or 0) + 1
        preorder_number = f"PRE-{today.strftime('%Y%m%d')}-{count:04d}"

        # Calculate total and deposit
        total_amount = data.unit_price * data.quantity
        deposit_amount = Decimal("0.00")
        if data.deposit_required and data.deposit_percentage:
            deposit_amount = total_amount * Decimal(str(data.deposit_percentage / 100))

        # Get queue position
        queue_result = await self.db.execute(
            select(func.max(Preorder.queue_position)).where(
                Preorder.product_id == data.product_id,
                Preorder.status == PreorderStatus.ACTIVE.value
            )
        )
        queue_position = (queue_result.scalar() or 0) + 1

        preorder = Preorder(
            preorder_number=preorder_number,
            product_id=data.product_id,
            variant_id=data.variant_id,
            customer_id=data.customer_id,
            quantity=data.quantity,
            unit_price=data.unit_price,
            total_amount=total_amount,
            deposit_required=data.deposit_required,
            deposit_percentage=data.deposit_percentage,
            deposit_amount=deposit_amount,
            expected_release_date=data.expected_release_date,
            queue_position=queue_position,
            channel_id=data.channel_id,
            source=data.source,
        )
        self.db.add(preorder)
        await self.db.commit()
        await self.db.refresh(preorder)
        return preorder

    async def get_preorders(
        self,
        status: Optional[str] = None,
        product_id: Optional[uuid.UUID] = None,
        customer_id: Optional[uuid.UUID] = None,
        page: int = 1,
        size: int = 20,
    ) -> Tuple[List[Preorder], int]:
        """Get pre-orders with filters."""
        query = select(Preorder)

        if status:
            query = query.where(Preorder.status == status)
        if product_id:
            query = query.where(Preorder.product_id == product_id)
        if customer_id:
            query = query.where(Preorder.customer_id == customer_id)

        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.db.execute(count_query)).scalar() or 0

        query = query.order_by(Preorder.queue_position)
        query = query.offset((page - 1) * size).limit(size)

        result = await self.db.execute(query)
        return list(result.scalars().all()), total

    async def convert_preorder_to_order(
        self,
        preorder_id: uuid.UUID
    ) -> Optional[Dict[str, Any]]:
        """Convert pre-order to regular order."""
        preorder = await self.db.get(Preorder, preorder_id)
        if not preorder or preorder.status != PreorderStatus.ACTIVE.value:
            return None

        # In a real implementation, this would:
        # 1. Create a new Order with the pre-order details
        # 2. Apply deposit as payment
        # 3. Update pre-order status

        preorder.status = PreorderStatus.CONVERTED.value
        preorder.converted_at = datetime.now(timezone.utc)

        await self.db.commit()

        return {
            'preorder_id': str(preorder.id),
            'status': 'converted',
            'remaining_amount': preorder.total_amount - preorder.deposit_amount
        }

    # ========================================================================
    # STATS
    # ========================================================================

    async def get_stats(self) -> DOMStats:
        """Get DOM statistics."""
        # Node stats
        total_nodes = (await self.db.execute(
            select(func.count()).where(FulfillmentNode.id.isnot(None))
        )).scalar() or 0

        active_nodes = (await self.db.execute(
            select(func.count()).where(
                FulfillmentNode.is_active == True
            )
        )).scalar() or 0

        # Rule stats
        total_rules = (await self.db.execute(
            select(func.count()).where(RoutingRule.id.isnot(None))
        )).scalar() or 0

        active_rules = (await self.db.execute(
            select(func.count()).where(
                RoutingRule.is_active == True
            )
        )).scalar() or 0

        # Today's orchestration stats
        today = date.today()
        today_start = datetime.combine(today, datetime.min.time())

        orchestrated_today = (await self.db.execute(
            select(func.count()).where(
                OrchestrationLog.created_at >= today_start
            )
        )).scalar() or 0

        split_today = (await self.db.execute(
            select(func.count()).where(
                OrchestrationLog.created_at >= today_start,
                OrchestrationLog.status == OrchestrationStatus.SPLIT.value
            )
        )).scalar() or 0

        backorder_today = (await self.db.execute(
            select(func.count()).where(
                OrchestrationLog.created_at >= today_start,
                OrchestrationLog.status == OrchestrationStatus.BACKORDER.value
            )
        )).scalar() or 0

        avg_time_result = await self.db.execute(
            select(func.avg(OrchestrationLog.processing_time_ms)).where(
                OrchestrationLog.created_at >= today_start
            )
        )
        avg_time = avg_time_result.scalar() or 0.0

        # Pending counts
        pending_backorders = (await self.db.execute(
            select(func.count()).where(
                Backorder.status == BackorderStatus.PENDING.value
            )
        )).scalar() or 0

        pending_preorders = (await self.db.execute(
            select(func.count()).where(
                Preorder.status == PreorderStatus.ACTIVE.value
            )
        )).scalar() or 0

        # Success rate
        successful = (await self.db.execute(
            select(func.count()).where(
                OrchestrationLog.created_at >= today_start,
                OrchestrationLog.status.in_([
                    OrchestrationStatus.ROUTED.value,
                    OrchestrationStatus.SPLIT.value
                ])
            )
        )).scalar() or 0

        success_rate = (successful / orchestrated_today * 100) if orchestrated_today > 0 else 100.0
        split_rate = (split_today / orchestrated_today * 100) if orchestrated_today > 0 else 0.0

        return DOMStats(
            total_fulfillment_nodes=total_nodes,
            active_fulfillment_nodes=active_nodes,
            total_routing_rules=total_rules,
            active_routing_rules=active_rules,
            orders_orchestrated_today=orchestrated_today,
            orders_split_today=split_today,
            orders_backordered_today=backorder_today,
            average_orchestration_time_ms=float(avg_time),
            pending_backorders=pending_backorders,
            pending_preorders=pending_preorders,
            orchestration_success_rate=success_rate,
            split_rate=split_rate,
        )
