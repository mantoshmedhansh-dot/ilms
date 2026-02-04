"""
Demo: Product Code & Barcode Generation for Spare Parts Division

All Barcodes are 16 characters with 8-digit serial numbers.

Two Barcode Formats:

1. FINISHED GOODS (FG) - 16 characters:
   Format: APAAAIIEL00000001
   - AP: Brand Prefix (2 chars)
   - AA: Year Code (2 chars)
   - A: Month Code (1 char)
   - IEL: Model Code (3 chars)
   - 00000001: Serial Number (8 digits)

2. SPARE PARTS (SP) - 16 characters:
   Format: APFSAAEC00000001
   - AP: Brand Prefix (2 chars)
   - FS/ST: Supplier Code (2 chars)
   - A: Year Code (1 char - single letter)
   - A: Month Code (1 char)
   - EC/PR: Channel Code (2 chars)
   - 00000001: Serial Number (8 digits)

Spare Parts Categories:
- Economical (EC): Supplied by FastTrack (FS)
- Premium (PR): Supplied by STOS (ST)

Same item code can have TWO barcode series:
- SPPRG001 → APFSAAEC00000001 (Economical from FastTrack)
- SPPRG001 → APSTAAPR00000001 (Premium from STOS)
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.serialization import SerializationService
from app.models.serialization import ItemType


def demo_barcode_generation():
    """Demonstrate the barcode generation logic (no DB needed)."""

    print("=" * 70)
    print("BARCODE GENERATION DEMO - 16 CHARACTER FORMAT")
    print("=" * 70)

    # Create a mock service just for the generation methods
    class MockDB:
        pass

    service = SerializationService(MockDB())

    # Current year/month codes
    year_code = service.get_year_code()  # AA for 2026
    year_code_single = service.get_year_code_single()  # A for 2026 (wraps)
    month_code = service.get_month_code()  # A for January

    print(f"\nCurrent Date Codes:")
    print(f"  Year Code (FG, 2-char): {year_code} (Year {service.parse_year_code(year_code)})")
    print(f"  Year Code (SP, 1-char): {year_code_single}")
    print(f"  Month Code: {month_code} (Month {service.parse_month_code(month_code)})")

    # ==================== FG Barcode Structure ====================
    print("\n" + "=" * 70)
    print("1. FINISHED GOODS (FG) BARCODE - 16 CHARACTERS")
    print("=" * 70)
    print("""
Format: APAAAIIEL00000001

┌──┬──┬─┬───┬────────┐
│AP│AA│A│IEL│00000001│
└──┴──┴─┴───┴────────┘
 │  │  │  │     │
 │  │  │  │     └─ Serial Number (8 digits, 00000001-99999999)
 │  │  │  └─────── Model Code (3 chars: IEL=i Elitz, PRG=Puro Guard)
 │  │  └────────── Month Code (A=Jan...L=Dec)
 │  └───────────── Year Code (2 chars: A-Z then AA, AB...)
 └──────────────── Brand Prefix (AP = ILMS.AI)
    """)

    # Generate sample FG barcodes
    print("Sample FG Barcodes:")
    print("-" * 50)
    models = [
        ("IEL", "i Elitz"),
        ("IPR", "i Premiuo"),
        ("BLT", "Blitz"),
        ("NEU", "Neura"),
    ]
    for model_code, model_name in models:
        barcode = service.generate_fg_barcode(
            year_code=year_code,
            month_code=month_code,
            model_code=model_code,
            serial_number=1,
        )
        print(f"  {model_name:<12} → {barcode} ({len(barcode)} chars)")

    # ==================== Spare Parts Barcode Structure ====================
    print("\n" + "=" * 70)
    print("2. SPARE PARTS (SP) BARCODE - 16 CHARACTERS")
    print("=" * 70)
    print("""
Format: APFSAAEC00000001

┌──┬──┬─┬─┬──┬────────┐
│AP│FS│A│A│EC│00000001│
└──┴──┴─┴─┴──┴────────┘
 │  │  │ │ │     │
 │  │  │ │ │     └─ Serial Number (8 digits)
 │  │  │ │ └─────── Channel Code (EC=Economical, PR=Premium)
 │  │  │ └───────── Month Code (A=Jan...L=Dec)
 │  │  └──────────── Year Code (1 char only, wraps after Z)
 │  └─────────────── Supplier Code (FS=FastTrack, ST=STOS)
 └────────────────── Brand Prefix (AP = ILMS.AI)

Supplier-Channel Mapping:
  FS (FastTrack) → EC (Economical)
  ST (STOS)      → PR (Premium)
    """)

    # ==================== Dual Series for Same Item ====================
    print("\n" + "=" * 70)
    print("3. DUAL SERIES - Same Item, Different Suppliers")
    print("=" * 70)
    print("""
The same spare part item can have TWO barcode series based on supplier:

Item Code: SPPRG001 (Puro Guard Filter)
    """)

    # Generate sample spare parts barcodes for both channels
    spare_items = [
        ("SPPRG001", "Puro Guard Filter"),
        ("SPSDF001", "Sediment Filter"),
        ("SPMBF001", "Membrane Filter"),
        ("SPPRV001", "Plastic PRV"),
    ]

    print(f"{'Item Code':<12} {'Economical (FastTrack)':<24} {'Premium (STOS)':<24}")
    print("-" * 70)

    for item_code, item_name in spare_items:
        # Economical barcode (FastTrack)
        ec_barcode = service.generate_spare_barcode(
            supplier_code="FS",
            year_code=year_code_single,
            month_code=month_code,
            channel_code="EC",
            serial_number=1,
        )
        # Premium barcode (STOS)
        pr_barcode = service.generate_spare_barcode(
            supplier_code="ST",
            year_code=year_code_single,
            month_code=month_code,
            channel_code="PR",
            serial_number=1,
        )
        print(f"{item_code:<12} {ec_barcode:<24} {pr_barcode:<24}")

    # ==================== Barcode Parsing ====================
    print("\n" + "=" * 70)
    print("4. BARCODE PARSING")
    print("=" * 70)

    # Parse FG barcode
    fg_sample = f"AP{year_code}{month_code}IEL00000150"
    print(f"\nFG Barcode: {fg_sample}")
    print("-" * 40)
    fg_parsed = service.parse_fg_barcode(fg_sample)
    for key, value in fg_parsed.items():
        print(f"  {key:<15}: {value}")

    # Parse Spare barcode (Economical)
    sp_ec_sample = f"APFS{year_code_single}{month_code}EC00000150"
    print(f"\nSpare (Economical): {sp_ec_sample}")
    print("-" * 40)
    sp_ec_parsed = service.parse_spare_barcode(sp_ec_sample)
    for key, value in sp_ec_parsed.items():
        print(f"  {key:<15}: {value}")

    # Parse Spare barcode (Premium)
    sp_pr_sample = f"APST{year_code_single}{month_code}PR00000150"
    print(f"\nSpare (Premium): {sp_pr_sample}")
    print("-" * 40)
    sp_pr_parsed = service.parse_spare_barcode(sp_pr_sample)
    for key, value in sp_pr_parsed.items():
        print(f"  {key:<15}: {value}")

    # ==================== Serial Range Example ====================
    print("\n" + "=" * 70)
    print("5. PURCHASE ORDER SERIAL GENERATION EXAMPLE")
    print("=" * 70)
    print(f"""
When a PO is created, serials are generated based on supplier:

PO for FastTrack (Economical):
┌─────────────────────────────────────────────────────────────────────────┐
│ PO Number: PO-2026-00015                                                 │
│ Vendor: FastTrack Filtration (FS) → Channel: EC (Economical)             │
├───────────────────────────┬──────┬───────────────────────────────────────┤
│ Item                      │ Qty  │ Serial Range                          │
├───────────────────────────┼──────┼───────────────────────────────────────┤
│ Sediment Filter - SPSDF   │ 2000 │ APFS{year_code_single}{month_code}EC00000001 - APFS{year_code_single}{month_code}EC00002000   │
│ Membrane Filter - SPMBF   │ 2000 │ APFS{year_code_single}{month_code}EC00000001 - APFS{year_code_single}{month_code}EC00002000   │
└───────────────────────────┴──────┴───────────────────────────────────────┘

PO for STOS Industrial (Premium):
┌─────────────────────────────────────────────────────────────────────────┐
│ PO Number: PO-2026-00016                                                 │
│ Vendor: STOS Industrial (ST) → Channel: PR (Premium)                     │
├───────────────────────────┬──────┬───────────────────────────────────────┤
│ Item                      │ Qty  │ Serial Range                          │
├───────────────────────────┼──────┼───────────────────────────────────────┤
│ Sediment Filter - SPSDF   │ 2000 │ APST{year_code_single}{month_code}PR00000001 - APST{year_code_single}{month_code}PR00002000   │
│ Membrane Filter - SPMBF   │ 2000 │ APST{year_code_single}{month_code}PR00000001 - APST{year_code_single}{month_code}PR00002000   │
└───────────────────────────┴──────┴───────────────────────────────────────┘
    """)

    # ==================== Summary ====================
    print("\n" + "=" * 70)
    print("6. SUMMARY")
    print("=" * 70)
    print(f"""
BARCODE STRUCTURE (Both 16 characters):

┌─────────────┬────────────────────────────┬──────────────────────────────┐
│ Type        │ FG (Finished Goods)        │ SP (Spare Parts)             │
├─────────────┼────────────────────────────┼──────────────────────────────┤
│ Format      │ AP + YY + M + MMM + SSSSSSSS│ AP + SS + Y + M + CC + SSSSSSSS│
│ Example     │ APAAAIIEL00000001          │ APFSAAEC00000001             │
│ Length      │ 16 chars                   │ 16 chars                     │
├─────────────┼────────────────────────────┼──────────────────────────────┤
│ Brand (AP)  │ 2 chars                    │ 2 chars                      │
│ Year        │ 2 chars (AA, AB...)        │ 1 char (A-Z, wraps)          │
│ Month       │ 1 char (A-L)               │ 1 char (A-L)                 │
│ Model       │ 3 chars (IEL, PRG...)      │ N/A                          │
│ Supplier    │ N/A                        │ 2 chars (FS, ST)             │
│ Channel     │ N/A                        │ 2 chars (EC, PR)             │
│ Serial      │ 8 digits (max 99,999,999)  │ 8 digits (max 99,999,999)    │
└─────────────┴────────────────────────────┴──────────────────────────────┘

SUPPLIER-CHANNEL MAPPING:
  FS (FastTrack Filtration) → EC (Economical)
  ST (STOS Industrial)      → PR (Premium)

ITEM CODE STRUCTURE:
  SP + PRG + 001 = SPPRG001 (Spare Part + Model + Sequence)

API ENDPOINTS:
  POST /api/v1/serialization/generate         - Generate serials for PO
  POST /api/v1/serialization/preview          - Preview barcodes
  GET  /api/v1/serialization/po/{{po_id}}     - Get PO serials
  GET  /api/v1/serialization/po/{{po_id}}/export - Export as CSV
  POST /api/v1/serialization/scan             - Scan during GRN
  GET  /api/v1/serialization/lookup/{{barcode}} - Lookup serial details
    """)

    print("=" * 70)
    print("DEMO COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    demo_barcode_generation()
