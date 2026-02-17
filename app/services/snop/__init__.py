"""
S&OP (Sales and Operations Planning) Services

Provides comprehensive demand forecasting, supply planning, and inventory optimization:
- DemandPlannerService: Multi-level demand aggregation and forecasting
- EnsembleForecaster: Advanced AI forecasting with multiple algorithms
- MLForecaster: Production ML forecasting (Prophet, XGBoost, SARIMAX) with auto-model selection
- DemandClassifier: ABC-XYZ demand classification for strategy selection
- DemandSensor: Real-time demand sensing and signal processing
- SNOPService: Main orchestration service (supply planning, inventory optimization, scenarios)
- ScenarioEngine: Advanced scenario planning (Monte Carlo, P&L, sensitivity, comparison)
- PlanningAgents: Autonomous AI agents (exception detection, reorder, forecast bias, alert center)
- NLPlanner: Natural language planning interface (conversational S&OP queries)
"""

from app.services.snop.demand_planner import DemandPlannerService
from app.services.snop.ensemble_forecaster import EnsembleForecaster
from app.services.snop.ml_forecaster import MLForecaster, DemandClassifier
from app.services.snop.demand_sensor import DemandSensor
from app.services.snop.supply_optimizer import SupplyOptimizer
from app.services.snop.scenario_engine import ScenarioEngine
from app.services.snop.planning_agents import PlanningAgents
from app.services.snop.nl_planner import NLPlanner
from app.services.snop.snop_service import SNOPService
from app.services.snop.inventory_network_service import InventoryNetworkService

__all__ = [
    "DemandPlannerService",
    "EnsembleForecaster",
    "MLForecaster",
    "DemandClassifier",
    "DemandSensor",
    "SupplyOptimizer",
    "ScenarioEngine",
    "PlanningAgents",
    "NLPlanner",
    "SNOPService",
    "InventoryNetworkService",
]
