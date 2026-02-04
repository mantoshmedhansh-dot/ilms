"""
Generate Sample Documents for Spare Parts Category:
1. Supply Order (Purchase Order) - ILMS.AI ordering from vendor
2. Sales Order - ILMS.AI selling to customer
3. Tax Invoice - ILMS.AI's invoice to customer
4. E-Way Bill - For transportation

Uses SP CODES from Product Master (e.g., SPSDF001, SPMBF001)
Barcode Format: AP + SS + Y + M + CC + SSSSSSSS (16 chars)

ILMS.AI ERP - Spare Parts Documents
"""
import asyncio
import sys
import os
from datetime import datetime, timedelta
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from app.database import async_session_factory
from app.models.product import Product, ProductItemType

# Company Details (from master)
ILMS.AI = {
    "name": "ILMS.AI",
    "address": "PLOT 36-A KH NO 181, PH-1, SHYAM VIHAR, DINDAPUR EXT",
    "city": "Najafgarh",
    "state": "Delhi",
    "pincode": "110043",
    "gstin": "07ABDCA6170C1Z5",
    "pan": "ABDCA6170C",
    "cin": "U32909DL2025PTC454115",
    "phone": "+91-9311939076",
    "email": "accounts@ilms.ai",
    "state_code": "07"
}

# Vendor - FastTrack (VND-00001)
VENDOR_FASTTRACK = {
    "name": "FASTRACK FILTRATION PVT. LTD.",
    "vendor_code": "VND-00001",
    "code": "FS",
    "address": "Peeragarhi",
    "city": "New Delhi",
    "state": "Delhi",
    "pincode": "110087",
    "gstin": "07ABDCA6170C1Z0",
    "state_code": "07",
    "channel": "EC",
    "category": "Economical",
    "contact": "Sandeep Taneja",
    "bank_name": "HDFC BANK",
    "bank_branch": "PEERAGARHI, DELHI",
    "bank_account": "50200076691896",
    "bank_ifsc": "HDFC0001127"
}

# Sample Customer
CUSTOMER = {
    "name": "Sharma Water Solutions",
    "address": "Shop No. 15, Sector 18 Market",
    "city": "Noida",
    "state": "Uttar Pradesh",
    "pincode": "201301",
    "gstin": "09AABCS9012E1Z7",
    "state_code": "09",
    "phone": "+91-9876543210",
    "email": "sharma.water@gmail.com"
}


def get_common_styles():
    """Common CSS styles for all documents."""
    return """
        <meta charset="UTF-8">
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Noto+Sans:wght@400;700&display=swap');
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { font-family: Arial, sans-serif; font-size: 11px; line-height: 1.4; padding: 15px; }
            .document { max-width: 800px; margin: 0 auto; border: 2px solid #000; }
            .header { background: linear-gradient(135deg, #1a5f7a 0%, #0d3d4d 100%); color: white; padding: 15px; text-align: center; }
            .header h1 { font-size: 22px; margin-bottom: 5px; }
            .header p { font-size: 10px; }
            .doc-title { background: #f0f0f0; padding: 10px; text-align: center; border-bottom: 2px solid #000; }
            .doc-title h2 { font-size: 16px; }
            .info-row { display: flex; border-bottom: 1px solid #000; }
            .info-col { flex: 1; padding: 8px; border-right: 1px solid #000; }
            .info-col:last-child { border-right: none; }
            .info-col h4 { font-size: 10px; background: #e0e0e0; padding: 3px 5px; margin-bottom: 5px; }
            .party-section { display: flex; border-bottom: 1px solid #000; }
            .party-box { flex: 1; padding: 10px; border-right: 1px solid #000; }
            .party-box:last-child { border-right: none; }
            .party-box h4 { font-size: 10px; background: #1a5f7a; color: white; padding: 5px; margin-bottom: 8px; }
            table { width: 100%; border-collapse: collapse; }
            th { background: #1a5f7a; color: white; padding: 8px 5px; font-size: 10px; text-align: center; border: 1px solid #000; }
            td { padding: 6px 5px; border: 1px solid #000; font-size: 10px; }
            .text-center { text-align: center; }
            .text-right { text-align: right; }
            .totals { margin-top: 10px; }
            .totals-row { display: flex; justify-content: flex-end; padding: 3px 15px; }
            .totals-label { width: 150px; text-align: right; padding-right: 10px; }
            .totals-value { width: 100px; text-align: right; font-weight: bold; }
            .grand-total { background: #1a5f7a; color: white; font-size: 14px; padding: 8px 15px; }
            .amount-words { padding: 10px; border-top: 1px solid #000; background: #f9f9f9; font-style: italic; }
            .footer { padding: 15px; border-top: 2px solid #000; }
            .signature-section { display: flex; justify-content: space-between; margin-top: 30px; }
            .signature-box { text-align: center; width: 200px; }
            .signature-line { border-top: 1px solid #000; margin-top: 40px; padding-top: 5px; }
            .terms { font-size: 9px; padding: 10px; background: #f5f5f5; border-top: 1px solid #000; }
            .sp-code { font-family: monospace; font-weight: bold; color: #1a5f7a; }
            .barcode-info { font-family: monospace; font-size: 9px; color: #666; }
            /* Print Button */
            .print-btn {
                position: fixed;
                top: 20px;
                right: 20px;
                background: linear-gradient(135deg, #1a5f7a 0%, #0d3d4d 100%);
                color: white;
                border: none;
                padding: 12px 24px;
                font-size: 14px;
                font-weight: bold;
                border-radius: 5px;
                cursor: pointer;
                box-shadow: 0 4px 6px rgba(0,0,0,0.3);
                z-index: 1000;
                display: flex;
                align-items: center;
                gap: 8px;
            }
            .print-btn:hover {
                background: linear-gradient(135deg, #0d3d4d 0%, #1a5f7a 100%);
                transform: translateY(-2px);
            }
            .print-btn svg { width: 18px; height: 18px; }
            @media print { .print-btn { display: none !important; } }
        </style>
    """


def get_print_button():
    """Print PDF button HTML."""
    return '''
    <button class="print-btn" onclick="window.print()">
        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z" />
        </svg>
        Print PDF
    </button>
    '''


def number_to_words(num):
    """Convert number to words for Indian currency."""
    ones = ['', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine', 'Ten',
            'Eleven', 'Twelve', 'Thirteen', 'Fourteen', 'Fifteen', 'Sixteen', 'Seventeen', 'Eighteen', 'Nineteen']
    tens = ['', '', 'Twenty', 'Thirty', 'Forty', 'Fifty', 'Sixty', 'Seventy', 'Eighty', 'Ninety']

    if num == 0:
        return 'Zero'

    def words(n):
        if n < 20:
            return ones[n]
        elif n < 100:
            return tens[n // 10] + (' ' + ones[n % 10] if n % 10 else '')
        elif n < 1000:
            return ones[n // 100] + ' Hundred' + (' ' + words(n % 100) if n % 100 else '')
        elif n < 100000:
            return words(n // 1000) + ' Thousand' + (' ' + words(n % 1000) if n % 1000 else '')
        elif n < 10000000:
            return words(n // 100000) + ' Lakh' + (' ' + words(n % 100000) if n % 100000 else '')
        else:
            return words(n // 10000000) + ' Crore' + (' ' + words(n % 10000000) if n % 10000000 else '')

    rupees = int(num)
    paise = int((num - rupees) * 100)

    result = 'Rupees ' + words(rupees)
    if paise:
        result += ' and ' + words(paise) + ' Paise'
    return result + ' Only'


def generate_supply_order(spare_parts):
    """Generate Supply Order (Purchase Order) for spare parts from vendor."""
    po_number = "PO-SP-2026-00001"
    po_date = datetime.now().strftime("%d-%m-%Y")
    delivery_date = (datetime.now() + timedelta(days=7)).strftime("%d-%m-%Y")

    # Select items for PO
    items = [
        {"product": spare_parts[0], "qty": 100},  # Sediment Filter
        {"product": spare_parts[2], "qty": 50},   # Pre Carbon Block
        {"product": spare_parts[6], "qty": 25},   # Membrane Premium
        {"product": spare_parts[9], "qty": 30},   # Iron Remover
        {"product": spare_parts[14], "qty": 40},  # Plastic PRV
    ]

    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Supply Order - {po_number}</title>
    {get_common_styles()}
</head>
<body>
    {get_print_button()}
    <div class="document">
        <div class="header">
            <h1>{ILMS.AI['name']}</h1>
            <p>{ILMS.AI['address']}, {ILMS.AI['city']}, {ILMS.AI['state']} - {ILMS.AI['pincode']}</p>
            <p>GSTIN: {ILMS.AI['gstin']} | PAN: {ILMS.AI['pan']} | Phone: {ILMS.AI['phone']}</p>
        </div>

        <div class="doc-title">
            <h2>SUPPLY ORDER / PURCHASE ORDER (SPARE PARTS)</h2>
        </div>

        <div class="info-row">
            <div class="info-col">
                <h4>PO Number</h4>
                <strong>{po_number}</strong>
            </div>
            <div class="info-col">
                <h4>PO Date</h4>
                {po_date}
            </div>
            <div class="info-col">
                <h4>Expected Delivery</h4>
                {delivery_date}
            </div>
            <div class="info-col">
                <h4>Supplier Channel</h4>
                <strong>{VENDOR_FASTTRACK['category']}</strong> ({VENDOR_FASTTRACK['channel']})
            </div>
        </div>

        <div class="party-section">
            <div class="party-box">
                <h4>SUPPLIER / VENDOR DETAILS</h4>
                <strong>{VENDOR_FASTTRACK['name']}</strong><br>
                {VENDOR_FASTTRACK['address']}<br>
                {VENDOR_FASTTRACK['city']}, {VENDOR_FASTTRACK['state']} - {VENDOR_FASTTRACK['pincode']}<br>
                <strong>GSTIN:</strong> {VENDOR_FASTTRACK['gstin']}<br>
                <strong>Supplier Code:</strong> {VENDOR_FASTTRACK['code']}
            </div>
            <div class="party-box">
                <h4>SHIP TO / DELIVERY ADDRESS</h4>
                <strong>{ILMS.AI['name']}</strong><br>
                {ILMS.AI['address']}<br>
                {ILMS.AI['city']}, {ILMS.AI['state']} - {ILMS.AI['pincode']}<br>
                <strong>GSTIN:</strong> {ILMS.AI['gstin']}
            </div>
        </div>

        <table>
            <thead>
                <tr>
                    <th style="width:5%">S.N.</th>
                    <th style="width:12%">SP CODE</th>
                    <th style="width:28%">Description</th>
                    <th style="width:10%">HSN</th>
                    <th style="width:8%">Qty</th>
                    <th style="width:8%">Unit</th>
                    <th style="width:10%">Rate (Rs.)</th>
                    <th style="width:10%">Amount (Rs.)</th>
                </tr>
            </thead>
            <tbody>"""

    subtotal = 0
    for idx, item in enumerate(items, 1):
        p = item["product"]
        qty = item["qty"]
        rate = float(p.cost_price)  # Use cost price for PO
        amount = qty * rate
        subtotal += amount

        # Generate expected barcode prefix for this supplier
        barcode_prefix = f"APFSAA{VENDOR_FASTTRACK['channel']}"

        html += f"""
                <tr>
                    <td class="text-center">{idx}</td>
                    <td class="text-center"><span class="sp-code">{p.fg_code}</span></td>
                    <td>{p.name}<br><span class="barcode-info">Barcode: {barcode_prefix}XXXXXXXX</span></td>
                    <td class="text-center">{p.hsn_code}</td>
                    <td class="text-center">{qty}</td>
                    <td class="text-center">Nos</td>
                    <td class="text-right">{rate:,.2f}</td>
                    <td class="text-right">{amount:,.2f}</td>
                </tr>"""

    # Calculate taxes (IGST since inter-state: Haryana to Maharashtra)
    igst_rate = 18
    igst_amount = subtotal * igst_rate / 100
    grand_total = subtotal + igst_amount

    html += f"""
            </tbody>
        </table>

        <div class="totals">
            <div class="totals-row">
                <span class="totals-label">Sub Total:</span>
                <span class="totals-value">Rs.{subtotal:,.2f}</span>
            </div>
            <div class="totals-row">
                <span class="totals-label">IGST @ {igst_rate}%:</span>
                <span class="totals-value">Rs.{igst_amount:,.2f}</span>
            </div>
            <div class="totals-row grand-total">
                <span class="totals-label">GRAND TOTAL:</span>
                <span class="totals-value">Rs.{grand_total:,.2f}</span>
            </div>
        </div>

        <div class="amount-words">
            <strong>Amount in Words:</strong> {number_to_words(grand_total)}
        </div>

        <div class="terms">
            <strong>Terms & Conditions:</strong><br>
            1. All items must be packed with proper barcodes as per ILMS.AI serialization format<br>
            2. Barcode Format: AP + {VENDOR_FASTTRACK['code']} (Supplier) + YY (Year) + M (Month) + {VENDOR_FASTTRACK['channel']} (Channel) + Serial (8 digits)<br>
            3. Payment terms: 30 days from invoice date<br>
            4. Quality certification required for each batch<br>
            5. Warranty: 6 months from date of sale to end customer
        </div>

        <div class="footer">
            <div class="signature-section">
                <div class="signature-box">
                    <div class="signature-line">Prepared By</div>
                </div>
                <div class="signature-box">
                    <div class="signature-line">Approved By</div>
                </div>
                <div class="signature-box">
                    <div class="signature-line">For {ILMS.AI['name']}</div>
                </div>
            </div>
        </div>
    </div>
</body>
</html>"""

    return html, po_number


def generate_sales_order(spare_parts):
    """Generate Sales Order for spare parts to customer."""
    so_number = "SO-SP-2026-00001"
    so_date = datetime.now().strftime("%d-%m-%Y")
    delivery_date = (datetime.now() + timedelta(days=3)).strftime("%d-%m-%Y")

    # Select items for SO
    items = [
        {"product": spare_parts[0], "qty": 10},   # Sediment Filter
        {"product": spare_parts[2], "qty": 5},    # Pre Carbon Block
        {"product": spare_parts[6], "qty": 3},    # Membrane Premium
        {"product": spare_parts[10], "qty": 5},   # HMR Cartridge
    ]

    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Sales Order - {so_number}</title>
    {get_common_styles()}
</head>
<body>
    {get_print_button()}
    <div class="document">
        <div class="header">
            <h1>{ILMS.AI['name']}</h1>
            <p>{ILMS.AI['address']}, {ILMS.AI['city']}, {ILMS.AI['state']} - {ILMS.AI['pincode']}</p>
            <p>GSTIN: {ILMS.AI['gstin']} | PAN: {ILMS.AI['pan']} | Phone: {ILMS.AI['phone']}</p>
        </div>

        <div class="doc-title">
            <h2>SALES ORDER (SPARE PARTS)</h2>
        </div>

        <div class="info-row">
            <div class="info-col">
                <h4>SO Number</h4>
                <strong>{so_number}</strong>
            </div>
            <div class="info-col">
                <h4>SO Date</h4>
                {so_date}
            </div>
            <div class="info-col">
                <h4>Delivery Date</h4>
                {delivery_date}
            </div>
            <div class="info-col">
                <h4>Payment Terms</h4>
                Advance Payment
            </div>
        </div>

        <div class="party-section">
            <div class="party-box">
                <h4>BILL TO</h4>
                <strong>{CUSTOMER['name']}</strong><br>
                {CUSTOMER['address']}<br>
                {CUSTOMER['city']}, {CUSTOMER['state']} - {CUSTOMER['pincode']}<br>
                <strong>GSTIN:</strong> {CUSTOMER['gstin']}<br>
                <strong>Phone:</strong> {CUSTOMER['phone']}
            </div>
            <div class="party-box">
                <h4>SHIP TO</h4>
                <strong>{CUSTOMER['name']}</strong><br>
                {CUSTOMER['address']}<br>
                {CUSTOMER['city']}, {CUSTOMER['state']} - {CUSTOMER['pincode']}<br>
                <strong>Phone:</strong> {CUSTOMER['phone']}
            </div>
        </div>

        <table>
            <thead>
                <tr>
                    <th style="width:5%">S.N.</th>
                    <th style="width:12%">SP CODE</th>
                    <th style="width:30%">Description</th>
                    <th style="width:10%">HSN</th>
                    <th style="width:8%">Qty</th>
                    <th style="width:8%">Unit</th>
                    <th style="width:12%">Rate (Rs.)</th>
                    <th style="width:12%">Amount (Rs.)</th>
                </tr>
            </thead>
            <tbody>"""

    subtotal = 0
    for idx, item in enumerate(items, 1):
        p = item["product"]
        qty = item["qty"]
        rate = float(p.selling_price)  # Use selling price for SO
        amount = qty * rate
        subtotal += amount

        html += f"""
                <tr>
                    <td class="text-center">{idx}</td>
                    <td class="text-center"><span class="sp-code">{p.fg_code}</span></td>
                    <td>{p.name}</td>
                    <td class="text-center">{p.hsn_code}</td>
                    <td class="text-center">{qty}</td>
                    <td class="text-center">Nos</td>
                    <td class="text-right">{rate:,.2f}</td>
                    <td class="text-right">{amount:,.2f}</td>
                </tr>"""

    # Calculate taxes (IGST since inter-state: Haryana to UP)
    igst_rate = 18
    igst_amount = subtotal * igst_rate / 100
    grand_total = subtotal + igst_amount

    html += f"""
            </tbody>
        </table>

        <div class="totals">
            <div class="totals-row">
                <span class="totals-label">Sub Total:</span>
                <span class="totals-value">Rs.{subtotal:,.2f}</span>
            </div>
            <div class="totals-row">
                <span class="totals-label">IGST @ {igst_rate}%:</span>
                <span class="totals-value">Rs.{igst_amount:,.2f}</span>
            </div>
            <div class="totals-row grand-total">
                <span class="totals-label">GRAND TOTAL:</span>
                <span class="totals-value">Rs.{grand_total:,.2f}</span>
            </div>
        </div>

        <div class="amount-words">
            <strong>Amount in Words:</strong> {number_to_words(grand_total)}
        </div>

        <div class="terms">
            <strong>Terms & Conditions:</strong><br>
            1. Goods once sold will not be taken back<br>
            2. All disputes subject to Gurugram jurisdiction<br>
            3. Warranty: 6 months from date of purchase<br>
            4. E&OE (Errors and Omissions Excepted)
        </div>

        <div class="footer">
            <div class="signature-section">
                <div class="signature-box">
                    <div class="signature-line">Customer Signature</div>
                </div>
                <div class="signature-box">
                    <div class="signature-line">For {ILMS.AI['name']}</div>
                </div>
            </div>
        </div>
    </div>
</body>
</html>"""

    return html, so_number


def generate_tax_invoice(spare_parts):
    """Generate Tax Invoice for spare parts."""
    inv_number = "INV-SP-2026-00001"
    inv_date = datetime.now().strftime("%d-%m-%Y")
    so_ref = "SO-SP-2026-00001"

    # Select items for Invoice (same as SO)
    items = [
        {"product": spare_parts[0], "qty": 10, "barcode": "APFSAAEC00000101"},
        {"product": spare_parts[2], "qty": 5, "barcode": "APFSAAEC00000201"},
        {"product": spare_parts[6], "qty": 3, "barcode": "APFSAAEC00000301"},
        {"product": spare_parts[10], "qty": 5, "barcode": "APFSAAEC00000401"},
    ]

    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Tax Invoice - {inv_number}</title>
    {get_common_styles()}
    <style>
        .invoice-badge {{ background: #28a745; color: white; padding: 3px 10px; border-radius: 3px; font-size: 10px; }}
    </style>
</head>
<body>
    {get_print_button()}
    <div class="document">
        <div class="header">
            <h1>{ILMS.AI['name']}</h1>
            <p>{ILMS.AI['address']}, {ILMS.AI['city']}, {ILMS.AI['state']} - {ILMS.AI['pincode']}</p>
            <p>GSTIN: {ILMS.AI['gstin']} | PAN: {ILMS.AI['pan']} | Phone: {ILMS.AI['phone']}</p>
        </div>

        <div class="doc-title">
            <h2>TAX INVOICE (SPARE PARTS) <span class="invoice-badge">ORIGINAL</span></h2>
        </div>

        <div class="info-row">
            <div class="info-col">
                <h4>Invoice Number</h4>
                <strong>{inv_number}</strong>
            </div>
            <div class="info-col">
                <h4>Invoice Date</h4>
                {inv_date}
            </div>
            <div class="info-col">
                <h4>SO Reference</h4>
                {so_ref}
            </div>
            <div class="info-col">
                <h4>Place of Supply</h4>
                {CUSTOMER['state']} ({CUSTOMER['state_code']})
            </div>
        </div>

        <div class="party-section">
            <div class="party-box">
                <h4>BILL TO</h4>
                <strong>{CUSTOMER['name']}</strong><br>
                {CUSTOMER['address']}<br>
                {CUSTOMER['city']}, {CUSTOMER['state']} - {CUSTOMER['pincode']}<br>
                <strong>GSTIN:</strong> {CUSTOMER['gstin']}<br>
                <strong>State Code:</strong> {CUSTOMER['state_code']}
            </div>
            <div class="party-box">
                <h4>SHIP TO</h4>
                <strong>{CUSTOMER['name']}</strong><br>
                {CUSTOMER['address']}<br>
                {CUSTOMER['city']}, {CUSTOMER['state']} - {CUSTOMER['pincode']}<br>
                <strong>Phone:</strong> {CUSTOMER['phone']}
            </div>
        </div>

        <table>
            <thead>
                <tr>
                    <th style="width:4%">S.N.</th>
                    <th style="width:10%">SP CODE</th>
                    <th style="width:24%">Description</th>
                    <th style="width:14%">Barcode</th>
                    <th style="width:8%">HSN</th>
                    <th style="width:6%">Qty</th>
                    <th style="width:10%">Rate (Rs.)</th>
                    <th style="width:8%">GST%</th>
                    <th style="width:12%">Amount (Rs.)</th>
                </tr>
            </thead>
            <tbody>"""

    subtotal = 0
    total_qty = 0
    for idx, item in enumerate(items, 1):
        p = item["product"]
        qty = item["qty"]
        barcode = item["barcode"]
        rate = float(p.selling_price)
        amount = qty * rate
        subtotal += amount
        total_qty += qty

        html += f"""
                <tr>
                    <td class="text-center">{idx}</td>
                    <td class="text-center"><span class="sp-code">{p.fg_code}</span></td>
                    <td>{p.name}</td>
                    <td class="text-center"><span class="barcode-info">{barcode}</span></td>
                    <td class="text-center">{p.hsn_code}</td>
                    <td class="text-center">{qty}</td>
                    <td class="text-right">{rate:,.2f}</td>
                    <td class="text-center">18%</td>
                    <td class="text-right">{amount:,.2f}</td>
                </tr>"""

    # Calculate taxes (IGST since inter-state)
    igst_rate = 18
    igst_amount = subtotal * igst_rate / 100
    grand_total = subtotal + igst_amount

    html += f"""
                <tr style="background: #f0f0f0; font-weight: bold;">
                    <td colspan="5" class="text-right">Total</td>
                    <td class="text-center">{total_qty}</td>
                    <td></td>
                    <td></td>
                    <td class="text-right">Rs.{subtotal:,.2f}</td>
                </tr>
            </tbody>
        </table>

        <div class="totals">
            <div class="totals-row">
                <span class="totals-label">Taxable Amount:</span>
                <span class="totals-value">Rs.{subtotal:,.2f}</span>
            </div>
            <div class="totals-row">
                <span class="totals-label">IGST @ {igst_rate}%:</span>
                <span class="totals-value">Rs.{igst_amount:,.2f}</span>
            </div>
            <div class="totals-row">
                <span class="totals-label">Round Off:</span>
                <span class="totals-value">Rs.{round(grand_total) - grand_total:,.2f}</span>
            </div>
            <div class="totals-row grand-total">
                <span class="totals-label">GRAND TOTAL:</span>
                <span class="totals-value">Rs.{round(grand_total):,.0f}</span>
            </div>
        </div>

        <div class="amount-words">
            <strong>Amount in Words:</strong> {number_to_words(round(grand_total))}
        </div>

        <div class="info-row" style="border-top: 1px solid #000;">
            <div class="info-col">
                <h4>HSN Summary</h4>
                <table style="font-size: 9px;">
                    <tr><th>HSN</th><th>Taxable</th><th>IGST</th><th>Total</th></tr>
                    <tr><td>84212190</td><td>Rs.{subtotal:,.2f}</td><td>Rs.{igst_amount:,.2f}</td><td>Rs.{grand_total:,.2f}</td></tr>
                </table>
            </div>
            <div class="info-col">
                <h4>Bank Details</h4>
                <strong>Bank:</strong> HDFC Bank<br>
                <strong>A/C No:</strong> 50100123456789<br>
                <strong>IFSC:</strong> HDFC0001234<br>
                <strong>Branch:</strong> Gurugram Sector 14
            </div>
        </div>

        <div class="terms">
            <strong>Terms & Conditions:</strong><br>
            1. Goods once sold will not be taken back or exchanged<br>
            2. Interest @ 18% p.a. will be charged on delayed payments<br>
            3. Subject to Gurugram jurisdiction only<br>
            4. Warranty as per manufacturer's terms
        </div>

        <div class="footer">
            <div class="signature-section">
                <div class="signature-box">
                    <div class="signature-line">Receiver's Signature</div>
                </div>
                <div class="signature-box">
                    <div class="signature-line">For {ILMS.AI['name']}<br>(Authorized Signatory)</div>
                </div>
            </div>
        </div>
    </div>
</body>
</html>"""

    return html, inv_number


def generate_eway_bill(spare_parts):
    """Generate E-Way Bill for spare parts transportation."""
    ewb_number = "EWB-SP-2026-00001"
    ewb_date = datetime.now().strftime("%d-%m-%Y %H:%M")
    inv_ref = "INV-SP-2026-00001"
    valid_upto = (datetime.now() + timedelta(days=1)).strftime("%d-%m-%Y %H:%M")

    # Select items (same as invoice)
    items = [
        {"product": spare_parts[0], "qty": 10},
        {"product": spare_parts[2], "qty": 5},
        {"product": spare_parts[6], "qty": 3},
        {"product": spare_parts[10], "qty": 5},
    ]

    subtotal = sum(item["qty"] * float(item["product"].selling_price) for item in items)
    igst_amount = subtotal * 18 / 100
    grand_total = subtotal + igst_amount

    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>E-Way Bill - {ewb_number}</title>
    {get_common_styles()}
    <style>
        .ewb-header {{ background: #dc3545; color: white; padding: 5px 15px; font-size: 12px; }}
        .qr-placeholder {{ width: 80px; height: 80px; border: 1px solid #000; display: flex; align-items: center; justify-content: center; font-size: 9px; }}
    </style>
</head>
<body>
    {get_print_button()}
    <div class="document">
        <div class="ewb-header">
            <strong>E-WAY BILL</strong> | Generated from GST Portal
        </div>

        <div class="header">
            <h1>{ILMS.AI['name']}</h1>
            <p>{ILMS.AI['address']}, {ILMS.AI['city']}, {ILMS.AI['state']} - {ILMS.AI['pincode']}</p>
            <p>GSTIN: {ILMS.AI['gstin']}</p>
        </div>

        <div class="doc-title">
            <h2>E-WAY BILL (SPARE PARTS)</h2>
        </div>

        <div class="info-row">
            <div class="info-col">
                <h4>E-Way Bill No.</h4>
                <strong style="font-size: 14px;">{ewb_number}</strong>
            </div>
            <div class="info-col">
                <h4>Generated Date</h4>
                {ewb_date}
            </div>
            <div class="info-col">
                <h4>Valid Upto</h4>
                <strong style="color: #dc3545;">{valid_upto}</strong>
            </div>
            <div class="info-col">
                <h4>Mode</h4>
                Road
            </div>
        </div>

        <div class="info-row">
            <div class="info-col">
                <h4>Document Type</h4>
                Tax Invoice
            </div>
            <div class="info-col">
                <h4>Document No.</h4>
                {inv_ref}
            </div>
            <div class="info-col">
                <h4>Document Date</h4>
                {datetime.now().strftime("%d-%m-%Y")}
            </div>
            <div class="info-col">
                <h4>Supply Type</h4>
                Outward - Sale
            </div>
        </div>

        <div class="party-section">
            <div class="party-box">
                <h4>FROM (CONSIGNOR)</h4>
                <strong>{ILMS.AI['name']}</strong><br>
                {ILMS.AI['address']}<br>
                {ILMS.AI['city']}, {ILMS.AI['state']} - {ILMS.AI['pincode']}<br>
                <strong>GSTIN:</strong> {ILMS.AI['gstin']}<br>
                <strong>State:</strong> {ILMS.AI['state']} ({ILMS.AI['state_code']})
            </div>
            <div class="party-box">
                <h4>TO (CONSIGNEE)</h4>
                <strong>{CUSTOMER['name']}</strong><br>
                {CUSTOMER['address']}<br>
                {CUSTOMER['city']}, {CUSTOMER['state']} - {CUSTOMER['pincode']}<br>
                <strong>GSTIN:</strong> {CUSTOMER['gstin']}<br>
                <strong>State:</strong> {CUSTOMER['state']} ({CUSTOMER['state_code']})
            </div>
        </div>

        <table>
            <thead>
                <tr>
                    <th style="width:5%">S.N.</th>
                    <th style="width:12%">SP CODE</th>
                    <th style="width:30%">Product Name</th>
                    <th style="width:12%">HSN Code</th>
                    <th style="width:10%">Qty</th>
                    <th style="width:10%">Unit</th>
                    <th style="width:15%">Value (Rs.)</th>
                </tr>
            </thead>
            <tbody>"""

    total_qty = 0
    for idx, item in enumerate(items, 1):
        p = item["product"]
        qty = item["qty"]
        value = qty * float(p.selling_price)
        total_qty += qty

        html += f"""
                <tr>
                    <td class="text-center">{idx}</td>
                    <td class="text-center"><span class="sp-code">{p.fg_code}</span></td>
                    <td>{p.name}</td>
                    <td class="text-center">{p.hsn_code}</td>
                    <td class="text-center">{qty}</td>
                    <td class="text-center">Nos</td>
                    <td class="text-right">{value:,.2f}</td>
                </tr>"""

    html += f"""
            </tbody>
        </table>

        <div class="info-row">
            <div class="info-col">
                <h4>Total Quantity</h4>
                {total_qty} Nos
            </div>
            <div class="info-col">
                <h4>Taxable Value</h4>
                Rs.{subtotal:,.2f}
            </div>
            <div class="info-col">
                <h4>IGST Amount</h4>
                Rs.{igst_amount:,.2f}
            </div>
            <div class="info-col">
                <h4>Total Invoice Value</h4>
                <strong>Rs.{grand_total:,.2f}</strong>
            </div>
        </div>

        <div class="party-section">
            <div class="party-box">
                <h4>TRANSPORTER DETAILS</h4>
                <strong>Name:</strong> BlueDart Express Ltd<br>
                <strong>GSTIN:</strong> 27AAACB1234F1Z5<br>
                <strong>Transporter ID:</strong> 27AAACB1234F1Z5<br>
                <strong>Approx Distance:</strong> 45 KM
            </div>
            <div class="party-box">
                <h4>VEHICLE DETAILS</h4>
                <strong>Vehicle No:</strong> HR-26-AB-1234<br>
                <strong>Vehicle Type:</strong> Regular<br>
                <strong>Transport Mode:</strong> Road<br>
                <strong>Transport Doc No:</strong> LR-2026-00123
            </div>
            <div class="party-box" style="text-align: center;">
                <h4>QR CODE</h4>
                <div class="qr-placeholder" style="margin: 0 auto;">
                    [QR Code]<br>
                    {ewb_number}
                </div>
            </div>
        </div>

        <div class="terms">
            <strong>Important:</strong><br>
            1. This E-Way Bill is system generated and valid for the period mentioned above<br>
            2. The goods should reach the destination before the validity expires<br>
            3. In case of any discrepancy, please contact the supplier immediately<br>
            4. This document must be carried during transit
        </div>

        <div class="footer">
            <div class="signature-section">
                <div class="signature-box">
                    <div class="signature-line">Verified By</div>
                </div>
                <div class="signature-box">
                    <div class="signature-line">For {ILMS.AI['name']}</div>
                </div>
            </div>
        </div>
    </div>
</body>
</html>"""

    return html, ewb_number


async def main():
    """Generate all spare parts documents."""
    print("=" * 80)
    print("GENERATING SPARE PARTS DOCUMENTS")
    print("=" * 80)

    # Fetch spare parts from database
    async with async_session_factory() as db:
        result = await db.execute(
            select(Product)
            .where(Product.item_type == ProductItemType.SPARE_PART)
            .where(Product.is_active == True)
            .order_by(Product.fg_code)
        )
        spare_parts = result.scalars().all()

    if not spare_parts:
        print("ERROR: No spare parts found in database!")
        print("Please run seed_spare_parts_master.py first.")
        return

    print(f"\nFound {len(spare_parts)} spare parts in Product Master")

    # Output directory
    output_dir = os.path.expanduser("~/Desktop")

    # Generate documents
    documents = []

    # 1. Supply Order (PO)
    html, doc_num = generate_supply_order(spare_parts)
    filepath = os.path.join(output_dir, f"SpareParty-SupplyOrder-{doc_num}.html")
    with open(filepath, "w") as f:
        f.write(html)
    documents.append(("Supply Order (PO)", doc_num, filepath))
    print(f"✓ Generated: {doc_num}")

    # 2. Sales Order
    html, doc_num = generate_sales_order(spare_parts)
    filepath = os.path.join(output_dir, f"SpareParts-SalesOrder-{doc_num}.html")
    with open(filepath, "w") as f:
        f.write(html)
    documents.append(("Sales Order", doc_num, filepath))
    print(f"✓ Generated: {doc_num}")

    # 3. Tax Invoice
    html, doc_num = generate_tax_invoice(spare_parts)
    filepath = os.path.join(output_dir, f"SpareParts-TaxInvoice-{doc_num}.html")
    with open(filepath, "w") as f:
        f.write(html)
    documents.append(("Tax Invoice", doc_num, filepath))
    print(f"✓ Generated: {doc_num}")

    # 4. E-Way Bill
    html, doc_num = generate_eway_bill(spare_parts)
    filepath = os.path.join(output_dir, f"SpareParts-EWayBill-{doc_num}.html")
    with open(filepath, "w") as f:
        f.write(html)
    documents.append(("E-Way Bill", doc_num, filepath))
    print(f"✓ Generated: {doc_num}")

    print("\n" + "=" * 80)
    print("DOCUMENTS GENERATED SUCCESSFULLY")
    print("=" * 80)
    print(f"\n{'Document Type':<25} {'Document Number':<25} {'Location'}")
    print("-" * 80)
    for doc_type, doc_num, filepath in documents:
        print(f"{doc_type:<25} {doc_num:<25} {filepath}")

    print("\n" + "=" * 80)
    print("SPARE PARTS USED IN DOCUMENTS")
    print("=" * 80)
    print(f"{'SP CODE':<12} {'Product Name':<40} {'Selling Price':>15}")
    print("-" * 80)
    for p in spare_parts[:5]:
        print(f"{p.fg_code:<12} {p.name[:38]:<40} Rs.{float(p.selling_price):>13,.2f}")
    print("...")

    return documents


if __name__ == "__main__":
    asyncio.run(main())
