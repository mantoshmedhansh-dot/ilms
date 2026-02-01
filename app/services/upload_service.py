"""Upload service for file validation and processing."""
import io
from typing import Optional, Tuple, List

from PIL import Image

from app.core.storage import StorageClient
from app.schemas.upload import UploadCategory


# Allowed MIME types by category
ALLOWED_IMAGE_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/svg+xml": ".svg",
}

ALLOWED_DOCUMENT_TYPES = {
    "application/pdf": ".pdf",
}

# Size limits in bytes
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB
MAX_DOCUMENT_SIZE = 10 * 1024 * 1024  # 10MB

# Thumbnail settings
THUMBNAIL_SIZE = (300, 300)


class UploadError(Exception):
    """Custom exception for upload errors."""
    pass


class UploadService:
    """Service for handling file uploads."""

    @staticmethod
    def validate_image(
        content: bytes,
        content_type: str,
        filename: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate image file.

        Args:
            content: File content as bytes
            content_type: MIME type
            filename: Original filename

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check content type
        if content_type not in ALLOWED_IMAGE_TYPES:
            return False, f"Invalid image type: {content_type}. Allowed: {', '.join(ALLOWED_IMAGE_TYPES.keys())}"

        # Check file size
        if len(content) > MAX_IMAGE_SIZE:
            max_mb = MAX_IMAGE_SIZE / (1024 * 1024)
            actual_mb = len(content) / (1024 * 1024)
            return False, f"Image too large: {actual_mb:.1f}MB. Maximum: {max_mb}MB"

        # For non-SVG images, validate it's a valid image
        if content_type != "image/svg+xml":
            try:
                img = Image.open(io.BytesIO(content))
                img.verify()
            except Exception:
                return False, "Invalid or corrupted image file"

        return True, None

    @staticmethod
    def validate_document(
        content: bytes,
        content_type: str,
        filename: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate document file.

        Args:
            content: File content as bytes
            content_type: MIME type
            filename: Original filename

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check content type
        if content_type not in ALLOWED_DOCUMENT_TYPES:
            return False, f"Invalid document type: {content_type}. Allowed: PDF"

        # Check file size
        if len(content) > MAX_DOCUMENT_SIZE:
            max_mb = MAX_DOCUMENT_SIZE / (1024 * 1024)
            actual_mb = len(content) / (1024 * 1024)
            return False, f"Document too large: {actual_mb:.1f}MB. Maximum: {max_mb}MB"

        # Basic PDF validation (check magic bytes)
        if content_type == "application/pdf" and not content.startswith(b"%PDF"):
            return False, "Invalid PDF file"

        return True, None

    @staticmethod
    def generate_thumbnail(
        content: bytes,
        content_type: str
    ) -> Optional[bytes]:
        """
        Generate thumbnail for image.

        Args:
            content: Original image content
            content_type: MIME type

        Returns:
            Thumbnail content as bytes, or None if not applicable
        """
        # SVG doesn't need thumbnails
        if content_type == "image/svg+xml":
            return None

        try:
            img = Image.open(io.BytesIO(content))

            # Convert to RGB if necessary (for PNG with transparency)
            if img.mode in ("RGBA", "LA", "P"):
                background = Image.new("RGB", img.size, (255, 255, 255))
                if img.mode == "P":
                    img = img.convert("RGBA")
                background.paste(img, mask=img.split()[-1] if img.mode == "RGBA" else None)
                img = background

            # Create thumbnail
            img.thumbnail(THUMBNAIL_SIZE, Image.Resampling.LANCZOS)

            # Save to bytes
            output = io.BytesIO()
            img.save(output, format="JPEG", quality=85, optimize=True)
            return output.getvalue()

        except Exception:
            return None

    @classmethod
    async def upload_image(
        cls,
        content: bytes,
        filename: str,
        content_type: str,
        category: UploadCategory
    ) -> dict:
        """
        Upload image with validation and thumbnail generation.

        Args:
            content: File content
            filename: Original filename
            content_type: MIME type
            category: Upload category

        Returns:
            Dict with url, thumbnail_url, file_name, file_size, content_type
        """
        # Validate
        is_valid, error = cls.validate_image(content, content_type, filename)
        if not is_valid:
            raise UploadError(error)

        # Generate unique path
        path = StorageClient.generate_unique_filename(filename, category.value)

        # Upload main image
        url = StorageClient.upload(content, path, content_type)

        # Generate and upload thumbnail
        thumbnail_url = None
        thumbnail_content = cls.generate_thumbnail(content, content_type)
        if thumbnail_content:
            thumb_path = path.rsplit(".", 1)[0] + "_thumb.jpg"
            thumbnail_url = StorageClient.upload(
                thumbnail_content,
                thumb_path,
                "image/jpeg"
            )

        return {
            "url": url,
            "thumbnail_url": thumbnail_url,
            "file_name": filename,
            "file_size": len(content),
            "content_type": content_type,
        }

    @classmethod
    async def upload_images(
        cls,
        files: List[Tuple[bytes, str, str]],
        category: UploadCategory,
        max_files: int = 10
    ) -> List[dict]:
        """
        Upload multiple images.

        Args:
            files: List of (content, filename, content_type) tuples
            category: Upload category
            max_files: Maximum number of files

        Returns:
            List of upload results
        """
        if len(files) > max_files:
            raise UploadError(f"Too many files. Maximum: {max_files}")

        results = []
        for content, filename, content_type in files:
            result = await cls.upload_image(content, filename, content_type, category)
            results.append(result)

        return results

    @classmethod
    async def upload_document(
        cls,
        content: bytes,
        filename: str,
        content_type: str,
        category: UploadCategory = UploadCategory.DOCUMENTS
    ) -> dict:
        """
        Upload document with validation.

        Args:
            content: File content
            filename: Original filename
            content_type: MIME type
            category: Upload category

        Returns:
            Dict with url, file_name, file_size, content_type
        """
        # Validate
        is_valid, error = cls.validate_document(content, content_type, filename)
        if not is_valid:
            raise UploadError(error)

        # Generate unique path
        path = StorageClient.generate_unique_filename(filename, category.value)

        # Upload document
        url = StorageClient.upload(content, path, content_type)

        return {
            "url": url,
            "file_name": filename,
            "file_size": len(content),
            "content_type": content_type,
        }

    @classmethod
    async def delete_file(cls, url: str) -> bool:
        """
        Delete file by URL.

        Args:
            url: File URL

        Returns:
            True if deleted successfully
        """
        return StorageClient.delete(url)
