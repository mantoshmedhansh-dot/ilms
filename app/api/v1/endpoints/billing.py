"""API endpoints for Billing & E-Invoice module (GST Compliant)."""
from typing import Optional, List
from uuid import UUID
from datetime import date, datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.billing import (
    TaxInvoice, InvoiceItem, InvoiceType, InvoiceStatus,
    CreditDebitNote, CreditDebitNoteItem, DocumentType, NoteReason,
    EWayBill, EWayBillItem, EWayBillStatus,
    PaymentReceipt, PaymentMode,
    InvoiceNumberSequence,
)
from app.models.order import Order
from app.models.customer import Customer
from app.models.dealer import Dealer
from app.models.user import User
from app.schemas.billing import (
    # TaxInvoice
    InvoiceCreate, InvoiceUpdate, InvoiceResponse, InvoiceBrief, InvoiceListResponse,
    InvoiceItemCreate,
    # Credit/Debit Note
    CreditDebitNoteCreate, CreditDebitNoteResponse, CreditDebitNoteListResponse,
    # E-Way Bill
    EWayBillCreate, EWayBillUpdate, EWayBillResponse, EWayBillListResponse,
    # Payment Receipt
    PaymentReceiptCreate, PaymentReceiptResponse, PaymentReceiptListResponse,
    # Reports
    GSTReportRequest, GSTR1Response, GSTR3BResponse,
    # E-Invoice/E-Way Bill Operations
    IRNCancelRequest, PartBUpdateRequest, EWBCancelRequest, EWBExtendRequest,
)
from app.api.deps import DB, CurrentUser, get_current_user, require_permissions
from app.services.audit_service import AuditService
from app.services.gst_einvoice_service import GSTEInvoiceService, GSTEInvoiceError
from app.services.gst_ewaybill_service import GSTEWayBillService, GSTEWayBillError
from app.services.auto_journal_service import AutoJournalService, AutoJournalError
from app.core.module_decorators import require_module

router = APIRouter()


# ==================== TaxInvoice ====================

@router.post("/invoices", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
@require_module("finance")
async def create_invoice(
    invoice_in: InvoiceCreate,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Create a new tax invoice."""
    # Map invoice type to series code
    series_code_map = {
        InvoiceType.TAX_INVOICE: "INV",
        InvoiceType.PROFORMA: "PI",
        InvoiceType.DELIVERY_CHALLAN: "DC",
        InvoiceType.EXPORT: "EXP",
        InvoiceType.SEZ: "SEZ",
        InvoiceType.DEEMED_EXPORT: "DE",
    }
    series_code = series_code_map.get(invoice_in.invoice_type, "INV")

    # Get current financial year
    from datetime import datetime
    now = datetime.now(timezone.utc)
    if now.month >= 4:
        financial_year = f"{now.year}-{str(now.year + 1)[2:]}"
    else:
        financial_year = f"{now.year - 1}-{str(now.year)[2:]}"

    # Generate invoice number from sequence
    sequence_result = await db.execute(
        select(InvoiceNumberSequence).where(
            and_(
                InvoiceNumberSequence.series_code == series_code,
                InvoiceNumberSequence.financial_year == financial_year,
                InvoiceNumberSequence.is_active == True,
            )
        )
    )
    sequence = sequence_result.scalar_one_or_none()

    if not sequence:
        # Create default sequence
        sequence = InvoiceNumberSequence(
            series_code=series_code,
            series_name=f"{invoice_in.invoice_type.value} Series",
            financial_year=financial_year,
            prefix=f"{series_code}/{financial_year}/",
            current_number=0,
        )
        db.add(sequence)
        await db.flush()

    sequence.current_number += 1
    invoice_number = f"{sequence.prefix}{str(sequence.current_number).zfill(sequence.padding_length)}"

    # Determine if inter-state
    shipping_state_code = invoice_in.shipping_state_code or invoice_in.billing_state_code
    is_inter_state = invoice_in.billing_state_code != shipping_state_code

    # Create invoice with initial zero values (will be updated after items)
    invoice = TaxInvoice(
        invoice_number=invoice_number,
        invoice_type=invoice_in.invoice_type,
        invoice_date=invoice_in.invoice_date,
        due_date=invoice_in.due_date,
        order_id=invoice_in.order_id,
        customer_id=invoice_in.customer_id,
        # Customer name (mapped from schema)
        customer_name=invoice_in.customer_name,
        customer_gstin=invoice_in.customer_gstin,
        # Billing Address (mapped from schema)
        billing_address_line1=invoice_in.billing_address_line1,
        billing_address_line2=invoice_in.billing_address_line2,
        billing_city=invoice_in.billing_city,
        billing_state=invoice_in.billing_state,
        billing_state_code=invoice_in.billing_state_code,
        billing_pincode=invoice_in.billing_pincode,
        # Shipping Address
        shipping_address_line1=invoice_in.shipping_address_line1 or invoice_in.billing_address_line1,
        shipping_address_line2=invoice_in.shipping_address_line2,
        shipping_city=invoice_in.shipping_city or invoice_in.billing_city,
        shipping_state=invoice_in.shipping_state or invoice_in.billing_state,
        shipping_state_code=shipping_state_code,
        shipping_pincode=invoice_in.shipping_pincode or invoice_in.billing_pincode,
        # Seller Info
        seller_gstin=invoice_in.seller_gstin,
        seller_name=invoice_in.seller_name,
        seller_address=invoice_in.seller_address,
        seller_state_code=invoice_in.seller_state_code,
        place_of_supply=invoice_in.place_of_supply,
        place_of_supply_code=invoice_in.place_of_supply_code,
        is_interstate=is_inter_state,
        is_reverse_charge=invoice_in.is_reverse_charge,
        # Other charges
        shipping_charges=invoice_in.shipping_charges,
        packaging_charges=invoice_in.packaging_charges,
        other_charges=invoice_in.other_charges,
        # Terms
        payment_terms=invoice_in.payment_terms,
        terms_and_conditions=invoice_in.terms_and_conditions,
        internal_notes=invoice_in.internal_notes,
        customer_notes=invoice_in.customer_notes,
        created_by=current_user.id,
        # Initialize totals to zero (will be updated after items are added)
        subtotal=Decimal("0"),
        taxable_amount=Decimal("0"),
        total_tax=Decimal("0"),
        grand_total=Decimal("0"),
        amount_due=Decimal("0"),
    )

    db.add(invoice)
    await db.flush()

    # Create invoice items and calculate totals
    subtotal = Decimal("0")
    total_discount = Decimal("0")
    taxable_amount = Decimal("0")
    cgst_total = Decimal("0")
    sgst_total = Decimal("0")
    igst_total = Decimal("0")
    cess_total = Decimal("0")
    line_number = 0

    for item_data in invoice_in.items:
        line_number += 1

        # Calculate item amounts
        gross_amount = item_data.quantity * item_data.unit_price
        discount_amount = gross_amount * (item_data.discount_percentage / 100)
        item_taxable = gross_amount - discount_amount

        # GST calculation based on inter/intra state
        gst_rate = item_data.gst_rate
        if is_inter_state:
            igst_rate = gst_rate
            cgst_rate = Decimal("0")
            sgst_rate = Decimal("0")
        else:
            igst_rate = Decimal("0")
            cgst_rate = gst_rate / 2
            sgst_rate = gst_rate / 2

        cgst_amount = item_taxable * (cgst_rate / 100)
        sgst_amount = item_taxable * (sgst_rate / 100)
        igst_amount = item_taxable * (igst_rate / 100)
        cess_amount = item_taxable * (item_data.cess_rate / 100) if item_data.cess_rate else Decimal("0")

        item_total = item_taxable + cgst_amount + sgst_amount + igst_amount + cess_amount

        # Calculate total tax for this item
        item_total_tax = cgst_amount + sgst_amount + igst_amount + cess_amount

        item = InvoiceItem(
            invoice_id=invoice.id,
            product_id=item_data.product_id,
            variant_id=item_data.variant_id,
            sku=item_data.sku,
            item_name=item_data.item_name,
            item_description=item_data.item_description,
            hsn_code=item_data.hsn_code,
            is_service=item_data.is_service,
            serial_numbers={"serials": item_data.serial_numbers} if item_data.serial_numbers else None,
            quantity=item_data.quantity,
            uom=item_data.uom,
            unit_price=item_data.unit_price,
            mrp=item_data.mrp,
            discount_percentage=item_data.discount_percentage,
            discount_amount=discount_amount,
            taxable_value=item_taxable,
            gst_rate=gst_rate,
            cgst_rate=cgst_rate,
            sgst_rate=sgst_rate,
            igst_rate=igst_rate,
            cgst_amount=cgst_amount,
            sgst_amount=sgst_amount,
            igst_amount=igst_amount,
            cess_rate=Decimal("0"),  # No cess for now
            cess_amount=cess_amount,
            total_tax=item_total_tax,
            line_total=item_total,
            warranty_months=item_data.warranty_months,
            order_item_id=item_data.order_item_id,
        )
        db.add(item)

        subtotal += gross_amount
        total_discount += discount_amount
        taxable_amount += item_taxable
        cgst_total += cgst_amount
        sgst_total += sgst_amount
        igst_total += igst_amount
        cess_total += cess_amount

    # Update invoice totals
    total_tax = cgst_total + sgst_total + igst_total + cess_total
    grand_total = taxable_amount + total_tax

    # Apply round off
    round_off = round(grand_total) - grand_total
    grand_total = round(grand_total)

    invoice.subtotal = subtotal
    invoice.discount_amount = total_discount
    invoice.taxable_amount = taxable_amount
    invoice.cgst_amount = cgst_total
    invoice.sgst_amount = sgst_total
    invoice.igst_amount = igst_total
    invoice.cess_amount = cess_total
    invoice.total_tax = total_tax
    invoice.round_off = round_off
    invoice.grand_total = grand_total
    invoice.amount_due = grand_total

    await db.commit()

    # Post accounting entry for the invoice
    try:
        from app.services.accounting_service import AccountingService
        accounting = AccountingService(db)
        await accounting.post_sales_invoice(
            invoice_id=invoice.id,
            customer_name=invoice.customer_name,
            subtotal=taxable_amount,
            cgst=cgst_total,
            sgst=sgst_total,
            igst=igst_total,
            total=grand_total,
            is_interstate=is_inter_state,
            product_type="purifier",  # Default, can be enhanced to detect from items
        )
        await db.commit()
    except Exception as e:
        # Log but don't fail invoice creation if accounting fails
        import logging
        logging.warning(f"Failed to post accounting entry for invoice {invoice.invoice_number}: {e}")

    # Load full invoice
    result = await db.execute(
        select(TaxInvoice)
        .options(selectinload(TaxInvoice.items))
        .where(TaxInvoice.id == invoice.id)
    )
    invoice = result.scalar_one()

    return invoice


@router.get("/invoices", response_model=InvoiceListResponse)
@require_module("finance")
async def list_invoices(
    db: DB,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    invoice_type: Optional[InvoiceType] = None,
    status: Optional[InvoiceStatus] = None,
    customer_id: Optional[UUID] = None,
    dealer_id: Optional[UUID] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    search: Optional[str] = None,
    current_user: User = Depends(get_current_user),
):
    """List invoices with filters."""
    query = select(TaxInvoice)
    count_query = select(func.count(TaxInvoice.id))
    value_query = select(func.coalesce(func.sum(TaxInvoice.grand_total), 0))

    filters = []
    if invoice_type:
        filters.append(TaxInvoice.invoice_type == invoice_type)
    if status:
        filters.append(TaxInvoice.status == status)
    if customer_id:
        filters.append(TaxInvoice.customer_id == customer_id)
    if dealer_id:
        filters.append(TaxInvoice.dealer_id == dealer_id)
    if start_date:
        filters.append(TaxInvoice.invoice_date >= start_date)
    if end_date:
        filters.append(TaxInvoice.invoice_date <= end_date)
    if search:
        filters.append(or_(
            TaxInvoice.invoice_number.ilike(f"%{search}%"),
            TaxInvoice.billing_name.ilike(f"%{search}%"),
        ))

    if filters:
        query = query.where(and_(*filters))
        count_query = count_query.where(and_(*filters))
        value_query = value_query.where(and_(*filters))

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    total_value_result = await db.execute(value_query)
    total_value = total_value_result.scalar() or Decimal("0")

    query = query.order_by(TaxInvoice.invoice_date.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    invoices = result.scalars().all()

    return InvoiceListResponse(
        items=[InvoiceBrief.model_validate(inv) for inv in invoices],
        total=total,
        total_value=total_value,
        skip=skip,
        limit=limit
    )


@router.get("/invoices/{invoice_id}", response_model=InvoiceResponse)
@require_module("finance")
async def get_invoice(
    invoice_id: UUID,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Get invoice by ID."""
    result = await db.execute(
        select(TaxInvoice)
        .options(selectinload(TaxInvoice.items))
        .where(TaxInvoice.id == invoice_id)
    )
    invoice = result.scalar_one_or_none()

    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    return invoice


@router.post("/invoices/{invoice_id}/generate-irn", response_model=InvoiceResponse)
@require_module("finance")
async def generate_einvoice_irn(
    invoice_id: UUID,
    db: DB,
    company_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_user),
):
    """
    Generate IRN (Invoice Reference Number) from GST E-Invoice portal.

    This integrates with NIC (National Informatics Centre) E-Invoice API to:
    - Authenticate with GST portal
    - Submit invoice data in prescribed JSON format
    - Receive IRN, ACK number, signed QR code
    - Update invoice with E-Invoice details

    Requirements:
    - Company must have E-Invoice enabled
    - E-Invoice credentials must be configured
    - Invoice must be a B2B invoice (customer has GSTIN)
    """
    # Get invoice
    result = await db.execute(
        select(TaxInvoice)
        .options(selectinload(TaxInvoice.items))
        .where(TaxInvoice.id == invoice_id)
    )
    invoice = result.scalar_one_or_none()

    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    if invoice.irn:
        raise HTTPException(status_code=400, detail="IRN already generated for this invoice")

    # Check if B2B invoice (GSTIN required for E-Invoice)
    if not invoice.customer_gstin:
        raise HTTPException(
            status_code=400,
            detail="E-Invoice is only applicable for B2B invoices (customer GSTIN required)"
        )

    # Determine company_id - use from invoice or parameter
    effective_company_id = company_id or current_user.company_id

    if not effective_company_id:
        raise HTTPException(
            status_code=400,
            detail="Company ID is required for E-Invoice generation"
        )

    try:
        # Initialize E-Invoice service
        einvoice_service = GSTEInvoiceService(db, effective_company_id)

        # Generate IRN via NIC portal
        irn_result = await einvoice_service.generate_irn(invoice_id)

        # Update invoice with E-Invoice details
        invoice.irn = irn_result.get("irn")
        invoice.irn_generated_at = datetime.now(timezone.utc)
        invoice.ack_number = irn_result.get("ack_number")
        invoice.ack_date = datetime.fromisoformat(irn_result["ack_date"]) if irn_result.get("ack_date") else datetime.now(timezone.utc)
        invoice.signed_qr_code = irn_result.get("signed_qr_code")
        invoice.signed_invoice_data = irn_result.get("signed_invoice")
        invoice.status = InvoiceStatus.IRN_GENERATED.value

        await db.commit()
        await db.refresh(invoice)

        # Log successful IRN generation
        try:
            audit_service = AuditService(db)
            await audit_service.log_action(
                user_id=current_user.id,
                action="GENERATE_IRN",
                entity_type="TaxInvoice",
                entity_id=invoice_id,
                details={
                    "irn": invoice.irn,
                    "ack_number": invoice.ack_number,
                    "invoice_number": invoice.invoice_number
                }
            )
        except Exception:
            pass  # Don't fail if audit logging fails

        return invoice

    except GSTEInvoiceError as e:
        raise HTTPException(
            status_code=400,
            detail=f"E-Invoice generation failed: {e.message}",
            headers={"X-Error-Code": e.error_code or "EINVOICE_ERROR"}
        )


@router.post("/invoices/{invoice_id}/cancel-irn", response_model=InvoiceResponse)
@require_module("finance")
async def cancel_einvoice_irn(
    invoice_id: UUID,
    cancel_request: IRNCancelRequest,
    db: DB,
    company_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_user),
):
    """
    Cancel IRN within 24 hours of generation.

    As per GST rules, an IRN can only be cancelled within 24 hours of generation.
    After 24 hours, you must issue a Credit Note instead.

    Valid reason codes:
    - "1": Duplicate invoice
    - "2": Data entry mistake
    - "3": Order cancelled
    - "4": Others
    """
    result = await db.execute(
        select(TaxInvoice)
        .options(selectinload(TaxInvoice.items))
        .where(TaxInvoice.id == invoice_id)
    )
    invoice = result.scalar_one_or_none()

    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    if not invoice.irn:
        raise HTTPException(status_code=400, detail="No IRN exists for this invoice")

    if invoice.status == InvoiceStatus.IRN_CANCELLED:
        raise HTTPException(status_code=400, detail="IRN is already cancelled")

    # Check 24 hour window
    if invoice.irn_generated_at:
        hours_elapsed = (datetime.now(timezone.utc) - invoice.irn_generated_at).total_seconds() / 3600
        if hours_elapsed > 24:
            raise HTTPException(
                status_code=400,
                detail="IRN cancellation window expired. IRN can only be cancelled within 24 hours. Please issue a Credit Note instead."
            )

    # Validate reason code
    valid_reasons = ["1", "2", "3", "4"]
    if cancel_request.reason not in valid_reasons:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid reason code. Valid codes: 1=Duplicate, 2=Data Entry Mistake, 3=Order Cancelled, 4=Others"
        )

    # Determine company_id
    effective_company_id = company_id or current_user.company_id

    if not effective_company_id:
        raise HTTPException(
            status_code=400,
            detail="Company ID is required for IRN cancellation"
        )

    try:
        # Initialize E-Invoice service
        einvoice_service = GSTEInvoiceService(db, effective_company_id)

        # Cancel IRN via NIC portal
        cancel_result = await einvoice_service.cancel_irn(
            invoice_id=invoice_id,
            reason=cancel_request.reason,
            cancel_remarks=cancel_request.remarks
        )

        # Update invoice status
        invoice.irn_cancelled_at = datetime.now(timezone.utc)
        invoice.irn_cancel_reason = cancel_request.reason
        invoice.status = InvoiceStatus.IRN_CANCELLED.value

        await db.commit()
        await db.refresh(invoice)

        # Log IRN cancellation
        try:
            audit_service = AuditService(db)
            await audit_service.log_action(
                user_id=current_user.id,
                action="CANCEL_IRN",
                entity_type="TaxInvoice",
                entity_id=invoice_id,
                details={
                    "irn": invoice.irn,
                    "reason": cancel_request.reason,
                    "remarks": cancel_request.remarks,
                    "invoice_number": invoice.invoice_number
                }
            )
        except Exception:
            pass  # Don't fail if audit logging fails

        return invoice

    except GSTEInvoiceError as e:
        raise HTTPException(
            status_code=400,
            detail=f"IRN cancellation failed: {e.message}",
            headers={"X-Error-Code": e.error_code or "EINVOICE_ERROR"}
        )


@router.get("/invoices/{invoice_id}/irn-details")
@require_module("finance")
async def get_irn_details(
    invoice_id: UUID,
    db: DB,
    company_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_user),
):
    """
    Get IRN details from GST portal for an invoice.

    Returns the full E-Invoice details including signed QR code.
    """
    result = await db.execute(
        select(TaxInvoice)
        .options(selectinload(TaxInvoice.items))
        .where(TaxInvoice.id == invoice_id)
    )
    invoice = result.scalar_one_or_none()

    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    if not invoice.irn:
        raise HTTPException(status_code=400, detail="No IRN exists for this invoice")

    effective_company_id = company_id or current_user.company_id

    if not effective_company_id:
        raise HTTPException(
            status_code=400,
            detail="Company ID is required"
        )

    try:
        einvoice_service = GSTEInvoiceService(db, effective_company_id)
        irn_details = await einvoice_service.get_irn_details(invoice.irn)

        return {
            "invoice_id": str(invoice_id),
            "invoice_number": invoice.invoice_number,
            "irn": invoice.irn,
            "ack_number": invoice.ack_number,
            "ack_date": invoice.ack_date,
            "irn_generated_at": invoice.irn_generated_at,
            "signed_qr_code": invoice.signed_qr_code,
            "portal_details": irn_details
        }

    except GSTEInvoiceError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to get IRN details: {e.message}",
            headers={"X-Error-Code": e.error_code or "EINVOICE_ERROR"}
        )


@router.get("/invoices/{invoice_id}/qr-code")
@require_module("finance")
async def get_invoice_qr_code(
    invoice_id: UUID,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """
    Get QR code image for an E-Invoice.

    Returns PNG image of the signed QR code.
    """
    from fastapi.responses import Response
    from app.services.gst_einvoice_service import generate_qr_code_image

    result = await db.execute(
        select(TaxInvoice).where(TaxInvoice.id == invoice_id)
    )
    invoice = result.scalar_one_or_none()

    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    if not invoice.signed_qr_code:
        raise HTTPException(
            status_code=400,
            detail="No QR code available. Generate IRN first."
        )

    try:
        qr_image = generate_qr_code_image(invoice.signed_qr_code)
        return Response(
            content=qr_image,
            media_type="image/png",
            headers={
                "Content-Disposition": f"inline; filename=qr_{invoice.invoice_number}.png"
            }
        )
    except GSTEInvoiceError as e:
        raise HTTPException(status_code=500, detail=str(e.message))


@router.get("/gstin/verify/{gstin}")
@require_module("finance")
async def verify_gstin(
    gstin: str,
    db: DB,
    company_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_user),
):
    """
    Verify a GSTIN via the E-Invoice portal.

    Returns taxpayer details if the GSTIN is valid.

    Response includes:
    - Legal name and trade name
    - Address and state code
    - Registration status (Active/Inactive)
    """
    # Validate GSTIN format (15 characters)
    if len(gstin) != 15:
        raise HTTPException(
            status_code=400,
            detail="Invalid GSTIN format. GSTIN must be 15 characters."
        )

    effective_company_id = company_id or current_user.company_id

    if not effective_company_id:
        raise HTTPException(
            status_code=400,
            detail="Company ID is required for GSTIN verification"
        )

    try:
        einvoice_service = GSTEInvoiceService(db, effective_company_id)
        result = await einvoice_service.verify_gstin(gstin)
        return result

    except GSTEInvoiceError as e:
        raise HTTPException(
            status_code=400,
            detail=f"GSTIN verification failed: {e.message}",
            headers={"X-Error-Code": e.error_code or "GSTIN_VERIFY_ERROR"}
        )


# ==================== Credit/Debit Notes ====================

@router.post("/credit-debit-notes", response_model=CreditDebitNoteResponse, status_code=status.HTTP_201_CREATED)
@require_module("finance")
async def create_credit_debit_note(
    note_in: CreditDebitNoteCreate,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Create a Credit or Debit Note."""
    # Verify original invoice
    invoice_result = await db.execute(
        select(TaxInvoice).where(TaxInvoice.id == note_in.original_invoice_id)
    )
    original_invoice = invoice_result.scalar_one_or_none()

    if not original_invoice:
        raise HTTPException(status_code=404, detail="Original invoice not found")

    # Generate note number
    prefix = "CN" if note_in.document_type == DocumentType.CREDIT_NOTE else "DN"
    today = date.today()
    count_result = await db.execute(
        select(func.count(CreditDebitNote.id)).where(
            and_(
                CreditDebitNote.document_type == note_in.document_type,
                func.date(CreditDebitNote.created_at) == today,
            )
        )
    )
    count = count_result.scalar() or 0
    note_number = f"{prefix}-{today.strftime('%Y%m%d')}-{str(count + 1).zfill(4)}"

    # Calculate totals from items
    taxable_amount = Decimal("0")
    cgst_total = Decimal("0")
    sgst_total = Decimal("0")
    igst_total = Decimal("0")
    cess_total = Decimal("0")

    for item in note_in.items:
        taxable_amount += item.taxable_amount
        cgst_total += item.cgst_amount
        sgst_total += item.sgst_amount
        igst_total += item.igst_amount
        cess_total += item.cess_amount

    total_tax = cgst_total + sgst_total + igst_total + cess_total
    grand_total = taxable_amount + total_tax

    note = CreditDebitNote(
        note_number=note_number,
        document_type=note_in.document_type,
        note_date=note_in.note_date,
        original_invoice_id=note_in.original_invoice_id,
        original_invoice_number=original_invoice.invoice_number,
        original_invoice_date=original_invoice.invoice_date,
        reason=note_in.reason,
        reason_description=note_in.reason_description,
        customer_id=original_invoice.customer_id,
        dealer_id=original_invoice.dealer_id,
        billing_gstin=original_invoice.billing_gstin,
        taxable_amount=taxable_amount,
        cgst_amount=cgst_total,
        sgst_amount=sgst_total,
        igst_amount=igst_total,
        cess_amount=cess_total,
        total_tax=total_tax,
        grand_total=grand_total,
        created_by=current_user.id,
    )

    db.add(note)
    await db.flush()

    # Create note items
    line_number = 0
    for item_data in note_in.items:
        line_number += 1
        item = CreditDebitNoteItem(
            note_id=note.id,
            line_number=line_number,
            product_id=item_data.product_id,
            product_name=item_data.product_name,
            hsn_code=item_data.hsn_code,
            quantity=item_data.quantity,
            unit_price=item_data.unit_price,
            taxable_amount=item_data.taxable_amount,
            cgst_rate=item_data.cgst_rate,
            sgst_rate=item_data.sgst_rate,
            igst_rate=item_data.igst_rate,
            cgst_amount=item_data.cgst_amount,
            sgst_amount=item_data.sgst_amount,
            igst_amount=item_data.igst_amount,
            cess_amount=item_data.cess_amount,
            total_amount=item_data.taxable_amount + item_data.cgst_amount + item_data.sgst_amount + item_data.igst_amount + item_data.cess_amount,
        )
        db.add(item)

    await db.commit()

    # Load full note
    result = await db.execute(
        select(CreditDebitNote)
        .options(selectinload(CreditDebitNote.items))
        .where(CreditDebitNote.id == note.id)
    )
    note = result.scalar_one()

    return note


@router.get("/credit-debit-notes", response_model=CreditDebitNoteListResponse)
@require_module("finance")
async def list_credit_debit_notes(
    db: DB,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    document_type: Optional[DocumentType] = None,
    customer_id: Optional[UUID] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    current_user: User = Depends(get_current_user),
):
    """List Credit/Debit Notes."""
    query = select(CreditDebitNote)
    count_query = select(func.count(CreditDebitNote.id))

    filters = []
    if document_type:
        filters.append(CreditDebitNote.document_type == document_type)
    if customer_id:
        filters.append(CreditDebitNote.customer_id == customer_id)
    if start_date:
        filters.append(CreditDebitNote.note_date >= start_date)
    if end_date:
        filters.append(CreditDebitNote.note_date <= end_date)

    if filters:
        query = query.where(and_(*filters))
        count_query = count_query.where(and_(*filters))

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(CreditDebitNote.note_date.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    notes = result.scalars().all()

    return CreditDebitNoteListResponse(
        items=[CreditDebitNoteResponse.model_validate(n) for n in notes],
        total=total,
        skip=skip,
        limit=limit
    )


# ==================== E-Way Bill ====================

@router.post("/eway-bills", response_model=EWayBillResponse, status_code=status.HTTP_201_CREATED)
@require_module("finance")
async def create_eway_bill(
    ewb_in: EWayBillCreate,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Create an E-Way Bill."""
    # Verify invoice
    invoice_result = await db.execute(
        select(TaxInvoice)
        .options(selectinload(TaxInvoice.items))
        .where(TaxInvoice.id == ewb_in.invoice_id)
    )
    invoice = invoice_result.scalar_one_or_none()

    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    # Check if E-Way Bill already exists
    existing = await db.execute(
        select(EWayBill).where(EWayBill.invoice_id == ewb_in.invoice_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="E-Way Bill already exists for this invoice")

    # E-Way Bill is required for goods value > ₹50,000
    if invoice.taxable_amount < 50000:
        raise HTTPException(
            status_code=400,
            detail="E-Way Bill not required for invoice value below ₹50,000"
        )

    # Create E-Way Bill
    ewb = EWayBill(
        invoice_id=invoice.id,
        document_number=ewb_in.document_number,
        document_date=ewb_in.document_date,
        supply_type=ewb_in.supply_type,
        sub_supply_type=ewb_in.sub_supply_type,
        document_type=ewb_in.document_type,
        transaction_type=ewb_in.transaction_type,
        # From Address
        from_gstin=ewb_in.from_gstin,
        from_name=ewb_in.from_name,
        from_address1=ewb_in.from_address1,
        from_address2=ewb_in.from_address2,
        from_place=ewb_in.from_place,
        from_pincode=ewb_in.from_pincode,
        from_state_code=ewb_in.from_state_code,
        # To Address
        to_gstin=ewb_in.to_gstin,
        to_name=ewb_in.to_name,
        to_address1=ewb_in.to_address1,
        to_address2=ewb_in.to_address2,
        to_place=ewb_in.to_place,
        to_pincode=ewb_in.to_pincode,
        to_state_code=ewb_in.to_state_code,
        # Values from invoice
        total_value=invoice.grand_total,
        cgst_amount=invoice.cgst_amount,
        sgst_amount=invoice.sgst_amount,
        igst_amount=invoice.igst_amount,
        cess_amount=invoice.cess_amount,
        # Transport
        transporter_id=ewb_in.transporter_id,
        transporter_name=ewb_in.transporter_name,
        transporter_gstin=ewb_in.transporter_gstin,
        transport_mode=ewb_in.transport_mode,
        distance_km=ewb_in.distance_km,
        vehicle_number=ewb_in.vehicle_number,
        vehicle_type=ewb_in.vehicle_type,
        transport_doc_number=ewb_in.transport_doc_number,
        transport_doc_date=ewb_in.transport_doc_date,
    )

    db.add(ewb)
    await db.flush()

    # Create E-Way Bill items
    for invoice_item in invoice.items:
        ewb_item = EWayBillItem(
            eway_bill_id=ewb.id,
            product_name=invoice_item.item_name,
            hsn_code=invoice_item.hsn_code,
            quantity=invoice_item.quantity,
            uom=invoice_item.uom,
            taxable_value=invoice_item.taxable_value,
            gst_rate=invoice_item.gst_rate,
            cgst_amount=invoice_item.cgst_amount,
            sgst_amount=invoice_item.sgst_amount,
            igst_amount=invoice_item.igst_amount,
        )
        db.add(ewb_item)

    await db.commit()

    # Load full E-Way Bill
    result = await db.execute(
        select(EWayBill)
        .options(selectinload(EWayBill.items))
        .where(EWayBill.id == ewb.id)
    )
    ewb = result.scalar_one()

    return ewb


@router.post("/eway-bills/{ewb_id}/generate", response_model=EWayBillResponse)
@require_module("finance")
async def generate_eway_bill_number(
    ewb_id: UUID,
    db: DB,
    company_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_user),
):
    """
    Generate E-Way Bill number from NIC GST portal.

    This integrates with the NIC E-Way Bill API to:
    - Authenticate with E-Way Bill portal
    - Submit E-Way Bill data in prescribed format
    - Receive E-Way Bill number and validity period
    - Update E-Way Bill record with portal response

    E-Way Bill validity is based on distance:
    - Up to 100 km: 1 day
    - Every additional 100 km: 1 additional day
    """
    result = await db.execute(
        select(EWayBill)
        .options(selectinload(EWayBill.items))
        .where(EWayBill.id == ewb_id)
    )
    ewb = result.scalar_one_or_none()

    if not ewb:
        raise HTTPException(status_code=404, detail="E-Way Bill not found")

    if ewb.eway_bill_number:
        raise HTTPException(status_code=400, detail="E-Way Bill number already generated")

    # Determine company_id
    effective_company_id = company_id or current_user.company_id

    if not effective_company_id:
        raise HTTPException(
            status_code=400,
            detail="Company ID is required for E-Way Bill generation"
        )

    try:
        # Initialize E-Way Bill service
        ewaybill_service = GSTEWayBillService(db, effective_company_id)

        # Generate E-Way Bill via NIC portal
        ewb_result = await ewaybill_service.generate_ewaybill(ewb_id)

        # Reload updated E-Way Bill
        result = await db.execute(
            select(EWayBill)
            .options(selectinload(EWayBill.items))
            .where(EWayBill.id == ewb_id)
        )
        ewb = result.scalar_one()

        # Log successful generation
        try:
            audit_service = AuditService(db)
            await audit_service.log_action(
                user_id=current_user.id,
                action="GENERATE_EWAYBILL",
                entity_type="EWayBill",
                entity_id=ewb_id,
                details={
                    "ewb_number": ewb.eway_bill_number,
                    "valid_until": str(ewb.valid_until) if ewb.valid_until else None,
                }
            )
        except Exception:
            pass

        return ewb

    except GSTEWayBillError as e:
        raise HTTPException(
            status_code=400,
            detail=f"E-Way Bill generation failed: {e.message}",
            headers={"X-Error-Code": e.error_code or "EWAYBILL_ERROR"}
        )


@router.put("/eway-bills/{ewb_id}/vehicle", response_model=EWayBillResponse)
@require_module("finance")
async def update_eway_bill_vehicle(
    ewb_id: UUID,
    update_request: PartBUpdateRequest,
    db: DB,
    company_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_user),
):
    """
    Update Part-B (vehicle/transporter details) of E-Way Bill.

    This is required when:
    - Vehicle breaks down and needs to be changed
    - Goods are transshipped to another vehicle
    - First time entering vehicle details

    Reason codes:
    - "1": Due to breakdown
    - "2": Due to transshipment
    - "3": Others
    - "4": First time
    """
    result = await db.execute(
        select(EWayBill).where(EWayBill.id == ewb_id)
    )
    ewb = result.scalar_one_or_none()

    if not ewb:
        raise HTTPException(status_code=404, detail="E-Way Bill not found")

    if not ewb.eway_bill_number:
        raise HTTPException(status_code=400, detail="E-Way Bill number not generated yet")

    if ewb.status == EWayBillStatus.CANCELLED:
        raise HTTPException(status_code=400, detail="Cannot update cancelled E-Way Bill")

    effective_company_id = company_id or current_user.company_id

    if not effective_company_id:
        raise HTTPException(
            status_code=400,
            detail="Company ID is required"
        )

    try:
        ewaybill_service = GSTEWayBillService(db, effective_company_id)

        update_result = await ewaybill_service.update_part_b(
            ewb_id=ewb_id,
            vehicle_number=update_request.vehicle_number,
            transport_mode=update_request.transport_mode,
            reason_code=update_request.reason_code,
            reason_remarks=update_request.reason_remarks,
            from_place=update_request.from_place,
            from_state=update_request.from_state
        )

        # Reload E-Way Bill
        result = await db.execute(
            select(EWayBill)
            .options(selectinload(EWayBill.items))
            .where(EWayBill.id == ewb_id)
        )
        ewb = result.scalar_one()

        return ewb

    except GSTEWayBillError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Part-B update failed: {e.message}",
            headers={"X-Error-Code": e.error_code or "EWAYBILL_ERROR"}
        )


@router.post("/eway-bills/{ewb_id}/cancel", response_model=EWayBillResponse)
@require_module("finance")
async def cancel_eway_bill(
    ewb_id: UUID,
    cancel_request: EWBCancelRequest,
    db: DB,
    company_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_user),
):
    """
    Cancel E-Way Bill within 24 hours of generation.

    As per GST rules, an E-Way Bill can only be cancelled within 24 hours.
    After 24 hours, it cannot be cancelled.

    Cancel reason codes:
    - "1": Duplicate
    - "2": Order Cancelled
    - "3": Data Entry Mistake
    - "4": Others
    """
    result = await db.execute(
        select(EWayBill).where(EWayBill.id == ewb_id)
    )
    ewb = result.scalar_one_or_none()

    if not ewb:
        raise HTTPException(status_code=404, detail="E-Way Bill not found")

    if not ewb.eway_bill_number:
        raise HTTPException(status_code=400, detail="E-Way Bill number not generated")

    if ewb.status == EWayBillStatus.CANCELLED:
        raise HTTPException(status_code=400, detail="E-Way Bill already cancelled")

    # Check 24 hour window
    if ewb.generated_at:
        hours_elapsed = (datetime.now(timezone.utc) - ewb.generated_at).total_seconds() / 3600
        if hours_elapsed > 24:
            raise HTTPException(
                status_code=400,
                detail="E-Way Bill can only be cancelled within 24 hours of generation"
            )

    # Validate reason code
    valid_reasons = ["1", "2", "3", "4"]
    if cancel_request.reason_code not in valid_reasons:
        raise HTTPException(
            status_code=400,
            detail="Invalid reason code. Valid codes: 1=Duplicate, 2=Order Cancelled, 3=Data Entry Mistake, 4=Others"
        )

    effective_company_id = company_id or current_user.company_id

    if not effective_company_id:
        raise HTTPException(
            status_code=400,
            detail="Company ID is required"
        )

    try:
        ewaybill_service = GSTEWayBillService(db, effective_company_id)

        cancel_result = await ewaybill_service.cancel_ewaybill(
            ewb_id=ewb_id,
            reason_code=cancel_request.reason_code,
            remarks=cancel_request.remarks
        )

        # Reload E-Way Bill
        result = await db.execute(
            select(EWayBill)
            .options(selectinload(EWayBill.items))
            .where(EWayBill.id == ewb_id)
        )
        ewb = result.scalar_one()

        # Log cancellation
        try:
            audit_service = AuditService(db)
            await audit_service.log_action(
                user_id=current_user.id,
                action="CANCEL_EWAYBILL",
                entity_type="EWayBill",
                entity_id=ewb_id,
                details={
                    "ewb_number": ewb.eway_bill_number,
                    "reason_code": cancel_request.reason_code,
                    "remarks": cancel_request.remarks
                }
            )
        except Exception:
            pass

        return ewb

    except GSTEWayBillError as e:
        raise HTTPException(
            status_code=400,
            detail=f"E-Way Bill cancellation failed: {e.message}",
            headers={"X-Error-Code": e.error_code or "EWAYBILL_ERROR"}
        )


@router.post("/eway-bills/{ewb_id}/extend", response_model=EWayBillResponse)
@require_module("finance")
async def extend_eway_bill_validity(
    ewb_id: UUID,
    extend_request: EWBExtendRequest,
    db: DB,
    company_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_user),
):
    """
    Extend E-Way Bill validity when goods are in transit.

    Can be extended 8 hours before expiry or 8 hours after expiry.

    Extension reason codes:
    - "1": Natural calamity
    - "2": Law and order situation
    - "3": Transshipment
    - "4": Accident
    - "99": Others

    Transit type:
    - "C": In-transit (goods still moving)
    - "R": Reached destination
    """
    result = await db.execute(
        select(EWayBill).where(EWayBill.id == ewb_id)
    )
    ewb = result.scalar_one_or_none()

    if not ewb:
        raise HTTPException(status_code=404, detail="E-Way Bill not found")

    if not ewb.eway_bill_number:
        raise HTTPException(status_code=400, detail="E-Way Bill number not generated")

    if ewb.status == EWayBillStatus.CANCELLED:
        raise HTTPException(status_code=400, detail="Cannot extend cancelled E-Way Bill")

    effective_company_id = company_id or current_user.company_id

    if not effective_company_id:
        raise HTTPException(
            status_code=400,
            detail="Company ID is required"
        )

    try:
        ewaybill_service = GSTEWayBillService(db, effective_company_id)

        extend_result = await ewaybill_service.extend_validity(
            ewb_id=ewb_id,
            from_place=extend_request.from_place,
            from_state=extend_request.from_state,
            remaining_distance=extend_request.remaining_distance,
            reason_code=extend_request.reason_code,
            reason_remarks=extend_request.reason_remarks,
            transit_type=extend_request.transit_type,
            vehicle_number=extend_request.vehicle_number
        )

        # Reload E-Way Bill
        result = await db.execute(
            select(EWayBill)
            .options(selectinload(EWayBill.items))
            .where(EWayBill.id == ewb_id)
        )
        ewb = result.scalar_one()

        return ewb

    except GSTEWayBillError as e:
        raise HTTPException(
            status_code=400,
            detail=f"E-Way Bill extension failed: {e.message}",
            headers={"X-Error-Code": e.error_code or "EWAYBILL_ERROR"}
        )


@router.get("/eway-bills/{ewb_id}/details")
@require_module("finance")
async def get_eway_bill_details(
    ewb_id: UUID,
    db: DB,
    company_id: Optional[UUID] = None,
    current_user: User = Depends(get_current_user),
):
    """
    Get E-Way Bill details from GST portal.

    Fetches the current status and details from NIC portal.
    """
    result = await db.execute(
        select(EWayBill)
        .options(selectinload(EWayBill.items))
        .where(EWayBill.id == ewb_id)
    )
    ewb = result.scalar_one_or_none()

    if not ewb:
        raise HTTPException(status_code=404, detail="E-Way Bill not found")

    if not ewb.eway_bill_number:
        raise HTTPException(status_code=400, detail="E-Way Bill number not generated")

    effective_company_id = company_id or current_user.company_id

    if not effective_company_id:
        raise HTTPException(
            status_code=400,
            detail="Company ID is required"
        )

    try:
        ewaybill_service = GSTEWayBillService(db, effective_company_id)
        portal_details = await ewaybill_service.get_ewaybill_details(ewb.eway_bill_number)

        return {
            "ewb_id": str(ewb_id),
            "ewb_number": ewb.eway_bill_number,
            "document_number": ewb.document_number,
            "status": ewb.status if ewb.status else None,
            "valid_from": ewb.valid_from,
            "valid_until": ewb.valid_until,
            "vehicle_number": ewb.vehicle_number,
            "portal_details": portal_details
        }

    except GSTEWayBillError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to get E-Way Bill details: {e.message}",
            headers={"X-Error-Code": e.error_code or "EWAYBILL_ERROR"}
        )


@router.get("/eway-bills", response_model=EWayBillListResponse)
@require_module("finance")
async def list_eway_bills(
    db: DB,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    status: Optional[EWayBillStatus] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    current_user: User = Depends(get_current_user),
):
    """List E-Way Bills."""
    query = select(EWayBill)
    count_query = select(func.count(EWayBill.id))

    filters = []
    if status:
        filters.append(EWayBill.status == status)
    if start_date:
        filters.append(func.date(EWayBill.created_at) >= start_date)
    if end_date:
        filters.append(func.date(EWayBill.created_at) <= end_date)

    if filters:
        query = query.where(and_(*filters))
        count_query = count_query.where(and_(*filters))

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.options(selectinload(EWayBill.items)).order_by(EWayBill.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    ewbs = result.scalars().all()

    return EWayBillListResponse(
        items=[EWayBillResponse.model_validate(e) for e in ewbs],
        total=total,
        skip=skip,
        limit=limit
    )


@router.get("/eway-bills/{ewb_id}/print")
@require_module("finance")
async def print_eway_bill(
    ewb_id: UUID,
    db: DB,
):
    """Generate printable E-Way Bill in HTML format."""
    from fastapi.responses import HTMLResponse

    result = await db.execute(
        select(EWayBill)
        .options(selectinload(EWayBill.items))
        .where(EWayBill.id == ewb_id)
    )
    ewb = result.scalar_one_or_none()

    if not ewb:
        raise HTTPException(status_code=404, detail="E-Way Bill not found")

    if not ewb.eway_bill_number:
        raise HTTPException(status_code=400, detail="E-Way Bill number not yet generated")

    # Format dates
    doc_date = ewb.document_date.strftime("%d-%m-%Y") if ewb.document_date else "N/A"
    valid_from = ewb.valid_from.strftime("%d-%m-%Y %H:%M") if ewb.valid_from else "N/A"
    valid_until = ewb.valid_until.strftime("%d-%m-%Y %H:%M") if ewb.valid_until else "N/A"
    generated_at = ewb.generated_at.strftime("%d-%m-%Y %H:%M") if ewb.generated_at else "N/A"

    # Transport mode mapping
    transport_modes = {"1": "Road", "2": "Rail", "3": "Air", "4": "Ship"}
    transport_mode_text = transport_modes.get(ewb.transport_mode, "Road")

    # Build items HTML
    items_html = ""
    for idx, item in enumerate(ewb.items, 1):
        items_html += f"""
        <tr>
            <td style="text-align: center;">{idx}</td>
            <td>{item.product_name}</td>
            <td style="text-align: center;">{item.hsn_code}</td>
            <td style="text-align: right;">{float(item.quantity):.2f}</td>
            <td style="text-align: center;">{item.uom}</td>
            <td style="text-align: right;">₹{float(item.taxable_value):,.2f}</td>
            <td style="text-align: right;">{float(item.gst_rate):.1f}%</td>
        </tr>
        """

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>E-Way Bill - {ewb.eway_bill_number}</title>
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{ font-family: Arial, sans-serif; font-size: 12px; padding: 20px; background: #f5f5f5; }}
            .container {{ max-width: 800px; margin: 0 auto; background: white; padding: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
            .header {{ text-align: center; border-bottom: 3px solid #1a5276; padding-bottom: 15px; margin-bottom: 20px; }}
            .header h1 {{ color: #1a5276; font-size: 24px; margin-bottom: 5px; }}
            .header .subtitle {{ color: #666; font-size: 14px; }}
            .ewb-number {{ background: #1a5276; color: white; padding: 10px 20px; font-size: 18px; font-weight: bold; display: inline-block; margin: 10px 0; border-radius: 5px; }}
            .status {{ display: inline-block; padding: 5px 15px; border-radius: 20px; font-weight: bold; margin-left: 10px; }}
            .status.generated {{ background: #27ae60; color: white; }}
            .status.pending {{ background: #f39c12; color: white; }}
            .status.cancelled {{ background: #e74c3c; color: white; }}
            .section {{ margin-bottom: 20px; }}
            .section-title {{ background: #ecf0f1; padding: 8px 15px; font-weight: bold; color: #2c3e50; border-left: 4px solid #1a5276; margin-bottom: 10px; }}
            .info-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 15px; }}
            .info-box {{ border: 1px solid #ddd; padding: 15px; border-radius: 5px; }}
            .info-box h4 {{ color: #1a5276; margin-bottom: 10px; border-bottom: 1px solid #eee; padding-bottom: 5px; }}
            .info-row {{ display: flex; margin-bottom: 5px; }}
            .info-label {{ width: 120px; color: #666; font-weight: 500; }}
            .info-value {{ flex: 1; color: #333; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
            th {{ background: #1a5276; color: white; padding: 10px; text-align: left; }}
            td {{ padding: 8px 10px; border-bottom: 1px solid #ddd; }}
            tr:hover {{ background: #f9f9f9; }}
            .totals {{ text-align: right; margin-top: 15px; padding: 15px; background: #f8f9fa; border-radius: 5px; }}
            .totals .row {{ display: flex; justify-content: flex-end; margin-bottom: 5px; }}
            .totals .label {{ width: 150px; color: #666; }}
            .totals .value {{ width: 120px; text-align: right; font-weight: 500; }}
            .totals .grand-total {{ font-size: 16px; font-weight: bold; color: #1a5276; border-top: 2px solid #1a5276; padding-top: 10px; margin-top: 10px; }}
            .validity {{ background: #e8f6f3; border: 1px solid #1abc9c; padding: 15px; border-radius: 5px; margin-top: 20px; }}
            .validity h4 {{ color: #16a085; margin-bottom: 10px; }}
            .qr-section {{ text-align: center; margin-top: 20px; padding: 20px; border: 2px dashed #ddd; }}
            .footer {{ text-align: center; margin-top: 20px; padding-top: 15px; border-top: 1px solid #ddd; color: #666; font-size: 10px; }}
            @media print {{
                body {{ background: white; padding: 0; }}
                .container {{ box-shadow: none; }}
                .no-print {{ display: none; }}
            }}
            .print-btn {{ background: #1a5276; color: white; padding: 10px 30px; border: none; cursor: pointer; font-size: 14px; border-radius: 5px; margin-bottom: 20px; }}
            .print-btn:hover {{ background: #154360; }}
        </style>
    </head>
    <body>
        <div class="container">
            <button class="print-btn no-print" onclick="window.print()">🖨️ Print E-Way Bill</button>

            <div class="header">
                <h1>E-WAY BILL</h1>
                <div class="subtitle">Generated under GST (Goods and Services Tax)</div>
                <div class="ewb-number">{ewb.eway_bill_number}</div>
                <span class="status {ewb.status.lower()}">{ewb.status}</span>
            </div>

            <div class="section">
                <div class="section-title">Document Details</div>
                <div class="info-grid">
                    <div class="info-box">
                        <div class="info-row">
                            <span class="info-label">Document No:</span>
                            <span class="info-value"><strong>{ewb.document_number}</strong></span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">Document Date:</span>
                            <span class="info-value">{doc_date}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">Document Type:</span>
                            <span class="info-value">{ewb.document_type}</span>
                        </div>
                    </div>
                    <div class="info-box">
                        <div class="info-row">
                            <span class="info-label">Supply Type:</span>
                            <span class="info-value">{"Outward" if ewb.supply_type == "O" else "Inward"}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">Generated On:</span>
                            <span class="info-value">{generated_at}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">Distance:</span>
                            <span class="info-value">{ewb.distance_km} KM</span>
                        </div>
                    </div>
                </div>
            </div>

            <div class="section">
                <div class="section-title">Party Details</div>
                <div class="info-grid">
                    <div class="info-box">
                        <h4>FROM (Consignor)</h4>
                        <div class="info-row">
                            <span class="info-label">GSTIN:</span>
                            <span class="info-value"><strong>{ewb.from_gstin}</strong></span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">Name:</span>
                            <span class="info-value">{ewb.from_name}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">Address:</span>
                            <span class="info-value">{ewb.from_address1}{', ' + ewb.from_address2 if ewb.from_address2 else ''}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">Place/Pincode:</span>
                            <span class="info-value">{ewb.from_place} - {ewb.from_pincode}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">State Code:</span>
                            <span class="info-value">{ewb.from_state_code}</span>
                        </div>
                    </div>
                    <div class="info-box">
                        <h4>TO (Consignee)</h4>
                        <div class="info-row">
                            <span class="info-label">GSTIN:</span>
                            <span class="info-value">{ewb.to_gstin or "Unregistered"}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">Name:</span>
                            <span class="info-value">{ewb.to_name}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">Address:</span>
                            <span class="info-value">{ewb.to_address1}{', ' + ewb.to_address2 if ewb.to_address2 else ''}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">Place/Pincode:</span>
                            <span class="info-value">{ewb.to_place} - {ewb.to_pincode}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">State Code:</span>
                            <span class="info-value">{ewb.to_state_code}</span>
                        </div>
                    </div>
                </div>
            </div>

            <div class="section">
                <div class="section-title">Transport Details</div>
                <div class="info-grid">
                    <div class="info-box">
                        <div class="info-row">
                            <span class="info-label">Mode:</span>
                            <span class="info-value">{transport_mode_text}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">Transporter:</span>
                            <span class="info-value">{ewb.transporter_name or "N/A"}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">Trans. GSTIN:</span>
                            <span class="info-value">{ewb.transporter_gstin or "N/A"}</span>
                        </div>
                    </div>
                    <div class="info-box">
                        <div class="info-row">
                            <span class="info-label">Vehicle No:</span>
                            <span class="info-value">{ewb.vehicle_number or "Not Updated"}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">Vehicle Type:</span>
                            <span class="info-value">{ewb.vehicle_type or "N/A"}</span>
                        </div>
                        <div class="info-row">
                            <span class="info-label">LR/RR No:</span>
                            <span class="info-value">{ewb.transport_doc_number or "N/A"}</span>
                        </div>
                    </div>
                </div>
            </div>

            <div class="section">
                <div class="section-title">Goods Details</div>
                <table>
                    <thead>
                        <tr>
                            <th style="width: 40px;">#</th>
                            <th>Product Name</th>
                            <th style="width: 80px;">HSN</th>
                            <th style="width: 70px;">Qty</th>
                            <th style="width: 50px;">UOM</th>
                            <th style="width: 100px;">Taxable Value</th>
                            <th style="width: 60px;">GST%</th>
                        </tr>
                    </thead>
                    <tbody>
                        {items_html}
                    </tbody>
                </table>

                <div class="totals">
                    <div class="row">
                        <span class="label">CGST:</span>
                        <span class="value">₹{float(ewb.cgst_amount):,.2f}</span>
                    </div>
                    <div class="row">
                        <span class="label">SGST:</span>
                        <span class="value">₹{float(ewb.sgst_amount):,.2f}</span>
                    </div>
                    <div class="row">
                        <span class="label">IGST:</span>
                        <span class="value">₹{float(ewb.igst_amount):,.2f}</span>
                    </div>
                    <div class="row">
                        <span class="label">CESS:</span>
                        <span class="value">₹{float(ewb.cess_amount):,.2f}</span>
                    </div>
                    <div class="row grand-total">
                        <span class="label">TOTAL VALUE:</span>
                        <span class="value">₹{float(ewb.total_value):,.2f}</span>
                    </div>
                </div>
            </div>

            <div class="validity">
                <h4>⏰ E-Way Bill Validity</h4>
                <div class="info-grid" style="margin-top: 10px;">
                    <div>
                        <div class="info-row">
                            <span class="info-label">Valid From:</span>
                            <span class="info-value"><strong>{valid_from}</strong></span>
                        </div>
                    </div>
                    <div>
                        <div class="info-row">
                            <span class="info-label">Valid Until:</span>
                            <span class="info-value"><strong>{valid_until}</strong></span>
                        </div>
                    </div>
                </div>
            </div>

            <div class="qr-section">
                <p style="color: #666;">QR Code will be displayed here when integrated with GST Portal</p>
                <p style="font-size: 10px; margin-top: 5px;">[Scan to verify E-Way Bill authenticity]</p>
            </div>

            <div class="footer">
                <p>This is a computer generated E-Way Bill and does not require signature.</p>
                <p>Generated by Consumer Durable ERP System | Verify at: ewaybillgst.gov.in</p>
            </div>
        </div>
    </body>
    </html>
    """

    return HTMLResponse(content=html_content)


# ==================== Payment Receipts ====================

@router.post("/receipts", response_model=PaymentReceiptResponse, status_code=status.HTTP_201_CREATED)
@require_module("finance")
async def create_payment_receipt(
    receipt_in: PaymentReceiptCreate,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Record a payment receipt against invoice."""
    # Verify invoice
    invoice_result = await db.execute(
        select(TaxInvoice).where(TaxInvoice.id == receipt_in.invoice_id)
    )
    invoice = invoice_result.scalar_one_or_none()

    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    if receipt_in.amount > invoice.amount_due:
        raise HTTPException(
            status_code=400,
            detail=f"Payment amount ({receipt_in.amount}) exceeds balance due ({invoice.amount_due})"
        )

    # Generate receipt number
    today = date.today()
    count_result = await db.execute(
        select(func.count(PaymentReceipt.id)).where(
            func.date(PaymentReceipt.created_at) == today
        )
    )
    count = count_result.scalar() or 0
    receipt_number = f"RCP-{today.strftime('%Y%m%d')}-{str(count + 1).zfill(4)}"

    receipt = PaymentReceipt(
        receipt_number=receipt_number,
        receipt_date=receipt_in.receipt_date,
        invoice_id=receipt_in.invoice_id,
        customer_id=invoice.customer_id,
        dealer_id=invoice.dealer_id,
        amount=receipt_in.amount,
        payment_mode=receipt_in.payment_mode,
        payment_reference=receipt_in.payment_reference,
        bank_name=receipt_in.bank_name,
        cheque_number=receipt_in.cheque_number,
        cheque_date=receipt_in.cheque_date,
        transaction_id=receipt_in.transaction_id,
        narration=receipt_in.narration,
        received_by=current_user.id,
        created_by=current_user.id,
    )

    db.add(receipt)
    await db.flush()  # Get receipt ID for journal entry

    # Update invoice
    invoice.amount_paid += receipt_in.amount
    invoice.amount_due -= receipt_in.amount

    if invoice.amount_due <= 0:
        invoice.status = InvoiceStatus.PAID.value
    else:
        invoice.status = InvoiceStatus.PARTIALLY_PAID.value

    # Auto-generate journal entry for payment receipt
    try:
        auto_journal_service = AutoJournalService(db)
        await auto_journal_service.generate_for_payment_receipt(
            receipt_id=receipt.id,
            user_id=current_user.id,
            auto_post=True  # Auto-post payment receipts
        )
    except AutoJournalError as e:
        # Log the error but don't fail the receipt creation
        import logging
        logging.warning(f"Failed to auto-generate journal for receipt {receipt.receipt_number}: {e.message}")

    await db.commit()
    await db.refresh(receipt)

    return receipt


@router.get("/receipts", response_model=PaymentReceiptListResponse)
@require_module("finance")
async def list_payment_receipts(
    db: DB,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    customer_id: Optional[UUID] = None,
    invoice_id: Optional[UUID] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    current_user: User = Depends(get_current_user),
):
    """List payment receipts."""
    query = select(PaymentReceipt)
    count_query = select(func.count(PaymentReceipt.id))
    amount_query = select(func.coalesce(func.sum(PaymentReceipt.amount), 0))

    filters = []
    if customer_id:
        filters.append(PaymentReceipt.customer_id == customer_id)
    if invoice_id:
        filters.append(PaymentReceipt.invoice_id == invoice_id)
    if start_date:
        filters.append(PaymentReceipt.receipt_date >= start_date)
    if end_date:
        filters.append(PaymentReceipt.receipt_date <= end_date)

    if filters:
        query = query.where(and_(*filters))
        count_query = count_query.where(and_(*filters))
        amount_query = amount_query.where(and_(*filters))

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    total_amount_result = await db.execute(amount_query)
    total_amount = total_amount_result.scalar() or Decimal("0")

    query = query.order_by(PaymentReceipt.receipt_date.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    receipts = result.scalars().all()

    return PaymentReceiptListResponse(
        items=[PaymentReceiptResponse.model_validate(r) for r in receipts],
        total=total,
        total_amount=total_amount,
        skip=skip,
        limit=limit
    )


# ==================== GST Reports ====================

@router.get("/reports/gstr1")
@require_module("finance")
async def get_gstr1_report(
    db: DB,
    month: int = Query(..., ge=1, le=12),
    year: int = Query(..., ge=2017),
    current_user: User = Depends(get_current_user),
):
    """Generate GSTR-1 (Outward Supplies) report data."""
    from calendar import monthrange
    start_date = date(year, month, 1)
    end_date = date(year, month, monthrange(year, month)[1])

    # B2B Invoices (to registered dealers/businesses)
    b2b_query = select(TaxInvoice).where(
        and_(
            TaxInvoice.invoice_date >= start_date,
            TaxInvoice.invoice_date <= end_date,
            TaxInvoice.billing_gstin.isnot(None),
            TaxInvoice.billing_gstin != "",
            TaxInvoice.status != InvoiceStatus.CANCELLED,
        )
    )
    b2b_result = await db.execute(b2b_query)
    b2b_invoices = b2b_result.scalars().all()

    # B2C Large (> 2.5L inter-state to unregistered)
    b2cl_query = select(TaxInvoice).where(
        and_(
            TaxInvoice.invoice_date >= start_date,
            TaxInvoice.invoice_date <= end_date,
            or_(TaxInvoice.billing_gstin.is_(None), TaxInvoice.billing_gstin == ""),
            TaxInvoice.is_inter_state == True,
            TaxInvoice.grand_total > 250000,
            TaxInvoice.status != InvoiceStatus.CANCELLED,
        )
    )
    b2cl_result = await db.execute(b2cl_query)
    b2cl_invoices = b2cl_result.scalars().all()

    # B2CS (B2C Small - remaining unregistered)
    b2cs_query = select(
        TaxInvoice.place_of_supply,
        func.sum(TaxInvoice.taxable_amount).label("taxable_value"),
        func.sum(TaxInvoice.cgst_amount).label("cgst"),
        func.sum(TaxInvoice.sgst_amount).label("sgst"),
        func.sum(TaxInvoice.igst_amount).label("igst"),
    ).where(
        and_(
            TaxInvoice.invoice_date >= start_date,
            TaxInvoice.invoice_date <= end_date,
            or_(TaxInvoice.billing_gstin.is_(None), TaxInvoice.billing_gstin == ""),
            TaxInvoice.status != InvoiceStatus.CANCELLED,
        )
    ).group_by(TaxInvoice.place_of_supply)

    b2cs_result = await db.execute(b2cs_query)
    b2cs_data = b2cs_result.all()

    # Credit/Debit Notes
    cdn_query = select(CreditDebitNote).where(
        and_(
            CreditDebitNote.note_date >= start_date,
            CreditDebitNote.note_date <= end_date,
        )
    )
    cdn_result = await db.execute(cdn_query)
    credit_debit_notes = cdn_result.scalars().all()

    # HSN Summary
    hsn_query = select(
        InvoiceItem.hsn_code,
        func.sum(InvoiceItem.quantity).label("qty"),
        func.sum(InvoiceItem.taxable_amount).label("taxable"),
        func.sum(InvoiceItem.igst_amount).label("igst"),
        func.sum(InvoiceItem.cgst_amount).label("cgst"),
        func.sum(InvoiceItem.sgst_amount).label("sgst"),
    ).join(TaxInvoice).where(
        and_(
            TaxInvoice.invoice_date >= start_date,
            TaxInvoice.invoice_date <= end_date,
            TaxInvoice.status != InvoiceStatus.CANCELLED,
        )
    ).group_by(InvoiceItem.hsn_code)

    hsn_result = await db.execute(hsn_query)
    hsn_summary = hsn_result.all()

    return {
        "return_period": f"{month:02d}{year}",
        "b2b": [
            {
                "gstin": inv.billing_gstin,
                "invoice_number": inv.invoice_number,
                "invoice_date": inv.invoice_date.isoformat(),
                "invoice_value": float(inv.grand_total),
                "place_of_supply": inv.place_of_supply,
                "taxable_value": float(inv.taxable_amount),
                "cgst": float(inv.cgst_amount),
                "sgst": float(inv.sgst_amount),
                "igst": float(inv.igst_amount),
                "cess": float(inv.cess_amount),
            }
            for inv in b2b_invoices
        ],
        "b2cl": [
            {
                "invoice_number": inv.invoice_number,
                "invoice_date": inv.invoice_date.isoformat(),
                "invoice_value": float(inv.grand_total),
                "place_of_supply": inv.place_of_supply,
                "taxable_value": float(inv.taxable_amount),
                "igst": float(inv.igst_amount),
            }
            for inv in b2cl_invoices
        ],
        "b2cs": [
            {
                "place_of_supply": row.place_of_supply,
                "taxable_value": float(row.taxable_value or 0),
                "cgst": float(row.cgst or 0),
                "sgst": float(row.sgst or 0),
                "igst": float(row.igst or 0),
            }
            for row in b2cs_data
        ],
        "cdnr": [
            {
                "note_number": note.note_number,
                "note_date": note.note_date.isoformat(),
                "note_type": note.document_type,
                "original_invoice_number": note.original_invoice_number,
                "original_invoice_date": note.original_invoice_date.isoformat() if note.original_invoice_date else None,
                "taxable_value": float(note.taxable_amount),
                "cgst": float(note.cgst_amount),
                "sgst": float(note.sgst_amount),
                "igst": float(note.igst_amount),
            }
            for note in credit_debit_notes
        ],
        "hsn": [
            {
                "hsn_code": row.hsn_code,
                "quantity": float(row.qty or 0),
                "taxable_value": float(row.taxable or 0),
                "igst": float(row.igst or 0),
                "cgst": float(row.cgst or 0),
                "sgst": float(row.sgst or 0),
            }
            for row in hsn_summary
        ],
    }


@router.get("/reports/gstr3b")
@require_module("finance")
async def get_gstr3b_report(
    db: DB,
    month: int = Query(..., ge=1, le=12),
    year: int = Query(..., ge=2017),
    current_user: User = Depends(get_current_user),
):
    """Generate GSTR-3B (Monthly Summary) report data."""
    from calendar import monthrange
    start_date = date(year, month, 1)
    end_date = date(year, month, monthrange(year, month)[1])

    # Outward taxable supplies
    outward_query = select(
        func.sum(TaxInvoice.taxable_amount).label("taxable"),
        func.sum(TaxInvoice.igst_amount).label("igst"),
        func.sum(TaxInvoice.cgst_amount).label("cgst"),
        func.sum(TaxInvoice.sgst_amount).label("sgst"),
        func.sum(TaxInvoice.cess_amount).label("cess"),
    ).where(
        and_(
            TaxInvoice.invoice_date >= start_date,
            TaxInvoice.invoice_date <= end_date,
            TaxInvoice.status != InvoiceStatus.CANCELLED,
        )
    )

    outward_result = await db.execute(outward_query)
    outward = outward_result.one()

    # Inter-state supplies
    inter_state_query = select(
        func.sum(TaxInvoice.taxable_amount).label("taxable"),
        func.sum(TaxInvoice.igst_amount).label("igst"),
    ).where(
        and_(
            TaxInvoice.invoice_date >= start_date,
            TaxInvoice.invoice_date <= end_date,
            TaxInvoice.is_inter_state == True,
            TaxInvoice.status != InvoiceStatus.CANCELLED,
        )
    )

    inter_result = await db.execute(inter_state_query)
    inter_state = inter_result.one()

    # Intra-state supplies
    intra_state_query = select(
        func.sum(TaxInvoice.taxable_amount).label("taxable"),
        func.sum(TaxInvoice.cgst_amount).label("cgst"),
        func.sum(TaxInvoice.sgst_amount).label("sgst"),
    ).where(
        and_(
            TaxInvoice.invoice_date >= start_date,
            TaxInvoice.invoice_date <= end_date,
            TaxInvoice.is_inter_state == False,
            TaxInvoice.status != InvoiceStatus.CANCELLED,
        )
    )

    intra_result = await db.execute(intra_state_query)
    intra_state = intra_result.one()

    return {
        "return_period": f"{month:02d}{year}",
        "outward_taxable_supplies": {
            "taxable_value": float(outward.taxable or 0),
            "igst": float(outward.igst or 0),
            "cgst": float(outward.cgst or 0),
            "sgst": float(outward.sgst or 0),
            "cess": float(outward.cess or 0),
        },
        "inter_state_supplies": {
            "taxable_value": float(inter_state.taxable or 0),
            "igst": float(inter_state.igst or 0),
        },
        "intra_state_supplies": {
            "taxable_value": float(intra_state.taxable or 0),
            "cgst": float(intra_state.cgst or 0),
            "sgst": float(intra_state.sgst or 0),
        },
        "tax_payable": {
            "igst": float(outward.igst or 0),
            "cgst": float(outward.cgst or 0),
            "sgst": float(outward.sgst or 0),
            "cess": float(outward.cess or 0),
            "total": float((outward.igst or 0) + (outward.cgst or 0) + (outward.sgst or 0) + (outward.cess or 0)),
        },
    }


@router.get("/reports/gstr2a")
@require_module("finance")
async def get_gstr2a_report(
    db: DB,
    month: int = Query(..., ge=1, le=12),
    year: int = Query(..., ge=2017),
    current_user: User = Depends(get_current_user),
):
    """Generate GSTR-2A (Inward Supplies) report data - Auto-populated from supplier filings."""
    from calendar import monthrange
    from app.models.purchase import PurchaseOrder, POStatus

    start_date = date(year, month, 1)
    end_date = date(year, month, monthrange(year, month)[1])

    # Get received purchase orders (inward supplies)
    po_query = select(PurchaseOrder).where(
        and_(
            PurchaseOrder.po_date >= start_date,
            PurchaseOrder.po_date <= end_date,
            PurchaseOrder.status.in_([POStatus.RECEIVED.value, POStatus.COMPLETED.value]),
        )
    )
    po_result = await db.execute(po_query)
    purchase_orders = po_result.scalars().all()

    # Calculate totals
    total_taxable = sum(float(po.subtotal or 0) for po in purchase_orders)
    total_igst = sum(float(po.igst_amount or 0) for po in purchase_orders)
    total_cgst = sum(float(po.cgst_amount or 0) for po in purchase_orders)
    total_sgst = sum(float(po.sgst_amount or 0) for po in purchase_orders)
    total_tax = total_igst + total_cgst + total_sgst

    return {
        "return_period": f"{month:02d}{year}",
        "summary": {
            "total_invoices": len(purchase_orders),
            "total_taxable_value": total_taxable,
            "total_igst": total_igst,
            "total_cgst": total_cgst,
            "total_sgst": total_sgst,
            "total_tax": total_tax,
            "itc_available": total_tax,  # Input Tax Credit available
        },
        "invoices": [
            {
                "id": str(po.id),
                "invoice_number": po.po_number,
                "invoice_date": po.po_date.isoformat() if po.po_date else None,
                "gstin": po.vendor_gstin if hasattr(po, 'vendor_gstin') else None,
                "vendor_name": po.vendor_name if hasattr(po, 'vendor_name') else "Vendor",
                "taxable_value": float(po.subtotal or 0),
                "igst": float(po.igst_amount or 0),
                "cgst": float(po.cgst_amount or 0),
                "sgst": float(po.sgst_amount or 0),
                "total_value": float(po.grand_total or 0),
                "status": "MATCHED" if po.status == POStatus.COMPLETED.value else "PENDING",
            }
            for po in purchase_orders
        ],
    }


@router.get("/reports/hsn-summary")
@require_module("finance")
async def get_hsn_summary_report(
    db: DB,
    month: int = Query(..., ge=1, le=12),
    year: int = Query(..., ge=2017),
    current_user: User = Depends(get_current_user),
):
    """Generate HSN-wise summary for GST returns."""
    from calendar import monthrange
    from app.models.purchase import PurchaseOrderItem, PurchaseOrder, POStatus

    start_date = date(year, month, 1)
    end_date = date(year, month, monthrange(year, month)[1])

    # Outward HSN (from sales invoices)
    outward_hsn_query = select(
        InvoiceItem.hsn_code,
        func.sum(InvoiceItem.quantity).label("qty"),
        func.sum(InvoiceItem.line_total).label("total_value"),
        func.sum(InvoiceItem.taxable_amount).label("taxable"),
        func.sum(InvoiceItem.igst_amount).label("igst"),
        func.sum(InvoiceItem.cgst_amount).label("cgst"),
        func.sum(InvoiceItem.sgst_amount).label("sgst"),
    ).join(TaxInvoice).where(
        and_(
            TaxInvoice.invoice_date >= start_date,
            TaxInvoice.invoice_date <= end_date,
            TaxInvoice.status != InvoiceStatus.CANCELLED,
            InvoiceItem.hsn_code.isnot(None),
        )
    ).group_by(InvoiceItem.hsn_code)

    outward_result = await db.execute(outward_hsn_query)
    outward_hsn = outward_result.all()

    # Inward HSN (from purchase orders)
    inward_hsn_query = select(
        PurchaseOrderItem.hsn_code,
        func.sum(PurchaseOrderItem.quantity).label("qty"),
        func.sum(PurchaseOrderItem.total_amount).label("total_value"),
        func.sum(PurchaseOrderItem.taxable_amount).label("taxable"),
        func.sum(PurchaseOrderItem.igst_amount).label("igst"),
        func.sum(PurchaseOrderItem.cgst_amount).label("cgst"),
        func.sum(PurchaseOrderItem.sgst_amount).label("sgst"),
    ).join(PurchaseOrder).where(
        and_(
            PurchaseOrder.po_date >= start_date,
            PurchaseOrder.po_date <= end_date,
            PurchaseOrder.status.in_([POStatus.RECEIVED.value, POStatus.COMPLETED.value]),
            PurchaseOrderItem.hsn_code.isnot(None),
        )
    ).group_by(PurchaseOrderItem.hsn_code)

    inward_result = await db.execute(inward_hsn_query)
    inward_hsn = inward_result.all()

    # Calculate stats
    outward_total = sum(float(row.taxable or 0) for row in outward_hsn)
    inward_total = sum(float(row.taxable or 0) for row in inward_hsn)

    return {
        "return_period": f"{month:02d}{year}",
        "stats": {
            "outward_hsn_codes": len(outward_hsn),
            "inward_hsn_codes": len(inward_hsn),
            "outward_taxable_value": outward_total,
            "inward_taxable_value": inward_total,
        },
        "outward_hsn": [
            {
                "hsn_code": row.hsn_code or "N/A",
                "description": "",  # Would need product lookup for description
                "uqc": "NOS",
                "total_quantity": float(row.qty or 0),
                "total_value": float(row.total_value or 0),
                "taxable_value": float(row.taxable or 0),
                "igst": float(row.igst or 0),
                "cgst": float(row.cgst or 0),
                "sgst": float(row.sgst or 0),
                "rate": 18,  # Default GST rate
            }
            for row in outward_hsn
        ],
        "inward_hsn": [
            {
                "hsn_code": row.hsn_code or "N/A",
                "description": "",
                "uqc": "NOS",
                "total_quantity": float(row.qty or 0),
                "total_value": float(row.total_value or 0),
                "taxable_value": float(row.taxable or 0),
                "igst": float(row.igst or 0),
                "cgst": float(row.cgst or 0),
                "sgst": float(row.sgst or 0),
                "rate": 18,
            }
            for row in inward_hsn
        ],
    }


@router.get("/reports/finance-dashboard")
@require_module("finance")
async def get_finance_dashboard_stats(
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Get finance dashboard statistics."""
    from app.models.accounting import FinancialPeriod, JournalEntry, JournalEntryStatus
    from app.models.purchase import PurchaseOrder
    from calendar import monthrange

    today = date.today()
    # Current month range
    month_start = date(today.year, today.month, 1)
    _, last_day = monthrange(today.year, today.month)
    month_end = date(today.year, today.month, last_day)

    # Previous month for comparison
    if today.month == 1:
        prev_month_start = date(today.year - 1, 12, 1)
        prev_month_end = date(today.year - 1, 12, 31)
    else:
        prev_month_start = date(today.year, today.month - 1, 1)
        _, prev_last_day = monthrange(today.year, today.month - 1)
        prev_month_end = date(today.year, today.month - 1, prev_last_day)

    # Revenue (from invoices)
    revenue_query = select(
        func.sum(TaxInvoice.grand_total)
    ).where(
        and_(
            TaxInvoice.invoice_date >= month_start,
            TaxInvoice.invoice_date <= month_end,
            TaxInvoice.status != InvoiceStatus.CANCELLED,
        )
    )
    revenue_result = await db.execute(revenue_query)
    current_revenue = float(revenue_result.scalar() or 0)

    prev_revenue_query = select(
        func.sum(TaxInvoice.grand_total)
    ).where(
        and_(
            TaxInvoice.invoice_date >= prev_month_start,
            TaxInvoice.invoice_date <= prev_month_end,
            TaxInvoice.status != InvoiceStatus.CANCELLED,
        )
    )
    prev_revenue_result = await db.execute(prev_revenue_query)
    prev_revenue = float(prev_revenue_result.scalar() or 0)

    revenue_change = ((current_revenue - prev_revenue) / prev_revenue * 100) if prev_revenue > 0 else 0

    # Expenses (from purchase orders)
    expenses_query = select(
        func.sum(PurchaseOrder.grand_total)
    ).where(
        and_(
            PurchaseOrder.po_date >= month_start,
            PurchaseOrder.po_date <= month_end,
        )
    )
    expenses_result = await db.execute(expenses_query)
    current_expenses = float(expenses_result.scalar() or 0)

    prev_expenses_query = select(
        func.sum(PurchaseOrder.grand_total)
    ).where(
        and_(
            PurchaseOrder.po_date >= prev_month_start,
            PurchaseOrder.po_date <= prev_month_end,
        )
    )
    prev_expenses_result = await db.execute(prev_expenses_query)
    prev_expenses = float(prev_expenses_result.scalar() or 0)

    expenses_change = ((current_expenses - prev_expenses) / prev_expenses * 100) if prev_expenses > 0 else 0

    # Gross profit
    gross_profit = current_revenue - current_expenses
    profit_margin = (gross_profit / current_revenue * 100) if current_revenue > 0 else 0

    # Accounts Receivable (unpaid invoices)
    ar_query = select(
        func.sum(TaxInvoice.grand_total - TaxInvoice.amount_paid)
    ).where(
        and_(
            TaxInvoice.status.in_([InvoiceStatus.SENT.value, InvoiceStatus.PARTIALLY_PAID.value]),
        )
    )
    ar_result = await db.execute(ar_query)
    accounts_receivable = float(ar_result.scalar() or 0)

    # Accounts Payable (unpaid POs) - simplified
    ap_query = select(
        func.sum(PurchaseOrder.grand_total)
    ).where(
        PurchaseOrder.status.in_(["APPROVED", "SENT"])
    )
    ap_result = await db.execute(ap_query)
    accounts_payable = float(ap_result.scalar() or 0)

    # Pending journal approvals
    pending_query = select(func.count(JournalEntry.id)).where(
        JournalEntry.status == JournalEntryStatus.PENDING_APPROVAL.value
    )
    pending_result = await db.execute(pending_query)
    pending_approvals = pending_result.scalar() or 0

    # Current period
    period_query = select(FinancialPeriod).where(
        and_(
            FinancialPeriod.start_date <= today,
            FinancialPeriod.end_date >= today,
            FinancialPeriod.status == "OPEN",
        )
    ).order_by(FinancialPeriod.start_date.desc()).limit(1)
    period_result = await db.execute(period_query)
    current_period = period_result.scalar_one_or_none()

    # GST filing status (simplified - based on current month)
    gstr1_due = date(today.year, today.month, 11) if today.day <= 11 else date(
        today.year if today.month < 12 else today.year + 1,
        today.month + 1 if today.month < 12 else 1,
        11
    )
    gstr3b_due = date(today.year, today.month, 20) if today.day <= 20 else date(
        today.year if today.month < 12 else today.year + 1,
        today.month + 1 if today.month < 12 else 1,
        20
    )

    return {
        "total_revenue": current_revenue,
        "revenue_change": round(revenue_change, 1),
        "total_expenses": current_expenses,
        "expenses_change": round(expenses_change, 1),
        "gross_profit": gross_profit,
        "profit_margin": round(profit_margin, 1),
        "accounts_receivable": accounts_receivable,
        "accounts_payable": accounts_payable,
        "pending_approvals": pending_approvals,
        "current_period": {
            "name": current_period.period_name if current_period else f"{today.strftime('%B %Y')}",
            "start_date": current_period.start_date.isoformat() if current_period else month_start.isoformat(),
            "end_date": current_period.end_date.isoformat() if current_period else month_end.isoformat(),
            "status": current_period.status if current_period else "OPEN",
        },
        "gst_filing": {
            "gstr1_due": gstr1_due.isoformat(),
            "gstr1_status": "PENDING" if today < gstr1_due else "OVERDUE",
            "gstr3b_due": gstr3b_due.isoformat(),
            "gstr3b_status": "PENDING" if today < gstr3b_due else "OVERDUE",
        },
    }


# ==================== Document Downloads ====================

@router.get("/invoices/{invoice_id}/download")
@require_module("finance")
async def download_tax_invoice(
    invoice_id: UUID,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Download Tax Invoice as printable HTML (GST compliant format)."""
    from fastapi.responses import HTMLResponse

    result = await db.execute(
        select(TaxInvoice)
        .options(selectinload(TaxInvoice.items))
        .where(TaxInvoice.id == invoice_id)
    )
    invoice = result.scalar_one_or_none()

    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    # Build items table
    items_html = ""
    for idx, item in enumerate(invoice.items, 1):
        unit_price = float(item.unit_price) if item.unit_price else 0.0
        taxable = float(item.taxable_value) if item.taxable_value else 0.0
        cgst = float(item.cgst_amount) if item.cgst_amount else 0.0
        sgst = float(item.sgst_amount) if item.sgst_amount else 0.0
        igst = float(item.igst_amount) if item.igst_amount else 0.0
        total = float(item.line_total) if item.line_total else 0.0

        items_html += f"""
        <tr>
            <td style="border: 1px solid #ddd; padding: 8px; text-align: center;">{idx}</td>
            <td style="border: 1px solid #ddd; padding: 8px;">{item.item_name or '-'}</td>
            <td style="border: 1px solid #ddd; padding: 8px;">{item.hsn_code or '-'}</td>
            <td style="border: 1px solid #ddd; padding: 8px; text-align: center;">{item.quantity}</td>
            <td style="border: 1px solid #ddd; padding: 8px;">{item.uom or 'NOS'}</td>
            <td style="border: 1px solid #ddd; padding: 8px; text-align: right;">₹{unit_price:,.2f}</td>
            <td style="border: 1px solid #ddd; padding: 8px; text-align: right;">₹{taxable:,.2f}</td>
            <td style="border: 1px solid #ddd; padding: 8px; text-align: right;">₹{cgst:,.2f}</td>
            <td style="border: 1px solid #ddd; padding: 8px; text-align: right;">₹{sgst:,.2f}</td>
            <td style="border: 1px solid #ddd; padding: 8px; text-align: right;">₹{igst:,.2f}</td>
            <td style="border: 1px solid #ddd; padding: 8px; text-align: right;">₹{total:,.2f}</td>
        </tr>
        """

    # Determine tax type display
    tax_type = "IGST" if invoice.is_interstate else "CGST + SGST"

    # Build billing address
    billing_address = f"{invoice.billing_address_line1}"
    if invoice.billing_address_line2:
        billing_address += f", {invoice.billing_address_line2}"
    billing_address += f", {invoice.billing_city}, {invoice.billing_state} - {invoice.billing_pincode}"

    # Build shipping address
    shipping_address = ""
    if invoice.shipping_address_line1:
        shipping_address = f"{invoice.shipping_address_line1}"
        if invoice.shipping_address_line2:
            shipping_address += f", {invoice.shipping_address_line2}"
        shipping_address += f", {invoice.shipping_city}, {invoice.shipping_state} - {invoice.shipping_pincode}"
    else:
        shipping_address = billing_address  # Same as billing

    # Convert amount to words (simplified)
    def amount_to_words(amount):
        """Convert amount to words (simplified for demonstration)."""
        units = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine"]
        teens = ["Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen",
                 "Sixteen", "Seventeen", "Eighteen", "Nineteen"]
        tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]

        if amount < 10:
            return units[int(amount)]
        elif amount < 20:
            return teens[int(amount) - 10]
        elif amount < 100:
            return tens[int(amount) // 10] + (" " + units[int(amount) % 10] if amount % 10 else "")
        elif amount < 1000:
            return units[int(amount) // 100] + " Hundred" + (" " + amount_to_words(amount % 100) if amount % 100 else "")
        elif amount < 100000:
            return amount_to_words(amount // 1000) + " Thousand" + (" " + amount_to_words(amount % 1000) if amount % 1000 else "")
        elif amount < 10000000:
            return amount_to_words(amount // 100000) + " Lakh" + (" " + amount_to_words(amount % 100000) if amount % 100000 else "")
        else:
            return amount_to_words(amount // 10000000) + " Crore" + (" " + amount_to_words(amount % 10000000) if amount % 10000000 else "")

    total_in_words = amount_to_words(int(invoice.grand_total or 0)) + " Rupees Only"

    irn_section = ""
    if invoice.irn:
        irn_section = f"""
        <div style="background: #e6f4ea; padding: 10px; border-radius: 5px; margin-bottom: 20px;">
            <strong>E-Invoice Details (IRN Generated)</strong><br>
            <small>IRN: {invoice.irn}</small><br>
            <small>Ack No: {invoice.irn_ack_number or 'N/A'}</small><br>
            <small>Ack Date: {invoice.irn_ack_date or 'N/A'}</small>
        </div>
        """

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>{'Proforma Invoice' if invoice.invoice_type and invoice.invoice_type == 'PROFORMA' else 'Delivery Challan' if invoice.invoice_type and invoice.invoice_type == 'DELIVERY_CHALLAN' else 'Tax Invoice'} - {invoice.invoice_number}</title>
        <style>
            @media print {{
                body {{ margin: 0; padding: 15px; }}
                .no-print {{ display: none; }}
            }}
            body {{
                font-family: Arial, sans-serif;
                max-width: 900px;
                margin: 0 auto;
                padding: 20px;
                color: #333;
                font-size: 12px;
            }}
            .header {{
                display: flex;
                justify-content: space-between;
                border-bottom: 2px solid #333;
                padding-bottom: 15px;
                margin-bottom: 15px;
            }}
            .company-info {{
                flex: 1;
            }}
            .company-name {{
                font-size: 20px;
                font-weight: bold;
                color: #1a73e8;
            }}
            .invoice-title {{
                text-align: right;
            }}
            .invoice-title h2 {{
                margin: 0;
                font-size: 18px;
                background: #1a73e8;
                color: white;
                padding: 10px 20px;
                display: inline-block;
            }}
            .info-grid {{
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 15px;
                margin-bottom: 15px;
            }}
            .info-box {{
                background: #f9f9f9;
                padding: 12px;
                border-radius: 5px;
                border: 1px solid #ddd;
            }}
            .info-box h4 {{
                margin: 0 0 8px 0;
                color: #1a73e8;
                font-size: 11px;
                text-transform: uppercase;
                border-bottom: 1px solid #ddd;
                padding-bottom: 5px;
            }}
            .info-box p {{
                margin: 4px 0;
                font-size: 11px;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-bottom: 15px;
                font-size: 10px;
            }}
            th {{
                background: #1a73e8;
                color: white;
                padding: 8px 5px;
                text-align: left;
                font-size: 10px;
            }}
            .totals {{
                width: 350px;
                margin-left: auto;
            }}
            .totals tr td {{
                padding: 6px 8px;
                border: 1px solid #ddd;
                font-size: 11px;
            }}
            .totals tr:last-child {{
                background: #1a73e8;
                color: white;
                font-weight: bold;
            }}
            .amount-words {{
                background: #f5f5f5;
                padding: 10px;
                border-radius: 5px;
                margin: 15px 0;
                font-style: italic;
            }}
            .footer-grid {{
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 20px;
                margin-top: 30px;
            }}
            .terms {{
                font-size: 10px;
                color: #666;
            }}
            .signature-box {{
                text-align: right;
            }}
            .signature-line {{
                border-top: 1px solid #333;
                margin-top: 60px;
                padding-top: 5px;
                display: inline-block;
                width: 200px;
            }}
            .print-btn {{
                position: fixed;
                top: 10px;
                right: 10px;
                padding: 10px 20px;
                background: #1a73e8;
                color: white;
                border: none;
                border-radius: 5px;
                cursor: pointer;
            }}
            .qr-code {{
                width: 80px;
                height: 80px;
                border: 1px solid #ddd;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 10px;
                color: #999;
            }}
        </style>
    </head>
    <body>
        <button class="print-btn no-print" onclick="window.print()">🖨️ Print / Save PDF</button>

        <div class="header">
            <div class="company-info">
                <div class="company-name">{invoice.seller_name}</div>
                <div style="font-size: 11px; color: #666; margin-top: 5px;">
                    {invoice.seller_address}<br>
                    <strong>GSTIN:</strong> {invoice.seller_gstin}<br>
                    State Code: {invoice.seller_state_code}
                </div>
            </div>
            <div class="invoice-title">
                <h2>{'PROFORMA INVOICE' if invoice.invoice_type and invoice.invoice_type == 'PROFORMA' else 'DELIVERY CHALLAN' if invoice.invoice_type and invoice.invoice_type == 'DELIVERY_CHALLAN' else 'TAX INVOICE'}</h2>
                <div style="margin-top: 10px; text-align: right; font-size: 11px;">
                    <strong>Invoice No:</strong> {invoice.invoice_number}<br>
                    <strong>Date:</strong> {invoice.invoice_date}<br>
                    <strong>Due Date:</strong> {invoice.due_date or 'N/A'}
                </div>
            </div>
        </div>

        {irn_section}

        <div class="info-grid">
            <div class="info-box">
                <h4>Bill To</h4>
                <p><strong>{invoice.customer_name}</strong></p>
                <p>{billing_address}</p>
                <p><strong>GSTIN:</strong> {invoice.customer_gstin or 'N/A (B2C)'}</p>
                <p><strong>State Code:</strong> {invoice.billing_state_code}</p>
            </div>
            <div class="info-box">
                <h4>Ship To</h4>
                <p>{shipping_address}</p>
                <p><strong>State Code:</strong> {invoice.shipping_state_code or invoice.billing_state_code}</p>
            </div>
        </div>

        <div class="info-grid">
            <div class="info-box">
                <h4>Supply Details</h4>
                <p><strong>Place of Supply:</strong> {invoice.place_of_supply} ({invoice.place_of_supply_code})</p>
                <p><strong>Supply Type:</strong> {'Inter-State' if invoice.is_interstate else 'Intra-State'} ({tax_type})</p>
                <p><strong>Reverse Charge:</strong> {'Yes' if invoice.is_reverse_charge else 'No'}</p>
            </div>
            <div class="info-box">
                <h4>Payment Details</h4>
                <p><strong>Payment Status:</strong> {invoice.status if invoice.status else 'N/A'}</p>
                <p><strong>Amount Due:</strong> ₹{float(invoice.amount_due or 0):,.2f}</p>
            </div>
        </div>

        <table>
            <thead>
                <tr>
                    <th style="width: 25px;">#</th>
                    <th style="width: 200px;">Description</th>
                    <th>HSN/SAC</th>
                    <th style="width: 40px;">Qty</th>
                    <th>UOM</th>
                    <th>Rate</th>
                    <th>Taxable</th>
                    <th>CGST</th>
                    <th>SGST</th>
                    <th>IGST</th>
                    <th>Total</th>
                </tr>
            </thead>
            <tbody>
                {items_html}
            </tbody>
        </table>

        <table class="totals">
            <tr>
                <td>Subtotal</td>
                <td style="text-align: right;">₹{float(invoice.subtotal or 0):,.2f}</td>
            </tr>
            <tr>
                <td>Discount</td>
                <td style="text-align: right;">₹{float(invoice.discount_amount or 0):,.2f}</td>
            </tr>
            <tr>
                <td>Taxable Amount</td>
                <td style="text-align: right;">₹{float(invoice.taxable_amount or 0):,.2f}</td>
            </tr>
            <tr>
                <td>CGST</td>
                <td style="text-align: right;">₹{float(invoice.cgst_amount or 0):,.2f}</td>
            </tr>
            <tr>
                <td>SGST</td>
                <td style="text-align: right;">₹{float(invoice.sgst_amount or 0):,.2f}</td>
            </tr>
            <tr>
                <td>IGST</td>
                <td style="text-align: right;">₹{float(invoice.igst_amount or 0):,.2f}</td>
            </tr>
            <tr>
                <td>CESS</td>
                <td style="text-align: right;">₹{float(invoice.cess_amount or 0):,.2f}</td>
            </tr>
            <tr>
                <td>Round Off</td>
                <td style="text-align: right;">₹{float(invoice.round_off or 0):,.2f}</td>
            </tr>
            <tr>
                <td><strong>Grand Total</strong></td>
                <td style="text-align: right;"><strong>₹{float(invoice.grand_total or 0):,.2f}</strong></td>
            </tr>
        </table>

        <div class="amount-words">
            <strong>Amount in Words:</strong> {total_in_words}
        </div>

        <div class="footer-grid">
            <div class="terms">
                <strong>Terms & Conditions:</strong>
                <ol style="margin: 5px 0; padding-left: 20px;">
                    <li>Goods once sold will not be taken back.</li>
                    <li>Interest @18% p.a. will be charged on delayed payments.</li>
                    <li>Subject to local jurisdiction only.</li>
                    <li>E&OE (Errors and Omissions Excepted)</li>
                </ol>
            </div>
            <div class="signature-box">
                <div class="qr-code">[QR Code]</div>
                <div class="signature-line">
                    Authorized Signatory
                </div>
            </div>
        </div>

        <p style="text-align: center; font-size: 9px; color: #999; margin-top: 20px;">
            This is a computer-generated invoice and does not require a signature.
            Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        </p>
    </body>
    </html>
    """

    return HTMLResponse(content=html_content)
