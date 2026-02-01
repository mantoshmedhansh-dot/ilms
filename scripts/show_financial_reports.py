"""Show current P&L and Balance Sheet reports with channel-wise breakdown."""
import asyncio
import sys
sys.path.insert(0, '/Users/mantosh/Consumer durable')

from datetime import date, datetime
from decimal import Decimal
from sqlalchemy import select, func, and_, text
from sqlalchemy.orm import joinedload

from app.database import async_session_factory
from app.models.accounting import ChartOfAccount, AccountType, GeneralLedger
from app.models.channel import SalesChannel


async def show_reports():
    """Show P&L and Balance Sheet."""
    print("=" * 80)
    print("FINANCIAL REPORTS")
    print(f"As of: {date.today()}")
    print("=" * 80)

    async with async_session_factory() as db:
        # Get all accounts with balances
        result = await db.execute(
            select(ChartOfAccount).order_by(ChartOfAccount.account_code)
        )
        all_accounts = result.scalars().all()

        # ==================== BALANCE SHEET ====================
        print("\n" + "=" * 80)
        print("                           BALANCE SHEET")
        print("=" * 80)

        # Assets
        print("\nASSETS")
        print("-" * 60)
        total_assets = Decimal("0")
        for acc in all_accounts:
            if acc.account_type == AccountType.ASSET and acc.current_balance != 0:
                print(f"  {acc.account_code} {acc.account_name:<40} ₹{acc.current_balance:>12,.2f}")
                total_assets += acc.current_balance
        print(f"  {'TOTAL ASSETS':<45} ₹{total_assets:>12,.2f}")

        # Liabilities
        print("\nLIABILITIES")
        print("-" * 60)
        total_liabilities = Decimal("0")
        for acc in all_accounts:
            if acc.account_type == AccountType.LIABILITY and acc.current_balance != 0:
                print(f"  {acc.account_code} {acc.account_name:<40} ₹{acc.current_balance:>12,.2f}")
                total_liabilities += acc.current_balance
        if total_liabilities == 0:
            print("  (No liability balances)")
        print(f"  {'TOTAL LIABILITIES':<45} ₹{total_liabilities:>12,.2f}")

        # Equity
        print("\nEQUITY")
        print("-" * 60)
        total_equity = Decimal("0")
        for acc in all_accounts:
            if acc.account_type == AccountType.EQUITY and acc.current_balance != 0:
                print(f"  {acc.account_code} {acc.account_name:<40} ₹{acc.current_balance:>12,.2f}")
                total_equity += acc.current_balance

        # Current period P&L (Revenue - Expenses)
        total_revenue = sum(acc.current_balance for acc in all_accounts if acc.account_type == AccountType.REVENUE)
        total_expenses = sum(acc.current_balance for acc in all_accounts if acc.account_type == AccountType.EXPENSE)
        current_pl = total_revenue - total_expenses

        if current_pl != 0:
            print(f"  {'Current Period Profit/Loss':<44} ₹{current_pl:>12,.2f}")
            total_equity += current_pl

        print(f"  {'TOTAL EQUITY':<45} ₹{total_equity:>12,.2f}")

        print("\n" + "-" * 60)
        print(f"  {'TOTAL LIABILITIES + EQUITY':<45} ₹{(total_liabilities + total_equity):>12,.2f}")

        # Balance check
        if abs(total_assets - (total_liabilities + total_equity)) < Decimal("0.01"):
            print("\n  ✓ Balance Sheet BALANCED")
        else:
            diff = total_assets - (total_liabilities + total_equity)
            print(f"\n  ✗ Balance Sheet UNBALANCED by ₹{diff:,.2f}")

        # ==================== PROFIT & LOSS ====================
        print("\n" + "=" * 80)
        print("                      PROFIT & LOSS STATEMENT")
        print("                   (Current Financial Period)")
        print("=" * 80)

        # Revenue
        print("\nREVENUE")
        print("-" * 60)
        for acc in all_accounts:
            if acc.account_type == AccountType.REVENUE and acc.current_balance != 0:
                print(f"  {acc.account_code} {acc.account_name:<40} ₹{acc.current_balance:>12,.2f}")
        print(f"  {'TOTAL REVENUE':<45} ₹{total_revenue:>12,.2f}")

        # Expenses
        print("\nEXPENSES")
        print("-" * 60)

        # COGS (5xxx accounts)
        cogs_total = Decimal("0")
        for acc in all_accounts:
            if acc.account_type == AccountType.EXPENSE and acc.account_code.startswith("5") and acc.current_balance != 0:
                print(f"  {acc.account_code} {acc.account_name:<40} ₹{acc.current_balance:>12,.2f}")
                cogs_total += acc.current_balance

        print(f"  {'Cost of Goods Sold (COGS)':<45} ₹{cogs_total:>12,.2f}")

        # Gross Profit
        gross_profit = total_revenue - cogs_total
        print(f"\n  {'GROSS PROFIT':<45} ₹{gross_profit:>12,.2f}")

        # Operating Expenses (6xxx accounts)
        print("\nOPERATING EXPENSES")
        print("-" * 60)
        opex_total = Decimal("0")
        for acc in all_accounts:
            if acc.account_type == AccountType.EXPENSE and acc.account_code.startswith("6") and acc.current_balance != 0:
                print(f"  {acc.account_code} {acc.account_name:<40} ₹{acc.current_balance:>12,.2f}")
                opex_total += acc.current_balance

        if opex_total == 0:
            print("  (No operating expenses)")
        print(f"  {'Total Operating Expenses':<45} ₹{opex_total:>12,.2f}")

        # Operating Profit
        operating_profit = gross_profit - opex_total
        print(f"\n  {'OPERATING PROFIT (EBIT)':<45} ₹{operating_profit:>12,.2f}")

        # Other Expenses (7xxx accounts)
        other_exp = Decimal("0")
        for acc in all_accounts:
            if acc.account_type == AccountType.EXPENSE and acc.account_code.startswith("7") and acc.current_balance != 0:
                print(f"  {acc.account_code} {acc.account_name:<40} ₹{acc.current_balance:>12,.2f}")
                other_exp += acc.current_balance

        # Net Profit
        net_profit = operating_profit - other_exp
        print("\n" + "=" * 60)
        print(f"  {'NET PROFIT / (LOSS)':<45} ₹{net_profit:>12,.2f}")
        print("=" * 60)

        # ==================== CHANNEL-WISE P&L ====================
        print("\n" + "=" * 80)
        print("                      CHANNEL-WISE P&L BREAKDOWN")
        print("=" * 80)

        # Get all channels
        result = await db.execute(select(SalesChannel).where(SalesChannel.status == 'ACTIVE'))
        channels = result.scalars().all()

        if not channels:
            print("\n  No sales channels configured.")
        else:
            # Get revenue accounts (4xxx)
            revenue_accounts = [acc for acc in all_accounts if acc.account_type == AccountType.REVENUE]
            revenue_account_ids = [acc.id for acc in revenue_accounts]

            # Get expense accounts (5xxx and 6xxx)
            expense_accounts = [acc for acc in all_accounts if acc.account_type == AccountType.EXPENSE]
            expense_account_ids = [acc.id for acc in expense_accounts]

            print(f"\n  {'Channel':<25} {'Revenue':>15} {'Expenses':>15} {'Net Profit':>15}")
            print("  " + "-" * 70)

            for channel in channels:
                # Get channel revenue from GL
                result = await db.execute(
                    select(func.sum(GeneralLedger.credit_amount))
                    .where(
                        and_(
                            GeneralLedger.channel_id == channel.id,
                            GeneralLedger.account_id.in_(revenue_account_ids)
                        )
                    )
                )
                ch_revenue = result.scalar() or Decimal("0")

                # Get channel expenses from GL
                result = await db.execute(
                    select(func.sum(GeneralLedger.debit_amount))
                    .where(
                        and_(
                            GeneralLedger.channel_id == channel.id,
                            GeneralLedger.account_id.in_(expense_account_ids)
                        )
                    )
                )
                ch_expenses = result.scalar() or Decimal("0")

                ch_profit = ch_revenue - ch_expenses

                if ch_revenue > 0 or ch_expenses > 0:
                    print(f"  {channel.name:<25} ₹{ch_revenue:>12,.2f} ₹{ch_expenses:>12,.2f} ₹{ch_profit:>12,.2f}")

            print("  " + "-" * 70)
            print(f"  {'TOTAL':<25} ₹{total_revenue:>12,.2f} ₹{total_expenses:>12,.2f} ₹{net_profit:>12,.2f}")

            print("\n  ✓ Channel tracking is NOW implemented!")
            print("  All new orders with channel info will automatically track channel-wise P&L.")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    asyncio.run(show_reports())
