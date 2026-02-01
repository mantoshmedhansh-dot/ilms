"""Service for managing transporters and serviceability."""
from typing import List, Optional, Tuple
from datetime import datetime
import uuid

from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transporter import Transporter, TransporterType, TransporterServiceability
from app.schemas.transporter import TransporterCreate, TransporterUpdate


class TransporterService:
    """Service for transporter management and serviceability checks."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ==================== TRANSPORTER CRUD ====================

    async def get_transporter(self, transporter_id: uuid.UUID) -> Optional[Transporter]:
        """Get transporter by ID."""
        stmt = (
            select(Transporter)
            .options(selectinload(Transporter.serviceability))
            .where(Transporter.id == transporter_id)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_transporter_by_code(self, code: str) -> Optional[Transporter]:
        """Get transporter by code."""
        stmt = select(Transporter).where(Transporter.code == code)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_transporters(
        self,
        transporter_type: Optional[TransporterType] = None,
        is_active: bool = True,
        supports_cod: Optional[bool] = None,
        skip: int = 0,
        limit: int = 20
    ) -> Tuple[List[Transporter], int]:
        """Get paginated transporters with filters."""
        stmt = select(Transporter).order_by(Transporter.priority, Transporter.name)

        filters = []
        if is_active is not None:
            filters.append(Transporter.is_active == is_active)
        if transporter_type:
            filters.append(Transporter.transporter_type == transporter_type)
        if supports_cod is not None:
            filters.append(Transporter.supports_cod == supports_cod)

        if filters:
            stmt = stmt.where(and_(*filters))

        # Count
        count_stmt = select(func.count(Transporter.id))
        if filters:
            count_stmt = count_stmt.where(and_(*filters))
        total = (await self.db.execute(count_stmt)).scalar() or 0

        # Paginate
        stmt = stmt.offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        items = list(result.scalars().all())

        return items, total

    async def create_transporter(self, data: TransporterCreate) -> Transporter:
        """Create new transporter."""
        # Check if code exists
        existing = await self.get_transporter_by_code(data.code)
        if existing:
            raise ValueError(f"Transporter with code {data.code} already exists")

        transporter = Transporter(**data.model_dump())
        self.db.add(transporter)
        await self.db.commit()
        await self.db.refresh(transporter)
        return transporter

    async def update_transporter(
        self,
        transporter_id: uuid.UUID,
        data: TransporterUpdate
    ) -> Transporter:
        """Update transporter."""
        transporter = await self.get_transporter(transporter_id)
        if not transporter:
            raise ValueError("Transporter not found")

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(transporter, key, value)

        await self.db.commit()
        await self.db.refresh(transporter)
        return transporter

    async def delete_transporter(self, transporter_id: uuid.UUID) -> bool:
        """Delete transporter (soft delete by deactivating)."""
        transporter = await self.get_transporter(transporter_id)
        if not transporter:
            raise ValueError("Transporter not found")

        transporter.is_active = False
        await self.db.commit()
        return True

    # ==================== SERVICEABILITY ====================

    async def check_serviceability(
        self,
        from_pincode: str,
        to_pincode: str,
        payment_mode: Optional[str] = None,
        weight_kg: Optional[float] = None
    ) -> List[dict]:
        """Check which transporters can service this route."""
        stmt = (
            select(TransporterServiceability)
            .options(selectinload(TransporterServiceability.transporter))
            .where(
                TransporterServiceability.origin_pincode == from_pincode,
                TransporterServiceability.destination_pincode == to_pincode,
                TransporterServiceability.is_serviceable == True
            )
        )

        result = await self.db.execute(stmt)
        serviceability_records = list(result.scalars().all())

        available_options = []

        for record in serviceability_records:
            transporter = record.transporter

            # Check if transporter is active
            if not transporter.is_active:
                continue

            # Check weight limits
            if weight_kg:
                if transporter.max_weight_kg and weight_kg > transporter.max_weight_kg:
                    continue
                if weight_kg < transporter.min_weight_kg:
                    continue

            # Check payment mode
            if payment_mode == "COD" and not record.cod_available:
                continue
            if payment_mode == "PREPAID" and not record.prepaid_available:
                continue

            available_options.append({
                "transporter": transporter,
                "estimated_days": record.estimated_days,
                "cod_available": record.cod_available,
                "prepaid_available": record.prepaid_available,
                "rate": record.rate,
                "cod_charge": record.cod_charge,
                "zone": record.zone,
            })

        # Sort by priority
        available_options.sort(key=lambda x: x["transporter"].priority)

        return available_options

    async def add_serviceability(
        self,
        transporter_id: uuid.UUID,
        origin_pincode: str,
        destination_pincode: str,
        estimated_days: Optional[int] = None,
        cod_available: bool = True,
        prepaid_available: bool = True,
        rate: Optional[float] = None,
        cod_charge: Optional[float] = None,
        zone: Optional[str] = None
    ) -> TransporterServiceability:
        """Add serviceability record for transporter."""
        # Check if already exists
        stmt = select(TransporterServiceability).where(
            TransporterServiceability.transporter_id == transporter_id,
            TransporterServiceability.origin_pincode == origin_pincode,
            TransporterServiceability.destination_pincode == destination_pincode
        )
        result = await self.db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            # Update existing
            existing.estimated_days = estimated_days
            existing.cod_available = cod_available
            existing.prepaid_available = prepaid_available
            existing.rate = rate
            existing.cod_charge = cod_charge
            existing.zone = zone
            existing.is_serviceable = True
            await self.db.commit()
            return existing

        # Create new
        serviceability = TransporterServiceability(
            transporter_id=transporter_id,
            origin_pincode=origin_pincode,
            destination_pincode=destination_pincode,
            estimated_days=estimated_days,
            cod_available=cod_available,
            prepaid_available=prepaid_available,
            rate=rate,
            cod_charge=cod_charge,
            zone=zone,
            is_serviceable=True,
        )
        self.db.add(serviceability)
        await self.db.commit()
        await self.db.refresh(serviceability)
        return serviceability

    async def bulk_add_serviceability(
        self,
        transporter_id: uuid.UUID,
        records: List[dict]
    ) -> int:
        """Bulk add serviceability records."""
        count = 0
        for record in records:
            await self.add_serviceability(
                transporter_id=transporter_id,
                origin_pincode=record.get("origin_pincode"),
                destination_pincode=record.get("destination_pincode"),
                estimated_days=record.get("estimated_days"),
                cod_available=record.get("cod_available", True),
                prepaid_available=record.get("prepaid_available", True),
                rate=record.get("rate"),
                cod_charge=record.get("cod_charge"),
                zone=record.get("zone"),
            )
            count += 1

        return count

    # ==================== AWB GENERATION ====================

    async def generate_awb(
        self,
        transporter_id: uuid.UUID
    ) -> str:
        """Generate next AWB number for transporter."""
        transporter = await self.get_transporter(transporter_id)
        if not transporter:
            raise ValueError("Transporter not found")

        prefix = transporter.awb_prefix or transporter.code[:3].upper()
        sequence = transporter.awb_sequence_current

        awb_number = f"{prefix}{sequence:010d}"

        # Update sequence
        transporter.awb_sequence_current = sequence + 1
        await self.db.commit()

        return awb_number

    async def get_tracking_url(
        self,
        transporter_id: uuid.UUID,
        awb_number: str
    ) -> Optional[str]:
        """Get tracking URL for AWB."""
        transporter = await self.get_transporter(transporter_id)
        if not transporter or not transporter.tracking_url_template:
            return None

        return transporter.tracking_url_template.replace("{awb}", awb_number)
