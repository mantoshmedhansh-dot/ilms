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

    to_encode = {
        "sub": str(subject),
        "exp": expire,
        "iat": datetime.now(timezone.utc),
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

    to_encode = {
        "sub": str(subject),
        "exp": expire,
        "iat": datetime.now(timezone.utc),
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
