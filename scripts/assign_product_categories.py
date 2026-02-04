"""
Assign Products to Categories

Updates products in the database to assign them to the correct categories.
"""

import os
import sys
import asyncio
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Products to assign to Water Purifiers category
WATER_PURIFIER_SLUGS = [
    "ilms-i-elitz",
    "ilms-i-premiuo",
    "ilms-blitz",
    "ilms-neura",
    "ilms-premiuo-uv",
    "ilms-optima",
]


async def main():
    from sqlalchemy import select, update
    from app.database import async_session_factory
    from app.models import Product, Category

    print("\n" + "=" * 60)
    print("ASSIGN PRODUCTS TO CATEGORIES")
    print("=" * 60 + "\n")

    async with async_session_factory() as db:
        # Get Water Purifiers category
        result = await db.execute(
            select(Category).where(Category.slug == "water-purifiers")
        )
        water_purifiers_cat = result.scalar_one_or_none()

        if not water_purifiers_cat:
            print("Error: Water Purifiers category not found!")
            return

        print(f"Found category: {water_purifiers_cat.name} (ID: {water_purifiers_cat.id})")
        print()

        # Update each product
        for slug in WATER_PURIFIER_SLUGS:
            result = await db.execute(
                select(Product).where(Product.slug == slug)
            )
            product = result.scalar_one_or_none()

            if product:
                old_category = product.category_id
                product.category_id = water_purifiers_cat.id
                print(f"  {product.name}: assigned to Water Purifiers")
            else:
                print(f"  Warning: Product not found: {slug}")

        await db.commit()
        print("\n" + "=" * 60)
        print("CATEGORY ASSIGNMENT COMPLETE")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
