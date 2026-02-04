import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, status, Request
from sqlalchemy import select

from app.api.deps import DB, TenantDB, CurrentUser
from app.schemas.auth import (
    LoginRequest,
    RefreshTokenRequest,
    TokenResponse,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    AdminResetPasswordRequest,
)
from app.services.auth_service import AuthService
from app.services.audit_service import AuditService
from app.models.user import User
from app.core.security import get_password_hash, blacklist_token
from app.services.email_service import get_email_service
from app.config import settings
from app.core.module_decorators import require_module

router = APIRouter(tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
async def login(
    request: Request,
    data: LoginRequest,
    db: TenantDB,
):
    """
    Authenticate user and return access/refresh tokens.
    """
    auth_service = AuthService(db)
    audit_service = AuditService(db)

    user = await auth_service.authenticate_user(data.email, data.password)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token, refresh_token, expires_in = await auth_service.create_tokens(user)

    # Log the login
    await audit_service.log_user_login(
        user_id=user.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    await db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=expires_in,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: Request,
    data: RefreshTokenRequest,
    db: TenantDB,
):
    """
    Refresh access token using a valid refresh token.
    """
    auth_service = AuthService(db)

    result = await auth_service.refresh_tokens(data.refresh_token)

    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token, refresh_token, expires_in = result

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=expires_in,
    )


@router.post("/logout")
@require_module("system_admin")
async def logout(
    request: Request,
    current_user: CurrentUser,
    db: DB,
):
    """
    Logout current user and invalidate the current token.

    Blacklists the current access token so it cannot be reused.
    """
    audit_service = AuditService(db)

    # Get the current token from authorization header
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        # Get tenant_id from request state if available
        tenant_id = getattr(request.state, "tenant_id", None)
        if tenant_id:
            tenant_id = uuid.UUID(tenant_id) if isinstance(tenant_id, str) else tenant_id

        # Blacklist the token
        await blacklist_token(
            db=db,
            token=token,
            user_id=current_user.id,
            tenant_id=tenant_id
        )

    await audit_service.log_user_logout(
        user_id=current_user.id,
        ip_address=request.client.host if request.client else None,
    )
    await db.commit()

    return {"message": "Successfully logged out. Token has been invalidated."}


@router.get("/me")
@require_module("system_admin")
async def get_current_user_info(
    current_user: CurrentUser,
):
    """
    Get current authenticated user's information.
    """
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "first_name": current_user.first_name,
        "last_name": current_user.last_name,
        "full_name": current_user.full_name,
        "phone": current_user.phone,
        "department": current_user.department,
        "designation": current_user.designation,
        "is_active": current_user.is_active,
        "roles": [
            {
                "id": str(role.id),
                "name": role.name,
                "code": role.code,
                "level": role.level,  # Already a string (VARCHAR)
            }
            for role in current_user.roles
        ],
        "region": {
            "id": str(current_user.region.id),
            "name": current_user.region.name,
            "code": current_user.region.code,
            "type": current_user.region.type,  # Already a string (VARCHAR)
        } if current_user.region else None,
    }


# Store reset tokens in memory (for production, use Redis or database)
password_reset_tokens: dict = {}


@router.post("/forgot-password")
async def forgot_password(
    request: Request,
    data: ForgotPasswordRequest,
    db: TenantDB,
):
    """
    Request a password reset. Generates a reset token and sends email.
    """
    # Find user by email
    stmt = select(User).where(User.email == data.email.lower())
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    # Always return success to prevent email enumeration
    if not user:
        return {
            "message": "If this email exists, a password reset link has been sent.",
            "email_sent": False
        }

    # Generate reset token
    reset_token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=1)

    # Store token (in production, store in database or Redis)
    password_reset_tokens[reset_token] = {
        "user_id": str(user.id),
        "email": user.email,
        "expires_at": expires_at
    }

    # Build reset URL
    frontend_url = getattr(settings, 'FRONTEND_URL', 'https://erp-five-phi.vercel.app')
    reset_url = f"{frontend_url}/reset-password?token={reset_token}"

    # Try to send email
    email_service = get_email_service()
    user_name = user.first_name or user.email.split('@')[0]
    email_sent = email_service.send_password_reset_email(
        to_email=user.email,
        reset_token=reset_token,
        reset_url=reset_url,
        user_name=user_name
    )

    # Return response
    if email_sent:
        return {
            "message": "Password reset link has been sent to your email.",
            "email_sent": True
        }
    else:
        # If email fails, return token directly (for development/testing)
        return {
            "message": "Email service not configured. Use the token below to reset your password.",
            "email_sent": False,
            "token": reset_token,
            "reset_url": reset_url
        }


@router.post("/reset-password")
async def reset_password(
    request: Request,
    data: ResetPasswordRequest,
    db: TenantDB,
):
    """
    Reset password using a valid reset token.
    """
    # Validate token
    token_data = password_reset_tokens.get(data.token)

    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )

    if datetime.now(timezone.utc) > token_data["expires_at"]:
        # Remove expired token
        del password_reset_tokens[data.token]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset token has expired"
        )

    # Find user
    stmt = select(User).where(User.email == token_data["email"])
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User not found"
        )

    # Update password
    user.password_hash = get_password_hash(data.new_password)
    await db.commit()

    # Remove used token
    del password_reset_tokens[data.token]

    return {"message": "Password has been reset successfully. You can now login with your new password."}


@router.post("/admin-reset-password")
@require_module("system_admin")
async def admin_reset_password(
    data: AdminResetPasswordRequest,
    db: DB,
    current_user: CurrentUser,
):
    """
    Reset a user's password (Super Admin only).
    """
    import uuid as uuid_module

    # Check if current user is super admin
    is_super_admin = any(role.code == "SUPER_ADMIN" for role in current_user.roles)
    if not is_super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Super Admin can reset user passwords"
        )

    # Validate user_id
    try:
        user_uuid = uuid_module.UUID(data.user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID"
        )

    # Find user
    stmt = select(User).where(User.id == user_uuid)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Cannot reset own password through this endpoint
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Use the regular password change feature for your own account"
        )

    # Update password
    user.password_hash = get_password_hash(data.new_password)
    await db.commit()

    return {"message": f"Password for {user.email} has been reset successfully."}
