"""Pydantic schemas for Accounting module."""
from datetime import datetime, date
from typing import Optional, List
from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict, field_validator, field_serializer

from app.schemas.base import BaseResponseSchema

from app.models.accounting import (
    AccountType, AccountSubType,
    FinancialPeriodStatus as PeriodStatus,
    JournalEntryStatus as JournalStatus
)


# ==================== ChartOfAccount Schemas ====================

class ChartOfAccountBase(BaseModel):
    """Base schema for ChartOfAccount."""
    account_code: str = Field(..., min_length=1, max_length=20, alias="code")
    account_name: str = Field(..., min_length=1, max_length=200, alias="name")
    account_type: AccountType = Field(..., alias="type")
    account_sub_type: Optional[AccountSubType] = Field(None, alias="subType")
    description: Optional[str] = None
    parent_id: Optional[UUID] = None
    is_group: bool = Field(False, alias="isGroup")
    is_system: bool = False
    is_active: bool = True
    allow_direct_posting: bool = True
    bank_name: Optional[str] = None
    bank_account_number: Optional[str] = None
    bank_ifsc: Optional[str] = None
    gst_type: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True)


class ChartOfAccountCreate(ChartOfAccountBase):
    """Schema for creating ChartOfAccount."""
    # Allow frontend to send either 'name' or 'account_name', 'type' or 'account_type'
    pass


class ChartOfAccountUpdate(BaseModel):
    """Schema for updating ChartOfAccount."""
    account_name: Optional[str] = None
    description: Optional[str] = None
    parent_id: Optional[UUID] = None
    is_active: Optional[bool] = None
    allow_manual_entries: Optional[bool] = None
    bank_name: Optional[str] = None
    bank_account_number: Optional[str] = None
    bank_ifsc: Optional[str] = None


class ChartOfAccountResponse(BaseResponseSchema):
    """Response schema for ChartOfAccount."""
    id: UUID
    account_code: str
    account_name: str
    account_type: AccountType
    account_sub_type: Optional[AccountSubType] = None
    description: Optional[str] = None
    parent_id: Optional[UUID] = None
    level: int = 1
    is_group: bool = False
    is_system: bool = False
    is_active: bool = True
    allow_direct_posting: bool = True
    opening_balance: Decimal = Decimal("0")
    current_balance: Decimal = Decimal("0")
    bank_name: Optional[str] = None
    bank_account_number: Optional[str] = None
    bank_ifsc: Optional[str] = None
    gst_type: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ChartOfAccountTreeResponse(ChartOfAccountResponse):
    """Response with children for tree view."""
    children: List["ChartOfAccountTreeResponse"] = []


# Alias for tree view
ChartOfAccountTree = ChartOfAccountTreeResponse


class AccountListResponse(BaseModel):
    """Paginated account list response."""
    items: List[ChartOfAccountResponse]
    total: int
    skip: int = 0
    limit: int = 100


class AccountBalanceResponse(BaseModel):
    """Account balance response."""
    account_id: UUID
    account_code: str
    account_name: str
    account_type: AccountType
    opening_balance: Decimal
    debit_total: Decimal
    credit_total: Decimal
    closing_balance: Decimal


# ==================== FinancialPeriod Schemas ====================

class FinancialPeriodBase(BaseModel):
    """Base schema for FinancialPeriod."""
    model_config = ConfigDict(populate_by_name=True)

    period_name: str = Field(..., min_length=1, max_length=50, alias="name")
    period_code: Optional[str] = Field(None, max_length=20, alias="code")
    period_type: str = Field("YEAR", max_length=20, description="YEAR, QUARTER, MONTH")
    start_date: date = Field(...)
    end_date: date = Field(...)
    financial_year: Optional[str] = Field(None, max_length=10)
    is_year_end: bool = False
    is_adjustment_period: bool = False

    # NOTE: Validator moved to FinancialPeriodCreate per coding standards
    # (Rule 2: Never put validators on Base schemas - they affect GET responses)


class FinancialPeriodCreate(FinancialPeriodBase):
    """Schema for creating FinancialPeriod."""

    @field_validator("end_date")
    @classmethod
    def validate_end_date(cls, v, info):
        if "start_date" in info.data and v <= info.data["start_date"]:
            raise ValueError("end_date must be after start_date")
        return v


class FinancialPeriodUpdate(BaseModel):
    """Schema for updating FinancialPeriod."""
    status: Optional[PeriodStatus] = None


class FinancialPeriodResponse(BaseResponseSchema):
    """Response schema for FinancialPeriod."""
    id: UUID
    period_name: str
    period_code: Optional[str] = None
    period_type: str = "YEAR"
    start_date: date
    end_date: date
    financial_year: Optional[str] = None
    is_year_end: bool = False
    is_adjustment_period: bool = False
    is_current: bool = False
    status: str
    closed_by: Optional[UUID] = None
    closed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class FinancialPeriodListResponse(BaseModel):
    """Response for listing periods."""
    items: List[FinancialPeriodResponse]
    total: int
    skip: int = 0
    limit: int = 20


# Alias for backward compatibility
PeriodListResponse = FinancialPeriodListResponse


# ==================== CostCenter Schemas ====================

class CostCenterBase(BaseModel):
    """Base schema for CostCenter."""
    model_config = ConfigDict(populate_by_name=True)

    code: str = Field(..., min_length=2, max_length=20)
    name: str = Field(..., min_length=2, max_length=200)
    cost_center_type: str = Field(..., description="DEPARTMENT, LOCATION, PROJECT, etc.")
    description: Optional[str] = None
    parent_id: Optional[UUID] = None
    department: Optional[str] = None
    manager_id: Optional[UUID] = None
    annual_budget: Optional[Decimal] = Field(None, ge=0)
    is_active: bool = True


class CostCenterCreate(CostCenterBase):
    """Schema for creating CostCenter."""
    pass


class CostCenterUpdate(BaseModel):
    """Schema for updating CostCenter."""
    name: Optional[str] = None
    description: Optional[str] = None
    parent_id: Optional[UUID] = None
    department: Optional[str] = None
    manager_id: Optional[UUID] = None
    annual_budget: Optional[Decimal] = None
    is_active: Optional[bool] = None


class CostCenterResponse(BaseResponseSchema):
    """Response schema for CostCenter."""
    id: UUID
    current_spend: Decimal = Decimal("0")
    created_at: datetime
    updated_at: datetime


# ==================== JournalEntry Schemas ====================

class JournalEntryLineBase(BaseModel):
    """Base schema for JournalEntryLine."""
    model_config = ConfigDict(populate_by_name=True)

    account_id: UUID
    # IMPORTANT: No aliases here - frontend expects these exact field names
    # Per CLAUDE.md Rule 3: Use exact same field names across backend/schema/frontend
    description: Optional[str] = None
    debit_amount: Decimal = Field(Decimal("0"), ge=0)
    credit_amount: Decimal = Field(Decimal("0"), ge=0)
    cost_center_id: Optional[UUID] = None


class JournalEntryLineCreate(JournalEntryLineBase):
    """Schema for creating JournalEntryLine."""
    pass


class JournalEntryLineResponse(BaseResponseSchema):
    """Response schema for JournalEntryLine."""
    id: UUID
    line_number: int
    account_id: UUID
    account_code: Optional[str] = None
    account_name: Optional[str] = None
    description: Optional[str] = None
    debit_amount: Decimal = Decimal("0")
    credit_amount: Decimal = Decimal("0")
    cost_center_id: Optional[UUID] = None

    # Serialize Decimal as float for JSON (frontend expects numbers, not strings)
    @field_serializer('debit_amount', 'credit_amount')
    def serialize_decimal(self, value: Decimal) -> float:
        return float(value) if value is not None else 0.0


class JournalEntryBase(BaseModel):
    """Base schema for JournalEntry."""
    entry_type: str = Field(..., description="MANUAL, SALES, PURCHASE, RECEIPT, PAYMENT, ADJUSTMENT, CLOSING")
    entry_date: date
    narration: str = Field(..., min_length=2, max_length=500)
    source_type: Optional[str] = None
    source_id: Optional[UUID] = None
    source_number: Optional[str] = None


class JournalEntryCreate(JournalEntryBase):
    """Schema for creating JournalEntry."""
    # period_id is optional - backend auto-determines from entry_date
    period_id: Optional[UUID] = None
    lines: List[JournalEntryLineCreate] = Field(..., min_length=2)

    @field_validator("lines")
    @classmethod
    def validate_lines(cls, v):
        if len(v) < 2:
            raise ValueError("Journal entry must have at least 2 lines")

        total_debit = sum(line.debit_amount for line in v)
        total_credit = sum(line.credit_amount for line in v)

        if total_debit != total_credit:
            raise ValueError(
                f"Journal entry must balance. Debit: {total_debit}, Credit: {total_credit}"
            )
        return v


class JournalEntryUpdate(BaseModel):
    """Schema for updating JournalEntry (only draft entries)."""
    entry_date: Optional[date] = None
    narration: Optional[str] = Field(None, min_length=2, max_length=500)
    source_number: Optional[str] = None
    lines: Optional[List[JournalEntryLineCreate]] = None

    @field_validator("lines")
    @classmethod
    def validate_lines(cls, v):
        if v is None:
            return v
        if len(v) < 2:
            raise ValueError("Journal entry must have at least 2 lines")

        total_debit = sum(line.debit_amount for line in v)
        total_credit = sum(line.credit_amount for line in v)

        if total_debit != total_credit:
            raise ValueError(
                f"Journal entry must balance. Debit: {total_debit}, Credit: {total_credit}"
            )
        return v


class JournalEntryResponse(BaseResponseSchema):
    """Response schema for JournalEntry."""
    id: UUID
    entry_number: str
    period_id: UUID
    status: str
    total_debit: Decimal
    total_credit: Decimal

    # Entry details - REQUIRED for list display
    entry_type: Optional[str] = None
    entry_date: Optional[date] = None
    narration: Optional[str] = None
    source_type: Optional[str] = None
    source_id: Optional[UUID] = None
    source_number: Optional[str] = None

    # Reversal fields
    is_reversed: bool = False
    reversal_of_id: Optional[UUID] = None
    reversed_by_id: Optional[UUID] = None

    # Workflow audit fields
    created_by: Optional[UUID] = None
    submitted_by: Optional[UUID] = None
    submitted_at: Optional[datetime] = None
    approval_level: Optional[str] = None
    approved_by: Optional[UUID] = None
    approved_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    posted_by: Optional[UUID] = None
    posted_at: Optional[datetime] = None

    # Related data
    lines: List[JournalEntryLineResponse] = []

    # Timestamps
    created_at: datetime
    updated_at: datetime

    # Serialize Decimal as float for JSON (frontend expects numbers, not strings)
    @field_serializer('total_debit', 'total_credit')
    def serialize_decimal(self, value: Decimal) -> float:
        return float(value) if value is not None else 0.0


class JournalEntryListResponse(BaseModel):
    """Response for listing journal entries."""
    items: List[JournalEntryResponse]
    total: int
    skip: int = 0
    limit: int = 50


# Alias for backward compatibility
JournalListResponse = JournalEntryListResponse


class JournalPostRequest(BaseModel):
    """Request to post a journal entry."""
    entry_ids: List[UUID]


class JournalReverseRequest(BaseModel):
    """Request to reverse a journal entry."""
    entry_id: UUID
    reversal_date: date
    reason: str


# ==================== Maker-Checker Approval Schemas ====================

class ApprovalUserInfo(BaseModel):
    """User info for approval display."""
    id: UUID
    name: str
    email: str


class JournalSubmitRequest(BaseModel):
    """Request to submit journal entry for approval."""
    remarks: Optional[str] = Field(None, max_length=500, description="Optional remarks for approver")


class JournalApproveRequest(BaseModel):
    """Request to approve a journal entry."""
    remarks: Optional[str] = Field(None, max_length=500, description="Approval remarks")
    auto_post: bool = Field(True, description="Automatically post to GL after approval")


class JournalRejectRequest(BaseModel):
    """Request to reject a journal entry."""
    reason: str = Field(..., min_length=5, max_length=500, description="Reason for rejection")


class JournalApprovalResponse(BaseResponseSchema):
    """Response for approval operations."""
    id: UUID
    entry_number: str
    status: str
    total_debit: Decimal
    total_credit: Decimal
    narration: str

    # Maker info
    created_by: UUID
    created_at: datetime
    creator_name: Optional[str] = None

    # Submission info
    submitted_by: Optional[UUID] = None
    submitted_at: Optional[datetime] = None
    submitter_name: Optional[str] = None

    # Checker info
    approval_level: Optional[str] = None
    approved_by: Optional[UUID] = None
    approved_at: Optional[datetime] = None
    approver_name: Optional[str] = None
    rejection_reason: Optional[str] = None

    # Posting info
    posted_by: Optional[UUID] = None
    posted_at: Optional[datetime] = None
    poster_name: Optional[str] = None

    message: Optional[str] = None


class PendingApprovalResponse(BaseModel):
    """Response for pending approvals list."""
    items: List[JournalApprovalResponse]
    total: int
    level_1_count: int = 0  # Up to 50,000
    level_2_count: int = 0  # 50,001 to 5,00,000
    level_3_count: int = 0  # Above 5,00,000


class ApprovalHistoryItem(BaseModel):
    """Single approval history entry."""
    action: str  # CREATED, SUBMITTED, APPROVED, REJECTED, POSTED
    performed_by: UUID
    performed_by_name: Optional[str] = None
    performed_at: datetime
    remarks: Optional[str] = None


class ApprovalHistoryResponse(BaseModel):
    """Approval history for a journal entry."""
    entry_id: UUID
    entry_number: str
    history: List[ApprovalHistoryItem]


# ==================== GeneralLedger Schemas ====================

class GeneralLedgerResponse(BaseResponseSchema):
    """Response schema for GeneralLedger."""
    id: UUID
    account_id: UUID
    period_id: UUID
    journal_entry_id: UUID
    entry_date: date
    entry_number: str
    description: Optional[str] = None
    debit_amount: Decimal
    credit_amount: Decimal
    balance: Decimal
    reference_type: Optional[str] = None
    reference_number: Optional[str] = None
    created_at: datetime


class LedgerQueryRequest(BaseModel):
    """Query parameters for ledger."""
    account_id: UUID
    start_date: date
    end_date: date
    include_opening: bool = True


class LedgerReportResponse(BaseModel):
    """Ledger report response."""
    account_id: UUID
    account_code: str
    account_name: str
    period_start: date
    period_end: date
    opening_balance: Decimal
    entries: List[GeneralLedgerResponse]
    total_debit: Decimal
    total_credit: Decimal
    closing_balance: Decimal


class LedgerListResponse(BaseModel):
    """Paginated ledger list response."""
    account_id: UUID
    account_code: str
    account_name: str
    items: List[GeneralLedgerResponse]
    total: int
    skip: int = 0
    limit: int = 100
    total_debit: Decimal = Decimal("0")
    total_credit: Decimal = Decimal("0")
    closing_balance: Decimal = Decimal("0")


class LedgerSummary(BaseModel):
    """Ledger summary."""
    total_debit: Decimal
    total_credit: Decimal
    balance: Decimal


# ==================== TaxConfiguration Schemas ====================

class TaxConfigurationBase(BaseModel):
    """Base schema for TaxConfiguration."""
    hsn_code: str = Field(..., min_length=4, max_length=8)
    description: str = Field(..., max_length=500)
    gst_rate: Decimal = Field(..., ge=0, le=100)
    cgst_rate: Decimal = Field(..., ge=0, le=50)
    sgst_rate: Decimal = Field(..., ge=0, le=50)
    igst_rate: Decimal = Field(..., ge=0, le=100)
    cess_rate: Decimal = Field(Decimal("0"), ge=0)
    is_service: bool = False
    is_exempt: bool = False
    is_nil_rated: bool = False
    is_non_gst: bool = False
    reverse_charge: bool = False
    is_active: bool = True


class TaxConfigurationCreate(TaxConfigurationBase):
    """Schema for creating TaxConfiguration."""
    pass


class TaxConfigurationUpdate(BaseModel):
    """Schema for updating TaxConfiguration."""
    description: Optional[str] = None
    gst_rate: Optional[Decimal] = None
    cgst_rate: Optional[Decimal] = None
    sgst_rate: Optional[Decimal] = None
    igst_rate: Optional[Decimal] = None
    cess_rate: Optional[Decimal] = None
    is_active: Optional[bool] = None


class TaxConfigurationResponse(BaseResponseSchema):
    """Response schema for TaxConfiguration."""
    id: UUID
    created_at: datetime
    updated_at: datetime


class TaxCalculationRequest(BaseModel):
    """Request for tax calculation."""
    hsn_code: str
    taxable_value: Decimal
    is_interstate: bool = False
    place_of_supply_code: Optional[str] = None


class TaxCalculationResponse(BaseModel):
    """Response for tax calculation."""
    hsn_code: str
    taxable_value: Decimal
    is_interstate: bool
    cgst_rate: Decimal
    cgst_amount: Decimal
    sgst_rate: Decimal
    sgst_amount: Decimal
    igst_rate: Decimal
    igst_amount: Decimal
    cess_rate: Decimal
    cess_amount: Decimal
    total_tax: Decimal
    total_amount: Decimal


# ==================== Report Schemas ====================

class TrialBalanceRequest(BaseModel):
    """Request for trial balance."""
    as_of_date: date
    period_id: Optional[UUID] = None


class TrialBalanceLineItem(BaseModel):
    """Trial balance line item."""
    account_id: UUID
    account_code: str
    account_name: str
    account_type: AccountType
    debit_balance: Decimal
    credit_balance: Decimal


class TrialBalanceResponse(BaseModel):
    """Trial balance response."""
    as_of_date: date
    items: List[TrialBalanceLineItem]
    total_debit: Decimal
    total_credit: Decimal
    is_balanced: bool


# Alias for backward compatibility
TrialBalanceItem = TrialBalanceLineItem


class ProfitLossRequest(BaseModel):
    """Request for P&L statement."""
    start_date: date
    end_date: date
    cost_center_id: Optional[UUID] = None


class BalanceSheetRequest(BaseModel):
    """Request for balance sheet."""
    as_of_date: date


class ProfitLossResponse(BaseModel):
    """Profit & Loss statement response."""
    start_date: date
    end_date: date
    revenue: Decimal = Decimal("0")
    cost_of_goods_sold: Decimal = Decimal("0")
    gross_profit: Decimal = Decimal("0")
    operating_expenses: Decimal = Decimal("0")
    operating_income: Decimal = Decimal("0")
    other_income: Decimal = Decimal("0")
    other_expenses: Decimal = Decimal("0")
    net_income: Decimal = Decimal("0")


class BalanceSheetResponse(BaseModel):
    """Balance Sheet response."""
    as_of_date: date
    total_assets: Decimal = Decimal("0")
    total_liabilities: Decimal = Decimal("0")
    total_equity: Decimal = Decimal("0")
    assets: dict = {}
    liabilities: dict = {}
    equity: dict = {}
