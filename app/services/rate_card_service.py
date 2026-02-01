"""Service for managing rate cards across D2C, B2B, and FTL segments."""
from typing import List, Optional, Tuple
from datetime import datetime, date
from decimal import Decimal
import uuid

from sqlalchemy import select, func, and_, or_, delete
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rate_card import (
    D2CRateCard, D2CWeightSlab, D2CSurcharge, ZoneMapping,
    B2BRateCard, B2BRateSlab, B2BAdditionalCharge,
    FTLRateCard, FTLLaneRate, FTLAdditionalCharge, FTLVehicleType,
    CarrierPerformance, ServiceType, B2BServiceType, FTLRateType,
)
from app.models.transporter import Transporter
from app.schemas.rate_card import (
    D2CRateCardCreate, D2CRateCardUpdate,
    D2CWeightSlabCreate, D2CSurchargeCreate,
    ZoneMappingCreate, ZoneLookupRequest,
    B2BRateCardCreate, B2BRateCardUpdate,
    B2BRateSlabCreate, B2BAdditionalChargeCreate,
    FTLRateCardCreate, FTLRateCardUpdate,
    FTLLaneRateCreate, FTLAdditionalChargeCreate,
    FTLVehicleTypeCreate, FTLVehicleTypeUpdate,
)


class RateCardService:
    """Service for rate card management across all logistics segments."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ============================================
    # D2C RATE CARD CRUD
    # ============================================

    async def get_d2c_rate_card(
        self,
        rate_card_id: uuid.UUID,
        include_details: bool = False
    ) -> Optional[D2CRateCard]:
        """Get D2C rate card by ID."""
        stmt = select(D2CRateCard).where(D2CRateCard.id == rate_card_id)

        if include_details:
            stmt = stmt.options(
                selectinload(D2CRateCard.weight_slabs),
                selectinload(D2CRateCard.surcharges),
                joinedload(D2CRateCard.transporter),
            )
        else:
            stmt = stmt.options(joinedload(D2CRateCard.transporter))

        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_d2c_rate_card_by_code(
        self,
        code: str,
        transporter_id: Optional[uuid.UUID] = None
    ) -> Optional[D2CRateCard]:
        """Get D2C rate card by code."""
        stmt = select(D2CRateCard).where(D2CRateCard.code == code)
        if transporter_id:
            stmt = stmt.where(D2CRateCard.transporter_id == transporter_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_d2c_rate_cards(
        self,
        transporter_id: Optional[uuid.UUID] = None,
        service_type: Optional[ServiceType] = None,
        is_active: Optional[bool] = True,
        effective_date: Optional[date] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> Tuple[List[D2CRateCard], int]:
        """List D2C rate cards with filters and pagination."""
        stmt = (
            select(D2CRateCard)
            .options(joinedload(D2CRateCard.transporter))
            .order_by(D2CRateCard.created_at.desc())
        )

        filters = []
        if transporter_id:
            filters.append(D2CRateCard.transporter_id == transporter_id)
        if service_type:
            filters.append(D2CRateCard.service_type == service_type)
        if is_active is not None:
            filters.append(D2CRateCard.is_active == is_active)
        if effective_date:
            filters.append(D2CRateCard.effective_from <= effective_date)
            filters.append(
                or_(
                    D2CRateCard.effective_to.is_(None),
                    D2CRateCard.effective_to >= effective_date
                )
            )

        if filters:
            stmt = stmt.where(and_(*filters))

        # Count query
        count_stmt = select(func.count(D2CRateCard.id))
        if filters:
            count_stmt = count_stmt.where(and_(*filters))
        total = (await self.db.execute(count_stmt)).scalar() or 0

        # Paginate
        stmt = stmt.offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        items = list(result.scalars().unique().all())

        return items, total

    async def create_d2c_rate_card(
        self,
        data: D2CRateCardCreate,
        created_by: Optional[uuid.UUID] = None
    ) -> D2CRateCard:
        """Create new D2C rate card with optional weight slabs and surcharges."""
        # Verify transporter exists
        transporter = await self.db.get(Transporter, data.transporter_id)
        if not transporter:
            raise ValueError(f"Transporter {data.transporter_id} not found")

        # Check for duplicate code
        existing = await self.get_d2c_rate_card_by_code(
            data.code, data.transporter_id
        )
        if existing:
            raise ValueError(
                f"Rate card with code {data.code} already exists for this transporter"
            )

        # Create rate card
        rate_card_data = data.model_dump(exclude={"weight_slabs", "surcharges"})
        rate_card_data["created_by"] = created_by
        rate_card = D2CRateCard(**rate_card_data)

        # Add weight slabs if provided
        if data.weight_slabs:
            for slab_data in data.weight_slabs:
                slab = D2CWeightSlab(**slab_data.model_dump())
                rate_card.weight_slabs.append(slab)

        # Add surcharges if provided
        if data.surcharges:
            for surcharge_data in data.surcharges:
                surcharge = D2CSurcharge(**surcharge_data.model_dump())
                rate_card.surcharges.append(surcharge)

        self.db.add(rate_card)
        await self.db.commit()
        await self.db.refresh(rate_card)

        # Reload with relationships
        return await self.get_d2c_rate_card(rate_card.id, include_details=True)

    async def update_d2c_rate_card(
        self,
        rate_card_id: uuid.UUID,
        data: D2CRateCardUpdate
    ) -> D2CRateCard:
        """Update D2C rate card."""
        rate_card = await self.get_d2c_rate_card(rate_card_id)
        if not rate_card:
            raise ValueError("Rate card not found")

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(rate_card, key, value)

        await self.db.commit()
        await self.db.refresh(rate_card)
        return rate_card

    async def delete_d2c_rate_card(
        self,
        rate_card_id: uuid.UUID,
        hard_delete: bool = False
    ) -> bool:
        """Delete D2C rate card (soft or hard delete)."""
        rate_card = await self.get_d2c_rate_card(rate_card_id)
        if not rate_card:
            raise ValueError("Rate card not found")

        if hard_delete:
            await self.db.delete(rate_card)
        else:
            rate_card.is_active = False

        await self.db.commit()
        return True

    # ============================================
    # D2C WEIGHT SLAB OPERATIONS
    # ============================================

    async def add_d2c_weight_slab(
        self,
        rate_card_id: uuid.UUID,
        data: D2CWeightSlabCreate
    ) -> D2CWeightSlab:
        """Add weight slab to D2C rate card."""
        rate_card = await self.get_d2c_rate_card(rate_card_id)
        if not rate_card:
            raise ValueError("Rate card not found")

        # Check for duplicate slab
        stmt = select(D2CWeightSlab).where(
            D2CWeightSlab.rate_card_id == rate_card_id,
            D2CWeightSlab.zone == data.zone,
            D2CWeightSlab.min_weight_kg == data.min_weight_kg
        )
        existing = (await self.db.execute(stmt)).scalar_one_or_none()
        if existing:
            raise ValueError(
                f"Weight slab for zone {data.zone} "
                f"starting at {data.min_weight_kg}kg already exists"
            )

        slab = D2CWeightSlab(rate_card_id=rate_card_id, **data.model_dump())
        self.db.add(slab)
        await self.db.commit()
        await self.db.refresh(slab)
        return slab

    async def bulk_add_d2c_weight_slabs(
        self,
        rate_card_id: uuid.UUID,
        slabs: List[D2CWeightSlabCreate],
        replace_existing: bool = False
    ) -> int:
        """Bulk add weight slabs to D2C rate card."""
        rate_card = await self.get_d2c_rate_card(rate_card_id)
        if not rate_card:
            raise ValueError("Rate card not found")

        if replace_existing:
            # Delete existing slabs
            await self.db.execute(
                delete(D2CWeightSlab).where(
                    D2CWeightSlab.rate_card_id == rate_card_id
                )
            )

        count = 0
        for slab_data in slabs:
            slab = D2CWeightSlab(rate_card_id=rate_card_id, **slab_data.model_dump())
            self.db.add(slab)
            count += 1

        await self.db.commit()
        return count

    async def delete_d2c_weight_slab(self, slab_id: uuid.UUID) -> bool:
        """Delete a weight slab."""
        slab = await self.db.get(D2CWeightSlab, slab_id)
        if not slab:
            raise ValueError("Weight slab not found")

        await self.db.delete(slab)
        await self.db.commit()
        return True

    # ============================================
    # D2C SURCHARGE OPERATIONS
    # ============================================

    async def add_d2c_surcharge(
        self,
        rate_card_id: uuid.UUID,
        data: D2CSurchargeCreate
    ) -> D2CSurcharge:
        """Add surcharge to D2C rate card."""
        rate_card = await self.get_d2c_rate_card(rate_card_id)
        if not rate_card:
            raise ValueError("Rate card not found")

        # Check for duplicate
        stmt = select(D2CSurcharge).where(
            D2CSurcharge.rate_card_id == rate_card_id,
            D2CSurcharge.surcharge_type == data.surcharge_type,
            D2CSurcharge.zone == data.zone
        )
        existing = (await self.db.execute(stmt)).scalar_one_or_none()
        if existing:
            raise ValueError(
                f"Surcharge {data.surcharge_type} for zone {data.zone} already exists"
            )

        surcharge = D2CSurcharge(rate_card_id=rate_card_id, **data.model_dump())
        self.db.add(surcharge)
        await self.db.commit()
        await self.db.refresh(surcharge)
        return surcharge

    async def bulk_add_d2c_surcharges(
        self,
        rate_card_id: uuid.UUID,
        surcharges: List[D2CSurchargeCreate],
        replace_existing: bool = False
    ) -> int:
        """Bulk add surcharges to D2C rate card."""
        rate_card = await self.get_d2c_rate_card(rate_card_id)
        if not rate_card:
            raise ValueError("Rate card not found")

        if replace_existing:
            await self.db.execute(
                delete(D2CSurcharge).where(
                    D2CSurcharge.rate_card_id == rate_card_id
                )
            )

        count = 0
        for surcharge_data in surcharges:
            surcharge = D2CSurcharge(
                rate_card_id=rate_card_id,
                **surcharge_data.model_dump()
            )
            self.db.add(surcharge)
            count += 1

        await self.db.commit()
        return count

    async def delete_d2c_surcharge(self, surcharge_id: uuid.UUID) -> bool:
        """Delete a surcharge."""
        surcharge = await self.db.get(D2CSurcharge, surcharge_id)
        if not surcharge:
            raise ValueError("Surcharge not found")

        await self.db.delete(surcharge)
        await self.db.commit()
        return True

    # ============================================
    # ZONE MAPPING OPERATIONS
    # ============================================

    async def get_zone_mapping(
        self,
        origin_pincode: str,
        destination_pincode: str
    ) -> Optional[ZoneMapping]:
        """Get zone mapping for origin-destination pair."""
        stmt = select(ZoneMapping).where(
            ZoneMapping.origin_pincode == origin_pincode,
            ZoneMapping.destination_pincode == destination_pincode
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def lookup_zone(
        self,
        origin_pincode: str,
        destination_pincode: str
    ) -> dict:
        """Lookup zone for a delivery pair, with fallback logic."""
        # Try exact pincode match
        mapping = await self.get_zone_mapping(origin_pincode, destination_pincode)
        if mapping:
            return {
                "zone": mapping.zone,
                "distance_km": mapping.distance_km,
                "is_oda": mapping.is_oda,
                "found": True,
            }

        # Try state-level fallback (using pincode prefix for state)
        # First 2-3 digits of Indian pincodes indicate region
        origin_prefix = origin_pincode[:3]
        dest_prefix = destination_pincode[:3]

        stmt = select(ZoneMapping).where(
            or_(
                and_(
                    ZoneMapping.origin_pincode.startswith(origin_prefix),
                    ZoneMapping.destination_pincode.startswith(dest_prefix)
                ),
                and_(
                    ZoneMapping.origin_state.isnot(None),
                    ZoneMapping.destination_state.isnot(None)
                )
            )
        ).limit(1)

        result = await self.db.execute(stmt)
        fallback = result.scalar_one_or_none()

        if fallback:
            return {
                "zone": fallback.zone,
                "distance_km": fallback.distance_km,
                "is_oda": fallback.is_oda,
                "found": True,
            }

        # Default zone calculation based on pincode similarity
        if origin_pincode[:3] == destination_pincode[:3]:
            zone = "A"  # Same city/area
        elif origin_pincode[:2] == destination_pincode[:2]:
            zone = "B"  # Same region
        elif origin_pincode[0] == destination_pincode[0]:
            zone = "C"  # Same zone
        else:
            zone = "D"  # Different zone

        return {
            "zone": zone,
            "distance_km": None,
            "is_oda": False,
            "found": False,
        }

    async def list_zone_mappings(
        self,
        origin_state: Optional[str] = None,
        destination_state: Optional[str] = None,
        zone: Optional[str] = None,
        skip: int = 0,
        limit: int = 20
    ) -> Tuple[List[ZoneMapping], int]:
        """List zone mappings with filters."""
        stmt = select(ZoneMapping).order_by(ZoneMapping.origin_pincode)

        filters = []
        if origin_state:
            filters.append(ZoneMapping.origin_state == origin_state)
        if destination_state:
            filters.append(ZoneMapping.destination_state == destination_state)
        if zone:
            filters.append(ZoneMapping.zone == zone)

        if filters:
            stmt = stmt.where(and_(*filters))

        count_stmt = select(func.count(ZoneMapping.id))
        if filters:
            count_stmt = count_stmt.where(and_(*filters))
        total = (await self.db.execute(count_stmt)).scalar() or 0

        stmt = stmt.offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        items = list(result.scalars().all())

        return items, total

    async def create_zone_mapping(self, data: ZoneMappingCreate) -> ZoneMapping:
        """Create zone mapping."""
        # Check for duplicate
        if data.origin_pincode and data.destination_pincode:
            existing = await self.get_zone_mapping(
                data.origin_pincode, data.destination_pincode
            )
            if existing:
                raise ValueError("Zone mapping already exists for this route")

        mapping = ZoneMapping(**data.model_dump())
        self.db.add(mapping)
        await self.db.commit()
        await self.db.refresh(mapping)
        return mapping

    async def bulk_create_zone_mappings(
        self,
        mappings: List[ZoneMappingCreate],
        skip_duplicates: bool = True
    ) -> int:
        """Bulk create zone mappings."""
        count = 0
        for mapping_data in mappings:
            try:
                mapping = ZoneMapping(**mapping_data.model_dump())
                self.db.add(mapping)
                count += 1
            except Exception:
                if not skip_duplicates:
                    raise
                continue

        await self.db.commit()
        return count

    async def delete_zone_mapping(self, mapping_id: uuid.UUID) -> bool:
        """Delete zone mapping."""
        mapping = await self.db.get(ZoneMapping, mapping_id)
        if not mapping:
            raise ValueError("Zone mapping not found")

        await self.db.delete(mapping)
        await self.db.commit()
        return True

    # ============================================
    # B2B RATE CARD CRUD
    # ============================================

    async def get_b2b_rate_card(
        self,
        rate_card_id: uuid.UUID,
        include_details: bool = False
    ) -> Optional[B2BRateCard]:
        """Get B2B rate card by ID."""
        stmt = select(B2BRateCard).where(B2BRateCard.id == rate_card_id)

        if include_details:
            stmt = stmt.options(
                selectinload(B2BRateCard.rate_slabs),
                selectinload(B2BRateCard.additional_charges),
                joinedload(B2BRateCard.transporter),
            )
        else:
            stmt = stmt.options(joinedload(B2BRateCard.transporter))

        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_b2b_rate_cards(
        self,
        transporter_id: Optional[uuid.UUID] = None,
        service_type: Optional[B2BServiceType] = None,
        is_active: Optional[bool] = True,
        skip: int = 0,
        limit: int = 20,
    ) -> Tuple[List[B2BRateCard], int]:
        """List B2B rate cards with filters."""
        stmt = (
            select(B2BRateCard)
            .options(joinedload(B2BRateCard.transporter))
            .order_by(B2BRateCard.created_at.desc())
        )

        filters = []
        if transporter_id:
            filters.append(B2BRateCard.transporter_id == transporter_id)
        if service_type:
            filters.append(B2BRateCard.service_type == service_type)
        if is_active is not None:
            filters.append(B2BRateCard.is_active == is_active)

        if filters:
            stmt = stmt.where(and_(*filters))

        count_stmt = select(func.count(B2BRateCard.id))
        if filters:
            count_stmt = count_stmt.where(and_(*filters))
        total = (await self.db.execute(count_stmt)).scalar() or 0

        stmt = stmt.offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        items = list(result.scalars().unique().all())

        return items, total

    async def create_b2b_rate_card(
        self,
        data: B2BRateCardCreate,
        created_by: Optional[uuid.UUID] = None
    ) -> B2BRateCard:
        """Create new B2B rate card."""
        transporter = await self.db.get(Transporter, data.transporter_id)
        if not transporter:
            raise ValueError(f"Transporter {data.transporter_id} not found")

        rate_card_data = data.model_dump(exclude={"rate_slabs", "additional_charges"})
        rate_card_data["created_by"] = created_by
        rate_card = B2BRateCard(**rate_card_data)

        if data.rate_slabs:
            for slab_data in data.rate_slabs:
                slab = B2BRateSlab(**slab_data.model_dump())
                rate_card.rate_slabs.append(slab)

        if data.additional_charges:
            for charge_data in data.additional_charges:
                charge = B2BAdditionalCharge(**charge_data.model_dump())
                rate_card.additional_charges.append(charge)

        self.db.add(rate_card)
        await self.db.commit()
        await self.db.refresh(rate_card)

        return await self.get_b2b_rate_card(rate_card.id, include_details=True)

    async def update_b2b_rate_card(
        self,
        rate_card_id: uuid.UUID,
        data: B2BRateCardUpdate
    ) -> B2BRateCard:
        """Update B2B rate card."""
        rate_card = await self.get_b2b_rate_card(rate_card_id)
        if not rate_card:
            raise ValueError("Rate card not found")

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(rate_card, key, value)

        await self.db.commit()
        await self.db.refresh(rate_card)
        return rate_card

    async def delete_b2b_rate_card(
        self,
        rate_card_id: uuid.UUID,
        hard_delete: bool = False
    ) -> bool:
        """Delete B2B rate card."""
        rate_card = await self.get_b2b_rate_card(rate_card_id)
        if not rate_card:
            raise ValueError("Rate card not found")

        if hard_delete:
            await self.db.delete(rate_card)
        else:
            rate_card.is_active = False

        await self.db.commit()
        return True

    # ============================================
    # B2B RATE SLAB OPERATIONS
    # ============================================

    async def add_b2b_rate_slab(
        self,
        rate_card_id: uuid.UUID,
        data: B2BRateSlabCreate
    ) -> B2BRateSlab:
        """Add rate slab to B2B rate card."""
        rate_card = await self.get_b2b_rate_card(rate_card_id)
        if not rate_card:
            raise ValueError("Rate card not found")

        slab = B2BRateSlab(rate_card_id=rate_card_id, **data.model_dump())
        self.db.add(slab)
        await self.db.commit()
        await self.db.refresh(slab)
        return slab

    async def bulk_add_b2b_rate_slabs(
        self,
        rate_card_id: uuid.UUID,
        slabs: List[B2BRateSlabCreate],
        replace_existing: bool = False
    ) -> int:
        """Bulk add rate slabs to B2B rate card."""
        rate_card = await self.get_b2b_rate_card(rate_card_id)
        if not rate_card:
            raise ValueError("Rate card not found")

        if replace_existing:
            await self.db.execute(
                delete(B2BRateSlab).where(B2BRateSlab.rate_card_id == rate_card_id)
            )

        count = 0
        for slab_data in slabs:
            slab = B2BRateSlab(rate_card_id=rate_card_id, **slab_data.model_dump())
            self.db.add(slab)
            count += 1

        await self.db.commit()
        return count

    async def delete_b2b_rate_slab(self, slab_id: uuid.UUID) -> bool:
        """Delete a B2B rate slab."""
        slab = await self.db.get(B2BRateSlab, slab_id)
        if not slab:
            raise ValueError("Rate slab not found")

        await self.db.delete(slab)
        await self.db.commit()
        return True

    # ============================================
    # FTL RATE CARD CRUD
    # ============================================

    async def get_ftl_rate_card(
        self,
        rate_card_id: uuid.UUID,
        include_details: bool = False
    ) -> Optional[FTLRateCard]:
        """Get FTL rate card by ID."""
        stmt = select(FTLRateCard).where(FTLRateCard.id == rate_card_id)

        if include_details:
            stmt = stmt.options(
                selectinload(FTLRateCard.lane_rates),
                selectinload(FTLRateCard.additional_charges),
                joinedload(FTLRateCard.transporter),
            )
        else:
            stmt = stmt.options(joinedload(FTLRateCard.transporter))

        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_ftl_rate_cards(
        self,
        transporter_id: Optional[uuid.UUID] = None,
        rate_type: Optional[FTLRateType] = None,
        is_active: Optional[bool] = True,
        skip: int = 0,
        limit: int = 20,
    ) -> Tuple[List[FTLRateCard], int]:
        """List FTL rate cards with filters."""
        stmt = (
            select(FTLRateCard)
            .options(joinedload(FTLRateCard.transporter))
            .order_by(FTLRateCard.created_at.desc())
        )

        filters = []
        if transporter_id:
            filters.append(FTLRateCard.transporter_id == transporter_id)
        if rate_type:
            filters.append(FTLRateCard.rate_type == rate_type)
        if is_active is not None:
            filters.append(FTLRateCard.is_active == is_active)

        if filters:
            stmt = stmt.where(and_(*filters))

        count_stmt = select(func.count(FTLRateCard.id))
        if filters:
            count_stmt = count_stmt.where(and_(*filters))
        total = (await self.db.execute(count_stmt)).scalar() or 0

        stmt = stmt.offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        items = list(result.scalars().unique().all())

        return items, total

    async def create_ftl_rate_card(
        self,
        data: FTLRateCardCreate,
        created_by: Optional[uuid.UUID] = None
    ) -> FTLRateCard:
        """Create new FTL rate card."""
        if data.transporter_id:
            transporter = await self.db.get(Transporter, data.transporter_id)
            if not transporter:
                raise ValueError(f"Transporter {data.transporter_id} not found")

        rate_card_data = data.model_dump(exclude={"lane_rates", "additional_charges"})
        rate_card_data["created_by"] = created_by
        rate_card = FTLRateCard(**rate_card_data)

        if data.lane_rates:
            for lane_data in data.lane_rates:
                lane = FTLLaneRate(**lane_data.model_dump())
                rate_card.lane_rates.append(lane)

        if data.additional_charges:
            for charge_data in data.additional_charges:
                charge = FTLAdditionalCharge(**charge_data.model_dump())
                rate_card.additional_charges.append(charge)

        self.db.add(rate_card)
        await self.db.commit()
        await self.db.refresh(rate_card)

        return await self.get_ftl_rate_card(rate_card.id, include_details=True)

    async def update_ftl_rate_card(
        self,
        rate_card_id: uuid.UUID,
        data: FTLRateCardUpdate
    ) -> FTLRateCard:
        """Update FTL rate card."""
        rate_card = await self.get_ftl_rate_card(rate_card_id)
        if not rate_card:
            raise ValueError("Rate card not found")

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(rate_card, key, value)

        await self.db.commit()
        await self.db.refresh(rate_card)
        return rate_card

    async def delete_ftl_rate_card(
        self,
        rate_card_id: uuid.UUID,
        hard_delete: bool = False
    ) -> bool:
        """Delete FTL rate card."""
        rate_card = await self.get_ftl_rate_card(rate_card_id)
        if not rate_card:
            raise ValueError("Rate card not found")

        if hard_delete:
            await self.db.delete(rate_card)
        else:
            rate_card.is_active = False

        await self.db.commit()
        return True

    # ============================================
    # FTL LANE RATE OPERATIONS
    # ============================================

    async def add_ftl_lane_rate(
        self,
        rate_card_id: uuid.UUID,
        data: FTLLaneRateCreate
    ) -> FTLLaneRate:
        """Add lane rate to FTL rate card."""
        rate_card = await self.get_ftl_rate_card(rate_card_id)
        if not rate_card:
            raise ValueError("Rate card not found")

        # Check for duplicate
        stmt = select(FTLLaneRate).where(
            FTLLaneRate.rate_card_id == rate_card_id,
            FTLLaneRate.origin_city == data.origin_city,
            FTLLaneRate.destination_city == data.destination_city,
            FTLLaneRate.vehicle_type == data.vehicle_type
        )
        existing = (await self.db.execute(stmt)).scalar_one_or_none()
        if existing:
            raise ValueError(
                f"Lane rate for {data.origin_city} -> {data.destination_city} "
                f"({data.vehicle_type}) already exists"
            )

        lane = FTLLaneRate(rate_card_id=rate_card_id, **data.model_dump())
        self.db.add(lane)
        await self.db.commit()
        await self.db.refresh(lane)
        return lane

    async def bulk_add_ftl_lane_rates(
        self,
        rate_card_id: uuid.UUID,
        lane_rates: List[FTLLaneRateCreate],
        replace_existing: bool = False
    ) -> int:
        """Bulk add lane rates to FTL rate card."""
        rate_card = await self.get_ftl_rate_card(rate_card_id)
        if not rate_card:
            raise ValueError("Rate card not found")

        if replace_existing:
            await self.db.execute(
                delete(FTLLaneRate).where(FTLLaneRate.rate_card_id == rate_card_id)
            )

        count = 0
        for lane_data in lane_rates:
            lane = FTLLaneRate(rate_card_id=rate_card_id, **lane_data.model_dump())
            self.db.add(lane)
            count += 1

        await self.db.commit()
        return count

    async def delete_ftl_lane_rate(self, lane_id: uuid.UUID) -> bool:
        """Delete a FTL lane rate."""
        lane = await self.db.get(FTLLaneRate, lane_id)
        if not lane:
            raise ValueError("Lane rate not found")

        await self.db.delete(lane)
        await self.db.commit()
        return True

    async def search_ftl_lanes(
        self,
        origin_city: Optional[str] = None,
        destination_city: Optional[str] = None,
        vehicle_type: Optional[str] = None,
        rate_card_id: Optional[uuid.UUID] = None,
        skip: int = 0,
        limit: int = 20
    ) -> Tuple[List[FTLLaneRate], int]:
        """Search FTL lane rates."""
        stmt = (
            select(FTLLaneRate)
            .options(joinedload(FTLLaneRate.rate_card))
            .order_by(FTLLaneRate.origin_city, FTLLaneRate.destination_city)
        )

        filters = [FTLLaneRate.is_active == True]
        if origin_city:
            filters.append(FTLLaneRate.origin_city.ilike(f"%{origin_city}%"))
        if destination_city:
            filters.append(FTLLaneRate.destination_city.ilike(f"%{destination_city}%"))
        if vehicle_type:
            filters.append(FTLLaneRate.vehicle_type == vehicle_type)
        if rate_card_id:
            filters.append(FTLLaneRate.rate_card_id == rate_card_id)

        stmt = stmt.where(and_(*filters))

        count_stmt = select(func.count(FTLLaneRate.id)).where(and_(*filters))
        total = (await self.db.execute(count_stmt)).scalar() or 0

        stmt = stmt.offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        items = list(result.scalars().unique().all())

        return items, total

    # ============================================
    # FTL VEHICLE TYPE OPERATIONS
    # ============================================

    async def get_vehicle_type(self, vehicle_id: uuid.UUID) -> Optional[FTLVehicleType]:
        """Get vehicle type by ID."""
        return await self.db.get(FTLVehicleType, vehicle_id)

    async def get_vehicle_type_by_code(self, code: str) -> Optional[FTLVehicleType]:
        """Get vehicle type by code."""
        stmt = select(FTLVehicleType).where(FTLVehicleType.code == code)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_vehicle_types(
        self,
        category: Optional[str] = None,
        is_active: bool = True,
        skip: int = 0,
        limit: int = 50
    ) -> Tuple[List[FTLVehicleType], int]:
        """List vehicle types."""
        stmt = select(FTLVehicleType).order_by(FTLVehicleType.capacity_tons)

        filters = []
        if category:
            filters.append(FTLVehicleType.category == category)
        if is_active is not None:
            filters.append(FTLVehicleType.is_active == is_active)

        if filters:
            stmt = stmt.where(and_(*filters))

        count_stmt = select(func.count(FTLVehicleType.id))
        if filters:
            count_stmt = count_stmt.where(and_(*filters))
        total = (await self.db.execute(count_stmt)).scalar() or 0

        stmt = stmt.offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        items = list(result.scalars().all())

        return items, total

    async def create_vehicle_type(self, data: FTLVehicleTypeCreate) -> FTLVehicleType:
        """Create new vehicle type."""
        existing = await self.get_vehicle_type_by_code(data.code)
        if existing:
            raise ValueError(f"Vehicle type with code {data.code} already exists")

        vehicle = FTLVehicleType(**data.model_dump())
        self.db.add(vehicle)
        await self.db.commit()
        await self.db.refresh(vehicle)
        return vehicle

    async def update_vehicle_type(
        self,
        vehicle_id: uuid.UUID,
        data: FTLVehicleTypeUpdate
    ) -> FTLVehicleType:
        """Update vehicle type."""
        vehicle = await self.get_vehicle_type(vehicle_id)
        if not vehicle:
            raise ValueError("Vehicle type not found")

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(vehicle, key, value)

        await self.db.commit()
        await self.db.refresh(vehicle)
        return vehicle

    async def delete_vehicle_type(self, vehicle_id: uuid.UUID) -> bool:
        """Delete vehicle type (soft delete)."""
        vehicle = await self.get_vehicle_type(vehicle_id)
        if not vehicle:
            raise ValueError("Vehicle type not found")

        vehicle.is_active = False
        await self.db.commit()
        return True

    # ============================================
    # CARRIER PERFORMANCE
    # ============================================

    async def get_carrier_performance(
        self,
        transporter_id: uuid.UUID,
        period_start: Optional[date] = None,
        period_end: Optional[date] = None,
        zone: Optional[str] = None
    ) -> Optional[CarrierPerformance]:
        """Get carrier performance for a specific period."""
        stmt = select(CarrierPerformance).where(
            CarrierPerformance.transporter_id == transporter_id
        )

        if period_start:
            stmt = stmt.where(CarrierPerformance.period_start >= period_start)
        if period_end:
            stmt = stmt.where(CarrierPerformance.period_end <= period_end)
        if zone:
            stmt = stmt.where(CarrierPerformance.zone == zone)

        stmt = stmt.order_by(CarrierPerformance.period_start.desc()).limit(1)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_carrier_performance(
        self,
        transporter_id: Optional[uuid.UUID] = None,
        zone: Optional[str] = None,
        period_start: Optional[date] = None,
        skip: int = 0,
        limit: int = 20
    ) -> Tuple[List[CarrierPerformance], int]:
        """List carrier performance records."""
        stmt = (
            select(CarrierPerformance)
            .options(joinedload(CarrierPerformance.transporter))
            .order_by(CarrierPerformance.overall_score.desc())
        )

        filters = []
        if transporter_id:
            filters.append(CarrierPerformance.transporter_id == transporter_id)
        if zone:
            filters.append(CarrierPerformance.zone == zone)
        if period_start:
            filters.append(CarrierPerformance.period_start >= period_start)

        if filters:
            stmt = stmt.where(and_(*filters))

        count_stmt = select(func.count(CarrierPerformance.id))
        if filters:
            count_stmt = count_stmt.where(and_(*filters))
        total = (await self.db.execute(count_stmt)).scalar() or 0

        stmt = stmt.offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        items = list(result.scalars().unique().all())

        return items, total

    # ============================================
    # HELPER METHODS
    # ============================================

    async def get_active_d2c_rate_card(
        self,
        transporter_id: uuid.UUID,
        service_type: ServiceType = ServiceType.STANDARD,
        effective_date: Optional[date] = None
    ) -> Optional[D2CRateCard]:
        """Get the active rate card for a transporter on a given date."""
        effective_date = effective_date or date.today()

        stmt = (
            select(D2CRateCard)
            .options(
                selectinload(D2CRateCard.weight_slabs),
                selectinload(D2CRateCard.surcharges),
            )
            .where(
                D2CRateCard.transporter_id == transporter_id,
                D2CRateCard.service_type == service_type,
                D2CRateCard.is_active == True,
                D2CRateCard.effective_from <= effective_date,
                or_(
                    D2CRateCard.effective_to.is_(None),
                    D2CRateCard.effective_to >= effective_date
                )
            )
            .order_by(D2CRateCard.is_default.desc(), D2CRateCard.effective_from.desc())
            .limit(1)
        )

        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_rate_card_summary(
        self,
        transporter_id: Optional[uuid.UUID] = None
    ) -> List[dict]:
        """Get summary of rate cards per transporter."""
        # D2C count
        d2c_stmt = (
            select(
                D2CRateCard.transporter_id,
                func.count(D2CRateCard.id).label("total"),
                func.sum(
                    func.case(
                        (D2CRateCard.is_active == True, 1),
                        else_=0
                    )
                ).label("active")
            )
            .group_by(D2CRateCard.transporter_id)
        )

        if transporter_id:
            d2c_stmt = d2c_stmt.where(D2CRateCard.transporter_id == transporter_id)

        d2c_result = await self.db.execute(d2c_stmt)
        d2c_counts = {row[0]: {"total": row[1], "active": row[2]} for row in d2c_result}

        # B2B count
        b2b_stmt = (
            select(
                B2BRateCard.transporter_id,
                func.count(B2BRateCard.id).label("total"),
                func.sum(
                    func.case(
                        (B2BRateCard.is_active == True, 1),
                        else_=0
                    )
                ).label("active")
            )
            .group_by(B2BRateCard.transporter_id)
        )

        if transporter_id:
            b2b_stmt = b2b_stmt.where(B2BRateCard.transporter_id == transporter_id)

        b2b_result = await self.db.execute(b2b_stmt)
        b2b_counts = {row[0]: {"total": row[1], "active": row[2]} for row in b2b_result}

        # FTL count
        ftl_stmt = (
            select(
                FTLRateCard.transporter_id,
                func.count(FTLRateCard.id).label("total"),
                func.sum(
                    func.case(
                        (FTLRateCard.is_active == True, 1),
                        else_=0
                    )
                ).label("active")
            )
            .where(FTLRateCard.transporter_id.isnot(None))
            .group_by(FTLRateCard.transporter_id)
        )

        if transporter_id:
            ftl_stmt = ftl_stmt.where(FTLRateCard.transporter_id == transporter_id)

        ftl_result = await self.db.execute(ftl_stmt)
        ftl_counts = {row[0]: {"total": row[1], "active": row[2]} for row in ftl_result}

        # Get transporters
        transporter_ids = set(d2c_counts.keys()) | set(b2b_counts.keys()) | set(ftl_counts.keys())

        if not transporter_ids:
            return []

        transporters_stmt = select(Transporter).where(Transporter.id.in_(transporter_ids))
        transporters = (await self.db.execute(transporters_stmt)).scalars().all()

        summary = []
        for t in transporters:
            d2c = d2c_counts.get(t.id, {"total": 0, "active": 0})
            b2b = b2b_counts.get(t.id, {"total": 0, "active": 0})
            ftl = ftl_counts.get(t.id, {"total": 0, "active": 0})

            summary.append({
                "transporter_id": t.id,
                "transporter_code": t.code,
                "transporter_name": t.name,
                "d2c_rate_cards": d2c["total"],
                "b2b_rate_cards": b2b["total"],
                "ftl_rate_cards": ftl["total"],
                "active_d2c": d2c["active"],
                "active_b2b": b2b["active"],
                "active_ftl": ftl["active"],
            })

        return summary
