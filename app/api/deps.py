from typing import Annotated, Optional, Set
import uuid
import logging

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db, get_db_with_tenant
from app.core.security import verify_access_token
from app.core.permissions import PermissionChecker
from app.models.user import User, UserRole
from app.models.role import Role, RoleLevel
from app.models.permission import Permission, RolePermission


logger = logging.getLogger(__name__)

# HTTP Bearer security scheme
security = HTTPBearer()


async def get_current_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
) -> User:
    """
    Dependency to get the current authenticated user.
    Validates the JWT token and returns the user object.

    IMPORTANT: Uses tenant schema (via request.state.schema) to query users,
    since users are stored per-tenant, not in public schema.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token = credentials.credentials
    user_id = verify_access_token(token)

    if user_id is None:
        logger.warning("Token verification failed - invalid or expired token")
        raise credentials_exception

    try:
        user_uuid = uuid.UUID(user_id)
    except ValueError:
        logger.warning(f"Invalid user_id in token: {user_id}")
        raise credentials_exception

    # Get tenant database session - users are in tenant schema, not public!
    async for db in get_db_with_tenant(request):
        # Query user with roles eagerly loaded
        stmt = (
            select(User)
            .options(
                joinedload(User.user_roles).joinedload(UserRole.role),
                joinedload(User.region)
            )
            .where(User.id == user_uuid)
        )
        result = await db.execute(stmt)
        user = result.unique().scalar_one_or_none()

        if user is None:
            schema = getattr(request.state, 'schema', 'unknown')
            logger.warning(f"User {user_id} not found in schema {schema}")
            raise credentials_exception

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is deactivated"
            )

        return user

    # Should not reach here
    raise credentials_exception


async def get_user_permissions(
    request: Request,
    user: Annotated[User, Depends(get_current_user)],
) -> Set[str]:
    """
    Get all permission codes for the current user.
    Aggregates permissions from all user's roles.

    Uses tenant schema since permissions/roles are per-tenant.
    """
    # SUPER_ADMIN has all permissions
    for role in user.roles:
        if role.level == RoleLevel.SUPER_ADMIN.name:
            # Return empty set - PermissionChecker will handle SUPER_ADMIN
            return set()

    # Get all role IDs
    role_ids = [role.id for role in user.roles]

    if not role_ids:
        return set()

    # Get tenant database session
    async for db in get_db_with_tenant(request):
        # Query all permissions for user's roles
        stmt = (
            select(Permission.code)
            .join(RolePermission, Permission.id == RolePermission.permission_id)
            .where(RolePermission.role_id.in_(role_ids))
            .where(Permission.is_active == True)
        )
        result = await db.execute(stmt)
        permission_codes = {row[0] for row in result.all()}
        return permission_codes

    return set()


async def get_permission_checker(
    user: Annotated[User, Depends(get_current_user)],
    permissions: Annotated[Set[str], Depends(get_user_permissions)]
) -> PermissionChecker:
    """
    Get a PermissionChecker instance for the current user.
    """
    return PermissionChecker(user, permissions)


def require_permissions(*required_permissions: str):
    """
    Dependency factory to require specific permissions.

    Usage:
        @router.get("/", dependencies=[Depends(require_permissions("products:view"))])
        async def list_products():
            ...
    """
    async def permission_dependency(
        permission_checker: Annotated[PermissionChecker, Depends(get_permission_checker)]
    ):
        for permission in required_permissions:
            if not permission_checker.has_permission(permission):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission denied. Required: {permission}"
                )
        return True

    return permission_dependency


def require_any_permission(*required_permissions: str):
    """
    Dependency factory to require any of the specified permissions.
    """
    async def permission_dependency(
        permission_checker: Annotated[PermissionChecker, Depends(get_permission_checker)]
    ):
        if not permission_checker.has_any_permission(list(required_permissions)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied. Required any of: {required_permissions}"
            )
        return True

    return permission_dependency


def require_role_level(level: RoleLevel):
    """
    Dependency factory to require a minimum role level.

    Usage:
        @router.get("/", dependencies=[Depends(require_role_level(RoleLevel.MANAGER))])
        async def manager_endpoint():
            ...
    """
    async def role_level_dependency(
        permission_checker: Annotated[PermissionChecker, Depends(get_permission_checker)]
    ):
        if not permission_checker.has_role_level(level):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient role level. Required: {level.name} or higher"
            )
        return True

    return role_level_dependency


# Type aliases for cleaner endpoint signatures
CurrentUser = Annotated[User, Depends(get_current_user)]
DB = Annotated[AsyncSession, Depends(get_db)]  # Public schema (for tenant management)
TenantDB = Annotated[AsyncSession, Depends(get_db_with_tenant)]  # Tenant schema (for user data)
Permissions = Annotated[PermissionChecker, Depends(get_permission_checker)]
