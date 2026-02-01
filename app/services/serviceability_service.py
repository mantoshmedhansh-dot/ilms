"""
Serviceability Service.

Handles:
1. Checking if a pincode is serviceable
2. Finding available warehouses for a pincode
3. Finding available transporters for the route
4. Final serviceability = Warehouse pincodes ∩ Transporter pincodes
"""
import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.serviceability import WarehouseServiceability, AllocationRule, ChannelCode
from app.models.transporter import Transporter, TransporterServiceability
from app.models.warehouse import Warehouse
from app.models.inventory import InventorySummary, StockItem, StockItemStatus
from app.models.product import Product
from app.schemas.serviceability import (
    ServiceabilityCheckRequest,
    ServiceabilityCheckResponse,
    WarehouseCandidate,
    TransporterOption,
    WarehouseServiceabilityCreate,
    WarehouseServiceabilityBulkCreate,
    WarehouseServiceabilityResponse,
    BulkPincodeUploadRequest,
    BulkPincodeUploadResponse,
    ServiceabilityDashboard,
)


class ServiceabilityService:
    """Service for checking pincode serviceability."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def check_serviceability(
        self,
        request: ServiceabilityCheckRequest
    ) -> ServiceabilityCheckResponse:
        """
        Check if a pincode is serviceable.

        Three-tier check:
        1. Find warehouses that serve this pincode
        2. Find transporters that can deliver to this pincode
        3. Final serviceability = warehouses with valid transporter routes

        Returns warehouse and transporter options.
        """
        pincode = request.pincode

        # 1. Find warehouses serving this pincode
        warehouse_query = (
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
        ws_result = await self.db.execute(warehouse_query)
        warehouse_serviceability = ws_result.scalars().all()

        if not warehouse_serviceability:
            return ServiceabilityCheckResponse(
                pincode=pincode,
                is_serviceable=False,
                message="Location not serviceable - no warehouse covers this pincode",
                cod_available=False,
                prepaid_available=False
            )

        # 2. Get warehouse details and check stock if products specified
        warehouse_candidates: List[WarehouseCandidate] = []
        overall_cod = False
        overall_prepaid = False
        min_days = None
        min_cost = None

        for ws in warehouse_serviceability:
            wh = ws.warehouse

            # Check stock availability if products specified
            stock_available = None
            available_qty = None

            import logging
            logger = logging.getLogger(__name__)

            if request.product_ids:
                logger.info(f"Serviceability: Checking stock for warehouse {wh.id} ({wh.code}), products: {request.product_ids}")
                stock_available, available_qty = await self._check_stock_availability(
                    wh.id,
                    request.product_ids
                )
                logger.info(f"Serviceability: Stock check result - available={stock_available}, qty={available_qty}")

            candidate = WarehouseCandidate(
                warehouse_id=wh.id,
                warehouse_code=wh.code,
                warehouse_name=wh.name,
                city=wh.city,
                estimated_days=ws.estimated_days,
                shipping_cost=ws.shipping_cost,
                priority=ws.priority,
                cod_available=ws.cod_available,
                prepaid_available=ws.prepaid_available,
                stock_available=stock_available,
                available_quantity=available_qty
            )
            warehouse_candidates.append(candidate)

            # Track overall availability
            if ws.cod_available:
                overall_cod = True
            if ws.prepaid_available:
                overall_prepaid = True
            if ws.estimated_days:
                if min_days is None or ws.estimated_days < min_days:
                    min_days = ws.estimated_days
            if ws.shipping_cost:
                if min_cost is None or ws.shipping_cost < min_cost:
                    min_cost = ws.shipping_cost

        # 3. Find transporters for these warehouse-pincode routes
        transporter_options = await self._find_transporters(
            warehouse_candidates,
            pincode,
            request.payment_mode
        )

        # Filter by payment mode if specified
        if request.payment_mode == "COD":
            warehouse_candidates = [w for w in warehouse_candidates if w.cod_available]
            overall_cod = len(warehouse_candidates) > 0
        elif request.payment_mode == "PREPAID":
            warehouse_candidates = [w for w in warehouse_candidates if w.prepaid_available]
            overall_prepaid = len(warehouse_candidates) > 0

        # Final serviceability
        is_serviceable = len(warehouse_candidates) > 0

        # Check stock availability for final response
        stock_available = None
        if request.product_ids and warehouse_candidates:
            stock_available = any(w.stock_available for w in warehouse_candidates if w.stock_available is not None)

        return ServiceabilityCheckResponse(
            pincode=pincode,
            is_serviceable=is_serviceable,
            message="Location is serviceable" if is_serviceable else "Location not serviceable",
            cod_available=overall_cod,
            prepaid_available=overall_prepaid,
            estimated_delivery_days=min_days,
            minimum_shipping_cost=min_cost,
            warehouse_options=warehouse_candidates,
            transporter_options=transporter_options,
            stock_available=stock_available
        )

    async def _check_stock_availability(
        self,
        warehouse_id: uuid.UUID,
        product_ids: List[uuid.UUID]
    ) -> tuple:
        """Check if products are available in warehouse."""
        import logging
        logger = logging.getLogger(__name__)

        logger.info(f"_check_stock_availability: warehouse_id={warehouse_id}, product_ids={product_ids}")

        # Check inventory summary
        query = select(InventorySummary).where(
            and_(
                InventorySummary.warehouse_id == warehouse_id,
                InventorySummary.product_id.in_(product_ids)
            )
        )
        result = await self.db.execute(query)
        summaries = result.scalars().all()

        logger.info(f"_check_stock_availability: Found {len(summaries)} inventory records")
        for s in summaries:
            logger.info(f"  - product_id={s.product_id}, available_quantity={s.available_quantity}")

        if not summaries:
            logger.warning(f"_check_stock_availability: NO inventory found for warehouse_id={warehouse_id}, product_ids={product_ids}")
            return False, 0

        total_available = sum(s.available_quantity for s in summaries)
        all_available = all(s.available_quantity > 0 for s in summaries)

        logger.info(f"_check_stock_availability: total_available={total_available}, all_available={all_available}")
        return all_available, total_available

    async def _find_transporters(
        self,
        warehouse_candidates: List[WarehouseCandidate],
        destination_pincode: str,
        payment_mode: Optional[str] = None
    ) -> List[TransporterOption]:
        """Find transporters that can deliver to destination pincode."""
        if not warehouse_candidates:
            return []

        # Get warehouse pincodes for origin
        warehouse_ids = [w.warehouse_id for w in warehouse_candidates]

        # Get warehouse details for origin pincodes
        wh_query = select(Warehouse).where(Warehouse.id.in_(warehouse_ids))
        wh_result = await self.db.execute(wh_query)
        warehouses = {wh.id: wh for wh in wh_result.scalars().all()}

        origin_pincodes = list(set(wh.pincode for wh in warehouses.values() if wh.pincode))

        if not origin_pincodes:
            return []

        # Find transporters with routes from any origin to destination
        ts_query = (
            select(TransporterServiceability)
            .join(Transporter)
            .where(
                and_(
                    TransporterServiceability.origin_pincode.in_(origin_pincodes),
                    TransporterServiceability.destination_pincode == destination_pincode,
                    TransporterServiceability.is_serviceable == True,
                    Transporter.is_active == True
                )
            )
            .options(selectinload(TransporterServiceability.transporter))
            .order_by(TransporterServiceability.rate)
        )
        ts_result = await self.db.execute(ts_query)
        transporter_serviceability = ts_result.scalars().all()

        # Build transporter options (deduplicate by transporter)
        seen_transporters = set()
        options: List[TransporterOption] = []

        for ts in transporter_serviceability:
            if ts.transporter_id in seen_transporters:
                continue
            seen_transporters.add(ts.transporter_id)

            transporter = ts.transporter

            # Filter by payment mode
            if payment_mode == "COD" and not ts.cod_available:
                continue
            if payment_mode == "PREPAID" and not ts.prepaid_available:
                continue

            options.append(TransporterOption(
                transporter_id=transporter.id,
                transporter_code=transporter.code,
                transporter_name=transporter.name,
                estimated_days=ts.estimated_days,
                shipping_cost=ts.rate,
                cod_available=ts.cod_available,
                prepaid_available=ts.prepaid_available,
                express_available=ts.express_available
            ))

        return options

    # ==================== CRUD Operations ====================

    async def create_warehouse_serviceability(
        self,
        data: WarehouseServiceabilityCreate
    ) -> WarehouseServiceability:
        """Create a single warehouse-pincode mapping."""
        ws = WarehouseServiceability(
            warehouse_id=data.warehouse_id,
            pincode=data.pincode,
            is_serviceable=data.is_serviceable,
            cod_available=data.cod_available,
            prepaid_available=data.prepaid_available,
            estimated_days=data.estimated_days,
            priority=data.priority,
            shipping_cost=data.shipping_cost,
            city=data.city,
            state=data.state,
            zone=data.zone,
            is_active=data.is_active
        )
        self.db.add(ws)
        await self.db.commit()
        await self.db.refresh(ws)
        return ws

    async def bulk_create_warehouse_serviceability(
        self,
        data: WarehouseServiceabilityBulkCreate
    ) -> List[WarehouseServiceability]:
        """Bulk create warehouse-pincode mappings."""
        created = []
        for pincode in data.pincodes:
            ws = WarehouseServiceability(
                warehouse_id=data.warehouse_id,
                pincode=pincode,
                is_serviceable=True,
                cod_available=data.cod_available,
                prepaid_available=data.prepaid_available,
                estimated_days=data.estimated_days,
                zone=data.zone,
                is_active=True
            )
            self.db.add(ws)
            created.append(ws)

        await self.db.commit()
        return created

    async def upload_pincodes_bulk(
        self,
        data: BulkPincodeUploadRequest
    ) -> BulkPincodeUploadResponse:
        """Upload pincodes in bulk with detailed response."""
        successful = 0
        failed = 0
        errors = []

        for item in data.pincodes:
            try:
                pincode = item.get("pincode", "")
                if not pincode or len(pincode) != 6:
                    errors.append({"pincode": pincode, "error": "Invalid pincode format"})
                    failed += 1
                    continue

                # Check if already exists
                existing = await self.db.execute(
                    select(WarehouseServiceability).where(
                        and_(
                            WarehouseServiceability.warehouse_id == data.warehouse_id,
                            WarehouseServiceability.pincode == pincode
                        )
                    )
                )
                if existing.scalar_one_or_none():
                    errors.append({"pincode": pincode, "error": "Already exists"})
                    failed += 1
                    continue

                ws = WarehouseServiceability(
                    warehouse_id=data.warehouse_id,
                    pincode=pincode,
                    is_serviceable=True,
                    cod_available=data.default_cod_available,
                    prepaid_available=True,
                    estimated_days=data.default_estimated_days,
                    city=item.get("city"),
                    state=item.get("state"),
                    zone=item.get("zone"),
                    is_active=True
                )
                self.db.add(ws)
                successful += 1
            except Exception as e:
                errors.append({"pincode": item.get("pincode", ""), "error": str(e)})
                failed += 1

        await self.db.commit()

        return BulkPincodeUploadResponse(
            warehouse_id=data.warehouse_id,
            total_uploaded=len(data.pincodes),
            successful=successful,
            failed=failed,
            errors=errors[:50]  # Limit errors to 50
        )

    async def get_warehouse_serviceability(
        self,
        warehouse_id: Optional[uuid.UUID] = None,
        pincode: Optional[str] = None,
        is_active: bool = True,
        skip: int = 0,
        limit: int = 100
    ) -> tuple:
        """Get warehouse serviceability with filters."""
        query = (
            select(WarehouseServiceability)
            .options(selectinload(WarehouseServiceability.warehouse))
        )

        conditions = []
        if warehouse_id:
            conditions.append(WarehouseServiceability.warehouse_id == warehouse_id)
        if pincode:
            conditions.append(WarehouseServiceability.pincode == pincode)
        if is_active is not None:
            conditions.append(WarehouseServiceability.is_active == is_active)

        if conditions:
            query = query.where(and_(*conditions))

        # Count
        count_query = select(func.count()).select_from(WarehouseServiceability)
        if conditions:
            count_query = count_query.where(and_(*conditions))
        count_result = await self.db.execute(count_query)
        total = count_result.scalar()

        # Paginate
        query = query.order_by(WarehouseServiceability.pincode).offset(skip).limit(limit)
        result = await self.db.execute(query)
        items = result.scalars().all()

        return items, total

    async def delete_warehouse_serviceability(
        self,
        warehouse_id: uuid.UUID,
        pincode: str
    ) -> bool:
        """Delete a warehouse-pincode mapping."""
        query = select(WarehouseServiceability).where(
            and_(
                WarehouseServiceability.warehouse_id == warehouse_id,
                WarehouseServiceability.pincode == pincode
            )
        )
        result = await self.db.execute(query)
        ws = result.scalar_one_or_none()

        if ws:
            await self.db.delete(ws)
            await self.db.commit()
            return True
        return False

    # ==================== Dashboard ====================

    async def get_dashboard(self) -> ServiceabilityDashboard:
        """Get serviceability dashboard stats."""
        # Total warehouses with serviceability
        wh_query = select(func.count(func.distinct(WarehouseServiceability.warehouse_id))).where(
            WarehouseServiceability.is_active == True
        )
        wh_result = await self.db.execute(wh_query)
        total_warehouses = wh_result.scalar() or 0

        # Total unique pincodes
        pin_query = select(func.count(func.distinct(WarehouseServiceability.pincode))).where(
            WarehouseServiceability.is_active == True
        )
        pin_result = await self.db.execute(pin_query)
        total_pincodes = pin_result.scalar() or 0

        # Total allocation rules
        rule_query = select(func.count(AllocationRule.id)).where(AllocationRule.is_active == True)
        rule_result = await self.db.execute(rule_query)
        total_rules = rule_result.scalar() or 0

        # Pincodes per warehouse
        coverage_query = (
            select(
                Warehouse.code,
                Warehouse.name,
                func.count(WarehouseServiceability.id).label("pincode_count")
            )
            .join(WarehouseServiceability)
            .where(WarehouseServiceability.is_active == True)
            .group_by(Warehouse.id, Warehouse.code, Warehouse.name)
        )
        coverage_result = await self.db.execute(coverage_query)
        warehouse_coverage = [
            {"code": r[0], "name": r[1], "pincodes": r[2]}
            for r in coverage_result.all()
        ]

        # Zone distribution
        zone_query = (
            select(
                WarehouseServiceability.zone,
                func.count(WarehouseServiceability.id)
            )
            .where(
                and_(
                    WarehouseServiceability.is_active == True,
                    WarehouseServiceability.zone.isnot(None)
                )
            )
            .group_by(WarehouseServiceability.zone)
        )
        zone_result = await self.db.execute(zone_query)
        zone_coverage = {r[0]: r[1] for r in zone_result.all()}

        return ServiceabilityDashboard(
            total_warehouses=total_warehouses,
            total_pincodes_covered=total_pincodes,
            total_allocation_rules=total_rules,
            warehouse_coverage=warehouse_coverage,
            zone_coverage=zone_coverage,
            recent_allocations=0,  # Will be populated by allocation service
            successful_allocations=0,
            failed_allocations=0,
            allocation_success_rate=0.0
        )
