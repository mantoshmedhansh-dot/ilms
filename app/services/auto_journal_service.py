"""
Auto Journal Entry Generation Service

Automatically generates journal entries for common business transactions:
- Sales invoices -> Sales Revenue, Tax Payable, Accounts Receivable
- Purchase bills -> Inventory/Expense, Tax Receivable, Accounts Payable
- Payment receipts -> Cash/Bank, Accounts Receivable
- Payment made -> Accounts Payable, Cash/Bank
- Bank transactions -> Bank account, Appropriate head

Based on pre-configured accounting rules and templates.

IMPORTANT: This service auto-triggers when:
1. Sales invoice is created (generates DRAFT journal)
2. Payment receipt is created (generates and posts journal)
3. Purchase invoice is approved (generates journal)
"""

from datetime import datetime, date, timezone
from decimal import Decimal
from typing import Optional, Dict, Any, List
from uuid import UUID
from enum import Enum

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.accounting import (
    JournalEntry, JournalEntryLine, ChartOfAccount,
    JournalEntryStatus, AccountSubType
)
from app.models.billing import TaxInvoice, InvoiceType


class TransactionType(str, Enum):
    """Transaction types for auto journal generation."""
    SALES_INVOICE = "SALES_INVOICE"
    SALES_RETURN = "SALES_RETURN"
    PURCHASE_BILL = "PURCHASE_BILL"
    PURCHASE_RETURN = "PURCHASE_RETURN"
    PAYMENT_RECEIVED = "PAYMENT_RECEIVED"
    PAYMENT_MADE = "PAYMENT_MADE"
    BANK_DEPOSIT = "BANK_DEPOSIT"
    BANK_WITHDRAWAL = "BANK_WITHDRAWAL"
    EXPENSE = "EXPENSE"
    STOCK_ADJUSTMENT = "STOCK_ADJUSTMENT"


class AutoJournalError(Exception):
    """Custom exception for auto journal errors."""
    def __init__(self, message: str, details: Dict = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class AutoJournalService:
    """
    Service for automatically generating journal entries.

    Uses pre-configured rules to determine debit/credit accounts
    based on transaction type and context.

    NOTE: This system is single-company, so company_id is optional.
    """

    # Default ledger account codes (configurable per system)
    DEFAULT_ACCOUNTS = {
        # Revenue accounts
        "SALES_REVENUE": "4000",
        "SERVICE_REVENUE": "4100",

        # Asset accounts
        "ACCOUNTS_RECEIVABLE": "1300",
        "CASH": "1010",
        "BANK": "1020",
        "INVENTORY": "1400",

        # Liability accounts
        "ACCOUNTS_PAYABLE": "2100",
        "GST_OUTPUT": "2300",
        "GST_INPUT": "1500",
        "CGST_PAYABLE": "2310",
        "SGST_PAYABLE": "2320",
        "IGST_PAYABLE": "2330",
        "CGST_RECEIVABLE": "1510",
        "SGST_RECEIVABLE": "1520",
        "IGST_RECEIVABLE": "1530",
        "TDS_PAYABLE": "2400",
        "TDS_RECEIVABLE": "1600",

        # Expense accounts
        "PURCHASE": "5000",
        "COST_OF_GOODS_SOLD": "5100",
        "DISCOUNT_ALLOWED": "6100",
        "DISCOUNT_RECEIVED": "4200",
        "ROUND_OFF": "6900",
    }

    def __init__(self, db: AsyncSession, company_id: UUID = None):
        self.db = db
        self.company_id = company_id  # Optional for single-company systems

    async def get_account_by_code(self, code: str) -> Optional[ChartOfAccount]:
        """Get ledger account by account_code."""
        result = await self.db.execute(
            select(ChartOfAccount).where(
                ChartOfAccount.account_code == code
            )
        )
        return result.scalar_one_or_none()

    async def get_account_by_id(self, account_id: UUID) -> Optional[ChartOfAccount]:
        """Get ledger account by ID."""
        result = await self.db.execute(
            select(ChartOfAccount).where(ChartOfAccount.id == account_id)
        )
        return result.scalar_one_or_none()

    async def get_or_create_account(
        self,
        code: str,
        name: str,
        account_type: str,
        sub_type: str = None
    ) -> ChartOfAccount:
        """Get or create a ledger account."""
        account = await self.get_account_by_code(code)

        if not account:
            account = ChartOfAccount(
                account_code=code,
                account_name=name,
                account_type=account_type,
                account_sub_type=sub_type,
                is_active=True,
                allow_direct_posting=True
            )
            self.db.add(account)
            await self.db.flush()

        return account

    async def get_customer_ar_account(self, customer_id: UUID) -> ChartOfAccount:
        """
        Get Accounts Receivable account for a customer.
        Uses customer's linked GL account if available, otherwise default AR.
        """
        from app.models.customer import Customer

        result = await self.db.execute(
            select(Customer).where(Customer.id == customer_id)
        )
        customer = result.scalar_one_or_none()

        if customer and customer.gl_account_id:
            account = await self.get_account_by_id(customer.gl_account_id)
            if account:
                return account

        # Fall back to default AR account
        return await self.get_or_create_account(
            self.DEFAULT_ACCOUNTS["ACCOUNTS_RECEIVABLE"],
            "Accounts Receivable",
            "ASSET",
            AccountSubType.ACCOUNTS_RECEIVABLE.value
        )

    async def get_vendor_ap_account(self, vendor_id: UUID) -> ChartOfAccount:
        """
        Get Accounts Payable account for a vendor.
        Uses vendor's linked GL account if available, otherwise default AP.
        """
        from app.models.vendor import Vendor

        result = await self.db.execute(
            select(Vendor).where(Vendor.id == vendor_id)
        )
        vendor = result.scalar_one_or_none()

        if vendor and vendor.gl_account_id:
            account = await self.get_account_by_id(vendor.gl_account_id)
            if account:
                return account

        # Fall back to default AP account
        return await self.get_or_create_account(
            self.DEFAULT_ACCOUNTS["ACCOUNTS_PAYABLE"],
            "Accounts Payable",
            "LIABILITY",
            AccountSubType.ACCOUNTS_PAYABLE.value
        )

    async def generate_for_sales_invoice(
        self,
        invoice_id: UUID,
        user_id: Optional[UUID] = None,
        auto_post: bool = False
    ) -> JournalEntry:
        """
        Generate journal entry for a sales invoice.

        Debit: Accounts Receivable (customer's GL account if linked)
        Credit: Sales Revenue, CGST/SGST/IGST Payable

        Args:
            invoice_id: ID of the sales invoice
            user_id: User creating the journal entry
            auto_post: If True, automatically post the journal entry
        """
        # Get invoice with items
        result = await self.db.execute(
            select(TaxInvoice)
            .options(selectinload(TaxInvoice.items))
            .where(TaxInvoice.id == invoice_id)
        )
        invoice = result.scalar_one_or_none()

        if not invoice:
            raise AutoJournalError("Invoice not found")

        # Check if journal entry already exists
        existing = await self.db.execute(
            select(JournalEntry).where(
                and_(
                    JournalEntry.reference_type == "TaxInvoice",
                    JournalEntry.reference_id == invoice_id
                )
            )
        )
        if existing.scalar_one_or_none():
            raise AutoJournalError("Journal entry already exists for this invoice")

        # Get AR account (use customer's linked GL account if available)
        if invoice.customer_id:
            ar_account = await self.get_customer_ar_account(invoice.customer_id)
        else:
            ar_account = await self.get_or_create_account(
                self.DEFAULT_ACCOUNTS["ACCOUNTS_RECEIVABLE"],
                "Accounts Receivable",
                "ASSET",
                AccountSubType.ACCOUNTS_RECEIVABLE.value
            )

        sales_account = await self.get_or_create_account(
            self.DEFAULT_ACCOUNTS["SALES_REVENUE"],
            "Sales Revenue",
            "REVENUE",
            AccountSubType.SALES_REVENUE.value
        )

        # Create journal entry
        journal = JournalEntry(
            entry_type="SALES",
            entry_number=f"JV-SALE-{invoice.invoice_number}",
            entry_date=invoice.invoice_date,
            reference_type="TaxInvoice",
            reference_id=invoice_id,
            reference_number=invoice.invoice_number,
            narration=f"Sales invoice {invoice.invoice_number} to {invoice.customer_name}",
            status=JournalEntryStatus.DRAFT.value,
            created_by=user_id,
        )
        self.db.add(journal)
        await self.db.flush()

        journal_lines = []

        # Debit: Accounts Receivable (full amount)
        ar_line = JournalEntryLine(
            journal_entry_id=journal.id,
            account_id=ar_account.id,
            debit_amount=invoice.grand_total,
            credit_amount=Decimal("0"),
            description=f"Receivable from {invoice.customer_name}"
        )
        journal_lines.append(ar_line)

        # Credit: Sales Revenue (taxable amount)
        sales_line = JournalEntryLine(
            journal_entry_id=journal.id,
            account_id=sales_account.id,
            debit_amount=Decimal("0"),
            credit_amount=invoice.taxable_amount,
            description=f"Sales to {invoice.customer_name}"
        )
        journal_lines.append(sales_line)

        # Credit: Tax accounts
        if invoice.cgst_amount and invoice.cgst_amount > 0:
            cgst_account = await self.get_or_create_account(
                self.DEFAULT_ACCOUNTS["CGST_PAYABLE"],
                "CGST Payable",
                "LIABILITY",
                AccountSubType.TAX_PAYABLE.value
            )
            cgst_line = JournalEntryLine(
                journal_entry_id=journal.id,
                account_id=cgst_account.id,
                debit_amount=Decimal("0"),
                credit_amount=invoice.cgst_amount,
                description="CGST on sales"
            )
            journal_lines.append(cgst_line)

        if invoice.sgst_amount and invoice.sgst_amount > 0:
            sgst_account = await self.get_or_create_account(
                self.DEFAULT_ACCOUNTS["SGST_PAYABLE"],
                "SGST Payable",
                "LIABILITY",
                AccountSubType.TAX_PAYABLE.value
            )
            sgst_line = JournalEntryLine(
                journal_entry_id=journal.id,
                account_id=sgst_account.id,
                debit_amount=Decimal("0"),
                credit_amount=invoice.sgst_amount,
                description="SGST on sales"
            )
            journal_lines.append(sgst_line)

        if invoice.igst_amount and invoice.igst_amount > 0:
            igst_account = await self.get_or_create_account(
                self.DEFAULT_ACCOUNTS["IGST_PAYABLE"],
                "IGST Payable",
                "LIABILITY",
                AccountSubType.TAX_PAYABLE.value
            )
            igst_line = JournalEntryLine(
                journal_entry_id=journal.id,
                account_id=igst_account.id,
                debit_amount=Decimal("0"),
                credit_amount=invoice.igst_amount,
                description="IGST on sales"
            )
            journal_lines.append(igst_line)

        # Handle round-off
        if invoice.round_off and invoice.round_off != 0:
            roundoff_account = await self.get_or_create_account(
                self.DEFAULT_ACCOUNTS["ROUND_OFF"],
                "Round Off",
                "EXPENSE" if invoice.round_off > 0 else "REVENUE"
            )
            roundoff_line = JournalEntryLine(
                journal_entry_id=journal.id,
                account_id=roundoff_account.id,
                debit_amount=Decimal("0") if invoice.round_off > 0 else abs(invoice.round_off),
                credit_amount=invoice.round_off if invoice.round_off > 0 else Decimal("0"),
                description="Round off adjustment"
            )
            journal_lines.append(roundoff_line)

        # Add all lines
        for line in journal_lines:
            self.db.add(line)

        # Calculate totals
        total_debit = sum(line.debit_amount for line in journal_lines)
        total_credit = sum(line.credit_amount for line in journal_lines)
        journal.total_debit = total_debit
        journal.total_credit = total_credit

        # Verify balanced
        if abs(total_debit - total_credit) > Decimal("0.01"):
            raise AutoJournalError(
                f"Journal entry not balanced. Debit: {total_debit}, Credit: {total_credit}",
                {"difference": float(total_debit - total_credit)}
            )

        # Auto-post if requested
        if auto_post:
            journal.status = JournalEntryStatus.POSTED.value
            journal.posted_at = datetime.now(timezone.utc)

        await self.db.flush()

        return journal

    async def generate_for_payment_receipt(
        self,
        receipt_id: UUID,
        bank_account_code: str = None,
        user_id: Optional[UUID] = None,
        auto_post: bool = True
    ) -> JournalEntry:
        """
        Generate journal entry for payment receipt.

        Debit: Cash/Bank
        Credit: Accounts Receivable (customer's GL account if linked)

        Args:
            receipt_id: ID of the payment receipt
            bank_account_code: Optional bank account code (defaults to BANK)
            user_id: User creating the journal entry
            auto_post: If True, automatically post the journal entry (default True for receipts)
        """
        from app.models.billing import PaymentReceipt

        result = await self.db.execute(
            select(PaymentReceipt).where(PaymentReceipt.id == receipt_id)
        )
        receipt = result.scalar_one_or_none()

        if not receipt:
            raise AutoJournalError("Payment receipt not found")

        # Check if journal entry already exists
        existing = await self.db.execute(
            select(JournalEntry).where(
                and_(
                    JournalEntry.reference_type == "PaymentReceipt",
                    JournalEntry.reference_id == receipt_id
                )
            )
        )
        if existing.scalar_one_or_none():
            raise AutoJournalError("Journal entry already exists for this receipt")

        # Determine cash/bank account
        if receipt.payment_mode in ["CASH", "COD"]:
            debit_account = await self.get_or_create_account(
                self.DEFAULT_ACCOUNTS["CASH"],
                "Cash in Hand",
                "ASSET",
                AccountSubType.CASH.value
            )
        else:
            bank_code = bank_account_code or self.DEFAULT_ACCOUNTS["BANK"]
            debit_account = await self.get_or_create_account(
                bank_code,
                "Bank Account",
                "ASSET",
                AccountSubType.BANK.value
            )

        # Get AR account (use customer's linked GL account if available)
        if receipt.customer_id:
            ar_account = await self.get_customer_ar_account(receipt.customer_id)
        else:
            ar_account = await self.get_or_create_account(
                self.DEFAULT_ACCOUNTS["ACCOUNTS_RECEIVABLE"],
                "Accounts Receivable",
                "ASSET",
                AccountSubType.ACCOUNTS_RECEIVABLE.value
            )

        # Create journal entry
        journal = JournalEntry(
            entry_type="RECEIPT",
            entry_number=f"JV-REC-{receipt.receipt_number}",
            entry_date=receipt.receipt_date,
            reference_type="PaymentReceipt",
            reference_id=receipt_id,
            reference_number=receipt.receipt_number,
            narration=f"Payment received via {receipt.payment_mode}",
            status=JournalEntryStatus.DRAFT.value,
            created_by=user_id,
        )
        self.db.add(journal)
        await self.db.flush()

        # Debit: Cash/Bank
        debit_line = JournalEntryLine(
            journal_entry_id=journal.id,
            account_id=debit_account.id,
            debit_amount=receipt.amount,
            credit_amount=Decimal("0"),
            description=f"Payment received from customer"
        )
        self.db.add(debit_line)

        # Credit: Accounts Receivable
        credit_line = JournalEntryLine(
            journal_entry_id=journal.id,
            account_id=ar_account.id,
            debit_amount=Decimal("0"),
            credit_amount=receipt.amount,
            description=f"Receipt against invoice"
        )
        self.db.add(credit_line)

        journal.total_debit = receipt.amount
        journal.total_credit = receipt.amount

        # Auto-post if requested (default for receipts)
        if auto_post:
            journal.status = JournalEntryStatus.POSTED.value
            journal.posted_at = datetime.now(timezone.utc)

        await self.db.flush()

        return journal

    async def generate_for_order_payment(
        self,
        order_id: UUID,
        amount: Decimal,
        payment_method: str,
        reference_number: str,
        user_id: Optional[UUID] = None,
        auto_post: bool = True,
        is_cash: bool = False
    ) -> JournalEntry:
        """
        Generate journal entry for order payment.

        Debit: Cash/Bank (based on payment method)
        Credit: Accounts Receivable

        Args:
            order_id: ID of the order
            amount: Payment amount
            payment_method: Payment method (CASH, UPI, CARD, etc.)
            reference_number: Transaction reference
            user_id: User creating the journal entry
            auto_post: If True, automatically post the journal entry
            is_cash: If True, use Cash account; else use Bank account
        """
        from app.models.order import Order

        result = await self.db.execute(
            select(Order).where(Order.id == order_id)
        )
        order = result.scalar_one_or_none()

        if not order:
            raise AutoJournalError("Order not found")

        # Check if journal entry already exists for this payment reference
        existing = await self.db.execute(
            select(JournalEntry).where(
                and_(
                    JournalEntry.source_type == "ORDER_PAYMENT",
                    JournalEntry.source_id == order_id,
                    JournalEntry.narration.contains(reference_number)
                )
            )
        )
        if existing.scalar_one_or_none():
            raise AutoJournalError("Journal entry already exists for this payment")

        # Determine cash/bank account
        if is_cash or payment_method.upper() in ["CASH", "COD"]:
            debit_account = await self.get_or_create_account(
                self.DEFAULT_ACCOUNTS["CASH"],
                "Cash in Hand",
                "ASSET",
                "CASH"
            )
        else:
            debit_account = await self.get_or_create_account(
                self.DEFAULT_ACCOUNTS["BANK"],
                "Bank Account",
                "ASSET",
                "BANK"
            )

        # Get AR account
        credit_account = await self.get_or_create_account(
            self.DEFAULT_ACCOUNTS["ACCOUNTS_RECEIVABLE"],
            "Accounts Receivable",
            "ASSET",
            "ACCOUNTS_RECEIVABLE"
        )

        # Get or create financial period
        period = await self._get_or_create_period()

        # Create journal entry
        entry_number = await self._generate_entry_number()
        narration = f"Payment received for Order {order.order_number} via {payment_method}. Ref: {reference_number}"

        journal = JournalEntry(
            entry_number=entry_number,
            entry_date=date.today(),
            entry_type="RECEIPT",
            source_type="ORDER_PAYMENT",
            source_id=order_id,
            source_number=order.order_number,
            period_id=period.id,
            narration=narration,
            total_debit=amount,
            total_credit=amount,
            status="DRAFT",
            created_by=user_id,
        )
        self.db.add(journal)
        await self.db.flush()

        # Create journal lines
        lines = []

        # Debit: Cash/Bank
        debit_line = JournalEntryLine(
            journal_entry_id=journal.id,
            account_id=debit_account.id,
            debit_amount=amount,
            credit_amount=Decimal("0"),
            description=f"Payment received - {order.order_number}",
        )
        self.db.add(debit_line)
        lines.append((debit_line.id, debit_line))

        # Credit: Accounts Receivable
        credit_line = JournalEntryLine(
            journal_entry_id=journal.id,
            account_id=credit_account.id,
            debit_amount=Decimal("0"),
            credit_amount=amount,
            description=f"AR cleared - {order.order_number}",
        )
        self.db.add(credit_line)
        lines.append((credit_line.id, credit_line))

        await self.db.flush()

        # Post to GL if auto_post
        if auto_post:
            await self._post_journal_entry(journal, lines)
            journal.status = "POSTED"
            journal.posted_at = datetime.now(timezone.utc)

        await self.db.flush()

        return journal

    async def generate_for_purchase_bill(
        self,
        purchase_invoice_id: UUID,
        user_id: Optional[UUID] = None,
        auto_post: bool = False
    ) -> JournalEntry:
        """
        Generate journal entry for a purchase bill/invoice.

        Debit: Purchase/Expense, GST Input
        Credit: Accounts Payable (vendor's GL account if linked)

        Args:
            purchase_invoice_id: ID of the purchase invoice
            user_id: User creating the journal entry
            auto_post: If True, automatically post the journal entry
        """
        from app.models.purchase import PurchaseInvoice

        result = await self.db.execute(
            select(PurchaseInvoice)
            .options(selectinload(PurchaseInvoice.items))
            .where(PurchaseInvoice.id == purchase_invoice_id)
        )
        invoice = result.scalar_one_or_none()

        if not invoice:
            raise AutoJournalError("Purchase invoice not found")

        # Check if journal entry already exists
        existing = await self.db.execute(
            select(JournalEntry).where(
                and_(
                    JournalEntry.reference_type == "PurchaseInvoice",
                    JournalEntry.reference_id == purchase_invoice_id
                )
            )
        )
        if existing.scalar_one_or_none():
            raise AutoJournalError("Journal entry already exists for this purchase invoice")

        # Get AP account (use vendor's linked GL account if available)
        if invoice.vendor_id:
            ap_account = await self.get_vendor_ap_account(invoice.vendor_id)
        else:
            ap_account = await self.get_or_create_account(
                self.DEFAULT_ACCOUNTS["ACCOUNTS_PAYABLE"],
                "Accounts Payable",
                "LIABILITY",
                AccountSubType.ACCOUNTS_PAYABLE.value
            )

        purchase_account = await self.get_or_create_account(
            self.DEFAULT_ACCOUNTS["PURCHASE"],
            "Purchases",
            "EXPENSE",
            AccountSubType.COST_OF_GOODS.value
        )

        # Create journal entry
        vendor_name = invoice.vendor.name if invoice.vendor else "Vendor"
        journal = JournalEntry(
            entry_type="PURCHASE",
            entry_number=f"JV-PUR-{invoice.invoice_number}",
            entry_date=invoice.invoice_date,
            reference_type="PurchaseInvoice",
            reference_id=purchase_invoice_id,
            reference_number=invoice.invoice_number,
            narration=f"Purchase invoice {invoice.invoice_number} from {vendor_name}",
            status=JournalEntryStatus.DRAFT.value,
            created_by=user_id,
        )
        self.db.add(journal)
        await self.db.flush()

        journal_lines = []

        # Debit: Purchase (taxable amount)
        purchase_line = JournalEntryLine(
            journal_entry_id=journal.id,
            account_id=purchase_account.id,
            debit_amount=invoice.taxable_amount or invoice.total_amount,
            credit_amount=Decimal("0"),
            description=f"Purchase from {vendor_name}"
        )
        journal_lines.append(purchase_line)

        # Debit: GST Input accounts
        if hasattr(invoice, 'cgst_amount') and invoice.cgst_amount and invoice.cgst_amount > 0:
            cgst_account = await self.get_or_create_account(
                self.DEFAULT_ACCOUNTS["CGST_RECEIVABLE"],
                "CGST Input",
                "ASSET"
            )
            cgst_line = JournalEntryLine(
                journal_entry_id=journal.id,
                account_id=cgst_account.id,
                debit_amount=invoice.cgst_amount,
                credit_amount=Decimal("0"),
                description="CGST Input on purchase"
            )
            journal_lines.append(cgst_line)

        if hasattr(invoice, 'sgst_amount') and invoice.sgst_amount and invoice.sgst_amount > 0:
            sgst_account = await self.get_or_create_account(
                self.DEFAULT_ACCOUNTS["SGST_RECEIVABLE"],
                "SGST Input",
                "ASSET"
            )
            sgst_line = JournalEntryLine(
                journal_entry_id=journal.id,
                account_id=sgst_account.id,
                debit_amount=invoice.sgst_amount,
                credit_amount=Decimal("0"),
                description="SGST Input on purchase"
            )
            journal_lines.append(sgst_line)

        if hasattr(invoice, 'igst_amount') and invoice.igst_amount and invoice.igst_amount > 0:
            igst_account = await self.get_or_create_account(
                self.DEFAULT_ACCOUNTS["IGST_RECEIVABLE"],
                "IGST Input",
                "ASSET"
            )
            igst_line = JournalEntryLine(
                journal_entry_id=journal.id,
                account_id=igst_account.id,
                debit_amount=invoice.igst_amount,
                credit_amount=Decimal("0"),
                description="IGST Input on purchase"
            )
            journal_lines.append(igst_line)

        # Credit: Accounts Payable (full amount)
        ap_line = JournalEntryLine(
            journal_entry_id=journal.id,
            account_id=ap_account.id,
            debit_amount=Decimal("0"),
            credit_amount=invoice.total_amount,
            description=f"Payable to {vendor_name}"
        )
        journal_lines.append(ap_line)

        # Add all lines
        for line in journal_lines:
            self.db.add(line)

        # Calculate totals
        total_debit = sum(line.debit_amount for line in journal_lines)
        total_credit = sum(line.credit_amount for line in journal_lines)
        journal.total_debit = total_debit
        journal.total_credit = total_credit

        # Verify balanced
        if abs(total_debit - total_credit) > Decimal("0.01"):
            raise AutoJournalError(
                f"Journal entry not balanced. Debit: {total_debit}, Credit: {total_credit}",
                {"difference": float(total_debit - total_credit)}
            )

        # Auto-post if requested
        if auto_post:
            journal.status = JournalEntryStatus.POSTED.value
            journal.posted_at = datetime.now(timezone.utc)

        await self.db.flush()

        return journal

    async def generate_for_stock_adjustment(
        self,
        adjustment_id: UUID,
        adjustment_number: str,
        adjustment_type: str,  # "POSITIVE" or "NEGATIVE"
        total_value: Decimal,
        reason: str,
        user_id: Optional[UUID] = None,
        auto_post: bool = True
    ) -> JournalEntry:
        """
        Generate journal entry for stock adjustment.

        For POSITIVE adjustment (stock increase):
            Debit: Inventory
            Credit: Inventory Adjustment (Income/Gain)

        For NEGATIVE adjustment (stock decrease):
            Debit: Inventory Adjustment (Expense/Loss)
            Credit: Inventory

        Args:
            adjustment_id: ID of the stock adjustment
            adjustment_number: Adjustment reference number
            adjustment_type: "POSITIVE" or "NEGATIVE"
            total_value: Total value of the adjustment
            reason: Reason for adjustment
            user_id: User creating the journal entry
            auto_post: If True, automatically post the journal entry
        """
        # Check if journal entry already exists
        existing = await self.db.execute(
            select(JournalEntry).where(
                and_(
                    JournalEntry.source_type == "STOCK_ADJUSTMENT",
                    JournalEntry.source_id == adjustment_id
                )
            )
        )
        if existing.scalar_one_or_none():
            raise AutoJournalError("Journal entry already exists for this adjustment")

        # Get inventory account
        inventory_account = await self.get_or_create_account(
            self.DEFAULT_ACCOUNTS.get("INVENTORY", "1200"),
            "Inventory",
            "ASSET",
            "INVENTORY"
        )

        # Get adjustment account (use expense for negative, income for positive)
        if adjustment_type == "NEGATIVE":
            adjustment_account = await self.get_or_create_account(
                "5200",  # Inventory Loss/Write-off
                "Inventory Write-off",
                "EXPENSE",
                "INVENTORY_LOSS"
            )
        else:
            adjustment_account = await self.get_or_create_account(
                "4200",  # Inventory Gain
                "Inventory Gain",
                "REVENUE",
                "INVENTORY_GAIN"
            )

        # Get or create financial period
        period = await self._get_or_create_period()

        # Create journal entry
        entry_number = await self._generate_entry_number()
        narration = f"Stock adjustment {adjustment_number}: {reason}"

        journal = JournalEntry(
            entry_number=entry_number,
            entry_date=date.today(),
            entry_type="ADJUSTMENT",
            source_type="STOCK_ADJUSTMENT",
            source_id=adjustment_id,
            source_number=adjustment_number,
            period_id=period.id,
            narration=narration,
            total_debit=total_value,
            total_credit=total_value,
            status="DRAFT",
            created_by=user_id,
        )
        self.db.add(journal)
        await self.db.flush()

        # Create journal lines
        lines = []

        if adjustment_type == "NEGATIVE":
            # Stock decrease: DR Expense, CR Inventory
            debit_line = JournalEntryLine(
                journal_entry_id=journal.id,
                account_id=adjustment_account.id,
                debit_amount=total_value,
                credit_amount=Decimal("0"),
                description=f"Inventory write-off - {adjustment_number}",
            )
            credit_line = JournalEntryLine(
                journal_entry_id=journal.id,
                account_id=inventory_account.id,
                debit_amount=Decimal("0"),
                credit_amount=total_value,
                description=f"Inventory reduced - {adjustment_number}",
            )
        else:
            # Stock increase: DR Inventory, CR Income
            debit_line = JournalEntryLine(
                journal_entry_id=journal.id,
                account_id=inventory_account.id,
                debit_amount=total_value,
                credit_amount=Decimal("0"),
                description=f"Inventory increased - {adjustment_number}",
            )
            credit_line = JournalEntryLine(
                journal_entry_id=journal.id,
                account_id=adjustment_account.id,
                debit_amount=Decimal("0"),
                credit_amount=total_value,
                description=f"Inventory gain - {adjustment_number}",
            )

        self.db.add(debit_line)
        self.db.add(credit_line)
        lines.append((debit_line.id, debit_line))
        lines.append((credit_line.id, credit_line))

        await self.db.flush()

        # Post to GL if auto_post
        if auto_post:
            await self._post_journal_entry(journal, lines)
            journal.status = "POSTED"
            journal.posted_at = datetime.now(timezone.utc)

        await self.db.flush()

        return journal

    async def generate_for_bank_transaction(
        self,
        bank_transaction_id: UUID,
        contra_account_code: str,
        user_id: Optional[UUID] = None
    ) -> JournalEntry:
        """
        Generate journal entry for bank transaction.

        For deposits: Debit Bank, Credit Contra Account
        For withdrawals: Debit Contra Account, Credit Bank
        """
        from app.models.banking import BankTransaction, BankAccount, TransactionType

        result = await self.db.execute(
            select(BankTransaction).where(BankTransaction.id == bank_transaction_id)
        )
        txn = result.scalar_one_or_none()

        if not txn:
            raise AutoJournalError("Bank transaction not found")

        # Get bank account
        bank_result = await self.db.execute(
            select(BankAccount).where(BankAccount.id == txn.bank_account_id)
        )
        bank_account = bank_result.scalar_one_or_none()

        if not bank_account:
            raise AutoJournalError("Bank account not found")

        # Check if journal already exists
        existing = await self.db.execute(
            select(JournalEntry).where(
                and_(
                    JournalEntry.reference_type == "BankTransaction",
                    JournalEntry.reference_id == bank_transaction_id
                )
            )
        )
        if existing.scalar_one_or_none():
            raise AutoJournalError("Journal entry already exists for this transaction")

        # Get accounts
        bank_ledger = await self.get_or_create_account(
            f"BANK-{bank_account.account_number[-4:]}",
            f"{bank_account.bank_name} - {bank_account.account_number[-4:]}",
            "ASSET",
            AccountSubType.BANK.value
        )

        contra_ledger = await self.get_account_by_code(contra_account_code)
        if not contra_ledger:
            raise AutoJournalError(f"Contra account not found: {contra_account_code}")

        # Create journal
        journal = JournalEntry(
            entry_type="PAYMENT",
            entry_number=f"JV-BANK-{txn.id.hex[:8].upper()}",
            entry_date=txn.transaction_date,
            reference_type="BankTransaction",
            reference_id=bank_transaction_id,
            reference_number=txn.reference_number,
            narration=txn.description[:500] if txn.description else "Bank transaction",
            status=JournalEntryStatus.DRAFT.value,
            created_by=user_id,
        )
        self.db.add(journal)
        await self.db.flush()

        if txn.transaction_type == TransactionType.CREDIT:
            # Deposit: Debit Bank, Credit Contra
            bank_line = JournalEntryLine(
                journal_entry_id=journal.id,
                account_id=bank_ledger.id,
                debit_amount=txn.amount,
                credit_amount=Decimal("0"),
                description="Bank deposit"
            )
            contra_line = JournalEntryLine(
                journal_entry_id=journal.id,
                account_id=contra_ledger.id,
                debit_amount=Decimal("0"),
                credit_amount=txn.amount,
                description=txn.description[:200] if txn.description else ""
            )
        else:
            # Withdrawal: Debit Contra, Credit Bank
            contra_line = JournalEntryLine(
                journal_entry_id=journal.id,
                account_id=contra_ledger.id,
                debit_amount=txn.amount,
                credit_amount=Decimal("0"),
                description=txn.description[:200] if txn.description else ""
            )
            bank_line = JournalEntryLine(
                journal_entry_id=journal.id,
                account_id=bank_ledger.id,
                debit_amount=Decimal("0"),
                credit_amount=txn.amount,
                description="Bank withdrawal"
            )

        self.db.add(bank_line)
        self.db.add(contra_line)

        journal.total_debit = txn.amount
        journal.total_credit = txn.amount

        await self.db.flush()

        # Mark bank transaction as having journal
        txn.matched_journal_entry_id = journal.id
        await self.db.flush()

        return journal

    async def post_journal_entry(self, journal_id: UUID) -> JournalEntry:
        """Post a draft journal entry."""
        result = await self.db.execute(
            select(JournalEntry)
            .options(selectinload(JournalEntry.lines))
            .where(JournalEntry.id == journal_id)
        )
        journal = result.scalar_one_or_none()

        if not journal:
            raise AutoJournalError("Journal entry not found")

        if journal.status != JournalEntryStatus.DRAFT.value:
            raise AutoJournalError(f"Cannot post journal in {journal.status} status")

        # Verify balanced
        total_debit = sum(line.debit_amount or Decimal("0") for line in journal.lines)
        total_credit = sum(line.credit_amount or Decimal("0") for line in journal.lines)

        if abs(total_debit - total_credit) > Decimal("0.01"):
            raise AutoJournalError(
                "Journal entry is not balanced",
                {"debit": float(total_debit), "credit": float(total_credit)}
            )

        journal.status = JournalEntryStatus.POSTED.value
        journal.posted_at = datetime.now(timezone.utc)

        await self.db.flush()

        return journal

    # ==================== Helper Methods ====================

    async def _get_or_create_period(self):
        """Get current financial period or create one if none exists."""
        from app.models.accounting import FinancialPeriod
        import uuid as uuid_module

        # Try to find current open period
        result = await self.db.execute(
            select(FinancialPeriod).where(
                and_(
                    FinancialPeriod.is_current == True,
                    FinancialPeriod.status == "OPEN"
                )
            ).limit(1)
        )
        period = result.scalar_one_or_none()

        if period:
            return period

        # Create a default period for current financial year
        today = date.today()
        # Indian FY: April to March
        if today.month >= 4:
            fy_start = date(today.year, 4, 1)
            fy_end = date(today.year + 1, 3, 31)
            fy_name = f"FY {today.year}-{str(today.year + 1)[2:]}"
        else:
            fy_start = date(today.year - 1, 4, 1)
            fy_end = date(today.year, 3, 31)
            fy_name = f"FY {today.year - 1}-{str(today.year)[2:]}"

        period = FinancialPeriod(
            id=uuid_module.uuid4(),
            period_name=fy_name,
            period_code=fy_name.replace(" ", "").replace("-", ""),
            financial_year=f"{fy_start.year}-{fy_end.year % 100:02d}",
            period_type="YEARLY",
            is_year_end=False,
            start_date=fy_start,
            end_date=fy_end,
            status="OPEN",
            is_current=True,
            is_adjustment_period=False,
        )
        self.db.add(period)
        await self.db.flush()

        return period

    async def _generate_entry_number(self) -> str:
        """Generate a unique journal entry number."""
        from sqlalchemy import func
        import uuid as uuid_module

        # Format: JV-YYYYMM-XXXX
        today = date.today()
        prefix = f"JV-{today.strftime('%Y%m')}-"

        # Count existing entries this month
        result = await self.db.execute(
            select(func.count(JournalEntry.id)).where(
                JournalEntry.entry_number.like(f"{prefix}%")
            )
        )
        count = result.scalar() or 0

        return f"{prefix}{(count + 1):04d}"

    async def _post_journal_entry(self, journal: JournalEntry, lines: List):
        """Post journal entry to general ledger."""
        from app.models.accounting import GeneralLedger, AccountType
        import uuid as uuid_module

        for line_id, line in lines:
            # Get account for balance type determination
            account = await self.get_account_by_id(line.account_id)
            if not account:
                continue

            # Calculate balance change based on account type
            # Asset/Expense: Debit increases, Credit decreases
            # Liability/Equity/Revenue: Credit increases, Debit decreases
            if account.account_type in ["ASSET", "EXPENSE"]:
                balance_change = (line.debit_amount or Decimal("0")) - (line.credit_amount or Decimal("0"))
            else:
                balance_change = (line.credit_amount or Decimal("0")) - (line.debit_amount or Decimal("0"))

            new_balance = (account.current_balance or Decimal("0")) + balance_change

            # Create GL entry
            gl_entry = GeneralLedger(
                id=uuid_module.uuid4(),
                account_id=line.account_id,
                period_id=journal.period_id,
                transaction_date=journal.entry_date,
                journal_entry_id=journal.id,
                journal_line_id=line.id if hasattr(line, 'id') and line.id else line_id,
                debit_amount=line.debit_amount or Decimal("0"),
                credit_amount=line.credit_amount or Decimal("0"),
                running_balance=new_balance,
                narration=line.description or journal.narration,
            )
            self.db.add(gl_entry)

            # Update account balance
            account.current_balance = new_balance

        await self.db.flush()
