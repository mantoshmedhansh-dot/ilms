from typing import List, Optional, Set, Dict, Any
import uuid

from sqlalchemy import select, func, delete
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole
from app.models.role import Role, RoleLevel
from app.models.permission import Permission, RolePermission
from app.models.module import Module
from app.schemas.role import RoleCreate, RoleUpdate
from app.schemas.permission import (
    PermissionsByModule,
    ModulePermissionGroup,
    PermissionGroupItem,
)


class RBACService:
    """
    Role-Based Access Control service.
    Manages roles, permissions, and user-role assignments.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    # ==================== ROLE METHODS ====================

    async def get_roles(
        self,
        skip: int = 0,
        limit: int = 100,
        include_inactive: bool = False
    ) -> tuple[List[Dict[str, Any]], int]:
        """Get paginated list of roles with permission counts."""
        # Count query
        count_stmt = select(func.count(Role.id))
        if not include_inactive:
            count_stmt = count_stmt.where(Role.is_active == True)
        total = (await self.db.execute(count_stmt)).scalar()

        # Subquery for permission count
        perm_count_subq = (
            select(
                RolePermission.role_id,
                func.count(RolePermission.permission_id).label('permission_count')
            )
            .group_by(RolePermission.role_id)
            .subquery()
        )

        # Data query with permission count
        stmt = (
            select(
                Role,
                func.coalesce(perm_count_subq.c.permission_count, 0).label('permission_count')
            )
            .outerjoin(perm_count_subq, Role.id == perm_count_subq.c.role_id)
            .order_by(Role.level, Role.name)
        )
        if not include_inactive:
            stmt = stmt.where(Role.is_active == True)
        stmt = stmt.offset(skip).limit(limit)

        result = await self.db.execute(stmt)
        rows = result.all()

        # Build result with permission count attached
        roles_with_count = []
        for row in rows:
            role = row[0]
            perm_count = row[1]
            # Attach permission_count as attribute
            role.permission_count = perm_count
            roles_with_count.append(role)

        return roles_with_count, total

    async def get_role_by_id(
        self,
        role_id: uuid.UUID,
        include_permissions: bool = False
    ) -> Optional[Role]:
        """Get a role by ID."""
        stmt = select(Role).where(Role.id == role_id)
        if include_permissions:
            # Need to load: role_permissions -> permission -> module
            # for accessing rp.permission.module.name in endpoints
            stmt = stmt.options(
                selectinload(Role.role_permissions)
                .selectinload(RolePermission.permission)
                .selectinload(Permission.module)
            )

        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_role_by_code(self, code: str) -> Optional[Role]:
        """Get a role by code."""
        stmt = select(Role).where(Role.code == code)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def create_role(
        self,
        data: RoleCreate,
        created_by: Optional[uuid.UUID] = None
    ) -> Role:
        """Create a new role."""
        role = Role(
            name=data.name,
            code=data.code,
            description=data.description,
            level=data.level,
            department=data.department,
        )
        self.db.add(role)
        await self.db.flush()

        # Assign permissions if provided
        if data.permission_ids:
            await self.update_role_permissions(
                role.id,
                data.permission_ids
            )

        await self.db.commit()
        await self.db.refresh(role)
        return role

    async def update_role(
        self,
        role_id: uuid.UUID,
        data: RoleUpdate
    ) -> Optional[Role]:
        """Update a role."""
        role = await self.get_role_by_id(role_id)
        if not role:
            return None

        # Fields that cannot be NULL in database
        non_nullable_fields = {"name", "level", "is_active"}

        # Prevent updating system roles' critical fields
        if role.is_system:
            # Only allow updating description and is_active for system roles
            if data.description is not None:
                role.description = data.description
            if data.is_active is not None:
                role.is_active = data.is_active
        else:
            for field, value in data.model_dump(exclude_unset=True).items():
                # Skip None values for non-nullable fields to avoid constraint violations
                if value is None and field in non_nullable_fields:
                    continue
                setattr(role, field, value)

        await self.db.commit()
        await self.db.refresh(role)
        return role

    async def delete_role(self, role_id: uuid.UUID) -> bool:
        """Delete a role (soft delete by deactivating)."""
        role = await self.get_role_by_id(role_id)
        if not role or role.is_system:
            return False

        role.is_active = False
        await self.db.commit()
        return True

    # ==================== PERMISSION METHODS ====================

    async def get_permissions(
        self,
        module_id: Optional[uuid.UUID] = None
    ) -> List[Permission]:
        """Get all permissions, optionally filtered by module."""
        stmt = (
            select(Permission)
            .options(selectinload(Permission.module))
            .where(Permission.is_active == True)
            .order_by(Permission.module_id, Permission.action)
        )

        if module_id:
            stmt = stmt.where(Permission.module_id == module_id)

        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_permissions_by_module(self) -> PermissionsByModule:
        """Get all permissions grouped by module."""
        # Get modules with their permissions
        stmt = (
            select(Module)
            .options(selectinload(Module.permissions))
            .where(Module.is_active == True)
            .order_by(Module.sort_order)
        )
        result = await self.db.execute(stmt)
        modules = result.scalars().all()

        module_groups = []
        total_permissions = 0

        for module in modules:
            active_permissions = [p for p in module.permissions if p.is_active]
            if active_permissions:
                permission_items = [
                    PermissionGroupItem(
                        id=p.id,
                        name=p.name,
                        code=p.code,
                        action=p.action,
                        description=p.description
                    )
                    for p in active_permissions
                ]
                module_groups.append(
                    ModulePermissionGroup(
                        module_id=module.id,
                        module_name=module.name,
                        module_code=module.code,
                        permissions=permission_items
                    )
                )
                total_permissions += len(permission_items)

        return PermissionsByModule(
            modules=module_groups,
            total_permissions=total_permissions
        )

    async def get_role_permissions(
        self,
        role_id: uuid.UUID
    ) -> List[Permission]:
        """Get all permissions assigned to a role."""
        stmt = (
            select(Permission)
            .join(RolePermission, Permission.id == RolePermission.permission_id)
            .options(selectinload(Permission.module))
            .where(RolePermission.role_id == role_id)
            .where(Permission.is_active == True)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def update_role_permissions(
        self,
        role_id: uuid.UUID,
        permission_ids: List[uuid.UUID]
    ) -> None:
        """Update all permissions for a role (replace existing)."""
        # Remove existing permissions
        await self.db.execute(
            delete(RolePermission).where(RolePermission.role_id == role_id)
        )

        # Add new permissions
        for perm_id in permission_ids:
            role_perm = RolePermission(
                role_id=role_id,
                permission_id=perm_id
            )
            self.db.add(role_perm)

        await self.db.flush()

    # ==================== USER-ROLE METHODS ====================

    async def get_user_roles(self, user_id: uuid.UUID) -> List[Role]:
        """Get all roles assigned to a user."""
        stmt = (
            select(Role)
            .join(UserRole, Role.id == UserRole.role_id)
            .where(UserRole.user_id == user_id)
            .where(Role.is_active == True)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def assign_roles_to_user(
        self,
        user_id: uuid.UUID,
        role_ids: List[uuid.UUID],
        assigned_by: Optional[uuid.UUID] = None
    ) -> None:
        """Assign roles to a user (replace existing)."""
        # Remove existing role assignments
        await self.db.execute(
            delete(UserRole).where(UserRole.user_id == user_id)
        )

        # Add new role assignments
        for role_id in role_ids:
            user_role = UserRole(
                user_id=user_id,
                role_id=role_id,
                assigned_by=assigned_by
            )
            self.db.add(user_role)

        await self.db.commit()

    async def add_role_to_user(
        self,
        user_id: uuid.UUID,
        role_id: uuid.UUID,
        assigned_by: Optional[uuid.UUID] = None
    ) -> bool:
        """Add a single role to a user."""
        # Check if already assigned
        stmt = select(UserRole).where(
            UserRole.user_id == user_id,
            UserRole.role_id == role_id
        )
        result = await self.db.execute(stmt)
        if result.scalar_one_or_none():
            return False  # Already assigned

        user_role = UserRole(
            user_id=user_id,
            role_id=role_id,
            assigned_by=assigned_by
        )
        self.db.add(user_role)
        await self.db.commit()
        return True

    async def remove_role_from_user(
        self,
        user_id: uuid.UUID,
        role_id: uuid.UUID
    ) -> bool:
        """Remove a single role from a user."""
        result = await self.db.execute(
            delete(UserRole).where(
                UserRole.user_id == user_id,
                UserRole.role_id == role_id
            )
        )
        await self.db.commit()
        return result.rowcount > 0

    # ==================== USER PERMISSION METHODS ====================

    async def get_user_permission_codes(
        self,
        user_id: uuid.UUID
    ) -> Set[str]:
        """Get all permission codes for a user across all their roles."""
        # Get user's roles first
        roles = await self.get_user_roles(user_id)

        # Check for SUPER_ADMIN
        for role in roles:
            if role.level == RoleLevel.SUPER_ADMIN.name:
                # Return all permission codes
                stmt = select(Permission.code).where(Permission.is_active == True)
                result = await self.db.execute(stmt)
                return {row[0] for row in result.all()}

        if not roles:
            return set()

        role_ids = [role.id for role in roles]

        # Get all permission codes for the user's roles
        stmt = (
            select(Permission.code)
            .join(RolePermission, Permission.id == RolePermission.permission_id)
            .where(RolePermission.role_id.in_(role_ids))
            .where(Permission.is_active == True)
        )
        result = await self.db.execute(stmt)
        return {row[0] for row in result.all()}

    async def check_user_permission(
        self,
        user_id: uuid.UUID,
        permission_code: str
    ) -> bool:
        """Check if a user has a specific permission."""
        permission_codes = await self.get_user_permission_codes(user_id)
        return permission_code in permission_codes

    # ==================== MODULE METHODS ====================

    async def get_modules(self) -> List[Module]:
        """Get all active modules."""
        stmt = (
            select(Module)
            .where(Module.is_active == True)
            .order_by(Module.sort_order)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
