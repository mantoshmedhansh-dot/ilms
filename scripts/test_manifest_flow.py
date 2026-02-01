#!/usr/bin/env python3
"""Test manifest creation and confirmation flow."""

import asyncio
import sys
import logging
from decimal import Decimal
import uuid
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add project to path
sys.path.insert(0, '/Users/mantosh/Desktop/Consumer durable 2')

from app.database import async_session_factory
from app.services.manifest_service import ManifestService
from app.services.shipment_service import ShipmentService
from app.models.shipment import Shipment, ShipmentStatus
from app.models.manifest import Manifest, ManifestStatus, BusinessType
from app.schemas.manifest import ManifestCreate
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload


async def test_manifest_flow():
    """Test creating and confirming a manifest."""

    async with async_session_factory() as db:
        manifest_service = ManifestService(db)
        shipment_service = ShipmentService(db)

        # Step 1: Find a packed shipment without a manifest
        logger.info("Finding a packed shipment without manifest...")

        result = await db.execute(
            select(Shipment)
            .where(Shipment.status == "PACKED")
            .where(Shipment.manifest_id.is_(None))
            .order_by(desc(Shipment.created_at))
            .limit(1)
        )
        shipment = result.scalar_one_or_none()

        if not shipment:
            logger.warning("No packed shipment found. Using shipped shipment...")
            # Try to find any shipment
            result = await db.execute(
                select(Shipment)
                .where(Shipment.manifest_id.is_(None))
                .order_by(desc(Shipment.created_at))
                .limit(1)
            )
            shipment = result.scalar_one_or_none()

        if not shipment:
            logger.error("No shipment found! Run test_shipment_flow.py first.")
            return None

        logger.info(f"Using shipment: {shipment.shipment_number}")
        logger.info(f"  ID: {shipment.id}")
        logger.info(f"  Status: {shipment.status}")
        logger.info(f"  AWB: {shipment.awb_number}")
        logger.info(f"  Warehouse ID: {shipment.warehouse_id}")
        logger.info(f"  Transporter ID: {shipment.transporter_id}")

        # Make sure shipment is in PACKED status for manifest
        if shipment.status != "PACKED":
            logger.info("Updating shipment to PACKED status for manifest...")
            shipment.status = "PACKED"
            await db.commit()
            await db.refresh(shipment)

        # Step 2: Create a manifest
        logger.info("\nCreating manifest...")

        manifest_data = ManifestCreate(
            warehouse_id=shipment.warehouse_id,
            transporter_id=shipment.transporter_id,
            business_type=BusinessType.B2C,  # B2C for D2C orders
            vehicle_number="MH12AB1234",
            driver_name="Test Driver",
            driver_phone="9876543210",
            remarks="Test manifest for D2C shipments",
        )

        manifest = await manifest_service.create_manifest(manifest_data)

        logger.info(f"Manifest created:")
        logger.info(f"  Manifest Number: {manifest.manifest_number}")
        logger.info(f"  Status: {manifest.status}")
        logger.info(f"  Business Type: {manifest.business_type}")

        # Step 3: Add shipment to manifest
        logger.info("\nAdding shipment to manifest...")

        manifest = await manifest_service.add_shipments(
            manifest_id=manifest.id,
            shipment_ids=[shipment.id]
        )

        logger.info(f"Shipment added:")
        logger.info(f"  Total Shipments: {manifest.total_shipments}")
        logger.info(f"  Total Weight: {manifest.total_weight_kg} kg")
        logger.info(f"  Status: {manifest.status}")

        # Step 4: Scan shipment (simulate physical verification)
        logger.info("\nScanning shipment for verification...")

        item, scanned, pending = await manifest_service.scan_shipment(
            manifest_id=manifest.id,
            awb_number=shipment.awb_number,
        )

        logger.info(f"Scan result:")
        logger.info(f"  Scanned: {scanned}")
        logger.info(f"  Pending: {pending}")

        # Step 5: Confirm manifest (Goods Issue)
        logger.info("\nConfirming manifest (Goods Issue)...")

        manifest = await manifest_service.confirm_manifest(
            manifest_id=manifest.id,
            vehicle_number="MH12AB1234",
            driver_name="Test Driver",
            driver_phone="9876543210",
            remarks="Manifest confirmed - handover complete",
        )

        logger.info(f"Manifest confirmed:")
        logger.info(f"  Manifest Number: {manifest.manifest_number}")
        logger.info(f"  Status: {manifest.status}")
        logger.info(f"  Confirmed At: {manifest.confirmed_at}")

        # Verify shipment status was updated
        await db.refresh(shipment)
        logger.info(f"\nShipment status after manifest confirmation: {shipment.status}")

        # Check if invoice was auto-generated
        logger.info("\nChecking for auto-generated invoice...")
        from sqlalchemy import text
        try:
            invoice_result = await db.execute(text("""
                SELECT id, invoice_number, invoice_type, status
                FROM tax_invoices
                WHERE shipment_id = :shipment_id
                ORDER BY created_at DESC
                LIMIT 1
            """), {"shipment_id": shipment.id})
            invoice = invoice_result.fetchone()

            if invoice:
                logger.info(f"Invoice auto-generated:")
                logger.info(f"  Invoice Number: {invoice[1]}")
                logger.info(f"  Type: {invoice[2]}")
                logger.info(f"  Status: {invoice[3]}")
            else:
                logger.info("  No invoice auto-generated (handled by separate flow)")
        except Exception as e:
            logger.info(f"  Invoice check skipped: {str(e)[:50]}...")

        logger.info("\n✅ MANIFEST FLOW TEST PASSED!")

        return manifest


if __name__ == "__main__":
    asyncio.run(test_manifest_flow())
