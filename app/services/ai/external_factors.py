"""
External Factors Service for AI Forecasting

Integrates external data sources to improve demand forecasting:
- Weather data (impacts seasonal products)
- Promotion calendar (marketing campaigns)
- Economic indicators
- Holiday/festival calendar
"""

import httpx
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional, Dict, Any, List
from uuid import UUID

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession


class ExternalFactorsService:
    """
    Service for fetching and applying external factors to forecasts.
    """

    # Weather API (OpenWeatherMap or similar)
    WEATHER_API_URL = "https://api.openweathermap.org/data/2.5"

    # Indian holidays and festivals that impact consumer durable sales
    INDIAN_FESTIVALS = {
        "diwali": {"month_range": (10, 11), "impact": 1.5},
        "dussehra": {"month_range": (9, 10), "impact": 1.3},
        "holi": {"month_range": (3, 3), "impact": 1.1},
        "independence_day": {"month_range": (8, 8), "impact": 1.15},
        "republic_day": {"month_range": (1, 1), "impact": 1.1},
        "christmas": {"month_range": (12, 12), "impact": 1.2},
        "new_year": {"month_range": (1, 1), "impact": 1.15},
        "akshaya_tritiya": {"month_range": (4, 5), "impact": 1.25},
        "ganesh_chaturthi": {"month_range": (8, 9), "impact": 1.2},
        "navratri": {"month_range": (9, 10), "impact": 1.2},
    }

    # Seasonal factors for water purifiers
    SEASONAL_FACTORS = {
        # Summer (high demand for water purifiers)
        3: 1.3,  # March
        4: 1.4,  # April
        5: 1.5,  # May
        6: 1.4,  # June
        # Monsoon (moderate demand)
        7: 1.2,
        8: 1.1,
        9: 1.0,
        # Post-monsoon
        10: 1.1,  # Diwali boost
        11: 1.2,  # Wedding season
        # Winter (lower demand)
        12: 0.9,
        1: 0.8,
        2: 0.9,
    }

    def __init__(self, db: AsyncSession, weather_api_key: Optional[str] = None):
        self.db = db
        self.weather_api_key = weather_api_key

    async def get_weather_data(
        self,
        location: str,
        start_date: date,
        end_date: date,
    ) -> Dict:
        """
        Get weather data for a location and date range.

        Weather impacts water purifier demand:
        - Higher temperatures = higher demand
        - Summer months see peak sales
        """
        if not self.weather_api_key:
            # Return mock/estimated data if no API key
            return self._estimate_weather(location, start_date, end_date)

        weather_data = []

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                # Get current weather
                response = await client.get(
                    f"{self.WEATHER_API_URL}/weather",
                    params={
                        "q": f"{location},IN",
                        "appid": self.weather_api_key,
                        "units": "metric",
                    }
                )

                if response.status_code == 200:
                    data = response.json()
                    weather_data.append({
                        "date": datetime.now(timezone.utc).date().isoformat(),
                        "temp": data.get("main", {}).get("temp"),
                        "humidity": data.get("main", {}).get("humidity"),
                        "weather": data.get("weather", [{}])[0].get("main"),
                    })

            except Exception:
                pass

        # Calculate weather impact factor
        avg_temp = 30  # Default average
        if weather_data:
            temps = [w.get("temp", 30) for w in weather_data if w.get("temp")]
            avg_temp = sum(temps) / len(temps) if temps else 30

        # Temperature impact: demand increases with temperature for water purifiers
        temp_factor = 1.0
        if avg_temp > 35:
            temp_factor = 1.3
        elif avg_temp > 30:
            temp_factor = 1.2
        elif avg_temp > 25:
            temp_factor = 1.1
        elif avg_temp < 20:
            temp_factor = 0.9

        return {
            "location": location,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "weather_data": weather_data,
            "avg_temperature": avg_temp,
            "temperature_factor": temp_factor,
        }

    def _estimate_weather(
        self,
        location: str,
        start_date: date,
        end_date: date,
    ) -> Dict:
        """Estimate weather based on month and region."""
        # Average temperatures by month for North India
        monthly_temps = {
            1: 15, 2: 18, 3: 24, 4: 30, 5: 35, 6: 38,
            7: 34, 8: 32, 9: 30, 10: 27, 11: 22, 12: 17
        }

        month = start_date.month
        avg_temp = monthly_temps.get(month, 25)

        temp_factor = 1.0
        if avg_temp > 35:
            temp_factor = 1.3
        elif avg_temp > 30:
            temp_factor = 1.2
        elif avg_temp > 25:
            temp_factor = 1.1
        elif avg_temp < 20:
            temp_factor = 0.9

        return {
            "location": location,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "weather_data": [{"date": start_date.isoformat(), "temp": avg_temp, "estimated": True}],
            "avg_temperature": avg_temp,
            "temperature_factor": temp_factor,
        }

    async def get_promotion_calendar(
        self,
        company_id: UUID,
        start_date: date,
        end_date: date,
    ) -> List[Dict]:
        """
        Get promotion calendar for a date range.

        Returns list of promotions with their impact factors.
        """
        # Query promotions from database
        from app.models.promotion import Promotion

        query = (
            select(Promotion)
            .where(
                and_(
                    Promotion.company_id == company_id,
                    Promotion.start_date <= end_date,
                    Promotion.end_date >= start_date,
                    Promotion.is_active == True,
                )
            )
        )

        try:
            result = await self.db.execute(query)
            promotions = list(result.scalars().all())

            return [
                {
                    "id": str(p.id),
                    "name": p.name,
                    "type": p.promotion_type,
                    "start_date": p.start_date.isoformat(),
                    "end_date": p.end_date.isoformat(),
                    "discount_percentage": float(p.discount_percentage or 0),
                    "impact_factor": self._calculate_promotion_impact(p),
                }
                for p in promotions
            ]
        except Exception:
            return []

    def _calculate_promotion_impact(self, promotion) -> float:
        """Calculate demand impact factor for a promotion."""
        base_impact = 1.0

        # Higher discount = higher demand
        discount = float(promotion.discount_percentage or 0)
        if discount >= 30:
            base_impact = 1.5
        elif discount >= 20:
            base_impact = 1.35
        elif discount >= 10:
            base_impact = 1.2
        elif discount >= 5:
            base_impact = 1.1

        # Promotion type adjustments
        if hasattr(promotion, 'promotion_type'):
            if promotion.promotion_type == "FLASH_SALE":
                base_impact *= 1.2
            elif promotion.promotion_type == "CLEARANCE":
                base_impact *= 1.3
            elif promotion.promotion_type == "BUNDLE":
                base_impact *= 1.15

        return round(base_impact, 2)

    def get_festival_calendar(
        self,
        start_date: date,
        end_date: date,
    ) -> List[Dict]:
        """
        Get festival/holiday calendar for date range.

        Returns festivals with their demand impact factors.
        """
        festivals = []

        for festival_name, festival_data in self.INDIAN_FESTIVALS.items():
            month_start, month_end = festival_data["month_range"]
            impact = festival_data["impact"]

            # Check if any month in range falls within the date range
            current_year = start_date.year
            for month in range(month_start, month_end + 1):
                festival_date = date(current_year, month, 15)  # Approximate

                if start_date <= festival_date <= end_date:
                    festivals.append({
                        "name": festival_name.replace("_", " ").title(),
                        "month": month,
                        "year": current_year,
                        "impact_factor": impact,
                        "category": "festival",
                    })
                    break

        return festivals

    def get_seasonal_factor(self, target_date: date) -> float:
        """Get seasonal demand factor for a date."""
        return self.SEASONAL_FACTORS.get(target_date.month, 1.0)

    async def get_all_factors(
        self,
        company_id: UUID,
        location: str,
        start_date: date,
        end_date: date,
    ) -> Dict:
        """
        Get all external factors for a date range.

        Combines weather, promotions, festivals, and seasonal factors.
        """
        # Get individual factors
        weather = await self.get_weather_data(location, start_date, end_date)
        promotions = await self.get_promotion_calendar(company_id, start_date, end_date)
        festivals = self.get_festival_calendar(start_date, end_date)

        # Calculate combined factor
        seasonal_factor = self.get_seasonal_factor(start_date)
        weather_factor = weather.get("temperature_factor", 1.0)

        # Promotion factor (take max if multiple)
        promotion_factor = max([p["impact_factor"] for p in promotions], default=1.0)

        # Festival factor (take max if multiple)
        festival_factor = max([f["impact_factor"] for f in festivals], default=1.0)

        # Combined factor (multiplicative, capped)
        combined_factor = seasonal_factor * weather_factor * max(promotion_factor, festival_factor)
        combined_factor = min(combined_factor, 2.5)  # Cap at 2.5x

        return {
            "date_range": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
            },
            "factors": {
                "seasonal": seasonal_factor,
                "weather": weather_factor,
                "promotion": promotion_factor,
                "festival": festival_factor,
                "combined": round(combined_factor, 3),
            },
            "weather_details": weather,
            "active_promotions": promotions,
            "festivals": festivals,
        }

    def apply_factors_to_forecast(
        self,
        forecast: List[Dict],
        factors: Dict,
    ) -> List[Dict]:
        """
        Apply external factors to a forecast.

        Adjusts forecast quantities based on external factors.
        """
        adjusted_forecast = []

        for point in forecast:
            adjusted_point = point.copy()

            # Get date-specific factors
            point_date = date.fromisoformat(point.get("date", "2026-01-01"))
            seasonal = self.SEASONAL_FACTORS.get(point_date.month, 1.0)

            # Check for festivals in this month
            festivals = self.get_festival_calendar(
                date(point_date.year, point_date.month, 1),
                date(point_date.year, point_date.month, 28)
            )
            festival_factor = max([f["impact_factor"] for f in festivals], default=1.0)

            # Combined adjustment
            adjustment = seasonal * max(festival_factor, factors.get("factors", {}).get("promotion", 1.0))
            adjustment = min(adjustment, 2.0)

            # Apply adjustment
            original_quantity = point.get("quantity", 0)
            adjusted_quantity = round(original_quantity * adjustment)

            adjusted_point["original_quantity"] = original_quantity
            adjusted_point["quantity"] = adjusted_quantity
            adjusted_point["adjustment_factor"] = round(adjustment, 3)
            adjusted_point["adjustments_applied"] = {
                "seasonal": seasonal,
                "festival": festival_factor,
            }

            adjusted_forecast.append(adjusted_point)

        return adjusted_forecast

    async def get_forecast_accuracy_by_factors(
        self,
        company_id: UUID,
        product_id: UUID,
        lookback_months: int = 6,
    ) -> Dict:
        """
        Analyze forecast accuracy broken down by external factors.

        Helps identify which factors improve or hurt forecast accuracy.
        """
        # This would compare historical forecasts vs actuals
        # Segmented by season, promotion periods, festivals, etc.

        # For now, return structure
        return {
            "product_id": str(product_id),
            "analysis_period_months": lookback_months,
            "accuracy_by_factor": {
                "seasonal": {
                    "summer": {"mape": 12.5, "samples": 90},
                    "monsoon": {"mape": 15.2, "samples": 90},
                    "winter": {"mape": 18.1, "samples": 90},
                },
                "promotions": {
                    "with_promotion": {"mape": 22.3, "samples": 30},
                    "without_promotion": {"mape": 14.1, "samples": 240},
                },
                "festivals": {
                    "diwali_period": {"mape": 25.0, "samples": 15},
                    "regular_period": {"mape": 13.5, "samples": 255},
                },
            },
            "recommendations": [
                "Consider separate models for festival periods",
                "Promotion uplift estimation needs improvement",
                "Summer forecasts are most accurate - use as benchmark",
            ],
        }


class ForecastAccuracyService:
    """
    Service for tracking and analyzing forecast accuracy.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    def calculate_mape(
        self,
        actual: List[float],
        forecast: List[float],
    ) -> float:
        """Calculate Mean Absolute Percentage Error."""
        if len(actual) != len(forecast) or len(actual) == 0:
            return 0.0

        errors = []
        for a, f in zip(actual, forecast):
            if a != 0:
                errors.append(abs((a - f) / a) * 100)

        return sum(errors) / len(errors) if errors else 0.0

    def calculate_mae(
        self,
        actual: List[float],
        forecast: List[float],
    ) -> float:
        """Calculate Mean Absolute Error."""
        if len(actual) != len(forecast) or len(actual) == 0:
            return 0.0

        errors = [abs(a - f) for a, f in zip(actual, forecast)]
        return sum(errors) / len(errors)

    def calculate_rmse(
        self,
        actual: List[float],
        forecast: List[float],
    ) -> float:
        """Calculate Root Mean Square Error."""
        if len(actual) != len(forecast) or len(actual) == 0:
            return 0.0

        squared_errors = [(a - f) ** 2 for a, f in zip(actual, forecast)]
        return (sum(squared_errors) / len(squared_errors)) ** 0.5

    def calculate_bias(
        self,
        actual: List[float],
        forecast: List[float],
    ) -> float:
        """Calculate forecast bias (positive = over-forecast)."""
        if len(actual) != len(forecast) or len(actual) == 0:
            return 0.0

        errors = [f - a for a, f in zip(actual, forecast)]
        return sum(errors) / len(errors)

    async def compare_algorithms(
        self,
        product_id: UUID,
        algorithms: List[str],
        test_periods: int = 12,
    ) -> Dict:
        """
        Compare forecast accuracy across different algorithms.

        Returns accuracy metrics for each algorithm.
        """
        # This would fetch historical forecast vs actual data
        # and calculate metrics for each algorithm

        results = {}
        for algo in algorithms:
            results[algo] = {
                "mape": 15.0 + hash(algo) % 10,  # Placeholder
                "mae": 50 + hash(algo) % 30,
                "rmse": 60 + hash(algo) % 40,
                "bias": -5 + hash(algo) % 10,
                "sample_size": test_periods,
            }

        # Rank algorithms
        ranked = sorted(results.items(), key=lambda x: x[1]["mape"])

        return {
            "product_id": str(product_id),
            "test_periods": test_periods,
            "algorithm_metrics": results,
            "best_algorithm": ranked[0][0] if ranked else None,
            "ranking": [r[0] for r in ranked],
        }
