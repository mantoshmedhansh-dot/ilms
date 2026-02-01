"""Pydantic schemas for ProductCost (COGS auto-calculation)."""
from pydantic import BaseModel, Field

from app.schemas.base import BaseResponseSchema
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
import uuid

from app.models.product_cost import ValuationMethod


# ==================== COST HISTORY SCHEMAS ====================

class CostHistoryEntry(BaseModel):
    """Single cost history entry from GRN receipt."""
    date: datetime
    quantity: int = Field(..., description="Quantity received in GRN")
    unit_cost: Decimal = Field(..., description="Unit price from GRN")
    grn_id: Optional[uuid.UUID] = None
    grn_number: Optional[str] = None
    running_average: Decimal = Field(..., description="Average cost after this GRN")


class CostHistoryResponse(BaseResponseSchema):
    """Response schema for cost history."""
    product_id: uuid.UUID
    product_name: str
    sku: str
    entries: List[CostHistoryEntry] = []
    total_entries: int = 0
# ==================== PRODUCT COST SCHEMAS ====================

class ProductCostBase(BaseModel):
    """Base schema for ProductCost."""
    valuation_method: str = Field(
        default="WEIGHTED_AVG",
        description="WEIGHTED_AVG, FIFO, SPECIFIC_ID"
    )
    standard_cost: Optional[Decimal] = Field(
        None,
        ge=0,
        description="Budgeted/standard cost for variance analysis"
    )


class ProductCostCreate(ProductCostBase):
    """Schema for creating a ProductCost record."""
    product_id: uuid.UUID
    variant_id: Optional[uuid.UUID] = None
    warehouse_id: Optional[uuid.UUID] = None


class ProductCostUpdate(BaseModel):
    """Schema for updating a ProductCost record."""
    valuation_method: Optional[str] = None
    standard_cost: Optional[Decimal] = Field(None, ge=0)


class ProductCostResponse(BaseResponseSchema):
    """Response schema for ProductCost."""
    id: uuid.UUID
    product_id: uuid.UUID
    variant_id: Optional[uuid.UUID] = None
    warehouse_id: Optional[uuid.UUID] = None

    # Valuation
    valuation_method: str

    # Cost Fields (auto-calculated)
    average_cost: Decimal
    last_purchase_cost: Optional[Decimal] = None
    standard_cost: Optional[Decimal] = None

    # Inventory Position
    quantity_on_hand: int
    total_value: Decimal

    # Tracking
    last_grn_id: Optional[uuid.UUID] = None
    last_calculated_at: Optional[datetime] = None

    # Variance Analysis
    cost_variance: Optional[Decimal] = None
    cost_variance_percentage: Optional[float] = None

    # Timestamps
    created_at: datetime
    updated_at: datetime

class ProductCostDetailResponse(ProductCostResponse):
    """Detailed response with cost history."""
    cost_history: List[CostHistoryEntry] = []
    product_name: Optional[str] = None
    sku: Optional[str] = None
    warehouse_name: Optional[str] = None


class ProductCostBriefResponse(BaseResponseSchema):
    """Brief cost response for product lists."""
    product_id: uuid.UUID
    average_cost: Decimal
    last_purchase_cost: Optional[Decimal] = None
    quantity_on_hand: int
    total_value: Decimal
    last_calculated_at: Optional[datetime] = None
# ==================== GRN COST UPDATE SCHEMAS ====================

class GRNCostUpdateRequest(BaseModel):
    """Request to update cost from a GRN acceptance."""
    grn_id: uuid.UUID
    warehouse_id: Optional[uuid.UUID] = None


class GRNCostUpdateResponse(BaseModel):
    """Response after cost update from GRN."""
    success: bool
    message: str
    updated_products: List[dict] = []
    # Format: [{"product_id": uuid, "product_name": str, "old_avg": Decimal, "new_avg": Decimal, "qty_added": int}]


# ==================== WEIGHTED AVERAGE CALCULATION SCHEMAS ====================

class WeightedAverageCostRequest(BaseModel):
    """Request to calculate weighted average cost."""
    product_id: uuid.UUID
    variant_id: Optional[uuid.UUID] = None
    warehouse_id: Optional[uuid.UUID] = None
    new_quantity: int = Field(..., ge=1, description="Quantity being added")
    new_unit_cost: Decimal = Field(..., ge=0, description="Cost per unit")


class WeightedAverageCostResponse(BaseModel):
    """Response with calculated weighted average cost."""
    product_id: uuid.UUID
    old_quantity: int
    old_average_cost: Decimal
    old_total_value: Decimal
    new_quantity: int
    new_unit_cost: Decimal
    new_purchase_value: Decimal
    resulting_quantity: int
    resulting_average_cost: Decimal
    resulting_total_value: Decimal


# ==================== PRODUCT COST SUMMARY SCHEMAS ====================

class ProductCostSummary(BaseModel):
    """Summary of product costs for reporting."""
    total_products: int = 0
    total_inventory_value: Decimal = Decimal("0")
    average_stock_value_per_product: Decimal = Decimal("0")
    products_with_cost: int = 0
    products_without_cost: int = 0

    # By valuation method
    weighted_avg_count: int = 0
    fifo_count: int = 0
    specific_id_count: int = 0


class ProductCostListResponse(BaseModel):
    """Paginated list of product costs."""
    items: List[ProductCostResponse]
    total: int
    page: int
    size: int
    pages: int
