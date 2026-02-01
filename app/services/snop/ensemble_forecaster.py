"""
Ensemble Forecasting Service

Advanced demand forecasting using multiple algorithms:
- Holt-Winters Triple Exponential Smoothing
- ARIMA (Auto-Regressive Integrated Moving Average)
- Prophet-like decomposition (pure Python implementation)
- XGBoost-style gradient boosting (simplified)
- Simple Moving Average
- Weighted Ensemble combining all models

No external ML libraries required - pure Python/NumPy compatible implementation.
"""

import math
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Optional, Tuple, Any
from collections import defaultdict
import uuid

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.snop import (
    DemandForecast,
    ForecastAlgorithm,
    ForecastGranularity,
    ForecastLevel,
    ForecastStatus,
    ExternalFactor,
)
from app.services.snop.demand_planner import DemandPlannerService


class EnsembleForecaster:
    """
    Advanced ensemble forecasting combining multiple algorithms.

    Each algorithm produces forecasts, and the ensemble combines them
    using weighted averaging based on historical accuracy.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.demand_planner = DemandPlannerService(db)

    # ==================== Holt-Winters Triple Exponential Smoothing ====================

    def holt_winters(
        self,
        data: List[float],
        season_length: int = 7,
        alpha: float = 0.3,
        beta: float = 0.1,
        gamma: float = 0.2,
        forecast_periods: int = 30
    ) -> Tuple[List[float], Dict[str, float]]:
        """
        Holt-Winters Triple Exponential Smoothing for seasonal data.

        Returns: (forecasts, metrics)
        """
        if len(data) < season_length * 2:
            return self._simple_moving_average(data, forecast_periods)

        n = len(data)

        # Initialize level, trend, and seasonality
        level = sum(data[:season_length]) / season_length
        trend = (sum(data[season_length:2*season_length]) - sum(data[:season_length])) / (season_length ** 2)

        # Initial seasonal indices
        seasonals = []
        for i in range(season_length):
            seasonals.append(data[i] / level if level > 0 else 1.0)

        fitted = []

        # Fit the model
        for i in range(n):
            if i >= season_length:
                old_level = level
                level = alpha * (data[i] / seasonals[i % season_length]) + (1 - alpha) * (level + trend)
                trend = beta * (level - old_level) + (1 - beta) * trend
                seasonals[i % season_length] = gamma * (data[i] / level) + (1 - gamma) * seasonals[i % season_length]

            fitted.append((level + trend) * seasonals[i % season_length])

        # Generate forecasts
        forecasts = []
        for i in range(forecast_periods):
            forecast = (level + (i + 1) * trend) * seasonals[(n + i) % season_length]
            forecasts.append(max(0, forecast))

        # Calculate accuracy metrics
        metrics = self._calculate_accuracy(data, fitted)

        return forecasts, metrics

    # ==================== ARIMA-like Model ====================

    def arima_forecast(
        self,
        data: List[float],
        p: int = 3,  # AR order
        d: int = 1,  # Differencing order
        q: int = 1,  # MA order
        forecast_periods: int = 30
    ) -> Tuple[List[float], Dict[str, float]]:
        """
        Simplified ARIMA implementation.

        Uses autoregression with differencing and simple moving average of residuals.
        """
        if len(data) < 10:
            return self._simple_moving_average(data, forecast_periods)

        # Apply differencing
        diff_data = data.copy()
        for _ in range(d):
            diff_data = [diff_data[i] - diff_data[i-1] for i in range(1, len(diff_data))]

        n = len(diff_data)
        if n < p + q:
            return self._simple_moving_average(data, forecast_periods)

        # Fit AR model using simple regression
        ar_coeffs = self._fit_ar(diff_data, p)

        # Calculate residuals and fit MA
        residuals = self._calculate_residuals(diff_data, ar_coeffs, p)
        ma_coeff = sum(residuals[-q:]) / q if residuals else 0

        # Generate forecasts on differenced data
        diff_forecasts = []
        recent_values = diff_data[-p:] if len(diff_data) >= p else diff_data

        for i in range(forecast_periods):
            ar_part = sum(ar_coeffs[j] * recent_values[-(j+1)] for j in range(min(len(ar_coeffs), len(recent_values))))
            forecast = ar_part + ma_coeff
            diff_forecasts.append(forecast)
            recent_values.append(forecast)
            if len(recent_values) > p:
                recent_values.pop(0)

        # Integrate back (reverse differencing)
        forecasts = []
        last_value = data[-1]
        for df in diff_forecasts:
            for _ in range(d):
                last_value = last_value + df
            forecasts.append(max(0, last_value))

        # Calculate accuracy using fitted values
        fitted = self._fit_arima_values(data, ar_coeffs, d)
        metrics = self._calculate_accuracy(data[p+d:], fitted[p+d:]) if len(fitted) > p+d else {"mape": 50.0}

        return forecasts, metrics

    def _fit_ar(self, data: List[float], p: int) -> List[float]:
        """Fit AR coefficients using Yule-Walker equations (simplified)."""
        n = len(data)
        if n <= p:
            return [1.0 / p] * p

        # Calculate autocorrelations
        mean = sum(data) / n
        var = sum((x - mean) ** 2 for x in data) / n

        if var == 0:
            return [0.0] * p

        autocorr = []
        for lag in range(p + 1):
            corr = sum((data[i] - mean) * (data[i - lag] - mean) for i in range(lag, n)) / (n * var)
            autocorr.append(corr)

        # Simple approximation: use autocorrelations as coefficients (normalized)
        coeffs = autocorr[1:p+1]
        total = sum(abs(c) for c in coeffs) or 1
        coeffs = [c / total for c in coeffs]

        return coeffs

    def _calculate_residuals(self, data: List[float], ar_coeffs: List[float], p: int) -> List[float]:
        """Calculate residuals from AR model."""
        residuals = []
        for i in range(p, len(data)):
            predicted = sum(ar_coeffs[j] * data[i - j - 1] for j in range(len(ar_coeffs)))
            residuals.append(data[i] - predicted)
        return residuals

    def _fit_arima_values(self, data: List[float], ar_coeffs: List[float], d: int) -> List[float]:
        """Generate fitted values for ARIMA."""
        # Simplified: use AR model on original data
        fitted = data[:len(ar_coeffs)]
        for i in range(len(ar_coeffs), len(data)):
            pred = sum(ar_coeffs[j] * data[i - j - 1] for j in range(len(ar_coeffs)))
            fitted.append(pred)
        return fitted

    # ==================== Prophet-like Decomposition ====================

    def prophet_forecast(
        self,
        data: List[float],
        forecast_periods: int = 30,
        yearly_seasonality: bool = True,
        weekly_seasonality: bool = True
    ) -> Tuple[List[float], Dict[str, float]]:
        """
        Prophet-like additive decomposition forecasting.

        Decomposes time series into:
        - Trend (linear)
        - Yearly seasonality (Fourier series)
        - Weekly seasonality
        """
        if len(data) < 14:
            return self._simple_moving_average(data, forecast_periods)

        n = len(data)

        # Fit trend using linear regression
        x_mean = (n - 1) / 2
        y_mean = sum(data) / n
        numerator = sum((i - x_mean) * (data[i] - y_mean) for i in range(n))
        denominator = sum((i - x_mean) ** 2 for i in range(n))
        slope = numerator / denominator if denominator > 0 else 0
        intercept = y_mean - slope * x_mean

        # Extract trend
        trend = [intercept + slope * i for i in range(n)]

        # Detrend
        detrended = [data[i] - trend[i] for i in range(n)]

        # Extract weekly seasonality (if enough data)
        weekly_pattern = [0.0] * 7
        if n >= 14 and weekly_seasonality:
            for day in range(7):
                day_values = [detrended[i] for i in range(n) if i % 7 == day]
                weekly_pattern[day] = sum(day_values) / len(day_values) if day_values else 0

        # Extract yearly seasonality using simplified Fourier
        yearly_pattern = [0.0] * 365
        if n >= 90 and yearly_seasonality:
            # Use monthly averages as proxy
            monthly_values = defaultdict(list)
            for i in range(n):
                month = (i // 30) % 12
                monthly_values[month].append(detrended[i])

            for month in range(12):
                if monthly_values[month]:
                    avg = sum(monthly_values[month]) / len(monthly_values[month])
                    for day in range(30):
                        yearly_pattern[month * 30 + day] = avg

        # Generate forecasts
        forecasts = []
        for i in range(forecast_periods):
            future_idx = n + i
            trend_component = intercept + slope * future_idx
            weekly_component = weekly_pattern[future_idx % 7]
            yearly_component = yearly_pattern[future_idx % 365] if yearly_seasonality else 0

            forecast = trend_component + weekly_component + yearly_component
            forecasts.append(max(0, forecast))

        # Calculate fitted values and metrics
        fitted = []
        for i in range(n):
            fit_value = trend[i] + weekly_pattern[i % 7]
            if yearly_seasonality and n >= 90:
                fit_value += yearly_pattern[i % 365]
            fitted.append(fit_value)

        metrics = self._calculate_accuracy(data, fitted)

        return forecasts, metrics

    # ==================== Gradient Boosting (Simplified) ====================

    def gradient_boost_forecast(
        self,
        data: List[float],
        forecast_periods: int = 30,
        n_estimators: int = 10,
        learning_rate: float = 0.1
    ) -> Tuple[List[float], Dict[str, float]]:
        """
        Simplified gradient boosting for time series.

        Uses sequential learning of residuals with decision stumps.
        """
        if len(data) < 10:
            return self._simple_moving_average(data, forecast_periods)

        n = len(data)
        lookback = min(7, n - 1)

        # Create features: lagged values
        X = []
        y = []
        for i in range(lookback, n):
            features = data[i-lookback:i]
            X.append(features)
            y.append(data[i])

        if not X:
            return self._simple_moving_average(data, forecast_periods)

        # Initialize predictions with mean
        predictions = [sum(y) / len(y)] * len(y)
        learners = []

        # Boosting iterations
        for _ in range(n_estimators):
            # Calculate residuals
            residuals = [y[i] - predictions[i] for i in range(len(y))]

            # Fit a simple "stump" - just learn mean adjustment based on lag-1
            lag1_values = [X[i][0] for i in range(len(X))]
            median_lag1 = sorted(lag1_values)[len(lag1_values) // 2]

            above_median = [residuals[i] for i in range(len(residuals)) if lag1_values[i] >= median_lag1]
            below_median = [residuals[i] for i in range(len(residuals)) if lag1_values[i] < median_lag1]

            pred_above = sum(above_median) / len(above_median) if above_median else 0
            pred_below = sum(below_median) / len(below_median) if below_median else 0

            learner = {
                "threshold": median_lag1,
                "pred_above": pred_above * learning_rate,
                "pred_below": pred_below * learning_rate
            }
            learners.append(learner)

            # Update predictions
            for i in range(len(predictions)):
                if lag1_values[i] >= median_lag1:
                    predictions[i] += learner["pred_above"]
                else:
                    predictions[i] += learner["pred_below"]

        # Generate forecasts
        forecasts = []
        recent = list(data[-lookback:])

        for _ in range(forecast_periods):
            # Base prediction
            pred = sum(y) / len(y)

            # Apply learners
            for learner in learners:
                if recent[0] >= learner["threshold"]:
                    pred += learner["pred_above"]
                else:
                    pred += learner["pred_below"]

            forecasts.append(max(0, pred))
            recent.pop(0)
            recent.append(pred)

        # Calculate metrics
        fitted_full = [sum(y) / len(y)] * lookback + predictions
        metrics = self._calculate_accuracy(data, fitted_full)

        return forecasts, metrics

    # ==================== Simple Moving Average ====================

    def _simple_moving_average(
        self,
        data: List[float],
        forecast_periods: int,
        window: int = 7
    ) -> Tuple[List[float], Dict[str, float]]:
        """Simple moving average forecast."""
        if not data:
            return [0.0] * forecast_periods, {"mape": 100.0}

        window = min(window, len(data))
        avg = sum(data[-window:]) / window

        forecasts = [max(0, avg)] * forecast_periods
        metrics = {"mape": 30.0, "mae": abs(avg - sum(data) / len(data)), "rmse": 0.0}

        return forecasts, metrics

    # ==================== Accuracy Metrics ====================

    def _calculate_accuracy(self, actual: List[float], predicted: List[float]) -> Dict[str, float]:
        """Calculate forecast accuracy metrics."""
        if not actual or not predicted:
            return {"mape": 100.0, "mae": 0.0, "rmse": 0.0, "bias": 0.0}

        n = min(len(actual), len(predicted))
        if n == 0:
            return {"mape": 100.0, "mae": 0.0, "rmse": 0.0, "bias": 0.0}

        # MAPE - Mean Absolute Percentage Error
        ape_sum = 0
        valid_count = 0
        for i in range(n):
            if actual[i] != 0:
                ape_sum += abs(actual[i] - predicted[i]) / abs(actual[i])
                valid_count += 1
        mape = (ape_sum / valid_count * 100) if valid_count > 0 else 100.0

        # MAE - Mean Absolute Error
        mae = sum(abs(actual[i] - predicted[i]) for i in range(n)) / n

        # RMSE - Root Mean Square Error
        mse = sum((actual[i] - predicted[i]) ** 2 for i in range(n)) / n
        rmse = math.sqrt(mse)

        # Bias
        bias = sum(predicted[i] - actual[i] for i in range(n)) / n

        return {
            "mape": min(mape, 100.0),
            "mae": mae,
            "rmse": rmse,
            "bias": bias
        }

    # ==================== Ensemble Combination ====================

    async def ensemble_forecast(
        self,
        product_id: Optional[uuid.UUID] = None,
        category_id: Optional[uuid.UUID] = None,
        warehouse_id: Optional[uuid.UUID] = None,
        start_date: Optional[date] = None,
        lookback_days: int = 365,
        forecast_periods: int = 30,
        granularity: ForecastGranularity = ForecastGranularity.DAILY
    ) -> Dict[str, Any]:
        """
        Generate ensemble forecast combining multiple algorithms.

        Weights are based on historical accuracy (inverse MAPE).
        """
        # Get historical data
        end_date = start_date or date.today()
        hist_start = end_date - timedelta(days=lookback_days)

        historical = await self.demand_planner.get_historical_demand(
            product_id=product_id,
            category_id=category_id,
            warehouse_id=warehouse_id,
            start_date=hist_start,
            end_date=end_date,
            granularity=granularity
        )

        if not historical:
            return {
                "forecasts": [{"date": end_date + timedelta(days=i+1), "forecasted_qty": 0, "lower_bound": 0, "upper_bound": 0} for i in range(forecast_periods)],
                "algorithm": ForecastAlgorithm.ENSEMBLE,
                "accuracy_metrics": {"mape": 100.0},
                "model_weights": {}
            }

        data = [float(h["quantity"]) for h in historical]

        # Determine season length based on granularity
        if granularity == ForecastGranularity.DAILY:
            season_length = 7  # Weekly pattern
        elif granularity == ForecastGranularity.WEEKLY:
            season_length = 4  # Monthly pattern
        else:
            season_length = 12  # Yearly pattern

        # Run all models
        models = {}

        # Holt-Winters
        hw_forecasts, hw_metrics = self.holt_winters(data, season_length, forecast_periods=forecast_periods)
        models["holt_winters"] = {"forecasts": hw_forecasts, "mape": hw_metrics["mape"]}

        # ARIMA
        arima_forecasts, arima_metrics = self.arima_forecast(data, forecast_periods=forecast_periods)
        models["arima"] = {"forecasts": arima_forecasts, "mape": arima_metrics["mape"]}

        # Prophet-like
        prophet_forecasts, prophet_metrics = self.prophet_forecast(data, forecast_periods=forecast_periods)
        models["prophet"] = {"forecasts": prophet_forecasts, "mape": prophet_metrics["mape"]}

        # Gradient Boosting
        gb_forecasts, gb_metrics = self.gradient_boost_forecast(data, forecast_periods=forecast_periods)
        models["gradient_boost"] = {"forecasts": gb_forecasts, "mape": gb_metrics["mape"]}

        # Calculate weights (inverse MAPE, normalized)
        total_inverse_mape = sum(1 / max(m["mape"], 1) for m in models.values())
        weights = {}
        for name, model in models.items():
            weights[name] = (1 / max(model["mape"], 1)) / total_inverse_mape

        # Combine forecasts
        ensemble_forecasts = []
        for i in range(forecast_periods):
            weighted_sum = sum(
                models[name]["forecasts"][i] * weights[name]
                for name in models
            )
            ensemble_forecasts.append(max(0, weighted_sum))

        # Calculate confidence intervals (using variance across models)
        confidence_intervals = []
        for i in range(forecast_periods):
            model_predictions = [models[name]["forecasts"][i] for name in models]
            mean_pred = ensemble_forecasts[i]
            variance = sum((p - mean_pred) ** 2 for p in model_predictions) / len(model_predictions)
            std_dev = math.sqrt(variance)

            # 95% confidence interval (approx 1.96 std devs)
            margin = std_dev * 1.96
            confidence_intervals.append({
                "lower": max(0, mean_pred - margin),
                "upper": mean_pred + margin
            })

        # Build forecast data points
        forecast_data = []
        base_date = end_date
        for i in range(forecast_periods):
            if granularity == ForecastGranularity.DAILY:
                forecast_date = base_date + timedelta(days=i+1)
            elif granularity == ForecastGranularity.WEEKLY:
                forecast_date = base_date + timedelta(weeks=i+1)
            else:
                # Monthly - approximate
                forecast_date = base_date + timedelta(days=30*(i+1))

            forecast_data.append({
                "date": forecast_date.isoformat(),
                "forecasted_qty": round(ensemble_forecasts[i], 2),
                "lower_bound": round(confidence_intervals[i]["lower"], 2),
                "upper_bound": round(confidence_intervals[i]["upper"], 2)
            })

        # Calculate ensemble accuracy (weighted average of individual accuracies)
        ensemble_mape = sum(models[name]["mape"] * weights[name] for name in models)

        return {
            "forecasts": forecast_data,
            "algorithm": ForecastAlgorithm.ENSEMBLE,
            "accuracy_metrics": {
                "mape": round(ensemble_mape, 2),
                "individual_models": {name: {"mape": m["mape"], "weight": round(weights[name], 4)} for name, m in models.items()}
            },
            "model_weights": weights
        }

    # ==================== Single Algorithm Forecasting ====================

    async def single_algorithm_forecast(
        self,
        algorithm: ForecastAlgorithm,
        product_id: Optional[uuid.UUID] = None,
        category_id: Optional[uuid.UUID] = None,
        warehouse_id: Optional[uuid.UUID] = None,
        start_date: Optional[date] = None,
        lookback_days: int = 365,
        forecast_periods: int = 30,
        granularity: ForecastGranularity = ForecastGranularity.DAILY
    ) -> Dict[str, Any]:
        """
        Generate forecast using a single specified algorithm.
        """
        end_date = start_date or date.today()
        hist_start = end_date - timedelta(days=lookback_days)

        historical = await self.demand_planner.get_historical_demand(
            product_id=product_id,
            category_id=category_id,
            warehouse_id=warehouse_id,
            start_date=hist_start,
            end_date=end_date,
            granularity=granularity
        )

        if not historical:
            return {
                "forecasts": [],
                "algorithm": algorithm,
                "accuracy_metrics": {"mape": 100.0}
            }

        data = [float(h["quantity"]) for h in historical]

        # Determine season length
        season_length = 7 if granularity == ForecastGranularity.DAILY else 4

        # Run specified algorithm
        if algorithm == ForecastAlgorithm.HOLT_WINTERS:
            forecasts, metrics = self.holt_winters(data, season_length, forecast_periods=forecast_periods)
        elif algorithm == ForecastAlgorithm.ARIMA:
            forecasts, metrics = self.arima_forecast(data, forecast_periods=forecast_periods)
        elif algorithm == ForecastAlgorithm.PROPHET:
            forecasts, metrics = self.prophet_forecast(data, forecast_periods=forecast_periods)
        elif algorithm == ForecastAlgorithm.XGBOOST or algorithm == ForecastAlgorithm.LIGHTGBM:
            forecasts, metrics = self.gradient_boost_forecast(data, forecast_periods=forecast_periods)
        else:
            # Default to ensemble
            return await self.ensemble_forecast(
                product_id=product_id,
                category_id=category_id,
                warehouse_id=warehouse_id,
                start_date=start_date,
                lookback_days=lookback_days,
                forecast_periods=forecast_periods,
                granularity=granularity
            )

        # Build forecast data
        forecast_data = []
        base_date = end_date
        std_dev = metrics.get("rmse", 0) or (sum(data) / len(data) * 0.2)

        for i in range(forecast_periods):
            if granularity == ForecastGranularity.DAILY:
                forecast_date = base_date + timedelta(days=i+1)
            elif granularity == ForecastGranularity.WEEKLY:
                forecast_date = base_date + timedelta(weeks=i+1)
            else:
                forecast_date = base_date + timedelta(days=30*(i+1))

            margin = std_dev * 1.96 * (1 + 0.05 * i)  # Widen CI over time

            forecast_data.append({
                "date": forecast_date.isoformat(),
                "forecasted_qty": round(forecasts[i], 2),
                "lower_bound": round(max(0, forecasts[i] - margin), 2),
                "upper_bound": round(forecasts[i] + margin, 2)
            })

        return {
            "forecasts": forecast_data,
            "algorithm": algorithm,
            "accuracy_metrics": {
                "mape": round(metrics.get("mape", 100), 2),
                "mae": round(metrics.get("mae", 0), 2),
                "rmse": round(metrics.get("rmse", 0), 2),
                "bias": round(metrics.get("bias", 0), 2)
            }
        }
