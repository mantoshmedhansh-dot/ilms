"""Seed Chart of Accounts, Financial Periods, and Cost Centers for complete financial orchestration."""
import asyncio
import sys
sys.path.insert(0, '/Users/mantosh/Consumer durable')

from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_factory
from app.models.accounting import (
    ChartOfAccount, AccountType, AccountSubType,
    FinancialPeriod, FinancialPeriodStatus,
    CostCenter,
)
from app.models import User, Role, RoleLevel
from app.core.security import get_password_hash

# System user ID for automated accounting entries
SYSTEM_USER_ID = "00000000-0000-0000-0000-000000000001"


# Standard Chart of Accounts for Consumer Durables Business
CHART_OF_ACCOUNTS = [
    # ==================== ASSETS ====================
    # Current Assets
    {"code": "1000", "name": "Current Assets", "type": AccountType.ASSET, "sub_type": AccountSubType.CURRENT_ASSET, "is_group": True},
    {"code": "1010", "name": "Cash on Hand", "type": AccountType.ASSET, "sub_type": AccountSubType.CASH, "parent_code": "1000"},
    {"code": "1020", "name": "Cash at Bank - HDFC", "type": AccountType.ASSET, "sub_type": AccountSubType.BANK, "parent_code": "1000", "is_bank_account": True, "bank_name": "HDFC Bank"},
    {"code": "1021", "name": "Cash at Bank - ICICI", "type": AccountType.ASSET, "sub_type": AccountSubType.BANK, "parent_code": "1000", "is_bank_account": True, "bank_name": "ICICI Bank"},
    {"code": "1100", "name": "Accounts Receivable", "type": AccountType.ASSET, "sub_type": AccountSubType.ACCOUNTS_RECEIVABLE, "parent_code": "1000"},
    {"code": "1110", "name": "Trade Receivables - Customers", "type": AccountType.ASSET, "sub_type": AccountSubType.ACCOUNTS_RECEIVABLE, "parent_code": "1100"},
    {"code": "1120", "name": "Trade Receivables - Dealers", "type": AccountType.ASSET, "sub_type": AccountSubType.ACCOUNTS_RECEIVABLE, "parent_code": "1100"},
    {"code": "1200", "name": "Inventory", "type": AccountType.ASSET, "sub_type": AccountSubType.INVENTORY, "parent_code": "1000"},
    {"code": "1210", "name": "Finished Goods - Water Purifiers", "type": AccountType.ASSET, "sub_type": AccountSubType.INVENTORY, "parent_code": "1200"},
    {"code": "1220", "name": "Spare Parts Inventory", "type": AccountType.ASSET, "sub_type": AccountSubType.INVENTORY, "parent_code": "1200"},
    {"code": "1230", "name": "Goods in Transit", "type": AccountType.ASSET, "sub_type": AccountSubType.INVENTORY, "parent_code": "1200"},
    {"code": "1300", "name": "Prepaid Expenses", "type": AccountType.ASSET, "sub_type": AccountSubType.CURRENT_ASSET, "parent_code": "1000"},
    {"code": "1400", "name": "GST Input Credit", "type": AccountType.ASSET, "sub_type": AccountSubType.CURRENT_ASSET, "parent_code": "1000"},
    {"code": "1410", "name": "CGST Input Credit", "type": AccountType.ASSET, "sub_type": AccountSubType.CURRENT_ASSET, "parent_code": "1400", "gst_type": "CGST"},
    {"code": "1420", "name": "SGST Input Credit", "type": AccountType.ASSET, "sub_type": AccountSubType.CURRENT_ASSET, "parent_code": "1400", "gst_type": "SGST"},
    {"code": "1430", "name": "IGST Input Credit", "type": AccountType.ASSET, "sub_type": AccountSubType.CURRENT_ASSET, "parent_code": "1400", "gst_type": "IGST"},

    # Fixed Assets
    {"code": "1500", "name": "Fixed Assets", "type": AccountType.ASSET, "sub_type": AccountSubType.FIXED_ASSET, "is_group": True},
    {"code": "1510", "name": "Land & Building", "type": AccountType.ASSET, "sub_type": AccountSubType.FIXED_ASSET, "parent_code": "1500"},
    {"code": "1520", "name": "Plant & Machinery", "type": AccountType.ASSET, "sub_type": AccountSubType.FIXED_ASSET, "parent_code": "1500"},
    {"code": "1530", "name": "Furniture & Fixtures", "type": AccountType.ASSET, "sub_type": AccountSubType.FIXED_ASSET, "parent_code": "1500"},
    {"code": "1540", "name": "Vehicles", "type": AccountType.ASSET, "sub_type": AccountSubType.FIXED_ASSET, "parent_code": "1500"},
    {"code": "1550", "name": "Computer & IT Equipment", "type": AccountType.ASSET, "sub_type": AccountSubType.FIXED_ASSET, "parent_code": "1500"},
    {"code": "1600", "name": "Accumulated Depreciation", "type": AccountType.ASSET, "sub_type": AccountSubType.FIXED_ASSET, "parent_code": "1500"},

    # ==================== LIABILITIES ====================
    # Current Liabilities
    {"code": "2000", "name": "Current Liabilities", "type": AccountType.LIABILITY, "sub_type": AccountSubType.CURRENT_LIABILITY, "is_group": True},
    {"code": "2100", "name": "Accounts Payable", "type": AccountType.LIABILITY, "sub_type": AccountSubType.ACCOUNTS_PAYABLE, "parent_code": "2000"},
    {"code": "2110", "name": "Trade Payables - Vendors", "type": AccountType.LIABILITY, "sub_type": AccountSubType.ACCOUNTS_PAYABLE, "parent_code": "2100"},
    {"code": "2120", "name": "Trade Payables - Service Providers", "type": AccountType.LIABILITY, "sub_type": AccountSubType.ACCOUNTS_PAYABLE, "parent_code": "2100"},
    {"code": "2200", "name": "GST Output Liability", "type": AccountType.LIABILITY, "sub_type": AccountSubType.TAX_PAYABLE, "parent_code": "2000"},
    {"code": "2210", "name": "CGST Output Liability", "type": AccountType.LIABILITY, "sub_type": AccountSubType.TAX_PAYABLE, "parent_code": "2200", "gst_type": "CGST"},
    {"code": "2220", "name": "SGST Output Liability", "type": AccountType.LIABILITY, "sub_type": AccountSubType.TAX_PAYABLE, "parent_code": "2200", "gst_type": "SGST"},
    {"code": "2230", "name": "IGST Output Liability", "type": AccountType.LIABILITY, "sub_type": AccountSubType.TAX_PAYABLE, "parent_code": "2200", "gst_type": "IGST"},
    {"code": "2300", "name": "TDS Payable", "type": AccountType.LIABILITY, "sub_type": AccountSubType.TAX_PAYABLE, "parent_code": "2000"},
    {"code": "2400", "name": "Salary Payable", "type": AccountType.LIABILITY, "sub_type": AccountSubType.CURRENT_LIABILITY, "parent_code": "2000"},
    {"code": "2500", "name": "Advance from Customers", "type": AccountType.LIABILITY, "sub_type": AccountSubType.CURRENT_LIABILITY, "parent_code": "2000"},
    {"code": "2600", "name": "Provisions", "type": AccountType.LIABILITY, "sub_type": AccountSubType.CURRENT_LIABILITY, "parent_code": "2000"},
    {"code": "2610", "name": "Provision for Warranty", "type": AccountType.LIABILITY, "sub_type": AccountSubType.CURRENT_LIABILITY, "parent_code": "2600"},
    {"code": "2620", "name": "Provision for Expenses", "type": AccountType.LIABILITY, "sub_type": AccountSubType.CURRENT_LIABILITY, "parent_code": "2600"},

    # Long-term Liabilities
    {"code": "2700", "name": "Long-term Liabilities", "type": AccountType.LIABILITY, "sub_type": AccountSubType.LONG_TERM_LIABILITY, "is_group": True},
    {"code": "2710", "name": "Term Loans", "type": AccountType.LIABILITY, "sub_type": AccountSubType.LONG_TERM_LIABILITY, "parent_code": "2700"},

    # ==================== EQUITY ====================
    {"code": "3000", "name": "Equity", "type": AccountType.EQUITY, "sub_type": AccountSubType.SHARE_CAPITAL, "is_group": True},
    {"code": "3100", "name": "Share Capital", "type": AccountType.EQUITY, "sub_type": AccountSubType.SHARE_CAPITAL, "parent_code": "3000"},
    {"code": "3200", "name": "Retained Earnings", "type": AccountType.EQUITY, "sub_type": AccountSubType.RETAINED_EARNINGS, "parent_code": "3000", "is_system": True},
    {"code": "3300", "name": "Current Year Profit/Loss", "type": AccountType.EQUITY, "sub_type": AccountSubType.RETAINED_EARNINGS, "parent_code": "3000", "is_system": True},

    # ==================== REVENUE ====================
    {"code": "4000", "name": "Revenue", "type": AccountType.REVENUE, "sub_type": AccountSubType.SALES_REVENUE, "is_group": True},
    {"code": "4100", "name": "Sales Revenue", "type": AccountType.REVENUE, "sub_type": AccountSubType.SALES_REVENUE, "parent_code": "4000"},
    {"code": "4110", "name": "Sales - Water Purifiers", "type": AccountType.REVENUE, "sub_type": AccountSubType.SALES_REVENUE, "parent_code": "4100"},
    {"code": "4120", "name": "Sales - Spare Parts", "type": AccountType.REVENUE, "sub_type": AccountSubType.SALES_REVENUE, "parent_code": "4100"},
    {"code": "4130", "name": "Sales - Accessories", "type": AccountType.REVENUE, "sub_type": AccountSubType.SALES_REVENUE, "parent_code": "4100"},
    {"code": "4200", "name": "Service Revenue", "type": AccountType.REVENUE, "sub_type": AccountSubType.SERVICE_REVENUE, "parent_code": "4000"},
    {"code": "4210", "name": "Installation Revenue", "type": AccountType.REVENUE, "sub_type": AccountSubType.SERVICE_REVENUE, "parent_code": "4200"},
    {"code": "4220", "name": "AMC Revenue", "type": AccountType.REVENUE, "sub_type": AccountSubType.SERVICE_REVENUE, "parent_code": "4200"},
    {"code": "4230", "name": "Service Call Revenue", "type": AccountType.REVENUE, "sub_type": AccountSubType.SERVICE_REVENUE, "parent_code": "4200"},
    {"code": "4300", "name": "Other Income", "type": AccountType.REVENUE, "sub_type": AccountSubType.OTHER_INCOME, "parent_code": "4000"},
    {"code": "4310", "name": "Interest Income", "type": AccountType.REVENUE, "sub_type": AccountSubType.OTHER_INCOME, "parent_code": "4300"},
    {"code": "4320", "name": "Discount Received", "type": AccountType.REVENUE, "sub_type": AccountSubType.OTHER_INCOME, "parent_code": "4300"},
    {"code": "4400", "name": "Sales Returns", "type": AccountType.REVENUE, "sub_type": AccountSubType.SALES_REVENUE, "parent_code": "4000"},
    {"code": "4500", "name": "Sales Discount", "type": AccountType.REVENUE, "sub_type": AccountSubType.SALES_REVENUE, "parent_code": "4000"},

    # ==================== EXPENSES ====================
    {"code": "5000", "name": "Cost of Goods Sold", "type": AccountType.EXPENSE, "sub_type": AccountSubType.COST_OF_GOODS, "is_group": True},
    {"code": "5100", "name": "COGS - Water Purifiers", "type": AccountType.EXPENSE, "sub_type": AccountSubType.COST_OF_GOODS, "parent_code": "5000"},
    {"code": "5200", "name": "COGS - Spare Parts", "type": AccountType.EXPENSE, "sub_type": AccountSubType.COST_OF_GOODS, "parent_code": "5000"},
    {"code": "5300", "name": "Freight Inward", "type": AccountType.EXPENSE, "sub_type": AccountSubType.COST_OF_GOODS, "parent_code": "5000"},
    {"code": "5400", "name": "Purchase Returns", "type": AccountType.EXPENSE, "sub_type": AccountSubType.COST_OF_GOODS, "parent_code": "5000"},

    {"code": "6000", "name": "Operating Expenses", "type": AccountType.EXPENSE, "sub_type": AccountSubType.OPERATING_EXPENSE, "is_group": True},
    {"code": "6100", "name": "Salaries & Wages", "type": AccountType.EXPENSE, "sub_type": AccountSubType.OPERATING_EXPENSE, "parent_code": "6000"},
    {"code": "6110", "name": "Salaries - Management", "type": AccountType.EXPENSE, "sub_type": AccountSubType.OPERATING_EXPENSE, "parent_code": "6100"},
    {"code": "6120", "name": "Salaries - Sales Team", "type": AccountType.EXPENSE, "sub_type": AccountSubType.OPERATING_EXPENSE, "parent_code": "6100"},
    {"code": "6130", "name": "Salaries - Service Team", "type": AccountType.EXPENSE, "sub_type": AccountSubType.OPERATING_EXPENSE, "parent_code": "6100"},
    {"code": "6140", "name": "Commission to Technicians", "type": AccountType.EXPENSE, "sub_type": AccountSubType.OPERATING_EXPENSE, "parent_code": "6100"},
    {"code": "6200", "name": "Rent & Utilities", "type": AccountType.EXPENSE, "sub_type": AccountSubType.OPERATING_EXPENSE, "parent_code": "6000"},
    {"code": "6210", "name": "Office Rent", "type": AccountType.EXPENSE, "sub_type": AccountSubType.OPERATING_EXPENSE, "parent_code": "6200"},
    {"code": "6220", "name": "Warehouse Rent", "type": AccountType.EXPENSE, "sub_type": AccountSubType.OPERATING_EXPENSE, "parent_code": "6200"},
    {"code": "6230", "name": "Electricity Charges", "type": AccountType.EXPENSE, "sub_type": AccountSubType.OPERATING_EXPENSE, "parent_code": "6200"},
    {"code": "6300", "name": "Marketing & Advertising", "type": AccountType.EXPENSE, "sub_type": AccountSubType.OPERATING_EXPENSE, "parent_code": "6000"},
    {"code": "6400", "name": "Logistics & Freight", "type": AccountType.EXPENSE, "sub_type": AccountSubType.OPERATING_EXPENSE, "parent_code": "6000"},
    {"code": "6410", "name": "Freight Outward", "type": AccountType.EXPENSE, "sub_type": AccountSubType.OPERATING_EXPENSE, "parent_code": "6400"},
    {"code": "6420", "name": "Courier Charges", "type": AccountType.EXPENSE, "sub_type": AccountSubType.OPERATING_EXPENSE, "parent_code": "6400"},
    {"code": "6500", "name": "Depreciation", "type": AccountType.EXPENSE, "sub_type": AccountSubType.OPERATING_EXPENSE, "parent_code": "6000"},
    {"code": "6600", "name": "Warranty Expenses", "type": AccountType.EXPENSE, "sub_type": AccountSubType.OPERATING_EXPENSE, "parent_code": "6000"},
    {"code": "6700", "name": "Bad Debts", "type": AccountType.EXPENSE, "sub_type": AccountSubType.OPERATING_EXPENSE, "parent_code": "6000"},
    {"code": "6800", "name": "Bank Charges", "type": AccountType.EXPENSE, "sub_type": AccountSubType.OPERATING_EXPENSE, "parent_code": "6000"},
    {"code": "6900", "name": "Miscellaneous Expenses", "type": AccountType.EXPENSE, "sub_type": AccountSubType.OPERATING_EXPENSE, "parent_code": "6000"},

    # Non-Operating Expenses (using OPERATING_EXPENSE as closest match)
    {"code": "7000", "name": "Non-Operating Expenses", "type": AccountType.EXPENSE, "sub_type": AccountSubType.OPERATING_EXPENSE, "is_group": True},
    {"code": "7100", "name": "Interest Expense", "type": AccountType.EXPENSE, "sub_type": AccountSubType.OPERATING_EXPENSE, "parent_code": "7000"},
    {"code": "7200", "name": "Loss on Sale of Assets", "type": AccountType.EXPENSE, "sub_type": AccountSubType.OPERATING_EXPENSE, "parent_code": "7000"},
]


async def seed_system_user(db: AsyncSession):
    """Seed system user for automated entries."""
    print("\n" + "=" * 60)
    print("SEEDING SYSTEM USER")
    print("=" * 60)

    from uuid import UUID

    # Check if system user exists
    result = await db.execute(
        select(User).where(User.id == UUID(SYSTEM_USER_ID))
    )
    existing = result.scalar_one_or_none()

    if existing:
        print(f"System user already exists (ID: {existing.id}). Skipping...")
        return existing.id

    # Get or create system role
    result = await db.execute(select(Role).where(Role.code == "SYSTEM"))
    system_role = result.scalar_one_or_none()

    if not system_role:
        system_role = Role(
            id=uuid4(),
            name="System",
            code="SYSTEM",
            level=RoleLevel.SUPER_ADMIN,
            description="System role for automated processes",
            is_system=True,
            is_active=True,
        )
        db.add(system_role)
        await db.flush()
        print("  + Created SYSTEM role")

    # Create system user with the specific ID from SYSTEM_USER_ID constant
    from uuid import UUID
    from app.models.user import UserRole

    system_user = User(
        id=UUID(SYSTEM_USER_ID),
        first_name="System",
        last_name="Account",
        phone="0000000000",
        email="system@internal.local",
        password_hash=get_password_hash("system-internal-only"),
        is_active=True,
        is_verified=True,
    )
    db.add(system_user)
    await db.flush()

    # Assign system role to user
    user_role = UserRole(
        id=uuid4(),
        user_id=system_user.id,
        role_id=system_role.id,
    )
    db.add(user_role)
    await db.flush()

    print(f"  + Created system user (ID: {system_user.id})")

    return system_user.id


async def seed_chart_of_accounts(db: AsyncSession):
    """Seed Chart of Accounts."""
    print("\n" + "=" * 60)
    print("SEEDING CHART OF ACCOUNTS")
    print("=" * 60)

    # Check if already seeded
    result = await db.execute(select(ChartOfAccount))
    existing = result.scalars().first()
    if existing:
        print("Chart of Accounts already exists. Skipping...")
        return

    # Create accounts in order (parents first)
    account_map = {}

    for acc_data in CHART_OF_ACCOUNTS:
        parent_id = None
        if "parent_code" in acc_data:
            parent_id = account_map.get(acc_data["parent_code"])

        account = ChartOfAccount(
            id=uuid4(),
            account_code=acc_data["code"],
            account_name=acc_data["name"],
            account_type=acc_data["type"],
            account_sub_type=acc_data["sub_type"],
            parent_id=parent_id,
            is_group=acc_data.get("is_group", False),
            is_system=acc_data.get("is_system", False),
            bank_name=acc_data.get("bank_name"),
            gst_type=acc_data.get("gst_type"),
            allow_direct_posting=not acc_data.get("is_group", False),
            opening_balance=Decimal("0"),
            current_balance=Decimal("0"),
            is_active=True,
        )
        db.add(account)
        account_map[acc_data["code"]] = account.id
        print(f"  + {acc_data['code']}: {acc_data['name']}")

    await db.flush()
    print(f"\nTotal Accounts Created: {len(CHART_OF_ACCOUNTS)}")


async def seed_financial_periods(db: AsyncSession):
    """Seed Financial Periods for FY 2025-26."""
    print("\n" + "=" * 60)
    print("SEEDING FINANCIAL PERIODS")
    print("=" * 60)

    # Check if already seeded
    result = await db.execute(select(FinancialPeriod))
    existing = result.scalars().first()
    if existing:
        print("Financial Periods already exist. Skipping...")
        return

    # Financial Year 2025-26 (April 2025 to March 2026)
    fy_id = uuid4()
    fy = FinancialPeriod(
        id=fy_id,
        period_name="FY 2025-26",
        period_type="YEAR",
        start_date=date(2025, 4, 1),
        end_date=date(2026, 3, 31),
        status=FinancialPeriodStatus.OPEN,
        is_current=True,
        is_adjustment_period=False,
    )
    db.add(fy)
    print(f"  + FY 2025-26 (Apr 2025 - Mar 2026)")

    # Monthly Periods
    months = [
        ("April 2025", date(2025, 4, 1), date(2025, 4, 30)),
        ("May 2025", date(2025, 5, 1), date(2025, 5, 31)),
        ("June 2025", date(2025, 6, 1), date(2025, 6, 30)),
        ("July 2025", date(2025, 7, 1), date(2025, 7, 31)),
        ("August 2025", date(2025, 8, 1), date(2025, 8, 31)),
        ("September 2025", date(2025, 9, 1), date(2025, 9, 30)),
        ("October 2025", date(2025, 10, 1), date(2025, 10, 31)),
        ("November 2025", date(2025, 11, 1), date(2025, 11, 30)),
        ("December 2025", date(2025, 12, 1), date(2025, 12, 31)),
        ("January 2026", date(2026, 1, 1), date(2026, 1, 31)),
        ("February 2026", date(2026, 2, 1), date(2026, 2, 28)),
        ("March 2026", date(2026, 3, 1), date(2026, 3, 31)),
    ]

    for name, start, end in months:
        # Current period (January 2026) is OPEN, past months are CLOSED
        is_current = start <= date.today() <= end
        status = FinancialPeriodStatus.OPEN if is_current else (
            FinancialPeriodStatus.CLOSED if end < date.today() else FinancialPeriodStatus.OPEN
        )

        period = FinancialPeriod(
            id=uuid4(),
            period_name=name,
            period_type="MONTH",
            start_date=start,
            end_date=end,
            status=status,
            is_current=is_current,
            is_adjustment_period=False,
        )
        db.add(period)
        print(f"  + {name} ({start} to {end}) - {status.value} {'(CURRENT)' if is_current else ''}")

    await db.flush()
    print(f"\nTotal Periods Created: 13 (1 Year + 12 Months)")


async def seed_cost_centers(db: AsyncSession):
    """Seed Cost Centers."""
    print("\n" + "=" * 60)
    print("SEEDING COST CENTERS")
    print("=" * 60)

    # Check if already seeded
    result = await db.execute(select(CostCenter))
    existing = result.scalars().first()
    if existing:
        print("Cost Centers already exist. Skipping...")
        return

    cost_centers = [
        {"code": "HQ", "name": "Head Office", "type": "DEPARTMENT"},
        {"code": "SALES", "name": "Sales Department", "type": "DEPARTMENT", "parent_code": "HQ"},
        {"code": "SERVICE", "name": "Service Department", "type": "DEPARTMENT", "parent_code": "HQ"},
        {"code": "WAREHOUSE", "name": "Warehouse Operations", "type": "DEPARTMENT", "parent_code": "HQ"},
        {"code": "ADMIN", "name": "Administration", "type": "DEPARTMENT", "parent_code": "HQ"},
        {"code": "WH-DEL", "name": "Delhi Warehouse", "type": "LOCATION"},
        {"code": "WH-MUM", "name": "Mumbai Warehouse", "type": "LOCATION"},
        {"code": "WH-BLR", "name": "Bangalore Warehouse", "type": "LOCATION"},
    ]

    cc_map = {}
    for cc_data in cost_centers:
        parent_id = None
        if "parent_code" in cc_data:
            parent_id = cc_map.get(cc_data["parent_code"])

        cc = CostCenter(
            id=uuid4(),
            code=cc_data["code"],
            name=cc_data["name"],
            cost_center_type=cc_data["type"],
            parent_id=parent_id,
            is_active=True,
        )
        db.add(cc)
        cc_map[cc_data["code"]] = cc.id
        print(f"  + {cc_data['code']}: {cc_data['name']}")

    await db.flush()
    print(f"\nTotal Cost Centers Created: {len(cost_centers)}")


async def main():
    """Main seed function."""
    print("\n" + "=" * 60)
    print("ACCOUNTING SEED SCRIPT")
    print("=" * 60)
    print(f"Started at: {datetime.now()}")

    async with async_session_factory() as db:
        try:
            await seed_system_user(db)
            await seed_chart_of_accounts(db)
            await seed_financial_periods(db)
            await seed_cost_centers(db)

            await db.commit()
            print("\n" + "=" * 60)
            print("ACCOUNTING SEED COMPLETED SUCCESSFULLY!")
            print("=" * 60)

        except Exception as e:
            await db.rollback()
            print(f"\nERROR: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(main())
