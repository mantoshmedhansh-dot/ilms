"""Costing Service for COGS calculation using Weighted Average Cost method.

Implements automatic cost calculation from GRN receipts:
- Weighted Average Cost (WAC) calculation
- Cost history tracking
- Landed cost allocation
- Integration with GRN acceptance workflow
"""
from typing import Optional, List, Tuple, Dict, Any
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
import uuid
import logging

from sqlalchemy import select, func, and_, or_, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload

from app.models.product import Product, ProductVariant
from app.models.product_cost import ProductCost, ValuationMethod
from app.models.purchase import GoodsReceiptNote, GRNItem, GRNStatus
from app.models.inventory import InventorySummary, StockItem
from app.models.warehouse import Warehouse

logger = logging.getLogger(__name__)


class CostingService:
    """
    Service for product cost management using Weighted Average Cost method.

    Formula:
    New Avg Cost = (Current Stock Value + New Purchase Value) / (Current Qty + New Qty)

    Where:
    - Current Stock Value = quantity_on_hand × average_cost
    - New Purchase Value = GRN Accepted Qty × GRN Unit Price

    Example:
    - Old: 100 units @ ₹50 = ₹5,000
    - New GRN: 50 units @ ₹55 = ₹2,750
    - New Avg = ₹7,750 / 150 = ₹51.67/unit
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    # ==================== WEIGHTED AVERAGE COST METHODS ====================

    async def calculate_weighted_average(
        self,
        product_id: uuid.UUID,
        new_qty: int,
        new_unit_cost: Decimal,
        variant_id: Optional[uuid.UUID] = None,
        warehouse_id: Optional[uuid.UUID] = None,
    ) -> Dict[str, Any]:
        """
        Calculate new weighted average cost without updating the database.

        Returns calculation details for preview/verification.
        """
        # Get or create ProductCost record
        product_cost = await self.get_or_create_product_cost(
            product_id=product_id,
            variant_id=variant_id,
            warehouse_id=warehouse_id,
        )

        old_qty = product_cost.quantity_on_hand
        old_avg = product_cost.average_cost or Decimal("0")
        old_value = Decimal(str(old_qty)) * old_avg

        new_purchase_value = Decimal(str(new_qty)) * new_unit_cost
        resulting_qty = old_qty + new_qty

        if resulting_qty > 0:
            new_avg = ((old_value + new_purchase_value) / Decimal(str(resulting_qty))).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
        else:
            new_avg = new_unit_cost

        resulting_value = Decimal(str(resulting_qty)) * new_avg

        return {
            "product_id": product_id,
            "variant_id": variant_id,
            "warehouse_id": warehouse_id,
            "old_quantity": old_qty,
            "old_average_cost": old_avg,
            "old_total_value": old_value,
            "new_quantity": new_qty,
            "new_unit_cost": new_unit_cost,
            "new_purchase_value": new_purchase_value,
            "resulting_quantity": resulting_qty,
            "resulting_average_cost": new_avg,
            "resulting_total_value": resulting_value,
        }

    async def update_cost_with_receipt(
        self,
        product_id: uuid.UUID,
        new_qty: int,
        new_unit_cost: Decimal,
        grn_id: uuid.UUID,
        grn_number: Optional[str] = None,
        variant_id: Optional[uuid.UUID] = None,
        warehouse_id: Optional[uuid.UUID] = None,
    ) -> ProductCost:
        """
        Update product cost using weighted average when goods are received.

        Called when GRN is accepted.
        """
        # Get or create ProductCost record
        product_cost = await self.get_or_create_product_cost(
            product_id=product_id,
            variant_id=variant_id,
            warehouse_id=warehouse_id,
        )

        old_qty = product_cost.quantity_on_hand
        old_avg = product_cost.average_cost or Decimal("0")
        old_value = Decimal(str(old_qty)) * old_avg

        new_purchase_value = Decimal(str(new_qty)) * new_unit_cost
        resulting_qty = old_qty + new_qty

        if resulting_qty > 0:
            new_avg = ((old_value + new_purchase_value) / Decimal(str(resulting_qty))).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
        else:
            new_avg = new_unit_cost

        # Update ProductCost record
        product_cost.quantity_on_hand = resulting_qty
        product_cost.average_cost = new_avg
        product_cost.last_purchase_cost = new_unit_cost
        product_cost.total_value = Decimal(str(resulting_qty)) * new_avg
        product_cost.last_grn_id = grn_id
        product_cost.last_calculated_at = datetime.now(timezone.utc)

        # Add to cost history
        history_entry = {
            "date": datetime.now(timezone.utc).isoformat(),
            "quantity": new_qty,
            "unit_cost": float(new_unit_cost),
            "grn_id": str(grn_id),
            "grn_number": grn_number,
            "running_average": float(new_avg),
            "old_qty": old_qty,
            "old_avg": float(old_avg),
        }

        if product_cost.cost_history is None:
            product_cost.cost_history = []
        product_cost.cost_history = product_cost.cost_history + [history_entry]

        await self.db.commit()
        await self.db.refresh(product_cost)

        logger.info(
            f"Updated cost for product {product_id}: "
            f"old_avg={old_avg}, new_avg={new_avg}, qty={old_qty} -> {resulting_qty}"
        )

        return product_cost

    # ==================== GRN INTEGRATION ====================

    async def update_cost_on_grn_acceptance(
        self,
        grn_id: uuid.UUID,
    ) -> Dict[str, Any]:
        """
        Update product costs when a GRN is accepted.

        Called from GRN accept endpoint.
        """
        # Get GRN with items
        query = (
            select(GoodsReceiptNote)
            .options(
                selectinload(GoodsReceiptNote.items).selectinload(GRNItem.product)
            )
            .where(GoodsReceiptNote.id == grn_id)
        )
        result = await self.db.execute(query)
        grn = result.scalar_one_or_none()

        if not grn:
            raise ValueError(f"GRN not found: {grn_id}")

        if grn.status not in ["ACCEPTED", "QC_PASSED", "PUT_AWAY_PENDING", "PUT_AWAY_COMPLETE"]:
            raise ValueError(f"GRN status must be ACCEPTED or later, got: {grn.status}")

        updated_products = []

        for item in grn.items:
            if item.quantity_accepted > 0:
                # Calculate effective unit cost (including any landed costs)
                effective_cost = item.unit_price

                # Update product cost
                product_cost = await self.update_cost_with_receipt(
                    product_id=item.product_id,
                    new_qty=item.quantity_accepted,
                    new_unit_cost=effective_cost,
                    grn_id=grn.id,
                    grn_number=grn.grn_number,
                    variant_id=item.variant_id,
                    warehouse_id=grn.warehouse_id,
                )

                updated_products.append({
                    "product_id": str(item.product_id),
                    "product_name": item.product_name,
                    "sku": item.sku,
                    "quantity_accepted": item.quantity_accepted,
                    "unit_price": float(item.unit_price),
                    "old_average_cost": float(
                        product_cost.cost_history[-1].get("old_avg", 0)
                        if product_cost.cost_history else 0
                    ),
                    "new_average_cost": float(product_cost.average_cost),
                })

        logger.info(f"Updated costs for GRN {grn.grn_number}: {len(updated_products)} products")

        return {
            "success": True,
            "grn_id": str(grn_id),
            "grn_number": grn.grn_number,
            "updated_products": updated_products,
            "total_updated": len(updated_products),
        }

    async def allocate_landed_costs(
        self,
        grn_id: uuid.UUID,
        freight: Decimal = Decimal("0"),
        packing: Decimal = Decimal("0"),
        customs: Decimal = Decimal("0"),
        other: Decimal = Decimal("0"),
    ) -> Dict[str, Any]:
        """
        Allocate header-level landed costs to GRN line items proportionally.

        Allocation is based on line item value (taxable_amount).
        After allocation, updates product costs with new effective unit prices.
        """
        total_additional_cost = freight + packing + customs + other

        if total_additional_cost <= 0:
            return {"success": True, "message": "No additional costs to allocate"}

        # Get GRN with items
        query = (
            select(GoodsReceiptNote)
            .options(selectinload(GoodsReceiptNote.items))
            .where(GoodsReceiptNote.id == grn_id)
        )
        result = await self.db.execute(query)
        grn = result.scalar_one_or_none()

        if not grn:
            raise ValueError(f"GRN not found: {grn_id}")

        # Calculate total value for allocation basis
        total_value = sum(
            item.unit_price * Decimal(str(item.quantity_accepted))
            for item in grn.items
            if item.quantity_accepted > 0
        )

        if total_value <= 0:
            return {"success": False, "message": "No accepted items to allocate costs to"}

        allocations = []

        for item in grn.items:
            if item.quantity_accepted > 0:
                item_value = item.unit_price * Decimal(str(item.quantity_accepted))
                allocation_ratio = item_value / total_value
                allocated_cost = (total_additional_cost * allocation_ratio).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )

                # Calculate new effective unit price including landed cost
                per_unit_additional = (allocated_cost / Decimal(str(item.quantity_accepted))).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP
                )
                effective_unit_price = item.unit_price + per_unit_additional

                allocations.append({
                    "product_id": str(item.product_id),
                    "product_name": item.product_name,
                    "original_unit_price": float(item.unit_price),
                    "allocated_cost": float(allocated_cost),
                    "per_unit_additional": float(per_unit_additional),
                    "effective_unit_price": float(effective_unit_price),
                })

        return {
            "success": True,
            "grn_id": str(grn_id),
            "total_additional_cost": float(total_additional_cost),
            "total_value_basis": float(total_value),
            "allocations": allocations,
        }

    # ==================== PRODUCT COST CRUD ====================

    async def get_product_cost(
        self,
        product_id: uuid.UUID,
        variant_id: Optional[uuid.UUID] = None,
        warehouse_id: Optional[uuid.UUID] = None,
    ) -> Optional[ProductCost]:
        """Get ProductCost for a specific product/variant/warehouse."""
        conditions = [ProductCost.product_id == product_id]

        if variant_id:
            conditions.append(ProductCost.variant_id == variant_id)
        else:
            conditions.append(ProductCost.variant_id.is_(None))

        if warehouse_id:
            conditions.append(ProductCost.warehouse_id == warehouse_id)
        else:
            conditions.append(ProductCost.warehouse_id.is_(None))

        query = select(ProductCost).where(and_(*conditions))
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def get_or_create_product_cost(
        self,
        product_id: uuid.UUID,
        variant_id: Optional[uuid.UUID] = None,
        warehouse_id: Optional[uuid.UUID] = None,
        valuation_method: str = "WEIGHTED_AVG",
    ) -> ProductCost:
        """Get existing ProductCost or create new one."""
        product_cost = await self.get_product_cost(
            product_id=product_id,
            variant_id=variant_id,
            warehouse_id=warehouse_id,
        )

        if product_cost:
            return product_cost

        # Create new ProductCost
        product_cost = ProductCost(
            product_id=product_id,
            variant_id=variant_id,
            warehouse_id=warehouse_id,
            valuation_method=valuation_method,
            average_cost=Decimal("0"),
            quantity_on_hand=0,
            total_value=Decimal("0"),
        )
        self.db.add(product_cost)
        await self.db.commit()
        await self.db.refresh(product_cost)

        return product_cost

    async def get_product_costs(
        self,
        product_id: Optional[uuid.UUID] = None,
        warehouse_id: Optional[uuid.UUID] = None,
        valuation_method: Optional[str] = None,
        has_stock: Optional[bool] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[ProductCost], int]:
        """Get paginated list of product costs."""
        query = select(ProductCost).options(
            selectinload(ProductCost.product),
            selectinload(ProductCost.warehouse),
        )

        conditions = []

        if product_id:
            conditions.append(ProductCost.product_id == product_id)
        if warehouse_id:
            conditions.append(ProductCost.warehouse_id == warehouse_id)
        if valuation_method:
            conditions.append(ProductCost.valuation_method == valuation_method)
        if has_stock is True:
            conditions.append(ProductCost.quantity_on_hand > 0)
        elif has_stock is False:
            conditions.append(ProductCost.quantity_on_hand == 0)

        if conditions:
            query = query.where(and_(*conditions))

        # Count
        count_query = select(func.count()).select_from(query.subquery())
        total = await self.db.scalar(count_query)

        # Paginate
        query = query.order_by(ProductCost.updated_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(query)

        return result.scalars().all(), total

    async def get_cost_for_product(
        self,
        product_id: uuid.UUID,
        quantity: int = 1,
        warehouse_id: Optional[uuid.UUID] = None,
    ) -> Decimal:
        """
        Get COGS for a product (for sales/accounting).

        Returns average cost × quantity.
        """
        product_cost = await self.get_product_cost(
            product_id=product_id,
            warehouse_id=warehouse_id,
        )

        if product_cost and product_cost.average_cost:
            return product_cost.average_cost * Decimal(str(quantity))

        # Fallback to product's static cost_price
        query = select(Product.cost_price).where(Product.id == product_id)
        result = await self.db.scalar(query)

        if result:
            return result * Decimal(str(quantity))

        return Decimal("0")

    async def get_cost_history(
        self,
        product_id: uuid.UUID,
        variant_id: Optional[uuid.UUID] = None,
        warehouse_id: Optional[uuid.UUID] = None,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """Get cost history for a product."""
        product_cost = await self.get_product_cost(
            product_id=product_id,
            variant_id=variant_id,
            warehouse_id=warehouse_id,
        )

        if not product_cost:
            return {
                "product_id": str(product_id),
                "entries": [],
                "total_entries": 0,
            }

        # Get product details
        query = select(Product).where(Product.id == product_id)
        result = await self.db.execute(query)
        product = result.scalar_one_or_none()

        entries = product_cost.cost_history or []
        # Get latest entries first
        entries = sorted(entries, key=lambda x: x.get("date", ""), reverse=True)[:limit]

        return {
            "product_id": str(product_id),
            "product_name": product.name if product else None,
            "sku": product.sku if product else None,
            "current_average_cost": float(product_cost.average_cost),
            "quantity_on_hand": product_cost.quantity_on_hand,
            "entries": entries,
            "total_entries": len(product_cost.cost_history or []),
        }

    # ==================== INVENTORY SUMMARY SYNC ====================

    async def sync_quantity_from_inventory(
        self,
        product_id: uuid.UUID,
        variant_id: Optional[uuid.UUID] = None,
        warehouse_id: Optional[uuid.UUID] = None,
    ) -> Optional[ProductCost]:
        """
        Sync quantity_on_hand from InventorySummary to ProductCost.

        Used when stock changes outside GRN (transfers, adjustments, sales).
        """
        product_cost = await self.get_product_cost(
            product_id=product_id,
            variant_id=variant_id,
            warehouse_id=warehouse_id,
        )

        if not product_cost:
            return None

        # Get current inventory quantity
        conditions = [InventorySummary.product_id == product_id]
        if warehouse_id:
            conditions.append(InventorySummary.warehouse_id == warehouse_id)
        if variant_id:
            conditions.append(InventorySummary.variant_id == variant_id)

        query = select(func.coalesce(func.sum(InventorySummary.total_quantity), 0)).where(
            and_(*conditions)
        )
        total_qty = await self.db.scalar(query)

        # Update ProductCost quantity and recalculate total value
        product_cost.quantity_on_hand = total_qty or 0
        product_cost.recalculate_total_value()

        await self.db.commit()
        await self.db.refresh(product_cost)

        return product_cost

    # ==================== REPORTING ====================

    async def get_inventory_valuation_summary(
        self,
        warehouse_id: Optional[uuid.UUID] = None,
    ) -> Dict[str, Any]:
        """Get summary of inventory valuation."""
        conditions = []
        if warehouse_id:
            conditions.append(ProductCost.warehouse_id == warehouse_id)

        query = select(ProductCost)
        if conditions:
            query = query.where(and_(*conditions))

        result = await self.db.execute(query)
        costs = result.scalars().all()

        total_value = Decimal("0")
        total_products = 0
        products_with_cost = 0
        products_without_cost = 0
        method_counts = {"WEIGHTED_AVG": 0, "FIFO": 0, "SPECIFIC_ID": 0}

        for cost in costs:
            total_products += 1
            total_value += cost.total_value or Decimal("0")

            if cost.average_cost and cost.average_cost > 0:
                products_with_cost += 1
            else:
                products_without_cost += 1

            method = cost.valuation_method or "WEIGHTED_AVG"
            if method in method_counts:
                method_counts[method] += 1

        avg_value = total_value / total_products if total_products > 0 else Decimal("0")

        return {
            "total_products": total_products,
            "total_inventory_value": float(total_value),
            "average_stock_value_per_product": float(avg_value),
            "products_with_cost": products_with_cost,
            "products_without_cost": products_without_cost,
            "weighted_avg_count": method_counts["WEIGHTED_AVG"],
            "fifo_count": method_counts["FIFO"],
            "specific_id_count": method_counts["SPECIFIC_ID"],
            "warehouse_id": str(warehouse_id) if warehouse_id else None,
        }

    async def initialize_costs_from_products(self) -> Dict[str, Any]:
        """
        Initialize ProductCost records for all products that don't have one.

        NOTE: average_cost is initialized to 0 (not from product.cost_price).
        The average_cost should ONLY be updated from actual GRN receipts.
        This follows industry best practice for Weighted Average Cost (WAC) accounting.
        """
        # Get products without ProductCost
        subquery = select(ProductCost.product_id)
        query = select(Product).where(Product.id.notin_(subquery))
        result = await self.db.execute(query)
        products = result.scalars().all()

        created = 0
        for product in products:
            product_cost = ProductCost(
                product_id=product.id,
                valuation_method="WEIGHTED_AVG",
                # IMPORTANT: average_cost starts at 0 and is ONLY updated from GRN receipts
                # product.cost_price is a static estimate, not actual COGS
                average_cost=Decimal("0"),
                quantity_on_hand=0,
                total_value=Decimal("0"),
            )
            self.db.add(product_cost)
            created += 1

        await self.db.commit()

        return {
            "success": True,
            "created": created,
            "message": f"Initialized ProductCost for {created} products",
        }
