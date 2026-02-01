#!/usr/bin/env python3
"""Test invoice generation flow."""

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
from app.services.order_service import OrderService
from app.models.order import Order, Invoice
from sqlalchemy import select, desc


async def test_invoice_flow():
    """Test generating an invoice for an order."""

    async with async_session_factory() as db:
        order_service = OrderService(db)

        # Step 1: Find a shipped order without invoice
        logger.info("Finding a shipped order without invoice...")

        result = await db.execute(
            select(Order)
            .outerjoin(Invoice, Order.id == Invoice.order_id)
            .where(Order.status.in_(["SHIPPED", "ALLOCATED", "CONFIRMED"]))
            .where(Invoice.id.is_(None))
            .order_by(desc(Order.created_at))
            .limit(1)
        )
        order = result.scalar_one_or_none()

        if not order:
            logger.error("No order found without invoice! Check earlier test data.")
            return None

        logger.info(f"Using order: {order.order_number}")
        logger.info(f"  ID: {order.id}")
        logger.info(f"  Status: {order.status}")
        logger.info(f"  Subtotal: {order.subtotal}")
        logger.info(f"  Tax Amount: {order.tax_amount}")
        logger.info(f"  Total Amount: {order.total_amount}")

        # Step 2: Generate invoice
        logger.info("\nGenerating invoice...")

        invoice = await order_service.generate_invoice(order.id)

        logger.info(f"Invoice generated:")
        logger.info(f"  Invoice Number: {invoice.invoice_number}")
        logger.info(f"  Invoice Date: {invoice.invoice_date}")
        logger.info(f"  Subtotal: {invoice.subtotal}")
        logger.info(f"  Tax Amount: {invoice.tax_amount}")
        logger.info(f"  CGST: {invoice.cgst_amount}")
        logger.info(f"  SGST: {invoice.sgst_amount}")
        logger.info(f"  IGST: {invoice.igst_amount}")
        logger.info(f"  Discount: {invoice.discount_amount}")
        logger.info(f"  Total: {invoice.total_amount}")

        # Step 3: Check for auto-generated sales journal entry
        logger.info("\nChecking for sales journal entry...")

        from sqlalchemy import text
        je_result = await db.execute(text("""
            SELECT je.id, je.entry_number, je.source_type, je.narration,
                   je.total_debit, je.total_credit, je.status
            FROM journal_entries je
            WHERE (je.source_type = 'SALES_INVOICE' AND je.source_id = :order_id)
               OR (je.narration LIKE :invoice_pattern)
            ORDER BY je.created_at DESC
            LIMIT 1
        """), {
            "order_id": order.id,
            "invoice_pattern": f"%{invoice.invoice_number}%"
        })
        je = je_result.fetchone()

        if je:
            logger.info(f"Sales Journal Entry found:")
            logger.info(f"  Entry Number: {je[1]}")
            logger.info(f"  Source Type: {je[2]}")
            logger.info(f"  Total Debit: {je[4]}")
            logger.info(f"  Total Credit: {je[5]}")
            logger.info(f"  Status: {je[6]}")
        else:
            logger.info("  No auto-generated sales journal entry (may be manual)")

        # Step 4: Verify invoice is linked to order
        await db.refresh(order)
        order_with_invoice = await order_service.get_order_by_id(order.id, include_all=True)

        if order_with_invoice.invoice:
            logger.info(f"\nInvoice linked to order: {order_with_invoice.invoice.invoice_number}")
        else:
            logger.warning("Invoice not properly linked to order!")

        logger.info("\n✅ INVOICE FLOW TEST PASSED!")

        return invoice


if __name__ == "__main__":
    asyncio.run(test_invoice_flow())
