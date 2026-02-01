"""Database models for Notifications module."""
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4
from enum import Enum

from sqlalchemy import (
    Column, String, Text, DateTime, Boolean, ForeignKey,
    Index
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import relationship

from app.database import Base


class NotificationType(str, Enum):
    """Types of notifications."""
    # System
    SYSTEM = "SYSTEM"
    ALERT = "ALERT"
    ANNOUNCEMENT = "ANNOUNCEMENT"

    # Orders
    ORDER_CREATED = "ORDER_CREATED"
    ORDER_CONFIRMED = "ORDER_CONFIRMED"
    ORDER_SHIPPED = "ORDER_SHIPPED"
    ORDER_DELIVERED = "ORDER_DELIVERED"
    ORDER_CANCELLED = "ORDER_CANCELLED"

    # Inventory
    LOW_STOCK = "LOW_STOCK"
    OUT_OF_STOCK = "OUT_OF_STOCK"
    STOCK_RECEIVED = "STOCK_RECEIVED"

    # Approvals
    APPROVAL_PENDING = "APPROVAL_PENDING"
    APPROVAL_APPROVED = "APPROVAL_APPROVED"
    APPROVAL_REJECTED = "APPROVAL_REJECTED"

    # HR
    LEAVE_REQUEST = "LEAVE_REQUEST"
    LEAVE_APPROVED = "LEAVE_APPROVED"
    LEAVE_REJECTED = "LEAVE_REJECTED"
    PAYSLIP_GENERATED = "PAYSLIP_GENERATED"
    APPRAISAL_DUE = "APPRAISAL_DUE"

    # Finance
    PAYMENT_RECEIVED = "PAYMENT_RECEIVED"
    PAYMENT_DUE = "PAYMENT_DUE"
    INVOICE_GENERATED = "INVOICE_GENERATED"

    # Service
    SERVICE_ASSIGNED = "SERVICE_ASSIGNED"
    SERVICE_COMPLETED = "SERVICE_COMPLETED"
    WARRANTY_EXPIRING = "WARRANTY_EXPIRING"

    # Fixed Assets
    ASSET_MAINTENANCE_DUE = "ASSET_MAINTENANCE_DUE"
    ASSET_TRANSFER_PENDING = "ASSET_TRANSFER_PENDING"

    # General
    TASK_ASSIGNED = "TASK_ASSIGNED"
    REMINDER = "REMINDER"
    MENTION = "MENTION"


class NotificationPriority(str, Enum):
    """Priority levels for notifications."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    URGENT = "URGENT"


class NotificationChannel(str, Enum):
    """Delivery channels for notifications."""
    IN_APP = "IN_APP"
    EMAIL = "EMAIL"
    SMS = "SMS"
    PUSH = "PUSH"
    WEBHOOK = "WEBHOOK"


class Notification(Base):
    """
    Notification model - stores all system notifications.
    """
    __tablename__ = "notifications"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)

    # Recipient
    user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Notification content
    notification_type = Column(String(50), nullable=False, index=True, comment="SYSTEM, ALERT, ANNOUNCEMENT, ORDER_*, LOW_STOCK, APPROVAL_*, LEAVE_*, etc.")
    priority = Column(String(20), default="MEDIUM", nullable=False, comment="LOW, MEDIUM, HIGH, URGENT")

    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)

    # Optional action link
    action_url = Column(String(500))
    action_label = Column(String(100))

    # Reference to related entity
    entity_type = Column(String(50))  # e.g., "order", "leave_request", "asset"
    entity_id = Column(PGUUID(as_uuid=True))

    # Additional data as JSONB
    extra_data = Column(JSONB, default=dict)

    # Status
    is_read = Column(Boolean, default=False, nullable=False, index=True)
    read_at = Column(DateTime(timezone=True))

    # Delivery status
    channels = Column(JSONB, default=list)  # List of channels notification was sent to
    delivered_at = Column(JSONB, default=dict)  # {channel: timestamp}

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    expires_at = Column(DateTime(timezone=True))  # Optional expiration

    # Relationships
    user = relationship("User", back_populates="notifications")

    __table_args__ = (
        Index('ix_notifications_user_unread', 'user_id', 'is_read'),
        Index('ix_notifications_user_type', 'user_id', 'notification_type'),
        Index('ix_notifications_created', 'created_at'),
    )


class NotificationPreference(Base):
    """
    User notification preferences.
    """
    __tablename__ = "notification_preferences"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)

    user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)

    # Channel preferences (which channels are enabled)
    email_enabled = Column(Boolean, default=True, nullable=False)
    sms_enabled = Column(Boolean, default=False, nullable=False)
    push_enabled = Column(Boolean, default=True, nullable=False)
    in_app_enabled = Column(Boolean, default=True, nullable=False)

    # Type-specific preferences (JSONB: {notification_type: {email: bool, sms: bool, push: bool, in_app: bool}})
    type_preferences = Column(JSONB, default=dict)

    # Quiet hours
    quiet_hours_enabled = Column(Boolean, default=False, nullable=False)
    quiet_hours_start = Column(String(5))  # HH:MM format
    quiet_hours_end = Column(String(5))

    # Digest preferences
    email_digest_enabled = Column(Boolean, default=False, nullable=False)
    email_digest_frequency = Column(String(20), default="DAILY")  # DAILY, WEEKLY

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    user = relationship("User", back_populates="notification_preferences")


class NotificationTemplate(Base):
    """
    Notification templates for different notification types.
    """
    __tablename__ = "notification_templates"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)

    notification_type = Column(String(50), nullable=False, unique=True, comment="SYSTEM, ALERT, ANNOUNCEMENT, ORDER_*, etc.")

    # Template content (with placeholders like {{order_number}})
    title_template = Column(String(200), nullable=False)
    message_template = Column(Text, nullable=False)

    # Email specific
    email_subject_template = Column(String(200))
    email_body_template = Column(Text)

    # SMS specific
    sms_template = Column(String(500))

    # Default channels for this notification type
    default_channels = Column(JSONB, default=["IN_APP"])

    # Default priority
    default_priority = Column(String(20), default="MEDIUM", comment="LOW, MEDIUM, HIGH, URGENT")

    # Is this notification type enabled
    is_active = Column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)


class Announcement(Base):
    """
    System-wide announcements visible to all users.
    """
    __tablename__ = "announcements"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)

    title = Column(String(200), nullable=False)
    message = Column(Text, nullable=False)

    # Display type
    announcement_type = Column(String(20), default="INFO")  # INFO, WARNING, SUCCESS, ERROR

    # Optional action
    action_url = Column(String(500))
    action_label = Column(String(100))

    # Target audience
    target_roles = Column(JSONB, default=list)  # Empty means all users
    target_departments = Column(JSONB, default=list)

    # Schedule
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True))

    # Display settings
    is_dismissible = Column(Boolean, default=True, nullable=False)
    show_on_dashboard = Column(Boolean, default=True, nullable=False)

    # Status
    is_active = Column(Boolean, default=True, nullable=False)

    # Created by
    created_by_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))

    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    created_by = relationship("User", foreign_keys=[created_by_id])


class AnnouncementDismissal(Base):
    """
    Tracks which users have dismissed announcements.
    """
    __tablename__ = "announcement_dismissals"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)

    announcement_id = Column(PGUUID(as_uuid=True), ForeignKey("announcements.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    dismissed_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        Index('ix_announcement_dismissals_unique', 'announcement_id', 'user_id', unique=True),
    )
