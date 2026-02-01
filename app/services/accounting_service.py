"""
Accounting Service for Automatic GL Posting.

This service handles automatic journal entry creation for business events:
- Sales Invoice → Debit AR, Credit Sales Revenue, Credit GST Output
- COGS Recognition → Debit COGS, Credit Inventory
- GRN Acceptance → Debit Inventory, Credit AP, Debit GST Input
- Payment Receipt → Debit Cash/Bank, Credit AR
- Payment Made → Debit AP, Credit Cash/Bank
"""
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, List, Dict, Any

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.accounting import (
    ChartOfAccount, JournalEntry, JournalEntryLine,
    GeneralLedger, FinancialPeriod, JournalEntryStatus,
    FinancialPeriodStatus, AccountType,
)


class AccountingService:
    """Service for automated accounting entries."""

    # System user ID for automated accounting entries (should be created in seed)
    SYSTEM_USER_ID = "00000000-0000-0000-0000-000000000001"

    # Account code mappings for standard transactions
    ACCOUNT_CODES = {
        # Assets
        "CASH": "1010",
        "BANK_HDFC": "1020",
        "BANK_ICICI": "1021",
        "AR_CUSTOMERS": "1110",
        "AR_DEALERS": "1120",
        "INVENTORY_FG": "1210",
        "INVENTORY_SPARES": "1220",
        "INVENTORY_TRANSIT": "1230",
        "CGST_INPUT": "1410",
        "SGST_INPUT": "1420",
        "IGST_INPUT": "1430",

        # Liabilities
        "AP_VENDORS": "2110",
        "AP_SERVICE": "2120",
        "CGST_OUTPUT": "2210",
        "SGST_OUTPUT": "2220",
        "IGST_OUTPUT": "2230",
        "ADVANCE_CUSTOMERS": "2500",
        "PROVISION_WARRANTY": "2610",

        # Revenue
        "SALES_PURIFIERS": "4110",
        "SALES_SPARES": "4120",
        "SALES_ACCESSORIES": "4130",
        "SERVICE_INSTALLATION": "4210",
        "SERVICE_AMC": "4220",
        "SERVICE_CALL": "4230",
        "SALES_RETURNS": "4400",
        "SALES_DISCOUNT": "4500",

        # Expenses
        "COGS_PURIFIERS": "5100",
        "COGS_SPARES": "5200",
        "FREIGHT_INWARD": "5300",
        "FREIGHT_OUTWARD": "6410",
        "WARRANTY_EXPENSE": "6600",
    }

    def __init__(self, db: AsyncSession, created_by: Optional[uuid.UUID] = None):
        self.db = db
        self.created_by = created_by or uuid.UUID(self.SYSTEM_USER_ID)
        self._account_cache: Dict[str, uuid.UUID] = {}

    async def _get_account_id(self, account_code: str) -> Optional[uuid.UUID]:
        """Get account ID by code with caching."""
        if account_code in self._account_cache:
            return self._account_cache[account_code]

        result = await self.db.execute(
            select(ChartOfAccount.id).where(
                ChartOfAccount.account_code == account_code
            )
        )
        account = result.scalar_one_or_none()
        if account:
            self._account_cache[account_code] = account
        return account

    async def _get_current_period(self) -> Optional[uuid.UUID]:
        """Get the current open financial period (monthly period preferred)."""
        result = await self.db.execute(
            select(FinancialPeriod).where(
                and_(
                    FinancialPeriod.is_current == True,
                    FinancialPeriod.status == FinancialPeriodStatus.OPEN,
                    FinancialPeriod.period_type == "MONTH"  # Prefer monthly period
                )
            ).limit(1)
        )
        period = result.scalar_one_or_none()

        # Fallback to any open period
        if not period:
            result = await self.db.execute(
                select(FinancialPeriod).where(
                    FinancialPeriod.status == FinancialPeriodStatus.OPEN
                ).limit(1)
            )
            period = result.scalar_one_or_none()

        return period.id if period else None

    async def _create_journal_entry(
        self,
        entry_type: str,
        source_type: str,
        source_id: uuid.UUID,
        narration: str,
        lines: List[Dict[str, Any]],
        entry_date: Optional[datetime] = None,
        source_number: Optional[str] = None,
        channel_id: Optional[uuid.UUID] = None,
        auto_post: bool = True,
    ) -> JournalEntry:
        """
        Create a journal entry with lines.

        Args:
            entry_type: Type of entry (SALES, PURCHASE, RECEIPT, PAYMENT, etc.)
            source_type: Source document type (INVOICE, GRN, PAYMENT, etc.)
            source_id: Source document ID
            narration: Entry description
            lines: List of line items with account_code, debit, credit, description
            entry_date: Date of entry (defaults to today)
            source_number: Source document number
            channel_id: Sales channel ID for channel-wise P&L
            auto_post: Whether to auto-post the entry
        """
        from datetime import date as date_type

        period_id = await self._get_current_period()
        if not period_id:
            raise ValueError("No open financial period found")

        # Generate entry number
        entry_number = f"JV-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"

        # Create journal entry
        journal_entry_id = uuid.uuid4()
        journal_entry = JournalEntry(
            id=journal_entry_id,
            entry_number=entry_number,
            entry_type=entry_type,
            entry_date=entry_date.date() if entry_date else date_type.today(),
            period_id=period_id,
            source_type=source_type,
            source_id=source_id,
            source_number=source_number,
            narration=narration,
            channel_id=channel_id,
            status=JournalEntryStatus.DRAFT,
            total_debit=Decimal("0"),
            total_credit=Decimal("0"),
            created_by=self.created_by,
        )

        total_debit = Decimal("0")
        total_credit = Decimal("0")
        created_lines = []

        # Create journal entry lines
        for idx, line_data in enumerate(lines, 1):
            account_id = await self._get_account_id(line_data["account_code"])
            if not account_id:
                raise ValueError(f"Account not found: {line_data['account_code']}")

            debit = Decimal(str(line_data.get("debit", 0)))
            credit = Decimal(str(line_data.get("credit", 0)))

            line_id = uuid.uuid4()
            line = JournalEntryLine(
                id=line_id,
                journal_entry_id=journal_entry_id,
                line_number=idx,
                account_id=account_id,
                debit_amount=debit,
                credit_amount=credit,
                description=line_data.get("description", ""),
            )
            self.db.add(line)
            created_lines.append((line_id, line))

            total_debit += debit
            total_credit += credit

        # Validate debit = credit
        if total_debit != total_credit:
            raise ValueError(
                f"Journal entry unbalanced: Debit={total_debit}, Credit={total_credit}"
            )

        journal_entry.total_debit = total_debit
        journal_entry.total_credit = total_credit

        self.db.add(journal_entry)

        # Auto-post if requested
        if auto_post:
            await self._post_journal_entry(journal_entry, created_lines)

        return journal_entry

    async def _post_journal_entry(self, journal_entry: JournalEntry, created_lines: List):
        """Post journal entry to general ledger."""
        for line_id, line in created_lines:
            # Get current account balance for running balance calculation
            account_result = await self.db.execute(
                select(ChartOfAccount).where(ChartOfAccount.id == line.account_id)
            )
            account = account_result.scalar_one()

            # Calculate balance change
            # For Asset/Expense: Debit increases, Credit decreases
            # For Liability/Equity/Revenue: Credit increases, Debit decreases
            if account.account_type in [AccountType.ASSET, AccountType.EXPENSE]:
                balance_change = line.debit_amount - line.credit_amount
            else:
                balance_change = line.credit_amount - line.debit_amount

            new_balance = account.current_balance + balance_change

            # Create GL entry
            gl_entry = GeneralLedger(
                id=uuid.uuid4(),
                account_id=line.account_id,
                period_id=journal_entry.period_id,
                transaction_date=journal_entry.entry_date,
                journal_entry_id=journal_entry.id,
                journal_line_id=line_id,
                debit_amount=line.debit_amount,
                credit_amount=line.credit_amount,
                running_balance=new_balance,
                narration=line.description or journal_entry.narration,
                channel_id=journal_entry.channel_id,
            )
            self.db.add(gl_entry)

            # Update account balance
            account.current_balance = new_balance

        # Update journal entry status
        journal_entry.status = JournalEntryStatus.POSTED.value

    # ==================== Business Event Handlers ====================

    async def post_sales_invoice(
        self,
        invoice_id: uuid.UUID,
        customer_name: str,
        subtotal: Decimal,
        cgst: Decimal,
        sgst: Decimal,
        igst: Decimal,
        total: Decimal,
        is_interstate: bool = False,
        product_type: str = "purifier",  # purifier, spare, accessory
        channel_id: Optional[uuid.UUID] = None,
    ) -> JournalEntry:
        """
        Post journal entry for sales invoice.

        Debit: Accounts Receivable (Total)
        Credit: Sales Revenue (Subtotal)
        Credit: GST Output (Tax amounts)
        """
        lines = []

        # Debit AR
        lines.append({
            "account_code": self.ACCOUNT_CODES["AR_CUSTOMERS"],
            "debit": total,
            "credit": Decimal("0"),
            "description": f"Invoice to {customer_name}",
        })

        # Credit Sales Revenue based on product type
        revenue_code = {
            "purifier": self.ACCOUNT_CODES["SALES_PURIFIERS"],
            "spare": self.ACCOUNT_CODES["SALES_SPARES"],
            "accessory": self.ACCOUNT_CODES["SALES_ACCESSORIES"],
        }.get(product_type, self.ACCOUNT_CODES["SALES_PURIFIERS"])

        lines.append({
            "account_code": revenue_code,
            "debit": Decimal("0"),
            "credit": subtotal,
            "description": f"Sales revenue - {product_type}",
        })

        # Credit GST Output
        if is_interstate and igst > 0:
            lines.append({
                "account_code": self.ACCOUNT_CODES["IGST_OUTPUT"],
                "debit": Decimal("0"),
                "credit": igst,
                "description": "IGST on sales",
            })
        else:
            if cgst > 0:
                lines.append({
                    "account_code": self.ACCOUNT_CODES["CGST_OUTPUT"],
                    "debit": Decimal("0"),
                    "credit": cgst,
                    "description": "CGST on sales",
                })
            if sgst > 0:
                lines.append({
                    "account_code": self.ACCOUNT_CODES["SGST_OUTPUT"],
                    "debit": Decimal("0"),
                    "credit": sgst,
                    "description": "SGST on sales",
                })

        return await self._create_journal_entry(
            entry_type="SALES",
            source_type="TAX_INVOICE",
            source_id=invoice_id,
            narration=f"Sales invoice to {customer_name}",
            lines=lines,
            channel_id=channel_id,
        )

    async def post_cogs_entry(
        self,
        order_id: uuid.UUID,
        order_number: str,
        cost_amount: Decimal,
        product_type: str = "purifier",
        channel_id: Optional[uuid.UUID] = None,
    ) -> JournalEntry:
        """
        Post COGS entry when order is shipped/delivered.

        Debit: Cost of Goods Sold
        Credit: Inventory
        """
        cogs_code = {
            "purifier": self.ACCOUNT_CODES["COGS_PURIFIERS"],
            "spare": self.ACCOUNT_CODES["COGS_SPARES"],
        }.get(product_type, self.ACCOUNT_CODES["COGS_PURIFIERS"])

        inventory_code = {
            "purifier": self.ACCOUNT_CODES["INVENTORY_FG"],
            "spare": self.ACCOUNT_CODES["INVENTORY_SPARES"],
        }.get(product_type, self.ACCOUNT_CODES["INVENTORY_FG"])

        lines = [
            {
                "account_code": cogs_code,
                "debit": cost_amount,
                "credit": Decimal("0"),
                "description": f"COGS for order {order_number}",
            },
            {
                "account_code": inventory_code,
                "debit": Decimal("0"),
                "credit": cost_amount,
                "description": f"Inventory reduction for order {order_number}",
            },
        ]

        return await self._create_journal_entry(
            entry_type="COGS",
            source_type="ORDER",
            source_id=order_id,
            narration=f"Cost of goods sold - Order {order_number}",
            source_number=order_number,
            lines=lines,
            channel_id=channel_id,
        )

    async def post_grn_entry(
        self,
        grn_id: uuid.UUID,
        grn_number: str,
        vendor_name: str,
        subtotal: Decimal,
        cgst: Decimal,
        sgst: Decimal,
        igst: Decimal,
        total: Decimal,
        is_interstate: bool = False,
        product_type: str = "purifier",
    ) -> JournalEntry:
        """
        Post journal entry for GRN (Goods Received Note).

        Debit: Inventory (Subtotal)
        Debit: GST Input Credit (Tax amounts)
        Credit: Accounts Payable (Total)
        """
        lines = []

        # Debit Inventory
        inventory_code = {
            "purifier": self.ACCOUNT_CODES["INVENTORY_FG"],
            "spare": self.ACCOUNT_CODES["INVENTORY_SPARES"],
        }.get(product_type, self.ACCOUNT_CODES["INVENTORY_FG"])

        lines.append({
            "account_code": inventory_code,
            "debit": subtotal,
            "credit": Decimal("0"),
            "description": f"Goods received from {vendor_name}",
        })

        # Debit GST Input Credit
        if is_interstate and igst > 0:
            lines.append({
                "account_code": self.ACCOUNT_CODES["IGST_INPUT"],
                "debit": igst,
                "credit": Decimal("0"),
                "description": "IGST input credit",
            })
        else:
            if cgst > 0:
                lines.append({
                    "account_code": self.ACCOUNT_CODES["CGST_INPUT"],
                    "debit": cgst,
                    "credit": Decimal("0"),
                    "description": "CGST input credit",
                })
            if sgst > 0:
                lines.append({
                    "account_code": self.ACCOUNT_CODES["SGST_INPUT"],
                    "debit": sgst,
                    "credit": Decimal("0"),
                    "description": "SGST input credit",
                })

        # Credit Accounts Payable
        lines.append({
            "account_code": self.ACCOUNT_CODES["AP_VENDORS"],
            "debit": Decimal("0"),
            "credit": total,
            "description": f"Payable to {vendor_name}",
        })

        return await self._create_journal_entry(
            entry_type="PURCHASE",
            source_type="GRN",
            source_id=grn_id,
            narration=f"GRN {grn_number} from {vendor_name}",
            source_number=grn_number,
            lines=lines,
        )

    async def post_payment_receipt(
        self,
        payment_id: uuid.UUID,
        payment_reference: str,
        customer_name: str,
        amount: Decimal,
        payment_mode: str = "bank",  # cash, bank
    ) -> JournalEntry:
        """
        Post journal entry for payment receipt from customer.

        Debit: Cash/Bank
        Credit: Accounts Receivable
        """
        cash_code = self.ACCOUNT_CODES["CASH"] if payment_mode == "cash" else self.ACCOUNT_CODES["BANK_HDFC"]

        lines = [
            {
                "account_code": cash_code,
                "debit": amount,
                "credit": Decimal("0"),
                "description": f"Payment received from {customer_name}",
            },
            {
                "account_code": self.ACCOUNT_CODES["AR_CUSTOMERS"],
                "debit": Decimal("0"),
                "credit": amount,
                "description": f"AR settlement - {customer_name}",
            },
        ]

        return await self._create_journal_entry(
            entry_type="RECEIPT",
            source_type="PAYMENT",
            source_id=payment_id,
            narration=f"Payment receipt {payment_reference} from {customer_name}",
            source_number=payment_reference,
            lines=lines,
        )

    async def post_vendor_payment(
        self,
        payment_id: uuid.UUID,
        payment_reference: str,
        vendor_name: str,
        amount: Decimal,
        payment_mode: str = "bank",
    ) -> JournalEntry:
        """
        Post journal entry for payment to vendor.

        Debit: Accounts Payable
        Credit: Cash/Bank
        """
        cash_code = self.ACCOUNT_CODES["CASH"] if payment_mode == "cash" else self.ACCOUNT_CODES["BANK_HDFC"]

        lines = [
            {
                "account_code": self.ACCOUNT_CODES["AP_VENDORS"],
                "debit": amount,
                "credit": Decimal("0"),
                "description": f"Payment to {vendor_name}",
            },
            {
                "account_code": cash_code,
                "debit": Decimal("0"),
                "credit": amount,
                "description": f"Payment to vendor - {vendor_name}",
            },
        ]

        return await self._create_journal_entry(
            entry_type="PAYMENT",
            source_type="VENDOR_PAYMENT",
            source_id=payment_id,
            narration=f"Vendor payment {payment_reference} to {vendor_name}",
            source_number=payment_reference,
            lines=lines,
        )

    async def post_warranty_provision(
        self,
        order_id: uuid.UUID,
        order_number: str,
        provision_amount: Decimal,
        channel_id: Optional[uuid.UUID] = None,
    ) -> JournalEntry:
        """
        Post warranty provision entry when product is sold.

        Debit: Warranty Expense
        Credit: Provision for Warranty
        """
        lines = [
            {
                "account_code": self.ACCOUNT_CODES["WARRANTY_EXPENSE"],
                "debit": provision_amount,
                "credit": Decimal("0"),
                "description": f"Warranty provision for order {order_number}",
            },
            {
                "account_code": self.ACCOUNT_CODES["PROVISION_WARRANTY"],
                "debit": Decimal("0"),
                "credit": provision_amount,
                "description": f"Warranty liability for order {order_number}",
            },
        ]

        return await self._create_journal_entry(
            entry_type="PROVISION",
            source_type="ORDER",
            source_id=order_id,
            narration=f"Warranty provision - Order {order_number}",
            source_number=order_number,
            lines=lines,
            channel_id=channel_id,
        )

    async def post_freight_expense(
        self,
        shipment_id: uuid.UUID,
        shipment_number: str,
        freight_amount: Decimal,
        freight_type: str = "outward",  # inward, outward
    ) -> JournalEntry:
        """
        Post freight expense entry.

        Debit: Freight Inward/Outward
        Credit: Accounts Payable (or Cash for immediate payment)
        """
        freight_code = (
            self.ACCOUNT_CODES["FREIGHT_INWARD"]
            if freight_type == "inward"
            else self.ACCOUNT_CODES["FREIGHT_OUTWARD"]
        )

        lines = [
            {
                "account_code": freight_code,
                "debit": freight_amount,
                "credit": Decimal("0"),
                "description": f"Freight for shipment {shipment_number}",
            },
            {
                "account_code": self.ACCOUNT_CODES["AP_SERVICE"],
                "debit": Decimal("0"),
                "credit": freight_amount,
                "description": f"Freight payable - {shipment_number}",
            },
        ]

        return await self._create_journal_entry(
            entry_type="EXPENSE",
            source_type="SHIPMENT",
            source_id=shipment_id,
            narration=f"Freight expense - Shipment {shipment_number}",
            source_number=shipment_number,
            lines=lines,
        )


# Helper function for easy access
async def get_accounting_service(db: AsyncSession) -> AccountingService:
    """Get accounting service instance."""
    return AccountingService(db)
