"""
DMS AI Command Center

Aggregator for all 4 DMS AI agents.
Returns combined status, alerts, and recommendations.
Uses parallel execution and in-memory caching for fast response.
"""

import asyncio
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.ai.dms.dealer_performance import DMSDealerPerformanceAgent
from app.services.ai.dms.collection_optimizer import DMSCollectionOptimizerAgent
from app.services.ai.dms.scheme_effectiveness import DMSSchemeEffectivenessAgent
from app.services.ai.dms.demand_sensing import DMSDemandSensingAgent

# In-memory TTL cache: {schema: {"data": ..., "ts": ...}}
_dashboard_cache: Dict[str, Dict] = {}
_CACHE_TTL = 120  # seconds


class DMSCommandCenter:
    """
    Aggregates all DMS AI agents into a unified command center.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def _get_schema(self) -> str:
        result = await self.db.execute(text("SELECT current_setting('search_path')"))
        return result.scalar() or "public"

    async def _run_agent(self, agent_class, schema: str, **kwargs) -> tuple:
        """Run a single agent with its own DB session for parallel execution."""
        from app.database import engine
        async with engine.connect() as conn:
            await conn.execute(text(f'SET search_path TO {schema}'))
            session = AsyncSession(bind=conn, expire_on_commit=False)
            try:
                agent = agent_class(session)
                await agent.analyze(**kwargs)
                status = await agent.get_status()
                recs = await agent.get_recommendations()
                return status, recs
            except Exception:
                agent = agent_class(session)
                status = await agent.get_status()
                return status, []
            finally:
                await session.close()

    async def get_dashboard(self) -> Dict:
        """Get full DMS AI dashboard data (cached, parallel agents)."""
        schema = await self._get_schema()

        # Check cache
        cached = _dashboard_cache.get(schema)
        if cached and (time.time() - cached["ts"]) < _CACHE_TTL:
            return cached["data"]

        # Run all 4 agents in parallel, each with its own DB session
        agent_classes = [
            DMSDealerPerformanceAgent,
            DMSCollectionOptimizerAgent,
            DMSSchemeEffectivenessAgent,
            DMSDemandSensingAgent,
        ]

        results = await asyncio.gather(
            *[self._run_agent(cls, schema) for cls in agent_classes],
            return_exceptions=True,
        )

        statuses = []
        all_recommendations = []
        for r in results:
            if isinstance(r, Exception):
                statuses.append({"id": "unknown", "status": "error", "error": str(r)})
            else:
                status, recs = r
                statuses.append(status)
                all_recommendations.extend(recs)

        severity_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
        all_recommendations.sort(key=lambda x: severity_order.get(x.get("severity", "LOW"), 4))

        severity_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for rec in all_recommendations:
            sev = rec.get("severity", "LOW")
            if sev in severity_counts:
                severity_counts[sev] += 1

        data = {
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

        # Store in cache
        _dashboard_cache[schema] = {"data": data, "ts": time.time()}
        return data

    def _agent_map(self) -> Dict:
        return {
            "dealer-performance": DMSDealerPerformanceAgent,
            "collection-optimizer": DMSCollectionOptimizerAgent,
            "scheme-effectiveness": DMSSchemeEffectivenessAgent,
            "demand-sensing": DMSDemandSensingAgent,
        }

    async def run_agent(self, agent_name: str, **kwargs) -> Dict:
        """Run a specific agent."""
        cls = self._agent_map().get(agent_name)
        if not cls:
            return {"error": f"Unknown agent: {agent_name}", "available": list(self._agent_map().keys())}
        agent = cls(self.db)
        return await agent.analyze(**kwargs)

    async def get_agent_status(self, agent_name: str) -> Dict:
        cls = self._agent_map().get(agent_name)
        if not cls:
            return {"error": f"Unknown agent: {agent_name}"}
        agent = cls(self.db)
        return await agent.get_status()

    async def get_agent_recommendations(self, agent_name: str) -> List[Dict]:
        cls = self._agent_map().get(agent_name)
        if not cls:
            return []
        agent = cls(self.db)
        return await agent.get_recommendations()

    async def get_capabilities(self) -> Dict:
        statuses = []
        for cls in self._agent_map().values():
            agent = cls(self.db)
            statuses.append(await agent.get_status())
        return {
            "module": "DMS AI",
            "description": "AI-powered distribution management intelligence",
            "agents": statuses,
            "total_agents": len(statuses),
        }
