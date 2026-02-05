"""
Returns Management API Endpoints - Phase 9: Reverse Logistics & Return Processing.

API endpoints for returns management including:
- Return authorizations (RMA)
- Return receipts
- Return inspections
- Refurbishment orders
- Disposition records
"""
from datetime import date
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies.auth import get_current_user, require_permissions
from app.models.user import User
from app.models.returns_management import (
    ReturnType, ReturnReason, RMAStatus, ReturnReceiptStatus,
    InspectionGrade, InspectionStatus, DispositionAction,
    RefurbishmentStatus
)
from app.schemas.returns_management import (
    ReturnAuthorizationCreate, ReturnAuthorizationUpdate, ReturnAuthorizationResponse,
    RMAApproval,
    ReturnReceiptCreate, ReturnReceiptUpdate, ReturnReceiptResponse, ReceiveItems,
    ReturnInspectionCreate, ReturnInspectionUpdate, ReturnInspectionResponse,
    InspectionComplete, InspectionDisposition,
    RefurbishmentOrderCreate, RefurbishmentOrderUpdate, RefurbishmentOrderResponse,
    RefurbishmentComplete, RefurbishmentQC,
    DispositionRecordCreate, DispositionRecordResponse,
    DispositionApproval, DispositionExecute,
    ReturnsDashboard
)
from app.services.returns_management_service import ReturnsManagementService

router = APIRouter()


# ============================================================================
# RETURN AUTHORIZATION (RMA)
# ============================================================================

@router.post(
    "/rma",
    response_model=ReturnAuthorizationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Return Authorization"
)
async def create_rma(
    data: ReturnAuthorizationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:manage"]))
):
    """Create a return authorization (RMA)."""
    service = ReturnsManagementService(db, current_user.tenant_id)
    return await service.create_rma(data, current_user.id)


@router.get(
    "/rma",
    response_model=List[ReturnAuthorizationResponse],
    summary="List Return Authorizations"
)
async def list_rmas(
    warehouse_id: Optional[UUID] = None,
    return_type: Optional[ReturnType] = None,
    status: Optional[RMAStatus] = None,
    customer_id: Optional[UUID] = None,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:read"]))
):
    """List return authorizations."""
    service = ReturnsManagementService(db, current_user.tenant_id)
    rmas, _ = await service.list_rmas(
        warehouse_id=warehouse_id,
        return_type=return_type,
        status=status,
        customer_id=customer_id,
        from_date=from_date,
        to_date=to_date,
        skip=skip,
        limit=limit
    )
    return rmas


@router.get(
    "/rma/{rma_id}",
    response_model=ReturnAuthorizationResponse,
    summary="Get Return Authorization"
)
async def get_rma(
    rma_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:read"]))
):
    """Get return authorization details."""
    service = ReturnsManagementService(db, current_user.tenant_id)
    rma = await service.get_rma(rma_id)
    if not rma:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="RMA not found"
        )
    return rma


@router.patch(
    "/rma/{rma_id}",
    response_model=ReturnAuthorizationResponse,
    summary="Update Return Authorization"
)
async def update_rma(
    rma_id: UUID,
    data: ReturnAuthorizationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:manage"]))
):
    """Update return authorization."""
    service = ReturnsManagementService(db, current_user.tenant_id)
    rma = await service.update_rma(rma_id, data)
    if not rma:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="RMA not found"
        )
    return rma


@router.post(
    "/rma/{rma_id}/approve",
    response_model=ReturnAuthorizationResponse,
    summary="Approve/Reject RMA"
)
async def approve_rma(
    rma_id: UUID,
    data: RMAApproval,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:manage"]))
):
    """Approve or reject a return authorization."""
    service = ReturnsManagementService(db, current_user.tenant_id)
    rma = await service.approve_rma(rma_id, data, current_user.id)
    if not rma:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="RMA not found or not in pending status"
        )
    return rma


@router.post(
    "/rma/{rma_id}/cancel",
    response_model=ReturnAuthorizationResponse,
    summary="Cancel RMA"
)
async def cancel_rma(
    rma_id: UUID,
    reason: str = Query(..., max_length=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:manage"]))
):
    """Cancel a return authorization."""
    service = ReturnsManagementService(db, current_user.tenant_id)
    rma = await service.cancel_rma(rma_id, reason)
    if not rma:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="RMA not found or cannot be cancelled"
        )
    return rma


# ============================================================================
# RETURN RECEIPTS
# ============================================================================

@router.post(
    "/receipts",
    response_model=ReturnReceiptResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Return Receipt"
)
async def create_receipt(
    data: ReturnReceiptCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:manage"]))
):
    """Create a return receipt."""
    service = ReturnsManagementService(db, current_user.tenant_id)
    return await service.create_receipt(data, current_user.id)


@router.get(
    "/receipts",
    response_model=List[ReturnReceiptResponse],
    summary="List Return Receipts"
)
async def list_receipts(
    warehouse_id: Optional[UUID] = None,
    status: Optional[ReturnReceiptStatus] = None,
    rma_id: Optional[UUID] = None,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:read"]))
):
    """List return receipts."""
    service = ReturnsManagementService(db, current_user.tenant_id)
    receipts, _ = await service.list_receipts(
        warehouse_id=warehouse_id,
        status=status,
        rma_id=rma_id,
        from_date=from_date,
        to_date=to_date,
        skip=skip,
        limit=limit
    )
    return receipts


@router.get(
    "/receipts/{receipt_id}",
    response_model=ReturnReceiptResponse,
    summary="Get Return Receipt"
)
async def get_receipt(
    receipt_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:read"]))
):
    """Get return receipt details."""
    service = ReturnsManagementService(db, current_user.tenant_id)
    receipt = await service.get_receipt(receipt_id)
    if not receipt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Receipt not found"
        )
    return receipt


@router.post(
    "/receipts/{receipt_id}/receive",
    response_model=ReturnReceiptResponse,
    summary="Receive Items"
)
async def receive_items(
    receipt_id: UUID,
    data: ReceiveItems,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:manage"]))
):
    """Receive items for a return receipt."""
    service = ReturnsManagementService(db, current_user.tenant_id)
    receipt = await service.receive_items(receipt_id, data, current_user.id)
    if not receipt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Receipt not found"
        )
    return receipt


@router.post(
    "/receipts/{receipt_id}/complete",
    response_model=ReturnReceiptResponse,
    summary="Complete Receipt"
)
async def complete_receipt(
    receipt_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:manage"]))
):
    """Complete a return receipt."""
    service = ReturnsManagementService(db, current_user.tenant_id)
    receipt = await service.complete_receipt(receipt_id)
    if not receipt:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Receipt not found or cannot be completed"
        )
    return receipt


# ============================================================================
# RETURN INSPECTIONS
# ============================================================================

@router.post(
    "/inspections",
    response_model=ReturnInspectionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Return Inspection"
)
async def create_inspection(
    data: ReturnInspectionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:manage"]))
):
    """Create a return inspection."""
    service = ReturnsManagementService(db, current_user.tenant_id)
    return await service.create_inspection(data)


@router.get(
    "/inspections",
    response_model=List[ReturnInspectionResponse],
    summary="List Return Inspections"
)
async def list_inspections(
    warehouse_id: Optional[UUID] = None,
    status: Optional[InspectionStatus] = None,
    grade: Optional[InspectionGrade] = None,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:read"]))
):
    """List return inspections."""
    service = ReturnsManagementService(db, current_user.tenant_id)
    inspections, _ = await service.list_inspections(
        warehouse_id=warehouse_id,
        status=status,
        grade=grade,
        from_date=from_date,
        to_date=to_date,
        skip=skip,
        limit=limit
    )
    return inspections


@router.get(
    "/inspections/{inspection_id}",
    response_model=ReturnInspectionResponse,
    summary="Get Return Inspection"
)
async def get_inspection(
    inspection_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:read"]))
):
    """Get return inspection details."""
    service = ReturnsManagementService(db, current_user.tenant_id)
    inspection = await service.get_inspection(inspection_id)
    if not inspection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inspection not found"
        )
    return inspection


@router.post(
    "/inspections/{inspection_id}/start",
    response_model=ReturnInspectionResponse,
    summary="Start Inspection"
)
async def start_inspection(
    inspection_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:manage"]))
):
    """Start an inspection."""
    service = ReturnsManagementService(db, current_user.tenant_id)
    inspection = await service.start_inspection(inspection_id, current_user.id)
    if not inspection:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inspection not found or cannot be started"
        )
    return inspection


@router.post(
    "/inspections/{inspection_id}/complete",
    response_model=ReturnInspectionResponse,
    summary="Complete Inspection"
)
async def complete_inspection(
    inspection_id: UUID,
    data: InspectionComplete,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:manage"]))
):
    """Complete an inspection with results."""
    service = ReturnsManagementService(db, current_user.tenant_id)
    inspection = await service.complete_inspection(inspection_id, data, current_user.id)
    if not inspection:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inspection not found or not in progress"
        )
    return inspection


@router.post(
    "/inspections/{inspection_id}/disposition",
    response_model=ReturnInspectionResponse,
    summary="Set Inspection Disposition"
)
async def set_inspection_disposition(
    inspection_id: UUID,
    data: InspectionDisposition,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:manage"]))
):
    """Set final disposition for an inspection."""
    service = ReturnsManagementService(db, current_user.tenant_id)
    inspection = await service.set_inspection_disposition(inspection_id, data, current_user.id)
    if not inspection:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inspection not found or not completed"
        )
    return inspection


# ============================================================================
# REFURBISHMENT ORDERS
# ============================================================================

@router.post(
    "/refurbishments",
    response_model=RefurbishmentOrderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Refurbishment Order"
)
async def create_refurbishment(
    data: RefurbishmentOrderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:manage"]))
):
    """Create a refurbishment order."""
    service = ReturnsManagementService(db, current_user.tenant_id)
    return await service.create_refurbishment(data, current_user.id)


@router.get(
    "/refurbishments",
    response_model=List[RefurbishmentOrderResponse],
    summary="List Refurbishment Orders"
)
async def list_refurbishments(
    warehouse_id: Optional[UUID] = None,
    status: Optional[RefurbishmentStatus] = None,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:read"]))
):
    """List refurbishment orders."""
    service = ReturnsManagementService(db, current_user.tenant_id)
    orders, _ = await service.list_refurbishments(
        warehouse_id=warehouse_id,
        status=status,
        from_date=from_date,
        to_date=to_date,
        skip=skip,
        limit=limit
    )
    return orders


@router.get(
    "/refurbishments/{order_id}",
    response_model=RefurbishmentOrderResponse,
    summary="Get Refurbishment Order"
)
async def get_refurbishment(
    order_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:read"]))
):
    """Get refurbishment order details."""
    service = ReturnsManagementService(db, current_user.tenant_id)
    order = await service.get_refurbishment(order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Refurbishment order not found"
        )
    return order


@router.post(
    "/refurbishments/{order_id}/start",
    response_model=RefurbishmentOrderResponse,
    summary="Start Refurbishment"
)
async def start_refurbishment(
    order_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:manage"]))
):
    """Start a refurbishment order."""
    service = ReturnsManagementService(db, current_user.tenant_id)
    order = await service.start_refurbishment(order_id, current_user.id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order not found or cannot be started"
        )
    return order


@router.post(
    "/refurbishments/{order_id}/complete",
    response_model=RefurbishmentOrderResponse,
    summary="Complete Refurbishment"
)
async def complete_refurbishment(
    order_id: UUID,
    data: RefurbishmentComplete,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:manage"]))
):
    """Complete a refurbishment order."""
    service = ReturnsManagementService(db, current_user.tenant_id)
    order = await service.complete_refurbishment(order_id, data, current_user.id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order not found or not in progress"
        )
    return order


@router.post(
    "/refurbishments/{order_id}/qc",
    response_model=RefurbishmentOrderResponse,
    summary="QC Refurbishment"
)
async def qc_refurbishment(
    order_id: UUID,
    data: RefurbishmentQC,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:manage"]))
):
    """QC a refurbishment order."""
    service = ReturnsManagementService(db, current_user.tenant_id)
    order = await service.qc_refurbishment(order_id, data, current_user.id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order not found"
        )
    return order


# ============================================================================
# DISPOSITION RECORDS
# ============================================================================

@router.post(
    "/dispositions",
    response_model=DispositionRecordResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Disposition Record"
)
async def create_disposition(
    data: DispositionRecordCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:manage"]))
):
    """Create a disposition record."""
    service = ReturnsManagementService(db, current_user.tenant_id)
    return await service.create_disposition(data, current_user.id)


@router.get(
    "/dispositions",
    response_model=List[DispositionRecordResponse],
    summary="List Disposition Records"
)
async def list_dispositions(
    warehouse_id: Optional[UUID] = None,
    disposition_action: Optional[DispositionAction] = None,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:read"]))
):
    """List disposition records."""
    service = ReturnsManagementService(db, current_user.tenant_id)
    records, _ = await service.list_dispositions(
        warehouse_id=warehouse_id,
        disposition_action=disposition_action,
        from_date=from_date,
        to_date=to_date,
        skip=skip,
        limit=limit
    )
    return records


@router.get(
    "/dispositions/{disposition_id}",
    response_model=DispositionRecordResponse,
    summary="Get Disposition Record"
)
async def get_disposition(
    disposition_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:read"]))
):
    """Get disposition record details."""
    service = ReturnsManagementService(db, current_user.tenant_id)
    record = await service.get_disposition(disposition_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Disposition record not found"
        )
    return record


@router.post(
    "/dispositions/{disposition_id}/approve",
    response_model=DispositionRecordResponse,
    summary="Approve Disposition"
)
async def approve_disposition(
    disposition_id: UUID,
    data: DispositionApproval,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:manage"]))
):
    """Approve a disposition record."""
    service = ReturnsManagementService(db, current_user.tenant_id)
    record = await service.approve_disposition(disposition_id, data, current_user.id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Disposition not found or already approved"
        )
    return record


@router.post(
    "/dispositions/{disposition_id}/execute",
    response_model=DispositionRecordResponse,
    summary="Execute Disposition"
)
async def execute_disposition(
    disposition_id: UUID,
    data: DispositionExecute,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:manage"]))
):
    """Execute a disposition record."""
    service = ReturnsManagementService(db, current_user.tenant_id)
    record = await service.execute_disposition(disposition_id, data, current_user.id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Disposition not found or not approved"
        )
    return record


# ============================================================================
# DASHBOARD
# ============================================================================

@router.get(
    "/dashboard/{warehouse_id}",
    response_model=ReturnsDashboard,
    summary="Get Returns Dashboard"
)
async def get_dashboard(
    warehouse_id: UUID,
    from_date: date = Query(default=None),
    to_date: date = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_permissions(["wms:read"]))
):
    """Get returns dashboard statistics."""
    if not from_date:
        from_date = date.today().replace(day=1)
    if not to_date:
        to_date = date.today()

    service = ReturnsManagementService(db, current_user.tenant_id)
    return await service.get_dashboard(warehouse_id, from_date, to_date)
