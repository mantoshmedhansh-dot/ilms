"""Invoice Service for automated invoice generation.

This service implements SAP S/4HANA-aligned Order-to-Invoice flow:
- Invoice generates AFTER Goods Issue (physical dispatch to courier)
- Serial numbers captured during picking flow to invoice
- Proper document linkage: Order -> Delivery -> Goods Issue -> Invoice

SAP Equivalent: VF01 triggered by VL09 (Post Goods Issue)
"""
import uuid
import logging
from datetime import datetime, timezone, date
from decimal import Decimal
from typing import Optional, Dict, List, Any

from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.billing import (
    TaxInvoice, InvoiceItem, InvoiceType, InvoiceStatus,
    InvoiceNumberSequence
)
from app.models.order import Order, OrderItem
from app.models.shipment import Shipment
from app.models.customer import Customer
from app.models.company import Company
from app.models.picklist import PicklistItem
from app.models.warehouse import Warehouse


logger = logging.getLogger(__name__)


# GST State Code mapping
GST_STATE_CODES = {
    "01": "Jammu & Kashmir", "02": "Himachal Pradesh", "03": "Punjab",
    "04": "Chandigarh", "05": "Uttarakhand", "06": "Haryana",
    "07": "Delhi", "08": "Rajasthan", "09": "Uttar Pradesh",
    "10": "Bihar", "11": "Sikkim", "12": "Arunachal Pradesh",
    "13": "Nagaland", "14": "Manipur", "15": "Mizoram",
    "16": "Tripura", "17": "Meghalaya", "18": "Assam",
    "19": "West Bengal", "20": "Jharkhand", "21": "Odisha",
    "22": "Chhattisgarh", "23": "Madhya Pradesh", "24": "Gujarat",
    "26": "Dadra & Nagar Haveli and Daman & Diu", "27": "Maharashtra",
    "28": "Andhra Pradesh (Old)", "29": "Karnataka", "30": "Goa",
    "31": "Lakshadweep", "32": "Kerala", "33": "Tamil Nadu",
    "34": "Puducherry", "35": "Andaman & Nicobar Islands",
    "36": "Telangana", "37": "Andhra Pradesh",
    "38": "Ladakh", "97": "Other Territory"
}

# Reverse mapping: State name to code
STATE_TO_CODE = {v.upper(): k for k, v in GST_STATE_CODES.items()}


class InvoiceGenerationError(Exception):
    """Exception raised when invoice generation fails."""
    pass


class InvoiceService:
    """Service for invoice management and auto-generation."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_company(self) -> Optional[Company]:
        """Get the primary company for seller details."""
        result = await self.db.execute(
            select(Company).where(
                and_(
                    Company.is_active == True,
                    Company.is_primary == True
                )
            )
        )
        company = result.scalar_one_or_none()

        if not company:
            # Fall back to first active company
            result = await self.db.execute(
                select(Company).where(Company.is_active == True).limit(1)
            )
            company = result.scalar_one_or_none()

        return company

    async def get_state_code_from_name(self, state_name: str) -> str:
        """Get GST state code from state name."""
        if not state_name:
            return "27"  # Default to Maharashtra

        state_upper = state_name.upper().strip()

        # Check for exact match
        if state_upper in STATE_TO_CODE:
            return STATE_TO_CODE[state_upper]

        # Check for partial match
        for name, code in STATE_TO_CODE.items():
            if state_upper in name or name in state_upper:
                return code

        # Default to Maharashtra if not found
        logger.warning(f"Could not find state code for '{state_name}', defaulting to Maharashtra (27)")
        return "27"

    async def get_picked_serial_numbers(self, order_id: uuid.UUID) -> Dict[uuid.UUID, List[str]]:
        """
        Get serial numbers captured during picking.

        Returns: {order_item_id: ["SN001", "SN002", ...]}
        """
        result = await self.db.execute(
            select(PicklistItem)
            .where(
                and_(
                    PicklistItem.order_id == order_id,
                    PicklistItem.picked_serials.isnot(None)
                )
            )
        )
        picklist_items = result.scalars().all()

        serials_by_item: Dict[uuid.UUID, List[str]] = {}
        for item in picklist_items:
            if item.picked_serials:
                # picked_serials is stored as comma-separated string
                serials = [s.strip() for s in item.picked_serials.split(",") if s.strip()]
                serials_by_item[item.order_item_id] = serials

        return serials_by_item

    async def generate_invoice_number(
        self,
        series_code: str = "INV",
        invoice_type: InvoiceType = InvoiceType.TAX_INVOICE
    ) -> str:
        """Generate unique invoice number from sequence."""
        # Get current financial year
        now = datetime.now(timezone.utc)
        if now.month >= 4:
            financial_year = f"{now.year}-{str(now.year + 1)[2:]}"
        else:
            financial_year = f"{now.year - 1}-{str(now.year)[2:]}"

        # Get or create sequence
        result = await self.db.execute(
            select(InvoiceNumberSequence).where(
                and_(
                    InvoiceNumberSequence.series_code == series_code,
                    InvoiceNumberSequence.financial_year == financial_year,
                    InvoiceNumberSequence.is_active == True,
                )
            )
        )
        sequence = result.scalar_one_or_none()

        if not sequence:
            # Create default sequence
            sequence = InvoiceNumberSequence(
                series_code=series_code,
                series_name=f"{invoice_type.value} Series",
                financial_year=financial_year,
                prefix=f"{series_code}/{financial_year}/",
                current_number=0,
            )
            self.db.add(sequence)
            await self.db.flush()

        sequence.current_number += 1
        return f"{sequence.prefix}{str(sequence.current_number).zfill(sequence.padding_length)}"

    async def check_invoice_exists_for_order(self, order_id: uuid.UUID) -> bool:
        """Check if an invoice already exists for the given order."""
        result = await self.db.execute(
            select(TaxInvoice.id).where(
                and_(
                    TaxInvoice.order_id == order_id,
                    TaxInvoice.status != InvoiceStatus.CANCELLED.value,
                    TaxInvoice.status != InvoiceStatus.VOID.value
                )
            )
        )
        return result.scalar_one_or_none() is not None

    async def auto_generate_invoice_on_goods_issue(
        self,
        shipment_id: uuid.UUID,
        manifest_number: str,
        generated_by: uuid.UUID
    ) -> TaxInvoice:
        """
        Auto-generate invoice when shipment is manifested (Goods Issue).

        SAP Equivalent: VF01 triggered by VL09 (Post Goods Issue)

        Flow:
        1. Get shipment and linked order
        2. Verify order doesn't already have invoice
        3. Retrieve serial numbers from picklist items
        4. Create TaxInvoice with:
           - Customer details (shipping/billing address)
           - Line items with serial numbers
           - GST calculation (CGST+SGST or IGST based on interstate)
        5. Link invoice to order and shipment
        6. Update order with invoice reference

        Args:
            shipment_id: UUID of the shipment being manifested
            manifest_number: Manifest number for reference
            generated_by: User ID who triggered the goods issue

        Returns:
            TaxInvoice: The newly created invoice

        Raises:
            InvoiceGenerationError: If invoice cannot be generated
        """
        # 1. Get shipment with order details
        shipment_result = await self.db.execute(
            select(Shipment)
            .options(
                selectinload(Shipment.order).selectinload(Order.items),
                selectinload(Shipment.order).selectinload(Order.customer),
                selectinload(Shipment.warehouse)
            )
            .where(Shipment.id == shipment_id)
        )
        shipment = shipment_result.scalar_one_or_none()

        if not shipment:
            raise InvoiceGenerationError(f"Shipment {shipment_id} not found")

        order = shipment.order
        if not order:
            raise InvoiceGenerationError(f"No order linked to shipment {shipment.shipment_number}")

        customer = order.customer
        if not customer:
            raise InvoiceGenerationError(f"No customer found for order {order.order_number}")

        # 2. Check if invoice already exists
        if await self.check_invoice_exists_for_order(order.id):
            logger.warning(f"Invoice already exists for order {order.order_number}, skipping auto-generation")
            # Return existing invoice
            existing_result = await self.db.execute(
                select(TaxInvoice)
                .options(selectinload(TaxInvoice.items))
                .where(
                    and_(
                        TaxInvoice.order_id == order.id,
                        TaxInvoice.status != InvoiceStatus.CANCELLED.value,
                        TaxInvoice.status != InvoiceStatus.VOID.value
                    )
                )
            )
            return existing_result.scalar_one()

        # 3. Get company details for seller info
        company = await self.get_company()
        if not company:
            raise InvoiceGenerationError("No active company found for seller details")

        # 4. Get serial numbers from picklist
        serials_by_item = await self.get_picked_serial_numbers(order.id)

        # 5. Prepare address details
        shipping_address = order.shipping_address or {}
        billing_address = order.billing_address or shipping_address

        # Get state codes
        shipping_state = shipping_address.get("state", shipment.ship_to_state or "")
        billing_state = billing_address.get("state", shipping_state)
        seller_state = company.state

        shipping_state_code = await self.get_state_code_from_name(shipping_state)
        billing_state_code = await self.get_state_code_from_name(billing_state)
        seller_state_code = company.state_code

        # Determine if inter-state
        is_interstate = seller_state_code != shipping_state_code

        # 6. Generate invoice number
        invoice_number = await self.generate_invoice_number()

        # 7. Create TaxInvoice
        invoice = TaxInvoice(
            invoice_number=invoice_number,
            invoice_type=InvoiceType.TAX_INVOICE.value,
            status=InvoiceStatus.GENERATED.value,
            invoice_date=date.today(),
            supply_date=date.today(),
            order_id=order.id,
            shipment_id=shipment.id,
            generation_trigger="GOODS_ISSUE",
            warehouse_id=shipment.warehouse_id,

            # Customer details
            customer_id=customer.id,
            customer_name=customer.full_name if hasattr(customer, 'full_name') else f"{customer.first_name or ''} {customer.last_name or ''}".strip(),
            customer_gstin=getattr(customer, 'gst_number', None),  # Customer model uses gst_number
            customer_pan=getattr(customer, 'pan', None),

            # Billing address
            billing_address_line1=billing_address.get("address_line1", billing_address.get("address", "")),
            billing_address_line2=billing_address.get("address_line2", billing_address.get("landmark", "")),
            billing_city=billing_address.get("city", ""),
            billing_state=billing_state,
            billing_state_code=billing_state_code,
            billing_pincode=billing_address.get("pincode", billing_address.get("zip", "")),
            billing_country=billing_address.get("country", "India"),

            # Shipping address
            shipping_address_line1=shipping_address.get("address_line1", shipping_address.get("address", "")),
            shipping_address_line2=shipping_address.get("address_line2", shipping_address.get("landmark", "")),
            shipping_city=shipping_address.get("city", shipment.ship_to_city or ""),
            shipping_state=shipping_state,
            shipping_state_code=shipping_state_code,
            shipping_pincode=shipping_address.get("pincode", shipment.ship_to_pincode),
            shipping_country=shipping_address.get("country", "India"),

            # Seller details
            seller_gstin=company.gstin,
            seller_name=company.trade_name or company.legal_name,
            seller_address=company.full_address,
            seller_state_code=seller_state_code,

            # Place of supply
            place_of_supply=shipping_state or GST_STATE_CODES.get(shipping_state_code, ""),
            place_of_supply_code=shipping_state_code,
            is_interstate=is_interstate,
            is_reverse_charge=False,

            # Charges from order
            shipping_charges=order.shipping_amount or Decimal("0"),
            packaging_charges=Decimal("0"),
            installation_charges=Decimal("0"),
            other_charges=Decimal("0"),

            # Payment terms
            payment_due_days=0,  # D2C is prepaid

            # Notes
            internal_notes=f"Auto-generated on Goods Issue. Manifest: {manifest_number}",

            # Audit
            created_by=generated_by,

            # Initialize totals to zero
            subtotal=Decimal("0"),
            discount_amount=Decimal("0"),
            taxable_amount=Decimal("0"),
            cgst_amount=Decimal("0"),
            sgst_amount=Decimal("0"),
            igst_amount=Decimal("0"),
            cess_amount=Decimal("0"),
            total_tax=Decimal("0"),
            grand_total=Decimal("0"),
            amount_paid=order.amount_paid or Decimal("0"),
            amount_due=Decimal("0"),
        )

        self.db.add(invoice)
        await self.db.flush()

        # 8. Create invoice items
        subtotal = Decimal("0")
        total_discount = Decimal("0")
        taxable_amount = Decimal("0")
        cgst_total = Decimal("0")
        sgst_total = Decimal("0")
        igst_total = Decimal("0")
        cess_total = Decimal("0")

        for order_item in order.items:
            # Get serial numbers for this item
            item_serials = serials_by_item.get(order_item.id, [])

            # Calculate item amounts
            gross_amount = Decimal(str(order_item.quantity)) * order_item.unit_price
            discount_amount = order_item.discount_amount or Decimal("0")
            item_taxable = gross_amount - discount_amount

            # GST calculation based on inter/intra state
            gst_rate = order_item.tax_rate or Decimal("18.00")
            if is_interstate:
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
            cess_amount = Decimal("0")

            item_total_tax = cgst_amount + sgst_amount + igst_amount + cess_amount
            item_total = item_taxable + item_total_tax

            # Create invoice item
            invoice_item = InvoiceItem(
                invoice_id=invoice.id,
                product_id=order_item.product_id,
                variant_id=order_item.variant_id,
                sku=order_item.product_sku,
                item_name=order_item.product_name,
                item_description=order_item.variant_name,
                hsn_code=order_item.hsn_code or "84212100",  # Default HSN for water purifiers
                is_service=False,
                serial_numbers={"serials": item_serials} if item_serials else None,
                quantity=Decimal(str(order_item.quantity)),
                uom="NOS",
                unit_price=order_item.unit_price,
                mrp=order_item.unit_mrp,
                discount_percentage=Decimal("0") if not gross_amount else (discount_amount / gross_amount * 100).quantize(Decimal("0.01")),
                discount_amount=discount_amount,
                taxable_value=item_taxable,
                gst_rate=gst_rate,
                cgst_rate=cgst_rate,
                sgst_rate=sgst_rate,
                igst_rate=igst_rate,
                cgst_amount=cgst_amount,
                sgst_amount=sgst_amount,
                igst_amount=igst_amount,
                cess_rate=Decimal("0"),
                cess_amount=cess_amount,
                total_tax=item_total_tax,
                line_total=item_total,
                warranty_months=order_item.warranty_months or 12,
                order_item_id=order_item.id,
            )
            self.db.add(invoice_item)

            # Accumulate totals
            subtotal += gross_amount
            total_discount += discount_amount
            taxable_amount += item_taxable
            cgst_total += cgst_amount
            sgst_total += sgst_amount
            igst_total += igst_amount
            cess_total += cess_amount

        # 9. Update invoice totals
        total_tax = cgst_total + sgst_total + igst_total + cess_total
        grand_total = taxable_amount + total_tax

        # Apply round off
        round_off = Decimal(str(round(float(grand_total)))) - grand_total
        grand_total = Decimal(str(round(float(grand_total))))

        # Calculate amount due (for prepaid orders, should be 0)
        amount_due = grand_total - (order.amount_paid or Decimal("0"))
        if amount_due < 0:
            amount_due = Decimal("0")

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
        invoice.amount_due = amount_due

        # Convert grand total to words
        invoice.amount_in_words = self._amount_to_words(grand_total)

        await self.db.flush()

        # 10. Post accounting entry
        # CRITICAL: This creates the GL entries that flow to P&L
        accounting_posted = False
        try:
            from app.services.accounting_service import AccountingService
            accounting = AccountingService(self.db)
            await accounting.post_sales_invoice(
                invoice_id=invoice.id,
                customer_name=invoice.customer_name,
                subtotal=taxable_amount,
                cgst=cgst_total,
                sgst=sgst_total,
                igst=igst_total,
                total=grand_total,
                is_interstate=is_interstate,
                product_type="purifier",
            )
            accounting_posted = True
            logger.info(f"Accounting entry posted for invoice {invoice.invoice_number}")
        except Exception as e:
            # Log as ERROR (not warning) since this affects financial reporting
            logger.error(
                f"ACCOUNTING FAILURE: Failed to post GL entry for invoice {invoice.invoice_number}. "
                f"Amount: {grand_total}, Customer: {invoice.customer_name}. "
                f"Error: {str(e)}. "
                f"ACTION REQUIRED: Manual journal entry needed for reconciliation."
            )
            # Store accounting status in invoice notes for tracking
            if invoice.internal_notes:
                invoice.internal_notes += f"\n[ACCOUNTING ERROR] GL posting failed: {str(e)}"
            else:
                invoice.internal_notes = f"[ACCOUNTING ERROR] GL posting failed: {str(e)}"

        logger.info(
            f"Auto-generated invoice {invoice.invoice_number} for order {order.order_number} "
            f"on goods issue (manifest: {manifest_number})"
        )

        # Load full invoice with items
        result = await self.db.execute(
            select(TaxInvoice)
            .options(selectinload(TaxInvoice.items))
            .where(TaxInvoice.id == invoice.id)
        )
        return result.scalar_one()

    def _amount_to_words(self, amount: Decimal) -> str:
        """Convert amount to words (Indian numbering system)."""
        try:
            from num2words import num2words
            rupees = int(amount)
            paise = int((amount - rupees) * 100)

            words = num2words(rupees, lang='en_IN').replace(",", "")
            result = f"Rupees {words.title()} Only"

            if paise > 0:
                paise_words = num2words(paise, lang='en_IN').replace(",", "")
                result = f"Rupees {words.title()} and {paise_words.title()} Paise Only"

            return result
        except ImportError:
            # Fallback if num2words not installed
            return f"INR {amount:,.2f}"
        except Exception:
            return f"INR {amount:,.2f}"
