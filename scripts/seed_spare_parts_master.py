"""
Create Spare Parts Product Master with SP Codes and Serialization.

SP Code Format: SP + 3-letter Category Code + Sequence
Example: SPSDF001 (Spare Part - Sediment Filter - 001)

Barcode Format (16 chars): AP + SS + Y + M + CC + SSSSSSSS
- AP = Aquapurite prefix
- SS = Supplier code (FS=FastTrack, ST=STOS)
- Y = Year (A=2026, B=2027, etc.)
- M = Month (A=Jan, B=Feb, etc.)
- CC = Channel code (EC=Economical, PR=Premium)
- SSSSSSSS = 8-digit serial number

Dual Series: Same item can have TWO barcode series based on supplier:
- Economical (FastTrack): APFSAAEC00000001
- Premium (STOS): APSTAAPR00000001

Aquapurite ERP - Spare Parts Master
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from decimal import Decimal
from datetime import datetime, timezone
from sqlalchemy import select, text
from app.database import async_session_factory
from app.models.product import Product, ProductItemType, ProductStatus
from app.models.category import Category
from app.models.brand import Brand

# Spare Parts Data with Category Codes
# Category Codes are 3-letter codes used in SP Code (e.g., SPSDF001)
# Channel Codes (EC/PR) are used in barcodes based on supplier
SPARE_PARTS = [
    {
        "name": "Sediment Filter (PP Yarn Wound)",
        "sku": "SP-SDF-001",
        "category_code": "SDF",  # Sediment Filter
        "sp_code": "SPSDF001",
        "hsn_code": "84212190",
        "description": "PP Yarn Wound Sediment Filter for pre-filtration",
        "mrp": 250.00,
        "selling_price": 180.00,
        "cost_price": 97.00,
    },
    {
        "name": "Sediment Filter (Spun Filter)",
        "sku": "SP-SDF-002",
        "category_code": "SDF",  # Sediment Filter
        "sp_code": "SPSDF002",
        "hsn_code": "84212190",
        "description": "Spun Filter for sediment removal",
        "mrp": 200.00,
        "selling_price": 150.00,
        "cost_price": 76.00,
    },
    {
        "name": "Pre Carbon Block (Premium)",
        "sku": "SP-PCB-001",
        "category_code": "PCB",  # Pre Carbon Block
        "sp_code": "SPPCB001",
        "hsn_code": "84212190",
        "description": "Premium Pre Carbon Block Filter for chlorine removal",
        "mrp": 350.00,
        "selling_price": 280.00,
        "cost_price": 114.00,
    },
    {
        "name": "Pre Carbon Block (Regular)",
        "sku": "SP-PCB-002",
        "category_code": "PCB",  # Pre Carbon Block
        "sp_code": "SPPCB002",
        "hsn_code": "84212190",
        "description": "Regular Pre Carbon Block Filter",
        "mrp": 300.00,
        "selling_price": 220.00,
        "cost_price": 111.00,
    },
    {
        "name": "Alkaline Mineral Block (Premium)",
        "sku": "SP-ALK-001",
        "category_code": "ALK",  # Alkaline
        "sp_code": "SPALK001",
        "hsn_code": "84212190",
        "description": "Premium Alkaline Mineral Filter for pH balance",
        "mrp": 200.00,
        "selling_price": 150.00,
        "cost_price": 61.00,
    },
    {
        "name": "Post Carbon with Copper (Regular)",
        "sku": "SP-POC-001",
        "category_code": "POC",  # Post Carbon
        "sp_code": "SPPOC001",
        "hsn_code": "84212190",
        "description": "Post Carbon Filter with Copper infusion",
        "mrp": 180.00,
        "selling_price": 130.00,
        "cost_price": 58.00,
    },
    {
        "name": "Membrane (Premium)",
        "sku": "SP-MBF-001",
        "category_code": "MBF",  # Membrane Filter
        "sp_code": "SPMBF001",
        "hsn_code": "84212190",
        "description": "Premium RO Membrane 100 GPD",
        "mrp": 1200.00,
        "selling_price": 900.00,
        "cost_price": 398.00,
    },
    {
        "name": "Membrane (Regular)",
        "sku": "SP-MBF-002",
        "category_code": "MBF",  # Membrane Filter
        "sp_code": "SPMBF002",
        "hsn_code": "84212190",
        "description": "Regular RO Membrane 75 GPD",
        "mrp": 1000.00,
        "selling_price": 750.00,
        "cost_price": 375.00,
    },
    {
        "name": "Pre-Filter Multi Layer Candle",
        "sku": "SP-PFC-001",
        "category_code": "PFC",  # Pre Filter Candle
        "sp_code": "SPPFC001",
        "hsn_code": "84212190",
        "description": "Multi-layer candle pre-filter for sediment removal",
        "mrp": 600.00,
        "selling_price": 450.00,
        "cost_price": 245.00,
    },
    {
        "name": "Iron Remover Cartridge",
        "sku": "SP-IRC-001",
        "category_code": "IRC",  # Iron Remover Cartridge
        "sp_code": "SPIRC001",
        "hsn_code": "84212190",
        "description": "Iron remover cartridge for high iron water",
        "mrp": 1500.00,
        "selling_price": 1100.00,
        "cost_price": 790.00,
    },
    {
        "name": "HMR Cartridge",
        "sku": "SP-HMR-001",
        "category_code": "HMR",  # Heavy Metal Remover
        "sp_code": "SPHMR001",
        "hsn_code": "84212190",
        "description": "Heavy Metal Remover Cartridge",
        "mrp": 1500.00,
        "selling_price": 1100.00,
        "cost_price": 801.00,
    },
    {
        "name": "Prefilter with Multilayer Candle",
        "sku": "SP-PFC-002",
        "category_code": "PFC",  # Pre Filter Candle
        "sp_code": "SPPFC002",
        "hsn_code": "84212190",
        "description": "Complete prefilter assembly with multilayer candle",
        "mrp": 700.00,
        "selling_price": 500.00,
        "cost_price": 280.00,
    },
    {
        "name": "Prefilter with Spun Filter",
        "sku": "SP-PFS-001",
        "category_code": "PFS",  # Pre Filter Spun
        "sp_code": "SPPFS001",
        "hsn_code": "84212190",
        "description": "Complete prefilter assembly with spun filter",
        "mrp": 550.00,
        "selling_price": 400.00,
        "cost_price": 225.00,
    },
    {
        "name": "Heavy Metal Remover",
        "sku": "SP-HMR-002",
        "category_code": "HMR",  # Heavy Metal Remover
        "sp_code": "SPHMR002",
        "hsn_code": "84212190",
        "description": "Heavy metal remover filter for arsenic, lead removal",
        "mrp": 1800.00,
        "selling_price": 1300.00,
        "cost_price": 850.00,
    },
    {
        "name": "Plastic PRV",
        "sku": "SP-PRV-001",
        "category_code": "PRV",  # PRV
        "sp_code": "SPPRV001",
        "hsn_code": "84212190",
        "description": "Plastic Pressure Reducing Valve",
        "mrp": 350.00,
        "selling_price": 250.00,
        "cost_price": 180.00,
    },
    {
        "name": "Brass Diverter Valve",
        "sku": "SP-BDV-001",
        "category_code": "BDV",  # Brass Diverter Valve
        "sp_code": "SPBDV001",
        "hsn_code": "84212190",
        "description": "Brass diverter valve for water purifier installation",
        "mrp": 300.00,
        "selling_price": 220.00,
        "cost_price": 150.00,
    },
]

# Supplier-Channel Mapping for Barcode Generation
SUPPLIER_CHANNEL_MAP = {
    "FS": {"name": "FastTrack Filtration", "channel": "EC", "category": "Economical"},
    "ST": {"name": "STOS Industrial", "channel": "PR", "category": "Premium"},
}


async def create_spare_parts_master():
    """Create spare parts in Product Master with SP codes."""
    async with async_session_factory() as db:
        # Get or create Spare Parts category
        result = await db.execute(
            select(Category).where(Category.name.ilike("%spare%"))
        )
        category = result.scalars().first()

        if not category:
            # Create Spare Parts category
            category = Category(
                name="Spare Parts",
                slug="spare-parts",
                description="Replacement parts and consumables for water purifiers",
                is_active=True
            )
            db.add(category)
            await db.flush()
            print(f"✓ Created category: {category.name}")

        # Get Aquapurite brand
        result = await db.execute(
            select(Brand).where(Brand.name.ilike("%aquapurite%"))
        )
        brand = result.scalars().first()

        if not brand:
            brand = Brand(
                name="Aquapurite",
                slug="aquapurite",
                description="Aquapurite Water Purification Systems",
                is_active=True
            )
            db.add(brand)
            await db.flush()
            print(f"✓ Created brand: {brand.name}")

        # First, delete existing spare parts to recreate with correct codes
        await db.execute(
            text("DELETE FROM model_code_references WHERE item_type = 'SPARE_PART'")
        )
        await db.execute(
            text("DELETE FROM products WHERE item_type = 'SP'")
        )
        await db.commit()
        print("✓ Cleared existing spare parts for re-creation")

        print("\n" + "=" * 120)
        print("CREATING SPARE PARTS PRODUCT MASTER (with Dual Barcode Series)")
        print("=" * 120)
        print(f"{'S.N.':<5} {'Product Name':<40} {'SKU':<15} {'SP CODE':<12} {'Cat':<5} {'HSN':<12} {'Price':>10}")
        print("-" * 120)

        created_count = 0

        for idx, sp in enumerate(SPARE_PARTS, 1):
            # Create new product
            product = Product(
                name=sp["name"],
                slug=sp["sku"].lower().replace("-", "-"),
                sku=sp["sku"],
                fg_code=sp["sp_code"],
                model_code=sp["category_code"],  # 3-letter category code
                hsn_code=sp["hsn_code"],
                item_type=ProductItemType.SPARE_PART,
                short_description=sp["description"],
                description=sp["description"],
                category_id=category.id,
                brand_id=brand.id,
                mrp=Decimal(str(sp["mrp"])),
                selling_price=Decimal(str(sp["selling_price"])),
                cost_price=Decimal(str(sp["cost_price"])),
                gst_rate=Decimal("18.00"),
                warranty_months=6,  # 6 months warranty for spare parts
                status=ProductStatus.ACTIVE,
                is_active=True,
            )
            db.add(product)
            created_count += 1

            print(f"{idx:<5} {sp['name'][:38]:<40} {sp['sku']:<15} {sp['sp_code']:<12} {sp['category_code']:<5} {sp['hsn_code']:<12} {sp['selling_price']:>10,.2f}")

        await db.commit()

        print("-" * 120)
        print(f"\n✓ Created: {created_count} spare parts in Product Master")

        # Now create model_code_references for serialization (with dual series support)
        print("\n" + "=" * 120)
        print("CREATING SERIALIZATION MODEL CODE REFERENCES (Dual Series)")
        print("=" * 120)
        print(f"{'SP Code':<12} {'Category':<5} {'Economical Barcode':<20} {'Premium Barcode':<20}")
        print("-" * 120)

        for sp in SPARE_PARTS:
            # Get product ID
            result = await db.execute(
                select(Product.id).where(Product.sku == sp["sku"])
            )
            product_row = result.fetchone()
            product_id = str(product_row[0]) if product_row else None

            # Create model code reference (stores the SP code and category for barcode generation)
            await db.execute(
                text("""
                    INSERT INTO model_code_references
                    (id, product_id, product_sku, fg_code, model_code, item_type, description, is_active, created_at, updated_at)
                    VALUES
                    (:id, :product_id, :product_sku, :fg_code, :model_code, :item_type, :description, TRUE, :now, :now)
                """),
                {
                    "id": str(__import__('uuid').uuid4()),
                    "product_id": product_id,
                    "product_sku": sp["sku"],
                    "fg_code": sp["sp_code"],
                    "model_code": sp["category_code"],
                    "item_type": "SPARE_PART",
                    "description": sp["name"],
                    "now": datetime.now(timezone.utc)
                }
            )

            # Show example barcodes for both suppliers (using EC/PR channel codes, not category codes)
            # Format: AP + SS(supplier) + Y(year) + M(month) + CC(channel) + SSSSSSSS(serial)
            economical_barcode = "APFSAAEC00000001"  # FastTrack + Economical
            premium_barcode = "APSTAAPR00000001"     # STOS + Premium
            print(f"{sp['sp_code']:<12} {sp['category_code']:<5} {economical_barcode:<20} {premium_barcode:<20}")

        await db.commit()

        # Generate summary
        print("\n" + "=" * 120)
        print("SPARE PARTS SERIALIZATION STRUCTURE")
        print("=" * 120)
        print("""
┌─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                      SPARE PARTS CODE FORMAT                                                         │
├─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│  SP CODE Format: SP + 3-letter Category Code + Sequence Number                                                       │
│  Example: SPSDF001 = SP (Spare Part) + SDF (Sediment Filter) + 001 (First in series)                                │
├─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                      BARCODE FORMAT (16 characters)                                                  │
├─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│  Format: AP + SS + Y + M + CC + SSSSSSSS                                                                             │
│                                                                                                                      │
│  AP = Aquapurite prefix (2 chars)                                                                                    │
│  SS = Supplier code (2 chars): FS=FastTrack, ST=STOS                                                                 │
│  Y  = Year code (1 char): A=2026, B=2027, C=2028...                                                                  │
│  M  = Month code (1 char): A=Jan, B=Feb, C=Mar...                                                                    │
│  CC = Channel code (2 chars): EC=Economical, PR=Premium                                                              │
│  SSSSSSSS = 8-digit serial number (max 99,999,999 units)                                                             │
├─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│                                      DUAL SERIES EXAMPLE                                                             │
├─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┤
│  Item: SPSDF001 (Sediment Filter)                                                                                    │
│                                                                                                                      │
│  ┌──────────────────┬────────────────────┬──────────────────────────────────────────────────────┐                    │
│  │ Supplier         │ Channel            │ Barcode Example                                      │                    │
│  ├──────────────────┼────────────────────┼──────────────────────────────────────────────────────┤                    │
│  │ FastTrack (FS)   │ Economical (EC)    │ APFSAAEC00000001                                     │                    │
│  │ STOS (ST)        │ Premium (PR)       │ APSTAAPR00000001                                     │                    │
│  └──────────────────┴────────────────────┴──────────────────────────────────────────────────────┘                    │
│                                                                                                                      │
│  Both barcodes can exist for the SAME SP CODE - different supply chain                                               │
└─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
""")

        # Print final product list
        result = await db.execute(
            select(Product)
            .where(Product.item_type == ProductItemType.SPARE_PART)
            .where(Product.is_active == True)
            .order_by(Product.fg_code)
        )
        products = result.scalars().all()

        print(f"\nTotal Spare Parts in Product Master: {len(products)}")
        print("-" * 120)
        print(f"{'S.N.':<5} {'SP CODE':<12} {'Product Name':<40} {'SKU':<15} {'Cat':<5} {'MRP':>10} {'Sell':>10}")
        print("-" * 120)

        for idx, p in enumerate(products, 1):
            print(f"{idx:<5} {p.fg_code or '-':<12} {p.name[:38]:<40} {p.sku:<15} {p.model_code or '-':<5} {float(p.mrp):>10,.2f} {float(p.selling_price):>10,.2f}")

        # Show supplier-channel mapping
        print("\n" + "=" * 120)
        print("SUPPLIER-CHANNEL MAPPING")
        print("=" * 120)
        print(f"{'Supplier Code':<15} {'Supplier Name':<25} {'Channel Code':<15} {'Category':<15}")
        print("-" * 120)
        for code, info in SUPPLIER_CHANNEL_MAP.items():
            print(f"{code:<15} {info['name']:<25} {info['channel']:<15} {info['category']:<15}")


if __name__ == "__main__":
    asyncio.run(create_spare_parts_master())
