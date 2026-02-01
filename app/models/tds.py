"""TDS (Tax Deducted at Source) Models."""
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import (
    Column, String, Numeric, Date, DateTime, Boolean,
    ForeignKey, Text, Index
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship

from app.database import Base


class TDSSection(str, Enum):
    """TDS Sections under Income Tax Act."""
    SEC_194A = "194A"  # Interest other than interest on securities (10%)
    SEC_194C = "194C"  # Payment to contractors (1%/2%)
    SEC_194H = "194H"  # Commission/Brokerage (5%)
    SEC_194I = "194I"  # Rent (10%)
    SEC_194IA = "194IA"  # Property purchase (1%)
    SEC_194J = "194J"  # Professional/Technical fees (10%)
    SEC_194Q = "194Q"  # Purchase of goods (0.1%)
    SEC_195 = "195"    # Payment to NRI (varies)
    SEC_192 = "192"    # Salary (slab rate)
    SEC_194B = "194B"  # Lottery/Game winnings (30%)
    SEC_194D = "194D"  # Insurance commission (5%)
    SEC_194E = "194E"  # Payment to non-resident sportsmen (20%)
    SEC_194G = "194G"  # Commission on lottery tickets (5%)
    SEC_194K = "194K"  # Payment of dividend (10%)
    SEC_194LA = "194LA"  # Compensation on land acquisition (10%)
    SEC_194LB = "194LB"  # Income from infrastructure bonds (5%)
    SEC_194N = "194N"  # Cash withdrawal (2%)
    SEC_194O = "194O"  # E-commerce (1%)


class TDSDeductionStatus(str, Enum):
    """Status of TDS deduction."""
    PENDING = "PENDING"          # Deducted, not deposited
    DEPOSITED = "DEPOSITED"      # Deposited to government
    CERTIFICATE_ISSUED = "CERTIFICATE_ISSUED"  # Form 16A issued


class TDSDeduction(Base):
    """TDS Deduction Record."""
    __tablename__ = "tds_deductions"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    company_id = Column(PGUUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)

    # Deductee Information
    deductee_id = Column(PGUUID(as_uuid=True), nullable=True)  # Vendor/Customer ID
    deductee_type = Column(String(50), nullable=False)  # VENDOR, CUSTOMER, EMPLOYEE
    deductee_name = Column(String(255), nullable=False)
    deductee_pan = Column(String(10), nullable=False)
    deductee_address = Column(Text, nullable=True)

    # Deduction Details
    section = Column(
        String(20),
        nullable=False,
        comment="194A, 194C, 194H, 194I, 194IA, 194J, 194Q, 195, 192, 194B, 194D, 194E, 194G, 194K, 194LA, 194LB, 194N, 194O"
    )
    deduction_date = Column(Date, nullable=False)
    financial_year = Column(String(9), nullable=False)  # 2024-25
    quarter = Column(String(2), nullable=False)  # Q1, Q2, Q3, Q4

    # Amount Details
    gross_amount = Column(Numeric(15, 2), nullable=False)
    tds_rate = Column(Numeric(5, 2), nullable=False)
    tds_amount = Column(Numeric(15, 2), nullable=False)
    surcharge = Column(Numeric(15, 2), default=0)
    education_cess = Column(Numeric(15, 2), default=0)
    total_tds = Column(Numeric(15, 2), nullable=False)

    # Lower/Nil Deduction Certificate
    lower_deduction_cert_no = Column(String(50), nullable=True)
    lower_deduction_rate = Column(Numeric(5, 2), nullable=True)

    # Reference
    reference_type = Column(String(50), nullable=True)  # INVOICE, PAYMENT, BILL
    reference_id = Column(PGUUID(as_uuid=True), nullable=True)
    reference_number = Column(String(100), nullable=True)
    narration = Column(Text, nullable=True)

    # Deposit Details
    status = Column(
        String(50),
        default="PENDING",
        comment="PENDING, DEPOSITED, CERTIFICATE_ISSUED"
    )
    deposit_date = Column(Date, nullable=True)
    challan_number = Column(String(50), nullable=True)
    challan_date = Column(Date, nullable=True)
    bsr_code = Column(String(20), nullable=True)  # Bank BSR Code
    cin = Column(String(50), nullable=True)  # Challan Identification Number

    # Certificate Details
    certificate_number = Column(String(50), nullable=True)
    certificate_date = Column(Date, nullable=True)
    certificate_issued = Column(Boolean, default=False)

    # Audit
    created_by = Column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    company = relationship("Company", back_populates="tds_deductions")

    __table_args__ = (
        Index("ix_tds_deductions_company_fy", "company_id", "financial_year"),
        Index("ix_tds_deductions_deductee_pan", "deductee_pan"),
        Index("ix_tds_deductions_status", "status"),
        Index("ix_tds_deductions_section", "section"),
    )


class TDSRate(Base):
    """TDS Rate Configuration."""
    __tablename__ = "tds_rates"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    company_id = Column(PGUUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)

    section = Column(
        String(20),
        nullable=False,
        comment="194A, 194C, 194H, 194I, 194IA, 194J, 194Q, 195, 192, 194B, 194D, 194E, 194G, 194K, 194LA, 194LB, 194N, 194O"
    )
    description = Column(String(255), nullable=False)

    # Rate Details
    standard_rate = Column(Numeric(5, 2), nullable=False)
    higher_rate = Column(Numeric(5, 2), nullable=True)  # If PAN not provided
    threshold_amount = Column(Numeric(15, 2), default=0)  # Min amount for TDS

    # Applicability
    effective_from = Column(Date, nullable=False)
    effective_to = Column(Date, nullable=True)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_tds_rates_company_section", "company_id", "section"),
    )


class Form16ACertificate(Base):
    """Form 16A Certificate Record."""
    __tablename__ = "form_16a_certificates"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    company_id = Column(PGUUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)

    # Certificate Info
    certificate_number = Column(String(50), nullable=False)
    issue_date = Column(Date, nullable=False)

    # Period
    financial_year = Column(String(9), nullable=False)
    quarter = Column(String(2), nullable=False)

    # Deductee
    deductee_name = Column(String(255), nullable=False)
    deductee_pan = Column(String(10), nullable=False)
    deductee_address = Column(Text, nullable=True)

    # Deductor (Company)
    deductor_name = Column(String(255), nullable=False)
    deductor_tan = Column(String(10), nullable=False)
    deductor_pan = Column(String(10), nullable=True)
    deductor_address = Column(Text, nullable=True)

    # Summary
    total_amount_paid = Column(Numeric(15, 2), nullable=False)
    total_tds_deducted = Column(Numeric(15, 2), nullable=False)
    total_tds_deposited = Column(Numeric(15, 2), nullable=False)

    # Status
    is_revised = Column(Boolean, default=False)
    original_certificate_id = Column(PGUUID(as_uuid=True), nullable=True)

    # Storage
    pdf_path = Column(String(500), nullable=True)

    created_by = Column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_form16a_company_fy_qtr", "company_id", "financial_year", "quarter"),
        Index("ix_form16a_deductee_pan", "deductee_pan"),
    )
