"""
Serialization API Endpoints for Barcode Generation in Procurement

Endpoints for:
- Generating serial numbers for Purchase Orders
- Managing supplier codes
- Managing model code references
- Scanning serials during GRN
- Exporting serials as CSV
"""

from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, String, and_

from app.api.deps import get_db, get_current_user, Permissions
from app.models.user import User
from app.models.serialization import (
    SerialSequence,
    POSerial,
    ModelCodeReference,
    SupplierCode,
    SerialStatus,
    ItemType,
)
from app.schemas.serialization import (
    # Supplier Code
    SupplierCodeCreate,
    SupplierCodeUpdate,
    SupplierCodeResponse,
    # Model Code
    ModelCodeCreate,
    ModelCodeUpdate,
    ModelCodeResponse,
    # Serial Generation
    GenerateSerialsRequest,
    GenerateSerialItem,
    GenerateSerialsResponse,
    # PO Serials
    POSerialResponse,
    POSerialsListResponse,
    # Scanning
    ScanSerialRequest,
    ScanSerialResponse,
    BulkScanRequest,
    BulkScanResponse,
    # Lookup
    SerialLookupResponse,
    # Sequence
    SequenceStatusRequest,
    SequenceStatusResponse,
    # Preview
    CodePreviewRequest,
    CodePreviewResponse,
    # FG Code
    FGCodeGenerateRequest,
    FGCodeGenerateResponse,
    # Create Product with Code
    CreateProductWithCodeRequest,
    CreateProductWithCodeResponse,
)
from app.models.product import Product, ProductItemType, ProductStatus
from app.services.serialization import SerializationService
from app.core.module_decorators import require_module

router = APIRouter()


# ==================== Supplier Code Endpoints ====================

@router.get("/suppliers", response_model=List[SupplierCodeResponse])
@require_module("oms_fulfillment")
async def list_supplier_codes(
    active_only: bool = Query(True, description="Only show active suppliers"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all supplier codes"""
    service = SerializationService(db)
    suppliers = await service.get_supplier_codes(active_only=active_only)
    return suppliers


@router.post("/suppliers", response_model=SupplierCodeResponse)
@require_module("oms_fulfillment")
async def create_supplier_code(
    data: SupplierCodeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new supplier code (2-letter code)"""
    service = SerializationService(db)
    try:
        supplier = await service.create_supplier_code(
            code=data.code,
            name=data.name,
            vendor_id=data.vendor_id,
            description=data.description,
        )
        return supplier
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/suppliers/{code}", response_model=SupplierCodeResponse)
@require_module("oms_fulfillment")
async def get_supplier_code(
    code: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get supplier code by code"""
    result = await db.execute(
        select(SupplierCode).where(SupplierCode.code == code.upper())
    )
    supplier = result.scalar_one_or_none()
    if not supplier:
        raise HTTPException(status_code=404, detail=f"Supplier code {code} not found")
    return supplier


@router.put("/suppliers/{code}/link-vendor")
@require_module("oms_fulfillment")
async def link_vendor_to_supplier_code(
    code: str,
    vendor_id: str = Query(..., description="Vendor ID to link"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Link a vendor to an existing supplier code.

    This is required for barcode generation during PO approval.
    Each vendor should be linked to a unique supplier code.
    """
    # Find the supplier code
    result = await db.execute(
        select(SupplierCode).where(SupplierCode.code == code.upper())
    )
    supplier = result.scalar_one_or_none()
    if not supplier:
        raise HTTPException(status_code=404, detail=f"Supplier code {code} not found")

    # Verify vendor exists
    from app.models.vendor import Vendor
    vendor_result = await db.execute(
        select(Vendor).where(Vendor.id == vendor_id)
    )
    vendor = vendor_result.scalar_one_or_none()
    if not vendor:
        raise HTTPException(status_code=404, detail=f"Vendor {vendor_id} not found")

    # Check if vendor already linked to another supplier code
    existing_link = await db.execute(
        select(SupplierCode).where(
            SupplierCode.vendor_id == vendor_id,
            SupplierCode.code != code.upper()
        )
    )
    existing = existing_link.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Vendor already linked to supplier code '{existing.code}'"
        )

    # Link vendor to supplier code
    supplier.vendor_id = vendor_id
    await db.commit()

    return {
        "success": True,
        "message": f"Vendor '{vendor.name}' linked to supplier code '{code.upper()}'",
        "supplier_code": code.upper(),
        "vendor_id": vendor_id,
        "vendor_name": vendor.name
    }


@router.post("/suppliers/auto-create-for-vendor")
@require_module("oms_fulfillment")
async def auto_create_supplier_code_for_vendor(
    vendor_id: str = Query(..., description="Vendor ID"),
    code: str = Query(..., min_length=2, max_length=2, description="2-letter supplier code"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new supplier code and link it to a vendor.

    Use this when a vendor doesn't have a supplier code yet.
    """
    import uuid

    # Verify vendor exists
    from app.models.vendor import Vendor
    vendor_result = await db.execute(
        select(Vendor).where(Vendor.id == vendor_id)
    )
    vendor = vendor_result.scalar_one_or_none()
    if not vendor:
        raise HTTPException(status_code=404, detail=f"Vendor {vendor_id} not found")

    # Check if vendor already has a supplier code
    existing_vendor_code = await db.execute(
        select(SupplierCode).where(SupplierCode.vendor_id == vendor_id)
    )
    if existing_vendor_code.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail=f"Vendor already has a supplier code"
        )

    # Check if code already exists
    existing_code = await db.execute(
        select(SupplierCode).where(SupplierCode.code == code.upper())
    )
    existing = existing_code.scalar_one_or_none()

    if existing:
        if existing.vendor_id:
            raise HTTPException(
                status_code=400,
                detail=f"Supplier code '{code.upper()}' already exists and is linked to another vendor"
            )
        # Link existing code to vendor
        existing.vendor_id = vendor_id
        await db.commit()
        return {
            "success": True,
            "message": f"Existing supplier code '{code.upper()}' linked to vendor '{vendor.name}'",
            "supplier_code": code.upper(),
            "vendor_id": vendor_id,
            "vendor_name": vendor.name,
            "action": "linked_existing"
        }

    # Create new supplier code
    new_supplier = SupplierCode(
        id=str(uuid.uuid4()),
        code=code.upper(),
        name=vendor.name,
        vendor_id=vendor_id,
        description=f"Auto-created for vendor {vendor.name}",
        is_active=True,
    )
    db.add(new_supplier)
    await db.commit()

    return {
        "success": True,
        "message": f"Created supplier code '{code.upper()}' for vendor '{vendor.name}'",
        "supplier_code": code.upper(),
        "vendor_id": vendor_id,
        "vendor_name": vendor.name,
        "action": "created_new"
    }


# ==================== Model Code Reference Endpoints ====================

@router.get("/model-codes", response_model=List[ModelCodeResponse])
@require_module("oms_fulfillment")
async def list_model_codes(
    active_only: bool = Query(True, description="Only show active model codes"),
    item_type: Optional[ItemType] = Query(None, description="Filter by item type (filters by fg_code prefix)"),
    linked_only: bool = Query(False, description="Only show model codes linked to products"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all model code references"""
    query = select(ModelCodeReference)
    if active_only:
        query = query.where(ModelCodeReference.is_active == True)
    if item_type:
        # Filter by fg_code prefix since item_type column doesn't exist in production
        # FG codes start with "WP" (Water Purifier), SP codes start with "SP" (Spare Part)
        if item_type.value == "FG":
            query = query.where(ModelCodeReference.fg_code.like("WP%"))
        elif item_type.value == "SP":
            query = query.where(ModelCodeReference.fg_code.like("SP%"))
    if linked_only:
        query = query.where(ModelCodeReference.product_id.isnot(None))
    query = query.order_by(ModelCodeReference.fg_code)

    result = await db.execute(query)
    return result.scalars().all()


@router.post("/model-codes", response_model=ModelCodeResponse)
@require_module("oms_fulfillment")
async def create_model_code(
    data: ModelCodeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new model code reference"""
    service = SerializationService(db)
    try:
        model_ref = await service.create_model_code_reference(
            fg_code=data.fg_code,
            model_code=data.model_code,
            # item_type removed - determined from fg_code prefix
            product_id=data.product_id,
            product_sku=data.product_sku,
            description=data.description,
        )
        return model_ref
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/model-codes/{fg_code}", response_model=ModelCodeResponse)
@require_module("oms_fulfillment")
async def get_model_code(
    fg_code: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get model code reference by FG code"""
    result = await db.execute(
        select(ModelCodeReference).where(ModelCodeReference.fg_code == fg_code.upper())
    )
    model_ref = result.scalar_one_or_none()
    if not model_ref:
        raise HTTPException(status_code=404, detail=f"Model code {fg_code} not found")
    return model_ref


# ==================== FG Code Generation ====================

@router.post("/fg-code/generate", response_model=FGCodeGenerateResponse)
@require_module("oms_fulfillment")
async def generate_fg_code(
    data: FGCodeGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Generate a new FG Code for a product.

    Example: WPRAIEL001
    - category_code: WP (Water Purifier)
    - subcategory_code: R (RO)
    - brand_code: A (ILMS.AI)
    - model_name: IELITZ -> generates IEL as model code
    """
    service = SerializationService(db)
    result = await service.generate_fg_code(
        category_code=data.category_code,
        subcategory_code=data.subcategory_code,
        brand_code=data.brand_code,
        model_name=data.model_name,
    )
    return result


# ==================== Create Product with Code ====================

@router.post("/create-product", response_model=CreateProductWithCodeResponse)
@require_module("oms_fulfillment")
async def create_product_with_code(
    data: CreateProductWithCodeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new product with auto-generated codes.

    This is the master product creation flow from the Serialization section.
    The system will:
    1. Generate FG Code / Item Code based on category, subcategory, brand, model
    2. Create the Product in the products table
    3. Create the ModelCodeReference linking the codes
    4. Return all generated codes and product details

    FG Code Format:
    - Finished Goods: WPRAIEL001 (WP=Category, R=Subcategory, A=Brand, IEL=Model, 001=Seq)
    - Spare Parts: SPSDFSD001 (SP=Category, SD=Subcategory, F=Brand, SDF=Model, 001=Seq)
    """
    import uuid
    import re

    # Map item type from schema to product model enum
    product_item_type = (
        ProductItemType.FINISHED_GOODS if data.item_type.value == "FG"
        else ProductItemType.SPARE_PART
    )

    # Generate FG Code / Item Code
    # Format: {category_code}{subcategory_code}{brand_code}{model_code}{sequence}
    base_code = f"{data.category_code}{data.subcategory_code}{data.brand_code}{data.model_code}"

    # Find next available sequence number for this base code
    existing_codes = await db.execute(
        select(ModelCodeReference.fg_code)
        .where(ModelCodeReference.fg_code.like(f"{base_code}%"))
        .order_by(ModelCodeReference.fg_code.desc())
    )
    existing_list = [row[0] for row in existing_codes.fetchall()]

    # Determine next sequence number
    next_seq = 1
    if existing_list:
        # Extract sequence numbers from existing codes
        for code in existing_list:
            match = re.search(r'(\d+)$', code)
            if match:
                seq_num = int(match.group(1))
                if seq_num >= next_seq:
                    next_seq = seq_num + 1

    # Generate the full FG Code with sequence
    fg_code = f"{base_code}{next_seq:03d}"

    # Check if FG code already exists
    existing_fg = await db.execute(
        select(Product).where(Product.fg_code == fg_code)
    )
    if existing_fg.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail=f"FG Code {fg_code} already exists"
        )

    # Check if model code reference already exists
    existing_model_ref = await db.execute(
        select(ModelCodeReference).where(ModelCodeReference.fg_code == fg_code)
    )
    if existing_model_ref.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail=f"Model code reference for {fg_code} already exists"
        )

    # Generate slug from name
    slug = re.sub(r'[^a-z0-9]+', '-', data.name.lower()).strip('-')
    # Ensure unique slug
    existing_slug = await db.execute(
        select(Product).where(Product.slug.like(f"{slug}%"))
    )
    slug_count = len(existing_slug.fetchall())
    if slug_count > 0:
        slug = f"{slug}-{slug_count + 1}"

    # Create the Product
    product_id = str(uuid.uuid4())
    product = Product(
        id=product_id,
        name=data.name,
        slug=slug,
        sku=fg_code,  # SKU = FG Code
        fg_code=fg_code,
        model_code=data.model_code,
        model_number=data.model_code,
        item_type=product_item_type,
        description=data.description,
        short_description=data.description[:500] if data.description and len(data.description) > 500 else data.description,
        category_id=data.category_id,
        brand_id=data.brand_id,
        mrp=data.mrp,
        selling_price=data.selling_price or data.mrp,
        cost_price=data.cost_price,
        hsn_code=data.hsn_code,
        gst_rate=data.gst_rate,
        warranty_months=data.warranty_months,
        status=ProductStatus.ACTIVE,
        is_active=True,
    )
    db.add(product)

    # Create the ModelCodeReference
    model_ref_id = str(uuid.uuid4()).replace("-", "")
    model_ref = ModelCodeReference(
        id=model_ref_id,
        product_id=product_id,
        product_sku=fg_code,
        fg_code=fg_code,
        model_code=data.model_code,
        # Note: item_type column removed from production database
        # Item type is determined from fg_code prefix (WP=FG, SP=SP)
        description=data.name,
        is_active=True,
    )
    db.add(model_ref)

    await db.commit()

    # Generate barcode format and example
    service = SerializationService(db)
    year_code = service.get_year_code()
    month_code = service.get_month_code()

    if data.item_type.value == "FG":
        barcode_format = f"AP + Year(2) + Month(1) + {data.model_code}(3) + Serial(8)"
        barcode_example = f"AP{year_code}{month_code}{data.model_code}00000001"
    else:
        barcode_format = f"AP + Supplier(2) + Year(1) + Month(1) + Channel(2) + Serial(8)"
        barcode_example = f"APFS{year_code[1]}{month_code}EC00000001"

    return CreateProductWithCodeResponse(
        success=True,
        message=f"Product created successfully with FG Code: {fg_code}",
        fg_code=fg_code,
        model_code=data.model_code,
        product_sku=fg_code,
        product_id=product_id,
        product_name=data.name,
        item_type=data.item_type,
        model_code_reference_id=model_ref_id,
        barcode_format=barcode_format,
        barcode_example=barcode_example,
    )


# ==================== Barcode Generation ====================

@router.post("/generate", response_model=GenerateSerialsResponse)
@require_module("oms_fulfillment")
async def generate_serials(
    data: GenerateSerialsRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Generate serial numbers/barcodes for a Purchase Order.

    Call this when a PO is approved and sent to vendor.
    The serials are sequential and continue from the last generated serial
    for the same model+supplier+year+month combination.
    """
    service = SerializationService(db)
    try:
        result = await service.generate_serials_for_po(data)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/preview", response_model=CodePreviewResponse)
@require_module("oms_fulfillment")
async def preview_codes(
    data: CodePreviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Preview what barcodes would be generated without saving.

    Useful for checking the next available serial numbers.
    """
    service = SerializationService(db)
    result = await service.preview_codes(
        supplier_code=data.supplier_code,
        model_code=data.model_code,
        quantity=data.quantity,
    )
    return result


# ==================== PO Serials ====================


@router.get("/serials")
@require_module("oms_fulfillment")
async def list_all_serials(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(50, ge=1, le=100, description="Page size"),
    item_type: Optional[str] = Query(None, description="Filter by item type (FG or SP)"),
    status: Optional[str] = Query(None, description="Filter by status"),
    search: Optional[str] = Query(None, description="Search by barcode or serial number"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List all serial numbers with pagination and filtering.

    This endpoint lists all po_serials (generated barcodes) across all POs.
    Use this for the Serial Numbers tab in Serialization section.
    """
    # Build query
    query = select(POSerial)
    count_query = select(func.count(POSerial.id))

    # Apply filters
    filters = []

    if item_type:
        filters.append(POSerial.item_type == item_type.upper())

    if status:
        filters.append(func.upper(POSerial.status) == status.upper())

    if search:
        search_filter = f"%{search}%"
        filters.append(
            (POSerial.barcode.ilike(search_filter)) |
            (POSerial.serial_number.cast(String).ilike(search_filter))
        )

    if filters:
        query = query.where(and_(*filters))
        count_query = count_query.where(and_(*filters))

    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination and ordering
    offset = (page - 1) * size
    query = query.order_by(POSerial.created_at.desc()).offset(offset).limit(size)

    # Execute query
    result = await db.execute(query)
    serials = result.scalars().all()

    # Calculate pages
    pages = (total + size - 1) // size if total > 0 else 0

    return {
        "items": [POSerialResponse.model_validate(s) for s in serials],
        "total": total,
        "page": page,
        "size": size,
        "pages": pages,
    }


@router.get("/po/{po_id}", response_model=POSerialsListResponse)
@require_module("oms_fulfillment")
async def get_po_serials(
    po_id: str,
    status: Optional[SerialStatus] = Query(None, description="Filter by status"),
    limit: int = Query(1000, le=10000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all serials for a Purchase Order"""
    service = SerializationService(db)

    serials = await service.get_serials_by_po(po_id, status=status, limit=limit, offset=offset)
    counts = await service.get_serials_count_by_po(po_id)

    return POSerialsListResponse(
        po_id=po_id,
        total=counts.get("total", 0),
        by_status=counts,
        serials=[POSerialResponse.model_validate(s) for s in serials],
    )


@router.get("/po/{po_id}/export")
@require_module("oms_fulfillment")
async def export_po_serials(
    po_id: str,
    format: str = Query("csv", pattern="^(csv|txt)$"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Export serials for a PO as CSV/TXT file.

    This can be sent to the vendor for barcode printing.
    """
    service = SerializationService(db)
    serials = await service.get_serials_by_po(po_id, limit=100000)

    if not serials:
        raise HTTPException(status_code=404, detail="No serials found for this PO")

    if format == "csv":
        # Generate CSV
        lines = ["Barcode,Model,Serial,Status"]
        for s in serials:
            lines.append(f"{s.barcode},{s.model_code},{s.serial_number},{s.status}")
        content = "\n".join(lines)
        media_type = "text/csv"
        filename = f"serials_{po_id}.csv"
    else:
        # Generate plain text (one barcode per line)
        content = "\n".join([s.barcode for s in serials])
        media_type = "text/plain"
        filename = f"serials_{po_id}.txt"

    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.post("/po/{po_id}/send-to-vendor")
@require_module("oms_fulfillment")
async def mark_serials_sent_to_vendor(
    po_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark all generated serials for a PO as sent to vendor"""
    service = SerializationService(db)
    count = await service.mark_serials_sent_to_vendor(po_id)
    return {"po_id": po_id, "serials_updated": count, "status": "sent_to_vendor"}


# ==================== Serial Scanning (GRN) ====================

@router.post("/scan", response_model=ScanSerialResponse)
@require_module("oms_fulfillment")
async def scan_serial(
    data: ScanSerialRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Scan and validate a barcode during GRN receiving.

    Marks the serial as RECEIVED if valid.
    """
    service = SerializationService(db)
    result = await service.scan_serial(
        barcode=data.barcode,
        grn_id=data.grn_id,
        grn_item_id=data.grn_item_id,
        user_id=current_user.id,
    )
    return result


@router.post("/scan/bulk", response_model=BulkScanResponse)
@require_module("oms_fulfillment")
async def bulk_scan_serials(
    data: BulkScanRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Scan multiple barcodes at once"""
    service = SerializationService(db)
    results = await service.bulk_scan_serials(
        barcodes=data.barcodes,
        grn_id=data.grn_id,
        user_id=current_user.id,
    )

    valid_count = sum(1 for r in results if r.is_valid)

    return BulkScanResponse(
        grn_id=data.grn_id,
        total_scanned=len(results),
        valid_count=valid_count,
        invalid_count=len(results) - valid_count,
        results=results,
    )


# ==================== Serial Lookup ====================

@router.get("/lookup/{barcode}", response_model=SerialLookupResponse)
@require_module("oms_fulfillment")
async def lookup_serial(
    barcode: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Look up full details of a serial by barcode.

    Returns PO info, product info, current location, warranty status, etc.
    """
    service = SerializationService(db)
    serial = await service.get_serial_by_barcode(barcode)

    if not serial:
        return SerialLookupResponse(
            barcode=barcode,
            found=False,
            serial=None,
        )

    # TODO: Fetch additional details (PO number, vendor name, product name, etc.)
    # For now, return basic info
    warranty_status = None
    if serial.warranty_end_date:
        if serial.warranty_end_date > datetime.now(timezone.utc):
            warranty_status = "ACTIVE"  # UPPERCASE per coding standards
        else:
            warranty_status = "EXPIRED"  # UPPERCASE per coding standards

    return SerialLookupResponse(
        barcode=barcode,
        found=True,
        serial=POSerialResponse.model_validate(serial),
        warranty_status=warranty_status,
    )


@router.post("/validate/{barcode}")
@require_module("oms_fulfillment")
async def validate_barcode(
    barcode: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Validate a barcode format and check if it exists.

    Does NOT update any status - just checks validity.
    """
    service = SerializationService(db)

    # Parse barcode to validate format
    try:
        parsed = service.parse_barcode(barcode)
    except ValueError as e:
        return {
            "barcode": barcode,
            "is_valid_format": False,
            "exists_in_db": False,
            "error": str(e),
        }

    # Check if exists in DB
    serial = await service.get_serial_by_barcode(barcode)

    return {
        "barcode": barcode,
        "is_valid_format": True,
        "exists_in_db": serial is not None,
        "parsed": parsed,
        "status": serial.status if serial else None,
    }


# ==================== Sequence Status ====================

@router.get("/sequence/{model_code}", response_model=SequenceStatusResponse)
@require_module("oms_fulfillment")
async def get_sequence_status(
    model_code: str,
    supplier_code: str = Query(..., min_length=2, max_length=2),
    year_code: Optional[str] = Query(None),
    month_code: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get current status of a serial sequence.

    Shows last serial used and next available serial.
    """
    service = SerializationService(db)
    result = await service.get_sequence_status(
        model_code=model_code,
        supplier_code=supplier_code,
        year_code=year_code,
        month_code=month_code,
    )
    return result


@router.post("/sequence/reset/{model_code}")
@require_module("oms_fulfillment")
async def reset_sequence(
    model_code: str,
    supplier_code: str = Query(..., min_length=2, max_length=2),
    new_last_serial: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Reset a sequence to a specific serial number.

    WARNING: This should only be used for corrections.
    Resetting to a lower number may cause duplicate barcodes!
    """
    service = SerializationService(db)
    year_code = service.get_year_code()
    month_code = service.get_month_code()

    result = await db.execute(
        select(SerialSequence).where(
            SerialSequence.model_code == model_code.upper(),
            SerialSequence.supplier_code == supplier_code.upper(),
            SerialSequence.year_code == year_code,
            SerialSequence.month_code == month_code,
        )
    )
    sequence = result.scalar_one_or_none()

    if not sequence:
        raise HTTPException(status_code=404, detail="Sequence not found")

    old_serial = sequence.last_serial
    sequence.last_serial = new_last_serial
    sequence.updated_at = datetime.now(timezone.utc)
    await db.commit()

    return {
        "model_code": model_code.upper(),
        "supplier_code": supplier_code.upper(),
        "year_code": year_code,
        "month_code": month_code,
        "old_last_serial": old_serial,
        "new_last_serial": new_last_serial,
    }


# ==================== Dashboard / Stats ====================

@router.get("/dashboard")
@require_module("oms_fulfillment")
async def serialization_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get serialization dashboard stats"""

    # Total serials by status
    status_result = await db.execute(
        select(
            POSerial.status,
            func.count(POSerial.id).label("count")
        ).group_by(POSerial.status)
    )
    status_counts = {row.status: row.count for row in status_result}

    # Total by month (current year)
    service = SerializationService(db)
    current_year_code = service.get_year_code()

    monthly_result = await db.execute(
        select(
            SerialSequence.month_code,
            func.sum(SerialSequence.total_generated).label("total")
        ).where(SerialSequence.year_code == current_year_code)
        .group_by(SerialSequence.month_code)
    )
    monthly_totals = {row.month_code: row.total or 0 for row in monthly_result}

    # Total supplier codes
    supplier_count = await db.execute(
        select(func.count(SupplierCode.id)).where(SupplierCode.is_active == True)
    )

    # Total model codes
    model_count = await db.execute(
        select(func.count(ModelCodeReference.id)).where(ModelCodeReference.is_active == True)
    )

    # Total serials
    total_serials = await db.execute(select(func.count(POSerial.id)))

    return {
        "total_serials": total_serials.scalar() or 0,
        "by_status": status_counts,
        "monthly_generation": monthly_totals,
        "active_supplier_codes": supplier_count.scalar() or 0,
        "active_model_codes": model_count.scalar() or 0,
        "current_year_code": current_year_code,
        "current_month_code": service.get_month_code(),
    }


# ==================== Seed / Reset Codes ====================

@router.post("/seed-codes")
@require_module("oms_fulfillment")
async def seed_serialization_codes(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    permissions: Permissions = None,
):
    """
    Reset and seed all model codes and supplier codes.

    WARNING: This deletes all existing codes and creates new ones.
    Only accessible by SUPER_ADMIN users.

    Creates proper codes for:
    - Water Purifier category (FG)
    - Spare Parts category (SP)
    - Supplier codes for vendors
    """
    # Only super admin can seed codes
    if not permissions or not permissions.is_super_admin():
        raise HTTPException(
            status_code=403,
            detail="Only Super Admin can seed serialization codes"
        )
    import uuid

    # Delete existing codes
    await db.execute(select(ModelCodeReference).execution_options(synchronize_session="fetch"))
    await db.execute(select(SupplierCode).execution_options(synchronize_session="fetch"))

    # Delete all model codes
    result = await db.execute(select(ModelCodeReference))
    for code in result.scalars().all():
        await db.delete(code)

    # Delete all supplier codes
    result = await db.execute(select(SupplierCode))
    for code in result.scalars().all():
        await db.delete(code)

    await db.flush()

    # ==================== SUPPLIER CODES ====================
    # These are 2-character codes for vendors/manufacturers

    supplier_codes_data = [
        # FG Suppliers (Finished Goods manufacturers)
        {"code": "FS", "name": "FastTrack Manufacturing", "description": "Primary FG manufacturer"},
        {"code": "ST", "name": "STOS Industries", "description": "Premium product manufacturer"},
        {"code": "AP", "name": "ILMS.AI In-house", "description": "In-house manufacturing"},

        # Spare Parts Suppliers
        {"code": "EC", "name": "Economical Spares", "description": "Budget spare parts supplier"},
        {"code": "PR", "name": "Premium Spares", "description": "Premium spare parts supplier"},
        {"code": "GN", "name": "Generic Parts", "description": "Generic replacement parts"},
    ]

    created_suppliers = []
    for data in supplier_codes_data:
        supplier = SupplierCode(
            id=str(uuid.uuid4()).replace("-", ""),
            code=data["code"],
            name=data["name"],
            description=data["description"],
            is_active=True,
        )
        db.add(supplier)
        created_suppliers.append(data["code"])

    # ==================== MODEL CODES - WATER PURIFIERS (FG) ====================
    # Format: WPRAIEL001 -> WP(Category) R(Subcategory) A(Brand) IEL(Model) 001(Seq)
    # Barcode Model Code: IEL (3 chars)

    water_purifier_codes = [
        # RO Water Purifiers - product_sku matches actual catalog SKU
        {"fg_code": "WPRAIEL001", "model_code": "IEL", "item_type": ItemType.FINISHED_GOODS,
         "product_sku": "WPIEL001", "description": "IELITZ RO Water Purifier"},
        {"fg_code": "WPRAIPX001", "model_code": "IPX", "item_type": ItemType.FINISHED_GOODS,
         "product_sku": "WPIPX001", "description": "IPX RO Water Purifier"},
        {"fg_code": "WPRAPRM001", "model_code": "PRM", "item_type": ItemType.FINISHED_GOODS,
         "product_sku": "WPPRM001", "description": "Premium RO Water Purifier"},

        # UV Water Purifiers
        {"fg_code": "WPUAUVX001", "model_code": "UVX", "item_type": ItemType.FINISHED_GOODS,
         "product_sku": "WPUVX001", "description": "UVX UV Water Purifier"},
        {"fg_code": "WPUAULX001", "model_code": "ULX", "item_type": ItemType.FINISHED_GOODS,
         "product_sku": "WPULX001", "description": "Ultra UV Water Purifier"},

        # Gravity Water Purifiers
        {"fg_code": "WPGAGRY001", "model_code": "GRY", "item_type": ItemType.FINISHED_GOODS,
         "product_sku": "WPGRY001", "description": "Gravity Water Purifier"},

        # RO+UV Combo
        {"fg_code": "WPCARUV001", "model_code": "RUV", "item_type": ItemType.FINISHED_GOODS,
         "product_sku": "WPRUV001", "description": "RO+UV Combo Water Purifier"},
    ]

    # ==================== MODEL CODES - SPARE PARTS (SP) ====================
    # Format: SPSDFSDF001 -> SP(Category) SD(Subcategory) F(Brand) SDF(Model) 001(Seq)
    # Barcode Channel Code: EC or PR (based on supplier)

    spare_parts_codes = [
        # Sediment Filters - product_sku matches actual catalog SKU
        {"fg_code": "SPSDFSD001", "model_code": "SDF", "item_type": ItemType.SPARE_PART,
         "product_sku": "SPSDF001", "description": "Sediment Filter (PP Yarn Wound) 10\""},
        {"fg_code": "SPSDFSD002", "model_code": "SD2", "item_type": ItemType.SPARE_PART,
         "product_sku": "SPSDF002", "description": "Sediment Filter 20\""},

        # Carbon Filters
        {"fg_code": "SPCBFCB001", "model_code": "CBF", "item_type": ItemType.SPARE_PART,
         "product_sku": "SPCBF001", "description": "Carbon Block Filter 10\""},
        {"fg_code": "SPCBFCB002", "model_code": "CB2", "item_type": ItemType.SPARE_PART,
         "product_sku": "SPCBF002", "description": "Granular Activated Carbon Filter"},

        # Alkaline Filters
        {"fg_code": "SPALFAL001", "model_code": "ALK", "item_type": ItemType.SPARE_PART,
         "product_sku": "SPALK001", "description": "Alkaline Mineral Block"},
        {"fg_code": "SPALFAL002", "model_code": "AL2", "item_type": ItemType.SPARE_PART,
         "product_sku": "SPALK002", "description": "Alkaline Cartridge"},

        # RO Membranes
        {"fg_code": "SPMBFMB001", "model_code": "MBR", "item_type": ItemType.SPARE_PART,
         "product_sku": "SPMBR001", "description": "RO Membrane 80 GPD"},
        {"fg_code": "SPMBFMB002", "model_code": "MB2", "item_type": ItemType.SPARE_PART,
         "product_sku": "SPMBR002", "description": "RO Membrane 100 GPD"},

        # UV Lamps
        {"fg_code": "SPUVLUL001", "model_code": "UVL", "item_type": ItemType.SPARE_PART,
         "product_sku": "SPUVL001", "description": "UV Lamp 11W"},
        {"fg_code": "SPUVLUL002", "model_code": "UV2", "item_type": ItemType.SPARE_PART,
         "product_sku": "SPUVL002", "description": "UV Lamp 16W"},

        # Pumps
        {"fg_code": "SPPMPPM001", "model_code": "PMP", "item_type": ItemType.SPARE_PART,
         "product_sku": "SPPMP001", "description": "Booster Pump 100 GPD"},
        {"fg_code": "SPPMPPM002", "model_code": "PM2", "item_type": ItemType.SPARE_PART,
         "product_sku": "SPPMP002", "description": "Booster Pump 75 GPD"},

        # SMPS / Adapters
        {"fg_code": "SPSMPSM001", "model_code": "SMP", "item_type": ItemType.SPARE_PART,
         "product_sku": "SPSMP001", "description": "SMPS 24V 2.5A"},
        {"fg_code": "SPSMPSM002", "model_code": "SM2", "item_type": ItemType.SPARE_PART,
         "product_sku": "SPSMP002", "description": "SMPS 36V 2A"},

        # Solenoid Valves
        {"fg_code": "SPSVLSV001", "model_code": "SVL", "item_type": ItemType.SPARE_PART,
         "product_sku": "SPSVL001", "description": "Solenoid Valve 24V"},

        # Flow Restrictors
        {"fg_code": "SPFRFFR001", "model_code": "FRF", "item_type": ItemType.SPARE_PART,
         "product_sku": "SPFRF001", "description": "Flow Restrictor 300ml"},

        # Connectors & Fittings
        {"fg_code": "SPCNFCN001", "model_code": "CNF", "item_type": ItemType.SPARE_PART,
         "product_sku": "SPCNF001", "description": "Quick Connect Fittings Set"},

        # Tubing
        {"fg_code": "SPTBGTB001", "model_code": "TBG", "item_type": ItemType.SPARE_PART,
         "product_sku": "SPTBG001", "description": "PE Tubing 1/4\" (10m)"},

        # Tanks
        {"fg_code": "SPTNKTN001", "model_code": "TNK", "item_type": ItemType.SPARE_PART,
         "product_sku": "SPTNK001", "description": "Storage Tank 8L"},
        {"fg_code": "SPTNKTN002", "model_code": "TN2", "item_type": ItemType.SPARE_PART,
         "product_sku": "SPTNK002", "description": "Storage Tank 12L"},

        # Pre-Filter Housing
        {"fg_code": "SPPFHPF001", "model_code": "PFH", "item_type": ItemType.SPARE_PART,
         "product_sku": "SPPFH001", "description": "Pre-Filter Housing 10\""},
    ]

    created_model_codes = []

    # Get ALL products from database to link by product_id
    products_result = await db.execute(select(Product))
    all_products = {p.sku: p for p in products_result.scalars().all()}

    # Add Water Purifier codes
    for data in water_purifier_codes:
        # Try to find matching product by SKU
        product = all_products.get(data["product_sku"])
        product_id = product.id if product else None

        model_ref = ModelCodeReference(
            id=uuid.uuid4(),
            product_id=product_id,  # Link to actual product
            fg_code=data["fg_code"],
            model_code=data["model_code"],
            # Note: item_type removed - determined from fg_code prefix
            product_sku=data["product_sku"],
            description=data["description"],
            is_active=True,
        )
        db.add(model_ref)
        created_model_codes.append({
            "fg_code": data["fg_code"],
            "model_code": data["model_code"],
            "product_sku": data["product_sku"],
            "product_linked": product_id is not None,
            "type": "FG"
        })

    # Add Spare Parts codes
    for data in spare_parts_codes:
        # Try to find matching product by SKU
        product = all_products.get(data["product_sku"])
        product_id = product.id if product else None

        model_ref = ModelCodeReference(
            id=uuid.uuid4(),
            product_id=product_id,  # Link to actual product
            fg_code=data["fg_code"],
            model_code=data["model_code"],
            # Note: item_type removed - determined from fg_code prefix
            product_sku=data["product_sku"],
            description=data["description"],
            is_active=True,
        )
        db.add(model_ref)
        created_model_codes.append({
            "fg_code": data["fg_code"],
            "model_code": data["model_code"],
            "product_sku": data["product_sku"],
            "product_linked": product_id is not None,
            "type": "SP"
        })

    await db.commit()

    return {
        "success": True,
        "message": "Serialization codes seeded successfully",
        "supplier_codes_created": len(created_suppliers),
        "supplier_codes": created_suppliers,
        "model_codes_created": len(created_model_codes),
        "model_codes": {
            "water_purifiers": [c for c in created_model_codes if c["type"] == "FG"],
            "spare_parts": [c for c in created_model_codes if c["type"] == "SP"],
        },
        "barcode_format": {
            "finished_goods": "AP + YearCode(2) + MonthCode(1) + ModelCode(3) + Serial(8) = 16 chars",
            "spare_parts": "AP + SupplierCode(2) + YearCode(1) + MonthCode(1) + ChannelCode(2) + Serial(8) = 16 chars",
        },
        "examples": {
            "fg_barcode": "APAAAIIEL00000001 (IELITZ Water Purifier, Jan 2026, Serial 1)",
            "sp_barcode_economical": "APFSAAEC00000001 (Economical spare from FastTrack)",
            "sp_barcode_premium": "APSTAAPR00000001 (Premium spare from STOS)",
        },
        "products_found_in_db": len(all_products),
        "products_linked": len([c for c in created_model_codes if c.get("product_linked")])
    }


@router.post("/auto-link-products")
@require_module("oms_fulfillment")
async def auto_link_products_to_model_codes(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    permissions: Permissions = None,
):
    """
    Auto-link existing products to model codes.

    This endpoint will:
    1. Get all products from the database
    2. Get all model codes
    3. Try to match them by SKU
    4. Update model codes with product_id where matches are found

    This is useful when products exist but weren't linked to model codes.
    """
    # Only super admin can auto-link
    if not permissions or not permissions.is_super_admin():
        raise HTTPException(
            status_code=403,
            detail="Only Super Admin can auto-link products"
        )

    # Get all products
    products_result = await db.execute(select(Product))
    all_products = {p.sku: p for p in products_result.scalars().all()}

    # Get all model codes
    model_codes_result = await db.execute(select(ModelCodeReference))
    all_model_codes = model_codes_result.scalars().all()

    linked_count = 0
    already_linked = 0
    not_found = []

    for mc in all_model_codes:
        # Skip if already linked
        if mc.product_id:
            already_linked += 1
            continue

        # Try to find product by product_sku
        product = all_products.get(mc.product_sku)

        if product:
            mc.product_id = product.id
            linked_count += 1
        else:
            not_found.append({"fg_code": mc.fg_code, "product_sku": mc.product_sku})

    await db.commit()

    return {
        "success": True,
        "message": f"Auto-linked {linked_count} model codes to products",
        "total_model_codes": len(all_model_codes),
        "already_linked": already_linked,
        "newly_linked": linked_count,
        "not_found": not_found,
        "products_in_db": len(all_products),
        "tip": "If products are not found, the product SKU in your catalog might be different. Use 'Create New Product' in Serialization to create products with correct codes."
    }


@router.post("/link-product-model-code")
@require_module("oms_fulfillment")
async def link_product_to_model_code(
    product_id: str = Query(..., description="Product ID to link"),
    model_code: str = Query(..., min_length=3, max_length=3, description="3-letter model code"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Manually link an existing product to a model code.

    This creates or updates the ModelCodeReference for a product.
    Use this when you have existing products that need model codes for barcode generation.
    """
    import uuid as uuid_module

    # Get the product
    result = await db.execute(
        select(Product).where(Product.id == product_id)
    )
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(status_code=404, detail=f"Product {product_id} not found")

    # Check if model code reference already exists for this product
    existing_ref = await db.execute(
        select(ModelCodeReference).where(ModelCodeReference.product_id == product_id)
    )
    model_ref = existing_ref.scalar_one_or_none()

    if model_ref:
        # Update existing
        model_ref.model_code = model_code.upper()
        model_ref.product_sku = product.sku
        model_ref.fg_code = product.fg_code or product.sku
        model_ref.description = product.name
        message = "Updated existing model code reference"
    else:
        # Create new
        # Note: item_type removed - determined from fg_code prefix
        model_ref = ModelCodeReference(
            id=str(uuid_module.uuid4()).replace("-", ""),
            product_id=product_id,
            product_sku=product.sku,
            fg_code=product.fg_code or product.sku,
            model_code=model_code.upper(),
            description=product.name,
            is_active=True,
        )
        db.add(model_ref)
        message = "Created new model code reference"

    await db.commit()

    return {
        "success": True,
        "message": message,
        "product_id": product_id,
        "product_sku": product.sku,
        "product_name": product.name,
        "model_code": model_code.upper(),
        "fg_code": model_ref.fg_code,
    }


@router.post("/sync-products-to-model-codes")
@require_module("oms_fulfillment")
async def sync_products_to_model_codes(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    permissions: Permissions = None,
):
    """
    Create model codes for ALL existing products that don't have one.

    This is the reverse of auto-link - it creates ModelCodeReferences for products
    that exist but don't have a model code assigned.

    For each product:
    - Creates a ModelCodeReference
    - Generates model_code from first 3 chars of SKU
    - Links by product_id
    """
    import re
    import uuid

    # Only super admin can sync
    if not permissions or not permissions.is_super_admin():
        raise HTTPException(
            status_code=403,
            detail="Only Super Admin can sync products"
        )

    # Get all products
    products_result = await db.execute(select(Product))
    all_products = products_result.scalars().all()

    # Get existing model codes to avoid duplicates
    model_codes_result = await db.execute(select(ModelCodeReference))
    existing_model_codes = {mc.product_id: mc for mc in model_codes_result.scalars().all() if mc.product_id}
    existing_skus = {mc.product_sku: mc for mc in model_codes_result.scalars().all() if mc.product_sku}

    created_count = 0
    skipped_count = 0
    created_codes = []

    for product in all_products:
        # Skip if already has a model code
        if product.id in existing_model_codes or product.sku in existing_skus:
            skipped_count += 1
            continue

        # Generate model code from SKU (first 3 alpha chars after category prefix)
        sku = product.sku or ""
        # Try to extract 3-letter model code
        # For SKU like "SPSDF001", extract "SDF"
        # For SKU like "WPIEL001", extract "IEL"
        alpha_chars = re.findall(r'[A-Z]', sku.upper())
        if len(alpha_chars) >= 5:
            # Skip first 2 chars (category), take next 3
            model_code = ''.join(alpha_chars[2:5])
        elif len(alpha_chars) >= 3:
            model_code = ''.join(alpha_chars[:3])
        else:
            model_code = sku[:3].upper() if len(sku) >= 3 else "UNK"

        # Create model code reference
        # Note: item_type removed - determined from fg_code prefix
        model_ref = ModelCodeReference(
            id=uuid.uuid4(),
            product_id=product.id,
            product_sku=product.sku,
            fg_code=product.fg_code or product.sku,  # Use fg_code if available, else sku
            model_code=model_code,
            description=product.name,
            is_active=True,
        )
        db.add(model_ref)
        created_count += 1
        created_codes.append({
            "product_sku": product.sku,
            "product_name": product.name,
            "model_code": model_code,
            "fg_code": model_ref.fg_code,
            "item_type": item_type.value
        })

    await db.commit()

    return {
        "success": True,
        "message": f"Created {created_count} model codes for products",
        "total_products": len(all_products),
        "created": created_count,
        "skipped": skipped_count,
        "created_codes": created_codes
    }


# ==================== PRODUCT ORCHESTRATION SYNC ====================

@router.post(
    "/sync-products",
    summary="Sync existing products with serialization",
    description="One-time sync for existing FG/SP products that don't have model codes or serial sequences. Creates ModelCodeReference and ProductSerialSequence entries.",
)
@require_module("oms_fulfillment")
async def sync_existing_products(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Sync existing products with serialization module.

    This utility:
    1. Finds all FG/SP products without model codes
    2. Auto-generates 3-letter model codes from product names
    3. Creates ModelCodeReference entries
    4. Creates ProductSerialSequence entries

    Only run this once after initial setup or when products were created
    before orchestration was implemented.
    """
    from app.services.product_orchestration_service import ProductOrchestrationService

    orchestration = ProductOrchestrationService(db)
    result = await orchestration.sync_existing_products()

    return {
        "success": True,
        "message": f"Synced {result['total_synced']} products with serialization",
        **result
    }
