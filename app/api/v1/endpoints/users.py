from typing import Optional
import uuid
from math import ceil

from fastapi import APIRouter, HTTPException, status, Query, Depends, Request
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.api.deps import DB, CurrentUser, Permissions, require_permissions
from app.models.user import User, UserRole
from app.models.role import Role
from app.schemas.user import (
    UserCreate,
    UserUpdate,
    UserResponse,
    UserListResponse,
    UserRoleAssignment,
    RoleBasicInfo,
    RegionBasicInfo,
)
from app.services.rbac_service import RBACService
from app.services.auth_service import AuthService
from app.services.audit_service import AuditService
from app.models.role import RoleLevel


router = APIRouter(tags=["Users"])


def _get_level_name(level) -> str:
    """Helper to get role level name, handling SQLite returning integers."""
    if hasattr(level, 'name'):
        return level.name
    try:
        return RoleLevel(level).name
    except (ValueError, TypeError):
        return str(level)


def _get_type_value(type_enum) -> str:
    """Helper to get type value, handling SQLite returning strings."""
    if hasattr(type_enum, 'value'):
        return type_enum.value
    return str(type_enum)


@router.get(
    "",
    response_model=UserListResponse,
    dependencies=[Depends(require_permissions("access_control:view"))]
)
async def list_users(
    db: DB,
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    search: Optional[str] = Query(None, description="Search by name or email"),
    role_id: Optional[uuid.UUID] = Query(None, description="Filter by role"),
    department: Optional[str] = Query(None, description="Filter by department"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
):
    """
    Get paginated list of users.
    Requires: access_control:view permission
    """
    skip = (page - 1) * size

    # Build query
    stmt = (
        select(User)
        .options(
            selectinload(User.user_roles).selectinload(UserRole.role),
            selectinload(User.region)
        )
        .order_by(User.created_at.desc())
    )

    count_stmt = select(func.count(User.id))

    # Apply filters
    if search:
        search_filter = f"%{search}%"
        stmt = stmt.where(
            (User.email.ilike(search_filter)) |
            (User.first_name.ilike(search_filter)) |
            (User.last_name.ilike(search_filter))
        )
        count_stmt = count_stmt.where(
            (User.email.ilike(search_filter)) |
            (User.first_name.ilike(search_filter)) |
            (User.last_name.ilike(search_filter))
        )

    if role_id:
        stmt = stmt.join(UserRole).where(UserRole.role_id == role_id)
        count_stmt = count_stmt.join(UserRole).where(UserRole.role_id == role_id)

    if department:
        stmt = stmt.where(User.department == department)
        count_stmt = count_stmt.where(User.department == department)

    if is_active is not None:
        stmt = stmt.where(User.is_active == is_active)
        count_stmt = count_stmt.where(User.is_active == is_active)

    # Get total count
    total = (await db.execute(count_stmt)).scalar()

    # Get paginated results
    stmt = stmt.offset(skip).limit(size)
    result = await db.execute(stmt)
    users = result.scalars().unique().all()

    # Build response
    items = []
    for user in users:
        items.append(UserResponse(
            id=user.id,
            email=user.email,
            phone=user.phone,
            first_name=user.first_name,
            last_name=user.last_name,
            full_name=user.full_name,
            employee_code=user.employee_code,
            department=user.department,
            designation=user.designation,
            avatar_url=user.avatar_url,
            is_active=user.is_active,
            is_verified=user.is_verified,
            region=RegionBasicInfo(
                id=user.region.id,
                name=user.region.name,
                code=user.region.code,
                type=_get_type_value(user.region.type) if hasattr(user.region.type, 'value') else str(user.region.type),
            ) if user.region else None,
            roles=[
                RoleBasicInfo(
                    id=ur.role.id,
                    name=ur.role.name,
                    code=ur.role.code,
                    level=_get_level_name(ur.role.level),
                )
                for ur in user.user_roles
                if ur.role.is_active
            ],
            created_at=user.created_at,
            updated_at=user.updated_at,
            last_login_at=user.last_login_at,
        ))

    return UserListResponse(
        items=items,
        total=total,
        page=page,
        size=size,
        pages=ceil(total / size) if total > 0 else 1,
    )


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    dependencies=[Depends(require_permissions("access_control:view"))]
)
async def get_user(
    user_id: uuid.UUID,
    db: DB,
):
    """
    Get a user by ID.
    Requires: access_control:view permission
    """
    stmt = (
        select(User)
        .options(
            selectinload(User.user_roles).selectinload(UserRole.role),
            selectinload(User.region)
        )
        .where(User.id == user_id)
    )
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return UserResponse(
        id=user.id,
        email=user.email,
        phone=user.phone,
        first_name=user.first_name,
        last_name=user.last_name,
        full_name=user.full_name,
        employee_code=user.employee_code,
        department=user.department,
        designation=user.designation,
        avatar_url=user.avatar_url,
        is_active=user.is_active,
        is_verified=user.is_verified,
        region=RegionBasicInfo(
            id=user.region.id,
            name=user.region.name,
            code=user.region.code,
            type=_get_type_value(user.region.type) if hasattr(user.region.type, 'value') else str(user.region.type),
        ) if user.region else None,
        roles=[
            RoleBasicInfo(
                id=ur.role.id,
                name=ur.role.name,
                code=ur.role.code,
                level=_get_level_name(ur.role.level),
            )
            for ur in user.user_roles
            if ur.role.is_active
        ],
        created_at=user.created_at,
        updated_at=user.updated_at,
        last_login_at=user.last_login_at,
    )


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions("access_control:create"))]
)
async def create_user(
    data: UserCreate,
    db: DB,
    current_user: CurrentUser,
    permissions: Permissions,
):
    """
    Create a new user.
    Requires: access_control:create permission
    """
    # Check if email already exists
    stmt = select(User).where(User.email == data.email.lower())
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Check if phone already exists (if provided)
    if data.phone:
        stmt = select(User).where(User.phone == data.phone)
        existing = (await db.execute(stmt)).scalar_one_or_none()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone number already registered"
            )

    auth_service = AuthService(db)
    rbac_service = RBACService(db)

    # Create user
    user = await auth_service.register_user(
        email=data.email,
        password=data.password,
        first_name=data.first_name,
        last_name=data.last_name,
        phone=data.phone,
        employee_code=data.employee_code,
        department=data.department,
        designation=data.designation,
        region_id=data.region_id,
    )

    # Assign roles if provided
    if data.role_ids:
        await rbac_service.assign_roles_to_user(
            user.id,
            data.role_ids,
            assigned_by=current_user.id
        )

    # Reload user with relationships
    stmt = (
        select(User)
        .options(
            selectinload(User.user_roles).selectinload(UserRole.role),
            selectinload(User.region)
        )
        .where(User.id == user.id)
    )
    result = await db.execute(stmt)
    user = result.scalar_one()

    return UserResponse(
        id=user.id,
        email=user.email,
        phone=user.phone,
        first_name=user.first_name,
        last_name=user.last_name,
        full_name=user.full_name,
        employee_code=user.employee_code,
        department=user.department,
        designation=user.designation,
        avatar_url=user.avatar_url,
        is_active=user.is_active,
        is_verified=user.is_verified,
        region=RegionBasicInfo(
            id=user.region.id,
            name=user.region.name,
            code=user.region.code,
            type=_get_type_value(user.region.type),
        ) if user.region else None,
        roles=[
            RoleBasicInfo(
                id=ur.role.id,
                name=ur.role.name,
                code=ur.role.code,
                level=_get_level_name(ur.role.level),
            )
            for ur in user.user_roles
            if ur.role.is_active
        ],
        created_at=user.created_at,
        updated_at=user.updated_at,
        last_login_at=user.last_login_at,
    )


@router.put(
    "/{user_id}",
    response_model=UserResponse,
    dependencies=[Depends(require_permissions("access_control:update"))]
)
async def update_user(
    user_id: uuid.UUID,
    data: UserUpdate,
    db: DB,
    current_user: CurrentUser,
    permissions: Permissions,
):
    """
    Update a user.
    Requires: access_control:update permission
    """
    stmt = (
        select(User)
        .options(
            selectinload(User.user_roles).selectinload(UserRole.role),
            selectinload(User.region)
        )
        .where(User.id == user_id)
    )
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Check if user can modify this user (unless modifying self)
    if user.id != current_user.id and not permissions.can_manage_user(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot modify a user at or above your own level"
        )

    # Update fields
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(user, field, value)

    await db.commit()
    await db.refresh(user)

    return UserResponse(
        id=user.id,
        email=user.email,
        phone=user.phone,
        first_name=user.first_name,
        last_name=user.last_name,
        full_name=user.full_name,
        employee_code=user.employee_code,
        department=user.department,
        designation=user.designation,
        avatar_url=user.avatar_url,
        is_active=user.is_active,
        is_verified=user.is_verified,
        region=RegionBasicInfo(
            id=user.region.id,
            name=user.region.name,
            code=user.region.code,
            type=_get_type_value(user.region.type),
        ) if user.region else None,
        roles=[
            RoleBasicInfo(
                id=ur.role.id,
                name=ur.role.name,
                code=ur.role.code,
                level=_get_level_name(ur.role.level),
            )
            for ur in user.user_roles
            if ur.role.is_active
        ],
        created_at=user.created_at,
        updated_at=user.updated_at,
        last_login_at=user.last_login_at,
    )


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permissions("access_control:delete"))]
)
async def delete_user(
    user_id: uuid.UUID,
    db: DB,
    current_user: CurrentUser,
):
    """
    Soft delete a user (deactivate).
    Requires: access_control:delete permission
    """
    import logging

    try:
        # Get user
        stmt = select(User).where(User.id == user_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Cannot delete yourself
        if user.id == current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete your own account"
            )

        # Soft delete - deactivate user
        user.is_active = False
        await db.commit()

        # Audit log (non-blocking - don't fail deletion if audit fails)
        try:
            audit_service = AuditService(db)
            await audit_service.log(
                action="DELETE",
                entity_type="User",
                entity_id=user.id,
                user_id=current_user.id,
                old_values={"is_active": True},
                new_values={"is_active": False}
            )
            await db.commit()
        except Exception as audit_error:
            logging.warning(f"Failed to create audit log for user deletion: {audit_error}")

        return None

    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error deleting user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete user: {str(e)}"
        )


@router.get(
    "/{user_id}/roles",
    dependencies=[Depends(require_permissions("access_control:view"))]
)
async def get_user_roles(
    user_id: uuid.UUID,
    db: DB,
):
    """
    Get all roles assigned to a user.
    Requires: access_control:view permission
    """
    rbac_service = RBACService(db)

    # Check if user exists
    stmt = select(User).where(User.id == user_id)
    user = (await db.execute(stmt)).scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    roles = await rbac_service.get_user_roles(user_id)

    return {
        "user_id": str(user_id),
        "user_name": user.full_name,
        "roles": [
            {
                "id": str(role.id),
                "name": role.name,
                "code": role.code,
                "level": _get_level_name(role.level),
                "department": role.department,
            }
            for role in roles
        ]
    }


@router.put(
    "/{user_id}/roles",
    dependencies=[Depends(require_permissions("access_control:assign"))]
)
async def assign_user_roles(
    request: Request,
    user_id: uuid.UUID,
    data: UserRoleAssignment,
    db: DB,
    current_user: CurrentUser,
    permissions: Permissions,
):
    """
    Assign roles to a user (replaces existing roles).
    Requires: access_control:assign permission
    """
    rbac_service = RBACService(db)
    audit_service = AuditService(db)

    # Check if user exists
    stmt = (
        select(User)
        .options(selectinload(User.user_roles).selectinload(UserRole.role))
        .where(User.id == user_id)
    )
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Check if user can modify this user
    if not permissions.is_super_admin() and not permissions.can_manage_user(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot assign roles to a user at or above your own level"
        )

    # Validate that user can assign these roles
    for role_id in data.role_ids:
        role = await rbac_service.get_role_by_id(role_id)
        if not role:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Role {role_id} not found"
            )
        if not permissions.can_manage_role(role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Cannot assign role '{role.name}' at or above your own level"
            )

    # Get old roles for audit
    old_role_ids = [ur.role_id for ur in user.user_roles]

    # Assign new roles
    await rbac_service.assign_roles_to_user(
        user_id,
        data.role_ids,
        assigned_by=current_user.id
    )

    # Audit log
    for role_id in data.role_ids:
        if role_id not in old_role_ids:
            role = await rbac_service.get_role_by_id(role_id)
            await audit_service.log_role_assigned(
                user_id=user_id,
                role_id=role_id,
                role_name=role.name,
                assigned_by=current_user.id,
                ip_address=request.client.host if request.client else None,
            )

    for old_role_id in old_role_ids:
        if old_role_id not in data.role_ids:
            role = await rbac_service.get_role_by_id(old_role_id)
            await audit_service.log_role_revoked(
                user_id=user_id,
                role_id=old_role_id,
                role_name=role.name if role else "Unknown",
                revoked_by=current_user.id,
                ip_address=request.client.host if request.client else None,
            )

    await db.commit()

    return {"message": "Roles assigned successfully"}
