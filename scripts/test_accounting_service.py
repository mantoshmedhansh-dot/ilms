"""Test the Accounting Service directly."""
import asyncio
import sys
sys.path.insert(0, '/Users/mantosh/Consumer durable')

from datetime import datetime
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import select, func

from app.database import async_session_factory
from app.models.accounting import (
    ChartOfAccount, JournalEntry, JournalEntryLine,
    GeneralLedger, FinancialPeriod, FinancialPeriodStatus,
)
from app.services.accounting_service import AccountingService


async def test_accounting():
    """Test the accounting service."""
    print("=" * 60)
    print("TESTING ACCOUNTING SERVICE")
    print("=" * 60)

    async with async_session_factory() as db:
        # 1. Check accounts exist
        print("\n1. Checking Chart of Accounts...")
        result = await db.execute(select(func.count(ChartOfAccount.id)))
        count = result.scalar()
        print(f"   Total accounts: {count}")

        # Check specific accounts
        key_accounts = ["1110", "4110", "2210", "2220"]  # AR, Sales, CGST Output, SGST Output
        for code in key_accounts:
            result = await db.execute(
                select(ChartOfAccount).where(ChartOfAccount.account_code == code)
            )
            acc = result.scalar_one_or_none()
            if acc:
                print(f"   {code}: {acc.account_name} (Balance: {acc.current_balance})")
            else:
                print(f"   {code}: NOT FOUND!")

        # 2. Check financial periods
        print("\n2. Checking Financial Periods...")
        result = await db.execute(
            select(FinancialPeriod).where(
                FinancialPeriod.status == FinancialPeriodStatus.OPEN
            )
        )
        periods = result.scalars().all()
        print(f"   Open periods: {len(periods)}")
        for p in periods:
            print(f"     - {p.period_name} (type={p.period_type}, current={p.is_current})")

        # 3. Test accounting service initialization
        print("\n3. Testing AccountingService...")
        try:
            accounting = AccountingService(db)

            # Test _get_current_period
            period_id = await accounting._get_current_period()
            if period_id:
                print(f"   Current period found: {period_id}")
            else:
                print("   ERROR: No current period found!")
                return

            # Test _get_account_id
            ar_id = await accounting._get_account_id("1110")
            if ar_id:
                print(f"   Account 1110 (AR) found: {ar_id}")
            else:
                print("   ERROR: Account 1110 not found!")
                return

        except Exception as e:
            print(f"   ERROR: {e}")
            import traceback
            traceback.print_exc()
            return

        # 4. Test posting a sales invoice entry
        print("\n4. Creating Test Sales Invoice Entry...")
        try:
            test_invoice_id = uuid4()

            journal_entry = await accounting.post_sales_invoice(
                invoice_id=test_invoice_id,
                customer_name="Test Customer",
                subtotal=Decimal("10000.00"),
                cgst=Decimal("900.00"),
                sgst=Decimal("900.00"),
                igst=Decimal("0.00"),
                total=Decimal("11800.00"),
                is_interstate=False,
                product_type="purifier",
            )

            print(f"   Journal Entry created: {journal_entry.entry_number}")
            print(f"   Status: {journal_entry.status}")
            print(f"   Total Debit: {journal_entry.total_debit}")
            print(f"   Total Credit: {journal_entry.total_credit}")

            # Commit the transaction
            await db.commit()
            print("   Transaction committed!")

        except Exception as e:
            print(f"   ERROR: {e}")
            import traceback
            traceback.print_exc()
            await db.rollback()
            return

        # 5. Verify entries were created
        print("\n5. Verifying Created Entries...")

        # Check Journal Entry
        result = await db.execute(select(func.count(JournalEntry.id)))
        je_count = result.scalar()
        print(f"   Journal Entries: {je_count}")

        # Check Journal Entry Lines
        result = await db.execute(select(func.count(JournalEntryLine.id)))
        jel_count = result.scalar()
        print(f"   Journal Entry Lines: {jel_count}")

        # Check General Ledger
        result = await db.execute(select(func.count(GeneralLedger.id)))
        gl_count = result.scalar()
        print(f"   General Ledger Entries: {gl_count}")

        # 6. Check account balances
        print("\n6. Account Balances After Transaction...")
        result = await db.execute(
            select(ChartOfAccount).where(
                ChartOfAccount.current_balance != 0
            ).order_by(ChartOfAccount.account_code)
        )
        accounts = result.scalars().all()
        if accounts:
            for acc in accounts:
                print(f"   {acc.account_code}: {acc.account_name} = {acc.current_balance}")
        else:
            print("   No accounts with non-zero balance!")

    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_accounting())
