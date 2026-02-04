"""
Generate Vendor Proforma Invoice PDF in STOS format.
Includes: Part Code, HSN Code, Bill To, Ship To

Reference: STOS Industrial Corporation Proforma Invoice STOS-001/25-26
"""
import asyncio
import sys
import os
import subprocess
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from decimal import Decimal
from datetime import datetime, date
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.database import async_session_factory
from app.models.purchase import VendorProformaInvoice, VendorProformaItem
from app.models.vendor import Vendor


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


def get_address_html(addr_dict, default_name=""):
    """Format address dict as HTML."""
    if not addr_dict:
        return f"<strong>{default_name}</strong>"

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


async def create_stos_proforma():
    """Create STOS Proforma Invoice matching the reference PDF."""
    async with async_session_factory() as db:
        # Check if already exists
        result = await db.execute(
            select(VendorProformaInvoice).where(
                VendorProformaInvoice.proforma_number == "STOS-001/25-26"
            )
        )
        existing = result.scalars().first()
        if existing:
            print(f"Proforma {existing.proforma_number} already exists")
            return existing.our_reference

        # Get STOS vendor
        result = await db.execute(
            select(Vendor).where(Vendor.name.ilike("%STOS%"))
        )
        vendor = result.scalars().first()

        if not vendor:
            print("STOS vendor not found!")
            return None

        # Get admin user
        from app.models.user import User
        result = await db.execute(select(User).limit(1))
        user = result.scalars().first()

        # Create Proforma Invoice
        pi = VendorProformaInvoice(
            proforma_number="STOS-001/25-26",
            our_reference="VPI-20251226-0001",
            vendor_id=vendor.id,
            proforma_date=date(2025, 12, 26),
            validity_date=date(2026, 1, 31),
            credit_days=30,
            payment_terms="ADVANCE PAYMENT AGAINST PERFORMA INVOICE",
            delivery_terms="FREIGHT EXTRA AS PER ACTUAL",
            bill_to={
                "name": "ILMS.AI",
                "address_line1": "PLOT 36-A KH NO 181, DINDAPUR EXT",
                "address_line2": "PH-1, SHYAM VIHAR, Najafgarh",
                "city": "New Delhi",
                "district": "West Delhi",
                "state": "Delhi",
                "pincode": "110043",
                "gstin": "07ABDCA6170C1Z0",
                "state_code": "07"
            },
            ship_to={
                "name": "ILMS.AI",
                "address_line1": "PLOT 36-A KH NO 181, DINDAPUR EXT",
                "address_line2": "PH-1, SHYAM VIHAR, Najafgarh",
                "city": "New Delhi",
                "district": "West Delhi",
                "state": "Delhi",
                "pincode": "110043",
                "gstin": "07ABDCA6170C1Z0",
                "state_code": "07"
            },
            subtotal=Decimal("5352900"),
            taxable_amount=Decimal("5352900"),
            igst_amount=Decimal("963522"),
            total_tax=Decimal("963522"),
            grand_total=Decimal("6316422"),
            received_by=user.id,
            vendor_remarks="E.& O.E.\n1. Goods once sold will not be taken back.\n2. Interest @ 18% p.a. will be charged if the payment is not made with in the stipulated time.\n3. Subject to Ghaziabad'Uttar Pradesh' Jurisdiction only."
        )
        db.add(pi)
        await db.flush()

        # Items from STOS PI
        items_data = [
            ("AFGPSW2001", "Sediment Woven Filter Assy (Grey)", "84212190", 3000, 97.00),
            ("AFGPPR2002", "Pre Carbon Filter Assy (Grey)", "84212190", 3000, 114.00),
            ("AFGPMH2003", "Membrane Filter Assy (Grey)", "84212190", 3000, 398.00),
            ("AFGALK2004", "Alkaline Mineral Filter Assy (Grey)", "84212190", 2000, 61.00),
            ("AFGRSS2501", "Sediment Spun Filter Assy (White)", "84212190", 3000, 76.00),
            ("AFGRPR2502", "Pre Carbon Filter Assy (White)", "84212190", 3000, 111.00),
            ("AFGRMF2503", "Membrane Filter Assy (White)", "84212190", 2000, 375.00),
            ("AFGRPC2504", "Post Carbon Copper Assy (White)", "84212190", 2000, 58.00),
            ("AFGPPF2005", "Pre Filter Assembly (Grey) - Premium", "84212190", 2000, 245.00),
            ("AFGRPF2505", "Pre Filter Assembly (Black) - Regular", "84212190", 1500, 225.00),
            ("AFGIRN2006", "Iron Remover & Sediment Pre-Filter Jumbo", "84212190", 700, 790.00),
            ("AFGHMR2007", "HMR & Sediment Pre-Filter Jumbo Assembly", "84212190", 400, 801.00),
            ("AFGPRV3001", "Plastic PRV", "84212190", 700, 180.00),
            ("AFGBDV3002", "Brass Diverter Valve", "84212190", 1000, 150.00),
        ]

        for idx, (part_code, desc, hsn, qty, price) in enumerate(items_data, 1):
            taxable = Decimal(str(qty * price))
            item = VendorProformaItem(
                proforma_id=pi.id,
                part_code=part_code,
                description=desc,
                hsn_code=hsn,
                uom="Pieces",
                quantity=Decimal(str(qty)),
                unit_price=Decimal(str(price)),
                taxable_amount=taxable,
                gst_rate=Decimal("18"),
                igst_amount=taxable * Decimal("0.18"),
                total_amount=taxable * Decimal("1.18")
            )
            db.add(item)

        await db.commit()
        print(f"✓ Created Proforma Invoice: {pi.proforma_number}")
        return pi.our_reference


async def generate_proforma_pdf(reference: str = None):
    """Generate PDF for Vendor Proforma Invoice in STOS format."""
    async with async_session_factory() as db:
        # Get PI with items
        query = select(VendorProformaInvoice).options(
            selectinload(VendorProformaInvoice.items),
            selectinload(VendorProformaInvoice.vendor)
        )

        if reference:
            query = query.where(
                (VendorProformaInvoice.our_reference == reference) |
                (VendorProformaInvoice.proforma_number == reference)
            )
        else:
            query = query.where(VendorProformaInvoice.proforma_number == "STOS-001/25-26")

        result = await db.execute(query)
        pi = result.scalars().first()

        if not pi:
            print(f"Proforma Invoice not found!")
            # Try to create it
            ref = await create_stos_proforma()
            if ref:
                return await generate_proforma_pdf(ref)
            return

        print(f"Generating Proforma Invoice PDF for: {pi.proforma_number}")
        print(f"Vendor: {pi.vendor.name if pi.vendor else 'Unknown'}")
        print(f"Items: {len(pi.items)}")

        # Vendor details
        vendor = pi.vendor
        vendor_info = {
            "name": vendor.name if vendor else "STOS INDUSTRIAL CORPORATION PRIVATE LIMITED",
            "formerly": "(Formerly \"Oxytek Components Pvt. Ltd.\")",
            "address": "E-180, SECTOR 17, KAVI NAGAR INDUSTRIAL AREA, GHAZIABAD, UTTAR PRADESH",
            "gstin": vendor.gstin if vendor else "09AACCO4091J1Z6",
            "state": "UTTAR PRADESH",
            "state_code": "09",
            "pan": "AACCO4091J",
            "cin": "U27100DL2016PTC308891",
            "bank_name": "ICICI BANK",
            "bank_branch": "GHAZIABAD - CHOUDHARY MORE",
            "account_no": "125605002916",
            "ifsc": "ICIC0001256"
        }

        # Bill To (buyer)
        bill_to = pi.bill_to or {
            "name": "ILMS.AI",
            "address_line1": "PLOT 36-A KH NO 181, DINDAPUR EXT",
            "address_line2": "PH-1, SHYAM VIHAR, Najafgarh",
            "city": "New Delhi",
            "district": "West Delhi",
            "state": "Delhi",
            "pincode": "110043",
            "gstin": "07ABDCA6170C1Z0",
            "state_code": "07"
        }

        # Ship To (defaults to bill_to)
        ship_to = pi.ship_to or bill_to

        # Sort items
        items = list(pi.items)

        # Generate HTML
        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Proforma Invoice - {pi.proforma_number}</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: Arial, sans-serif; font-size: 11px; padding: 15px; }}
        .header {{ display: flex; justify-content: space-between; margin-bottom: 10px; }}
        .header-left {{ font-size: 10px; }}
        .header-right {{ text-align: right; font-size: 10px; }}
        .title {{ text-align: center; margin: 15px 0; }}
        .title h1 {{ font-size: 20px; font-weight: bold; color: #000; margin-bottom: 3px; }}
        .title .formerly {{ font-size: 11px; font-style: italic; }}
        .title .address {{ font-size: 10px; color: #333; margin-top: 5px; }}
        .doc-type {{ text-align: center; background: #e0e0e0; padding: 5px; font-weight: bold; margin-bottom: 15px; font-size: 12px; }}
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
        th {{ background: #f0f0f0; font-weight: bold; }}
        td.left {{ text-align: left; }}
        td.right {{ text-align: right; }}
        .amount-row {{ background: #f9f9f9; }}
        .grand-total {{ font-weight: bold; font-size: 12px; }}
        .bank-details {{ border: 1px solid #000; padding: 10px; margin-bottom: 10px; }}
        .terms {{ font-size: 10px; margin-top: 10px; }}
        .signature {{ text-align: right; margin-top: 20px; }}
        .amount-words {{ background: #ffffcc; padding: 8px; border: 1px solid #000; margin: 10px 0; font-size: 11px; }}
        .print-btn {{ position: fixed; top: 10px; right: 10px; padding: 10px 20px; background: #28a745; color: white; border: none; cursor: pointer; font-size: 14px; border-radius: 5px; z-index: 1000; }}
        .print-btn:hover {{ background: #218838; }}
        @media print {{
            .print-btn {{ display: none; }}
            body {{ padding: 0; }}
        }}
    </style>
</head>
<body>
    <button class="print-btn" onclick="window.print()">Print / Save as PDF</button>

    <!-- Header with Vendor (Seller) Details -->
    <div class="header">
        <div class="header-left">
            <div>GSTIN : {vendor_info['gstin']}</div>
            <div>STATE : {vendor_info['state']}</div>
            <div>STATE CODE : {vendor_info['state_code']}</div>
            <div>PAN NO. : {vendor_info['pan']}</div>
        </div>
        <div class="header-right">
            <div>{vendor_info['cin']}</div>
            <div style="margin-top: 10px;"><strong>Original Copy</strong></div>
        </div>
    </div>

    <!-- Document Type -->
    <div class="doc-type">PROFORMA INVOICE</div>

    <!-- Vendor Company Name -->
    <div class="title">
        <h1>{vendor_info['name'].upper()}</h1>
        <div class="formerly">{vendor_info['formerly']}</div>
        <div class="address">{vendor_info['address']}</div>
    </div>

    <!-- PI Details -->
    <div class="info-row">
        <div class="info-box">
            <div><strong>P. Invoice No. :</strong> {pi.proforma_number}</div>
            <div><strong>Reverse Charges :</strong> NO</div>
        </div>
        <div class="info-box right">
            <div><strong>Dated :</strong> {pi.proforma_date.strftime('%d-%m-%Y')}</div>
            <div><strong>E WAY BILL NO. :</strong> N.A.</div>
        </div>
    </div>

    <!-- Bill To & Ship To (Side by Side) -->
    <div class="party-box">
        <div class="party-header">
            <div class="party-header-col">Details Of Receiver | Billed To:</div>
            <div class="party-header-col right">Details Of Consignee | Shipped To:</div>
        </div>
        <div class="party-row">
            <div class="party-col">
                <strong>{bill_to.get('name', 'ILMS.AI')}</strong><br>
                {bill_to.get('address_line1', '')}<br>
                {bill_to.get('address_line2', '')}<br>
                {bill_to.get('city', '')}, {bill_to.get('district', bill_to.get('city', ''))}, {bill_to.get('state', '')}, {bill_to.get('pincode', '')}<br>
                <br>
                State Code : {bill_to.get('state_code', '07')}<br>
                GSTIN : {bill_to.get('gstin', 'N/A')}<br>
                {f"Phone : {bill_to.get('phone')}" if bill_to.get('phone') else ""}
                {f"<br>Email : {bill_to.get('email')}" if bill_to.get('email') else ""}
            </div>
            <div class="party-col right">
                <strong>{ship_to.get('name', 'ILMS.AI')}</strong><br>
                {ship_to.get('address_line1', '')}<br>
                {ship_to.get('address_line2', '')}<br>
                {ship_to.get('city', '')}, {ship_to.get('district', ship_to.get('city', ''))}, {ship_to.get('state', '')}, {ship_to.get('pincode', '')}<br>
                <br>
                State Code : {ship_to.get('state_code', '07')}<br>
                GSTIN : {ship_to.get('gstin', 'N/A')}<br>
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
                <th style="width: 85px;">PART CODE</th>
                <th style="width: 70px;">HSN/SAC<br>Code</th>
                <th style="width: 65px;">Qty.</th>
                <th style="width: 50px;">Unit</th>
                <th style="width: 70px;">Price</th>
                <th style="width: 95px;">Amount(`)</th>
            </tr>
        </thead>
        <tbody>"""

        # Items
        total_qty = Decimal("0")
        for idx, item in enumerate(items, 1):
            total_qty += item.quantity
            html += f"""
            <tr>
                <td>{idx}.</td>
                <td class="left">{item.description}</td>
                <td>{item.part_code or '-'}</td>
                <td>{item.hsn_code or '84212190'}</td>
                <td>{float(item.quantity):,.2f}</td>
                <td>{item.uom}</td>
                <td class="right">{float(item.unit_price):,.2f}</td>
                <td class="right">{float(item.taxable_amount):,.2f}</td>
            </tr>"""

        # Total row
        html += f"""
            <tr class="amount-row">
                <td colspan="4" class="right"><strong>Total</strong></td>
                <td><strong>{float(total_qty):,.3f}</strong></td>
                <td>Pieces</td>
                <td class="right" colspan="2"><strong>Total {float(pi.subtotal):,.2f}</strong></td>
            </tr>
            <tr class="amount-row">
                <td colspan="6" class="right">Totals c/o</td>
                <td colspan="2" class="right">{float(pi.subtotal):,.2f}</td>
            </tr>"""

        # Tax - IGST for inter-state (UP to Delhi)
        if pi.igst_amount and pi.igst_amount > 0:
            html += f"""
            <tr class="amount-row">
                <td colspan="6" class="right">Add : IGST @ 18.00 %</td>
                <td colspan="2" class="right">{float(pi.igst_amount):,.2f}</td>
            </tr>"""
        else:
            if pi.cgst_amount and pi.cgst_amount > 0:
                html += f"""
            <tr class="amount-row">
                <td colspan="6" class="right">Add : CGST @ 9.00 %</td>
                <td colspan="2" class="right">{float(pi.cgst_amount):,.2f}</td>
            </tr>"""
            if pi.sgst_amount and pi.sgst_amount > 0:
                html += f"""
            <tr class="amount-row">
                <td colspan="6" class="right">Add : SGST @ 9.00 %</td>
                <td colspan="2" class="right">{float(pi.sgst_amount):,.2f}</td>
            </tr>"""

        html += f"""
            <tr class="grand-total">
                <td colspan="6" class="right">Grand Total `</td>
                <td colspan="2" class="right">{float(pi.grand_total):,.2f}</td>
            </tr>
        </tbody>
    </table>

    <!-- Sale Type -->
    <div style="margin: 5px 0; font-size: 10px;">Sale</div>

    <!-- Amount in Words -->
    <div class="amount-words">
        <strong>Amount in Words:</strong> {amount_to_words(float(pi.grand_total))}
    </div>

    <!-- Bank Details -->
    <div class="bank-details">
        <div><strong>{vendor_info['name'].upper()}</strong></div>
        <table style="border: none; margin-top: 5px;">
            <tr style="border: none;">
                <td style="border: none; width: 80px;">Bank Name</td>
                <td style="border: none;">: {vendor_info['bank_name']}</td>
                <td style="border: none; width: 60px;">Branch</td>
                <td style="border: none;">: {vendor_info['bank_branch']}</td>
            </tr>
            <tr style="border: none;">
                <td style="border: none;">A/c No.</td>
                <td style="border: none;">: {vendor_info['account_no']}</td>
                <td style="border: none;">IFS Code</td>
                <td style="border: none;">: {vendor_info['ifsc']}</td>
            </tr>
        </table>
    </div>

    <!-- Terms & Conditions -->
    <div class="terms">
        <div><strong>Terms & Conditions</strong></div>
        <div>E.& O.E.</div>
        <ol style="margin-left: 15px; margin-top: 5px;">
            <li>Goods once sold will not be taken back.</li>
            <li>Interest @ 18% p.a. will be charged if the payment is not made with in the stipulated time.</li>
            <li>Subject to Ghaziabad'Uttar Pradesh' Jurisdiction only.</li>
            <li>ADVANCE PAYMENT AGAINST PERFORMA INVOICE.</li>
            <li>FREIGHT EXTRA AS PER ACTUAL</li>
        </ol>
    </div>

    <!-- Signature -->
    <div class="signature">
        <div>for <strong>{vendor_info['name'].upper()}</strong></div>
        <div style="margin-top: 50px;">Authorised Signatory</div>
    </div>

</body>
</html>"""

        # Save HTML
        filename = f"/tmp/PI-{pi.proforma_number.replace('/', '-')}.html"
        with open(filename, 'w') as f:
            f.write(html)

        print(f"\n✓ Proforma Invoice PDF generated: {filename}")
        print("Opening in browser...")

        # Open in browser
        subprocess.run(['open', filename])


if __name__ == "__main__":
    reference = sys.argv[1] if len(sys.argv) > 1 else None
    asyncio.run(generate_proforma_pdf(reference))
