"""
AI Services Module for ILMS.AI ERP

This module provides AI-powered capabilities:
- Demand Forecasting (Time-series prediction)
- Payment Prediction (Cash flow intelligence)
- Predictive Maintenance (Service scheduling)
- AI Chatbot (Natural language ERP queries)
- Smart Allocation (Logistics optimization)
"""

from app.services.ai.demand_forecasting import DemandForecastingService
from app.services.ai.payment_prediction import PaymentPredictionService
from app.services.ai.predictive_maintenance import PredictiveMaintenanceService
from app.services.ai.chatbot import ERPChatbotService

__all__ = [
    "DemandForecastingService",
    "PaymentPredictionService",
    "PredictiveMaintenanceService",
    "ERPChatbotService",
]
