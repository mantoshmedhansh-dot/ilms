"""
Generate STOS Spare Parts Purchase Order PDF/HTML document.
"""
import asyncio
import sys
import os
import webbrowser
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.database import async_session_factory
from app.models.purchase import PurchaseOrder, POStatus


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

    if rupees == 0:
        return f'{two_digits(paise)} Paise Only'

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


async def generate_po_pdf():
    """Generate PO document for STOS Spare Parts."""

    async with async_session_factory() as db:
        result = await db.execute(
            select(PurchaseOrder)
            .options(selectinload(PurchaseOrder.items))
            .where(PurchaseOrder.po_number == "PO-2026-00006")
        )
        po = result.scalar_one_or_none()

        if not po:
            print("ERROR: Purchase Order not found!")
            return

        print(f"Generating PDF for: {po.po_number}")
        print(f"Vendor: {po.vendor_name}")
        print(f"Status: {po.status.value}")
        print(f"Items: {len(po.items)}")

        # Build items table rows
        items_html = ""
        total_qty = 0
        for idx, item in enumerate(po.items, 1):
            total_qty += item.quantity_ordered
            items_html += f"""
            <tr>
                <td style="text-align: center;">{idx}</td>
                <td>
                    <strong>{item.product_name}</strong><br>
                    <small style="color: #666;">SKU: {item.sku} | HSN: {item.hsn_code or 'N/A'}</small>
                    {f'<br><small style="color: #888;">{item.notes}</small>' if item.notes else ''}
                </td>
                <td style="text-align: center;">{item.quantity_ordered:,}</td>
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

        # Status badge color
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
            body {{ margin: 0; padding: 15px; }}
            .container {{ box-shadow: none; }}
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', Arial, sans-serif;
            font-size: 11px;
            line-height: 1.4;
            color: #333;
            background: #f5f5f5;
            padding: 20px;
        }}
        .container {{
            max-width: 900px;
            margin: 0 auto;
            background: white;
            padding: 25px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .print-btn {{
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 12px 24px;
            background: #2563eb;
            color: white;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 14px;
            font-weight: 600;
            z-index: 1000;
        }}
        .print-btn:hover {{ background: #1d4ed8; }}
        .header {{
            text-align: center;
            border-bottom: 3px solid #2563eb;
            padding-bottom: 12px;
            margin-bottom: 15px;
        }}
        .company-name {{
            font-size: 22px;
            font-weight: bold;
            color: #1e40af;
        }}
        .document-title {{
            font-size: 16px;
            font-weight: bold;
            color: #dc2626;
            margin: 12px 0;
            padding: 8px;
            background: #fef2f2;
            border: 1px solid #fecaca;
            text-align: center;
        }}
        .urgent-banner {{
            background: #fef3c7;
            border: 2px solid #f59e0b;
            color: #92400e;
            padding: 8px 15px;
            margin-bottom: 15px;
            border-radius: 4px;
            text-align: center;
            font-weight: bold;
        }}
        .info-grid {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
            margin-bottom: 15px;
        }}
        .info-box {{
            border: 1px solid #e5e7eb;
            padding: 10px;
            border-radius: 4px;
        }}
        .info-box h4 {{
            color: #1e40af;
            margin-bottom: 6px;
            font-size: 10px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 12px 0;
            font-size: 10px;
        }}
        th {{
            background: #1e40af;
            color: white;
            padding: 8px 6px;
            text-align: left;
            font-size: 10px;
        }}
        td {{
            padding: 8px 6px;
            border-bottom: 1px solid #e5e7eb;
            vertical-align: top;
        }}
        tr:nth-child(even) {{ background: #f9fafb; }}
        .totals {{
            margin-left: auto;
            width: 280px;
        }}
        .totals table td {{
            padding: 5px 8px;
        }}
        .totals .grand-total {{
            font-size: 12px;
            font-weight: bold;
            background: #1e40af;
            color: white;
        }}
        .amount-words {{
            background: #fef3c7;
            padding: 8px;
            margin: 12px 0;
            border-left: 4px solid #f59e0b;
            font-style: italic;
            font-size: 10px;
        }}
        .delivery-schedule {{
            background: #ecfdf5;
            padding: 10px;
            margin: 12px 0;
            border-left: 4px solid #10b981;
        }}
        .delivery-schedule h4 {{
            color: #065f46;
            margin-bottom: 5px;
        }}
        .terms {{
            margin-top: 15px;
            padding: 12px;
            background: #f9fafb;
            border-radius: 4px;
            font-size: 10px;
        }}
        .terms h4 {{
            color: #1e40af;
            margin-bottom: 8px;
        }}
        .terms ol {{
            margin-left: 18px;
        }}
        .terms li {{
            margin: 4px 0;
        }}
        .signatures {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 40px;
            margin-top: 30px;
            padding-top: 15px;
        }}
        .signature-box {{
            text-align: center;
        }}
        .signature-line {{
            border-top: 1px solid #333;
            margin-top: 50px;
            padding-top: 5px;
        }}
        .status-badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 10px;
            font-weight: bold;
        }}
        .status-approved {{
            background: #dcfce7;
            color: #166534;
        }}
        .status-pending {{
            background: #fef3c7;
            color: #92400e;
        }}
        .footer {{
            margin-top: 20px;
            padding-top: 12px;
            border-top: 1px solid #e5e7eb;
            text-align: center;
            font-size: 9px;
            color: #6b7280;
        }}
        .summary-box {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
            margin: 10px 0;
            padding: 10px;
            background: #eff6ff;
            border-radius: 4px;
        }}
    </style>
</head>
<body>
    <button class="print-btn no-print" onclick="window.print()">🖨️ Print / Save as PDF</button>

    <div class="container">
        <div class="header">
            <div class="company-name">ILMS.AI INDIA PVT LTD</div>
            <div style="font-size: 10px; color: #666; margin-top: 5px;">
                123 Industrial Area, Sector 5, Noida, UP - 201301<br>
                Phone: +91-120-4567890 | Email: accounts@ilms.ai<br>
                GSTIN: 09AABCU9603R1ZM | PAN: AABCU9603R
            </div>
        </div>

        <div class="document-title">
            PURCHASE ORDER - SPARE PARTS
            <span class="status-badge {status_class}" style="margin-left: 15px;">
                {po.status.value}
            </span>
        </div>

        <div class="urgent-banner">
            ⚠️ URGENT: Project delayed by 1 month - Need immediate processing
        </div>

        <div class="info-grid">
            <div class="info-box">
                <h4>Order Details</h4>
                <table style="margin: 0;">
                    <tr><td style="border: none; padding: 2px 0; width: 120px;"><strong>PO Number:</strong></td><td style="border: none; padding: 2px 0;">{po.po_number}</td></tr>
                    <tr><td style="border: none; padding: 2px 0;"><strong>PO Date:</strong></td><td style="border: none; padding: 2px 0;">{po.po_date.strftime('%d-%b-%Y') if po.po_date else 'N/A'}</td></tr>
                    <tr><td style="border: none; padding: 2px 0;"><strong>Reference:</strong></td><td style="border: none; padding: 2px 0;">{po.quotation_reference or 'N/A'}</td></tr>
                    <tr><td style="border: none; padding: 2px 0;"><strong>Payment Terms:</strong></td><td style="border: none; padding: 2px 0;">{po.payment_terms or 'N/A'}</td></tr>
                </table>
            </div>
            <div class="info-box">
                <h4>Vendor Details</h4>
                <strong>{po.vendor_name}</strong><br>
                {vendor_address_str}<br>
                <strong>GSTIN:</strong> {po.vendor_gstin or 'N/A'}<br>
                <strong>Contact:</strong> Saurabh Sharma
            </div>
        </div>

        <div class="summary-box">
            <div><strong>Total Items:</strong> {len(po.items)} categories</div>
            <div><strong>Total Quantity:</strong> {total_qty:,} pieces</div>
        </div>

        <table>
            <thead>
                <tr>
                    <th style="width: 35px; text-align: center;">S.No</th>
                    <th>Item Description</th>
                    <th style="width: 60px; text-align: center;">Qty</th>
                    <th style="width: 40px; text-align: center;">UOM</th>
                    <th style="width: 80px; text-align: right;">Unit Price</th>
                    <th style="width: 100px; text-align: right;">Amount</th>
                </tr>
            </thead>
            <tbody>
                {items_html}
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
            <table style="margin: 5px 0;">
                <tr>
                    <td style="border: none; padding: 3px 0;"><strong>Batch 1:</strong></td>
                    <td style="border: none; padding: 3px 0;">15th - 25th January 2026</td>
                    <td style="border: none; padding: 3px 0;">~13,100 items</td>
                </tr>
                <tr>
                    <td style="border: none; padding: 3px 0;"><strong>Batch 2:</strong></td>
                    <td style="border: none; padding: 3px 0;">15th February 2026</td>
                    <td style="border: none; padding: 3px 0;">~14,700 items</td>
                </tr>
            </table>
            <div style="margin-top: 8px; padding-top: 8px; border-top: 1px dashed #10b981;">
                <strong>Payment:</strong> 25% Advance (₹{po.advance_required:,.2f}) | Balance on Delivery
            </div>
        </div>

        <div class="terms">
            <h4>Terms & Conditions</h4>
            <ol>
                <li><strong>DELIVERY:</strong> As per schedule above (Batch 1: Jan, Batch 2: Feb 2026)</li>
                <li><strong>QUALITY:</strong> All items must meet ILMS.AI quality standards</li>
                <li><strong>PACKAGING:</strong> Individual packaging with barcode labels required</li>
                <li><strong>WARRANTY:</strong> 6 months from date of delivery</li>
                <li><strong>RENDER IMAGES:</strong> Vendor to provide render photos of all spares for marketing material</li>
                <li><strong>PARTNERSHIP:</strong> This is a LONG TERM STRATEGIC PARTNERSHIP - exclusive supplier arrangement</li>
            </ol>
        </div>

        <div style="background: #fef2f2; padding: 10px; margin-top: 12px; border-left: 4px solid #dc2626; font-size: 10px;">
            <strong>Special Instructions:</strong><br>
            {po.special_instructions or 'N/A'}
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
                    {'Finance Head' if po.approved_at else 'Pending Approval'}<br>
                    <small>{po.approved_at.strftime('%d-%b-%Y %H:%M') if po.approved_at else 'Awaiting approval'}</small>
                </div>
            </div>
        </div>

        <div class="footer">
            This is a computer-generated document. No signature required.<br>
            Generated on: {datetime.now().strftime('%d-%b-%Y %H:%M:%S')} | Approval Status: {po.status.value}
        </div>
    </div>
</body>
</html>
        """

        # Save to file
        output_path = "/tmp/PO-2026-00006-STOS-SpareParts.html"
        with open(output_path, "w") as f:
            f.write(html)

        print(f"\nPDF/HTML generated: {output_path}")
        print("Opening in browser...")

        # Open in browser
        webbrowser.open(f"file://{output_path}")

        return output_path


if __name__ == "__main__":
    asyncio.run(generate_po_pdf())
