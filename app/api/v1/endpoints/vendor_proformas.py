"""Vendor Proforma Invoice API endpoints."""
from typing import Optional
from uuid import UUID, uuid4
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy import select, func, desc, and_, or_
from sqlalchemy.orm import selectinload

from app.api.deps import DB, get_current_user
from app.models.user import User
from app.models.purchase import VendorProformaInvoice, VendorProformaItem, PurchaseOrder
from app.models.vendor import Vendor
from app.services.document_sequence_service import DocumentSequenceService
from app.core.module_decorators import require_module

router = APIRouter()


# ==================== List Proformas ====================
@router.get("")
@require_module("procurement")
async def list_vendor_proformas(
    db: DB,
    current_user: User = Depends(get_current_user),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    vendor_id: Optional[UUID] = None,
    status: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    search: Optional[str] = None,
):
    """
    List vendor proforma invoices with filtering.

    Filters:
    - vendor_id: Filter by vendor
    - status: RECEIVED, UNDER_REVIEW, APPROVED, REJECTED, CONVERTED_TO_PO, EXPIRED, CANCELLED
    - start_date/end_date: Date range filter
    - search: Search in proforma number, our reference
    """
    query = select(VendorProformaInvoice).options(
        selectinload(VendorProformaInvoice.vendor),
        selectinload(VendorProformaInvoice.items)
    )

    conditions = []

    if vendor_id:
        conditions.append(VendorProformaInvoice.vendor_id == vendor_id)

    if status:
        conditions.append(VendorProformaInvoice.status == status.upper())

    if start_date:
        conditions.append(VendorProformaInvoice.proforma_date >= start_date)

    if end_date:
        conditions.append(VendorProformaInvoice.proforma_date <= end_date)

    if search:
        conditions.append(
            or_(
                VendorProformaInvoice.proforma_number.ilike(f"%{search}%"),
                VendorProformaInvoice.our_reference.ilike(f"%{search}%")
            )
        )

    if conditions:
        query = query.where(and_(*conditions))

    # Count total
    count_query = select(func.count()).select_from(VendorProformaInvoice)
    if conditions:
        count_query = count_query.where(and_(*conditions))
    total = await db.scalar(count_query) or 0

    # Get paginated results
    query = query.order_by(desc(VendorProformaInvoice.proforma_date))
    query = query.offset((page - 1) * size).limit(size)

    result = await db.execute(query)
    proformas = result.scalars().unique().all()

    return {
        "items": [
            {
                "id": str(pf.id),
                "proforma_number": pf.proforma_number,
                "our_reference": pf.our_reference,
                "status": pf.status,
                "vendor_id": str(pf.vendor_id),
                "vendor_name": pf.vendor.business_name if pf.vendor else None,
                "proforma_date": pf.proforma_date.isoformat() if pf.proforma_date else None,
                "validity_date": pf.validity_date.isoformat() if pf.validity_date else None,
                "total_amount": float(pf.total_amount) if pf.total_amount else 0,
                "items_count": len(pf.items) if pf.items else 0,
                "created_at": pf.created_at.isoformat() if hasattr(pf, 'created_at') and pf.created_at else None,
            }
            for pf in proformas
        ],
        "total": total,
        "page": page,
        "size": size,
        "pages": (total + size - 1) // size,
    }


# ==================== Create Proforma ====================
@router.post("", status_code=status.HTTP_201_CREATED)
@require_module("procurement")
async def create_vendor_proforma(
    data: dict,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """
    Create a new vendor proforma invoice.

    Request body:
    - vendor_id: UUID
    - proforma_number: str (vendor's quotation number)
    - proforma_date: date
    - validity_date: date (optional)
    - items: list of item dicts
    - notes: str (optional)
    """
    # Generate our internal reference (VPI = Vendor Proforma Invoice)
    today = date.today()
    random_suffix = str(uuid4())[:8].upper()
    our_reference = f"VPI-{today.strftime('%Y%m%d')}-{random_suffix}"

    # Calculate totals from items
    items_data = data.get("items", [])
    subtotal = Decimal("0")
    total_tax = Decimal("0")

    for item in items_data:
        quantity = Decimal(str(item.get("quantity", 0)))
        unit_price = Decimal(str(item.get("unit_price", 0)))
        discount = Decimal(str(item.get("discount_amount", 0)))
        taxable = (quantity * unit_price) - discount

        gst_rate = Decimal(str(item.get("gst_rate", 18)))
        tax = taxable * (gst_rate / 100)

        subtotal += taxable
        total_tax += tax

    total_amount = subtotal + total_tax

    # Create proforma
    proforma = VendorProformaInvoice(
        vendor_id=data["vendor_id"],
        proforma_number=data["proforma_number"],
        our_reference=our_reference,
        proforma_date=data["proforma_date"],
        validity_date=data.get("validity_date"),
        status="RECEIVED",
        subtotal=subtotal,
        tax_amount=total_tax,
        total_amount=total_amount,
        notes=data.get("notes"),
        created_by=current_user.id,
    )

    db.add(proforma)
    await db.flush()

    # Create items
    for item in items_data:
        quantity = Decimal(str(item.get("quantity", 0)))
        unit_price = Decimal(str(item.get("unit_price", 0)))
        discount = Decimal(str(item.get("discount_amount", 0)))
        taxable = (quantity * unit_price) - discount
        gst_rate = Decimal(str(item.get("gst_rate", 18)))
        tax = taxable * (gst_rate / 100)

        proforma_item = VendorProformaItem(
            proforma_id=proforma.id,
            product_id=item.get("product_id"),
            part_code=item.get("part_code"),
            description=item["description"],
            hsn_code=item.get("hsn_code"),
            uom=item.get("uom", "NOS"),
            quantity=quantity,
            unit_price=unit_price,
            discount_percent=item.get("discount_percent", 0),
            discount_amount=discount,
            taxable_amount=taxable,
            gst_rate=gst_rate,
            cgst_amount=tax / 2 if data.get("is_intrastate", True) else Decimal("0"),
            sgst_amount=tax / 2 if data.get("is_intrastate", True) else Decimal("0"),
            igst_amount=tax if not data.get("is_intrastate", True) else Decimal("0"),
            total_amount=taxable + tax,
        )
        db.add(proforma_item)

    await db.commit()
    await db.refresh(proforma)

    return {
        "id": str(proforma.id),
        "our_reference": proforma.our_reference,
        "status": proforma.status,
        "message": "Vendor proforma created successfully"
    }


# ==================== Get Proforma Details ====================
@router.get("/{proforma_id}")
@require_module("procurement")
async def get_vendor_proforma(
    proforma_id: UUID,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Get vendor proforma invoice details with items."""
    query = select(VendorProformaInvoice).options(
        selectinload(VendorProformaInvoice.vendor),
        selectinload(VendorProformaInvoice.items).selectinload(VendorProformaItem.product)
    ).where(VendorProformaInvoice.id == proforma_id)

    result = await db.execute(query)
    proforma = result.scalar_one_or_none()

    if not proforma:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vendor proforma not found"
        )

    return {
        "id": str(proforma.id),
        "proforma_number": proforma.proforma_number,
        "our_reference": proforma.our_reference,
        "status": proforma.status,
        "vendor": {
            "id": str(proforma.vendor.id) if proforma.vendor else None,
            "business_name": proforma.vendor.business_name if proforma.vendor else None,
            "gstin": proforma.vendor.gstin if proforma.vendor else None,
        } if proforma.vendor else None,
        "proforma_date": proforma.proforma_date.isoformat() if proforma.proforma_date else None,
        "validity_date": proforma.validity_date.isoformat() if proforma.validity_date else None,
        "subtotal": float(proforma.subtotal) if proforma.subtotal else 0,
        "tax_amount": float(proforma.tax_amount) if proforma.tax_amount else 0,
        "total_amount": float(proforma.total_amount) if proforma.total_amount else 0,
        "notes": proforma.notes,
        "items": [
            {
                "id": str(item.id),
                "product_id": str(item.product_id) if item.product_id else None,
                "product_name": item.product.name if item.product else None,
                "part_code": item.part_code,
                "description": item.description,
                "hsn_code": item.hsn_code,
                "uom": item.uom,
                "quantity": float(item.quantity),
                "unit_price": float(item.unit_price),
                "discount_percent": float(item.discount_percent) if item.discount_percent else 0,
                "discount_amount": float(item.discount_amount) if item.discount_amount else 0,
                "taxable_amount": float(item.taxable_amount),
                "gst_rate": float(item.gst_rate),
                "cgst_amount": float(item.cgst_amount) if item.cgst_amount else 0,
                "sgst_amount": float(item.sgst_amount) if item.sgst_amount else 0,
                "igst_amount": float(item.igst_amount) if item.igst_amount else 0,
                "total_amount": float(item.total_amount),
            }
            for item in (proforma.items or [])
        ],
        "po_id": str(proforma.po_id) if hasattr(proforma, 'po_id') and proforma.po_id else None,
        "created_at": proforma.created_at.isoformat() if hasattr(proforma, 'created_at') and proforma.created_at else None,
    }


# ==================== Approve Proforma ====================
@router.post("/{proforma_id}/approve")
@require_module("procurement")
async def approve_proforma(
    proforma_id: UUID,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Approve a vendor proforma invoice."""
    proforma = await db.get(VendorProformaInvoice, proforma_id)

    if not proforma:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Proforma not found"
        )

    if proforma.status not in ("RECEIVED", "UNDER_REVIEW"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot approve proforma in {proforma.status} status"
        )

    proforma.status = "APPROVED"
    proforma.approved_by = current_user.id

    await db.commit()

    return {"message": "Proforma approved successfully", "status": proforma.status}


# ==================== Reject Proforma ====================
@router.post("/{proforma_id}/reject")
@require_module("procurement")
async def reject_proforma(
    proforma_id: UUID,
    data: dict,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Reject a vendor proforma invoice."""
    proforma = await db.get(VendorProformaInvoice, proforma_id)

    if not proforma:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Proforma not found"
        )

    if proforma.status not in ("RECEIVED", "UNDER_REVIEW"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot reject proforma in {proforma.status} status"
        )

    proforma.status = "REJECTED"
    if hasattr(proforma, 'rejection_reason'):
        proforma.rejection_reason = data.get("reason")

    await db.commit()

    return {"message": "Proforma rejected successfully", "status": proforma.status}


# ==================== Convert to PO ====================
@router.post("/{proforma_id}/convert-to-po")
@require_module("procurement")
async def convert_proforma_to_po(
    proforma_id: UUID,
    data: dict,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """
    Convert approved proforma to Purchase Order.

    Request body:
    - warehouse_id: UUID (destination warehouse)
    - expected_delivery_date: date
    - notes: str (optional)
    """
    # Load proforma with items
    query = select(VendorProformaInvoice).options(
        selectinload(VendorProformaInvoice.items)
    ).where(VendorProformaInvoice.id == proforma_id)

    result = await db.execute(query)
    proforma = result.scalar_one_or_none()

    if not proforma:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Proforma not found"
        )

    if proforma.status != "APPROVED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only approved proformas can be converted to PO"
        )

    # Generate PO number
    seq_service = DocumentSequenceService(db)
    po_number = await seq_service.get_next_number("PO")

    # Create Purchase Order
    from app.models.purchase import PurchaseOrder, PurchaseOrderItem

    po = PurchaseOrder(
        po_number=po_number,
        vendor_id=proforma.vendor_id,
        warehouse_id=data["warehouse_id"],
        status="DRAFT",
        order_date=date.today(),
        expected_date=data.get("expected_delivery_date"),
        subtotal=proforma.subtotal,
        tax_amount=proforma.tax_amount,
        total_amount=proforma.total_amount,
        notes=data.get("notes", f"Converted from proforma {proforma.our_reference}"),
        created_by=current_user.id,
    )

    db.add(po)
    await db.flush()

    # Create PO items from proforma items
    for pf_item in proforma.items:
        po_item = PurchaseOrderItem(
            po_id=po.id,
            product_id=pf_item.product_id,
            variant_id=pf_item.variant_id if hasattr(pf_item, 'variant_id') else None,
            description=pf_item.description,
            hsn_code=pf_item.hsn_code,
            uom=pf_item.uom,
            quantity=pf_item.quantity,
            unit_price=pf_item.unit_price,
            discount_percent=pf_item.discount_percent,
            discount_amount=pf_item.discount_amount,
            taxable_amount=pf_item.taxable_amount,
            gst_rate=pf_item.gst_rate,
            cgst_amount=pf_item.cgst_amount,
            sgst_amount=pf_item.sgst_amount,
            igst_amount=pf_item.igst_amount,
            total_amount=pf_item.total_amount,
        )
        db.add(po_item)

    # Update proforma status
    proforma.status = "CONVERTED_TO_PO"
    if hasattr(proforma, 'po_id'):
        proforma.po_id = po.id

    await db.commit()

    return {
        "message": "Proforma converted to PO successfully",
        "po_id": str(po.id),
        "po_number": po_number
    }


# ==================== Compare Proformas ====================
@router.post("/compare")
@require_module("procurement")
async def compare_proformas(
    data: dict,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """
    Compare multiple vendor proforma invoices for the same items.

    Request body:
    - proforma_ids: list of UUIDs
    """
    proforma_ids = data.get("proforma_ids", [])

    if len(proforma_ids) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least 2 proformas required for comparison"
        )

    # Load proformas with items
    query = select(VendorProformaInvoice).options(
        selectinload(VendorProformaInvoice.vendor),
        selectinload(VendorProformaInvoice.items)
    ).where(VendorProformaInvoice.id.in_(proforma_ids))

    result = await db.execute(query)
    proformas = result.scalars().unique().all()

    # Build comparison
    comparison = {
        "proformas": [
            {
                "id": str(pf.id),
                "vendor_name": pf.vendor.business_name if pf.vendor else None,
                "proforma_number": pf.proforma_number,
                "proforma_date": pf.proforma_date.isoformat() if pf.proforma_date else None,
                "validity_date": pf.validity_date.isoformat() if pf.validity_date else None,
                "total_amount": float(pf.total_amount) if pf.total_amount else 0,
                "items_count": len(pf.items) if pf.items else 0,
            }
            for pf in proformas
        ],
        "lowest_total": min((float(pf.total_amount) for pf in proformas if pf.total_amount), default=0),
        "highest_total": max((float(pf.total_amount) for pf in proformas if pf.total_amount), default=0),
    }

    # Recommend lowest quote
    if proformas:
        lowest = min(proformas, key=lambda p: float(p.total_amount or 0))
        comparison["recommendation"] = {
            "proforma_id": str(lowest.id),
            "vendor_name": lowest.vendor.business_name if lowest.vendor else None,
            "total_amount": float(lowest.total_amount) if lowest.total_amount else 0,
        }

    return comparison
