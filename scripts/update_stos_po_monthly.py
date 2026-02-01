"""
Update STOS Spare Parts PO with month-wise quantities and regenerate PDF.
"""
import asyncio
import sys
import os
import webbrowser
from datetime import datetime
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
from app.database import async_session_factory
from app.models.purchase import PurchaseOrder, PurchaseOrderItem, POStatus


# Month-wise quantities from the email
MONTHLY_QUANTITIES = {
    "SP-SDF-YRN-001": {"2026-01": 1500, "2026-02": 1500},  # Sediment Filter (PP Yarn Wound)
    "SP-SDF-SPN-001": {"2026-01": 1500, "2026-02": 1500},  # Sediment Filter (Spun Filter)
    "SP-PCB-PRM-001": {"2026-01": 1500, "2026-02": 1500},  # Pre Carbon Block (Premium)
    "SP-PCB-REG-001": {"2026-01": 1500, "2026-02": 1500},  # Pre Carbon Block (Regular)
    "SP-ALK-PRM-001": {"2026-01": 1000, "2026-02": 1000},  # Alkaline Mineral Block (Premium)
    "SP-POC-COP-001": {"2026-01": 1000, "2026-02": 1000},  # Post Carbon with Copper (Regular)
    "SP-MBR-PRM-001": {"2026-01": 1000, "2026-02": 1000},  # Membrane (Premium)
    "SP-MBR-REG-001": {"2026-01": 1000, "2026-02": 1000},  # Membrane (Regular)
    "SP-PFC-MLT-001": {"2026-01": 1000, "2026-02": 1000},  # Pre-Filter Multi Layer Candle
    "SP-HMR-001": {"2026-01": 200, "2026-02": 500},        # HMR Cartridge
    "SP-PFA-MLC-001": {"2026-01": 500, "2026-02": 1000},   # Prefilter with Multilayer Candle
    "SP-PFA-SPN-001": {"2026-01": 500, "2026-02": 1000},   # Prefilter with Spun Filter
    "SP-HMR-BLK-001": {"2026-01": 200, "2026-02": 200},    # Heavy Metal Remover
    "SP-PRV-PLS-001": {"2026-01": 200, "2026-02": 500},    # Plastic PRV
    "SP-DVV-BRS-001": {"2026-01": 500, "2026-02": 500},    # Brass Diverter Valve
}


def amount_to_words(amount):
    """Convert amount to words in Indian format."""
    ones = ['', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine',
            'Ten', 'Eleven', 'Twelve', 'Thirteen', 'Fourteen', 'Fifteen', 'Sixteen',
            'Seventeen', 'Eighteen', 'Nineteen']
    tens = ['', '', 'Twenty', 'Thirty', 'Forty', 'Fifty', 'Sixty', 'Seventy', 'Eighty', 'Ninety']

    def two_digits(n):
        if n < 20:
            return ones[n]
        return tens[n // 10] + (' ' + ones[n % 10] if n % 10 else '')

    def three_digits(n):
        if n < 100:
            return two_digits(n)
        return ones[n // 100] + ' Hundred' + (' ' + two_digits(n % 100) if n % 100 else '')

    if amount == 0:
        return 'Zero Rupees Only'

    rupees = int(amount)
    paise = int(round((amount - rupees) * 100))

    crore = rupees // 10000000
    rupees %= 10000000
    lakh = rupees // 100000
    rupees %= 100000
    thousand = rupees // 1000
    rupees %= 1000

    words = []
    if crore:
        words.append(f'{two_digits(crore)} Crore')
    if lakh:
        words.append(f'{two_digits(lakh)} Lakh')
    if thousand:
        words.append(f'{two_digits(thousand)} Thousand')
    if rupees:
        words.append(three_digits(rupees))

    result = ' '.join(words) + ' Rupees'
    if paise:
        result += f' and {two_digits(paise)} Paise'
    return result + ' Only'


async def update_and_generate_pdf():
    """Update PO items with monthly quantities and generate PDF."""

    async with async_session_factory() as db:
        # Get the STOS PO
        result = await db.execute(
            select(PurchaseOrder)
            .options(selectinload(PurchaseOrder.items))
            .where(PurchaseOrder.po_number == "PO-2026-00006")
        )
        po = result.scalar_one_or_none()

        if not po:
            print("ERROR: PO not found!")
            return

        print(f"Updating PO: {po.po_number}")
        print(f"Vendor: {po.vendor_name}")
        print(f"Items: {len(po.items)}")

        # Update each item with monthly quantities
        for item in po.items:
            if item.sku in MONTHLY_QUANTITIES:
                item.monthly_quantities = MONTHLY_QUANTITIES[item.sku]
                print(f"  Updated: {item.sku} -> {MONTHLY_QUANTITIES[item.sku]}")

        await db.commit()
        print("\n✓ Monthly quantities updated!")

        # Refresh to get updated data
        await db.refresh(po)

        # Generate PDF with month-wise columns
        print("\nGenerating PDF with month-wise breakdown...")

        # Build items table rows with monthly columns
        items_html = ""
        total_qty = 0
        jan_total = 0
        feb_total = 0

        for idx, item in enumerate(po.items, 1):
            total_qty += item.quantity_ordered
            monthly = item.monthly_quantities or {}
            jan_qty = monthly.get("2026-01", 0)
            feb_qty = monthly.get("2026-02", 0)
            jan_total += jan_qty
            feb_total += feb_qty

            items_html += f"""
            <tr>
                <td style="text-align: center;">{idx}</td>
                <td>
                    <strong>{item.product_name}</strong><br>
                    <small style="color: #666;">SKU: {item.sku}</small>
                </td>
                <td style="text-align: center; background: #fef3c7;">{jan_qty:,}</td>
                <td style="text-align: center; background: #dbeafe;">{feb_qty:,}</td>
                <td style="text-align: center; font-weight: bold;">{item.quantity_ordered:,}</td>
                <td style="text-align: center;">{item.uom}</td>
                <td style="text-align: right;">₹{item.unit_price:,.2f}</td>
                <td style="text-align: right;">₹{item.taxable_amount:,.2f}</td>
            </tr>
            """

        # Get vendor address
        vendor_addr = po.vendor_address or {}
        vendor_address_str = f"""
            {vendor_addr.get('address_line1', '')}<br>
            {vendor_addr.get('address_line2', '') + '<br>' if vendor_addr.get('address_line2') else ''}
            {vendor_addr.get('city', '')}, {vendor_addr.get('state', '')} - {vendor_addr.get('pincode', '')}
        """

        # Amount in words
        amount_words = amount_to_words(float(po.grand_total))

        # Status badge
        status_class = "status-pending" if po.status == POStatus.PENDING_APPROVAL else "status-approved"

        # Generate HTML
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Purchase Order - {po.po_number}</title>
    <style>
        @media print {{
            .no-print {{ display: none !important; }}
            body {{ margin: 0; padding: 10px; }}
            .container {{ box-shadow: none; }}
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', Arial, sans-serif;
            font-size: 10px;
            line-height: 1.3;
            color: #333;
            background: #f5f5f5;
            padding: 15px;
        }}
        .container {{
            max-width: 950px;
            margin: 0 auto;
            background: white;
            padding: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .print-btn {{
            position: fixed;
            top: 15px;
            right: 15px;
            padding: 10px 20px;
            background: #2563eb;
            color: white;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 13px;
            font-weight: 600;
            z-index: 1000;
        }}
        .print-btn:hover {{ background: #1d4ed8; }}
        .header {{
            text-align: center;
            border-bottom: 3px solid #2563eb;
            padding-bottom: 10px;
            margin-bottom: 12px;
        }}
        .company-name {{
            font-size: 20px;
            font-weight: bold;
            color: #1e40af;
        }}
        .document-title {{
            font-size: 14px;
            font-weight: bold;
            color: #dc2626;
            margin: 10px 0;
            padding: 6px;
            background: #fef2f2;
            border: 1px solid #fecaca;
            text-align: center;
        }}
        .urgent-banner {{
            background: #fef3c7;
            border: 2px solid #f59e0b;
            color: #92400e;
            padding: 6px 12px;
            margin-bottom: 12px;
            border-radius: 4px;
            text-align: center;
            font-weight: bold;
            font-size: 11px;
        }}
        .info-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 12px;
            margin-bottom: 12px;
        }}
        .info-box {{
            border: 1px solid #e5e7eb;
            padding: 8px;
            border-radius: 4px;
            font-size: 9px;
        }}
        .info-box h4 {{
            color: #1e40af;
            margin-bottom: 5px;
            font-size: 9px;
            text-transform: uppercase;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 10px 0;
            font-size: 9px;
        }}
        th {{
            background: #1e40af;
            color: white;
            padding: 6px 4px;
            text-align: left;
            font-size: 9px;
        }}
        th.month-jan {{
            background: #f59e0b;
        }}
        th.month-feb {{
            background: #3b82f6;
        }}
        td {{
            padding: 6px 4px;
            border-bottom: 1px solid #e5e7eb;
            vertical-align: top;
        }}
        tr:nth-child(even) {{ background: #f9fafb; }}
        .totals {{
            margin-left: auto;
            width: 260px;
        }}
        .totals table td {{
            padding: 4px 6px;
        }}
        .totals .grand-total {{
            font-size: 11px;
            font-weight: bold;
            background: #1e40af;
            color: white;
        }}
        .amount-words {{
            background: #fef3c7;
            padding: 6px;
            margin: 10px 0;
            border-left: 4px solid #f59e0b;
            font-style: italic;
            font-size: 9px;
        }}
        .delivery-schedule {{
            background: #ecfdf5;
            padding: 8px;
            margin: 10px 0;
            border-left: 4px solid #10b981;
            font-size: 9px;
        }}
        .delivery-schedule h4 {{
            color: #065f46;
            margin-bottom: 4px;
            font-size: 10px;
        }}
        .terms {{
            margin-top: 12px;
            padding: 10px;
            background: #f9fafb;
            border-radius: 4px;
            font-size: 9px;
        }}
        .terms h4 {{
            color: #1e40af;
            margin-bottom: 6px;
            font-size: 10px;
        }}
        .terms ol {{
            margin-left: 15px;
        }}
        .terms li {{
            margin: 3px 0;
        }}
        .signatures {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
            margin-top: 25px;
        }}
        .signature-box {{
            text-align: center;
        }}
        .signature-line {{
            border-top: 1px solid #333;
            margin-top: 40px;
            padding-top: 4px;
            font-size: 9px;
        }}
        .status-badge {{
            display: inline-block;
            padding: 3px 10px;
            border-radius: 15px;
            font-size: 9px;
            font-weight: bold;
        }}
        .status-approved {{ background: #dcfce7; color: #166534; }}
        .status-pending {{ background: #fef3c7; color: #92400e; }}
        .footer {{
            margin-top: 15px;
            padding-top: 10px;
            border-top: 1px solid #e5e7eb;
            text-align: center;
            font-size: 8px;
            color: #6b7280;
        }}
        .month-summary {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 8px;
            margin: 8px 0;
            font-size: 10px;
        }}
        .month-box {{
            padding: 8px;
            border-radius: 4px;
            text-align: center;
        }}
        .month-jan-box {{ background: #fef3c7; border: 1px solid #f59e0b; }}
        .month-feb-box {{ background: #dbeafe; border: 1px solid #3b82f6; }}
        .month-total-box {{ background: #dcfce7; border: 1px solid #10b981; }}
    </style>
</head>
<body>
    <button class="print-btn no-print" onclick="window.print()">🖨️ Print / Save as PDF</button>

    <div class="container">
        <div class="header">
            <div class="company-name">AQUAPURITE INDIA PVT LTD</div>
            <div style="font-size: 9px; color: #666; margin-top: 4px;">
                123 Industrial Area, Sector 5, Noida, UP - 201301 | GSTIN: 09AABCU9603R1ZM
            </div>
        </div>

        <div class="document-title">
            PURCHASE ORDER - SPARE PARTS (MONTH-WISE SCHEDULE)
            <span class="status-badge {status_class}" style="margin-left: 10px;">{po.status.value}</span>
        </div>

        <div class="urgent-banner">
            ⚠️ URGENT: Project delayed by 1 month - Need immediate processing
        </div>

        <div class="info-grid">
            <div class="info-box">
                <h4>Order Details</h4>
                <table style="margin: 0;">
                    <tr><td style="border: none; padding: 2px 0; width: 100px;"><strong>PO Number:</strong></td><td style="border: none; padding: 2px 0;">{po.po_number}</td></tr>
                    <tr><td style="border: none; padding: 2px 0;"><strong>PO Date:</strong></td><td style="border: none; padding: 2px 0;">{po.po_date.strftime('%d-%b-%Y') if po.po_date else 'N/A'}</td></tr>
                    <tr><td style="border: none; padding: 2px 0;"><strong>Reference:</strong></td><td style="border: none; padding: 2px 0;">{po.quotation_reference or 'N/A'}</td></tr>
                    <tr><td style="border: none; padding: 2px 0;"><strong>Payment:</strong></td><td style="border: none; padding: 2px 0;">25% Advance, Balance on Delivery</td></tr>
                </table>
            </div>
            <div class="info-box">
                <h4>Vendor Details</h4>
                <strong>{po.vendor_name}</strong><br>
                {vendor_address_str}<br>
                <strong>GSTIN:</strong> {po.vendor_gstin or 'N/A'}
            </div>
        </div>

        <div class="month-summary">
            <div class="month-box month-jan-box">
                <strong>JAN 2026</strong><br>
                15th-25th Jan<br>
                <span style="font-size: 14px; font-weight: bold;">{jan_total:,}</span> pcs
            </div>
            <div class="month-box month-feb-box">
                <strong>FEB 2026</strong><br>
                15th Feb<br>
                <span style="font-size: 14px; font-weight: bold;">{feb_total:,}</span> pcs
            </div>
            <div class="month-box month-total-box">
                <strong>TOTAL</strong><br>
                Combined<br>
                <span style="font-size: 14px; font-weight: bold;">{total_qty:,}</span> pcs
            </div>
        </div>

        <table>
            <thead>
                <tr>
                    <th style="width: 30px; text-align: center;">S.No</th>
                    <th>Item Description</th>
                    <th class="month-jan" style="width: 70px; text-align: center;">JAN '26</th>
                    <th class="month-feb" style="width: 70px; text-align: center;">FEB '26</th>
                    <th style="width: 70px; text-align: center; background: #166534;">TOTAL</th>
                    <th style="width: 35px; text-align: center;">UOM</th>
                    <th style="width: 70px; text-align: right;">Rate</th>
                    <th style="width: 90px; text-align: right;">Amount</th>
                </tr>
            </thead>
            <tbody>
                {items_html}
                <tr style="background: #f3f4f6; font-weight: bold;">
                    <td colspan="2" style="text-align: right;"><strong>TOTAL QUANTITIES →</strong></td>
                    <td style="text-align: center; background: #fef3c7;">{jan_total:,}</td>
                    <td style="text-align: center; background: #dbeafe;">{feb_total:,}</td>
                    <td style="text-align: center; background: #dcfce7;">{total_qty:,}</td>
                    <td colspan="3"></td>
                </tr>
            </tbody>
        </table>

        <div class="totals">
            <table>
                <tr>
                    <td><strong>Subtotal:</strong></td>
                    <td style="text-align: right;">₹{po.subtotal:,.2f}</td>
                </tr>
                <tr>
                    <td>CGST @ 9%:</td>
                    <td style="text-align: right;">₹{po.cgst_amount:,.2f}</td>
                </tr>
                <tr>
                    <td>SGST @ 9%:</td>
                    <td style="text-align: right;">₹{po.sgst_amount:,.2f}</td>
                </tr>
                <tr class="grand-total">
                    <td><strong>GRAND TOTAL:</strong></td>
                    <td style="text-align: right;"><strong>₹{po.grand_total:,.2f}</strong></td>
                </tr>
            </table>
        </div>

        <div class="amount-words">
            <strong>Amount in Words:</strong> {amount_words}
        </div>

        <div class="delivery-schedule">
            <h4>📦 Delivery Schedule</h4>
            <table style="margin: 4px 0;">
                <tr>
                    <td style="border: none; padding: 2px 0; width: 80px;"><strong>Batch 1 (Jan):</strong></td>
                    <td style="border: none; padding: 2px 0;">15th - 25th January 2026</td>
                    <td style="border: none; padding: 2px 0; text-align: right;"><strong>{jan_total:,} pieces</strong></td>
                </tr>
                <tr>
                    <td style="border: none; padding: 2px 0;"><strong>Batch 2 (Feb):</strong></td>
                    <td style="border: none; padding: 2px 0;">15th February 2026</td>
                    <td style="border: none; padding: 2px 0; text-align: right;"><strong>{feb_total:,} pieces</strong></td>
                </tr>
            </table>
            <div style="margin-top: 6px; padding-top: 6px; border-top: 1px dashed #10b981;">
                <strong>Payment:</strong> 25% Advance (₹{po.advance_required:,.2f}) | Balance on each delivery
            </div>
        </div>

        <div class="terms">
            <h4>Terms & Conditions</h4>
            <ol>
                <li><strong>DELIVERY:</strong> As per month-wise schedule (Jan & Feb 2026 batches)</li>
                <li><strong>QUALITY:</strong> All items must meet Aquapurite quality standards</li>
                <li><strong>PACKAGING:</strong> Individual packaging with barcode labels required</li>
                <li><strong>WARRANTY:</strong> 6 months from date of delivery</li>
                <li><strong>RENDER IMAGES:</strong> Vendor to provide render photos of all spares for marketing</li>
                <li><strong>PARTNERSHIP:</strong> Long-term strategic partnership - exclusive supplier arrangement</li>
            </ol>
        </div>

        <div class="signatures">
            <div class="signature-box">
                <div class="signature-line">
                    <strong>Prepared By</strong><br>
                    Procurement Team
                </div>
            </div>
            <div class="signature-box">
                <div class="signature-line">
                    <strong>Approved By</strong><br>
                    {'Finance Head' if po.approved_at else 'Pending Approval'}
                </div>
            </div>
        </div>

        <div class="footer">
            Generated on: {datetime.now().strftime('%d-%b-%Y %H:%M:%S')} | Status: {po.status.value}
        </div>
    </div>
</body>
</html>
        """

        # Save to file
        output_path = "/tmp/PO-2026-00006-STOS-MonthWise.html"
        with open(output_path, "w") as f:
            f.write(html)

        print(f"\n✓ PDF generated: {output_path}")
        print("Opening in browser...")

        # Open in browser
        webbrowser.open(f"file://{output_path}")

        return output_path


if __name__ == "__main__":
    asyncio.run(update_and_generate_pdf())
