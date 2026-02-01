#!/usr/bin/env python3
"""
Generate Purchase Order PO/APL/ST/25-26/002 from Aquapurite to STOS
Spare Parts Order with MONTH-WISE breakdown for Jan-March 2026

This script follows the proper architecture:
1. Uses monthly_quantities field for each item
2. Generates proper month-wise PDF/HTML
3. Uses master data from database

Vendor: STOS Industrial Corporation (VND-00002)
Inter-state: Delhi (07) to Uttar Pradesh (09) = IGST 18%
Payment: 25% Advance with PO, 75% after 45 days
Delivery: 15th Jan 2026 - 15th March 2026 (3 months)
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
DELIVERY_MONTHS = ["2026-01", "2026-02", "2026-03"]  # Jan, Feb, Mar 2026
MONTH_LABELS = {
    "2026-01": "JAN '26",
    "2026-02": "FEB '26",
    "2026-03": "MAR '26"
}
VALIDITY = "30 Days"

# Order Items with MONTH-WISE breakdown (total qty split across 3 months)
# Each item has: total_qty, rate, and distribution across months
ORDER_ITEMS = [
    {
        "sr_no": 1, "sku": "SP-SDF-001", "name": "Sediment Filter (PP Yarn Wound)",
        "hsn": "84212190", "rate": Decimal("97.00"),
        "monthly": {"2026-01": 1000, "2026-02": 1000, "2026-03": 1000}  # Total: 3000
    },
    {
        "sr_no": 2, "sku": "SP-SDF-002", "name": "Sediment Filter (Spun Filter)",
        "hsn": "84212190", "rate": Decimal("76.00"),
        "monthly": {"2026-01": 1000, "2026-02": 1000, "2026-03": 1000}  # Total: 3000
    },
    {
        "sr_no": 3, "sku": "SP-PCB-001", "name": "Pre Carbon Block (Premium)",
        "hsn": "84212190", "rate": Decimal("114.00"),
        "monthly": {"2026-01": 1000, "2026-02": 1000, "2026-03": 1000}  # Total: 3000
    },
    {
        "sr_no": 4, "sku": "SP-PCB-002", "name": "Pre Carbon Block (Regular)",
        "hsn": "84212190", "rate": Decimal("111.00"),
        "monthly": {"2026-01": 1000, "2026-02": 1000, "2026-03": 1000}  # Total: 3000
    },
    {
        "sr_no": 5, "sku": "SP-ALK-001", "name": "Alkaline Mineral Block (Premium)",
        "hsn": "84212190", "rate": Decimal("61.00"),
        "monthly": {"2026-01": 700, "2026-02": 700, "2026-03": 600}  # Total: 2000
    },
    {
        "sr_no": 6, "sku": "SP-POC-001", "name": "Post Carbon with Copper (Regular)",
        "hsn": "84212190", "rate": Decimal("58.00"),
        "monthly": {"2026-01": 700, "2026-02": 700, "2026-03": 600}  # Total: 2000
    },
    {
        "sr_no": 7, "sku": "SP-MBF-001", "name": "Membrane (Premium)",
        "hsn": "84212190", "rate": Decimal("398.00"),
        "monthly": {"2026-01": 700, "2026-02": 700, "2026-03": 600}  # Total: 2000
    },
    {
        "sr_no": 8, "sku": "SP-MBF-002", "name": "Membrane (Regular)",
        "hsn": "84212190", "rate": Decimal("375.00"),
        "monthly": {"2026-01": 700, "2026-02": 700, "2026-03": 600}  # Total: 2000
    },
    {
        "sr_no": 9, "sku": "SP-PFC-001", "name": "Pre-Filter Multi Layer Candle",
        "hsn": "84212190", "rate": Decimal("245.00"),
        "monthly": {"2026-01": 700, "2026-02": 700, "2026-03": 600}  # Total: 2000
    },
    {
        "sr_no": 10, "sku": "SP-HMR-001", "name": "HMR Cartridge",
        "hsn": "84212190", "rate": Decimal("801.00"),
        "monthly": {"2026-01": 250, "2026-02": 250, "2026-03": 200}  # Total: 700
    },
    {
        "sr_no": 11, "sku": "SP-PFC-002", "name": "Prefilter with Multilayer Candle",
        "hsn": "84212190", "rate": Decimal("280.00"),
        "monthly": {"2026-01": 500, "2026-02": 500, "2026-03": 500}  # Total: 1500
    },
    {
        "sr_no": 12, "sku": "SP-PFS-001", "name": "Prefilter with Spun Filter",
        "hsn": "84212190", "rate": Decimal("225.00"),
        "monthly": {"2026-01": 500, "2026-02": 500, "2026-03": 500}  # Total: 1500
    },
    {
        "sr_no": 13, "sku": "SP-HMR-002", "name": "Heavy Metal Remover",
        "hsn": "84212190", "rate": Decimal("850.00"),
        "monthly": {"2026-01": 150, "2026-02": 150, "2026-03": 100}  # Total: 400
    },
    {
        "sr_no": 14, "sku": "SP-PRV-001", "name": "Plastic PRV",
        "hsn": "84212190", "rate": Decimal("180.00"),
        "monthly": {"2026-01": 250, "2026-02": 250, "2026-03": 200}  # Total: 700
    },
    {
        "sr_no": 15, "sku": "SP-BDV-001", "name": "Brass Diverter Valve",
        "hsn": "84212190", "rate": Decimal("150.00"),
        "monthly": {"2026-01": 350, "2026-02": 350, "2026-03": 300}  # Total: 1000
    },
]

# Payment Terms
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


def generate_po_html(company: dict, vendor: dict, ship_to: dict) -> str:
    """Generate Purchase Order HTML with MONTH-WISE columns and BILL TO / SHIP TO"""

    # Calculate totals
    items_html = ""
    subtotal = Decimal("0")
    month_totals = {m: 0 for m in DELIVERY_MONTHS}

    for item in ORDER_ITEMS:
        total_qty = sum(item["monthly"].values())
        amount = total_qty * item["rate"]
        subtotal += amount

        # Update month totals
        for m in DELIVERY_MONTHS:
            month_totals[m] += item["monthly"].get(m, 0)

        # Build month columns
        month_cols = ""
        for m in DELIVERY_MONTHS:
            qty = item["monthly"].get(m, 0)
            bg_color = "#fef3c7" if m == "2026-01" else "#dbeafe" if m == "2026-02" else "#dcfce7"
            month_cols += f'<td class="text-center" style="background: {bg_color};">{qty:,}</td>'

        items_html += f"""
                <tr>
                    <td class="text-center">{item['sr_no']}</td>
                    <td><span class="sp-code">{item['sku']}</span></td>
                    <td>{item['name']}</td>
                    <td class="text-center">{item['hsn']}</td>
                    {month_cols}
                    <td class="text-center" style="background: #f3f4f6; font-weight: bold;">{total_qty:,}</td>
                    <td class="text-center">Nos</td>
                    <td class="text-right">Rs. {item['rate']:,.2f}</td>
                    <td class="text-right">Rs. {amount:,.2f}</td>
                </tr>"""

    # Calculate grand totals
    total_qty = sum(month_totals.values())
    igst_amount = subtotal * IGST_RATE / 100
    grand_total = subtotal + igst_amount
    advance_amount = grand_total * ADVANCE_PERCENTAGE / 100
    balance_amount = grand_total - advance_amount

    # Build month headers and totals row
    month_headers = ""
    month_totals_row = ""
    for m in DELIVERY_MONTHS:
        label = MONTH_LABELS[m]
        bg_color = "#f59e0b" if m == "2026-01" else "#3b82f6" if m == "2026-02" else "#10b981"
        month_headers += f'<th style="width: 70px; text-align: center; background: {bg_color};">{label}</th>'

        bg_color2 = "#fef3c7" if m == "2026-01" else "#dbeafe" if m == "2026-02" else "#dcfce7"
        month_totals_row += f'<td class="text-center" style="background: {bg_color2}; font-weight: bold;">{month_totals[m]:,}</td>'

    # Month summary boxes
    month_boxes = ""
    for i, m in enumerate(DELIVERY_MONTHS):
        bg = ["#fef3c7", "#dbeafe", "#dcfce7"][i]
        border = ["#f59e0b", "#3b82f6", "#10b981"][i]
        delivery = ["15th-25th Jan", "15th Feb", "15th Mar"][i]
        month_boxes += f"""
            <div class="month-box" style="background: {bg}; border: 1px solid {border};">
                <strong>{MONTH_LABELS[m]}</strong><br>
                {delivery}<br>
                <span style="font-size: 16px; font-weight: bold;">{month_totals[m]:,}</span> pcs
            </div>"""

    # Calculate lot-wise values and payments
    lot_values = {}
    for item in ORDER_ITEMS:
        for m in DELIVERY_MONTHS:
            qty = item["monthly"].get(m, 0)
            if qty > 0:
                if m not in lot_values:
                    lot_values[m] = Decimal("0")
                lot_values[m] += qty * item["rate"]

    # Generate lot payment rows
    lot_payment_rows = ""
    total_advance = Decimal("0")
    total_balance = Decimal("0")
    lot_details = [
        ("LOT 1 (JAN)", "2026-01", "15th Jan 2026", "With PO", "1st Mar 2026"),
        ("LOT 2 (FEB)", "2026-02", "15th Feb 2026", "1st Feb 2026", "1st Apr 2026"),
        ("LOT 3 (MAR)", "2026-03", "15th Mar 2026", "1st Mar 2026", "30th Apr 2026"),
    ]

    for lot_name, month_code, delivery_date, adv_due, bal_due in lot_details:
        lot_value = lot_values.get(month_code, Decimal("0"))
        lot_tax = lot_value * IGST_RATE / 100
        lot_total = lot_value + lot_tax
        lot_advance = lot_total * ADVANCE_PERCENTAGE / 100
        lot_balance = lot_total - lot_advance

        total_advance += lot_advance
        total_balance += lot_balance

        bg = "#fef3c7" if "JAN" in lot_name else "#dbeafe" if "FEB" in lot_name else "#dcfce7"

        lot_payment_rows += f"""
                <tr style="background: {bg};">
                    <td style="padding: 5px; font-weight: bold;">{lot_name}</td>
                    <td style="padding: 5px; text-align: center;">{delivery_date}</td>
                    <td style="padding: 5px; text-align: right;">{month_totals[month_code]:,}</td>
                    <td style="padding: 5px; text-align: right;">Rs. {lot_total:,.2f}</td>
                    <td style="padding: 5px; text-align: right; color: #166534; font-weight: bold;">Rs. {lot_advance:,.2f}</td>
                    <td style="padding: 5px; text-align: center;">{adv_due}</td>
                    <td style="padding: 5px; text-align: right; color: #b45309; font-weight: bold;">Rs. {lot_balance:,.2f}</td>
                    <td style="padding: 5px; text-align: center;">{bal_due}</td>
                </tr>"""

    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Purchase Order - {PO_NUMBER}</title>
    <style>
        @page {{ size: A4 landscape; margin: 8mm; }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: Arial, sans-serif; font-size: 9px; line-height: 1.3; padding: 10px; background: #fff; }}
        .document {{ max-width: 290mm; margin: 0 auto; border: 2px solid #000; }}

        .header {{ background: linear-gradient(135deg, #1a5f7a 0%, #0d3d4d 100%); color: white; padding: 10px; text-align: center; }}
        .header h1 {{ font-size: 18px; margin-bottom: 3px; }}
        .header .contact {{ font-size: 8px; }}

        .doc-title {{ background: #f0f0f0; padding: 8px; text-align: center; border-bottom: 2px solid #000; }}
        .doc-title h2 {{ font-size: 14px; color: #1a5f7a; }}

        .info-grid {{ display: flex; flex-wrap: wrap; border-bottom: 1px solid #000; }}
        .info-box {{ flex: 1; min-width: 20%; padding: 5px 6px; border-right: 1px solid #000; font-size: 8px; }}
        .info-box:last-child {{ border-right: none; }}
        .info-box label {{ display: block; font-size: 7px; color: #666; text-transform: uppercase; }}
        .info-box value {{ display: block; font-weight: bold; font-size: 9px; }}

        .party-section {{ display: flex; border-bottom: 1px solid #000; }}
        .party-box {{ flex: 1; padding: 6px; border-right: 1px solid #000; font-size: 8px; }}
        .party-box:last-child {{ border-right: none; }}
        .party-header {{ background: #1a5f7a; color: white; padding: 3px 5px; margin: -6px -6px 6px -6px; font-size: 8px; font-weight: bold; }}
        .party-box .company-name {{ font-weight: bold; font-size: 9px; color: #1a5f7a; }}

        .month-summary {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 6px; margin: 6px 8px; font-size: 9px; }}
        .month-box {{ padding: 6px; border-radius: 4px; text-align: center; }}

        table {{ width: 100%; border-collapse: collapse; font-size: 8px; }}
        th {{ background: #1a5f7a; color: white; padding: 4px 3px; text-align: center; border: 1px solid #000; font-size: 8px; }}
        td {{ padding: 4px 3px; border: 1px solid #000; }}
        .text-center {{ text-align: center; }}
        .text-right {{ text-align: right; }}
        .sp-code {{ font-family: monospace; font-weight: bold; color: #1a5f7a; font-size: 7px; }}

        .totals-section {{ display: flex; border-bottom: 1px solid #000; }}
        .totals-left {{ flex: 1; padding: 6px; border-right: 1px solid #000; font-size: 8px; }}
        .totals-right {{ width: 240px; }}
        .totals-row {{ display: flex; padding: 3px 6px; border-bottom: 1px solid #ddd; }}
        .totals-label {{ flex: 1; text-align: right; padding-right: 8px; }}
        .totals-value {{ width: 90px; text-align: right; font-weight: bold; }}
        .grand-total {{ background: #1a5f7a; color: white; font-size: 10px; }}
        .advance {{ background: #28a745; color: white; }}
        .balance {{ background: #ffc107; color: #000; }}

        .amount-words {{ padding: 6px; background: #f9f9f9; border-bottom: 1px solid #000; font-style: italic; font-size: 8px; }}

        .bank-section {{ padding: 6px; border-bottom: 1px solid #000; background: #fff3cd; font-size: 8px; }}
        .bank-section h4 {{ color: #856404; margin-bottom: 3px; font-size: 9px; }}

        .terms {{ padding: 6px; font-size: 7px; border-bottom: 1px solid #000; }}
        .terms h4 {{ margin-bottom: 3px; color: #1a5f7a; font-size: 9px; }}
        .terms ol {{ margin-left: 12px; }}

        .signature-section {{ display: flex; padding: 10px; }}
        .signature-box {{ flex: 1; text-align: center; }}
        .signature-line {{ border-top: 1px solid #000; margin-top: 30px; padding-top: 3px; width: 120px; margin-left: auto; margin-right: auto; font-size: 8px; }}

        .footer {{ background: #f0f0f0; padding: 4px; text-align: center; font-size: 7px; color: #666; }}

        .print-btn {{
            position: fixed; top: 15px; right: 15px;
            background: linear-gradient(135deg, #1a5f7a 0%, #0d3d4d 100%);
            color: white; border: none; padding: 10px 20px; font-size: 13px;
            font-weight: bold; border-radius: 5px; cursor: pointer;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3); z-index: 1000;
            display: flex; align-items: center; gap: 6px;
        }}
        .print-btn:hover {{ background: linear-gradient(135deg, #0d3d4d 0%, #1a5f7a 100%); }}
        .print-btn svg {{ width: 16px; height: 16px; }}
        @media print {{ .print-btn {{ display: none !important; }} body {{ padding: 0; }} }}

        .delivery-schedule {{ padding: 6px; background: #ecfdf5; border-bottom: 1px solid #000; font-size: 8px; }}
        .delivery-schedule h4 {{ color: #065f46; margin-bottom: 3px; font-size: 9px; }}
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
                {company['address_line1']}, {company['city']}, {company['state']} - {company['pincode']} |
                GSTIN: {company['gstin']} | CIN: {company['cin']} | Email: {company['email']}
            </div>
        </div>

        <div class="doc-title">
            <h2>PURCHASE ORDER - SPARE PARTS (MONTH-WISE SCHEDULE: JAN-MAR 2026)</h2>
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
                <label>Delivery Period</label>
                <value style="color: #dc3545;">15th Jan - 15th Mar 2026</value>
            </div>
            <div class="info-box">
                <label>Payment Terms</label>
                <value>Per Lot: 25% Adv + 75% (45 days)</value>
            </div>
            <div class="info-box">
                <label>Tax Type</label>
                <value>IGST 18% (Inter-State)</value>
            </div>
        </div>

        <div class="party-section">
            <div class="party-box">
                <div class="party-header">SUPPLIER / VENDOR</div>
                <p class="company-name">{vendor['legal_name']}</p>
                <p>{vendor['address_line1']}, {vendor['city']}, {vendor['state']} - {vendor['pincode']}</p>
                <p><strong>GSTIN:</strong> {vendor['gstin']} | <strong>Code:</strong> {vendor['vendor_code']}</p>
                <p><strong>Contact:</strong> {vendor.get('contact_name', 'N/A')} | {vendor.get('contact_phone', 'N/A')}</p>
            </div>
            <div class="party-box">
                <div class="party-header">BILL TO (Buyer)</div>
                <p class="company-name">{company['legal_name']}</p>
                <p>{company['address_line1']}, {company['city']}, {company['state']} - {company['pincode']}</p>
                <p><strong>GSTIN:</strong> {company['gstin']} | <strong>State:</strong> {company['state']} ({company['state_code']})</p>
                <p><strong>Email:</strong> {company['email']}</p>
            </div>
            <div class="party-box">
                <div class="party-header">SHIP TO (Delivery)</div>
                <p class="company-name">{ship_to['name']}</p>
                <p>{ship_to['address_line1']}, {ship_to['city']}, {ship_to['state']} - {ship_to['pincode']}</p>
                <p><strong>GSTIN:</strong> {company['gstin']} | <strong>State:</strong> {ship_to['state']} ({ship_to['state_code']})</p>
            </div>
        </div>

        <div class="month-summary">
            {month_boxes}
            <div class="month-box" style="background: #f3f4f6; border: 2px solid #1a5f7a;">
                <strong>TOTAL</strong><br>
                3 Months<br>
                <span style="font-size: 16px; font-weight: bold;">{total_qty:,}</span> pcs
            </div>
        </div>

        <table>
            <thead>
                <tr>
                    <th style="width:3%">S.N.</th>
                    <th style="width:8%">SKU</th>
                    <th style="width:18%">Description</th>
                    <th style="width:7%">HSN</th>
                    {month_headers}
                    <th style="width:7%; background: #166534;">TOTAL</th>
                    <th style="width:4%">UOM</th>
                    <th style="width:8%">Rate</th>
                    <th style="width:10%">Amount</th>
                </tr>
            </thead>
            <tbody>
                {items_html}
                <tr style="font-weight: bold; background: #f3f4f6;">
                    <td colspan="4" class="text-right">TOTAL QUANTITIES</td>
                    {month_totals_row}
                    <td class="text-center" style="background: #dcfce7;">{total_qty:,}</td>
                    <td colspan="3"></td>
                </tr>
            </tbody>
        </table>

        <div class="totals-section">
            <div class="totals-left">
                <strong>HSN Summary (Inter-State: IGST):</strong>
                <table style="margin-top: 3px;">
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
                <p style="margin-top: 5px; font-size: 7px; color: #666;">
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
                    <span class="totals-label">Total Advance (3 Lots × 25%):</span>
                    <span class="totals-value">Rs. {total_advance:,.2f}</span>
                </div>
                <div class="totals-row balance">
                    <span class="totals-label">Total Balance (3 Lots × 75%):</span>
                    <span class="totals-value">Rs. {total_balance:,.2f}</span>
                </div>
            </div>
        </div>

        <div class="amount-words">
            <strong>Grand Total in Words:</strong> {number_to_words(float(grand_total))}
        </div>

        <div class="delivery-schedule">
            <h4>DELIVERY SCHEDULE & LOT-WISE PAYMENT PLAN</h4>
            <table style="margin-top: 5px; font-size: 8px; width: 100%;">
                <tr style="background: #166534; color: white;">
                    <th style="padding: 5px; text-align: left; width: 10%;">LOT</th>
                    <th style="padding: 5px; text-align: center; width: 15%;">DELIVERY DATE</th>
                    <th style="padding: 5px; text-align: right; width: 10%;">QTY</th>
                    <th style="padding: 5px; text-align: right; width: 15%;">LOT VALUE (incl. GST)</th>
                    <th style="padding: 5px; text-align: right; width: 15%;">ADVANCE (25%)</th>
                    <th style="padding: 5px; text-align: center; width: 15%;">ADVANCE DUE</th>
                    <th style="padding: 5px; text-align: right; width: 15%;">BALANCE (75%)</th>
                    <th style="padding: 5px; text-align: center; width: 15%;">BALANCE DUE</th>
                </tr>
                {lot_payment_rows}
                <tr style="background: #f3f4f6; font-weight: bold;">
                    <td style="padding: 5px;" colspan="2">TOTAL</td>
                    <td style="padding: 5px; text-align: right;">{total_qty:,}</td>
                    <td style="padding: 5px; text-align: right;">Rs. {grand_total:,.2f}</td>
                    <td style="padding: 5px; text-align: right;">Rs. {total_advance:,.2f}</td>
                    <td style="padding: 5px;"></td>
                    <td style="padding: 5px; text-align: right;">Rs. {total_balance:,.2f}</td>
                    <td style="padding: 5px;"></td>
                </tr>
            </table>
            <p style="margin-top: 5px; font-size: 7px; color: #666;">
                <strong>Note:</strong> Advance for each lot must be paid before delivery. Balance is due 45 days after each lot's delivery.
            </p>
        </div>

        <div class="bank-section">
            <h4>SUPPLIER BANK DETAILS</h4>
            <p><strong>Bank:</strong> {vendor['bank_name']} | <strong>Branch:</strong> {vendor['bank_branch'] or 'N/A'}</p>
            <p><strong>A/c:</strong> {vendor['bank_account_number']} | <strong>IFSC:</strong> {vendor['bank_ifsc']} | <strong>Name:</strong> {vendor['bank_account_name']}</p>
        </div>

        <div class="terms">
            <h4>TERMS & CONDITIONS:</h4>
            <ol>
                <li><strong>Payment (Lot-wise):</strong> 25% Advance for each lot before delivery, 75% Balance within 45 days from each lot's delivery</li>
                <li><strong>Delivery:</strong> As per lot-wise schedule - LOT 1 (Jan), LOT 2 (Feb), LOT 3 (Mar 2026)</li>
                <li><strong>Advance Payment:</strong> LOT 1 advance with PO, LOT 2 advance before 1st Feb, LOT 3 advance before 1st Mar</li>
                <li><strong>Quality:</strong> All items must meet Aquapurite quality standards</li>
                <li><strong>Packaging:</strong> Individual packaging with barcode labels required</li>
                <li><strong>Warranty:</strong> 6 months from date of delivery</li>
                <li>All disputes subject to Ghaziabad/Delhi jurisdiction.</li>
            </ol>
        </div>

        <div class="signature-section">
            <div class="signature-box">
                <div class="signature-line">Prepared By<br>Purchase Dept.</div>
            </div>
            <div class="signature-box">
                <div class="signature-line">Verified By<br>Accounts</div>
            </div>
            <div class="signature-box">
                <div class="signature-line">For {company['display_name']}<br>(Authorized Signatory)</div>
            </div>
        </div>

        <div class="footer">
            Purchase Order from Aquapurite ERP | {PO_NUMBER} | Generated: {datetime.now().strftime("%d-%m-%Y %H:%M:%S")}
        </div>
    </div>
</body>
</html>"""

    return html


async def main():
    """Main function to generate month-wise PO from master data"""
    print("=" * 80)
    print("GENERATING PURCHASE ORDER - SPARE PARTS (MONTH-WISE)")
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
        print(f"   Inter-state transaction (Delhi 07 -> UP 09)")
        print(f"   Tax: IGST {IGST_RATE}%")

        # Calculate totals with month-wise breakdown
        print("\n4. Order Summary (Month-wise):")
        print("-" * 100)
        print(f"{'S.No':<5} {'SKU':<12} {'Description':<30} {'JAN':>8} {'FEB':>8} {'MAR':>8} {'TOTAL':>8} {'Rate':>10} {'Amount':>12}")
        print("-" * 100)

        subtotal = Decimal("0")
        for item in ORDER_ITEMS:
            jan = item["monthly"].get("2026-01", 0)
            feb = item["monthly"].get("2026-02", 0)
            mar = item["monthly"].get("2026-03", 0)
            total = jan + feb + mar
            amount = total * item["rate"]
            subtotal += amount
            print(f"{item['sr_no']:<5} {item['sku']:<12} {item['name'][:30]:<30} {jan:>8,} {feb:>8,} {mar:>8,} {total:>8,} Rs.{item['rate']:>8,.0f} Rs.{amount:>10,.0f}")

        igst = subtotal * IGST_RATE / 100
        grand_total = subtotal + igst
        advance = grand_total * ADVANCE_PERCENTAGE / 100
        balance = grand_total - advance

        print("-" * 100)
        print(f"{'Sub Total':<78} Rs.{subtotal:>18,.2f}")
        print(f"{'IGST @ 18%':<78} Rs.{igst:>18,.2f}")
        print(f"{'GRAND TOTAL':<78} Rs.{grand_total:>18,.2f}")
        print("=" * 100)

        # Calculate lot-wise payments
        print("\n5. LOT-WISE PAYMENT SCHEDULE:")
        print("-" * 100)
        print(f"{'LOT':<15} {'DELIVERY':<15} {'QTY':>10} {'LOT VALUE':>18} {'ADVANCE (25%)':>18} {'BALANCE (75%)':>18}")
        print("-" * 100)

        lot_values = {}
        for item in ORDER_ITEMS:
            for m in ["2026-01", "2026-02", "2026-03"]:
                qty = item["monthly"].get(m, 0)
                if qty > 0:
                    if m not in lot_values:
                        lot_values[m] = Decimal("0")
                    lot_values[m] += qty * item["rate"]

        total_adv = Decimal("0")
        total_bal = Decimal("0")
        lot_info = [
            ("LOT 1 (JAN)", "2026-01", "15th Jan 2026"),
            ("LOT 2 (FEB)", "2026-02", "15th Feb 2026"),
            ("LOT 3 (MAR)", "2026-03", "15th Mar 2026"),
        ]

        for lot_name, month_code, delivery in lot_info:
            lot_val = lot_values.get(month_code, Decimal("0"))
            lot_tax = lot_val * IGST_RATE / 100
            lot_total = lot_val + lot_tax
            lot_adv = lot_total * ADVANCE_PERCENTAGE / 100
            lot_bal = lot_total - lot_adv
            total_adv += lot_adv
            total_bal += lot_bal

            month_qty = sum(item["monthly"].get(month_code, 0) for item in ORDER_ITEMS)
            print(f"{lot_name:<15} {delivery:<15} {month_qty:>10,} Rs.{lot_total:>15,.2f} Rs.{lot_adv:>15,.2f} Rs.{lot_bal:>15,.2f}")

        print("-" * 100)
        print(f"{'TOTAL':<15} {'3 Months':<15} {'':<10} Rs.{grand_total:>15,.2f} Rs.{total_adv:>15,.2f} Rs.{total_bal:>15,.2f}")
        print("=" * 100)

        # Fetch warehouse details for Ship To
        print("\n6. Fetching warehouse details for Ship To...")
        result = await db.execute(text("""
            SELECT name, address_line1, address_line2, city, state, pincode
            FROM warehouses WHERE is_active = true LIMIT 1
        """))
        wh_row = result.fetchone()

        if wh_row:
            ship_to = {
                "name": wh_row[0],
                "address_line1": wh_row[1],
                "address_line2": wh_row[2],
                "city": wh_row[3],
                "state": wh_row[4],
                "pincode": wh_row[5],
                "state_code": company['state_code'],  # Use company's state code
            }
            print(f"   Warehouse: {ship_to['name']}")
            print(f"   Address: {ship_to['address_line1']}, {ship_to['city']}, {ship_to['state']}")
        else:
            # Default to company address if no warehouse found
            ship_to = {
                "name": company['legal_name'] + " - Warehouse",
                "address_line1": company['address_line1'],
                "address_line2": company.get('address_line2'),
                "city": company['city'],
                "state": company['state'],
                "pincode": company['pincode'],
                "state_code": company['state_code'],
            }
            print(f"   Using company address as Ship To")

        # Generate HTML
        print("\n7. Generating Purchase Order HTML (with Bill To & Ship To)...")
        html_content = generate_po_html(company, vendor, ship_to)

        # Save to /tmp
        output_path = f"/tmp/PurchaseOrder-{PO_NUMBER.replace('/', '-')}-MonthWise.html"
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        print(f"\n{'=' * 80}")
        print("PURCHASE ORDER GENERATED SUCCESSFULLY (LOT-WISE PAYMENTS)")
        print("=" * 80)
        print(f"\nPO Number: {PO_NUMBER}")
        print(f"Buyer: {company['legal_name']}")
        print(f"Supplier: {vendor['legal_name']}")
        print(f"Total Value: Rs. {grand_total:,.2f}")
        print(f"\nLOT-WISE PAYMENT SUMMARY:")
        print(f"  LOT 1 (JAN): Advance Rs. {(lot_values.get('2026-01', 0) * Decimal('1.18') * Decimal('0.25')):,.2f} | Balance Rs. {(lot_values.get('2026-01', 0) * Decimal('1.18') * Decimal('0.75')):,.2f}")
        print(f"  LOT 2 (FEB): Advance Rs. {(lot_values.get('2026-02', 0) * Decimal('1.18') * Decimal('0.25')):,.2f} | Balance Rs. {(lot_values.get('2026-02', 0) * Decimal('1.18') * Decimal('0.75')):,.2f}")
        print(f"  LOT 3 (MAR): Advance Rs. {(lot_values.get('2026-03', 0) * Decimal('1.18') * Decimal('0.25')):,.2f} | Balance Rs. {(lot_values.get('2026-03', 0) * Decimal('1.18') * Decimal('0.75')):,.2f}")
        print(f"\nTotal Advance (3 Lots): Rs. {total_adv:,.2f}")
        print(f"Total Balance (3 Lots): Rs. {total_bal:,.2f}")
        print(f"\nFile: {output_path}")

        return output_path


if __name__ == "__main__":
    output = asyncio.run(main())
    if output:
        os.system(f'open "{output}"')
