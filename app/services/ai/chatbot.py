"""
AI-Powered ERP Chatbot Service

Provides natural language interface to ERP data:
- Sales queries ("What were sales last month?")
- Inventory queries ("How many units of X in stock?")
- Customer queries ("Show me pending orders")
- Financial queries ("What's our receivables position?")

Uses intent classification and SQL generation.
"""

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Optional, Tuple, Any
from uuid import UUID
import re
from collections import defaultdict

from sqlalchemy import select, func, and_, or_, desc, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order, OrderItem, OrderStatus
from app.models.product import Product
from app.models.customer import Customer
from app.models.inventory import InventorySummary
from app.models.billing import TaxInvoice as Invoice, InvoiceStatus
from app.models.service_request import ServiceRequest, ServiceStatus
from app.models.installation import Installation


# Intent patterns for classification
INTENT_PATTERNS = {
    "sales_total": [
        r"(total|how much|what).*(sales|revenue|sold)",
        r"sales.*(today|yesterday|this week|this month|last month)",
        r"revenue.*(today|yesterday|this week|this month|last month)",
    ],
    "order_count": [
        r"(how many|count|number of).*(orders|sales)",
        r"orders.*(today|yesterday|this week|this month)",
    ],
    "top_products": [
        r"(top|best|highest).*(selling|performing|products)",
        r"(popular|trending).*(products|items)",
    ],
    "inventory_check": [
        r"(how many|stock|inventory|available).*(units|quantity|items)",
        r"(in stock|available).*",
        r"stock.*(level|status|check)",
    ],
    "low_stock": [
        r"(low stock|out of stock|reorder|running out)",
        r"stock.*alert",
    ],
    "customer_info": [
        r"(customer|client).*(info|details|contact)",
        r"(show|find|get).*(customer|client)",
    ],
    "pending_orders": [
        r"(pending|open|unprocessed).*(orders|sales)",
        r"orders.*(pending|waiting|process)",
    ],
    "receivables": [
        r"(receivables|outstanding|due|unpaid).*(amount|invoices|balance)",
        r"(how much|what).*(owed|due|receivable)",
    ],
    "service_requests": [
        r"(service|support|complaint).*(requests|tickets|calls)",
        r"(open|pending).*(service|tickets|complaints)",
    ],
    "warranty_expiry": [
        r"(warranty|warranties).*(expiring|ending|due)",
    ],
    "help": [
        r"(help|what can|how to|guide)",
        r"(capabilities|features|options)",
    ]
}

# Time period extraction
TIME_PATTERNS = {
    "today": lambda: (date.today(), date.today()),
    "yesterday": lambda: (date.today() - timedelta(days=1), date.today() - timedelta(days=1)),
    "this week": lambda: (date.today() - timedelta(days=date.today().weekday()), date.today()),
    "last week": lambda: (
        date.today() - timedelta(days=date.today().weekday() + 7),
        date.today() - timedelta(days=date.today().weekday() + 1)
    ),
    "this month": lambda: (date.today().replace(day=1), date.today()),
    "last month": lambda: (
        (date.today().replace(day=1) - timedelta(days=1)).replace(day=1),
        date.today().replace(day=1) - timedelta(days=1)
    ),
    "this quarter": lambda: (
        date(date.today().year, ((date.today().month - 1) // 3) * 3 + 1, 1),
        date.today()
    ),
    "this year": lambda: (date(date.today().year, 1, 1), date.today()),
    "last 7 days": lambda: (date.today() - timedelta(days=7), date.today()),
    "last 30 days": lambda: (date.today() - timedelta(days=30), date.today()),
    "last 90 days": lambda: (date.today() - timedelta(days=90), date.today()),
}


class ERPChatbotService:
    """
    Natural language interface for ERP queries.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    def _classify_intent(self, query: str) -> Tuple[str, float]:
        """
        Classify the user's intent from their query.
        Returns: (intent, confidence)
        """
        query_lower = query.lower()

        best_intent = "unknown"
        best_score = 0

        for intent, patterns in INTENT_PATTERNS.items():
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

        for period_name, date_func in TIME_PATTERNS.items():
            if period_name in query_lower:
                return date_func()

        # Default to last 30 days
        return date.today() - timedelta(days=30), date.today()

    def _extract_product_name(self, query: str) -> Optional[str]:
        """Extract product name from query."""
        # Look for quoted strings
        quoted = re.findall(r'"([^"]+)"', query)
        if quoted:
            return quoted[0]

        quoted = re.findall(r"'([^']+)'", query)
        if quoted:
            return quoted[0]

        return None

    async def query(self, user_query: str) -> Dict:
        """
        Process a natural language query and return results.
        """
        # Classify intent
        intent, confidence = self._classify_intent(user_query)

        # Extract time period
        start_date, end_date = self._extract_time_period(user_query)

        # Route to appropriate handler
        handlers = {
            "sales_total": self._handle_sales_total,
            "order_count": self._handle_order_count,
            "top_products": self._handle_top_products,
            "inventory_check": self._handle_inventory_check,
            "low_stock": self._handle_low_stock,
            "customer_info": self._handle_customer_info,
            "pending_orders": self._handle_pending_orders,
            "receivables": self._handle_receivables,
            "service_requests": self._handle_service_requests,
            "warranty_expiry": self._handle_warranty_expiry,
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
                "end": end_date.isoformat()
            }
            return result
        except Exception as e:
            return {
                "answer": f"I encountered an error processing your query: {str(e)}",
                "intent": intent,
                "confidence": confidence,
                "error": True
            }

    # ==================== Intent Handlers ====================

    async def _handle_sales_total(
        self,
        query: str,
        start_date: date,
        end_date: date
    ) -> Dict:
        """Handle sales/revenue queries."""
        result = await self.db.execute(
            select(
                func.sum(Order.total_amount).label('total'),
                func.count(Order.id).label('count')
            ).where(
                and_(
                    Order.created_at >= start_date,
                    Order.created_at <= end_date + timedelta(days=1),
                    Order.status.in_([
                        OrderStatus.CONFIRMED,
                        OrderStatus.SHIPPED,
                        OrderStatus.DELIVERED,
                        OrderStatus.IN_TRANSIT
                    ])
                )
            )
        )
        row = result.one()

        total = float(row.total or 0)
        count = row.count or 0

        period_name = self._get_period_name(query)

        return {
            "answer": f"Total sales {period_name}: ₹{total:,.2f} from {count} orders.",
            "data": {
                "total_revenue": total,
                "order_count": count,
                "avg_order_value": round(total / count, 2) if count > 0 else 0
            },
            "visualization": "metric_card",
            "follow_up_suggestions": [
                "Show me top selling products",
                "Compare with last month",
                "Show daily breakdown"
            ]
        }

    async def _handle_order_count(
        self,
        query: str,
        start_date: date,
        end_date: date
    ) -> Dict:
        """Handle order count queries."""
        # Get counts by status
        result = await self.db.execute(
            select(
                Order.status,
                func.count(Order.id).label('count')
            ).where(
                and_(
                    Order.created_at >= start_date,
                    Order.created_at <= end_date + timedelta(days=1)
                )
            ).group_by(Order.status)
        )
        rows = result.all()

        status_counts = {str(r.status): r.count for r in rows}
        total = sum(status_counts.values())

        period_name = self._get_period_name(query)

        return {
            "answer": f"Total orders {period_name}: {total}",
            "data": {
                "total": total,
                "by_status": status_counts
            },
            "visualization": "pie_chart",
            "follow_up_suggestions": [
                "Show pending orders",
                "Show order trends",
                "What's the average order value?"
            ]
        }

    async def _handle_top_products(
        self,
        query: str,
        start_date: date,
        end_date: date
    ) -> Dict:
        """Handle top products queries."""
        result = await self.db.execute(
            select(
                Product.name,
                Product.sku,
                func.sum(OrderItem.quantity).label('qty'),
                func.sum(OrderItem.total_amount).label('revenue')
            ).join(
                OrderItem, Product.id == OrderItem.product_id
            ).join(
                Order, OrderItem.order_id == Order.id
            ).where(
                and_(
                    Order.created_at >= start_date,
                    Order.created_at <= end_date + timedelta(days=1),
                    Order.status != OrderStatus.CANCELLED
                )
            ).group_by(
                Product.id, Product.name, Product.sku
            ).order_by(
                desc(func.sum(OrderItem.total_amount))
            ).limit(10)
        )
        rows = result.all()

        products = [
            {
                "name": r.name,
                "sku": r.sku,
                "quantity_sold": r.qty,
                "revenue": float(r.revenue or 0)
            }
            for r in rows
        ]

        period_name = self._get_period_name(query)

        if products:
            top = products[0]
            answer = f"Top selling product {period_name}: {top['name']} with ₹{top['revenue']:,.2f} in sales ({top['quantity_sold']} units)"
        else:
            answer = f"No sales data found {period_name}."

        return {
            "answer": answer,
            "data": {"products": products},
            "visualization": "bar_chart",
            "follow_up_suggestions": [
                "Show product inventory levels",
                "Compare with previous period",
                "Show by category"
            ]
        }

    async def _handle_inventory_check(
        self,
        query: str,
        start_date: date,
        end_date: date
    ) -> Dict:
        """Handle inventory queries."""
        product_name = self._extract_product_name(query)

        if product_name:
            # Search for specific product
            result = await self.db.execute(
                select(
                    Product.name,
                    Product.sku,
                    InventorySummary.available_quantity,
                    InventorySummary.reserved_quantity,
                    InventorySummary.reorder_level
                ).join(
                    InventorySummary, Product.id == InventorySummary.product_id
                ).where(
                    or_(
                        Product.name.ilike(f"%{product_name}%"),
                        Product.sku.ilike(f"%{product_name}%")
                    )
                ).limit(5)
            )
            rows = result.all()

            if rows:
                items = [
                    {
                        "name": r.name,
                        "sku": r.sku,
                        "available": r.available_quantity,
                        "reserved": r.reserved_quantity,
                        "reorder_level": r.reorder_level
                    }
                    for r in rows
                ]
                answer = f"Found {len(items)} matching product(s). {items[0]['name']}: {items[0]['available']} units available."
            else:
                items = []
                answer = f"No products found matching '{product_name}'."

            return {
                "answer": answer,
                "data": {"items": items},
                "visualization": "table"
            }
        else:
            # Overall inventory summary
            result = await self.db.execute(
                select(
                    func.count(InventorySummary.product_id).label('total_products'),
                    func.sum(InventorySummary.available_quantity).label('total_qty'),
                    func.sum(InventorySummary.total_value).label('total_value')
                )
            )
            row = result.one()

            return {
                "answer": f"Inventory summary: {row.total_products} products, {row.total_qty or 0} total units, value ₹{float(row.total_value or 0):,.2f}",
                "data": {
                    "total_products": row.total_products,
                    "total_quantity": row.total_qty or 0,
                    "total_value": float(row.total_value or 0)
                },
                "visualization": "metric_card",
                "follow_up_suggestions": [
                    "Show low stock items",
                    "Check stock for 'filter'",
                    "Show inventory by category"
                ]
            }

    async def _handle_low_stock(
        self,
        query: str,
        start_date: date,
        end_date: date
    ) -> Dict:
        """Handle low stock queries."""
        result = await self.db.execute(
            select(
                Product.name,
                Product.sku,
                InventorySummary.available_quantity,
                InventorySummary.reorder_level
            ).join(
                InventorySummary, Product.id == InventorySummary.product_id
            ).where(
                InventorySummary.available_quantity <= InventorySummary.reorder_level
            ).order_by(
                InventorySummary.available_quantity.asc()
            ).limit(20)
        )
        rows = result.all()

        items = [
            {
                "name": r.name,
                "sku": r.sku,
                "available": r.available_quantity,
                "reorder_level": r.reorder_level
            }
            for r in rows
        ]

        if items:
            answer = f"Found {len(items)} items below reorder level. Most critical: {items[0]['name']} ({items[0]['available']} units)."
        else:
            answer = "All items are above reorder level. Inventory looks healthy!"

        return {
            "answer": answer,
            "data": {"low_stock_items": items},
            "visualization": "table",
            "follow_up_suggestions": [
                "Create purchase order",
                "Show demand forecast",
                "Show supplier contacts"
            ]
        }

    async def _handle_customer_info(
        self,
        query: str,
        start_date: date,
        end_date: date
    ) -> Dict:
        """Handle customer queries."""
        # Extract customer name/phone
        search_term = self._extract_product_name(query)  # Reuse for quoted strings

        if search_term:
            result = await self.db.execute(
                select(Customer).where(
                    or_(
                        Customer.name.ilike(f"%{search_term}%"),
                        Customer.phone.ilike(f"%{search_term}%"),
                        Customer.email.ilike(f"%{search_term}%")
                    )
                ).limit(5)
            )
            customers = result.scalars().all()

            if customers:
                items = [
                    {
                        "name": c.name,
                        "phone": c.phone,
                        "email": c.email,
                        "city": c.city
                    }
                    for c in customers
                ]
                answer = f"Found {len(items)} customer(s) matching '{search_term}'."
            else:
                items = []
                answer = f"No customers found matching '{search_term}'."
        else:
            # Customer stats
            result = await self.db.execute(
                select(func.count(Customer.id))
            )
            count = result.scalar()

            items = []
            answer = f"Total customers in database: {count}"

        return {
            "answer": answer,
            "data": {"customers": items} if items else {"total": count},
            "visualization": "table" if items else "metric_card"
        }

    async def _handle_pending_orders(
        self,
        query: str,
        start_date: date,
        end_date: date
    ) -> Dict:
        """Handle pending orders queries."""
        result = await self.db.execute(
            select(
                Order.order_number,
                Order.created_at,
                Order.total_amount,
                Order.status,
                Customer.name.label('customer_name')
            ).join(
                Customer, Order.customer_id == Customer.id
            ).where(
                Order.status.in_([OrderStatus.PENDING, OrderStatus.CONFIRMED, OrderStatus.PROCESSING])
            ).order_by(
                Order.created_at.asc()
            ).limit(20)
        )
        rows = result.all()

        orders = [
            {
                "order_number": r.order_number,
                "customer": r.customer_name,
                "amount": float(r.total_amount or 0),
                "status": r.status,
                "date": r.created_at.isoformat() if r.created_at else None
            }
            for r in rows
        ]

        total_value = sum(o["amount"] for o in orders)

        return {
            "answer": f"Found {len(orders)} pending orders worth ₹{total_value:,.2f}.",
            "data": {"orders": orders, "total_value": total_value},
            "visualization": "table",
            "follow_up_suggestions": [
                "Show oldest pending orders",
                "Process pending orders",
                "Show orders by status"
            ]
        }

    async def _handle_receivables(
        self,
        query: str,
        start_date: date,
        end_date: date
    ) -> Dict:
        """Handle receivables queries."""
        result = await self.db.execute(
            select(
                func.sum(Invoice.total_amount).label('total'),
                func.count(Invoice.id).label('count')
            ).where(
                Invoice.status.in_([InvoiceStatus.PENDING, InvoiceStatus.SENT])
            )
        )
        row = result.one()

        total = float(row.total or 0)
        count = row.count or 0

        # Get overdue
        overdue_result = await self.db.execute(
            select(
                func.sum(Invoice.total_amount).label('total'),
                func.count(Invoice.id).label('count')
            ).where(
                and_(
                    Invoice.status.in_([InvoiceStatus.PENDING, InvoiceStatus.SENT]),
                    Invoice.due_date < date.today()
                )
            )
        )
        overdue = overdue_result.one()
        overdue_total = float(overdue.total or 0)

        return {
            "answer": f"Total receivables: ₹{total:,.2f} from {count} invoices. Overdue: ₹{overdue_total:,.2f}",
            "data": {
                "total_receivables": total,
                "invoice_count": count,
                "overdue_amount": overdue_total,
                "overdue_count": overdue.count or 0
            },
            "visualization": "metric_card",
            "follow_up_suggestions": [
                "Show overdue invoices",
                "Predict collections",
                "Show aging analysis"
            ]
        }

    async def _handle_service_requests(
        self,
        query: str,
        start_date: date,
        end_date: date
    ) -> Dict:
        """Handle service request queries."""
        result = await self.db.execute(
            select(
                ServiceRequest.status,
                func.count(ServiceRequest.id).label('count')
            ).group_by(ServiceRequest.status)
        )
        rows = result.all()

        status_counts = {str(r.status): r.count for r in rows}
        total = sum(status_counts.values())
        open_count = status_counts.get('PENDING', 0) + status_counts.get('ASSIGNED', 0) + status_counts.get('SCHEDULED', 0)

        return {
            "answer": f"Total service requests: {total}. Open tickets: {open_count}",
            "data": {
                "total": total,
                "open": open_count,
                "by_status": status_counts
            },
            "visualization": "pie_chart",
            "follow_up_suggestions": [
                "Show urgent tickets",
                "Show technician workload",
                "Show SLA breaches"
            ]
        }

    async def _handle_warranty_expiry(
        self,
        query: str,
        start_date: date,
        end_date: date
    ) -> Dict:
        """Handle warranty expiry queries."""
        # Warranties expiring in next 30 days
        expiry_date = date.today() + timedelta(days=30)

        result = await self.db.execute(
            select(
                Installation.installation_number,
                Installation.warranty_end_date,
                Customer.name.label('customer_name'),
                Product.name.label('product_name')
            ).join(
                Customer, Installation.customer_id == Customer.id
            ).join(
                Product, Installation.product_id == Product.id
            ).where(
                and_(
                    Installation.warranty_end_date >= date.today(),
                    Installation.warranty_end_date <= expiry_date
                )
            ).order_by(
                Installation.warranty_end_date.asc()
            ).limit(20)
        )
        rows = result.all()

        warranties = [
            {
                "installation": r.installation_number,
                "customer": r.customer_name,
                "product": r.product_name,
                "expiry_date": r.warranty_end_date.isoformat() if r.warranty_end_date else None
            }
            for r in rows
        ]

        return {
            "answer": f"{len(warranties)} warranties expiring in the next 30 days.",
            "data": {"warranties": warranties},
            "visualization": "table",
            "follow_up_suggestions": [
                "Send renewal reminders",
                "Show AMC opportunities",
                "Contact these customers"
            ]
        }

    async def _handle_help(
        self,
        query: str,
        start_date: date,
        end_date: date
    ) -> Dict:
        """Handle help queries."""
        return {
            "answer": "I can help you with the following queries:",
            "data": {
                "capabilities": [
                    {"category": "Sales", "examples": ["What were sales this month?", "Show top selling products", "Total orders today"]},
                    {"category": "Inventory", "examples": ["Stock for 'RO Filter'", "Show low stock items", "Inventory value"]},
                    {"category": "Customers", "examples": ["Find customer 'John'", "Pending orders", "Customer count"]},
                    {"category": "Finance", "examples": ["What are our receivables?", "Overdue invoices", "Cash flow"]},
                    {"category": "Service", "examples": ["Open service tickets", "Warranties expiring", "SLA status"]}
                ]
            },
            "visualization": "list"
        }

    async def _handle_unknown(
        self,
        query: str,
        start_date: date,
        end_date: date
    ) -> Dict:
        """Handle unknown queries."""
        return {
            "answer": "I'm not sure how to answer that. Try asking about sales, orders, inventory, customers, or service requests.",
            "data": None,
            "follow_up_suggestions": [
                "What were sales this month?",
                "Show low stock items",
                "Open service tickets",
                "Help"
            ]
        }

    def _get_period_name(self, query: str) -> str:
        """Extract human-readable period name from query."""
        query_lower = query.lower()
        for period in TIME_PATTERNS.keys():
            if period in query_lower:
                return period
        return "in the selected period"

    # ==================== Quick Stats ====================

    async def get_quick_stats(self) -> Dict:
        """
        Get quick stats for chatbot initial display.
        """
        today = date.today()
        month_start = today.replace(day=1)

        # Today's orders
        today_orders = await self.db.execute(
            select(
                func.count(Order.id).label('count'),
                func.sum(Order.total_amount).label('total')
            ).where(
                func.date(Order.created_at) == today
            )
        )
        today_row = today_orders.one()

        # Month's orders
        month_orders = await self.db.execute(
            select(
                func.count(Order.id).label('count'),
                func.sum(Order.total_amount).label('total')
            ).where(
                Order.created_at >= month_start
            )
        )
        month_row = month_orders.one()

        # Open tickets
        tickets = await self.db.execute(
            select(func.count(ServiceRequest.id)).where(
                ServiceRequest.status.in_([
                    ServiceStatus.PENDING,
                    ServiceStatus.ASSIGNED,
                    ServiceStatus.SCHEDULED
                ])
            )
        )
        open_tickets = tickets.scalar() or 0

        return {
            "today": {
                "orders": today_row.count or 0,
                "revenue": float(today_row.total or 0)
            },
            "this_month": {
                "orders": month_row.count or 0,
                "revenue": float(month_row.total or 0)
            },
            "open_tickets": open_tickets,
            "suggested_queries": [
                "What were sales this week?",
                "Show top products",
                "Low stock items",
                "Pending orders"
            ]
        }
