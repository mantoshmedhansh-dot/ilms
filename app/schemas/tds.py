"""TDS (Tax Deducted at Source) schemas for API requests/responses."""
from pydantic import BaseModel, Field

from app.schemas.base import BaseResponseSchema
from typing import Optional, List
from uuid import UUID
from datetime import date
from decimal import Decimal


class TDSCalculationRequest(BaseModel):
    """Request for TDS calculation."""
    amount: Decimal = Field(..., gt=0, description="Gross amount for TDS calculation")
    section: str = Field(..., description="TDS Section like 194C, 194J")
    pan_available: bool = Field(True, description="Whether PAN is available")
    lower_deduction_rate: Optional[Decimal] = Field(None, description="Lower deduction rate if applicable")


class TDSCalculationResponse(BaseModel):
    """Response for TDS calculation."""
    gross_amount: Decimal
    section: str
    tds_rate: float
    tds_amount: Decimal
    surcharge: Decimal
    education_cess: Decimal
    total_tds: Decimal
    pan_available: bool
    lower_deduction_applied: bool


class RecordTDSRequest(BaseModel):
    """Request to record a TDS deduction."""
    deductee_id: Optional[UUID] = Field(None, description="Deductee entity ID")
    deductee_type: str = Field(..., description="Deductee type: VENDOR, CUSTOMER, EMPLOYEE")
    deductee_name: str = Field(..., description="Deductee name")
    deductee_pan: str = Field(..., min_length=10, max_length=10, description="Deductee PAN")
    deductee_address: Optional[str] = Field(None, description="Deductee address")
    section: str = Field(..., description="TDS section")
    deduction_date: date = Field(..., description="Date of deduction")
    gross_amount: Decimal = Field(..., gt=0, description="Gross amount")
    pan_available: bool = Field(True, description="Whether PAN is available")
    lower_deduction_cert_no: Optional[str] = Field(None, description="Lower deduction certificate number")
    lower_deduction_rate: Optional[Decimal] = Field(None, description="Lower deduction rate")
    reference_type: Optional[str] = Field(None, description="Reference document type")
    reference_id: Optional[UUID] = Field(None, description="Reference document ID")
    reference_number: Optional[str] = Field(None, description="Reference document number")
    narration: Optional[str] = Field(None, description="Narration")


class TDSDeductionResponse(BaseModel):
    """Response for TDS deduction."""
    id: UUID
    deductee_name: str
    deductee_pan: str
    section: str
    deduction_date: date
    financial_year: str
    quarter: str
    gross_amount: Decimal
    tds_rate: float
    total_tds: Decimal
    status: str
    challan_number: Optional[str] = None
    certificate_issued: bool


class MarkDepositedRequest(BaseModel):
    """Request to mark TDS as deposited."""
    deduction_ids: List[UUID] = Field(..., description="List of deduction IDs to mark")
    deposit_date: date = Field(..., description="Date of deposit")
    challan_number: str = Field(..., description="Challan number")
    challan_date: date = Field(..., description="Challan date")
    bsr_code: str = Field(..., description="BSR code")
    cin: Optional[str] = Field(None, description="CIN number")


class Form16ARequest(BaseModel):
    """Request for Form 16A generation."""
    deductee_pan: str = Field(..., min_length=10, max_length=10, description="Deductee PAN")
    financial_year: str = Field(..., pattern=r"^\d{4}-\d{2}$", description="Financial year (e.g., 2025-26)")
    quarter: str = Field(..., pattern=r"^Q[1-4]$", description="Quarter (Q1-Q4)")


class PendingDepositSummary(BaseModel):
    """Summary of pending TDS deposits."""
    section: str = Field(..., description="TDS section")
    count: int = Field(..., description="Number of pending deductions")
    total_amount: Decimal = Field(..., description="Total TDS amount pending")
    earliest_date: date = Field(..., description="Earliest deduction date")
