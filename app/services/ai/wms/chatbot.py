"""
WMS AI Chatbot Service

Natural language interface for warehouse management queries:
- Zone utilization queries
- Pick performance analysis
- Anomaly checking
- Slotting analysis
- Replenishment status
- Worker productivity

Follows the same pattern as ERPChatbotService.
"""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import List, Dict, Optional, Tuple, Any
from uuid import UUID
import re
from collections import defaultdict

from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.inventory import StockItem, InventorySummary, StockMovement
from app.models.wms_advanced import WarehouseTask, TaskType, TaskStatus, SlotScore
from app.models.wms import WarehouseZone, WarehouseBin, ZoneType
from app.models.warehouse import Warehouse
from app.models.labor import WarehouseWorker, ProductivityMetric, WorkShift, WorkerStatus
from app.models.order import Order, OrderStatus


# Intent patterns for WMS queries
WMS_INTENT_PATTERNS = {
    "zone_utilization": [
        r"(zone|area).*(utilization|usage|capacity|fill|occupied)",
        r"(how full|how busy|capacity).*(zone|warehouse|area)",
        r"(utilization|usage).*(zone|warehouse)",
    ],
    "pick_performance": [
        r"(pick|picking).*(performance|rate|speed|efficiency|throughput)",
        r"(how fast|how many).*(pick|picked|picks)",
        r"(picker|worker).*(performance|efficiency|output)",
    ],
    "anomaly_check": [
        r"(anomal|unusual|abnormal|irregular|outlier)",
        r"(anything wrong|any issue|any problem).*(warehouse|wms|operation)",
        r"(detect|check|find).*(anomal|issue|problem|discrepancy)",
    ],
    "slotting_analysis": [
        r"(slot|slotting|bin).*(analysis|optimization|score|class)",
        r"(abc|velocity).*(class|analysis|distribution)",
        r"(relocat|move|reposition).*(product|item|sku|bin)",
    ],
    "replenishment_status": [
        r"(replenish|restock|refill).*(status|need|required|pending)",
        r"(low stock|running low|empty).*(bin|zone|pick)",
        r"(forward pick|picking zone).*(stock|level|status)",
    ],
    "worker_productivity": [
        r"(worker|employee|staff).*(productivity|output|performance|efficiency)",
        r"(labor|workforce).*(performance|utilization|productivity)",
        r"(who|which worker).*(best|top|most|least|worst)",
    ],
    "inventory_overview": [
        r"(inventory|stock).*(overview|summary|status|level|count)",
        r"(how much|how many).*(stock|inventory|item)",
        r"(total|current).*(inventory|stock)",
    ],
    "task_status": [
        r"(task|work order).*(status|pending|progress|queue)",
        r"(how many|count).*(task|job|assignment).*(pending|open|queue)",
        r"(backlog|pending).*(task|work|pick|putaway)",
    ],
    "help": [
        r"(help|what can|how to|guide|capabilities)",
        r"(what|which).*(question|query|ask)",
    ],
}

# Time period extraction
WMS_TIME_PATTERNS = {
    "today": lambda: (date.today(), date.today()),
    "yesterday": lambda: (date.today() - timedelta(days=1), date.today() - timedelta(days=1)),
    "this week": lambda: (date.today() - timedelta(days=date.today().weekday()), date.today()),
    "last week": lambda: (
        date.today() - timedelta(days=date.today().weekday() + 7),
        date.today() - timedelta(days=date.today().weekday() + 1),
    ),
    "this month": lambda: (date.today().replace(day=1), date.today()),
    "last 7 days": lambda: (date.today() - timedelta(days=7), date.today()),
    "last 30 days": lambda: (date.today() - timedelta(days=30), date.today()),
}


class WMSChatbotService:
    """
    Natural language interface for WMS queries.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    def _classify_intent(self, query: str) -> Tuple[str, float]:
        """Classify user intent from query."""
        query_lower = query.lower()
        best_intent = "unknown"
        best_score = 0

        for intent, patterns in WMS_INTENT_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, query_lower):
                    score = len(re.findall(pattern, query_lower))
                    if score > best_score:
                        best_score = score
                        best_intent = intent

        confidence = min(0.95, 0.5 + best_score * 0.15) if best_score > 0 else 0.2
        return best_intent, confidence

    def _extract_time_period(self, query: str) -> Tuple[date, date]:
        """Extract time period from query."""
        query_lower = query.lower()
        for period_name, date_func in WMS_TIME_PATTERNS.items():
            if period_name in query_lower:
                return date_func()
        return date.today() - timedelta(days=7), date.today()

    # ==================== Intent Handlers ====================

    async def _handle_zone_utilization(self, query: str, start: date, end: date) -> Dict:
        """Handle zone utilization queries."""
        result = await self.db.execute(
            select(
                WarehouseZone.name,
                WarehouseZone.zone_type,
                WarehouseZone.current_utilization,
                WarehouseZone.max_capacity,
            )
            .order_by(desc(WarehouseZone.current_utilization))
            .limit(20)
        )
        zones = result.all()

        zone_data = []
        for z in zones:
            util_pct = (float(z.current_utilization or 0) / float(z.max_capacity or 1) * 100) if z.max_capacity else 0
            zone_data.append({
                "zone": z.name,
                "type": z.zone_type,
                "utilization": f"{util_pct:.1f}%",
                "capacity": z.max_capacity or 0,
                "used": z.current_utilization or 0,
            })

        avg_util = sum(float(z["utilization"].rstrip('%')) for z in zone_data) / max(len(zone_data), 1)

        return {
            "response": f"Warehouse has {len(zone_data)} zones with average utilization of {avg_util:.1f}%. "
                       f"{'Some zones are running hot!' if avg_util > 80 else 'Utilization is within normal range.'}",
            "data": {"zones": zone_data},
            "suggestions": [
                "Show me pick performance",
                "Any anomalies detected?",
                "What is the replenishment status?",
            ],
        }

    async def _handle_pick_performance(self, query: str, start: date, end: date) -> Dict:
        """Handle pick performance queries."""
        start_dt = datetime.combine(start, datetime.min.time()).replace(tzinfo=timezone.utc)
        end_dt = datetime.combine(end, datetime.max.time()).replace(tzinfo=timezone.utc)

        result = await self.db.execute(
            select(
                func.count(WarehouseTask.id).label("total_tasks"),
                func.sum(WarehouseTask.quantity_completed).label("total_picked"),
                func.count(func.nullif(WarehouseTask.status == TaskStatus.COMPLETED.value, False)).label("completed"),
            )
            .where(
                and_(
                    WarehouseTask.task_type == TaskType.PICK.value,
                    WarehouseTask.created_at >= start_dt,
                    WarehouseTask.created_at <= end_dt,
                )
            )
        )
        row = result.one()

        total = int(row.total_tasks or 0)
        picked = int(row.total_picked or 0)
        completed = int(row.completed or 0)
        completion_rate = (completed / total * 100) if total > 0 else 0

        return {
            "response": f"Pick performance ({start} to {end}): {total} pick tasks created, "
                       f"{completed} completed ({completion_rate:.1f}% completion rate), "
                       f"{picked} total items picked.",
            "data": {
                "total_tasks": total,
                "completed_tasks": completed,
                "total_items_picked": picked,
                "completion_rate": f"{completion_rate:.1f}%",
                "period": f"{start} to {end}",
            },
            "suggestions": [
                "Show worker productivity",
                "Any pick rate anomalies?",
                "Show zone utilization",
            ],
        }

    async def _handle_anomaly_check(self, query: str, start: date, end: date) -> Dict:
        """Handle anomaly check queries."""
        from app.services.ai.wms.anomaly_detection import WMSAnomalyDetectionAgent
        agent = WMSAnomalyDetectionAgent(self.db)
        analysis = await agent.analyze(days=30)

        total = analysis.get("summary", {}).get("total_anomalies", 0)
        anomalies = analysis.get("anomalies", [])[:5]

        anomaly_summary = []
        for a in anomalies:
            anomaly_summary.append({
                "type": a.get("type", "").replace("_", " ").title(),
                "severity": a.get("severity", "LOW"),
                "details": a.get("details", ""),
            })

        if total == 0:
            detail_msg = "No issues detected - operations are normal."
        elif anomaly_summary:
            top = anomaly_summary[0]
            detail_msg = f"{top['severity']} severity issue found: {top['details'][:100]}"
        else:
            detail_msg = "Analysis complete."

        return {
            "response": f"Anomaly detection found {total} anomalies in the last 30 days. {detail_msg}",
            "data": {"total_anomalies": total, "top_anomalies": anomaly_summary},
            "suggestions": [
                "Show inventory discrepancies",
                "Run full anomaly detection",
                "Show pick performance",
            ],
        }

    async def _handle_slotting_analysis(self, query: str, start: date, end: date) -> Dict:
        """Handle slotting analysis queries."""
        result = await self.db.execute(
            select(
                SlotScore.slot_class,
                func.count(SlotScore.id).label("count"),
            )
            .group_by(SlotScore.slot_class)
        )
        rows = result.all()

        distribution = {row.slot_class: int(row.count) for row in rows}
        total = sum(distribution.values())

        return {
            "response": f"ABC slotting analysis: {total} products classified. "
                       f"A-class (fast movers): {distribution.get('A', 0)}, "
                       f"B-class: {distribution.get('B', 0)}, "
                       f"C-class: {distribution.get('C', 0)}, "
                       f"D-class (dead stock): {distribution.get('D', 0)}.",
            "data": {"abc_distribution": distribution, "total_products": total},
            "suggestions": [
                "Show relocation recommendations",
                "Run smart slotting analysis",
                "Show pick performance",
            ],
        }

    async def _handle_replenishment_status(self, query: str, start: date, end: date) -> Dict:
        """Handle replenishment status queries."""
        from app.services.ai.wms.replenishment import WMSReplenishmentAgent
        agent = WMSReplenishmentAgent(self.db)
        analysis = await agent.analyze(days=7)

        summary = analysis.get("summary", {})
        suggestions = analysis.get("suggestions", [])[:5]

        replenish_data = []
        for s in suggestions:
            replenish_data.append({
                "bin": s.get("destination_bin", ""),
                "urgency": s.get("urgency", ""),
                "current_qty": s.get("current_qty", 0),
                "replenish_qty": s.get("replenish_qty", 0),
            })

        return {
            "response": f"Replenishment status: {summary.get('bins_needing_replenishment', 0)} bins need replenishment "
                       f"out of {summary.get('total_picking_bins', 0)} total picking bins. "
                       f"Critical: {summary.get('by_urgency', {}).get('CRITICAL', 0)}, "
                       f"High: {summary.get('by_urgency', {}).get('HIGH', 0)}.",
            "data": {
                "bins_needing_replenishment": summary.get("bins_needing_replenishment", 0),
                "by_urgency": summary.get("by_urgency", {}),
                "top_replenishments": replenish_data,
            },
            "suggestions": [
                "Show consumption rates",
                "Run replenishment analysis",
                "Show zone utilization",
            ],
        }

    async def _handle_worker_productivity(self, query: str, start: date, end: date) -> Dict:
        """Handle worker productivity queries."""
        start_dt = datetime.combine(start, datetime.min.time()).replace(tzinfo=timezone.utc)
        end_dt = datetime.combine(end, datetime.max.time()).replace(tzinfo=timezone.utc)

        result = await self.db.execute(
            select(
                WarehouseTask.assigned_to,
                func.count(WarehouseTask.id).label("tasks_completed"),
                func.sum(WarehouseTask.quantity_completed).label("units_processed"),
            )
            .where(
                and_(
                    WarehouseTask.status == TaskStatus.COMPLETED.value,
                    WarehouseTask.completed_at >= start_dt,
                    WarehouseTask.completed_at <= end_dt,
                    WarehouseTask.assigned_to.isnot(None),
                )
            )
            .group_by(WarehouseTask.assigned_to)
            .order_by(desc("units_processed"))
            .limit(10)
        )
        rows = result.all()

        workers = []
        for row in rows:
            workers.append({
                "worker_id": str(row.assigned_to),
                "tasks_completed": int(row.tasks_completed),
                "units_processed": int(row.units_processed or 0),
            })

        avg_units = sum(w["units_processed"] for w in workers) / max(len(workers), 1)

        return {
            "response": f"Top {len(workers)} workers by productivity ({start} to {end}). "
                       f"Average units processed: {avg_units:.0f}. "
                       f"Top performer: {workers[0]['units_processed']} units." if workers else "No worker productivity data available for this period.",
            "data": {"workers": workers, "average_units": round(avg_units)},
            "suggestions": [
                "Show labor forecast",
                "Show pick performance",
                "Any productivity anomalies?",
            ],
        }

    async def _handle_inventory_overview(self, query: str, start: date, end: date) -> Dict:
        """Handle inventory overview queries."""
        result = await self.db.execute(
            select(
                func.count(InventorySummary.id).label("total_records"),
                func.sum(InventorySummary.total_quantity).label("total_qty"),
                func.sum(InventorySummary.available_quantity).label("available_qty"),
                func.sum(InventorySummary.reserved_quantity).label("reserved_qty"),
            )
        )
        row = result.one()

        total_qty = int(row.total_qty or 0)
        available = int(row.available_qty or 0)
        reserved = int(row.reserved_qty or 0)

        return {
            "response": f"Inventory overview: {total_qty} total units across {int(row.total_records or 0)} product-warehouse records. "
                       f"Available: {available}, Reserved: {reserved}.",
            "data": {
                "total_quantity": total_qty,
                "available_quantity": available,
                "reserved_quantity": reserved,
                "records": int(row.total_records or 0),
            },
            "suggestions": [
                "Show low stock items",
                "Show zone utilization",
                "Any inventory discrepancies?",
            ],
        }

    async def _handle_task_status(self, query: str, start: date, end: date) -> Dict:
        """Handle task status queries."""
        result = await self.db.execute(
            select(
                WarehouseTask.task_type,
                WarehouseTask.status,
                func.count(WarehouseTask.id).label("count"),
            )
            .group_by(WarehouseTask.task_type, WarehouseTask.status)
        )
        rows = result.all()

        task_summary = defaultdict(lambda: defaultdict(int))
        for row in rows:
            task_summary[row.task_type][row.status] = int(row.count)

        pending_total = sum(
            counts.get("PENDING", 0) + counts.get("ASSIGNED", 0)
            for counts in task_summary.values()
        )

        return {
            "response": f"Task queue status: {pending_total} tasks pending/assigned across {len(task_summary)} task types.",
            "data": {
                "task_summary": {k: dict(v) for k, v in task_summary.items()},
                "total_pending": pending_total,
            },
            "suggestions": [
                "Show pick performance",
                "Show worker productivity",
                "Show replenishment status",
            ],
        }

    async def _handle_help(self, query: str, start: date, end: date) -> Dict:
        """Handle help queries."""
        return {
            "response": "I'm your WMS AI Assistant. I can help with:\n\n"
                       "- **Zone Utilization**: \"How full are the warehouse zones?\"\n"
                       "- **Pick Performance**: \"What's the pick rate today?\"\n"
                       "- **Anomaly Detection**: \"Any anomalies in operations?\"\n"
                       "- **Slotting Analysis**: \"Show ABC classification\"\n"
                       "- **Replenishment**: \"Which bins need restocking?\"\n"
                       "- **Worker Productivity**: \"Who are the top performers?\"\n"
                       "- **Inventory Overview**: \"What's the current stock level?\"\n"
                       "- **Task Status**: \"How many tasks are pending?\"",
            "data": None,
            "suggestions": [
                "Show zone utilization",
                "Any anomalies detected?",
                "Show replenishment status",
                "Show pick performance",
            ],
        }

    async def _handle_unknown(self, query: str, start: date, end: date) -> Dict:
        """Handle unknown queries."""
        return {
            "response": f"I'm not sure how to answer that. I specialize in warehouse management queries "
                       f"like zone utilization, pick performance, anomalies, slotting, replenishment, and worker productivity.",
            "data": None,
            "suggestions": [
                "Show zone utilization",
                "What's the pick performance?",
                "Any anomalies?",
                "Help",
            ],
        }

    # ==================== Main Query Method ====================

    async def query(self, user_query: str) -> Dict:
        """Process a natural language WMS query."""
        intent, confidence = self._classify_intent(user_query)
        start_date, end_date = self._extract_time_period(user_query)

        handlers = {
            "zone_utilization": self._handle_zone_utilization,
            "pick_performance": self._handle_pick_performance,
            "anomaly_check": self._handle_anomaly_check,
            "slotting_analysis": self._handle_slotting_analysis,
            "replenishment_status": self._handle_replenishment_status,
            "worker_productivity": self._handle_worker_productivity,
            "inventory_overview": self._handle_inventory_overview,
            "task_status": self._handle_task_status,
            "help": self._handle_help,
            "unknown": self._handle_unknown,
        }

        handler = handlers.get(intent, self._handle_unknown)

        try:
            result = await handler(user_query, start_date, end_date)
            result["intent"] = intent
            result["confidence"] = confidence
            result["time_period"] = {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
            }
            return result
        except Exception as e:
            return {
                "response": f"I encountered an error processing your query: {str(e)}",
                "intent": intent,
                "confidence": confidence,
                "data": None,
                "suggestions": ["Help", "Show zone utilization"],
            }

    async def get_quick_stats(self) -> Dict:
        """Get quick WMS stats for dashboard."""
        # Pending tasks
        task_result = await self.db.execute(
            select(func.count(WarehouseTask.id)).where(
                WarehouseTask.status.in_([TaskStatus.PENDING.value, TaskStatus.ASSIGNED.value])
            )
        )
        pending_tasks = task_result.scalar() or 0

        # Active workers
        worker_result = await self.db.execute(
            select(func.count(WarehouseWorker.id)).where(
                WarehouseWorker.status == WorkerStatus.ACTIVE.value
            )
        )
        active_workers = worker_result.scalar() or 0

        return {
            "pending_tasks": pending_tasks,
            "active_workers": active_workers,
        }
