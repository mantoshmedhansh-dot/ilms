"""Channel-wise P&L and Balance Sheet Reports API endpoints."""
from typing import Optional
from uuid import UUID
from datetime import datetime, date, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy import select, func, desc, and_, or_, case

from app.api.deps import DB, get_current_user
from app.models.user import User
from app.models.order import Order, OrderItem
from app.models.channel import SalesChannel
from app.models.accounting import ChartOfAccount, JournalEntry, JournalEntryLine
from app.core.module_decorators import require_module

router = APIRouter()


# ==================== Channel P&L Report ====================
@router.get("/pnl")
@require_module("sales_distribution")
async def get_channel_pnl(
    db: DB,
    current_user: User = Depends(get_current_user),
    channel_id: Optional[UUID] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    year: Optional[int] = None,
    month: Optional[int] = None,
):
    """
    Get Profit & Loss report by channel.

    If channel_id is provided, returns P&L for that channel.
    Otherwise, returns comparative P&L across all channels.
    """
    # Default to current month if no dates provided
    if not start_date and not end_date:
        if year and month:
            start_date = date(year, month, 1)
            if month == 12:
                end_date = date(year + 1, 1, 1) - timedelta(days=1)
            else:
                end_date = date(year, month + 1, 1) - timedelta(days=1)
        else:
            today = date.today()
            start_date = today.replace(day=1)
            end_date = today

    # Get all channels for comparison
    channels_query = select(SalesChannel).where(SalesChannel.status == "ACTIVE")
    if channel_id:
        channels_query = channels_query.where(SalesChannel.id == channel_id)

    channels_result = await db.execute(channels_query)
    channels = channels_result.scalars().all()

    pnl_data = []

    for channel in channels:
        # Revenue (Sales)
        revenue_query = select(
            func.coalesce(func.sum(Order.total_amount), 0).label("gross_revenue"),
            func.coalesce(func.sum(Order.discount_amount), 0).label("discounts"),
            func.coalesce(func.sum(Order.tax_amount), 0).label("taxes_collected"),
            func.count(Order.id).label("order_count")
        ).where(
            and_(
                Order.channel_id == channel.id,
                Order.status.notin_(["CANCELLED", "DRAFT"]),
                Order.created_at >= start_date,
                Order.created_at <= end_date
            )
        )
        revenue_result = await db.execute(revenue_query)
        revenue_data = revenue_result.one()

        gross_revenue = float(revenue_data.gross_revenue or 0)
        discounts = float(revenue_data.discounts or 0)
        net_revenue = gross_revenue - discounts

        # Cost of Goods Sold (from order items)
        cogs_query = select(
            func.coalesce(func.sum(OrderItem.quantity * OrderItem.unit_cost), 0)
        ).select_from(OrderItem).join(
            Order, OrderItem.order_id == Order.id
        ).where(
            and_(
                Order.channel_id == channel.id,
                Order.status.notin_(["CANCELLED", "DRAFT"]),
                Order.created_at >= start_date,
                Order.created_at <= end_date
            )
        )
        cogs = float(await db.scalar(cogs_query) or 0)

        gross_profit = net_revenue - cogs
        gross_margin = (gross_profit / net_revenue * 100) if net_revenue > 0 else 0

        # Operating Expenses (from journal entries linked to channel)
        # For now, we'll estimate based on channel commission rates
        commission_rate = float(channel.commission_percent or 0) / 100
        channel_fees = net_revenue * commission_rate

        # Shipping costs (from orders)
        shipping_query = select(
            func.coalesce(func.sum(Order.shipping_amount), 0)
        ).where(
            and_(
                Order.channel_id == channel.id,
                Order.status.notin_(["CANCELLED", "DRAFT"]),
                Order.created_at >= start_date,
                Order.created_at <= end_date
            )
        )
        shipping_costs = float(await db.scalar(shipping_query) or 0)

        # Payment processing fees (estimated at 2%)
        payment_fees = net_revenue * 0.02

        operating_expenses = channel_fees + shipping_costs + payment_fees
        operating_income = gross_profit - operating_expenses
        operating_margin = (operating_income / net_revenue * 100) if net_revenue > 0 else 0

        # Net income (after allocating fixed costs proportionally)
        # For simplicity, using operating income as net income
        net_income = operating_income
        net_margin = (net_income / net_revenue * 100) if net_revenue > 0 else 0

        pnl_data.append({
            "channel_id": str(channel.id),
            "channel_name": channel.name,
            "channel_type": channel.channel_type,
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
            "revenue": {
                "gross_revenue": gross_revenue,
                "discounts": discounts,
                "net_revenue": net_revenue,
                "order_count": revenue_data.order_count,
            },
            "cost_of_goods_sold": cogs,
            "gross_profit": gross_profit,
            "gross_margin_percent": round(gross_margin, 2),
            "operating_expenses": {
                "channel_fees": round(channel_fees, 2),
                "shipping_costs": shipping_costs,
                "payment_processing": round(payment_fees, 2),
                "total": round(operating_expenses, 2),
            },
            "operating_income": round(operating_income, 2),
            "operating_margin_percent": round(operating_margin, 2),
            "net_income": round(net_income, 2),
            "net_margin_percent": round(net_margin, 2),
        })

    # Calculate totals
    total_revenue = sum(p["revenue"]["net_revenue"] for p in pnl_data)
    total_cogs = sum(p["cost_of_goods_sold"] for p in pnl_data)
    total_gross_profit = sum(p["gross_profit"] for p in pnl_data)
    total_operating_income = sum(p["operating_income"] for p in pnl_data)
    total_net_income = sum(p["net_income"] for p in pnl_data)

    return {
        "report_type": "Channel P&L",
        "period": {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        },
        "channels": pnl_data,
        "totals": {
            "net_revenue": total_revenue,
            "cost_of_goods_sold": total_cogs,
            "gross_profit": total_gross_profit,
            "gross_margin_percent": round((total_gross_profit / total_revenue * 100) if total_revenue > 0 else 0, 2),
            "operating_income": round(total_operating_income, 2),
            "net_income": round(total_net_income, 2),
            "net_margin_percent": round((total_net_income / total_revenue * 100) if total_revenue > 0 else 0, 2),
        },
    }


# ==================== Channel Balance Sheet ====================
@router.get("/balance-sheet")
@require_module("sales_distribution")
async def get_channel_balance_sheet(
    db: DB,
    current_user: User = Depends(get_current_user),
    channel_id: Optional[UUID] = None,
    as_of_date: Optional[date] = None,
):
    """
    Get Balance Sheet report by channel.

    Shows assets, liabilities, and equity position for each channel.
    """
    if not as_of_date:
        as_of_date = date.today()

    # Get all channels
    channels_query = select(SalesChannel).where(SalesChannel.status == "ACTIVE")
    if channel_id:
        channels_query = channels_query.where(SalesChannel.id == channel_id)

    channels_result = await db.execute(channels_query)
    channels = channels_result.scalars().all()

    balance_sheets = []

    for channel in channels:
        # Current Assets
        # Accounts Receivable (unpaid orders)
        ar_query = select(
            func.coalesce(func.sum(Order.total_amount - Order.paid_amount), 0)
        ).where(
            and_(
                Order.channel_id == channel.id,
                Order.status.notin_(["CANCELLED", "DRAFT"]),
                Order.payment_status != "PAID",
                Order.created_at <= as_of_date
            )
        )
        accounts_receivable = float(await db.scalar(ar_query) or 0)

        # Inventory allocated to channel (estimate based on sales ratio)
        # For simplicity, using a placeholder
        inventory = 0  # Would need inventory allocation model

        # Prepaid expenses (channel-specific prepayments)
        prepaid = 0

        total_current_assets = accounts_receivable + inventory + prepaid

        # Fixed Assets
        # Channel-specific equipment, software licenses, etc.
        fixed_assets = 0

        total_assets = total_current_assets + fixed_assets

        # Current Liabilities
        # Accounts Payable (to channel/marketplace)
        # Pending settlements, commissions owed
        commission_rate = float(channel.commission_percent or 0) / 100

        # Estimate pending commission based on recent sales
        pending_comm_query = select(
            func.coalesce(func.sum(Order.total_amount), 0)
        ).where(
            and_(
                Order.channel_id == channel.id,
                Order.status == "DELIVERED",
                Order.created_at >= as_of_date - timedelta(days=30),
                Order.created_at <= as_of_date
            )
        )
        recent_sales = float(await db.scalar(pending_comm_query) or 0)
        accounts_payable = recent_sales * commission_rate

        # Deferred Revenue (prepaid orders)
        deferred_revenue_query = select(
            func.coalesce(func.sum(Order.paid_amount), 0)
        ).where(
            and_(
                Order.channel_id == channel.id,
                Order.status.in_(["PENDING", "CONFIRMED", "PROCESSING"]),
                Order.payment_status == "PAID"
            )
        )
        deferred_revenue = float(await db.scalar(deferred_revenue_query) or 0)

        total_current_liabilities = accounts_payable + deferred_revenue

        # Long-term Liabilities
        long_term_liabilities = 0

        total_liabilities = total_current_liabilities + long_term_liabilities

        # Equity
        # Retained earnings from channel (cumulative profit)
        retained_earnings_query = select(
            func.coalesce(func.sum(Order.total_amount - Order.discount_amount), 0)
        ).where(
            and_(
                Order.channel_id == channel.id,
                Order.status == "DELIVERED",
                Order.created_at <= as_of_date
            )
        )
        cumulative_revenue = float(await db.scalar(retained_earnings_query) or 0)
        # Estimate retained earnings as 10% of revenue (after all costs)
        retained_earnings = cumulative_revenue * 0.10

        total_equity = retained_earnings

        # Balance check
        balance_check = total_assets - total_liabilities - total_equity

        balance_sheets.append({
            "channel_id": str(channel.id),
            "channel_name": channel.name,
            "channel_type": channel.channel_type,
            "as_of_date": as_of_date.isoformat(),
            "assets": {
                "current_assets": {
                    "accounts_receivable": round(accounts_receivable, 2),
                    "inventory": round(inventory, 2),
                    "prepaid_expenses": round(prepaid, 2),
                    "total": round(total_current_assets, 2),
                },
                "fixed_assets": round(fixed_assets, 2),
                "total_assets": round(total_assets, 2),
            },
            "liabilities": {
                "current_liabilities": {
                    "accounts_payable": round(accounts_payable, 2),
                    "deferred_revenue": round(deferred_revenue, 2),
                    "total": round(total_current_liabilities, 2),
                },
                "long_term_liabilities": round(long_term_liabilities, 2),
                "total_liabilities": round(total_liabilities, 2),
            },
            "equity": {
                "retained_earnings": round(retained_earnings, 2),
                "total_equity": round(total_equity, 2),
            },
            "balance_check": round(balance_check, 2),
        })

    # Calculate totals
    total_assets = sum(b["assets"]["total_assets"] for b in balance_sheets)
    total_liabilities = sum(b["liabilities"]["total_liabilities"] for b in balance_sheets)
    total_equity = sum(b["equity"]["total_equity"] for b in balance_sheets)

    return {
        "report_type": "Channel Balance Sheet",
        "as_of_date": as_of_date.isoformat(),
        "channels": balance_sheets,
        "totals": {
            "total_assets": round(total_assets, 2),
            "total_liabilities": round(total_liabilities, 2),
            "total_equity": round(total_equity, 2),
        },
    }


# ==================== Channel Comparison Report ====================
@router.get("/comparison")
@require_module("sales_distribution")
async def get_channel_comparison(
    db: DB,
    current_user: User = Depends(get_current_user),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    metric: str = Query("revenue", pattern="^(revenue|orders|margin|aov)$"),
):
    """
    Compare channels by selected metric.

    Metrics:
    - revenue: Total revenue
    - orders: Order count
    - margin: Profit margin percentage
    - aov: Average order value
    """
    if not start_date:
        start_date = date.today() - timedelta(days=30)
    if not end_date:
        end_date = date.today()

    # Get all active channels
    channels_query = select(SalesChannel).where(SalesChannel.status == "ACTIVE")
    channels_result = await db.execute(channels_query)
    channels = channels_result.scalars().all()

    comparison = []

    for channel in channels:
        # Get channel metrics
        metrics_query = select(
            func.count(Order.id).label("orders"),
            func.coalesce(func.sum(Order.total_amount), 0).label("revenue"),
            func.coalesce(func.avg(Order.total_amount), 0).label("aov")
        ).where(
            and_(
                Order.channel_id == channel.id,
                Order.status.notin_(["CANCELLED", "DRAFT"]),
                Order.created_at >= start_date,
                Order.created_at <= end_date
            )
        )
        metrics_result = await db.execute(metrics_query)
        metrics = metrics_result.one()

        # Calculate COGS for margin
        cogs_query = select(
            func.coalesce(func.sum(OrderItem.quantity * OrderItem.unit_cost), 0)
        ).select_from(OrderItem).join(
            Order, OrderItem.order_id == Order.id
        ).where(
            and_(
                Order.channel_id == channel.id,
                Order.status.notin_(["CANCELLED", "DRAFT"]),
                Order.created_at >= start_date,
                Order.created_at <= end_date
            )
        )
        cogs = float(await db.scalar(cogs_query) or 0)

        revenue = float(metrics.revenue or 0)
        gross_profit = revenue - cogs
        margin = (gross_profit / revenue * 100) if revenue > 0 else 0

        comparison.append({
            "channel_id": str(channel.id),
            "channel_name": channel.name,
            "channel_type": channel.channel_type,
            "orders": metrics.orders,
            "revenue": revenue,
            "aov": round(float(metrics.aov or 0), 2),
            "margin_percent": round(margin, 2),
        })

    # Sort by selected metric
    if metric == "revenue":
        comparison.sort(key=lambda x: x["revenue"], reverse=True)
    elif metric == "orders":
        comparison.sort(key=lambda x: x["orders"], reverse=True)
    elif metric == "margin":
        comparison.sort(key=lambda x: x["margin_percent"], reverse=True)
    elif metric == "aov":
        comparison.sort(key=lambda x: x["aov"], reverse=True)

    return {
        "report_type": "Channel Comparison",
        "period": {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        },
        "sorted_by": metric,
        "channels": comparison,
    }


# ==================== Channel Performance Trend ====================
@router.get("/trend")
@require_module("sales_distribution")
async def get_channel_trend(
    db: DB,
    current_user: User = Depends(get_current_user),
    channel_id: Optional[UUID] = None,
    days: int = Query(30, ge=7, le=365),
    group_by: str = Query("day", pattern="^(day|week|month)$"),
):
    """Get channel performance trend over time."""
    start_date = date.today() - timedelta(days=days)

    conditions = [
        Order.status.notin_(["CANCELLED", "DRAFT"]),
        Order.created_at >= start_date
    ]
    if channel_id:
        conditions.append(Order.channel_id == channel_id)

    if group_by == "day":
        date_expr = func.date(Order.created_at)
    elif group_by == "week":
        date_expr = func.date_trunc('week', Order.created_at)
    else:
        date_expr = func.date_trunc('month', Order.created_at)

    query = select(
        date_expr.label("period"),
        SalesChannel.name.label("channel_name"),
        func.count(Order.id).label("orders"),
        func.coalesce(func.sum(Order.total_amount), 0).label("revenue")
    ).select_from(Order).join(
        SalesChannel, Order.channel_id == SalesChannel.id
    ).where(
        and_(*conditions)
    ).group_by(date_expr, SalesChannel.name).order_by(date_expr)

    result = await db.execute(query)
    data = result.all()

    # Group by channel
    channels_data = {}
    for row in data:
        channel_name = row.channel_name
        if channel_name not in channels_data:
            channels_data[channel_name] = {"labels": [], "orders": [], "revenue": []}
        channels_data[channel_name]["labels"].append(str(row.period)[:10])
        channels_data[channel_name]["orders"].append(row.orders)
        channels_data[channel_name]["revenue"].append(float(row.revenue or 0))

    return {
        "period_days": days,
        "group_by": group_by,
        "channels": channels_data,
    }
