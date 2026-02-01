#!/usr/bin/env python3
"""Test GL entries and P&L verification."""

import asyncio
import sys
import logging
from decimal import Decimal
import uuid
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add project to path
sys.path.insert(0, '/Users/mantosh/Desktop/Consumer durable 2')

from app.database import async_session_factory


async def test_gl_pnl_flow():
    """Test verifying GL entries and calculating P&L."""

    async with async_session_factory() as db:
        from sqlalchemy import text

        # Step 1: Check all journal entries
        logger.info("=" * 70)
        logger.info("JOURNAL ENTRIES SUMMARY")
        logger.info("=" * 70)

        je_result = await db.execute(text("""
            SELECT
                je.entry_number, je.entry_type, je.source_type,
                je.total_debit, je.total_credit, je.status, je.entry_date
            FROM journal_entries je
            ORDER BY je.created_at DESC
            LIMIT 10
        """))
        journal_entries = je_result.fetchall()

        logger.info(f"Recent Journal Entries ({len(journal_entries)}):")
        total_debit = Decimal("0")
        total_credit = Decimal("0")
        for je in journal_entries:
            logger.info(f"  {je[0]} | {je[1]} | {je[2]} | DR: {je[3]} | CR: {je[4]} | {je[5]}")
            total_debit += je[3] or Decimal("0")
            total_credit += je[4] or Decimal("0")

        logger.info(f"\nTotal Debits: {total_debit}")
        logger.info(f"Total Credits: {total_credit}")

        # Step 2: Check General Ledger entries
        logger.info("\n" + "=" * 70)
        logger.info("GENERAL LEDGER ENTRIES")
        logger.info("=" * 70)

        gl_result = await db.execute(text("""
            SELECT
                ca.account_code, ca.account_name, ca.account_type,
                SUM(gl.debit_amount) as total_dr,
                SUM(gl.credit_amount) as total_cr,
                COUNT(*) as entry_count
            FROM general_ledger gl
            JOIN chart_of_accounts ca ON gl.account_id = ca.id
            GROUP BY ca.account_code, ca.account_name, ca.account_type
            ORDER BY ca.account_code
        """))
        gl_entries = gl_result.fetchall()

        logger.info(f"GL Account Summary ({len(gl_entries)} accounts):")
        for gl in gl_entries:
            dr = gl[3] or Decimal("0")
            cr = gl[4] or Decimal("0")
            balance = dr - cr
            logger.info(f"  {gl[0]} | {gl[1]:<25} | {gl[2]:<10} | DR: {dr:>10.2f} | CR: {cr:>10.2f} | Bal: {balance:>10.2f}")

        # Step 3: Check Chart of Accounts balances
        logger.info("\n" + "=" * 70)
        logger.info("CHART OF ACCOUNTS - CURRENT BALANCES")
        logger.info("=" * 70)

        coa_result = await db.execute(text("""
            SELECT
                account_code, account_name, account_type,
                current_balance
            FROM chart_of_accounts
            WHERE current_balance != 0 OR account_code IN ('1010', '1020', '1300', '4000')
            ORDER BY account_code
        """))
        accounts = coa_result.fetchall()

        logger.info("Accounts with non-zero balances:")
        total_assets = Decimal("0")
        total_liabilities = Decimal("0")
        total_revenue = Decimal("0")
        total_expenses = Decimal("0")

        for acc in accounts:
            balance = acc[3] or Decimal("0")
            logger.info(f"  {acc[0]} | {acc[1]:<25} | {acc[2]:<10} | Balance: {balance:>12.2f}")

            if acc[2] == "ASSET":
                total_assets += balance
            elif acc[2] == "LIABILITY":
                total_liabilities += balance
            elif acc[2] == "REVENUE":
                total_revenue += balance
            elif acc[2] == "EXPENSE":
                total_expenses += balance

        # Step 4: Calculate P&L
        logger.info("\n" + "=" * 70)
        logger.info("PROFIT & LOSS SUMMARY")
        logger.info("=" * 70)

        logger.info(f"Total Revenue:  {total_revenue:>12.2f}")
        logger.info(f"Total Expenses: {total_expenses:>12.2f}")
        logger.info(f"-" * 30)
        net_profit = total_revenue - total_expenses
        logger.info(f"Net Profit:     {net_profit:>12.2f}")

        # Step 5: Balance Sheet Summary
        logger.info("\n" + "=" * 70)
        logger.info("BALANCE SHEET SUMMARY")
        logger.info("=" * 70)

        logger.info(f"Total Assets:      {total_assets:>12.2f}")
        logger.info(f"Total Liabilities: {total_liabilities:>12.2f}")
        logger.info(f"-" * 30)
        net_equity = total_assets - total_liabilities
        logger.info(f"Net Equity:        {net_equity:>12.2f}")

        # Step 6: Verify accounting equation
        logger.info("\n" + "=" * 70)
        logger.info("ACCOUNTING VERIFICATION")
        logger.info("=" * 70)

        # Check if journal entries are balanced
        je_balanced = abs(total_debit - total_credit) < Decimal("0.01")
        logger.info(f"Journal Entries Balanced: {'✅ YES' if je_balanced else '❌ NO'}")
        logger.info(f"  Total Debit:  {total_debit}")
        logger.info(f"  Total Credit: {total_credit}")

        # Accounting equation: Assets = Liabilities + Equity
        equity_from_equation = total_assets - total_liabilities
        logger.info(f"\nAccounting Equation (A = L + E):")
        logger.info(f"  Assets:      {total_assets:>12.2f}")
        logger.info(f"  Liabilities: {total_liabilities:>12.2f}")
        logger.info(f"  Equity:      {equity_from_equation:>12.2f}")

        logger.info("\n" + "=" * 70)
        if je_balanced and len(journal_entries) > 0:
            logger.info("✅ GL + P&L FLOW TEST PASSED!")
            logger.info("=" * 70)
        else:
            if len(journal_entries) == 0:
                logger.info("⚠️ No journal entries found - payment test may need to run first")
            else:
                logger.info("❌ GL + P&L FLOW TEST FAILED - entries not balanced")
            logger.info("=" * 70)

        return {
            "journal_entries": len(journal_entries),
            "gl_accounts": len(gl_entries),
            "total_debit": total_debit,
            "total_credit": total_credit,
            "net_profit": net_profit,
            "net_equity": net_equity,
        }


if __name__ == "__main__":
    asyncio.run(test_gl_pnl_flow())
