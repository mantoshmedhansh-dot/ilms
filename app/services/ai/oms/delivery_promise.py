"""
OMS Delivery Promise (ATP) Agent

Calculates delivery promise dates:
- Inventory check across serviceable warehouses
- Transit time from WarehouseServiceability.estimated_days
- Processing time from historical Order status timestamps
- Day-of-week buffer

Returns: earliest_date, latest_date, confidence, breakdown

No external ML libraries required - pure Python implementation.
"""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import List, Dict, Optional, Any
from uuid import UUID
import math
from collections import defaultdict

from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order, OrderItem, OrderStatus
from app.models.inventory import InventorySummary
from app.models.warehouse import Warehouse
from app.models.serviceability import WarehouseServiceability


class OMSDeliveryPromiseAgent:
    """
    Calculates delivery promise dates with confidence levels.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self._status = "idle"
        self._last_run = None
        self._results = None

    async def _get_processing_time(self) -> Dict:
        """Estimate processing time from historical order timestamps."""
        # Get average time from CONFIRMED to SHIPPED
        result = await self.db.execute(
            select(
                func.avg(
                    func.extract('epoch', Order.updated_at) -
                    func.extract('epoch', Order.confirmed_at)
                ).label("avg_processing_secs"),
            )
            .where(
                and_(
                    Order.confirmed_at.isnot(None),
                    Order.status.in_([
                        OrderStatus.SHIPPED.value,
                        OrderStatus.DELIVERED.value,
                        OrderStatus.IN_TRANSIT.value,
                    ]),
                )
            )
        )
        row = result.one()

        avg_secs = float(row.avg_processing_secs or 0)
        avg_days = avg_secs / 86400 if avg_secs > 0 else 2.0

        # Cap between 0.5 and 7 days
        avg_days = max(0.5, min(7, avg_days))

        return {
            "avg_processing_days": round(avg_days, 1),
            "min_processing_days": max(0.5, round(avg_days * 0.7, 1)),
            "max_processing_days": round(avg_days * 1.5, 1),
        }

    async def _check_inventory_availability(
        self, product_id: UUID, pincode: str, quantity: int = 1
    ) -> List[Dict]:
        """Check inventory availability across serviceable warehouses."""
        # Get serviceable warehouses for pincode
        result = await self.db.execute(
            select(
                WarehouseServiceability.warehouse_id,
                WarehouseServiceability.estimated_days,
                WarehouseServiceability.shipping_cost,
                Warehouse.name.label("warehouse_name"),
                Warehouse.city.label("warehouse_city"),
                InventorySummary.available_quantity,
            )
            .join(Warehouse, WarehouseServiceability.warehouse_id == Warehouse.id)
            .outerjoin(
                InventorySummary,
                and_(
                    InventorySummary.warehouse_id == WarehouseServiceability.warehouse_id,
                    InventorySummary.product_id == product_id,
                ),
            )
            .where(
                and_(
                    WarehouseServiceability.pincode == pincode,
                    WarehouseServiceability.is_serviceable == True,
                    WarehouseServiceability.is_active == True,
                )
            )
            .order_by(WarehouseServiceability.estimated_days)
        )
        rows = result.all()

        options = []
        for row in rows:
            available = int(row.available_quantity or 0)
            if available >= quantity:
                options.append({
                    "warehouse_id": str(row.warehouse_id),
                    "warehouse_name": row.warehouse_name,
                    "warehouse_city": row.warehouse_city,
                    "transit_days": row.estimated_days or 5,
                    "shipping_cost": float(row.shipping_cost or 0),
                    "available_qty": available,
                    "in_stock": True,
                })

        return options

    def _calculate_dow_buffer(self, start_date: date) -> int:
        """Add buffer for weekends and holidays."""
        # Simple: if delivery falls on Sunday, push to Monday
        dow = start_date.weekday()
        if dow == 6:  # Sunday
            return 1
        return 0

    # ==================== Main Analysis ====================

    async def analyze(
        self,
        product_id: Optional[UUID] = None,
        pincode: Optional[str] = None,
        quantity: int = 1,
    ) -> Dict:
        """Calculate delivery promise for a product + pincode."""
        self._status = "running"
        try:
            processing = await self._get_processing_time()

            if product_id and pincode:
                options = await self._check_inventory_availability(product_id, pincode, quantity)

                if not options:
                    self._results = {
                        "agent": "delivery_promise",
                        "generated_at": datetime.now(timezone.utc).isoformat(),
                        "product_id": str(product_id),
                        "pincode": pincode,
                        "quantity": quantity,
                        "available": False,
                        "message": "Product not available for delivery to this pincode",
                        "processing_time": processing,
                    }
                    self._status = "completed"
                    self._last_run = datetime.now(timezone.utc)
                    return self._results

                # Best option (fastest delivery)
                best = options[0]
                transit = best["transit_days"]

                today = date.today()
                min_proc = processing["min_processing_days"]
                avg_proc = processing["avg_processing_days"]
                max_proc = processing["max_processing_days"]

                earliest_date = today + timedelta(days=math.ceil(min_proc + transit))
                expected_date = today + timedelta(days=math.ceil(avg_proc + transit))
                latest_date = today + timedelta(days=math.ceil(max_proc + transit))

                # DOW buffer
                dow_buf = self._calculate_dow_buffer(expected_date)
                expected_date += timedelta(days=dow_buf)
                latest_date += timedelta(days=dow_buf)

                # Confidence based on data quality
                confidence = 0.85
                if len(options) > 2:
                    confidence = 0.90
                if processing["avg_processing_days"] > 4:
                    confidence -= 0.10

                self._results = {
                    "agent": "delivery_promise",
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "product_id": str(product_id),
                    "pincode": pincode,
                    "quantity": quantity,
                    "available": True,
                    "earliest_date": earliest_date.isoformat(),
                    "expected_date": expected_date.isoformat(),
                    "latest_date": latest_date.isoformat(),
                    "confidence": round(confidence, 2),
                    "breakdown": {
                        "processing_days": processing["avg_processing_days"],
                        "transit_days": transit,
                        "dow_buffer": dow_buf,
                        "total_days": math.ceil(avg_proc + transit + dow_buf),
                    },
                    "fulfillment_warehouse": best["warehouse_name"],
                    "warehouse_city": best["warehouse_city"],
                    "shipping_cost": best["shipping_cost"],
                    "alternative_warehouses": len(options) - 1,
                    "processing_time": processing,
                }
            else:
                # General processing time stats
                self._results = {
                    "agent": "delivery_promise",
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "processing_time": processing,
                    "message": "Provide product_id and pincode for specific delivery promise",
                }

            self._status = "completed"
            self._last_run = datetime.now(timezone.utc)
            return self._results

        except Exception as e:
            self._status = "error"
            return {"agent": "delivery_promise", "error": str(e), "status": "error"}

    async def get_recommendations(self) -> List[Dict]:
        if not self._results:
            return []
        if not self._results.get("available", True):
            return [{
                "type": "delivery_promise",
                "severity": "MEDIUM",
                "recommendation": "Product not serviceable at requested pincode. Consider expanding warehouse serviceability.",
            }]
        return []

    async def get_status(self) -> Dict:
        return {
            "id": "delivery_promise",
            "name": "Delivery Promise (ATP) Agent",
            "description": "Calculates delivery dates based on inventory, processing time, transit, and day-of-week patterns",
            "status": self._status,
            "last_run": self._last_run.isoformat() if self._last_run else None,
            "data_sources": "Order, InventorySummary, WarehouseServiceability, Warehouse",
            "capabilities": [
                "Delivery date calculation",
                "Inventory availability check",
                "Processing time estimation",
                "Confidence scoring",
                "Multi-warehouse fallback",
            ],
        }
