"""
Product Q&A API Endpoints

Endpoints for product questions and answers on the D2C storefront.
- Get questions for a product (public)
- Ask a question (authenticated customer)
- Answer a question (authenticated customer or admin)
- Vote helpful (authenticated customer)
"""

import uuid
from typing import Optional
from uuid import UUID
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.customer import Customer
from app.api.v1.endpoints.d2c_auth import get_current_customer
from app.models.product import Product
from app.models.product_review import (

    ProductQuestion,
    ProductAnswer,
    QuestionHelpful,
    AnswerHelpful,
)
from app.core.module_decorators import require_module


router = APIRouter(prefix="/questions", tags=["Product Q&A"])


# ============================================================================
# Pydantic Schemas
# ============================================================================

class AnswerResponse(BaseModel):
    """Response schema for an answer"""
    id: str
    answer_text: str
    answered_by: str
    is_seller_answer: bool
    is_verified_buyer: bool = False
    helpful_count: int = 0
    created_at: datetime

    class Config:
        from_attributes = True


class QuestionResponse(BaseModel):
    """Response schema for a question"""
    id: str
    question_text: str
    asked_by: str
    answers: list[AnswerResponse] = []
    answer_count: int = 0
    helpful_count: int = 0
    created_at: datetime

    class Config:
        from_attributes = True


class QuestionListResponse(BaseModel):
    """Paginated list of questions"""
    items: list[QuestionResponse]
    total: int
    page: int
    size: int


class CreateQuestionRequest(BaseModel):
    """Request to create a question"""
    product_id: str = Field(..., description="Product ID")
    question_text: str = Field(..., min_length=10, max_length=500, description="Question text")


class CreateAnswerRequest(BaseModel):
    """Request to create an answer"""
    answer_text: str = Field(..., min_length=10, max_length=2000, description="Answer text")


# ============================================================================
# Helper Functions
# ============================================================================

def anonymize_name(name: str) -> str:
    """Anonymize customer name (e.g., 'John Doe' -> 'John D.')"""
    if not name:
        return "Customer"
    parts = name.strip().split()
    if len(parts) == 1:
        return parts[0]
    return f"{parts[0]} {parts[-1][0]}."


def question_to_response(question: ProductQuestion) -> QuestionResponse:
    """Convert ProductQuestion model to response schema"""
    answers = []
    for a in (question.answers or []):
        if a.is_approved:
            answers.append(AnswerResponse(
                id=str(a.id),
                answer_text=a.answer_text,
                answered_by=a.answered_by,
                is_seller_answer=a.is_seller_answer,
                is_verified_buyer=a.is_verified_buyer,
                helpful_count=a.helpful_count,
                created_at=a.created_at,
            ))

    return QuestionResponse(
        id=str(question.id),
        question_text=question.question_text,
        asked_by=question.asked_by,
        answers=answers,
        answer_count=len(answers),
        helpful_count=question.helpful_count,
        created_at=question.created_at,
    )


# ============================================================================
# Public Endpoints
# ============================================================================

@router.get("/product/{product_id}", response_model=QuestionListResponse)
@require_module("d2c_storefront")
async def get_questions_for_product(
    product_id: str,
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """
    Get questions for a product.

    Public endpoint - no authentication required.
    Only returns approved questions with approved answers.
    """
    try:
        product_uuid = UUID(product_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid product ID format")

    # Check product exists
    product_result = await db.execute(
        select(Product.id).where(Product.id == product_uuid)
    )
    if not product_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Product not found")

    # Count total approved questions
    count_query = select(func.count(ProductQuestion.id)).where(
        ProductQuestion.product_id == product_uuid,
        ProductQuestion.is_approved == True
    )
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Fetch questions with answers
    query = (
        select(ProductQuestion)
        .options(selectinload(ProductQuestion.answers))
        .where(
            ProductQuestion.product_id == product_uuid,
            ProductQuestion.is_approved == True
        )
        .order_by(ProductQuestion.helpful_count.desc(), ProductQuestion.created_at.desc())
        .offset((page - 1) * size)
        .limit(size)
    )

    result = await db.execute(query)
    questions = result.scalars().all()

    return QuestionListResponse(
        items=[question_to_response(q) for q in questions],
        total=total,
        page=page,
        size=size,
    )


# ============================================================================
# Authenticated Customer Endpoints
# ============================================================================

@router.post("", response_model=QuestionResponse, status_code=status.HTTP_201_CREATED)
@require_module("d2c_storefront")
async def create_question(
    request: CreateQuestionRequest,
    db: AsyncSession = Depends(get_db),
    current_customer: Optional[Customer] = Depends(get_current_customer),
):
    """
    Ask a question about a product.

    Requires customer authentication.
    """
    if not current_customer:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required to ask a question"
        )

    try:
        product_uuid = UUID(request.product_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid product ID format")

    # Check product exists and is active
    product_result = await db.execute(
        select(Product).where(Product.id == product_uuid, Product.is_active == True)
    )
    product = product_result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Create question
    question = ProductQuestion(
        id=uuid.uuid4(),
        product_id=product_uuid,
        customer_id=current_customer.id,
        question_text=request.question_text,
        asked_by=anonymize_name(current_customer.full_name or current_customer.email or "Customer"),
        is_approved=True,  # Auto-approve for now, can add moderation later
    )

    db.add(question)
    await db.commit()
    await db.refresh(question)

    # Load answers relationship
    await db.refresh(question, ["answers"])

    return question_to_response(question)


@router.post("/{question_id}/answers", response_model=AnswerResponse, status_code=status.HTTP_201_CREATED)
@require_module("d2c_storefront")
async def create_answer(
    question_id: str,
    request: CreateAnswerRequest,
    db: AsyncSession = Depends(get_db),
    current_customer: Optional[Customer] = Depends(get_current_customer),
):
    """
    Answer a question as a customer.

    Requires customer authentication.
    For seller/admin answers, use the ERP admin panel.
    """
    if not current_customer:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required to answer a question"
        )

    # Customer answer
    customer_id = current_customer.id
    answered_by = anonymize_name(current_customer.full_name or "Verified Buyer")
    is_seller_answer = False

    try:
        question_uuid = UUID(question_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid question ID format")

    # Check question exists
    question_result = await db.execute(
        select(ProductQuestion).where(ProductQuestion.id == question_uuid)
    )
    question = question_result.scalar_one_or_none()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    # Check if customer is a verified buyer (purchased this product)
    from app.models.order import Order, OrderItem

    buyer_check = await db.execute(
        select(Order.id)
        .join(OrderItem)
        .where(
            Order.customer_id == customer_id,
            OrderItem.product_id == question.product_id,
            Order.status.in_(["DELIVERED", "COMPLETED"])
        )
        .limit(1)
    )
    is_verified_buyer = buyer_check.scalar_one_or_none() is not None

    # Create answer
    answer = ProductAnswer(
        id=uuid.uuid4(),
        question_id=question_uuid,
        customer_id=customer_id,
        answer_text=request.answer_text,
        answered_by=answered_by,
        is_seller_answer=is_seller_answer,
        is_verified_buyer=is_verified_buyer,
        is_approved=True,  # Auto-approve for now
    )

    db.add(answer)
    await db.commit()
    await db.refresh(answer)

    return AnswerResponse(
        id=str(answer.id),
        answer_text=answer.answer_text,
        answered_by=answer.answered_by,
        is_seller_answer=answer.is_seller_answer,
        is_verified_buyer=answer.is_verified_buyer,
        helpful_count=answer.helpful_count,
        created_at=answer.created_at,
    )


@router.post("/{question_id}/helpful", status_code=status.HTTP_200_OK)
@require_module("d2c_storefront")
async def vote_question_helpful(
    question_id: str,
    db: AsyncSession = Depends(get_db),
    current_customer: Optional[Customer] = Depends(get_current_customer),
):
    """
    Mark a question as helpful.

    Requires customer authentication. Each customer can vote once per question.
    """
    if not current_customer:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required to vote"
        )

    try:
        question_uuid = UUID(question_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid question ID format")

    # Check question exists
    question_result = await db.execute(
        select(ProductQuestion).where(ProductQuestion.id == question_uuid)
    )
    question = question_result.scalar_one_or_none()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")

    # Check if already voted
    existing_vote = await db.execute(
        select(QuestionHelpful).where(
            QuestionHelpful.question_id == question_uuid,
            QuestionHelpful.customer_id == current_customer.id
        )
    )
    if existing_vote.scalar_one_or_none():
        return {"message": "Already voted", "helpful_count": question.helpful_count}

    # Create vote and increment count
    vote = QuestionHelpful(
        id=uuid.uuid4(),
        question_id=question_uuid,
        customer_id=current_customer.id,
    )
    db.add(vote)

    question.helpful_count += 1
    await db.commit()

    return {"message": "Vote recorded", "helpful_count": question.helpful_count}


@router.post("/answers/{answer_id}/helpful", status_code=status.HTTP_200_OK)
@require_module("d2c_storefront")
async def vote_answer_helpful(
    answer_id: str,
    db: AsyncSession = Depends(get_db),
    current_customer: Optional[Customer] = Depends(get_current_customer),
):
    """
    Mark an answer as helpful.

    Requires customer authentication. Each customer can vote once per answer.
    """
    if not current_customer:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required to vote"
        )

    try:
        answer_uuid = UUID(answer_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid answer ID format")

    # Check answer exists
    answer_result = await db.execute(
        select(ProductAnswer).where(ProductAnswer.id == answer_uuid)
    )
    answer = answer_result.scalar_one_or_none()
    if not answer:
        raise HTTPException(status_code=404, detail="Answer not found")

    # Check if already voted
    existing_vote = await db.execute(
        select(AnswerHelpful).where(
            AnswerHelpful.answer_id == answer_uuid,
            AnswerHelpful.customer_id == current_customer.id
        )
    )
    if existing_vote.scalar_one_or_none():
        return {"message": "Already voted", "helpful_count": answer.helpful_count}

    # Create vote and increment count
    vote = AnswerHelpful(
        id=uuid.uuid4(),
        answer_id=answer_uuid,
        customer_id=current_customer.id,
    )
    db.add(vote)

    answer.helpful_count += 1
    await db.commit()

    return {"message": "Vote recorded", "helpful_count": answer.helpful_count}
