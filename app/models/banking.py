"""Banking models for bank accounts, transactions, and reconciliation."""
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Optional, List
from uuid import UUID, uuid4

from sqlalchemy import (
    Column, String, Text, Numeric, Boolean, Date, DateTime,
    ForeignKey, Integer
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship, Mapped, mapped_column

from app.database import Base


class AccountType(str, Enum):
    """Bank account types."""
    CURRENT = "CURRENT"
    SAVINGS = "SAVINGS"
    CASH_CREDIT = "CASH_CREDIT"
    OVERDRAFT = "OVERDRAFT"
    FIXED_DEPOSIT = "FIXED_DEPOSIT"


class TransactionType(str, Enum):
    """Bank transaction types."""
    CREDIT = "CREDIT"
    DEBIT = "DEBIT"


class ReconciliationStatus(str, Enum):
    """Reconciliation status."""
    PENDING = "PENDING"
    MATCHED = "MATCHED"
    UNMATCHED = "UNMATCHED"
    PARTIALLY_MATCHED = "PARTIALLY_MATCHED"


class BankAccount(Base):
    """
    Bank account master for managing multiple bank accounts.

    Links to ledger account for automatic journal entries.
    """
    __tablename__ = "bank_accounts"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)

    # Account Details
    account_name: Mapped[str] = mapped_column(String(200), nullable=False)
    account_number: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    bank_name: Mapped[str] = mapped_column(String(200), nullable=False)
    branch_name: Mapped[Optional[str]] = mapped_column(String(200))
    ifsc_code: Mapped[Optional[str]] = mapped_column(String(20))
    swift_code: Mapped[Optional[str]] = mapped_column(String(20))

    # Account Type
    account_type: Mapped[str] = mapped_column(String(50), default="CURRENT")

    # Balances
    opening_balance: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    current_balance: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)

    # Linked Ledger Account (for auto journal entries)
    ledger_account_id: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True), ForeignKey("chart_of_accounts.id"))

    # Credit Limits (for CC/OD accounts)
    credit_limit: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))
    available_limit: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))

    # Last Reconciliation
    last_reconciled_date: Mapped[Optional[date]] = mapped_column(Date)
    last_reconciled_balance: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Audit
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    created_by: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))

    # Relationships
    transactions = relationship("BankTransaction", back_populates="bank_account", lazy="dynamic")

    def __repr__(self):
        return f"<BankAccount {self.bank_name} - {self.account_number}>"


class BankTransaction(Base):
    """
    Individual bank transaction imported from statements.

    Used for bank reconciliation with journal entries.
    """
    __tablename__ = "bank_transactions"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)

    # Parent Account
    bank_account_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("bank_accounts.id"), nullable=False)

    # Transaction Details
    transaction_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    value_date: Mapped[Optional[date]] = mapped_column(Date)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    reference_number: Mapped[Optional[str]] = mapped_column(String(100))
    cheque_number: Mapped[Optional[str]] = mapped_column(String(20))

    # Transaction Type
    transaction_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="CREDIT, DEBIT"
    )

    # Amounts
    amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    debit_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), default=0)
    credit_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), default=0)
    running_balance: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2))

    # Reconciliation
    is_reconciled: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    reconciled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    matched_journal_entry_id: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True), ForeignKey("journal_entries.id"))
    reconciliation_status: Mapped[Optional[str]] = mapped_column(String(50), default="PENDING")

    # Import Tracking
    source: Mapped[str] = mapped_column(String(50), default="IMPORT")  # IMPORT, MANUAL, API
    import_reference: Mapped[Optional[str]] = mapped_column(String(255))  # Original filename
    import_batch_id: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True))

    # Categorization (auto-detected or manual)
    category: Mapped[Optional[str]] = mapped_column(String(100))
    party_name: Mapped[Optional[str]] = mapped_column(String(200))
    party_id: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True))

    # Audit
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    created_by: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))

    # Relationships
    bank_account = relationship("BankAccount", back_populates="transactions")

    def __repr__(self):
        return f"<BankTransaction {self.transaction_date} {self.amount}>"


class BankReconciliation(Base):
    """
    Bank reconciliation session/batch tracking.

    Stores reconciliation summary and status for audit purposes.
    """
    __tablename__ = "bank_reconciliations"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)

    # Account
    bank_account_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("bank_accounts.id"), nullable=False)

    # Period
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)

    # Balances
    statement_opening_balance: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    statement_closing_balance: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    book_balance: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)

    # Reconciliation Items
    total_credits: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    total_debits: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    uncleared_deposits: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    uncleared_withdrawals: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)
    difference: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0)

    # Statistics
    total_transactions: Mapped[int] = mapped_column(Integer, default=0)
    matched_transactions: Mapped[int] = mapped_column(Integer, default=0)
    unmatched_transactions: Mapped[int] = mapped_column(Integer, default=0)

    # Status
    status: Mapped[str] = mapped_column(String(50), default="IN_PROGRESS")  # IN_PROGRESS, COMPLETED, APPROVED
    is_balanced: Mapped[bool] = mapped_column(Boolean, default=False)
    approved_by: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))
    approved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # Notes
    notes: Mapped[Optional[str]] = mapped_column(Text)

    # Audit
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    created_by: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"))

    def __repr__(self):
        return f"<BankReconciliation {self.start_date} to {self.end_date}>"
