"""
Pricing Engine Service for Logistics Allocation.

This service handles:
1. Weight calculation (actual vs volumetric)
2. Zone determination
3. D2C cost calculation (courier partners)
4. B2B cost calculation (LTL/PTL)
5. FTL cost calculation (full truck load)
6. Multi-carrier comparison
7. Allocation strategies (cheapest, fastest, best SLA, balanced)
"""
from typing import List, Optional, Dict, Any, Tuple
from datetime import date
from decimal import Decimal, ROUND_UP
from enum import Enum
import uuid

from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.rate_card import (
    D2CRateCard, D2CWeightSlab, D2CSurcharge,
    B2BRateCard, B2BRateSlab, B2BAdditionalCharge,
    FTLRateCard, FTLLaneRate, FTLAdditionalCharge,
    CarrierPerformance, ServiceType, SurchargeType, CalculationType,
    B2BServiceType, B2BRateType, TransportMode,
)
from app.models.transporter import Transporter
from app.services.rate_card_service import RateCardService


class LogisticsSegment(str, Enum):
    """Logistics segment classification."""
    D2C = "D2C"  # Direct to Consumer (< 30kg, single parcel)
    B2B = "B2B"  # Business to Business (30kg - 3000kg, LTL/PTL)
    FTL = "FTL"  # Full Truck Load (> 3000kg or full vehicle)


class AllocationStrategy(str, Enum):
    """Carrier allocation strategy."""
    CHEAPEST_FIRST = "CHEAPEST_FIRST"  # Sort by cost (ascending)
    FASTEST_FIRST = "FASTEST_FIRST"    # Sort by TAT (ascending)
    BEST_SLA = "BEST_SLA"              # Sort by performance score (descending)
    BALANCED = "BALANCED"              # Weighted score of cost, TAT, performance


class RateCalculationRequest:
    """Request object for rate calculation."""
    def __init__(
        self,
        origin_pincode: str,
        destination_pincode: str,
        weight_kg: float,
        length_cm: Optional[float] = None,
        width_cm: Optional[float] = None,
        height_cm: Optional[float] = None,
        payment_mode: str = "PREPAID",  # PREPAID or COD
        order_value: float = 0,
        channel: str = "D2C",  # D2C, AMAZON, FLIPKART, etc.
        declared_value: Optional[float] = None,
        is_fragile: bool = False,
        is_dangerous_goods: bool = False,
        num_packages: int = 1,
        service_type: Optional[str] = None,  # STANDARD, EXPRESS, SAME_DAY
        transporter_ids: Optional[List[uuid.UUID]] = None,  # Filter specific transporters
    ):
        self.origin_pincode = origin_pincode
        self.destination_pincode = destination_pincode
        self.weight_kg = weight_kg
        self.length_cm = length_cm
        self.width_cm = width_cm
        self.height_cm = height_cm
        self.payment_mode = payment_mode.upper()
        self.order_value = order_value
        self.channel = channel.upper()
        self.declared_value = declared_value or order_value
        self.is_fragile = is_fragile
        self.is_dangerous_goods = is_dangerous_goods
        self.num_packages = num_packages
        self.service_type = service_type
        self.transporter_ids = transporter_ids


class CostBreakdown:
    """Detailed cost breakdown for a carrier."""
    def __init__(self):
        self.base_rate: Decimal = Decimal("0")
        self.additional_weight_charge: Decimal = Decimal("0")
        self.fuel_surcharge: Decimal = Decimal("0")
        self.cod_charge: Decimal = Decimal("0")
        self.oda_charge: Decimal = Decimal("0")
        self.handling_charge: Decimal = Decimal("0")
        self.insurance: Decimal = Decimal("0")
        self.rto_risk_charge: Decimal = Decimal("0")
        self.gst: Decimal = Decimal("0")
        self.other_charges: Decimal = Decimal("0")
        self.total: Decimal = Decimal("0")

    def to_dict(self) -> dict:
        return {
            "base_rate": float(self.base_rate),
            "additional_weight_charge": float(self.additional_weight_charge),
            "fuel_surcharge": float(self.fuel_surcharge),
            "cod_charge": float(self.cod_charge),
            "oda_charge": float(self.oda_charge),
            "handling_charge": float(self.handling_charge),
            "insurance": float(self.insurance),
            "rto_risk_charge": float(self.rto_risk_charge),
            "gst": float(self.gst),
            "other_charges": float(self.other_charges),
            "total": float(self.total),
        }


class CarrierQuote:
    """Quote from a carrier for a shipment."""
    def __init__(
        self,
        transporter_id: uuid.UUID,
        transporter_code: str,
        transporter_name: str,
        rate_card_id: uuid.UUID,
        rate_card_code: str,
        segment: LogisticsSegment,
        service_type: str,
        cost_breakdown: CostBreakdown,
        estimated_days_min: int,
        estimated_days_max: int,
        zone: str,
        chargeable_weight_kg: float,
        performance_score: Optional[float] = None,
        is_cod_available: bool = True,
        is_serviceable: bool = True,
        remarks: Optional[str] = None,
    ):
        self.transporter_id = transporter_id
        self.transporter_code = transporter_code
        self.transporter_name = transporter_name
        self.rate_card_id = rate_card_id
        self.rate_card_code = rate_card_code
        self.segment = segment
        self.service_type = service_type
        self.cost_breakdown = cost_breakdown
        self.estimated_days_min = estimated_days_min
        self.estimated_days_max = estimated_days_max
        self.zone = zone
        self.chargeable_weight_kg = chargeable_weight_kg
        self.performance_score = performance_score
        self.is_cod_available = is_cod_available
        self.is_serviceable = is_serviceable
        self.remarks = remarks
        self.allocation_score: float = 0.0

    def to_dict(self) -> dict:
        return {
            "transporter_id": str(self.transporter_id),
            "transporter_code": self.transporter_code,
            "transporter_name": self.transporter_name,
            "rate_card_id": str(self.rate_card_id),
            "rate_card_code": self.rate_card_code,
            "segment": self.segment.value,
            "service_type": self.service_type,
            "cost_breakdown": self.cost_breakdown.to_dict(),
            "total_cost": float(self.cost_breakdown.total),
            "estimated_delivery": {
                "min_days": self.estimated_days_min,
                "max_days": self.estimated_days_max,
            },
            "zone": self.zone,
            "chargeable_weight_kg": self.chargeable_weight_kg,
            "performance_score": self.performance_score,
            "allocation_score": round(self.allocation_score, 2),
            "is_cod_available": self.is_cod_available,
            "is_serviceable": self.is_serviceable,
            "remarks": self.remarks,
        }


class PricingEngine:
    """
    Logistics Pricing Engine.

    Handles cost calculation and carrier allocation for D2C, B2B, and FTL segments.
    """

    # Volumetric divisor (standard for courier industry)
    VOLUMETRIC_DIVISOR = 5000

    # GST rate (18% for logistics in India)
    GST_RATE = Decimal("0.18")

    # Weight thresholds for segment classification
    D2C_MAX_WEIGHT = 30  # kg
    B2B_MAX_WEIGHT = 3000  # kg

    # Allocation strategy weights
    STRATEGY_WEIGHTS = {
        AllocationStrategy.BALANCED: {
            "cost": 0.40,
            "tat": 0.30,
            "performance": 0.30,
        }
    }

    def __init__(self, db: AsyncSession):
        self.db = db
        self.rate_card_service = RateCardService(db)

    # ============================================
    # WEIGHT CALCULATIONS
    # ============================================

    def calculate_volumetric_weight(
        self,
        length_cm: float,
        width_cm: float,
        height_cm: float,
        divisor: int = None
    ) -> float:
        """Calculate volumetric weight from dimensions."""
        divisor = divisor or self.VOLUMETRIC_DIVISOR
        return (length_cm * width_cm * height_cm) / divisor

    def get_chargeable_weight(
        self,
        actual_weight_kg: float,
        length_cm: Optional[float] = None,
        width_cm: Optional[float] = None,
        height_cm: Optional[float] = None,
    ) -> Tuple[float, str]:
        """
        Calculate chargeable weight (max of actual and volumetric).

        Returns:
            Tuple of (chargeable_weight, weight_type)
        """
        if not all([length_cm, width_cm, height_cm]):
            return actual_weight_kg, "ACTUAL"

        volumetric_weight = self.calculate_volumetric_weight(
            length_cm, width_cm, height_cm
        )

        if volumetric_weight > actual_weight_kg:
            return round(volumetric_weight, 2), "VOLUMETRIC"
        return actual_weight_kg, "ACTUAL"

    # ============================================
    # SEGMENT CLASSIFICATION
    # ============================================

    def classify_segment(self, request: RateCalculationRequest) -> LogisticsSegment:
        """
        Classify shipment into logistics segment based on weight and other factors.

        D2C: Weight < 30kg, single parcel, courier partners
        B2B: 30kg - 3000kg, multi-parcel, LTL/PTL
        FTL: > 3000kg or full truck requirement
        """
        chargeable_weight, _ = self.get_chargeable_weight(
            request.weight_kg,
            request.length_cm,
            request.width_cm,
            request.height_cm
        )

        if chargeable_weight <= self.D2C_MAX_WEIGHT and request.num_packages == 1:
            return LogisticsSegment.D2C
        elif chargeable_weight <= self.B2B_MAX_WEIGHT:
            return LogisticsSegment.B2B
        else:
            return LogisticsSegment.FTL

    # ============================================
    # D2C PRICING
    # ============================================

    async def calculate_d2c_rate(
        self,
        request: RateCalculationRequest,
        rate_card: D2CRateCard,
        zone_info: dict
    ) -> Optional[CarrierQuote]:
        """Calculate D2C shipping rate for a specific rate card."""
        zone = zone_info.get("zone", "D")
        is_oda = zone_info.get("is_oda", False)

        # Get chargeable weight
        chargeable_weight, weight_type = self.get_chargeable_weight(
            request.weight_kg,
            request.length_cm,
            request.width_cm,
            request.height_cm
        )

        # Find applicable weight slab
        weight_slab = await self._find_d2c_weight_slab(
            rate_card.id, zone, chargeable_weight
        )
        if not weight_slab:
            return None

        # Check payment mode availability
        if request.payment_mode == "COD" and not weight_slab.cod_available:
            return None
        if request.payment_mode == "PREPAID" and not weight_slab.prepaid_available:
            return None

        # Calculate cost breakdown
        cost = CostBreakdown()

        # Base rate
        cost.base_rate = Decimal(str(weight_slab.base_rate))

        # Additional weight charge
        if chargeable_weight > weight_slab.max_weight_kg:
            # Find next slab or calculate additional
            additional_weight = Decimal(str(chargeable_weight - weight_slab.max_weight_kg))
            weight_unit = Decimal(str(weight_slab.additional_weight_unit_kg or 0.5))
            additional_rate = Decimal(str(weight_slab.additional_rate_per_kg or 0))

            if weight_unit > 0:
                additional_units = (additional_weight / weight_unit).quantize(
                    Decimal("1"), rounding=ROUND_UP
                )
                cost.additional_weight_charge = additional_units * additional_rate

        # Get surcharges
        surcharges = await self._get_d2c_surcharges(rate_card.id, zone)

        subtotal = cost.base_rate + cost.additional_weight_charge

        for surcharge in surcharges:
            charge_amount = self._calculate_surcharge(
                surcharge, subtotal, request.order_value, chargeable_weight, is_oda
            )

            if surcharge.surcharge_type == SurchargeType.FUEL:
                cost.fuel_surcharge = charge_amount
            elif surcharge.surcharge_type == SurchargeType.COD_HANDLING and request.payment_mode == "COD":
                cost.cod_charge += charge_amount
            elif surcharge.surcharge_type == SurchargeType.COD_PERCENTAGE and request.payment_mode == "COD":
                # Percentage of order value
                cost.cod_charge += (Decimal(str(request.order_value)) * Decimal(str(surcharge.value)) / 100)
            elif surcharge.surcharge_type == SurchargeType.ODA and is_oda:
                cost.oda_charge = charge_amount
            elif surcharge.surcharge_type == SurchargeType.INSURANCE:
                cost.insurance = (Decimal(str(request.declared_value)) * Decimal(str(surcharge.value)) / 100)
            elif surcharge.surcharge_type == SurchargeType.RTO:
                cost.rto_risk_charge = charge_amount

        # Calculate subtotal before GST
        subtotal_before_gst = (
            cost.base_rate +
            cost.additional_weight_charge +
            cost.fuel_surcharge +
            cost.cod_charge +
            cost.oda_charge +
            cost.handling_charge +
            cost.insurance +
            cost.rto_risk_charge +
            cost.other_charges
        )

        # GST calculation
        cost.gst = (subtotal_before_gst * self.GST_RATE).quantize(Decimal("0.01"))

        # Total
        cost.total = subtotal_before_gst + cost.gst

        # Get performance score
        performance = await self._get_carrier_performance(
            rate_card.transporter_id, zone
        )

        # Create quote
        return CarrierQuote(
            transporter_id=rate_card.transporter_id,
            transporter_code=rate_card.transporter.code if rate_card.transporter else "N/A",
            transporter_name=rate_card.transporter.name if rate_card.transporter else "N/A",
            rate_card_id=rate_card.id,
            rate_card_code=rate_card.code,
            segment=LogisticsSegment.D2C,
            service_type=rate_card.service_type,
            cost_breakdown=cost,
            estimated_days_min=weight_slab.estimated_days_min or 2,
            estimated_days_max=weight_slab.estimated_days_max or 5,
            zone=zone,
            chargeable_weight_kg=chargeable_weight,
            performance_score=performance.overall_score if performance else None,
            is_cod_available=weight_slab.cod_available,
            is_serviceable=True,
        )

    async def _find_d2c_weight_slab(
        self,
        rate_card_id: uuid.UUID,
        zone: str,
        weight_kg: float
    ) -> Optional[D2CWeightSlab]:
        """Find applicable weight slab for D2C rate card."""
        stmt = (
            select(D2CWeightSlab)
            .where(
                D2CWeightSlab.rate_card_id == rate_card_id,
                D2CWeightSlab.zone == zone,
                D2CWeightSlab.min_weight_kg <= weight_kg,
                D2CWeightSlab.is_active == True,
            )
            .order_by(D2CWeightSlab.min_weight_kg.desc())
            .limit(1)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _get_d2c_surcharges(
        self,
        rate_card_id: uuid.UUID,
        zone: Optional[str] = None
    ) -> List[D2CSurcharge]:
        """Get surcharges for D2C rate card."""
        stmt = (
            select(D2CSurcharge)
            .where(
                D2CSurcharge.rate_card_id == rate_card_id,
                D2CSurcharge.is_active == True,
            )
        )
        if zone:
            stmt = stmt.where(
                or_(
                    D2CSurcharge.zone.is_(None),
                    D2CSurcharge.zone == zone
                )
            )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    def _calculate_surcharge(
        self,
        surcharge: D2CSurcharge,
        subtotal: Decimal,
        order_value: float,
        weight_kg: float,
        is_oda: bool
    ) -> Decimal:
        """Calculate surcharge amount based on calculation type."""
        value = Decimal(str(surcharge.value))

        if surcharge.calculation_type == CalculationType.PERCENTAGE:
            amount = (subtotal * value / 100)
        elif surcharge.calculation_type == CalculationType.FIXED:
            amount = value
        elif surcharge.calculation_type == CalculationType.PER_KG:
            amount = value * Decimal(str(weight_kg))
        else:
            amount = value

        # Apply min/max constraints
        if surcharge.min_amount and amount < Decimal(str(surcharge.min_amount)):
            amount = Decimal(str(surcharge.min_amount))
        if surcharge.max_amount and amount > Decimal(str(surcharge.max_amount)):
            amount = Decimal(str(surcharge.max_amount))

        return amount.quantize(Decimal("0.01"))

    # ============================================
    # B2B PRICING
    # ============================================

    async def calculate_b2b_rate(
        self,
        request: RateCalculationRequest,
        rate_card: B2BRateCard,
        zone_info: dict
    ) -> Optional[CarrierQuote]:
        """Calculate B2B (LTL/PTL) shipping rate."""
        zone = zone_info.get("zone", "D")

        # Get chargeable weight (with minimum chargeable weight)
        chargeable_weight, _ = self.get_chargeable_weight(
            request.weight_kg,
            request.length_cm,
            request.width_cm,
            request.height_cm
        )

        # Apply minimum chargeable weight
        if chargeable_weight < rate_card.min_chargeable_weight_kg:
            chargeable_weight = float(rate_card.min_chargeable_weight_kg)

        # Find applicable rate slab
        rate_slab = await self._find_b2b_rate_slab(
            rate_card.id,
            zone,
            chargeable_weight,
            request.origin_pincode,
            request.destination_pincode
        )

        if not rate_slab:
            return None

        # Calculate cost breakdown
        cost = CostBreakdown()

        # Calculate base rate based on rate type
        if rate_slab.rate_type == B2BRateType.PER_KG:
            cost.base_rate = Decimal(str(rate_slab.rate)) * Decimal(str(chargeable_weight))
        elif rate_slab.rate_type == B2BRateType.PER_CFT:
            # Calculate CFT from dimensions
            if request.length_cm and request.width_cm and request.height_cm:
                cft = (request.length_cm * request.width_cm * request.height_cm) / 28316.8
                cost.base_rate = Decimal(str(rate_slab.rate)) * Decimal(str(cft))
            else:
                cost.base_rate = Decimal(str(rate_slab.rate)) * Decimal(str(chargeable_weight))
        else:  # FLAT_RATE
            cost.base_rate = Decimal(str(rate_slab.rate))

        # Apply minimum charge
        if rate_slab.min_charge and cost.base_rate < Decimal(str(rate_slab.min_charge)):
            cost.base_rate = Decimal(str(rate_slab.min_charge))

        # Get additional charges
        additional_charges = await self._get_b2b_additional_charges(rate_card.id)

        for charge in additional_charges:
            amount = self._calculate_b2b_additional_charge(
                charge, cost.base_rate, chargeable_weight, request.num_packages
            )

            if charge.charge_type == "HANDLING":
                cost.handling_charge += amount
            elif charge.charge_type == "DOCKET":
                cost.other_charges += amount
            elif charge.charge_type == "LOADING":
                cost.handling_charge += amount
            elif charge.charge_type == "UNLOADING":
                cost.handling_charge += amount
            elif charge.charge_type == "FUEL":
                cost.fuel_surcharge += amount
            elif charge.charge_type == "ODA":
                if zone_info.get("is_oda"):
                    cost.oda_charge += amount
            else:
                cost.other_charges += amount

        # Subtotal before GST
        subtotal_before_gst = (
            cost.base_rate +
            cost.handling_charge +
            cost.fuel_surcharge +
            cost.oda_charge +
            cost.other_charges
        )

        # GST
        cost.gst = (subtotal_before_gst * self.GST_RATE).quantize(Decimal("0.01"))

        # Total
        cost.total = subtotal_before_gst + cost.gst

        # Get performance score
        performance = await self._get_carrier_performance(
            rate_card.transporter_id, zone
        )

        return CarrierQuote(
            transporter_id=rate_card.transporter_id,
            transporter_code=rate_card.transporter.code if rate_card.transporter else "N/A",
            transporter_name=rate_card.transporter.name if rate_card.transporter else "N/A",
            rate_card_id=rate_card.id,
            rate_card_code=rate_card.code,
            segment=LogisticsSegment.B2B,
            service_type=rate_card.service_type,
            cost_breakdown=cost,
            estimated_days_min=rate_slab.transit_days_min or 3,
            estimated_days_max=rate_slab.transit_days_max or 7,
            zone=zone,
            chargeable_weight_kg=chargeable_weight,
            performance_score=performance.overall_score if performance else None,
            is_cod_available=False,  # B2B typically doesn't support COD
            is_serviceable=True,
        )

    async def _find_b2b_rate_slab(
        self,
        rate_card_id: uuid.UUID,
        zone: str,
        weight_kg: float,
        origin_pincode: str,
        destination_pincode: str
    ) -> Optional[B2BRateSlab]:
        """Find applicable rate slab for B2B rate card."""
        # Try to find lane-specific rate first
        stmt = (
            select(B2BRateSlab)
            .where(
                B2BRateSlab.rate_card_id == rate_card_id,
                B2BRateSlab.is_active == True,
                B2BRateSlab.min_weight_kg <= weight_kg,
                or_(
                    B2BRateSlab.max_weight_kg.is_(None),
                    B2BRateSlab.max_weight_kg >= weight_kg
                )
            )
        )

        # Prefer zone-specific or lane-specific rates
        stmt = stmt.where(
            or_(
                B2BRateSlab.zone == zone,
                B2BRateSlab.zone.is_(None)
            )
        ).order_by(
            B2BRateSlab.zone.desc().nulls_last(),  # Prefer zone-specific
            B2BRateSlab.min_weight_kg.desc()
        ).limit(1)

        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _get_b2b_additional_charges(
        self,
        rate_card_id: uuid.UUID
    ) -> List[B2BAdditionalCharge]:
        """Get additional charges for B2B rate card."""
        stmt = (
            select(B2BAdditionalCharge)
            .where(
                B2BAdditionalCharge.rate_card_id == rate_card_id,
                B2BAdditionalCharge.is_active == True,
            )
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    def _calculate_b2b_additional_charge(
        self,
        charge: B2BAdditionalCharge,
        base_rate: Decimal,
        weight_kg: float,
        num_packages: int
    ) -> Decimal:
        """Calculate B2B additional charge amount."""
        value = Decimal(str(charge.value))

        if charge.calculation_type == CalculationType.PERCENTAGE:
            return (base_rate * value / 100).quantize(Decimal("0.01"))
        elif charge.calculation_type == CalculationType.PER_KG:
            return (value * Decimal(str(weight_kg))).quantize(Decimal("0.01"))
        elif charge.per_unit == "PER_PKG":
            return (value * Decimal(str(num_packages))).quantize(Decimal("0.01"))
        else:  # FIXED
            return value

    # ============================================
    # FTL PRICING
    # ============================================

    async def calculate_ftl_rate(
        self,
        request: RateCalculationRequest,
        rate_card: FTLRateCard,
        origin_city: str,
        destination_city: str,
        vehicle_type: Optional[str] = None
    ) -> List[CarrierQuote]:
        """Calculate FTL shipping rates for all matching lane rates."""
        quotes = []

        # Find matching lane rates
        lane_rates = await self._find_ftl_lane_rates(
            rate_card.id,
            origin_city,
            destination_city,
            vehicle_type
        )

        for lane in lane_rates:
            cost = CostBreakdown()

            # Base rate (per trip)
            cost.base_rate = Decimal(str(lane.rate_per_trip))

            # Extra kilometer charges
            if lane.rate_per_km and lane.distance_km and lane.min_running_km:
                if lane.distance_km > lane.min_running_km:
                    extra_km = lane.distance_km - lane.min_running_km
                    extra_km_rate = Decimal(str(lane.extra_km_rate or lane.rate_per_km))
                    cost.other_charges += extra_km_rate * Decimal(str(extra_km))

            # Get additional charges
            additional_charges = await self._get_ftl_additional_charges(rate_card.id)

            for charge in additional_charges:
                amount = self._calculate_ftl_additional_charge(charge, cost.base_rate)

                if charge.charge_type == "TOLL":
                    cost.other_charges += amount
                elif charge.charge_type == "DETENTION":
                    cost.handling_charge += amount
                elif charge.charge_type in ["LOADING", "UNLOADING"]:
                    cost.handling_charge += amount
                else:
                    cost.other_charges += amount

            # Subtotal before GST
            subtotal_before_gst = (
                cost.base_rate +
                cost.handling_charge +
                cost.other_charges
            )

            # GST
            cost.gst = (subtotal_before_gst * self.GST_RATE).quantize(Decimal("0.01"))

            # Total
            cost.total = subtotal_before_gst + cost.gst

            # Get performance score
            performance = await self._get_carrier_performance(
                rate_card.transporter_id, None
            ) if rate_card.transporter_id else None

            # Calculate transit time in days
            transit_hours = lane.transit_hours or 24
            estimated_days = max(1, transit_hours // 24)

            quotes.append(CarrierQuote(
                transporter_id=rate_card.transporter_id or uuid.UUID(int=0),
                transporter_code=rate_card.transporter.code if rate_card.transporter else "SELF",
                transporter_name=rate_card.transporter.name if rate_card.transporter else "Self Delivery",
                rate_card_id=rate_card.id,
                rate_card_code=rate_card.code,
                segment=LogisticsSegment.FTL,
                service_type=f"{lane.vehicle_type}",
                cost_breakdown=cost,
                estimated_days_min=estimated_days,
                estimated_days_max=estimated_days + 1,
                zone=f"{lane.origin_city}->{lane.destination_city}",
                chargeable_weight_kg=lane.vehicle_capacity_tons * 1000 if lane.vehicle_capacity_tons else 0,
                performance_score=performance.overall_score if performance else None,
                is_cod_available=False,
                is_serviceable=True,
                remarks=f"Vehicle: {lane.vehicle_type}, Distance: {lane.distance_km}km"
            ))

        return quotes

    async def _find_ftl_lane_rates(
        self,
        rate_card_id: uuid.UUID,
        origin_city: str,
        destination_city: str,
        vehicle_type: Optional[str] = None
    ) -> List[FTLLaneRate]:
        """Find matching FTL lane rates."""
        stmt = (
            select(FTLLaneRate)
            .where(
                FTLLaneRate.rate_card_id == rate_card_id,
                FTLLaneRate.is_active == True,
                FTLLaneRate.origin_city.ilike(f"%{origin_city}%"),
                FTLLaneRate.destination_city.ilike(f"%{destination_city}%"),
            )
        )

        if vehicle_type:
            stmt = stmt.where(FTLLaneRate.vehicle_type == vehicle_type)

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def _get_ftl_additional_charges(
        self,
        rate_card_id: uuid.UUID
    ) -> List[FTLAdditionalCharge]:
        """Get additional charges for FTL rate card."""
        stmt = (
            select(FTLAdditionalCharge)
            .where(
                FTLAdditionalCharge.rate_card_id == rate_card_id,
                FTLAdditionalCharge.is_active == True,
            )
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    def _calculate_ftl_additional_charge(
        self,
        charge: FTLAdditionalCharge,
        base_rate: Decimal
    ) -> Decimal:
        """Calculate FTL additional charge amount."""
        value = Decimal(str(charge.value))

        if charge.calculation_type == CalculationType.PERCENTAGE:
            return (base_rate * value / 100).quantize(Decimal("0.01"))
        else:  # FIXED
            return value

    # ============================================
    # CARRIER PERFORMANCE
    # ============================================

    async def _get_carrier_performance(
        self,
        transporter_id: uuid.UUID,
        zone: Optional[str] = None
    ) -> Optional[CarrierPerformance]:
        """Get latest carrier performance record."""
        stmt = (
            select(CarrierPerformance)
            .where(CarrierPerformance.transporter_id == transporter_id)
        )

        if zone:
            stmt = stmt.where(
                or_(
                    CarrierPerformance.zone == zone,
                    CarrierPerformance.zone.is_(None)
                )
            )

        stmt = stmt.order_by(
            CarrierPerformance.period_end.desc()
        ).limit(1)

        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    # ============================================
    # MULTI-CARRIER COMPARISON
    # ============================================

    async def get_quotes(
        self,
        request: RateCalculationRequest
    ) -> Dict[str, Any]:
        """
        Get quotes from all eligible carriers for a shipment.

        Returns:
            Dictionary containing quotes and recommended carrier.
        """
        # Determine segment
        segment = self.classify_segment(request)

        # Get zone info
        zone_info = await self.rate_card_service.lookup_zone(
            request.origin_pincode,
            request.destination_pincode
        )

        quotes: List[CarrierQuote] = []

        if segment == LogisticsSegment.D2C:
            quotes = await self._get_d2c_quotes(request, zone_info)
        elif segment == LogisticsSegment.B2B:
            quotes = await self._get_b2b_quotes(request, zone_info)
        else:
            # For FTL, we need city names from pincodes (simplified here)
            origin_city = request.origin_pincode[:3]  # Placeholder
            destination_city = request.destination_pincode[:3]
            quotes = await self._get_ftl_quotes(request, origin_city, destination_city)

        # Filter non-serviceable quotes
        serviceable_quotes = [q for q in quotes if q.is_serviceable]

        if not serviceable_quotes:
            return {
                "segment": segment.value,
                "zone": zone_info.get("zone"),
                "chargeable_weight": self.get_chargeable_weight(
                    request.weight_kg,
                    request.length_cm,
                    request.width_cm,
                    request.height_cm
                )[0],
                "quotes": [],
                "recommended": None,
                "message": "No serviceable carriers found for this route",
            }

        # Sort by allocation score
        sorted_quotes = self._apply_allocation_strategy(
            serviceable_quotes, AllocationStrategy.BALANCED
        )

        return {
            "segment": segment.value,
            "zone": zone_info.get("zone"),
            "chargeable_weight": sorted_quotes[0].chargeable_weight_kg if sorted_quotes else 0,
            "quotes": [q.to_dict() for q in sorted_quotes],
            "recommended": sorted_quotes[0].to_dict() if sorted_quotes else None,
            "alternatives": [q.to_dict() for q in sorted_quotes[1:4]] if len(sorted_quotes) > 1 else [],
        }

    async def _get_d2c_quotes(
        self,
        request: RateCalculationRequest,
        zone_info: dict
    ) -> List[CarrierQuote]:
        """Get D2C quotes from all eligible carriers."""
        quotes = []

        # Determine service type filter
        service_type = None
        if request.service_type:
            try:
                service_type = ServiceType(request.service_type)
            except ValueError:
                pass

        # Get active D2C rate cards
        rate_cards, _ = await self.rate_card_service.list_d2c_rate_cards(
            transporter_id=request.transporter_ids[0] if request.transporter_ids and len(request.transporter_ids) == 1 else None,
            service_type=service_type,
            is_active=True,
            effective_date=date.today(),
            skip=0,
            limit=50,
        )

        for rate_card in rate_cards:
            # Filter by transporter IDs if provided
            if request.transporter_ids and rate_card.transporter_id not in request.transporter_ids:
                continue

            quote = await self.calculate_d2c_rate(request, rate_card, zone_info)
            if quote:
                quotes.append(quote)

        return quotes

    async def _get_b2b_quotes(
        self,
        request: RateCalculationRequest,
        zone_info: dict
    ) -> List[CarrierQuote]:
        """Get B2B quotes from all eligible carriers."""
        quotes = []

        # Determine service type filter
        service_type = None
        if request.service_type:
            try:
                service_type = B2BServiceType(request.service_type)
            except ValueError:
                pass

        # Get active B2B rate cards
        rate_cards, _ = await self.rate_card_service.list_b2b_rate_cards(
            transporter_id=request.transporter_ids[0] if request.transporter_ids and len(request.transporter_ids) == 1 else None,
            service_type=service_type,
            is_active=True,
            skip=0,
            limit=50,
        )

        for rate_card in rate_cards:
            if request.transporter_ids and rate_card.transporter_id not in request.transporter_ids:
                continue

            quote = await self.calculate_b2b_rate(request, rate_card, zone_info)
            if quote:
                quotes.append(quote)

        return quotes

    async def _get_ftl_quotes(
        self,
        request: RateCalculationRequest,
        origin_city: str,
        destination_city: str
    ) -> List[CarrierQuote]:
        """Get FTL quotes from all eligible carriers."""
        quotes = []

        # Get active FTL rate cards
        rate_cards, _ = await self.rate_card_service.list_ftl_rate_cards(
            transporter_id=request.transporter_ids[0] if request.transporter_ids and len(request.transporter_ids) == 1 else None,
            is_active=True,
            skip=0,
            limit=50,
        )

        for rate_card in rate_cards:
            if request.transporter_ids and rate_card.transporter_id and rate_card.transporter_id not in request.transporter_ids:
                continue

            ftl_quotes = await self.calculate_ftl_rate(
                request, rate_card, origin_city, destination_city
            )
            quotes.extend(ftl_quotes)

        return quotes

    # ============================================
    # ALLOCATION STRATEGIES
    # ============================================

    def _apply_allocation_strategy(
        self,
        quotes: List[CarrierQuote],
        strategy: AllocationStrategy
    ) -> List[CarrierQuote]:
        """Apply allocation strategy and calculate scores."""
        if not quotes:
            return []

        if strategy == AllocationStrategy.CHEAPEST_FIRST:
            # Sort by cost (ascending)
            for quote in quotes:
                quote.allocation_score = 100 - float(quote.cost_breakdown.total) / 10
            return sorted(quotes, key=lambda q: float(q.cost_breakdown.total))

        elif strategy == AllocationStrategy.FASTEST_FIRST:
            # Sort by TAT (ascending)
            for quote in quotes:
                quote.allocation_score = 100 - quote.estimated_days_min * 10
            return sorted(quotes, key=lambda q: q.estimated_days_min)

        elif strategy == AllocationStrategy.BEST_SLA:
            # Sort by performance score (descending)
            for quote in quotes:
                quote.allocation_score = quote.performance_score or 50
            return sorted(quotes, key=lambda q: q.performance_score or 0, reverse=True)

        else:  # BALANCED
            # Calculate weighted score
            weights = self.STRATEGY_WEIGHTS[AllocationStrategy.BALANCED]

            # Normalize values for scoring
            costs = [float(q.cost_breakdown.total) for q in quotes]
            tats = [q.estimated_days_min for q in quotes]
            perfs = [q.performance_score or 50 for q in quotes]

            min_cost, max_cost = min(costs), max(costs) or 1
            min_tat, max_tat = min(tats), max(tats) or 1
            min_perf, max_perf = min(perfs), max(perfs) or 1

            cost_range = max_cost - min_cost or 1
            tat_range = max_tat - min_tat or 1
            perf_range = max_perf - min_perf or 1

            for quote in quotes:
                # Cost score (lower is better, so invert)
                cost_score = 100 - ((float(quote.cost_breakdown.total) - min_cost) / cost_range * 100)

                # TAT score (lower is better, so invert)
                tat_score = 100 - ((quote.estimated_days_min - min_tat) / tat_range * 100)

                # Performance score (higher is better)
                perf_score = ((quote.performance_score or 50) - min_perf) / perf_range * 100

                # Weighted score
                quote.allocation_score = (
                    cost_score * weights["cost"] +
                    tat_score * weights["tat"] +
                    perf_score * weights["performance"]
                )

            return sorted(quotes, key=lambda q: q.allocation_score, reverse=True)

    # ============================================
    # ALLOCATION
    # ============================================

    async def allocate(
        self,
        request: RateCalculationRequest,
        strategy: AllocationStrategy = AllocationStrategy.BALANCED
    ) -> Dict[str, Any]:
        """
        Allocate carrier for a shipment based on strategy.

        Returns:
            Allocation result with selected carrier and alternatives.
        """
        result = await self.get_quotes(request)

        if not result.get("quotes"):
            return {
                "success": False,
                "message": "No eligible carriers found",
                "allocation": None,
            }

        # Re-sort with specified strategy
        quotes = [
            self._dict_to_quote(q) for q in result["quotes"]
        ]
        sorted_quotes = self._apply_allocation_strategy(quotes, strategy)

        selected = sorted_quotes[0]

        return {
            "success": True,
            "strategy": strategy.value,
            "segment": result["segment"],
            "zone": result["zone"],
            "allocation": {
                "carrier": {
                    "id": str(selected.transporter_id),
                    "code": selected.transporter_code,
                    "name": selected.transporter_name,
                },
                "rate_card_id": str(selected.rate_card_id),
                "rate_card_code": selected.rate_card_code,
                "cost_breakdown": selected.cost_breakdown.to_dict(),
                "total_cost": float(selected.cost_breakdown.total),
                "estimated_delivery": {
                    "min_days": selected.estimated_days_min,
                    "max_days": selected.estimated_days_max,
                },
                "score": round(selected.allocation_score, 2),
            },
            "alternatives": [
                {
                    "carrier": {
                        "id": str(q.transporter_id),
                        "code": q.transporter_code,
                        "name": q.transporter_name,
                    },
                    "total_cost": float(q.cost_breakdown.total),
                    "estimated_days_min": q.estimated_days_min,
                    "score": round(q.allocation_score, 2),
                }
                for q in sorted_quotes[1:4]
            ],
        }

    def _dict_to_quote(self, data: dict) -> CarrierQuote:
        """Convert dictionary back to CarrierQuote object."""
        cost = CostBreakdown()
        cost_data = data.get("cost_breakdown", {})
        cost.base_rate = Decimal(str(cost_data.get("base_rate", 0)))
        cost.additional_weight_charge = Decimal(str(cost_data.get("additional_weight_charge", 0)))
        cost.fuel_surcharge = Decimal(str(cost_data.get("fuel_surcharge", 0)))
        cost.cod_charge = Decimal(str(cost_data.get("cod_charge", 0)))
        cost.oda_charge = Decimal(str(cost_data.get("oda_charge", 0)))
        cost.handling_charge = Decimal(str(cost_data.get("handling_charge", 0)))
        cost.insurance = Decimal(str(cost_data.get("insurance", 0)))
        cost.rto_risk_charge = Decimal(str(cost_data.get("rto_risk_charge", 0)))
        cost.gst = Decimal(str(cost_data.get("gst", 0)))
        cost.other_charges = Decimal(str(cost_data.get("other_charges", 0)))
        cost.total = Decimal(str(cost_data.get("total", 0)))

        return CarrierQuote(
            transporter_id=uuid.UUID(data["transporter_id"]),
            transporter_code=data["transporter_code"],
            transporter_name=data["transporter_name"],
            rate_card_id=uuid.UUID(data["rate_card_id"]),
            rate_card_code=data["rate_card_code"],
            segment=LogisticsSegment(data["segment"]),
            service_type=data["service_type"],
            cost_breakdown=cost,
            estimated_days_min=data["estimated_delivery"]["min_days"],
            estimated_days_max=data["estimated_delivery"]["max_days"],
            zone=data["zone"],
            chargeable_weight_kg=data["chargeable_weight_kg"],
            performance_score=data.get("performance_score"),
            is_cod_available=data.get("is_cod_available", False),
            is_serviceable=data.get("is_serviceable", True),
        )
