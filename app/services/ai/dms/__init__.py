"""
DMS AI Agents Module for ILMS.AI ERP

Provides AI-powered distribution management capabilities:
- Dealer Performance (achievement scoring, payment compliance, growth tracking)
- Collection Optimizer (aging analysis, payment prediction, priority ranking)
- Scheme Effectiveness (ROI, budget utilization, participation rates)
- Demand Sensing (dealer trends, retailer velocity, seasonal forecasting)
"""

from app.services.ai.dms.dealer_performance import DMSDealerPerformanceAgent
from app.services.ai.dms.collection_optimizer import DMSCollectionOptimizerAgent
from app.services.ai.dms.scheme_effectiveness import DMSSchemeEffectivenessAgent
from app.services.ai.dms.demand_sensing import DMSDemandSensingAgent
from app.services.ai.dms.command_center import DMSCommandCenter
from app.services.ai.dms.chatbot import DMSChatbotService

__all__ = [
    "DMSDealerPerformanceAgent",
    "DMSCollectionOptimizerAgent",
    "DMSSchemeEffectivenessAgent",
    "DMSDemandSensingAgent",
    "DMSCommandCenter",
    "DMSChatbotService",
]
