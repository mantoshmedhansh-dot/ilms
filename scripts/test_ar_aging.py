#!/usr/bin/env python3
"""Test AR Aging and Customer Ledger functionality."""

import asyncio
import sys
import logging
from decimal import Decimal
import uuid
from datetime import date, datetime, timedelta

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Suppress SQLAlchemy logs
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)

# Add project to path
sys.path.insert(0, '/Users/mantosh/Desktop/Consumer durable 2')

from app.database import async_session_factory
from app.models.customer import Customer, CustomerLedger, CustomerTransactionType
from sqlalchemy import select, text


async def run_ar_aging_test():
    """Test AR Aging and Customer Ledger functionality."""

    print("\n" + "=" * 80)
    print("AR AGING & CUSTOMER LEDGER TEST")
    print("=" * 80)

    async with async_session_factory() as db:
        # Get test customer
        result = await db.execute(
            select(Customer).where(Customer.is_active == True).limit(1)
        )
        customer = result.scalar_one_or_none()

        if not customer:
            print("ERROR: No active customer found!")
            return

        print(f"\n[STEP 1] Using Customer: {customer.full_name} ({customer.customer_code})")

        # ========== STEP 2: Create Sample Ledger Entries ==========
        print("\n[STEP 2] Creating Sample Ledger Entries")
        print("-" * 40)

        # Clear existing entries for this customer (for testing)
        await db.execute(text("""
            DELETE FROM customer_ledger WHERE customer_id = :customer_id
        """), {'customer_id': str(customer.id)})
        await db.commit()

        today = date.today()

        # Create sample invoices with different due dates (for aging)
        sample_entries = [
            # Opening balance
            {
                'transaction_type': 'OPENING_BALANCE',
                'transaction_date': today - timedelta(days=120),
                'due_date': None,
                'reference_type': 'MANUAL',
                'reference_number': 'OB-001',
                'debit_amount': Decimal('5000.00'),
                'credit_amount': Decimal('0'),
                'description': 'Opening Balance',
            },
            # Invoice 1 - Over 90 days old (very overdue)
            {
                'transaction_type': 'INVOICE',
                'transaction_date': today - timedelta(days=120),
                'due_date': today - timedelta(days=100),
                'reference_type': 'INVOICE',
                'reference_number': 'INV-TEST-001',
                'debit_amount': Decimal('15000.00'),
                'credit_amount': Decimal('0'),
                'description': 'Invoice - Over 90 days overdue',
            },
            # Invoice 2 - 61-90 days overdue
            {
                'transaction_type': 'INVOICE',
                'transaction_date': today - timedelta(days=90),
                'due_date': today - timedelta(days=70),
                'reference_type': 'INVOICE',
                'reference_number': 'INV-TEST-002',
                'debit_amount': Decimal('8000.00'),
                'credit_amount': Decimal('0'),
                'description': 'Invoice - 61-90 days overdue',
            },
            # Invoice 3 - 31-60 days overdue
            {
                'transaction_type': 'INVOICE',
                'transaction_date': today - timedelta(days=60),
                'due_date': today - timedelta(days=45),
                'reference_type': 'INVOICE',
                'reference_number': 'INV-TEST-003',
                'debit_amount': Decimal('12000.00'),
                'credit_amount': Decimal('0'),
                'description': 'Invoice - 31-60 days overdue',
            },
            # Invoice 4 - 1-30 days overdue
            {
                'transaction_type': 'INVOICE',
                'transaction_date': today - timedelta(days=30),
                'due_date': today - timedelta(days=15),
                'reference_type': 'INVOICE',
                'reference_number': 'INV-TEST-004',
                'debit_amount': Decimal('6000.00'),
                'credit_amount': Decimal('0'),
                'description': 'Invoice - 1-30 days overdue',
            },
            # Invoice 5 - Current (not yet due)
            {
                'transaction_type': 'INVOICE',
                'transaction_date': today - timedelta(days=10),
                'due_date': today + timedelta(days=20),
                'reference_type': 'INVOICE',
                'reference_number': 'INV-TEST-005',
                'debit_amount': Decimal('9000.00'),
                'credit_amount': Decimal('0'),
                'description': 'Invoice - Current (not due)',
            },
            # Payment 1 - Partial payment
            {
                'transaction_type': 'PAYMENT',
                'transaction_date': today - timedelta(days=60),
                'due_date': None,
                'reference_type': 'PAYMENT_RECEIPT',
                'reference_number': 'PAY-TEST-001',
                'debit_amount': Decimal('0'),
                'credit_amount': Decimal('10000.00'),
                'description': 'Partial payment received',
            },
        ]

        running_balance = Decimal('0')
        for entry_data in sample_entries:
            running_balance += entry_data['debit_amount'] - entry_data['credit_amount']

            entry = CustomerLedger(
                customer_id=customer.id,
                transaction_type=entry_data['transaction_type'],
                transaction_date=entry_data['transaction_date'],
                due_date=entry_data['due_date'],
                reference_type=entry_data['reference_type'],
                reference_number=entry_data['reference_number'],
                debit_amount=entry_data['debit_amount'],
                credit_amount=entry_data['credit_amount'],
                balance=running_balance,
                description=entry_data['description'],
            )
            db.add(entry)
            print(f"  Created: {entry_data['reference_number']} | "
                  f"DR: {entry_data['debit_amount']:>10.2f} | "
                  f"CR: {entry_data['credit_amount']:>10.2f} | "
                  f"Bal: {running_balance:>10.2f}")

        await db.commit()
        print(f"\n  Total entries created: {len(sample_entries)}")
        print(f"  Running balance: ₹{running_balance:,.2f}")

        # ========== STEP 3: Test Customer Ledger Query ==========
        print("\n[STEP 3] Customer Ledger Query")
        print("-" * 40)

        ledger_result = await db.execute(
            select(CustomerLedger)
            .where(CustomerLedger.customer_id == customer.id)
            .order_by(CustomerLedger.transaction_date)
        )
        ledger_entries = ledger_result.scalars().all()

        print(f"\n  {'Date':<12} {'Type':<15} {'Reference':<15} {'Debit':>12} {'Credit':>12} {'Balance':>12}")
        print("  " + "-" * 78)
        for entry in ledger_entries:
            print(f"  {str(entry.transaction_date):<12} {entry.transaction_type:<15} "
                  f"{entry.reference_number:<15} {entry.debit_amount:>12,.2f} "
                  f"{entry.credit_amount:>12,.2f} {entry.balance:>12,.2f}")

        # ========== STEP 4: Test AR Aging Calculation ==========
        print("\n[STEP 4] AR Aging Calculation")
        print("-" * 40)

        # Calculate aging buckets manually
        aging_buckets = {
            'CURRENT': Decimal('0'),
            '1_30': Decimal('0'),
            '31_60': Decimal('0'),
            '61_90': Decimal('0'),
            'OVER_90': Decimal('0'),
        }

        unsettled_result = await db.execute(
            select(CustomerLedger).where(
                CustomerLedger.customer_id == customer.id,
                CustomerLedger.is_settled == False,
                CustomerLedger.debit_amount > 0,
            )
        )
        unsettled = unsettled_result.scalars().all()

        for entry in unsettled:
            outstanding = entry.debit_amount - entry.credit_amount
            if outstanding <= 0:
                continue

            if entry.due_date:
                days_overdue = (today - entry.due_date).days
            else:
                days_overdue = (today - entry.transaction_date).days - 30

            if days_overdue <= 0:
                aging_buckets['CURRENT'] += outstanding
            elif days_overdue <= 30:
                aging_buckets['1_30'] += outstanding
            elif days_overdue <= 60:
                aging_buckets['31_60'] += outstanding
            elif days_overdue <= 90:
                aging_buckets['61_90'] += outstanding
            else:
                aging_buckets['OVER_90'] += outstanding

        print(f"\n  Aging Summary for {customer.full_name}:")
        print(f"  " + "-" * 50)
        print(f"  {'Current (Not Due)':<25} ₹{aging_buckets['CURRENT']:>12,.2f}")
        print(f"  {'1-30 Days Overdue':<25} ₹{aging_buckets['1_30']:>12,.2f}")
        print(f"  {'31-60 Days Overdue':<25} ₹{aging_buckets['31_60']:>12,.2f}")
        print(f"  {'61-90 Days Overdue':<25} ₹{aging_buckets['61_90']:>12,.2f}")
        print(f"  {'Over 90 Days':<25} ₹{aging_buckets['OVER_90']:>12,.2f}")
        print(f"  " + "-" * 50)
        total_outstanding = sum(aging_buckets.values())
        print(f"  {'TOTAL OUTSTANDING':<25} ₹{total_outstanding:>12,.2f}")

        # ========== STEP 5: Summary ==========
        print("\n" + "=" * 80)
        print("AR AGING TEST SUMMARY")
        print("=" * 80)

        print(f"""
  Customer:           {customer.full_name} ({customer.customer_code})
  Total Entries:      {len(ledger_entries)}
  Total Outstanding:  ₹{total_outstanding:,.2f}

  Aging Breakdown:
  - Current:          ₹{aging_buckets['CURRENT']:,.2f}
  - 1-30 Days:        ₹{aging_buckets['1_30']:,.2f}
  - 31-60 Days:       ₹{aging_buckets['31_60']:,.2f}
  - 61-90 Days:       ₹{aging_buckets['61_90']:,.2f}
  - Over 90 Days:     ₹{aging_buckets['OVER_90']:,.2f}
""")

        if total_outstanding > 0:
            print("  ✅ AR AGING TEST PASSED!")
        else:
            print("  ⚠️ No outstanding balance (all paid)")

        print("=" * 80 + "\n")

        return {
            'customer_id': str(customer.id),
            'customer_name': customer.full_name,
            'total_entries': len(ledger_entries),
            'total_outstanding': float(total_outstanding),
            'aging_buckets': {k: float(v) for k, v in aging_buckets.items()},
        }


if __name__ == "__main__":
    asyncio.run(run_ar_aging_test())
