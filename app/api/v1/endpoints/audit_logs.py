"""Audit Logs API endpoints."""
from typing import Optional
from uuid import UUID
from datetime import datetime, date, timezone

from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy import select, func, desc, and_
from sqlalchemy.orm import selectinload

from app.api.deps import DB, get_current_user
from app.models.user import User
from app.models.audit_log import AuditLog
from app.core.module_decorators import require_module

router = APIRouter()


@router.get("")
@require_module("system_admin")
async def list_audit_logs(
    db: DB,
    current_user: User = Depends(get_current_user),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    user_id: Optional[UUID] = None,
    action: Optional[str] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[UUID] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    search: Optional[str] = None,
):
    """
    List audit logs with filtering and pagination.

    Filters:
    - user_id: Filter by user who performed action
    - action: Filter by action type (CREATE, UPDATE, DELETE, etc.)
    - entity_type: Filter by entity type (USER, ROLE, ORDER, etc.)
    - entity_id: Filter by specific entity ID
    - start_date/end_date: Date range filter
    - search: Search in description
    """
    # Build query
    query = select(AuditLog).options(selectinload(AuditLog.user))

    conditions = []

    if user_id:
        conditions.append(AuditLog.user_id == user_id)

    if action:
        conditions.append(AuditLog.action == action.upper())

    if entity_type:
        conditions.append(AuditLog.entity_type == entity_type.upper())

    if entity_id:
        conditions.append(AuditLog.entity_id == entity_id)

    if start_date:
        conditions.append(AuditLog.created_at >= datetime.combine(start_date, datetime.min.time()))

    if end_date:
        conditions.append(AuditLog.created_at <= datetime.combine(end_date, datetime.max.time()))

    if search:
        conditions.append(AuditLog.description.ilike(f"%{search}%"))

    if conditions:
        query = query.where(and_(*conditions))

    # Count total
    count_query = select(func.count()).select_from(AuditLog)
    if conditions:
        count_query = count_query.where(and_(*conditions))
    total = await db.scalar(count_query) or 0

    # Get paginated results
    query = query.order_by(desc(AuditLog.created_at))
    query = query.offset((page - 1) * size).limit(size)

    result = await db.execute(query)
    logs = result.scalars().all()

    return {
        "items": [
            {
                "id": str(log.id),
                "user_id": str(log.user_id) if log.user_id else None,
                "user_name": f"{log.user.first_name} {log.user.last_name}" if log.user else "System",
                "user_email": log.user.email if log.user else None,
                "action": log.action,
                "entity_type": log.entity_type,
                "entity_id": str(log.entity_id) if log.entity_id else None,
                "old_values": log.old_values,
                "new_values": log.new_values,
                "description": log.description,
                "ip_address": log.ip_address,
                "user_agent": log.user_agent,
                "created_at": log.created_at.isoformat() if log.created_at else None,
            }
            for log in logs
        ],
        "total": total,
        "page": page,
        "size": size,
        "pages": (total + size - 1) // size,
    }


@router.get("/actions")
@require_module("system_admin")
async def get_audit_actions(
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Get list of unique action types for filtering."""
    query = select(AuditLog.action).distinct()
    result = await db.execute(query)
    actions = [row[0] for row in result.all()]
    return {"actions": sorted(actions)}


@router.get("/entity-types")
@require_module("system_admin")
async def get_audit_entity_types(
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Get list of unique entity types for filtering."""
    query = select(AuditLog.entity_type).distinct()
    result = await db.execute(query)
    entity_types = [row[0] for row in result.all()]
    return {"entity_types": sorted(entity_types)}


@router.get("/stats")
@require_module("system_admin")
async def get_audit_stats(
    db: DB,
    current_user: User = Depends(get_current_user),
    days: int = Query(30, ge=1, le=365),
):
    """Get audit log statistics for the specified number of days."""
    from datetime import timedelta

    start_date = datetime.now(timezone.utc) - timedelta(days=days)

    # Total logs in period
    total_query = select(func.count()).select_from(AuditLog).where(
        AuditLog.created_at >= start_date
    )
    total_logs = await db.scalar(total_query) or 0

    # Logs by action
    action_query = select(
        AuditLog.action,
        func.count().label("count")
    ).where(
        AuditLog.created_at >= start_date
    ).group_by(AuditLog.action).order_by(desc("count"))

    action_result = await db.execute(action_query)
    by_action = [{"action": row[0], "count": row[1]} for row in action_result.all()]

    # Logs by entity type
    entity_query = select(
        AuditLog.entity_type,
        func.count().label("count")
    ).where(
        AuditLog.created_at >= start_date
    ).group_by(AuditLog.entity_type).order_by(desc("count"))

    entity_result = await db.execute(entity_query)
    by_entity = [{"entity_type": row[0], "count": row[1]} for row in entity_result.all()]

    # Most active users
    user_query = select(
        AuditLog.user_id,
        func.count().label("count")
    ).where(
        and_(
            AuditLog.created_at >= start_date,
            AuditLog.user_id.isnot(None)
        )
    ).group_by(AuditLog.user_id).order_by(desc("count")).limit(10)

    user_result = await db.execute(user_query)
    top_users_data = user_result.all()

    # Get user details
    top_users = []
    for user_id, count in top_users_data:
        user = await db.get(User, user_id)
        if user:
            top_users.append({
                "user_id": str(user_id),
                "user_name": f"{user.first_name} {user.last_name}",
                "count": count
            })

    return {
        "period_days": days,
        "total_logs": total_logs,
        "by_action": by_action,
        "by_entity_type": by_entity,
        "top_users": top_users,
    }


@router.get("/{log_id}")
@require_module("system_admin")
async def get_audit_log(
    log_id: UUID,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Get a specific audit log entry."""
    query = select(AuditLog).options(selectinload(AuditLog.user)).where(
        AuditLog.id == log_id
    )
    result = await db.execute(query)
    log = result.scalar_one_or_none()

    if not log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audit log not found"
        )

    return {
        "id": str(log.id),
        "user_id": str(log.user_id) if log.user_id else None,
        "user_name": f"{log.user.first_name} {log.user.last_name}" if log.user else "System",
        "user_email": log.user.email if log.user else None,
        "action": log.action,
        "entity_type": log.entity_type,
        "entity_id": str(log.entity_id) if log.entity_id else None,
        "old_values": log.old_values,
        "new_values": log.new_values,
        "description": log.description,
        "ip_address": log.ip_address,
        "user_agent": log.user_agent,
        "created_at": log.created_at.isoformat() if log.created_at else None,
    }


@router.get("/entity/{entity_type}/{entity_id}")
@require_module("system_admin")
async def get_entity_history(
    entity_type: str,
    entity_id: UUID,
    db: DB,
    current_user: User = Depends(get_current_user),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    """Get audit history for a specific entity."""
    query = select(AuditLog).options(selectinload(AuditLog.user)).where(
        and_(
            AuditLog.entity_type == entity_type.upper(),
            AuditLog.entity_id == entity_id
        )
    ).order_by(desc(AuditLog.created_at))

    # Count
    count_query = select(func.count()).select_from(AuditLog).where(
        and_(
            AuditLog.entity_type == entity_type.upper(),
            AuditLog.entity_id == entity_id
        )
    )
    total = await db.scalar(count_query) or 0

    # Paginate
    query = query.offset((page - 1) * size).limit(size)
    result = await db.execute(query)
    logs = result.scalars().all()

    return {
        "entity_type": entity_type.upper(),
        "entity_id": str(entity_id),
        "items": [
            {
                "id": str(log.id),
                "user_id": str(log.user_id) if log.user_id else None,
                "user_name": f"{log.user.first_name} {log.user.last_name}" if log.user else "System",
                "action": log.action,
                "old_values": log.old_values,
                "new_values": log.new_values,
                "description": log.description,
                "created_at": log.created_at.isoformat() if log.created_at else None,
            }
            for log in logs
        ],
        "total": total,
        "page": page,
        "size": size,
    }
