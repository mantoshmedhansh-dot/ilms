"""Stock Transfer API endpoints."""
from typing import Optional
import uuid
from math import ceil
from datetime import datetime

from fastapi import APIRouter, HTTPException, status, Query, Depends

from app.api.deps import DB, CurrentUser, require_permissions
from app.models.stock_transfer import TransferStatus, TransferType
from app.schemas.stock_transfer import (
    StockTransferCreate,
    StockTransferUpdate,
    StockTransferResponse,
    StockTransferDetail,
    StockTransferListResponse,
    TransferApproval,
    TransferRejection,
    TransferDispatch,
    TransferReceive,
    TransferItemDetail,
)
from app.services.transfer_service import TransferService


router = APIRouter(tags=["Stock Transfers"])


@router.get(
    "",
    response_model=StockTransferListResponse,
    dependencies=[Depends(require_permissions("inventory:view"))]
)
async def list_transfers(
    db: DB,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    from_warehouse_id: Optional[uuid.UUID] = Query(None),
    to_warehouse_id: Optional[uuid.UUID] = Query(None),
    status: Optional[TransferStatus] = Query(None),
    transfer_type: Optional[TransferType] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
):
    """
    Get paginated list of stock transfers.
    Requires: inventory:view permission
    """
    service = TransferService(db)
    skip = (page - 1) * size

    transfers, total = await service.get_transfers(
        from_warehouse_id=from_warehouse_id,
        to_warehouse_id=to_warehouse_id,
        status=status,
        transfer_type=transfer_type,
        date_from=date_from,
        date_to=date_to,
        skip=skip,
        limit=size,
    )

    return StockTransferListResponse(
        items=[StockTransferResponse.model_validate(t) for t in transfers],
        total=total,
        page=page,
        size=size,
        pages=ceil(total / size) if total > 0 else 1,
    )


@router.get(
    "/{transfer_id}",
    response_model=StockTransferDetail,
    dependencies=[Depends(require_permissions("inventory:view"))]
)
async def get_transfer(
    transfer_id: uuid.UUID,
    db: DB,
):
    """Get transfer by ID with items."""
    service = TransferService(db)
    transfer = await service.get_transfer_by_id(transfer_id, include_items=True)

    if not transfer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transfer not found"
        )

    response = StockTransferDetail.model_validate(transfer)
    if transfer.from_warehouse:
        response.from_warehouse_name = transfer.from_warehouse.name
        response.from_warehouse_code = transfer.from_warehouse.code
    if transfer.to_warehouse:
        response.to_warehouse_name = transfer.to_warehouse.name
        response.to_warehouse_code = transfer.to_warehouse.code

    # Add item details
    response.items = []
    for item in transfer.items:
        item_detail = TransferItemDetail.model_validate(item)
        if item.product:
            item_detail.product_name = item.product.name
            item_detail.product_sku = item.product.sku
        response.items.append(item_detail)

    return response


@router.post(
    "",
    response_model=StockTransferResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions("inventory:create"))]
)
async def create_transfer(
    data: StockTransferCreate,
    db: DB,
    current_user: CurrentUser,
):
    """
    Create a new stock transfer request.
    Requires: inventory:create permission
    """
    service = TransferService(db)

    try:
        transfer = await service.create_transfer(
            from_warehouse_id=data.from_warehouse_id,
            to_warehouse_id=data.to_warehouse_id,
            items=[item.model_dump() for item in data.items],
            transfer_type=data.transfer_type,
            expected_date=data.expected_date,
            notes=data.notes,
            requested_by=current_user.id,
        )
        return StockTransferResponse.model_validate(transfer)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.put(
    "/{transfer_id}",
    response_model=StockTransferResponse,
    dependencies=[Depends(require_permissions("inventory:update"))]
)
async def update_transfer(
    transfer_id: uuid.UUID,
    data: StockTransferUpdate,
    db: DB,
    current_user: CurrentUser,
):
    """
    Update a transfer (only draft status).
    Requires: inventory:update permission
    """
    service = TransferService(db)
    transfer = await service.get_transfer_by_id(transfer_id)

    if not transfer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transfer not found"
        )

    if transfer.status != TransferStatus.DRAFT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only draft transfers can be updated"
        )

    # Update fields
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if hasattr(transfer, key):
            setattr(transfer, key, value)

    await db.commit()
    await db.refresh(transfer)
    return StockTransferResponse.model_validate(transfer)


@router.post(
    "/{transfer_id}/submit",
    response_model=StockTransferResponse,
    dependencies=[Depends(require_permissions("inventory:update"))]
)
async def submit_transfer(
    transfer_id: uuid.UUID,
    db: DB,
    current_user: CurrentUser,
):
    """
    Submit transfer for approval.
    Requires: inventory:update permission
    """
    service = TransferService(db)

    try:
        transfer = await service.submit_for_approval(transfer_id)
        return StockTransferResponse.model_validate(transfer)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post(
    "/{transfer_id}/approve",
    response_model=StockTransferResponse,
    dependencies=[Depends(require_permissions("inventory:update"))]
)
async def approve_transfer(
    transfer_id: uuid.UUID,
    data: TransferApproval,
    db: DB,
    current_user: CurrentUser,
):
    """
    Approve a transfer request.
    Requires: inventory:update permission
    """
    service = TransferService(db)

    try:
        transfer = await service.approve_transfer(
            transfer_id,
            approved_by=current_user.id,
            item_approvals=data.items,
            notes=data.notes,
        )
        return StockTransferResponse.model_validate(transfer)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post(
    "/{transfer_id}/reject",
    response_model=StockTransferResponse,
    dependencies=[Depends(require_permissions("inventory:update"))]
)
async def reject_transfer(
    transfer_id: uuid.UUID,
    data: TransferRejection,
    db: DB,
    current_user: CurrentUser,
):
    """
    Reject a transfer request.
    Requires: inventory:update permission
    """
    service = TransferService(db)

    try:
        transfer = await service.reject_transfer(
            transfer_id,
            rejected_by=current_user.id,
            reason=data.reason,
        )
        return StockTransferResponse.model_validate(transfer)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post(
    "/{transfer_id}/dispatch",
    response_model=StockTransferResponse,
    dependencies=[Depends(require_permissions("inventory:update"))]
)
async def dispatch_transfer(
    transfer_id: uuid.UUID,
    data: TransferDispatch,
    db: DB,
    current_user: CurrentUser,
):
    """
    Dispatch an approved transfer.
    Requires: inventory:update permission
    """
    service = TransferService(db)

    try:
        transfer = await service.dispatch_transfer(
            transfer_id,
            dispatched_by=current_user.id,
            vehicle_number=data.vehicle_number,
            driver_name=data.driver_name,
            driver_phone=data.driver_phone,
            challan_number=data.challan_number,
            eway_bill_number=data.eway_bill_number,
            serial_items=data.serial_items,
            notes=data.notes,
        )
        return StockTransferResponse.model_validate(transfer)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post(
    "/{transfer_id}/receive",
    response_model=StockTransferResponse,
    dependencies=[Depends(require_permissions("inventory:update"))]
)
async def receive_transfer(
    transfer_id: uuid.UUID,
    data: TransferReceive,
    db: DB,
    current_user: CurrentUser,
):
    """
    Receive a dispatched transfer.
    Requires: inventory:update permission
    """
    service = TransferService(db)

    try:
        transfer = await service.receive_transfer(
            transfer_id,
            received_by=current_user.id,
            item_receipts=[item.model_dump() for item in data.items],
            notes=data.notes,
        )
        return StockTransferResponse.model_validate(transfer)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post(
    "/{transfer_id}/cancel",
    response_model=StockTransferResponse,
    dependencies=[Depends(require_permissions("inventory:update"))]
)
async def cancel_transfer(
    transfer_id: uuid.UUID,
    data: TransferRejection,
    db: DB,
    current_user: CurrentUser,
):
    """
    Cancel a transfer.
    Requires: inventory:update permission
    """
    service = TransferService(db)

    try:
        transfer = await service.cancel_transfer(
            transfer_id,
            cancelled_by=current_user.id,
            reason=data.reason,
        )
        return StockTransferResponse.model_validate(transfer)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
