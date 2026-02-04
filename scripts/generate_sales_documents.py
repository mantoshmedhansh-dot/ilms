"""
Generate Sales Documents (Sales Order, Tax Invoice, E-Way Bill) for ILMS.AI.
Uses Product Master data with FG Codes (not Part Codes).

FG Code = ILMS.AI's Finished Goods Code (e.g., WPRAIEL001)
Part Code = Vendor's code (used only in Purchase Orders)

ILMS.AI ERP System
"""
import asyncio
import sys
import os
import subprocess
import shutil
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from decimal import Decimal
from datetime import datetime, date
from sqlalchemy import select
from app.database import async_session_factory
from app.models.product import Product


def number_to_words(num):
    """Convert number to words (Indian numbering system)."""
    ones = ['', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine',
            'Ten', 'Eleven', 'Twelve', 'Thirteen', 'Fourteen', 'Fifteen', 'Sixteen',
            'Seventeen', 'Eighteen', 'Nineteen']
    tens = ['', '', 'Twenty', 'Thirty', 'Forty', 'Fifty', 'Sixty', 'Seventy', 'Eighty', 'Ninety']

    def two_digit(n):
        if n < 20:
            return ones[n]
        return tens[n // 10] + ('' if n % 10 == 0 else ' ' + ones[n % 10])

    def three_digit(n):
        if n < 100:
            return two_digit(n)
        return ones[n // 100] + ' Hundred' + ('' if n % 100 == 0 else ' ' + two_digit(n % 100))

    if num == 0:
        return 'Zero'

    num = int(num)
    result = []

    if num >= 10000000:
        result.append(two_digit(num // 10000000) + ' Crore')
        num %= 10000000

    if num >= 100000:
        result.append(two_digit(num // 100000) + ' Lakh')
        num %= 100000

    if num >= 1000:
        result.append(two_digit(num // 1000) + ' Thousand')
        num %= 1000

    if num > 0:
        result.append(three_digit(num))

    return ' '.join(result)


def amount_to_words(amount):
    """Convert amount to words with Rupees and Paise."""
    rupees = int(amount)
    paise = int((amount - rupees) * 100)

    words = "Rupees " + number_to_words(rupees)
    if paise > 0:
        words += " and " + number_to_words(paise) + " Paise"
    words += " Only"
    return words


# ILMS.AI Company Details (Seller)
COMPANY = {
    "name": "ILMS.AI",
    "address_line1": "PLOT 36-A KH NO 181, DINDAPUR EXT",
    "address_line2": "PH-1, SHYAM VIHAR, Najafgarh",
    "city": "New Delhi",
    "district": "West Delhi",
    "state": "Delhi",
    "pincode": "110043",
    "gstin": "07ABDCA6170C1Z0",
    "state_code": "07",
    "pan": "ABDCA6170C",
    "cin": "U74999DL2020PTC000000",
    "phone": "+91-11-12345678",
    "email": "sales@ilms.ai",
    "website": "www.ilms.ai",
    "bank_name": "ICICI BANK",
    "bank_branch": "NAJAFGARH",
    "account_no": "123456789012",
    "ifsc": "ICIC0001234"
}

# Sample Customer (Buyer) - Bill To
BILL_TO = {
    "name": "ABC Water Solutions Pvt. Ltd.",
    "address_line1": "45, Industrial Area, Phase-2",
    "address_line2": "Sector 62",
    "city": "Noida",
    "district": "Gautam Buddha Nagar",
    "state": "Uttar Pradesh",
    "pincode": "201301",
    "gstin": "09AABCA1234B1Z5",
    "state_code": "09",
    "phone": "+91-120-4567890",
    "email": "purchase@abcwater.com",
    "contact_person": "Mr. Rajesh Kumar"
}

# Ship To (can be different)
SHIP_TO = {
    "name": "ABC Water Solutions Pvt. Ltd.",
    "address_line1": "Warehouse No. 12, Transport Nagar",
    "address_line2": "Near NH-24",
    "city": "Ghaziabad",
    "district": "Ghaziabad",
    "state": "Uttar Pradesh",
    "pincode": "201002",
    "gstin": "09AABCA1234B1Z5",
    "state_code": "09",
    "phone": "+91-120-9876543",
    "contact_person": "Mr. Suresh (Store Manager)"
}


async def get_products_from_master():
    """Fetch products from Product Master with FG Codes."""
    async with async_session_factory() as db:
        result = await db.execute(
            select(Product)
            .where(Product.is_active == True)
            .where(Product.fg_code.isnot(None))
            .limit(10)
        )
        products = result.scalars().all()

        items = []
        for idx, p in enumerate(products, 1):
            items.append({
                "sn": idx,
                "description": p.name,
                "fg_code": p.fg_code,  # FG Code from Product Master
                "sku": p.sku,
                "hsn": p.hsn_code or "84212110",
                "qty": 2 + idx,  # Sample quantities
                "unit": "Nos",
                "price": float(p.selling_price)
            })

        return items


def generate_sales_proforma_html(items, doc_date):
    """Generate Sales Proforma Invoice HTML using FG Code."""
    pi_number = "PI-2026-00001"
    validity_date = date(2026, 2, 7)

    # Calculate totals
    subtotal = sum(item["qty"] * item["price"] for item in items)
    is_igst = COMPANY["state_code"] != BILL_TO["state_code"]

    if is_igst:
        igst_amount = subtotal * 0.18
        cgst_amount = sgst_amount = 0
    else:
        igst_amount = 0
        cgst_amount = sgst_amount = subtotal * 0.09

    grand_total = subtotal + igst_amount + cgst_amount + sgst_amount

    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Sales Proforma Invoice - {pi_number}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: Arial, sans-serif; font-size: 11px; padding: 15px; background: #fff; }}
        .header {{ display: flex; justify-content: space-between; margin-bottom: 10px; }}
        .header-left {{ font-size: 10px; }}
        .header-right {{ text-align: right; font-size: 10px; }}
        .title {{ text-align: center; margin: 10px 0; }}
        .title h1 {{ font-size: 22px; font-weight: bold; color: #0066cc; margin-bottom: 3px; }}
        .title .address {{ font-size: 10px; color: #333; margin-top: 5px; }}
        .doc-type {{ text-align: center; background: #0066cc; color: white; padding: 8px; font-weight: bold; margin: 15px 0; font-size: 14px; }}
        .info-row {{ display: flex; justify-content: space-between; margin-bottom: 10px; border: 1px solid #000; }}
        .info-box {{ padding: 8px; width: 50%; }}
        .info-box.right {{ border-left: 1px solid #000; }}
        .party-box {{ border: 1px solid #000; margin-bottom: 10px; }}
        .party-header {{ display: flex; background: #f0f0f0; border-bottom: 1px solid #000; }}
        .party-header-col {{ width: 50%; padding: 5px 10px; font-weight: bold; text-align: center; font-size: 10px; }}
        .party-header-col.right {{ border-left: 1px solid #000; }}
        .party-row {{ display: flex; }}
        .party-col {{ width: 50%; padding: 10px; line-height: 1.6; font-size: 11px; }}
        .party-col.right {{ border-left: 1px solid #000; }}
        table {{ width: 100%; border-collapse: collapse; margin-bottom: 10px; }}
        th, td {{ border: 1px solid #000; padding: 5px; text-align: center; font-size: 10px; }}
        th {{ background: #0066cc; color: white; font-weight: bold; }}
        td.left {{ text-align: left; }}
        td.right {{ text-align: right; }}
        .amount-row {{ background: #f9f9f9; }}
        .grand-total {{ font-weight: bold; font-size: 12px; background: #e6f2ff !important; }}
        .bank-details {{ border: 1px solid #000; padding: 10px; margin-bottom: 10px; background: #f9f9f9; }}
        .terms {{ font-size: 10px; margin-top: 10px; }}
        .signature {{ text-align: right; margin-top: 20px; }}
        .amount-words {{ background: #ffffcc; padding: 8px; border: 1px solid #000; margin: 10px 0; font-size: 11px; }}
        .print-btn {{ position: fixed; top: 10px; right: 10px; padding: 10px 20px; background: #0066cc; color: white; border: none; cursor: pointer; font-size: 14px; border-radius: 5px; }}
        .fg-code {{ font-family: 'Courier New', monospace; font-weight: bold; color: #0066cc; }}
        @media print {{ .print-btn {{ display: none; }} }}
    </style>
</head>
<body>
    <button class="print-btn" onclick="window.print()">Print / Save as PDF</button>

    <div class="header">
        <div class="header-left">
            <div><strong>GSTIN :</strong> {COMPANY['gstin']}</div>
            <div><strong>STATE :</strong> {COMPANY['state'].upper()}</div>
            <div><strong>STATE CODE :</strong> {COMPANY['state_code']}</div>
            <div><strong>PAN NO. :</strong> {COMPANY['pan']}</div>
        </div>
        <div class="header-right">
            <div><strong>CIN :</strong> {COMPANY['cin']}</div>
            <div style="margin-top: 10px;"><strong>Original Copy</strong></div>
        </div>
    </div>

    <div class="doc-type">PROFORMA INVOICE / QUOTATION</div>

    <div class="title">
        <h1>{COMPANY['name']}</h1>
        
        <div class="address">{COMPANY['address_line1']}, {COMPANY['address_line2']}, {COMPANY['city']}, {COMPANY['state']} - {COMPANY['pincode']}</div>
    </div>

    <div class="info-row">
        <div class="info-box">
            <div><strong>Proforma Invoice No. :</strong> {pi_number}</div>
            <div><strong>Reverse Charges :</strong> NO</div>
        </div>
        <div class="info-box right">
            <div><strong>Date :</strong> {doc_date.strftime('%d-%m-%Y')}</div>
            <div><strong>Valid Until :</strong> {validity_date.strftime('%d-%m-%Y')}</div>
        </div>
    </div>

    <div class="party-box">
        <div class="party-header">
            <div class="party-header-col">Details Of Buyer | Billed To:</div>
            <div class="party-header-col right">Details Of Consignee | Shipped To:</div>
        </div>
        <div class="party-row">
            <div class="party-col">
                <strong>{BILL_TO['name']}</strong><br>
                {BILL_TO['address_line1']}<br>
                {BILL_TO['address_line2']}<br>
                {BILL_TO['city']}, {BILL_TO['state']} - {BILL_TO['pincode']}<br><br>
                <strong>State Code :</strong> {BILL_TO['state_code']}<br>
                <strong>GSTIN :</strong> {BILL_TO['gstin']}<br>
                <strong>Contact :</strong> {BILL_TO['contact_person']}<br>
                <strong>Phone :</strong> {BILL_TO['phone']}
            </div>
            <div class="party-col right">
                <strong>{SHIP_TO['name']}</strong><br>
                {SHIP_TO['address_line1']}<br>
                {SHIP_TO['address_line2']}<br>
                {SHIP_TO['city']}, {SHIP_TO['state']} - {SHIP_TO['pincode']}<br><br>
                <strong>State Code :</strong> {SHIP_TO['state_code']}<br>
                <strong>GSTIN :</strong> {SHIP_TO['gstin']}<br>
                <strong>Contact :</strong> {SHIP_TO['contact_person']}<br>
                <strong>Phone :</strong> {SHIP_TO['phone']}
            </div>
        </div>
    </div>

    <table>
        <thead>
            <tr>
                <th style="width: 25px;">S.N.</th>
                <th>Description of Goods</th>
                <th style="width: 100px;">FG CODE</th>
                <th style="width: 70px;">HSN/SAC</th>
                <th style="width: 45px;">Qty</th>
                <th style="width: 35px;">Unit</th>
                <th style="width: 70px;">Rate (₹)</th>
                <th style="width: 90px;">Amount (₹)</th>
            </tr>
        </thead>
        <tbody>"""

    total_qty = 0
    for item in items:
        amount = item["qty"] * item["price"]
        total_qty += item["qty"]
        html += f"""
            <tr>
                <td>{item['sn']}</td>
                <td class="left">{item['description']}</td>
                <td class="fg-code">{item['fg_code']}</td>
                <td>{item['hsn']}</td>
                <td>{item['qty']:,}</td>
                <td>{item['unit']}</td>
                <td class="right">{item['price']:,.2f}</td>
                <td class="right">{amount:,.2f}</td>
            </tr>"""

    html += f"""
            <tr class="amount-row">
                <td colspan="4" class="right"><strong>Sub Total</strong></td>
                <td><strong>{total_qty:,}</strong></td>
                <td></td>
                <td colspan="2" class="right"><strong>{subtotal:,.2f}</strong></td>
            </tr>"""

    if is_igst:
        html += f"""
            <tr class="amount-row">
                <td colspan="6" class="right">Add: IGST @ 18%</td>
                <td colspan="2" class="right">{igst_amount:,.2f}</td>
            </tr>"""
    else:
        html += f"""
            <tr class="amount-row">
                <td colspan="6" class="right">Add: CGST @ 9%</td>
                <td colspan="2" class="right">{cgst_amount:,.2f}</td>
            </tr>
            <tr class="amount-row">
                <td colspan="6" class="right">Add: SGST @ 9%</td>
                <td colspan="2" class="right">{sgst_amount:,.2f}</td>
            </tr>"""

    html += f"""
            <tr class="grand-total">
                <td colspan="6" class="right"><strong>GRAND TOTAL (₹)</strong></td>
                <td colspan="2" class="right"><strong>{grand_total:,.2f}</strong></td>
            </tr>
        </tbody>
    </table>

    <div class="amount-words">
        <strong>Amount in Words:</strong> {amount_to_words(grand_total)}
    </div>

    <div class="bank-details">
        <div><strong>BANK DETAILS FOR PAYMENT:</strong></div>
        <table style="border: none; margin-top: 5px;">
            <tr style="border: none;"><td style="border: none; width: 100px;">Account Name</td><td style="border: none;">: {COMPANY['name']}</td></tr>
            <tr style="border: none;"><td style="border: none;">Bank Name</td><td style="border: none;">: {COMPANY['bank_name']}</td></tr>
            <tr style="border: none;"><td style="border: none;">Account No.</td><td style="border: none;">: {COMPANY['account_no']}</td></tr>
            <tr style="border: none;"><td style="border: none;">IFSC Code</td><td style="border: none;">: {COMPANY['ifsc']}</td></tr>
        </table>
    </div>

    <div class="terms">
        <div><strong>Terms & Conditions:</strong></div>
        <ol style="margin-left: 15px; margin-top: 5px;">
            <li>Payment: 50% advance, balance before dispatch.</li>
            <li>Delivery: 7-10 working days from advance receipt.</li>
            <li>Warranty: 1 year from installation (excludes consumables).</li>
            <li>Subject to Delhi jurisdiction only.</li>
        </ol>
    </div>

    <div class="signature">
        <div>For <strong>{COMPANY['name']}</strong></div>
        <div style="margin-top: 50px; border-top: 1px solid #000; display: inline-block; padding-top: 5px;">Authorised Signatory</div>
    </div>
</body>
</html>"""

    return html, pi_number, grand_total


def generate_sales_order_html(items, doc_date):
    """Generate Sales Order HTML using FG Code."""
    so_number = "SO-2026-00001"

    subtotal = sum(item["qty"] * item["price"] for item in items)
    is_igst = COMPANY["state_code"] != BILL_TO["state_code"]

    if is_igst:
        igst_amount = subtotal * 0.18
        cgst_amount = sgst_amount = 0
    else:
        igst_amount = 0
        cgst_amount = sgst_amount = subtotal * 0.09

    grand_total = subtotal + igst_amount + cgst_amount + sgst_amount
    advance = grand_total * 0.5
    balance = grand_total - advance

    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Sales Order - {so_number}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: Arial, sans-serif; font-size: 11px; padding: 15px; }}
        .header {{ display: flex; justify-content: space-between; margin-bottom: 10px; }}
        .header-left {{ font-size: 10px; }}
        .header-right {{ text-align: right; font-size: 10px; }}
        .title {{ text-align: center; margin: 10px 0; }}
        .title h1 {{ font-size: 22px; font-weight: bold; color: #28a745; }}
        .title .address {{ font-size: 10px; color: #333; margin-top: 5px; }}
        .doc-type {{ text-align: center; background: #28a745; color: white; padding: 8px; font-weight: bold; margin: 15px 0; font-size: 14px; }}
        .info-row {{ display: flex; justify-content: space-between; margin-bottom: 10px; border: 1px solid #000; }}
        .info-box {{ padding: 8px; width: 50%; }}
        .info-box.right {{ border-left: 1px solid #000; }}
        .party-box {{ border: 1px solid #000; margin-bottom: 10px; }}
        .party-header {{ display: flex; background: #f0f0f0; border-bottom: 1px solid #000; }}
        .party-header-col {{ width: 50%; padding: 5px 10px; font-weight: bold; text-align: center; font-size: 10px; }}
        .party-header-col.right {{ border-left: 1px solid #000; }}
        .party-row {{ display: flex; }}
        .party-col {{ width: 50%; padding: 10px; line-height: 1.6; font-size: 11px; }}
        .party-col.right {{ border-left: 1px solid #000; }}
        table {{ width: 100%; border-collapse: collapse; margin-bottom: 10px; }}
        th, td {{ border: 1px solid #000; padding: 5px; text-align: center; font-size: 10px; }}
        th {{ background: #28a745; color: white; font-weight: bold; }}
        td.left {{ text-align: left; }}
        td.right {{ text-align: right; }}
        .amount-row {{ background: #f9f9f9; }}
        .grand-total {{ font-weight: bold; font-size: 12px; background: #d4edda !important; }}
        .payment-box {{ border: 1px solid #28a745; padding: 10px; margin: 10px 0; background: #d4edda; }}
        .terms {{ font-size: 10px; margin-top: 10px; }}
        .signature {{ text-align: right; margin-top: 20px; }}
        .amount-words {{ background: #ffffcc; padding: 8px; border: 1px solid #000; margin: 10px 0; font-size: 11px; }}
        .status-badge {{ display: inline-block; padding: 5px 15px; background: #28a745; color: white; border-radius: 20px; font-weight: bold; }}
        .fg-code {{ font-family: 'Courier New', monospace; font-weight: bold; color: #28a745; }}
        .print-btn {{ position: fixed; top: 10px; right: 10px; padding: 10px 20px; background: #28a745; color: white; border: none; cursor: pointer; font-size: 14px; border-radius: 5px; }}
        @media print {{ .print-btn {{ display: none; }} }}
    </style>
</head>
<body>
    <button class="print-btn" onclick="window.print()">Print / Save as PDF</button>

    <div class="header">
        <div class="header-left">
            <div><strong>GSTIN :</strong> {COMPANY['gstin']}</div>
            <div><strong>STATE :</strong> {COMPANY['state'].upper()}</div>
            <div><strong>STATE CODE :</strong> {COMPANY['state_code']}</div>
            <div><strong>PAN NO. :</strong> {COMPANY['pan']}</div>
        </div>
        <div class="header-right">
            <div><strong>CIN :</strong> {COMPANY['cin']}</div>
            <div style="margin-top: 10px;"><span class="status-badge">✓ CONFIRMED</span></div>
        </div>
    </div>

    <div class="doc-type">SALES ORDER</div>

    <div class="title">
        <h1>{COMPANY['name']}</h1>
        
        <div class="address">{COMPANY['address_line1']}, {COMPANY['address_line2']}, {COMPANY['city']}, {COMPANY['state']} - {COMPANY['pincode']}</div>
    </div>

    <div class="info-row">
        <div class="info-box">
            <div><strong>Sales Order No. :</strong> {so_number}</div>
            <div><strong>PI Reference :</strong> PI-2026-00001</div>
            <div><strong>Customer PO :</strong> ABC/PO/2026/001</div>
        </div>
        <div class="info-box right">
            <div><strong>Order Date :</strong> {doc_date.strftime('%d-%m-%Y')}</div>
            <div><strong>Expected Delivery :</strong> {date(2026, 1, 17).strftime('%d-%m-%Y')}</div>
            <div><strong>Payment Terms :</strong> 50% Advance</div>
        </div>
    </div>

    <div class="party-box">
        <div class="party-header">
            <div class="party-header-col">Details Of Buyer | Billed To:</div>
            <div class="party-header-col right">Details Of Consignee | Shipped To:</div>
        </div>
        <div class="party-row">
            <div class="party-col">
                <strong>{BILL_TO['name']}</strong><br>
                {BILL_TO['address_line1']}<br>
                {BILL_TO['address_line2']}<br>
                {BILL_TO['city']}, {BILL_TO['state']} - {BILL_TO['pincode']}<br><br>
                <strong>State Code :</strong> {BILL_TO['state_code']}<br>
                <strong>GSTIN :</strong> {BILL_TO['gstin']}<br>
                <strong>Contact :</strong> {BILL_TO['contact_person']}
            </div>
            <div class="party-col right">
                <strong>{SHIP_TO['name']}</strong><br>
                {SHIP_TO['address_line1']}<br>
                {SHIP_TO['address_line2']}<br>
                {SHIP_TO['city']}, {SHIP_TO['state']} - {SHIP_TO['pincode']}<br><br>
                <strong>State Code :</strong> {SHIP_TO['state_code']}<br>
                <strong>GSTIN :</strong> {SHIP_TO['gstin']}<br>
                <strong>Contact :</strong> {SHIP_TO['contact_person']}
            </div>
        </div>
    </div>

    <table>
        <thead>
            <tr>
                <th style="width: 25px;">S.N.</th>
                <th>Description of Goods</th>
                <th style="width: 100px;">FG CODE</th>
                <th style="width: 70px;">HSN/SAC</th>
                <th style="width: 45px;">Qty</th>
                <th style="width: 35px;">Unit</th>
                <th style="width: 70px;">Rate (₹)</th>
                <th style="width: 90px;">Amount (₹)</th>
            </tr>
        </thead>
        <tbody>"""

    total_qty = 0
    for item in items:
        amount = item["qty"] * item["price"]
        total_qty += item["qty"]
        html += f"""
            <tr>
                <td>{item['sn']}</td>
                <td class="left">{item['description']}</td>
                <td class="fg-code">{item['fg_code']}</td>
                <td>{item['hsn']}</td>
                <td>{item['qty']:,}</td>
                <td>{item['unit']}</td>
                <td class="right">{item['price']:,.2f}</td>
                <td class="right">{amount:,.2f}</td>
            </tr>"""

    html += f"""
            <tr class="amount-row">
                <td colspan="4" class="right"><strong>Sub Total</strong></td>
                <td><strong>{total_qty:,}</strong></td>
                <td></td>
                <td colspan="2" class="right"><strong>{subtotal:,.2f}</strong></td>
            </tr>"""

    if is_igst:
        html += f"""
            <tr class="amount-row"><td colspan="6" class="right">IGST @ 18%</td><td colspan="2" class="right">{igst_amount:,.2f}</td></tr>"""
    else:
        html += f"""
            <tr class="amount-row"><td colspan="6" class="right">CGST @ 9%</td><td colspan="2" class="right">{cgst_amount:,.2f}</td></tr>
            <tr class="amount-row"><td colspan="6" class="right">SGST @ 9%</td><td colspan="2" class="right">{sgst_amount:,.2f}</td></tr>"""

    html += f"""
            <tr class="grand-total">
                <td colspan="6" class="right"><strong>GRAND TOTAL (₹)</strong></td>
                <td colspan="2" class="right"><strong>{grand_total:,.2f}</strong></td>
            </tr>
        </tbody>
    </table>

    <div class="amount-words"><strong>Amount in Words:</strong> {amount_to_words(grand_total)}</div>

    <div class="payment-box">
        <table style="border: none; width: 100%;">
            <tr style="border: none;"><td style="border: none; width: 50%;"><strong>Total Order Value:</strong></td><td style="border: none; text-align: right;">₹{grand_total:,.2f}</td></tr>
            <tr style="border: none;"><td style="border: none;"><strong>Advance Received (50%):</strong></td><td style="border: none; text-align: right; color: green;">₹{advance:,.2f}</td></tr>
            <tr style="border: none;"><td style="border: none;"><strong>Balance Due:</strong></td><td style="border: none; text-align: right; color: red; font-weight: bold;">₹{balance:,.2f}</td></tr>
        </table>
    </div>

    <div class="terms">
        <div><strong>Terms & Conditions:</strong></div>
        <ol style="margin-left: 15px; margin-top: 5px;">
            <li>Order confirmed against PI-2026-00001.</li>
            <li>Delivery after balance payment.</li>
            <li>Warranty: 1 year from installation.</li>
        </ol>
    </div>

    <div class="signature">
        <div>For <strong>{COMPANY['name']}</strong></div>
        <div style="margin-top: 50px; border-top: 1px solid #000; display: inline-block; padding-top: 5px;">Authorised Signatory</div>
    </div>
</body>
</html>"""

    return html, so_number, grand_total


def generate_tax_invoice_html(items, doc_date):
    """Generate Tax Invoice HTML using FG Code."""
    inv_number = "INV-2026-00001"
    eway_bill = "331234567890"

    subtotal = sum(item["qty"] * item["price"] for item in items)
    is_igst = COMPANY["state_code"] != BILL_TO["state_code"]

    if is_igst:
        igst_amount = subtotal * 0.18
        cgst_amount = sgst_amount = 0
    else:
        igst_amount = 0
        cgst_amount = sgst_amount = subtotal * 0.09

    grand_total = subtotal + igst_amount + cgst_amount + sgst_amount

    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Tax Invoice - {inv_number}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: Arial, sans-serif; font-size: 11px; padding: 15px; }}
        .header {{ display: flex; justify-content: space-between; margin-bottom: 10px; }}
        .header-left {{ font-size: 10px; }}
        .header-right {{ text-align: right; font-size: 10px; }}
        .title {{ text-align: center; margin: 10px 0; }}
        .title h1 {{ font-size: 22px; font-weight: bold; color: #dc3545; }}
        .title .address {{ font-size: 10px; color: #333; margin-top: 5px; }}
        .doc-type {{ text-align: center; background: #dc3545; color: white; padding: 8px; font-weight: bold; margin: 15px 0; font-size: 14px; }}
        .copy-type {{ text-align: center; font-size: 10px; font-weight: bold; margin-bottom: 10px; }}
        .info-row {{ display: flex; justify-content: space-between; margin-bottom: 10px; border: 1px solid #000; }}
        .info-box {{ padding: 8px; width: 50%; }}
        .info-box.right {{ border-left: 1px solid #000; }}
        .transport-box {{ border: 1px solid #000; padding: 8px; margin: 10px 0; background: #e9ecef; font-size: 10px; }}
        .party-box {{ border: 1px solid #000; margin-bottom: 10px; }}
        .party-header {{ display: flex; background: #f0f0f0; border-bottom: 1px solid #000; }}
        .party-header-col {{ width: 50%; padding: 5px 10px; font-weight: bold; text-align: center; font-size: 10px; }}
        .party-header-col.right {{ border-left: 1px solid #000; }}
        .party-row {{ display: flex; }}
        .party-col {{ width: 50%; padding: 10px; line-height: 1.6; font-size: 11px; }}
        .party-col.right {{ border-left: 1px solid #000; }}
        table {{ width: 100%; border-collapse: collapse; margin-bottom: 10px; }}
        th, td {{ border: 1px solid #000; padding: 4px; text-align: center; font-size: 9px; }}
        th {{ background: #dc3545; color: white; font-weight: bold; }}
        td.left {{ text-align: left; }}
        td.right {{ text-align: right; }}
        .amount-row {{ background: #f9f9f9; }}
        .grand-total {{ font-weight: bold; font-size: 11px; background: #f8d7da !important; }}
        .bank-details {{ border: 1px solid #000; padding: 10px; margin-bottom: 10px; background: #f9f9f9; }}
        .terms {{ font-size: 9px; margin-top: 10px; }}
        .signature-row {{ display: flex; justify-content: space-between; margin-top: 15px; }}
        .signature-box {{ text-align: center; width: 30%; font-size: 10px; }}
        .amount-words {{ background: #ffffcc; padding: 8px; border: 1px solid #000; margin: 10px 0; font-size: 11px; }}
        .fg-code {{ font-family: 'Courier New', monospace; font-weight: bold; color: #dc3545; }}
        .print-btn {{ position: fixed; top: 10px; right: 10px; padding: 10px 20px; background: #dc3545; color: white; border: none; cursor: pointer; font-size: 14px; border-radius: 5px; }}
        @media print {{ .print-btn {{ display: none; }} }}
    </style>
</head>
<body>
    <button class="print-btn" onclick="window.print()">Print / Save as PDF</button>

    <div class="header">
        <div class="header-left">
            <div><strong>GSTIN :</strong> {COMPANY['gstin']}</div>
            <div><strong>STATE :</strong> {COMPANY['state'].upper()}</div>
            <div><strong>STATE CODE :</strong> {COMPANY['state_code']}</div>
            <div><strong>PAN NO. :</strong> {COMPANY['pan']}</div>
        </div>
        <div class="header-right">
            <div><strong>CIN :</strong> {COMPANY['cin']}</div>
            <div style="margin-top: 5px; border: 1px dashed #999; padding: 5px; font-size: 9px;">[ QR Code ]</div>
        </div>
    </div>

    <div class="doc-type">TAX INVOICE</div>
    <div class="copy-type">(ORIGINAL FOR RECIPIENT)</div>

    <div class="title">
        <h1>{COMPANY['name']}</h1>
        
        <div class="address">{COMPANY['address_line1']}, {COMPANY['address_line2']}, {COMPANY['city']}, {COMPANY['state']} - {COMPANY['pincode']}</div>
    </div>

    <div class="info-row">
        <div class="info-box">
            <div><strong>Invoice No. :</strong> {inv_number}</div>
            <div><strong>SO Reference :</strong> SO-2026-00001</div>
            <div><strong>IRN :</strong> <em>Generated on filing</em></div>
        </div>
        <div class="info-box right">
            <div><strong>Invoice Date :</strong> {doc_date.strftime('%d-%m-%Y')}</div>
            <div><strong>E-Way Bill :</strong> {eway_bill}</div>
            <div><strong>Payment Status :</strong> <span style="color: green; font-weight: bold;">PAID</span></div>
        </div>
    </div>

    <div class="transport-box">
        <strong>Transport Details:</strong> Vehicle: DL01AB1234 | Transporter: BlueDart Express | Mode: Road | Distance: 45 KM
    </div>

    <div class="party-box">
        <div class="party-header">
            <div class="party-header-col">Details Of Buyer | Billed To:</div>
            <div class="party-header-col right">Details Of Consignee | Shipped To:</div>
        </div>
        <div class="party-row">
            <div class="party-col">
                <strong>{BILL_TO['name']}</strong><br>
                {BILL_TO['address_line1']}<br>
                {BILL_TO['address_line2']}<br>
                {BILL_TO['city']}, {BILL_TO['state']} - {BILL_TO['pincode']}<br><br>
                <strong>State Code :</strong> {BILL_TO['state_code']}<br>
                <strong>GSTIN :</strong> {BILL_TO['gstin']}
            </div>
            <div class="party-col right">
                <strong>{SHIP_TO['name']}</strong><br>
                {SHIP_TO['address_line1']}<br>
                {SHIP_TO['address_line2']}<br>
                {SHIP_TO['city']}, {SHIP_TO['state']} - {SHIP_TO['pincode']}<br><br>
                <strong>State Code :</strong> {SHIP_TO['state_code']}<br>
                <strong>GSTIN :</strong> {SHIP_TO['gstin']}
            </div>
        </div>
    </div>

    <table>
        <thead>
            <tr>
                <th style="width: 20px;">S.N.</th>
                <th>Description of Goods</th>
                <th style="width: 90px;">FG CODE</th>
                <th style="width: 60px;">HSN/SAC</th>
                <th style="width: 35px;">Qty</th>
                <th style="width: 30px;">Unit</th>
                <th style="width: 55px;">Rate</th>
                <th style="width: 70px;">Taxable Amt</th>
                <th style="width: 40px;">GST%</th>
                <th style="width: 55px;">GST Amt</th>
                <th style="width: 70px;">Total (₹)</th>
            </tr>
        </thead>
        <tbody>"""

    total_qty = 0
    total_taxable = 0
    total_gst = 0
    for item in items:
        taxable = item["qty"] * item["price"]
        gst_amt = taxable * 0.18
        total = taxable + gst_amt
        total_qty += item["qty"]
        total_taxable += taxable
        total_gst += gst_amt

        html += f"""
            <tr>
                <td>{item['sn']}</td>
                <td class="left">{item['description']}</td>
                <td class="fg-code">{item['fg_code']}</td>
                <td>{item['hsn']}</td>
                <td>{item['qty']}</td>
                <td>{item['unit']}</td>
                <td class="right">{item['price']:,.2f}</td>
                <td class="right">{taxable:,.2f}</td>
                <td>18%</td>
                <td class="right">{gst_amt:,.2f}</td>
                <td class="right">{total:,.2f}</td>
            </tr>"""

    html += f"""
            <tr class="amount-row">
                <td colspan="4" class="right"><strong>Total</strong></td>
                <td><strong>{total_qty}</strong></td>
                <td></td>
                <td></td>
                <td class="right"><strong>{total_taxable:,.2f}</strong></td>
                <td></td>
                <td class="right"><strong>{total_gst:,.2f}</strong></td>
                <td class="right"><strong>{grand_total:,.2f}</strong></td>
            </tr>
            <tr class="amount-row"><td colspan="9" class="right">Taxable Amount</td><td colspan="2" class="right">{subtotal:,.2f}</td></tr>"""

    if is_igst:
        html += f"""<tr class="amount-row"><td colspan="9" class="right">IGST @ 18%</td><td colspan="2" class="right">{igst_amount:,.2f}</td></tr>"""
    else:
        html += f"""
            <tr class="amount-row"><td colspan="9" class="right">CGST @ 9%</td><td colspan="2" class="right">{cgst_amount:,.2f}</td></tr>
            <tr class="amount-row"><td colspan="9" class="right">SGST @ 9%</td><td colspan="2" class="right">{sgst_amount:,.2f}</td></tr>"""

    html += f"""
            <tr class="grand-total">
                <td colspan="9" class="right"><strong>GRAND TOTAL (₹)</strong></td>
                <td colspan="2" class="right"><strong>{grand_total:,.2f}</strong></td>
            </tr>
        </tbody>
    </table>

    <div class="amount-words"><strong>Amount in Words:</strong> {amount_to_words(grand_total)}</div>

    <div class="bank-details">
        <div><strong>BANK DETAILS:</strong></div>
        <table style="border: none; margin-top: 5px; font-size: 10px;">
            <tr style="border: none;"><td style="border: none; width: 80px;">Account Name</td><td style="border: none;">: {COMPANY['name']}</td></tr>
            <tr style="border: none;"><td style="border: none;">Bank / Branch</td><td style="border: none;">: {COMPANY['bank_name']} / {COMPANY['bank_branch']}</td></tr>
            <tr style="border: none;"><td style="border: none;">A/c No. / IFSC</td><td style="border: none;">: {COMPANY['account_no']} / {COMPANY['ifsc']}</td></tr>
        </table>
    </div>

    <div class="terms">
        <strong>Terms:</strong> Goods once sold will not be taken back. Subject to Delhi jurisdiction. E&OE.
    </div>

    <div class="signature-row">
        <div class="signature-box"><div style="border-bottom: 1px solid #000; height: 40px;"></div><div>Customer Signature</div></div>
        <div class="signature-box"><div style="border-bottom: 1px solid #000; height: 40px;"></div><div>Received By</div></div>
        <div class="signature-box">
            <div>For <strong>{COMPANY['name']}</strong></div>
            <div style="border-bottom: 1px solid #000; height: 35px; margin-top: 5px;"></div>
            <div>Authorised Signatory</div>
        </div>
    </div>
</body>
</html>"""

    return html, inv_number, grand_total


def generate_eway_bill_html(items, doc_date):
    """Generate E-Way Bill HTML using FG Code."""
    eway_number = "331234567890"
    inv_number = "INV-2026-00001"

    subtotal = sum(item["qty"] * item["price"] for item in items)
    is_igst = COMPANY["state_code"] != BILL_TO["state_code"]

    if is_igst:
        igst_amount = subtotal * 0.18
        cgst_amount = sgst_amount = 0
    else:
        igst_amount = 0
        cgst_amount = sgst_amount = subtotal * 0.09

    grand_total = subtotal + igst_amount + cgst_amount + sgst_amount

    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>E-Way Bill - {eway_number}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: Arial, sans-serif; font-size: 11px; padding: 15px; }}
        .header {{ text-align: center; margin-bottom: 10px; }}
        .header h1 {{ font-size: 20px; color: #6c3483; margin-bottom: 5px; }}
        .header .sub {{ font-size: 12px; color: #666; }}
        .eway-box {{ border: 2px solid #6c3483; padding: 15px; margin-bottom: 15px; }}
        .eway-header {{ display: flex; justify-content: space-between; margin-bottom: 15px; }}
        .eway-number {{ font-size: 16px; font-weight: bold; color: #6c3483; }}
        .qr-box {{ border: 1px dashed #999; padding: 10px; text-align: center; font-size: 10px; }}
        .section {{ margin-bottom: 15px; }}
        .section-title {{ background: #6c3483; color: white; padding: 5px 10px; font-weight: bold; font-size: 11px; margin-bottom: 5px; }}
        .section-content {{ padding: 10px; border: 1px solid #ddd; font-size: 10px; }}
        .two-col {{ display: flex; }}
        .col {{ width: 50%; padding: 5px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
        th, td {{ border: 1px solid #000; padding: 5px; text-align: center; font-size: 9px; }}
        th {{ background: #6c3483; color: white; }}
        td.left {{ text-align: left; }}
        td.right {{ text-align: right; }}
        .total-row {{ background: #f0e6f6; font-weight: bold; }}
        .fg-code {{ font-family: 'Courier New', monospace; font-weight: bold; color: #6c3483; }}
        .print-btn {{ position: fixed; top: 10px; right: 10px; padding: 10px 20px; background: #6c3483; color: white; border: none; cursor: pointer; font-size: 14px; border-radius: 5px; }}
        @media print {{ .print-btn {{ display: none; }} }}
    </style>
</head>
<body>
    <button class="print-btn" onclick="window.print()">Print / Save as PDF</button>

    <div class="header">
        <h1>E-WAY BILL</h1>
        <div class="sub">Generated from GST Portal - NIC</div>
    </div>

    <div class="eway-box">
        <div class="eway-header">
            <div>
                <div class="eway-number">E-Way Bill No: {eway_number}</div>
                <div style="font-size: 10px; margin-top: 5px;">Generated Date: {doc_date.strftime('%d-%m-%Y %H:%M')}</div>
                <div style="font-size: 10px;">Valid Until: {date(2026, 1, 10).strftime('%d-%m-%Y %H:%M')}</div>
            </div>
            <div class="qr-box">
                [ QR Code ]<br>
                Scan to verify
            </div>
        </div>

        <div class="two-col">
            <div class="col">
                <div class="section">
                    <div class="section-title">PART-A: SUPPLY DETAILS</div>
                    <div class="section-content">
                        <div><strong>Document Type:</strong> Tax Invoice</div>
                        <div><strong>Document No:</strong> {inv_number}</div>
                        <div><strong>Document Date:</strong> {doc_date.strftime('%d-%m-%Y')}</div>
                        <div><strong>Supply Type:</strong> Outward - B2B</div>
                        <div><strong>Sub Supply Type:</strong> Supply</div>
                        <div><strong>Transaction Type:</strong> Regular</div>
                    </div>
                </div>
            </div>
            <div class="col">
                <div class="section">
                    <div class="section-title">PART-B: VEHICLE DETAILS</div>
                    <div class="section-content">
                        <div><strong>Mode:</strong> Road</div>
                        <div><strong>Vehicle No:</strong> DL01AB1234</div>
                        <div><strong>From:</strong> {COMPANY['city']}, {COMPANY['state']}</div>
                        <div><strong>To:</strong> {SHIP_TO['city']}, {SHIP_TO['state']}</div>
                        <div><strong>Distance:</strong> 45 KM</div>
                        <div><strong>Transporter:</strong> BlueDart Express</div>
                    </div>
                </div>
            </div>
        </div>

        <div class="two-col">
            <div class="col">
                <div class="section">
                    <div class="section-title">FROM (Consignor)</div>
                    <div class="section-content">
                        <div><strong>{COMPANY['name']}</strong></div>
                        <div>{COMPANY['address_line1']}</div>
                        <div>{COMPANY['city']}, {COMPANY['state']} - {COMPANY['pincode']}</div>
                        <div><strong>GSTIN:</strong> {COMPANY['gstin']}</div>
                        <div><strong>State Code:</strong> {COMPANY['state_code']}</div>
                    </div>
                </div>
            </div>
            <div class="col">
                <div class="section">
                    <div class="section-title">TO (Consignee)</div>
                    <div class="section-content">
                        <div><strong>{SHIP_TO['name']}</strong></div>
                        <div>{SHIP_TO['address_line1']}</div>
                        <div>{SHIP_TO['city']}, {SHIP_TO['state']} - {SHIP_TO['pincode']}</div>
                        <div><strong>GSTIN:</strong> {SHIP_TO['gstin']}</div>
                        <div><strong>State Code:</strong> {SHIP_TO['state_code']}</div>
                    </div>
                </div>
            </div>
        </div>

        <div class="section">
            <div class="section-title">ITEM DETAILS</div>
            <table>
                <thead>
                    <tr>
                        <th style="width: 25px;">S.N.</th>
                        <th>Product Name</th>
                        <th style="width: 90px;">FG CODE</th>
                        <th style="width: 70px;">HSN Code</th>
                        <th style="width: 45px;">Qty</th>
                        <th style="width: 40px;">Unit</th>
                        <th style="width: 80px;">Taxable Value</th>
                        <th style="width: 50px;">Tax Rate</th>
                        <th style="width: 70px;">Tax Amount</th>
                    </tr>
                </thead>
                <tbody>"""

    total_qty = 0
    total_taxable = 0
    total_tax = 0
    for item in items:
        taxable = item["qty"] * item["price"]
        tax_amt = taxable * 0.18
        total_qty += item["qty"]
        total_taxable += taxable
        total_tax += tax_amt

        html += f"""
                    <tr>
                        <td>{item['sn']}</td>
                        <td class="left">{item['description']}</td>
                        <td class="fg-code">{item['fg_code']}</td>
                        <td>{item['hsn']}</td>
                        <td>{item['qty']}</td>
                        <td>{item['unit']}</td>
                        <td class="right">{taxable:,.2f}</td>
                        <td>18%</td>
                        <td class="right">{tax_amt:,.2f}</td>
                    </tr>"""

    html += f"""
                    <tr class="total-row">
                        <td colspan="4" class="right"><strong>TOTAL</strong></td>
                        <td><strong>{total_qty}</strong></td>
                        <td></td>
                        <td class="right"><strong>{total_taxable:,.2f}</strong></td>
                        <td></td>
                        <td class="right"><strong>{total_tax:,.2f}</strong></td>
                    </tr>
                </tbody>
            </table>
        </div>

        <div class="section">
            <div class="section-title">VALUE SUMMARY</div>
            <div class="section-content">
                <div class="two-col">
                    <div class="col">
                        <div><strong>Total Taxable Value:</strong> ₹{subtotal:,.2f}</div>
                        {"<div><strong>IGST:</strong> ₹" + f"{igst_amount:,.2f}</div>" if is_igst else f"<div><strong>CGST:</strong> ₹{cgst_amount:,.2f}</div><div><strong>SGST:</strong> ₹{sgst_amount:,.2f}</div>"}
                    </div>
                    <div class="col">
                        <div><strong>Total Tax:</strong> ₹{total_tax:,.2f}</div>
                        <div style="font-size: 14px; color: #6c3483; font-weight: bold;"><strong>Total Invoice Value:</strong> ₹{grand_total:,.2f}</div>
                    </div>
                </div>
            </div>
        </div>

        <div style="text-align: center; margin-top: 15px; font-size: 9px; color: #666;">
            This is a computer-generated E-Way Bill. No signature required.<br>
            Verify at: https://ewaybillgst.gov.in
        </div>
    </div>
</body>
</html>"""

    return html, eway_number, grand_total


async def main():
    """Generate all sales documents using Product Master data."""
    print("=" * 60)
    print("ILMS.AI ERP - Sales Document Generator")
    print("Using FG Codes from Product Master")
    print("=" * 60)

    # Fetch products from database
    items = await get_products_from_master()

    if not items:
        print("\n❌ No products with FG Codes found in Product Master!")
        print("   Please ensure products have fg_code set.")
        return

    print(f"\n✓ Loaded {len(items)} products from Product Master:")
    for item in items:
        print(f"  - {item['description']}: {item['fg_code']}")

    doc_date = date(2026, 1, 7)
    desktop = os.path.expanduser("~/Desktop")

    # Generate all documents
    print("\n" + "-" * 60)
    print("Generating Documents...")

    # 1. Sales Proforma Invoice
    html, doc_num, total = generate_sales_proforma_html(items, doc_date)
    filename = f"{desktop}/PI-2026-00001-FG.html"
    with open(filename, 'w') as f:
        f.write(html)
    print(f"✓ Sales Proforma Invoice: {filename}")
    print(f"  Amount: ₹{total:,.2f}")

    # 2. Sales Order
    html, doc_num, total = generate_sales_order_html(items, doc_date)
    filename = f"{desktop}/SO-2026-00001-FG.html"
    with open(filename, 'w') as f:
        f.write(html)
    print(f"✓ Sales Order: {filename}")
    print(f"  Amount: ₹{total:,.2f}")

    # 3. Tax Invoice
    html, doc_num, total = generate_tax_invoice_html(items, doc_date)
    filename = f"{desktop}/INV-2026-00001-FG.html"
    with open(filename, 'w') as f:
        f.write(html)
    print(f"✓ Tax Invoice: {filename}")
    print(f"  Amount: ₹{total:,.2f}")

    # 4. E-Way Bill
    html, doc_num, total = generate_eway_bill_html(items, doc_date)
    filename = f"{desktop}/EWAY-331234567890.html"
    with open(filename, 'w') as f:
        f.write(html)
    print(f"✓ E-Way Bill: {filename}")
    print(f"  Amount: ₹{total:,.2f}")

    print("\n" + "=" * 60)
    print("All documents generated with FG Codes from Product Master!")
    print("Opening in browser...")
    print("=" * 60)

    # Open all files
    subprocess.run(['open',
        f"{desktop}/PI-2026-00001-FG.html",
        f"{desktop}/SO-2026-00001-FG.html",
        f"{desktop}/INV-2026-00001-FG.html",
        f"{desktop}/EWAY-331234567890.html"
    ])


if __name__ == "__main__":
    asyncio.run(main())
