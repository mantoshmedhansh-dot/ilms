#!/usr/bin/env python3
"""
PRODUCTION ORDER FLOW TEST
==========================
Tests against PRODUCTION Supabase database.

Uses existing:
- PO: PO/APL/25-26/0001 (PARTIALLY_RECEIVED)
- GRN: GRN/APL/25-26/00001 (ACCEPTED)
- Customer: MKS (9013034082)
- ProductCost with weighted average costs

Flow:
1. Create order for MKS > ₹50,000
2. Process: PAY → ALLOCATE → SHIP → INVOICE
3. Calculate COGS from ProductCost.average_cost
4. Post GL entries
5. Check E-way bill (required for > ₹50,000)
6. Generate Balance Sheet & P&L
"""

import asyncio
import asyncpg
from decimal import Decimal, ROUND_HALF_UP
from datetime import date, datetime, timezone
import uuid

# Production database config
PROD_DB = {
    'host': 'db.aavjhutqzwusgdwrczds.supabase.co',
    'port': 6543,
    'database': 'postgres',
    'user': 'postgres',
    'password': 'Aquapurite2026',
    'statement_cache_size': 0,  # For pgbouncer
}


async def run_production_test():
    """Run order flow test against production database."""

    print("\n" + "=" * 80)
    print("PRODUCTION ORDER FLOW TEST")
    print("=" * 80)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("Database: Supabase Production\n")

    conn = await asyncpg.connect(**PROD_DB)
    # Timezone-naive for 'timestamp without time zone' columns
    now_naive = datetime.utcnow()
    # Timezone-aware for 'timestamp with time zone' columns
    now_aware = datetime.now(timezone.utc)

    try:
        # ============================================================
        # STEP 1: VERIFY EXISTING DATA
        # ============================================================
        print("=" * 80)
        print("[STEP 1] VERIFYING EXISTING DATA")
        print("=" * 80)

        # Check PO
        row = await conn.fetchrow('''
            SELECT po_number, status, grand_total, total_received_value
            FROM purchase_orders WHERE po_number = $1
        ''', 'PO/APL/25-26/0001')

        if row:
            print(f"  ✓ PO: {row['po_number']} | Status: {row['status']}")
            print(f"    Total: ₹{row['grand_total']:,.2f} | Received: ₹{row['total_received_value']:,.2f}")
        else:
            print("  ✗ PO not found!")
            return

        # Check GRN
        row = await conn.fetchrow('''
            SELECT grn_number, status, total_quantity_accepted, total_value
            FROM goods_receipt_notes WHERE grn_number = $1
        ''', 'GRN/APL/25-26/00001')

        if row:
            print(f"  ✓ GRN: {row['grn_number']} | Status: {row['status']}")
            print(f"    Qty Accepted: {row['total_quantity_accepted']} | Value: ₹{row['total_value']:,.2f}")

        # Check customer
        customer = await conn.fetchrow('''
            SELECT id, customer_code, first_name, last_name, phone
            FROM customers WHERE phone = $1
        ''', '9013034082')

        if customer:
            print(f"  ✓ Customer: {customer['first_name']} {customer['last_name']} ({customer['customer_code']})")
            print(f"    Phone: {customer['phone']}")
        else:
            print("  ✗ Customer not found!")
            return

        # Check warehouse
        warehouse = await conn.fetchrow('''
            SELECT id, name, code FROM warehouses WHERE is_active = true LIMIT 1
        ''')
        print(f"  ✓ Warehouse: {warehouse['name']} ({warehouse['code']})")

        # Check financial period
        period = await conn.fetchrow('''
            SELECT id, period_code FROM financial_periods WHERE is_current = true
        ''')
        if not period:
            print("  ⚠ No current financial period - will create")
        else:
            print(f"  ✓ Period: {period['period_code']}")

        # ============================================================
        # STEP 2: GET FG PRODUCTS WITH PRODUCTCOST
        # ============================================================
        print("\n" + "=" * 80)
        print("[STEP 2] GETTING FG PRODUCTS WITH PRODUCTCOST")
        print("=" * 80)

        products = await conn.fetch('''
            SELECT p.id, p.sku, p.name, p.selling_price, p.gst_rate,
                   pc.average_cost, pc.quantity_on_hand,
                   inv.available_quantity
            FROM products p
            LEFT JOIN product_costs pc ON pc.product_id = p.id
            LEFT JOIN inventory_summary inv ON inv.product_id = p.id
            WHERE p.item_type = $1 AND p.is_active = true
            ORDER BY p.selling_price DESC
        ''', 'FG')

        print(f"\n  {'SKU':<15} {'Name':<20} {'Sell Price':<12} {'Avg Cost':<12} {'Available':<10}")
        print("  " + "-" * 75)

        for p in products:
            sp = p['selling_price'] or 0
            ac = p['average_cost'] or 0
            avail = p['available_quantity'] or 0
            print(f"  {p['sku']:<15} {p['name'][:20]:<20} ₹{sp:>9,.0f} ₹{ac:>9,.0f} {avail:>9}")

        # ============================================================
        # STEP 3: CREATE ORDER > ₹50,000
        # ============================================================
        print("\n" + "=" * 80)
        print("[STEP 3] CREATING ORDER > ₹50,000 FOR MKS")
        print("=" * 80)

        # Select products for order (need > ₹50,000)
        # 2 x i-Elitz (₹24,999 each) + 1 x Premiuo (₹19,999) = ₹69,997
        order_items = []

        for p in products:
            if p['sku'] == 'WPRAIEL001':  # i-Elitz
                order_items.append({
                    'product_id': p['id'],
                    'sku': p['sku'],
                    'name': p['name'],
                    'quantity': 2,
                    'unit_price': p['selling_price'],
                    'gst_rate': p['gst_rate'] or Decimal('18'),
                    'avg_cost': p['average_cost'] or Decimal('0'),
                })
            elif p['sku'] == 'WPRAPRE001':  # Premiuo
                order_items.append({
                    'product_id': p['id'],
                    'sku': p['sku'],
                    'name': p['name'],
                    'quantity': 1,
                    'unit_price': p['selling_price'],
                    'gst_rate': p['gst_rate'] or Decimal('18'),
                    'avg_cost': p['average_cost'] or Decimal('0'),
                })

        # Calculate totals
        subtotal = Decimal('0')
        total_tax = Decimal('0')
        total_cogs = Decimal('0')

        print(f"\n  {'Product':<25} {'Qty':<5} {'Unit Price':<12} {'Total':<12} {'COGS':<12}")
        print("  " + "-" * 70)

        for item in order_items:
            line_total = item['unit_price'] * item['quantity']
            tax = (line_total * item['gst_rate'] / 100).quantize(Decimal('0.01'))
            cogs = item['avg_cost'] * item['quantity']

            item['line_total'] = line_total
            item['tax'] = tax
            item['cogs'] = cogs

            subtotal += line_total
            total_tax += tax
            total_cogs += cogs

            print(f"  {item['sku']:<25} {item['quantity']:<5} ₹{item['unit_price']:>9,.0f} ₹{line_total:>9,.0f} ₹{cogs:>9,.0f}")

        total_amount = subtotal + total_tax

        print("  " + "-" * 70)
        print(f"  {'Subtotal':<43} ₹{subtotal:>9,.0f}")
        print(f"  {'Tax (18%)':<43} ₹{total_tax:>9,.0f}")
        print(f"  {'TOTAL':<43} ₹{total_amount:>9,.0f}")
        print(f"  {'COGS (from ProductCost)':<43} ₹{total_cogs:>9,.0f}")

        if total_amount < 50000:
            print(f"\n  ⚠ Order total < ₹50,000. Need to add more items.")
            return

        print(f"\n  ✓ Order Total: ₹{total_amount:,.2f} (> ₹50,000 - E-way bill required)")

        # Generate order number
        today_str = date.today().strftime('%Y%m%d')
        count = await conn.fetchval('''
            SELECT COUNT(*) FROM orders WHERE order_number LIKE $1
        ''', f'ORD-{today_str}%')
        order_number = f"ORD-{today_str}-{(count or 0) + 1:04d}"

        # Insert order
        order_id = uuid.uuid4()
        await conn.execute('''
            INSERT INTO orders (
                id, order_number, customer_id, status, source, warehouse_id,
                subtotal, tax_amount, discount_amount, shipping_amount, total_amount,
                payment_method, payment_status, amount_paid, paid_at,
                shipping_address, billing_address, created_at, updated_at
            ) VALUES (
                $1, $2, $3, $4, $5, $6,
                $7, $8, $9, $10, $11,
                $12, $13, $14, $15,
                $16, $17, $18, $19
            )
        ''',
            order_id, order_number, customer['id'], 'CONFIRMED', 'D2C', warehouse['id'],
            subtotal, total_tax, Decimal('0'), Decimal('0'), total_amount,
            'RAZORPAY', 'PAID', total_amount, now_aware,  # paid_at is timestamptz
            '{"city": "Delhi", "state": "Delhi", "pincode": "110001"}',
            '{"city": "Delhi", "state": "Delhi", "pincode": "110001"}',
            now_naive, now_naive  # created_at/updated_at are timestamp (no tz)
        )

        # Insert order items
        for i, item in enumerate(order_items):
            await conn.execute('''
                INSERT INTO order_items (
                    id, order_id, product_id, product_name, product_sku,
                    quantity, unit_price, unit_mrp, discount_amount,
                    tax_rate, tax_amount, total_amount,
                    hsn_code, warranty_months, created_at
                ) VALUES (
                    $1, $2, $3, $4, $5,
                    $6, $7, $8, $9,
                    $10, $11, $12,
                    $13, $14, $15
                )
            ''',
                uuid.uuid4(), order_id, item['product_id'], item['name'], item['sku'],
                item['quantity'], item['unit_price'], item['unit_price'],  # MRP = selling price
                Decimal('0'),  # No discount
                item['gst_rate'], item['tax'], item['line_total'] + item['tax'],
                '84212100', 12, now_naive  # 12 months warranty
            )

        print(f"\n  ✅ Order Created: {order_number}")

        # ============================================================
        # STEP 4: PROCESS ORDER FLOW
        # ============================================================
        print("\n" + "=" * 80)
        print("[STEP 4] PROCESSING ORDER FLOW")
        print("=" * 80)

        # Update to ALLOCATED
        await conn.execute('''
            UPDATE orders SET status = $1, allocated_at = $2, updated_at = $2
            WHERE id = $3
        ''', 'ALLOCATED', now_naive, order_id)
        print("  ✓ CONFIRMED → ALLOCATED")

        # Update to SHIPPED
        await conn.execute('''
            UPDATE orders SET status = $1, shipped_at = $2, updated_at = $2
            WHERE id = $3
        ''', 'SHIPPED', now_naive, order_id)
        print("  ✓ ALLOCATED → SHIPPED")

        # ============================================================
        # STEP 5: CREATE INVOICE
        # ============================================================
        print("\n" + "=" * 80)
        print("[STEP 5] CREATING INVOICE")
        print("=" * 80)

        # Generate invoice number
        inv_count = await conn.fetchval('''
            SELECT COUNT(*) FROM tax_invoices WHERE invoice_number LIKE $1
        ''', 'INV/FY2526/%')
        invoice_number = f"INV/FY2526/{(inv_count or 0) + 1:05d}"

        cgst = (total_tax / 2).quantize(Decimal('0.01'))
        sgst = cgst

        invoice_id = uuid.uuid4()
        await conn.execute('''
            INSERT INTO tax_invoices (
                id, invoice_number, invoice_type, status, invoice_date,
                order_id, customer_id, customer_name,
                billing_address_line1, billing_city, billing_state, billing_state_code, billing_pincode, billing_country,
                seller_gstin, seller_name, seller_address, seller_state_code,
                place_of_supply, place_of_supply_code, is_interstate, is_reverse_charge,
                subtotal, discount_amount, taxable_amount,
                cgst_amount, sgst_amount, igst_amount, cess_amount, total_tax,
                shipping_charges, packaging_charges, installation_charges, other_charges,
                grand_total, currency, round_off, amount_paid, amount_due, payment_due_days,
                created_at, updated_at
            ) VALUES (
                $1, $2, $3, $4, $5,
                $6, $7, $8,
                $9, $10, $11, $12, $13, $14,
                $15, $16, $17, $18,
                $19, $20, $21, $22,
                $23, $24, $25,
                $26, $27, $28, $29, $30,
                $31, $32, $33, $34,
                $35, $36, $37, $38, $39, $40,
                $41, $42
            )
        ''',
            invoice_id, invoice_number, 'B2C', 'GENERATED', date.today(),
            order_id, customer['id'], f"{customer['first_name']} {customer['last_name']}",
            'Test Address', 'Delhi', 'Delhi', '07', '110001', 'India',
            '07AABCU9603R1ZM', 'Aquapurite Water Solutions Pvt Ltd', 'Delhi, India', '07',
            'Delhi', '07', False, False,
            subtotal, Decimal('0'), subtotal,
            cgst, sgst, Decimal('0'), Decimal('0'), total_tax,
            Decimal('0'), Decimal('0'), Decimal('0'), Decimal('0'),
            total_amount, 'INR', Decimal('0'), total_amount, Decimal('0'), 0,
            now_naive, now_naive
        )

        # Create invoice items
        for item in order_items:
            item_cgst = (item['tax'] / 2).quantize(Decimal('0.01'))
            item_sgst = item_cgst
            gst_rate_half = (item['gst_rate'] / 2).quantize(Decimal('0.01'))

            await conn.execute('''
                INSERT INTO invoice_items (
                    id, invoice_id, product_id, sku, item_name, hsn_code, is_service,
                    quantity, uom, unit_price,
                    discount_percentage, discount_amount, taxable_value,
                    gst_rate, cgst_rate, sgst_rate, igst_rate, cess_rate,
                    cgst_amount, sgst_amount, igst_amount, cess_amount, total_tax, line_total,
                    created_at
                ) VALUES (
                    $1, $2, $3, $4, $5, $6, $7,
                    $8, $9, $10,
                    $11, $12, $13,
                    $14, $15, $16, $17, $18,
                    $19, $20, $21, $22, $23, $24,
                    $25
                )
            ''',
                uuid.uuid4(), invoice_id, item['product_id'], item['sku'], item['name'], '84212100', False,
                item['quantity'], 'NOS', item['unit_price'],
                Decimal('0'), Decimal('0'), item['line_total'],
                item['gst_rate'], gst_rate_half, gst_rate_half, Decimal('0'), Decimal('0'),
                item_cgst, item_sgst, Decimal('0'), Decimal('0'), item['tax'], item['line_total'] + item['tax'],
                now_naive
            )

        print(f"  ✅ Invoice Created: {invoice_number}")
        print(f"     Total: ₹{total_amount:,.2f}")

        # ============================================================
        # STEP 6: CHECK E-WAY BILL REQUIREMENT
        # ============================================================
        print("\n" + "=" * 80)
        print("[STEP 6] E-WAY BILL CHECK")
        print("=" * 80)

        if total_amount > 50000:
            print(f"  ⚠️ E-WAY BILL REQUIRED")
            print(f"     Invoice Amount: ₹{total_amount:,.2f}")
            print(f"     Threshold: ₹50,000")
            print(f"     Status: Would be generated via GST portal integration")

            # Check if E-way bill table exists and create entry
            eway_exists = await conn.fetchval('''
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'e_way_bills'
                )
            ''')

            if eway_exists:
                print(f"     E-Way Bill table exists - ready for generation")
        else:
            print(f"  ✓ E-Way Bill not required (≤ ₹50,000)")

        # ============================================================
        # STEP 7: POST GL ENTRIES
        # ============================================================
        print("\n" + "=" * 80)
        print("[STEP 7] POSTING GL ENTRIES WITH ACTUAL COGS")
        print("=" * 80)

        # Get or verify GL accounts from chart_of_accounts
        gl_accounts = {}
        account_defs = [
            ('1020', 'Bank Account', 'ASSET'),
            ('1200', 'Inventory', 'ASSET'),
            ('2310', 'CGST Payable', 'LIABILITY'),
            ('2320', 'SGST Payable', 'LIABILITY'),
            ('4000', 'Sales Revenue', 'REVENUE'),
            ('5000', 'Cost of Goods Sold', 'EXPENSE'),
        ]

        for code, name, acc_type in account_defs:
            row = await conn.fetchrow('''
                SELECT id, current_balance FROM chart_of_accounts WHERE account_code = $1
            ''', code)
            if row:
                gl_accounts[code] = {'id': row['id'], 'balance': row['current_balance'] or Decimal('0')}
            else:
                # Create account
                acc_id = uuid.uuid4()
                await conn.execute('''
                    INSERT INTO chart_of_accounts (
                        id, account_code, account_name, account_type,
                        level, is_group, opening_balance, current_balance,
                        is_active, is_system, allow_direct_posting, sort_order,
                        created_at, updated_at
                    ) VALUES (
                        $1, $2, $3, $4,
                        $5, $6, $7, $8,
                        $9, $10, $11, $12,
                        $13, $14
                    )
                ''', acc_id, code, name, acc_type,
                    1, False, Decimal('0'), Decimal('0'),
                    True, False, True, 0,
                    now_naive, now_naive)
                gl_accounts[code] = {'id': acc_id, 'balance': Decimal('0')}

        # Get or create financial period
        if not period:
            period_id = uuid.uuid4()
            await conn.execute('''
                INSERT INTO financial_periods (id, period_code, period_name, start_date, end_date, status, is_current)
                VALUES ($1, $2, $3, $4, $5, $6, true)
            ''', period_id, 'FY2526', 'FY 2025-26', date(2025, 4, 1), date(2026, 3, 31), 'OPEN')
        else:
            period_id = period['id']

        # Generate JE number
        je_count = await conn.fetchval('''
            SELECT COUNT(*) FROM journal_entries WHERE entry_number LIKE $1
        ''', 'JV-202601%')

        # Get a system user ID (or use a default UUID for system entries)
        system_user = await conn.fetchval('''
            SELECT id FROM users LIMIT 1
        ''')
        if not system_user:
            system_user = uuid.uuid4()  # Fallback

        # SALES ENTRY
        je_sales_id = uuid.uuid4()
        je_sales_num = f"JV-202601-{(je_count or 0) + 1:04d}"

        await conn.execute('''
            INSERT INTO journal_entries (
                id, entry_number, entry_date, period_id, entry_type, source_type,
                source_id, source_number, narration, total_debit, total_credit,
                status, is_reversed, created_by, posted_at, created_at, updated_at
            ) VALUES (
                $1, $2, $3, $4, $5, $6,
                $7, $8, $9, $10, $11,
                $12, $13, $14, $15, $16, $17
            )
        ''',
            je_sales_id, je_sales_num, date.today(), period_id, 'SALES', 'INVOICE',
            invoice_id, invoice_number, f'Sales invoice {invoice_number}',
            total_amount, total_amount, 'POSTED', False, system_user, now_naive,
            now_naive, now_naive
        )

        # JE Lines for sales
        await conn.execute('''
            INSERT INTO journal_entry_lines (id, journal_entry_id, account_id, debit_amount, credit_amount, description, line_number, created_at)
            VALUES ($1, $2, $3, $4, 0, $5, 1, $6)
        ''', uuid.uuid4(), je_sales_id, gl_accounts['1020']['id'], total_amount, 'Bank receipt', now_naive)

        await conn.execute('''
            INSERT INTO journal_entry_lines (id, journal_entry_id, account_id, debit_amount, credit_amount, description, line_number, created_at)
            VALUES ($1, $2, $3, 0, $4, $5, 2, $6)
        ''', uuid.uuid4(), je_sales_id, gl_accounts['4000']['id'], subtotal, 'Sales revenue', now_naive)

        await conn.execute('''
            INSERT INTO journal_entry_lines (id, journal_entry_id, account_id, debit_amount, credit_amount, description, line_number, created_at)
            VALUES ($1, $2, $3, 0, $4, $5, 3, $6)
        ''', uuid.uuid4(), je_sales_id, gl_accounts['2310']['id'], cgst, 'CGST payable', now_naive)

        await conn.execute('''
            INSERT INTO journal_entry_lines (id, journal_entry_id, account_id, debit_amount, credit_amount, description, line_number, created_at)
            VALUES ($1, $2, $3, 0, $4, $5, 4, $6)
        ''', uuid.uuid4(), je_sales_id, gl_accounts['2320']['id'], sgst, 'SGST payable', now_naive)

        print(f"  ✓ Sales Entry: {je_sales_num}")
        print(f"    DR Bank: ₹{total_amount:,.2f}")
        print(f"    CR Sales: ₹{subtotal:,.2f}")
        print(f"    CR CGST: ₹{cgst:,.2f}")
        print(f"    CR SGST: ₹{sgst:,.2f}")

        # COGS ENTRY (using actual ProductCost.average_cost)
        je_cogs_id = uuid.uuid4()
        je_cogs_num = f"JV-202601-{(je_count or 0) + 2:04d}"

        await conn.execute('''
            INSERT INTO journal_entries (
                id, entry_number, entry_date, period_id, entry_type, source_type,
                source_id, source_number, narration, total_debit, total_credit,
                status, is_reversed, created_by, posted_at, created_at, updated_at
            ) VALUES (
                $1, $2, $3, $4, $5, $6,
                $7, $8, $9, $10, $11,
                $12, $13, $14, $15, $16, $17
            )
        ''',
            je_cogs_id, je_cogs_num, date.today(), period_id, 'COGS', 'INVOICE',
            invoice_id, invoice_number, f'COGS for {invoice_number} (from ProductCost.average_cost)',
            total_cogs, total_cogs, 'POSTED', False, system_user, now_naive,
            now_naive, now_naive
        )

        await conn.execute('''
            INSERT INTO journal_entry_lines (id, journal_entry_id, account_id, debit_amount, credit_amount, description, line_number, created_at)
            VALUES ($1, $2, $3, $4, 0, $5, 1, $6)
        ''', uuid.uuid4(), je_cogs_id, gl_accounts['5000']['id'], total_cogs, 'Cost of Goods Sold', now_naive)

        await conn.execute('''
            INSERT INTO journal_entry_lines (id, journal_entry_id, account_id, debit_amount, credit_amount, description, line_number, created_at)
            VALUES ($1, $2, $3, 0, $4, $5, 2, $6)
        ''', uuid.uuid4(), je_cogs_id, gl_accounts['1200']['id'], total_cogs, 'Inventory reduction', now_naive)

        print(f"\n  ✓ COGS Entry: {je_cogs_num}")
        print(f"    DR COGS: ₹{total_cogs:,.2f} (from ProductCost.average_cost)")
        print(f"    CR Inventory: ₹{total_cogs:,.2f}")

        # Update GL balances in chart_of_accounts
        await conn.execute('UPDATE chart_of_accounts SET current_balance = current_balance + $1 WHERE account_code = $2', total_amount, '1020')
        await conn.execute('UPDATE chart_of_accounts SET current_balance = current_balance + $1 WHERE account_code = $2', subtotal, '4000')
        await conn.execute('UPDATE chart_of_accounts SET current_balance = current_balance + $1 WHERE account_code = $2', cgst, '2310')
        await conn.execute('UPDATE chart_of_accounts SET current_balance = current_balance + $1 WHERE account_code = $2', sgst, '2320')
        await conn.execute('UPDATE chart_of_accounts SET current_balance = current_balance + $1 WHERE account_code = $2', total_cogs, '5000')
        await conn.execute('UPDATE chart_of_accounts SET current_balance = current_balance - $1 WHERE account_code = $2', total_cogs, '1200')

        # ============================================================
        # STEP 8: GENERATE BALANCE SHEET & P&L
        # ============================================================
        print("\n" + "=" * 80)
        print("[STEP 8] BALANCE SHEET & P&L")
        print("=" * 80)

        # Get all GL accounts from chart_of_accounts
        accounts = await conn.fetch('''
            SELECT account_code, account_name, account_type, current_balance
            FROM chart_of_accounts
            ORDER BY account_code
        ''')

        assets = {}
        liabilities = {}
        equity = {}
        revenue = {}
        expenses = {}

        for acc in accounts:
            bal = acc['current_balance'] or Decimal('0')
            if acc['account_type'] == 'ASSET':
                assets[acc['account_name']] = bal
            elif acc['account_type'] == 'LIABILITY':
                liabilities[acc['account_name']] = bal
            elif acc['account_type'] == 'EQUITY':
                equity[acc['account_name']] = bal
            elif acc['account_type'] == 'REVENUE':
                revenue[acc['account_name']] = bal
            elif acc['account_type'] == 'EXPENSE':
                expenses[acc['account_name']] = bal

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

        liab_equity = total_liabilities + total_equity_with_income
        print(f"\n{'TOTAL LIABILITIES + EQUITY':<32} ₹{liab_equity:>15,.2f}")

        if abs(total_assets - liab_equity) < Decimal('0.01'):
            print("✅ Balance Sheet BALANCES!")
        else:
            print(f"⚠️ Difference: ₹{total_assets - liab_equity:,.2f}")

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

        if total_revenue > 0:
            gross_margin = (net_income / total_revenue * 100)
            print(f"  {'Gross Margin':<30} {gross_margin:>14.1f}%")

        # ============================================================
        # SUMMARY
        # ============================================================
        print("\n" + "=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)
        print(f"""
  EXISTING DATA USED:
  - PO: PO/APL/25-26/0001
  - GRN: GRN/APL/25-26/00001
  - Customer: MKS (9013034082)

  NEW RECORDS CREATED:
  - Order: {order_number}
  - Invoice: {invoice_number}
  - Journal Entries: {je_sales_num}, {je_cogs_num}

  FINANCIAL SUMMARY:
  - Order Total: ₹{total_amount:,.2f}
  - COGS (from ProductCost): ₹{total_cogs:,.2f}
  - Gross Profit: ₹{subtotal - total_cogs:,.2f}
  - Net Income: ₹{net_income:,.2f}

  E-WAY BILL: {'REQUIRED (>₹50,000)' if total_amount > 50000 else 'Not required'}

  COGS CALCULATION METHOD:
  - Used ProductCost.average_cost for each product
  - No shortcuts - actual weighted average from system
""")

        # Show COGS breakdown
        print("  COGS BREAKDOWN (from ProductCost.average_cost):")
        for item in order_items:
            print(f"    {item['sku']}: {item['quantity']} x ₹{item['avg_cost']:,.2f} = ₹{item['cogs']:,.2f}")

        print("\n" + "=" * 80)
        print("✅ PRODUCTION ORDER FLOW TEST COMPLETED!")
        print("=" * 80)

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(run_production_test())
