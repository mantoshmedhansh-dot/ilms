"""
OMS AI Command Center

Aggregator for all 5 OMS AI agents.
Returns combined status, alerts, and recommendations.
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.ai.oms.fraud_detection import OMSFraudDetectionAgent
from app.services.ai.oms.smart_routing import OMSSmartRoutingAgent
from app.services.ai.oms.delivery_promise import OMSDeliveryPromiseAgent
from app.services.ai.oms.order_prioritization import OMSOrderPrioritizationAgent
from app.services.ai.oms.returns_prediction import OMSReturnsPredictionAgent


class OMSCommandCenter:
    """
    Aggregates all OMS AI agents into a unified command center.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.fraud_agent = OMSFraudDetectionAgent(db)
        self.routing_agent = OMSSmartRoutingAgent(db)
        self.delivery_agent = OMSDeliveryPromiseAgent(db)
        self.priority_agent = OMSOrderPrioritizationAgent(db)
        self.returns_agent = OMSReturnsPredictionAgent(db)

    async def get_dashboard(self) -> Dict:
        """Get full OMS AI dashboard data."""
        statuses = [
            await self.fraud_agent.get_status(),
            await self.routing_agent.get_status(),
            await self.delivery_agent.get_status(),
            await self.priority_agent.get_status(),
            await self.returns_agent.get_status(),
        ]

        all_recommendations = []
        for agent in [self.fraud_agent, self.routing_agent, self.delivery_agent,
                     self.priority_agent, self.returns_agent]:
            recs = await agent.get_recommendations()
            all_recommendations.extend(recs)

        severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        all_recommendations.sort(key=lambda x: severity_order.get(x.get("severity", "LOW"), 4))

        severity_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for rec in all_recommendations:
            sev = rec.get("severity", "LOW")
            if sev in severity_counts:
                severity_counts[sev] += 1

        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "agents": statuses,
            "summary": {
                "total_alerts": len(all_recommendations),
                "by_severity": severity_counts,
                "agents_ready": sum(1 for s in statuses if s["status"] in ("completed", "idle")),
                "agents_total": len(statuses),
            },
            "recommendations": all_recommendations[:30],
        }

    async def run_agent(self, agent_name: str, **kwargs) -> Dict:
        """Run a specific agent."""
        agents = {
            "fraud-detection": self.fraud_agent,
            "smart-routing": self.routing_agent,
            "delivery-promise": self.delivery_agent,
            "order-prioritization": self.priority_agent,
            "returns-prediction": self.returns_agent,
        }
        agent = agents.get(agent_name)
        if not agent:
            return {"error": f"Unknown agent: {agent_name}", "available": list(agents.keys())}
        return await agent.analyze(**kwargs)

    async def get_agent_status(self, agent_name: str) -> Dict:
        agents = {
            "fraud-detection": self.fraud_agent,
            "smart-routing": self.routing_agent,
            "delivery-promise": self.delivery_agent,
            "order-prioritization": self.priority_agent,
            "returns-prediction": self.returns_agent,
        }
        agent = agents.get(agent_name)
        if not agent:
            return {"error": f"Unknown agent: {agent_name}"}
        return await agent.get_status()

    async def get_agent_recommendations(self, agent_name: str) -> List[Dict]:
        agents = {
            "fraud-detection": self.fraud_agent,
            "smart-routing": self.routing_agent,
            "delivery-promise": self.delivery_agent,
            "order-prioritization": self.priority_agent,
            "returns-prediction": self.returns_agent,
        }
        agent = agents.get(agent_name)
        if not agent:
            return []
        return await agent.get_recommendations()

    async def get_capabilities(self) -> Dict:
        statuses = [
            await self.fraud_agent.get_status(),
            await self.routing_agent.get_status(),
            await self.delivery_agent.get_status(),
            await self.priority_agent.get_status(),
            await self.returns_agent.get_status(),
        ]
        return {
            "module": "OMS AI",
            "description": "AI-powered order management intelligence",
            "agents": statuses,
            "total_agents": len(statuses),
        }
