"""API endpoints for Notifications module."""
from datetime import datetime, timezone
from typing import Optional, List
from uuid import UUID
import re

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.notifications import (
    Notification, NotificationPreference, NotificationTemplate,
    Announcement, AnnouncementDismissal,
    NotificationType, NotificationPriority
)
from app.models.user import User
from app.schemas.notifications import (
    NotificationCreate, NotificationResponse, NotificationListResponse,
    NotificationMarkRead, NotificationStats,
    NotificationPreferenceCreate, NotificationPreferenceUpdate, NotificationPreferenceResponse,
    AnnouncementCreate, AnnouncementUpdate, AnnouncementResponse, AnnouncementListResponse,
    NotificationTemplateCreate, NotificationTemplateUpdate, NotificationTemplateResponse, NotificationTemplateListResponse,
    SendNotificationRequest, BulkNotificationResult, NotificationTypeInfo
)
from app.api.deps import DB, CurrentUser, get_current_user, require_permissions
from app.core.module_decorators import require_module

router = APIRouter()


# ==================== Helper Functions ====================

def render_template(template: str, variables: dict) -> str:
    """Render template with variables ({{var}} syntax)."""
    result = template
    for key, value in variables.items():
        result = result.replace(f"{{{{{key}}}}}", str(value))
    return result


async def create_notification_from_template(
    db: AsyncSession,
    notification_type: NotificationType,
    user_id: UUID,
    variables: dict,
    entity_type: str = None,
    entity_id: UUID = None,
    override_channels: List[str] = None,
    override_priority: NotificationPriority = None,
) -> Optional[Notification]:
    """Create a notification from template."""
    # Get template
    result = await db.execute(
        select(NotificationTemplate)
        .where(NotificationTemplate.notification_type == notification_type)
        .where(NotificationTemplate.is_active == True)
    )
    template = result.scalar_one_or_none()

    if not template:
        return None

    # Render templates
    title = render_template(template.title_template, variables)
    message = render_template(template.message_template, variables)

    # Create notification
    notification = Notification(
        user_id=user_id,
        notification_type=notification_type,
        priority=override_priority or template.default_priority,
        title=title,
        message=message,
        entity_type=entity_type,
        entity_id=entity_id,
        channels=override_channels or template.default_channels,
    )

    db.add(notification)
    return notification


# ==================== User Notifications ====================

@router.get("/my", response_model=NotificationListResponse)
@require_module("system_admin")
async def get_my_notifications(
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    is_read: Optional[bool] = None,
    notification_type: Optional[NotificationType] = None,
    db: AsyncSession = Depends(DB),
    current_user: User = Depends(get_current_user),
):
    """Get current user's notifications."""
    query = select(Notification).where(Notification.user_id == current_user.id)

    if is_read is not None:
        query = query.where(Notification.is_read == is_read)

    if notification_type:
        query = query.where(Notification.notification_type == notification_type)

    # Count total
    count_query = select(func.count(Notification.id)).where(Notification.user_id == current_user.id)
    if is_read is not None:
        count_query = count_query.where(Notification.is_read == is_read)
    if notification_type:
        count_query = count_query.where(Notification.notification_type == notification_type)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Count unread
    unread_result = await db.execute(
        select(func.count(Notification.id))
        .where(Notification.user_id == current_user.id)
        .where(Notification.is_read == False)
    )
    unread_count = unread_result.scalar() or 0

    # Get paginated results
    query = query.order_by(Notification.created_at.desc())
    query = query.offset((page - 1) * size).limit(size)

    result = await db.execute(query)
    notifications = result.scalars().all()

    return NotificationListResponse(
        items=[NotificationResponse.model_validate(n) for n in notifications],
        total=total,
        unread_count=unread_count,
        page=page,
        size=size,
        pages=(total + size - 1) // size,
    )


@router.get("/my/unread-count")
@require_module("system_admin")
async def get_unread_count(
    db: AsyncSession = Depends(DB),
    current_user: User = Depends(get_current_user),
):
    """Get count of unread notifications for current user."""
    result = await db.execute(
        select(func.count(Notification.id))
        .where(Notification.user_id == current_user.id)
        .where(Notification.is_read == False)
    )
    count = result.scalar() or 0
    return {"unread_count": count}


@router.put("/my/read")
@require_module("system_admin")
async def mark_notifications_read(
    data: NotificationMarkRead,
    db: AsyncSession = Depends(DB),
    current_user: User = Depends(get_current_user),
):
    """Mark specific notifications as read."""
    now = datetime.now(timezone.utc)

    result = await db.execute(
        select(Notification)
        .where(Notification.id.in_(data.notification_ids))
        .where(Notification.user_id == current_user.id)
        .where(Notification.is_read == False)
    )
    notifications = result.scalars().all()

    for notification in notifications:
        notification.is_read = True
        notification.read_at = now

    await db.commit()

    return {"marked_read": len(notifications)}


@router.put("/my/read-all")
@require_module("system_admin")
async def mark_all_read(
    db: AsyncSession = Depends(DB),
    current_user: User = Depends(get_current_user),
):
    """Mark all notifications as read for current user."""
    now = datetime.now(timezone.utc)

    result = await db.execute(
        select(Notification)
        .where(Notification.user_id == current_user.id)
        .where(Notification.is_read == False)
    )
    notifications = result.scalars().all()

    for notification in notifications:
        notification.is_read = True
        notification.read_at = now

    await db.commit()

    return {"marked_read": len(notifications)}


@router.delete("/my/{notification_id}")
@require_module("system_admin")
async def delete_notification(
    notification_id: UUID,
    db: AsyncSession = Depends(DB),
    current_user: User = Depends(get_current_user),
):
    """Delete a notification."""
    result = await db.execute(
        select(Notification)
        .where(Notification.id == notification_id)
        .where(Notification.user_id == current_user.id)
    )
    notification = result.scalar_one_or_none()

    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")

    await db.delete(notification)
    await db.commit()

    return {"deleted": True}


@router.get("/my/stats", response_model=NotificationStats)
@require_module("system_admin")
async def get_notification_stats(
    db: AsyncSession = Depends(DB),
    current_user: User = Depends(get_current_user),
):
    """Get notification statistics for current user."""
    # Total count
    total_result = await db.execute(
        select(func.count(Notification.id))
        .where(Notification.user_id == current_user.id)
    )
    total = total_result.scalar() or 0

    # Unread count
    unread_result = await db.execute(
        select(func.count(Notification.id))
        .where(Notification.user_id == current_user.id)
        .where(Notification.is_read == False)
    )
    unread = unread_result.scalar() or 0

    # By type
    type_result = await db.execute(
        select(Notification.notification_type, func.count(Notification.id))
        .where(Notification.user_id == current_user.id)
        .group_by(Notification.notification_type)
    )
    by_type = {str(row[0].value): row[1] for row in type_result.all()}

    # By priority
    priority_result = await db.execute(
        select(Notification.priority, func.count(Notification.id))
        .where(Notification.user_id == current_user.id)
        .group_by(Notification.priority)
    )
    by_priority = {str(row[0].value): row[1] for row in priority_result.all()}

    return NotificationStats(
        total=total,
        unread=unread,
        by_type=by_type,
        by_priority=by_priority,
    )


# ==================== Notification Preferences ====================

@router.get("/preferences", response_model=NotificationPreferenceResponse)
@require_module("system_admin")
async def get_my_preferences(
    db: AsyncSession = Depends(DB),
    current_user: User = Depends(get_current_user),
):
    """Get current user's notification preferences."""
    result = await db.execute(
        select(NotificationPreference)
        .where(NotificationPreference.user_id == current_user.id)
    )
    preference = result.scalar_one_or_none()

    if not preference:
        # Create default preferences
        preference = NotificationPreference(user_id=current_user.id)
        db.add(preference)
        await db.commit()
        await db.refresh(preference)

    return NotificationPreferenceResponse.model_validate(preference)


@router.put("/preferences", response_model=NotificationPreferenceResponse)
@require_module("system_admin")
async def update_my_preferences(
    data: NotificationPreferenceUpdate,
    db: AsyncSession = Depends(DB),
    current_user: User = Depends(get_current_user),
):
    """Update current user's notification preferences."""
    result = await db.execute(
        select(NotificationPreference)
        .where(NotificationPreference.user_id == current_user.id)
    )
    preference = result.scalar_one_or_none()

    if not preference:
        preference = NotificationPreference(user_id=current_user.id)
        db.add(preference)

    # Update fields
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(preference, field, value)

    await db.commit()
    await db.refresh(preference)

    return NotificationPreferenceResponse.model_validate(preference)


# ==================== Announcements ====================

@router.get("/announcements", response_model=AnnouncementListResponse)
@require_module("system_admin")
async def list_announcements(
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    active_only: bool = True,
    db: AsyncSession = Depends(DB),
    current_user: User = Depends(get_current_user),
):
    """List announcements for current user."""
    now = datetime.now(timezone.utc)

    query = select(Announcement)

    if active_only:
        query = query.where(Announcement.is_active == True)
        query = query.where(Announcement.start_date <= now)
        query = query.where(or_(Announcement.end_date == None, Announcement.end_date >= now))

    # Count total
    count_query = select(func.count(Announcement.id))
    if active_only:
        count_query = count_query.where(Announcement.is_active == True)
        count_query = count_query.where(Announcement.start_date <= now)
        count_query = count_query.where(or_(Announcement.end_date == None, Announcement.end_date >= now))

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Get paginated results
    query = query.order_by(Announcement.start_date.desc())
    query = query.offset((page - 1) * size).limit(size)

    result = await db.execute(query)
    announcements = result.scalars().all()

    # Check dismissals for current user
    dismissal_result = await db.execute(
        select(AnnouncementDismissal.announcement_id)
        .where(AnnouncementDismissal.user_id == current_user.id)
    )
    dismissed_ids = {row[0] for row in dismissal_result.all()}

    items = []
    for ann in announcements:
        response = AnnouncementResponse.model_validate(ann)
        response.is_dismissed = ann.id in dismissed_ids
        items.append(response)

    return AnnouncementListResponse(
        items=items,
        total=total,
        page=page,
        size=size,
        pages=(total + size - 1) // size,
    )


@router.get("/announcements/active")
@require_module("system_admin")
async def get_active_announcements(
    db: AsyncSession = Depends(DB),
    current_user: User = Depends(get_current_user),
):
    """Get active, non-dismissed announcements for current user (for dashboard)."""
    now = datetime.now(timezone.utc)

    # Get dismissed announcement IDs
    dismissal_result = await db.execute(
        select(AnnouncementDismissal.announcement_id)
        .where(AnnouncementDismissal.user_id == current_user.id)
    )
    dismissed_ids = {row[0] for row in dismissal_result.all()}

    # Get active announcements
    result = await db.execute(
        select(Announcement)
        .where(Announcement.is_active == True)
        .where(Announcement.start_date <= now)
        .where(or_(Announcement.end_date == None, Announcement.end_date >= now))
        .order_by(Announcement.start_date.desc())
    )
    announcements = result.scalars().all()

    # Filter out dismissed and return only dashboard-visible ones
    items = []
    for ann in announcements:
        if ann.id not in dismissed_ids and ann.show_on_dashboard:
            response = AnnouncementResponse.model_validate(ann)
            response.is_dismissed = False
            items.append(response)

    return {"announcements": items}


@router.post("/announcements/{announcement_id}/dismiss")
@require_module("system_admin")
async def dismiss_announcement(
    announcement_id: UUID,
    db: AsyncSession = Depends(DB),
    current_user: User = Depends(get_current_user),
):
    """Dismiss an announcement for current user."""
    # Check announcement exists and is dismissible
    result = await db.execute(
        select(Announcement)
        .where(Announcement.id == announcement_id)
    )
    announcement = result.scalar_one_or_none()

    if not announcement:
        raise HTTPException(status_code=404, detail="Announcement not found")

    if not announcement.is_dismissible:
        raise HTTPException(status_code=400, detail="This announcement cannot be dismissed")

    # Check if already dismissed
    dismissal_result = await db.execute(
        select(AnnouncementDismissal)
        .where(AnnouncementDismissal.announcement_id == announcement_id)
        .where(AnnouncementDismissal.user_id == current_user.id)
    )
    existing = dismissal_result.scalar_one_or_none()

    if not existing:
        dismissal = AnnouncementDismissal(
            announcement_id=announcement_id,
            user_id=current_user.id,
        )
        db.add(dismissal)
        await db.commit()

    return {"dismissed": True}


# ==================== Admin: Announcements ====================

@router.post("/announcements", response_model=AnnouncementResponse)
@require_module("system_admin")
async def create_announcement(
    data: AnnouncementCreate,
    db: AsyncSession = Depends(DB),
    current_user: User = Depends(require_permissions(["NOTIFICATIONS_MANAGE"])),
):
    """Create a new announcement (admin only)."""
    announcement = Announcement(
        **data.model_dump(),
        created_by_id=current_user.id,
    )

    db.add(announcement)
    await db.commit()
    await db.refresh(announcement)

    response = AnnouncementResponse.model_validate(announcement)
    response.created_by_name = current_user.full_name
    return response


@router.put("/announcements/{announcement_id}", response_model=AnnouncementResponse)
@require_module("system_admin")
async def update_announcement(
    announcement_id: UUID,
    data: AnnouncementUpdate,
    db: AsyncSession = Depends(DB),
    current_user: User = Depends(require_permissions(["NOTIFICATIONS_MANAGE"])),
):
    """Update an announcement (admin only)."""
    result = await db.execute(
        select(Announcement)
        .where(Announcement.id == announcement_id)
    )
    announcement = result.scalar_one_or_none()

    if not announcement:
        raise HTTPException(status_code=404, detail="Announcement not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(announcement, field, value)

    await db.commit()
    await db.refresh(announcement)

    return AnnouncementResponse.model_validate(announcement)


@router.delete("/announcements/{announcement_id}")
@require_module("system_admin")
async def delete_announcement(
    announcement_id: UUID,
    db: AsyncSession = Depends(DB),
    current_user: User = Depends(require_permissions(["NOTIFICATIONS_MANAGE"])),
):
    """Delete an announcement (admin only)."""
    result = await db.execute(
        select(Announcement)
        .where(Announcement.id == announcement_id)
    )
    announcement = result.scalar_one_or_none()

    if not announcement:
        raise HTTPException(status_code=404, detail="Announcement not found")

    await db.delete(announcement)
    await db.commit()

    return {"deleted": True}


# ==================== Admin: Templates ====================

@router.get("/templates", response_model=NotificationTemplateListResponse)
@require_module("system_admin")
async def list_templates(
    db: AsyncSession = Depends(DB),
    current_user: User = Depends(require_permissions(["NOTIFICATIONS_MANAGE"])),
):
    """List all notification templates (admin only)."""
    result = await db.execute(
        select(NotificationTemplate)
        .order_by(NotificationTemplate.notification_type)
    )
    templates = result.scalars().all()

    return NotificationTemplateListResponse(
        items=[NotificationTemplateResponse.model_validate(t) for t in templates],
        total=len(templates),
    )


@router.post("/templates", response_model=NotificationTemplateResponse)
@require_module("system_admin")
async def create_template(
    data: NotificationTemplateCreate,
    db: AsyncSession = Depends(DB),
    current_user: User = Depends(require_permissions(["NOTIFICATIONS_MANAGE"])),
):
    """Create a notification template (admin only)."""
    # Check if template for this type already exists
    result = await db.execute(
        select(NotificationTemplate)
        .where(NotificationTemplate.notification_type == data.notification_type)
    )
    existing = result.scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Template for {data.notification_type.value} already exists"
        )

    template = NotificationTemplate(**data.model_dump())
    db.add(template)
    await db.commit()
    await db.refresh(template)

    return NotificationTemplateResponse.model_validate(template)


@router.put("/templates/{template_id}", response_model=NotificationTemplateResponse)
@require_module("system_admin")
async def update_template(
    template_id: UUID,
    data: NotificationTemplateUpdate,
    db: AsyncSession = Depends(DB),
    current_user: User = Depends(require_permissions(["NOTIFICATIONS_MANAGE"])),
):
    """Update a notification template (admin only)."""
    result = await db.execute(
        select(NotificationTemplate)
        .where(NotificationTemplate.id == template_id)
    )
    template = result.scalar_one_or_none()

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(template, field, value)

    await db.commit()
    await db.refresh(template)

    return NotificationTemplateResponse.model_validate(template)


# ==================== Admin: Send Notifications ====================

@router.post("/send", response_model=BulkNotificationResult)
@require_module("system_admin")
async def send_notification(
    data: SendNotificationRequest,
    db: AsyncSession = Depends(DB),
    current_user: User = Depends(require_permissions(["NOTIFICATIONS_MANAGE"])),
):
    """Send notifications to users using a template (admin only)."""
    created_ids = []
    failed = 0

    for user_id in data.user_ids:
        try:
            notification = await create_notification_from_template(
                db=db,
                notification_type=data.notification_type,
                user_id=user_id,
                variables=data.variables or {},
                entity_type=data.entity_type,
                entity_id=data.entity_id,
                override_channels=data.override_channels,
                override_priority=data.override_priority,
            )

            if notification:
                created_ids.append(notification.id)
            else:
                failed += 1
        except Exception:
            failed += 1

    await db.commit()

    return BulkNotificationResult(
        total_sent=len(data.user_ids),
        successful=len(created_ids),
        failed=failed,
        notifications=created_ids,
    )


# ==================== Notification Types ====================

@router.get("/types")
@require_module("system_admin")
async def list_notification_types():
    """List all notification types with their categories."""
    categories = {
        "SYSTEM": ["SYSTEM", "ALERT", "ANNOUNCEMENT"],
        "ORDERS": ["ORDER_CREATED", "ORDER_CONFIRMED", "ORDER_SHIPPED", "ORDER_DELIVERED", "ORDER_CANCELLED"],
        "INVENTORY": ["LOW_STOCK", "OUT_OF_STOCK", "STOCK_RECEIVED"],
        "APPROVALS": ["APPROVAL_PENDING", "APPROVAL_APPROVED", "APPROVAL_REJECTED"],
        "HR": ["LEAVE_REQUEST", "LEAVE_APPROVED", "LEAVE_REJECTED", "PAYSLIP_GENERATED", "APPRAISAL_DUE"],
        "FINANCE": ["PAYMENT_RECEIVED", "PAYMENT_DUE", "INVOICE_GENERATED"],
        "SERVICE": ["SERVICE_ASSIGNED", "SERVICE_COMPLETED", "WARRANTY_EXPIRING"],
        "FIXED_ASSETS": ["ASSET_MAINTENANCE_DUE", "ASSET_TRANSFER_PENDING"],
        "GENERAL": ["TASK_ASSIGNED", "REMINDER", "MENTION"],
    }

    types = []
    for category, type_list in categories.items():
        for type_name in type_list:
            types.append({
                "type": type_name,
                "category": category,
                "label": type_name.replace("_", " ").title(),
            })

    return {"types": types, "categories": list(categories.keys())}
