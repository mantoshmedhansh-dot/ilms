"""
Dunning / Payment Reminder Job.

Checks for overdue invoices and generates alerts grouped by aging bucket:
- 1-30 days overdue
- 31-60 days overdue
- 61-90 days overdue
- 90+ days overdue

Triggers:
- Daily scheduled job (via APScheduler)
"""
import logging
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Dict, Any, List

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.billing import TaxInvoice
from app.models.notifications import Notification, NotificationType
from app.models.user import User

logger = logging.getLogger(__name__)

AGING_BUCKETS = [
    {"label": "1-30 days", "min_days": 1, "max_days": 30, "severity": "LOW"},
    {"label": "31-60 days", "min_days": 31, "max_days": 60, "severity": "MEDIUM"},
    {"label": "61-90 days", "min_days": 61, "max_days": 90, "severity": "HIGH"},
    {"label": "90+ days", "min_days": 91, "max_days": 99999, "severity": "CRITICAL"},
]


async def run_dunning_reminders_job(db: AsyncSession) -> Dict[str, Any]:
    """
    Main dunning job: find overdue invoices, group by aging, generate alerts.

    Returns:
        Summary of overdue invoices and alerts generated
    """
    logger.info("Starting dunning reminders job...")
    today = date.today()

    results = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "overdue_invoices": 0,
        "total_overdue_amount": 0,
        "aging_summary": {},
        "alerts_created": 0,
        "errors": [],
    }

    try:
        # Get users with finance-related roles to receive dunning alerts
        from app.models.role import Role
        from app.models.user import UserRole
        admin_result = await db.execute(
            select(UserRole.user_id).join(
                Role, Role.id == UserRole.role_id
            ).where(
                Role.name.in_(["SUPER_ADMIN", "DIRECTOR", "Finance Head", "Accounts Executive"])
            ).limit(10)
        )
        admin_ids = [row[0] for row in admin_result.all()]
        if not admin_ids:
            # Fallback: get first active user
            fallback_result = await db.execute(
                select(User.id).where(User.is_active == True).limit(1)
            )
            row = fallback_result.first()
            admin_ids = [row[0]] if row else []

        if not admin_ids:
            logger.warning("No users found to receive dunning alerts")
            results["errors"].append("No users found for dunning alerts")
            return results

        # Get all overdue invoices (due_date < today AND amount_due > 0)
        query = select(TaxInvoice).where(
            and_(
                TaxInvoice.due_date < today,
                TaxInvoice.amount_due > 0,
                TaxInvoice.status.notin_(["CANCELLED", "VOID", "DRAFT"]),
            )
        )

        result = await db.execute(query)
        overdue_invoices = list(result.scalars().all())
        results["overdue_invoices"] = len(overdue_invoices)

        # Group by aging bucket
        bucketed: Dict[str, List[dict]] = {}
        for bucket in AGING_BUCKETS:
            bucketed[bucket["label"]] = []

        total_overdue = Decimal("0")

        for invoice in overdue_invoices:
            days_overdue = (today - invoice.due_date).days
            amount_due = invoice.amount_due or Decimal("0")
            total_overdue += amount_due

            invoice_info = {
                "invoice_id": str(invoice.id),
                "invoice_number": invoice.invoice_number,
                "customer_name": invoice.customer_name,
                "customer_id": str(invoice.customer_id) if invoice.customer_id else None,
                "due_date": invoice.due_date.isoformat(),
                "days_overdue": days_overdue,
                "amount_due": float(amount_due),
                "grand_total": float(invoice.grand_total) if invoice.grand_total else 0,
            }

            for bucket in AGING_BUCKETS:
                if bucket["min_days"] <= days_overdue <= bucket["max_days"]:
                    bucketed[bucket["label"]].append(invoice_info)
                    break

        results["total_overdue_amount"] = float(total_overdue)

        # Generate alerts per aging bucket
        for bucket in AGING_BUCKETS:
            label = bucket["label"]
            invoices_in_bucket = bucketed[label]
            count = len(invoices_in_bucket)
            bucket_total = sum(i["amount_due"] for i in invoices_in_bucket)

            results["aging_summary"][label] = {
                "count": count,
                "total_amount": bucket_total,
                "severity": bucket["severity"],
            }

            if count == 0:
                continue

            # Create a notification/alert for this bucket
            try:
                alert_title = f"Dunning Alert: {count} invoice(s) overdue {label}"
                alert_body = (
                    f"{count} invoice(s) totaling ₹{bucket_total:,.2f} are overdue "
                    f"by {label}. Severity: {bucket['severity']}."
                )

                # Top 5 offenders for detail
                top_offenders = sorted(invoices_in_bucket, key=lambda x: -x["amount_due"])[:5]
                detail_lines = []
                for inv in top_offenders:
                    detail_lines.append(
                        f"  - {inv['invoice_number']}: {inv['customer_name']} "
                        f"₹{inv['amount_due']:,.2f} ({inv['days_overdue']} days)"
                    )
                if detail_lines:
                    alert_body += "\nTop overdue:\n" + "\n".join(detail_lines)

                severity_to_priority = {
                    "LOW": "LOW",
                    "MEDIUM": "MEDIUM",
                    "HIGH": "HIGH",
                    "CRITICAL": "URGENT",
                }

                for admin_id in admin_ids:
                    notification = Notification(
                        user_id=admin_id,
                        notification_type=NotificationType.ALERT.value,
                        priority=severity_to_priority.get(bucket["severity"], "MEDIUM"),
                        title=alert_title,
                        message=alert_body,
                        entity_type="dunning",
                        extra_data={
                            "type": "DUNNING_REMINDER",
                            "aging_bucket": label,
                            "severity": bucket["severity"],
                            "invoice_count": count,
                            "total_amount": bucket_total,
                        },
                        is_read=False,
                    )
                    db.add(notification)
                results["alerts_created"] += 1

            except Exception as e:
                error_msg = f"Failed to create alert for bucket {label}: {e}"
                logger.error(error_msg)
                results["errors"].append(error_msg)

        await db.commit()

    except Exception as e:
        error_msg = f"Dunning reminders job failed: {e}"
        logger.error(error_msg)
        results["errors"].append(error_msg)

    results["completed_at"] = datetime.now(timezone.utc).isoformat()
    logger.info(
        f"Dunning job completed: {results['overdue_invoices']} overdue invoices, "
        f"₹{results['total_overdue_amount']:,.2f} total, "
        f"{results['alerts_created']} alerts created"
    )

    return results


def register_dunning_job(scheduler):
    """
    Register the dunning reminders job with APScheduler.

    Runs daily at 8:00 AM IST (2:30 AM UTC).
    """
    from app.database import get_db_context

    async def job_wrapper():
        async with get_db_context() as db:
            await run_dunning_reminders_job(db)

    scheduler.add_job(
        job_wrapper,
        'cron',
        hour=2,
        minute=30,
        id='dunning_payment_reminders',
        name='Daily dunning / payment reminders',
        replace_existing=True,
    )

    logger.info("Dunning reminders job registered to run daily at 2:30 UTC (8:00 AM IST)")
