"""
Product Image Upload Script

This script uploads product images to Supabase Storage via the production API.
It requires a valid auth token.

Usage:
1. Login to the ERP (www.aquapurite.org/login)
2. Get the auth token from browser's localStorage (key: 'token')
3. Run: python scripts/upload_product_images.py <token>

Or set the AUTH_TOKEN environment variable.
"""

import os
import sys
import requests
from pathlib import Path

# API Configuration
API_BASE_URL = "https://aquapurite-erp-api.onrender.com"
PRODUCT_IMAGE_BASE_PATH = "/Users/mantosh/Desktop/Aquapurite/Product Image"

# Product image mapping
PRODUCT_IMAGES = {
    "aquapurite-i-elitz": {
        "folder": "Elitz",
        "files": ["I Elitz-1.jpg", "I Elitz-2.jpg", "I Elitz-3.jpg"]
    },
    "aquapurite-i-premiuo": {
        "folder": "I premiuo",
        "files": ["I premiuo-1.jpg", "I premiuo-2.jpg", "I premiuo-3.jpg"]
    },
    "aquapurite-blitz": {
        "folder": "Blitz",
        "files": ["Blitz-1.jpg", "Blitz-2.jpg", "Blitz-3.jpg"]
    },
    "aquapurite-neura": {
        "folder": "Neura",
        "files": ["Neura-1.jpg", "Neura-2.jpg", "Neura-3.jpg"]
    },
    "aquapurite-premiuo-uv": {
        "folder": "Premiumem UV",
        "files": ["Prewmiuo UV-1.jpg", "Prewmiuo UV-2.jpg", "Prewmiuo UV-3.jpg"]
    },
}


def upload_image(file_path: str, token: str, category: str = "products") -> dict:
    """Upload a single image to the API."""
    url = f"{API_BASE_URL}/api/v1/uploads/image"
    headers = {"Authorization": f"Bearer {token}"}

    with open(file_path, "rb") as f:
        files = {"file": (os.path.basename(file_path), f, "image/jpeg")}
        data = {"category": category}
        response = requests.post(url, headers=headers, files=files, data=data)

    if response.status_code == 200:
        return response.json()
    else:
        print(f"  Error uploading {file_path}: {response.status_code} - {response.text}")
        return None


def main():
    # Get auth token
    token = os.environ.get("AUTH_TOKEN") or (sys.argv[1] if len(sys.argv) > 1 else None)

    if not token:
        print("Error: No auth token provided.")
        print("\nUsage:")
        print("  python scripts/upload_product_images.py <auth_token>")
        print("  OR")
        print("  AUTH_TOKEN=<token> python scripts/upload_product_images.py")
        print("\nTo get your auth token:")
        print("1. Login to www.aquapurite.org/login")
        print("2. Open browser DevTools (F12)")
        print("3. Go to Application > Local Storage > https://aquapurite.org")
        print("4. Copy the value of 'token'")
        sys.exit(1)

    print("\n" + "="*60)
    print("PRODUCT IMAGE UPLOAD")
    print("="*60 + "\n")

    # Test API connection
    print("Testing API connection...")
    try:
        response = requests.get(f"{API_BASE_URL}/health")
        if response.status_code != 200:
            print(f"Error: API not responding. Status: {response.status_code}")
            sys.exit(1)
        print("API connection OK\n")
    except Exception as e:
        print(f"Error: Could not connect to API: {e}")
        sys.exit(1)

    # Upload images for each product
    uploaded_urls = {}

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

            print(f"  Uploading: {filename}...", end=" ")
            result = upload_image(file_path, token)

            if result:
                url = result.get("url")
                product_urls.append({
                    "url": url,
                    "thumbnail_url": result.get("thumbnail_url"),
                    "is_primary": (i == 0)
                })
                print(f"OK")
            else:
                print(f"FAILED")

        uploaded_urls[product_slug] = product_urls
        print(f"  Uploaded {len(product_urls)} images for {product_slug}")

    # Print summary
    print("\n" + "="*60)
    print("UPLOAD COMPLETE - IMAGE URLs")
    print("="*60 + "\n")

    for product_slug, urls in uploaded_urls.items():
        print(f"\n{product_slug}:")
        for i, img in enumerate(urls):
            primary = " (primary)" if img.get("is_primary") else ""
            print(f"  [{i+1}] {img['url']}{primary}")

    # Save URLs to a file for easy reference
    output_file = "/Users/mantosh/Desktop/Consumer durable 2/scripts/uploaded_image_urls.txt"
    with open(output_file, "w") as f:
        f.write("Product Image URLs\n")
        f.write("="*60 + "\n\n")
        for product_slug, urls in uploaded_urls.items():
            f.write(f"\n{product_slug}:\n")
            for i, img in enumerate(urls):
                primary = " (primary)" if img.get("is_primary") else ""
                f.write(f"  [{i+1}] {img['url']}{primary}\n")
                if img.get("thumbnail_url"):
                    f.write(f"      thumb: {img['thumbnail_url']}\n")

    print(f"\nImage URLs saved to: {output_file}")
    print("\nNext step: Update products in database with these URLs")


if __name__ == "__main__":
    main()
