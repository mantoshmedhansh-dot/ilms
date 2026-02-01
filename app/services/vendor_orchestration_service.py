"""
Vendor Orchestration Service

Central service that orchestrates all downstream actions when vendor status changes.
This eliminates the need for manual duplicate entries across modules.

When a vendor is approved:
1. Auto-create Supplier Code (for SPARE_PARTS/MANUFACTURER vendors) → Serialization
2. Initialize Vendor Ledger entry → Finance/Accounting
3. Link to GL Control Accounts → Finance
4. Send notifications → Procurement team

This follows the principle: "One entry, automatic propagation"
"""
import uuid
import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.vendor import Vendor, VendorLedger, VendorTransactionType, VendorType
from app.models.serialization import SupplierCode


class VendorOrchestrationService:
    """
    Central service that orchestrates all downstream actions
    when a vendor status changes.

    Design principle: Single point of entry, automatic propagation
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def on_vendor_approved(self, vendor: Vendor, approved_by_id: uuid.UUID) -> dict:
        """
        Called when vendor is approved. Triggers all downstream setups.

        Args:
            vendor: The vendor that was just approved
            approved_by_id: User ID who approved the vendor

        Returns:
            dict with results of all orchestration actions
        """
        results = {
            "vendor_id": str(vendor.id),
            "vendor_code": vendor.vendor_code,
            "actions_performed": []
        }

        # 1. Create Supplier Code (if vendor supplies spare parts or is a manufacturer)
        if self._should_create_supplier_code(vendor):
            supplier_code = await self._create_supplier_code(vendor)
            if supplier_code:
                results["supplier_code"] = supplier_code
                results["actions_performed"].append("supplier_code_created")

        # 2. Initialize Vendor Ledger with opening balance entry
        if vendor.opening_balance and vendor.opening_balance > 0:
            ledger_entry = await self._create_opening_balance_entry(vendor, approved_by_id)
            if ledger_entry:
                results["ledger_entry_id"] = str(ledger_entry.id)
                results["actions_performed"].append("opening_balance_created")

        # 3. Future: Link GL Accounts (when accounting module is fully integrated)
        # await self._ensure_gl_accounts(vendor)

        # 4. Future: Send notification to procurement team
        # await self._notify_procurement_team(vendor)

        return results

    def _should_create_supplier_code(self, vendor: Vendor) -> bool:
        """
        Determine if this vendor needs a supplier code for barcode generation.

        Supplier codes are needed for:
        - SPARE_PARTS vendors (always)
        - MANUFACTURER vendors (they might supply both FG and SP)
        - RAW_MATERIAL vendors (components need tracking)
        """
        supplier_code_vendor_types = [
            VendorType.SPARE_PARTS.value,
            VendorType.MANUFACTURER.value,
            VendorType.RAW_MATERIAL.value,
            "SPARE_PARTS",
            "MANUFACTURER",
            "RAW_MATERIAL",
        ]
        return vendor.vendor_type in supplier_code_vendor_types

    async def _create_supplier_code(self, vendor: Vendor) -> Optional[str]:
        """
        Auto-generate a unique 2-character supplier code from vendor name.

        Algorithm:
        1. Take first letters of first two words: "SARJAN WATERTECH" -> "SW"
        2. If single word, take first two letters: "FastTrack" -> "FA"
        3. If code exists, iterate: SA, SB, SC... until unique found
        4. Store in both supplier_codes table AND vendor.supplier_code field
        """
        # Skip if vendor already has a supplier code
        if vendor.supplier_code:
            return vendor.supplier_code

        # Check if vendor already has a supplier_code record
        existing = await self.db.execute(
            select(SupplierCode).where(SupplierCode.vendor_id == vendor.id)
        )
        if existing.scalar_one_or_none():
            return None  # Already exists

        # Generate base code from vendor name
        words = vendor.name.upper().replace("PVT", "").replace("LTD", "").replace("INDIA", "").split()
        words = [w for w in words if len(w) > 1]  # Filter out single chars

        if len(words) >= 2:
            base_code = words[0][0] + words[1][0]
        elif len(words) == 1 and len(words[0]) >= 2:
            base_code = words[0][:2]
        else:
            # Fallback: use first 2 chars of vendor code
            base_code = vendor.vendor_code[-2:].upper()

        # Ensure uppercase and 2 chars
        base_code = base_code.upper()[:2]

        # Find unique code
        code = base_code
        suffix = 0
        max_attempts = 26 * 26  # AA to ZZ

        while suffix < max_attempts:
            # Check if code exists
            exists = await self.db.execute(
                select(SupplierCode).where(SupplierCode.code == code)
            )
            if not exists.scalar_one_or_none():
                # Also check vendor.supplier_code field
                vendor_exists = await self.db.execute(
                    select(Vendor).where(Vendor.supplier_code == code)
                )
                if not vendor_exists.scalar_one_or_none():
                    break  # Found unique code

            # Generate next code
            suffix += 1
            if suffix < 26:
                code = base_code[0] + chr(65 + suffix)  # SA, SB, SC...
            else:
                # Two-letter iteration: AA, AB, AC...
                first = suffix // 26
                second = suffix % 26
                code = chr(65 + first) + chr(65 + second)

        # Create SupplierCode record
        supplier_code_record = SupplierCode(
            id=str(uuid.uuid4()),
            vendor_id=vendor.id,
            code=code,
            name=vendor.name,
            description=f"Auto-created for {vendor.vendor_code} on approval",
            is_active=True
        )
        self.db.add(supplier_code_record)

        # Also store on vendor for quick access
        vendor.supplier_code = code

        return code

    async def _create_opening_balance_entry(
        self,
        vendor: Vendor,
        created_by_id: uuid.UUID
    ) -> Optional[VendorLedger]:
        """
        Create opening balance entry in vendor ledger.
        This establishes the starting point for vendor account tracking.
        """
        if not vendor.opening_balance or vendor.opening_balance <= 0:
            return None

        # Check if opening balance entry already exists
        existing = await self.db.execute(
            select(VendorLedger).where(
                VendorLedger.vendor_id == vendor.id,
                VendorLedger.transaction_type == VendorTransactionType.OPENING_BALANCE.value
            )
        )
        if existing.scalar_one_or_none():
            return None  # Already exists

        ledger_entry = VendorLedger(
            vendor_id=vendor.id,
            transaction_type=VendorTransactionType.OPENING_BALANCE.value,
            transaction_date=datetime.now(timezone.utc).date(),
            reference_type="OPENING",
            reference_number=f"OB-{vendor.vendor_code}",
            debit_amount=Decimal("0"),
            credit_amount=vendor.opening_balance,
            running_balance=vendor.opening_balance,
            narration=f"Opening balance for {vendor.name}",
            created_by=created_by_id
        )
        self.db.add(ledger_entry)

        # Update vendor's current balance
        vendor.current_balance = vendor.opening_balance

        return ledger_entry

    async def sync_existing_vendors(self) -> dict:
        """
        One-time utility to sync existing approved vendors that don't have supplier codes.
        Run this to fix vendors that were approved before orchestration was implemented.

        Returns:
            dict with count of vendors synced
        """
        # Find approved SPARE_PARTS/MANUFACTURER vendors without supplier codes
        result = await self.db.execute(
            select(Vendor).where(
                Vendor.status == "ACTIVE",
                Vendor.vendor_type.in_(["SPARE_PARTS", "MANUFACTURER", "RAW_MATERIAL"]),
                Vendor.supplier_code.is_(None)
            )
        )
        vendors = result.scalars().all()

        synced = []
        for vendor in vendors:
            code = await self._create_supplier_code(vendor)
            if code:
                synced.append({
                    "vendor_code": vendor.vendor_code,
                    "vendor_name": vendor.name,
                    "supplier_code": code
                })

        await self.db.commit()

        return {
            "total_synced": len(synced),
            "vendors": synced
        }
