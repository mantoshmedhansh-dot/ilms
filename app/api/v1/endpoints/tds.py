"""API endpoints for TDS (Tax Deducted at Source) Management."""
from typing import Optional, List
from uuid import UUID
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.tds import TDSDeduction, TDSDeductionStatus, TDSSection
from app.api.deps import DB, get_current_user
from app.schemas.tds import (
    TDSCalculationRequest,
    TDSCalculationResponse,
    RecordTDSRequest,
    TDSDeductionResponse,
    MarkDepositedRequest,
    Form16ARequest,
    PendingDepositSummary,
)
from app.services.tds_service import TDSService, TDSError
from app.core.module_decorators import require_module

router = APIRouter()


# ==================== TDS Calculation ====================

@router.post("/calculate", response_model=TDSCalculationResponse)
@require_module("finance")
async def calculate_tds(
    request: TDSCalculationRequest,
    db: DB,
    company_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_user),
):
    """
    Calculate TDS amount for a given gross amount and section.

    This is a utility endpoint to preview TDS before recording.
    """
    effective_company_id = company_id or current_user.company_id

    if not effective_company_id:
        raise HTTPException(status_code=400, detail="Company ID is required")

    try:
        service = TDSService(db, effective_company_id)
        result = service.calculate_tds(
            amount=request.amount,
            section=request.section,
            pan_available=request.pan_available,
            lower_deduction_rate=float(request.lower_deduction_rate) if request.lower_deduction_rate else None
        )

        return TDSCalculationResponse(
            gross_amount=result["gross_amount"],
            section=result["section"],
            tds_rate=result["tds_rate"],
            tds_amount=result["tds_amount"],
            surcharge=result["surcharge"],
            education_cess=result["education_cess"],
            total_tds=result["total_tds"],
            pan_available=result["pan_available"],
            lower_deduction_applied=result["lower_deduction_applied"]
        )
    except TDSError as e:
        raise HTTPException(status_code=400, detail=e.message)


# ==================== Record TDS Deduction ====================

@router.post("/deductions", response_model=TDSDeductionResponse)
@require_module("finance")
async def record_tds_deduction(
    request: RecordTDSRequest,
    db: DB,
    company_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_user),
):
    """
    Record a TDS deduction.

    Used when making payments to vendors/contractors where TDS is applicable.
    """
    effective_company_id = company_id or current_user.company_id

    if not effective_company_id:
        raise HTTPException(status_code=400, detail="Company ID is required")

    try:
        service = TDSService(db, effective_company_id)
        result = await service.record_tds_deduction(
            deductee_id=request.deductee_id,
            deductee_type=request.deductee_type,
            deductee_name=request.deductee_name,
            deductee_pan=request.deductee_pan,
            deductee_address=request.deductee_address,
            section=request.section,
            deduction_date=request.deduction_date,
            gross_amount=request.gross_amount,
            pan_available=request.pan_available,
            lower_deduction_cert_no=request.lower_deduction_cert_no,
            lower_deduction_rate=float(request.lower_deduction_rate) if request.lower_deduction_rate else None,
            reference_type=request.reference_type,
            reference_id=request.reference_id,
            reference_number=request.reference_number,
            narration=request.narration,
            user_id=current_user.id
        )

        return TDSDeductionResponse(
            id=result["id"],
            deductee_name=result["deductee_name"],
            deductee_pan=result["deductee_pan"],
            section=result["section"],
            deduction_date=result["deduction_date"],
            financial_year=result["financial_year"],
            quarter=result["quarter"],
            gross_amount=result["gross_amount"],
            tds_rate=result["tds_rate"],
            total_tds=result["total_tds"],
            status=result["status"],
            challan_number=None,
            certificate_issued=False
        )
    except TDSError as e:
        raise HTTPException(status_code=400, detail=e.message)


@router.get("/deductions", response_model=List[TDSDeductionResponse])
@require_module("finance")
async def list_tds_deductions(
    db: DB,
    financial_year: Optional[str] = Query(None, description="Financial year like 2024-25"),
    quarter: Optional[str] = Query(None, description="Quarter like Q1, Q2, Q3, Q4"),
    status: Optional[str] = Query(None, description="PENDING, DEPOSITED, CERTIFICATE_ISSUED"),
    section: Optional[str] = Query(None, description="TDS section like 194C, 194J"),
    deductee_pan: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    company_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_user),
):
    """List all TDS deductions with filters."""
    effective_company_id = company_id or current_user.company_id

    if not effective_company_id:
        raise HTTPException(status_code=400, detail="Company ID is required")

    query = select(TDSDeduction).where(TDSDeduction.company_id == effective_company_id)

    if financial_year:
        query = query.where(TDSDeduction.financial_year == financial_year)
    if quarter:
        query = query.where(TDSDeduction.quarter == quarter)
    if status:
        query = query.where(TDSDeduction.status == TDSDeductionStatus(status))
    if section:
        query = query.where(TDSDeduction.section == TDSSection(section))
    if deductee_pan:
        query = query.where(TDSDeduction.deductee_pan == deductee_pan)

    query = query.order_by(TDSDeduction.deduction_date.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    deductions = result.scalars().all()

    return [
        TDSDeductionResponse(
            id=d.id,
            deductee_name=d.deductee_name,
            deductee_pan=d.deductee_pan,
            section=d.section,
            deduction_date=d.deduction_date,
            financial_year=d.financial_year,
            quarter=d.quarter,
            gross_amount=d.gross_amount,
            tds_rate=float(d.tds_rate),
            total_tds=d.total_tds,
            status=d.status,
            challan_number=d.challan_number,
            certificate_issued=d.certificate_issued
        )
        for d in deductions
    ]


@router.get("/deductions/{deduction_id}")
@require_module("finance")
async def get_tds_deduction(
    deduction_id: UUID,
    db: DB,
    company_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_user),
):
    """Get details of a specific TDS deduction."""
    effective_company_id = company_id or current_user.company_id

    result = await db.execute(
        select(TDSDeduction).where(
            and_(
                TDSDeduction.id == deduction_id,
                TDSDeduction.company_id == effective_company_id
            )
        )
    )
    deduction = result.scalar_one_or_none()

    if not deduction:
        raise HTTPException(status_code=404, detail="TDS deduction not found")

    return {
        "id": str(deduction.id),
        "deductee_id": str(deduction.deductee_id) if deduction.deductee_id else None,
        "deductee_type": deduction.deductee_type,
        "deductee_name": deduction.deductee_name,
        "deductee_pan": deduction.deductee_pan,
        "deductee_address": deduction.deductee_address,
        "section": deduction.section,
        "deduction_date": str(deduction.deduction_date),
        "financial_year": deduction.financial_year,
        "quarter": deduction.quarter,
        "gross_amount": float(deduction.gross_amount),
        "tds_rate": float(deduction.tds_rate),
        "tds_amount": float(deduction.tds_amount),
        "surcharge": float(deduction.surcharge),
        "education_cess": float(deduction.education_cess),
        "total_tds": float(deduction.total_tds),
        "lower_deduction_cert_no": deduction.lower_deduction_cert_no,
        "lower_deduction_rate": float(deduction.lower_deduction_rate) if deduction.lower_deduction_rate else None,
        "reference_type": deduction.reference_type,
        "reference_id": str(deduction.reference_id) if deduction.reference_id else None,
        "reference_number": deduction.reference_number,
        "narration": deduction.narration,
        "status": deduction.status,
        "deposit_date": str(deduction.deposit_date) if deduction.deposit_date else None,
        "challan_number": deduction.challan_number,
        "challan_date": str(deduction.challan_date) if deduction.challan_date else None,
        "bsr_code": deduction.bsr_code,
        "cin": deduction.cin,
        "certificate_number": deduction.certificate_number,
        "certificate_date": str(deduction.certificate_date) if deduction.certificate_date else None,
        "certificate_issued": deduction.certificate_issued,
        "created_at": deduction.created_at.isoformat()
    }


# ==================== Pending Deposits ====================

@router.get("/pending-deposits")
@require_module("finance")
async def get_pending_deposits(
    db: DB,
    financial_year: Optional[str] = None,
    company_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_user),
):
    """
    Get summary of TDS deductions pending deposit.

    These need to be deposited to the government by the 7th of next month.
    """
    effective_company_id = company_id or current_user.company_id

    if not effective_company_id:
        raise HTTPException(status_code=400, detail="Company ID is required")

    try:
        service = TDSService(db, effective_company_id)
        pending = await service.get_pending_deposits(financial_year)

        return {
            "success": True,
            "pending_deposits": pending,
            "total_pending_amount": sum(p["total_tds"] for p in pending)
        }
    except TDSError as e:
        raise HTTPException(status_code=400, detail=e.message)


@router.post("/mark-deposited")
@require_module("finance")
async def mark_tds_deposited(
    request: MarkDepositedRequest,
    db: DB,
    company_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_user),
):
    """
    Mark TDS deductions as deposited to government.

    Record challan details after making the payment.
    """
    effective_company_id = company_id or current_user.company_id

    if not effective_company_id:
        raise HTTPException(status_code=400, detail="Company ID is required")

    try:
        service = TDSService(db, effective_company_id)
        result = await service.mark_as_deposited(
            deduction_ids=request.deduction_ids,
            deposit_date=request.deposit_date,
            challan_number=request.challan_number,
            challan_date=request.challan_date,
            bsr_code=request.bsr_code,
            cin=request.cin
        )

        return result
    except TDSError as e:
        raise HTTPException(status_code=400, detail=e.message)


# ==================== Form 16A Certificates ====================

@router.post("/form-16a/generate")
@require_module("finance")
async def generate_form_16a(
    request: Form16ARequest,
    db: DB,
    company_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_user),
):
    """
    Generate Form 16A certificate data for a deductee.

    Form 16A is TDS certificate issued quarterly to the deductee.
    """
    effective_company_id = company_id or current_user.company_id

    if not effective_company_id:
        raise HTTPException(status_code=400, detail="Company ID is required")

    try:
        service = TDSService(db, effective_company_id)
        result = await service.generate_form_16a(
            deductee_pan=request.deductee_pan,
            financial_year=request.financial_year,
            quarter=request.quarter
        )

        return result
    except TDSError as e:
        raise HTTPException(status_code=400, detail=e.message)


@router.post("/form-16a/download")
@require_module("finance")
async def download_form_16a_pdf(
    request: Form16ARequest,
    db: DB,
    company_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_user),
):
    """
    Generate and download Form 16A as PDF.

    Returns base64 encoded PDF content.
    """
    effective_company_id = company_id or current_user.company_id

    if not effective_company_id:
        raise HTTPException(status_code=400, detail="Company ID is required")

    try:
        service = TDSService(db, effective_company_id)

        # Get deductor info
        from app.models.company import Company
        company_result = await db.execute(
            select(Company).where(Company.id == effective_company_id)
        )
        company = company_result.scalar_one_or_none()

        if not company:
            raise HTTPException(status_code=404, detail="Company not found")

        deductor_info = {
            "name": company.name,
            "tan": getattr(company, 'tan', '') or "XXXXXXXXXX",
            "pan": getattr(company, 'pan', '') or "",
            "address": f"{getattr(company, 'address_line1', '')} {getattr(company, 'city', '')} {getattr(company, 'state', '')} {getattr(company, 'pincode', '')}".strip()
        }

        pdf_bytes = await service.generate_form_16a_pdf(
            deductee_pan=request.deductee_pan,
            financial_year=request.financial_year,
            quarter=request.quarter,
            deductor_name=deductor_info["name"],
            deductor_tan=deductor_info["tan"],
            deductor_address=deductor_info["address"]
        )

        import base64
        return {
            "success": True,
            "filename": f"Form16A_{request.deductee_pan}_{request.financial_year}_{request.quarter}.pdf",
            "content_type": "application/pdf",
            "content_base64": base64.b64encode(pdf_bytes).decode()
        }
    except TDSError as e:
        raise HTTPException(status_code=400, detail=e.message)


# ==================== Statistics & Reports ====================

@router.get("/summary")
@require_module("finance")
async def get_tds_summary(
    financial_year: str = Query(..., description="Financial year like 2024-25"),
    db: DB = None,
    company_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_user),
):
    """Get TDS summary for a financial year."""
    effective_company_id = company_id or current_user.company_id

    if not effective_company_id:
        raise HTTPException(status_code=400, detail="Company ID is required")

    # Summary by section
    section_query = select(
        TDSDeduction.section,
        func.count(TDSDeduction.id).label("count"),
        func.sum(TDSDeduction.gross_amount).label("total_gross"),
        func.sum(TDSDeduction.total_tds).label("total_tds")
    ).where(
        and_(
            TDSDeduction.company_id == effective_company_id,
            TDSDeduction.financial_year == financial_year
        )
    ).group_by(TDSDeduction.section)

    section_result = await db.execute(section_query)
    section_summary = section_result.all()

    # Summary by quarter
    quarter_query = select(
        TDSDeduction.quarter,
        func.count(TDSDeduction.id).label("count"),
        func.sum(TDSDeduction.total_tds).label("total_tds")
    ).where(
        and_(
            TDSDeduction.company_id == effective_company_id,
            TDSDeduction.financial_year == financial_year
        )
    ).group_by(TDSDeduction.quarter)

    quarter_result = await db.execute(quarter_query)
    quarter_summary = quarter_result.all()

    # Summary by status
    status_query = select(
        TDSDeduction.status,
        func.count(TDSDeduction.id).label("count"),
        func.sum(TDSDeduction.total_tds).label("total_tds")
    ).where(
        and_(
            TDSDeduction.company_id == effective_company_id,
            TDSDeduction.financial_year == financial_year
        )
    ).group_by(TDSDeduction.status)

    status_result = await db.execute(status_query)
    status_summary = status_result.all()

    return {
        "financial_year": financial_year,
        "by_section": [
            {
                "section": row.section,
                "count": row.count,
                "total_gross": float(row.total_gross or 0),
                "total_tds": float(row.total_tds or 0)
            }
            for row in section_summary
        ],
        "by_quarter": [
            {
                "quarter": row.quarter,
                "count": row.count,
                "total_tds": float(row.total_tds or 0)
            }
            for row in quarter_summary
        ],
        "by_status": [
            {
                "status": row.status,
                "count": row.count,
                "total_tds": float(row.total_tds or 0)
            }
            for row in status_summary
        ],
        "totals": {
            "total_deductions": sum(row.count for row in section_summary),
            "total_gross_amount": sum(float(row.total_gross or 0) for row in section_summary),
            "total_tds_amount": sum(float(row.total_tds or 0) for row in section_summary)
        }
    }


@router.get("/sections")
@require_module("finance")
async def get_tds_sections():
    """Get list of all TDS sections with rates."""
    from app.services.tds_service import TDS_RATES

    return {
        "sections": [
            {
                "code": code,
                "description": info["description"],
                "standard_rate": info["rate"],
                "higher_rate": info["rate"] * 2,  # When PAN not provided
                "threshold": info["threshold"]
            }
            for code, info in TDS_RATES.items()
        ]
    }
