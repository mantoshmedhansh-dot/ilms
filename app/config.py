from pydantic_settings import BaseSettings
from pydantic import field_validator
from typing import Optional, Union
from functools import lru_cache
import json
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    DATABASE_URL: str

    # Database Connection Pool Settings
    DB_POOL_SIZE: int = 10  # Base number of connections in pool
    DB_MAX_OVERFLOW: int = 20  # Extra connections allowed beyond pool_size
    DB_POOL_TIMEOUT: int = 30  # Seconds to wait for connection from pool
    DB_POOL_RECYCLE: int = 1800  # Recycle connections after 30 minutes

    # JWT Settings
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # App Settings
    APP_NAME: str = "Consumer Durable Backend"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # CORS - accepts JSON string, comma-separated, or list
    # Reads from CORS_ORIGINS or ALLOWED_ORIGINS env var
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://localhost:5173",
        "https://frontend-ilms.vercel.app",
        "https://frontend-git-main-ilms.vercel.app",
        "*",  # Allow all in production (can be restricted via env var)
    ]

    # Email/SMTP Settings (Gmail)
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""  # Your Gmail address
    SMTP_PASSWORD: str = ""  # Gmail App Password
    SMTP_FROM_EMAIL: str = ""  # Sender email (defaults to SMTP_USER)
    SMTP_FROM_NAME: str = "Aquapurite ERP"

    # Frontend URL for email links
    FRONTEND_URL: str = "https://erp-woad-eight.vercel.app"

    # Redis Cache Settings
    REDIS_URL: Optional[str] = None  # e.g., "redis://localhost:6379/0"
    CACHE_ENABLED: bool = True
    SERVICEABILITY_CACHE_TTL: int = 3600  # 1 hour for pincode serviceability
    PRODUCT_CACHE_TTL: int = 300  # 5 minutes for product data
    STOCK_CACHE_TTL: int = 30  # 30 seconds for real-time stock (short for accuracy)
    CATEGORY_CACHE_TTL: int = 1800  # 30 minutes for categories
    COMPANY_CACHE_TTL: int = 3600  # 1 hour for company info

    # Razorpay Payment Gateway
    RAZORPAY_KEY_ID: str = ""  # Razorpay Key ID
    RAZORPAY_KEY_SECRET: str = ""  # Razorpay Key Secret
    RAZORPAY_WEBHOOK_SECRET: Optional[str] = None  # For webhook verification

    # SMS Gateway (MSG91)
    MSG91_AUTH_KEY: str = ""  # MSG91 Auth Key
    MSG91_SENDER_ID: str = "AQUAPU"  # 6-char sender ID
    MSG91_TEMPLATE_ID_ORDER_CONFIRMED: str = ""  # DLT Template ID for order confirmation
    MSG91_TEMPLATE_ID_ORDER_SHIPPED: str = ""  # DLT Template ID for order shipped
    MSG91_TEMPLATE_ID_OTP: str = ""  # DLT Template ID for OTP

    # D2C Storefront URLs
    D2C_FRONTEND_URL: str = "https://www.aquapurite.com"

    # Shiprocket Integration
    SHIPROCKET_EMAIL: str = ""  # Shiprocket account email
    SHIPROCKET_PASSWORD: str = ""  # Shiprocket account password
    SHIPROCKET_API_URL: str = "https://apiv2.shiprocket.in/v1/external"
    SHIPROCKET_WEBHOOK_SECRET: Optional[str] = None  # For webhook verification
    SHIPROCKET_DEFAULT_PICKUP_LOCATION: str = ""  # Default pickup location name
    SHIPROCKET_AUTO_SHIP: bool = False  # Auto-assign courier on order creation

    # Supabase Storage Settings
    SUPABASE_URL: str = ""  # e.g., "https://xxxx.supabase.co"
    SUPABASE_SERVICE_KEY: str = ""  # Service role key (NOT anon key)
    SUPABASE_STORAGE_BUCKET: str = "uploads"  # Default bucket name

    # Channel Inventory Settings
    CHANNEL_INVENTORY_ENABLED: bool = True  # Enable channel-specific inventory for D2C
    CHANNEL_INVENTORY_STRICT_MODE: bool = False  # If True, allocation fails if channel inventory consumption fails
    D2C_CHANNEL_CODE: str = "D2C-002"  # Code for D2C channel (matches production: Aquapurite.com)
    D2C_FALLBACK_STRATEGY: str = "AUTO_REPLENISH"  # Options: NO_FALLBACK, SHARED_POOL, AUTO_REPLENISH
    MARKETPLACE_FALLBACK_STRATEGY: str = "NO_FALLBACK"  # Marketplaces should not fallback to prevent SLA violations

    # Auto-Replenish Settings
    AUTO_REPLENISH_INTERVAL_MINUTES: int = 15  # How often to run auto-replenish job
    AUTO_REPLENISH_DEFAULT_SAFETY_STOCK: int = 50  # Default safety stock if not configured
    AUTO_REPLENISH_DEFAULT_REORDER_POINT: int = 10  # Default reorder point if not configured

    # Marketplace Sync Settings
    MARKETPLACE_SYNC_INTERVAL_MINUTES: int = 30  # How often to sync to marketplaces
    MARKETPLACE_SYNC_BATCH_SIZE: int = 100  # Number of items to sync per batch

    # Google Maps / Places API (for address autocomplete)
    GOOGLE_MAPS_API_KEY: str = ""  # Google Maps API key with Places API enabled
    GOOGLE_PLACES_COUNTRY_RESTRICTION: str = "in"  # Restrict to India

    # DigiPin Settings (India's Digital Address System)
    DIGIPIN_API_URL: str = "https://digipin.gov.in/api"  # DigiPin API base URL
    DIGIPIN_API_KEY: str = ""  # DigiPin API key (if required)

    # Cloudflare Turnstile CAPTCHA Settings
    TURNSTILE_SECRET_KEY: str = ""  # Cloudflare Turnstile secret key for server verification
    TURNSTILE_ENABLED: bool = True  # Set to False to disable CAPTCHA verification

    @field_validator('CORS_ORIGINS', mode='before')
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return [origin.strip() for origin in v.split(',')]
        return v

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
