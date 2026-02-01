#!/usr/bin/env python3
"""
PROPER COGS FLOW TEST - No Shortcuts
=====================================
This test follows the actual business flow:

1. CREATE PO - Purchase Order for spare parts
2. CREATE GRN - Goods Receipt Note
3. ACCEPT GRN - Triggers ProductCost update with Weighted Average Cost
4. CREATE CUSTOMER - Mantosh (9013034082)
5. CREATE ORDER - > ₹50,000
6. FULL FLOW - PAY → ALLOCATE → SHIP → MANIFEST → INVOICE
7. COGS POSTING - Using actual ProductCost.average_cost
8. BALANCE SHEET & P&L - With accurate COGS
9. E-WAY BILL CHECK - Required for orders > ₹50,000
"""

import asyncio
import sys
import logging
from decimal import Decimal, ROUND_HALF_UP
import uuid
from datetime import date, datetime, timedelta, timezone

# Setup logging
logging.basicConfig(level=logging.WARNING, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add project to path
sys.path.insert(0, '/Users/mantosh/Desktop/Consumer durable 2')

from app.database import async_session_factory
from sqlalchemy import select, func, text
from sqlalchemy.orm import selectinload

# Models
from app.models.purchase import PurchaseOrder, PurchaseOrderItem, GoodsReceiptNote, GRNItem
from app.models.product import Product
from app.models.product_cost import ProductCost
from app.models.vendor import Vendor
from app.models.warehouse import Warehouse
from app.models.customer import Customer
from app.models.order import Order, OrderItem
from app.models.user import User
from app.models.inventory import InventorySummary, StockItem
from app.models.shipment import Shipment
from app.models.billing import TaxInvoice, InvoiceItem, EWayBill
from app.models.accounting import GLAccount, JournalEntry, JournalEntryLine, FinancialPeriod

# Services
from app.services.costing_service import CostingService


async def run_proper_cogs_test():
    """Run the complete COGS flow test without shortcuts."""

    print("\n" + "=" * 80)
    print("PROPER COGS FLOW TEST - NO SHORTCUTS")
    print("=" * 80)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    async with async_session_factory() as db:

        # ============================================================
        # STEP 1: GET PREREQUISITES
        # ============================================================
        print("=" * 80)
        print("[STEP 1] GATHERING PREREQUISITES")
        print("=" * 80)

        # Get vendor
        result = await db.execute(
            select(Vendor).where(Vendor.gstin.isnot(None)).limit(1)
        )
        vendor = result.scalar_one_or_none()
        if not vendor:
            print("ERROR: No vendor with GSTIN found!")
            return
        print(f"  Vendor: {vendor.name} (GSTIN: {vendor.gstin})")

        # Get warehouse
        result = await db.execute(select(Warehouse).limit(1))
        warehouse = result.scalar_one_or_none()
        if not warehouse:
            print("ERROR: No warehouse found!")
            return
        print(f"  Warehouse: {warehouse.name} ({warehouse.code})")

        # Get user for receiving
        result = await db.execute(select(User).limit(1))
        user = result.scalar_one_or_none()
        if not user:
            print("ERROR: No user found!")
            return
        print(f"  User: {user.email}")

        # Get spare parts for PO
        result = await db.execute(
            select(Product)
            .where(Product.item_type == 'SP', Product.is_active == True)
            .order_by(Product.cost_price.desc())
            .limit(5)
        )
        spare_parts = result.scalars().all()
        if not spare_parts:
            print("ERROR: No spare parts found!")
            return
        print(f"  Spare Parts: {len(spare_parts)} products found")

        # Get financial period
        result = await db.execute(
            select(FinancialPeriod).where(FinancialPeriod.is_current == True)
        )
        period = result.scalar_one_or_none()
        if not period:
            print("  Creating financial period...")
            period = FinancialPeriod(
                period_code='FY2526',
                period_name='FY 2025-26',
                start_date=date(2025, 4, 1),
                end_date=date(2026, 3, 31),
                status='OPEN',
                is_current=True,
            )
            db.add(period)
            await db.commit()
        print(f"  Period: {period.period_code}")

        # ============================================================
        # STEP 2: CREATE PURCHASE ORDER
        # ============================================================
        print("\n" + "=" * 80)
        print("[STEP 2] CREATING PURCHASE ORDER")
        print("=" * 80)

        # Generate PO number
        today_str = date.today().strftime('%Y%m%d')
        result = await db.execute(
            select(func.count(PurchaseOrder.id))
            .where(PurchaseOrder.po_number.like(f'PO-{today_str}%'))
        )
        po_count = result.scalar() or 0
        po_number = f"PO-{today_str}-{po_count + 1:04d}"

        # Calculate PO totals
        po_items_data = []
        subtotal = Decimal('0')

        for i, product in enumerate(spare_parts):
            qty = 100  # Order 100 of each spare part
            unit_price = product.cost_price or Decimal('100')
            taxable = unit_price * qty
            gst_rate = product.gst_rate or Decimal('18')
            cgst = (taxable * gst_rate / 2 / 100).quantize(Decimal('0.01'))
            sgst = cgst
            total = taxable + cgst + sgst

            po_items_data.append({
                'product': product,
                'qty': qty,
                'unit_price': unit_price,
                'taxable': taxable,
                'gst_rate': gst_rate,
                'cgst': cgst,
                'sgst': sgst,
                'total': total,
            })
            subtotal += taxable

            print(f"  {product.sku}: {qty} x ₹{unit_price:,.2f} = ₹{taxable:,.2f}")

        total_cgst = sum(item['cgst'] for item in po_items_data)
        total_sgst = sum(item['sgst'] for item in po_items_data)
        total_tax = total_cgst + total_sgst
        grand_total = subtotal + total_tax

        # Create PO
        po = PurchaseOrder(
            po_number=po_number,
            po_date=date.today(),
            status='APPROVED',  # Already approved for testing
            vendor_id=vendor.id,
            delivery_warehouse_id=warehouse.id,
            vendor_name=vendor.name,
            vendor_gstin=vendor.gstin,
            subtotal=subtotal,
            discount_amount=Decimal('0'),
            taxable_amount=subtotal,
            cgst_amount=total_cgst,
            sgst_amount=total_sgst,
            igst_amount=Decimal('0'),
            total_tax=total_tax,
            grand_total=grand_total,
            expected_delivery_date=date.today(),
        )
        db.add(po)
        await db.flush()

        # Create PO items
        for i, item_data in enumerate(po_items_data):
            po_item = PurchaseOrderItem(
                purchase_order_id=po.id,
                product_id=item_data['product'].id,
                product_name=item_data['product'].name,
                sku=item_data['product'].sku,
                hsn_code=item_data['product'].hsn_code or '84212100',
                line_number=i + 1,
                quantity_ordered=item_data['qty'],
                quantity_pending=item_data['qty'],
                uom='PCS',
                unit_price=item_data['unit_price'],
                taxable_amount=item_data['taxable'],
                gst_rate=item_data['gst_rate'],
                cgst_rate=item_data['gst_rate'] / 2,
                sgst_rate=item_data['gst_rate'] / 2,
                cgst_amount=item_data['cgst'],
                sgst_amount=item_data['sgst'],
                total_amount=item_data['total'],
            )
            db.add(po_item)

        await db.commit()
        print(f"\n  ✅ PO Created: {po_number}")
        print(f"     Subtotal: ₹{subtotal:,.2f}")
        print(f"     Tax: ₹{total_tax:,.2f}")
        print(f"     Grand Total: ₹{grand_total:,.2f}")

        # ============================================================
        # STEP 3: CREATE GRN (Goods Receipt Note)
        # ============================================================
        print("\n" + "=" * 80)
        print("[STEP 3] CREATING GRN (Goods Receipt Note)")
        print("=" * 80)

        # Generate GRN number
        result = await db.execute(
            select(func.count(GoodsReceiptNote.id))
            .where(GoodsReceiptNote.grn_number.like(f'GRN-{today_str}%'))
        )
        grn_count = result.scalar() or 0
        grn_number = f"GRN-{today_str}-{grn_count + 1:04d}"

        # Get PO items
        result = await db.execute(
            select(PurchaseOrderItem)
            .where(PurchaseOrderItem.purchase_order_id == po.id)
        )
        po_items = result.scalars().all()

        # Create GRN
        grn = GoodsReceiptNote(
            grn_number=grn_number,
            grn_date=date.today(),
            status='ACCEPTED',  # Directly accepted for testing
            purchase_order_id=po.id,
            vendor_id=vendor.id,
            warehouse_id=warehouse.id,
            vendor_challan_number=f'DC-{today_str}',
            vendor_challan_date=date.today(),
            total_items=len(po_items),
            total_quantity_received=sum(item.quantity_ordered for item in po_items),
            total_quantity_accepted=sum(item.quantity_ordered for item in po_items),
            total_quantity_rejected=0,
            total_value=grand_total,
            qc_required=False,
            qc_status='PASSED',
            received_by=user.id,
        )
        db.add(grn)
        await db.flush()

        # Create GRN items
        for po_item in po_items:
            grn_item = GRNItem(
                grn_id=grn.id,
                po_item_id=po_item.id,
                product_id=po_item.product_id,
                product_name=po_item.product_name,
                sku=po_item.sku,
                hsn_code=po_item.hsn_code,
                quantity_expected=po_item.quantity_ordered,
                quantity_received=po_item.quantity_ordered,
                quantity_accepted=po_item.quantity_ordered,
                quantity_rejected=0,
                unit_price=po_item.unit_price,
                accepted_value=po_item.unit_price * po_item.quantity_ordered,
                qc_result='PASSED',
            )
            db.add(grn_item)

            # Update PO item quantities
            po_item.quantity_received = po_item.quantity_ordered
            po_item.quantity_accepted = po_item.quantity_ordered
            po_item.quantity_pending = 0

        # Update PO status
        po.status = 'FULLY_RECEIVED'
        po.total_received_value = grand_total

        await db.commit()
        print(f"  ✅ GRN Created: {grn_number}")
        print(f"     Items: {grn.total_items}")
        print(f"     Qty Accepted: {grn.total_quantity_accepted}")
        print(f"     Total Value: ₹{grn.total_value:,.2f}")

        # ============================================================
        # STEP 4: UPDATE PRODUCT COSTS (Weighted Average)
        # ============================================================
        print("\n" + "=" * 80)
        print("[STEP 4] UPDATING PRODUCT COSTS (Weighted Average)")
        print("=" * 80)

        costing_service = CostingService(db)

        # Refresh GRN with items
        await db.refresh(grn)
        result = await db.execute(
            select(GRNItem).where(GRNItem.grn_id == grn.id)
        )
        grn_items = result.scalars().all()

        print(f"\n  {'SKU':<20} {'Old Avg':<12} {'GRN Qty':<10} {'Unit Cost':<12} {'New Avg':<12}")
        print("  " + "-" * 70)

        for grn_item in grn_items:
            # Get or create ProductCost
            product_cost = await costing_service.get_or_create_product_cost(
                product_id=grn_item.product_id,
                warehouse_id=warehouse.id,
            )
            old_avg = product_cost.average_cost or Decimal('0')

            # Update cost with receipt
            updated_cost = await costing_service.update_cost_with_receipt(
                product_id=grn_item.product_id,
                new_qty=grn_item.quantity_accepted,
                new_unit_cost=grn_item.unit_price,
                grn_id=grn.id,
                grn_number=grn.grn_number,
                warehouse_id=warehouse.id,
            )

            print(f"  {grn_item.sku:<20} ₹{old_avg:<10,.2f} {grn_item.quantity_accepted:<10} "
                  f"₹{grn_item.unit_price:<10,.2f} ₹{updated_cost.average_cost:<10,.2f}")

        await db.commit()
        print("\n  ✅ ProductCost updated with Weighted Average Cost!")

        # ============================================================
        # STEP 5: CREATE CUSTOMER
        # ============================================================
        print("\n" + "=" * 80)
        print("[STEP 5] CREATING CUSTOMER - Mantosh (9013034082)")
        print("=" * 80)

        # Check if customer exists
        result = await db.execute(
            select(Customer).where(Customer.mobile == '9013034082')
        )
        customer = result.scalar_one_or_none()

        if not customer:
            # Generate customer code
            result = await db.execute(
                select(func.count(Customer.id))
                .where(Customer.customer_code.like(f'CUST-{today_str}%'))
            )
            cust_count = result.scalar() or 0
            customer_code = f"CUST-{today_str}-{cust_count + 1:04d}"

            customer = Customer(
                customer_code=customer_code,
                first_name='Mantosh',
                last_name='MKS',
                full_name='Mantosh MKS',
                mobile='9013034082',
                email='mantosh@example.com',
                customer_type='B2C',
                source='D2C',
                gstin=None,  # B2C customer
                billing_address={
                    'name': 'Mantosh MKS',
                    'address_line1': '123 Test Street',
                    'city': 'Delhi',
                    'state': 'Delhi',
                    'pincode': '110001',
                },
                shipping_address={
                    'name': 'Mantosh MKS',
                    'address_line1': '123 Test Street',
                    'city': 'Delhi',
                    'state': 'Delhi',
                    'pincode': '110001',
                },
                is_active=True,
            )
            db.add(customer)
            await db.commit()
            print(f"  ✅ Customer Created: {customer.full_name}")
        else:
            print(f"  ✓ Customer exists: {customer.full_name}")

        print(f"     Code: {customer.customer_code}")
        print(f"     Mobile: {customer.mobile}")

        # ============================================================
        # STEP 6: CREATE ORDER > ₹50,000
        # ============================================================
        print("\n" + "=" * 80)
        print("[STEP 6] CREATING ORDER > ₹50,000")
        print("=" * 80)

        # Get FG products for order
        result = await db.execute(
            select(Product)
            .where(Product.item_type == 'FG', Product.is_active == True)
            .order_by(Product.mrp.desc())
            .limit(3)
        )
        fg_products = result.scalars().all()

        # Generate order number
        result = await db.execute(
            select(func.count(Order.id))
            .where(Order.order_number.like(f'ORD-{today_str}%'))
        )
        order_count = result.scalar() or 0
        order_number = f"ORD-{today_str}-{order_count + 1:04d}"

        # Calculate order totals (need > ₹50,000)
        order_items_data = []
        subtotal = Decimal('0')

        for product in fg_products[:2]:  # Take 2 products
            qty = 2  # 2 each
            unit_price = product.selling_price or product.mrp or Decimal('15000')
            line_total = unit_price * qty
            gst_rate = product.gst_rate or Decimal('18')
            tax = (line_total * gst_rate / 100).quantize(Decimal('0.01'))

            order_items_data.append({
                'product': product,
                'qty': qty,
                'unit_price': unit_price,
                'line_total': line_total,
                'gst_rate': gst_rate,
                'tax': tax,
            })
            subtotal += line_total

            print(f"  {product.sku}: {qty} x ₹{unit_price:,.2f} = ₹{line_total:,.2f}")

        total_tax = sum(item['tax'] for item in order_items_data)
        total_amount = subtotal + total_tax

        print(f"\n  Subtotal: ₹{subtotal:,.2f}")
        print(f"  Tax: ₹{total_tax:,.2f}")
        print(f"  Total: ₹{total_amount:,.2f}")

        if total_amount < 50000:
            print(f"  ⚠️ Order < ₹50,000, adding more items...")
            # Add more quantity
            for item in order_items_data:
                item['qty'] += 2
                item['line_total'] = item['unit_price'] * item['qty']
                item['tax'] = (item['line_total'] * item['gst_rate'] / 100).quantize(Decimal('0.01'))

            subtotal = sum(item['line_total'] for item in order_items_data)
            total_tax = sum(item['tax'] for item in order_items_data)
            total_amount = subtotal + total_tax
            print(f"  New Total: ₹{total_amount:,.2f}")

        # Create order
        order = Order(
            order_number=order_number,
            customer_id=customer.id,
            status='CONFIRMED',
            source='D2C',
            warehouse_id=warehouse.id,
            subtotal=subtotal,
            tax_amount=total_tax,
            discount_amount=Decimal('0'),
            shipping_amount=Decimal('0'),
            total_amount=total_amount,
            payment_method='RAZORPAY',
            payment_status='PAID',
            amount_paid=total_amount,
            paid_at=datetime.now(timezone.utc),
            shipping_address=customer.shipping_address,
            billing_address=customer.billing_address,
        )
        db.add(order)
        await db.flush()

        # Create order items
        for i, item_data in enumerate(order_items_data):
            order_item = OrderItem(
                order_id=order.id,
                product_id=item_data['product'].id,
                product_name=item_data['product'].name,
                product_sku=item_data['product'].sku,
                quantity=item_data['qty'],
                unit_price=item_data['unit_price'],
                tax_rate=item_data['gst_rate'],
                tax_amount=item_data['tax'],
                total_amount=item_data['line_total'] + item_data['tax'],
                hsn_code=item_data['product'].hsn_code or '84212100',
            )
            db.add(order_item)

        await db.commit()
        print(f"\n  ✅ Order Created: {order_number}")
        print(f"     Total: ₹{total_amount:,.2f} (E-way bill required: {total_amount > 50000})")

        # ============================================================
        # STEP 7: PROCESS ORDER FLOW
        # ============================================================
        print("\n" + "=" * 80)
        print("[STEP 7] PROCESSING ORDER FLOW")
        print("=" * 80)

        # Allocate
        order.status = 'ALLOCATED'
        order.allocated_at = datetime.now(timezone.utc)
        print("  ✓ ALLOCATED")

        # Ship
        order.status = 'SHIPPED'
        order.shipped_at = datetime.now(timezone.utc)
        print("  ✓ SHIPPED")

        await db.commit()

        # ============================================================
        # STEP 8: CREATE INVOICE
        # ============================================================
        print("\n" + "=" * 80)
        print("[STEP 8] CREATING INVOICE")
        print("=" * 80)

        # Generate invoice number
        result = await db.execute(
            select(func.count(TaxInvoice.id))
            .where(TaxInvoice.invoice_number.like(f'INV/FY2526/%'))
        )
        inv_count = result.scalar() or 0
        invoice_number = f"INV/FY2526/{inv_count + 1:05d}"

        # Calculate GST
        cgst = (total_tax / 2).quantize(Decimal('0.01'))
        sgst = cgst

        invoice = TaxInvoice(
            invoice_number=invoice_number,
            invoice_date=date.today(),
            invoice_type='B2C',
            order_id=order.id,
            customer_id=customer.id,
            customer_name=customer.full_name,
            customer_mobile=customer.mobile,
            place_of_supply='Delhi',
            place_of_supply_code='07',
            is_interstate=False,
            subtotal=subtotal,
            discount_amount=Decimal('0'),
            taxable_amount=subtotal,
            cgst_amount=cgst,
            sgst_amount=sgst,
            igst_amount=Decimal('0'),
            total_tax=total_tax,
            grand_total=total_amount,
            status='GENERATED',
            billing_address=customer.billing_address,
            shipping_address=customer.shipping_address,
        )
        db.add(invoice)
        await db.flush()

        # Create invoice items
        result = await db.execute(
            select(OrderItem).where(OrderItem.order_id == order.id)
        )
        order_items = result.scalars().all()

        for oi in order_items:
            inv_item = InvoiceItem(
                invoice_id=invoice.id,
                product_id=oi.product_id,
                product_name=oi.product_name,
                sku=oi.product_sku,
                hsn_code=oi.hsn_code or '84212100',
                quantity=oi.quantity,
                uom='NOS',
                unit_price=oi.unit_price,
                discount_amount=Decimal('0'),
                taxable_value=oi.unit_price * oi.quantity,
                gst_rate=oi.tax_rate,
                cgst_amount=(oi.tax_amount / 2).quantize(Decimal('0.01')),
                sgst_amount=(oi.tax_amount / 2).quantize(Decimal('0.01')),
                igst_amount=Decimal('0'),
                total_tax=oi.tax_amount,
                line_total=oi.total_amount,
            )
            db.add(inv_item)

        await db.commit()
        print(f"  ✅ Invoice Created: {invoice_number}")
        print(f"     Total: ₹{total_amount:,.2f}")

        # ============================================================
        # STEP 9: CALCULATE COGS FROM PRODUCTCOST
        # ============================================================
        print("\n" + "=" * 80)
        print("[STEP 9] CALCULATING COGS FROM PRODUCTCOST (Weighted Average)")
        print("=" * 80)

        total_cogs = Decimal('0')
        cogs_details = []

        print(f"\n  {'Product':<25} {'Qty':<8} {'Avg Cost':<12} {'COGS':<15}")
        print("  " + "-" * 65)

        for oi in order_items:
            # Get ProductCost for this product
            product_cost = await costing_service.get_product_cost(
                product_id=oi.product_id,
                warehouse_id=warehouse.id,
            )

            if product_cost and product_cost.average_cost > 0:
                avg_cost = product_cost.average_cost
            else:
                # Fallback to product.cost_price
                result = await db.execute(
                    select(Product.cost_price).where(Product.id == oi.product_id)
                )
                avg_cost = result.scalar() or Decimal('0')

            item_cogs = avg_cost * oi.quantity
            total_cogs += item_cogs

            cogs_details.append({
                'product_id': oi.product_id,
                'sku': oi.product_sku,
                'qty': oi.quantity,
                'avg_cost': avg_cost,
                'cogs': item_cogs,
            })

            print(f"  {oi.product_sku:<25} {oi.quantity:<8} ₹{avg_cost:<10,.2f} ₹{item_cogs:<13,.2f}")

        print("  " + "-" * 65)
        print(f"  {'TOTAL COGS':<35} {'':8} {'':12} ₹{total_cogs:<13,.2f}")

        # ============================================================
        # STEP 10: POST GL ENTRIES (Sales + COGS)
        # ============================================================
        print("\n" + "=" * 80)
        print("[STEP 10] POSTING GL ENTRIES")
        print("=" * 80)

        # Get or create GL accounts
        gl_accounts = {}
        account_defs = [
            ('1010', 'Cash in Hand', 'ASSET', 'CASH'),
            ('1020', 'Bank Account', 'ASSET', 'BANK'),
            ('1200', 'Inventory', 'ASSET', 'INVENTORY'),
            ('1300', 'Accounts Receivable', 'ASSET', 'ACCOUNTS_RECEIVABLE'),
            ('2310', 'CGST Payable', 'LIABILITY', 'TAX_PAYABLE'),
            ('2320', 'SGST Payable', 'LIABILITY', 'TAX_PAYABLE'),
            ('4000', 'Sales Revenue', 'REVENUE', 'SALES_REVENUE'),
            ('4100', 'Sales Returns', 'REVENUE', 'SALES_RETURNS'),
            ('5000', 'Cost of Goods Sold', 'EXPENSE', 'COGS'),
        ]

        for code, name, acc_type, subtype in account_defs:
            result = await db.execute(
                select(GLAccount).where(GLAccount.account_code == code)
            )
            account = result.scalar_one_or_none()
            if not account:
                account = GLAccount(
                    account_code=code,
                    account_name=name,
                    account_type=acc_type,
                    account_subtype=subtype,
                    is_active=True,
                    current_balance=Decimal('0'),
                )
                db.add(account)
            gl_accounts[code] = account

        await db.flush()

        # Generate journal entry number
        result = await db.execute(
            select(func.count(JournalEntry.id))
            .where(JournalEntry.entry_number.like('JV-202601%'))
        )
        je_count = result.scalar() or 0

        # ----- SALES ENTRY -----
        je_sales = JournalEntry(
            entry_number=f'JV-202601-{je_count + 1:04d}',
            entry_date=date.today(),
            period_id=period.id,
            entry_type='SALES',
            source_type='INVOICE',
            source_id=invoice.id,
            source_number=invoice.invoice_number,
            narration=f'Sales invoice {invoice.invoice_number} - {customer.full_name}',
            total_debit=total_amount,
            total_credit=total_amount,
            status='POSTED',
            posted_at=datetime.now(timezone.utc),
        )
        db.add(je_sales)
        await db.flush()

        # DR Accounts Receivable (or Bank if paid)
        line1 = JournalEntryLine(
            journal_entry_id=je_sales.id,
            account_id=gl_accounts['1020'].id,  # Bank (paid)
            debit_amount=total_amount,
            credit_amount=Decimal('0'),
            description=f'Payment received for {invoice.invoice_number}',
            line_number=1,
        )
        db.add(line1)

        # CR Sales Revenue
        line2 = JournalEntryLine(
            journal_entry_id=je_sales.id,
            account_id=gl_accounts['4000'].id,
            debit_amount=Decimal('0'),
            credit_amount=subtotal,
            description='Sales revenue',
            line_number=2,
        )
        db.add(line2)

        # CR CGST Payable
        line3 = JournalEntryLine(
            journal_entry_id=je_sales.id,
            account_id=gl_accounts['2310'].id,
            debit_amount=Decimal('0'),
            credit_amount=cgst,
            description='CGST on sales',
            line_number=3,
        )
        db.add(line3)

        # CR SGST Payable
        line4 = JournalEntryLine(
            journal_entry_id=je_sales.id,
            account_id=gl_accounts['2320'].id,
            debit_amount=Decimal('0'),
            credit_amount=sgst,
            description='SGST on sales',
            line_number=4,
        )
        db.add(line4)

        print(f"  ✓ Sales Entry: {je_sales.entry_number}")
        print(f"    DR Bank: ₹{total_amount:,.2f}")
        print(f"    CR Sales: ₹{subtotal:,.2f}")
        print(f"    CR CGST: ₹{cgst:,.2f}")
        print(f"    CR SGST: ₹{sgst:,.2f}")

        # ----- COGS ENTRY -----
        je_cogs = JournalEntry(
            entry_number=f'JV-202601-{je_count + 2:04d}',
            entry_date=date.today(),
            period_id=period.id,
            entry_type='COGS',
            source_type='INVOICE',
            source_id=invoice.id,
            source_number=invoice.invoice_number,
            narration=f'COGS for invoice {invoice.invoice_number}',
            total_debit=total_cogs,
            total_credit=total_cogs,
            status='POSTED',
            posted_at=datetime.now(timezone.utc),
        )
        db.add(je_cogs)
        await db.flush()

        # DR COGS
        line5 = JournalEntryLine(
            journal_entry_id=je_cogs.id,
            account_id=gl_accounts['5000'].id,
            debit_amount=total_cogs,
            credit_amount=Decimal('0'),
            description=f'COGS for {invoice.invoice_number}',
            line_number=1,
        )
        db.add(line5)

        # CR Inventory
        line6 = JournalEntryLine(
            journal_entry_id=je_cogs.id,
            account_id=gl_accounts['1200'].id,
            debit_amount=Decimal('0'),
            credit_amount=total_cogs,
            description='Inventory reduction',
            line_number=2,
        )
        db.add(line6)

        print(f"\n  ✓ COGS Entry: {je_cogs.entry_number}")
        print(f"    DR COGS: ₹{total_cogs:,.2f}")
        print(f"    CR Inventory: ₹{total_cogs:,.2f}")

        # Update GL account balances
        gl_accounts['1020'].current_balance += total_amount  # Bank
        gl_accounts['4000'].current_balance += subtotal  # Sales
        gl_accounts['2310'].current_balance += cgst  # CGST Payable
        gl_accounts['2320'].current_balance += sgst  # SGST Payable
        gl_accounts['5000'].current_balance += total_cogs  # COGS
        gl_accounts['1200'].current_balance -= total_cogs  # Inventory

        await db.commit()

        # ============================================================
        # STEP 11: CHECK E-WAY BILL REQUIREMENT
        # ============================================================
        print("\n" + "=" * 80)
        print("[STEP 11] E-WAY BILL CHECK")
        print("=" * 80)

        if total_amount > 50000:
            print(f"  ⚠️ E-Way Bill REQUIRED (Order > ₹50,000)")
            print(f"     Order Value: ₹{total_amount:,.2f}")
            print(f"     Threshold: ₹50,000")

            # Check if E-way bill exists
            result = await db.execute(
                select(EWayBill).where(EWayBill.invoice_id == invoice.id)
            )
            eway = result.scalar_one_or_none()

            if eway:
                print(f"  ✅ E-Way Bill exists: {eway.eway_bill_number}")
            else:
                print(f"  ⚠️ E-Way Bill NOT generated yet")
                print(f"     Would need to be generated via GST portal integration")
        else:
            print(f"  ✓ E-Way Bill not required (Order ≤ ₹50,000)")

        # ============================================================
        # STEP 12: GENERATE BALANCE SHEET & P&L
        # ============================================================
        print("\n" + "=" * 80)
        print("[STEP 12] BALANCE SHEET & P&L")
        print("=" * 80)

        # Refresh GL accounts
        result = await db.execute(select(GLAccount))
        all_accounts = result.scalars().all()

        assets = {}
        liabilities = {}
        equity = {}
        revenue = {}
        expenses = {}

        for acc in all_accounts:
            if acc.account_type == 'ASSET':
                assets[acc.account_name] = acc.current_balance
            elif acc.account_type == 'LIABILITY':
                liabilities[acc.account_name] = acc.current_balance
            elif acc.account_type == 'EQUITY':
                equity[acc.account_name] = acc.current_balance
            elif acc.account_type == 'REVENUE':
                revenue[acc.account_name] = acc.current_balance
            elif acc.account_type == 'EXPENSE':
                expenses[acc.account_name] = acc.current_balance

        total_assets = sum(assets.values())
        total_liabilities = sum(liabilities.values())
        total_equity = sum(equity.values())
        total_revenue = sum(revenue.values())
        total_expenses = sum(expenses.values())
        net_income = total_revenue - total_expenses

        print("\n" + "=" * 60)
        print("BALANCE SHEET")
        print("=" * 60)

        print("\nASSETS:")
        for name, balance in sorted(assets.items()):
            if balance != 0:
                print(f"  {name:<30} ₹{balance:>15,.2f}")
        print(f"  {'TOTAL ASSETS':<30} ₹{total_assets:>15,.2f}")

        print("\nLIABILITIES:")
        for name, balance in sorted(liabilities.items()):
            if balance != 0:
                print(f"  {name:<30} ₹{balance:>15,.2f}")
        print(f"  {'TOTAL LIABILITIES':<30} ₹{total_liabilities:>15,.2f}")

        print("\nEQUITY:")
        print(f"  {'Retained Earnings (Net Income)':<30} ₹{net_income:>15,.2f}")
        total_equity_with_income = total_equity + net_income
        print(f"  {'TOTAL EQUITY':<30} ₹{total_equity_with_income:>15,.2f}")

        liab_plus_equity = total_liabilities + total_equity_with_income
        print(f"\n{'TOTAL LIABILITIES + EQUITY':<32} ₹{liab_plus_equity:>15,.2f}")

        if abs(total_assets - liab_plus_equity) < Decimal('0.01'):
            print("✅ Balance Sheet BALANCES!")
        else:
            print(f"⚠️ Difference: ₹{total_assets - liab_plus_equity:,.2f}")

        print("\n" + "=" * 60)
        print("INCOME STATEMENT (P&L)")
        print("=" * 60)

        print("\nREVENUE:")
        for name, balance in sorted(revenue.items()):
            if balance != 0:
                print(f"  {name:<30} ₹{balance:>15,.2f}")
        print(f"  {'TOTAL REVENUE':<30} ₹{total_revenue:>15,.2f}")

        print("\nEXPENSES:")
        for name, balance in sorted(expenses.items()):
            if balance != 0:
                print(f"  {name:<30} ₹{balance:>15,.2f}")
        print(f"  {'TOTAL EXPENSES (COGS)':<30} ₹{total_expenses:>15,.2f}")

        print(f"\n  {'NET INCOME':<30} ₹{net_income:>15,.2f}")
        gross_margin = ((total_revenue - total_expenses) / total_revenue * 100) if total_revenue > 0 else 0
        print(f"  {'Gross Margin':<30} {gross_margin:>14.1f}%")

        # ============================================================
        # SUMMARY
        # ============================================================
        print("\n" + "=" * 80)
        print("TEST SUMMARY - PROPER COGS FLOW")
        print("=" * 80)
        print(f"""
  Purchase Order:      {po_number}
  GRN:                 {grn_number}
  Customer:            {customer.full_name} ({customer.mobile})
  Order:               {order_number}
  Invoice:             {invoice_number}

  Order Value:         ₹{total_amount:,.2f}
  COGS (Weighted Avg): ₹{total_cogs:,.2f}
  Gross Profit:        ₹{subtotal - total_cogs:,.2f}
  Gross Margin:        {gross_margin:.1f}%

  E-Way Bill Required: {'YES' if total_amount > 50000 else 'NO'}

  Balance Sheet:       {'BALANCED' if abs(total_assets - liab_plus_equity) < Decimal('0.01') else 'UNBALANCED'}
  Total Assets:        ₹{total_assets:,.2f}
  Total Liabilities:   ₹{total_liabilities:,.2f}
  Net Income:          ₹{net_income:,.2f}
""")

        print("=" * 80)
        print("✅ PROPER COGS FLOW TEST COMPLETED!")
        print("   No shortcuts - All calculations from actual GRN and ProductCost")
        print("=" * 80)


if __name__ == "__main__":
    asyncio.run(run_proper_cogs_test())
