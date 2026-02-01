"""Auto Journal Entry generation schemas for API requests/responses."""
from pydantic import BaseModel, Field

from app.schemas.base import BaseResponseSchema
from typing import Optional, List
from uuid import UUID
from datetime import date


class GenerateFromInvoiceRequest(BaseModel):
    """Request to generate journal from invoice."""
    invoice_id: UUID = Field(..., description="Sales invoice ID")
    auto_post: bool = Field(False, description="Automatically post the journal entry")


class GenerateFromReceiptRequest(BaseModel):
    """Request to generate journal from payment receipt."""
    receipt_id: UUID = Field(..., description="Payment receipt ID")
    bank_account_code: Optional[str] = Field(None, description="Bank account ledger code")
    auto_post: bool = Field(False, description="Automatically post the journal entry")


class GenerateFromBankTxnRequest(BaseModel):
    """Request to generate journal from bank transaction."""
    bank_transaction_id: UUID = Field(..., description="Bank transaction ID")
    contra_account_code: str = Field(..., description="Contra account ledger code")
    auto_post: bool = Field(False, description="Automatically post the journal entry")


class BulkGenerateRequest(BaseModel):
    """Request for bulk journal generation."""
    invoice_ids: Optional[List[UUID]] = Field(None, description="List of invoice IDs")
    receipt_ids: Optional[List[UUID]] = Field(None, description="List of receipt IDs")
    auto_post: bool = Field(False, description="Automatically post all journal entries")


class JournalEntryResponse(BaseModel):
    """Response for journal entry."""
    id: UUID
    entry_number: str
    entry_date: date
    journal_type: str
    narration: str
    total_debit: float
    total_credit: float
    status: str
    reference_type: Optional[str] = None
    reference_id: Optional[UUID] = None


class GenerationResult(BaseModel):
    """Result of journal generation."""
    success: bool = Field(..., description="Whether generation was successful")
    journal_id: Optional[UUID] = Field(None, description="Generated journal entry ID")
    entry_number: Optional[str] = Field(None, description="Generated journal entry number")
    message: str = Field(..., description="Result message")
    error: Optional[str] = Field(None, description="Error message if failed")
