"""Script to generate serial numbers/barcodes for an existing approved PO."""
import asyncio
import os
import sys
import uuid

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from datetime import datetime

# Production database URL
DATABASE_URL = os.environ.get("DATABASE_URL", "")

if not DATABASE_URL:
    print("ERROR: Set DATABASE_URL environment variable")
    exit(1)

# Ensure correct driver
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://")
elif DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+psycopg://")

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


# Barcode generation helpers
YEAR_CODES = {
    2024: "A", 2025: "B", 2026: "C", 2027: "D", 2028: "E", 2029: "F", 2030: "G",
    2031: "H", 2032: "I", 2033: "J", 2034: "K", 2035: "L"
}

MONTH_CODES = {
    1: "A", 2: "B", 3: "C", 4: "D", 5: "E", 6: "F",
    7: "G", 8: "H", 9: "I", 10: "J", 11: "K", 12: "L"
}


def get_year_code():
    return YEAR_CODES.get(datetime.now().year, "X")


def get_month_code():
    return MONTH_CODES.get(datetime.now().month, "X")


def generate_barcode(supplier_code, year_code, month_code, model_code, serial_number, item_type="SPARE_PART"):
    """Generate barcode in format: APSTCASDF00000001"""
    brand_prefix = "AP"
    if item_type == "SPARE_PART":
        # Spare parts: AP + 2-letter supplier + 1-letter year + 1-letter month + 3-letter model + 8-digit serial
        return f"{brand_prefix}{supplier_code.upper()}{year_code}{month_code}{model_code.upper()}{serial_number:08d}"
    else:
        # FG: Similar format
        return f"{brand_prefix}{supplier_code.upper()}{year_code}{month_code}{model_code.upper()}{serial_number:08d}"


async def generate_serials_for_po(po_number: str):
    """Generate serial numbers for a specific PO."""
    async with async_session() as session:
        # Get PO details
        result = await session.execute(
            text("""
                SELECT po.id, po.po_number, po.status, po.vendor_id
                FROM purchase_orders po
                WHERE po.po_number = :po_number
            """),
            {"po_number": po_number}
        )
        po = result.fetchone()

        if not po:
            print(f"PO {po_number} not found!")
            return

        print(f"Found PO: {po.po_number} (Status: {po.status})")
        po_id = po.id
        vendor_id = po.vendor_id

        # Get supplier code
        result = await session.execute(
            text("SELECT code FROM supplier_codes WHERE vendor_id = :vendor_id"),
            {"vendor_id": str(vendor_id)}
        )
        sc = result.fetchone()
        supplier_code = sc.code if sc else "XX"
        print(f"Supplier code: {supplier_code}")

        # Check existing serials
        result = await session.execute(
            text("SELECT COUNT(*) FROM po_serials WHERE po_id = :po_id"),
            {"po_id": str(po_id)}
        )
        existing_count = result.scalar()
        print(f"Existing serials for this PO: {existing_count}")

        if existing_count > 0:
            print("Serials already exist for this PO. Skipping generation.")
            return

        # Get PO items with model codes
        result = await session.execute(
            text("""
                SELECT poi.id, poi.sku, poi.quantity_ordered, poi.product_id,
                       mcr.model_code, mcr.fg_code
                FROM purchase_order_items poi
                LEFT JOIN model_code_references mcr ON poi.product_id::text = mcr.product_id::text
                WHERE poi.purchase_order_id = :po_id
            """),
            {"po_id": str(po_id)}
        )
        items = result.fetchall()

        print(f"Found {len(items)} line items")

        year_code = get_year_code()
        month_code = get_month_code()
        print(f"Using year code: {year_code}, month code: {month_code}")

        total_serials = 0

        for item in items:
            sku = item.sku
            qty = item.quantity_ordered
            product_id = item.product_id
            model_code = item.model_code if item.model_code else sku[:3].upper()

            print(f"\n  Processing SKU: {sku}, Model: {model_code}, Quantity: {qty}")

            # Get or create product serial sequence
            result = await session.execute(
                text("""
                    SELECT id, last_serial FROM product_serial_sequences
                    WHERE model_code = :model_code
                """),
                {"model_code": model_code}
            )
            seq = result.fetchone()

            if seq:
                start_serial = (seq.last_serial or 0) + 1
                seq_id = seq.id
            else:
                # Create new sequence
                seq_id = str(uuid.uuid4())
                start_serial = 1
                await session.execute(
                    text("""
                        INSERT INTO product_serial_sequences
                        (id, model_code, product_sku, item_type, last_serial, total_generated, created_at, updated_at)
                        VALUES (:id, :model_code, :sku, 'SPARE_PART', 0, 0, NOW(), NOW())
                    """),
                    {"id": seq_id, "model_code": model_code, "sku": sku}
                )

            end_serial = start_serial + qty - 1
            print(f"    Serial range: {start_serial} to {end_serial}")

            # Generate serials in batches for efficiency
            batch_size = 500
            for batch_start in range(0, qty, batch_size):
                batch_end = min(batch_start + batch_size, qty)

                for i in range(batch_start, batch_end):
                    serial_num = start_serial + i
                    barcode = generate_barcode(supplier_code, year_code, month_code, model_code, serial_num)

                    await session.execute(
                        text("""
                            INSERT INTO po_serials
                            (id, po_id, po_item_id, product_id, product_sku, model_code, item_type,
                             brand_prefix, supplier_code, year_code, month_code, serial_number, barcode,
                             status, created_at, updated_at)
                            VALUES
                            (:id, :po_id, :po_item_id, :product_id, :sku, :model_code, 'SPARE_PART',
                             'AP', :supplier_code, :year_code, :month_code, :serial_number, :barcode,
                             'GENERATED', NOW(), NOW())
                        """),
                        {
                            "id": str(uuid.uuid4()),
                            "po_id": str(po_id),
                            "po_item_id": str(item.id),
                            "product_id": str(product_id) if product_id else None,
                            "sku": sku,
                            "model_code": model_code,
                            "supplier_code": supplier_code,
                            "year_code": year_code,
                            "month_code": month_code,
                            "serial_number": serial_num,
                            "barcode": barcode,
                        }
                    )
                    total_serials += 1

                # Commit after each batch
                await session.commit()
                print(f"    Generated {min(batch_end, qty)}/{qty} serials...")

            # Update sequence
            await session.execute(
                text("""
                    UPDATE product_serial_sequences
                    SET last_serial = :end_serial,
                        total_generated = total_generated + :qty,
                        updated_at = NOW()
                    WHERE id = :id
                """),
                {"end_serial": end_serial, "qty": qty, "id": seq_id}
            )
            await session.commit()

        print(f"\n✓ Successfully generated {total_serials} serial numbers/barcodes!")

        # Verify and show sample
        result = await session.execute(
            text("SELECT serial_number, barcode, model_code, product_sku FROM po_serials WHERE po_id = :po_id ORDER BY created_at LIMIT 10"),
            {"po_id": str(po_id)}
        )
        serials = result.fetchall()
        print("\nFirst 10 serials generated:")
        for s in serials:
            print(f"  {s.barcode} (SKU: {s.product_sku}, Model: {s.model_code})")


if __name__ == "__main__":
    po_number = sys.argv[1] if len(sys.argv) > 1 else "PO-20260113-0001"
    asyncio.run(generate_serials_for_po(po_number))
