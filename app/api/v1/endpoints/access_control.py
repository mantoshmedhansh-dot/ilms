from typing import Optional
import uuid

from fastapi import APIRouter, Depends, Query

from app.api.deps import DB, CurrentUser, Permissions
from app.schemas.module import (
    ModuleResponse,
    ModuleListResponse,
    PermissionCheckRequest,
    PermissionCheckResponse,
    MultiplePermissionCheckResponse,
)
from app.services.rbac_service import RBACService
from app.core.module_decorators import require_module

router = APIRouter(prefix="/access", tags=["Access Control"])


@router.post("/check", response_model=PermissionCheckResponse)
@require_module("system_admin")
async def check_permission(
    data: PermissionCheckRequest,
    current_user: CurrentUser,
    permission_checker: Permissions,
):
    """
    Check if the current user has a specific permission.
    This endpoint is useful for frontend permission checks.
    """
    has_permission = permission_checker.has_permission(data.permission_code)

    return PermissionCheckResponse(
        user_id=str(current_user.id),
        permission_code=data.permission_code,
        has_permission=has_permission,
        is_super_admin=permission_checker.is_super_admin(),
    )


@router.post("/check-multiple", response_model=MultiplePermissionCheckResponse)
@require_module("system_admin")
async def check_multiple_permissions(
    permission_codes: list[str],
    current_user: CurrentUser,
    permission_checker: Permissions,
):
    """
    Check multiple permissions at once.
    Returns a dict mapping permission codes to boolean values.
    """
    results = {}
    for code in permission_codes:
        results[code] = permission_checker.has_permission(code)

    return MultiplePermissionCheckResponse(
        user_id=str(current_user.id),
        is_super_admin=permission_checker.is_super_admin(),
        permissions=results,
    )


@router.get("/modules", response_model=ModuleListResponse)
@require_module("system_admin")
async def list_modules(
    db: DB,
    current_user: CurrentUser,
):
    """
    Get all available modules.
    Used for building navigation and permission assignment UI.
    """
    rbac_service = RBACService(db)
    modules = await rbac_service.get_modules()

    return ModuleListResponse(
        items=[ModuleResponse.model_validate(m) for m in modules],
        total=len(modules)
    )


@router.get("/user-access-summary")
@require_module("system_admin")
async def get_user_access_summary(
    db: DB,
    current_user: CurrentUser,
    permission_checker: Permissions,
):
    """
    Get a summary of current user's access.
    Includes roles, permissions grouped by module, and region info.
    """
    rbac_service = RBACService(db)

    # Get permission codes
    if permission_checker.is_super_admin():
        all_permissions = await rbac_service.get_permissions()
        permission_codes = [p.code for p in all_permissions]
    else:
        permission_codes = list(await rbac_service.get_user_permission_codes(current_user.id))

    # Group permissions by module
    # Handle both formats: "module:action" (legacy) and "MODULE_ACTION" (current)
    permissions_by_module = {}
    for code in permission_codes:
        if ":" in code:
            # Legacy format: "module:action"
            parts = code.split(":")
            if len(parts) == 2:
                module = parts[0]
                action = parts[1]
        elif "_" in code:
            # Current format: "MODULE_ACTION" (e.g., ORDERS_VIEW)
            # Split from the last underscore to handle codes like "ROLE_MGMT_VIEW"
            last_underscore = code.rfind("_")
            if last_underscore > 0:
                module = code[:last_underscore]
                action = code[last_underscore + 1:].lower()
            else:
                continue
        else:
            continue

        if module not in permissions_by_module:
            permissions_by_module[module] = []
        permissions_by_module[module].append(action)

    return {
        "user": {
            "id": str(current_user.id),
            "email": current_user.email,
            "name": current_user.full_name,
        },
        "is_super_admin": permission_checker.is_super_admin(),
        "roles": [
            {
                "id": str(role.id),
                "name": role.name,
                "code": role.code,
                "level": role.level,  # Already a string (VARCHAR)
                "department": role.department,
            }
            for role in current_user.roles
        ],
        "region": {
            "id": str(current_user.region.id),
            "name": current_user.region.name,
            "code": current_user.region.code,
            "type": current_user.region.type,  # Already a string (VARCHAR)
        } if current_user.region else None,
        "permissions_by_module": permissions_by_module,
        "total_permissions": len(permission_codes),
    }
