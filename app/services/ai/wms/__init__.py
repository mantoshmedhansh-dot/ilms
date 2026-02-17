"""
WMS AI Agents Module for ILMS.AI ERP

Provides AI-powered warehouse management capabilities:
- Anomaly Detection (z-score analysis on pick rates, inventory discrepancies)
- Smart Slotting (ABC velocity classification, pick-frequency scoring)
- Labor Forecasting (Holt-Winters on order volumes, shift staffing)
- Replenishment (Forward-pick bin monitoring, consumption rate analysis)
"""

from app.services.ai.wms.anomaly_detection import WMSAnomalyDetectionAgent
from app.services.ai.wms.smart_slotting import WMSSmartSlottingAgent
from app.services.ai.wms.labor_forecasting import WMSLaborForecastingAgent
from app.services.ai.wms.replenishment import WMSReplenishmentAgent
from app.services.ai.wms.command_center import WMSCommandCenter
from app.services.ai.wms.chatbot import WMSChatbotService

__all__ = [
    "WMSAnomalyDetectionAgent",
    "WMSSmartSlottingAgent",
    "WMSLaborForecastingAgent",
    "WMSReplenishmentAgent",
    "WMSCommandCenter",
    "WMSChatbotService",
]
