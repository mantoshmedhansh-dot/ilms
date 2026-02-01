from typing import Optional, Dict, Any, List
import uuid
from datetime import datetime

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog


class AuditService:
    """
    Audit service for logging all access control changes.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def log(
        self,
        action: str,
        entity_type: str,
        entity_id: Optional[uuid.UUID] = None,
        user_id: Optional[uuid.UUID] = None,
        old_values: Optional[Dict[str, Any]] = None,
        new_values: Optional[Dict[str, Any]] = None,
        description: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditLog:
        """
        Create an audit log entry.

        Args:
            action: The action performed (CREATE, UPDATE, DELETE, etc.)
            entity_type: Type of entity (USER, ROLE, PERMISSION, etc.)
            entity_id: ID of the affected entity
            user_id: ID of the user performing the action
            old_values: Previous values (for updates)
            new_values: New values (for creates/updates)
            description: Human-readable description
            ip_address: Client IP address
            user_agent: Client user agent

        Returns:
            The created AuditLog entry
        """
        audit_log = AuditLog(
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            user_id=user_id,
            old_values=old_values,
            new_values=new_values,
            description=description,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.db.add(audit_log)
        await self.db.flush()
        return audit_log

    async def log_role_created(
        self,
        role_id: uuid.UUID,
        role_data: Dict[str, Any],
        user_id: Optional[uuid.UUID] = None,
        ip_address: Optional[str] = None,
    ) -> AuditLog:
        """Log role creation."""
        return await self.log(
            action="CREATE",
            entity_type="ROLE",
            entity_id=role_id,
            user_id=user_id,
            new_values=role_data,
            description=f"Created role: {role_data.get('name')}",
            ip_address=ip_address,
        )

    async def log_role_updated(
        self,
        role_id: uuid.UUID,
        old_data: Dict[str, Any],
        new_data: Dict[str, Any],
        user_id: Optional[uuid.UUID] = None,
        ip_address: Optional[str] = None,
    ) -> AuditLog:
        """Log role update."""
        return await self.log(
            action="UPDATE",
            entity_type="ROLE",
            entity_id=role_id,
            user_id=user_id,
            old_values=old_data,
            new_values=new_data,
            description=f"Updated role: {new_data.get('name', old_data.get('name'))}",
            ip_address=ip_address,
        )

    async def log_role_deleted(
        self,
        role_id: uuid.UUID,
        role_data: Dict[str, Any],
        user_id: Optional[uuid.UUID] = None,
        ip_address: Optional[str] = None,
    ) -> AuditLog:
        """Log role deletion."""
        return await self.log(
            action="DELETE",
            entity_type="ROLE",
            entity_id=role_id,
            user_id=user_id,
            old_values=role_data,
            description=f"Deleted role: {role_data.get('name')}",
            ip_address=ip_address,
        )

    async def log_role_assigned(
        self,
        user_id: uuid.UUID,
        role_id: uuid.UUID,
        role_name: str,
        assigned_by: Optional[uuid.UUID] = None,
        ip_address: Optional[str] = None,
    ) -> AuditLog:
        """Log role assignment to user."""
        return await self.log(
            action="ASSIGN_ROLE",
            entity_type="USER_ROLE",
            entity_id=user_id,
            user_id=assigned_by,
            new_values={"role_id": str(role_id), "role_name": role_name},
            description=f"Assigned role '{role_name}' to user",
            ip_address=ip_address,
        )

    async def log_role_revoked(
        self,
        user_id: uuid.UUID,
        role_id: uuid.UUID,
        role_name: str,
        revoked_by: Optional[uuid.UUID] = None,
        ip_address: Optional[str] = None,
    ) -> AuditLog:
        """Log role revocation from user."""
        return await self.log(
            action="REVOKE_ROLE",
            entity_type="USER_ROLE",
            entity_id=user_id,
            user_id=revoked_by,
            old_values={"role_id": str(role_id), "role_name": role_name},
            description=f"Revoked role '{role_name}' from user",
            ip_address=ip_address,
        )

    async def log_permission_granted(
        self,
        role_id: uuid.UUID,
        permission_ids: List[uuid.UUID],
        granted_by: Optional[uuid.UUID] = None,
        ip_address: Optional[str] = None,
    ) -> AuditLog:
        """Log permission grant to role."""
        return await self.log(
            action="GRANT_PERMISSION",
            entity_type="ROLE_PERMISSION",
            entity_id=role_id,
            user_id=granted_by,
            new_values={"permission_ids": [str(pid) for pid in permission_ids]},
            description=f"Updated permissions for role",
            ip_address=ip_address,
        )

    async def log_user_login(
        self,
        user_id: uuid.UUID,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditLog:
        """Log user login."""
        return await self.log(
            action="LOGIN",
            entity_type="USER",
            entity_id=user_id,
            user_id=user_id,
            description="User logged in",
            ip_address=ip_address,
            user_agent=user_agent,
        )

    async def log_user_logout(
        self,
        user_id: uuid.UUID,
        ip_address: Optional[str] = None,
    ) -> AuditLog:
        """Log user logout."""
        return await self.log(
            action="LOGOUT",
            entity_type="USER",
            entity_id=user_id,
            user_id=user_id,
            description="User logged out",
            ip_address=ip_address,
        )

    async def get_audit_logs(
        self,
        entity_type: Optional[str] = None,
        entity_id: Optional[uuid.UUID] = None,
        user_id: Optional[uuid.UUID] = None,
        action: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[List[AuditLog], int]:
        """
        Get audit logs with filtering.
        """
        stmt = select(AuditLog).order_by(AuditLog.created_at.desc())

        if entity_type:
            stmt = stmt.where(AuditLog.entity_type == entity_type)
        if entity_id:
            stmt = stmt.where(AuditLog.entity_id == entity_id)
        if user_id:
            stmt = stmt.where(AuditLog.user_id == user_id)
        if action:
            stmt = stmt.where(AuditLog.action == action)
        if start_date:
            stmt = stmt.where(AuditLog.created_at >= start_date)
        if end_date:
            stmt = stmt.where(AuditLog.created_at <= end_date)

        # Count total
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.db.execute(count_stmt)).scalar()

        # Get paginated results
        stmt = stmt.offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        logs = result.scalars().all()

        return list(logs), total
