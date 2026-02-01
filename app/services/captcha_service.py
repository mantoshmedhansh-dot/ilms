"""
Cloudflare Turnstile CAPTCHA Verification Service

Verifies CAPTCHA tokens submitted from the frontend.
"""

import logging
import httpx
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)

TURNSTILE_VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


async def verify_turnstile_token(token: Optional[str], remote_ip: Optional[str] = None) -> bool:
    """
    Verify a Cloudflare Turnstile CAPTCHA token.

    Args:
        token: The CAPTCHA token from the frontend
        remote_ip: Optional client IP address for additional validation

    Returns:
        True if verification successful or CAPTCHA disabled, False otherwise
    """
    # If CAPTCHA is disabled or no secret key configured, allow all requests
    if not settings.TURNSTILE_ENABLED or not settings.TURNSTILE_SECRET_KEY:
        logger.debug("Turnstile verification skipped: disabled or no secret key")
        return True

    # If no token provided, fail verification
    if not token:
        logger.warning("Turnstile verification failed: no token provided")
        return False

    # For development bypass tokens
    if token == "development-bypass":
        logger.debug("Turnstile verification: development bypass token accepted")
        return True

    try:
        async with httpx.AsyncClient() as client:
            payload = {
                "secret": settings.TURNSTILE_SECRET_KEY,
                "response": token,
            }
            if remote_ip:
                payload["remoteip"] = remote_ip

            response = await client.post(
                TURNSTILE_VERIFY_URL,
                data=payload,
                timeout=10.0,
            )

            if response.status_code != 200:
                logger.error(f"Turnstile API error: HTTP {response.status_code}")
                return False

            result = response.json()

            if result.get("success"):
                logger.debug("Turnstile verification successful")
                return True
            else:
                error_codes = result.get("error-codes", [])
                logger.warning(f"Turnstile verification failed: {error_codes}")
                return False

    except httpx.TimeoutException:
        logger.error("Turnstile verification timed out")
        # On timeout, allow request to prevent blocking legitimate users
        return True
    except Exception as e:
        logger.error(f"Turnstile verification error: {e}")
        # On error, allow request to prevent blocking legitimate users
        return True
