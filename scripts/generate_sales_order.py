"""
Generate Sales Order PDF for ILMS.AI.
This is the confirmed order document ILMS.AI (as seller) issues to customers.

ILMS.AI ERP System - Sales Document
"""
import asyncio
import sys
import os
import subprocess
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from decimal import Decimal
from datetime import datetime, date


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


async def generate_sales_order():
    """Generate Sales Order from ILMS.AI."""

    # ILMS.AI Company Details (Seller)
    company = {
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
    }

    # Sample Customer (Buyer) - Bill To
    bill_to = {
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

    # Ship To
    ship_to = {
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

    # Sales Order Details
    so_number = "SO-2026-00001"
    so_date = date(2026, 1, 7)
    pi_reference = "PI-2026-00001"
    expected_delivery = date(2026, 1, 17)
    payment_received = 301844.00  # 50% advance

    # Sample Items
    items = [
        {"sn": 1, "description": "AquaPure RO System - 25 LPH", "part_code": "AP-RO-025", "hsn": "84212110", "qty": 5, "unit": "Nos", "price": 45000.00},
        {"sn": 2, "description": "AquaPure UV System - 50 LPH", "part_code": "AP-UV-050", "hsn": "84212110", "qty": 3, "unit": "Nos", "price": 35000.00},
        {"sn": 3, "description": "Sediment Filter Cartridge - 10\"", "part_code": "AP-SED-10", "hsn": "84212190", "qty": 100, "unit": "Pcs", "price": 150.00},
        {"sn": 4, "description": "Carbon Block Filter - 10\"", "part_code": "AP-CB-10", "hsn": "84212190", "qty": 100, "unit": "Pcs", "price": 250.00},
        {"sn": 5, "description": "RO Membrane - 100 GPD", "part_code": "AP-MEM-100", "hsn": "84212190", "qty": 50, "unit": "Pcs", "price": 1800.00},
        {"sn": 6, "description": "UV Lamp Assembly - 11W", "part_code": "AP-UVL-11", "hsn": "85393110", "qty": 20, "unit": "Pcs", "price": 850.00},
        {"sn": 7, "description": "Pressure Pump - 100 GPD", "part_code": "AP-PMP-100", "hsn": "84138190", "qty": 10, "unit": "Pcs", "price": 2500.00},
        {"sn": 8, "description": "Installation Kit - Standard", "part_code": "AP-KIT-STD", "hsn": "84212190", "qty": 8, "unit": "Sets", "price": 1200.00},
    ]

    # Calculate totals
    subtotal = sum(item["qty"] * item["price"] for item in items)
    is_igst = company["state_code"] != bill_to["state_code"]

    if is_igst:
        igst_amount = subtotal * 0.18
        cgst_amount = sgst_amount = 0
    else:
        igst_amount = 0
        cgst_amount = sgst_amount = subtotal * 0.09

    grand_total = subtotal + igst_amount + cgst_amount + sgst_amount
    balance_due = grand_total - payment_received

    # Generate HTML
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Sales Order - {so_number}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: Arial, sans-serif; font-size: 11px; padding: 15px; background: #fff; }}
        .header {{ display: flex; justify-content: space-between; margin-bottom: 10px; }}
        .header-left {{ font-size: 10px; }}
        .header-right {{ text-align: right; font-size: 10px; }}
        .title {{ text-align: center; margin: 10px 0; }}
        .title h1 {{ font-size: 22px; font-weight: bold; color: #28a745; margin-bottom: 3px; }}
        .title .address {{ font-size: 10px; color: #333; margin-top: 5px; }}
        .title .contact {{ font-size: 10px; color: #333; }}
        .doc-type {{ text-align: center; background: #28a745; color: white; padding: 8px; font-weight: bold; margin: 15px 0; font-size: 14px; letter-spacing: 1px; }}
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
        .status-badge {{ display: inline-block; padding: 5px 15px; border-radius: 20px; font-weight: bold; font-size: 11px; }}
        .status-confirmed {{ background: #28a745; color: white; }}
        .print-btn {{ position: fixed; top: 10px; right: 10px; padding: 10px 20px; background: #28a745; color: white; border: none; cursor: pointer; font-size: 14px; border-radius: 5px; z-index: 1000; }}
        .print-btn:hover {{ background: #218838; }}
        @media print {{
            .print-btn {{ display: none; }}
        }}
    </style>
</head>
<body>
    <button class="print-btn" onclick="window.print()">Print / Save as PDF</button>

    <!-- Header -->
    <div class="header">
        <div class="header-left">
            <div><strong>GSTIN :</strong> {company['gstin']}</div>
            <div><strong>STATE :</strong> {company['state'].upper()}</div>
            <div><strong>STATE CODE :</strong> {company['state_code']}</div>
            <div><strong>PAN NO. :</strong> {company['pan']}</div>
        </div>
        <div class="header-right">
            <div><strong>CIN :</strong> {company['cin']}</div>
            <div style="margin-top: 10px;"><span class="status-badge status-confirmed">✓ CONFIRMED</span></div>
        </div>
    </div>

    <!-- Document Type -->
    <div class="doc-type">SALES ORDER</div>

    <!-- Company Name -->
    <div class="title">
        <h1>{company['name']}</h1>
        
        <div class="address">{company['address_line1']}, {company['address_line2']}, {company['city']}, {company['state']} - {company['pincode']}</div>
        <div class="contact">Phone: {company['phone']} | Email: {company['email']} | Web: {company['website']}</div>
    </div>

    <!-- SO Details -->
    <div class="info-row">
        <div class="info-box">
            <div><strong>Sales Order No. :</strong> {so_number}</div>
            <div><strong>PI Reference :</strong> {pi_reference}</div>
            <div><strong>Customer PO :</strong> ABC/PO/2026/001</div>
        </div>
        <div class="info-box right">
            <div><strong>Order Date :</strong> {so_date.strftime('%d-%m-%Y')}</div>
            <div><strong>Expected Delivery :</strong> {expected_delivery.strftime('%d-%m-%Y')}</div>
            <div><strong>Payment Terms :</strong> 50% Advance, 50% Before Dispatch</div>
        </div>
    </div>

    <!-- Bill To & Ship To -->
    <div class="party-box">
        <div class="party-header">
            <div class="party-header-col">Details Of Buyer | Billed To:</div>
            <div class="party-header-col right">Details Of Consignee | Shipped To:</div>
        </div>
        <div class="party-row">
            <div class="party-col">
                <strong>{bill_to['name']}</strong><br>
                {bill_to['address_line1']}<br>
                {bill_to['address_line2']}<br>
                {bill_to['city']}, {bill_to['district']}, {bill_to['state']} - {bill_to['pincode']}<br>
                <br>
                <strong>State Code :</strong> {bill_to['state_code']}<br>
                <strong>GSTIN :</strong> {bill_to['gstin']}<br>
                <strong>Contact :</strong> {bill_to.get('contact_person', 'N/A')}<br>
                <strong>Phone :</strong> {bill_to.get('phone', 'N/A')}
            </div>
            <div class="party-col right">
                <strong>{ship_to['name']}</strong><br>
                {ship_to['address_line1']}<br>
                {ship_to['address_line2']}<br>
                {ship_to['city']}, {ship_to['district']}, {ship_to['state']} - {ship_to['pincode']}<br>
                <br>
                <strong>State Code :</strong> {ship_to['state_code']}<br>
                <strong>GSTIN :</strong> {ship_to['gstin']}<br>
                <strong>Contact :</strong> {ship_to.get('contact_person', 'N/A')}<br>
                <strong>Phone :</strong> {ship_to.get('phone', 'N/A')}
            </div>
        </div>
    </div>

    <!-- Items Table -->
    <table>
        <thead>
            <tr>
                <th style="width: 30px;">S.N.</th>
                <th>Description of Goods</th>
                <th style="width: 80px;">PART CODE</th>
                <th style="width: 70px;">HSN/SAC</th>
                <th style="width: 50px;">Qty</th>
                <th style="width: 40px;">Unit</th>
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
                <td>{item['part_code']}</td>
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

    <!-- Amount in Words -->
    <div class="amount-words">
        <strong>Amount in Words:</strong> {amount_to_words(grand_total)}
    </div>

    <!-- Payment Status -->
    <div class="payment-box">
        <table style="border: none; width: 100%;">
            <tr style="border: none;">
                <td style="border: none; width: 50%;"><strong>Total Order Value:</strong></td>
                <td style="border: none; text-align: right;">₹{grand_total:,.2f}</td>
            </tr>
            <tr style="border: none;">
                <td style="border: none;"><strong>Advance Received (50%):</strong></td>
                <td style="border: none; text-align: right; color: green;">₹{payment_received:,.2f}</td>
            </tr>
            <tr style="border: none;">
                <td style="border: none;"><strong>Balance Due Before Dispatch:</strong></td>
                <td style="border: none; text-align: right; color: #dc3545; font-weight: bold;">₹{balance_due:,.2f}</td>
            </tr>
        </table>
    </div>

    <!-- Terms -->
    <div class="terms">
        <div><strong>Terms & Conditions:</strong></div>
        <ol style="margin-left: 15px; margin-top: 5px;">
            <li>This Sales Order is raised against your confirmed purchase order.</li>
            <li>Delivery will be scheduled after receipt of balance payment.</li>
            <li>Goods will be dispatched within 3-5 working days after payment confirmation.</li>
            <li>Warranty: 1 year from date of installation.</li>
            <li>Subject to Delhi jurisdiction only.</li>
        </ol>
    </div>

    <!-- Signature -->
    <div class="signature">
        <div>For <strong>{company['name']}</strong></div>
        <div style="margin-top: 50px; border-top: 1px solid #000; display: inline-block; padding-top: 5px;">
            Authorised Signatory
        </div>
    </div>

</body>
</html>"""

    # Save
    filename = f"/tmp/{so_number}.html"
    with open(filename, 'w') as f:
        f.write(html)

    print(f"✓ Sales Order generated: {filename}")

    # Copy to Desktop
    desktop_file = os.path.expanduser(f"~/Desktop/{so_number}.html")
    import shutil
    shutil.copy(filename, desktop_file)

    return desktop_file


if __name__ == "__main__":
    asyncio.run(generate_sales_order())
