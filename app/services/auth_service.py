from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
import uuid

from sqlalchemy import select
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, UserRole
from app.core.security import (
    verify_password,
    verify_and_check_needs_rehash,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    verify_refresh_token,
)
from app.config import settings


class AuthService:
    """Authentication service for user login and token management."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def authenticate_user(
        self,
        email: str,
        password: str
    ) -> Optional[User]:
        """
        Authenticate a user by email and password.

        Supports both argon2 and bcrypt password hashes. If the password
        is verified using a deprecated algorithm (bcrypt), it will be
        automatically migrated to argon2 for improved security.

        Args:
            email: User's email address
            password: Plain text password

        Returns:
            User object if authentication successful, None otherwise
        """
        # Use joinedload instead of selectinload to avoid psycopg3 UUID type casting issues
        stmt = (
            select(User)
            .options(
                joinedload(User.user_roles).joinedload(UserRole.role),
                joinedload(User.region)
            )
            .where(User.email == email.lower())
        )
        result = await self.db.execute(stmt)
        user = result.unique().scalar_one_or_none()  # unique() needed with joinedload

        if user is None:
            return None

        # Verify password and check if hash needs to be upgraded
        is_valid, needs_rehash = verify_and_check_needs_rehash(password, user.password_hash)

        if not is_valid:
            return None

        if not user.is_active:
            return None

        # Transparently migrate old bcrypt hashes to argon2
        if needs_rehash:
            user.password_hash = get_password_hash(password)
            await self.db.commit()

        return user

    async def create_tokens(
        self,
        user: User
    ) -> Tuple[str, str, int]:
        """
        Create access and refresh tokens for a user.

        Args:
            user: The authenticated user

        Returns:
            Tuple of (access_token, refresh_token, expires_in_seconds)
        """
        # Additional claims to include in token
        additional_claims = {
            "email": user.email,
            "roles": [role.code for role in user.roles],
        }

        access_token = create_access_token(
            subject=user.id,
            additional_claims=additional_claims
        )

        refresh_token = create_refresh_token(subject=user.id)

        expires_in = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60

        # Update last login time
        user.last_login_at = datetime.now(timezone.utc)
        await self.db.commit()

        return access_token, refresh_token, expires_in

    async def refresh_tokens(
        self,
        refresh_token: str
    ) -> Optional[Tuple[str, str, int]]:
        """
        Refresh access and refresh tokens using a valid refresh token.

        Args:
            refresh_token: The JWT refresh token

        Returns:
            Tuple of (new_access_token, new_refresh_token, expires_in_seconds)
            or None if token is invalid
        """
        user_id = verify_refresh_token(refresh_token)

        if user_id is None:
            return None

        try:
            user_uuid = uuid.UUID(user_id)
        except ValueError:
            return None

        # Get user - use joinedload instead of selectinload to avoid psycopg3 UUID type casting issues
        stmt = (
            select(User)
            .options(
                joinedload(User.user_roles).joinedload(UserRole.role),
                joinedload(User.region)
            )
            .where(User.id == user_uuid)
        )
        result = await self.db.execute(stmt)
        user = result.unique().scalar_one_or_none()

        if user is None or not user.is_active:
            return None

        return await self.create_tokens(user)

    async def register_user(
        self,
        email: str,
        password: str,
        first_name: str,
        last_name: Optional[str] = None,
        phone: Optional[str] = None,
        **kwargs
    ) -> User:
        """
        Register a new user.

        Args:
            email: User's email address
            password: Plain text password
            first_name: User's first name
            last_name: User's last name (optional)
            phone: User's phone number (optional)
            **kwargs: Additional user fields

        Returns:
            The created User object
        """
        password_hash = get_password_hash(password)

        # Convert empty strings to None for optional fields with unique constraints
        phone = phone if phone else None
        last_name = last_name if last_name else None

        user = User(
            email=email.lower(),
            password_hash=password_hash,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            **kwargs
        )

        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)

        return user

    async def change_password(
        self,
        user: User,
        current_password: str,
        new_password: str
    ) -> bool:
        """
        Change a user's password.

        Args:
            user: The user object
            current_password: Current password for verification
            new_password: New password to set

        Returns:
            True if password changed successfully, False otherwise
        """
        if not verify_password(current_password, user.password_hash):
            return False

        user.password_hash = get_password_hash(new_password)
        await self.db.commit()

        return True

    async def reset_password(
        self,
        user: User,
        new_password: str
    ) -> None:
        """
        Reset a user's password (admin function).

        Args:
            user: The user object
            new_password: New password to set
        """
        user.password_hash = get_password_hash(new_password)
        await self.db.commit()
