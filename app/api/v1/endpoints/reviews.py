"""
Product Reviews API Endpoints

Public and authenticated endpoints for product reviews.
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, HTTPException, status, Depends, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.product import Product
from app.models.product_review import ProductReview, ReviewHelpful
from app.models.customer import Customer
from app.models.order import Order, OrderItem
from app.api.v1.endpoints.d2c_auth import get_current_customer, require_customer
from app.core.module_decorators import require_module

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/reviews", tags=["Product Reviews"])


# ==================== Schemas ====================

class ReviewCreate(BaseModel):
    """Request to create a review."""
    product_id: str
    rating: int = Field(..., ge=1, le=5, description="Rating from 1 to 5 stars")
    title: Optional[str] = Field(None, max_length=200)
    review_text: Optional[str] = Field(None, max_length=2000)

    @field_validator("rating")
    @classmethod
    def validate_rating(cls, v: int) -> int:
        if v < 1 or v > 5:
            raise ValueError("Rating must be between 1 and 5")
        return v


class ReviewResponse(BaseModel):
    """Review response."""
    id: str
    rating: int
    title: Optional[str]
    review_text: Optional[str]
    is_verified_purchase: bool
    helpful_count: int
    created_at: datetime
    customer_name: str
    admin_response: Optional[str] = None
    admin_response_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ReviewSummary(BaseModel):
    """Summary of reviews for a product."""
    average_rating: float
    total_reviews: int
    rating_distribution: dict  # {1: count, 2: count, etc.}
    verified_purchase_count: int


class ReviewListResponse(BaseModel):
    """Paginated list of reviews."""
    reviews: List[ReviewResponse]
    summary: ReviewSummary
    total: int
    page: int
    size: int


class HelpfulVoteRequest(BaseModel):
    """Request to vote on a review."""
    is_helpful: bool


# ==================== Public Endpoints ====================

@router.get("/product/{product_id}", response_model=ReviewListResponse)
@require_module("d2c_storefront")
async def get_product_reviews(
    product_id: uuid.UUID,
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=50),
    sort_by: str = Query("recent", enum=["recent", "helpful", "rating_high", "rating_low"]),
    rating_filter: Optional[int] = Query(None, ge=1, le=5),
    db: AsyncSession = Depends(get_db),
):
    """
    Get reviews for a product (public endpoint).
    """
    offset = (page - 1) * size

    # Build query
    query = select(ProductReview).where(
        ProductReview.product_id == product_id,
        ProductReview.is_approved == True,
    )

    # Apply rating filter
    if rating_filter:
        query = query.where(ProductReview.rating == rating_filter)

    # Apply sorting
    if sort_by == "helpful":
        query = query.order_by(ProductReview.helpful_count.desc())
    elif sort_by == "rating_high":
        query = query.order_by(ProductReview.rating.desc())
    elif sort_by == "rating_low":
        query = query.order_by(ProductReview.rating.asc())
    else:  # recent
        query = query.order_by(ProductReview.created_at.desc())

    # Get total count
    count_query = select(func.count(ProductReview.id)).where(
        ProductReview.product_id == product_id,
        ProductReview.is_approved == True,
    )
    if rating_filter:
        count_query = count_query.where(ProductReview.rating == rating_filter)

    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    # Get reviews with pagination
    result = await db.execute(
        query.options(selectinload(ProductReview.customer))
        .offset(offset)
        .limit(size)
    )
    reviews = result.scalars().all()

    # Get summary statistics
    summary = await _get_review_summary(db, product_id)

    return ReviewListResponse(
        reviews=[
            ReviewResponse(
                id=str(review.id),
                rating=review.rating,
                title=review.title,
                review_text=review.review_text,
                is_verified_purchase=review.is_verified_purchase,
                helpful_count=review.helpful_count,
                created_at=review.created_at,
                customer_name=_mask_customer_name(review.customer.first_name if review.customer else "Customer"),
                admin_response=review.admin_response,
                admin_response_at=review.admin_response_at,
            )
            for review in reviews
        ],
        summary=summary,
        total=total,
        page=page,
        size=size,
    )


@router.get("/product/{product_id}/summary", response_model=ReviewSummary)
@require_module("d2c_storefront")
async def get_review_summary(
    product_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Get review summary for a product (public endpoint).
    """
    return await _get_review_summary(db, product_id)


# ==================== Authenticated Endpoints ====================

@router.post("", response_model=ReviewResponse)
@require_module("d2c_storefront")
async def create_review(
    request: ReviewCreate,
    customer: Customer = Depends(require_customer),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new review (requires authentication).
    """
    product_id = uuid.UUID(request.product_id)

    # Check if product exists
    product_result = await db.execute(
        select(Product).where(Product.id == product_id)
    )
    product = product_result.scalar_one_or_none()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found",
        )

    # Check if customer already reviewed this product
    existing_review = await db.execute(
        select(ProductReview).where(
            ProductReview.product_id == product_id,
            ProductReview.customer_id == customer.id,
        )
    )
    if existing_review.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already reviewed this product",
        )

    # Check if verified purchase
    is_verified = await _check_verified_purchase(db, customer.id, product_id)

    # Find associated order (if any)
    order_id = None
    if is_verified:
        order_result = await db.execute(
            select(OrderItem.order_id)
            .join(Order, OrderItem.order_id == Order.id)
            .where(
                Order.customer_id == customer.id,
                OrderItem.product_id == product_id,
                Order.status == "DELIVERED",
            )
            .limit(1)
        )
        order_row = order_result.first()
        if order_row:
            order_id = order_row[0]

    # Create review
    review = ProductReview(
        product_id=product_id,
        customer_id=customer.id,
        order_id=order_id,
        rating=request.rating,
        title=request.title,
        review_text=request.review_text,
        is_verified_purchase=is_verified,
        is_approved=True,  # Auto-approve for now
    )

    db.add(review)
    await db.commit()
    await db.refresh(review)

    logger.info(f"Review created for product {product_id} by customer {customer.id}")

    return ReviewResponse(
        id=str(review.id),
        rating=review.rating,
        title=review.title,
        review_text=review.review_text,
        is_verified_purchase=review.is_verified_purchase,
        helpful_count=review.helpful_count,
        created_at=review.created_at,
        customer_name=_mask_customer_name(customer.first_name),
    )


@router.put("/{review_id}", response_model=ReviewResponse)
@require_module("d2c_storefront")
async def update_review(
    review_id: uuid.UUID,
    request: ReviewCreate,
    customer: Customer = Depends(require_customer),
    db: AsyncSession = Depends(get_db),
):
    """
    Update own review.
    """
    result = await db.execute(
        select(ProductReview).where(
            ProductReview.id == review_id,
            ProductReview.customer_id == customer.id,
        )
    )
    review = result.scalar_one_or_none()

    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found",
        )

    review.rating = request.rating
    review.title = request.title
    review.review_text = request.review_text
    review.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(review)

    return ReviewResponse(
        id=str(review.id),
        rating=review.rating,
        title=review.title,
        review_text=review.review_text,
        is_verified_purchase=review.is_verified_purchase,
        helpful_count=review.helpful_count,
        created_at=review.created_at,
        customer_name=_mask_customer_name(customer.first_name),
    )


@router.delete("/{review_id}")
@require_module("d2c_storefront")
async def delete_review(
    review_id: uuid.UUID,
    customer: Customer = Depends(require_customer),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete own review.
    """
    result = await db.execute(
        select(ProductReview).where(
            ProductReview.id == review_id,
            ProductReview.customer_id == customer.id,
        )
    )
    review = result.scalar_one_or_none()

    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found",
        )

    await db.delete(review)
    await db.commit()

    return {"message": "Review deleted"}


@router.post("/{review_id}/helpful")
@require_module("d2c_storefront")
async def vote_helpful(
    review_id: uuid.UUID,
    request: HelpfulVoteRequest,
    customer: Customer = Depends(require_customer),
    db: AsyncSession = Depends(get_db),
):
    """
    Mark a review as helpful or not helpful.
    """
    # Check review exists
    review_result = await db.execute(
        select(ProductReview).where(ProductReview.id == review_id)
    )
    review = review_result.scalar_one_or_none()

    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Review not found",
        )

    # Can't vote on own review
    if review.customer_id == customer.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot vote on your own review",
        )

    # Check for existing vote
    existing_vote = await db.execute(
        select(ReviewHelpful).where(
            ReviewHelpful.review_id == review_id,
            ReviewHelpful.customer_id == customer.id,
        )
    )
    vote = existing_vote.scalar_one_or_none()

    if vote:
        # Update existing vote
        old_helpful = vote.is_helpful
        vote.is_helpful = request.is_helpful

        # Update counts
        if old_helpful != request.is_helpful:
            if request.is_helpful:
                review.helpful_count += 1
                review.not_helpful_count -= 1
            else:
                review.helpful_count -= 1
                review.not_helpful_count += 1
    else:
        # Create new vote
        vote = ReviewHelpful(
            review_id=review_id,
            customer_id=customer.id,
            is_helpful=request.is_helpful,
        )
        db.add(vote)

        if request.is_helpful:
            review.helpful_count += 1
        else:
            review.not_helpful_count += 1

    await db.commit()

    return {"message": "Vote recorded", "helpful_count": review.helpful_count}


@router.get("/my-reviews", response_model=List[ReviewResponse])
@require_module("d2c_storefront")
async def get_my_reviews(
    customer: Customer = Depends(require_customer),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all reviews by the authenticated customer.
    """
    result = await db.execute(
        select(ProductReview)
        .where(ProductReview.customer_id == customer.id)
        .order_by(ProductReview.created_at.desc())
    )
    reviews = result.scalars().all()

    return [
        ReviewResponse(
            id=str(review.id),
            rating=review.rating,
            title=review.title,
            review_text=review.review_text,
            is_verified_purchase=review.is_verified_purchase,
            helpful_count=review.helpful_count,
            created_at=review.created_at,
            customer_name=customer.first_name,
            admin_response=review.admin_response,
            admin_response_at=review.admin_response_at,
        )
        for review in reviews
    ]


@router.get("/can-review/{product_id}")
@require_module("d2c_storefront")
async def can_review_product(
    product_id: uuid.UUID,
    customer: Optional[Customer] = Depends(get_current_customer),
    db: AsyncSession = Depends(get_db),
):
    """
    Check if current customer can review a product.
    """
    if not customer:
        return {
            "can_review": False,
            "reason": "Login required to write a review",
            "is_verified_purchase": False,
        }

    # Check if already reviewed
    existing_review = await db.execute(
        select(ProductReview).where(
            ProductReview.product_id == product_id,
            ProductReview.customer_id == customer.id,
        )
    )
    if existing_review.scalar_one_or_none():
        return {
            "can_review": False,
            "reason": "You have already reviewed this product",
            "is_verified_purchase": False,
        }

    # Check if verified purchase
    is_verified = await _check_verified_purchase(db, customer.id, product_id)

    return {
        "can_review": True,
        "reason": None,
        "is_verified_purchase": is_verified,
    }


# ==================== Helper Functions ====================

async def _get_review_summary(db: AsyncSession, product_id: uuid.UUID) -> ReviewSummary:
    """Get review summary statistics for a product."""
    # Get average and count
    stats_result = await db.execute(
        select(
            func.avg(ProductReview.rating),
            func.count(ProductReview.id),
            func.count(ProductReview.id).filter(ProductReview.is_verified_purchase == True),
        )
        .where(
            ProductReview.product_id == product_id,
            ProductReview.is_approved == True,
        )
    )
    stats = stats_result.first()
    avg_rating = float(stats[0]) if stats[0] else 0.0
    total_reviews = stats[1] or 0
    verified_count = stats[2] or 0

    # Get rating distribution
    dist_result = await db.execute(
        select(ProductReview.rating, func.count(ProductReview.id))
        .where(
            ProductReview.product_id == product_id,
            ProductReview.is_approved == True,
        )
        .group_by(ProductReview.rating)
    )
    distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    for row in dist_result:
        distribution[row[0]] = row[1]

    return ReviewSummary(
        average_rating=round(avg_rating, 1),
        total_reviews=total_reviews,
        rating_distribution=distribution,
        verified_purchase_count=verified_count,
    )


async def _check_verified_purchase(
    db: AsyncSession, customer_id: uuid.UUID, product_id: uuid.UUID
) -> bool:
    """Check if customer has purchased this product."""
    result = await db.execute(
        select(OrderItem.id)
        .join(Order, OrderItem.order_id == Order.id)
        .where(
            Order.customer_id == customer_id,
            OrderItem.product_id == product_id,
            Order.status == "DELIVERED",
        )
        .limit(1)
    )
    return result.first() is not None


def _mask_customer_name(name: str) -> str:
    """Mask customer name for privacy (e.g., 'John' -> 'J***')."""
    if not name or len(name) < 2:
        return "Customer"
    return name[0] + "*" * (len(name) - 1)
