"""
Product Review Model for D2C Storefront

Allows customers to rate and review products they've purchased.
"""

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from sqlalchemy import String, Boolean, DateTime, ForeignKey, Integer, Text, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.database import Base

if TYPE_CHECKING:
    from app.models.customer import Customer
    from app.models.product import Product


class ProductReview(Base):
    """
    Customer review for a product.
    Reviews can only be submitted by verified purchasers.
    """
    __tablename__ = "product_reviews"
    __table_args__ = (
        CheckConstraint('rating >= 1 AND rating <= 5', name='check_rating_range'),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Foreign Keys
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    order_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="SET NULL"),
        nullable=True,
        comment="Order in which this product was purchased"
    )

    # Review Content
    rating: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Rating from 1 to 5 stars"
    )
    title: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
        comment="Review title/headline"
    )
    review_text: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Full review text"
    )

    # Verification & Moderation
    is_verified_purchase: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="True if customer actually purchased this product"
    )
    is_approved: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Admin approval status"
    )
    is_featured: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Featured review (shown prominently)"
    )

    # Helpful votes
    helpful_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Number of users who found this helpful"
    )
    not_helpful_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False
    )

    # Images (JSON array of URLs)
    images: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        default=list,
        comment="Array of image URLs uploaded with review"
    )

    # Admin response
    admin_response: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Response from the seller/admin"
    )
    admin_response_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    product: Mapped["Product"] = relationship("Product", back_populates="reviews")
    customer: Mapped["Customer"] = relationship("Customer")

    def __repr__(self) -> str:
        return f"<ProductReview(product_id={self.product_id}, rating={self.rating})>"


class ReviewHelpful(Base):
    """
    Tracks which users found a review helpful.
    Prevents duplicate votes.
    """
    __tablename__ = "review_helpful"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    review_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("product_reviews.id", ondelete="CASCADE"),
        nullable=False
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False
    )
    is_helpful: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        comment="True = helpful, False = not helpful"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    __table_args__ = (
        # Each customer can only vote once per review
        {'sqlite_autoincrement': True},
    )


class ProductQuestion(Base):
    """
    Customer question about a product.
    Questions can be answered by sellers, verified buyers, or community members.
    """
    __tablename__ = "product_questions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Foreign Keys
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Question Content
    question_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="The question text"
    )

    # Display name (anonymized or full name)
    asked_by: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Display name of the person who asked"
    )

    # Moderation
    is_approved: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Admin approval status"
    )

    # Helpful votes
    helpful_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Number of users who found this helpful"
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    product: Mapped["Product"] = relationship("Product", back_populates="questions")
    customer: Mapped["Customer"] = relationship("Customer")
    answers: Mapped[list["ProductAnswer"]] = relationship(
        "ProductAnswer",
        back_populates="question",
        cascade="all, delete-orphan",
        order_by="ProductAnswer.helpful_count.desc()"
    )

    @property
    def answer_count(self) -> int:
        return len(self.answers) if self.answers else 0

    def __repr__(self) -> str:
        return f"<ProductQuestion(product_id={self.product_id}, question={self.question_text[:50]}...)>"


class ProductAnswer(Base):
    """
    Answer to a product question.
    Can be from seller (official response) or community members.
    """
    __tablename__ = "product_answers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    # Foreign Keys
    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("product_questions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    customer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="SET NULL"),
        nullable=True,
        comment="Customer who answered (null for seller answers)"
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="Admin/Staff user who answered (for seller answers)"
    )

    # Answer Content
    answer_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="The answer text"
    )

    # Display name
    answered_by: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Display name of the person who answered"
    )

    # Is this an official seller/brand response?
    is_seller_answer: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="True if this is an official seller/brand response"
    )

    # Is this from a verified buyer?
    is_verified_buyer: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="True if answerer has purchased this product"
    )

    # Moderation
    is_approved: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Admin approval status"
    )

    # Helpful votes
    helpful_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Number of users who found this helpful"
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    question: Mapped["ProductQuestion"] = relationship("ProductQuestion", back_populates="answers")
    customer: Mapped[Optional["Customer"]] = relationship("Customer")

    def __repr__(self) -> str:
        return f"<ProductAnswer(question_id={self.question_id}, is_seller={self.is_seller_answer})>"


class QuestionHelpful(Base):
    """
    Tracks which users found a question helpful.
    Prevents duplicate votes.
    """
    __tablename__ = "question_helpful"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("product_questions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )


class AnswerHelpful(Base):
    """
    Tracks which users found an answer helpful.
    Prevents duplicate votes.
    """
    __tablename__ = "answer_helpful"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    answer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("product_answers.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customers.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
