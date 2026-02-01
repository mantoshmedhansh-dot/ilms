#!/usr/bin/env python3
"""
Generate Purchase Order PO/APL/FF/25-26/001 from Aquapurite to FastTrack
Using master data from database

Reference: Proforma Invoice PI NO./FF/25-26/005 dated 19.11.2025
25% Advance Payment Made: Rs. 2,41,412.50
"""

import asyncio
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import text
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import async_session_factory

# PO Details
PO_NUMBER = "PO/APL/FF/25-26/001"
PO_DATE = date(2025, 11, 20)  # Date after PI date
PI_REFERENCE = "PI NO./FF/25-26/005"
PI_DATE = "19.11.2025"
EXPECTED_DELIVERY = "20.12.2025"  # 30 days from advance payment

# Order Items (from PI)
ORDER_ITEMS = [
    {
        "sr_no": 1,
        "name": "AQUAPURITE BLITZ (RO+UV)",
        "model_code": "BLITZ",
        "fg_code": "WPRABLZ001",
        "hsn_code": "84212110",
        "quantity": 150,
        "unit": "Nos",
        "unit_price": Decimal("2304.00"),
    },
    {
        "sr_no": 2,
        "name": "AQUAPURITE NEURA (RO+UV)",
        "model_code": "NEURA",
        "fg_code": "WPRANEU001",
        "hsn_code": "84212110",
        "quantity": 150,
        "unit": "Nos",
        "unit_price": Decimal("2509.00"),
    },
    {
        "sr_no": 3,
        "name": "AQUAPURITE i ELITZ (Hot/Normal/Ambient)",
        "model_code": "i ELITZ",
        "fg_code": "WPRAIEL001",
        "hsn_code": "84212110",
        "quantity": 20,
        "unit": "Nos",
        "unit_price": Decimal("12185.00"),
    },
]

# Payment Details
ADVANCE_PERCENTAGE = Decimal("25")
ADVANCE_PAID = Decimal("241412.50")
ADVANCE_DATE = "20.11.2025"
ADVANCE_REF = "RTGS/NEFT Transfer"

# GST Rates (Intra-state: CGST + SGST for Delhi to Delhi)
CGST_RATE = Decimal("9")
SGST_RATE = Decimal("9")


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
    paise = int(round((num - rupees) * 100))

    result = 'Rupees ' + words(rupees)
    if paise:
        result += ' and ' + words(paise) + ' Paise'
    return result + ' Only'


def generate_po_html(company: dict, vendor: dict) -> str:
    """Generate Purchase Order HTML using master data"""

    # Calculate totals
    items_html = ""
    subtotal = Decimal("0")
    total_qty = 0

    for item in ORDER_ITEMS:
        amount = item["quantity"] * item["unit_price"]
        subtotal += amount
        total_qty += item["quantity"]
        items_html += f"""
                <tr>
                    <td class="text-center">{item['sr_no']}</td>
                    <td>
                        <strong>{item['name']}</strong><br>
                        <span style="font-size: 9px; color: #666;">Model: {item['model_code']}</span>
                    </td>
                    <td class="text-center"><span class="fg-code">{item['fg_code']}</span></td>
                    <td class="text-center">{item['hsn_code']}</td>
                    <td class="text-center"><strong>{item['quantity']}</strong></td>
                    <td class="text-center">{item['unit']}</td>
                    <td class="text-right">Rs. {item['unit_price']:,.2f}</td>
                    <td class="text-right"><strong>Rs. {amount:,.2f}</strong></td>
                </tr>"""

    # Tax calculations (Intra-state: CGST + SGST - Both Delhi)
    cgst_amount = subtotal * CGST_RATE / 100
    sgst_amount = subtotal * SGST_RATE / 100
    total_tax = cgst_amount + sgst_amount
    grand_total = subtotal + total_tax
    balance_due = grand_total - ADVANCE_PAID

    # Format company address
    company_address = f"""{company['address_line1']}
{company['address_line2'] if company['address_line2'] else ''}
{company['city']}, {company['state']} - {company['pincode']}"""

    # Format vendor address
    vendor_address = f"""{vendor['address_line1']}
{vendor['address_line2'] if vendor['address_line2'] else ''}
{vendor['city']}, {vendor['state']} - {vendor['pincode']}"""

    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Purchase Order - {PO_NUMBER}</title>
    <style>
        @page {{ size: A4; margin: 10mm; }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: Arial, sans-serif; font-size: 11px; line-height: 1.4; padding: 10px; background: #fff; }}
        .document {{ max-width: 210mm; margin: 0 auto; border: 2px solid #000; }}

        /* Header */
        .header {{ background: linear-gradient(135deg, #1a5f7a 0%, #0d3d4d 100%); color: white; padding: 15px; text-align: center; }}
        .header h1 {{ font-size: 24px; margin-bottom: 8px; letter-spacing: 2px; }}
        .header .contact {{ font-size: 9px; }}

        /* Document Title */
        .doc-title {{ background: #f0f0f0; padding: 12px; text-align: center; border-bottom: 2px solid #000; }}
        .doc-title h2 {{ font-size: 18px; color: #1a5f7a; }}

        /* Info Grid */
        .info-grid {{ display: flex; flex-wrap: wrap; border-bottom: 1px solid #000; }}
        .info-box {{ flex: 1; min-width: 25%; padding: 8px 10px; border-right: 1px solid #000; }}
        .info-box:last-child {{ border-right: none; }}
        .info-box label {{ display: block; font-size: 9px; color: #666; text-transform: uppercase; margin-bottom: 3px; }}
        .info-box value {{ display: block; font-weight: bold; font-size: 11px; }}

        /* Party Section */
        .party-section {{ display: flex; border-bottom: 1px solid #000; }}
        .party-box {{ flex: 1; padding: 10px; border-right: 1px solid #000; }}
        .party-box:last-child {{ border-right: none; }}
        .party-header {{ background: #1a5f7a; color: white; padding: 5px 8px; margin: -10px -10px 10px -10px; font-size: 10px; font-weight: bold; }}
        .party-box p {{ margin-bottom: 3px; }}
        .party-box .company-name {{ font-weight: bold; font-size: 12px; color: #1a5f7a; }}

        /* Table */
        table {{ width: 100%; border-collapse: collapse; }}
        th {{ background: #1a5f7a; color: white; padding: 8px 5px; font-size: 10px; text-align: center; border: 1px solid #000; }}
        td {{ padding: 8px 5px; border: 1px solid #000; font-size: 10px; }}
        .text-center {{ text-align: center; }}
        .text-right {{ text-align: right; }}
        .fg-code {{ font-family: 'Courier New', monospace; font-weight: bold; color: #1a5f7a; font-size: 9px; }}

        /* Totals */
        .totals-section {{ display: flex; border-bottom: 1px solid #000; }}
        .totals-left {{ flex: 1; padding: 10px; border-right: 1px solid #000; }}
        .totals-right {{ width: 300px; }}
        .totals-row {{ display: flex; padding: 5px 10px; border-bottom: 1px solid #ddd; }}
        .totals-row:last-child {{ border-bottom: none; }}
        .totals-label {{ flex: 1; text-align: right; padding-right: 15px; }}
        .totals-value {{ width: 110px; text-align: right; font-weight: bold; }}
        .grand-total {{ background: #1a5f7a; color: white; font-size: 12px; }}
        .advance-paid {{ background: #28a745; color: white; }}
        .balance-due {{ background: #dc3545; color: white; }}

        /* Amount in Words */
        .amount-words {{ padding: 10px; background: #f9f9f9; border-bottom: 1px solid #000; font-style: italic; }}

        /* Payment Section */
        .payment-section {{ padding: 10px; border-bottom: 1px solid #000; background: #e8f5e9; }}
        .payment-section h4 {{ color: #2e7d32; margin-bottom: 8px; }}
        .payment-detail {{ display: flex; margin-bottom: 5px; }}
        .payment-detail label {{ width: 150px; font-weight: bold; }}

        /* Bank Details */
        .bank-section {{ padding: 10px; border-bottom: 1px solid #000; background: #fff3cd; }}
        .bank-section h4 {{ color: #856404; margin-bottom: 8px; }}

        /* Terms */
        .terms {{ padding: 10px; font-size: 9px; border-bottom: 1px solid #000; }}
        .terms h4 {{ margin-bottom: 5px; color: #1a5f7a; }}
        .terms ol {{ margin-left: 15px; }}
        .terms li {{ margin-bottom: 3px; }}

        /* Signature */
        .signature-section {{ display: flex; padding: 20px; }}
        .signature-box {{ flex: 1; text-align: center; }}
        .signature-line {{ border-top: 1px solid #000; margin-top: 50px; padding-top: 5px; width: 180px; margin-left: auto; margin-right: auto; }}

        /* Footer */
        .footer {{ background: #f0f0f0; padding: 8px; text-align: center; font-size: 9px; color: #666; }}

        /* Print Button */
        .print-btn {{
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
        }}
        .print-btn:hover {{
            background: linear-gradient(135deg, #0d3d4d 0%, #1a5f7a 100%);
            transform: translateY(-2px);
            box-shadow: 0 6px 8px rgba(0,0,0,0.4);
        }}
        .print-btn svg {{
            width: 18px;
            height: 18px;
        }}

        @media print {{
            body {{ padding: 0; }}
            .document {{ border: 1px solid #000; }}
            .print-btn {{ display: none !important; }}
        }}
    </style>
</head>
<body>
    <!-- Print PDF Button -->
    <button class="print-btn" onclick="window.print()">
        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z" />
        </svg>
        Print PDF
    </button>

    <div class="document">
        <!-- Header -->
        <div class="header">
            <h1>{company['legal_name']}</h1>
            <div class="contact">
                {company['address_line1']}, {company['address_line2'] or ''}, {company['city']}, {company['state']} - {company['pincode']}<br>
                GSTIN: {company['gstin']} | CIN: {company['cin']}<br>
                Phone: {company['phone']} | Email: {company['email']}
            </div>
        </div>

        <!-- Document Title -->
        <div class="doc-title">
            <h2>PURCHASE ORDER</h2>
        </div>

        <!-- PO Info -->
        <div class="info-grid">
            <div class="info-box">
                <label>PO Number</label>
                <value style="font-size: 13px; color: #1a5f7a;">{PO_NUMBER}</value>
            </div>
            <div class="info-box">
                <label>PO Date</label>
                <value>{PO_DATE.strftime('%d.%m.%Y')}</value>
            </div>
            <div class="info-box">
                <label>PI Reference</label>
                <value>{PI_REFERENCE}</value>
            </div>
            <div class="info-box">
                <label>PI Date</label>
                <value>{PI_DATE}</value>
            </div>
        </div>

        <div class="info-grid">
            <div class="info-box">
                <label>Expected Delivery</label>
                <value style="color: #dc3545;">{EXPECTED_DELIVERY}</value>
            </div>
            <div class="info-box">
                <label>Delivery Terms</label>
                <value>Ex-Works, Delhi</value>
            </div>
            <div class="info-box">
                <label>Payment Terms</label>
                <value>25% Adv, 25% Dispatch, 50% PDC</value>
            </div>
            <div class="info-box">
                <label>Tax Type</label>
                <value>CGST + SGST (Intra-State)</value>
            </div>
        </div>

        <!-- Vendor & Delivery Details -->
        <div class="party-section">
            <div class="party-box">
                <div class="party-header">SUPPLIER / VENDOR DETAILS</div>
                <p class="company-name">{vendor['legal_name']}</p>
                <p>{vendor['address_line1']}</p>
                <p>{vendor['address_line2'] or ''}</p>
                <p>{vendor['city']}, {vendor['state']} - {vendor['pincode']}</p>
                <p><strong>GSTIN:</strong> {vendor['gstin'] or 'N/A'}</p>
                <p><strong>State Code:</strong> {vendor['state_code']}</p>
                <p><strong>Contact:</strong> {vendor['contact_name']}</p>
                <p><strong>Phone:</strong> {vendor['contact_phone'] or 'N/A'}</p>
                <p><strong>Vendor Code:</strong> {vendor['vendor_code']}</p>
            </div>
            <div class="party-box">
                <div class="party-header">SHIP TO / DELIVERY ADDRESS</div>
                <p class="company-name">{company['legal_name']}</p>
                <p>{company['address_line1']}</p>
                <p>{company['address_line2'] or ''}</p>
                <p>{company['city']}, {company['state']} - {company['pincode']}</p>
                <p><strong>GSTIN:</strong> {company['gstin']}</p>
                <p><strong>State Code:</strong> {company['state_code']}</p>
                <p><strong>Contact:</strong> Store Manager</p>
                <p><strong>Phone:</strong> {company['phone']}</p>
            </div>
        </div>

        <!-- Order Items Table -->
        <table>
            <thead>
                <tr>
                    <th style="width:5%">S.N.</th>
                    <th style="width:25%">Product Description</th>
                    <th style="width:12%">FG Code</th>
                    <th style="width:10%">HSN Code</th>
                    <th style="width:8%">Qty</th>
                    <th style="width:6%">Unit</th>
                    <th style="width:14%">Rate</th>
                    <th style="width:14%">Amount</th>
                </tr>
            </thead>
            <tbody>
                {items_html}
                <tr style="background: #f5f5f5; font-weight: bold;">
                    <td colspan="4" class="text-right">TOTAL</td>
                    <td class="text-center">{total_qty}</td>
                    <td class="text-center">Nos</td>
                    <td></td>
                    <td class="text-right">Rs. {subtotal:,.2f}</td>
                </tr>
            </tbody>
        </table>

        <!-- Totals Section -->
        <div class="totals-section">
            <div class="totals-left">
                <strong>HSN Summary (Intra-State: CGST + SGST):</strong>
                <table style="margin-top: 5px; font-size: 9px;">
                    <tr style="background: #e0e0e0;">
                        <th>HSN Code</th>
                        <th>Taxable Value</th>
                        <th>CGST @{CGST_RATE}%</th>
                        <th>SGST @{SGST_RATE}%</th>
                        <th>Total Tax</th>
                    </tr>
                    <tr>
                        <td class="text-center">84212110</td>
                        <td class="text-right">Rs. {subtotal:,.2f}</td>
                        <td class="text-right">Rs. {cgst_amount:,.2f}</td>
                        <td class="text-right">Rs. {sgst_amount:,.2f}</td>
                        <td class="text-right">Rs. {total_tax:,.2f}</td>
                    </tr>
                </table>
                <p style="margin-top: 10px; font-size: 9px; color: #666;">
                    <strong>Note:</strong> Intra-state supply (Delhi to Delhi) - CGST + SGST applicable
                </p>
            </div>
            <div class="totals-right">
                <div class="totals-row">
                    <span class="totals-label">Sub Total:</span>
                    <span class="totals-value">Rs. {subtotal:,.2f}</span>
                </div>
                <div class="totals-row">
                    <span class="totals-label">CGST @ {CGST_RATE}%:</span>
                    <span class="totals-value">Rs. {cgst_amount:,.2f}</span>
                </div>
                <div class="totals-row">
                    <span class="totals-label">SGST @ {SGST_RATE}%:</span>
                    <span class="totals-value">Rs. {sgst_amount:,.2f}</span>
                </div>
                <div class="totals-row grand-total">
                    <span class="totals-label">GRAND TOTAL:</span>
                    <span class="totals-value">Rs. {grand_total:,.2f}</span>
                </div>
                <div class="totals-row advance-paid">
                    <span class="totals-label">Advance Paid ({ADVANCE_PERCENTAGE}%):</span>
                    <span class="totals-value">Rs. {ADVANCE_PAID:,.2f}</span>
                </div>
                <div class="totals-row balance-due">
                    <span class="totals-label">Balance Due:</span>
                    <span class="totals-value">Rs. {balance_due:,.2f}</span>
                </div>
            </div>
        </div>

        <!-- Amount in Words -->
        <div class="amount-words">
            <strong>Grand Total in Words:</strong> {number_to_words(float(grand_total))}<br>
            <strong>Advance Paid in Words:</strong> {number_to_words(float(ADVANCE_PAID))}
        </div>

        <!-- Payment Details -->
        <div class="payment-section">
            <h4>ADVANCE PAYMENT DETAILS</h4>
            <div class="payment-detail">
                <label>Payment Date:</label>
                <span>{ADVANCE_DATE}</span>
            </div>
            <div class="payment-detail">
                <label>Transaction Reference:</label>
                <span>{ADVANCE_REF}</span>
            </div>
            <div class="payment-detail">
                <label>Amount Transferred:</label>
                <span><strong>Rs. {ADVANCE_PAID:,.2f}</strong> ({ADVANCE_PERCENTAGE}% of Grand Total)</span>
            </div>
            <div class="payment-detail">
                <label>Balance Payment:</label>
                <span><strong>Rs. {balance_due:,.2f}</strong> (25% at dispatch + 50% PDC)</span>
            </div>
        </div>

        <!-- Bank Details -->
        <div class="bank-section">
            <h4>SUPPLIER BANK DETAILS (For Future Payments)</h4>
            <div class="payment-detail">
                <label>Bank Name:</label>
                <span>{vendor['bank_name']}</span>
            </div>
            <div class="payment-detail">
                <label>Branch:</label>
                <span>{vendor['bank_branch']}</span>
            </div>
            <div class="payment-detail">
                <label>Account Number:</label>
                <span><strong>{vendor['bank_account_number']}</strong></span>
            </div>
            <div class="payment-detail">
                <label>IFSC Code:</label>
                <span>{vendor['bank_ifsc']}</span>
            </div>
            <div class="payment-detail">
                <label>Account Name:</label>
                <span>{vendor['bank_account_name']}</span>
            </div>
        </div>

        <!-- Terms & Conditions -->
        <div class="terms">
            <h4>TERMS & CONDITIONS:</h4>
            <ol>
                <li><strong>Payment Terms:</strong>
                    <ul style="margin-left: 15px;">
                        <li>25% Advance against Proforma Invoice - <strong>PAID</strong></li>
                        <li>25% at the time of dispatch</li>
                        <li>Balance 50% against Post Dated Cheque</li>
                    </ul>
                </li>
                <li><strong>Delivery:</strong> Within 30 days from receipt of advance payment and packing material design from buyer.</li>
                <li><strong>Warranty:</strong>
                    <ul style="margin-left: 15px;">
                        <li>18 months on electronic parts from date of invoice</li>
                        <li>1 year general service warranty</li>
                    </ul>
                </li>
                <li><strong>Packing Material:</strong> UV LED to be provided by buyer.</li>
                <li><strong>Quality:</strong> All products must meet Aquapurite quality standards and pass inspection before acceptance.</li>
                <li><strong>Serialization:</strong> Each unit must have individual barcode label as per Aquapurite serialization format.</li>
                <li><strong>Documentation:</strong> Packing list with barcode details (CSV/Excel) must accompany each shipment.</li>
                <li>This PO is subject to the terms agreed in the Proforma Invoice {PI_REFERENCE}.</li>
                <li>All disputes subject to Delhi jurisdiction.</li>
            </ol>
        </div>

        <!-- Signature Section -->
        <div class="signature-section">
            <div class="signature-box">
                <p><strong>Prepared By:</strong></p>
                <div class="signature-line">Purchase Department</div>
            </div>
            <div class="signature-box">
                <p><strong>Verified By:</strong></p>
                <div class="signature-line">Accounts Department</div>
            </div>
            <div class="signature-box">
                <p><strong>Approved By:</strong></p>
                <div class="signature-line">For {company['display_name']}<br>(Authorized Signatory)</div>
            </div>
        </div>

        <!-- Footer -->
        <div class="footer">
            This is a system generated Purchase Order from Aquapurite ERP | Document ID: {PO_NUMBER} | Generated on: {datetime.now().strftime("%d-%m-%Y %H:%M:%S")}
        </div>
    </div>
</body>
</html>"""

    return html


async def main():
    """Main function to generate PO from master data"""
    print("=" * 80)
    print("GENERATING PURCHASE ORDER FROM MASTER DATA")
    print("=" * 80)

    async with async_session_factory() as db:
        # Fetch company (Aquapurite) details using explicit column names
        print("\n1. Fetching Aquapurite company details from master...")
        result = await db.execute(text("""
            SELECT legal_name, trade_name, gstin, state_code, cin,
                   address_line1, address_line2, city, state, pincode,
                   email, phone
            FROM companies LIMIT 1
        """))
        row = result.fetchone()

        if not row:
            print("ERROR: Company not found in database!")
            return

        company = {
            "legal_name": row[0],
            "display_name": row[1] or row[0],
            "gstin": row[2],
            "state_code": row[3],
            "cin": row[4],
            "address_line1": row[5],
            "address_line2": row[6],
            "city": row[7],
            "state": row[8],
            "pincode": row[9],
            "email": row[10],
            "phone": row[11],
        }

        print(f"   Company: {company['legal_name']}")
        print(f"   GSTIN: {company['gstin']}")
        print(f"   State Code: {company['state_code']} (Delhi)")
        print(f"   Address: {company['address_line1']}, {company['city']}")

        # Fetch FastTrack vendor details using explicit column names
        print("\n2. Fetching FastTrack vendor details from master...")
        result = await db.execute(text("""
            SELECT vendor_code, name, legal_name, trade_name, gstin, gst_state_code,
                   contact_person, designation, email, phone,
                   address_line1, address_line2, city, state, pincode,
                   bank_name, bank_branch, bank_account_number, bank_ifsc, beneficiary_name
            FROM vendors WHERE vendor_code = 'VND-00001'
        """))
        row = result.fetchone()

        if not row:
            print("ERROR: FastTrack vendor (VND-00001) not found!")
            return

        vendor = {
            "vendor_code": row[0],
            "name": row[1],
            "legal_name": row[2],
            "display_name": row[3] or row[1],  # trade_name or name
            "gstin": row[4],
            "state_code": row[5],  # gst_state_code
            "contact_name": row[6],  # contact_person
            "contact_designation": row[7],  # designation
            "contact_email": row[8],
            "contact_phone": row[9],
            "address_line1": row[10],
            "address_line2": row[11],
            "city": row[12],
            "state": row[13],
            "pincode": row[14],
            "bank_name": row[15],
            "bank_branch": row[16],
            "bank_account_number": row[17],
            "bank_ifsc": row[18],
            "bank_account_name": row[19],  # beneficiary_name
        }

        print(f"   Vendor: {vendor['legal_name']}")
        print(f"   Vendor Code: {vendor['vendor_code']}")
        print(f"   GSTIN: {vendor['gstin'] or 'Not registered'}")
        print(f"   State Code: {vendor['state_code']} (Delhi)")
        print(f"   Contact: {vendor['contact_name']}")
        print(f"   Bank: {vendor['bank_name']} - A/c: {vendor['bank_account_number']}")

        # Verify intra-state transaction
        print("\n3. Tax Calculation:")
        if company['state_code'] == vendor['state_code']:
            print(f"   ✓ Intra-state transaction (Both in State Code: {company['state_code']})")
            print(f"   ✓ Tax: CGST {CGST_RATE}% + SGST {SGST_RATE}%")
        else:
            print(f"   Inter-state transaction (Company: {company['state_code']}, Vendor: {vendor['state_code']})")
            print(f"   Tax: IGST 18%")

        # Calculate totals
        subtotal = sum(Decimal(str(item["quantity"])) * item["unit_price"] for item in ORDER_ITEMS)
        cgst = subtotal * CGST_RATE / 100
        sgst = subtotal * SGST_RATE / 100
        grand_total = subtotal + cgst + sgst

        print("\n4. Order Summary:")
        print("-" * 70)
        print(f"{'S.No':<5} {'Product':<30} {'Qty':>8} {'Rate':>12} {'Amount':>15}")
        print("-" * 70)
        for item in ORDER_ITEMS:
            amount = item["quantity"] * item["unit_price"]
            print(f"{item['sr_no']:<5} {item['name']:<30} {item['quantity']:>8} Rs.{item['unit_price']:>10,.2f} Rs.{amount:>12,.2f}")
        print("-" * 70)
        print(f"{'Sub Total':<45} Rs.{subtotal:>22,.2f}")
        print(f"{'CGST @ 9%':<45} Rs.{cgst:>22,.2f}")
        print(f"{'SGST @ 9%':<45} Rs.{sgst:>22,.2f}")
        print(f"{'GRAND TOTAL':<45} Rs.{grand_total:>22,.2f}")
        print("-" * 70)
        print(f"{'Advance Paid (25%)':<45} Rs.{ADVANCE_PAID:>22,.2f}")
        print(f"{'Balance Due':<45} Rs.{grand_total - ADVANCE_PAID:>22,.2f}")
        print("=" * 70)

        # Generate HTML
        print("\n5. Generating Purchase Order HTML...")
        html_content = generate_po_html(company, vendor)

        # Save to /tmp (more reliable)
        output_path = f"/tmp/PurchaseOrder-{PO_NUMBER.replace('/', '-')}.html"
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        print(f"\n{'=' * 80}")
        print("PURCHASE ORDER GENERATED SUCCESSFULLY")
        print("=" * 80)
        print(f"\nPO Number: {PO_NUMBER}")
        print(f"Buyer: {company['legal_name']}")
        print(f"Supplier: {vendor['legal_name']}")
        print(f"Total Value: Rs. {grand_total:,.2f}")
        print(f"\nFile: {output_path}")

        return output_path


if __name__ == "__main__":
    output = asyncio.run(main())
    if output:
        # Open in browser
        os.system(f'open -a Safari "{output}"')
