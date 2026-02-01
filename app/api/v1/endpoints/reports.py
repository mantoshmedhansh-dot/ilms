"""Reports API endpoints for frontend dashboard."""
from typing import Optional, List
from datetime import date, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, and_, case, or_
from sqlalchemy.orm import aliased

from app.api.deps import DB, get_current_user
from app.models.user import User
from app.models.order import Order, OrderItem
from app.models.product_cost import ProductCost
from app.models.accounting import ChartOfAccount
from app.core.module_decorators import require_module

router = APIRouter()


# ==================== Helper Functions ====================

def parse_period(period: str) -> tuple[date, date]:
    """Parse period string to start/end dates."""
    today = date.today()

    if period == "this_month":
        start = today.replace(day=1)
        end = today
    elif period == "last_month":
        first_of_this_month = today.replace(day=1)
        end = first_of_this_month - timedelta(days=1)
        start = end.replace(day=1)
    elif period == "this_quarter":
        quarter = (today.month - 1) // 3
        start = date(today.year, quarter * 3 + 1, 1)
        end = today
    elif period == "last_quarter":
        quarter = (today.month - 1) // 3
        if quarter == 0:
            start = date(today.year - 1, 10, 1)
            end = date(today.year - 1, 12, 31)
        else:
            start = date(today.year, (quarter - 1) * 3 + 1, 1)
            end_month = quarter * 3
            if end_month == 3:
                end = date(today.year, 3, 31)
            elif end_month == 6:
                end = date(today.year, 6, 30)
            else:
                end = date(today.year, 9, 30)
    elif period == "this_year":
        start = date(today.year, 1, 1)
        end = today
    elif period == "last_year":
        start = date(today.year - 1, 1, 1)
        end = date(today.year - 1, 12, 31)
    else:
        # Default to this month
        start = today.replace(day=1)
        end = today

    return start, end


# ==================== Balance Sheet ====================

# Account sub-types that are considered "current"
CURRENT_ASSET_SUBTYPES = {"CASH", "BANK", "ACCOUNTS_RECEIVABLE", "INVENTORY", "PREPAID_EXPENSE", "CURRENT_ASSET"}
CURRENT_LIABILITY_SUBTYPES = {"ACCOUNTS_PAYABLE", "TAX_PAYABLE", "ACCRUED_EXPENSE", "SHORT_TERM_DEBT", "CURRENT_LIABILITY"}


def build_section_items(accounts: list, previous_balances: dict) -> List[dict]:
    """Build line items for a balance sheet section."""
    items = []
    for acc in accounts:
        current = float(acc.current_balance or 0)
        previous = previous_balances.get(str(acc.id), 0.0)
        variance = current - previous
        variance_pct = (variance / previous * 100) if previous != 0 else 0

        items.append({
            "account_code": acc.account_code,
            "account_name": acc.account_name,
            "current_balance": current,
            "previous_balance": previous,
            "variance": variance,
            "variance_percentage": round(variance_pct, 2),
            "is_group": acc.is_group,
            "indent_level": acc.level - 1 if acc.level else 0
        })
    return items


@router.get("/balance-sheet")
@require_module("sales_distribution")
async def get_balance_sheet(
    db: DB,
    current_user: User = Depends(get_current_user),
    as_of_date: str = Query("today"),
    compare: bool = Query(True),
):
    """
    Get Balance Sheet report with line items and comparison.

    Returns assets, liabilities, equity with individual account breakdowns.
    """
    today = date.today()

    # For now, we use current balances from chart_of_accounts
    # In a full implementation, we'd query GL entries up to as_of_date

    # Get all non-group asset accounts
    asset_query = select(ChartOfAccount).where(
        and_(
            ChartOfAccount.account_type == "ASSET",
            ChartOfAccount.is_group == False,
            ChartOfAccount.is_active == True,
        )
    ).order_by(ChartOfAccount.account_code)

    asset_result = await db.execute(asset_query)
    all_assets = asset_result.scalars().all()

    # Split into current and non-current
    current_assets = [a for a in all_assets if a.account_sub_type in CURRENT_ASSET_SUBTYPES or a.account_sub_type is None]
    non_current_assets = [a for a in all_assets if a.account_sub_type and a.account_sub_type not in CURRENT_ASSET_SUBTYPES]

    # Get all non-group liability accounts
    liability_query = select(ChartOfAccount).where(
        and_(
            ChartOfAccount.account_type == "LIABILITY",
            ChartOfAccount.is_group == False,
            ChartOfAccount.is_active == True,
        )
    ).order_by(ChartOfAccount.account_code)

    liability_result = await db.execute(liability_query)
    all_liabilities = liability_result.scalars().all()

    # Split into current and non-current
    current_liabilities = [l for l in all_liabilities if l.account_sub_type in CURRENT_LIABILITY_SUBTYPES or l.account_sub_type is None]
    non_current_liabilities = [l for l in all_liabilities if l.account_sub_type and l.account_sub_type not in CURRENT_LIABILITY_SUBTYPES]

    # Get all equity accounts
    equity_query = select(ChartOfAccount).where(
        and_(
            ChartOfAccount.account_type == "EQUITY",
            ChartOfAccount.is_group == False,
            ChartOfAccount.is_active == True,
        )
    ).order_by(ChartOfAccount.account_code)

    equity_result = await db.execute(equity_query)
    equity_accounts = equity_result.scalars().all()

    # For comparison, use opening_balance as "previous" (simplified)
    # In a full implementation, we'd query GL at a previous date
    previous_balances = {}
    for acc in all_assets + all_liabilities + equity_accounts:
        previous_balances[str(acc.id)] = float(acc.opening_balance or 0)

    # Build sections
    current_assets_items = build_section_items(current_assets, previous_balances)
    non_current_assets_items = build_section_items(non_current_assets, previous_balances)
    current_liabilities_items = build_section_items(current_liabilities, previous_balances)
    non_current_liabilities_items = build_section_items(non_current_liabilities, previous_balances)
    equity_items = build_section_items(equity_accounts, previous_balances)

    # Calculate totals
    total_current_assets = sum(float(a.current_balance or 0) for a in current_assets)
    total_non_current_assets = sum(float(a.current_balance or 0) for a in non_current_assets)
    total_assets = total_current_assets + total_non_current_assets

    total_current_liabilities = sum(float(l.current_balance or 0) for l in current_liabilities)
    total_non_current_liabilities = sum(float(l.current_balance or 0) for l in non_current_liabilities)
    total_liabilities = total_current_liabilities + total_non_current_liabilities

    total_equity = sum(float(e.current_balance or 0) for e in equity_accounts)

    # Previous totals
    prev_current_assets = sum(previous_balances.get(str(a.id), 0) for a in current_assets)
    prev_non_current_assets = sum(previous_balances.get(str(a.id), 0) for a in non_current_assets)
    prev_total_assets = prev_current_assets + prev_non_current_assets

    prev_current_liabilities = sum(previous_balances.get(str(l.id), 0) for l in current_liabilities)
    prev_non_current_liabilities = sum(previous_balances.get(str(l.id), 0) for l in non_current_liabilities)
    prev_total_liabilities = prev_current_liabilities + prev_non_current_liabilities

    prev_total_equity = sum(previous_balances.get(str(e.id), 0) for e in equity_accounts)

    total_liabilities_and_equity = total_liabilities + total_equity
    prev_total_liabilities_and_equity = prev_total_liabilities + prev_total_equity

    # Ratios
    working_capital = total_current_assets - total_current_liabilities
    current_ratio = total_current_assets / total_current_liabilities if total_current_liabilities > 0 else 0
    debt_to_equity = total_liabilities / total_equity if total_equity > 0 else 0

    difference = total_assets - total_liabilities_and_equity
    is_balanced = abs(difference) < 0.01

    return {
        "as_of_date": today.isoformat(),
        "previous_date": (today - timedelta(days=30)).isoformat(),
        "assets": {
            "current_assets": {
                "title": "Current Assets",
                "items": current_assets_items,
                "total": total_current_assets,
                "previous_total": prev_current_assets,
            },
            "non_current_assets": {
                "title": "Non-Current Assets",
                "items": non_current_assets_items,
                "total": total_non_current_assets,
                "previous_total": prev_non_current_assets,
            },
            "total": total_assets,
            "previous_total": prev_total_assets,
        },
        "liabilities": {
            "current_liabilities": {
                "title": "Current Liabilities",
                "items": current_liabilities_items,
                "total": total_current_liabilities,
                "previous_total": prev_current_liabilities,
            },
            "non_current_liabilities": {
                "title": "Non-Current Liabilities",
                "items": non_current_liabilities_items,
                "total": total_non_current_liabilities,
                "previous_total": prev_non_current_liabilities,
            },
            "total": total_liabilities,
            "previous_total": prev_total_liabilities,
        },
        "equity": {
            "title": "Shareholders Equity",
            "items": equity_items,
            "total": total_equity,
            "previous_total": prev_total_equity,
        },
        "total_liabilities_and_equity": total_liabilities_and_equity,
        "previous_total_liabilities_and_equity": prev_total_liabilities_and_equity,
        "is_balanced": is_balanced,
        "difference": difference,
        "current_ratio": round(current_ratio, 2),
        "debt_to_equity": round(debt_to_equity, 2),
        "working_capital": working_capital,
    }


# ==================== Trial Balance ====================

@router.get("/trial-balance")
@require_module("sales_distribution")
async def get_trial_balance(
    db: DB,
    current_user: User = Depends(get_current_user),
    period: str = Query("this_month"),
):
    """
    Get Trial Balance report with account-wise debit/credit balances.

    Returns all accounts with opening, period movement, and closing balances.
    """
    today = date.today()
    start_date, end_date = parse_period(period)

    # Get all non-group accounts
    accounts_query = select(ChartOfAccount).where(
        and_(
            ChartOfAccount.is_group == False,
            ChartOfAccount.is_active == True,
        )
    ).order_by(ChartOfAccount.account_type, ChartOfAccount.account_code)

    result = await db.execute(accounts_query)
    accounts = result.scalars().all()

    account_list = []
    total_debits = Decimal("0")
    total_credits = Decimal("0")

    for acc in accounts:
        current_balance = Decimal(str(acc.current_balance or 0))
        opening_balance = Decimal(str(acc.opening_balance or 0))

        # Determine debit/credit based on account type and balance sign
        # Assets & Expenses: positive = debit, negative = credit
        # Liabilities, Equity, Revenue: positive = credit, negative = debit
        is_debit_account = acc.account_type in ("ASSET", "EXPENSE")

        if is_debit_account:
            debit_balance = max(current_balance, Decimal("0"))
            credit_balance = max(-current_balance, Decimal("0"))
            opening_debit = max(opening_balance, Decimal("0"))
            opening_credit = max(-opening_balance, Decimal("0"))
        else:
            credit_balance = max(current_balance, Decimal("0"))
            debit_balance = max(-current_balance, Decimal("0"))
            opening_credit = max(opening_balance, Decimal("0"))
            opening_debit = max(-opening_balance, Decimal("0"))

        # Period movement is the difference
        period_debit = max(debit_balance - opening_debit, Decimal("0"))
        period_credit = max(credit_balance - opening_credit, Decimal("0"))

        account_list.append({
            "account_code": acc.account_code,
            "account_name": acc.account_name,
            "account_type": acc.account_type,
            "debit_balance": float(debit_balance),
            "credit_balance": float(credit_balance),
            "opening_debit": float(opening_debit),
            "opening_credit": float(opening_credit),
            "period_debit": float(period_debit),
            "period_credit": float(period_credit),
        })

        total_debits += debit_balance
        total_credits += credit_balance

    difference = total_debits - total_credits

    return {
        "as_of_date": today.isoformat(),
        "period_start": start_date.isoformat(),
        "period_end": end_date.isoformat(),
        "accounts": account_list,
        "total_debits": float(total_debits),
        "total_credits": float(total_credits),
        "is_balanced": abs(difference) < Decimal("0.01"),
        "difference": float(difference),
    }


# ==================== Profit & Loss ====================

@router.get("/profit-loss")
@require_module("sales_distribution")
async def get_profit_loss_report(
    db: DB,
    current_user: User = Depends(get_current_user),
    period: str = Query("this_month"),
    compare: bool = Query(True),
):
    """
    Get Profit & Loss statement.

    Returns revenue, COGS, operating expenses, and net income.
    Matches frontend ProfitLossData interface exactly.
    """
    today = date.today()
    start_date, end_date = parse_period(period)

    # Get previous period for comparison
    period_length = (end_date - start_date).days + 1
    prev_end = start_date - timedelta(days=1)
    prev_start = prev_end - timedelta(days=period_length - 1)

    # Period names for display
    period_name = f"{start_date.strftime('%b %d')} - {end_date.strftime('%b %d, %Y')}"
    previous_period_name = f"{prev_start.strftime('%b %d')} - {prev_end.strftime('%b %d, %Y')}"

    def build_line_item(acc, current_amount: Decimal, previous_amount: Decimal = Decimal("0")) -> dict:
        """Build a line item matching ProfitLossLineItem interface."""
        variance = float(current_amount - previous_amount)
        variance_pct = (variance / float(previous_amount) * 100) if previous_amount != 0 else 0.0
        return {
            "account_code": acc.account_code,
            "account_name": acc.account_name,
            "current_period": float(current_amount),
            "previous_period": float(previous_amount),
            "variance": variance,
            "variance_percentage": round(variance_pct, 2),
            "is_group": False,
            "indent_level": 0,
        }

    # Get revenue accounts (4xxx)
    revenue_query = select(ChartOfAccount).where(
        and_(
            ChartOfAccount.account_type == "REVENUE",
            ChartOfAccount.is_group == False,
            ChartOfAccount.is_active == True,
        )
    ).order_by(ChartOfAccount.account_code)

    revenue_result = await db.execute(revenue_query)
    revenue_accounts = revenue_result.scalars().all()

    revenue_items = []
    total_revenue = Decimal("0")
    prev_total_revenue = Decimal("0")

    for acc in revenue_accounts:
        amount = Decimal(str(acc.current_balance or 0))
        prev_amount = Decimal(str(acc.opening_balance or 0))
        total_revenue += amount
        prev_total_revenue += prev_amount
        if amount != 0 or prev_amount != 0:
            revenue_items.append(build_line_item(acc, amount, prev_amount))

    # Get COGS accounts (5xxx)
    cogs_query = select(ChartOfAccount).where(
        and_(
            ChartOfAccount.account_type == "EXPENSE",
            ChartOfAccount.account_code.like("5%"),
            ChartOfAccount.is_group == False,
            ChartOfAccount.is_active == True,
        )
    ).order_by(ChartOfAccount.account_code)

    cogs_result = await db.execute(cogs_query)
    cogs_accounts = cogs_result.scalars().all()

    cogs_items = []
    total_cogs = Decimal("0")
    prev_total_cogs = Decimal("0")

    for acc in cogs_accounts:
        amount = Decimal(str(acc.current_balance or 0))
        prev_amount = Decimal(str(acc.opening_balance or 0))
        total_cogs += amount
        prev_total_cogs += prev_amount
        if amount != 0 or prev_amount != 0:
            cogs_items.append(build_line_item(acc, amount, prev_amount))

    gross_profit = total_revenue - total_cogs
    prev_gross_profit = prev_total_revenue - prev_total_cogs
    gross_margin_pct = float((gross_profit / total_revenue * 100) if total_revenue > 0 else 0)

    # Get operating expense accounts (3xxx, 6xxx, 7xxx - excluding 5xxx COGS)
    opex_query = select(ChartOfAccount).where(
        and_(
            ChartOfAccount.account_type == "EXPENSE",
            ~ChartOfAccount.account_code.like("5%"),  # Exclude COGS
            ChartOfAccount.is_group == False,
            ChartOfAccount.is_active == True,
        )
    ).order_by(ChartOfAccount.account_code)

    opex_result = await db.execute(opex_query)
    opex_accounts = opex_result.scalars().all()

    opex_items = []
    total_opex = Decimal("0")
    prev_total_opex = Decimal("0")

    for acc in opex_accounts:
        amount = Decimal(str(acc.current_balance or 0))
        prev_amount = Decimal(str(acc.opening_balance or 0))
        total_opex += amount
        prev_total_opex += prev_amount
        if amount != 0 or prev_amount != 0:
            opex_items.append(build_line_item(acc, amount, prev_amount))

    operating_income = gross_profit - total_opex
    prev_operating_income = prev_gross_profit - prev_total_opex
    operating_margin_pct = float((operating_income / total_revenue * 100) if total_revenue > 0 else 0)

    # For now, no other income/expenses or taxes
    net_profit_before_tax = operating_income
    prev_net_profit_before_tax = prev_operating_income
    tax_expense = Decimal("0")
    prev_tax_expense = Decimal("0")
    net_profit = net_profit_before_tax - tax_expense
    prev_net_profit = prev_net_profit_before_tax - prev_tax_expense
    net_margin_pct = float((net_profit / total_revenue * 100) if total_revenue > 0 else 0)

    return {
        "period_name": period_name,
        "from_date": start_date.isoformat(),
        "to_date": end_date.isoformat(),
        "previous_period_name": previous_period_name,
        "revenue": {
            "title": "Revenue",
            "items": revenue_items,
            "total": float(total_revenue),
            "previous_total": float(prev_total_revenue),
        },
        "cost_of_goods_sold": {
            "title": "Cost of Goods Sold",
            "items": cogs_items,
            "total": float(total_cogs),
            "previous_total": float(prev_total_cogs),
        },
        "gross_profit": float(gross_profit),
        "previous_gross_profit": float(prev_gross_profit),
        "operating_expenses": {
            "title": "Operating Expenses",
            "items": opex_items,
            "total": float(total_opex),
            "previous_total": float(prev_total_opex),
        },
        "operating_income": float(operating_income),
        "previous_operating_income": float(prev_operating_income),
        "other_income": {
            "title": "Other Income",
            "items": [],
            "total": 0.0,
            "previous_total": 0.0,
        },
        "other_expenses": {
            "title": "Other Expenses",
            "items": [],
            "total": 0.0,
            "previous_total": 0.0,
        },
        "net_profit_before_tax": float(net_profit_before_tax),
        "previous_net_profit_before_tax": float(prev_net_profit_before_tax),
        "tax_expense": float(tax_expense),
        "previous_tax_expense": float(prev_tax_expense),
        "net_profit": float(net_profit),
        "previous_net_profit": float(prev_net_profit),
        "gross_margin_percentage": round(gross_margin_pct, 2),
        "operating_margin_percentage": round(operating_margin_pct, 2),
        "net_margin_percentage": round(net_margin_pct, 2),
    }


# ==================== Channel Balance Sheet ====================

@router.get("/channel-balance-sheet")
@require_module("sales_distribution")
async def get_channel_balance_sheet(
    db: DB,
    current_user: User = Depends(get_current_user),
    as_of_date: str = Query("today"),
):
    """
    Get Channel-wise Balance Sheet.

    Note: For now returns overall balance sheet as channel-wise tracking
    requires GL entries with channel_id, which may not be populated.
    """
    # Reuse balance sheet logic but return in channel format
    today = date.today()

    # Get totals by account type
    asset_query = select(
        func.sum(ChartOfAccount.current_balance)
    ).where(
        and_(
            ChartOfAccount.account_type == "ASSET",
            ChartOfAccount.is_group == False,
        )
    )
    total_assets = float(await db.scalar(asset_query) or 0)

    liability_query = select(
        func.sum(ChartOfAccount.current_balance)
    ).where(
        and_(
            ChartOfAccount.account_type == "LIABILITY",
            ChartOfAccount.is_group == False,
        )
    )
    total_liabilities = float(await db.scalar(liability_query) or 0)

    equity_query = select(
        func.sum(ChartOfAccount.current_balance)
    ).where(
        and_(
            ChartOfAccount.account_type == "EQUITY",
            ChartOfAccount.is_group == False,
        )
    )
    total_equity = float(await db.scalar(equity_query) or 0)

    return {
        "as_of_date": today.isoformat(),
        "total_assets": total_assets,
        "total_liabilities": total_liabilities,
        "total_equity": total_equity,
        "total_liabilities_and_equity": total_liabilities + total_equity,
        "channels": [
            {
                "channel_id": "OVERALL",
                "channel_name": "All Channels",
                "channel_type": "CONSOLIDATED",
                "assets": total_assets,
                "liabilities": total_liabilities,
                "equity": total_equity,
            }
        ],
    }


# Map source codes to display names
SOURCE_DISPLAY_NAMES = {
    "WEBSITE": "D2C Website",
    "D2C": "D2C Website",
    "MOBILE_APP": "Mobile App",
    "STORE": "Retail Store",
    "PHONE": "Phone Orders",
    "DEALER": "Dealer/B2B",
    "AMAZON": "Amazon",
    "FLIPKART": "Flipkart",
    "OTHER": "Other Channels",
}

# Map source codes to channel types
SOURCE_CHANNEL_TYPES = {
    "WEBSITE": "D2C",
    "D2C": "D2C",
    "MOBILE_APP": "D2C",
    "STORE": "RETAIL",
    "PHONE": "D2C",
    "DEALER": "B2B",
    "AMAZON": "MARKETPLACE",
    "FLIPKART": "MARKETPLACE",
    "OTHER": "OTHER",
}

# Commission rates by channel
COMMISSION_RATES = {
    "WEBSITE": Decimal("0"),
    "D2C": Decimal("0"),
    "MOBILE_APP": Decimal("0"),
    "STORE": Decimal("0"),
    "PHONE": Decimal("0"),
    "DEALER": Decimal("0.05"),  # 5%
    "AMAZON": Decimal("0.15"),  # 15%
    "FLIPKART": Decimal("0.12"),  # 12%
    "OTHER": Decimal("0.05"),
}


def map_channel_filter_to_sources(channel_id: str) -> list[str]:
    """Map frontend channel filter to Order.source values."""
    if not channel_id or channel_id == "all":
        return []  # No filter = all sources

    channel_lower = channel_id.lower()
    if channel_lower in ["d2c", "website"]:
        return ["WEBSITE", "D2C", "MOBILE_APP", "PHONE"]
    elif channel_lower == "amazon":
        return ["AMAZON"]
    elif channel_lower == "flipkart":
        return ["FLIPKART"]
    elif channel_lower in ["b2b", "dealer"]:
        return ["DEALER"]
    elif channel_lower == "store":
        return ["STORE"]
    else:
        return [channel_id.upper()]


@router.get("/channel-pl")
@require_module("sales_distribution")
async def get_channel_pl(
    db: DB,
    current_user: User = Depends(get_current_user),
    period: str = Query("this_month"),
    channel_id: Optional[str] = None,
):
    """
    Get Channel-wise Profit & Loss report.

    Response format matches frontend ConsolidatedPL interface.
    COGS calculated from ProductCost.average_cost (PO → GRN flow).
    """
    start_date, end_date = parse_period(period)

    # Get previous period for comparison
    period_length = (end_date - start_date).days + 1
    prev_end = start_date - timedelta(days=1)
    prev_start = prev_end - timedelta(days=period_length - 1)

    # Get source filter
    source_filter = map_channel_filter_to_sources(channel_id) if channel_id else []

    # Get distinct sources with data
    # Only count orders with payment_status = 'PAID' (same as Dashboard)
    sources_query = select(Order.source).where(
        and_(
            Order.status.notin_(["CANCELLED", "DRAFT"]),
            or_(
                Order.payment_status == "PAID",
                Order.payment_status == "paid",
                func.upper(Order.payment_status) == "PAID"
            ),
            func.date(Order.created_at) >= start_date,
            func.date(Order.created_at) <= end_date
        )
    )
    if source_filter:
        sources_query = sources_query.where(Order.source.in_(source_filter))

    sources_query = sources_query.distinct()
    sources_result = await db.execute(sources_query)
    sources = [row[0] for row in sources_result.all() if row[0]]

    # If no data, return empty but with structure
    if not sources:
        return {
            "total_revenue": 0.0,
            "total_cogs": 0.0,
            "total_gross_profit": 0.0,
            "total_operating_expenses": 0.0,
            "total_net_income": 0.0,
            "channels": []
        }

    total_revenue = Decimal("0")
    total_cogs = Decimal("0")
    total_gross_profit = Decimal("0")
    total_operating_expenses = Decimal("0")
    total_net_income = Decimal("0")

    channel_data = []

    for source in sources:
        source_value = source or "OTHER"

        # Current period revenue (only PAID orders - same as Dashboard)
        revenue_query = select(
            func.coalesce(func.sum(Order.total_amount), 0).label("revenue"),
            func.coalesce(func.sum(Order.discount_amount), 0).label("discounts"),
            func.count(Order.id).label("order_count")
        ).where(
            and_(
                Order.source == source_value,
                Order.status.notin_(["CANCELLED", "DRAFT"]),
                or_(
                    Order.payment_status == "PAID",
                    func.upper(Order.payment_status) == "PAID"
                ),
                func.date(Order.created_at) >= start_date,
                func.date(Order.created_at) <= end_date
            )
        )
        revenue_result = await db.execute(revenue_query)
        revenue_data = revenue_result.one()

        gross_revenue = Decimal(str(revenue_data.revenue or 0))
        discounts = Decimal(str(revenue_data.discounts or 0))
        net_revenue = gross_revenue - discounts

        # Previous period revenue (only PAID orders)
        prev_revenue_query = select(
            func.coalesce(func.sum(Order.total_amount - Order.discount_amount), 0)
        ).where(
            and_(
                Order.source == source_value,
                Order.status.notin_(["CANCELLED", "DRAFT"]),
                or_(
                    Order.payment_status == "PAID",
                    func.upper(Order.payment_status) == "PAID"
                ),
                func.date(Order.created_at) >= prev_start,
                func.date(Order.created_at) <= prev_end
            )
        )
        prev_net_revenue = Decimal(str(await db.scalar(prev_revenue_query) or 0))

        # COGS from OrderItem joined with ProductCost (proper WAC from PO → GRN)
        # Join OrderItem with ProductCost on product_id to get average_cost
        # Use LEFT JOIN so orders without ProductCost still show (with 0 COGS)
        cogs_query = select(
            func.coalesce(
                func.sum(
                    OrderItem.quantity * func.coalesce(ProductCost.average_cost, Decimal("0"))
                ),
                0
            )
        ).select_from(OrderItem).join(
            Order, OrderItem.order_id == Order.id
        ).outerjoin(
            ProductCost,
            and_(
                ProductCost.product_id == OrderItem.product_id,
                # Get company-wide cost (warehouse_id IS NULL)
                or_(
                    ProductCost.warehouse_id.is_(None),
                    ProductCost.warehouse_id == Order.warehouse_id
                )
            )
        ).where(
            and_(
                Order.source == source_value,
                Order.status.notin_(["CANCELLED", "DRAFT"]),
                or_(
                    Order.payment_status == "PAID",
                    func.upper(Order.payment_status) == "PAID"
                ),
                func.date(Order.created_at) >= start_date,
                func.date(Order.created_at) <= end_date
            )
        )
        cogs = Decimal(str(await db.scalar(cogs_query) or 0))

        # Previous COGS
        prev_cogs_query = select(
            func.coalesce(
                func.sum(
                    OrderItem.quantity * func.coalesce(ProductCost.average_cost, Decimal("0"))
                ),
                0
            )
        ).select_from(OrderItem).join(
            Order, OrderItem.order_id == Order.id
        ).outerjoin(
            ProductCost,
            and_(
                ProductCost.product_id == OrderItem.product_id,
                or_(
                    ProductCost.warehouse_id.is_(None),
                    ProductCost.warehouse_id == Order.warehouse_id
                )
            )
        ).where(
            and_(
                Order.source == source_value,
                Order.status.notin_(["CANCELLED", "DRAFT"]),
                or_(
                    Order.payment_status == "PAID",
                    func.upper(Order.payment_status) == "PAID"
                ),
                func.date(Order.created_at) >= prev_start,
                func.date(Order.created_at) <= prev_end
            )
        )
        prev_cogs = Decimal(str(await db.scalar(prev_cogs_query) or 0))

        gross_profit = net_revenue - cogs
        gross_margin = float((gross_profit / net_revenue * 100) if net_revenue > 0 else 0)

        prev_gross_profit = prev_net_revenue - prev_cogs

        # Operating expenses (channel fees + shipping + payment processing)
        commission_rate = COMMISSION_RATES.get(source_value, Decimal("0.05"))
        channel_fees = net_revenue * commission_rate

        shipping_query = select(
            func.coalesce(func.sum(Order.shipping_amount), 0)
        ).where(
            and_(
                Order.source == source_value,
                Order.status.notin_(["CANCELLED", "DRAFT"]),
                or_(
                    Order.payment_status == "PAID",
                    func.upper(Order.payment_status) == "PAID"
                ),
                func.date(Order.created_at) >= start_date,
                func.date(Order.created_at) <= end_date
            )
        )
        shipping = Decimal(str(await db.scalar(shipping_query) or 0))

        payment_fees = net_revenue * Decimal("0.02")  # 2% payment processing

        operating_expenses = channel_fees + shipping + payment_fees
        operating_income = gross_profit - operating_expenses
        net_income = operating_income
        net_margin = float((net_income / net_revenue * 100) if net_revenue > 0 else 0)

        prev_operating_expenses = prev_net_revenue * (commission_rate + Decimal("0.02"))
        prev_net_income = prev_gross_profit - prev_operating_expenses

        # Build revenue line items
        revenue_change = float(((net_revenue - prev_net_revenue) / prev_net_revenue * 100) if prev_net_revenue > 0 else 0)

        channel_data.append({
            "channel_id": source_value,
            "channel_name": SOURCE_DISPLAY_NAMES.get(source_value, source_value),
            "channel_type": SOURCE_CHANNEL_TYPES.get(source_value, "OTHER"),
            "revenue": [
                {
                    "account_code": "4000",
                    "account_name": "Product Sales",
                    "amount": float(gross_revenue),
                    "previous_amount": float(prev_net_revenue + (prev_cogs * Decimal("0.1"))),
                    "change_percent": revenue_change,
                    "is_header": False,
                    "indent_level": 0
                },
                {
                    "account_code": "4900",
                    "account_name": "Discounts & Allowances",
                    "amount": float(-discounts),
                    "previous_amount": 0,
                    "change_percent": 0,
                    "is_header": False,
                    "indent_level": 0
                }
            ],
            "cost_of_goods_sold": [
                {
                    "account_code": "5000",
                    "account_name": "Cost of Goods Sold",
                    "amount": float(cogs),
                    "previous_amount": float(prev_cogs),
                    "change_percent": float(((cogs - prev_cogs) / prev_cogs * 100) if prev_cogs > 0 else 0),
                    "is_header": False,
                    "indent_level": 0
                }
            ],
            "gross_profit": float(gross_profit),
            "gross_margin_percent": round(gross_margin, 2),
            "operating_expenses": [
                {
                    "account_code": "6100",
                    "account_name": "Channel/Platform Fees",
                    "amount": float(channel_fees),
                    "previous_amount": 0,
                    "change_percent": 0,
                    "is_header": False,
                    "indent_level": 0
                },
                {
                    "account_code": "6200",
                    "account_name": "Shipping & Logistics",
                    "amount": float(shipping),
                    "previous_amount": 0,
                    "change_percent": 0,
                    "is_header": False,
                    "indent_level": 0
                },
                {
                    "account_code": "6300",
                    "account_name": "Payment Processing Fees",
                    "amount": float(payment_fees),
                    "previous_amount": 0,
                    "change_percent": 0,
                    "is_header": False,
                    "indent_level": 0
                }
            ],
            "operating_income": float(operating_income),
            "other_income_expense": [],
            "net_income": float(net_income),
            "net_margin_percent": round(net_margin, 2),
            "previous_gross_profit": float(prev_gross_profit),
            "previous_net_income": float(prev_net_income),
        })

        total_revenue += net_revenue
        total_cogs += cogs
        total_gross_profit += gross_profit
        total_operating_expenses += operating_expenses
        total_net_income += net_income

    return {
        "total_revenue": float(total_revenue),
        "total_cogs": float(total_cogs),
        "total_gross_profit": float(total_gross_profit),
        "total_operating_expenses": float(total_operating_expenses),
        "total_net_income": float(total_net_income),
        "channels": channel_data
    }


# ==================== GEOGRAPHIC ANALYTICS ====================

from app.models.customer import Customer


@router.get("/geographic/orders")
@require_module("sales_distribution")
async def get_geographic_order_stats(
    db: DB,
    current_user: User = Depends(get_current_user),
    period: str = Query("this_month"),
    group_by: str = Query("state", regex="^(state|city|pincode)$"),
    limit: int = Query(20, ge=1, le=100),
):
    """
    Get order statistics grouped by geographic location.

    Grouping options:
    - state: Orders by state
    - city: Orders by city
    - pincode: Orders by pincode

    Returns top locations by order count and revenue.
    """
    start_date, end_date = parse_period(period)

    # Build the group by column based on parameter
    # Orders have shipping_address as JSON, need to extract location fields
    if group_by == "state":
        # Extract state from JSON shipping_address
        location_field = func.json_extract_path_text(Order.shipping_address, 'state')
    elif group_by == "city":
        location_field = func.json_extract_path_text(Order.shipping_address, 'city')
    else:  # pincode
        location_field = func.json_extract_path_text(Order.shipping_address, 'pincode')

    # Query orders grouped by location
    query = select(
        location_field.label('location'),
        func.count(Order.id).label('order_count'),
        func.sum(Order.total_amount).label('total_revenue'),
        func.avg(Order.total_amount).label('avg_order_value'),
        func.count(func.distinct(Order.customer_id)).label('unique_customers'),
    ).where(
        and_(
            Order.status.notin_(["CANCELLED", "DRAFT"]),
            func.date(Order.created_at) >= start_date,
            func.date(Order.created_at) <= end_date,
            location_field.isnot(None),
            location_field != "",
        )
    ).group_by(location_field).order_by(
        func.count(Order.id).desc()
    ).limit(limit)

    result = await db.execute(query)
    rows = result.all()

    # Calculate totals
    total_orders = sum(row.order_count for row in rows)
    total_revenue = sum(float(row.total_revenue or 0) for row in rows)

    locations = []
    for row in rows:
        revenue = float(row.total_revenue or 0)
        locations.append({
            "location": row.location,
            "order_count": row.order_count,
            "order_share": round((row.order_count / total_orders * 100) if total_orders > 0 else 0, 2),
            "total_revenue": revenue,
            "revenue_share": round((revenue / total_revenue * 100) if total_revenue > 0 else 0, 2),
            "avg_order_value": round(float(row.avg_order_value or 0), 2),
            "unique_customers": row.unique_customers,
        })

    return {
        "period": period,
        "group_by": group_by,
        "total_orders": total_orders,
        "total_revenue": total_revenue,
        "locations": locations,
    }


@router.get("/geographic/customers")
@require_module("sales_distribution")
async def get_geographic_customer_stats(
    db: DB,
    current_user: User = Depends(get_current_user),
    group_by: str = Query("state", regex="^(state|city)$"),
    limit: int = Query(20, ge=1, le=100),
):
    """
    Get customer statistics grouped by geographic location.

    Returns customer distribution across states/cities with order metrics.
    """
    # Customer location is in primary_address JSON field
    if group_by == "state":
        location_field = func.json_extract_path_text(Customer.primary_address, 'state')
    else:  # city
        location_field = func.json_extract_path_text(Customer.primary_address, 'city')

    # Query customer stats by location
    query = select(
        location_field.label('location'),
        func.count(Customer.id).label('customer_count'),
        func.sum(Customer.total_orders).label('total_orders'),
        func.sum(Customer.total_spent).label('total_revenue'),
        func.avg(Customer.total_spent).label('avg_customer_value'),
    ).where(
        and_(
            Customer.is_active == True,
            location_field.isnot(None),
            location_field != "",
        )
    ).group_by(location_field).order_by(
        func.count(Customer.id).desc()
    ).limit(limit)

    result = await db.execute(query)
    rows = result.all()

    total_customers = sum(row.customer_count for row in rows)

    locations = []
    for row in rows:
        locations.append({
            "location": row.location,
            "customer_count": row.customer_count,
            "customer_share": round((row.customer_count / total_customers * 100) if total_customers > 0 else 0, 2),
            "total_orders": row.total_orders or 0,
            "total_revenue": float(row.total_revenue or 0),
            "avg_customer_value": round(float(row.avg_customer_value or 0), 2),
        })

    return {
        "group_by": group_by,
        "total_customers": total_customers,
        "locations": locations,
    }


@router.get("/geographic/heatmap")
@require_module("sales_distribution")
async def get_geographic_heatmap_data(
    db: DB,
    current_user: User = Depends(get_current_user),
    metric: str = Query("orders", regex="^(orders|revenue|customers)$"),
    period: str = Query("this_month"),
):
    """
    Get geographic data formatted for heatmap visualization.

    Returns state-level data with metrics for India map visualization.
    """
    start_date, end_date = parse_period(period)

    state_field = func.json_extract_path_text(Order.shipping_address, 'state')

    # State abbreviations for mapping
    STATE_CODES = {
        "Andhra Pradesh": "AP", "Arunachal Pradesh": "AR", "Assam": "AS",
        "Bihar": "BR", "Chhattisgarh": "CG", "Goa": "GA", "Gujarat": "GJ",
        "Haryana": "HR", "Himachal Pradesh": "HP", "Jharkhand": "JH",
        "Karnataka": "KA", "Kerala": "KL", "Madhya Pradesh": "MP",
        "Maharashtra": "MH", "Manipur": "MN", "Meghalaya": "ML",
        "Mizoram": "MZ", "Nagaland": "NL", "Odisha": "OD", "Punjab": "PB",
        "Rajasthan": "RJ", "Sikkim": "SK", "Tamil Nadu": "TN",
        "Telangana": "TS", "Tripura": "TR", "Uttar Pradesh": "UP",
        "Uttarakhand": "UK", "West Bengal": "WB", "Delhi": "DL",
        "Jammu and Kashmir": "JK", "Ladakh": "LA", "Chandigarh": "CH",
        "Puducherry": "PY", "Andaman and Nicobar Islands": "AN",
        "Dadra and Nagar Haveli and Daman and Diu": "DD", "Lakshadweep": "LD",
    }

    query = select(
        state_field.label('state'),
        func.count(Order.id).label('order_count'),
        func.sum(Order.total_amount).label('total_revenue'),
        func.count(func.distinct(Order.customer_id)).label('unique_customers'),
    ).where(
        and_(
            Order.status.notin_(["CANCELLED", "DRAFT"]),
            func.date(Order.created_at) >= start_date,
            func.date(Order.created_at) <= end_date,
            state_field.isnot(None),
            state_field != "",
        )
    ).group_by(state_field)

    result = await db.execute(query)
    rows = result.all()

    # Calculate max value for normalization
    if metric == "orders":
        max_val = max((row.order_count for row in rows), default=1)
    elif metric == "revenue":
        max_val = max((float(row.total_revenue or 0) for row in rows), default=1)
    else:
        max_val = max((row.unique_customers for row in rows), default=1)

    heatmap_data = []
    for row in rows:
        state_name = row.state
        if metric == "orders":
            value = row.order_count
        elif metric == "revenue":
            value = float(row.total_revenue or 0)
        else:
            value = row.unique_customers

        heatmap_data.append({
            "state": state_name,
            "state_code": STATE_CODES.get(state_name, state_name[:2].upper()),
            "value": value,
            "intensity": round(value / max_val, 2) if max_val > 0 else 0,
            "order_count": row.order_count,
            "revenue": float(row.total_revenue or 0),
            "customers": row.unique_customers,
        })

    return {
        "metric": metric,
        "period": period,
        "max_value": max_val,
        "data": heatmap_data,
    }


# ==================== PROMOTIONAL ANALYTICS ====================

from app.models.coupon import Coupon

@router.get("/promotions/performance")
@require_module("sales_distribution")
async def get_promotion_performance(
    db: DB,
    current_user: User = Depends(get_current_user),
    period: str = Query("this_month"),
    limit: int = Query(20, ge=1, le=100),
):
    """
    Get performance metrics for coupons and promotions.

    Returns:
    - Coupon usage stats
    - Revenue impact
    - Customer acquisition from promotions
    """
    start_date, end_date = parse_period(period)

    # Get orders with discount codes
    promo_query = select(
        Order.discount_code,
        func.count(Order.id).label('usage_count'),
        func.sum(Order.discount_amount).label('total_discount'),
        func.sum(Order.total_amount).label('total_revenue'),
        func.avg(Order.total_amount).label('avg_order_value'),
        func.count(func.distinct(Order.customer_id)).label('unique_customers'),
    ).where(
        and_(
            Order.status.notin_(["CANCELLED", "DRAFT"]),
            func.date(Order.created_at) >= start_date,
            func.date(Order.created_at) <= end_date,
            Order.discount_code.isnot(None),
            Order.discount_code != "",
        )
    ).group_by(Order.discount_code).order_by(
        func.count(Order.id).desc()
    ).limit(limit)

    result = await db.execute(promo_query)
    promo_rows = result.all()

    # Get coupon details for matching
    coupon_codes = [row.discount_code for row in promo_rows if row.discount_code]
    coupon_details = {}
    if coupon_codes:
        coupon_query = select(Coupon).where(Coupon.code.in_(coupon_codes))
        coupon_result = await db.execute(coupon_query)
        coupons = coupon_result.scalars().all()
        coupon_details = {c.code: c for c in coupons}

    promotions = []
    total_discount_given = 0
    total_revenue_with_promo = 0

    for row in promo_rows:
        coupon = coupon_details.get(row.discount_code)
        discount = float(row.total_discount or 0)
        revenue = float(row.total_revenue or 0)

        total_discount_given += discount
        total_revenue_with_promo += revenue

        promotions.append({
            "code": row.discount_code,
            "name": coupon.name if coupon else row.discount_code,
            "type": coupon.discount_type if coupon else "UNKNOWN",
            "usage_count": row.usage_count,
            "usage_limit": coupon.max_uses if coupon else None,
            "total_discount": discount,
            "total_revenue": revenue,
            "avg_order_value": round(float(row.avg_order_value or 0), 2),
            "unique_customers": row.unique_customers,
            "roi": round((revenue / discount - 1) * 100, 2) if discount > 0 else 0,
            "is_active": coupon.is_active if coupon else None,
        })

    # Get overall stats
    total_orders_query = select(func.count(Order.id)).where(
        and_(
            Order.status.notin_(["CANCELLED", "DRAFT"]),
            func.date(Order.created_at) >= start_date,
            func.date(Order.created_at) <= end_date,
        )
    )
    total_orders = await db.scalar(total_orders_query) or 0

    promo_orders = sum(p["usage_count"] for p in promotions)

    return {
        "period": period,
        "summary": {
            "total_promotions_used": len(promotions),
            "total_discount_given": total_discount_given,
            "total_revenue_with_promotions": total_revenue_with_promo,
            "promo_orders_count": promo_orders,
            "total_orders_count": total_orders,
            "promo_order_rate": round((promo_orders / total_orders * 100) if total_orders > 0 else 0, 2),
            "avg_discount_per_order": round(total_discount_given / promo_orders, 2) if promo_orders > 0 else 0,
        },
        "promotions": promotions,
    }


@router.get("/promotions/trends")
@require_module("sales_distribution")
async def get_promotion_trends(
    db: DB,
    current_user: User = Depends(get_current_user),
    coupon_code: Optional[str] = Query(None),
    period: str = Query("this_month"),
):
    """
    Get daily trends for promotion usage.

    Shows usage over time for tracking campaign effectiveness.
    """
    start_date, end_date = parse_period(period)

    conditions = [
        Order.status.notin_(["CANCELLED", "DRAFT"]),
        func.date(Order.created_at) >= start_date,
        func.date(Order.created_at) <= end_date,
    ]

    if coupon_code:
        conditions.append(Order.discount_code == coupon_code)
    else:
        conditions.append(Order.discount_code.isnot(None))
        conditions.append(Order.discount_code != "")

    # Daily trend query
    trend_query = select(
        func.date(Order.created_at).label('date'),
        func.count(Order.id).label('order_count'),
        func.sum(Order.discount_amount).label('total_discount'),
        func.sum(Order.total_amount).label('total_revenue'),
    ).where(
        and_(*conditions)
    ).group_by(
        func.date(Order.created_at)
    ).order_by(
        func.date(Order.created_at)
    )

    result = await db.execute(trend_query)
    rows = result.all()

    daily_data = []
    for row in rows:
        daily_data.append({
            "date": row.date.isoformat() if row.date else None,
            "order_count": row.order_count,
            "total_discount": float(row.total_discount or 0),
            "total_revenue": float(row.total_revenue or 0),
        })

    return {
        "period": period,
        "coupon_code": coupon_code,
        "total_days": len(daily_data),
        "daily_data": daily_data,
    }
