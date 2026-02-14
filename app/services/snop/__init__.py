"""
S&OP (Sales and Operations Planning) Services

Provides comprehensive demand forecasting, supply planning, and inventory optimization:
- DemandPlannerService: Multi-level demand aggregation and forecasting
- EnsembleForecaster: Advanced AI forecasting with multiple algorithms
- MLForecaster: Production ML forecasting (Prophet, XGBoost, SARIMAX) with auto-model selection
- DemandClassifier: ABC-XYZ demand classification for strategy selection
- SNOPService: Main orchestration service (supply planning, inventory optimization, scenarios)
"""

from app.services.snop.demand_planner import DemandPlannerService
from app.services.snop.ensemble_forecaster import EnsembleForecaster
from app.services.snop.ml_forecaster import MLForecaster, DemandClassifier
from app.services.snop.snop_service import SNOPService

__all__ = [
    "DemandPlannerService",
    "EnsembleForecaster",
    "MLForecaster",
    "DemandClassifier",
    "SNOPService",
]
