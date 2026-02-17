"""
S&OP Auto-Triggering Jobs — Tenant-Aware Background Scheduling

Provides 6 scheduled jobs for autonomous S&OP operations:
1. snop_exception_agent    — Detect supply chain anomalies (every 4 hours)
2. snop_reorder_check      — Auto-generate purchase requisitions (every 60 min)
3. snop_bias_detection     — Detect forecast bias (daily 6 AM IST)
4. snop_pos_signal_detection — Detect POS demand signals (every 60 min)
5. snop_forecast_regeneration — Weekly forecast refresh (Sunday 2 AM IST)
6. snop_alert_digest       — Morning briefing alert digest (daily 8 AM IST)

All jobs use the @tenant_job decorator for multi-tenant schema isolation.
"""

import logging
from datetime import datetime, timezone

from sqlalchemy import text, select
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.ext.asyncio import AsyncSession

from app.jobs.tenant_job_runner import tenant_job

logger = logging.getLogger(__name__)


# ============================================================
# Helper: get admin user IDs for a tenant
# ============================================================

async def _get_admin_user_ids(session: AsyncSession):
    """Fetch user IDs with admin/superadmin roles in the current tenant schema."""
    try:
        result = await session.execute(
            text("""
                SELECT id FROM users
                WHERE role IN ('admin', 'superadmin', 'ADMIN', 'SUPERADMIN')
                AND is_active = true
            """)
        )
        return [row.id for row in result.fetchall()]
    except ProgrammingError:
        return []


async def _create_notification(
    session: AsyncSession,
    user_id,
    notification_type: str,
    priority: str,
    title: str,
    message: str,
    entity_type: str = None,
    action_url: str = None,
    extra_data: dict = None,
):
    """Create a notification record for a user."""
    from app.models.notifications import Notification

    notification = Notification(
        user_id=user_id,
        notification_type=notification_type,
        priority=priority,
        title=title,
        message=message,
        entity_type=entity_type,
        action_url=action_url,
        extra_data=extra_data or {},
    )
    session.add(notification)


# ============================================================
# Job 1: Exception Detection Agent (every 4 hours)
# ============================================================

@tenant_job("snop_exception_agent")
async def snop_exception_agent(session: AsyncSession, tenant: dict):
    """
    Run the S&OP exception detection agent for a tenant.

    Detects stockout risks, overstock, and demand-supply gaps.
    Creates URGENT notifications for admin users when CRITICAL alerts found.
    """
    try:
        from app.services.snop.planning_agents import PlanningAgents

        agents = PlanningAgents(session)
        result = await agents.run_exception_agent()

        total = result.get("total_alerts", 0)
        by_severity = result.get("by_severity", {})
        critical_count = by_severity.get("CRITICAL", 0)
        high_count = by_severity.get("HIGH", 0)

        logger.info(
            f"Tenant '{tenant['subdomain']}': Exception agent found {total} alerts "
            f"(CRITICAL={critical_count}, HIGH={high_count})"
        )

        # Notify admins on CRITICAL alerts
        if critical_count > 0:
            admin_ids = await _get_admin_user_ids(session)
            for admin_id in admin_ids:
                await _create_notification(
                    session,
                    user_id=admin_id,
                    notification_type="ALERT",
                    priority="URGENT",
                    title=f"S&OP: {critical_count} Critical Supply Chain Alerts",
                    message=(
                        f"Exception agent detected {critical_count} CRITICAL and "
                        f"{high_count} HIGH severity alerts. "
                        f"Immediate review recommended."
                    ),
                    entity_type="snop_exception",
                    action_url="/dashboard/snop/alerts",
                    extra_data=by_severity,
                )

    except ProgrammingError as e:
        if "does not exist" in str(e):
            logger.debug(
                f"Tenant '{tenant['subdomain']}': S&OP tables not yet created"
            )
        else:
            raise


# ============================================================
# Job 2: Reorder Check Agent (every 60 minutes)
# ============================================================

@tenant_job("snop_reorder_check")
async def snop_reorder_check(session: AsyncSession, tenant: dict):
    """
    Run the S&OP reorder agent for a tenant.

    Checks inventory positions and auto-creates DRAFT Purchase Requisitions
    for EMERGENCY and URGENT reorder suggestions.
    """
    try:
        from app.services.snop.planning_agents import PlanningAgents

        agents = PlanningAgents(session)
        result = await agents.run_reorder_agent()

        total = result.get("total_suggestions", 0)
        by_urgency = result.get("by_urgency", {})
        emergency = by_urgency.get("EMERGENCY", 0)
        urgent = by_urgency.get("URGENT", 0)

        logger.info(
            f"Tenant '{tenant['subdomain']}': Reorder agent found {total} suggestions "
            f"(EMERGENCY={emergency}, URGENT={urgent})"
        )

        # Auto-create PRs for emergency/urgent items
        pr_count = 0
        for suggestion in result.get("suggestions", []):
            if suggestion.get("urgency") in ("EMERGENCY", "URGENT"):
                try:
                    # Get a system user ID for PR creation
                    admin_ids = await _get_admin_user_ids(session)
                    if not admin_ids:
                        logger.warning(
                            f"Tenant '{tenant['subdomain']}': No admin users found for PR creation"
                        )
                        break

                    await agents.create_purchase_requisition_from_suggestion(
                        suggestion=suggestion,
                        user_id=admin_ids[0],
                    )
                    pr_count += 1
                except Exception as pr_err:
                    logger.warning(
                        f"Tenant '{tenant['subdomain']}': Failed to create PR for "
                        f"product {suggestion.get('product_id', 'unknown')}: {pr_err}"
                    )

        if pr_count > 0:
            logger.info(
                f"Tenant '{tenant['subdomain']}': Created {pr_count} DRAFT Purchase Requisitions"
            )

    except ProgrammingError as e:
        if "does not exist" in str(e):
            logger.debug(
                f"Tenant '{tenant['subdomain']}': S&OP/inventory tables not yet created"
            )
        else:
            raise


# ============================================================
# Job 3: Forecast Bias Detection (daily at 6:00 AM IST)
# ============================================================

@tenant_job("snop_bias_detection")
async def snop_bias_detection(session: AsyncSession, tenant: dict):
    """
    Run the S&OP forecast bias detection agent for a tenant.

    Analyzes forecast accuracy, detects systematic bias, and creates
    notifications for HIGH severity findings.
    """
    try:
        from app.services.snop.planning_agents import PlanningAgents

        agents = PlanningAgents(session)
        result = await agents.run_bias_agent()

        total_findings = result.get("total_findings", 0)
        overall = result.get("overall_stats", {})

        logger.info(
            f"Tenant '{tenant['subdomain']}': Bias agent found {total_findings} findings. "
            f"Overall bias: {overall.get('overall_avg_bias', 0):.1f}% "
            f"({overall.get('overall_direction', 'N/A')}). "
            f"Best algo: {overall.get('best_algorithm', 'N/A')}, "
            f"Worst algo: {overall.get('worst_algorithm', 'N/A')}"
        )

        # Notify on HIGH severity findings
        high_findings = [
            f for f in result.get("findings", [])
            if f.get("severity") == "HIGH"
        ]

        if high_findings:
            admin_ids = await _get_admin_user_ids(session)
            for admin_id in admin_ids:
                await _create_notification(
                    session,
                    user_id=admin_id,
                    notification_type="ALERT",
                    priority="HIGH",
                    title=f"S&OP: {len(high_findings)} Forecast Bias Issues Detected",
                    message=(
                        f"Bias detection found {len(high_findings)} high-severity issues. "
                        f"Overall forecast bias: {overall.get('overall_avg_bias', 0):.1f}% "
                        f"({overall.get('overall_direction', 'N/A')}). "
                        f"Review algorithm settings."
                    ),
                    entity_type="snop_bias",
                    action_url="/dashboard/snop/forecasts",
                    extra_data={
                        "findings_count": total_findings,
                        "algorithm_mape": overall.get("algorithm_mape", {}),
                    },
                )

    except ProgrammingError as e:
        if "does not exist" in str(e):
            logger.debug(
                f"Tenant '{tenant['subdomain']}': S&OP forecast tables not yet created"
            )
        else:
            raise


# ============================================================
# Job 4: POS Signal Detection (every 60 minutes)
# ============================================================

@tenant_job("snop_pos_signal_detection")
async def snop_pos_signal_detection(session: AsyncSession, tenant: dict):
    """
    Detect demand signals from POS/order data for a tenant.

    Compares recent demand to historical averages and creates demand signals
    for spikes and drops. Also expires old signals.
    """
    try:
        from app.services.snop.demand_sensor import DemandSensor

        sensor = DemandSensor(session)

        # Expire old signals first
        expired_count = await sensor.expire_old_signals()
        if expired_count > 0:
            logger.info(
                f"Tenant '{tenant['subdomain']}': Expired {expired_count} old demand signals"
            )

        # Detect new POS signals
        new_signals = await sensor.detect_pos_signals()

        logger.info(
            f"Tenant '{tenant['subdomain']}': POS signal detection found "
            f"{len(new_signals)} new signals"
        )

    except ProgrammingError as e:
        if "does not exist" in str(e):
            logger.debug(
                f"Tenant '{tenant['subdomain']}': S&OP/order tables not yet created"
            )
        else:
            raise


# ============================================================
# Job 5: Weekly Forecast Regeneration (Sunday 2:00 AM IST)
# ============================================================

@tenant_job("snop_forecast_regeneration")
async def snop_forecast_regeneration(session: AsyncSession, tenant: dict):
    """
    Regenerate demand forecasts for all active products in a tenant.

    Uses ENSEMBLE algorithm with WEEKLY granularity and 90-day horizon.
    Creates a summary notification for admin users.
    """
    try:
        from app.services.snop.snop_service import SNOPService
        from app.models.snop import ForecastAlgorithm, ForecastGranularity

        service = SNOPService(session)

        forecasts = await service.generate_forecasts(
            algorithm=ForecastAlgorithm.ENSEMBLE,
            granularity=ForecastGranularity.WEEKLY,
            forecast_horizon_days=90,
        )

        forecast_count = len(forecasts)
        logger.info(
            f"Tenant '{tenant['subdomain']}': Generated {forecast_count} weekly forecasts"
        )

        # Notify admins
        if forecast_count > 0:
            admin_ids = await _get_admin_user_ids(session)
            for admin_id in admin_ids:
                await _create_notification(
                    session,
                    user_id=admin_id,
                    notification_type="SYSTEM",
                    priority="MEDIUM",
                    title=f"S&OP: Weekly Forecasts Generated ({forecast_count})",
                    message=(
                        f"Automated weekly forecast regeneration completed. "
                        f"{forecast_count} forecasts generated using ENSEMBLE algorithm "
                        f"with 90-day horizon. Review and approve in the S&OP dashboard."
                    ),
                    entity_type="snop_forecast",
                    action_url="/dashboard/snop/forecasts",
                    extra_data={"forecast_count": forecast_count},
                )

    except ProgrammingError as e:
        if "does not exist" in str(e):
            logger.debug(
                f"Tenant '{tenant['subdomain']}': S&OP tables not yet created"
            )
        else:
            raise


# ============================================================
# Job 6: Daily Alert Digest (daily at 8:00 AM IST)
# ============================================================

@tenant_job("snop_alert_digest")
async def snop_alert_digest(session: AsyncSession, tenant: dict):
    """
    Generate a morning briefing alert digest for a tenant.

    Runs the full alert center and creates a single digest notification
    per admin user summarizing all active alerts.
    """
    try:
        from app.services.snop.planning_agents import PlanningAgents

        agents = PlanningAgents(session)
        result = await agents.get_alert_center()

        summary = result.get("summary", {})
        total_alerts = summary.get("total_alerts", 0)
        by_severity = summary.get("by_severity", {})

        logger.info(
            f"Tenant '{tenant['subdomain']}': Alert digest — {total_alerts} total alerts. "
            f"CRITICAL={by_severity.get('CRITICAL', 0)}, "
            f"HIGH={by_severity.get('HIGH', 0)}, "
            f"MEDIUM={by_severity.get('MEDIUM', 0)}"
        )

        if total_alerts > 0:
            admin_ids = await _get_admin_user_ids(session)

            # Build digest message
            severity_parts = []
            for sev in ("CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"):
                count = by_severity.get(sev, 0)
                if count > 0:
                    severity_parts.append(f"{count} {sev}")
            severity_summary = ", ".join(severity_parts)

            by_category = summary.get("by_category", {})
            category_parts = [f"{v} {k}" for k, v in by_category.items() if v > 0]
            category_summary = ", ".join(category_parts[:5])  # Top 5 categories

            for admin_id in admin_ids:
                await _create_notification(
                    session,
                    user_id=admin_id,
                    notification_type="SYSTEM",
                    priority="HIGH" if by_severity.get("CRITICAL", 0) > 0 else "MEDIUM",
                    title=f"S&OP Morning Briefing: {total_alerts} Active Alerts",
                    message=(
                        f"Daily S&OP alert digest: {severity_summary}. "
                        f"Categories: {category_summary}. "
                        f"Review the alert center for details and recommended actions."
                    ),
                    entity_type="snop_digest",
                    action_url="/dashboard/snop/alerts",
                    extra_data={
                        "by_severity": by_severity,
                        "by_category": by_category,
                        "agents_status": result.get("agents_status", {}),
                    },
                )

    except ProgrammingError as e:
        if "does not exist" in str(e):
            logger.debug(
                f"Tenant '{tenant['subdomain']}': S&OP tables not yet created"
            )
        else:
            raise
