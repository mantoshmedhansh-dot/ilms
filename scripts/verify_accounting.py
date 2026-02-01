"""Verify accounting data in the database."""
import asyncio
import sys
sys.path.insert(0, '/Users/mantosh/Consumer durable')

from sqlalchemy import select, func, text

from app.database import async_session_factory
from app.models.accounting import (
    ChartOfAccount, JournalEntry, JournalEntryLine, GeneralLedger,
)


async def verify():
    """Verify accounting data."""
    print("=" * 70)
    print("ACCOUNTING DATA VERIFICATION")
    print("=" * 70)

    async with async_session_factory() as db:
        # 1. Journal Entries - use raw SQL to avoid UUID issues
        print("\n=== JOURNAL ENTRIES ===")
        result = await db.execute(
            text("""
                SELECT entry_number, entry_type, source_type, entry_date,
                       total_debit, total_credit, status, narration
                FROM journal_entries
                ORDER BY created_at DESC LIMIT 5
            """)
        )
        entries = result.fetchall()

        if entries:
            for je in entries:
                print(f"\n  Entry: {je[0]}")
                print(f"  Type: {je[1]} | Source: {je[2]}")
                print(f"  Date: {je[3]} | Status: {je[6]}")
                print(f"  Debit: ₹{float(je[4]):,.2f} | Credit: ₹{float(je[5]):,.2f}")
                print(f"  Narration: {je[7]}")
        else:
            print("  No journal entries found")

        # 2. General Ledger Summary
        print("\n=== GENERAL LEDGER SUMMARY ===")
        result = await db.execute(select(func.count(GeneralLedger.id)))
        gl_count = result.scalar()
        print(f"  Total GL Entries: {gl_count}")

        # 3. Account Balances (non-zero)
        print("\n=== ACCOUNT BALANCES (Non-Zero) ===")
        result = await db.execute(
            select(ChartOfAccount).where(
                ChartOfAccount.current_balance != 0
            ).order_by(ChartOfAccount.account_code)
        )
        accounts = result.scalars().all()

        if accounts:
            total_debits = 0
            total_credits = 0

            for acc in accounts:
                balance_type = "Dr" if acc.current_balance >= 0 else "Cr"
                print(f"  {acc.account_code}: {acc.account_name}")
                print(f"           Balance: ₹{abs(acc.current_balance):,.2f} {balance_type}")

                # Calculate totals based on account type
                if acc.account_type.value in ['ASSET', 'EXPENSE']:
                    total_debits += acc.current_balance
                else:
                    total_credits += acc.current_balance

            print(f"\n  --- Summary ---")
            print(f"  Total Assets/Expenses (Debit Nature): ₹{total_debits:,.2f}")
            print(f"  Total Liabilities/Equity/Revenue (Credit Nature): ₹{total_credits:,.2f}")
        else:
            print("  No accounts with non-zero balance")

        # 4. Trial Balance Check
        print("\n=== TRIAL BALANCE CHECK ===")
        if accounts:
            assets_expenses = sum(a.current_balance for a in accounts if a.account_type.value in ['ASSET', 'EXPENSE'])
            liab_equity_rev = sum(a.current_balance for a in accounts if a.account_type.value not in ['ASSET', 'EXPENSE'])

            print(f"  Debit Balances (Assets+Expenses): ₹{assets_expenses:,.2f}")
            print(f"  Credit Balances (Liab+Equity+Rev): ₹{liab_equity_rev:,.2f}")

            if abs(assets_expenses - liab_equity_rev) < 0.01:
                print("  ✓ Trial Balance BALANCED")
            else:
                diff = assets_expenses - liab_equity_rev
                print(f"  ✗ Trial Balance UNBALANCED by ₹{diff:,.2f}")

    print("\n" + "=" * 70)


if __name__ == "__main__":
    asyncio.run(verify())
