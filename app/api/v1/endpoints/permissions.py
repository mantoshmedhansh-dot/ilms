from typing import Optional, List
import uuid

from fastapi import APIRouter, Query, Depends
from sqlalchemy import select

from app.api.deps import DB, CurrentUser, Permissions, require_permissions
from app.schemas.permission import PermissionListResponse, PermissionResponse, PermissionsByModule
from app.services.rbac_service import RBACService
from app.models.module import Module
from app.core.module_decorators import require_module

router = APIRouter(tags=["Permissions"])


@router.get("/modules", response_model=List[str])
@require_module("system_admin")
async def get_modules(db: DB):
    """
    Get list of all module codes.
    Used for filtering permissions by module.
    """
    result = await db.execute(
        select(Module.code)
        .where(Module.is_active == True)
        .order_by(Module.sort_order, Module.name)
    )
    modules = result.scalars().all()
    return list(modules)


@router.get(
    "",
    response_model=PermissionListResponse,
    dependencies=[Depends(require_permissions("access_control:view"))]
)
async def list_permissions(
    db: DB,
    module_id: Optional[uuid.UUID] = Query(None, description="Filter by module ID"),
):
    """
    Get all permissions, optionally filtered by module.
    Requires: access_control:view permission
    """
    rbac_service = RBACService(db)

    permissions = await rbac_service.get_permissions(module_id=module_id)

    return PermissionListResponse(
        items=[
            PermissionResponse(
                id=p.id,
                name=p.name,
                code=p.code,
                description=p.description,
                action=p.action,
                is_active=p.is_active,
                module={
                    "id": p.module.id,
                    "name": p.module.name,
                    "code": p.module.code,
                } if p.module else None,
                created_at=p.created_at,
                updated_at=p.updated_at,
            )
            for p in permissions
        ],
        total=len(permissions)
    )


@router.get(
    "/by-module",
    response_model=PermissionsByModule,
    dependencies=[Depends(require_permissions("access_control:view"))]
)
async def get_permissions_by_module(
    db: DB,
):
    """
    Get all permissions grouped by module.
    Useful for building permission assignment UI.
    Requires: access_control:view permission
    """
    rbac_service = RBACService(db)
    return await rbac_service.get_permissions_by_module()


@router.get("/my-permissions")
@require_module("system_admin")
async def get_my_permissions(
    db: DB,
    current_user: CurrentUser,
    permission_checker: Permissions,
):
    """
    Get current user's permissions.
    No special permission required - users can always see their own permissions.
    """
    rbac_service = RBACService(db)

    if permission_checker.is_super_admin():
        # SUPER_ADMIN has all permissions
        permissions = await rbac_service.get_permissions()
        return {
            "user_id": str(current_user.id),
            "is_super_admin": True,
            "roles": [
                {
                    "id": str(role.id),
                    "name": role.name,
                    "code": role.code,
                    "level": role.level,  # Already a string (VARCHAR)
                }
                for role in current_user.roles
            ],
            "permissions": [p.code for p in permissions],
            "permissions_detail": [
                {
                    "code": p.code,
                    "name": p.name,
                    "action": p.action,
                    "module": p.module.code if p.module else None,
                }
                for p in permissions
            ],
        }

    # Get user's permissions from their roles
    permission_codes = await rbac_service.get_user_permission_codes(current_user.id)

    return {
        "user_id": str(current_user.id),
        "is_super_admin": False,
        "roles": [
            {
                "id": str(role.id),
                "name": role.name,
                "code": role.code,
                "level": role.level,  # Already a string (VARCHAR)
            }
            for role in current_user.roles
        ],
        "permissions": list(permission_codes),
    }
