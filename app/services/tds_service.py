"""
TDS (Tax Deducted at Source) Certificate Generation Service

Handles TDS compliance for India including:
- TDS deduction tracking on payments
- Form 16A certificate generation (non-salary)
- Form 16 certificate generation (salary)
- Quarterly TDS return preparation (26Q, 24Q)
- TDS remittance tracking

TDS Sections covered:
- 194A: Interest (10%)
- 194C: Contractor payments (1%/2%)
- 194H: Commission/Brokerage (5%)
- 194I: Rent (10%)
- 194J: Professional/Technical fees (10%)
- 192: Salary
"""

from datetime import datetime, date, timezone
from decimal import Decimal
from typing import Optional, Dict, Any, List
from uuid import UUID
from enum import Enum
import io

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload


class TDSSection(str, Enum):
    """TDS sections under Income Tax Act."""
    SEC_192 = "192"      # Salary
    SEC_194A = "194A"    # Interest
    SEC_194C = "194C"    # Contractor
    SEC_194H = "194H"    # Commission
    SEC_194I = "194I"    # Rent
    SEC_194J = "194J"    # Professional fees
    SEC_194Q = "194Q"    # Purchase of goods
    SEC_195 = "195"      # Non-resident


class TDSRate(str, Enum):
    """Standard TDS rates."""
    SALARY = "Slab"
    INTEREST_10 = "10"
    CONTRACTOR_IND_1 = "1"
    CONTRACTOR_COMP_2 = "2"
    COMMISSION_5 = "5"
    RENT_10 = "10"
    PROFESSIONAL_10 = "10"
    PURCHASE_0_1 = "0.1"
    NON_RESIDENT_20 = "20"


# TDS section details
TDS_SECTIONS = {
    "192": {"name": "Salary", "rate": "Slab", "threshold": 250000},
    "194A": {"name": "Interest other than securities", "rate": 10, "threshold": 40000},
    "194C": {"name": "Payment to Contractors", "rate": {"individual": 1, "company": 2}, "threshold": 30000},
    "194H": {"name": "Commission or Brokerage", "rate": 5, "threshold": 15000},
    "194I": {"name": "Rent", "rate": 10, "threshold": 240000},
    "194J": {"name": "Professional/Technical fees", "rate": 10, "threshold": 30000},
    "194Q": {"name": "Purchase of goods", "rate": 0.1, "threshold": 5000000},
    "195": {"name": "Payment to Non-resident", "rate": 20, "threshold": 0},
}


class TDSError(Exception):
    """Custom exception for TDS errors."""
    def __init__(self, message: str, details: Dict = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class TDSService:
    """
    Service for TDS tracking, calculation, and certificate generation.
    """

    def __init__(self, db: AsyncSession, company_id: UUID):
        self.db = db
        self.company_id = company_id

    def calculate_tds(
        self,
        amount: Decimal,
        section: str,
        is_company: bool = False,
        pan_available: bool = True,
        lower_deduction_cert: bool = False,
        lower_rate: Decimal = None
    ) -> Dict:
        """
        Calculate TDS amount based on section and amount.

        Args:
            amount: Payment amount
            section: TDS section code
            is_company: Whether deductee is a company
            pan_available: Whether PAN is available
            lower_deduction_cert: Whether lower deduction certificate exists
            lower_rate: Rate from lower deduction certificate
        """
        section_info = TDS_SECTIONS.get(section)
        if not section_info:
            raise TDSError(f"Invalid TDS section: {section}")

        # Check threshold
        threshold = section_info.get("threshold", 0)
        if amount < threshold:
            return {
                "tds_amount": Decimal("0"),
                "rate": 0,
                "section": section,
                "reason": f"Below threshold of Rs. {threshold}"
            }

        # Determine rate
        rate = section_info["rate"]
        if isinstance(rate, dict):
            rate = rate.get("company" if is_company else "individual", rate.get("individual", 0))

        if rate == "Slab":
            # Salary - needs separate calculation
            return {
                "tds_amount": Decimal("0"),
                "rate": "Slab",
                "section": section,
                "reason": "Salary TDS requires separate calculation"
            }

        # Convert rate to decimal
        rate = Decimal(str(rate))

        # Apply lower deduction certificate rate if applicable
        if lower_deduction_cert and lower_rate is not None:
            rate = lower_rate

        # Higher rate if PAN not available (20% or double, whichever is higher)
        if not pan_available:
            rate = max(rate * 2, Decimal("20"))

        # Calculate TDS
        tds_amount = (amount * rate) / Decimal("100")

        return {
            "tds_amount": tds_amount.quantize(Decimal("0.01")),
            "rate": float(rate),
            "section": section,
            "section_name": section_info["name"],
            "threshold": threshold,
            "pan_available": pan_available,
            "higher_rate_applied": not pan_available
        }

    async def record_tds_deduction(
        self,
        deductee_id: UUID,
        deductee_type: str,  # VENDOR, EMPLOYEE, CUSTOMER
        deductee_name: str,
        deductee_pan: str,
        section: str,
        payment_amount: Decimal,
        tds_amount: Decimal,
        tds_rate: Decimal,
        payment_date: date,
        payment_reference: str = None,
        challan_number: str = None,
        challan_date: date = None,
        user_id: UUID = None
    ) -> Dict:
        """
        Record a TDS deduction.

        Returns the created TDS deduction record.
        """
        from app.models.tds import TDSDeduction

        # Get financial year and quarter
        fy_start = date(payment_date.year if payment_date.month >= 4 else payment_date.year - 1, 4, 1)
        fy_end = date(fy_start.year + 1, 3, 31)
        financial_year = f"{fy_start.year}-{fy_end.year % 100:02d}"

        # Determine quarter
        month = payment_date.month
        if month in [4, 5, 6]:
            quarter = "Q1"
        elif month in [7, 8, 9]:
            quarter = "Q2"
        elif month in [10, 11, 12]:
            quarter = "Q3"
        else:
            quarter = "Q4"

        deduction = TDSDeduction(
            company_id=self.company_id,
            deductee_id=deductee_id,
            deductee_type=deductee_type,
            deductee_name=deductee_name,
            deductee_pan=deductee_pan,
            section=section,
            payment_amount=payment_amount,
            tds_amount=tds_amount,
            tds_rate=tds_rate,
            payment_date=payment_date,
            payment_reference=payment_reference,
            financial_year=financial_year,
            quarter=quarter,
            challan_number=challan_number,
            challan_date=challan_date,
            is_deposited=bool(challan_number),
            created_by=user_id,
        )

        self.db.add(deduction)
        await self.db.commit()
        await self.db.refresh(deduction)

        return {
            "id": str(deduction.id),
            "deductee_name": deductee_name,
            "section": section,
            "payment_amount": float(payment_amount),
            "tds_amount": float(tds_amount),
            "financial_year": financial_year,
            "quarter": quarter
        }

    async def get_tds_summary(
        self,
        financial_year: str,
        quarter: str = None,
        section: str = None
    ) -> Dict:
        """
        Get TDS summary for a period.

        Returns totals by section and deductee.
        """
        from app.models.tds import TDSDeduction

        query = select(TDSDeduction).where(
            and_(
                TDSDeduction.company_id == self.company_id,
                TDSDeduction.financial_year == financial_year
            )
        )

        if quarter:
            query = query.where(TDSDeduction.quarter == quarter)
        if section:
            query = query.where(TDSDeduction.section == section)

        result = await self.db.execute(query)
        deductions = result.scalars().all()

        # Group by section
        by_section = {}
        for ded in deductions:
            if ded.section not in by_section:
                by_section[ded.section] = {
                    "section": ded.section,
                    "section_name": TDS_SECTIONS.get(ded.section, {}).get("name", "Unknown"),
                    "total_payment": Decimal("0"),
                    "total_tds": Decimal("0"),
                    "count": 0,
                    "deposited": Decimal("0"),
                    "pending": Decimal("0")
                }
            by_section[ded.section]["total_payment"] += ded.payment_amount
            by_section[ded.section]["total_tds"] += ded.tds_amount
            by_section[ded.section]["count"] += 1
            if ded.is_deposited:
                by_section[ded.section]["deposited"] += ded.tds_amount
            else:
                by_section[ded.section]["pending"] += ded.tds_amount

        return {
            "financial_year": financial_year,
            "quarter": quarter,
            "by_section": [
                {**s, "total_payment": float(s["total_payment"]),
                 "total_tds": float(s["total_tds"]),
                 "deposited": float(s["deposited"]),
                 "pending": float(s["pending"])}
                for s in by_section.values()
            ],
            "grand_total_payment": float(sum(s["total_payment"] for s in by_section.values())),
            "grand_total_tds": float(sum(s["total_tds"] for s in by_section.values())),
            "total_deposited": float(sum(s["deposited"] for s in by_section.values())),
            "total_pending": float(sum(s["pending"] for s in by_section.values()))
        }

    async def generate_form_16a(
        self,
        deductee_pan: str,
        financial_year: str,
        quarter: str
    ) -> Dict:
        """
        Generate Form 16A certificate for a deductee.

        Form 16A is the TDS certificate for non-salary payments.
        """
        from app.models.tds import TDSDeduction
        from app.models.company import Company

        # Get company details
        company_result = await self.db.execute(
            select(Company).where(Company.id == self.company_id)
        )
        company = company_result.scalar_one_or_none()

        if not company:
            raise TDSError("Company not found")

        # Get all deductions for this deductee in the period
        query = select(TDSDeduction).where(
            and_(
                TDSDeduction.company_id == self.company_id,
                TDSDeduction.deductee_pan == deductee_pan,
                TDSDeduction.financial_year == financial_year,
                TDSDeduction.quarter == quarter
            )
        ).order_by(TDSDeduction.payment_date)

        result = await self.db.execute(query)
        deductions = list(result.scalars().all())

        if not deductions:
            raise TDSError("No TDS deductions found for this deductee in the specified period")

        # Calculate totals
        total_payment = sum(d.payment_amount for d in deductions)
        total_tds = sum(d.tds_amount for d in deductions)

        # Get unique deductee details from first record
        deductee_name = deductions[0].deductee_name

        # Determine quarter dates
        fy_start_year = int(financial_year.split("-")[0])
        quarter_dates = {
            "Q1": (date(fy_start_year, 4, 1), date(fy_start_year, 6, 30)),
            "Q2": (date(fy_start_year, 7, 1), date(fy_start_year, 9, 30)),
            "Q3": (date(fy_start_year, 10, 1), date(fy_start_year, 12, 31)),
            "Q4": (date(fy_start_year + 1, 1, 1), date(fy_start_year + 1, 3, 31)),
        }
        period_from, period_to = quarter_dates.get(quarter, (None, None))

        certificate_data = {
            "certificate_number": f"FORM16A/{financial_year}/{quarter}/{deductee_pan[-4:]}",
            "form_type": "16A",

            # Deductor (Company) Details
            "deductor": {
                "name": company.name,
                "tan": company.tan,
                "pan": company.pan,
                "address": company.address,
                "city": company.city,
                "state": company.state,
                "pincode": company.pincode,
            },

            # Deductee Details
            "deductee": {
                "name": deductee_name,
                "pan": deductee_pan,
            },

            # Period
            "financial_year": financial_year,
            "quarter": quarter,
            "period_from": str(period_from) if period_from else None,
            "period_to": str(period_to) if period_to else None,

            # Summary
            "total_payment": float(total_payment),
            "total_tds_deducted": float(total_tds),

            # Details by section
            "section_wise": {},

            # Transaction details
            "transactions": [],

            # Challan details (for deposited TDS)
            "challans": [],

            # Certificate date
            "certificate_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        }

        # Group by section
        for ded in deductions:
            if ded.section not in certificate_data["section_wise"]:
                certificate_data["section_wise"][ded.section] = {
                    "section": ded.section,
                    "section_name": TDS_SECTIONS.get(ded.section, {}).get("name", ""),
                    "total_payment": Decimal("0"),
                    "total_tds": Decimal("0"),
                }
            certificate_data["section_wise"][ded.section]["total_payment"] += ded.payment_amount
            certificate_data["section_wise"][ded.section]["total_tds"] += ded.tds_amount

            # Add transaction
            certificate_data["transactions"].append({
                "date": str(ded.payment_date),
                "section": ded.section,
                "amount": float(ded.payment_amount),
                "tds": float(ded.tds_amount),
                "rate": float(ded.tds_rate),
                "reference": ded.payment_reference,
            })

            # Add challan if deposited
            if ded.challan_number and ded.challan_number not in [c["challan_number"] for c in certificate_data["challans"]]:
                certificate_data["challans"].append({
                    "challan_number": ded.challan_number,
                    "challan_date": str(ded.challan_date) if ded.challan_date else None,
                    "bsr_code": ded.bsr_code if hasattr(ded, 'bsr_code') else None,
                })

        # Convert section_wise decimals to float
        for section in certificate_data["section_wise"].values():
            section["total_payment"] = float(section["total_payment"])
            section["total_tds"] = float(section["total_tds"])

        certificate_data["section_wise"] = list(certificate_data["section_wise"].values())

        return certificate_data

    async def generate_form_16a_pdf(
        self,
        deductee_pan: str,
        financial_year: str,
        quarter: str
    ) -> bytes:
        """
        Generate Form 16A as PDF.

        Returns PDF bytes.
        """
        cert_data = await self.generate_form_16a(deductee_pan, financial_year, quarter)

        # Generate HTML
        html_content = self._generate_form_16a_html(cert_data)

        # For now, return HTML as bytes (PDF generation would need weasyprint or similar)
        return html_content.encode('utf-8')

    def _generate_form_16a_html(self, cert_data: Dict) -> str:
        """Generate HTML for Form 16A certificate."""
        transactions_html = ""
        for i, txn in enumerate(cert_data["transactions"], 1):
            transactions_html += f"""
            <tr>
                <td style="text-align: center;">{i}</td>
                <td style="text-align: center;">{txn['date']}</td>
                <td style="text-align: center;">{txn['section']}</td>
                <td style="text-align: right;">{txn['amount']:,.2f}</td>
                <td style="text-align: center;">{txn['rate']}%</td>
                <td style="text-align: right;">{txn['tds']:,.2f}</td>
            </tr>
            """

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Form 16A - TDS Certificate</title>
            <style>
                body {{ font-family: Arial, sans-serif; font-size: 12px; margin: 20px; }}
                .header {{ text-align: center; margin-bottom: 20px; }}
                .header h1 {{ margin: 5px 0; font-size: 18px; }}
                .header h2 {{ margin: 5px 0; font-size: 14px; font-weight: normal; }}
                .section {{ margin: 15px 0; }}
                .section-title {{ font-weight: bold; margin-bottom: 10px; background: #f0f0f0; padding: 5px; }}
                .details-table {{ width: 100%; border-collapse: collapse; }}
                .details-table td {{ padding: 5px; vertical-align: top; }}
                .data-table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
                .data-table th, .data-table td {{ border: 1px solid #000; padding: 5px; }}
                .data-table th {{ background: #f0f0f0; }}
                .totals {{ margin-top: 20px; }}
                .footer {{ margin-top: 30px; text-align: center; }}
                .signature {{ margin-top: 50px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>FORM NO. 16A</h1>
                <h2>Certificate under section 203 of the Income-tax Act, 1961</h2>
                <h2>for Tax Deducted at Source on payments other than Salary</h2>
            </div>

            <div class="section">
                <div class="section-title">Certificate No: {cert_data['certificate_number']}</div>
            </div>

            <div class="section">
                <div class="section-title">PART A - Details of Deductor</div>
                <table class="details-table">
                    <tr>
                        <td width="30%">Name of Deductor:</td>
                        <td><strong>{cert_data['deductor']['name']}</strong></td>
                    </tr>
                    <tr>
                        <td>TAN:</td>
                        <td><strong>{cert_data['deductor']['tan'] or 'N/A'}</strong></td>
                    </tr>
                    <tr>
                        <td>PAN:</td>
                        <td><strong>{cert_data['deductor']['pan'] or 'N/A'}</strong></td>
                    </tr>
                    <tr>
                        <td>Address:</td>
                        <td>{cert_data['deductor']['address'] or ''}, {cert_data['deductor']['city'] or ''},
                            {cert_data['deductor']['state'] or ''} - {cert_data['deductor']['pincode'] or ''}</td>
                    </tr>
                </table>
            </div>

            <div class="section">
                <div class="section-title">PART B - Details of Deductee</div>
                <table class="details-table">
                    <tr>
                        <td width="30%">Name of Deductee:</td>
                        <td><strong>{cert_data['deductee']['name']}</strong></td>
                    </tr>
                    <tr>
                        <td>PAN of Deductee:</td>
                        <td><strong>{cert_data['deductee']['pan']}</strong></td>
                    </tr>
                </table>
            </div>

            <div class="section">
                <div class="section-title">Period: {cert_data['quarter']} of Financial Year {cert_data['financial_year']}</div>
                <p>From: {cert_data['period_from']} To: {cert_data['period_to']}</p>
            </div>

            <div class="section">
                <div class="section-title">PART C - Details of Tax Deducted and Deposited</div>
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>Sr.</th>
                            <th>Date of Payment</th>
                            <th>Section</th>
                            <th>Amount Paid (Rs.)</th>
                            <th>TDS Rate</th>
                            <th>TDS Deducted (Rs.)</th>
                        </tr>
                    </thead>
                    <tbody>
                        {transactions_html}
                    </tbody>
                    <tfoot>
                        <tr>
                            <th colspan="3" style="text-align: right;">TOTAL</th>
                            <th style="text-align: right;">{cert_data['total_payment']:,.2f}</th>
                            <th></th>
                            <th style="text-align: right;">{cert_data['total_tds_deducted']:,.2f}</th>
                        </tr>
                    </tfoot>
                </table>
            </div>

            <div class="section totals">
                <p><strong>Total Amount Paid/Credited:</strong> Rs. {cert_data['total_payment']:,.2f}</p>
                <p><strong>Total Tax Deducted at Source:</strong> Rs. {cert_data['total_tds_deducted']:,.2f}</p>
            </div>

            <div class="footer">
                <p>I, the undersigned, hereby certify that a sum of Rs. {cert_data['total_tds_deducted']:,.2f}
                   has been deducted at source and paid to the credit of the Central Government.</p>

                <div class="signature">
                    <p>Date: {cert_data['certificate_date']}</p>
                    <br/><br/>
                    <p>_______________________________</p>
                    <p>Signature of the person responsible for deduction of tax</p>
                    <p>Name: {cert_data['deductor']['name']}</p>
                    <p>Designation: Authorized Signatory</p>
                </div>
            </div>
        </body>
        </html>
        """
        return html

    async def get_pending_deposits(self, financial_year: str = None) -> List[Dict]:
        """Get TDS deductions pending deposit to government."""
        from app.models.tds import TDSDeduction

        query = select(TDSDeduction).where(
            and_(
                TDSDeduction.company_id == self.company_id,
                TDSDeduction.is_deposited == False
            )
        )

        if financial_year:
            query = query.where(TDSDeduction.financial_year == financial_year)

        query = query.order_by(TDSDeduction.payment_date)

        result = await self.db.execute(query)
        deductions = result.scalars().all()

        return [
            {
                "id": str(d.id),
                "deductee_name": d.deductee_name,
                "deductee_pan": d.deductee_pan,
                "section": d.section,
                "payment_date": str(d.payment_date),
                "payment_amount": float(d.payment_amount),
                "tds_amount": float(d.tds_amount),
                "financial_year": d.financial_year,
                "quarter": d.quarter,
            }
            for d in deductions
        ]

    async def mark_as_deposited(
        self,
        deduction_ids: List[UUID],
        challan_number: str,
        challan_date: date,
        bsr_code: str = None
    ) -> Dict:
        """Mark TDS deductions as deposited with challan details."""
        from app.models.tds import TDSDeduction

        result = await self.db.execute(
            select(TDSDeduction).where(TDSDeduction.id.in_(deduction_ids))
        )
        deductions = list(result.scalars().all())

        total_deposited = Decimal("0")
        for ded in deductions:
            ded.is_deposited = True
            ded.challan_number = challan_number
            ded.challan_date = challan_date
            if bsr_code:
                ded.bsr_code = bsr_code
            total_deposited += ded.tds_amount

        await self.db.commit()

        return {
            "success": True,
            "deductions_updated": len(deductions),
            "total_deposited": float(total_deposited),
            "challan_number": challan_number,
            "challan_date": str(challan_date)
        }
