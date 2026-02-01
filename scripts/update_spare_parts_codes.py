"""
Update spare parts with HSN codes and Part codes from STOS Proforma Invoice.
Based on STOS PI No: STOS-001/25-26 dated 26-12-2025

HSN Code: 84212190 - Water filtering/purifying machinery and apparatus parts
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from decimal import Decimal
from sqlalchemy import select, update
from app.database import async_session_factory
from app.models.product import Product

# STOS Part Code Mapping from PI
# Format: (our_sku_pattern, part_code, hsn_code, description)
STOS_PART_CODES = [
    # From STOS PI STOS-001/25-26
    ("SP-SDF-YRN", "AFGPSW2001", "84212190", "Sediment Woven Filter Assy (Grey)"),
    ("SP-SDF-SPN", "AFGRSS2501", "84212190", "Sediment Spun Filter Assy (White)"),
    ("SP-PCB-PRM", "AFGPPR2002", "84212190", "Pre Carbon Filter Assy (Grey/Premium)"),
    ("SP-PCB-REG", "AFGRPR2502", "84212190", "Pre Carbon Filter Assy (White/Regular)"),
    ("SP-ALK-PRM", "AFGALK2004", "84212190", "Alkaline Mineral Filter Assy (Grey)"),
    ("SP-POC-COP", "AFGRPC2504", "84212190", "Post Carbon Copper Assy (White)"),
    ("SP-MBR-PRM", "AFGPMH2003", "84212190", "Membrane Filter Assy (Grey/Premium)"),
    ("SP-MBR-REG", "AFGRMF2503", "84212190", "Membrane Filter Assy (White/Regular)"),
    ("SP-PFC-MLT", "AFGPPF2005", "84212190", "Pre Filter Assembly (Grey) - Premium"),
    ("SP-PFA-SPN", "AFGRPF2505", "84212190", "Pre Filter Assembly (Black) - Regular"),
    ("SP-HMR", "AFGHMR2007", "84212190", "HMR & Sediment Pre-Filter Jumbo Assembly"),
    ("SP-PFA-MLC", "AFGIRN2006", "84212190", "Iron Remover & Sediment Pre-Filter Jumbo"),
    ("SP-HMR-BLK", "AFGHMR2007", "84212190", "HMR Assembly (Black)"),
    ("SP-PRV-PLS", "AFGPRV3001", "84212190", "Plastic PRV"),
    ("SP-DVV-BRS", "AFGBDV3002", "84212190", "Brass Diverter Valve"),
]

# All water purifier parts use this HSN code
DEFAULT_HSN_CODE = "84212190"

async def update_spare_parts():
    """Update spare parts products with HSN codes and Part codes."""
    async with async_session_factory() as db:
        # Get all spare parts
        result = await db.execute(
            select(Product).where(Product.sku.like("SP-%"))
        )
        products = result.scalars().all()

        print(f"Found {len(products)} spare parts\n")

        updated_count = 0
        for product in products:
            # Find matching part code
            part_code = None
            for sku_pattern, code, hsn, desc in STOS_PART_CODES:
                if product.sku.startswith(sku_pattern):
                    part_code = code
                    break

            # Update product
            product.hsn_code = DEFAULT_HSN_CODE
            if part_code:
                product.part_code = part_code

            print(f"  Updated: {product.sku} -> HSN: {DEFAULT_HSN_CODE}, Part Code: {part_code or 'N/A'}")
            updated_count += 1

        await db.commit()
        print(f"\n✓ Updated {updated_count} spare parts with HSN codes")

        # Also update purchase order items for STOS PO
        print("\n--- Updating Purchase Order Items ---")
        from app.models.purchase import PurchaseOrderItem, PurchaseOrder

        # Get STOS PO
        result = await db.execute(
            select(PurchaseOrder).where(PurchaseOrder.po_number == "PO-2026-00006")
        )
        stos_po = result.scalars().first()

        if stos_po:
            result = await db.execute(
                select(PurchaseOrderItem).where(PurchaseOrderItem.purchase_order_id == stos_po.id)
            )
            po_items = result.scalars().all()

            for item in po_items:
                # Find matching part code
                part_code = None
                for sku_pattern, code, hsn, desc in STOS_PART_CODES:
                    if item.sku.startswith(sku_pattern):
                        part_code = code
                        break

                item.hsn_code = DEFAULT_HSN_CODE
                if part_code:
                    item.part_code = part_code

                print(f"  PO Item: {item.sku} -> HSN: {DEFAULT_HSN_CODE}, Part Code: {part_code or 'N/A'}")

            await db.commit()
            print(f"\n✓ Updated {len(po_items)} PO items with HSN codes")
        else:
            print("  STOS PO (PO-2026-00006) not found")

if __name__ == "__main__":
    asyncio.run(update_spare_parts())
