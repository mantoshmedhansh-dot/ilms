"""
OMS AI Agents Module for ILMS.AI ERP

Provides AI-powered order management capabilities:
- Fraud Detection (weighted scoring, velocity checks, risk assessment)
- Smart Routing (warehouse scoring, cost optimization, split orders)
- Delivery Promise / ATP (inventory check, transit time, confidence)
- Order Prioritization (value, SLA urgency, customer tier, aging)
- Returns Prediction (return probability, risk assessment)
"""

from app.services.ai.oms.fraud_detection import OMSFraudDetectionAgent
from app.services.ai.oms.smart_routing import OMSSmartRoutingAgent
from app.services.ai.oms.delivery_promise import OMSDeliveryPromiseAgent
from app.services.ai.oms.order_prioritization import OMSOrderPrioritizationAgent
from app.services.ai.oms.returns_prediction import OMSReturnsPredictionAgent
from app.services.ai.oms.command_center import OMSCommandCenter
from app.services.ai.oms.chatbot import OMSChatbotService

__all__ = [
    "OMSFraudDetectionAgent",
    "OMSSmartRoutingAgent",
    "OMSDeliveryPromiseAgent",
    "OMSOrderPrioritizationAgent",
    "OMSReturnsPredictionAgent",
    "OMSCommandCenter",
    "OMSChatbotService",
]
