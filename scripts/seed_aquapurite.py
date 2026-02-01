"""Seed script for Aquapurite water purifier products."""
import asyncio
import sys
import os
from decimal import Decimal

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from app.database import async_session_factory
from app.models.brand import Brand
from app.models.category import Category
from app.models.product import Product, ProductStatus, ProductSpecification


async def seed_aquapurite():
    """Seed Aquapurite brand, categories, and products."""
    async with async_session_factory() as db:
        try:
            # 1. Create Aquapurite Brand
            brand_result = await db.execute(
                select(Brand).where(Brand.slug == "aquapurite")
            )
            brand = brand_result.scalar_one_or_none()

            if not brand:
                brand = Brand(
                    name="Aquapurite",
                    slug="aquapurite",
                    description="Premium water purification solutions",
                    logo_url="/images/brands/aquapurite-logo.png",
                    website="https://aquapurite.com",
                    is_active=True,
                    is_featured=True
                )
                db.add(brand)
                await db.flush()
                print(f"Created brand: Aquapurite (ID: {brand.id})")
            else:
                print(f"Brand already exists: Aquapurite (ID: {brand.id})")

            # 2. Create Categories
            categories_data = [
                {
                    "name": "RO Water Purifiers",
                    "slug": "ro-water-purifiers",
                    "description": "Reverse Osmosis water purifiers for TDS reduction",
                    "icon": "ro",
                    "image_url": "/images/categories/ro-icon.png"
                },
                {
                    "name": "UV Water Purifiers",
                    "slug": "uv-water-purifiers",
                    "description": "UV sterilization water purifiers",
                    "icon": "uv",
                    "image_url": "/images/categories/uv-icon.png"
                },
                {
                    "name": "RO+UV Water Purifiers",
                    "slug": "ro-uv-water-purifiers",
                    "description": "Combined RO and UV water purifiers for comprehensive purification",
                    "icon": "ro-uv",
                    "image_url": "/images/categories/ro-uv-icon.png"
                },
                {
                    "name": "Hot & Cold Water Purifiers",
                    "slug": "hot-cold-water-purifiers",
                    "description": "Multi-temperature water dispensing purifiers",
                    "icon": "hot-cold",
                    "image_url": "/images/categories/hot-cold-icon.png"
                }
            ]

            category_map = {}
            for cat_data in categories_data:
                cat_result = await db.execute(
                    select(Category).where(Category.slug == cat_data["slug"])
                )
                category = cat_result.scalar_one_or_none()

                if not category:
                    category = Category(
                        name=cat_data["name"],
                        slug=cat_data["slug"],
                        description=cat_data["description"],
                        icon=cat_data["icon"],
                        image_url=cat_data["image_url"],
                        is_active=True,
                        sort_order=len(category_map)
                    )
                    db.add(category)
                    await db.flush()
                    print(f"Created category: {cat_data['name']} (ID: {category.id})")
                else:
                    print(f"Category already exists: {cat_data['name']} (ID: {category.id})")

                category_map[cat_data["slug"]] = category

            # 3. Create Products
            products_data = [
                {
                    "name": "Aquapurite Blitz",
                    "slug": "aquapurite-blitz",
                    "sku": "AP-BLITZ-001",
                    "model_number": "BLITZ-RO-UV",
                    "category_slug": "ro-uv-water-purifiers",
                    "short_description": "RO+UV water purifier with Zinc Copper enrichment and pH Balance technology",
                    "description": """<h2>Aquapurite Blitz - Advanced RO+UV Water Purifier</h2>
<p>Experience the purest water with Aquapurite Blitz featuring advanced RO+UV purification technology.</p>
<h3>Key Features:</h3>
<ul>
<li>9-Stage Purification Process</li>
<li>RO + UV + UF Technology</li>
<li>Zinc & Copper Enrichment</li>
<li>pH Balance Technology</li>
<li>TDS Controller</li>
<li>10L Storage Tank</li>
</ul>""",
                    "features": "RO+UV+UF, Zinc Copper, pH Balance, 9-Stage Purification, 10L Tank, Smart LED Indicators",
                    "mrp": Decimal("17999.00"),
                    "selling_price": Decimal("14999.00"),
                    "dealer_price": Decimal("11999.00"),
                    "cost_price": Decimal("9500.00"),
                    "hsn_code": "84212110",
                    "gst_rate": Decimal("18.00"),
                    "warranty_months": 12,
                    "extended_warranty_available": True,
                    "specifications": [
                        {"group": "General", "key": "Model", "value": "Blitz"},
                        {"group": "General", "key": "Type", "value": "RO+UV+UF"},
                        {"group": "General", "key": "Storage Capacity", "value": "10 Liters"},
                        {"group": "General", "key": "Color", "value": "White/Black"},
                        {"group": "Technical", "key": "Purification Stages", "value": "9"},
                        {"group": "Technical", "key": "Input TDS", "value": "Up to 2500 ppm"},
                        {"group": "Technical", "key": "Purification Rate", "value": "15 LPH"},
                        {"group": "Technical", "key": "UV Power", "value": "11W"},
                        {"group": "Features", "key": "Mineral Enrichment", "value": "Zinc + Copper"},
                        {"group": "Features", "key": "pH Balance", "value": "Yes"},
                        {"group": "Features", "key": "TDS Controller", "value": "Yes"},
                        {"group": "Dimensions", "key": "Size (LxWxH)", "value": "38 x 27 x 54 cm"},
                        {"group": "Dimensions", "key": "Weight", "value": "9.5 kg"},
                    ],
                    "dead_weight_kg": Decimal("9.5"),
                    "length_cm": Decimal("38"),
                    "width_cm": Decimal("27"),
                    "height_cm": Decimal("54"),
                },
                {
                    "name": "Aquapurite i Elitz",
                    "slug": "aquapurite-i-elitz",
                    "sku": "AP-IELITZ-001",
                    "model_number": "IELITZ-HOT-COLD",
                    "fg_code": "WPRAIEL001",
                    "model_code": "IEL",
                    "category_slug": "hot-cold-water-purifiers",
                    "short_description": "Premium Hot/Cold/Ambient RO water purifier with instant heating technology",
                    "description": """<h2>Aquapurite i Elitz - Hot, Cold & Ambient Water Purifier</h2>
<p>The ultimate convenience with 3-temperature water dispensing and advanced RO purification.</p>
<h3>Key Features:</h3>
<ul>
<li>Hot, Cold & Ambient Water</li>
<li>Instant Heating Technology</li>
<li>RO + UV + UF Purification</li>
<li>12L Storage Tank</li>
<li>Touch Panel Controls</li>
<li>Energy Saving Mode</li>
</ul>""",
                    "features": "Hot/Cold/Ambient, RO+UV+UF, Touch Controls, 12L Tank, Energy Saving, Child Lock",
                    "mrp": Decimal("34999.00"),
                    "selling_price": Decimal("26999.00"),
                    "dealer_price": Decimal("21999.00"),
                    "cost_price": Decimal("18000.00"),
                    "hsn_code": "84212110",
                    "gst_rate": Decimal("18.00"),
                    "warranty_months": 12,
                    "extended_warranty_available": True,
                    "specifications": [
                        {"group": "General", "key": "Model", "value": "i Elitz"},
                        {"group": "General", "key": "Type", "value": "Hot/Cold/Ambient RO"},
                        {"group": "General", "key": "Storage Capacity", "value": "12 Liters"},
                        {"group": "General", "key": "Color", "value": "White/Blue"},
                        {"group": "Technical", "key": "Purification Stages", "value": "8"},
                        {"group": "Technical", "key": "Input TDS", "value": "Up to 2500 ppm"},
                        {"group": "Technical", "key": "Purification Rate", "value": "20 LPH"},
                        {"group": "Technical", "key": "Heating Power", "value": "500W"},
                        {"group": "Technical", "key": "Cooling Power", "value": "80W"},
                        {"group": "Features", "key": "Hot Water Temperature", "value": "85-90°C"},
                        {"group": "Features", "key": "Cold Water Temperature", "value": "8-12°C"},
                        {"group": "Features", "key": "Touch Panel", "value": "Yes"},
                        {"group": "Features", "key": "Child Lock", "value": "Yes"},
                        {"group": "Dimensions", "key": "Size (LxWxH)", "value": "42 x 32 x 58 cm"},
                        {"group": "Dimensions", "key": "Weight", "value": "14 kg"},
                    ],
                    "dead_weight_kg": Decimal("14"),
                    "length_cm": Decimal("42"),
                    "width_cm": Decimal("32"),
                    "height_cm": Decimal("58"),
                },
                {
                    "name": "Aquapurite i Premiuo",
                    "slug": "aquapurite-i-premiuo",
                    "sku": "AP-IPREMIUO-001",
                    "model_number": "IPREMIUO-HOT-AMB",
                    "fg_code": "WPRAIPREM001",
                    "model_code": "IPM",
                    "category_slug": "hot-cold-water-purifiers",
                    "short_description": "Hot & Ambient RO water purifier with premium design and instant heating",
                    "description": """<h2>Aquapurite i Premiuo - Hot & Ambient Water Purifier</h2>
<p>Premium design meets functionality with hot and ambient water dispensing.</p>
<h3>Key Features:</h3>
<ul>
<li>Hot & Ambient Water</li>
<li>Instant Hot Water</li>
<li>RO + UV Purification</li>
<li>10L Storage Tank</li>
<li>Sleek Design</li>
<li>Auto-Shutoff</li>
</ul>""",
                    "features": "Hot/Ambient, RO+UV, Instant Heat, 10L Tank, Auto-Shutoff, Premium Design",
                    "mrp": Decimal("29999.00"),
                    "selling_price": Decimal("23999.00"),
                    "dealer_price": Decimal("19500.00"),
                    "cost_price": Decimal("15500.00"),
                    "hsn_code": "84212110",
                    "gst_rate": Decimal("18.00"),
                    "warranty_months": 12,
                    "extended_warranty_available": True,
                    "specifications": [
                        {"group": "General", "key": "Model", "value": "i Premiuo"},
                        {"group": "General", "key": "Type", "value": "Hot/Ambient RO"},
                        {"group": "General", "key": "Storage Capacity", "value": "10 Liters"},
                        {"group": "General", "key": "Color", "value": "White/Gold"},
                        {"group": "Technical", "key": "Purification Stages", "value": "7"},
                        {"group": "Technical", "key": "Input TDS", "value": "Up to 2000 ppm"},
                        {"group": "Technical", "key": "Purification Rate", "value": "18 LPH"},
                        {"group": "Technical", "key": "Heating Power", "value": "450W"},
                        {"group": "Features", "key": "Hot Water Temperature", "value": "80-85°C"},
                        {"group": "Features", "key": "Touch Panel", "value": "Yes"},
                        {"group": "Features", "key": "Child Lock", "value": "Yes"},
                        {"group": "Dimensions", "key": "Size (LxWxH)", "value": "40 x 30 x 55 cm"},
                        {"group": "Dimensions", "key": "Weight", "value": "12 kg"},
                    ],
                    "dead_weight_kg": Decimal("12"),
                    "length_cm": Decimal("40"),
                    "width_cm": Decimal("30"),
                    "height_cm": Decimal("55"),
                },
                {
                    "name": "Aquapurite Neura",
                    "slug": "aquapurite-neura",
                    "sku": "AP-NEURA-001",
                    "model_number": "NEURA-RO-UV",
                    "fg_code": "WPRANEU001",
                    "model_code": "NEU",
                    "category_slug": "ro-uv-water-purifiers",
                    "short_description": "Smart RO+UV water purifier with Zinc Copper enrichment and IOT connectivity",
                    "description": """<h2>Aquapurite Neura - Smart RO+UV Water Purifier</h2>
<p>Intelligent water purification with advanced mineral enrichment technology.</p>
<h3>Key Features:</h3>
<ul>
<li>Smart IOT Connectivity</li>
<li>RO + UV + UF Technology</li>
<li>Zinc & Copper Enrichment</li>
<li>Real-time TDS Display</li>
<li>Filter Life Indicator</li>
<li>8L Storage Tank</li>
</ul>""",
                    "features": "RO+UV+UF, Zinc Copper, Smart IOT, TDS Display, 8L Tank, Filter Indicator",
                    "mrp": Decimal("16999.00"),
                    "selling_price": Decimal("13999.00"),
                    "dealer_price": Decimal("10999.00"),
                    "cost_price": Decimal("8500.00"),
                    "hsn_code": "84212110",
                    "gst_rate": Decimal("18.00"),
                    "warranty_months": 12,
                    "extended_warranty_available": True,
                    "specifications": [
                        {"group": "General", "key": "Model", "value": "Neura"},
                        {"group": "General", "key": "Type", "value": "RO+UV+UF"},
                        {"group": "General", "key": "Storage Capacity", "value": "8 Liters"},
                        {"group": "General", "key": "Color", "value": "White/Grey"},
                        {"group": "Technical", "key": "Purification Stages", "value": "8"},
                        {"group": "Technical", "key": "Input TDS", "value": "Up to 2500 ppm"},
                        {"group": "Technical", "key": "Purification Rate", "value": "15 LPH"},
                        {"group": "Technical", "key": "UV Power", "value": "11W"},
                        {"group": "Features", "key": "Mineral Enrichment", "value": "Zinc + Copper"},
                        {"group": "Features", "key": "TDS Display", "value": "Yes"},
                        {"group": "Features", "key": "IOT Enabled", "value": "Yes"},
                        {"group": "Dimensions", "key": "Size (LxWxH)", "value": "36 x 26 x 52 cm"},
                        {"group": "Dimensions", "key": "Weight", "value": "8.5 kg"},
                    ],
                    "dead_weight_kg": Decimal("8.5"),
                    "length_cm": Decimal("36"),
                    "width_cm": Decimal("26"),
                    "height_cm": Decimal("52"),
                },
                {
                    "name": "Aquapurite Premiuo UV",
                    "slug": "aquapurite-premiuo-uv",
                    "sku": "AP-PREMIUOUV-001",
                    "model_number": "PREMIUO-UV",
                    "fg_code": "WPRAPUV001",
                    "model_code": "PUV",
                    "category_slug": "uv-water-purifiers",
                    "short_description": "Compact UV water purifier for low TDS water with advanced UV sterilization",
                    "description": """<h2>Aquapurite Premiuo UV - Compact UV Water Purifier</h2>
<p>Perfect for municipal/low TDS water with powerful UV sterilization.</p>
<h3>Key Features:</h3>
<ul>
<li>UV + UF Purification</li>
<li>Ideal for Low TDS Water</li>
<li>Compact Design</li>
<li>No Water Wastage</li>
<li>6L Storage Tank</li>
<li>Easy Installation</li>
</ul>""",
                    "features": "UV+UF, Zero Water Wastage, Compact Design, 6L Tank, Auto-Shutoff",
                    "mrp": Decimal("8999.00"),
                    "selling_price": Decimal("6999.00"),
                    "dealer_price": Decimal("5499.00"),
                    "cost_price": Decimal("4200.00"),
                    "hsn_code": "84212110",
                    "gst_rate": Decimal("18.00"),
                    "warranty_months": 12,
                    "extended_warranty_available": True,
                    "specifications": [
                        {"group": "General", "key": "Model", "value": "Premiuo UV"},
                        {"group": "General", "key": "Type", "value": "UV+UF"},
                        {"group": "General", "key": "Storage Capacity", "value": "6 Liters"},
                        {"group": "General", "key": "Color", "value": "White"},
                        {"group": "Technical", "key": "Purification Stages", "value": "4"},
                        {"group": "Technical", "key": "Input TDS", "value": "Up to 200 ppm"},
                        {"group": "Technical", "key": "Purification Rate", "value": "60 LPH"},
                        {"group": "Technical", "key": "UV Power", "value": "11W"},
                        {"group": "Features", "key": "Water Wastage", "value": "Zero"},
                        {"group": "Features", "key": "Auto-Shutoff", "value": "Yes"},
                        {"group": "Dimensions", "key": "Size (LxWxH)", "value": "32 x 24 x 48 cm"},
                        {"group": "Dimensions", "key": "Weight", "value": "5.5 kg"},
                    ],
                    "dead_weight_kg": Decimal("5.5"),
                    "length_cm": Decimal("32"),
                    "width_cm": Decimal("24"),
                    "height_cm": Decimal("48"),
                }
            ]

            created_products = []
            for prod_data in products_data:
                # Check if product exists
                prod_result = await db.execute(
                    select(Product).where(Product.sku == prod_data["sku"])
                )
                product = prod_result.scalar_one_or_none()

                if product:
                    print(f"Product already exists: {prod_data['name']} (SKU: {prod_data['sku']})")
                    continue

                category = category_map.get(prod_data["category_slug"])
                if not category:
                    print(f"Category not found: {prod_data['category_slug']}, skipping {prod_data['name']}")
                    continue

                # Create product
                product = Product(
                    name=prod_data["name"],
                    slug=prod_data["slug"],
                    sku=prod_data["sku"],
                    model_number=prod_data["model_number"],
                    fg_code=prod_data.get("fg_code"),
                    model_code=prod_data.get("model_code"),
                    short_description=prod_data["short_description"],
                    description=prod_data["description"],
                    features=prod_data["features"],
                    category_id=category.id,
                    brand_id=brand.id,
                    mrp=prod_data["mrp"],
                    selling_price=prod_data["selling_price"],
                    dealer_price=prod_data["dealer_price"],
                    cost_price=prod_data["cost_price"],
                    hsn_code=prod_data["hsn_code"],
                    gst_rate=prod_data["gst_rate"],
                    warranty_months=prod_data["warranty_months"],
                    extended_warranty_available=prod_data["extended_warranty_available"],
                    dead_weight_kg=prod_data.get("dead_weight_kg"),
                    length_cm=prod_data.get("length_cm"),
                    width_cm=prod_data.get("width_cm"),
                    height_cm=prod_data.get("height_cm"),
                    status=ProductStatus.ACTIVE,
                    is_active=True,
                    is_featured=True,
                    is_new_arrival=True
                )
                db.add(product)
                await db.flush()

                # Add specifications
                for i, spec in enumerate(prod_data["specifications"]):
                    spec_obj = ProductSpecification(
                        product_id=product.id,
                        group_name=spec["group"],
                        key=spec["key"],
                        value=spec["value"],
                        sort_order=i
                    )
                    db.add(spec_obj)

                created_products.append(product)
                print(f"Created product: {prod_data['name']} (SKU: {prod_data['sku']}, Price: ₹{prod_data['selling_price']})")

            await db.commit()

            print("\n" + "=" * 60)
            print("SUMMARY")
            print("=" * 60)
            print(f"Brand: Aquapurite")
            print(f"Categories: {len(category_map)}")
            print(f"Products created: {len(created_products)}")
            print("=" * 60)

            return True

        except Exception as e:
            await db.rollback()
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()
            return False


if __name__ == "__main__":
    asyncio.run(seed_aquapurite())
