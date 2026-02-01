"""
Seed script for Products module.
Creates sample categories, brands, and products for a Consumer Durable company.

Usage:
    python -m scripts.seed_products
"""

import asyncio
import sys
from pathlib import Path
from decimal import Decimal

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from app.database import async_session_factory, engine, Base
from app.models.category import Category
from app.models.brand import Brand
from app.models.product import (
    Product, ProductStatus, ProductImage, ProductSpecification,
    ProductVariant, ProductDocument, DocumentType
)


# ==================== CATEGORIES ====================
CATEGORIES = [
    # Root categories
    {"name": "Water Purifiers", "slug": "water-purifiers", "description": "RO, UV, and UF water purifiers for clean drinking water", "icon": "water_drop", "sort_order": 1, "is_featured": True},
    {"name": "Air Purifiers", "slug": "air-purifiers", "description": "HEPA and ionizer air purifiers for clean air", "icon": "air", "sort_order": 2, "is_featured": True},
    {"name": "Kitchen Appliances", "slug": "kitchen-appliances", "description": "Modern kitchen appliances", "icon": "kitchen", "sort_order": 3, "is_featured": True},
    {"name": "Home Appliances", "slug": "home-appliances", "description": "Essential home appliances", "icon": "home", "sort_order": 4},
    {"name": "Spare Parts", "slug": "spare-parts", "description": "Genuine spare parts and accessories", "icon": "build", "sort_order": 5},
]

# Sub-categories (with parent references)
SUB_CATEGORIES = [
    # Water Purifier sub-categories
    {"name": "RO Water Purifiers", "slug": "ro-water-purifiers", "parent_slug": "water-purifiers", "sort_order": 1},
    {"name": "UV Water Purifiers", "slug": "uv-water-purifiers", "parent_slug": "water-purifiers", "sort_order": 2},
    {"name": "RO+UV Water Purifiers", "slug": "ro-uv-water-purifiers", "parent_slug": "water-purifiers", "sort_order": 3},
    {"name": "Gravity Water Purifiers", "slug": "gravity-water-purifiers", "parent_slug": "water-purifiers", "sort_order": 4},

    # Kitchen sub-categories
    {"name": "Mixer Grinders", "slug": "mixer-grinders", "parent_slug": "kitchen-appliances", "sort_order": 1},
    {"name": "Induction Cooktops", "slug": "induction-cooktops", "parent_slug": "kitchen-appliances", "sort_order": 2},
    {"name": "Electric Kettles", "slug": "electric-kettles", "parent_slug": "kitchen-appliances", "sort_order": 3},

    # Spare Parts sub-categories
    {"name": "RO Filters", "slug": "ro-filters", "parent_slug": "spare-parts", "sort_order": 1},
    {"name": "UV Lamps", "slug": "uv-lamps", "parent_slug": "spare-parts", "sort_order": 2},
    {"name": "Membranes", "slug": "membranes", "parent_slug": "spare-parts", "sort_order": 3},
]


# ==================== BRANDS ====================
BRANDS = [
    {
        "name": "AquaPure",
        "slug": "aquapure",
        "description": "Premium water purification solutions for healthy living",
        "logo_url": "/images/brands/aquapure-logo.png",
        "website": "https://www.aquapure.com",
        "is_featured": True,
        "sort_order": 1,
    },
    {
        "name": "CleanAir Pro",
        "slug": "cleanair-pro",
        "description": "Advanced air purification technology",
        "logo_url": "/images/brands/cleanair-logo.png",
        "website": "https://www.cleanairpro.com",
        "is_featured": True,
        "sort_order": 2,
    },
    {
        "name": "KitchenMaster",
        "slug": "kitchenmaster",
        "description": "Smart kitchen appliances for modern homes",
        "logo_url": "/images/brands/kitchenmaster-logo.png",
        "is_featured": True,
        "sort_order": 3,
    },
]


# ==================== PRODUCTS ====================
PRODUCTS = [
    # Water Purifiers
    {
        "name": "AquaPure Elite 8L RO+UV+UF Water Purifier",
        "slug": "aquapure-elite-8l-ro-uv-uf",
        "sku": "AP-WP-001",
        "model_number": "APE-8000",
        "category_slug": "ro-uv-water-purifiers",
        "brand_slug": "aquapure",
        "short_description": "Advanced 8-stage purification with mineralizer",
        "description": """
<h3>AquaPure Elite - Premium Water Purification</h3>
<p>Experience the purest drinking water with our flagship 8-stage RO+UV+UF water purifier.</p>

<h4>Key Features:</h4>
<ul>
    <li>8-Stage Advanced Purification</li>
    <li>TDS Controller & Mineralizer</li>
    <li>8 Liter Storage Tank</li>
    <li>UV + UF Double Protection</li>
    <li>Smart LED Indicators</li>
</ul>
        """,
        "features": "8-Stage Purification|TDS Controller|Mineralizer|UV+UF Protection|8L Tank|Smart Indicators",
        "mrp": Decimal("24999.00"),
        "selling_price": Decimal("18999.00"),
        "dealer_price": Decimal("15000.00"),
        "hsn_code": "84212110",
        "gst_rate": Decimal("18.00"),
        "warranty_months": 12,
        "extended_warranty_available": True,
        "warranty_terms": "1 year comprehensive warranty. Extended warranty available for up to 3 years.",
        "weight_kg": Decimal("9.5"),
        "length_cm": Decimal("40"),
        "width_cm": Decimal("28"),
        "height_cm": Decimal("55"),
        "status": ProductStatus.ACTIVE,
        "is_featured": True,
        "is_bestseller": True,
        "specifications": [
            {"group": "General", "key": "Brand", "value": "AquaPure"},
            {"group": "General", "key": "Model", "value": "APE-8000"},
            {"group": "General", "key": "Color", "value": "White & Blue"},
            {"group": "Technical", "key": "Purification Technology", "value": "RO + UV + UF"},
            {"group": "Technical", "key": "Storage Capacity", "value": "8 Liters"},
            {"group": "Technical", "key": "Purification Stages", "value": "8"},
            {"group": "Technical", "key": "Input TDS Range", "value": "Up to 2000 ppm"},
            {"group": "Technical", "key": "Purification Rate", "value": "15 L/hr"},
            {"group": "Dimensions", "key": "Dimensions (LxWxH)", "value": "40 x 28 x 55 cm"},
            {"group": "Dimensions", "key": "Weight", "value": "9.5 kg"},
            {"group": "Electrical", "key": "Power Consumption", "value": "60 W"},
            {"group": "Electrical", "key": "Voltage", "value": "230V AC, 50Hz"},
        ],
        "images": [
            {"url": "/images/products/ap-wp-001-1.jpg", "is_primary": True, "alt": "AquaPure Elite Front View"},
            {"url": "/images/products/ap-wp-001-2.jpg", "is_primary": False, "alt": "AquaPure Elite Side View"},
            {"url": "/images/products/ap-wp-001-3.jpg", "is_primary": False, "alt": "AquaPure Elite Installation"},
        ],
    },
    {
        "name": "AquaPure Smart 7L RO+UV Water Purifier",
        "slug": "aquapure-smart-7l-ro-uv",
        "sku": "AP-WP-002",
        "model_number": "APS-7000",
        "category_slug": "ro-uv-water-purifiers",
        "brand_slug": "aquapure",
        "short_description": "Smart water purifier with app control",
        "description": "Smart 7-stage water purifier with WiFi connectivity and mobile app control.",
        "mrp": Decimal("19999.00"),
        "selling_price": Decimal("15999.00"),
        "hsn_code": "84212110",
        "warranty_months": 12,
        "status": ProductStatus.ACTIVE,
        "is_featured": True,
        "specifications": [
            {"group": "General", "key": "Brand", "value": "AquaPure"},
            {"group": "Technical", "key": "Purification Technology", "value": "RO + UV"},
            {"group": "Technical", "key": "Storage Capacity", "value": "7 Liters"},
            {"group": "Smart Features", "key": "WiFi Enabled", "value": "Yes"},
            {"group": "Smart Features", "key": "App Control", "value": "Yes"},
        ],
        "images": [
            {"url": "/images/products/ap-wp-002-1.jpg", "is_primary": True, "alt": "AquaPure Smart Front"},
        ],
    },
    {
        "name": "AquaPure Basic 6L UV Water Purifier",
        "slug": "aquapure-basic-6l-uv",
        "sku": "AP-WP-003",
        "model_number": "APB-6000",
        "category_slug": "uv-water-purifiers",
        "brand_slug": "aquapure",
        "short_description": "Affordable UV purification for municipal water",
        "mrp": Decimal("8999.00"),
        "selling_price": Decimal("6999.00"),
        "hsn_code": "84212110",
        "warranty_months": 12,
        "status": ProductStatus.ACTIVE,
        "specifications": [
            {"group": "Technical", "key": "Purification Technology", "value": "UV"},
            {"group": "Technical", "key": "Storage Capacity", "value": "6 Liters"},
            {"group": "Technical", "key": "Best For", "value": "Municipal/Corporation Water"},
        ],
        "images": [
            {"url": "/images/products/ap-wp-003-1.jpg", "is_primary": True, "alt": "AquaPure Basic"},
        ],
    },

    # Air Purifiers
    {
        "name": "CleanAir Pro HEPA-500 Air Purifier",
        "slug": "cleanair-pro-hepa-500",
        "sku": "CA-AP-001",
        "model_number": "HEPA-500",
        "category_slug": "air-purifiers",
        "brand_slug": "cleanair-pro",
        "short_description": "HEPA H13 filter with 500 sq ft coverage",
        "description": "Advanced HEPA H13 air purifier with activated carbon filter for rooms up to 500 sq ft.",
        "mrp": Decimal("29999.00"),
        "selling_price": Decimal("24999.00"),
        "hsn_code": "84213990",
        "warranty_months": 24,
        "status": ProductStatus.ACTIVE,
        "is_featured": True,
        "specifications": [
            {"group": "General", "key": "Brand", "value": "CleanAir Pro"},
            {"group": "Technical", "key": "Filter Type", "value": "HEPA H13 + Activated Carbon"},
            {"group": "Technical", "key": "Coverage Area", "value": "500 sq ft"},
            {"group": "Technical", "key": "CADR", "value": "400 m³/h"},
            {"group": "Technical", "key": "Noise Level", "value": "25-52 dB"},
        ],
        "images": [
            {"url": "/images/products/ca-ap-001-1.jpg", "is_primary": True, "alt": "CleanAir Pro HEPA-500"},
        ],
    },

    # Kitchen Appliances
    {
        "name": "KitchenMaster Turbo 750W Mixer Grinder",
        "slug": "kitchenmaster-turbo-750w",
        "sku": "KM-MG-001",
        "model_number": "KMT-750",
        "category_slug": "mixer-grinders",
        "brand_slug": "kitchenmaster",
        "short_description": "Powerful 750W motor with 3 stainless steel jars",
        "mrp": Decimal("4999.00"),
        "selling_price": Decimal("3499.00"),
        "hsn_code": "85094010",
        "warranty_months": 24,
        "status": ProductStatus.ACTIVE,
        "is_bestseller": True,
        "specifications": [
            {"group": "Technical", "key": "Motor Power", "value": "750W"},
            {"group": "Technical", "key": "Speed Settings", "value": "3"},
            {"group": "Technical", "key": "Number of Jars", "value": "3"},
            {"group": "Technical", "key": "Jar Material", "value": "Stainless Steel"},
        ],
        "images": [
            {"url": "/images/products/km-mg-001-1.jpg", "is_primary": True, "alt": "KitchenMaster Turbo"},
        ],
        "variants": [
            {"name": "Red", "sku": "KM-MG-001-RED", "attributes": {"color": "Red"}, "stock": 50},
            {"name": "Black", "sku": "KM-MG-001-BLK", "attributes": {"color": "Black"}, "stock": 75},
            {"name": "White", "sku": "KM-MG-001-WHT", "attributes": {"color": "White"}, "stock": 60},
        ],
    },

    # Spare Parts
    {
        "name": "AquaPure RO Membrane 80 GPD",
        "slug": "aquapure-ro-membrane-80gpd",
        "sku": "AP-SP-001",
        "model_number": "APROM-80",
        "category_slug": "membranes",
        "brand_slug": "aquapure",
        "short_description": "Genuine 80 GPD RO membrane for AquaPure purifiers",
        "mrp": Decimal("2499.00"),
        "selling_price": Decimal("1999.00"),
        "hsn_code": "84212190",
        "warranty_months": 6,
        "status": ProductStatus.ACTIVE,
        "specifications": [
            {"group": "Technical", "key": "Capacity", "value": "80 GPD"},
            {"group": "Technical", "key": "Compatibility", "value": "AquaPure Elite, Smart series"},
            {"group": "Technical", "key": "Replacement Interval", "value": "12-18 months"},
        ],
        "images": [
            {"url": "/images/products/ap-sp-001-1.jpg", "is_primary": True, "alt": "RO Membrane"},
        ],
    },
    {
        "name": "AquaPure UV Lamp 11W",
        "slug": "aquapure-uv-lamp-11w",
        "sku": "AP-SP-002",
        "model_number": "APUV-11",
        "category_slug": "uv-lamps",
        "brand_slug": "aquapure",
        "short_description": "Genuine 11W UV lamp for water purifiers",
        "mrp": Decimal("899.00"),
        "selling_price": Decimal("699.00"),
        "hsn_code": "85393190",
        "warranty_months": 6,
        "status": ProductStatus.ACTIVE,
        "specifications": [
            {"group": "Technical", "key": "Power", "value": "11W"},
            {"group": "Technical", "key": "Life", "value": "8000 hours"},
        ],
        "images": [
            {"url": "/images/products/ap-sp-002-1.jpg", "is_primary": True, "alt": "UV Lamp"},
        ],
    },
]


async def seed_categories(session) -> dict:
    """Seed categories and return slug to category mapping."""
    print("Seeding categories...")
    category_map = {}

    # Create root categories
    for cat_data in CATEGORIES:
        stmt = select(Category).where(Category.slug == cat_data["slug"])
        existing = (await session.execute(stmt)).scalar_one_or_none()

        if existing:
            category_map[cat_data["slug"]] = existing
            print(f"  Category '{cat_data['name']}' already exists")
        else:
            category = Category(**cat_data)
            session.add(category)
            await session.flush()
            category_map[cat_data["slug"]] = category
            print(f"  Created category: {cat_data['name']}")

    # Create sub-categories
    for cat_data in SUB_CATEGORIES:
        stmt = select(Category).where(Category.slug == cat_data["slug"])
        existing = (await session.execute(stmt)).scalar_one_or_none()

        if existing:
            category_map[cat_data["slug"]] = existing
            print(f"  Sub-category '{cat_data['name']}' already exists")
        else:
            parent = category_map.get(cat_data["parent_slug"])
            if parent:
                category = Category(
                    name=cat_data["name"],
                    slug=cat_data["slug"],
                    parent_id=parent.id,
                    sort_order=cat_data.get("sort_order", 0),
                )
                session.add(category)
                await session.flush()
                category_map[cat_data["slug"]] = category
                print(f"  Created sub-category: {cat_data['name']}")

    return category_map


async def seed_brands(session) -> dict:
    """Seed brands and return slug to brand mapping."""
    print("\nSeeding brands...")
    brand_map = {}

    for brand_data in BRANDS:
        stmt = select(Brand).where(Brand.slug == brand_data["slug"])
        existing = (await session.execute(stmt)).scalar_one_or_none()

        if existing:
            brand_map[brand_data["slug"]] = existing
            print(f"  Brand '{brand_data['name']}' already exists")
        else:
            brand = Brand(**brand_data)
            session.add(brand)
            await session.flush()
            brand_map[brand_data["slug"]] = brand
            print(f"  Created brand: {brand_data['name']}")

    return brand_map


async def seed_products(session, category_map: dict, brand_map: dict):
    """Seed products with images, specs, and variants."""
    print("\nSeeding products...")

    for prod_data in PRODUCTS:
        # Check if exists
        stmt = select(Product).where(Product.sku == prod_data["sku"])
        existing = (await session.execute(stmt)).scalar_one_or_none()

        if existing:
            print(f"  Product '{prod_data['name']}' already exists")
            continue

        # Get category and brand
        category = category_map.get(prod_data.pop("category_slug"))
        brand = brand_map.get(prod_data.pop("brand_slug"))

        if not category or not brand:
            print(f"  Warning: Category or brand not found for {prod_data['name']}")
            continue

        # Extract nested data
        specs_data = prod_data.pop("specifications", [])
        images_data = prod_data.pop("images", [])
        variants_data = prod_data.pop("variants", [])

        # Create product
        product = Product(
            **prod_data,
            category_id=category.id,
            brand_id=brand.id,
        )
        session.add(product)
        await session.flush()

        # Add specifications
        for i, spec in enumerate(specs_data):
            spec_obj = ProductSpecification(
                product_id=product.id,
                group_name=spec.get("group", "General"),
                key=spec["key"],
                value=spec["value"],
                sort_order=i,
            )
            session.add(spec_obj)

        # Add images
        for i, img in enumerate(images_data):
            image_obj = ProductImage(
                product_id=product.id,
                image_url=img["url"],
                alt_text=img.get("alt", product.name),
                is_primary=img.get("is_primary", False),
                sort_order=i,
            )
            session.add(image_obj)

        # Add variants
        for i, var in enumerate(variants_data):
            variant_obj = ProductVariant(
                product_id=product.id,
                name=var["name"],
                sku=var["sku"],
                attributes=var.get("attributes"),
                stock_quantity=var.get("stock", 0),
                sort_order=i,
            )
            session.add(variant_obj)

        print(f"  Created product: {product.name} ({product.sku})")

    await session.flush()


async def main():
    """Main seed function."""
    print("=" * 60)
    print("Product Catalog Seed Script")
    print("=" * 60)

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_factory() as session:
        try:
            category_map = await seed_categories(session)
            brand_map = await seed_brands(session)
            await seed_products(session, category_map, brand_map)

            await session.commit()

            print("\n" + "=" * 60)
            print("Product seeding completed!")
            print("=" * 60)
            print(f"\nSummary:")
            print(f"  - Categories: {len(category_map)}")
            print(f"  - Brands: {len(brand_map)}")
            print(f"  - Products: {len(PRODUCTS)}")

        except Exception as e:
            await session.rollback()
            print(f"\nError during seeding: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(main())
