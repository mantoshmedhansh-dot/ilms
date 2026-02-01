#!/usr/bin/env python3
"""
Generate Purchase Order PO/APL/ST/25-26/002 from Aquapurite to STOS
Spare Parts Order for Jan-March 2026

Vendor: STOS Industrial Corporation (VND-00002)
Inter-state: Delhi (07) to Uttar Pradesh (09) = IGST 18%
Payment: 25% Advance with PO, 75% after 45 days
"""

import asyncio
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import text
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import async_session_factory

# PO Details
PO_NUMBER = "PO/APL/ST/25-26/002"
PO_DATE = date(2026, 1, 10)
DELIVERY_SCHEDULE = "15th Jan 2026 - 15th March 2026"
VALIDITY = "30 Days"

# Order Items (Spare Parts for 2 months)
ORDER_ITEMS = [
    {"sr_no": 1, "sku": "SP-SDF-001", "name": "Sediment Filter (PP Yarn Wound)", "hsn": "84212190", "qty": 3000, "rate": Decimal("97.00")},
    {"sr_no": 2, "sku": "SP-SDF-002", "name": "Sediment Filter (Spun Filter)", "hsn": "84212190", "qty": 3000, "rate": Decimal("76.00")},
    {"sr_no": 3, "sku": "SP-PCB-001", "name": "Pre Carbon Block (Premium)", "hsn": "84212190", "qty": 3000, "rate": Decimal("114.00")},
    {"sr_no": 4, "sku": "SP-PCB-002", "name": "Pre Carbon Block (Regular)", "hsn": "84212190", "qty": 3000, "rate": Decimal("111.00")},
    {"sr_no": 5, "sku": "SP-ALK-001", "name": "Alkaline Mineral Block (Premium)", "hsn": "84212190", "qty": 2000, "rate": Decimal("61.00")},
    {"sr_no": 6, "sku": "SP-POC-001", "name": "Post Carbon with Copper (Regular)", "hsn": "84212190", "qty": 2000, "rate": Decimal("58.00")},
    {"sr_no": 7, "sku": "SP-MBF-001", "name": "Membrane (Premium)", "hsn": "84212190", "qty": 2000, "rate": Decimal("398.00")},
    {"sr_no": 8, "sku": "SP-MBF-002", "name": "Membrane (Regular)", "hsn": "84212190", "qty": 2000, "rate": Decimal("375.00")},
    {"sr_no": 9, "sku": "SP-PFC-001", "name": "Pre-Filter Multi Layer Candle", "hsn": "84212190", "qty": 2000, "rate": Decimal("245.00")},
    {"sr_no": 10, "sku": "SP-HMR-001", "name": "HMR Cartridge", "hsn": "84212190", "qty": 700, "rate": Decimal("801.00")},
    {"sr_no": 11, "sku": "SP-PFC-002", "name": "Prefilter with Multilayer Candle", "hsn": "84212190", "qty": 1500, "rate": Decimal("280.00")},
    {"sr_no": 12, "sku": "SP-PFS-001", "name": "Prefilter with Spun Filter", "hsn": "84212190", "qty": 1500, "rate": Decimal("225.00")},
    {"sr_no": 13, "sku": "SP-HMR-002", "name": "Heavy Metal Remover", "hsn": "84212190", "qty": 400, "rate": Decimal("850.00")},
    {"sr_no": 14, "sku": "SP-PRV-001", "name": "Plastic PRV", "hsn": "84212190", "qty": 700, "rate": Decimal("180.00")},
    {"sr_no": 15, "sku": "SP-BDV-001", "name": "Brass Diverter Valve", "hsn": "84212190", "qty": 1000, "rate": Decimal("150.00")},
]

# Payment Terms (Modified as per discussion)
ADVANCE_PERCENTAGE = Decimal("25")
BALANCE_DAYS = 45

# GST Rate (Inter-state: IGST)
IGST_RATE = Decimal("18")


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
    """Generate Purchase Order HTML"""

    # Calculate totals
    items_html = ""
    subtotal = Decimal("0")
    total_qty = 0

    for item in ORDER_ITEMS:
        amount = item["qty"] * item["rate"]
        subtotal += amount
        total_qty += item["qty"]
        items_html += f"""
                <tr>
                    <td class="text-center">{item['sr_no']}</td>
                    <td><span class="sp-code">{item['sku']}</span></td>
                    <td>{item['name']}</td>
                    <td class="text-center">{item['hsn']}</td>
                    <td class="text-center">{item['qty']:,}</td>
                    <td class="text-center">Nos</td>
                    <td class="text-right">Rs. {item['rate']:,.2f}</td>
                    <td class="text-right">Rs. {amount:,.2f}</td>
                </tr>"""

    # Tax calculation (Inter-state: IGST)
    igst_amount = subtotal * IGST_RATE / 100
    grand_total = subtotal + igst_amount

    # Payment calculation
    advance_amount = grand_total * ADVANCE_PERCENTAGE / 100
    balance_amount = grand_total - advance_amount

    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Purchase Order - {PO_NUMBER}</title>
    <style>
        @page {{ size: A4; margin: 10mm; }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: Arial, sans-serif; font-size: 10px; line-height: 1.4; padding: 10px; background: #fff; }}
        .document {{ max-width: 210mm; margin: 0 auto; border: 2px solid #000; }}

        .header {{ background: linear-gradient(135deg, #1a5f7a 0%, #0d3d4d 100%); color: white; padding: 12px; text-align: center; }}
        .header h1 {{ font-size: 20px; margin-bottom: 5px; }}
        .header .contact {{ font-size: 9px; }}

        .doc-title {{ background: #f0f0f0; padding: 10px; text-align: center; border-bottom: 2px solid #000; }}
        .doc-title h2 {{ font-size: 16px; color: #1a5f7a; }}

        .info-grid {{ display: flex; flex-wrap: wrap; border-bottom: 1px solid #000; }}
        .info-box {{ flex: 1; min-width: 25%; padding: 6px 8px; border-right: 1px solid #000; }}
        .info-box:last-child {{ border-right: none; }}
        .info-box label {{ display: block; font-size: 8px; color: #666; text-transform: uppercase; }}
        .info-box value {{ display: block; font-weight: bold; font-size: 10px; }}

        .party-section {{ display: flex; border-bottom: 1px solid #000; }}
        .party-box {{ flex: 1; padding: 8px; border-right: 1px solid #000; font-size: 9px; }}
        .party-box:last-child {{ border-right: none; }}
        .party-header {{ background: #1a5f7a; color: white; padding: 4px 6px; margin: -8px -8px 8px -8px; font-size: 9px; font-weight: bold; }}
        .party-box p {{ margin-bottom: 2px; }}
        .party-box .company-name {{ font-weight: bold; font-size: 10px; color: #1a5f7a; }}

        table {{ width: 100%; border-collapse: collapse; }}
        th {{ background: #1a5f7a; color: white; padding: 6px 4px; font-size: 9px; text-align: center; border: 1px solid #000; }}
        td {{ padding: 5px 4px; border: 1px solid #000; font-size: 9px; }}
        .text-center {{ text-align: center; }}
        .text-right {{ text-align: right; }}
        .sp-code {{ font-family: monospace; font-weight: bold; color: #1a5f7a; font-size: 8px; }}

        .totals-section {{ display: flex; border-bottom: 1px solid #000; }}
        .totals-left {{ flex: 1; padding: 8px; border-right: 1px solid #000; font-size: 9px; }}
        .totals-right {{ width: 280px; }}
        .totals-row {{ display: flex; padding: 4px 8px; border-bottom: 1px solid #ddd; }}
        .totals-row:last-child {{ border-bottom: none; }}
        .totals-label {{ flex: 1; text-align: right; padding-right: 10px; }}
        .totals-value {{ width: 100px; text-align: right; font-weight: bold; }}
        .grand-total {{ background: #1a5f7a; color: white; font-size: 11px; }}
        .advance {{ background: #28a745; color: white; }}
        .balance {{ background: #ffc107; color: #000; }}

        .amount-words {{ padding: 8px; background: #f9f9f9; border-bottom: 1px solid #000; font-style: italic; font-size: 9px; }}

        .bank-section {{ padding: 8px; border-bottom: 1px solid #000; background: #fff3cd; font-size: 9px; }}
        .bank-section h4 {{ color: #856404; margin-bottom: 5px; font-size: 10px; }}

        .terms {{ padding: 8px; font-size: 8px; border-bottom: 1px solid #000; }}
        .terms h4 {{ margin-bottom: 4px; color: #1a5f7a; font-size: 10px; }}
        .terms ol {{ margin-left: 15px; }}
        .terms li {{ margin-bottom: 2px; }}

        .signature-section {{ display: flex; padding: 15px; }}
        .signature-box {{ flex: 1; text-align: center; }}
        .signature-line {{ border-top: 1px solid #000; margin-top: 40px; padding-top: 5px; width: 150px; margin-left: auto; margin-right: auto; font-size: 9px; }}

        .footer {{ background: #f0f0f0; padding: 6px; text-align: center; font-size: 8px; color: #666; }}

        .print-btn {{
            position: fixed; top: 20px; right: 20px;
            background: linear-gradient(135deg, #1a5f7a 0%, #0d3d4d 100%);
            color: white; border: none; padding: 12px 24px; font-size: 14px;
            font-weight: bold; border-radius: 5px; cursor: pointer;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3); z-index: 1000;
            display: flex; align-items: center; gap: 8px;
        }}
        .print-btn:hover {{ background: linear-gradient(135deg, #0d3d4d 0%, #1a5f7a 100%); }}
        .print-btn svg {{ width: 18px; height: 18px; }}
        @media print {{ .print-btn {{ display: none !important; }} body {{ padding: 0; }} }}
    </style>
</head>
<body>
    <button class="print-btn" onclick="window.print()">
        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h6a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z" />
        </svg>
        Print PDF
    </button>

    <div class="document">
        <div class="header">
            <h1>{company['legal_name']}</h1>
            <div class="contact">
                {company['address_line1']}, {company['address_line2'] or ''}, {company['city']}, {company['state']} - {company['pincode']}<br>
                GSTIN: {company['gstin']} | CIN: {company['cin']} | Phone: {company['phone']} | Email: {company['email']}
            </div>
        </div>

        <div class="doc-title">
            <h2>PURCHASE ORDER - SPARE PARTS</h2>
        </div>

        <div class="info-grid">
            <div class="info-box">
                <label>PO Number</label>
                <value style="color: #1a5f7a;">{PO_NUMBER}</value>
            </div>
            <div class="info-box">
                <label>PO Date</label>
                <value>{PO_DATE.strftime('%d.%m.%Y')}</value>
            </div>
            <div class="info-box">
                <label>Delivery Schedule</label>
                <value style="color: #dc3545;">{DELIVERY_SCHEDULE}</value>
            </div>
            <div class="info-box">
                <label>Validity</label>
                <value>{VALIDITY}</value>
            </div>
        </div>

        <div class="info-grid">
            <div class="info-box">
                <label>Delivery Terms</label>
                <value>Ex-Works + Freight</value>
            </div>
            <div class="info-box">
                <label>Payment Terms</label>
                <value>25% Adv, 75% in 45 Days</value>
            </div>
            <div class="info-box">
                <label>Tax Type</label>
                <value>IGST 18% (Inter-State)</value>
            </div>
            <div class="info-box">
                <label>Category</label>
                <value>Spare Parts</value>
            </div>
        </div>

        <div class="party-section">
            <div class="party-box">
                <div class="party-header">SUPPLIER / VENDOR DETAILS</div>
                <p class="company-name">{vendor['legal_name']}</p>
                <p>{vendor['address_line1']}</p>
                <p>{vendor['city']}, {vendor['state']} - {vendor['pincode']}</p>
                <p><strong>GSTIN:</strong> {vendor['gstin']}</p>
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
            </div>
        </div>

        <table>
            <thead>
                <tr>
                    <th style="width:4%">S.N.</th>
                    <th style="width:10%">SKU</th>
                    <th style="width:28%">Description</th>
                    <th style="width:10%">HSN</th>
                    <th style="width:10%">Qty</th>
                    <th style="width:6%">Unit</th>
                    <th style="width:14%">Rate</th>
                    <th style="width:14%">Amount</th>
                </tr>
            </thead>
            <tbody>
                {items_html}
                <tr style="background: #f5f5f5; font-weight: bold;">
                    <td colspan="4" class="text-right">TOTAL</td>
                    <td class="text-center">{total_qty:,}</td>
                    <td class="text-center">Nos</td>
                    <td></td>
                    <td class="text-right">Rs. {subtotal:,.2f}</td>
                </tr>
            </tbody>
        </table>

        <div class="totals-section">
            <div class="totals-left">
                <strong>HSN Summary (Inter-State: IGST):</strong>
                <table style="margin-top: 5px; font-size: 8px;">
                    <tr style="background: #e0e0e0;">
                        <th>HSN Code</th>
                        <th>Taxable Value</th>
                        <th>IGST @{IGST_RATE}%</th>
                        <th>Total</th>
                    </tr>
                    <tr>
                        <td class="text-center">84212190</td>
                        <td class="text-right">Rs. {subtotal:,.2f}</td>
                        <td class="text-right">Rs. {igst_amount:,.2f}</td>
                        <td class="text-right">Rs. {grand_total:,.2f}</td>
                    </tr>
                </table>
                <p style="margin-top: 8px; font-size: 8px; color: #666;">
                    <strong>Note:</strong> Inter-state supply (Delhi to Uttar Pradesh) - IGST applicable
                </p>
            </div>
            <div class="totals-right">
                <div class="totals-row">
                    <span class="totals-label">Sub Total:</span>
                    <span class="totals-value">Rs. {subtotal:,.2f}</span>
                </div>
                <div class="totals-row">
                    <span class="totals-label">IGST @ {IGST_RATE}%:</span>
                    <span class="totals-value">Rs. {igst_amount:,.2f}</span>
                </div>
                <div class="totals-row grand-total">
                    <span class="totals-label">GRAND TOTAL:</span>
                    <span class="totals-value">Rs. {grand_total:,.2f}</span>
                </div>
                <div class="totals-row advance">
                    <span class="totals-label">Advance ({ADVANCE_PERCENTAGE}%):</span>
                    <span class="totals-value">Rs. {advance_amount:,.2f}</span>
                </div>
                <div class="totals-row balance">
                    <span class="totals-label">Balance (in {BALANCE_DAYS} days):</span>
                    <span class="totals-value">Rs. {balance_amount:,.2f}</span>
                </div>
            </div>
        </div>

        <div class="amount-words">
            <strong>Grand Total in Words:</strong> {number_to_words(float(grand_total))}
        </div>

        <div class="bank-section">
            <h4>SUPPLIER BANK DETAILS (For Payment)</h4>
            <p><strong>Bank Name:</strong> {vendor['bank_name']} | <strong>Branch:</strong> {vendor['bank_branch'] or 'Ghaziabad'}</p>
            <p><strong>Account Number:</strong> {vendor['bank_account_number']} | <strong>IFSC:</strong> {vendor['bank_ifsc']}</p>
            <p><strong>Account Name:</strong> {vendor['bank_account_name']}</p>
        </div>

        <div class="terms">
            <h4>TERMS & CONDITIONS:</h4>
            <ol>
                <li><strong>Payment Terms:</strong>
                    <ul style="margin-left: 15px;">
                        <li>25% Advance with Purchase Order</li>
                        <li>Balance 75% within 45 days from delivery</li>
                    </ul>
                </li>
                <li><strong>Delivery Schedule:</strong> As per monthly schedule (15th Jan - 25th Jan & 15th Feb 2026)</li>
                <li><strong>Pricing:</strong> Ex-Works + Freight charged as actual</li>
                <li><strong>Quality:</strong> All items must meet Aquapurite quality standards</li>
                <li><strong>Packaging:</strong> Standard packaging; pouches and packaging materials as agreed - no design change until 90% pouches utilized</li>
                <li><strong>Documentation:</strong> Delivery challan with item-wise barcode details required</li>
                <li><strong>Lead Time:</strong> 14 days from order confirmation (as per quotation)</li>
                <li><strong>Warranty:</strong> As per original quotation terms</li>
                <li>All disputes subject to Ghaziabad/Delhi jurisdiction.</li>
            </ol>
        </div>

        <div class="signature-section">
            <div class="signature-box">
                <div class="signature-line">Prepared By<br>Purchase Dept.</div>
            </div>
            <div class="signature-box">
                <div class="signature-line">Verified By<br>Accounts Dept.</div>
            </div>
            <div class="signature-box">
                <div class="signature-line">For {company['display_name']}<br>(Authorized Signatory)</div>
            </div>
        </div>

        <div class="footer">
            Purchase Order from Aquapurite ERP | Document: {PO_NUMBER} | Generated: {datetime.now().strftime("%d-%m-%Y %H:%M:%S")}
        </div>
    </div>
</body>
</html>"""

    return html


async def main():
    """Main function to generate PO from master data"""
    print("=" * 80)
    print("GENERATING PURCHASE ORDER - SPARE PARTS (STOS)")
    print("=" * 80)

    async with async_session_factory() as db:
        # Fetch company details
        print("\n1. Fetching Aquapurite company details...")
        result = await db.execute(text("""
            SELECT legal_name, trade_name, gstin, state_code, cin,
                   address_line1, address_line2, city, state, pincode,
                   email, phone
            FROM companies LIMIT 1
        """))
        row = result.fetchone()

        if not row:
            print("ERROR: Company not found!")
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
        print(f"   State Code: {company['state_code']} (Delhi)")

        # Fetch STOS vendor details
        print("\n2. Fetching STOS vendor details...")
        result = await db.execute(text("""
            SELECT vendor_code, name, legal_name, trade_name, gstin, gst_state_code,
                   contact_person, designation, email, phone,
                   address_line1, address_line2, city, state, pincode,
                   bank_name, bank_branch, bank_account_number, bank_ifsc, beneficiary_name
            FROM vendors WHERE vendor_code = 'VND-00002'
        """))
        row = result.fetchone()

        if not row:
            print("ERROR: STOS vendor (VND-00002) not found!")
            return

        vendor = {
            "vendor_code": row[0],
            "name": row[1],
            "legal_name": row[2],
            "display_name": row[3] or row[1],
            "gstin": row[4],
            "state_code": row[5],
            "contact_name": row[6],
            "contact_designation": row[7],
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
            "bank_account_name": row[19],
        }

        print(f"   Vendor: {vendor['legal_name']}")
        print(f"   Vendor Code: {vendor['vendor_code']}")
        print(f"   GSTIN: {vendor['gstin']}")
        print(f"   State Code: {vendor['state_code']} (Uttar Pradesh)")

        # Tax calculation
        print("\n3. Tax Calculation:")
        print(f"   Inter-state transaction (Delhi 07 → UP 09)")
        print(f"   Tax: IGST {IGST_RATE}%")

        # Calculate totals
        subtotal = sum(Decimal(str(item["qty"])) * item["rate"] for item in ORDER_ITEMS)
        igst = subtotal * IGST_RATE / 100
        grand_total = subtotal + igst
        advance = grand_total * ADVANCE_PERCENTAGE / 100
        balance = grand_total - advance

        print("\n4. Order Summary:")
        print("-" * 80)
        print(f"{'S.No':<5} {'SKU':<12} {'Description':<35} {'Qty':>8} {'Rate':>10} {'Amount':>12}")
        print("-" * 80)
        for item in ORDER_ITEMS:
            amount = item["qty"] * item["rate"]
            print(f"{item['sr_no']:<5} {item['sku']:<12} {item['name'][:35]:<35} {item['qty']:>8,} Rs.{item['rate']:>8,.0f} Rs.{amount:>10,.0f}")
        print("-" * 80)
        print(f"{'Sub Total':<58} Rs.{subtotal:>18,.2f}")
        print(f"{'IGST @ 18%':<58} Rs.{igst:>18,.2f}")
        print(f"{'GRAND TOTAL':<58} Rs.{grand_total:>18,.2f}")
        print("-" * 80)
        print(f"{'Advance (25%)':<58} Rs.{advance:>18,.2f}")
        print(f"{'Balance (45 days)':<58} Rs.{balance:>18,.2f}")
        print("=" * 80)

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
        print(f"Advance (25%): Rs. {advance:,.2f}")
        print(f"Balance (45 days): Rs. {balance:,.2f}")
        print(f"\nFile: {output_path}")

        # Also create PO record in database
        print("\n6. Recording PO in database...")
        try:
            po_id = os.urandom(16).hex()
            await db.execute(text("""
                INSERT INTO purchase_orders (id, po_number, vendor_id, status, subtotal, tax_amount, total_amount, notes, created_at, updated_at)
                SELECT :id, :po_number, id, 'DRAFT', :subtotal, :tax, :total, :notes, datetime('now'), datetime('now')
                FROM vendors WHERE vendor_code = 'VND-00002'
            """), {
                "id": po_id,
                "po_number": PO_NUMBER,
                "subtotal": float(subtotal),
                "tax": float(igst),
                "total": float(grand_total),
                "notes": f"Spare Parts Order for Jan-March 2026. Delivery: {DELIVERY_SCHEDULE}. Payment: 25% Advance, 75% in 45 days."
            })
            await db.commit()
            print(f"   PO recorded in database with status: DRAFT")
        except Exception as e:
            print(f"   Note: Could not record in DB (may already exist): {str(e)[:50]}")

        return output_path


if __name__ == "__main__":
    output = asyncio.run(main())
    if output:
        os.system(f'open -a Safari "{output}"')
