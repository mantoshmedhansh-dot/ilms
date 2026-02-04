from datetime import datetime, timedelta, timezone
from typing import Optional, Any, Tuple
import uuid

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings


# Password hashing context with multi-algorithm support
# - bcrypt is now default (faster, widely supported, still secure)
# - argon2 supported for new high-security requirements
pwd_context = CryptContext(
    schemes=["bcrypt", "argon2"],
    default="bcrypt",
    deprecated=[],
    # Bcrypt settings (secure and fast)
    bcrypt__rounds=12,  # Good balance of security and speed
)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a hashed password.

    Supports both argon2 and bcrypt hashes automatically.
    Uses passlib's CryptContext which detects the algorithm from the hash format.
    """
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    """
    Hash a password using argon2 (preferred algorithm).

    Returns an argon2id hash which is:
    - Winner of Password Hashing Competition (2015)
    - Resistant to GPU cracking attacks
    - Memory-hard (prevents ASIC attacks)
    """
    return pwd_context.hash(password)


def verify_and_check_needs_rehash(plain_password: str, hashed_password: str) -> Tuple[bool, bool]:
    """
    Verify password and check if the hash needs to be upgraded.

    Returns:
        Tuple of (is_valid, needs_rehash)
        - is_valid: True if password matches
        - needs_rehash: True if password should be re-hashed (e.g., using old bcrypt)

    Usage in login flow:
        is_valid, needs_rehash = verify_and_check_needs_rehash(password, user.hashed_password)
        if is_valid:
            if needs_rehash:
                user.hashed_password = get_password_hash(password)
                await db.commit()
            return user
    """
    try:
        is_valid = pwd_context.verify(plain_password, hashed_password)
        if is_valid:
            needs_rehash = pwd_context.needs_update(hashed_password)
            return (True, needs_rehash)
        return (False, False)
    except Exception:
        return (False, False)


def create_access_token(
    subject: str | uuid.UUID,
    expires_delta: Optional[timedelta] = None,
    additional_claims: Optional[dict[str, Any]] = None
) -> str:
    """
    Create a JWT access token.

    Args:
        subject: The subject of the token (usually user ID)
        expires_delta: Optional custom expiration time
        additional_claims: Optional additional claims to include

    Returns:
        Encoded JWT token string
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    jti = str(uuid.uuid4())  # Unique token ID for blacklisting

    to_encode = {
        "sub": str(subject),
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "jti": jti,
        "type": "access"
    }

    if additional_claims:
        to_encode.update(additional_claims)

    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def create_refresh_token(
    subject: str | uuid.UUID,
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT refresh token.

    Args:
        subject: The subject of the token (usually user ID)
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT refresh token string
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    jti = str(uuid.uuid4())  # Unique token ID for blacklisting

    to_encode = {
        "sub": str(subject),
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "jti": jti,
        "type": "refresh"
    }

    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def decode_token(token: str) -> Optional[dict[str, Any]]:
    """
    Decode and validate a JWT token.

    Args:
        token: The JWT token to decode

    Returns:
        Decoded token payload or None if invalid
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError:
        return None


def verify_access_token(token: str) -> Optional[str]:
    """
    Verify an access token and return the subject (user ID).

    Args:
        token: The JWT access token

    Returns:
        User ID string or None if invalid
    """
    payload = decode_token(token)
    if payload is None:
        return None

    if payload.get("type") != "access":
        return None

    return payload.get("sub")


def verify_refresh_token(token: str) -> Optional[str]:
    """
    Verify a refresh token and return the subject (user ID).

    Args:
        token: The JWT refresh token

    Returns:
        User ID string or None if invalid
    """
    payload = decode_token(token)
    if payload is None:
        return None

    if payload.get("type") != "refresh":
        return None

    return payload.get("sub")


async def blacklist_token(
    db,
    token: str,
    user_id: uuid.UUID,
    tenant_id: Optional[uuid.UUID] = None
) -> bool:
    """
    Add a token to the blacklist.

    Args:
        db: Database session (public schema)
        token: The JWT token to blacklist
        user_id: User ID who owns the token
        tenant_id: Tenant ID (optional)

    Returns:
        True if token was blacklisted successfully
    """
    from app.models.tenant import TokenBlacklist

    payload = decode_token(token)
    if payload is None:
        return False

    jti = payload.get("jti")
    if not jti:
        return False  # Token doesn't have JTI, can't blacklist

    token_type = payload.get("type", "access")
    exp = payload.get("exp")

    if exp:
        expires_at = datetime.fromtimestamp(exp, tz=timezone.utc)
    else:
        expires_at = datetime.now(timezone.utc) + timedelta(days=7)

    blacklist_entry = TokenBlacklist(
        jti=jti,
        token_type=token_type,
        user_id=user_id,
        tenant_id=tenant_id,
        expires_at=expires_at
    )

    db.add(blacklist_entry)
    return True


async def is_token_blacklisted(db, token: str) -> bool:
    """
    Check if a token is blacklisted.

    Args:
        db: Database session (public schema)
        token: The JWT token to check

    Returns:
        True if token is blacklisted, False otherwise
    """
    from sqlalchemy import select
    from app.models.tenant import TokenBlacklist

    payload = decode_token(token)
    if payload is None:
        return True  # Invalid token, treat as blacklisted

    jti = payload.get("jti")
    if not jti:
        return False  # Old tokens without JTI, allow them

    stmt = select(TokenBlacklist).where(TokenBlacklist.jti == jti)
    result = await db.execute(stmt)
    blacklisted = result.scalar_one_or_none()

    return blacklisted is not None


async def cleanup_expired_blacklist_entries(db) -> int:
    """
    Remove expired tokens from the blacklist.

    Call this periodically (e.g., daily via cron job).

    Args:
        db: Database session (public schema)

    Returns:
        Number of entries removed
    """
    from sqlalchemy import delete
    from app.models.tenant import TokenBlacklist

    stmt = delete(TokenBlacklist).where(
        TokenBlacklist.expires_at < datetime.now(timezone.utc)
    )
    result = await db.execute(stmt)
    await db.commit()

    return result.rowcount
