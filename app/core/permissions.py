from typing import List, Set, Optional
from functools import wraps
import uuid

from fastapi import HTTPException, status

from app.models.role import Role, RoleLevel
from app.models.user import User


# Map level names to hierarchy values using RoleLevel enum for type safety
# Lower value = higher authority (SUPER_ADMIN=0 is highest)
LEVEL_ORDER = {
    RoleLevel.SUPER_ADMIN.name: RoleLevel.SUPER_ADMIN.value,
    RoleLevel.DIRECTOR.name: RoleLevel.DIRECTOR.value,
    RoleLevel.HEAD.name: RoleLevel.HEAD.value,
    RoleLevel.MANAGER.name: RoleLevel.MANAGER.value,
    RoleLevel.EXECUTIVE.name: RoleLevel.EXECUTIVE.value,
}


def get_level_value(level: str) -> int:
    """Convert string level to numeric value for comparison.

    Uses RoleLevel enum values for consistency.
    Returns EXECUTIVE level (4) as default for unknown levels.
    """
    return LEVEL_ORDER.get(str(level), RoleLevel.EXECUTIVE.value)


class PermissionChecker:
    """
    Permission checker utility for RBAC.
    Supports hierarchical permission inheritance.
    """

    def __init__(self, user: User, user_permissions: Set[str]):
        """
        Initialize permission checker.

        Args:
            user: The user object
            user_permissions: Set of permission codes the user has
        """
        self.user = user
        self.permissions = user_permissions
        self.roles = user.roles
        self.highest_role_level = self._get_highest_role_level()

    def _get_highest_role_level(self) -> Optional[str]:
        """Get the highest (lowest number) role level for the user as string."""
        if not self.roles:
            return None

        # Find role with lowest level value (highest authority)
        return min((role.level for role in self.roles), key=get_level_value)

    def is_super_admin(self) -> bool:
        """Check if user is a SUPER_ADMIN."""
        return self.highest_role_level == RoleLevel.SUPER_ADMIN.name

    def has_permission(self, permission_code: str) -> bool:
        """
        Check if user has a specific permission.
        SUPER_ADMIN automatically has all permissions.

        Args:
            permission_code: The permission code to check (e.g., 'products:view')

        Returns:
            True if user has the permission
        """
        if self.is_super_admin():
            return True

        return permission_code in self.permissions

    def has_any_permission(self, permission_codes: List[str]) -> bool:
        """
        Check if user has any of the specified permissions.

        Args:
            permission_codes: List of permission codes

        Returns:
            True if user has at least one permission
        """
        if self.is_super_admin():
            return True

        return bool(self.permissions & set(permission_codes))

    def has_all_permissions(self, permission_codes: List[str]) -> bool:
        """
        Check if user has all of the specified permissions.

        Args:
            permission_codes: List of permission codes

        Returns:
            True if user has all permissions
        """
        if self.is_super_admin():
            return True

        return set(permission_codes).issubset(self.permissions)

    def has_role(self, role_code: str) -> bool:
        """
        Check if user has a specific role.

        Args:
            role_code: The role code to check

        Returns:
            True if user has the role
        """
        return any(role.code == role_code for role in self.roles)

    def has_role_level(self, level: RoleLevel) -> bool:
        """
        Check if user has a role at or above the specified level.

        Args:
            level: The minimum role level required (RoleLevel enum)

        Returns:
            True if user has sufficient role level
        """
        if self.highest_role_level is None:
            return False

        # Compare using level order values (lower = higher authority)
        user_level_value = get_level_value(self.highest_role_level)
        required_level_value = level.value  # RoleLevel is IntEnum
        return user_level_value <= required_level_value

    def can_manage_role(self, target_role: Role) -> bool:
        """
        Check if user can manage (assign/revoke) a specific role.
        Users can only manage roles below their own level.

        Args:
            target_role: The role to be managed

        Returns:
            True if user can manage the role
        """
        if self.highest_role_level is None:
            return False

        # SUPER_ADMIN can manage all roles
        if self.is_super_admin():
            return True

        # Can only manage roles below own level (higher value = lower authority)
        return get_level_value(self.highest_role_level) < get_level_value(target_role.level)

    def can_manage_user(self, target_user: User) -> bool:
        """
        Check if user can manage another user.
        Users can only manage users with lower role levels.

        Args:
            target_user: The user to be managed

        Returns:
            True if user can manage the target user
        """
        if self.highest_role_level is None:
            return False

        # SUPER_ADMIN can manage all users
        if self.is_super_admin():
            return True

        # Cannot manage self through this check
        if self.user.id == target_user.id:
            return False

        # Get target user's highest role level
        target_roles = target_user.roles
        if not target_roles:
            return True  # Can manage users without roles

        # Find target's highest level (lowest value = highest authority)
        target_highest_level = min((role.level for role in target_roles), key=get_level_value)

        # Compare using level values (lower value = higher authority)
        return get_level_value(self.highest_role_level) < get_level_value(target_highest_level)


def require_permission(permission_code: str):
    """
    Decorator to require a specific permission for an endpoint.

    Usage:
        @require_permission("products:create")
        async def create_product(...):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get permission_checker from kwargs (injected by dependency)
            permission_checker: PermissionChecker = kwargs.get("permission_checker")
            if not permission_checker:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Permission checker not available"
                )

            if not permission_checker.has_permission(permission_code):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission denied. Required: {permission_code}"
                )

            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_any_permission(permission_codes: List[str]):
    """
    Decorator to require any of the specified permissions.
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            permission_checker: PermissionChecker = kwargs.get("permission_checker")
            if not permission_checker:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Permission checker not available"
                )

            if not permission_checker.has_any_permission(permission_codes):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission denied. Required any of: {permission_codes}"
                )

            return await func(*args, **kwargs)
        return wrapper
    return decorator


def require_role_level(level: RoleLevel):
    """
    Decorator to require a minimum role level.

    Usage:
        @require_role_level(RoleLevel.MANAGER)
        async def manager_endpoint(...):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            permission_checker: PermissionChecker = kwargs.get("permission_checker")
            if not permission_checker:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Permission checker not available"
                )

            if not permission_checker.has_role_level(level):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Insufficient role level. Required: {level.name} or higher"
                )

            return await func(*args, **kwargs)
        return wrapper
    return decorator
