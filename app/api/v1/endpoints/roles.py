from typing import Optional
import uuid
import logging
from math import ceil

from fastapi import APIRouter, HTTPException, status, Query, Depends, Request

from app.api.deps import DB, CurrentUser, Permissions, require_permissions

logger = logging.getLogger(__name__)
from app.core.permissions import get_level_value
from app.schemas.role import (
    RoleCreate,
    RoleUpdate,
    RoleResponse,
    RoleListResponse,
    RoleWithPermissions,
    PermissionBasicInfo,
)
from app.schemas.permission import RolePermissionUpdate
from app.services.rbac_service import RBACService
from app.services.audit_service import AuditService


router = APIRouter(tags=["Roles"])


@router.get(
    "",
    response_model=RoleListResponse,
    dependencies=[Depends(require_permissions("access_control:view"))]
)
async def list_roles(
    db: DB,
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(20, ge=1, le=100, description="Page size"),
    include_inactive: bool = Query(False, description="Include inactive roles"),
):
    """
    Get paginated list of roles.
    Requires: access_control:view permission
    """
    rbac_service = RBACService(db)
    skip = (page - 1) * size

    roles, total = await rbac_service.get_roles(
        skip=skip,
        limit=size,
        include_inactive=include_inactive
    )

    return RoleListResponse(
        items=[RoleResponse.model_validate(role) for role in roles],
        total=total,
        page=page,
        size=size,
        pages=ceil(total / size) if total > 0 else 1,
    )


@router.get(
    "/{role_id}",
    response_model=RoleWithPermissions,
    dependencies=[Depends(require_permissions("access_control:view"))]
)
async def get_role(
    role_id: uuid.UUID,
    db: DB,
):
    """
    Get a role by ID with its permissions.
    Requires: access_control:view permission
    """
    try:
        rbac_service = RBACService(db)

        role = await rbac_service.get_role_by_id(role_id, include_permissions=True)
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Role not found"
            )

        # Build response with permissions (with null safety)
        permissions = []
        for rp in role.role_permissions:
            # Skip if permission is None (orphaned record) or inactive
            if rp.permission is None or not rp.permission.is_active:
                continue
            permissions.append(
                PermissionBasicInfo(
                    id=rp.permission.id,
                    name=rp.permission.name,
                    code=rp.permission.code,
                    action=rp.permission.action,
                    module_name=rp.permission.module.name if rp.permission.module else None
                )
            )

        return RoleWithPermissions(
            id=role.id,
            name=role.name,
            code=role.code,
            description=role.description,
            level=role.level,
            department=role.department,
            is_system=role.is_system,
            is_active=role.is_active,
            created_at=role.created_at,
            updated_at=role.updated_at,
            permissions=permissions,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching role {role_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error fetching role: {str(e)}"
        )


@router.post(
    "",
    response_model=RoleResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permissions("access_control:create"))]
)
async def create_role(
    request: Request,
    data: RoleCreate,
    db: DB,
    current_user: CurrentUser,
    permissions: Permissions,
):
    """
    Create a new role.
    Requires: access_control:create permission
    """
    rbac_service = RBACService(db)
    audit_service = AuditService(db)

    # Check if role code already exists
    existing = await rbac_service.get_role_by_code(data.code)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Role with code '{data.code}' already exists"
        )

    # Check if user can create roles at this level
    if not permissions.is_super_admin():
        # Users can only create roles below their own level
        # Lower level value = higher authority (SUPER_ADMIN=0)
        if get_level_value(data.level.value) <= get_level_value(permissions.highest_role_level):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot create a role at or above your own level"
            )

    role = await rbac_service.create_role(data, created_by=current_user.id)

    # Audit log
    await audit_service.log_role_created(
        role_id=role.id,
        role_data={
            "name": role.name,
            "code": role.code,
            "level": role.level,  # Already a string (VARCHAR)
            "department": role.department,
        },
        user_id=current_user.id,
        ip_address=request.client.host if request.client else None,
    )
    await db.commit()

    return RoleResponse.model_validate(role)


@router.put(
    "/{role_id}",
    response_model=RoleResponse,
    dependencies=[Depends(require_permissions("access_control:update"))]
)
async def update_role(
    request: Request,
    role_id: uuid.UUID,
    data: RoleUpdate,
    db: DB,
    current_user: CurrentUser,
    permissions: Permissions,
):
    """
    Update a role.
    Requires: access_control:update permission
    """
    try:
        rbac_service = RBACService(db)
        audit_service = AuditService(db)

        role = await rbac_service.get_role_by_id(role_id)
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Role not found"
            )

        # Check if user can modify this role
        if not permissions.can_manage_role(role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot modify a role at or above your own level"
            )

        old_data = {
            "name": role.name,
            "description": role.description,
            "level": role.level,
            "department": role.department,
            "is_active": role.is_active,
        }

        # Update the role (this commits internally)
        updated_role = await rbac_service.update_role(role_id, data)

        # Audit log - create in same transaction
        new_data = {k: v for k, v in data.model_dump(exclude_unset=True).items()}
        await audit_service.log_role_updated(
            role_id=role_id,
            old_data=old_data,
            new_data=new_data,
            user_id=current_user.id,
            ip_address=request.client.host if request.client else None,
        )
        await db.commit()

        # Get permission count separately
        from sqlalchemy import select, func
        from app.models.permission import RolePermission
        count_result = await db.execute(
            select(func.count(RolePermission.permission_id))
            .where(RolePermission.role_id == role_id)
        )
        permission_count = count_result.scalar() or 0

        # Build response manually to avoid serialization issues
        return RoleResponse(
            id=updated_role.id,
            name=updated_role.name,
            code=updated_role.code,
            description=updated_role.description,
            level=updated_role.level,
            department=updated_role.department,
            is_system=updated_role.is_system,
            is_active=updated_role.is_active,
            permission_count=permission_count,
            created_at=updated_role.created_at,
            updated_at=updated_role.updated_at,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating role {role_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating role: {str(e)}"
        )


@router.delete(
    "/{role_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permissions("access_control:delete"))]
)
async def delete_role(
    request: Request,
    role_id: uuid.UUID,
    db: DB,
    current_user: CurrentUser,
    permissions: Permissions,
):
    """
    Delete (deactivate) a role.
    System roles cannot be deleted.
    Requires: access_control:delete permission
    """
    rbac_service = RBACService(db)
    audit_service = AuditService(db)

    role = await rbac_service.get_role_by_id(role_id)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )

    if role.is_system:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="System roles cannot be deleted"
        )

    # Check if user can delete this role
    if not permissions.can_manage_role(role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete a role at or above your own level"
        )

    success = await rbac_service.delete_role(role_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to delete role"
        )

    # Audit log
    await audit_service.log_role_deleted(
        role_id=role_id,
        role_data={
            "name": role.name,
            "code": role.code,
            "level": role.level,  # Already a string (VARCHAR)
        },
        user_id=current_user.id,
        ip_address=request.client.host if request.client else None,
    )
    await db.commit()


@router.get(
    "/{role_id}/permissions",
    dependencies=[Depends(require_permissions("access_control:view"))]
)
async def get_role_permissions(
    role_id: uuid.UUID,
    db: DB,
):
    """
    Get all permissions assigned to a role.
    Requires: access_control:view permission
    """
    rbac_service = RBACService(db)

    role = await rbac_service.get_role_by_id(role_id)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )

    permissions = await rbac_service.get_role_permissions(role_id)

    return {
        "role_id": str(role_id),
        "role_name": role.name,
        "permissions": [
            {
                "id": str(p.id),
                "name": p.name,
                "code": p.code,
                "action": p.action,
                "module": {
                    "id": str(p.module.id),
                    "name": p.module.name,
                    "code": p.module.code,
                } if p.module else None,
            }
            for p in permissions
        ]
    }


@router.put(
    "/{role_id}/permissions",
    dependencies=[Depends(require_permissions("access_control:update"))]
)
async def update_role_permissions(
    request: Request,
    role_id: uuid.UUID,
    data: RolePermissionUpdate,
    db: DB,
    current_user: CurrentUser,
    permissions: Permissions,
):
    """
    Update all permissions for a role (replaces existing).
    Requires: access_control:update permission
    """
    rbac_service = RBACService(db)
    audit_service = AuditService(db)

    role = await rbac_service.get_role_by_id(role_id)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Role not found"
        )

    # Check if user can modify this role
    if not permissions.can_manage_role(role):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot modify permissions for a role at or above your own level"
        )

    await rbac_service.update_role_permissions(
        role_id,
        data.permission_ids
    )

    # Audit log
    await audit_service.log_permission_granted(
        role_id=role_id,
        permission_ids=data.permission_ids,
        granted_by=current_user.id,
        ip_address=request.client.host if request.client else None,
    )
    await db.commit()

    return {"message": "Permissions updated successfully"}
