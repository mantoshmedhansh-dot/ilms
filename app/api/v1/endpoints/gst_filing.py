"""API endpoints for GST e-Filing and ITC Management.

Provides:
- GSTR-1 data preparation and filing
- GSTR-3B data preparation and filing
- GSTR-2A/2B download for ITC reconciliation
- ITC ledger management
- Filing status tracking
"""
from typing import Optional, List
from uuid import UUID
from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.itc import ITCLedger, ITCSummary, GSTFiling
from app.api.deps import DB, get_current_user
from app.services.gst_filing_service import GSTFilingService, GSTFilingError
from app.services.itc_service import ITCService
from app.core.module_decorators import require_module


router = APIRouter()


# ==================== Request/Response Schemas ====================

class GSTFilingRequest(BaseModel):
    """Request schema for GST filing."""
    month: int = Field(..., ge=1, le=12, description="Month (1-12)")
    year: int = Field(..., ge=2017, description="Year")
    company_id: Optional[UUID] = None


class GSTFilingResponse(BaseModel):
    """Response schema for GST filing."""
    status: str
    return_type: str
    period: str
    arn: Optional[str] = None
    filing_date: Optional[str] = None
    details: Optional[dict] = None


class GSTR1DataResponse(BaseModel):
    """Response schema for GSTR-1 prepared data."""
    gstin: str
    period: str
    b2b_count: int
    b2c_count: int
    total_taxable_value: float
    total_tax: float
    data: dict


class FilingStatusResponse(BaseModel):
    """Response schema for filing status."""
    gstin: str
    return_type: str
    period: str
    status: str
    arn: Optional[str] = None
    filing_date: Optional[str] = None


class ITCEntryCreate(BaseModel):
    """Request schema for creating ITC entry."""
    vendor_gstin: str = Field(..., min_length=15, max_length=15)
    vendor_name: str
    invoice_number: str
    invoice_date: date
    invoice_value: float
    taxable_value: float
    cgst_itc: float = 0
    sgst_itc: float = 0
    igst_itc: float = 0
    cess_itc: float = 0
    itc_type: str = "INPUTS"
    hsn_code: Optional[str] = None
    description: Optional[str] = None
    vendor_id: Optional[UUID] = None
    purchase_invoice_id: Optional[UUID] = None


class ITCEntryResponse(BaseModel):
    """Response schema for ITC entry."""
    id: UUID
    period: str
    vendor_gstin: str
    vendor_name: str
    invoice_number: str
    invoice_date: date
    invoice_value: float
    taxable_value: float
    cgst_itc: float
    sgst_itc: float
    igst_itc: float
    cess_itc: float
    total_itc: float
    status: str
    gstr2a_matched: bool
    gstr2b_matched: bool
    match_status: str
    available_itc: float

    class Config:
        from_attributes = True


class ITCAvailableResponse(BaseModel):
    """Response schema for available ITC."""
    cgst_available: float
    sgst_available: float
    igst_available: float
    cess_available: float
    total_available: float
    invoice_count: int


class ITCReconcileRequest(BaseModel):
    """Request schema for ITC reconciliation."""
    period: str = Field(..., description="Period in YYYYMM format")
    gstr2a_data: Optional[List[dict]] = None
    gstr2b_data: Optional[List[dict]] = None


class ITCReconcileResponse(BaseModel):
    """Response schema for ITC reconciliation result."""
    period: str
    matched: int
    unmatched: int
    partial_matches: int
    mismatches: List[dict]


class GSTDashboardResponse(BaseModel):
    """Response schema for GST dashboard."""
    gstin: str
    company_name: str
    filing_status: List[dict]
    itc_summary: Optional[dict] = None


# ==================== GST Filing Endpoints ====================

@router.post(
    "/file/gstr1",
    response_model=GSTFilingResponse,
    summary="File GSTR-1 return",
    description="""
    File GSTR-1 (Outward supplies) return for a specified period.

    **Business Rules:**
    - GSTR-1 must be filed by 11th of next month
    - All B2B and B2C invoices for the period are included
    - Requires GSP credentials to be configured

    **Permissions Required:** gst:file
    """,
    responses={
        200: {"description": "GSTR-1 filed successfully"},
        400: {"description": "Filing error or validation failed"},
        401: {"description": "GST portal authentication failed"},
    }
)
async def file_gstr1(
    request: GSTFilingRequest,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """File GSTR-1 for the specified period."""
    company_id = request.company_id or current_user.company_id

    if not company_id:
        raise HTTPException(
            status_code=400,
            detail="Company ID is required for GST filing"
        )

    try:
        filing_service = GSTFilingService(db, company_id)
        result = await filing_service.file_gstr1(request.month, request.year)
        return GSTFilingResponse(**result)

    except GSTFilingError as e:
        raise HTTPException(
            status_code=400,
            detail={"message": e.message, "error_code": e.error_code, "details": e.details}
        )


@router.post(
    "/file/gstr3b",
    response_model=GSTFilingResponse,
    summary="File GSTR-3B return",
    description="""
    File GSTR-3B (Summary return) for a specified period.

    **Business Rules:**
    - GSTR-3B must be filed by 20th of next month
    - Summarizes all outward supplies and ITC claims
    - Tax payment should be made before filing

    **Permissions Required:** gst:file
    """,
    responses={
        200: {"description": "GSTR-3B filed successfully"},
        400: {"description": "Filing error or validation failed"},
    }
)
async def file_gstr3b(
    request: GSTFilingRequest,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """File GSTR-3B for the specified period."""
    company_id = request.company_id or current_user.company_id

    if not company_id:
        raise HTTPException(
            status_code=400,
            detail="Company ID is required for GST filing"
        )

    try:
        filing_service = GSTFilingService(db, company_id)
        result = await filing_service.file_gstr3b(request.month, request.year)
        return GSTFilingResponse(**result)

    except GSTFilingError as e:
        raise HTTPException(
            status_code=400,
            detail={"message": e.message, "error_code": e.error_code, "details": e.details}
        )


@router.get(
    "/filing-status",
    response_model=FilingStatusResponse,
    summary="Get GST filing status",
    description="Check the filing status of a specific GST return.",
)
@require_module("finance")
async def get_filing_status(
    return_type: str = Query(..., description="Return type: GSTR1, GSTR3B"),
    period: str = Query(..., description="Period in MMYYYY format"),
    company_id: Optional[UUID] = None,
    db: DB = None,
    current_user: User = Depends(get_current_user),
):
    """Get filing status for a specific return period."""
    effective_company_id = company_id or current_user.company_id

    if not effective_company_id:
        raise HTTPException(status_code=400, detail="Company ID is required")

    try:
        filing_service = GSTFilingService(db, effective_company_id)
        result = await filing_service.get_filing_status(return_type, period)
        return FilingStatusResponse(**result)

    except GSTFilingError as e:
        raise HTTPException(status_code=400, detail=e.message)


@router.get(
    "/gstr1/preview",
    response_model=GSTR1DataResponse,
    summary="Preview GSTR-1 data",
    description="Generate and preview GSTR-1 data before filing.",
)
@require_module("finance")
async def preview_gstr1_data(
    month: int = Query(..., ge=1, le=12),
    year: int = Query(..., ge=2017),
    company_id: Optional[UUID] = None,
    db: DB = None,
    current_user: User = Depends(get_current_user),
):
    """Preview GSTR-1 data for a period."""
    effective_company_id = company_id or current_user.company_id

    if not effective_company_id:
        raise HTTPException(status_code=400, detail="Company ID is required")

    try:
        filing_service = GSTFilingService(db, effective_company_id)
        company = await filing_service._get_company()
        data = await filing_service.prepare_gstr1_data(month, year)

        # Calculate summary
        b2b_count = sum(len(b.get("inv", [])) for b in data.get("b2b", []))
        b2cl_count = sum(len(b.get("inv", [])) for b in data.get("b2cl", []))
        b2cs_count = len(data.get("b2cs", []))

        return GSTR1DataResponse(
            gstin=company.gstin,
            period=f"{month:02d}{year}",
            b2b_count=b2b_count,
            b2c_count=b2cl_count + b2cs_count,
            total_taxable_value=data.get("gt", 0),
            total_tax=0,  # Would need to calculate from data
            data=data
        )

    except GSTFilingError as e:
        raise HTTPException(status_code=400, detail=e.message)


@router.get(
    "/dashboard",
    response_model=GSTDashboardResponse,
    summary="Get GST filing dashboard",
    description="Get comprehensive GST filing dashboard with status of all returns.",
)
@require_module("finance")
async def get_gst_dashboard(
    company_id: Optional[UUID] = None,
    db: DB = None,
    current_user: User = Depends(get_current_user),
):
    """Get GST filing dashboard data."""
    effective_company_id = company_id or current_user.company_id

    if not effective_company_id:
        raise HTTPException(status_code=400, detail="Company ID is required")

    try:
        filing_service = GSTFilingService(db, effective_company_id)
        dashboard_data = await filing_service.get_gst_dashboard_data()

        # Get ITC summary
        itc_service = ITCService(db, effective_company_id)
        itc_dashboard = await itc_service.get_itc_dashboard()

        return GSTDashboardResponse(
            gstin=dashboard_data["gstin"],
            company_name=dashboard_data["company_name"],
            filing_status=dashboard_data["filing_status"],
            itc_summary=itc_dashboard
        )

    except GSTFilingError as e:
        raise HTTPException(status_code=400, detail=e.message)


# ==================== GSTR-2A/2B Download ====================

@router.get(
    "/gstr2a/download",
    summary="Download GSTR-2A data",
    description="Download GSTR-2A (auto-populated inward supplies) from GST portal.",
)
async def download_gstr2a(
    month: int = Query(..., ge=1, le=12),
    year: int = Query(..., ge=2017),
    company_id: Optional[UUID] = None,
    db: DB = None,
    current_user: User = Depends(get_current_user),
):
    """Download GSTR-2A for ITC reconciliation."""
    effective_company_id = company_id or current_user.company_id

    if not effective_company_id:
        raise HTTPException(status_code=400, detail="Company ID is required")

    try:
        filing_service = GSTFilingService(db, effective_company_id)
        result = await filing_service.download_gstr2a(month, year)
        return result

    except GSTFilingError as e:
        raise HTTPException(status_code=400, detail=e.message)


# ==================== ITC Management Endpoints ====================

@router.get(
    "/itc/available",
    response_model=ITCAvailableResponse,
    summary="Get available ITC",
    description="Get aggregated available ITC by tax component.",
)
@require_module("finance")
async def get_available_itc(
    period: Optional[str] = Query(None, description="Period in YYYYMM format"),
    vendor_gstin: Optional[str] = None,
    company_id: Optional[UUID] = None,
    db: DB = None,
    current_user: User = Depends(get_current_user),
):
    """Get available ITC summary."""
    effective_company_id = company_id or current_user.company_id

    if not effective_company_id:
        raise HTTPException(status_code=400, detail="Company ID is required")

    itc_service = ITCService(db, effective_company_id)
    result = await itc_service.get_available_itc(period, vendor_gstin)
    return ITCAvailableResponse(**result)


@router.get(
    "/itc/ledger",
    summary="Get ITC ledger",
    description="Get ITC ledger entries with filters.",
)
@require_module("finance")
async def get_itc_ledger(
    period: Optional[str] = None,
    status: Optional[str] = None,
    match_status: Optional[str] = None,
    vendor_gstin: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    company_id: Optional[UUID] = None,
    db: DB = None,
    current_user: User = Depends(get_current_user),
):
    """Get ITC ledger entries."""
    effective_company_id = company_id or current_user.company_id

    if not effective_company_id:
        raise HTTPException(status_code=400, detail="Company ID is required")

    itc_service = ITCService(db, effective_company_id)
    result = await itc_service.get_itc_ledger(
        period=period,
        status=status,
        match_status=match_status,
        vendor_gstin=vendor_gstin,
        skip=skip,
        limit=limit
    )

    return {
        "total": result["total"],
        "items": [
            ITCEntryResponse(
                id=e.id,
                period=e.period,
                vendor_gstin=e.vendor_gstin,
                vendor_name=e.vendor_name,
                invoice_number=e.invoice_number,
                invoice_date=e.invoice_date,
                invoice_value=float(e.invoice_value),
                taxable_value=float(e.taxable_value),
                cgst_itc=float(e.cgst_itc),
                sgst_itc=float(e.sgst_itc),
                igst_itc=float(e.igst_itc),
                cess_itc=float(e.cess_itc),
                total_itc=float(e.total_itc),
                status=e.status,
                gstr2a_matched=e.gstr2a_matched,
                gstr2b_matched=e.gstr2b_matched,
                match_status=e.match_status,
                available_itc=float(e.available_itc),
            )
            for e in result["entries"]
        ],
        "skip": skip,
        "limit": limit
    }


@router.post(
    "/itc/entry",
    response_model=ITCEntryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create ITC entry",
    description="Create a new ITC ledger entry from a vendor invoice.",
)
@require_module("finance")
async def create_itc_entry(
    entry_in: ITCEntryCreate,
    company_id: Optional[UUID] = None,
    db: DB = None,
    current_user: User = Depends(get_current_user),
):
    """Create a new ITC entry."""
    effective_company_id = company_id or current_user.company_id

    if not effective_company_id:
        raise HTTPException(status_code=400, detail="Company ID is required")

    from decimal import Decimal

    itc_service = ITCService(db, effective_company_id)
    entry = await itc_service.create_itc_entry(
        vendor_gstin=entry_in.vendor_gstin,
        vendor_name=entry_in.vendor_name,
        invoice_number=entry_in.invoice_number,
        invoice_date=entry_in.invoice_date,
        invoice_value=Decimal(str(entry_in.invoice_value)),
        taxable_value=Decimal(str(entry_in.taxable_value)),
        cgst_itc=Decimal(str(entry_in.cgst_itc)),
        sgst_itc=Decimal(str(entry_in.sgst_itc)),
        igst_itc=Decimal(str(entry_in.igst_itc)),
        cess_itc=Decimal(str(entry_in.cess_itc)),
        itc_type=entry_in.itc_type,
        hsn_code=entry_in.hsn_code,
        description=entry_in.description,
        vendor_id=entry_in.vendor_id,
        purchase_invoice_id=entry_in.purchase_invoice_id,
        created_by=current_user.id,
    )

    await db.commit()

    return ITCEntryResponse(
        id=entry.id,
        period=entry.period,
        vendor_gstin=entry.vendor_gstin,
        vendor_name=entry.vendor_name,
        invoice_number=entry.invoice_number,
        invoice_date=entry.invoice_date,
        invoice_value=float(entry.invoice_value),
        taxable_value=float(entry.taxable_value),
        cgst_itc=float(entry.cgst_itc),
        sgst_itc=float(entry.sgst_itc),
        igst_itc=float(entry.igst_itc),
        cess_itc=float(entry.cess_itc),
        total_itc=float(entry.total_itc),
        status=entry.status,
        gstr2a_matched=entry.gstr2a_matched,
        gstr2b_matched=entry.gstr2b_matched,
        match_status=entry.match_status,
        available_itc=float(entry.available_itc),
    )


@router.post(
    "/itc/reconcile",
    response_model=ITCReconcileResponse,
    summary="Reconcile ITC with GSTR-2A/2B",
    description="Reconcile ITC ledger entries with GSTR-2A or GSTR-2B data.",
)
@require_module("finance")
async def reconcile_itc(
    request: ITCReconcileRequest,
    company_id: Optional[UUID] = None,
    db: DB = None,
    current_user: User = Depends(get_current_user),
):
    """Reconcile ITC with GSTR-2A/2B data."""
    effective_company_id = company_id or current_user.company_id

    if not effective_company_id:
        raise HTTPException(status_code=400, detail="Company ID is required")

    itc_service = ITCService(db, effective_company_id)

    if request.gstr2a_data:
        result = await itc_service.reconcile_with_gstr2a(request.period, request.gstr2a_data)
    elif request.gstr2b_data:
        result = await itc_service.reconcile_with_gstr2b(request.period, request.gstr2b_data)
    else:
        # Auto-download and reconcile
        filing_service = GSTFilingService(db, effective_company_id)
        month = int(request.period[4:])
        year = int(request.period[:4])

        gstr2a_result = await filing_service.download_gstr2a(month, year)
        gstr2a_data = gstr2a_result.get("data", {}).get("b2b", [])

        result = await itc_service.reconcile_with_gstr2a(request.period, gstr2a_data)

    return ITCReconcileResponse(**result)


@router.get(
    "/itc/dashboard",
    summary="Get ITC dashboard",
    description="Get ITC dashboard with available credits and matching status.",
)
@require_module("finance")
async def get_itc_dashboard(
    company_id: Optional[UUID] = None,
    db: DB = None,
    current_user: User = Depends(get_current_user),
):
    """Get ITC dashboard data."""
    effective_company_id = company_id or current_user.company_id

    if not effective_company_id:
        raise HTTPException(status_code=400, detail="Company ID is required")

    itc_service = ITCService(db, effective_company_id)
    return await itc_service.get_itc_dashboard()


# ==================== MISSING ENDPOINTS FOR FRONTEND INTEGRATION ====================

class GSTAuthenticateResponse(BaseModel):
    """Response schema for GST portal authentication."""
    success: bool
    message: str
    session_id: Optional[str] = None
    expiry: Optional[str] = None


class ITCSummaryResponse(BaseModel):
    """Response schema for ITC summary."""
    total_available: float
    total_utilized: float
    total_reversed: float
    balance: float
    cgst_available: float
    sgst_available: float
    igst_available: float
    cess_available: float
    matched_with_gstr2a: int
    matched_with_gstr2b: int
    mismatch_count: int
    mismatch_value: float


class ITCUtilizeRequest(BaseModel):
    """Request schema for ITC utilization."""
    period: str = Field(..., description="Period in YYYYMM format")
    cgst_utilized: float = 0
    sgst_utilized: float = 0
    igst_utilized: float = 0
    cess_utilized: float = 0


class ITCUtilizeResponse(BaseModel):
    """Response schema for ITC utilization."""
    period: str
    cgst_utilized: float
    sgst_utilized: float
    igst_utilized: float
    cess_utilized: float
    total_utilized: float
    remaining_balance: float


class ITCReverseRequest(BaseModel):
    """Request schema for ITC reversal."""
    reason: str
    amount: Optional[float] = None


class ITCReverseResponse(BaseModel):
    """Response schema for ITC reversal."""
    id: UUID
    reversed_amount: float
    new_status: str
    reason: str


class FilingHistoryItem(BaseModel):
    """Filing history item."""
    id: str
    return_type: str
    period: str
    status: str
    due_date: str
    filed_date: Optional[str] = None
    arn: Optional[str] = None
    taxable_value: float
    tax_liability: float


class FilingHistoryResponse(BaseModel):
    """Response schema for filing history."""
    items: List[FilingHistoryItem]
    total: int
    page: int
    size: int


class ITCMismatchItem(BaseModel):
    """ITC mismatch item."""
    id: UUID
    vendor_gstin: str
    vendor_name: str
    invoice_number: str
    invoice_date: date
    books_amount: float
    portal_amount: float
    difference: float
    mismatch_type: str  # MISSING_IN_PORTAL, AMOUNT_MISMATCH, EXTRA_IN_PORTAL


class ITCMismatchReportResponse(BaseModel):
    """Response schema for ITC mismatch report."""
    period: str
    items: List[ITCMismatchItem]
    total_mismatch_count: int
    total_mismatch_value: float
    missing_in_portal: int
    amount_mismatches: int
    extra_in_portal: int


@router.post(
    "/authenticate",
    response_model=GSTAuthenticateResponse,
    summary="Authenticate with GST Portal",
    description="""
    Authenticate with the GST portal using configured GSP credentials.

    **Note:** This endpoint initiates a session with the GST portal for
    subsequent filing operations. The session typically expires after 30 minutes.

    **Permissions Required:** gst:authenticate
    """,
)
@require_module("finance")
async def authenticate_gst_portal(
    company_id: Optional[UUID] = None,
    db: DB = None,
    current_user: User = Depends(get_current_user),
):
    """Authenticate with GST portal."""
    effective_company_id = company_id or current_user.company_id

    if not effective_company_id:
        raise HTTPException(status_code=400, detail="Company ID is required")

    try:
        filing_service = GSTFilingService(db, effective_company_id)
        result = await filing_service.authenticate_gst_portal()
        return GSTAuthenticateResponse(**result)

    except GSTFilingError as e:
        raise HTTPException(status_code=400, detail=e.message)


@router.get(
    "/filing-history",
    response_model=FilingHistoryResponse,
    summary="Get GST filing history",
    description="Get the history of GST return filings with pagination.",
)
@require_module("finance")
async def get_filing_history(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(12, ge=1, le=100, description="Items per page"),
    return_type: Optional[str] = Query(None, description="Filter by return type: GSTR1, GSTR3B"),
    company_id: Optional[UUID] = None,
    db: DB = None,
    current_user: User = Depends(get_current_user),
):
    """Get filing history with pagination."""
    effective_company_id = company_id or current_user.company_id

    if not effective_company_id:
        raise HTTPException(status_code=400, detail="Company ID is required")

    try:
        filing_service = GSTFilingService(db, effective_company_id)
        result = await filing_service.get_filing_history(
            page=page,
            size=size,
            return_type=return_type
        )
        return FilingHistoryResponse(**result)

    except GSTFilingError as e:
        raise HTTPException(status_code=400, detail=e.message)


# Add alias route for frontend compatibility: /gst/download/gstr2a
@router.get(
    "/download/gstr2a",
    summary="Download GSTR-2A data (alias)",
    description="Download GSTR-2A (auto-populated inward supplies) from GST portal. Alias for /gstr2a/download.",
)
async def download_gstr2a_alias(
    month: int = Query(..., ge=1, le=12),
    year: int = Query(..., ge=2017),
    company_id: Optional[UUID] = None,
    db: DB = None,
    current_user: User = Depends(get_current_user),
):
    """Download GSTR-2A for ITC reconciliation (alias endpoint)."""
    return await download_gstr2a(month, year, company_id, db, current_user)


@router.get(
    "/itc/summary",
    response_model=ITCSummaryResponse,
    summary="Get ITC summary",
    description="Get summarized ITC data including available, utilized, and reversed amounts.",
)
@require_module("finance")
async def get_itc_summary(
    period: Optional[str] = Query(None, description="Period in YYYYMM format"),
    company_id: Optional[UUID] = None,
    db: DB = None,
    current_user: User = Depends(get_current_user),
):
    """Get ITC summary for a period."""
    effective_company_id = company_id or current_user.company_id

    if not effective_company_id:
        raise HTTPException(status_code=400, detail="Company ID is required")

    itc_service = ITCService(db, effective_company_id)
    result = await itc_service.get_itc_summary(period)
    return ITCSummaryResponse(**result)


@router.post(
    "/itc/utilize",
    response_model=ITCUtilizeResponse,
    summary="Utilize ITC against tax liability",
    description="""
    Utilize available Input Tax Credit against GST liability.

    **Business Rules:**
    - IGST credit is utilized first against IGST liability
    - Then CGST and SGST credits against respective liabilities
    - Cross-utilization follows GST rules (IGST → CGST → SGST)

    **Permissions Required:** gst:itc:utilize
    """,
)
async def utilize_itc(
    request: ITCUtilizeRequest,
    company_id: Optional[UUID] = None,
    db: DB = None,
    current_user: User = Depends(get_current_user),
):
    """Utilize ITC against tax liability."""
    effective_company_id = company_id or current_user.company_id

    if not effective_company_id:
        raise HTTPException(status_code=400, detail="Company ID is required")

    itc_service = ITCService(db, effective_company_id)
    result = await itc_service.utilize_itc(
        period=request.period,
        cgst_utilized=request.cgst_utilized,
        sgst_utilized=request.sgst_utilized,
        igst_utilized=request.igst_utilized,
        cess_utilized=request.cess_utilized,
        utilized_by=current_user.id,
    )

    await db.commit()
    return ITCUtilizeResponse(**result)


@router.post(
    "/itc/{entry_id}/reverse",
    response_model=ITCReverseResponse,
    summary="Reverse ITC entry",
    description="""
    Reverse an ITC entry due to various reasons like vendor non-compliance,
    goods returned, credit note received, etc.

    **Business Rules:**
    - Only AVAILABLE status ITC can be reversed
    - Reversal reason is mandatory
    - Partial reversal is allowed by specifying amount

    **Permissions Required:** gst:itc:reverse
    """,
)
@require_module("finance")
async def reverse_itc_entry(
    entry_id: UUID,
    request: ITCReverseRequest,
    company_id: Optional[UUID] = None,
    db: DB = None,
    current_user: User = Depends(get_current_user),
):
    """Reverse an ITC entry."""
    effective_company_id = company_id or current_user.company_id

    if not effective_company_id:
        raise HTTPException(status_code=400, detail="Company ID is required")

    itc_service = ITCService(db, effective_company_id)
    result = await itc_service.reverse_itc_entry(
        entry_id=entry_id,
        reason=request.reason,
        amount=request.amount,
        reversed_by=current_user.id,
    )

    await db.commit()
    return ITCReverseResponse(**result)


@router.get(
    "/itc/mismatch-report",
    response_model=ITCMismatchReportResponse,
    summary="Get ITC mismatch report",
    description="""
    Get report of mismatches between ITC ledger and GSTR-2A/2B data.

    **Mismatch Types:**
    - MISSING_IN_PORTAL: Invoice in books but not in GSTR-2A/2B
    - AMOUNT_MISMATCH: Invoice exists but amounts differ
    - EXTRA_IN_PORTAL: Invoice in portal but not in books
    """,
)
@require_module("finance")
async def get_itc_mismatch_report(
    period: str = Query(..., description="Period in YYYYMM format"),
    company_id: Optional[UUID] = None,
    db: DB = None,
    current_user: User = Depends(get_current_user),
):
    """Get ITC mismatch report for a period."""
    effective_company_id = company_id or current_user.company_id

    if not effective_company_id:
        raise HTTPException(status_code=400, detail="Company ID is required")

    itc_service = ITCService(db, effective_company_id)
    result = await itc_service.get_mismatch_report(period)
    return ITCMismatchReportResponse(**result)
