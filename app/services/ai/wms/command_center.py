"""
WMS AI Command Center

Aggregator that instantiates all 4 WMS AI agents and returns
combined status, alerts, and recommendations.
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.ai.wms.anomaly_detection import WMSAnomalyDetectionAgent
from app.services.ai.wms.smart_slotting import WMSSmartSlottingAgent
from app.services.ai.wms.labor_forecasting import WMSLaborForecastingAgent
from app.services.ai.wms.replenishment import WMSReplenishmentAgent


class WMSCommandCenter:
    """
    Aggregates all WMS AI agents into a unified command center.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.anomaly_agent = WMSAnomalyDetectionAgent(db)
        self.slotting_agent = WMSSmartSlottingAgent(db)
        self.labor_agent = WMSLaborForecastingAgent(db)
        self.replenishment_agent = WMSReplenishmentAgent(db)

    async def get_dashboard(self, warehouse_id: Optional[UUID] = None) -> Dict:
        """Get full dashboard data from all agents."""
        # Get status from all agents
        statuses = [
            await self.anomaly_agent.get_status(),
            await self.slotting_agent.get_status(),
            await self.labor_agent.get_status(),
            await self.replenishment_agent.get_status(),
        ]

        # Collect all recommendations
        all_recommendations = []
        for agent in [self.anomaly_agent, self.slotting_agent, self.labor_agent, self.replenishment_agent]:
            recs = await agent.get_recommendations()
            all_recommendations.extend(recs)

        # Sort by severity
        severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        all_recommendations.sort(key=lambda x: severity_order.get(x.get("severity", "LOW"), 4))

        # Severity summary
        severity_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for rec in all_recommendations:
            sev = rec.get("severity", "LOW")
            if sev in severity_counts:
                severity_counts[sev] += 1

        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "warehouse_id": str(warehouse_id) if warehouse_id else "all",
            "agents": statuses,
            "summary": {
                "total_alerts": len(all_recommendations),
                "by_severity": severity_counts,
                "agents_ready": sum(1 for s in statuses if s["status"] in ("completed", "idle")),
                "agents_total": len(statuses),
            },
            "recommendations": all_recommendations[:30],
        }

    async def run_agent(self, agent_name: str, warehouse_id: Optional[UUID] = None, **kwargs) -> Dict:
        """Run a specific agent."""
        agents = {
            "anomaly-detection": self.anomaly_agent,
            "smart-slotting": self.slotting_agent,
            "labor-forecasting": self.labor_agent,
            "replenishment": self.replenishment_agent,
        }

        agent = agents.get(agent_name)
        if not agent:
            return {"error": f"Unknown agent: {agent_name}", "available": list(agents.keys())}

        return await agent.analyze(warehouse_id=warehouse_id, **kwargs)

    async def get_agent_status(self, agent_name: str) -> Dict:
        """Get status of a specific agent."""
        agents = {
            "anomaly-detection": self.anomaly_agent,
            "smart-slotting": self.slotting_agent,
            "labor-forecasting": self.labor_agent,
            "replenishment": self.replenishment_agent,
        }

        agent = agents.get(agent_name)
        if not agent:
            return {"error": f"Unknown agent: {agent_name}"}

        return await agent.get_status()

    async def get_agent_recommendations(self, agent_name: str) -> List[Dict]:
        """Get recommendations from a specific agent."""
        agents = {
            "anomaly-detection": self.anomaly_agent,
            "smart-slotting": self.slotting_agent,
            "labor-forecasting": self.labor_agent,
            "replenishment": self.replenishment_agent,
        }

        agent = agents.get(agent_name)
        if not agent:
            return []

        return await agent.get_recommendations()

    async def get_capabilities(self) -> Dict:
        """Get capabilities of all agents."""
        statuses = [
            await self.anomaly_agent.get_status(),
            await self.slotting_agent.get_status(),
            await self.labor_agent.get_status(),
            await self.replenishment_agent.get_status(),
        ]

        return {
            "module": "WMS AI",
            "description": "AI-powered warehouse management intelligence",
            "agents": statuses,
            "total_agents": len(statuses),
        }
