"""Supabase Storage client for file uploads."""
import uuid
from typing import Optional, Tuple, TYPE_CHECKING

from app.config import settings

# Lazy import to avoid crash if supabase not installed
_supabase_client = None
_supabase_available = None

def _check_supabase_available():
    """Check if supabase package is available."""
    global _supabase_available
    if _supabase_available is None:
        try:
            import supabase
            _supabase_available = True
        except ImportError:
            _supabase_available = False
    return _supabase_available


class StorageClient:
    """Client for Supabase Storage operations."""

    _client = None

    @classmethod
    def get_client(cls):
        """Get or create Supabase client."""
        if cls._client is None:
            if not _check_supabase_available():
                raise ImportError(
                    "supabase package not installed. "
                    "Run: pip install supabase"
                )
            if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_KEY:
                raise ValueError(
                    "Supabase credentials not configured. "
                    "Set SUPABASE_URL and SUPABASE_SERVICE_KEY environment variables."
                )
            from supabase import create_client

            # Simple client creation - works with supabase>=2.0.0
            cls._client = create_client(
                settings.SUPABASE_URL,
                settings.SUPABASE_SERVICE_KEY
            )
        return cls._client

    @classmethod
    def get_bucket(cls):
        """Get the storage bucket."""
        client = cls.get_client()
        return client.storage.from_(settings.SUPABASE_STORAGE_BUCKET)

    @classmethod
    def upload(
        cls,
        content: bytes,
        path: str,
        content_type: str
    ) -> str:
        """
        Upload file to Supabase Storage.

        Args:
            content: File content as bytes
            path: Storage path (e.g., "logos/company-logo.png")
            content_type: MIME type (e.g., "image/png")

        Returns:
            Public URL of the uploaded file
        """
        bucket = cls.get_bucket()

        # Upload file (upsert=True to overwrite if exists)
        bucket.upload(
            path=path,
            file=content,
            file_options={"content-type": content_type, "upsert": "true"}
        )

        # Return public URL
        return cls.get_public_url(path)

    @classmethod
    def delete(cls, path: str) -> bool:
        """
        Delete file from Supabase Storage.

        Args:
            path: Storage path or full URL

        Returns:
            True if deleted successfully
        """
        # Extract path from full URL if needed
        if path.startswith("http"):
            path = cls.extract_path_from_url(path)

        if not path:
            return False

        bucket = cls.get_bucket()
        bucket.remove([path])
        return True

    @classmethod
    def get_public_url(cls, path: str) -> str:
        """
        Get public URL for a file.

        Args:
            path: Storage path

        Returns:
            Public URL
        """
        bucket = cls.get_bucket()
        result = bucket.get_public_url(path)
        return result

    @classmethod
    def extract_path_from_url(cls, url: str) -> Optional[str]:
        """
        Extract storage path from a Supabase Storage URL.

        Args:
            url: Full Supabase Storage URL

        Returns:
            Storage path or None if not a valid Supabase URL
        """
        if not url:
            return None

        # URL format: https://xxx.supabase.co/storage/v1/object/public/uploads/path/file.ext
        bucket_name = settings.SUPABASE_STORAGE_BUCKET
        marker = f"/storage/v1/object/public/{bucket_name}/"

        if marker in url:
            return url.split(marker)[1]

        return None

    @classmethod
    def generate_unique_filename(cls, original_filename: str, prefix: str = "") -> str:
        """
        Generate a unique filename to prevent collisions.

        Args:
            original_filename: Original file name
            prefix: Optional prefix for organization (e.g., "logos", "products")

        Returns:
            Unique filename with path
        """
        # Get file extension
        ext = ""
        if "." in original_filename:
            ext = "." + original_filename.rsplit(".", 1)[1].lower()

        # Generate unique ID
        unique_id = uuid.uuid4().hex[:12]

        # Build path
        if prefix:
            return f"{prefix}/{unique_id}{ext}"
        return f"{unique_id}{ext}"


# Convenience function for quick access
def get_storage_client() -> type[StorageClient]:
    """Get the StorageClient class."""
    return StorageClient
