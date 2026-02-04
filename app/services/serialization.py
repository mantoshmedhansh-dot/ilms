"""
Serialization Service for Barcode Generation

All Barcodes are 16 characters with 8-digit serial numbers for future scalability.

Two Barcode Formats:

1. FINISHED GOODS (FG) - 16 characters:
   Format: APAAAIIEL00000001
   - AP: Brand Prefix (2 chars)
   - AA: Year Code (2 chars: A-Z then AA, AB...)
   - A: Month Code (1 char: A=Jan...L=Dec)
   - IEL: Model Code (3 chars)
   - 00000001: Serial Number (8 digits)

2. SPARE PARTS (SP) - 16 characters:
   Format: APFSAAEC00000001
   - AP: Brand Prefix (2 chars)
   - FS/ST: Supplier Code (2 chars: FS=FastTrack, ST=STOS)
   - A: Year Code (1 char: A=2000...Z=2025, wraps after Z)
   - A: Month Code (1 char: A=Jan...L=Dec)
   - EC/PR: Channel Code (2 chars: EC=Economical, PR=Premium)
   - 00000001: Serial Number (8 digits)

Key Differences:
- FG barcode has NO supplier code, uses 2-char year
- Spare barcode has supplier code + channel code, uses 1-char year

Spare Parts Categories:
- Economical (EC): Supplied by FastTrack (FS)
- Premium (PR): Supplied by STOS (ST)

Same spare part item can have TWO series:
- SPPRG001 → APFSAAEC00000001 (Economical from FastTrack)
- SPPRG001 → APSTAAPR00000001 (Premium from STOS)
"""

import uuid
from datetime import datetime, timezone
from typing import List, Optional, Dict, Tuple
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.serialization import (
    SerialSequence,
    ProductSerialSequence,
    POSerial,
    ModelCodeReference,
    SupplierCode,
    SerialStatus,
    ItemType,
)
from app.models.purchase import PurchaseOrder, PurchaseOrderItem, GoodsReceiptNote
from app.models.product import Product
from app.models.inventory import StockItem
from app.schemas.serialization import (
    GenerateSerialsRequest,
    GenerateSerialItem,
    GenerateSerialsResponse,
    GeneratedSerialSummary,
    POSerialResponse,
    ScanSerialResponse,
    SequenceStatusResponse,
    CodePreviewResponse,
    FGCodeGenerateResponse,
)


class SerializationService:
    """Service for generating and managing product serial numbers/barcodes"""

    BRAND_PREFIX = "AP"  # ILMS.AI

    # Year code mapping: A=2000, B=2001, ... Z=2025
    # After Z, we use AA=2026, AB=2027, etc.
    YEAR_BASE = 2000

    # Month code mapping: A=Jan, B=Feb, ... L=Dec
    MONTH_CODES = "ABCDEFGHIJKL"

    # Supplier to Channel mapping for Spare Parts
    # Supplier Code -> Channel Code
    SUPPLIER_CHANNEL_MAP = {
        "FS": "EC",  # FastTrack -> Economical
        "ST": "PR",  # STOS -> Premium
    }

    # Reverse mapping: Channel -> Supplier
    CHANNEL_SUPPLIER_MAP = {
        "EC": "FS",  # Economical -> FastTrack
        "PR": "ST",  # Premium -> STOS
    }

    def __init__(self, db: AsyncSession):
        self.db = db

    # ==================== Year/Month Code Helpers ====================

    def get_year_code(self, year: int = None) -> str:
        """Convert year to code (A=2000, Z=2025, AA=2026, AB=2027...)"""
        if year is None:
            year = datetime.now().year

        offset = year - self.YEAR_BASE

        if offset < 0:
            raise ValueError(f"Year {year} is before base year {self.YEAR_BASE}")

        if offset <= 25:
            # Single letter A-Z
            return chr(65 + offset)  # A=65 in ASCII
        else:
            # Double letter AA, AB, AC...
            first = (offset - 26) // 26
            second = (offset - 26) % 26
            return chr(65 + first) + chr(65 + second)

    def get_month_code(self, month: int = None) -> str:
        """Convert month to code (A=Jan, L=Dec)"""
        if month is None:
            month = datetime.now().month

        if month < 1 or month > 12:
            raise ValueError(f"Invalid month: {month}")

        return self.MONTH_CODES[month - 1]

    def parse_year_code(self, code: str) -> int:
        """Parse year code back to year number"""
        if len(code) == 1:
            return self.YEAR_BASE + (ord(code.upper()) - 65)
        else:
            first = ord(code[0].upper()) - 65
            second = ord(code[1].upper()) - 65
            return self.YEAR_BASE + 26 + (first * 26) + second

    def parse_month_code(self, code: str) -> int:
        """Parse month code back to month number"""
        return self.MONTH_CODES.index(code.upper()) + 1

    def get_year_code_single(self, year: int = None) -> str:
        """
        Get single-character year code for spare parts.
        Uses A-Z only (2000-2025), then wraps around or uses extended logic.
        For years beyond 2025, we cycle (2026=A, 2027=B, etc.) or use modulo.
        """
        if year is None:
            year = datetime.now().year

        offset = year - self.YEAR_BASE

        if offset < 0:
            raise ValueError(f"Year {year} is before base year {self.YEAR_BASE}")

        # Use modulo 26 to keep single character (wraps after Z)
        # So 2026 = offset 26 -> 26 % 26 = 0 -> 'A'
        # 2027 = offset 27 -> 27 % 26 = 1 -> 'B'
        return chr(65 + (offset % 26))  # A=65 in ASCII

    def get_channel_from_supplier(self, supplier_code: str) -> str:
        """Get channel code from supplier code (uses hardcoded map for backwards compatibility)"""
        channel = self.SUPPLIER_CHANNEL_MAP.get(supplier_code.upper())
        if not channel:
            # For new supplier codes not in hardcoded map, default to "EC" (Economical)
            # This allows new vendors to be added via database without code changes
            return "EC"
        return channel

    async def get_supplier_code_by_vendor_id(self, vendor_id) -> Optional[SupplierCode]:
        """Get supplier code from database by vendor ID"""
        result = await self.db.execute(
            select(SupplierCode).where(
                SupplierCode.vendor_id == vendor_id,
                SupplierCode.is_active == True
            )
        )
        return result.scalar_one_or_none()

    async def get_or_create_supplier_code_for_vendor(self, vendor_id, vendor_name: str) -> Optional[str]:
        """Get supplier code for a vendor, or return None if not mapped (don't auto-create)"""
        supplier_code = await self.get_supplier_code_by_vendor_id(vendor_id)
        if supplier_code:
            return supplier_code.code
        return None

    def get_supplier_from_channel(self, channel_code: str) -> str:
        """Get supplier code from channel code"""
        supplier = self.CHANNEL_SUPPLIER_MAP.get(channel_code.upper())
        if not supplier:
            raise ValueError(f"Unknown channel code: {channel_code}. Valid: {list(self.CHANNEL_SUPPLIER_MAP.keys())}")
        return supplier

    # ==================== Barcode Generation ====================

    # Serial number length (8 digits for 99,999,999 units)
    SERIAL_DIGITS = 8
    MAX_SERIAL = 99999999

    def generate_fg_barcode(
        self,
        year_code: str,
        month_code: str,
        model_code: str,
        serial_number: int
    ) -> str:
        """
        Generate a FINISHED GOODS barcode (16 chars).

        Format: APAAAIIEL00000001
        - AP: Brand prefix (2)
        - AA: Year code (2)
        - A: Month code (1)
        - IEL: Model code (3)
        - 00000001: Serial number (8 digits)
        """
        return f"{self.BRAND_PREFIX}{year_code}{month_code}{model_code.upper()}{serial_number:08d}"

    def generate_spare_barcode(
        self,
        supplier_code: str,
        year_code: str,
        month_code: str,
        model_code: str,
        serial_number: int
    ) -> str:
        """
        Generate a SPARE PARTS barcode (17 chars - same as FG).

        Format: APFSAABDV00000001
        - AP: Brand prefix (2)
        - FS: Supplier code (2)
        - A: Year code (1 char - single letter)
        - A: Month code (1)
        - BDV: Model code (3) - unique per product for unique barcodes
        - 00000001: Serial number (8 digits)
        """
        return f"{self.BRAND_PREFIX}{supplier_code.upper()}{year_code}{month_code}{model_code.upper()}{serial_number:08d}"

    def generate_barcode(
        self,
        supplier_code: str,
        year_code: str,
        month_code: str,
        model_code: str,
        serial_number: int,
        item_type: ItemType = ItemType.FINISHED_GOODS
    ) -> str:
        """
        Generate a barcode based on item type.

        For FG: Uses model_code, no supplier code in barcode
        For Spare: Uses model_code AND supplier code in barcode for uniqueness
        """
        if item_type == ItemType.SPARE_PART:
            # Use single-char year for spare parts
            year_single = year_code[0] if len(year_code) > 1 else year_code
            return self.generate_spare_barcode(
                supplier_code=supplier_code,
                year_code=year_single,
                month_code=month_code,
                model_code=model_code,  # Use model_code for uniqueness per product
                serial_number=serial_number
            )
        else:
            # FG barcode (no supplier code in barcode)
            return self.generate_fg_barcode(
                year_code=year_code,
                month_code=month_code,
                model_code=model_code,
                serial_number=serial_number
            )

    def parse_fg_barcode(self, barcode: str) -> Dict:
        """
        Parse a FG barcode (16 chars): APAAAIIEL00000001
        """
        if len(barcode) != 16:
            raise ValueError(f"Invalid FG barcode length: {len(barcode)}, expected 16")

        return {
            "barcode_type": "FG",
            "brand_prefix": barcode[:2],      # AP
            "year_code": barcode[2:4],        # AA
            "month_code": barcode[4],         # A
            "model_code": barcode[5:8],       # IEL
            "serial_number": int(barcode[8:]),  # 00000001
        }

    def parse_spare_barcode(self, barcode: str) -> Dict:
        """
        Parse a Spare Parts barcode (17 chars): APFSAABDV00000001
        """
        if len(barcode) != 17:
            raise ValueError(f"Invalid Spare barcode length: {len(barcode)}, expected 17")

        supplier_code = barcode[2:4]
        model_code = barcode[6:9]

        return {
            "barcode_type": "SPARE",
            "brand_prefix": barcode[:2],       # AP
            "supplier_code": supplier_code,    # FS or ST
            "year_code": barcode[4],           # A (single char)
            "month_code": barcode[5],          # A
            "model_code": model_code,          # BDV, PRV, etc. (3 chars)
            "serial_number": int(barcode[9:]),  # 00000001
        }

    def parse_barcode(self, barcode: str) -> Dict:
        """
        Parse a barcode and auto-detect type (FG or Spare).

        FG format: APAAAIIEL00000001 (16 chars - no supplier code)
        Spare format: APFSAABDV00000001 (17 chars - includes supplier code)
        """
        if len(barcode) == 17:
            # 17 chars = Spare parts barcode (has supplier code)
            return self.parse_spare_barcode(barcode)
        elif len(barcode) == 16:
            # 16 chars = FG barcode (no supplier code)
            return self.parse_fg_barcode(barcode)
        else:
            raise ValueError(f"Invalid barcode length: {len(barcode)}, expected 16 (FG) or 17 (Spare)")

    # ==================== Sequence Management ====================

    async def get_or_create_sequence(
        self,
        model_code: str,
        supplier_code: str,
        year_code: str = None,
        month_code: str = None,
        product_id: str = None,
        item_type: ItemType = ItemType.FINISHED_GOODS
    ) -> SerialSequence:
        """LEGACY: Get existing sequence or create new one (by model+supplier+year+month)"""

        if year_code is None:
            year_code = self.get_year_code()
        if month_code is None:
            month_code = self.get_month_code()

        # Try to find existing sequence
        result = await self.db.execute(
            select(SerialSequence).where(
                and_(
                    SerialSequence.model_code == model_code.upper(),
                    SerialSequence.supplier_code == supplier_code.upper(),
                    SerialSequence.year_code == year_code,
                    SerialSequence.month_code == month_code,
                )
            )
        )
        sequence = result.scalar_one_or_none()

        if sequence:
            return sequence

        # Create new sequence
        sequence = SerialSequence(
            id=str(uuid.uuid4()),
            model_code=model_code.upper(),
            supplier_code=supplier_code.upper(),
            year_code=year_code,
            month_code=month_code,
            product_id=product_id,
            item_type=item_type,
            last_serial=0,
            total_generated=0,
        )
        self.db.add(sequence)
        await self.db.flush()

        return sequence

    # ==================== Product-Level Sequence Management (NEW) ====================

    async def get_or_create_product_sequence(
        self,
        model_code: str,
        product_id: str = None,
        product_name: str = None,
        product_sku: str = None,
        item_type: ItemType = ItemType.FINISHED_GOODS,
        max_serial: int = 99999999
    ) -> ProductSerialSequence:
        """
        Get or create a product-level serial sequence.

        Each product/model + item_type combination has ONE sequence that is continuous across all time.
        Serial numbers do NOT reset by year/month.

        FG and SP can have the same model_code but will have SEPARATE sequences.
        Example:
        - FG IEL: sequence 1-99999999
        - SP IEL: sequence 1-99999999 (separate)
        """
        # Try to find existing sequence by model_code AND item_type
        result = await self.db.execute(
            select(ProductSerialSequence).where(
                and_(
                    ProductSerialSequence.model_code == model_code.upper(),
                    ProductSerialSequence.item_type == item_type
                )
            )
        )
        sequence = result.scalar_one_or_none()

        if sequence:
            return sequence

        # Create new product sequence - use string UUIDs for VARCHAR columns
        sequence = ProductSerialSequence(
            id=str(uuid.uuid4()),
            model_code=model_code.upper(),
            product_id=str(product_id) if product_id else None,
            product_name=product_name,
            product_sku=product_sku,
            item_type=item_type,
            last_serial=0,
            total_generated=0,
            max_serial=max_serial,
        )
        self.db.add(sequence)
        await self.db.flush()

        return sequence

    async def get_next_product_serial_range(
        self,
        sequence: ProductSerialSequence,
        quantity: int
    ) -> Tuple[int, int]:
        """
        Reserve a range of serial numbers from product sequence.

        Returns (start_serial, end_serial)
        """
        start_serial = sequence.last_serial + 1
        end_serial = start_serial + quantity - 1

        if end_serial > sequence.max_serial:
            raise ValueError(
                f"Serial number overflow for {sequence.model_code}! "
                f"Max is {sequence.max_serial}, requested end: {end_serial}. "
                f"Current last serial: {sequence.last_serial}"
            )

        # Update sequence
        sequence.last_serial = end_serial
        sequence.total_generated += quantity
        sequence.updated_at = datetime.now(timezone.utc)

        return start_serial, end_serial

    async def get_product_sequence_status(
        self,
        model_code: str,
        item_type: ItemType = None
    ) -> Optional[ProductSerialSequence]:
        """
        Get the product sequence status for a model code.

        If item_type is provided, returns the specific sequence for that type.
        Otherwise, returns the first matching sequence (for backward compatibility).
        """
        if item_type:
            result = await self.db.execute(
                select(ProductSerialSequence).where(
                    and_(
                        ProductSerialSequence.model_code == model_code.upper(),
                        ProductSerialSequence.item_type == item_type
                    )
                )
            )
        else:
            result = await self.db.execute(
                select(ProductSerialSequence).where(
                    ProductSerialSequence.model_code == model_code.upper()
                )
            )
        return result.scalar_one_or_none()

    async def get_product_sequences_by_type(
        self,
        item_type: ItemType
    ) -> List[ProductSerialSequence]:
        """Get all product sequences for a specific item type (FG or SP)."""
        result = await self.db.execute(
            select(ProductSerialSequence)
            .where(ProductSerialSequence.item_type == item_type)
            .order_by(ProductSerialSequence.model_code)
        )
        return result.scalars().all()

    async def get_all_product_sequences(self) -> List[ProductSerialSequence]:
        """Get all product serial sequences."""
        result = await self.db.execute(
            select(ProductSerialSequence).order_by(ProductSerialSequence.model_code)
        )
        return result.scalars().all()

    async def get_next_serial_range(
        self,
        sequence: SerialSequence,
        quantity: int
    ) -> Tuple[int, int]:
        """
        LEGACY: Reserve a range of serial numbers.

        Returns (start_serial, end_serial)
        """
        start_serial = sequence.last_serial + 1
        end_serial = start_serial + quantity - 1

        if end_serial > self.MAX_SERIAL:
            raise ValueError(
                f"Serial number overflow! Max is {self.MAX_SERIAL}, requested end: {end_serial}. "
                f"Current last serial for {sequence.supplier_code}/{sequence.model_code}: {sequence.last_serial}"
            )

        # Update sequence
        sequence.last_serial = end_serial
        sequence.total_generated += quantity
        sequence.updated_at = datetime.now(timezone.utc)

        return start_serial, end_serial

    # ==================== Serial Generation ====================

    async def generate_serials_for_po(
        self,
        request: GenerateSerialsRequest
    ) -> GenerateSerialsResponse:
        """
        Generate serial numbers for a Purchase Order.

        Uses PRODUCT-LEVEL sequencing:
        - Each model (Aura, Elige, etc.) has its own continuous serial number range
        - Serial numbers do NOT reset by year/month
        - Year/month codes are still included in barcode for traceability

        This is called when a PO is sent to the vendor.
        """
        import logging
        logging.info(f"[SerializationService] generate_serials_for_po called: po_id={request.po_id}, supplier={request.supplier_code}, items={len(request.items)}")

        # Year/month codes for barcode (traceability only, not for sequence lookup)
        year_code = self.get_year_code()
        month_code = self.get_month_code()
        logging.info(f"[SerializationService] year_code={year_code}, month_code={month_code}")

        all_barcodes = []
        item_summaries = []

        for idx, item in enumerate(request.items):
            logging.info(f"[SerializationService] Processing item {idx+1}/{len(request.items)}: model={item.model_code}, qty={item.quantity}, type={item.item_type}")

            # NEW: Use product-level sequencing (continuous per model)
            product_sequence = await self.get_or_create_product_sequence(
                model_code=item.model_code,
                product_id=item.product_id,
                product_name=item.product_name if hasattr(item, 'product_name') else None,
                product_sku=item.product_sku,
                item_type=item.item_type,
            )
            logging.info(f"[SerializationService] Got sequence: id={product_sequence.id}, last_serial={product_sequence.last_serial}")

            # Reserve serial range from product sequence
            start_serial, end_serial = await self.get_next_product_serial_range(
                product_sequence, item.quantity
            )
            logging.info(f"[SerializationService] Reserved range: {start_serial} - {end_serial}")

            # Generate individual serial records
            item_barcodes = []

            # For spare parts, get the channel code
            channel_code = None
            if item.item_type == ItemType.SPARE_PART:
                channel_code = self.get_channel_from_supplier(request.supplier_code)

            for serial_num in range(start_serial, end_serial + 1):
                barcode = self.generate_barcode(
                    supplier_code=request.supplier_code,
                    year_code=year_code,
                    month_code=month_code,
                    model_code=item.model_code,
                    serial_number=serial_num,
                    item_type=item.item_type,
                )

                # Database columns are VARCHAR(36) for po_id, po_item_id, product_id
                # Store as strings to match database schema
                po_serial = POSerial(
                    id=str(uuid.uuid4()),
                    po_id=str(request.po_id),
                    po_item_id=str(item.po_item_id) if item.po_item_id else None,
                    product_id=str(item.product_id) if item.product_id else None,
                    product_sku=item.product_sku,
                    model_code=item.model_code.upper(),
                    item_type=item.item_type.value if hasattr(item.item_type, 'value') else str(item.item_type),
                    brand_prefix=self.BRAND_PREFIX,
                    supplier_code=request.supplier_code.upper(),
                    year_code=year_code if item.item_type != ItemType.SPARE_PART else year_code[0],
                    month_code=month_code,
                    serial_number=serial_num,
                    barcode=barcode,
                    status=SerialStatus.GENERATED.value,
                )
                self.db.add(po_serial)
                item_barcodes.append(barcode)

            all_barcodes.extend(item_barcodes)

            # Create summary for this item
            item_summaries.append(GeneratedSerialSummary(
                model_code=item.model_code.upper(),
                quantity=item.quantity,
                start_serial=start_serial,
                end_serial=end_serial,
                start_barcode=item_barcodes[0],
                end_barcode=item_barcodes[-1],
            ))

        logging.info(f"[SerializationService] Committing {len(all_barcodes)} serial records to database...")
        await self.db.commit()
        logging.info(f"[SerializationService] COMMIT SUCCESS: {len(all_barcodes)} serials generated for PO {request.po_id}")

        return GenerateSerialsResponse(
            po_id=request.po_id,
            supplier_code=request.supplier_code.upper(),
            total_generated=len(all_barcodes),
            items=item_summaries,
            barcodes=all_barcodes,
        )

    # ==================== Serial Retrieval ====================

    async def get_serials_by_po(
        self,
        po_id: str,
        status: SerialStatus = None,
        limit: int = 1000,
        offset: int = 0
    ) -> List[POSerial]:
        """Get all serials for a PO"""
        # po_id is VARCHAR(36) in database, use string comparison
        po_id_str = str(po_id) if po_id else None

        query = select(POSerial).where(POSerial.po_id == po_id_str)

        if status:
            query = query.where(POSerial.status == status)

        query = query.order_by(POSerial.serial_number).offset(offset).limit(limit)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_serial_by_barcode(self, barcode: str) -> Optional[POSerial]:
        """Get serial details by barcode"""
        result = await self.db.execute(
            select(POSerial).where(POSerial.barcode == barcode.upper())
        )
        return result.scalar_one_or_none()

    async def get_serials_count_by_po(self, po_id: str) -> Dict[str, int]:
        """Get count of serials by status for a PO"""
        # po_id is VARCHAR(36) in database, use string comparison
        po_id_str = str(po_id) if po_id else None

        result = await self.db.execute(
            select(
                POSerial.status,
                func.count(POSerial.id).label("count")
            ).where(POSerial.po_id == po_id_str)
            .group_by(POSerial.status)
        )

        counts = {"total": 0}
        for row in result:
            counts[row.status] = row.count
            counts["total"] += row.count

        return counts

    # ==================== Serial Scanning (GRN) ====================

    async def scan_serial(
        self,
        barcode: str,
        grn_id: str,
        grn_item_id: str = None,
        user_id: str = None
    ) -> ScanSerialResponse:
        """
        Scan and validate a serial during GRN receiving.

        Marks the serial as RECEIVED if valid.
        """
        serial = await self.get_serial_by_barcode(barcode)

        if not serial:
            return ScanSerialResponse(
                barcode=barcode,
                is_valid=False,
                status=SerialStatus.GENERATED,
                message=f"Barcode {barcode} not found in system",
                serial_details=None,
            )

        # Check if already received
        if serial.status in [SerialStatus.RECEIVED, SerialStatus.ASSIGNED, SerialStatus.SOLD]:
            return ScanSerialResponse(
                barcode=barcode,
                is_valid=False,
                status=serial.status,
                message=f"Barcode already processed. Current status: {serial.status}",
                serial_details=POSerialResponse.model_validate(serial),
            )

        # Check if cancelled
        if serial.status == SerialStatus.CANCELLED:
            return ScanSerialResponse(
                barcode=barcode,
                is_valid=False,
                status=serial.status,
                message="Barcode has been cancelled",
                serial_details=POSerialResponse.model_validate(serial),
            )

        # Mark as received
        serial.status = SerialStatus.RECEIVED.value
        serial.grn_id = grn_id
        serial.grn_item_id = grn_item_id
        serial.received_at = datetime.now(timezone.utc)
        serial.received_by = user_id
        serial.updated_at = datetime.now(timezone.utc)

        await self.db.commit()

        return ScanSerialResponse(
            barcode=barcode,
            is_valid=True,
            status=SerialStatus.RECEIVED,
            message="Serial received successfully",
            serial_details=POSerialResponse.model_validate(serial),
        )

    async def bulk_scan_serials(
        self,
        barcodes: List[str],
        grn_id: str,
        user_id: str = None
    ) -> List[ScanSerialResponse]:
        """Scan multiple barcodes at once"""
        results = []
        for barcode in barcodes:
            result = await self.scan_serial(barcode, grn_id, user_id=user_id)
            results.append(result)
        return results

    # ==================== Serial Assignment (Stock) ====================

    async def assign_serial_to_stock(
        self,
        barcode: str,
        stock_item_id: str
    ) -> POSerial:
        """Assign a serial to a stock item"""
        serial = await self.get_serial_by_barcode(barcode)

        if not serial:
            raise ValueError(f"Barcode {barcode} not found")

        if serial.status != SerialStatus.RECEIVED:
            raise ValueError(
                f"Serial must be in RECEIVED status to assign. Current: {serial.status}"
            )

        serial.status = SerialStatus.ASSIGNED.value
        serial.stock_item_id = stock_item_id
        serial.assigned_at = datetime.now(timezone.utc)
        serial.updated_at = datetime.now(timezone.utc)

        await self.db.commit()
        return serial

    # ==================== Serial Sale ====================

    async def mark_serial_sold(
        self,
        barcode: str,
        order_id: str,
        order_item_id: str = None,
        customer_id: str = None,
        warranty_months: int = 12
    ) -> POSerial:
        """Mark a serial as sold and set warranty dates"""
        serial = await self.get_serial_by_barcode(barcode)

        if not serial:
            raise ValueError(f"Barcode {barcode} not found")

        if serial.status not in [SerialStatus.ASSIGNED, SerialStatus.RECEIVED]:
            raise ValueError(
                f"Serial must be in ASSIGNED or RECEIVED status to sell. Current: {serial.status}"
            )

        now = datetime.now(timezone.utc)
        serial.status = SerialStatus.SOLD.value
        serial.order_id = order_id
        serial.order_item_id = order_item_id
        serial.customer_id = customer_id
        serial.sold_at = now
        serial.warranty_start_date = now
        serial.warranty_end_date = datetime(
            now.year + (now.month + warranty_months - 1) // 12,
            (now.month + warranty_months - 1) % 12 + 1,
            now.day
        )
        serial.updated_at = now

        await self.db.commit()
        return serial

    # ==================== Sequence Status ====================

    async def get_sequence_status(
        self,
        model_code: str,
        supplier_code: str,
        year_code: str = None,
        month_code: str = None
    ) -> SequenceStatusResponse:
        """Get current status of a serial sequence"""

        if year_code is None:
            year_code = self.get_year_code()
        if month_code is None:
            month_code = self.get_month_code()

        sequence = await self.get_or_create_sequence(
            model_code=model_code,
            supplier_code=supplier_code,
            year_code=year_code,
            month_code=month_code,
        )

        next_barcode = self.generate_barcode(
            supplier_code=supplier_code,
            year_code=year_code,
            month_code=month_code,
            model_code=model_code,
            serial_number=sequence.last_serial + 1,
        )

        return SequenceStatusResponse(
            model_code=model_code.upper(),
            supplier_code=supplier_code.upper(),
            year_code=year_code,
            month_code=month_code,
            last_serial=sequence.last_serial,
            next_serial=sequence.last_serial + 1,
            total_generated=sequence.total_generated,
            next_barcode_preview=next_barcode,
        )

    # ==================== Code Preview ====================

    async def preview_codes(
        self,
        supplier_code: str,
        model_code: str,
        quantity: int = 5
    ) -> CodePreviewResponse:
        """Preview what codes would be generated without saving"""

        year_code = self.get_year_code()
        month_code = self.get_month_code()

        # Get current sequence to know where we'd start
        sequence = await self.get_or_create_sequence(
            model_code=model_code,
            supplier_code=supplier_code,
            year_code=year_code,
            month_code=month_code,
        )

        # Generate preview barcodes
        preview_barcodes = []
        for i in range(quantity):
            barcode = self.generate_barcode(
                supplier_code=supplier_code,
                year_code=year_code,
                month_code=month_code,
                model_code=model_code,
                serial_number=sequence.last_serial + 1 + i,
            )
            preview_barcodes.append(barcode)

        # Rollback any changes (we don't want to commit the sequence if it was newly created)
        await self.db.rollback()

        return CodePreviewResponse(
            supplier_code=supplier_code.upper(),
            model_code=model_code.upper(),
            year_code=year_code,
            month_code=month_code,
            current_last_serial=sequence.last_serial,
            preview_barcodes=preview_barcodes,
        )

    # ==================== FG Code Generation ====================

    async def generate_fg_code(
        self,
        category_code: str,  # WP
        subcategory_code: str,  # R
        brand_code: str,  # A
        model_name: str,  # IELITZ -> IEL
    ) -> FGCodeGenerateResponse:
        """
        Generate a new FG Code.

        Example: WPRAIEL001
        - WP: Water Purifier
        - R: RO
        - A: ILMS.AI
        - IEL: Model code (first 3 letters of model name)
        - 001: Sequential number
        """
        # Extract model code (first 3 letters, uppercase)
        model_code = model_name[:3].upper()

        # Find the next available number for this prefix
        prefix = f"{category_code.upper()}{subcategory_code.upper()}{brand_code.upper()}{model_code}"

        result = await self.db.execute(
            select(ModelCodeReference)
            .where(ModelCodeReference.fg_code.like(f"{prefix}%"))
            .order_by(ModelCodeReference.fg_code.desc())
        )
        last_ref = result.scalar_one_or_none()

        if last_ref:
            # Extract number from last FG code
            last_num = int(last_ref.fg_code[-3:])
            next_num = last_num + 1
        else:
            next_num = 1

        fg_code = f"{prefix}{next_num:03d}"

        return FGCodeGenerateResponse(
            fg_code=fg_code,
            model_code=model_code,
            description=f"{category_code} {subcategory_code} {brand_code} {model_name}",
            next_available_number=next_num,
        )

    # ==================== Supplier Code Management ====================

    async def get_supplier_codes(self, active_only: bool = True) -> List[SupplierCode]:
        """Get all supplier codes"""
        query = select(SupplierCode)
        if active_only:
            query = query.where(SupplierCode.is_active == True)
        query = query.order_by(SupplierCode.code)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def create_supplier_code(
        self,
        code: str,
        name: str,
        vendor_id: str = None,
        description: str = None
    ) -> SupplierCode:
        """Create a new supplier code"""

        # Check if code already exists
        result = await self.db.execute(
            select(SupplierCode).where(SupplierCode.code == code.upper())
        )
        if result.scalar_one_or_none():
            raise ValueError(f"Supplier code {code} already exists")

        supplier_code = SupplierCode(
            id=str(uuid.uuid4()),
            code=code.upper(),
            name=name,
            vendor_id=vendor_id,
            description=description,
            is_active=True,
        )
        self.db.add(supplier_code)
        await self.db.commit()

        return supplier_code

    # ==================== Model Code Management ====================

    async def get_model_codes(self, active_only: bool = True) -> List[ModelCodeReference]:
        """Get all model code references"""
        query = select(ModelCodeReference)
        if active_only:
            query = query.where(ModelCodeReference.is_active == True)
        query = query.order_by(ModelCodeReference.fg_code)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def create_model_code_reference(
        self,
        fg_code: str,
        model_code: str,
        product_id: str = None,
        product_sku: str = None,
        description: str = None
    ) -> ModelCodeReference:
        """Create a new model code reference

        Note: item_type parameter removed - column doesn't exist in production database.
        Item type is determined from fg_code prefix (WP=FG, SP=SP).
        """

        # Check if FG code already exists
        result = await self.db.execute(
            select(ModelCodeReference).where(ModelCodeReference.fg_code == fg_code.upper())
        )
        if result.scalar_one_or_none():
            raise ValueError(f"FG code {fg_code} already exists")

        model_ref = ModelCodeReference(
            id=str(uuid.uuid4()),
            fg_code=fg_code.upper(),
            model_code=model_code.upper(),
            # Note: item_type removed - determined from fg_code prefix
            product_id=product_id,
            product_sku=product_sku,
            description=description,
            is_active=True,
        )
        self.db.add(model_ref)
        await self.db.commit()

        return model_ref

    # ==================== Update PO Status ====================

    async def mark_serials_sent_to_vendor(self, po_id: str) -> int:
        """Mark all serials for a PO as sent to vendor"""
        # po_id is VARCHAR(36) in database
        po_id_str = str(po_id) if po_id else None

        result = await self.db.execute(
            select(POSerial).where(
                and_(
                    POSerial.po_id == po_id_str,
                    POSerial.status == SerialStatus.GENERATED
                )
            )
        )
        serials = result.scalars().all()

        count = 0
        for serial in serials:
            serial.status = SerialStatus.SENT_TO_VENDOR.value
            serial.updated_at = datetime.now(timezone.utc)
            count += 1

        await self.db.commit()
        return count

    async def cancel_serials(self, po_id: str, reason: str = None) -> int:
        """Cancel all unreceived serials for a PO"""
        # po_id is VARCHAR(36) in database
        po_id_str = str(po_id) if po_id else None

        result = await self.db.execute(
            select(POSerial).where(
                and_(
                    POSerial.po_id == po_id_str,
                    POSerial.status.in_([
                        SerialStatus.GENERATED,
                        SerialStatus.PRINTED,
                        SerialStatus.SENT_TO_VENDOR
                    ])
                )
            )
        )
        serials = result.scalars().all()

        count = 0
        for serial in serials:
            serial.status = SerialStatus.CANCELLED.value
            serial.notes = reason
            serial.updated_at = datetime.now(timezone.utc)
            count += 1

        await self.db.commit()
        return count
