"""
ITC (Input Tax Credit) Service

Manages ITC tracking, reconciliation, and utilization:
- ITC availed from vendor invoices
- GSTR-2A/2B reconciliation
- ITC utilization against output tax
- ITC reversal management
"""

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional, Dict, Any, List
from uuid import UUID, uuid4

from sqlalchemy import select, and_, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.itc import ITCLedger, ITCSummary, ITCStatus, ITCMatchStatus
from app.models.company import Company


class ITCService:
    """
    Service for ITC management and reconciliation.
    """

    def __init__(self, db: AsyncSession, company_id: UUID):
        self.db = db
        self.company_id = company_id

    def _get_period(self, year: int, month: int) -> str:
        """Get period in YYYYMM format."""
        return f"{year}{month:02d}"

    async def create_itc_entry(
        self,
        vendor_gstin: str,
        vendor_name: str,
        invoice_number: str,
        invoice_date: date,
        invoice_value: Decimal,
        taxable_value: Decimal,
        cgst_itc: Decimal = Decimal("0"),
        sgst_itc: Decimal = Decimal("0"),
        igst_itc: Decimal = Decimal("0"),
        cess_itc: Decimal = Decimal("0"),
        itc_type: str = "INPUTS",
        hsn_code: Optional[str] = None,
        description: Optional[str] = None,
        vendor_id: Optional[UUID] = None,
        purchase_invoice_id: Optional[UUID] = None,
        created_by: Optional[UUID] = None,
    ) -> ITCLedger:
        """Create a new ITC ledger entry."""
        period = self._get_period(invoice_date.year, invoice_date.month)
        total_itc = cgst_itc + sgst_itc + igst_itc + cess_itc

        itc_entry = ITCLedger(
            id=uuid4(),
            company_id=self.company_id,
            period=period,
            vendor_id=vendor_id,
            vendor_gstin=vendor_gstin,
            vendor_name=vendor_name,
            invoice_number=invoice_number,
            invoice_date=invoice_date,
            invoice_value=invoice_value,
            itc_type=itc_type,
            taxable_value=taxable_value,
            cgst_itc=cgst_itc,
            sgst_itc=sgst_itc,
            igst_itc=igst_itc,
            cess_itc=cess_itc,
            total_itc=total_itc,
            status=ITCStatus.AVAILABLE.value,
            match_status=ITCMatchStatus.PENDING.value,
            is_interstate=igst_itc > 0,
            hsn_code=hsn_code,
            description=description,
            purchase_invoice_id=purchase_invoice_id,
            created_by=created_by,
        )

        self.db.add(itc_entry)
        await self.db.flush()
        await self.db.refresh(itc_entry)

        return itc_entry

    async def get_available_itc(
        self,
        period: Optional[str] = None,
        vendor_gstin: Optional[str] = None,
    ) -> Dict:
        """
        Get available ITC summary.

        Returns aggregated ITC by component (CGST, SGST, IGST, Cess).
        """
        query = (
            select(
                func.sum(ITCLedger.cgst_itc - ITCLedger.utilized_amount).label("cgst_available"),
                func.sum(ITCLedger.sgst_itc).label("sgst_available"),
                func.sum(ITCLedger.igst_itc).label("igst_available"),
                func.sum(ITCLedger.cess_itc).label("cess_available"),
                func.count(ITCLedger.id).label("invoice_count"),
            )
            .where(
                and_(
                    ITCLedger.company_id == self.company_id,
                    ITCLedger.status == ITCStatus.AVAILABLE.value,
                )
            )
        )

        if period:
            query = query.where(ITCLedger.period == period)
        if vendor_gstin:
            query = query.where(ITCLedger.vendor_gstin == vendor_gstin)

        result = await self.db.execute(query)
        row = result.one()

        cgst = row.cgst_available or Decimal("0")
        sgst = row.sgst_available or Decimal("0")
        igst = row.igst_available or Decimal("0")
        cess = row.cess_available or Decimal("0")

        return {
            "cgst_available": float(cgst),
            "sgst_available": float(sgst),
            "igst_available": float(igst),
            "cess_available": float(cess),
            "total_available": float(cgst + sgst + igst + cess),
            "invoice_count": row.invoice_count or 0,
        }

    async def get_itc_ledger(
        self,
        period: Optional[str] = None,
        status: Optional[str] = None,
        match_status: Optional[str] = None,
        vendor_gstin: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Dict:
        """Get ITC ledger entries with filters."""
        conditions = [ITCLedger.company_id == self.company_id]

        if period:
            conditions.append(ITCLedger.period == period)
        if status:
            conditions.append(ITCLedger.status == status)
        if match_status:
            conditions.append(ITCLedger.match_status == match_status)
        if vendor_gstin:
            conditions.append(ITCLedger.vendor_gstin == vendor_gstin)

        # Count query
        count_query = select(func.count(ITCLedger.id)).where(and_(*conditions))
        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        # Data query
        query = (
            select(ITCLedger)
            .where(and_(*conditions))
            .order_by(ITCLedger.invoice_date.desc())
            .offset(skip)
            .limit(limit)
        )

        result = await self.db.execute(query)
        entries = list(result.scalars().all())

        return {
            "total": total,
            "entries": entries,
        }

    async def reconcile_with_gstr2a(
        self,
        period: str,
        gstr2a_data: List[Dict],
    ) -> Dict:
        """
        Reconcile ITC ledger with GSTR-2A data.

        Matches invoices from GSTR-2A with ITC ledger entries.
        """
        matched = 0
        unmatched = 0
        new_entries = 0
        mismatches = []

        for supplier_data in gstr2a_data:
            vendor_gstin = supplier_data.get("ctin")
            invoices = supplier_data.get("inv", [])

            for inv in invoices:
                invoice_number = inv.get("inum")
                invoice_date_str = inv.get("idt")
                invoice_value = Decimal(str(inv.get("val", 0)))

                # Find matching ITC entry
                query = (
                    select(ITCLedger)
                    .where(
                        and_(
                            ITCLedger.company_id == self.company_id,
                            ITCLedger.vendor_gstin == vendor_gstin,
                            ITCLedger.invoice_number == invoice_number,
                        )
                    )
                )
                result = await self.db.execute(query)
                itc_entry = result.scalar_one_or_none()

                if itc_entry:
                    # Check for amount match
                    if abs(itc_entry.invoice_value - invoice_value) < Decimal("1"):
                        itc_entry.gstr2a_matched = True
                        itc_entry.match_status = ITCMatchStatus.MATCHED.value
                        itc_entry.match_date = datetime.now(timezone.utc)
                        itc_entry.gstr2a_data = inv
                        matched += 1
                    else:
                        itc_entry.match_status = ITCMatchStatus.PARTIAL_MATCH.value
                        itc_entry.match_difference = invoice_value - itc_entry.invoice_value
                        itc_entry.gstr2a_data = inv
                        mismatches.append({
                            "vendor_gstin": vendor_gstin,
                            "invoice_number": invoice_number,
                            "book_value": float(itc_entry.invoice_value),
                            "gstr2a_value": float(invoice_value),
                            "difference": float(invoice_value - itc_entry.invoice_value),
                        })
                else:
                    # Entry in GSTR-2A but not in books - create pending entry
                    unmatched += 1

        await self.db.commit()

        return {
            "period": period,
            "matched": matched,
            "unmatched": unmatched,
            "partial_matches": len(mismatches),
            "new_entries": new_entries,
            "mismatches": mismatches,
        }

    async def reconcile_with_gstr2b(
        self,
        period: str,
        gstr2b_data: List[Dict],
    ) -> Dict:
        """
        Reconcile ITC ledger with GSTR-2B data.

        GSTR-2B is the auto-drafted ITC statement.
        """
        matched = 0
        mismatches = []

        for supplier_data in gstr2b_data:
            vendor_gstin = supplier_data.get("ctin")
            invoices = supplier_data.get("inv", [])

            for inv in invoices:
                invoice_number = inv.get("inum")

                query = (
                    select(ITCLedger)
                    .where(
                        and_(
                            ITCLedger.company_id == self.company_id,
                            ITCLedger.vendor_gstin == vendor_gstin,
                            ITCLedger.invoice_number == invoice_number,
                        )
                    )
                )
                result = await self.db.execute(query)
                itc_entry = result.scalar_one_or_none()

                if itc_entry:
                    itc_entry.gstr2b_matched = True
                    itc_entry.gstr2b_data = inv
                    if itc_entry.gstr2a_matched:
                        itc_entry.match_status = ITCMatchStatus.MATCHED.value
                    matched += 1

        await self.db.commit()

        return {
            "period": period,
            "matched": matched,
            "mismatches": mismatches,
        }

    async def utilize_itc(
        self,
        period: str,
        cgst_utilized: float,
        sgst_utilized: float,
        igst_utilized: float,
        cess_utilized: float = 0,
        utilized_by: Optional[UUID] = None,
    ) -> Dict:
        """
        Utilize ITC against output tax liability.

        Updates ITC ledger entries as utilized.
        """
        # Get available ITC entries for the period
        query = (
            select(ITCLedger)
            .where(
                and_(
                    ITCLedger.company_id == self.company_id,
                    ITCLedger.period <= period,
                    ITCLedger.status == ITCStatus.AVAILABLE.value,
                    ITCLedger.gstr2b_matched == True,  # Only matched ITC can be utilized
                )
            )
            .order_by(ITCLedger.invoice_date.asc())  # FIFO
        )

        result = await self.db.execute(query)
        entries = list(result.scalars().all())

        utilized_entries = []
        remaining = {
            "cgst": Decimal(str(cgst_utilized)),
            "sgst": Decimal(str(sgst_utilized)),
            "igst": Decimal(str(igst_utilized)),
            "cess": Decimal(str(cess_utilized)),
        }

        for entry in entries:
            if all(v <= 0 for v in remaining.values()):
                break

            utilized_amount = Decimal("0")

            # Utilize IGST first (can be used for CGST, SGST, IGST)
            if remaining["igst"] > 0 and entry.igst_itc > entry.utilized_amount:
                available = entry.igst_itc - entry.utilized_amount
                utilize = min(available, remaining["igst"])
                utilized_amount += utilize
                remaining["igst"] -= utilize

            # Then CGST
            if remaining["cgst"] > 0 and entry.cgst_itc > 0:
                available = entry.cgst_itc
                utilize = min(available, remaining["cgst"])
                utilized_amount += utilize
                remaining["cgst"] -= utilize

            # Then SGST
            if remaining["sgst"] > 0 and entry.sgst_itc > 0:
                available = entry.sgst_itc
                utilize = min(available, remaining["sgst"])
                utilized_amount += utilize
                remaining["sgst"] -= utilize

            if utilized_amount > 0:
                entry.utilized_amount += utilized_amount
                entry.utilized_in_period = period
                entry.utilized_at = datetime.now(timezone.utc)

                if entry.utilized_amount >= entry.total_itc:
                    entry.status = ITCStatus.UTILIZED.value

                utilized_entries.append({
                    "invoice_number": entry.invoice_number,
                    "vendor_gstin": entry.vendor_gstin,
                    "utilized_amount": float(utilized_amount),
                })

        await self.db.commit()

        # Calculate remaining balance
        available = await self.get_available_itc(period)

        return {
            "period": period,
            "cgst_utilized": float(cgst_utilized - float(remaining["cgst"])),
            "sgst_utilized": float(sgst_utilized - float(remaining["sgst"])),
            "igst_utilized": float(igst_utilized - float(remaining["igst"])),
            "cess_utilized": float(cess_utilized - float(remaining["cess"])),
            "total_utilized": float(
                (cgst_utilized - float(remaining["cgst"])) +
                (sgst_utilized - float(remaining["sgst"])) +
                (igst_utilized - float(remaining["igst"])) +
                (cess_utilized - float(remaining["cess"]))
            ),
            "remaining_balance": available["total_available"],
        }

    async def reverse_itc(
        self,
        itc_id: UUID,
        reversal_amount: Decimal,
        reason: str,
    ) -> ITCLedger:
        """
        Reverse ITC as per GST rules.

        Reasons include: Rule 42/43 reversal, non-payment, etc.
        """
        result = await self.db.execute(
            select(ITCLedger).where(ITCLedger.id == itc_id)
        )
        entry = result.scalar_one_or_none()

        if not entry:
            raise ValueError("ITC entry not found")

        if reversal_amount > entry.available_itc:
            raise ValueError("Reversal amount exceeds available ITC")

        entry.reversed_amount += reversal_amount
        entry.reversal_reason = reason
        entry.reversed_at = datetime.now(timezone.utc)

        if entry.reversed_amount >= entry.total_itc - entry.utilized_amount:
            entry.status = ITCStatus.REVERSED.value

        await self.db.commit()
        await self.db.refresh(entry)

        return entry

    async def get_itc_summary(self, period: Optional[str] = None) -> Dict:
        """
        Get ITC summary for frontend display.

        Returns aggregated ITC data including available, utilized, and reversed amounts.
        """
        # Get current period if not specified
        if not period:
            current_date = datetime.now(timezone.utc)
            period = self._get_period(current_date.year, current_date.month)

        # Get aggregated values from ITC ledger
        query = (
            select(
                func.sum(ITCLedger.cgst_itc).label("cgst_available"),
                func.sum(ITCLedger.sgst_itc).label("sgst_available"),
                func.sum(ITCLedger.igst_itc).label("igst_available"),
                func.sum(ITCLedger.cess_itc).label("cess_available"),
                func.sum(ITCLedger.total_itc).label("total_available"),
                func.sum(ITCLedger.utilized_amount).label("total_utilized"),
                func.sum(ITCLedger.reversed_amount).label("total_reversed"),
                func.count(ITCLedger.id).label("total_invoices"),
                func.sum(func.cast(ITCLedger.gstr2a_matched, type_=Decimal)).label("gstr2a_matched"),
                func.sum(func.cast(ITCLedger.gstr2b_matched, type_=Decimal)).label("gstr2b_matched"),
            )
            .where(
                and_(
                    ITCLedger.company_id == self.company_id,
                    ITCLedger.status == ITCStatus.AVAILABLE.value,
                )
            )
        )

        if period:
            query = query.where(ITCLedger.period <= period)

        result = await self.db.execute(query)
        row = result.one()

        total_available = float(row.total_available or 0)
        total_utilized = float(row.total_utilized or 0)
        total_reversed = float(row.total_reversed or 0)
        cgst_available = float(row.cgst_available or 0)
        sgst_available = float(row.sgst_available or 0)
        igst_available = float(row.igst_available or 0)
        cess_available = float(row.cess_available or 0)

        total_invoices = row.total_invoices or 0
        gstr2a_matched = int(row.gstr2a_matched or 0)
        gstr2b_matched = int(row.gstr2b_matched or 0)

        # Get mismatch count
        mismatch_query = (
            select(func.count(ITCLedger.id))
            .where(
                and_(
                    ITCLedger.company_id == self.company_id,
                    ITCLedger.match_status == ITCMatchStatus.PARTIAL_MATCH.value,
                )
            )
        )
        mismatch_result = await self.db.execute(mismatch_query)
        mismatch_count = mismatch_result.scalar() or 0

        # Get mismatch value
        mismatch_value_query = (
            select(func.sum(ITCLedger.total_itc))
            .where(
                and_(
                    ITCLedger.company_id == self.company_id,
                    ITCLedger.match_status == ITCMatchStatus.PARTIAL_MATCH.value,
                )
            )
        )
        mismatch_value_result = await self.db.execute(mismatch_value_query)
        mismatch_value = float(mismatch_value_result.scalar() or 0)

        return {
            "total_available": total_available,
            "total_utilized": total_utilized,
            "total_reversed": total_reversed,
            "balance": total_available - total_utilized - total_reversed,
            "cgst_available": cgst_available,
            "sgst_available": sgst_available,
            "igst_available": igst_available,
            "cess_available": cess_available,
            "matched_with_gstr2a": gstr2a_matched,
            "matched_with_gstr2b": gstr2b_matched,
            "mismatch_count": mismatch_count,
            "mismatch_value": mismatch_value,
        }

    async def get_itc_summary_model(self, period: str) -> Optional[ITCSummary]:
        """Get or create ITC summary model for a period."""
        result = await self.db.execute(
            select(ITCSummary)
            .where(
                and_(
                    ITCSummary.company_id == self.company_id,
                    ITCSummary.period == period,
                )
            )
        )
        summary = result.scalar_one_or_none()

        if not summary:
            summary = await self._calculate_summary(period)

        return summary

    async def _calculate_summary(self, period: str) -> ITCSummary:
        """Calculate and create ITC summary for a period."""
        # Get aggregated values
        query = (
            select(
                func.sum(ITCLedger.cgst_itc).label("total_cgst"),
                func.sum(ITCLedger.sgst_itc).label("total_sgst"),
                func.sum(ITCLedger.igst_itc).label("total_igst"),
                func.sum(ITCLedger.cess_itc).label("total_cess"),
                func.sum(ITCLedger.utilized_amount).label("total_utilized"),
                func.sum(ITCLedger.reversed_amount).label("total_reversed"),
                func.count(ITCLedger.id).label("total_invoices"),
                func.sum(
                    func.cast(ITCLedger.gstr2b_matched, type_=Decimal)
                ).label("matched_count"),
            )
            .where(
                and_(
                    ITCLedger.company_id == self.company_id,
                    ITCLedger.period == period,
                )
            )
        )

        result = await self.db.execute(query)
        row = result.one()

        # Get previous period closing balance
        prev_period = self._get_previous_period(period)
        prev_summary = await self.db.execute(
            select(ITCSummary)
            .where(
                and_(
                    ITCSummary.company_id == self.company_id,
                    ITCSummary.period == prev_period,
                )
            )
        )
        prev = prev_summary.scalar_one_or_none()

        summary = ITCSummary(
            id=uuid4(),
            company_id=self.company_id,
            period=period,
            opening_cgst=prev.closing_cgst if prev else Decimal("0"),
            opening_sgst=prev.closing_sgst if prev else Decimal("0"),
            opening_igst=prev.closing_igst if prev else Decimal("0"),
            opening_cess=prev.closing_cess if prev else Decimal("0"),
            availed_cgst=row.total_cgst or Decimal("0"),
            availed_sgst=row.total_sgst or Decimal("0"),
            availed_igst=row.total_igst or Decimal("0"),
            availed_cess=row.total_cess or Decimal("0"),
            total_invoices=row.total_invoices or 0,
            matched_invoices=int(row.matched_count or 0),
            unmatched_invoices=(row.total_invoices or 0) - int(row.matched_count or 0),
        )

        # Calculate closing balances
        summary.closing_cgst = summary.opening_cgst + summary.availed_cgst - summary.utilized_cgst - summary.reversed_cgst
        summary.closing_sgst = summary.opening_sgst + summary.availed_sgst - summary.utilized_sgst - summary.reversed_sgst
        summary.closing_igst = summary.opening_igst + summary.availed_igst - summary.utilized_igst - summary.reversed_igst
        summary.closing_cess = summary.opening_cess + summary.availed_cess - summary.utilized_cess - summary.reversed_cess

        self.db.add(summary)
        await self.db.commit()
        await self.db.refresh(summary)

        return summary

    def _get_previous_period(self, period: str) -> str:
        """Get previous period in YYYYMM format."""
        year = int(period[:4])
        month = int(period[4:])

        if month == 1:
            return f"{year - 1}12"
        return f"{year}{month - 1:02d}"

    async def get_itc_dashboard(self) -> Dict:
        """Get ITC dashboard data."""
        current_date = datetime.now(timezone.utc)
        current_period = self._get_period(current_date.year, current_date.month)

        # Get available ITC
        available = await self.get_available_itc()

        # Get matching statistics
        match_query = (
            select(
                func.count(ITCLedger.id).label("total"),
                func.sum(func.cast(ITCLedger.gstr2a_matched, type_=Decimal)).label("gstr2a_matched"),
                func.sum(func.cast(ITCLedger.gstr2b_matched, type_=Decimal)).label("gstr2b_matched"),
            )
            .where(
                and_(
                    ITCLedger.company_id == self.company_id,
                    ITCLedger.period == current_period,
                )
            )
        )
        match_result = await self.db.execute(match_query)
        match_row = match_result.one()

        total_invoices = match_row.total or 0
        gstr2a_matched = int(match_row.gstr2a_matched or 0)
        gstr2b_matched = int(match_row.gstr2b_matched or 0)

        return {
            "current_period": current_period,
            "available_itc": available,
            "matching_status": {
                "total_invoices": total_invoices,
                "gstr2a_matched": gstr2a_matched,
                "gstr2b_matched": gstr2b_matched,
                "unmatched": total_invoices - gstr2a_matched,
                "match_rate": round(gstr2a_matched / total_invoices * 100, 2) if total_invoices > 0 else 0,
            },
        }

    async def reverse_itc_entry(
        self,
        entry_id: UUID,
        reason: str,
        amount: Optional[float] = None,
        reversed_by: Optional[UUID] = None,
    ) -> Dict:
        """
        Reverse an ITC entry.

        Args:
            entry_id: ID of the ITC entry to reverse
            reason: Reason for reversal
            amount: Optional amount to reverse (full reversal if not specified)
            reversed_by: User ID who initiated the reversal

        Returns:
            Dict with reversal details
        """
        result = await self.db.execute(
            select(ITCLedger).where(
                and_(
                    ITCLedger.id == entry_id,
                    ITCLedger.company_id == self.company_id,
                )
            )
        )
        entry = result.scalar_one_or_none()

        if not entry:
            raise ValueError("ITC entry not found")

        if entry.status != ITCStatus.AVAILABLE.value:
            raise ValueError(f"Cannot reverse ITC with status {entry.status}")

        # Determine reversal amount
        available = float(entry.total_itc - entry.utilized_amount - entry.reversed_amount)
        reversal_amount = amount if amount is not None else available

        if reversal_amount > available:
            raise ValueError(f"Reversal amount ({reversal_amount}) exceeds available ITC ({available})")

        # Update entry
        entry.reversed_amount = Decimal(str(entry.reversed_amount)) + Decimal(str(reversal_amount))
        entry.reversal_reason = reason
        entry.reversed_at = datetime.now(timezone.utc)

        # Update status if fully reversed
        if float(entry.reversed_amount) >= float(entry.total_itc - entry.utilized_amount):
            entry.status = ITCStatus.REVERSED.value

        await self.db.flush()
        await self.db.refresh(entry)

        return {
            "id": entry.id,
            "reversed_amount": float(reversal_amount),
            "new_status": entry.status,
            "reason": reason,
        }

    async def get_mismatch_report(self, period: str) -> Dict:
        """
        Get ITC mismatch report for a period.

        Finds discrepancies between:
        - ITC in books but not in GSTR-2A/2B (MISSING_IN_PORTAL)
        - ITC with amount differences (AMOUNT_MISMATCH)
        - ITC in portal but not in books (EXTRA_IN_PORTAL - requires GSTR2A data)

        Returns:
            Dict with mismatch details and counts
        """
        # Get entries with mismatches
        query = (
            select(ITCLedger)
            .where(
                and_(
                    ITCLedger.company_id == self.company_id,
                    ITCLedger.period == period,
                    ITCLedger.match_status.in_([
                        ITCMatchStatus.UNMATCHED.value,
                        ITCMatchStatus.PARTIAL_MATCH.value,
                    ])
                )
            )
            .order_by(ITCLedger.invoice_date.desc())
        )

        result = await self.db.execute(query)
        entries = list(result.scalars().all())

        items = []
        missing_in_portal = 0
        amount_mismatches = 0
        extra_in_portal = 0
        total_mismatch_value = Decimal("0")

        for entry in entries:
            mismatch_type = "MISSING_IN_PORTAL"
            difference = float(entry.total_itc)

            if entry.match_status == ITCMatchStatus.PARTIAL_MATCH.value:
                mismatch_type = "AMOUNT_MISMATCH"
                difference = float(entry.match_difference or 0)
                amount_mismatches += 1
            else:
                missing_in_portal += 1

            total_mismatch_value += abs(Decimal(str(difference)))

            items.append({
                "id": entry.id,
                "vendor_gstin": entry.vendor_gstin,
                "vendor_name": entry.vendor_name,
                "invoice_number": entry.invoice_number,
                "invoice_date": entry.invoice_date,
                "books_amount": float(entry.total_itc),
                "portal_amount": float(entry.total_itc) - difference if mismatch_type == "AMOUNT_MISMATCH" else 0,
                "difference": difference,
                "mismatch_type": mismatch_type,
            })

        return {
            "period": period,
            "items": items,
            "total_mismatch_count": len(items),
            "total_mismatch_value": float(total_mismatch_value),
            "missing_in_portal": missing_in_portal,
            "amount_mismatches": amount_mismatches,
            "extra_in_portal": extra_in_portal,
        }
