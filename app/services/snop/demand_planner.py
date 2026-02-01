"""
Demand Planner Service

Multi-level demand aggregation and forecasting:
- SKU-level daily/weekly forecasts
- Category-level weekly/monthly aggregation
- Regional monthly forecasts
- Channel-based demand analysis
"""

import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import List, Dict, Optional, Tuple, Any
from collections import defaultdict
import math

from sqlalchemy import select, func, and_, or_, desc, extract
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.order import Order, OrderItem, OrderStatus, OrderSource
from app.models.product import Product, ProductVariant
from app.models.category import Category
from app.models.warehouse import Warehouse
from app.models.region import Region
from app.models.snop import (
    DemandForecast,
    ForecastAdjustment,
    ExternalFactor,
    ForecastGranularity,
    ForecastLevel,
    ForecastStatus,
    ForecastAlgorithm,
    ExternalFactorType,
)


class DemandPlannerService:
    """
    Multi-level demand planning service.

    Aggregates historical sales data at various levels:
    - SKU (product) level
    - Category level
    - Regional level
    - Channel level

    Supports multiple time granularities:
    - Daily
    - Weekly
    - Monthly
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    # ==================== Historical Data Aggregation ====================

    async def get_historical_demand(
        self,
        product_id: Optional[uuid.UUID] = None,
        category_id: Optional[uuid.UUID] = None,
        warehouse_id: Optional[uuid.UUID] = None,
        region_id: Optional[uuid.UUID] = None,
        channel: Optional[str] = None,
        start_date: date = None,
        end_date: date = None,
        granularity: ForecastGranularity = ForecastGranularity.DAILY
    ) -> List[Dict[str, Any]]:
        """
        Get historical demand data aggregated by the specified granularity.

        Returns list of dicts: [{"date": date, "quantity": Decimal, "revenue": Decimal}, ...]
        """
        if start_date is None:
            start_date = date.today() - timedelta(days=365)
        if end_date is None:
            end_date = date.today()

        # Build base query for delivered orders
        query = (
            select(
                Order.created_at,
                func.sum(OrderItem.quantity).label("quantity"),
                func.sum(OrderItem.total_amount).label("revenue")
            )
            .join(OrderItem, Order.id == OrderItem.order_id)
            .join(Product, OrderItem.product_id == Product.id)
            .where(
                and_(
                    Order.status.in_([OrderStatus.DELIVERED, OrderStatus.PARTIALLY_DELIVERED]),
                    Order.created_at >= start_date,
                    Order.created_at <= end_date
                )
            )
        )

        # Apply filters
        if product_id:
            query = query.where(OrderItem.product_id == product_id)
        if category_id:
            query = query.where(Product.category_id == category_id)
        if warehouse_id:
            query = query.where(Order.warehouse_id == warehouse_id)
        if region_id:
            query = query.where(Order.region_id == region_id)
        if channel:
            query = query.where(Order.source == channel)

        # Group by granularity
        if granularity == ForecastGranularity.DAILY:
            query = query.group_by(Order.created_at).order_by(Order.created_at)
        elif granularity == ForecastGranularity.WEEKLY:
            # Group by ISO week
            query = query.group_by(
                extract('year', Order.created_at),
                extract('week', Order.created_at)
            ).order_by(
                extract('year', Order.created_at),
                extract('week', Order.created_at)
            )
        elif granularity == ForecastGranularity.MONTHLY:
            query = query.group_by(
                extract('year', Order.created_at),
                extract('month', Order.created_at)
            ).order_by(
                extract('year', Order.created_at),
                extract('month', Order.created_at)
            )

        result = await self.db.execute(query)
        rows = result.all()

        # Convert to standardized format
        demand_data = []
        for row in rows:
            if granularity == ForecastGranularity.DAILY:
                demand_data.append({
                    "date": row.order_date,
                    "quantity": Decimal(str(row.quantity or 0)),
                    "revenue": Decimal(str(row.revenue or 0))
                })
            else:
                # For weekly/monthly, we need to reconstruct the date
                demand_data.append({
                    "date": row.order_date if hasattr(row, 'order_date') else start_date,
                    "quantity": Decimal(str(row.quantity or 0)),
                    "revenue": Decimal(str(row.revenue or 0))
                })

        return demand_data

    async def get_demand_by_product(
        self,
        start_date: date,
        end_date: date,
        warehouse_id: Optional[uuid.UUID] = None,
        category_id: Optional[uuid.UUID] = None,
        top_n: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get demand aggregated by product for the given period.
        """
        query = (
            select(
                Product.id.label("product_id"),
                Product.name.label("product_name"),
                Product.sku.label("product_sku"),
                func.sum(OrderItem.quantity).label("total_quantity"),
                func.sum(OrderItem.total_amount).label("total_revenue"),
                func.count(Order.id.distinct()).label("order_count")
            )
            .join(OrderItem, OrderItem.product_id == Product.id)
            .join(Order, Order.id == OrderItem.order_id)
            .where(
                and_(
                    Order.status.in_([OrderStatus.DELIVERED, OrderStatus.PARTIALLY_DELIVERED]),
                    Order.created_at >= start_date,
                    Order.created_at <= end_date
                )
            )
            .group_by(Product.id, Product.name, Product.sku)
            .order_by(desc(func.sum(OrderItem.quantity)))
            .limit(top_n)
        )

        if warehouse_id:
            query = query.where(Order.warehouse_id == warehouse_id)
        if category_id:
            query = query.where(Product.category_id == category_id)

        result = await self.db.execute(query)
        rows = result.all()

        return [
            {
                "product_id": row.product_id,
                "product_name": row.product_name,
                "product_sku": row.product_sku,
                "total_quantity": Decimal(str(row.total_quantity or 0)),
                "total_revenue": Decimal(str(row.total_revenue or 0)),
                "order_count": row.order_count
            }
            for row in rows
        ]

    async def get_demand_by_category(
        self,
        start_date: date,
        end_date: date,
        warehouse_id: Optional[uuid.UUID] = None
    ) -> List[Dict[str, Any]]:
        """
        Get demand aggregated by category.
        """
        query = (
            select(
                Category.id.label("category_id"),
                Category.name.label("category_name"),
                func.sum(OrderItem.quantity).label("total_quantity"),
                func.sum(OrderItem.total_amount).label("total_revenue"),
                func.count(Product.id.distinct()).label("product_count")
            )
            .join(Product, Product.category_id == Category.id)
            .join(OrderItem, OrderItem.product_id == Product.id)
            .join(Order, Order.id == OrderItem.order_id)
            .where(
                and_(
                    Order.status.in_([OrderStatus.DELIVERED, OrderStatus.PARTIALLY_DELIVERED]),
                    Order.created_at >= start_date,
                    Order.created_at <= end_date
                )
            )
            .group_by(Category.id, Category.name)
            .order_by(desc(func.sum(OrderItem.quantity)))
        )

        if warehouse_id:
            query = query.where(Order.warehouse_id == warehouse_id)

        result = await self.db.execute(query)
        rows = result.all()

        return [
            {
                "category_id": row.category_id,
                "category_name": row.category_name,
                "total_quantity": Decimal(str(row.total_quantity or 0)),
                "total_revenue": Decimal(str(row.total_revenue or 0)),
                "product_count": row.product_count
            }
            for row in rows
        ]

    async def get_demand_by_channel(
        self,
        start_date: date,
        end_date: date,
        product_id: Optional[uuid.UUID] = None
    ) -> List[Dict[str, Any]]:
        """
        Get demand aggregated by sales channel.
        """
        query = (
            select(
                Order.source.label("channel"),
                func.sum(OrderItem.quantity).label("total_quantity"),
                func.sum(OrderItem.total_amount).label("total_revenue"),
                func.count(Order.id.distinct()).label("order_count")
            )
            .join(OrderItem, OrderItem.order_id == Order.id)
            .where(
                and_(
                    Order.status.in_([OrderStatus.DELIVERED, OrderStatus.PARTIALLY_DELIVERED]),
                    Order.created_at >= start_date,
                    Order.created_at <= end_date
                )
            )
            .group_by(Order.source)
            .order_by(desc(func.sum(OrderItem.quantity)))
        )

        if product_id:
            query = query.where(OrderItem.product_id == product_id)

        result = await self.db.execute(query)
        rows = result.all()

        return [
            {
                "channel": row.channel if row.channel else "UNKNOWN",
                "total_quantity": Decimal(str(row.total_quantity or 0)),
                "total_revenue": Decimal(str(row.total_revenue or 0)),
                "order_count": row.order_count
            }
            for row in rows
        ]

    async def get_demand_by_region(
        self,
        start_date: date,
        end_date: date,
        product_id: Optional[uuid.UUID] = None,
        category_id: Optional[uuid.UUID] = None
    ) -> List[Dict[str, Any]]:
        """
        Get demand aggregated by region.
        """
        query = (
            select(
                Region.id.label("region_id"),
                Region.name.label("region_name"),
                func.sum(OrderItem.quantity).label("total_quantity"),
                func.sum(OrderItem.total_amount).label("total_revenue"),
                func.count(Order.id.distinct()).label("order_count")
            )
            .join(Order, Order.region_id == Region.id)
            .join(OrderItem, OrderItem.order_id == Order.id)
            .join(Product, OrderItem.product_id == Product.id)
            .where(
                and_(
                    Order.status.in_([OrderStatus.DELIVERED, OrderStatus.PARTIALLY_DELIVERED]),
                    Order.created_at >= start_date,
                    Order.created_at <= end_date
                )
            )
            .group_by(Region.id, Region.name)
            .order_by(desc(func.sum(OrderItem.quantity)))
        )

        if product_id:
            query = query.where(OrderItem.product_id == product_id)
        if category_id:
            query = query.where(Product.category_id == category_id)

        result = await self.db.execute(query)
        rows = result.all()

        return [
            {
                "region_id": row.region_id,
                "region_name": row.region_name,
                "total_quantity": Decimal(str(row.total_quantity or 0)),
                "total_revenue": Decimal(str(row.total_revenue or 0)),
                "order_count": row.order_count
            }
            for row in rows
        ]

    # ==================== Demand Statistics ====================

    async def calculate_demand_statistics(
        self,
        product_id: Optional[uuid.UUID] = None,
        category_id: Optional[uuid.UUID] = None,
        warehouse_id: Optional[uuid.UUID] = None,
        lookback_days: int = 365
    ) -> Dict[str, Any]:
        """
        Calculate demand statistics for inventory optimization.

        Returns:
        - avg_daily_demand
        - demand_std_dev
        - coefficient_of_variation
        - seasonality_index
        - trend
        """
        end_date = date.today()
        start_date = end_date - timedelta(days=lookback_days)

        # Get daily demand data
        daily_demand = await self.get_historical_demand(
            product_id=product_id,
            category_id=category_id,
            warehouse_id=warehouse_id,
            start_date=start_date,
            end_date=end_date,
            granularity=ForecastGranularity.DAILY
        )

        if not daily_demand:
            return {
                "avg_daily_demand": Decimal("0"),
                "demand_std_dev": Decimal("0"),
                "coefficient_of_variation": 0.0,
                "max_demand": Decimal("0"),
                "min_demand": Decimal("0"),
                "seasonality_detected": False,
                "trend": "stable"
            }

        # Extract quantities
        quantities = [float(d["quantity"]) for d in daily_demand]

        # Calculate statistics
        n = len(quantities)
        mean_demand = sum(quantities) / n

        # Standard deviation
        variance = sum((q - mean_demand) ** 2 for q in quantities) / n
        std_dev = math.sqrt(variance)

        # Coefficient of variation
        cv = std_dev / mean_demand if mean_demand > 0 else 0

        # Trend detection (simple linear regression slope)
        if n > 1:
            x_mean = (n - 1) / 2
            numerator = sum((i - x_mean) * (quantities[i] - mean_demand) for i in range(n))
            denominator = sum((i - x_mean) ** 2 for i in range(n))
            slope = numerator / denominator if denominator > 0 else 0

            # Classify trend
            if slope > mean_demand * 0.001:
                trend = "increasing"
            elif slope < -mean_demand * 0.001:
                trend = "decreasing"
            else:
                trend = "stable"
        else:
            trend = "stable"

        # Seasonality detection (simple check based on monthly variance)
        monthly_demand = await self.get_historical_demand(
            product_id=product_id,
            category_id=category_id,
            warehouse_id=warehouse_id,
            start_date=start_date,
            end_date=end_date,
            granularity=ForecastGranularity.MONTHLY
        )

        if len(monthly_demand) >= 12:
            monthly_quantities = [float(d["quantity"]) for d in monthly_demand]
            monthly_mean = sum(monthly_quantities) / len(monthly_quantities)
            monthly_variance = sum((q - monthly_mean) ** 2 for q in monthly_quantities) / len(monthly_quantities)
            monthly_cv = math.sqrt(monthly_variance) / monthly_mean if monthly_mean > 0 else 0
            seasonality_detected = monthly_cv > 0.3  # 30% variation suggests seasonality
        else:
            seasonality_detected = False

        return {
            "avg_daily_demand": Decimal(str(round(mean_demand, 4))),
            "demand_std_dev": Decimal(str(round(std_dev, 4))),
            "coefficient_of_variation": round(cv, 4),
            "max_demand": Decimal(str(max(quantities))),
            "min_demand": Decimal(str(min(quantities))),
            "seasonality_detected": seasonality_detected,
            "trend": trend,
            "data_points": n
        }

    # ==================== External Factors ====================

    async def get_active_external_factors(
        self,
        product_id: Optional[uuid.UUID] = None,
        category_id: Optional[uuid.UUID] = None,
        region_id: Optional[uuid.UUID] = None,
        for_date: date = None
    ) -> List[ExternalFactor]:
        """
        Get active external factors affecting demand.
        """
        if for_date is None:
            for_date = date.today()

        query = (
            select(ExternalFactor)
            .where(
                and_(
                    ExternalFactor.is_active == True,
                    ExternalFactor.start_date <= for_date,
                    ExternalFactor.end_date >= for_date
                )
            )
        )

        # Filter by scope
        conditions = [ExternalFactor.applies_to_all == True]

        if product_id:
            conditions.append(ExternalFactor.product_id == product_id)
        if category_id:
            conditions.append(ExternalFactor.category_id == category_id)
        if region_id:
            conditions.append(ExternalFactor.region_id == region_id)

        query = query.where(or_(*conditions))

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def calculate_external_factor_impact(
        self,
        base_forecast: Decimal,
        factors: List[ExternalFactor]
    ) -> Tuple[Decimal, List[Dict[str, Any]]]:
        """
        Calculate the combined impact of external factors on forecast.

        Returns: (adjusted_forecast, factor_details)
        """
        adjusted_forecast = base_forecast
        factor_details = []

        for factor in factors:
            original = adjusted_forecast

            # Apply multiplicative impact
            if factor.impact_multiplier != 1.0:
                adjusted_forecast = adjusted_forecast * Decimal(str(factor.impact_multiplier))

            # Apply absolute impact
            if factor.impact_absolute:
                adjusted_forecast = adjusted_forecast + factor.impact_absolute

            factor_details.append({
                "factor_id": str(factor.id),
                "factor_name": factor.factor_name,
                "factor_type": factor.factor_type,  # Already a string (VARCHAR)
                "original_forecast": float(original),
                "adjusted_forecast": float(adjusted_forecast),
                "impact_pct": round((float(adjusted_forecast) - float(original)) / float(original) * 100, 2) if float(original) > 0 else 0
            })

        return adjusted_forecast, factor_details

    # ==================== Forecast Generation ====================

    async def generate_forecast_code(self) -> str:
        """Generate unique forecast code."""
        today = datetime.now(timezone.utc)
        prefix = f"FC{today.strftime('%Y%m%d')}"

        # Get count of forecasts created today
        result = await self.db.execute(
            select(func.count(DemandForecast.id))
            .where(DemandForecast.forecast_code.like(f"{prefix}%"))
        )
        count = result.scalar() or 0

        return f"{prefix}{count + 1:04d}"

    async def create_demand_forecast(
        self,
        forecast_name: str,
        forecast_level: ForecastLevel,
        granularity: ForecastGranularity,
        forecast_start_date: date,
        forecast_end_date: date,
        forecast_data: List[Dict[str, Any]],
        algorithm: ForecastAlgorithm = ForecastAlgorithm.ENSEMBLE,
        product_id: Optional[uuid.UUID] = None,
        category_id: Optional[uuid.UUID] = None,
        warehouse_id: Optional[uuid.UUID] = None,
        region_id: Optional[uuid.UUID] = None,
        channel: Optional[str] = None,
        accuracy_metrics: Optional[Dict[str, float]] = None,
        user_id: Optional[uuid.UUID] = None,
        notes: Optional[str] = None
    ) -> DemandForecast:
        """
        Create and save a new demand forecast.
        """
        forecast_code = await self.generate_forecast_code()

        # Calculate aggregated metrics
        total_qty = sum(Decimal(str(d.get("forecasted_qty", 0))) for d in forecast_data)
        horizon_days = (forecast_end_date - forecast_start_date).days + 1
        avg_daily = total_qty / Decimal(str(horizon_days)) if horizon_days > 0 else Decimal("0")
        peak_demand = max(Decimal(str(d.get("forecasted_qty", 0))) for d in forecast_data) if forecast_data else Decimal("0")

        forecast = DemandForecast(
            forecast_code=forecast_code,
            forecast_name=forecast_name,
            forecast_level=forecast_level,
            granularity=granularity,
            product_id=product_id,
            category_id=category_id,
            warehouse_id=warehouse_id,
            region_id=region_id,
            channel=channel,
            forecast_start_date=forecast_start_date,
            forecast_end_date=forecast_end_date,
            forecast_horizon_days=horizon_days,
            forecast_data=forecast_data,
            total_forecasted_qty=total_qty,
            avg_daily_demand=avg_daily,
            peak_demand=peak_demand,
            algorithm_used=algorithm,
            mape=accuracy_metrics.get("mape") if accuracy_metrics else None,
            mae=accuracy_metrics.get("mae") if accuracy_metrics else None,
            rmse=accuracy_metrics.get("rmse") if accuracy_metrics else None,
            forecast_bias=accuracy_metrics.get("bias") if accuracy_metrics else None,
            status=ForecastStatus.DRAFT,
            created_by_id=user_id,
            notes=notes
        )

        self.db.add(forecast)
        await self.db.commit()
        await self.db.refresh(forecast)

        return forecast

    async def get_forecast(self, forecast_id: uuid.UUID) -> Optional[DemandForecast]:
        """Get a forecast by ID."""
        result = await self.db.execute(
            select(DemandForecast)
            .options(
                selectinload(DemandForecast.product),
                selectinload(DemandForecast.category),
                selectinload(DemandForecast.warehouse),
                selectinload(DemandForecast.region),
                selectinload(DemandForecast.adjustments)
            )
            .where(DemandForecast.id == forecast_id)
        )
        return result.scalar_one_or_none()

    async def list_forecasts(
        self,
        product_id: Optional[uuid.UUID] = None,
        category_id: Optional[uuid.UUID] = None,
        status: Optional[ForecastStatus] = None,
        forecast_level: Optional[ForecastLevel] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Tuple[List[DemandForecast], int]:
        """List forecasts with filters."""
        query = select(DemandForecast).where(DemandForecast.is_active == True)

        if product_id:
            query = query.where(DemandForecast.product_id == product_id)
        if category_id:
            query = query.where(DemandForecast.category_id == category_id)
        if status:
            query = query.where(DemandForecast.status == status)
        if forecast_level:
            query = query.where(DemandForecast.forecast_level == forecast_level)

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        count_result = await self.db.execute(count_query)
        total = count_result.scalar()

        # Get paginated results
        query = query.order_by(desc(DemandForecast.created_at)).offset(offset).limit(limit)
        result = await self.db.execute(query)
        forecasts = list(result.scalars().all())

        return forecasts, total

    # ==================== Forecast Workflow ====================

    async def submit_for_review(
        self,
        forecast_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> DemandForecast:
        """Submit forecast for review."""
        forecast = await self.get_forecast(forecast_id)
        if not forecast:
            raise ValueError(f"Forecast {forecast_id} not found")

        if forecast.status != ForecastStatus.DRAFT:
            raise ValueError(f"Forecast must be in DRAFT status to submit for review")

        forecast.status = ForecastStatus.PENDING_REVIEW.value
        forecast.submitted_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(forecast)

        return forecast

    async def approve_forecast(
        self,
        forecast_id: uuid.UUID,
        user_id: uuid.UUID,
        comments: Optional[str] = None
    ) -> DemandForecast:
        """Approve a forecast."""
        forecast = await self.get_forecast(forecast_id)
        if not forecast:
            raise ValueError(f"Forecast {forecast_id} not found")

        if forecast.status not in [ForecastStatus.PENDING_REVIEW, ForecastStatus.UNDER_REVIEW]:
            raise ValueError(f"Forecast must be pending review to approve")

        forecast.status = ForecastStatus.APPROVED.value
        forecast.approved_by_id = user_id
        forecast.approved_at = datetime.now(timezone.utc)
        if comments:
            forecast.notes = (forecast.notes or "") + f"\n[Approval Comment]: {comments}"

        await self.db.commit()
        await self.db.refresh(forecast)

        return forecast

    async def reject_forecast(
        self,
        forecast_id: uuid.UUID,
        user_id: uuid.UUID,
        reason: str
    ) -> DemandForecast:
        """Reject a forecast."""
        forecast = await self.get_forecast(forecast_id)
        if not forecast:
            raise ValueError(f"Forecast {forecast_id} not found")

        forecast.status = ForecastStatus.REJECTED.value
        forecast.reviewed_by_id = user_id
        forecast.reviewed_at = datetime.now(timezone.utc)
        forecast.notes = (forecast.notes or "") + f"\n[Rejection Reason]: {reason}"

        await self.db.commit()
        await self.db.refresh(forecast)

        return forecast

    async def request_adjustment(
        self,
        forecast_id: uuid.UUID,
        user_id: uuid.UUID,
        reason: str
    ) -> DemandForecast:
        """Request changes to a forecast."""
        forecast = await self.get_forecast(forecast_id)
        if not forecast:
            raise ValueError(f"Forecast {forecast_id} not found")

        forecast.status = ForecastStatus.ADJUSTMENT_REQUESTED.value
        forecast.reviewed_by_id = user_id
        forecast.reviewed_at = datetime.now(timezone.utc)
        forecast.notes = (forecast.notes or "") + f"\n[Adjustment Requested]: {reason}"

        await self.db.commit()
        await self.db.refresh(forecast)

        return forecast

    # ==================== Forecast Adjustments ====================

    async def create_adjustment(
        self,
        forecast_id: uuid.UUID,
        adjustment_date: date,
        adjusted_qty: Decimal,
        adjustment_reason: str,
        user_id: uuid.UUID,
        justification: Optional[str] = None
    ) -> ForecastAdjustment:
        """Create a manual adjustment to a forecast."""
        forecast = await self.get_forecast(forecast_id)
        if not forecast:
            raise ValueError(f"Forecast {forecast_id} not found")

        # Find original quantity for the date
        original_qty = Decimal("0")
        for data_point in forecast.forecast_data:
            if str(data_point.get("date")) == str(adjustment_date):
                original_qty = Decimal(str(data_point.get("forecasted_qty", 0)))
                break

        adjustment_pct = float((adjusted_qty - original_qty) / original_qty * 100) if original_qty > 0 else 0

        adjustment = ForecastAdjustment(
            forecast_id=forecast_id,
            adjustment_date=adjustment_date,
            original_qty=original_qty,
            adjusted_qty=adjusted_qty,
            adjustment_pct=adjustment_pct,
            adjustment_reason=adjustment_reason,
            justification=justification,
            adjusted_by_id=user_id,
            status=ForecastStatus.PENDING_REVIEW
        )

        self.db.add(adjustment)
        await self.db.commit()
        await self.db.refresh(adjustment)

        return adjustment

    async def approve_adjustment(
        self,
        adjustment_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> ForecastAdjustment:
        """Approve a forecast adjustment and update the forecast."""
        result = await self.db.execute(
            select(ForecastAdjustment).where(ForecastAdjustment.id == adjustment_id)
        )
        adjustment = result.scalar_one_or_none()

        if not adjustment:
            raise ValueError(f"Adjustment {adjustment_id} not found")

        adjustment.status = ForecastStatus.APPROVED.value
        adjustment.approved_by_id = user_id
        adjustment.approved_at = datetime.now(timezone.utc)

        # Update the forecast data
        forecast = await self.get_forecast(adjustment.forecast_id)
        if forecast:
            updated_data = []
            for data_point in forecast.forecast_data:
                if str(data_point.get("date")) == str(adjustment.adjustment_date):
                    data_point["forecasted_qty"] = float(adjustment.adjusted_qty)
                    data_point["adjusted"] = True
                updated_data.append(data_point)
            forecast.forecast_data = updated_data

            # Recalculate totals
            forecast.total_forecasted_qty = sum(
                Decimal(str(d.get("forecasted_qty", 0))) for d in updated_data
            )

        await self.db.commit()
        await self.db.refresh(adjustment)

        return adjustment
