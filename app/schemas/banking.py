"""Banking module schemas for API requests/responses."""
from pydantic import BaseModel, Field

from app.schemas.base import BaseResponseSchema
from typing import Optional, List
from uuid import UUID
from datetime import date, datetime
from decimal import Decimal


class BankAccountCreate(BaseModel):
    """Create bank account request."""
    account_name: str = Field(..., description="Account display name")
    account_number: str = Field(..., description="Bank account number")
    bank_name: str = Field(..., description="Bank name")
    branch_name: Optional[str] = Field(None, description="Branch name")
    ifsc_code: Optional[str] = Field(None, description="IFSC code")
    swift_code: Optional[str] = Field(None, description="SWIFT code for international transfers")
    account_type: str = Field("CURRENT", description="Account type: CURRENT, SAVINGS, CASH_CREDIT, OVERDRAFT")
    opening_balance: Decimal = Field(Decimal("0"), description="Opening balance")
    ledger_account_id: Optional[UUID] = Field(None, description="Linked ledger account ID")
    credit_limit: Optional[Decimal] = Field(None, description="Credit limit for OD/CC accounts")


class BankAccountResponse(BaseResponseSchema):
    """Bank account response."""
    id: UUID
    account_name: str
    account_number: str
    bank_name: str
    branch_name: Optional[str] = None
    ifsc_code: Optional[str] = None
    swift_code: Optional[str] = None
    account_type: str
    opening_balance: Decimal = Decimal("0")
    current_balance: Decimal
    ledger_account_id: Optional[UUID] = None
    credit_limit: Optional[Decimal] = None
    available_limit: Optional[Decimal] = None
    last_reconciled_date: Optional[date] = None
    last_reconciled_balance: Optional[Decimal] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    created_by: Optional[UUID] = None

class BankTransactionResponse(BaseResponseSchema):
    """Bank transaction response."""
    id: UUID
    transaction_date: date
    description: str
    reference_number: Optional[str] = None
    transaction_type: str
    amount: Decimal
    debit_amount: Decimal
    credit_amount: Decimal
    running_balance: Optional[Decimal] = None
    is_reconciled: bool

class ImportResult(BaseModel):
    """Import result response."""
    success: bool = Field(..., description="Whether import was successful")
    bank_format: str = Field(..., description="Detected bank format")
    statistics: dict = Field(..., description="Import statistics")
    transactions: List[dict] = Field(..., description="Imported transactions")
    errors: Optional[List[dict]] = Field(None, description="Any errors encountered")


class ReconciliationMatch(BaseModel):
    """Match bank transaction with journal entry."""
    bank_transaction_id: UUID = Field(..., description="Bank transaction ID")
    journal_entry_id: UUID = Field(..., description="Journal entry ID to match with")
