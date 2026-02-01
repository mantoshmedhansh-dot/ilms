"""Pydantic schemas for Notifications module."""
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict

from app.schemas.base import BaseResponseSchema

from app.models.notifications import NotificationType, NotificationPriority


# ==================== Notification Schemas ====================

class NotificationCreate(BaseModel):
    """Schema for creating a notification."""
    user_id: UUID
    notification_type: NotificationType
    priority: NotificationPriority = NotificationPriority.MEDIUM
    title: str = Field(..., max_length=200)
    message: str
    action_url: Optional[str] = Field(None, max_length=500)
    action_label: Optional[str] = Field(None, max_length=100)
    entity_type: Optional[str] = Field(None, max_length=50)
    entity_id: Optional[UUID] = None
    extra_data: Optional[Dict[str, Any]] = None
    channels: Optional[List[str]] = None


class NotificationResponse(BaseResponseSchema):
    """Response schema for Notification."""
    id: UUID
    user_id: UUID
    notification_type: Optional[str] = None
    priority: Optional[str] = "MEDIUM"
    title: str
    message: str
    action_url: Optional[str] = None
    action_label: Optional[str] = None
    entity_type: Optional[str] = None
    entity_id: Optional[UUID] = None
    extra_data: Optional[Dict[str, Any]] = None
    is_read: Optional[bool] = False
    read_at: Optional[datetime] = None
    channels: Optional[List[str]] = None
    created_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None


class NotificationListResponse(BaseModel):
    """Response for listing notifications."""
    items: List[NotificationResponse]
    total: int
    unread_count: int
    page: int = 1
    size: int = 50
    pages: int = 1


class NotificationMarkRead(BaseModel):
    """Schema for marking notifications as read."""
    notification_ids: List[UUID]


class NotificationStats(BaseModel):
    """Notification statistics."""
    total: int
    unread: int
    by_type: Dict[str, int]
    by_priority: Dict[str, int]


# ==================== Notification Preference Schemas ====================

class NotificationPreferenceBase(BaseModel):
    """Base schema for notification preferences."""
    email_enabled: bool = True
    sms_enabled: bool = False
    push_enabled: bool = True
    in_app_enabled: bool = True
    type_preferences: Optional[Dict[str, Dict[str, bool]]] = None
    quiet_hours_enabled: bool = False
    quiet_hours_start: Optional[str] = Field(None, pattern=r"^\d{2}:\d{2}$")
    quiet_hours_end: Optional[str] = Field(None, pattern=r"^\d{2}:\d{2}$")
    email_digest_enabled: bool = False
    email_digest_frequency: str = "DAILY"


class NotificationPreferenceCreate(NotificationPreferenceBase):
    """Schema for creating notification preferences."""
    pass


class NotificationPreferenceUpdate(BaseModel):
    """Schema for updating notification preferences."""
    email_enabled: Optional[bool] = None
    sms_enabled: Optional[bool] = None
    push_enabled: Optional[bool] = None
    in_app_enabled: Optional[bool] = None
    type_preferences: Optional[Dict[str, Dict[str, bool]]] = None
    quiet_hours_enabled: Optional[bool] = None
    quiet_hours_start: Optional[str] = Field(None, pattern=r"^\d{2}:\d{2}$")
    quiet_hours_end: Optional[str] = Field(None, pattern=r"^\d{2}:\d{2}$")
    email_digest_enabled: Optional[bool] = None
    email_digest_frequency: Optional[str] = None


class NotificationPreferenceResponse(BaseResponseSchema):
    """Response schema for notification preferences."""
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime


# ==================== Announcement Schemas ====================

class AnnouncementCreate(BaseModel):
    """Schema for creating an announcement."""
    title: str = Field(..., max_length=200)
    message: str
    announcement_type: str = "INFO"
    action_url: Optional[str] = Field(None, max_length=500)
    action_label: Optional[str] = Field(None, max_length=100)
    target_roles: Optional[List[str]] = None
    target_departments: Optional[List[str]] = None
    start_date: datetime
    end_date: Optional[datetime] = None
    is_dismissible: bool = True
    show_on_dashboard: bool = True


class AnnouncementUpdate(BaseModel):
    """Schema for updating an announcement."""
    title: Optional[str] = Field(None, max_length=200)
    message: Optional[str] = None
    announcement_type: Optional[str] = None
    action_url: Optional[str] = Field(None, max_length=500)
    action_label: Optional[str] = Field(None, max_length=100)
    target_roles: Optional[List[str]] = None
    target_departments: Optional[List[str]] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    is_dismissible: Optional[bool] = None
    show_on_dashboard: Optional[bool] = None
    is_active: Optional[bool] = None


class AnnouncementResponse(BaseResponseSchema):
    """Response schema for announcement."""
    id: UUID
    title: str
    message: str
    announcement_type: Optional[str] = "INFO"
    action_url: Optional[str] = None
    action_label: Optional[str] = None
    target_roles: Optional[List[str]] = None
    target_departments: Optional[List[str]] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    is_dismissible: Optional[bool] = True
    show_on_dashboard: Optional[bool] = True
    is_active: Optional[bool] = True
    created_by_id: Optional[UUID] = None
    created_by_name: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    is_dismissed: bool = False  # For current user


class AnnouncementListResponse(BaseModel):
    """Response for listing announcements."""
    items: List[AnnouncementResponse]
    total: int
    page: int = 1
    size: int = 50
    pages: int = 1


# ==================== Notification Template Schemas ====================

class NotificationTemplateCreate(BaseModel):
    """Schema for creating a notification template."""
    notification_type: NotificationType
    title_template: str = Field(..., max_length=200)
    message_template: str
    email_subject_template: Optional[str] = Field(None, max_length=200)
    email_body_template: Optional[str] = None
    sms_template: Optional[str] = Field(None, max_length=500)
    default_channels: List[str] = ["IN_APP"]
    default_priority: NotificationPriority = NotificationPriority.MEDIUM


class NotificationTemplateUpdate(BaseModel):
    """Schema for updating a notification template."""
    title_template: Optional[str] = Field(None, max_length=200)
    message_template: Optional[str] = None
    email_subject_template: Optional[str] = Field(None, max_length=200)
    email_body_template: Optional[str] = None
    sms_template: Optional[str] = Field(None, max_length=500)
    default_channels: Optional[List[str]] = None
    default_priority: Optional[NotificationPriority] = None
    is_active: Optional[bool] = None


class NotificationTemplateResponse(BaseResponseSchema):
    """Response schema for notification template."""
    id: UUID
    notification_type: str  # VARCHAR in DB
    title_template: str
    message_template: str
    email_subject_template: Optional[str] = None
    email_body_template: Optional[str] = None
    sms_template: Optional[str] = None
    default_channels: List[str]
    default_priority: str  # VARCHAR in DB
    is_active: bool
    created_at: datetime
    updated_at: datetime


class NotificationTemplateListResponse(BaseModel):
    """Response for listing notification templates."""
    items: List[NotificationTemplateResponse]
    total: int


# ==================== Send Notification Request ====================

class SendNotificationRequest(BaseModel):
    """Request to send a notification using a template."""
    notification_type: NotificationType
    user_ids: List[UUID]  # Can send to multiple users
    variables: Optional[Dict[str, str]] = None  # Template variables
    entity_type: Optional[str] = None
    entity_id: Optional[UUID] = None
    override_channels: Optional[List[str]] = None
    override_priority: Optional[NotificationPriority] = None


class BulkNotificationResult(BaseModel):
    """Result of bulk notification send."""
    total_sent: int
    successful: int
    failed: int
    notifications: List[UUID]


# ==================== Notification Types List ====================

class NotificationTypeInfo(BaseModel):
    """Information about a notification type."""
    type: str
    label: str
    description: str
    category: str
    default_channels: List[str]
