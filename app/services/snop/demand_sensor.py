"""
Demand Sensing Service

Real-time demand signal processing and short-term forecast adjustment:
- Signal ingestion from multiple sources (POS, promotions, weather, market intel)
- Signal strength computation with time decay
- Forecast adjustment based on active signals
- Signal impact tracking and post-event analysis
- Automatic signal expiration and lifecycle management

Inspired by o9 Solutions demand sensing and Blue Yonder Luminate Demand Edge.
"""

import uuid
import math
import logging
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import List, Dict, Optional, Any
from collections import defaultdict

from sqlalchemy import select, func, and_, or_, desc, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.snop import (
    DemandSignal,
    DemandForecast,
    ExternalFactor,
    DemandSignalType,
    DemandSignalStatus,
    ExternalFactorType,
    ForecastGranularity,
    ForecastStatus,
)
from app.models.product import Product

logger = logging.getLogger(__name__)


class DemandSensor:
    """
    Demand sensing engine for real-time forecast adjustment.

    Key concepts:
    - Signal Strength: 0.0 to 1.0, indicates how strong the demand indicator is
    - Impact Direction: UP or DOWN, the direction of demand change
    - Impact %: The estimated percentage change in demand
    - Decay Rate: How quickly the signal loses strength over time
    - Confidence: How reliable the signal source is
    - Effective Strength: signal_strength * confidence * decay_factor

    The sensing engine combines all active signals to compute a
    net forecast adjustment, weighted by effective strength.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    # ==================== Signal CRUD ====================

    async def _generate_signal_code(self) -> str:
        """Generate unique signal code like DS20260214-0001."""
        today = datetime.now(timezone.utc)
        prefix = f"DS{today.strftime('%Y%m%d')}"

        result = await self.db.execute(
            select(func.count(DemandSignal.id))
            .where(DemandSignal.signal_code.like(f"{prefix}%"))
        )
        count = result.scalar() or 0

        return f"{prefix}-{count + 1:04d}"

    async def create_signal(
        self,
        signal_name: str,
        signal_type: DemandSignalType,
        effective_start: date,
        effective_end: date,
        impact_direction: str = "UP",
        impact_pct: float = 0.0,
        signal_strength: float = 0.5,
        confidence: float = 0.7,
        decay_rate: float = 0.1,
        product_id: Optional[uuid.UUID] = None,
        category_id: Optional[uuid.UUID] = None,
        region_id: Optional[uuid.UUID] = None,
        channel: Optional[str] = None,
        applies_to_all: bool = False,
        source: str = "MANUAL",
        source_data: Optional[Dict[str, Any]] = None,
        user_id: Optional[uuid.UUID] = None,
        notes: Optional[str] = None,
    ) -> DemandSignal:
        """Create a new demand signal."""
        signal_code = await self._generate_signal_code()

        signal = DemandSignal(
            signal_code=signal_code,
            signal_name=signal_name,
            signal_type=signal_type.value,
            product_id=product_id,
            category_id=category_id,
            region_id=region_id,
            channel=channel,
            applies_to_all=applies_to_all,
            signal_strength=signal_strength,
            impact_direction=impact_direction,
            impact_pct=impact_pct,
            confidence=confidence,
            effective_start=effective_start,
            effective_end=effective_end,
            decay_rate=decay_rate,
            source=source,
            source_data=source_data or {},
            status=DemandSignalStatus.ACTIVE.value,
            created_by_id=user_id,
            notes=notes,
        )

        self.db.add(signal)
        await self.db.commit()
        await self.db.refresh(signal)

        logger.info(f"Created demand signal {signal_code}: {signal_name} ({signal_type.value})")
        return signal

    async def get_signal(self, signal_id: uuid.UUID) -> Optional[DemandSignal]:
        """Get a single demand signal by ID."""
        result = await self.db.execute(
            select(DemandSignal).where(DemandSignal.id == signal_id)
        )
        return result.scalar_one_or_none()

    async def list_signals(
        self,
        status: Optional[DemandSignalStatus] = None,
        signal_type: Optional[DemandSignalType] = None,
        product_id: Optional[uuid.UUID] = None,
        category_id: Optional[uuid.UUID] = None,
        active_only: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[DemandSignal], int]:
        """List demand signals with filters."""
        query = select(DemandSignal)
        count_query = select(func.count(DemandSignal.id))

        filters = []
        if status:
            filters.append(DemandSignal.status == status.value)
        if signal_type:
            filters.append(DemandSignal.signal_type == signal_type.value)
        if product_id:
            filters.append(
                or_(DemandSignal.product_id == product_id, DemandSignal.applies_to_all == True)
            )
        if category_id:
            filters.append(
                or_(DemandSignal.category_id == category_id, DemandSignal.applies_to_all == True)
            )
        if active_only:
            today = date.today()
            filters.append(DemandSignal.status == DemandSignalStatus.ACTIVE.value)
            filters.append(DemandSignal.effective_start <= today)
            filters.append(DemandSignal.effective_end >= today)

        if filters:
            query = query.where(and_(*filters))
            count_query = count_query.where(and_(*filters))

        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        result = await self.db.execute(
            query.order_by(desc(DemandSignal.detected_at))
            .offset(offset)
            .limit(limit)
        )
        signals = list(result.scalars().all())

        return signals, total

    async def update_signal(
        self,
        signal_id: uuid.UUID,
        signal_strength: Optional[float] = None,
        impact_pct: Optional[float] = None,
        confidence: Optional[float] = None,
        effective_end: Optional[date] = None,
        status: Optional[DemandSignalStatus] = None,
        actual_impact: Optional[float] = None,
        notes: Optional[str] = None,
        user_id: Optional[uuid.UUID] = None,
    ) -> Optional[DemandSignal]:
        """Update a demand signal."""
        signal = await self.get_signal(signal_id)
        if not signal:
            return None

        if signal_strength is not None:
            signal.signal_strength = signal_strength
        if impact_pct is not None:
            signal.impact_pct = impact_pct
        if confidence is not None:
            signal.confidence = confidence
        if effective_end is not None:
            signal.effective_end = effective_end
        if status is not None:
            signal.status = status.value
            if status == DemandSignalStatus.ACKNOWLEDGED and user_id:
                signal.acknowledged_by_id = user_id
        if actual_impact is not None:
            signal.actual_impact = actual_impact
        if notes is not None:
            signal.notes = notes

        await self.db.commit()
        await self.db.refresh(signal)
        return signal

    async def dismiss_signal(self, signal_id: uuid.UUID, user_id: uuid.UUID) -> Optional[DemandSignal]:
        """Dismiss a signal (mark as irrelevant)."""
        return await self.update_signal(
            signal_id,
            status=DemandSignalStatus.DISMISSED,
            user_id=user_id,
        )

    # ==================== Signal Strength & Decay ====================

    def compute_effective_strength(self, signal: DemandSignal, as_of: Optional[date] = None) -> float:
        """
        Compute the current effective strength of a signal after decay.

        effective_strength = signal_strength * confidence * exp(-decay_rate * days_elapsed)
        """
        today = as_of or date.today()

        # Signal hasn't started yet
        if today < signal.effective_start:
            return 0.0

        # Signal has expired
        if today > signal.effective_end:
            return 0.0

        days_elapsed = (today - signal.effective_start).days
        decay_factor = math.exp(-signal.decay_rate * days_elapsed)

        return signal.signal_strength * signal.confidence * decay_factor

    def compute_signal_info(self, signal: DemandSignal) -> Dict[str, Any]:
        """Compute full signal info including decay and remaining days."""
        today = date.today()
        current_strength = self.compute_effective_strength(signal)
        days_active = max(0, (today - signal.effective_start).days)
        days_remaining = max(0, (signal.effective_end - today).days)

        return {
            "current_strength": round(current_strength, 4),
            "days_active": days_active,
            "days_remaining": days_remaining,
        }

    # ==================== Signal Lifecycle ====================

    async def expire_old_signals(self) -> int:
        """Mark expired signals. Returns count of signals expired."""
        today = date.today()

        result = await self.db.execute(
            update(DemandSignal)
            .where(
                and_(
                    DemandSignal.status.in_([
                        DemandSignalStatus.ACTIVE.value,
                        DemandSignalStatus.ACKNOWLEDGED.value,
                    ]),
                    DemandSignal.effective_end < today,
                )
            )
            .values(status=DemandSignalStatus.EXPIRED.value)
        )

        await self.db.commit()
        expired_count = result.rowcount
        if expired_count > 0:
            logger.info(f"Expired {expired_count} demand signals")
        return expired_count

    # ==================== Demand Sensing Analysis ====================

    async def analyze_demand_signals(
        self,
        product_id: Optional[uuid.UUID] = None,
        category_id: Optional[uuid.UUID] = None,
        horizon_days: int = 30,
    ) -> Dict[str, Any]:
        """
        Analyze active demand signals and compute net forecast adjustment.

        This is the core demand sensing logic:
        1. Gather all active signals relevant to the scope
        2. Compute effective strength for each (with decay)
        3. Aggregate by signal type
        4. Compute weighted net forecast adjustment
        5. Generate recommendations
        """
        # First expire old signals
        await self.expire_old_signals()

        today = date.today()
        end_date = today + timedelta(days=horizon_days)

        # Get relevant active signals
        filters = [
            DemandSignal.status.in_([
                DemandSignalStatus.ACTIVE.value,
                DemandSignalStatus.ACKNOWLEDGED.value,
            ]),
            DemandSignal.effective_start <= end_date,
            DemandSignal.effective_end >= today,
        ]

        if product_id:
            filters.append(
                or_(DemandSignal.product_id == product_id, DemandSignal.applies_to_all == True)
            )
        if category_id:
            filters.append(
                or_(DemandSignal.category_id == category_id, DemandSignal.applies_to_all == True)
            )

        result = await self.db.execute(
            select(DemandSignal)
            .where(and_(*filters))
            .order_by(desc(DemandSignal.signal_strength))
        )
        signals = list(result.scalars().all())

        # Also get external factors in the same window
        ext_filters = [
            ExternalFactor.is_active == True,
            ExternalFactor.start_date <= end_date,
            ExternalFactor.end_date >= today,
        ]
        if product_id:
            ext_filters.append(
                or_(ExternalFactor.product_id == product_id, ExternalFactor.applies_to_all == True)
            )
        if category_id:
            ext_filters.append(
                or_(ExternalFactor.category_id == category_id, ExternalFactor.applies_to_all == True)
            )

        ext_result = await self.db.execute(
            select(ExternalFactor).where(and_(*ext_filters))
        )
        external_factors = list(ext_result.scalars().all())

        # Count all signals for context
        total_count_result = await self.db.execute(select(func.count(DemandSignal.id)))
        total_count = total_count_result.scalar() or 0

        # Compute aggregate impact
        impact_by_type: Dict[str, float] = defaultdict(float)
        total_weighted_impact = 0.0
        total_weight = 0.0
        signal_timeline = []
        top_signals = []

        for signal in signals:
            eff_strength = self.compute_effective_strength(signal)
            if eff_strength <= 0:
                continue

            # Direction-aware impact
            directed_impact = signal.impact_pct if signal.impact_direction == "UP" else -signal.impact_pct

            # Weighted by effective strength
            weighted_impact = directed_impact * eff_strength
            total_weighted_impact += weighted_impact
            total_weight += eff_strength

            # Group by type
            impact_by_type[signal.signal_type] += weighted_impact

            info = self.compute_signal_info(signal)
            top_signals.append({
                "id": str(signal.id),
                "code": signal.signal_code,
                "name": signal.signal_name,
                "type": signal.signal_type,
                "strength": signal.signal_strength,
                "current_strength": info["current_strength"],
                "direction": signal.impact_direction,
                "impact_pct": signal.impact_pct,
                "effective_impact": round(weighted_impact, 2),
                "confidence": signal.confidence,
                "source": signal.source,
                "effective_start": signal.effective_start.isoformat(),
                "effective_end": signal.effective_end.isoformat(),
                "days_remaining": info["days_remaining"],
                "status": signal.status,
            })

        # Include external factors as implicit signals
        for ef in external_factors:
            multiplier_impact = (ef.impact_multiplier - 1.0) * 100  # Convert multiplier to %
            if abs(multiplier_impact) > 0.1:
                ef_type = f"EXT_{ef.factor_type}"
                impact_by_type[ef_type] += multiplier_impact

                signal_timeline.append({
                    "type": "external_factor",
                    "name": ef.factor_name,
                    "factor_type": ef.factor_type,
                    "impact_pct": round(multiplier_impact, 2),
                    "start": ef.start_date.isoformat(),
                    "end": ef.end_date.isoformat(),
                })

        # Net forecast adjustment
        net_adjustment = total_weighted_impact / total_weight if total_weight > 0 else 0.0
        weighted_confidence = total_weight / len(signals) if signals else 0.0

        # Build timeline from signals
        for sig in signals:
            signal_timeline.append({
                "type": "demand_signal",
                "name": sig.signal_name,
                "signal_type": sig.signal_type,
                "impact_pct": sig.impact_pct,
                "direction": sig.impact_direction,
                "start": sig.effective_start.isoformat(),
                "end": sig.effective_end.isoformat(),
            })

        # Sort timeline by start date
        signal_timeline.sort(key=lambda x: x["start"])

        # Generate recommendations
        recommendations = self._generate_recommendations(
            signals, external_factors, net_adjustment, impact_by_type
        )

        return {
            "analysis_date": today.isoformat(),
            "active_signals_count": len(signals),
            "total_signals_count": total_count,
            "impact_by_type": {k: round(v, 2) for k, v in impact_by_type.items()},
            "net_forecast_adjustment_pct": round(net_adjustment, 2),
            "weighted_confidence": round(weighted_confidence, 4),
            "signal_timeline": signal_timeline,
            "top_signals": sorted(top_signals, key=lambda x: abs(x["effective_impact"]), reverse=True)[:10],
            "recommendations": recommendations,
        }

    def _generate_recommendations(
        self,
        signals: list,
        external_factors: list,
        net_adjustment: float,
        impact_by_type: Dict[str, float],
    ) -> List[str]:
        """Generate actionable recommendations based on signals."""
        recs = []

        if not signals and not external_factors:
            recs.append("No active demand signals detected. Forecasts are based on historical patterns only.")
            recs.append("Consider setting up POS integration for real-time demand sensing.")
            return recs

        if net_adjustment > 10:
            recs.append(
                f"Strong upward demand signal detected (+{net_adjustment:.1f}%). "
                "Consider increasing procurement and safety stock levels."
            )
        elif net_adjustment > 5:
            recs.append(
                f"Moderate demand uplift expected (+{net_adjustment:.1f}%). "
                "Review supply plan to ensure adequate stock."
            )
        elif net_adjustment < -10:
            recs.append(
                f"Significant demand reduction signal ({net_adjustment:.1f}%). "
                "Consider reducing upcoming procurement orders."
            )
        elif net_adjustment < -5:
            recs.append(
                f"Mild demand softening detected ({net_adjustment:.1f}%). "
                "Monitor closely before adjusting supply plans."
            )

        # Type-specific recommendations
        if impact_by_type.get(DemandSignalType.PROMOTION_LAUNCH.value, 0) > 0:
            recs.append(
                "Active promotion detected. Ensure sufficient inventory in "
                "promotion channels to avoid stockouts."
            )

        if impact_by_type.get(DemandSignalType.STOCKOUT_ALERT.value, 0) > 0:
            recs.append(
                "Stockout alert active! Expedite procurement or redistribute "
                "inventory from other locations."
            )

        if impact_by_type.get(DemandSignalType.WEATHER_EVENT.value, 0) != 0:
            recs.append(
                "Weather event impacting demand. Monitor logistics and "
                "adjust delivery schedules accordingly."
            )

        if impact_by_type.get(DemandSignalType.COMPETITOR_PRICE.value, 0) != 0:
            recs.append(
                "Competitor price change detected. Review pricing strategy "
                "and assess impact on market share."
            )

        if impact_by_type.get(DemandSignalType.FESTIVAL_SEASON.value, 0) > 0:
            recs.append(
                "Festival season demand expected. Pre-position inventory "
                "and plan for increased logistics capacity."
            )

        high_confidence = [s for s in signals if s.confidence >= 0.8]
        if high_confidence:
            recs.append(
                f"{len(high_confidence)} high-confidence signal(s) detected. "
                "Prioritize these for immediate action."
            )

        return recs

    # ==================== Forecast Adjustment ====================

    async def apply_signals_to_forecast(
        self,
        forecast_id: uuid.UUID,
    ) -> Dict[str, Any]:
        """
        Apply active demand signals to adjust a forecast's data points.

        Returns adjustment summary.
        """
        # Get the forecast
        result = await self.db.execute(
            select(DemandForecast).where(DemandForecast.id == forecast_id)
        )
        forecast = result.scalar_one_or_none()
        if not forecast:
            raise ValueError(f"Forecast {forecast_id} not found")

        # Get relevant signals
        analysis = await self.analyze_demand_signals(
            product_id=forecast.product_id,
            category_id=forecast.category_id,
        )

        net_adjustment_pct = analysis["net_forecast_adjustment_pct"]

        if abs(net_adjustment_pct) < 0.5:
            return {
                "forecast_id": str(forecast_id),
                "adjustment_applied": False,
                "reason": "Net signal impact too small (< 0.5%)",
                "net_adjustment_pct": net_adjustment_pct,
            }

        # Adjust forecast data
        multiplier = 1 + (net_adjustment_pct / 100)
        original_data = forecast.forecast_data or []
        adjusted_data = []

        for point in original_data:
            adj_qty = float(point.get("forecasted_qty", 0)) * multiplier
            adj_lower = float(point.get("lower_bound", 0)) * multiplier
            adj_upper = float(point.get("upper_bound", 0)) * multiplier

            adjusted_data.append({
                **point,
                "forecasted_qty": round(max(0, adj_qty), 2),
                "lower_bound": round(max(0, adj_lower), 2),
                "upper_bound": round(max(0, adj_upper), 2),
                "signal_adjusted": True,
                "original_qty": point.get("forecasted_qty", 0),
            })

        # Update forecast
        forecast.forecast_data = adjusted_data
        original_total = float(forecast.total_forecasted_qty)
        forecast.total_forecasted_qty = Decimal(str(round(original_total * multiplier, 2)))
        forecast.external_factors_json = {
            "demand_sensing_applied": True,
            "net_adjustment_pct": net_adjustment_pct,
            "signals_count": analysis["active_signals_count"],
            "applied_at": datetime.now(timezone.utc).isoformat(),
        }

        # Mark signals as applied
        signal_ids = [s["id"] for s in analysis["top_signals"]]
        for sid in signal_ids:
            sig = await self.get_signal(uuid.UUID(sid))
            if sig and sig.status == DemandSignalStatus.ACTIVE.value:
                sig.status = DemandSignalStatus.APPLIED.value
                affected = sig.forecast_ids_affected or []
                affected.append(str(forecast_id))
                sig.forecast_ids_affected = affected

        await self.db.commit()
        await self.db.refresh(forecast)

        return {
            "forecast_id": str(forecast_id),
            "adjustment_applied": True,
            "net_adjustment_pct": net_adjustment_pct,
            "original_total_qty": original_total,
            "adjusted_total_qty": float(forecast.total_forecasted_qty),
            "signals_applied": len(signal_ids),
            "data_points_adjusted": len(adjusted_data),
        }

    # ==================== Auto-detect Signals from POS Data ====================

    async def detect_pos_signals(
        self,
        lookback_days: int = 7,
        spike_threshold: float = 1.5,
        drop_threshold: float = 0.5,
    ) -> List[DemandSignal]:
        """
        Auto-detect demand signals from recent POS/order data.

        Compares recent daily demand to historical average.
        Signals are created when demand exceeds thresholds:
        - spike_threshold: multiplier above average (default 1.5x = +50%)
        - drop_threshold: multiplier below average (default 0.5x = -50%)
        """
        from app.models.order import Order, OrderItem, OrderStatus

        today = date.today()
        recent_start = today - timedelta(days=lookback_days)
        historical_start = today - timedelta(days=90)

        # Get products with recent orders
        recent_query = (
            select(
                OrderItem.product_id,
                func.sum(OrderItem.quantity).label("recent_qty"),
            )
            .join(Order, OrderItem.order_id == Order.id)
            .where(
                and_(
                    Order.order_date >= recent_start,
                    Order.status.notin_([OrderStatus.CANCELLED.value]),
                )
            )
            .group_by(OrderItem.product_id)
        )

        hist_query = (
            select(
                OrderItem.product_id,
                func.sum(OrderItem.quantity).label("hist_qty"),
                func.count(func.distinct(Order.order_date)).label("hist_days"),
            )
            .join(Order, OrderItem.order_id == Order.id)
            .where(
                and_(
                    Order.order_date >= historical_start,
                    Order.order_date < recent_start,
                    Order.status.notin_([OrderStatus.CANCELLED.value]),
                )
            )
            .group_by(OrderItem.product_id)
        )

        recent_result = await self.db.execute(recent_query)
        recent_data = {row.product_id: float(row.recent_qty) for row in recent_result}

        hist_result = await self.db.execute(hist_query)
        hist_data = {
            row.product_id: (
                float(row.hist_qty) / max(1, row.hist_days) * lookback_days
            )
            for row in hist_result
        }

        created_signals = []

        for product_id, recent_qty in recent_data.items():
            expected_qty = hist_data.get(product_id, 0)
            if expected_qty <= 0:
                continue

            ratio = recent_qty / expected_qty

            if ratio >= spike_threshold:
                # Demand spike
                impact_pct = (ratio - 1) * 100
                signal = await self.create_signal(
                    signal_name=f"POS Spike Detected (x{ratio:.1f})",
                    signal_type=DemandSignalType.POS_SPIKE,
                    effective_start=today,
                    effective_end=today + timedelta(days=14),
                    impact_direction="UP",
                    impact_pct=min(impact_pct, 200),
                    signal_strength=min(0.9, 0.5 + (ratio - spike_threshold) * 0.2),
                    confidence=0.8,
                    decay_rate=0.05,
                    product_id=product_id,
                    source="POS_SYSTEM",
                    source_data={
                        "recent_qty": recent_qty,
                        "expected_qty": expected_qty,
                        "ratio": round(ratio, 2),
                        "lookback_days": lookback_days,
                    },
                )
                created_signals.append(signal)

            elif ratio <= drop_threshold:
                # Demand drop
                impact_pct = (1 - ratio) * 100
                signal = await self.create_signal(
                    signal_name=f"POS Drop Detected (x{ratio:.2f})",
                    signal_type=DemandSignalType.POS_DROP,
                    effective_start=today,
                    effective_end=today + timedelta(days=14),
                    impact_direction="DOWN",
                    impact_pct=min(impact_pct, 80),
                    signal_strength=min(0.9, 0.5 + (drop_threshold - ratio) * 0.4),
                    confidence=0.75,
                    decay_rate=0.05,
                    product_id=product_id,
                    source="POS_SYSTEM",
                    source_data={
                        "recent_qty": recent_qty,
                        "expected_qty": expected_qty,
                        "ratio": round(ratio, 2),
                        "lookback_days": lookback_days,
                    },
                )
                created_signals.append(signal)

        logger.info(f"POS signal detection found {len(created_signals)} signals")
        return created_signals
