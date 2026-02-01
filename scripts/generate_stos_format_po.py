"""
Generate Purchase Order PDF in STOS Proforma Invoice format.
Includes: Part Code, HSN Code, Month-wise quantities, Bill To, Ship To

Reference: STOS Industrial Corporation Proforma Invoice STOS-001/25-26
"""
import asyncio
import sys
import os
import subprocess
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from decimal import Decimal
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.database import async_session_factory
from app.models.purchase import PurchaseOrder, PurchaseOrderItem

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

    # Crores
    if num >= 10000000:
        result.append(two_digit(num // 10000000) + ' Crore')
        num %= 10000000

    # Lakhs
    if num >= 100000:
        result.append(two_digit(num // 100000) + ' Lakh')
        num %= 100000

    # Thousands
    if num >= 1000:
        result.append(two_digit(num // 1000) + ' Thousand')
        num %= 1000

    # Hundreds and below
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


def get_address_html(addr_dict, default_name=""):
    """Format address dict as HTML."""
    if not addr_dict:
        return f"<div><strong>{default_name}</strong></div>"

    lines = []
    if addr_dict.get('name'):
        lines.append(f"<strong>{addr_dict['name']}</strong>")
    if addr_dict.get('address_line1'):
        lines.append(addr_dict['address_line1'])
    if addr_dict.get('address_line2'):
        lines.append(addr_dict['address_line2'])

    city_state = []
    if addr_dict.get('city'):
        city_state.append(addr_dict['city'])
    if addr_dict.get('district') and addr_dict['district'] != addr_dict.get('city'):
        city_state.append(addr_dict['district'])
    if addr_dict.get('state'):
        city_state.append(addr_dict['state'])
    if addr_dict.get('pincode'):
        city_state.append(addr_dict['pincode'])
    if city_state:
        lines.append(", ".join(city_state))

    return "<br>".join(lines)


async def generate_po_pdf(po_number: str):
    """Generate PDF for Purchase Order in STOS format with Bill To and Ship To."""
    async with async_session_factory() as db:
        # Get PO with items
        result = await db.execute(
            select(PurchaseOrder)
            .options(selectinload(PurchaseOrder.items))
            .where(PurchaseOrder.po_number == po_number)
        )
        po = result.scalars().first()

        if not po:
            print(f"PO {po_number} not found!")
            return

        print(f"Generating STOS-format PDF for: {po.po_number}")
        print(f"Vendor: {po.vendor_name}")
        print(f"Items: {len(po.items)}")

        # Get sorted items
        items = sorted(po.items, key=lambda x: x.line_number)

        # Extract months from monthly_quantities
        months = set()
        for item in items:
            if item.monthly_quantities:
                months.update(item.monthly_quantities.keys())
        months = sorted(months)

        # Bill To (use from PO or default)
        bill_to = po.bill_to or {
            "name": "Aquapurite Private Limited",
            "address_line1": "PLOT 36-A KH NO 181, DINDAPUR EXT",
            "address_line2": "PH-1, SHYAM VIHAR, Najafgarh",
            "city": "New Delhi",
            "district": "West Delhi",
            "state": "Delhi",
            "pincode": "110043",
            "gstin": "07ABDCA6170C1Z0",
            "state_code": "07"
        }

        # Ship To (use from PO, or default to bill_to)
        ship_to = po.ship_to or bill_to

        # Vendor address
        vendor_addr = po.vendor_address or {}

        # Generate HTML
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Purchase Order - {po.po_number}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: Arial, sans-serif; font-size: 11px; padding: 15px; }}
        .header {{ display: flex; justify-content: space-between; margin-bottom: 10px; }}
        .header-left {{ font-size: 10px; }}
        .header-right {{ text-align: right; font-size: 10px; }}
        .title {{ text-align: center; margin: 15px 0; }}
        .title h1 {{ font-size: 18px; font-weight: bold; color: #000; margin-bottom: 5px; }}
        .title .subtitle {{ font-size: 10px; color: #666; }}
        .doc-type {{ text-align: center; background: #e0e0e0; padding: 5px; font-weight: bold; margin-bottom: 15px; }}
        .info-row {{ display: flex; justify-content: space-between; margin-bottom: 10px; border: 1px solid #000; }}
        .info-box {{ padding: 8px; width: 50%; }}
        .info-box.right {{ border-left: 1px solid #000; }}
        .info-label {{ font-weight: bold; margin-bottom: 3px; text-decoration: underline; }}
        .party-box {{ border: 1px solid #000; margin-bottom: 10px; }}
        .party-header {{ display: flex; background: #f0f0f0; border-bottom: 1px solid #000; }}
        .party-header-col {{ width: 50%; padding: 5px 10px; font-weight: bold; text-align: center; }}
        .party-header-col.right {{ border-left: 1px solid #000; }}
        .party-row {{ display: flex; }}
        .party-col {{ width: 50%; padding: 10px; line-height: 1.5; }}
        .party-col.right {{ border-left: 1px solid #000; }}
        table {{ width: 100%; border-collapse: collapse; margin-bottom: 10px; }}
        th, td {{ border: 1px solid #000; padding: 5px; text-align: center; font-size: 10px; }}
        th {{ background: #f0f0f0; font-weight: bold; }}
        td.left {{ text-align: left; }}
        td.right {{ text-align: right; }}
        .amount-row {{ background: #f9f9f9; }}
        .grand-total {{ font-weight: bold; font-size: 12px; }}
        .footer {{ margin-top: 15px; }}
        .bank-details {{ border: 1px solid #000; padding: 10px; margin-bottom: 10px; }}
        .terms {{ font-size: 10px; }}
        .signature {{ text-align: right; margin-top: 30px; }}
        .amount-words {{ background: #ffffcc; padding: 8px; border: 1px solid #000; margin: 10px 0; font-size: 11px; }}
        .print-btn {{ position: fixed; top: 10px; right: 10px; padding: 10px 20px; background: #007bff; color: white; border: none; cursor: pointer; font-size: 14px; border-radius: 5px; z-index: 1000; }}
        .print-btn:hover {{ background: #0056b3; }}
        @media print {{
            .print-btn {{ display: none; }}
            body {{ padding: 0; }}
        }}
    </style>
</head>
<body>
    <button class="print-btn" onclick="window.print()">Print / Save as PDF</button>

    <!-- Header with Vendor Details (Since this is a PO from us to vendor) -->
    <div class="header">
        <div class="header-left">
            <div>GSTIN : {bill_to.get('gstin', '07ABDCA6170C1Z0')}</div>
            <div>STATE : {bill_to.get('state', 'DELHI').upper()}</div>
            <div>STATE CODE : {bill_to.get('state_code', '07')}</div>
            <div>PAN NO. : {bill_to.get('gstin', '07ABDCA6170C1Z0')[2:12] if bill_to.get('gstin') else 'ABDCA6170C'}</div>
        </div>
        <div class="header-right">
            <div>CIN NO. U27100DL2020PTC000000</div>
            <div style="margin-top: 10px;"><strong>Original Copy</strong></div>
        </div>
    </div>

    <!-- Document Type -->
    <div class="doc-type">PURCHASE ORDER</div>

    <!-- Company Name -->
    <div class="title">
        <h1>{bill_to.get('name', 'AQUAPURITE PRIVATE LIMITED').upper()}</h1>
        <div class="subtitle">{bill_to.get('address_line1', '')}, {bill_to.get('address_line2', '')}, {bill_to.get('city', '')}, {bill_to.get('state', '')}, {bill_to.get('pincode', '')}</div>
    </div>

    <!-- PO Details -->
    <div class="info-row">
        <div class="info-box">
            <div><strong>P.O. Number :</strong> {po.po_number}</div>
            <div><strong>Reverse Charges :</strong> NO</div>
        </div>
        <div class="info-box right">
            <div><strong>Dated :</strong> {po.po_date.strftime('%d-%m-%Y')}</div>
            <div><strong>E WAY BILL NO. :</strong> N.A.</div>
        </div>
    </div>

    <!-- Vendor Details -->
    <div class="party-box">
        <div class="party-header">
            <div class="party-header-col" style="width: 100%;">Details Of Supplier | Vendor</div>
        </div>
        <div class="party-row">
            <div class="party-col" style="width: 100%;">
                <strong>{po.vendor_name}</strong><br>
                {vendor_addr.get('address_line1', 'E-180, SECTOR 17, KAVI NAGAR INDUSTRIAL AREA')}<br>
                {vendor_addr.get('address_line2', 'DHADHAPUR RUPA')}<br>
                {vendor_addr.get('city', 'GHAZIABAD')}, {vendor_addr.get('state', 'UTTAR PRADESH')}<br>
                <br>
                State Code : {vendor_addr.get('state_code', '09')}<br>
                GSTIN : {po.vendor_gstin or 'N/A'}
            </div>
        </div>
    </div>

    <!-- Bill To & Ship To Section (Side by Side) -->
    <div class="party-box">
        <div class="party-header">
            <div class="party-header-col">Details Of Receiver | Billed To:</div>
            <div class="party-header-col right">Details Of Consignee | Shipped To:</div>
        </div>
        <div class="party-row">
            <div class="party-col">
                <strong>{bill_to.get('name', 'Aquapurite Private Limited')}</strong><br>
                {bill_to.get('address_line1', '')}<br>
                {bill_to.get('address_line2', '')}<br>
                {bill_to.get('city', '')}, {bill_to.get('district', bill_to.get('city', ''))}, {bill_to.get('state', '')}, {bill_to.get('pincode', '')}<br>
                <br>
                State Code : {bill_to.get('state_code', '07')}<br>
                GSTIN : {bill_to.get('gstin', '07ABDCA6170C1Z0')}<br>
                {f"Phone : {bill_to.get('phone')}" if bill_to.get('phone') else ""}
                {f"<br>Email : {bill_to.get('email')}" if bill_to.get('email') else ""}
            </div>
            <div class="party-col right">
                <strong>{ship_to.get('name', 'Aquapurite Private Limited')}</strong><br>
                {ship_to.get('address_line1', '')}<br>
                {ship_to.get('address_line2', '')}<br>
                {ship_to.get('city', '')}, {ship_to.get('district', ship_to.get('city', ''))}, {ship_to.get('state', '')}, {ship_to.get('pincode', '')}<br>
                <br>
                State Code : {ship_to.get('state_code', '07')}<br>
                GSTIN : {ship_to.get('gstin', '07ABDCA6170C1Z0')}<br>
                {f"Contact Person : {ship_to.get('contact_person')}" if ship_to.get('contact_person') else ""}
                {f"<br>Phone : {ship_to.get('phone')}" if ship_to.get('phone') else ""}
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
                <th style="width: 65px;">HSN/SAC<br>Code</th>"""

        # Add month columns if available
        for month in months:
            month_label = datetime.strptime(month, "%Y-%m").strftime("%b '%y").upper()
            html += f'\n                <th style="width: 55px;">{month_label}</th>'

        html += f"""
                <th style="width: 55px;">Qty.</th>
                <th style="width: 40px;">Unit</th>
                <th style="width: 65px;">Price</th>
                <th style="width: 85px;">Amount(`)</th>
            </tr>
        </thead>
        <tbody>"""

        # Items
        total_qty = 0
        for idx, item in enumerate(items, 1):
            # Calculate month-wise quantities
            month_qtys = []
            item_total_qty = item.quantity_ordered
            total_qty += item_total_qty

            for month in months:
                qty = item.monthly_quantities.get(month, 0) if item.monthly_quantities else 0
                month_qtys.append(qty)

            html += f"""
            <tr>
                <td>{idx}.</td>
                <td class="left">{item.product_name}</td>
                <td>{item.part_code or '-'}</td>
                <td>{item.hsn_code or '84212190'}</td>"""

            for qty in month_qtys:
                html += f'\n                <td>{qty:,}</td>' if qty else '\n                <td>-</td>'

            html += f"""
                <td>{item_total_qty:,}</td>
                <td>{item.uom}</td>
                <td class="right">{float(item.unit_price):,.2f}</td>
                <td class="right">{float(item.taxable_amount):,.2f}</td>
            </tr>"""

        # Total row
        html += f"""
            <tr class="amount-row">
                <td colspan="4"><strong>Total</strong></td>"""

        for month in months:
            month_total = sum(
                item.monthly_quantities.get(month, 0)
                for item in items
                if item.monthly_quantities
            )
            html += f'\n                <td><strong>{month_total:,}</strong></td>'

        html += f"""
                <td><strong>{total_qty:,}</strong></td>
                <td>Pieces</td>
                <td class="right" colspan="2"><strong>Total {float(po.subtotal):,.2f}</strong></td>
            </tr>"""

        # Tax calculations - Determine if IGST or CGST+SGST
        # IGST for inter-state (different state codes), CGST+SGST for intra-state
        vendor_state = vendor_addr.get('state_code', '09')
        buyer_state = bill_to.get('state_code', '07')
        is_igst = vendor_state != buyer_state

        num_cols = 4 + len(months)

        html += f"""
            <tr class="amount-row">
                <td colspan="{num_cols}" class="right">Totals c/o</td>
                <td colspan="3" class="right">{float(po.subtotal):,.2f}</td>
            </tr>"""

        if is_igst and po.igst_amount > 0:
            html += f"""
            <tr class="amount-row">
                <td colspan="{num_cols}" class="right">Add : IGST @ 18.00 %</td>
                <td colspan="3" class="right">{float(po.igst_amount):,.2f}</td>
            </tr>"""
        else:
            if po.cgst_amount > 0:
                html += f"""
            <tr class="amount-row">
                <td colspan="{num_cols}" class="right">Add : CGST @ 9.00 %</td>
                <td colspan="3" class="right">{float(po.cgst_amount):,.2f}</td>
            </tr>"""
            if po.sgst_amount > 0:
                html += f"""
            <tr class="amount-row">
                <td colspan="{num_cols}" class="right">Add : SGST @ 9.00 %</td>
                <td colspan="3" class="right">{float(po.sgst_amount):,.2f}</td>
            </tr>"""

        html += f"""
            <tr class="grand-total">
                <td colspan="{num_cols}" class="right">Grand Total `</td>
                <td colspan="3" class="right">{float(po.grand_total):,.2f}</td>
            </tr>
        </tbody>
    </table>

    <!-- Amount in Words -->
    <div class="amount-words">
        <strong>Amount in Words:</strong> {amount_to_words(float(po.grand_total))}
    </div>

    <!-- Bank Details -->
    <div class="bank-details">
        <div><strong>{bill_to.get('name', 'AQUAPURITE PRIVATE LIMITED').upper()}</strong></div>
        <table style="border: none; margin-top: 5px;">
            <tr style="border: none;">
                <td style="border: none; width: 100px;">Bank Name</td>
                <td style="border: none;">: ICICI BANK</td>
                <td style="border: none; width: 80px;">Branch</td>
                <td style="border: none;">: NAJAFGARH</td>
            </tr>
            <tr style="border: none;">
                <td style="border: none;">A/c No.</td>
                <td style="border: none;">: 123456789012</td>
                <td style="border: none;">IFS Code</td>
                <td style="border: none;">: ICIC0001234</td>
            </tr>
        </table>
    </div>

    <!-- Terms & Conditions -->
    <div class="terms">
        <div><strong>Terms & Conditions</strong></div>
        <div>E.& O.E.</div>
        <ol>
            <li>Goods to be delivered within {(po.expected_delivery_date - po.po_date).days if po.expected_delivery_date else 30} days from PO date.</li>
            <li>Payment terms: {po.payment_terms or f'Net {po.credit_days} days'}</li>
            <li>All disputes subject to Delhi Jurisdiction only.</li>
            <li>Quality as per approved samples.</li>
            <li>Freight: {po.special_instructions or 'EXTRA AS PER ACTUAL'}</li>
        </ol>
    </div>

    <!-- Signature -->
    <div class="signature">
        <div>for <strong>{bill_to.get('name', 'AQUAPURITE PRIVATE LIMITED').upper()}</strong></div>
        <div style="margin-top: 40px;">Authorised Signatory</div>
    </div>

</body>
</html>"""

        # Save HTML
        filename = f"/tmp/{po.po_number}-STOS-Format.html"
        with open(filename, 'w') as f:
            f.write(html)

        print(f"\n✓ PDF generated: {filename}")
        print("Opening in browser...")

        # Open in browser
        subprocess.run(['open', filename])


if __name__ == "__main__":
    po_number = sys.argv[1] if len(sys.argv) > 1 else "PO-2026-00006"
    asyncio.run(generate_po_pdf(po_number))
