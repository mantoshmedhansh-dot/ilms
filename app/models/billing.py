"""Enhanced Billing models with GST e-Invoice compliance.

Supports:
- Tax Invoice (B2B, B2C)
- Credit Note / Debit Note
- E-Invoice with IRN (Invoice Reference Number)
- E-Way Bill for goods movement
- Payment receipts and advances
"""
import uuid
from datetime import datetime, date, timezone
from enum import Enum
from typing import TYPE_CHECKING, Optional, List
from decimal import Decimal

from sqlalchemy import String, Boolean, DateTime, ForeignKey, Integer, Text, Numeric, Date
from sqlalchemy import UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.order import Order
    from app.models.product import Product
    from app.models.user import User
    from app.models.warehouse import Warehouse
    from app.models.shipment import Shipment


class InvoiceType(str, Enum):
    """Invoice type enumeration."""
    TAX_INVOICE = "TAX_INVOICE"           # Regular B2B/B2C tax invoice
    PROFORMA = "PROFORMA"                  # Proforma invoice (quote)
    DELIVERY_CHALLAN = "DELIVERY_CHALLAN"  # Goods delivery without invoice
    EXPORT = "EXPORT"                      # Export invoice
    SEZ = "SEZ"                            # SEZ supply invoice
    DEEMED_EXPORT = "DEEMED_EXPORT"        # Deemed export invoice


class InvoiceStatus(str, Enum):
    """Invoice status enumeration."""
    DRAFT = "DRAFT"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    GENERATED = "GENERATED"           # PDF generated
    IRN_PENDING = "IRN_PENDING"       # E-invoice IRN generation pending
    IRN_GENERATED = "IRN_GENERATED"   # E-invoice IRN generated
    SENT = "SENT"                     # Sent to customer
    PARTIALLY_PAID = "PARTIALLY_PAID"
    PAID = "PAID"
    OVERDUE = "OVERDUE"
    CANCELLED = "CANCELLED"
    VOID = "VOID"


class DocumentType(str, Enum):
    """Document type for credit/debit notes."""
    CREDIT_NOTE = "CREDIT_NOTE"
    DEBIT_NOTE = "DEBIT_NOTE"


class NoteReason(str, Enum):
    """Reason for credit/debit note."""
    # Credit Note Reasons
    SALES_RETURN = "SALES_RETURN"
    POST_SALE_DISCOUNT = "POST_SALE_DISCOUNT"
    DEFICIENCY_IN_SERVICE = "DEFICIENCY_IN_SERVICE"
    CORRECTION_IN_INVOICE = "CORRECTION_IN_INVOICE"
    CHANGE_IN_POS = "CHANGE_IN_POS"
    FINALIZATION_OF_PROVISIONAL = "FINALIZATION_OF_PROVISIONAL"
    # Debit Note Reasons
    PRICE_INCREASE = "PRICE_INCREASE"
    ADDITIONAL_CHARGES = "ADDITIONAL_CHARGES"
    QUALITY_VARIATION = "QUALITY_VARIATION"
    OTHER = "OTHER"


class EWayBillStatus(str, Enum):
    """E-Way Bill status."""
    PENDING = "PENDING"
    GENERATED = "GENERATED"
    EXTENDED = "EXTENDED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


class PaymentMode(str, Enum):
    """Payment mode enumeration."""
    CASH = "CASH"
    CHEQUE = "CHEQUE"
    RTGS = "RTGS"
    NEFT = "NEFT"
    UPI = "UPI"
    CREDIT_CARD = "CREDIT_CARD"
    DEBIT_CARD = "DEBIT_CARD"
    NET_BANKING = "NET_BANKING"
    WALLET = "WALLET"
    EMI = "EMI"
    CREDIT = "CREDIT"               # Credit sale (B2B)
    ADVANCE = "ADVANCE"             # Adjusted from advance
    TDS_DEDUCTED = "TDS_DEDUCTED"   # TDS deduction


class TaxInvoice(Base):
    """
    Tax Invoice model with e-invoice compliance.
    Supports GST e-invoicing with IRN generation.
    """
    __tablename__ = "tax_invoices"
    __table_args__ = (
        Index("ix_tax_invoices_invoice_date", "invoice_date"),
        Index("ix_tax_invoices_irn", "irn"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Invoice Identification
    invoice_number: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
        comment="Unique invoice number e.g., INV/2024-25/00001"
    )
    invoice_series: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="Invoice series code"
    )

    # Type & Status
    invoice_type: Mapped[str] = mapped_column(
        String(50),
        default="TAX_INVOICE",
        nullable=False,
        comment="TAX_INVOICE, PROFORMA, DELIVERY_CHALLAN, EXPORT, SEZ, DEEMED_EXPORT"
    )
    status: Mapped[str] = mapped_column(
        String(50),
        default="DRAFT",
        nullable=False,
        index=True,
        comment="DRAFT, PENDING_APPROVAL, APPROVED, GENERATED, IRN_PENDING, IRN_GENERATED, SENT, PARTIALLY_PAID, PAID, OVERDUE, CANCELLED, VOID"
    )

    # Dates
    invoice_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    supply_date: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True,
        comment="Date of supply for GST"
    )

    # Order Reference
    order_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )

    # Shipment Reference (link to shipment that triggered invoice)
    shipment_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("shipments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Shipment that triggered this invoice (for goods issue)"
    )

    # Invoice Generation Trigger
    generation_trigger: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="MANUAL, GOODS_ISSUE, ORDER_CONFIRMATION, etc."
    )

    # Warehouse/Branch
    warehouse_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="SET NULL"),
        nullable=True
    )

    # Customer Details (denormalized for invoice permanence)
    customer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    customer_name: Mapped[str] = mapped_column(String(200), nullable=False)
    customer_gstin: Mapped[Optional[str]] = mapped_column(
        String(15),
        nullable=True,
        comment="Customer GSTIN for B2B"
    )
    customer_pan: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)

    # Billing Address
    billing_address_line1: Mapped[str] = mapped_column(String(255), nullable=False)
    billing_address_line2: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    billing_city: Mapped[str] = mapped_column(String(100), nullable=False)
    billing_state: Mapped[str] = mapped_column(String(100), nullable=False)
    billing_state_code: Mapped[str] = mapped_column(
        String(2),
        nullable=False,
        comment="GST state code e.g., 27 for Maharashtra"
    )
    billing_pincode: Mapped[str] = mapped_column(String(10), nullable=False)
    billing_country: Mapped[str] = mapped_column(String(100), default="India")

    # Shipping Address (if different)
    shipping_address_line1: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    shipping_address_line2: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    shipping_city: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    shipping_state: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    shipping_state_code: Mapped[Optional[str]] = mapped_column(String(2), nullable=True)
    shipping_pincode: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    shipping_country: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Seller Details (denormalized)
    seller_gstin: Mapped[str] = mapped_column(
        String(15),
        nullable=False,
        comment="Seller GSTIN"
    )
    seller_name: Mapped[str] = mapped_column(String(200), nullable=False)
    seller_address: Mapped[str] = mapped_column(String(500), nullable=False)
    seller_state_code: Mapped[str] = mapped_column(String(2), nullable=False)

    # Place of Supply
    place_of_supply: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Place of supply for GST"
    )
    place_of_supply_code: Mapped[str] = mapped_column(
        String(2),
        nullable=False,
        comment="State code for place of supply"
    )
    is_interstate: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="True if interstate supply (IGST), False if intrastate (CGST+SGST)"
    )
    is_reverse_charge: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="Reverse charge mechanism"
    )

    # Amounts (in INR)
    subtotal: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
        comment="Sum of line items before tax"
    )
    discount_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0"),
        comment="Total discount"
    )
    taxable_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
        comment="Taxable value after discount"
    )

    # GST Components
    cgst_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0"),
        comment="Central GST amount"
    )
    sgst_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0"),
        comment="State GST amount"
    )
    igst_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0"),
        comment="Integrated GST amount"
    )
    cess_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0"),
        comment="GST Compensation Cess"
    )
    total_tax: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        comment="Total tax amount"
    )

    # Other Charges
    shipping_charges: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        default=Decimal("0")
    )
    packaging_charges: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        default=Decimal("0")
    )
    installation_charges: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        default=Decimal("0")
    )
    other_charges: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        default=Decimal("0")
    )

    # Grand Total
    grand_total: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
        comment="Final invoice amount"
    )
    amount_in_words: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True
    )
    currency: Mapped[str] = mapped_column(String(3), default="INR")

    # Round Off
    round_off: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        default=Decimal("0")
    )

    # Payment Status
    amount_paid: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("0")
    )
    amount_due: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False
    )
    payment_terms: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    payment_due_days: Mapped[int] = mapped_column(Integer, default=30)

    # E-Invoice Fields (GST Portal)
    irn: Mapped[Optional[str]] = mapped_column(
        String(64),
        unique=True,
        nullable=True,
        comment="Invoice Reference Number from GST Portal"
    )
    irn_generated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    ack_number: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Acknowledgement number from GST Portal"
    )
    ack_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    signed_invoice: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Digitally signed invoice JSON"
    )
    signed_qr_code: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Signed QR code for e-invoice"
    )
    einvoice_status: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="E-invoice portal status"
    )
    einvoice_error: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="E-invoice generation error if any"
    )

    # E-Way Bill Reference
    eway_bill_number: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True
    )

    # Document Links
    pdf_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    original_copy_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    duplicate_copy_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Remarks
    terms_and_conditions: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    internal_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    customer_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Channel Reference
    channel_code: Mapped[Optional[str]] = mapped_column(
        String(30),
        nullable=True,
        comment="Sales channel code"
    )
    channel_invoice_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Invoice ID on marketplace/channel"
    )

    # Audit
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    cancellation_reason: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    items: Mapped[List["InvoiceItem"]] = relationship(
        "InvoiceItem",
        back_populates="invoice",
        cascade="all, delete-orphan"
    )
    payments: Mapped[List["PaymentReceipt"]] = relationship(
        "PaymentReceipt",
        back_populates="invoice",
        cascade="all, delete-orphan"
    )
    credit_notes: Mapped[List["CreditDebitNote"]] = relationship(
        "CreditDebitNote",
        back_populates="invoice",
        foreign_keys="CreditDebitNote.invoice_id"
    )
    eway_bill: Mapped[Optional["EWayBill"]] = relationship(
        "EWayBill",
        back_populates="invoice",
        uselist=False
    )
    order: Mapped[Optional["Order"]] = relationship("Order")
    shipment: Mapped[Optional["Shipment"]] = relationship("Shipment")
    customer: Mapped[Optional["User"]] = relationship("User", foreign_keys=[customer_id])

    @property
    def is_b2b(self) -> bool:
        """Check if B2B invoice (customer has GSTIN)."""
        return bool(self.customer_gstin)

    @property
    def is_paid(self) -> bool:
        """Check if invoice is fully paid."""
        return self.amount_due <= 0

    def __repr__(self) -> str:
        return f"<Invoice(number='{self.invoice_number}', status='{self.status}')>"


class InvoiceItem(Base):
    """Invoice line item with HSN/SAC and tax breakup."""
    __tablename__ = "invoice_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    invoice_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tax_invoices.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Product Reference
    product_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="SET NULL"),
        nullable=True
    )
    variant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("product_variants.id", ondelete="SET NULL"),
        nullable=True
    )

    # Item Details (denormalized)
    sku: Mapped[str] = mapped_column(String(50), nullable=False)
    item_name: Mapped[str] = mapped_column(String(300), nullable=False)
    item_description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    hsn_code: Mapped[str] = mapped_column(
        String(8),
        nullable=False,
        comment="HSN code for goods, SAC for services"
    )
    is_service: Mapped[bool] = mapped_column(Boolean, default=False)

    # Serial Numbers
    serial_numbers: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="List of serial numbers for this item"
    )

    # Quantity & UOM
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False)
    uom: Mapped[str] = mapped_column(
        String(10),
        default="NOS",
        comment="Unit of measurement"
    )

    # Pricing
    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        comment="Price per unit before discount"
    )
    mrp: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 2),
        nullable=True,
        comment="Maximum Retail Price"
    )
    discount_percentage: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        default=Decimal("0")
    )
    discount_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0")
    )
    taxable_value: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        comment="Value after discount"
    )

    # GST Rates
    gst_rate: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        nullable=False,
        comment="GST rate (5, 12, 18, 28)"
    )
    cgst_rate: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        default=Decimal("0")
    )
    sgst_rate: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        default=Decimal("0")
    )
    igst_rate: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        default=Decimal("0")
    )
    cess_rate: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        default=Decimal("0")
    )

    # GST Amounts
    cgst_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0")
    )
    sgst_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0")
    )
    igst_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0")
    )
    cess_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0")
    )
    total_tax: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False
    )

    # Line Total
    line_total: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
        comment="Taxable value + Tax"
    )

    # Warranty
    warranty_months: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    warranty_end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Order Item Reference
    order_item_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    invoice: Mapped["TaxInvoice"] = relationship("TaxInvoice", back_populates="items")
    product: Mapped[Optional["Product"]] = relationship("Product")

    def __repr__(self) -> str:
        return f"<InvoiceItem(sku='{self.sku}', qty={self.quantity})>"


class CreditDebitNote(Base):
    """
    Credit Note / Debit Note model.
    Used for returns, price adjustments, corrections.
    """
    __tablename__ = "credit_debit_notes"
    __table_args__ = (
        Index("ix_credit_debit_notes_date", "note_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Note Identification
    note_number: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
        comment="Credit/Debit note number"
    )
    document_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="CREDIT_NOTE, DEBIT_NOTE"
    )

    # Reference Invoice
    invoice_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tax_invoices.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )
    original_invoice_number: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Original invoice number"
    )
    original_invoice_date: Mapped[date] = mapped_column(Date, nullable=False)

    # Note Details
    note_date: Mapped[date] = mapped_column(Date, nullable=False)
    reason: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="SALES_RETURN, POST_SALE_DISCOUNT, DEFICIENCY_IN_SERVICE, CORRECTION_IN_INVOICE, CHANGE_IN_POS, FINALIZATION_OF_PROVISIONAL, PRICE_INCREASE, ADDITIONAL_CHARGES, QUALITY_VARIATION, OTHER"
    )
    reason_description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Status
    status: Mapped[str] = mapped_column(
        String(50),
        default="DRAFT",
        nullable=False,
        comment="DRAFT, PENDING_APPROVAL, APPROVED, GENERATED, CANCELLED, VOID"
    )

    # Customer Details
    customer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    customer_name: Mapped[str] = mapped_column(String(200), nullable=False)
    customer_gstin: Mapped[Optional[str]] = mapped_column(String(15), nullable=True)

    # Place of Supply
    place_of_supply: Mapped[str] = mapped_column(String(100), nullable=False)
    place_of_supply_code: Mapped[str] = mapped_column(String(2), nullable=False)
    is_interstate: Mapped[bool] = mapped_column(Boolean, default=False)

    # Amounts
    taxable_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    cgst_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    sgst_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    igst_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    cess_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    total_tax: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    grand_total: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)

    # E-Invoice Fields
    irn: Mapped[Optional[str]] = mapped_column(
        String(64),
        unique=True,
        nullable=True,
        comment="IRN for credit/debit note"
    )
    ack_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    ack_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Pre-GST Reference (for notes against old invoices)
    pre_gst: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        comment="True if against pre-GST invoice"
    )

    # PDF
    pdf_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Audit
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    invoice: Mapped["TaxInvoice"] = relationship(
        "TaxInvoice",
        back_populates="credit_notes",
        foreign_keys=[invoice_id]
    )
    items: Mapped[List["CreditDebitNoteItem"]] = relationship(
        "CreditDebitNoteItem",
        back_populates="note",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<CreditDebitNote(number='{self.note_number}', type='{self.document_type}')>"


class CreditDebitNoteItem(Base):
    """Line items for Credit/Debit Note."""
    __tablename__ = "credit_debit_note_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    note_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("credit_debit_notes.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Item Details
    product_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="SET NULL"),
        nullable=True
    )
    sku: Mapped[str] = mapped_column(String(50), nullable=False)
    item_name: Mapped[str] = mapped_column(String(300), nullable=False)
    hsn_code: Mapped[str] = mapped_column(String(8), nullable=False)

    # Quantity
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False)
    uom: Mapped[str] = mapped_column(String(10), default="NOS")

    # Values
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    taxable_value: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    # GST
    gst_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    cgst_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    sgst_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    igst_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    total_tax: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    line_total: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)

    # Reference to original invoice item
    original_invoice_item_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    note: Mapped["CreditDebitNote"] = relationship(
        "CreditDebitNote",
        back_populates="items"
    )

    def __repr__(self) -> str:
        return f"<CreditDebitNoteItem(sku='{self.sku}')>"


class EWayBill(Base):
    """
    E-Way Bill model for goods movement.
    Required for transporting goods > INR 50,000.
    """
    __tablename__ = "eway_bills"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # E-Way Bill Number
    eway_bill_number: Mapped[Optional[str]] = mapped_column(
        String(20),
        unique=True,
        nullable=True,
        index=True,
        comment="12-digit E-Way Bill number"
    )

    # Invoice Reference
    invoice_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tax_invoices.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Status
    status: Mapped[str] = mapped_column(
        String(50),
        default="PENDING",
        nullable=False,
        comment="PENDING, GENERATED, EXTENDED, CANCELLED, EXPIRED"
    )

    # Document Details
    document_type: Mapped[str] = mapped_column(
        String(20),
        default="INV",
        comment="INV, CHL (Challan), BIL (Bill)"
    )
    document_number: Mapped[str] = mapped_column(String(50), nullable=False)
    document_date: Mapped[date] = mapped_column(Date, nullable=False)

    # Supply Type
    supply_type: Mapped[str] = mapped_column(
        String(10),
        default="O",
        comment="O=Outward, I=Inward"
    )
    sub_supply_type: Mapped[str] = mapped_column(
        String(10),
        default="1",
        comment="1=Supply, 2=Export, 3=Job Work, etc."
    )

    # Transaction Type
    transaction_type: Mapped[str] = mapped_column(
        String(10),
        default="1",
        comment="1=Regular, 2=Bill To-Ship To, 3=Bill From-Dispatch From"
    )

    # From Address (Consignor)
    from_gstin: Mapped[str] = mapped_column(String(15), nullable=False)
    from_name: Mapped[str] = mapped_column(String(200), nullable=False)
    from_address1: Mapped[str] = mapped_column(String(255), nullable=False)
    from_address2: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    from_place: Mapped[str] = mapped_column(String(100), nullable=False)
    from_pincode: Mapped[str] = mapped_column(String(10), nullable=False)
    from_state_code: Mapped[str] = mapped_column(String(2), nullable=False)

    # To Address (Consignee)
    to_gstin: Mapped[Optional[str]] = mapped_column(String(15), nullable=True)
    to_name: Mapped[str] = mapped_column(String(200), nullable=False)
    to_address1: Mapped[str] = mapped_column(String(255), nullable=False)
    to_address2: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    to_place: Mapped[str] = mapped_column(String(100), nullable=False)
    to_pincode: Mapped[str] = mapped_column(String(10), nullable=False)
    to_state_code: Mapped[str] = mapped_column(String(2), nullable=False)

    # Goods Value
    total_value: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    cgst_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    sgst_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    igst_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    cess_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))

    # Transport Details
    transporter_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("transporters.id", ondelete="SET NULL"),
        nullable=True
    )
    transporter_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    transporter_gstin: Mapped[Optional[str]] = mapped_column(String(15), nullable=True)
    transport_mode: Mapped[str] = mapped_column(
        String(10),
        default="1",
        comment="1=Road, 2=Rail, 3=Air, 4=Ship"
    )
    vehicle_number: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    vehicle_type: Mapped[Optional[str]] = mapped_column(
        String(10),
        nullable=True,
        comment="R=Regular, O=ODC"
    )
    transport_doc_number: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="LR/RR/AWB number"
    )
    transport_doc_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Distance
    distance_km: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Approximate distance in KM"
    )

    # Validity
    valid_from: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    valid_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Extension Details
    extension_count: Mapped[int] = mapped_column(Integer, default=0)
    extended_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    extension_reason: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Cancellation
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    cancellation_reason: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # API Response
    generated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    api_response: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        comment="Raw response from GST portal"
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    invoice: Mapped["TaxInvoice"] = relationship("TaxInvoice", back_populates="eway_bill")
    items: Mapped[List["EWayBillItem"]] = relationship(
        "EWayBillItem",
        back_populates="eway_bill",
        cascade="all, delete-orphan"
    )

    @property
    def is_valid(self) -> bool:
        """Check if E-Way Bill is still valid."""
        if self.status != EWayBillStatus.GENERATED:
            return False
        if self.valid_until:
            return datetime.now(timezone.utc) < self.valid_until
        return True

    def __repr__(self) -> str:
        return f"<EWayBill(number='{self.eway_bill_number}', status='{self.status}')>"


class EWayBillItem(Base):
    """E-Way Bill item details."""
    __tablename__ = "eway_bill_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    eway_bill_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("eway_bills.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Item Details
    product_name: Mapped[str] = mapped_column(String(300), nullable=False)
    part_code: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="Vendor's part code e.g., AFGPSW2001"
    )
    hsn_code: Mapped[str] = mapped_column(String(8), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(10, 3), nullable=False)
    uom: Mapped[str] = mapped_column(String(10), default="NOS")
    taxable_value: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    gst_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    cgst_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    sgst_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    igst_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))

    # Relationships
    eway_bill: Mapped["EWayBill"] = relationship("EWayBill", back_populates="items")

    def __repr__(self) -> str:
        return f"<EWayBillItem(hsn='{self.hsn_code}', qty={self.quantity})>"


class PaymentReceipt(Base):
    """
    Payment receipt for invoice payments.
    Tracks partial/full payments against invoices.
    """
    __tablename__ = "payment_receipts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Receipt Number
    receipt_number: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
        comment="Payment receipt number"
    )

    # Invoice Reference
    invoice_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tax_invoices.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Customer
    customer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Payment Details
    payment_date: Mapped[date] = mapped_column(Date, nullable=False)
    payment_mode: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="CASH, CHEQUE, RTGS, NEFT, UPI, CREDIT_CARD, DEBIT_CARD, NET_BANKING, WALLET, EMI, CREDIT, ADVANCE, TDS_DEDUCTED"
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="INR")

    # Bank Details (for cheque/RTGS/NEFT)
    bank_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    bank_branch: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    cheque_number: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    cheque_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    transaction_reference: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="UTR/Transaction ID"
    )

    # TDS Details
    tds_applicable: Mapped[bool] = mapped_column(Boolean, default=False)
    tds_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), nullable=True)
    tds_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    tds_section: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="TDS section e.g., 194C, 194J"
    )

    # Net Amount
    net_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
        comment="Amount after TDS"
    )

    # Status
    is_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    confirmed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    is_bounced: Mapped[bool] = mapped_column(Boolean, default=False)
    bounced_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    bounce_reason: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Remarks
    remarks: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    # Audit
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    invoice: Mapped["TaxInvoice"] = relationship("TaxInvoice", back_populates="payments")

    def __repr__(self) -> str:
        return f"<PaymentReceipt(number='{self.receipt_number}', amount={self.amount})>"


class InvoiceNumberSequence(Base):
    """
    Invoice number sequence management.
    Maintains series-wise number sequences.
    """
    __tablename__ = "invoice_number_sequences"
    __table_args__ = (
        UniqueConstraint("series_code", "financial_year", name="uq_invoice_sequence"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Series Identification
    series_code: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Invoice series code e.g., INV, CN, DN"
    )
    series_name: Mapped[str] = mapped_column(String(100), nullable=False)

    # Financial Year
    financial_year: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        comment="e.g., 2024-25"
    )

    # Prefix/Suffix Pattern
    prefix: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="e.g., INV/2024-25/"
    )
    suffix: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Sequence
    current_number: Mapped[int] = mapped_column(Integer, default=0)
    padding_length: Mapped[int] = mapped_column(
        Integer,
        default=5,
        comment="Zero padding for number"
    )

    # Warehouse specific (optional)
    warehouse_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("warehouses.id", ondelete="SET NULL"),
        nullable=True
    )

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    def get_next_number(self) -> str:
        """Generate next invoice number."""
        self.current_number += 1
        number = str(self.current_number).zfill(self.padding_length)
        return f"{self.prefix}{number}{self.suffix or ''}"

    def __repr__(self) -> str:
        return f"<InvoiceNumberSequence(series='{self.series_code}', year='{self.financial_year}')>"
