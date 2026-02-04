"""
Product Catalog Setup Script

This script:
1. Uploads product images to Supabase Storage
2. Creates the 6 main ILMS.AI water purifier products
3. Adds specifications and images to each product

Run: python -m scripts.setup_product_catalog
"""

import os
import sys
import uuid
import asyncio
from pathlib import Path
from decimal import Decimal
from datetime import datetime, timezone

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import async_session_factory
# Import all models to ensure relationships are registered
from app.models import *
from app.models.product import Product, ProductImage, ProductSpecification, ProductDocument
from app.models.category import Category
from app.models.brand import Brand

# Try to import Supabase
try:
    from supabase import create_client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    print("Warning: Supabase not installed. Images will not be uploaded.")

# Configuration
PRODUCT_IMAGE_BASE_PATH = "/Users/mantosh/Desktop/ILMS.AI/Product Image"
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")
STORAGE_BUCKET = os.getenv("SUPABASE_STORAGE_BUCKET", "uploads")

# Product definitions with all data
PRODUCTS = [
    {
        "name": "ILMS.AI i Elitz",
        "slug": "ilms-i-elitz",
        "sku": "WPRAIEL001",
        "fg_code": "WPRAIEL001",
        "model_code": "IEL",
        "model_number": "i Elitz",
        "item_type": "FG",
        "short_description": "Hot / Cold / Ambient | 12 Stage RO+UV+UF | Alkaline + Copper & Zinc | 8L Storage",
        "description": """ILMS.AI i Elitz is our premium water purifier designed to deliver safe, healthy, and great-tasting drinking water for modern Indian households.

Featuring advanced 12-stage intelligent purification technology with RO+UV+UF, this purifier ensures complete removal of harmful contaminants while retaining essential minerals. The unique Alkaline technology maintains optimal pH balance (8.5-9.5) for better hydration and health benefits.

With Hot, Cold, and Ambient water dispensing options, i Elitz is perfect for families who want instant access to purified water at their preferred temperature. The built-in fruit and vegetable detoxifier adds extra value for health-conscious users.

Backed by ILMS.AI's trusted Pan-India service network, i Elitz ensures long-term reliability and peace of mind with no filter replacement costs for 2 years.""",
        "features": """• 12-Stage Intelligent Purification Technology
• Hot / Cold / Ambient Water Dispenser
• Balanced Alkaline Water (pH 8.5-9.5)
• Copper & Zinc Enriched Water
• 40% Water Saving vs Conventional RO
• Built-in Fruit & Vegetable Detoxifier
• 8L Purified Water Storage
• No Filter Replacement Cost for 2 Years
• BIS Compliant & ISI Certified""",
        "mrp": Decimal("29999.00"),
        "selling_price": Decimal("24999.00"),
        "dealer_price": Decimal("18999.00"),
        "cost_price": Decimal("14999.00"),
        "hsn_code": "84212110",
        "gst_rate": Decimal("18.00"),
        "warranty_months": 12,
        "extended_warranty_available": True,
        "warranty_terms": "1 Year Comprehensive Warranty. Extended warranty available for purchase.",
        "dead_weight_kg": Decimal("14.5"),
        "length_cm": Decimal("38.0"),
        "width_cm": Decimal("32.0"),
        "height_cm": Decimal("52.0"),
        "is_active": True,
        "is_featured": True,
        "is_bestseller": True,
        "is_new_arrival": True,
        "status": "ACTIVE",
        "image_folder": "Elitz",
        "image_files": ["I Elitz-1.jpg", "I Elitz-2.jpg", "I Elitz-3.jpg"],
        "specifications": [
            # General
            {"group": "General", "key": "Technology", "value": "RO + UV + UF"},
            {"group": "General", "key": "Purification Stages", "value": "12 Stages"},
            {"group": "General", "key": "Storage Capacity", "value": "8 Liters"},
            {"group": "General", "key": "Dispenser Type", "value": "Hot / Cold / Ambient"},
            {"group": "General", "key": "Suitable For", "value": "Municipal, Borewell, Tanker Water"},
            {"group": "General", "key": "Max TDS Handled", "value": "Up to 2000 ppm"},
            # Purification Features
            {"group": "Purification", "key": "Alkaline Technology", "value": "Yes (pH 8.5-9.5)"},
            {"group": "Purification", "key": "Copper Infusion", "value": "Yes"},
            {"group": "Purification", "key": "Zinc Enrichment", "value": "Yes"},
            {"group": "Purification", "key": "Detoxifier", "value": "Fruit & Vegetable Detoxifier"},
            {"group": "Purification", "key": "Water Saving", "value": "40% vs Conventional RO"},
            # Performance
            {"group": "Performance", "key": "Purification Rate", "value": "15 Liters/hour"},
            {"group": "Performance", "key": "Recovery Rate", "value": "Up to 60%"},
            {"group": "Performance", "key": "Hot Water Temp", "value": "80-90°C"},
            {"group": "Performance", "key": "Cold Water Temp", "value": "8-12°C"},
            # Electrical
            {"group": "Electrical", "key": "Input Voltage", "value": "220-240V AC, 50Hz"},
            {"group": "Electrical", "key": "Power Consumption", "value": "60W (Purification)"},
            {"group": "Electrical", "key": "Heating Power", "value": "500W"},
            {"group": "Electrical", "key": "Cooling Power", "value": "75W"},
            # Physical
            {"group": "Physical", "key": "Dimensions (LxWxH)", "value": "38 x 32 x 52 cm"},
            {"group": "Physical", "key": "Net Weight", "value": "14.5 kg"},
            {"group": "Physical", "key": "Color", "value": "White with Gold Accents"},
            # Certifications
            {"group": "Certifications", "key": "BIS Compliant", "value": "Yes"},
            {"group": "Certifications", "key": "ISI Mark", "value": "IS 14724:2020"},
        ]
    },
    {
        "name": "ILMS.AI i Premiuo",
        "slug": "ilms-i-premiuo",
        "sku": "WPRAPRE001",
        "fg_code": "WPRAPRE001",
        "model_code": "PRE",
        "model_number": "i Premiuo",
        "item_type": "FG",
        "short_description": "Hot / Ambient | 9 Stage RO+UV+UF | Alkaline + Copper & Zinc | 7L Storage",
        "description": """ILMS.AI i Premiuo combines intelligent 9-stage purification with hot and ambient water dispensing for the modern Indian kitchen.

With advanced RO+UV+UF technology and balanced alkaline output, i Premiuo delivers mineral-rich, healthy water at the perfect temperature. The DIY filter technology makes maintenance easy and cost-effective.

Designed for families who value both health and convenience, i Premiuo offers copper and zinc enriched water with 40% water saving compared to conventional RO systems.

Backed by ILMS.AI's Pan-India service network with no filter replacement costs for 2 years.""",
        "features": """• 9-Stage Intelligent Purification Technology
• Hot / Ambient Water Dispenser
• Balanced Alkaline Water (pH 8.5-9.5)
• Copper & Zinc Enriched Water
• 40% Water Saving vs Conventional RO
• DIY Filter Technology for Easy Maintenance
• 7L Purified Water Storage
• No Filter Replacement Cost for 2 Years
• BIS Compliant & ISI Certified""",
        "mrp": Decimal("24999.00"),
        "selling_price": Decimal("19999.00"),
        "dealer_price": Decimal("14999.00"),
        "cost_price": Decimal("11999.00"),
        "hsn_code": "84212110",
        "gst_rate": Decimal("18.00"),
        "warranty_months": 12,
        "extended_warranty_available": True,
        "warranty_terms": "1 Year Comprehensive Warranty. Extended warranty available for purchase.",
        "dead_weight_kg": Decimal("12.0"),
        "length_cm": Decimal("35.0"),
        "width_cm": Decimal("30.0"),
        "height_cm": Decimal("48.0"),
        "is_active": True,
        "is_featured": True,
        "is_bestseller": False,
        "is_new_arrival": True,
        "status": "ACTIVE",
        "image_folder": "I premiuo",
        "image_files": ["I premiuo-1.jpg", "I premiuo-2.jpg", "I premiuo-3.jpg"],
        "specifications": [
            {"group": "General", "key": "Technology", "value": "RO + UV + UF"},
            {"group": "General", "key": "Purification Stages", "value": "9 Stages"},
            {"group": "General", "key": "Storage Capacity", "value": "7 Liters"},
            {"group": "General", "key": "Dispenser Type", "value": "Hot / Ambient"},
            {"group": "General", "key": "Suitable For", "value": "Municipal, Borewell, Tanker Water"},
            {"group": "General", "key": "Max TDS Handled", "value": "Up to 2000 ppm"},
            {"group": "Purification", "key": "Alkaline Technology", "value": "Yes (pH 8.5-9.5)"},
            {"group": "Purification", "key": "Copper Infusion", "value": "Yes"},
            {"group": "Purification", "key": "Zinc Enrichment", "value": "Yes"},
            {"group": "Purification", "key": "DIY Filter Technology", "value": "Yes"},
            {"group": "Purification", "key": "Water Saving", "value": "40% vs Conventional RO"},
            {"group": "Performance", "key": "Purification Rate", "value": "12 Liters/hour"},
            {"group": "Performance", "key": "Hot Water Temp", "value": "80-90°C"},
            {"group": "Electrical", "key": "Input Voltage", "value": "220-240V AC, 50Hz"},
            {"group": "Electrical", "key": "Power Consumption", "value": "50W (Purification)"},
            {"group": "Electrical", "key": "Heating Power", "value": "500W"},
            {"group": "Physical", "key": "Dimensions (LxWxH)", "value": "35 x 30 x 48 cm"},
            {"group": "Physical", "key": "Net Weight", "value": "12 kg"},
            {"group": "Physical", "key": "Color", "value": "White with Blue Accents"},
            {"group": "Certifications", "key": "BIS Compliant", "value": "Yes"},
            {"group": "Certifications", "key": "ISI Mark", "value": "IS 14724:2020"},
        ]
    },
    {
        "name": "ILMS.AI Blitz",
        "slug": "ilms-blitz",
        "sku": "WPRABLT001",
        "fg_code": "WPRABLT001",
        "model_code": "BLT",
        "model_number": "Blitz",
        "item_type": "FG",
        "short_description": "RO+UV+UF | 8 Stage | Copper & Zinc | 12L Storage | Triple Protection",
        "description": """ILMS.AI Blitz brings powerful 8-stage purification with triple protection technology for families who need large capacity purified water.

Featuring RO+UV+UF technology with in-tank UV LED disinfection, Blitz ensures every drop of water is safe and healthy. The bacteriostatic copper and zinc infusion provides additional health benefits and natural preservation.

With a generous 12L storage capacity and 40% water saving, Blitz is perfect for larger families. Free TDS meter included for easy monitoring.

Backed by ILMS.AI's Pan-India service network with no filter replacement costs for 2 years.""",
        "features": """• 8-Stage Water Purifier with Triple Protection
• RO + UV + UF Technology
• In-Tank UV LED Disinfection
• Bacteriostatic Copper & Zinc Infused Water
• 40% Water Saving vs Conventional RO
• 12L Purified Water Storage
• Free TDS Meter Included
• Free Jumbo Sediment Filter (Worth ₹1099)
• No Filter Replacement Cost for 2 Years""",
        "mrp": Decimal("19999.00"),
        "selling_price": Decimal("15999.00"),
        "dealer_price": Decimal("11999.00"),
        "cost_price": Decimal("8999.00"),
        "hsn_code": "84212110",
        "gst_rate": Decimal("18.00"),
        "warranty_months": 12,
        "extended_warranty_available": True,
        "warranty_terms": "1 Year Comprehensive Warranty. Extended warranty available for purchase.",
        "dead_weight_kg": Decimal("10.5"),
        "length_cm": Decimal("40.0"),
        "width_cm": Decimal("28.0"),
        "height_cm": Decimal("45.0"),
        "is_active": True,
        "is_featured": True,
        "is_bestseller": True,
        "is_new_arrival": False,
        "status": "ACTIVE",
        "image_folder": "Blitz",
        "image_files": ["Blitz-1.jpg", "Blitz-2.jpg", "Blitz-3.jpg"],
        "specifications": [
            {"group": "General", "key": "Technology", "value": "RO + UV + UF"},
            {"group": "General", "key": "Purification Stages", "value": "8 Stages"},
            {"group": "General", "key": "Storage Capacity", "value": "12 Liters"},
            {"group": "General", "key": "Dispenser Type", "value": "Ambient"},
            {"group": "General", "key": "Suitable For", "value": "Municipal, Borewell, Tanker Water"},
            {"group": "General", "key": "Max TDS Handled", "value": "Up to 2000 ppm"},
            {"group": "Purification", "key": "Triple Protection", "value": "RO + UV + UF"},
            {"group": "Purification", "key": "Copper Infusion", "value": "Yes (Bacteriostatic)"},
            {"group": "Purification", "key": "Zinc Enrichment", "value": "Yes"},
            {"group": "Purification", "key": "In-Tank UV LED", "value": "Yes"},
            {"group": "Purification", "key": "Water Saving", "value": "40% vs Conventional RO"},
            {"group": "Performance", "key": "Purification Rate", "value": "15 Liters/hour"},
            {"group": "Electrical", "key": "Input Voltage", "value": "220-240V AC, 50Hz"},
            {"group": "Electrical", "key": "Power Consumption", "value": "45W"},
            {"group": "Physical", "key": "Dimensions (LxWxH)", "value": "40 x 28 x 45 cm"},
            {"group": "Physical", "key": "Net Weight", "value": "10.5 kg"},
            {"group": "Physical", "key": "Color", "value": "White with Black Accents"},
            {"group": "Certifications", "key": "BIS Compliant", "value": "Yes"},
            {"group": "Certifications", "key": "ISI Mark", "value": "IS 14724:2020"},
            {"group": "Freebies", "key": "TDS Meter", "value": "Included Free"},
            {"group": "Freebies", "key": "Jumbo Sediment Filter", "value": "Included Free (Worth ₹1099)"},
        ]
    },
    {
        "name": "ILMS.AI Neura",
        "slug": "ilms-neura",
        "sku": "WPRANEU001",
        "fg_code": "WPRANEU001",
        "model_code": "NEU",
        "model_number": "Neura",
        "item_type": "FG",
        "short_description": "RO+UV | 7 Stage | Copper & Zinc | 7L Storage | In-Tank UV LED",
        "description": """ILMS.AI Neura delivers essential 7-stage RO+UV purification with intelligent features at an accessible price point.

With triple protection technology and in-tank UV LED disinfection, Neura ensures consistent water safety. Bacteriostatic copper and zinc infusion provides natural antibacterial properties and essential minerals.

Perfect for small to medium families, Neura offers 7L storage with 40% water saving. Free TDS meter included for quality monitoring.

Backed by ILMS.AI's Pan-India service network with no filter replacement costs for 2 years.""",
        "features": """• 7-Stage Water Purifier with Triple Protection
• RO + UV Technology
• In-Tank UV LED Disinfection
• Bacteriostatic Copper & Zinc Infused Water
• 40% Water Saving vs Conventional RO
• 7L Purified Water Storage
• Free TDS Meter Included
• No Filter Replacement Cost for 2 Years
• BIS Compliant & ISI Certified""",
        "mrp": Decimal("14999.00"),
        "selling_price": Decimal("11999.00"),
        "dealer_price": Decimal("8999.00"),
        "cost_price": Decimal("6999.00"),
        "hsn_code": "84212110",
        "gst_rate": Decimal("18.00"),
        "warranty_months": 12,
        "extended_warranty_available": True,
        "warranty_terms": "1 Year Comprehensive Warranty. Extended warranty available for purchase.",
        "dead_weight_kg": Decimal("8.5"),
        "length_cm": Decimal("35.0"),
        "width_cm": Decimal("26.0"),
        "height_cm": Decimal("42.0"),
        "is_active": True,
        "is_featured": False,
        "is_bestseller": False,
        "is_new_arrival": False,
        "status": "ACTIVE",
        "image_folder": "Neura",
        "image_files": ["Neura-1.jpg", "Neura-2.jpg", "Neura-3.jpg"],
        "specifications": [
            {"group": "General", "key": "Technology", "value": "RO + UV"},
            {"group": "General", "key": "Purification Stages", "value": "7 Stages"},
            {"group": "General", "key": "Storage Capacity", "value": "7 Liters"},
            {"group": "General", "key": "Dispenser Type", "value": "Ambient"},
            {"group": "General", "key": "Suitable For", "value": "Municipal, Borewell, Tanker Water"},
            {"group": "General", "key": "Max TDS Handled", "value": "Up to 1500 ppm"},
            {"group": "Purification", "key": "Triple Protection", "value": "RO + UV"},
            {"group": "Purification", "key": "Copper Infusion", "value": "Yes (Bacteriostatic)"},
            {"group": "Purification", "key": "Zinc Enrichment", "value": "Yes"},
            {"group": "Purification", "key": "In-Tank UV LED", "value": "Yes"},
            {"group": "Purification", "key": "Water Saving", "value": "40% vs Conventional RO"},
            {"group": "Performance", "key": "Purification Rate", "value": "12 Liters/hour"},
            {"group": "Electrical", "key": "Input Voltage", "value": "220-240V AC, 50Hz"},
            {"group": "Electrical", "key": "Power Consumption", "value": "36W"},
            {"group": "Physical", "key": "Dimensions (LxWxH)", "value": "35 x 26 x 42 cm"},
            {"group": "Physical", "key": "Net Weight", "value": "8.5 kg"},
            {"group": "Physical", "key": "Color", "value": "White with Blue Accents"},
            {"group": "Certifications", "key": "BIS Compliant", "value": "Yes"},
            {"group": "Certifications", "key": "ISI Mark", "value": "IS 14724:2020"},
            {"group": "Freebies", "key": "TDS Meter", "value": "Included Free"},
        ]
    },
    {
        "name": "ILMS.AI Premiuo UV",
        "slug": "ilms-premiuo-uv",
        "sku": "WPRAPUV001",
        "fg_code": "WPRAPUV001",
        "model_code": "PUV",
        "model_number": "Premiuo UV",
        "item_type": "FG",
        "short_description": "UV + Copper + Magnesium + Zinc | 4 Stage | For Low TDS Water",
        "description": """ILMS.AI Premiuo UV is designed for areas with already low TDS municipal water that needs disinfection without RO.

With 4-stage UV purification enhanced with copper, magnesium, and zinc infusion, Premiuo UV delivers safe, mineral-rich water while preserving natural minerals. Ideal for metro cities with reliable municipal water supply.

No water wastage as there's no RO membrane - 100% water recovery. Perfect for environmentally conscious users who want purified water without the waste.

Backed by ILMS.AI's Pan-India service network with no filter replacement costs for 2 years.""",
        "features": """• 4-Stage UV Purification Technology
• Copper + Magnesium + Zinc Enriched Water
• Zero Water Wastage (No RO)
• 100% Water Recovery
• Ideal for Low TDS Municipal Water
• Energy Efficient
• Compact Design
• No Filter Replacement Cost for 2 Years
• BIS Compliant & ISI Certified""",
        "mrp": Decimal("9999.00"),
        "selling_price": Decimal("7999.00"),
        "dealer_price": Decimal("5999.00"),
        "cost_price": Decimal("4499.00"),
        "hsn_code": "84212110",
        "gst_rate": Decimal("18.00"),
        "warranty_months": 12,
        "extended_warranty_available": True,
        "warranty_terms": "1 Year Comprehensive Warranty. Extended warranty available for purchase.",
        "dead_weight_kg": Decimal("6.0"),
        "length_cm": Decimal("30.0"),
        "width_cm": Decimal("24.0"),
        "height_cm": Decimal("38.0"),
        "is_active": True,
        "is_featured": False,
        "is_bestseller": False,
        "is_new_arrival": False,
        "status": "ACTIVE",
        "image_folder": "Premiumem UV",
        "image_files": ["Prewmiuo UV-1.jpg", "Prewmiuo UV-2.jpg", "Prewmiuo UV-3.jpg"],
        "specifications": [
            {"group": "General", "key": "Technology", "value": "UV"},
            {"group": "General", "key": "Purification Stages", "value": "4 Stages"},
            {"group": "General", "key": "Storage Capacity", "value": "Built-in Tank"},
            {"group": "General", "key": "Dispenser Type", "value": "Ambient"},
            {"group": "General", "key": "Suitable For", "value": "Low TDS Municipal Water"},
            {"group": "General", "key": "Recommended TDS", "value": "Below 200 ppm"},
            {"group": "Purification", "key": "UV Disinfection", "value": "Yes"},
            {"group": "Purification", "key": "Copper Infusion", "value": "Yes"},
            {"group": "Purification", "key": "Magnesium", "value": "Yes"},
            {"group": "Purification", "key": "Zinc Enrichment", "value": "Yes"},
            {"group": "Purification", "key": "Water Recovery", "value": "100% (No Wastage)"},
            {"group": "Performance", "key": "Purification Rate", "value": "60 Liters/hour"},
            {"group": "Electrical", "key": "Input Voltage", "value": "220-240V AC, 50Hz"},
            {"group": "Electrical", "key": "Power Consumption", "value": "25W"},
            {"group": "Physical", "key": "Dimensions (LxWxH)", "value": "30 x 24 x 38 cm"},
            {"group": "Physical", "key": "Net Weight", "value": "6 kg"},
            {"group": "Physical", "key": "Color", "value": "White"},
            {"group": "Certifications", "key": "BIS Compliant", "value": "Yes"},
            {"group": "Certifications", "key": "ISI Mark", "value": "IS 14724:2020"},
        ]
    },
    {
        "name": "ILMS.AI Optima",
        "slug": "ilms-optima",
        "sku": "WPRAOPT001",
        "fg_code": "WPRAOPT001",
        "model_code": "OPT",
        "model_number": "Optima",
        "item_type": "FG",
        "short_description": "RO+UV+UF | 10 Stage | Alkaline + Copper & Zinc | 6.5L Storage",
        "description": """ILMS.AI Optima is our balanced mid-range purifier offering 10-stage RO+UV+UF purification with alkaline technology.

With advanced purification and alkaline pH balancing, Optima delivers healthy, mineral-rich water. Copper and zinc enrichment provides additional health benefits and natural antibacterial properties.

Compact 6.5L storage makes it ideal for small families and apartments. 40% water saving compared to conventional RO systems.

Backed by ILMS.AI's Pan-India service network with affordable spares and transparent pricing.""",
        "features": """• 10-Stage RO+UV+UF Purification
• Balanced Alkaline Water (pH 8.5-9.5)
• Copper & Zinc Enriched Water
• 40% Water Saving vs Conventional RO
• 6.5L Purified Water Storage
• Compact Design for Small Spaces
• Smart LED Indicators
• No Filter Replacement Cost for 2 Years
• BIS Compliant & ISI Certified""",
        "mrp": Decimal("17999.00"),
        "selling_price": Decimal("13999.00"),
        "dealer_price": Decimal("10499.00"),
        "cost_price": Decimal("7999.00"),
        "hsn_code": "84212110",
        "gst_rate": Decimal("18.00"),
        "warranty_months": 12,
        "extended_warranty_available": True,
        "warranty_terms": "1 Year Comprehensive Warranty. Extended warranty available for purchase.",
        "dead_weight_kg": Decimal("9.0"),
        "length_cm": Decimal("33.0"),
        "width_cm": Decimal("27.0"),
        "height_cm": Decimal("43.0"),
        "is_active": True,
        "is_featured": True,
        "is_bestseller": False,
        "is_new_arrival": False,
        "status": "ACTIVE",
        "image_folder": None,  # No folder yet - uses optima image.jp2
        "image_files": [],
        "specifications": [
            {"group": "General", "key": "Technology", "value": "RO + UV + UF"},
            {"group": "General", "key": "Purification Stages", "value": "10 Stages"},
            {"group": "General", "key": "Storage Capacity", "value": "6.5 Liters"},
            {"group": "General", "key": "Dispenser Type", "value": "Ambient"},
            {"group": "General", "key": "Suitable For", "value": "Municipal, Borewell, Tanker Water"},
            {"group": "General", "key": "Max TDS Handled", "value": "Up to 2000 ppm"},
            {"group": "Purification", "key": "Alkaline Technology", "value": "Yes (pH 8.5-9.5)"},
            {"group": "Purification", "key": "Copper Infusion", "value": "Yes"},
            {"group": "Purification", "key": "Zinc Enrichment", "value": "Yes"},
            {"group": "Purification", "key": "Water Saving", "value": "40% vs Conventional RO"},
            {"group": "Performance", "key": "Purification Rate", "value": "12 Liters/hour"},
            {"group": "Electrical", "key": "Input Voltage", "value": "220-240V AC, 50Hz"},
            {"group": "Electrical", "key": "Power Consumption", "value": "40W"},
            {"group": "Physical", "key": "Dimensions (LxWxH)", "value": "33 x 27 x 43 cm"},
            {"group": "Physical", "key": "Net Weight", "value": "9 kg"},
            {"group": "Physical", "key": "Color", "value": "White with Gold Accents"},
            {"group": "Certifications", "key": "BIS Compliant", "value": "Yes"},
            {"group": "Certifications", "key": "ISI Mark", "value": "IS 14724:2020"},
        ]
    },
]


def get_supabase_client():
    """Get Supabase client for storage operations."""
    if not SUPABASE_AVAILABLE:
        return None
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("Warning: Supabase credentials not configured")
        return None
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def upload_image_to_supabase(client, local_path: str, storage_path: str) -> str | None:
    """Upload image to Supabase Storage and return public URL."""
    if not client:
        return None

    try:
        with open(local_path, "rb") as f:
            file_data = f.read()

        # Get content type
        ext = local_path.lower().split(".")[-1]
        content_types = {
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "png": "image/png",
            "webp": "image/webp",
        }
        content_type = content_types.get(ext, "image/jpeg")

        # Upload to Supabase
        result = client.storage.from_(STORAGE_BUCKET).upload(
            storage_path,
            file_data,
            {"content-type": content_type, "upsert": "true"}
        )

        # Get public URL
        public_url = client.storage.from_(STORAGE_BUCKET).get_public_url(storage_path)
        print(f"  ✓ Uploaded: {storage_path}")
        return public_url

    except Exception as e:
        print(f"  ✗ Failed to upload {local_path}: {e}")
        return None


async def get_or_create_category(db: AsyncSession, name: str = "Water Purifiers") -> uuid.UUID:
    """Get or create the Water Purifiers category."""
    result = await db.execute(
        select(Category).where(Category.name == name)
    )
    category = result.scalar_one_or_none()

    if not category:
        category = Category(
            name=name,
            slug="water-purifiers",
            description="Premium water purifiers for home and office",
            is_active=True,
            sort_order=1
        )
        db.add(category)
        await db.flush()
        print(f"Created category: {name}")

    return category.id


async def get_or_create_brand(db: AsyncSession, name: str = "ILMS.AI") -> uuid.UUID:
    """Get or create the ILMS.AI brand."""
    result = await db.execute(
        select(Brand).where(Brand.name == name)
    )
    brand = result.scalar_one_or_none()

    if not brand:
        brand = Brand(
            name=name,
            slug="ilms",
            description="India's trusted water purification brand",
            is_active=True
        )
        db.add(brand)
        await db.flush()
        print(f"Created brand: {name}")

    return brand.id


async def setup_products():
    """Main function to setup all products."""
    print("\n" + "="*60)
    print("ILMS.AI PRODUCT CATALOG SETUP")
    print("="*60 + "\n")

    # Initialize Supabase client
    supabase = get_supabase_client()
    if supabase:
        print("✓ Supabase client initialized")
    else:
        print("⚠ Supabase not available - images will not be uploaded")

    async with async_session_factory() as db:
        # Get or create category and brand
        category_id = await get_or_create_category(db)
        brand_id = await get_or_create_brand(db)

        print(f"\nCategory ID: {category_id}")
        print(f"Brand ID: {brand_id}\n")

        for product_data in PRODUCTS:
            print(f"\n--- Processing: {product_data['name']} ---")

            # Check if product exists by SKU, fg_code, or slug
            result = await db.execute(
                select(Product).where(
                    (Product.sku == product_data["sku"]) |
                    (Product.fg_code == product_data.get("fg_code")) |
                    (Product.slug == product_data.get("slug"))
                )
            )
            product = result.scalar_one_or_none()

            if product:
                print(f"  Product exists (id={product.id}), updating...")
            else:
                print(f"  Creating new product...")
                product = Product(
                    id=uuid.uuid4(),
                    category_id=category_id,
                    brand_id=brand_id,
                )
                db.add(product)

            # Update product fields
            for key in ["name", "slug", "sku", "fg_code", "model_code", "model_number",
                       "item_type", "short_description", "description", "features",
                       "mrp", "selling_price", "dealer_price", "cost_price",
                       "hsn_code", "gst_rate", "warranty_months", "extended_warranty_available",
                       "warranty_terms", "dead_weight_kg", "length_cm", "width_cm", "height_cm",
                       "is_active", "is_featured", "is_bestseller", "is_new_arrival", "status"]:
                if key in product_data:
                    setattr(product, key, product_data[key])

            product.published_at = datetime.now(timezone.utc)
            await db.flush()

            # Clear existing specifications
            await db.execute(
                ProductSpecification.__table__.delete().where(
                    ProductSpecification.product_id == product.id
                )
            )

            # Add specifications
            print(f"  Adding {len(product_data['specifications'])} specifications...")
            for i, spec in enumerate(product_data["specifications"]):
                spec_obj = ProductSpecification(
                    product_id=product.id,
                    group_name=spec["group"],
                    key=spec["key"],
                    value=spec["value"],
                    sort_order=i
                )
                db.add(spec_obj)

            # Upload and add images
            if product_data["image_folder"] and product_data["image_files"]:
                # Clear existing images
                await db.execute(
                    ProductImage.__table__.delete().where(
                        ProductImage.product_id == product.id
                    )
                )

                print(f"  Uploading {len(product_data['image_files'])} images...")
                for i, image_file in enumerate(product_data["image_files"]):
                    local_path = os.path.join(
                        PRODUCT_IMAGE_BASE_PATH,
                        product_data["image_folder"],
                        image_file
                    )

                    if os.path.exists(local_path):
                        # Upload to Supabase
                        storage_path = f"products/{product_data['slug']}/{image_file.lower().replace(' ', '-')}"
                        image_url = upload_image_to_supabase(supabase, local_path, storage_path)

                        if image_url:
                            image_obj = ProductImage(
                                product_id=product.id,
                                image_url=image_url,
                                alt_text=f"{product_data['name']} - View {i+1}",
                                is_primary=(i == 0),
                                sort_order=i
                            )
                            db.add(image_obj)
                    else:
                        print(f"  ⚠ Image not found: {local_path}")

            print(f"  ✓ {product_data['name']} complete")

        # Commit all changes
        await db.commit()
        print("\n" + "="*60)
        print("✓ ALL PRODUCTS SETUP COMPLETE")
        print("="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(setup_products())
