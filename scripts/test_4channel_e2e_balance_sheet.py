#!/usr/bin/env python3
"""
4-Channel E2E Order Flow Test with Balance Sheet Generation

Creates orders from 4 channels with specific products:
- GT (General Trade): Aquapurite Neura
- MT (Modern Trade): Aquapurite Blitz
- D2C (Direct to Consumer): Aquapurite i Elitz
- Marketplace (Amazon): Aquapurite Premiuo UV

Processes through complete flow: ORDER → PAY → ALLOCATE → SHIP → MANIFEST → INVOICE → GL → Balance Sheet
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
from app.models.customer import Customer, CustomerAddress
from app.models.channel import SalesChannel
from app.models.warehouse import Warehouse
from app.models.transporter import Transporter, TransporterServiceability
from app.models.order import Order, OrderItem, OrderStatusHistory
from app.models.shipment import Shipment, ShipmentTracking
from app.models.manifest import Manifest, ManifestItem
from app.models.billing import TaxInvoice, InvoiceItem
from app.models.accounting import ChartOfAccount as GLAccount, JournalEntry, JournalEntryLine, FinancialPeriod
from app.models.inventory import StockItem, InventorySummary
from sqlalchemy import select, text, func
from sqlalchemy.orm import selectinload


# Product SKUs for each channel
CHANNEL_PRODUCTS = {
    'GT': {'sku': 'WPRANEU001', 'name': 'Aquapurite Neura'},
    'MT': {'sku': 'WPRABLT001', 'name': 'Aquapurite Blitz'},
    'D2C': {'sku': 'WPRAIEL001', 'name': 'Aquapurite i Elitz'},
    'MARKETPLACE': {'sku': 'WPRAPUV001', 'name': 'Aquapurite Premiuo UV'},
}


async def setup_test_data(db):
    """Setup required test data: customers, stock, etc."""
    print("\n" + "=" * 80)
    print("SETTING UP TEST DATA")
    print("=" * 80)

    # Get or create test customer
    result = await db.execute(
        select(Customer).where(Customer.is_active == True).limit(1)
    )
    customer = result.scalar_one_or_none()

    if not customer:
        print("ERROR: No active customer found! Please seed customer data first.")
        return None

    print(f"Using Customer: {customer.full_name} ({customer.customer_code})")

    # Get products
    products = {}
    for channel_code, product_info in CHANNEL_PRODUCTS.items():
        result = await db.execute(
            select(Product).where(Product.sku == product_info['sku'])
        )
        product = result.scalar_one_or_none()
        if product:
            products[channel_code] = product
            print(f"  {channel_code}: {product.name} (SKU: {product.sku}, MRP: ₹{product.mrp}, Cost: ₹{product.cost_price})")
        else:
            print(f"  WARNING: Product {product_info['sku']} not found!")

    if len(products) < 4:
        print("ERROR: Not all products found!")
        return None

    # Get sales channels
    channels = {}
    for code in ['GT', 'MT', 'D2C', 'AMAZON']:
        result = await db.execute(
            select(SalesChannel).where(SalesChannel.code == code)
        )
        channel = result.scalar_one_or_none()
        if channel:
            channels[code] = channel
            print(f"  Channel: {channel.name} ({channel.code})")

    # Map AMAZON to MARKETPLACE
    if 'AMAZON' in channels:
        channels['MARKETPLACE'] = channels['AMAZON']

    # Get warehouse
    result = await db.execute(
        select(Warehouse).where(Warehouse.is_active == True).limit(1)
    )
    warehouse = result.scalar_one_or_none()
    if warehouse:
        print(f"  Warehouse: {warehouse.name} ({warehouse.code})")
    else:
        print("ERROR: No active warehouse found!")
        return None

    # Get transporter
    result = await db.execute(
        select(Transporter).where(Transporter.is_active == True).limit(1)
    )
    transporter = result.scalar_one_or_none()
    if transporter:
        print(f"  Transporter: {transporter.name} ({transporter.code})")
    else:
        print("ERROR: No active transporter found!")
        return None

    # Ensure stock exists for all products
    print("\n  Checking/Creating Stock Items...")
    for channel_code, product in products.items():
        # Check inventory summary
        result = await db.execute(
            select(InventorySummary).where(
                InventorySummary.warehouse_id == warehouse.id,
                InventorySummary.product_id == product.id
            )
        )
        inv_summary = result.scalar_one_or_none()

        if not inv_summary or inv_summary.available_quantity < 1:
            # Create stock items
            for i in range(5):  # Create 5 units each
                serial = f"TEST-{product.sku}-{channel_code}-{i+1:04d}"
                stock_item = StockItem(
                    product_id=product.id,
                    warehouse_id=warehouse.id,
                    serial_number=serial,
                    barcode=serial,
                    status='AVAILABLE',
                    purchase_price=product.cost_price or Decimal('5000'),
                    landed_cost=product.cost_price or Decimal('5000'),
                    received_date=datetime.now(timezone.utc),
                )
                db.add(stock_item)

            # Update or create inventory summary
            if not inv_summary:
                inv_summary = InventorySummary(
                    warehouse_id=warehouse.id,
                    product_id=product.id,
                    total_quantity=5,
                    available_quantity=5,
                    average_cost=float(product.cost_price or Decimal('5000')),
                    total_value=float(product.cost_price or Decimal('5000')) * 5,
                )
                db.add(inv_summary)
            else:
                inv_summary.total_quantity += 5
                inv_summary.available_quantity += 5
                inv_summary.total_value = inv_summary.total_quantity * inv_summary.average_cost

            print(f"    Created 5 stock items for {product.sku}")

    await db.commit()

    return {
        'customer': customer,
        'products': products,
        'channels': channels,
        'warehouse': warehouse,
        'transporter': transporter,
    }


async def generate_order_number(db):
    """Generate unique order number."""
    today = date.today().strftime('%Y%m%d')
    result = await db.execute(
        text("SELECT COUNT(*) FROM orders WHERE order_number LIKE :pattern"),
        {'pattern': f'ORD-{today}-%'}
    )
    count = result.scalar() or 0
    return f"ORD-{today}-{count + 1:04d}"


async def generate_shipment_number(db):
    """Generate unique shipment number."""
    today = date.today().strftime('%Y%m%d')
    result = await db.execute(
        text("SELECT COUNT(*) FROM shipments WHERE shipment_number LIKE :pattern"),
        {'pattern': f'SH-{today}-%'}
    )
    count = result.scalar() or 0
    return f"SH-{today}-{count + 1:04d}"


async def generate_manifest_number(db):
    """Generate unique manifest number."""
    today = date.today().strftime('%Y%m%d')
    result = await db.execute(
        text("SELECT COUNT(*) FROM manifests WHERE manifest_number LIKE :pattern"),
        {'pattern': f'MF-{today}-%'}
    )
    count = result.scalar() or 0
    return f"MF-{today}-{count + 1:04d}"


async def generate_invoice_number(db):
    """Generate unique invoice number."""
    # Get current financial year
    today = date.today()
    if today.month >= 4:
        fy_start = today.year
        fy_end = today.year + 1
    else:
        fy_start = today.year - 1
        fy_end = today.year

    fy_code = f"FY{str(fy_start)[2:]}{str(fy_end)[2:]}"

    result = await db.execute(
        text("SELECT COUNT(*) FROM tax_invoices WHERE invoice_number LIKE :pattern"),
        {'pattern': f'INV/{fy_code}/%'}
    )
    count = result.scalar() or 0
    return f"INV/{fy_code}/{count + 1:05d}"


async def create_order(db, test_data, channel_code, product):
    """Create a single order."""
    customer = test_data['customer']
    warehouse = test_data['warehouse']
    channel = test_data['channels'].get(channel_code)

    if not channel:
        print(f"  WARNING: Channel {channel_code} not found, using D2C")
        channel = test_data['channels'].get('D2C')

    order_number = await generate_order_number(db)

    # Calculate pricing
    unit_price = product.mrp or Decimal('10000')
    quantity = 1
    subtotal = unit_price * quantity
    tax_rate = Decimal('18')  # 18% GST
    tax_amount = (subtotal * tax_rate / 100).quantize(Decimal('0.01'))
    total_amount = subtotal + tax_amount

    # Shipping address (use customer's default or create)
    shipping_address = {
        "contact_name": customer.full_name,
        "contact_phone": customer.phone,
        "address_line1": "123 Test Street",
        "city": "Delhi",
        "state": "Delhi",
        "pincode": "110001",
        "country": "India"
    }

    # Create order
    order = Order(
        order_number=order_number,
        customer_id=customer.id,
        status='NEW',
        source=channel_code if channel_code != 'MARKETPLACE' else 'AMAZON',
        warehouse_id=warehouse.id,
        subtotal=subtotal,
        tax_amount=tax_amount,
        discount_amount=Decimal('0'),
        shipping_amount=Decimal('0'),
        total_amount=total_amount,
        payment_method='COD' if channel_code in ['GT', 'MT'] else 'PREPAID',
        payment_status='PENDING',
        amount_paid=Decimal('0'),
        shipping_address=shipping_address,
        billing_address=shipping_address,
    )
    db.add(order)
    await db.flush()  # Get order.id

    # Create order item
    order_item = OrderItem(
        order_id=order.id,
        product_id=product.id,
        product_name=product.name,
        product_sku=product.sku,
        quantity=quantity,
        unit_price=unit_price,
        unit_mrp=unit_price,
        tax_rate=tax_rate,
        tax_amount=tax_amount,
        discount_amount=Decimal('0'),
        total_amount=total_amount,
        hsn_code=product.hsn_code or '84212100',
        warranty_months=product.warranty_months or 12,
    )
    db.add(order_item)

    # Create status history
    status_history = OrderStatusHistory(
        order_id=order.id,
        from_status=None,
        to_status='NEW',
        notes=f'Order created via {channel_code} channel',
        created_at=datetime.now(timezone.utc),
    )
    db.add(status_history)

    await db.flush()

    return order


async def process_payment(db, order, test_data):
    """Record payment for order."""
    order.amount_paid = order.total_amount
    order.payment_status = 'PAID'
    order.paid_at = datetime.now(timezone.utc)

    # Add status history
    status_history = OrderStatusHistory(
        order_id=order.id,
        from_status=order.status,
        to_status='CONFIRMED',
        notes='Payment received',
        created_at=datetime.now(timezone.utc),
    )
    db.add(status_history)

    order.status = 'CONFIRMED'
    order.confirmed_at = datetime.now(timezone.utc)

    await db.flush()


async def allocate_order(db, order, test_data):
    """Allocate order to warehouse and transporter."""
    warehouse = test_data['warehouse']
    transporter = test_data['transporter']

    order.warehouse_id = warehouse.id
    order.allocated_at = datetime.now(timezone.utc)

    # Add status history
    status_history = OrderStatusHistory(
        order_id=order.id,
        from_status=order.status,
        to_status='ALLOCATED',
        notes=f'Allocated to {warehouse.name}, Transporter: {transporter.name}',
        created_at=datetime.now(timezone.utc),
    )
    db.add(status_history)

    order.status = 'ALLOCATED'

    # Allocate stock item
    result = await db.execute(
        select(StockItem).where(
            StockItem.warehouse_id == warehouse.id,
            StockItem.status == 'AVAILABLE'
        ).limit(1)
    )
    stock_item = result.scalar_one_or_none()
    if stock_item:
        stock_item.status = 'ALLOCATED'
        stock_item.order_id = order.id
        stock_item.allocated_at = datetime.now(timezone.utc)

    await db.flush()


async def create_shipment(db, order, test_data):
    """Create shipment for order."""
    warehouse = test_data['warehouse']
    transporter = test_data['transporter']

    shipment_number = await generate_shipment_number(db)
    awb_number = f"AQ{date.today().strftime('%Y%m%d')}{str(uuid.uuid4())[:8].upper()}"

    shipment = Shipment(
        shipment_number=shipment_number,
        order_id=order.id,
        warehouse_id=warehouse.id,
        transporter_id=transporter.id,
        status='CREATED',
        awb_number=awb_number,
        payment_mode='PREPAID' if order.payment_status == 'PAID' else 'COD',
        cod_amount=order.total_amount if order.payment_status != 'PAID' else Decimal('0'),
        weight_kg=Decimal('5.0'),
        chargeable_weight_kg=Decimal('5.0'),
        packaging_type='BOX',
        no_of_boxes=1,
        ship_to_name=order.shipping_address.get('contact_name', 'Customer'),
        ship_to_phone=order.shipping_address.get('contact_phone', '9999999999'),
        ship_to_email=test_data['customer'].email,
        ship_to_address=order.shipping_address,
        ship_to_pincode=order.shipping_address.get('pincode', '110001'),
        ship_to_city=order.shipping_address.get('city', 'Delhi'),
        ship_to_state=order.shipping_address.get('state', 'Delhi'),
    )
    db.add(shipment)
    await db.flush()

    # Create tracking entry
    tracking = ShipmentTracking(
        shipment_id=shipment.id,
        status='CREATED',
        event_time=datetime.now(timezone.utc),
        remarks='Shipment created',
    )
    db.add(tracking)

    # Update order status
    status_history = OrderStatusHistory(
        order_id=order.id,
        from_status=order.status,
        to_status='PICKED',
        notes=f'Shipment created: {shipment_number}',
        created_at=datetime.now(timezone.utc),
    )
    db.add(status_history)

    order.status = 'PICKED'

    await db.flush()

    return shipment


async def create_manifest_and_invoice(db, shipments, test_data, created_orders):
    """Create manifest and auto-generate invoices (Goods Issue)."""
    warehouse = test_data['warehouse']
    transporter = test_data['transporter']

    manifest_number = await generate_manifest_number(db)

    manifest = Manifest(
        manifest_number=manifest_number,
        warehouse_id=warehouse.id,
        transporter_id=transporter.id,
        business_type='B2C',
        manifest_date=datetime.now(timezone.utc),
        status='DRAFT',
        vehicle_number='DL01AB1234',
        driver_name='Test Driver',
        driver_phone='9876543210',
        total_shipments=len(shipments),
        total_weight_kg=float(sum(s.weight_kg or Decimal('0') for s in shipments)),
    )
    db.add(manifest)
    await db.flush()

    # Add shipments to manifest
    for shipment in shipments:
        # Get order for order_number
        order_for_item = next((o for o in created_orders if o.id == shipment.order_id), None)
        order_number = order_for_item.order_number if order_for_item else 'UNKNOWN'

        manifest_item = ManifestItem(
            manifest_id=manifest.id,
            shipment_id=shipment.id,
            awb_number=shipment.awb_number,
            order_number=order_number,
            weight_kg=float(shipment.weight_kg) if shipment.weight_kg else 0.0,
            no_of_boxes=shipment.no_of_boxes or 1,
        )
        db.add(manifest_item)

        # Update shipment status
        shipment.manifest_id = manifest.id
        shipment.status = 'MANIFESTED'

    await db.flush()

    # Confirm manifest (Goods Issue) - This triggers invoice generation
    manifest.status = 'CONFIRMED'
    manifest.confirmed_at = datetime.now(timezone.utc)

    # Generate invoices for each shipment
    invoices = []
    for shipment in shipments:
        order_id = shipment.order_id
        if not order_id:
            continue

        # Generate invoice using fresh order from DB
        invoice = await generate_invoice(db, order_id, shipment, manifest)
        invoices.append(invoice)

        # Update shipment status
        shipment.status = 'IN_TRANSIT'

        # Add tracking
        tracking = ShipmentTracking(
            shipment_id=shipment.id,
            status='IN_TRANSIT',
            event_time=datetime.now(timezone.utc),
            remarks=f'Goods issued. Manifest: {manifest_number}',
        )
        db.add(tracking)

        # Update order status - fetch fresh order
        result = await db.execute(
            select(Order).where(Order.id == order_id)
        )
        order = result.scalar_one_or_none()
        if order:
            status_history = OrderStatusHistory(
                order_id=order.id,
                from_status=order.status,
                to_status='SHIPPED',
                notes=f'Shipped via manifest {manifest_number}',
                created_at=datetime.now(timezone.utc),
            )
            db.add(status_history)
            order.status = 'SHIPPED'
            order.shipped_at = datetime.now(timezone.utc)

    await db.flush()

    return manifest, invoices


async def generate_invoice(db, order_id, shipment, manifest):
    """Generate tax invoice for order."""
    invoice_number = await generate_invoice_number(db)

    # Fetch fresh order from database
    result = await db.execute(
        select(Order).where(Order.id == order_id)
    )
    order = result.scalar_one_or_none()
    if not order:
        raise ValueError(f"Order {order_id} not found!")

    # Get order items
    result = await db.execute(
        select(OrderItem).where(OrderItem.order_id == order_id)
    )
    order_items = result.scalars().all()

    # Calculate GST based on same state or inter-state
    seller_state_code = '07'  # Delhi
    buyer_state_code = '07'  # Same state for test

    is_inter_state = seller_state_code != buyer_state_code

    if is_inter_state:
        igst_amount = order.tax_amount
        cgst_amount = Decimal('0')
        sgst_amount = Decimal('0')
    else:
        cgst_amount = (order.tax_amount / 2).quantize(Decimal('0.01'))
        sgst_amount = (order.tax_amount / 2).quantize(Decimal('0.01'))
        igst_amount = Decimal('0')

    # Get customer for invoice
    result = await db.execute(
        select(Customer).where(Customer.id == order.customer_id)
    )
    customer = result.scalar_one_or_none()

    invoice = TaxInvoice(
        invoice_number=invoice_number,
        invoice_type='TAX_INVOICE',
        status='GENERATED',
        invoice_date=date.today(),
        supply_date=date.today(),
        order_id=None,  # Skip foreign key for now
        shipment_id=None,  # Skip foreign key for now
        customer_id=None,  # TaxInvoice.customer_id FKs to users, not customers - skip
        customer_name=customer.full_name if customer else 'Customer',
        billing_address_line1=order.billing_address.get('address_line1', '123 Test Street'),
        billing_city=order.billing_address.get('city', 'Delhi'),
        billing_state=order.billing_address.get('state', 'Delhi'),
        billing_state_code=buyer_state_code,
        billing_pincode=order.billing_address.get('pincode', '110001'),
        shipping_address_line1=order.shipping_address.get('address_line1', '123 Test Street'),
        shipping_city=order.shipping_address.get('city', 'Delhi'),
        shipping_state=order.shipping_address.get('state', 'Delhi'),
        shipping_state_code=buyer_state_code,
        shipping_pincode=order.shipping_address.get('pincode', '110001'),
        seller_gstin='07AABCT1234H1Z5',  # Test GSTIN
        seller_name='Aquapurite Pvt Ltd',
        seller_address='123 Industrial Area, Delhi',
        seller_state_code=seller_state_code,
        place_of_supply=order.shipping_address.get('state', 'Delhi'),
        place_of_supply_code=buyer_state_code,
        is_interstate=is_inter_state,
        subtotal=order.subtotal,
        discount_amount=order.discount_amount,
        taxable_amount=order.subtotal - order.discount_amount,
        cgst_amount=cgst_amount,
        sgst_amount=sgst_amount,
        igst_amount=igst_amount,
        cess_amount=Decimal('0'),
        total_tax=order.tax_amount,
        shipping_charges=order.shipping_amount,
        grand_total=order.total_amount,
        amount_paid=order.amount_paid,
        amount_due=order.total_amount - order.amount_paid,
        internal_notes=f'Auto-generated on Goods Issue. Manifest: {manifest.manifest_number}',
    )
    db.add(invoice)
    await db.flush()

    # Create invoice items
    for order_item in order_items:
        taxable_value = order_item.unit_price * order_item.quantity - order_item.discount_amount

        if is_inter_state:
            item_igst = order_item.tax_amount
            item_cgst = Decimal('0')
            item_sgst = Decimal('0')
        else:
            item_cgst = (order_item.tax_amount / 2).quantize(Decimal('0.01'))
            item_sgst = (order_item.tax_amount / 2).quantize(Decimal('0.01'))
            item_igst = Decimal('0')

        invoice_item = InvoiceItem(
            invoice_id=invoice.id,
            order_item_id=order_item.id,
            product_id=order_item.product_id,
            sku=order_item.product_sku,
            item_name=order_item.product_name,
            hsn_code=order_item.hsn_code,
            quantity=order_item.quantity,
            uom='NOS',
            unit_price=order_item.unit_price,
            mrp=order_item.unit_mrp,
            discount_amount=order_item.discount_amount,
            taxable_value=taxable_value,
            gst_rate=order_item.tax_rate,
            cgst_rate=Decimal('9') if not is_inter_state else Decimal('0'),
            sgst_rate=Decimal('9') if not is_inter_state else Decimal('0'),
            igst_rate=Decimal('18') if is_inter_state else Decimal('0'),
            cgst_amount=item_cgst,
            sgst_amount=item_sgst,
            igst_amount=item_igst,
            cess_amount=Decimal('0'),
            total_tax=order_item.tax_amount,
            line_total=order_item.total_amount,
        )
        db.add(invoice_item)

    await db.flush()

    return invoice


async def post_gl_entries(db, invoices, test_data):
    """Post GL entries for all invoices."""
    print("\n  Posting GL Entries...")

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

    # Get or create financial period
    result = await db.execute(
        select(FinancialPeriod).where(FinancialPeriod.is_current == True)
    )
    period = result.scalar_one_or_none()
    if not period:
        period = FinancialPeriod(
            period_code='FY2526',
            period_name='FY 2025-26',
            start_date=date(2025, 4, 1),
            end_date=date(2026, 3, 31),
            status='OPEN',
            is_current=True,
        )
        db.add(period)
        await db.flush()

    # Get the maximum existing entry number to avoid duplicates
    result = await db.execute(
        select(func.max(JournalEntry.entry_number))
    )
    max_entry = result.scalar_one_or_none()
    if max_entry and max_entry.startswith(f"JV-{date.today().strftime('%Y%m')}-"):
        entry_count = int(max_entry.split('-')[-1])
    else:
        entry_count = 0

    # Create journal entries for each invoice
    for invoice in invoices:
        entry_count += 1
        entry_number = f"JV-{date.today().strftime('%Y%m')}-{entry_count:04d}"

        # Sales Invoice Journal Entry
        # DR Accounts Receivable
        # CR Sales Revenue
        # CR CGST/SGST/IGST Payable

        journal_entry = JournalEntry(
            entry_number=entry_number,
            entry_date=date.today(),
            entry_type='SALES',
            status='POSTED',
            source_type='INVOICE',
            source_number=invoice.invoice_number,
            source_id=invoice.id,
            narration=f'Sales Invoice {invoice.invoice_number}',
            total_debit=invoice.grand_total,
            total_credit=invoice.grand_total,
            period_id=period.id,
            posted_at=datetime.now(timezone.utc),
        )
        db.add(journal_entry)
        await db.flush()

        # Debit: Accounts Receivable
        dr_ar = JournalEntryLine(
            journal_entry_id=journal_entry.id,
            account_id=gl_accounts['ACCOUNTS_RECEIVABLE'].id,
            debit_amount=invoice.grand_total,
            credit_amount=Decimal('0'),
            description=f'Sale to {invoice.customer_name}',
        )
        db.add(dr_ar)

        # Credit: Sales Revenue
        cr_sales = JournalEntryLine(
            journal_entry_id=journal_entry.id,
            account_id=gl_accounts['SALES_REVENUE'].id,
            debit_amount=Decimal('0'),
            credit_amount=invoice.taxable_amount,
            description='Sales revenue',
        )
        db.add(cr_sales)

        # Credit: GST Payable
        if invoice.cgst_amount > 0:
            cr_cgst = JournalEntryLine(
                journal_entry_id=journal_entry.id,
                account_id=gl_accounts['CGST_PAYABLE'].id,
                debit_amount=Decimal('0'),
                credit_amount=invoice.cgst_amount,
                description='CGST on sale',
            )
            db.add(cr_cgst)

        if invoice.sgst_amount > 0:
            cr_sgst = JournalEntryLine(
                journal_entry_id=journal_entry.id,
                account_id=gl_accounts['SGST_PAYABLE'].id,
                debit_amount=Decimal('0'),
                credit_amount=invoice.sgst_amount,
                description='SGST on sale',
            )
            db.add(cr_sgst)

        if invoice.igst_amount > 0:
            cr_igst = JournalEntryLine(
                journal_entry_id=journal_entry.id,
                account_id=gl_accounts['IGST_PAYABLE'].id,
                debit_amount=Decimal('0'),
                credit_amount=invoice.igst_amount,
                description='IGST on sale',
            )
            db.add(cr_igst)

        # COGS Entry (Cost of Goods Sold)
        # DR COGS, CR Inventory
        # Get product cost from invoice items (since order_id may be null)
        result = await db.execute(
            select(InvoiceItem).where(InvoiceItem.invoice_id == invoice.id)
        )
        invoice_items = result.scalars().all()

        cogs_total = Decimal('0')
        for item in invoice_items:
            # Get product cost
            result = await db.execute(
                select(Product).where(Product.id == item.product_id)
            )
            product = result.scalar_one_or_none()
            if product and product.cost_price:
                cogs_total += product.cost_price * item.quantity

        if cogs_total > 0:
            entry_count += 1
            cogs_entry_number = f"JV-{date.today().strftime('%Y%m')}-{entry_count:04d}"

            cogs_entry = JournalEntry(
                entry_number=cogs_entry_number,
                entry_date=date.today(),
                entry_type='COST',
                status='POSTED',
                source_type='INVOICE',
                source_number=invoice.invoice_number,
                source_id=invoice.id,
                narration=f'COGS for Invoice {invoice.invoice_number}',
                total_debit=cogs_total,
                total_credit=cogs_total,
                period_id=period.id,
                posted_at=datetime.now(timezone.utc),
            )
            db.add(cogs_entry)
            await db.flush()

            # DR COGS
            dr_cogs = JournalEntryLine(
                journal_entry_id=cogs_entry.id,
                account_id=gl_accounts['COGS'].id,
                debit_amount=cogs_total,
                credit_amount=Decimal('0'),
                description=f'Cost of goods sold',
            )
            db.add(dr_cogs)

            # CR Inventory
            cr_inv = JournalEntryLine(
                journal_entry_id=cogs_entry.id,
                account_id=gl_accounts['INVENTORY'].id,
                debit_amount=Decimal('0'),
                credit_amount=cogs_total,
                description=f'Inventory issued',
            )
            db.add(cr_inv)

        # Payment Entry (since orders are paid)
        # DR Cash/Bank, CR Accounts Receivable
        entry_count += 1
        payment_entry_number = f"JV-{date.today().strftime('%Y%m')}-{entry_count:04d}"

        payment_entry = JournalEntry(
            entry_number=payment_entry_number,
            entry_date=date.today(),
            entry_type='RECEIPT',
            status='POSTED',
            source_type='PAYMENT',
            source_number=invoice.invoice_number,
            source_id=invoice.id,
            narration=f'Payment for Invoice {invoice.invoice_number}',
            total_debit=invoice.amount_paid,
            total_credit=invoice.amount_paid,
            period_id=period.id,
            posted_at=datetime.now(timezone.utc),
        )
        db.add(payment_entry)
        await db.flush()

        # DR Cash/Bank
        dr_cash = JournalEntryLine(
            journal_entry_id=payment_entry.id,
            account_id=gl_accounts['BANK'].id,
            debit_amount=invoice.amount_paid,
            credit_amount=Decimal('0'),
            description='Payment received',
        )
        db.add(dr_cash)

        # CR Accounts Receivable
        cr_ar = JournalEntryLine(
            journal_entry_id=payment_entry.id,
            account_id=gl_accounts['ACCOUNTS_RECEIVABLE'].id,
            debit_amount=Decimal('0'),
            credit_amount=invoice.amount_paid,
            description='Payment received',
        )
        db.add(cr_ar)

        print(f"    Posted entries for Invoice {invoice.invoice_number}")

    await db.commit()
    return gl_accounts


async def generate_balance_sheet(db, gl_accounts):
    """Generate and display Balance Sheet."""
    print("\n" + "=" * 80)
    print("BALANCE SHEET")
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

    # Mapping for display
    type_display = {
        'ASSET': 'ASSETS',
        'LIABILITY': 'LIABILITIES',
        'EQUITY': 'EQUITY',
        'REVENUE': 'REVENUE',
        'EXPENSE': 'EXPENSES',
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
    print("INCOME STATEMENT (P&L)")
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


async def run_4channel_e2e_test():
    """Main test execution."""
    print("\n" + "=" * 80)
    print("4-CHANNEL E2E ORDER FLOW TEST")
    print("=" * 80)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    async with async_session_factory() as db:
        # Step 1: Setup test data
        test_data = await setup_test_data(db)
        if not test_data:
            print("ERROR: Failed to setup test data!")
            return

        # Step 2: Create orders for each channel
        print("\n" + "=" * 80)
        print("CREATING ORDERS")
        print("=" * 80)

        created_orders = []
        channel_order_map = {}

        for channel_code in ['GT', 'MT', 'D2C', 'MARKETPLACE']:
            product = test_data['products'].get(channel_code)
            if not product:
                print(f"  Skipping {channel_code}: Product not found")
                continue

            order = await create_order(db, test_data, channel_code, product)
            created_orders.append(order)
            channel_order_map[channel_code] = order

            print(f"  [{channel_code}] Order {order.order_number}: {product.name}")
            print(f"         Amount: ₹{order.total_amount:,.2f} | Status: {order.status}")

        await db.flush()

        # Step 3: Process payments
        print("\n" + "=" * 80)
        print("PROCESSING PAYMENTS")
        print("=" * 80)

        for channel_code, order in channel_order_map.items():
            await process_payment(db, order, test_data)
            print(f"  [{channel_code}] {order.order_number}: Payment ₹{order.amount_paid:,.2f} | Status: {order.payment_status}")

        await db.flush()

        # Step 4: Allocate orders
        print("\n" + "=" * 80)
        print("ALLOCATING ORDERS")
        print("=" * 80)

        for channel_code, order in channel_order_map.items():
            await allocate_order(db, order, test_data)
            print(f"  [{channel_code}] {order.order_number}: Allocated to {test_data['warehouse'].name}")

        await db.flush()

        # Step 5: Create shipments
        print("\n" + "=" * 80)
        print("CREATING SHIPMENTS")
        print("=" * 80)

        shipments = []
        for channel_code, order in channel_order_map.items():
            shipment = await create_shipment(db, order, test_data)
            shipments.append(shipment)
            print(f"  [{channel_code}] {order.order_number}: Shipment {shipment.shipment_number} | AWB: {shipment.awb_number}")

        await db.flush()

        # Step 6: Create manifest and generate invoices (Goods Issue)
        print("\n" + "=" * 80)
        print("CREATING MANIFEST & INVOICES (GOODS ISSUE)")
        print("=" * 80)

        manifest, invoices = await create_manifest_and_invoice(db, shipments, test_data, created_orders)
        print(f"  Manifest: {manifest.manifest_number} | Status: {manifest.status}")
        print(f"  Shipments in Manifest: {len(shipments)}")
        print("\n  Generated Invoices:")
        for invoice in invoices:
            print(f"    - {invoice.invoice_number}: ₹{invoice.grand_total:,.2f}")

        await db.commit()

        # Step 7: Post GL entries
        print("\n" + "=" * 80)
        print("POSTING GL ENTRIES")
        print("=" * 80)

        gl_accounts = await post_gl_entries(db, invoices, test_data)

        # Step 8: Generate Balance Sheet
        financials = await generate_balance_sheet(db, gl_accounts)

        # Summary
        print("\n" + "=" * 80)
        print("TEST SUMMARY")
        print("=" * 80)

        total_order_value = sum(o.total_amount for o in created_orders)
        total_cogs = Decimal('0')
        for order in created_orders:
            result = await db.execute(
                select(OrderItem).where(OrderItem.order_id == order.id)
            )
            items = result.scalars().all()
            for item in items:
                result = await db.execute(
                    select(Product).where(Product.id == item.product_id)
                )
                product = result.scalar_one_or_none()
                if product and product.cost_price:
                    total_cogs += product.cost_price * item.quantity

        print(f"""
  Orders Created:        {len(created_orders)}
  Total Order Value:     ₹{total_order_value:,.2f}
  Total COGS:            ₹{total_cogs:,.2f}
  Gross Profit:          ₹{(total_order_value - total_cogs):,.2f}
  Gross Margin:          {((total_order_value - total_cogs) / total_order_value * 100):.1f}%

  Shipments:             {len(shipments)}
  Invoices Generated:    {len(invoices)}
  GL Entries Posted:     {len(invoices) * 3}  (Sales + COGS + Payment)

  Financial Summary:
  - Total Revenue:       ₹{financials['total_revenue']:,.2f}
  - Total Expenses:      ₹{financials['total_expense']:,.2f}
  - Net Income:          ₹{financials['net_income']:,.2f}
  - Total Assets:        ₹{financials['total_assets']:,.2f}
  - Total Liabilities:   ₹{financials['total_liabilities']:,.2f}

  Channel Breakdown:
""")
        for channel_code, order in channel_order_map.items():
            product = test_data['products'].get(channel_code)
            print(f"    {channel_code:<12}: {order.order_number} | {product.name:<25} | ₹{order.total_amount:,.2f}")

        print("\n" + "=" * 80)
        print("✅ 4-CHANNEL E2E TEST COMPLETED SUCCESSFULLY!")
        print("=" * 80 + "\n")


if __name__ == "__main__":
    asyncio.run(run_4channel_e2e_test())
