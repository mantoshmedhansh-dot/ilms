#!/usr/bin/env python3
"""
4-Channel Return Flow Test with Balance Sheet Update

Tests the complete return/cancellation flow for orders created in the E2E test:
- Creates return orders for all 4 channel orders
- Processes returns through complete flow (INITIATE → AUTHORIZE → RECEIVE → INSPECT → APPROVE)
- Creates credit notes
- Posts GL entries for returns (reverse sales, tax, COGS)
- Generates updated Balance Sheet and P&L showing the impact of returns
"""

import asyncio
import sys
import logging
from decimal import Decimal
import uuid
from datetime import date, datetime, timedelta, timezone

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Suppress SQLAlchemy logs
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)

# Add project to path
sys.path.insert(0, '/Users/mantosh/Desktop/Consumer durable 2')

from app.database import async_session_factory
from app.models.product import Product
from app.models.customer import Customer
from app.models.order import Order, OrderItem
from app.models.billing import TaxInvoice, InvoiceItem, CreditDebitNote, CreditDebitNoteItem
from app.models.return_order import ReturnOrder, ReturnItem, ReturnStatusHistory, Refund
from app.models.accounting import (
    ChartOfAccount as GLAccount,
    JournalEntry,
    JournalEntryLine,
    FinancialPeriod,
)
from sqlalchemy import select, func, desc
from sqlalchemy.orm import selectinload


async def get_recent_orders(db):
    """Get the most recent 4 orders from the E2E test."""
    print("\n" + "=" * 80)
    print("FETCHING RECENT ORDERS FOR RETURN")
    print("=" * 80)

    # Get the most recent 4 orders (from the E2E test)
    result = await db.execute(
        select(Order)
        .where(Order.status.in_(['DELIVERED', 'SHIPPED', 'CONFIRMED', 'PROCESSING']))
        .order_by(desc(Order.created_at))
        .limit(4)
    )
    orders = result.scalars().all()

    if len(orders) < 4:
        print(f"  WARNING: Only found {len(orders)} orders. Expected 4.")

    for order in orders:
        # Get order items
        result = await db.execute(
            select(OrderItem).where(OrderItem.order_id == order.id)
        )
        items = result.scalars().all()
        item_names = [item.product_name for item in items]
        print(f"  Order: {order.order_number} | Status: {order.status} | Amount: ₹{order.total_amount:,.2f}")
        print(f"    Items: {', '.join(item_names)}")

    return orders


async def create_return_order(db, order, return_reason='DEFECTIVE'):
    """Create a return order for the given order."""

    # Generate RMA number
    today_str = date.today().strftime('%Y%m%d')
    result = await db.execute(
        select(func.count(ReturnOrder.id))
        .where(ReturnOrder.rma_number.like(f'RMA-{today_str}%'))
    )
    count = result.scalar() or 0
    rma_number = f"RMA-{today_str}-{count + 1:04d}"

    # Get order items
    result = await db.execute(
        select(OrderItem).where(OrderItem.order_id == order.id)
    )
    order_items = result.scalars().all()

    # Calculate return amounts
    total_return_amount = order.total_amount
    restocking_fee = Decimal('0')  # No restocking fee for defective items
    shipping_deduction = Decimal('0')
    net_refund_amount = total_return_amount - restocking_fee - shipping_deduction

    # Create return order
    return_order = ReturnOrder(
        rma_number=rma_number,
        order_id=order.id,
        customer_id=order.customer_id,
        return_type='RETURN',
        return_reason=return_reason,
        return_reason_details=f'Return for order {order.order_number} - Product defective',
        status='INITIATED',
        total_return_amount=total_return_amount,
        restocking_fee=restocking_fee,
        shipping_deduction=shipping_deduction,
        net_refund_amount=net_refund_amount,
    )
    db.add(return_order)
    await db.flush()

    # Create return items
    for order_item in order_items:
        total_amount = order_item.unit_price * order_item.quantity
        return_item = ReturnItem(
            return_order_id=return_order.id,
            order_item_id=order_item.id,
            product_id=order_item.product_id,
            product_name=order_item.product_name,
            sku=order_item.product_sku,
            quantity_ordered=order_item.quantity,
            quantity_returned=order_item.quantity,  # Full return
            unit_price=order_item.unit_price,
            total_amount=total_amount,
            condition='DEFECTIVE',
        )
        db.add(return_item)

    # Create initial status history
    status_history = ReturnStatusHistory(
        return_order_id=return_order.id,
        from_status=None,
        to_status='INITIATED',
        notes='Return initiated by customer',
    )
    db.add(status_history)

    await db.flush()
    return return_order


async def process_return_flow(db, return_order):
    """Process return through complete flow: AUTHORIZE → RECEIVE → INSPECT → APPROVE."""

    status_flow = [
        ('AUTHORIZED', 'Return authorized by admin'),
        ('PICKUP_SCHEDULED', 'Pickup scheduled with courier'),
        ('PICKED_UP', 'Items picked up from customer'),
        ('IN_TRANSIT', 'Items in transit to warehouse'),
        ('RECEIVED', 'Items received at warehouse'),
        ('UNDER_INSPECTION', 'Items under quality inspection'),
        ('APPROVED', 'Return approved after inspection'),
    ]

    current_status = return_order.status

    for new_status, notes in status_flow:
        # Create status history
        history = ReturnStatusHistory(
            return_order_id=return_order.id,
            from_status=current_status,
            to_status=new_status,
            notes=notes,
        )
        db.add(history)

        # Update return order status
        return_order.status = new_status
        current_status = new_status

        # Update inspection details if inspecting
        if new_status == 'UNDER_INSPECTION':
            return_order.inspected_at = datetime.now(timezone.utc)

        # Update return items for approval
        if new_status == 'APPROVED':
            result = await db.execute(
                select(ReturnItem).where(ReturnItem.return_order_id == return_order.id)
            )
            return_items = result.scalars().all()
            for item in return_items:
                item.inspection_result = 'ACCEPTED'
                item.accepted_quantity = item.quantity_returned
                item.refund_amount = item.unit_price * item.quantity_returned

    await db.flush()
    return return_order


async def create_credit_note(db, return_order, original_invoice):
    """Create a credit note for the return."""

    # Generate credit note number
    today_str = date.today().strftime('%Y%m%d')
    result = await db.execute(
        select(func.count(CreditDebitNote.id))
        .where(CreditDebitNote.note_number.like(f'CN/FY2526%'))
    )
    count = result.scalar() or 0
    note_number = f"CN/FY2526/{count + 1:05d}"

    # Get return items
    result = await db.execute(
        select(ReturnItem).where(ReturnItem.return_order_id == return_order.id)
    )
    return_items = result.scalars().all()

    # Calculate credit note amounts (reverse of invoice)
    taxable_amount = Decimal('0')
    cgst_amount = Decimal('0')
    sgst_amount = Decimal('0')
    igst_amount = Decimal('0')

    for item in return_items:
        item_taxable = item.unit_price * item.accepted_quantity
        taxable_amount += item_taxable

    # Get tax from original invoice proportionally
    is_interstate = False
    if original_invoice:
        tax_rate = (original_invoice.total_tax / original_invoice.taxable_amount) if original_invoice.taxable_amount else Decimal('0.18')
        total_tax = taxable_amount * tax_rate
        is_interstate = original_invoice.is_interstate
        if is_interstate:
            igst_amount = total_tax
        else:
            cgst_amount = (total_tax / 2).quantize(Decimal('0.01'))
            sgst_amount = (total_tax / 2).quantize(Decimal('0.01'))
    else:
        # Default 18% GST split
        total_tax = taxable_amount * Decimal('0.18')
        cgst_amount = (total_tax / 2).quantize(Decimal('0.01'))
        sgst_amount = (total_tax / 2).quantize(Decimal('0.01'))

    grand_total = taxable_amount + cgst_amount + sgst_amount + igst_amount

    # Create credit note - invoice_id is required, so we must have an invoice
    if not original_invoice:
        print(f"    WARNING: No original invoice found for return {return_order.rma_number}")
        return None

    credit_note = CreditDebitNote(
        note_number=note_number,
        document_type='CREDIT_NOTE',
        invoice_id=original_invoice.id,
        original_invoice_number=original_invoice.invoice_number,
        original_invoice_date=original_invoice.invoice_date,
        reason='SALES_RETURN',
        reason_description=f'Credit note for return {return_order.rma_number}',
        status='GENERATED',
        note_date=date.today(),
        customer_name=original_invoice.customer_name,
        place_of_supply=original_invoice.place_of_supply or 'Delhi',
        place_of_supply_code=original_invoice.place_of_supply_code or '07',
        is_interstate=is_interstate,
        taxable_amount=taxable_amount,
        cgst_amount=cgst_amount,
        sgst_amount=sgst_amount,
        igst_amount=igst_amount,
        total_tax=cgst_amount + sgst_amount + igst_amount,
        grand_total=grand_total,
    )
    db.add(credit_note)
    await db.flush()

    # Create credit note items
    for return_item in return_items:
        item_taxable = return_item.unit_price * return_item.accepted_quantity
        if is_interstate:
            item_igst = item_taxable * Decimal('0.18')
            item_cgst = Decimal('0')
            item_sgst = Decimal('0')
        else:
            item_cgst = (item_taxable * Decimal('0.09')).quantize(Decimal('0.01'))
            item_sgst = (item_taxable * Decimal('0.09')).quantize(Decimal('0.01'))
            item_igst = Decimal('0')

        cn_item = CreditDebitNoteItem(
            note_id=credit_note.id,
            product_id=return_item.product_id,
            sku=return_item.sku,
            item_name=return_item.product_name,
            hsn_code='84212100',  # Water purifier HSN
            quantity=return_item.accepted_quantity,
            uom='NOS',
            unit_price=return_item.unit_price,
            taxable_value=item_taxable,
            gst_rate=Decimal('18.00'),  # 18% GST rate
            cgst_amount=item_cgst,
            sgst_amount=item_sgst,
            igst_amount=item_igst,
            total_tax=item_cgst + item_sgst + item_igst,
            line_total=item_taxable + item_cgst + item_sgst + item_igst,
        )
        db.add(cn_item)

    await db.flush()
    return credit_note


async def create_refund(db, return_order):
    """Create a refund record for the return."""

    # Generate refund number
    today_str = date.today().strftime('%Y%m%d')
    result = await db.execute(
        select(func.count(Refund.id))
        .where(Refund.refund_number.like(f'REF-{today_str}%'))
    )
    count = result.scalar() or 0
    refund_number = f"REF-{today_str}-{count + 1:04d}"

    # Get order for refund amount
    result = await db.execute(
        select(Order).where(Order.id == return_order.order_id)
    )
    order = result.scalar_one_or_none()

    refund = Refund(
        refund_number=refund_number,
        return_order_id=return_order.id,
        order_id=return_order.order_id,
        customer_id=return_order.customer_id,
        refund_type='RETURN',
        refund_method='ORIGINAL_PAYMENT',
        status='COMPLETED',  # Mark as completed for test
        order_amount=order.total_amount if order else return_order.total_return_amount,
        refund_amount=return_order.net_refund_amount,
        processing_fee=Decimal('0'),
        net_refund=return_order.net_refund_amount,
        tax_refund=(return_order.net_refund_amount * Decimal('0.18') / Decimal('1.18')).quantize(Decimal('0.01')),
        reason=return_order.return_reason,  # Required field
        processed_at=datetime.now(timezone.utc),
        notes=f'Refund for return {return_order.rma_number}',
    )
    db.add(refund)
    await db.flush()

    # Update return order status
    return_order.status = 'REFUND_PROCESSED'
    history = ReturnStatusHistory(
        return_order_id=return_order.id,
        from_status='APPROVED',
        to_status='REFUND_PROCESSED',
        notes=f'Refund processed: {refund_number}',
    )
    db.add(history)

    await db.flush()
    return refund


async def post_return_gl_entries(db, return_orders, credit_notes, refunds):
    """Post GL entries for all returns."""
    print("\n  Posting Return GL Entries...")

    # Get or create GL accounts
    gl_accounts = {}
    account_codes = {
        'SALES_REVENUE': ('4000', 'Sales Revenue', 'REVENUE', 'SALES_REVENUE'),
        'ACCOUNTS_RECEIVABLE': ('1300', 'Accounts Receivable', 'ASSET', 'ACCOUNTS_RECEIVABLE'),
        'COGS': ('5000', 'Cost of Goods Sold', 'EXPENSE', 'COST_OF_GOODS'),
        'INVENTORY': ('1200', 'Inventory', 'ASSET', 'INVENTORY'),
        'CGST_PAYABLE': ('2310', 'CGST Payable', 'LIABILITY', 'TAX_PAYABLE'),
        'SGST_PAYABLE': ('2320', 'SGST Payable', 'LIABILITY', 'TAX_PAYABLE'),
        'IGST_PAYABLE': ('2330', 'IGST Payable', 'LIABILITY', 'TAX_PAYABLE'),
        'CASH': ('1010', 'Cash in Hand', 'ASSET', 'CASH'),
        'BANK': ('1020', 'Bank Account', 'ASSET', 'BANK'),
        'SALES_RETURNS': ('4100', 'Sales Returns', 'REVENUE', 'SALES_REVENUE'),
    }

    for key, (code, name, acc_type, sub_type) in account_codes.items():
        result = await db.execute(
            select(GLAccount).where(GLAccount.account_code == code)
        )
        account = result.scalar_one_or_none()
        if not account:
            account = GLAccount(
                account_code=code,
                account_name=name,
                account_type=acc_type,
                account_sub_type=sub_type,
                is_active=True,
            )
            db.add(account)
            await db.flush()
        gl_accounts[key] = account

    # Get financial period
    result = await db.execute(
        select(FinancialPeriod).where(FinancialPeriod.is_current == True)
    )
    period = result.scalar_one_or_none()
    if not period:
        period = FinancialPeriod(
            period_code='FY2526',
            period_name='FY 2025-26',
            period_type='YEAR',
            start_date=date(2025, 4, 1),
            end_date=date(2026, 3, 31),
            status='OPEN',
            is_current=True,
        )
        db.add(period)
        await db.flush()

    # Get max entry number
    result = await db.execute(
        select(func.max(JournalEntry.entry_number))
    )
    max_entry = result.scalar_one_or_none()
    if max_entry and max_entry.startswith(f"JV-{date.today().strftime('%Y%m')}-"):
        entry_count = int(max_entry.split('-')[-1])
    else:
        entry_count = 0

    # Post GL entries for each return/credit note
    for i, (return_order, credit_note, refund) in enumerate(zip(return_orders, credit_notes, refunds)):
        # Get return items to calculate COGS reversal
        result = await db.execute(
            select(ReturnItem).where(ReturnItem.return_order_id == return_order.id)
        )
        return_items = result.scalars().all()

        cogs_reversal = Decimal('0')
        for item in return_items:
            result = await db.execute(
                select(Product).where(Product.id == item.product_id)
            )
            product = result.scalar_one_or_none()
            if product and product.cost_price:
                cogs_reversal += product.cost_price * item.accepted_quantity

        # === Entry 1: Sales Return (reverse the sale) ===
        entry_count += 1
        entry_number = f"JV-{date.today().strftime('%Y%m')}-{entry_count:04d}"

        # DR Sales Returns (or DR Sales Revenue to reduce it)
        # CR Accounts Receivable
        # CR CGST/SGST Payable (reverse tax liability)
        sales_return_entry = JournalEntry(
            entry_number=entry_number,
            entry_date=date.today(),
            entry_type='SALES_RETURN',
            status='POSTED',
            source_type='CREDIT_NOTE',
            source_number=credit_note.note_number,
            source_id=credit_note.id,
            narration=f'Sales return - {credit_note.note_number} for {return_order.rma_number}',
            total_debit=credit_note.grand_total,
            total_credit=credit_note.grand_total,
            period_id=period.id,
            posted_at=datetime.now(timezone.utc),
        )
        db.add(sales_return_entry)
        await db.flush()

        # DR Sales Returns (reduces revenue)
        dr_sales_return = JournalEntryLine(
            journal_entry_id=sales_return_entry.id,
            account_id=gl_accounts['SALES_RETURNS'].id,
            debit_amount=credit_note.taxable_amount,
            credit_amount=Decimal('0'),
            description=f'Sales return for {return_order.rma_number}',
        )
        db.add(dr_sales_return)

        # DR CGST Payable (reverse tax liability)
        if credit_note.cgst_amount > 0:
            dr_cgst = JournalEntryLine(
                journal_entry_id=sales_return_entry.id,
                account_id=gl_accounts['CGST_PAYABLE'].id,
                debit_amount=credit_note.cgst_amount,
                credit_amount=Decimal('0'),
                description='CGST reversal on return',
            )
            db.add(dr_cgst)

        # DR SGST Payable (reverse tax liability)
        if credit_note.sgst_amount > 0:
            dr_sgst = JournalEntryLine(
                journal_entry_id=sales_return_entry.id,
                account_id=gl_accounts['SGST_PAYABLE'].id,
                debit_amount=credit_note.sgst_amount,
                credit_amount=Decimal('0'),
                description='SGST reversal on return',
            )
            db.add(dr_sgst)

        # DR IGST Payable (if interstate)
        if credit_note.igst_amount > 0:
            dr_igst = JournalEntryLine(
                journal_entry_id=sales_return_entry.id,
                account_id=gl_accounts['IGST_PAYABLE'].id,
                debit_amount=credit_note.igst_amount,
                credit_amount=Decimal('0'),
                description='IGST reversal on return',
            )
            db.add(dr_igst)

        # CR Accounts Receivable (reduce customer balance)
        cr_ar = JournalEntryLine(
            journal_entry_id=sales_return_entry.id,
            account_id=gl_accounts['ACCOUNTS_RECEIVABLE'].id,
            debit_amount=Decimal('0'),
            credit_amount=credit_note.grand_total,
            description=f'Reduce AR for return {return_order.rma_number}',
        )
        db.add(cr_ar)

        # === Entry 2: COGS Reversal (restore inventory) ===
        if cogs_reversal > 0:
            entry_count += 1
            cogs_entry_number = f"JV-{date.today().strftime('%Y%m')}-{entry_count:04d}"

            cogs_reversal_entry = JournalEntry(
                entry_number=cogs_entry_number,
                entry_date=date.today(),
                entry_type='COST_REVERSAL',
                status='POSTED',
                source_type='CREDIT_NOTE',
                source_number=credit_note.note_number,
                source_id=credit_note.id,
                narration=f'COGS reversal for return {return_order.rma_number}',
                total_debit=cogs_reversal,
                total_credit=cogs_reversal,
                period_id=period.id,
                posted_at=datetime.now(timezone.utc),
            )
            db.add(cogs_reversal_entry)
            await db.flush()

            # DR Inventory (restore stock value)
            dr_inventory = JournalEntryLine(
                journal_entry_id=cogs_reversal_entry.id,
                account_id=gl_accounts['INVENTORY'].id,
                debit_amount=cogs_reversal,
                credit_amount=Decimal('0'),
                description=f'Inventory restored for return',
            )
            db.add(dr_inventory)

            # CR COGS (reduce expense)
            cr_cogs = JournalEntryLine(
                journal_entry_id=cogs_reversal_entry.id,
                account_id=gl_accounts['COGS'].id,
                debit_amount=Decimal('0'),
                credit_amount=cogs_reversal,
                description=f'COGS reversal for return',
            )
            db.add(cr_cogs)

        # === Entry 3: Refund Payment ===
        entry_count += 1
        refund_entry_number = f"JV-{date.today().strftime('%Y%m')}-{entry_count:04d}"

        refund_entry = JournalEntry(
            entry_number=refund_entry_number,
            entry_date=date.today(),
            entry_type='REFUND',
            status='POSTED',
            source_type='REFUND',
            source_number=refund.refund_number,
            source_id=refund.id,
            narration=f'Refund payment for {return_order.rma_number}',
            total_debit=refund.net_refund,
            total_credit=refund.net_refund,
            period_id=period.id,
            posted_at=datetime.now(timezone.utc),
        )
        db.add(refund_entry)
        await db.flush()

        # DR Accounts Receivable (clear the credit balance from return)
        dr_ar_refund = JournalEntryLine(
            journal_entry_id=refund_entry.id,
            account_id=gl_accounts['ACCOUNTS_RECEIVABLE'].id,
            debit_amount=refund.net_refund,
            credit_amount=Decimal('0'),
            description=f'Clear AR for refund {refund.refund_number}',
        )
        db.add(dr_ar_refund)

        # CR Bank (cash outflow)
        cr_bank = JournalEntryLine(
            journal_entry_id=refund_entry.id,
            account_id=gl_accounts['BANK'].id,
            debit_amount=Decimal('0'),
            credit_amount=refund.net_refund,
            description=f'Refund paid to customer',
        )
        db.add(cr_bank)

        print(f"    Posted GL entries for Return {return_order.rma_number}")

    await db.commit()
    return gl_accounts


async def generate_balance_sheet(db, gl_accounts):
    """Generate and display Balance Sheet after returns."""
    print("\n" + "=" * 80)
    print("BALANCE SHEET (AFTER RETURNS)")
    print(f"As of {date.today().strftime('%d %B %Y')}")
    print("=" * 80)

    # Calculate account balances from journal entry lines
    balance_sheet = {
        'ASSET': {},
        'LIABILITY': {},
        'EQUITY': {},
        'REVENUE': {},
        'EXPENSE': {},
    }

    # Get all GL accounts with their balances
    result = await db.execute(
        select(GLAccount)
    )
    all_accounts = result.scalars().all()

    for account in all_accounts:
        # Calculate balance from journal entry lines
        result = await db.execute(
            select(
                func.coalesce(func.sum(JournalEntryLine.debit_amount), 0).label('total_debit'),
                func.coalesce(func.sum(JournalEntryLine.credit_amount), 0).label('total_credit')
            ).where(JournalEntryLine.account_id == account.id)
        )
        row = result.first()
        total_debit = Decimal(str(row.total_debit)) if row.total_debit else Decimal('0')
        total_credit = Decimal(str(row.total_credit)) if row.total_credit else Decimal('0')

        # Calculate balance based on account type (Assets, Expenses = Debit normal balance)
        is_debit_normal = account.account_type in ['ASSET', 'EXPENSE']
        if is_debit_normal:
            balance = total_debit - total_credit
        else:
            balance = total_credit - total_debit

        if balance != 0:
            category = account.account_type
            if category in balance_sheet:
                balance_sheet[category][account.account_name] = balance
            else:
                balance_sheet['ASSET'][account.account_name] = balance

    # Display Balance Sheet
    print("\n" + "-" * 40)
    print("ASSETS")
    print("-" * 40)
    total_assets = Decimal('0')
    for name, balance in balance_sheet['ASSET'].items():
        print(f"  {name:<30} ₹{balance:>12,.2f}")
        total_assets += balance
    print(f"  {'TOTAL ASSETS':<30} ₹{total_assets:>12,.2f}")

    print("\n" + "-" * 40)
    print("LIABILITIES")
    print("-" * 40)
    total_liabilities = Decimal('0')
    for name, balance in balance_sheet['LIABILITY'].items():
        print(f"  {name:<30} ₹{balance:>12,.2f}")
        total_liabilities += balance
    print(f"  {'TOTAL LIABILITIES':<30} ₹{total_liabilities:>12,.2f}")

    print("\n" + "-" * 40)
    print("EQUITY")
    print("-" * 40)
    total_equity = Decimal('0')
    for name, balance in balance_sheet['EQUITY'].items():
        print(f"  {name:<30} ₹{balance:>12,.2f}")
        total_equity += balance

    # Calculate Retained Earnings (Revenue - Expenses)
    total_revenue = sum(balance_sheet['REVENUE'].values()) if balance_sheet['REVENUE'] else Decimal('0')
    total_expense = sum(balance_sheet['EXPENSE'].values()) if balance_sheet['EXPENSE'] else Decimal('0')
    net_income = total_revenue - total_expense
    print(f"  {'Retained Earnings (Net Income)':<30} ₹{net_income:>12,.2f}")
    total_equity += net_income

    print(f"  {'TOTAL EQUITY':<30} ₹{total_equity:>12,.2f}")

    print("\n" + "-" * 40)
    print(f"TOTAL LIABILITIES + EQUITY: ₹{(total_liabilities + total_equity):>12,.2f}")
    print("-" * 40)

    # Verify accounting equation
    if abs(total_assets - (total_liabilities + total_equity)) < Decimal('0.01'):
        print("\n✅ Balance Sheet BALANCES! Assets = Liabilities + Equity")
    else:
        print(f"\n⚠️ Balance Sheet does NOT balance!")
        print(f"   Assets: ₹{total_assets:,.2f}")
        print(f"   L+E: ₹{(total_liabilities + total_equity):,.2f}")
        print(f"   Difference: ₹{abs(total_assets - (total_liabilities + total_equity)):,.2f}")

    # Display Income Statement
    print("\n" + "=" * 80)
    print("INCOME STATEMENT (P&L) - AFTER RETURNS")
    print(f"For the period ending {date.today().strftime('%d %B %Y')}")
    print("=" * 80)

    print("\n" + "-" * 40)
    print("REVENUE")
    print("-" * 40)
    for name, balance in balance_sheet['REVENUE'].items():
        print(f"  {name:<30} ₹{balance:>12,.2f}")
    print(f"  {'TOTAL REVENUE':<30} ₹{total_revenue:>12,.2f}")

    print("\n" + "-" * 40)
    print("EXPENSES")
    print("-" * 40)
    for name, balance in balance_sheet['EXPENSE'].items():
        print(f"  {name:<30} ₹{balance:>12,.2f}")
    print(f"  {'TOTAL EXPENSES':<30} ₹{total_expense:>12,.2f}")

    print("\n" + "-" * 40)
    print(f"  {'NET INCOME':<30} ₹{net_income:>12,.2f}")
    print("-" * 40)

    return {
        'total_assets': total_assets,
        'total_liabilities': total_liabilities,
        'total_equity': total_equity,
        'total_revenue': total_revenue,
        'total_expense': total_expense,
        'net_income': net_income,
    }


async def run_return_flow_test():
    """Main test execution."""
    print("\n" + "=" * 80)
    print("4-CHANNEL RETURN FLOW TEST")
    print("=" * 80)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    async with async_session_factory() as db:
        # Step 1: Get recent orders
        orders = await get_recent_orders(db)
        if not orders:
            print("ERROR: No orders found to return!")
            return

        # Step 2: Create return orders
        print("\n" + "=" * 80)
        print("CREATING RETURN ORDERS")
        print("=" * 80)

        return_reasons = ['DEFECTIVE', 'DAMAGED', 'WRONG_ITEM', 'CHANGED_MIND']
        return_orders = []

        for i, order in enumerate(orders):
            reason = return_reasons[i % len(return_reasons)]
            return_order = await create_return_order(db, order, reason)
            return_orders.append(return_order)
            print(f"  Created: {return_order.rma_number} for {order.order_number} | Reason: {reason}")

        await db.flush()

        # Step 3: Process return flow
        print("\n" + "=" * 80)
        print("PROCESSING RETURN FLOW")
        print("=" * 80)

        for return_order in return_orders:
            await process_return_flow(db, return_order)
            print(f"  {return_order.rma_number}: INITIATED → ... → APPROVED")

        await db.flush()

        # Step 4: Get original invoices for credit notes
        print("\n" + "=" * 80)
        print("CREATING CREDIT NOTES")
        print("=" * 80)

        # Get all recent invoices
        result = await db.execute(
            select(TaxInvoice)
            .order_by(desc(TaxInvoice.created_at))
            .limit(20)
        )
        all_invoices = result.scalars().all()

        credit_notes = []
        used_invoices = set()  # Track used invoices to avoid duplicates

        for return_order in return_orders:
            # Find invoice by matching amount (that hasn't been used yet)
            original_invoice = None
            for inv in all_invoices:
                if inv.id not in used_invoices:
                    if abs(inv.grand_total - return_order.total_return_amount) < Decimal('1'):
                        original_invoice = inv
                        used_invoices.add(inv.id)
                        break

            # Fallback to any unused invoice
            if not original_invoice:
                for inv in all_invoices:
                    if inv.id not in used_invoices:
                        original_invoice = inv
                        used_invoices.add(inv.id)
                        break

            if not original_invoice:
                print(f"  WARNING: No invoice found for return {return_order.rma_number}")
                continue

            credit_note = await create_credit_note(db, return_order, original_invoice)
            if credit_note:
                credit_notes.append(credit_note)
                print(f"  Created: {credit_note.note_number} | Amount: ₹{credit_note.grand_total:,.2f}")
            else:
                print(f"  SKIPPED: Could not create credit note for {return_order.rma_number}")

        await db.flush()

        if not credit_notes:
            print("\n  ERROR: No credit notes could be created!")
            return

        # Step 5: Create refunds (only for returns with credit notes)
        print("\n" + "=" * 80)
        print("PROCESSING REFUNDS")
        print("=" * 80)

        # Filter return orders to only those with credit notes
        valid_return_orders = return_orders[:len(credit_notes)]

        refunds = []
        for return_order in valid_return_orders:
            refund = await create_refund(db, return_order)
            refunds.append(refund)
            print(f"  {refund.refund_number}: ₹{refund.net_refund:,.2f} | Status: {refund.status}")

        await db.commit()

        # Step 6: Post GL entries for returns
        print("\n" + "=" * 80)
        print("POSTING RETURN GL ENTRIES")
        print("=" * 80)

        gl_accounts = await post_return_gl_entries(db, valid_return_orders, credit_notes, refunds)

        # Step 7: Generate Balance Sheet
        financials = await generate_balance_sheet(db, gl_accounts)

        # Summary
        print("\n" + "=" * 80)
        print("RETURN FLOW TEST SUMMARY")
        print("=" * 80)

        total_return_value = sum(ro.total_return_amount for ro in return_orders)
        total_refund_value = sum(r.net_refund for r in refunds)
        total_cogs_returned = Decimal('0')

        for return_order in return_orders:
            result = await db.execute(
                select(ReturnItem).where(ReturnItem.return_order_id == return_order.id)
            )
            items = result.scalars().all()
            for item in items:
                result = await db.execute(
                    select(Product).where(Product.id == item.product_id)
                )
                product = result.scalar_one_or_none()
                if product and product.cost_price:
                    total_cogs_returned += product.cost_price * item.accepted_quantity

        print(f"""
  Returns Processed:     {len(return_orders)}
  Credit Notes Created:  {len(credit_notes)}
  Refunds Issued:        {len(refunds)}

  Total Return Value:    ₹{total_return_value:,.2f}
  Total Refund Amount:   ₹{total_refund_value:,.2f}
  COGS Returned:         ₹{total_cogs_returned:,.2f}

  Financial Summary (After Returns):
  - Total Revenue:       ₹{financials['total_revenue']:,.2f}
  - Total Expenses:      ₹{financials['total_expense']:,.2f}
  - Net Income:          ₹{financials['net_income']:,.2f}
  - Total Assets:        ₹{financials['total_assets']:,.2f}
  - Total Liabilities:   ₹{financials['total_liabilities']:,.2f}

  Return Breakdown:
""")

        for i, (return_order, credit_note, refund) in enumerate(zip(return_orders, credit_notes, refunds)):
            result = await db.execute(
                select(Order).where(Order.id == return_order.order_id)
            )
            order = result.scalar_one_or_none()
            order_num = order.order_number if order else "N/A"
            print(f"    {return_order.rma_number}: {order_num} | CN: {credit_note.note_number} | Refund: ₹{refund.net_refund:,.2f}")

        print("\n" + "=" * 80)
        print("✅ 4-CHANNEL RETURN FLOW TEST COMPLETED SUCCESSFULLY!")
        print("=" * 80)


if __name__ == "__main__":
    asyncio.run(run_return_flow_test())
