"""
AI-Powered Predictive Maintenance Service

Predicts service needs for installed water purifiers:
- Component failure prediction
- Filter change reminders
- Proactive service scheduling
- Health scoring

Uses installation history, service patterns, and component lifecycle data.
"""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import List, Dict, Optional, Tuple
from uuid import UUID
from collections import defaultdict
import math

from sqlalchemy import select, func, and_, or_, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.installation import Installation, InstallationStatus
from app.models.service_request import ServiceRequest, ServiceType, ServiceStatus
from app.models.customer import Customer
from app.models.product import Product


# Component lifecycle data (in days) - based on industry standards for RO systems
COMPONENT_LIFECYCLE = {
    "sediment_filter": {
        "name": "Sediment Filter",
        "lifecycle_days": 90,
        "warning_days": 75,
        "critical_days": 100,
        "cost_estimate": 150
    },
    "pre_carbon_filter": {
        "name": "Pre-Carbon Filter",
        "lifecycle_days": 180,
        "warning_days": 150,
        "critical_days": 200,
        "cost_estimate": 250
    },
    "ro_membrane": {
        "name": "RO Membrane",
        "lifecycle_days": 730,  # 2 years
        "warning_days": 640,
        "critical_days": 800,
        "cost_estimate": 1500
    },
    "post_carbon_filter": {
        "name": "Post-Carbon Filter",
        "lifecycle_days": 180,
        "warning_days": 150,
        "critical_days": 200,
        "cost_estimate": 300
    },
    "uv_lamp": {
        "name": "UV Lamp",
        "lifecycle_days": 365,
        "warning_days": 300,
        "critical_days": 400,
        "cost_estimate": 800
    },
    "mineral_cartridge": {
        "name": "Mineral Cartridge",
        "lifecycle_days": 180,
        "warning_days": 150,
        "critical_days": 200,
        "cost_estimate": 400
    },
    "pump_motor": {
        "name": "Pump/Motor",
        "lifecycle_days": 1095,  # 3 years
        "warning_days": 900,
        "critical_days": 1200,
        "cost_estimate": 2500
    }
}

# TDS impact factors (higher TDS = faster degradation)
TDS_FACTOR = {
    (0, 200): 1.0,      # Low TDS - normal lifecycle
    (200, 500): 1.15,   # Medium TDS - 15% faster wear
    (500, 1000): 1.35,  # High TDS - 35% faster wear
    (1000, 2000): 1.6,  # Very High TDS - 60% faster wear
    (2000, float('inf')): 2.0  # Extreme TDS - double wear
}


class PredictiveMaintenanceService:
    """
    AI service for predicting maintenance needs and scheduling proactive service.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    def _get_tds_factor(self, tds: Optional[int]) -> float:
        """Get TDS adjustment factor for component lifecycle."""
        if tds is None:
            return 1.0

        for (low, high), factor in TDS_FACTOR.items():
            if low <= tds < high:
                return factor
        return 1.0

    def _calculate_component_health(
        self,
        days_since_install_or_service: int,
        component: str,
        tds_factor: float = 1.0
    ) -> Dict:
        """Calculate health score for a specific component."""
        if component not in COMPONENT_LIFECYCLE:
            return {"health": 100, "status": "UNKNOWN"}

        config = COMPONENT_LIFECYCLE[component]

        # Adjust lifecycle for TDS
        adjusted_lifecycle = config["lifecycle_days"] / tds_factor
        adjusted_warning = config["warning_days"] / tds_factor
        adjusted_critical = config["critical_days"] / tds_factor

        # Calculate health (100% at start, 0% at lifecycle end)
        health = max(0, min(100, 100 * (1 - days_since_install_or_service / adjusted_lifecycle)))

        # Predict failure date
        days_remaining = max(0, int(adjusted_lifecycle - days_since_install_or_service))
        predicted_failure = date.today() + timedelta(days=days_remaining)

        # Determine status
        if days_since_install_or_service >= adjusted_critical:
            status = "CRITICAL"
            urgency = "Replace immediately"
        elif days_since_install_or_service >= adjusted_lifecycle:
            status = "OVERDUE"
            urgency = "Schedule replacement soon"
        elif days_since_install_or_service >= adjusted_warning:
            status = "WARNING"
            urgency = "Plan for replacement"
        else:
            status = "GOOD"
            urgency = "No action needed"

        return {
            "component": component,
            "name": config["name"],
            "health_score": round(health, 1),
            "status": status,
            "days_since_service": days_since_install_or_service,
            "expected_lifecycle_days": int(adjusted_lifecycle),
            "days_remaining": days_remaining,
            "predicted_failure_date": predicted_failure.isoformat(),
            "urgency": urgency,
            "replacement_cost": config["cost_estimate"]
        }

    # ==================== Installation Health Prediction ====================

    async def predict_installation_health(
        self,
        installation_id: UUID
    ) -> Dict:
        """
        Predict health and maintenance needs for a specific installation.
        """
        # Get installation with related data
        query = select(Installation).options(
            joinedload(Installation.customer),
            joinedload(Installation.product)
        ).where(Installation.id == installation_id)

        result = await self.db.execute(query)
        installation = result.unique().scalar_one_or_none()

        if not installation:
            return {"error": "Installation not found"}

        # Get service history
        service_query = select(ServiceRequest).where(
            and_(
                ServiceRequest.installation_id == installation_id,
                ServiceRequest.status == ServiceStatus.COMPLETED
            )
        ).order_by(ServiceRequest.completed_at.desc())

        service_result = await self.db.execute(service_query)
        service_history = service_result.scalars().all()

        # Calculate days since installation
        install_date = installation.installation_date or installation.warranty_start_date
        if isinstance(install_date, datetime):
            install_date = install_date.date()

        if not install_date:
            install_date = installation.created_at.date() if installation.created_at else date.today()

        days_since_install = (date.today() - install_date).days

        # Get TDS factor
        tds = installation.input_tds
        tds_factor = self._get_tds_factor(tds)

        # Get last service date for each component type
        last_filter_service = None
        last_membrane_service = None
        last_general_service = None

        for service in service_history:
            if service.service_type == ServiceType.FILTER_CHANGE and not last_filter_service:
                last_filter_service = service.completed_at
            elif service.service_type == ServiceType.AMC_SERVICE and not last_general_service:
                last_general_service = service.completed_at
            elif service.service_type in [ServiceType.PREVENTIVE_MAINTENANCE, ServiceType.WARRANTY_REPAIR]:
                if not last_membrane_service:
                    last_membrane_service = service.completed_at

        # Calculate days since last service for different components
        filter_service_date = last_filter_service or install_date
        if isinstance(filter_service_date, datetime):
            filter_service_date = filter_service_date.date()
        days_since_filter = (date.today() - filter_service_date).days

        membrane_service_date = last_membrane_service or install_date
        if isinstance(membrane_service_date, datetime):
            membrane_service_date = membrane_service_date.date()
        days_since_membrane = (date.today() - membrane_service_date).days

        # Calculate component health
        components = []
        for component in ["sediment_filter", "pre_carbon_filter", "post_carbon_filter", "mineral_cartridge"]:
            health = self._calculate_component_health(days_since_filter, component, tds_factor)
            components.append(health)

        # Membrane and UV use installation date (less frequently changed)
        components.append(self._calculate_component_health(days_since_membrane, "ro_membrane", tds_factor))
        components.append(self._calculate_component_health(days_since_install, "uv_lamp", tds_factor))
        components.append(self._calculate_component_health(days_since_install, "pump_motor", tds_factor))

        # Calculate overall health score (weighted average)
        weights = {
            "sediment_filter": 0.10,
            "pre_carbon_filter": 0.10,
            "post_carbon_filter": 0.10,
            "mineral_cartridge": 0.10,
            "ro_membrane": 0.30,
            "uv_lamp": 0.15,
            "pump_motor": 0.15
        }

        overall_health = sum(
            c["health_score"] * weights.get(c["component"], 0.1)
            for c in components
        )

        # Determine overall status
        critical_count = sum(1 for c in components if c["status"] == "CRITICAL")
        warning_count = sum(1 for c in components if c["status"] == "WARNING")
        overdue_count = sum(1 for c in components if c["status"] == "OVERDUE")

        if critical_count > 0:
            overall_status = "CRITICAL"
        elif overdue_count > 0:
            overall_status = "OVERDUE"
        elif warning_count > 0:
            overall_status = "WARNING"
        else:
            overall_status = "GOOD"

        # Find next recommended service date
        upcoming_services = [c for c in components if c["days_remaining"] > 0]
        if upcoming_services:
            next_service = min(upcoming_services, key=lambda x: x["days_remaining"])
            next_service_date = next_service["predicted_failure_date"]
            next_component = next_service["name"]
        else:
            next_service_date = date.today().isoformat()
            next_component = "Multiple components"

        # Calculate estimated maintenance cost
        estimated_cost = sum(
            c["replacement_cost"] for c in components
            if c["status"] in ["CRITICAL", "OVERDUE", "WARNING"]
        )

        return {
            "installation_id": str(installation_id),
            "installation_number": installation.installation_number,
            "customer_name": installation.customer.name if installation.customer else "Unknown",
            "customer_phone": installation.customer.phone if installation.customer else None,
            "product_name": installation.product.name if installation.product else "Unknown",
            "serial_number": installation.serial_number,

            "installation_date": install_date.isoformat(),
            "days_since_installation": days_since_install,
            "input_tds": tds,
            "tds_adjustment_factor": tds_factor,

            "warranty_status": "ACTIVE" if installation.is_under_warranty else "EXPIRED",
            "warranty_days_remaining": installation.warranty_days_remaining,

            "overall_health_score": round(overall_health, 1),
            "overall_status": overall_status,

            "component_health": components,

            "alerts": {
                "critical": critical_count,
                "overdue": overdue_count,
                "warning": warning_count
            },

            "next_recommended_service": {
                "date": next_service_date,
                "component": next_component,
                "estimated_cost": estimated_cost
            },

            "service_history_count": len(service_history),
            "last_service_date": service_history[0].completed_at.isoformat() if service_history else None,

            "recommendations": self._generate_recommendations(components, overall_health)
        }

    def _generate_recommendations(
        self,
        components: List[Dict],
        overall_health: float
    ) -> List[Dict]:
        """Generate actionable recommendations."""
        recommendations = []

        # Critical components first
        for comp in components:
            if comp["status"] == "CRITICAL":
                recommendations.append({
                    "priority": "HIGH",
                    "action": f"Replace {comp['name']} immediately",
                    "reason": f"Component is {comp['days_since_service']} days old, exceeding critical threshold",
                    "estimated_cost": comp["replacement_cost"]
                })
            elif comp["status"] == "OVERDUE":
                recommendations.append({
                    "priority": "MEDIUM",
                    "action": f"Schedule {comp['name']} replacement",
                    "reason": f"Component has exceeded expected lifecycle",
                    "estimated_cost": comp["replacement_cost"]
                })

        # General health recommendations
        if overall_health < 50:
            recommendations.append({
                "priority": "HIGH",
                "action": "Schedule comprehensive service visit",
                "reason": "Overall system health is below 50%",
                "estimated_cost": None
            })
        elif overall_health < 70:
            recommendations.append({
                "priority": "MEDIUM",
                "action": "Consider preventive maintenance",
                "reason": "System health is declining",
                "estimated_cost": None
            })

        return recommendations

    # ==================== Proactive Service List ====================

    async def get_proactive_service_list(
        self,
        health_threshold: int = 80,
        limit: int = 50
    ) -> List[Dict]:
        """
        Get list of installations that need proactive service.
        """
        # Get all active installations
        query = select(Installation).options(
            joinedload(Installation.customer),
            joinedload(Installation.product)
        ).where(
            Installation.status == InstallationStatus.COMPLETED
        ).order_by(
            Installation.installation_date.asc()
        )

        result = await self.db.execute(query)
        installations = result.unique().scalars().all()

        service_needed = []

        for installation in installations:
            try:
                health = await self.predict_installation_health(installation.id)
                if "error" in health:
                    continue

                if health["overall_health_score"] < health_threshold:
                    service_needed.append({
                        "installation_id": str(installation.id),
                        "installation_number": installation.installation_number,
                        "customer_name": health["customer_name"],
                        "customer_phone": health["customer_phone"],
                        "product_name": health["product_name"],
                        "serial_number": installation.serial_number,

                        "overall_health": health["overall_health_score"],
                        "status": health["overall_status"],

                        "critical_components": health["alerts"]["critical"],
                        "overdue_components": health["alerts"]["overdue"],
                        "warning_components": health["alerts"]["warning"],

                        "next_service_date": health["next_recommended_service"]["date"],
                        "estimated_cost": health["next_recommended_service"]["estimated_cost"],

                        "warranty_status": health["warranty_status"],
                        "days_since_installation": health["days_since_installation"],

                        "priority_score": self._calculate_priority_score(health)
                    })
            except Exception:
                continue

        # Sort by priority score
        service_needed.sort(key=lambda x: x["priority_score"], reverse=True)

        return service_needed[:limit]

    def _calculate_priority_score(self, health: Dict) -> float:
        """Calculate priority score for service scheduling."""
        score = 0

        # Health score impact (lower health = higher priority)
        score += (100 - health["overall_health_score"]) * 0.4

        # Critical components
        score += health["alerts"]["critical"] * 20

        # Overdue components
        score += health["alerts"]["overdue"] * 10

        # Warning components
        score += health["alerts"]["warning"] * 5

        # Warranty status (prioritize warranty customers)
        if health["warranty_status"] == "ACTIVE":
            score += 10

        return round(score, 1)

    # ==================== Service Prediction Dashboard ====================

    async def get_maintenance_dashboard(self) -> Dict:
        """
        Get predictive maintenance dashboard data.
        """
        # Get proactive service list
        service_list = await self.get_proactive_service_list(health_threshold=80, limit=100)

        # Aggregate stats
        critical_count = sum(1 for s in service_list if s["status"] == "CRITICAL")
        overdue_count = sum(1 for s in service_list if s["status"] == "OVERDUE")
        warning_count = sum(1 for s in service_list if s["status"] == "WARNING")

        # Estimated revenue from service
        total_estimated_revenue = sum(s["estimated_cost"] or 0 for s in service_list)

        # By week distribution
        this_week = []
        next_week = []
        later = []

        today = date.today()
        week_end = today + timedelta(days=7)
        two_weeks = today + timedelta(days=14)

        for item in service_list:
            try:
                service_date = datetime.fromisoformat(item["next_service_date"]).date()
                if service_date <= week_end:
                    this_week.append(item)
                elif service_date <= two_weeks:
                    next_week.append(item)
                else:
                    later.append(item)
            except Exception:
                later.append(item)

        # Get installations by health status
        total_query = select(func.count(Installation.id)).where(
            Installation.status == InstallationStatus.COMPLETED
        )
        total_result = await self.db.execute(total_query)
        total_installations = total_result.scalar() or 0

        healthy_count = total_installations - len(service_list)

        return {
            "generated_at": datetime.now().isoformat(),

            "summary": {
                "total_active_installations": total_installations,
                "healthy": healthy_count,
                "needs_attention": len(service_list),
                "critical": critical_count,
                "overdue": overdue_count,
                "warning": warning_count
            },

            "service_schedule": {
                "this_week": len(this_week),
                "next_week": len(next_week),
                "later": len(later)
            },

            "revenue_opportunity": {
                "estimated_service_revenue": round(total_estimated_revenue, 2),
                "potential_amc_renewals": sum(
                    1 for s in service_list
                    if s["warranty_status"] == "EXPIRED" and s["overall_health"] < 70
                )
            },

            "top_urgent": service_list[:10],

            "insights": [
                {
                    "type": "critical",
                    "message": f"{critical_count} installations need immediate attention",
                    "severity": "high" if critical_count > 0 else "info"
                },
                {
                    "type": "revenue",
                    "message": f"Potential service revenue: ₹{total_estimated_revenue:,.0f}",
                    "severity": "info"
                },
                {
                    "type": "scheduling",
                    "message": f"{len(this_week)} services recommended this week",
                    "severity": "medium" if len(this_week) > 5 else "info"
                }
            ],

            "health_distribution": {
                "good": healthy_count,
                "warning": warning_count,
                "critical": critical_count + overdue_count
            }
        }

    # ==================== Component Failure Analysis ====================

    async def analyze_component_failures(
        self,
        days_back: int = 365
    ) -> Dict:
        """
        Analyze historical component failures for trend insights.
        """
        start_date = date.today() - timedelta(days=days_back)

        # Get completed service requests with parts
        query = select(ServiceRequest).where(
            and_(
                ServiceRequest.status == ServiceStatus.COMPLETED,
                ServiceRequest.completed_at >= start_date,
                ServiceRequest.parts_used.isnot(None)
            )
        )

        result = await self.db.execute(query)
        services = result.scalars().all()

        # Analyze parts usage
        part_failures = defaultdict(int)
        monthly_failures = defaultdict(lambda: defaultdict(int))

        for service in services:
            parts = service.parts_used or []
            service_month = service.completed_at.strftime("%Y-%m") if service.completed_at else "unknown"

            for part in parts:
                part_name = part.get("name", part.get("part_id", "unknown"))
                part_failures[part_name] += 1
                monthly_failures[service_month][part_name] += 1

        # Sort by frequency
        sorted_failures = sorted(part_failures.items(), key=lambda x: x[1], reverse=True)

        return {
            "analysis_period_days": days_back,
            "total_services_analyzed": len(services),

            "top_failing_components": [
                {"component": name, "failure_count": count}
                for name, count in sorted_failures[:10]
            ],

            "monthly_trend": [
                {
                    "month": month,
                    "failures": dict(failures)
                }
                for month, failures in sorted(monthly_failures.items())
            ],

            "insights": [
                f"Most common failure: {sorted_failures[0][0]} ({sorted_failures[0][1]} occurrences)" if sorted_failures else "No failure data",
                f"Average failures per month: {len(services) / max(1, days_back / 30):.1f}"
            ]
        }
