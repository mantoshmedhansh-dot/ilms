"""
Direct Supabase Storage Upload Script

Uploads product images directly to Supabase Storage and updates the database.

Required environment variables:
- SUPABASE_URL: Your Supabase project URL (e.g., https://xxx.supabase.co)
- SUPABASE_SERVICE_KEY: Your Supabase service role key
- SUPABASE_STORAGE_BUCKET: Storage bucket name (default: uploads)

Usage:
    export SUPABASE_URL="https://xxx.supabase.co"
    export SUPABASE_SERVICE_KEY="eyJ..."
    python scripts/upload_images_direct.py
"""

import os
import sys
import uuid
import asyncio
from pathlib import Path
from datetime import datetime, timezone

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Product image mapping
PRODUCT_IMAGE_BASE_PATH = "/Users/mantosh/Desktop/ILMS.AI/Product Image"

PRODUCT_IMAGES = {
    "ilms-i-elitz": {
        "folder": "Elitz",
        "files": ["I Elitz-1.jpg", "I Elitz-2.jpg", "I Elitz-3.jpg"]
    },
    "ilms-i-premiuo": {
        "folder": "I premiuo",
        "files": ["I premiuo-1.jpg", "I premiuo-2.jpg", "I premiuo-3.jpg"]
    },
    "ilms-blitz": {
        "folder": "Blitz",
        "files": ["Blitz-1.jpg", "Blitz-2.jpg", "Blitz-3.jpg"]
    },
    "ilms-neura": {
        "folder": "Neura",
        "files": ["Neura-1.jpg", "Neura-2.jpg", "Neura-3.jpg"]
    },
    "ilms-premiuo-uv": {
        "folder": "Premiumem UV",
        "files": ["Prewmiuo UV-1.jpg", "Prewmiuo UV-2.jpg", "Prewmiuo UV-3.jpg"]
    },
}


def get_supabase_client():
    """Initialize Supabase client."""
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_SERVICE_KEY")

    if not supabase_url or not supabase_key:
        return None

    try:
        from supabase import create_client
        return create_client(supabase_url, supabase_key)
    except ImportError:
        print("Error: supabase package not installed. Run: pip install supabase")
        return None
    except Exception as e:
        print(f"Error initializing Supabase: {e}")
        return None


def upload_image_to_supabase(supabase, file_path: str, storage_path: str) -> str:
    """Upload a single image to Supabase Storage."""
    bucket_name = os.environ.get("SUPABASE_STORAGE_BUCKET", "uploads")

    try:
        with open(file_path, "rb") as f:
            content = f.read()

        # Get content type
        ext = os.path.splitext(file_path)[1].lower()
        content_types = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".webp": "image/webp",
        }
        content_type = content_types.get(ext, "application/octet-stream")

        # Upload
        bucket = supabase.storage.from_(bucket_name)
        bucket.upload(
            path=storage_path,
            file=content,
            file_options={"content-type": content_type, "upsert": "true"}
        )

        # Get public URL
        result = bucket.get_public_url(storage_path)
        return result

    except Exception as e:
        print(f"  Error uploading {file_path}: {e}")
        return None


async def update_database_images(product_slug: str, image_urls: list):
    """Update product images in the database."""
    from sqlalchemy import select
    from app.database import async_session_factory
    from app.models import Product, ProductImage

    async with async_session_factory() as db:
        # Find product by slug
        result = await db.execute(
            select(Product).where(Product.slug == product_slug)
        )
        product = result.scalar_one_or_none()

        if not product:
            print(f"  Warning: Product not found: {product_slug}")
            return

        # Clear existing images
        await db.execute(
            ProductImage.__table__.delete().where(
                ProductImage.product_id == product.id
            )
        )

        # Add new images
        for i, img_data in enumerate(image_urls):
            image = ProductImage(
                product_id=product.id,
                image_url=img_data["url"],
                thumbnail_url=img_data.get("thumbnail_url"),
                alt_text=f"{product.name} - View {i+1}",
                is_primary=(i == 0),
                sort_order=i
            )
            db.add(image)

        await db.commit()
        print(f"  Database updated with {len(image_urls)} images")


async def main():
    print("\n" + "="*60)
    print("DIRECT SUPABASE STORAGE UPLOAD")
    print("="*60 + "\n")

    # Initialize Supabase
    supabase = get_supabase_client()
    if not supabase:
        print("Error: Supabase client not initialized.")
        print("\nPlease set environment variables:")
        print("  export SUPABASE_URL='https://your-project.supabase.co'")
        print("  export SUPABASE_SERVICE_KEY='your-service-role-key'")
        print("  export SUPABASE_STORAGE_BUCKET='uploads'")
        print("\nYou can find these in your Supabase dashboard:")
        print("  Project Settings > API > Project URL and service_role key")
        sys.exit(1)

    print("Supabase client initialized\n")

    # Upload images for each product
    for product_slug, image_config in PRODUCT_IMAGES.items():
        print(f"\n--- {product_slug} ---")
        folder = image_config["folder"]
        files = image_config["files"]

        product_urls = []

        for i, filename in enumerate(files):
            file_path = os.path.join(PRODUCT_IMAGE_BASE_PATH, folder, filename)

            if not os.path.exists(file_path):
                print(f"  Warning: File not found: {file_path}")
                continue

            # Generate storage path
            safe_filename = filename.lower().replace(" ", "-")
            storage_path = f"products/{product_slug}/{safe_filename}"

            print(f"  Uploading: {filename}...", end=" ")
            url = upload_image_to_supabase(supabase, file_path, storage_path)

            if url:
                product_urls.append({
                    "url": url,
                    "thumbnail_url": None,  # Will be generated by the backend
                    "is_primary": (i == 0)
                })
                print("OK")
            else:
                print("FAILED")

        # Update database
        if product_urls:
            await update_database_images(product_slug, product_urls)

    print("\n" + "="*60)
    print("UPLOAD COMPLETE")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(main())
