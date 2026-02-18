"""Channel-wise P&L and Balance Sheet Reports API endpoints.

Enhanced with:
- Geographic drill-down (Region → Cluster → Warehouse)
- Manpower costs from HRMS (Payslip → Employee → CostCenter → Warehouse)
- Warehouse logistics/billing costs (StorageCharge, HandlingCharge, VAS)
"""
from typing import Optional, List
from uuid import UUID
from datetime import datetime, date, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy import select, func, desc, and_, or_, case
from sqlalchemy.sql.functions import coalesce
from sqlalchemy.orm import selectinload

from app.api.deps import DB, get_current_user
from app.models.user import User
from app.models.order import Order, OrderItem
from app.models.channel import SalesChannel
from app.models.accounting import ChartOfAccount, JournalEntry, JournalEntryLine, CostCenter
from app.models.region import Region
from app.models.warehouse import Warehouse
from app.models.hr import Employee, Payslip, Payroll, Department
from app.models.warehouse_billing import (
    BillingInvoice, StorageCharge, HandlingCharge, ValueAddedServiceCharge
)
from app.core.module_decorators import require_module

router = APIRouter()


# ==================== Helper: Map SalesChannel to Order.source values ====================
def _channel_to_sources(channel) -> list[str]:
    """Map a SalesChannel record to matching Order.source values.

    Order.source uses: WEBSITE, MOBILE_APP, STORE, PHONE, DEALER, AMAZON, FLIPKART, OTHER
    SalesChannel.channel_type uses: D2C, D2C_WEBSITE, D2C_APP, MARKETPLACE, AMAZON, FLIPKART, etc.
    """
    ct = (channel.channel_type or "").upper()
    code = (channel.code or "").upper()

    # Direct marketplace matches
    for mp in ("AMAZON", "FLIPKART", "MYNTRA", "MEESHO", "AJIO", "NYKAA", "TATACLIQ", "JIOMART"):
        if mp in ct or mp in code:
            return [mp]

    # D2C channels
    if ct in ("D2C", "D2C_WEBSITE"):
        return ["WEBSITE", "D2C"]
    if ct == "D2C_APP":
        return ["MOBILE_APP"]

    # B2B / Dealer channels
    if ct in ("B2B", "DEALER", "DEALER_PORTAL", "DISTRIBUTOR", "MODERN_TRADE", "CORPORATE", "GOVERNMENT"):
        return ["DEALER"]

    # Offline / Retail
    if ct in ("OFFLINE", "RETAIL_STORE", "FRANCHISE"):
        return ["STORE"]

    # Quick commerce
    if ct == "QUICK_COMMERCE":
        return ["QUICK_COMMERCE"]

    # Fallback: try to match channel_type directly as a source
    return [ct] if ct else ["OTHER"]


# ==================== Helper: Get warehouse IDs for geo filter ====================
async def _get_warehouse_ids_for_geo(
    db,
    region_id: Optional[UUID] = None,
    cluster_id: Optional[UUID] = None,
    warehouse_id: Optional[UUID] = None,
) -> Optional[List[UUID]]:
    """Resolve geographic filter to a list of warehouse IDs.

    Returns None if no geo filter is applied (means: don't filter by warehouse).
    Returns a list of warehouse UUIDs when a filter is active.
    """
    if warehouse_id:
        return [warehouse_id]

    if cluster_id:
        # Cluster = a region of type STATE/CITY; get all warehouses under it
        wh_query = select(Warehouse.id).where(
            and_(Warehouse.region_id == cluster_id, Warehouse.is_active == True)
        )
        result = await db.execute(wh_query)
        return [row[0] for row in result.all()]

    if region_id:
        # Region = ZONE; get all child regions (clusters), then warehouses
        children_query = select(Region.id).where(Region.parent_id == region_id)
        children_result = await db.execute(children_query)
        cluster_ids = [row[0] for row in children_result.all()]
        # Include warehouses directly under the region + under its clusters
        all_region_ids = [region_id] + cluster_ids
        wh_query = select(Warehouse.id).where(
            and_(Warehouse.region_id.in_(all_region_ids), Warehouse.is_active == True)
        )
        result = await db.execute(wh_query)
        return [row[0] for row in result.all()]

    return None


# ==================== Helper: Manpower cost computation ====================
async def _compute_manpower_cost(
    db, warehouse_ids: List[UUID], start_date: date, end_date: date
) -> dict:
    """Compute manpower cost for warehouse(s) in a date range.

    Flow: Payslip → Employee.cost_center_id → CostCenter.warehouse_id → match
    """
    # Get cost center IDs linked to these warehouses
    cc_query = select(CostCenter.id).where(
        and_(CostCenter.warehouse_id.in_(warehouse_ids), CostCenter.is_active == True)
    )
    cc_result = await db.execute(cc_query)
    cc_ids = [row[0] for row in cc_result.all()]

    if not cc_ids:
        return {
            "total_manpower_cost": 0,
            "headcount": 0,
            "avg_monthly_ctc": 0,
            "by_department": [],
        }

    # Get employees in these cost centers
    emp_in_cc = select(Employee.id, Employee.department_id).where(
        and_(
            Employee.cost_center_id.in_(cc_ids),
            Employee.status == "ACTIVE",
        )
    ).subquery()

    # Sum payslip costs for these employees in the period
    # CTC = gross_earnings + employer_pf + employer_esic
    cost_query = select(
        func.coalesce(
            func.sum(Payslip.gross_earnings + Payslip.employer_pf + Payslip.employer_esic), 0
        ).label("total_cost"),
        func.count(func.distinct(Payslip.employee_id)).label("headcount"),
    ).select_from(Payslip).join(
        Payroll, Payslip.payroll_id == Payroll.id
    ).where(
        and_(
            Payslip.employee_id.in_(select(emp_in_cc.c.id)),
            Payroll.status.in_(["PROCESSED", "APPROVED", "PAID"]),
            Payroll.payroll_month >= start_date,
            Payroll.payroll_month <= end_date,
        )
    )
    cost_result = await db.execute(cost_query)
    cost_data = cost_result.one()

    total_cost = float(cost_data.total_cost or 0)
    headcount = int(cost_data.headcount or 0)
    avg_ctc = round(total_cost / headcount, 2) if headcount > 0 else 0

    # Breakdown by department
    dept_query = select(
        Department.name.label("department"),
        func.count(func.distinct(Payslip.employee_id)).label("headcount"),
        func.coalesce(
            func.sum(Payslip.gross_earnings + Payslip.employer_pf + Payslip.employer_esic), 0
        ).label("cost"),
    ).select_from(Payslip).join(
        Employee, Payslip.employee_id == Employee.id
    ).join(
        Department, Employee.department_id == Department.id
    ).join(
        Payroll, Payslip.payroll_id == Payroll.id
    ).where(
        and_(
            Employee.cost_center_id.in_(cc_ids),
            Payroll.status.in_(["PROCESSED", "APPROVED", "PAID"]),
            Payroll.payroll_month >= start_date,
            Payroll.payroll_month <= end_date,
        )
    ).group_by(Department.name)

    dept_result = await db.execute(dept_query)
    by_department = [
        {
            "department": row.department,
            "headcount": row.headcount,
            "cost": round(float(row.cost), 2),
        }
        for row in dept_result.all()
    ]

    return {
        "total_manpower_cost": round(total_cost, 2),
        "headcount": headcount,
        "avg_monthly_ctc": avg_ctc,
        "by_department": by_department,
    }


# ==================== Helper: Warehouse logistics cost ====================
async def _compute_warehouse_costs(
    db, warehouse_ids: List[UUID], start_date: date, end_date: date
) -> dict:
    """Compute warehouse operations costs from billing models."""
    # Storage charges
    storage_query = select(
        func.coalesce(func.sum(StorageCharge.amount), 0)
    ).where(
        and_(
            StorageCharge.warehouse_id.in_(warehouse_ids),
            StorageCharge.charge_date >= start_date,
            StorageCharge.charge_date <= end_date,
        )
    )
    storage_cost = float(await db.scalar(storage_query) or 0)

    # Handling charges
    handling_query = select(
        func.coalesce(func.sum(HandlingCharge.amount), 0)
    ).where(
        and_(
            HandlingCharge.warehouse_id.in_(warehouse_ids),
            HandlingCharge.charge_date >= start_date,
            HandlingCharge.charge_date <= end_date,
        )
    )
    handling_cost = float(await db.scalar(handling_query) or 0)

    # VAS charges
    vas_query = select(
        func.coalesce(func.sum(ValueAddedServiceCharge.amount), 0)
    ).where(
        and_(
            ValueAddedServiceCharge.warehouse_id.in_(warehouse_ids),
            ValueAddedServiceCharge.charge_date >= start_date,
            ValueAddedServiceCharge.charge_date <= end_date,
        )
    )
    vas_cost = float(await db.scalar(vas_query) or 0)

    total = storage_cost + handling_cost + vas_cost

    return {
        "storage_cost": round(storage_cost, 2),
        "handling_cost": round(handling_cost, 2),
        "vas_cost": round(vas_cost, 2),
        "total_warehouse_cost": round(total, 2),
    }


# ==================== Geo Hierarchy Endpoint ====================
@router.get("/geo-hierarchy")
@require_module("sales_distribution")
async def get_geo_hierarchy(
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """
    Get geographic hierarchy for drill-down filters.

    Returns: Region (ZONE) → Cluster (STATE/CITY) → Warehouse
    """
    # Get all ZONE-level regions
    zones_query = select(Region).where(
        and_(Region.type == "ZONE", Region.is_active == True)
    ).order_by(Region.name)
    zones_result = await db.execute(zones_query)
    zones = zones_result.scalars().all()

    regions = []
    for zone in zones:
        # Get clusters (children of this zone: STATE/CITY)
        clusters_query = select(Region).where(
            and_(Region.parent_id == zone.id, Region.is_active == True)
        ).order_by(Region.name)
        clusters_result = await db.execute(clusters_query)
        clusters = clusters_result.scalars().all()

        cluster_data = []
        for cluster in clusters:
            # Get warehouses in this cluster region
            wh_query = select(Warehouse).where(
                and_(Warehouse.region_id == cluster.id, Warehouse.is_active == True)
            ).order_by(Warehouse.name)
            wh_result = await db.execute(wh_query)
            warehouses = wh_result.scalars().all()

            cluster_data.append({
                "id": str(cluster.id),
                "name": cluster.name,
                "code": cluster.code,
                "type": cluster.type,
                "warehouses": [
                    {
                        "id": str(wh.id),
                        "name": wh.name,
                        "code": wh.code,
                    }
                    for wh in warehouses
                ],
            })

        # Also get warehouses directly under the zone (not under a cluster)
        direct_wh_query = select(Warehouse).where(
            and_(Warehouse.region_id == zone.id, Warehouse.is_active == True)
        ).order_by(Warehouse.name)
        direct_wh_result = await db.execute(direct_wh_query)
        direct_warehouses = direct_wh_result.scalars().all()

        regions.append({
            "id": str(zone.id),
            "name": zone.name,
            "code": zone.code,
            "type": zone.type,
            "clusters": cluster_data,
            "warehouses": [
                {
                    "id": str(wh.id),
                    "name": wh.name,
                    "code": wh.code,
                }
                for wh in direct_warehouses
            ],
        })

    return {"regions": regions}


# ==================== Channel P&L Report (Enhanced) ====================
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
    # Geographic drill-down
    region_id: Optional[UUID] = None,
    cluster_id: Optional[UUID] = None,
    warehouse_id: Optional[UUID] = None,
    # Cost toggles
    include_manpower: bool = Query(False, description="Include manpower costs from HRMS"),
    include_warehouse_costs: bool = Query(False, description="Include warehouse logistics costs"),
):
    """
    Get Profit & Loss report by channel with geographic drill-down.

    Supports filtering by:
    - channel_id: Specific sales channel
    - region_id: Zone-level geographic region
    - cluster_id: State/city cluster within a region
    - warehouse_id: Specific warehouse
    - include_manpower: Add manpower cost breakdown from payroll
    - include_warehouse_costs: Add warehouse storage/handling/VAS costs
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

    # Resolve geo filter to warehouse IDs
    geo_warehouse_ids = await _get_warehouse_ids_for_geo(
        db, region_id=region_id, cluster_id=cluster_id, warehouse_id=warehouse_id
    )

    # Build geo filter label
    geo_filter = None
    if warehouse_id:
        wh = await db.get(Warehouse, warehouse_id)
        geo_filter = {"warehouse": wh.name if wh else str(warehouse_id)}
    if cluster_id:
        cl = await db.get(Region, cluster_id)
        geo_filter = geo_filter or {}
        geo_filter["cluster"] = cl.name if cl else str(cluster_id)
    if region_id:
        rg = await db.get(Region, region_id)
        geo_filter = geo_filter or {}
        geo_filter["region"] = rg.name if rg else str(region_id)

    # Get channels
    channels_query = select(SalesChannel).where(SalesChannel.status == "ACTIVE")
    if channel_id:
        channels_query = channels_query.where(SalesChannel.id == channel_id)

    channels_result = await db.execute(channels_query)
    channels = channels_result.scalars().all()

    pnl_data = []

    for channel in channels:
        # Map channel to Order.source values
        source_values = _channel_to_sources(channel)

        # Base order filter conditions — match by Order.source (always populated)
        # instead of Order.channel_id (often NULL)
        base_conditions = [
            Order.source.in_(source_values),
            Order.status.notin_(["CANCELLED", "DRAFT"]),
            Order.created_at >= start_date,
            Order.created_at <= end_date,
        ]

        # Add warehouse filter if geo drill-down active
        if geo_warehouse_ids is not None:
            if not geo_warehouse_ids:
                # No warehouses match the geo filter — skip with zeros
                pnl_data.append(_empty_channel_pnl(channel, start_date, end_date, geo_filter))
                continue
            base_conditions.append(Order.warehouse_id.in_(geo_warehouse_ids))

        # Revenue (Sales)
        revenue_query = select(
            func.coalesce(func.sum(Order.total_amount), 0).label("gross_revenue"),
            func.coalesce(func.sum(Order.discount_amount), 0).label("discounts"),
            func.coalesce(func.sum(Order.tax_amount), 0).label("taxes_collected"),
            func.count(Order.id).label("order_count"),
        ).where(and_(*base_conditions))
        revenue_result = await db.execute(revenue_query)
        revenue_data = revenue_result.one()

        gross_revenue = float(revenue_data.gross_revenue or 0)
        discounts = float(revenue_data.discounts or 0)
        net_revenue = gross_revenue - discounts

        # COGS — use COALESCE(unit_cost, unit_price * 0.65) as fallback
        cogs_query = select(
            func.coalesce(
                func.sum(
                    OrderItem.quantity * coalesce(OrderItem.unit_cost, OrderItem.unit_price * Decimal("0.65"))
                ),
                0,
            )
        ).select_from(OrderItem).join(
            Order, OrderItem.order_id == Order.id
        ).where(and_(*base_conditions))
        cogs = float(await db.scalar(cogs_query) or 0)

        gross_profit = net_revenue - cogs
        gross_margin = (gross_profit / net_revenue * 100) if net_revenue > 0 else 0

        # Channel commission (fixed field name: commission_percentage)
        commission_rate = float(channel.commission_percentage or 0) / 100
        channel_fees = net_revenue * commission_rate

        # Shipping costs
        shipping_query = select(
            func.coalesce(func.sum(Order.shipping_amount), 0)
        ).where(and_(*base_conditions))
        shipping_costs = float(await db.scalar(shipping_query) or 0)

        # Payment processing fees (estimated at 2%)
        payment_fees = net_revenue * 0.02

        # Warehouse costs (if requested and geo filter provides warehouse IDs)
        warehouse_costs = {"storage_cost": 0, "handling_cost": 0, "vas_cost": 0, "total_warehouse_cost": 0}
        if include_warehouse_costs and geo_warehouse_ids:
            warehouse_costs = await _compute_warehouse_costs(db, geo_warehouse_ids, start_date, end_date)

        # Manpower costs (if requested and geo filter provides warehouse IDs)
        manpower_detail = None
        manpower_cost = 0
        if include_manpower and geo_warehouse_ids:
            manpower_detail = await _compute_manpower_cost(db, geo_warehouse_ids, start_date, end_date)
            manpower_cost = manpower_detail["total_manpower_cost"]

        total_opex = (
            channel_fees + shipping_costs + payment_fees
            + warehouse_costs["total_warehouse_cost"]
            + manpower_cost
        )

        ebitda = gross_profit - total_opex
        ebitda_margin = (ebitda / net_revenue * 100) if net_revenue > 0 else 0

        channel_pnl = {
            "channel_id": str(channel.id),
            "channel_name": channel.name,
            "channel_type": channel.channel_type,
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
            "geo_filter": geo_filter,
            "revenue": {
                "gross_revenue": round(gross_revenue, 2),
                "discounts": round(discounts, 2),
                "net_revenue": round(net_revenue, 2),
                "order_count": revenue_data.order_count,
            },
            "cogs": {
                "product_cost": round(cogs, 2),
                "gross_profit": round(gross_profit, 2),
                "gross_margin_pct": round(gross_margin, 2),
            },
            "opex": {
                "channel_commission": round(channel_fees, 2),
                "shipping_cost": round(shipping_costs, 2),
                "payment_processing": round(payment_fees, 2),
                "warehouse_storage": round(warehouse_costs["storage_cost"], 2),
                "warehouse_handling": round(warehouse_costs["handling_cost"], 2),
                "warehouse_vas": round(warehouse_costs["vas_cost"], 2),
                "manpower_cost": round(manpower_cost, 2),
                "total_opex": round(total_opex, 2),
            },
            "ebitda": round(ebitda, 2),
            "ebitda_margin_pct": round(ebitda_margin, 2),
        }

        if manpower_detail:
            channel_pnl["manpower_detail"] = manpower_detail

        pnl_data.append(channel_pnl)

    # Totals
    total_revenue = sum(p["revenue"]["net_revenue"] for p in pnl_data)
    total_cogs = sum(p["cogs"]["product_cost"] for p in pnl_data)
    total_gross_profit = sum(p["cogs"]["gross_profit"] for p in pnl_data)
    total_opex = sum(p["opex"]["total_opex"] for p in pnl_data)
    total_ebitda = sum(p["ebitda"] for p in pnl_data)

    return {
        "report_type": "Channel P&L",
        "period": {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        },
        "geo_filter": geo_filter,
        "channels": pnl_data,
        "totals": {
            "net_revenue": round(total_revenue, 2),
            "cost_of_goods_sold": round(total_cogs, 2),
            "gross_profit": round(total_gross_profit, 2),
            "gross_margin_pct": round((total_gross_profit / total_revenue * 100) if total_revenue > 0 else 0, 2),
            "total_opex": round(total_opex, 2),
            "ebitda": round(total_ebitda, 2),
            "ebitda_margin_pct": round((total_ebitda / total_revenue * 100) if total_revenue > 0 else 0, 2),
        },
    }


def _empty_channel_pnl(channel, start_date, end_date, geo_filter):
    """Return a zero-valued P&L entry for a channel with no matching warehouse data."""
    return {
        "channel_id": str(channel.id),
        "channel_name": channel.name,
        "channel_type": channel.channel_type,
        "period": {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        },
        "geo_filter": geo_filter,
        "revenue": {"gross_revenue": 0, "discounts": 0, "net_revenue": 0, "order_count": 0},
        "cogs": {"product_cost": 0, "gross_profit": 0, "gross_margin_pct": 0},
        "opex": {
            "channel_commission": 0, "shipping_cost": 0, "payment_processing": 0,
            "warehouse_storage": 0, "warehouse_handling": 0, "warehouse_vas": 0,
            "manpower_cost": 0, "total_opex": 0,
        },
        "ebitda": 0,
        "ebitda_margin_pct": 0,
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
        source_values = _channel_to_sources(channel)

        # Accounts Receivable (unpaid orders)
        ar_query = select(
            func.coalesce(func.sum(Order.total_amount - Order.amount_paid), 0)
        ).where(
            and_(
                Order.source.in_(source_values),
                Order.status.notin_(["CANCELLED", "DRAFT"]),
                Order.payment_status != "PAID",
                Order.created_at <= as_of_date
            )
        )
        accounts_receivable = float(await db.scalar(ar_query) or 0)

        inventory = 0
        prepaid = 0
        total_current_assets = accounts_receivable + inventory + prepaid
        fixed_assets = 0
        total_assets = total_current_assets + fixed_assets

        # Current Liabilities
        commission_rate = float(channel.commission_percentage or 0) / 100

        pending_comm_query = select(
            func.coalesce(func.sum(Order.total_amount), 0)
        ).where(
            and_(
                Order.source.in_(source_values),
                Order.status == "DELIVERED",
                Order.created_at >= as_of_date - timedelta(days=30),
                Order.created_at <= as_of_date
            )
        )
        recent_sales = float(await db.scalar(pending_comm_query) or 0)
        accounts_payable = recent_sales * commission_rate

        deferred_revenue_query = select(
            func.coalesce(func.sum(Order.amount_paid), 0)
        ).where(
            and_(
                Order.source.in_(source_values),
                Order.status.in_(["PENDING_PAYMENT", "CONFIRMED", "ALLOCATED"]),
                Order.payment_status == "PAID"
            )
        )
        deferred_revenue = float(await db.scalar(deferred_revenue_query) or 0)

        total_current_liabilities = accounts_payable + deferred_revenue
        long_term_liabilities = 0
        total_liabilities = total_current_liabilities + long_term_liabilities

        # Equity
        retained_earnings_query = select(
            func.coalesce(func.sum(Order.total_amount - Order.discount_amount), 0)
        ).where(
            and_(
                Order.source.in_(source_values),
                Order.status == "DELIVERED",
                Order.created_at <= as_of_date
            )
        )
        cumulative_revenue = float(await db.scalar(retained_earnings_query) or 0)
        retained_earnings = cumulative_revenue * 0.10
        total_equity = retained_earnings

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

    Metrics: revenue, orders, margin, aov
    """
    if not start_date:
        start_date = date.today() - timedelta(days=30)
    if not end_date:
        end_date = date.today()

    channels_query = select(SalesChannel).where(SalesChannel.status == "ACTIVE")
    channels_result = await db.execute(channels_query)
    channels = channels_result.scalars().all()

    comparison = []

    for channel in channels:
        source_values = _channel_to_sources(channel)

        metrics_query = select(
            func.count(Order.id).label("orders"),
            func.coalesce(func.sum(Order.total_amount), 0).label("revenue"),
            func.coalesce(func.avg(Order.total_amount), 0).label("aov")
        ).where(
            and_(
                Order.source.in_(source_values),
                Order.status.notin_(["CANCELLED", "DRAFT"]),
                Order.created_at >= start_date,
                Order.created_at <= end_date
            )
        )
        metrics_result = await db.execute(metrics_query)
        metrics = metrics_result.one()

        cogs_query = select(
            func.coalesce(
                func.sum(
                    OrderItem.quantity * coalesce(OrderItem.unit_cost, OrderItem.unit_price * Decimal("0.65"))
                ),
                0,
            )
        ).select_from(OrderItem).join(
            Order, OrderItem.order_id == Order.id
        ).where(
            and_(
                Order.source.in_(source_values),
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

    sort_key = {"revenue": "revenue", "orders": "orders", "margin": "margin_percent", "aov": "aov"}
    comparison.sort(key=lambda x: x[sort_key.get(metric, "revenue")], reverse=True)

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

    if group_by == "day":
        date_expr = func.date(Order.created_at)
    elif group_by == "week":
        date_expr = func.date_trunc('week', Order.created_at)
    else:
        date_expr = func.date_trunc('month', Order.created_at)

    # Get channels and query per-channel using Order.source mapping
    channels_query = select(SalesChannel).where(SalesChannel.status == "ACTIVE")
    if channel_id:
        channels_query = channels_query.where(SalesChannel.id == channel_id)
    channels_result = await db.execute(channels_query)
    all_channels = channels_result.scalars().all()

    channels_data = {}
    for channel in all_channels:
        source_values = _channel_to_sources(channel)
        conditions = [
            Order.source.in_(source_values),
            Order.status.notin_(["CANCELLED", "DRAFT"]),
            Order.created_at >= start_date,
        ]

        query = select(
            date_expr.label("period"),
            func.count(Order.id).label("orders"),
            func.coalesce(func.sum(Order.total_amount), 0).label("revenue")
        ).where(
            and_(*conditions)
        ).group_by(date_expr).order_by(date_expr)

        result = await db.execute(query)
        data = result.all()

        if data:
            channels_data[channel.name] = {
                "labels": [str(row.period)[:10] for row in data],
                "orders": [row.orders for row in data],
                "revenue": [float(row.revenue or 0) for row in data],
            }

    return {
        "period_days": days,
        "group_by": group_by,
        "channels": channels_data,
    }
