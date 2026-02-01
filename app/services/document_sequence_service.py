"""
Document Sequence Service for Atomic Number Generation

INDUSTRY BEST PRACTICE:
- Financial year based numbering (April-March)
- Continuous sequence within financial year (NO daily reset)
- Atomic number generation with database-level locking
- Format: {PREFIX}/{COMPANY_CODE}/{FY}/{SEQUENCE}

USAGE:
    from app.services.document_sequence_service import DocumentSequenceService

    async def create_pr(db: AsyncSession):
        service = DocumentSequenceService(db)
        pr_number = await service.get_next_number("PR")
        # Returns: PR/APL/25-26/00001

SUPPORTED DOCUMENT TYPES:
    PR  - Purchase Requisition
    PO  - Purchase Order
    GRN - Goods Receipt Note
    SRN - Sales Return Note
    ST  - Stock Transfer
    SA  - Stock Adjustment
    MF  - Manifest
    PL  - Picklist
"""

from typing import Optional
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document_sequence import DocumentSequence, DocumentSequenceAudit, DocumentType


# Document type metadata
DOCUMENT_METADATA = {
    "PR": {"name": "Purchase Requisition", "padding": 5},
    "PO": {"name": "Purchase Order", "padding": 5},
    "GRN": {"name": "Goods Receipt Note", "padding": 5},
    "SRN": {"name": "Sales Return Note", "padding": 5},
    "ST": {"name": "Stock Transfer", "padding": 5},
    "SA": {"name": "Stock Adjustment", "padding": 5},
    "MF": {"name": "Manifest", "padding": 5},
    "PL": {"name": "Picklist", "padding": 5},
    "DEMO": {"name": "Demo Booking", "padding": 5},
}


class DocumentSequenceService:
    """
    Service for generating atomic document numbers.

    Uses database-level locking (SELECT FOR UPDATE) to ensure
    no duplicate numbers are generated even under concurrent load.

    Features:
    - Atomic number generation with database-level locking
    - Audit logging for all operations
    - Automatic sync via database triggers
    """

    def __init__(
        self,
        db: AsyncSession,
        company_code: str = "APL",
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None
    ):
        """
        Initialize the service.

        Args:
            db: Async database session
            company_code: Company code for document numbers (default: APL)
            user_id: Optional user ID for audit logging
            ip_address: Optional IP address for audit logging
        """
        self.db = db
        self.company_code = company_code
        self.user_id = user_id
        self.ip_address = ip_address

    async def _log_audit(
        self,
        document_type: str,
        financial_year: str,
        operation: str,
        old_number: Optional[int] = None,
        new_number: Optional[int] = None,
        document_number: Optional[str] = None,
        source: str = "API"
    ):
        """Log an audit record for sequence operations."""
        import uuid as uuid_module
        audit = DocumentSequenceAudit(
            document_type=document_type,
            financial_year=financial_year,
            operation=operation,
            old_number=old_number,
            new_number=new_number,
            document_number=document_number,
            source=source,
            user_id=uuid_module.UUID(self.user_id) if self.user_id else None,
            ip_address=self.ip_address,
        )
        self.db.add(audit)

    async def get_next_number(
        self,
        document_type: str,
        financial_year: Optional[str] = None
    ) -> str:
        """
        Get next document number with atomic increment.

        Uses SELECT FOR UPDATE to prevent race conditions.
        Creates sequence record if it doesn't exist.
        Logs the operation to audit table.

        Args:
            document_type: Document type code (PR, PO, GRN, etc.)
            financial_year: Optional FY string. Auto-calculated if not provided.

        Returns:
            Formatted document number, e.g., PR/APL/25-26/00001

        Raises:
            ValueError: If document_type is invalid
        """
        # Validate document type
        doc_type = document_type.upper()
        if doc_type not in DOCUMENT_METADATA:
            valid_types = ", ".join(DOCUMENT_METADATA.keys())
            raise ValueError(f"Invalid document type '{doc_type}'. Valid types: {valid_types}")

        # Get current financial year if not provided
        if not financial_year:
            financial_year = DocumentSequence.get_financial_year()

        # Lock and get/create sequence record
        sequence = await self._get_or_create_sequence(doc_type, financial_year)

        # Store old number for audit
        old_number = sequence.current_number

        # Generate the next number
        doc_number = sequence.get_next_number()

        # Log to audit table
        await self._log_audit(
            document_type=doc_type,
            financial_year=financial_year,
            operation="GET_NEXT",
            old_number=old_number,
            new_number=sequence.current_number,
            document_number=doc_number,
            source="API"
        )

        # Commit to release lock and persist increment
        await self.db.flush()

        return doc_number

    async def preview_next_number(
        self,
        document_type: str,
        financial_year: Optional[str] = None
    ) -> str:
        """
        Preview what the next number would be without incrementing.

        Args:
            document_type: Document type code
            financial_year: Optional FY string

        Returns:
            What the next document number would be
        """
        doc_type = document_type.upper()
        if doc_type not in DOCUMENT_METADATA:
            valid_types = ", ".join(DOCUMENT_METADATA.keys())
            raise ValueError(f"Invalid document type '{doc_type}'. Valid types: {valid_types}")

        if not financial_year:
            financial_year = DocumentSequence.get_financial_year()

        # Get sequence without locking
        result = await self.db.execute(
            select(DocumentSequence)
            .where(
                DocumentSequence.document_type == doc_type,
                DocumentSequence.financial_year == financial_year,
                DocumentSequence.is_active == True
            )
        )
        sequence = result.scalar_one_or_none()

        if sequence:
            return sequence.preview_next_number()

        # No sequence exists yet - would be first number
        metadata = DOCUMENT_METADATA[doc_type]
        padding = metadata["padding"]
        seq = "1".zfill(padding)
        return f"{doc_type}/{self.company_code}/{financial_year}/{seq}"

    async def get_current_number(
        self,
        document_type: str,
        financial_year: Optional[str] = None
    ) -> int:
        """
        Get the current (last used) sequence number.

        Args:
            document_type: Document type code
            financial_year: Optional FY string

        Returns:
            Current sequence number (0 if no sequence exists)
        """
        doc_type = document_type.upper()
        if not financial_year:
            financial_year = DocumentSequence.get_financial_year()

        result = await self.db.execute(
            select(DocumentSequence.current_number)
            .where(
                DocumentSequence.document_type == doc_type,
                DocumentSequence.financial_year == financial_year,
                DocumentSequence.is_active == True
            )
        )
        current = result.scalar_one_or_none()
        return current or 0

    async def initialize_sequence(
        self,
        document_type: str,
        starting_number: int = 0,
        financial_year: Optional[str] = None
    ) -> DocumentSequence:
        """
        Initialize or reset a sequence to a specific number.

        Use this to migrate existing data or correct sequences.

        Args:
            document_type: Document type code
            starting_number: Number to start from (next will be +1)
            financial_year: Optional FY string

        Returns:
            The sequence record
        """
        doc_type = document_type.upper()
        if doc_type not in DOCUMENT_METADATA:
            raise ValueError(f"Invalid document type: {doc_type}")

        if not financial_year:
            financial_year = DocumentSequence.get_financial_year()

        metadata = DOCUMENT_METADATA[doc_type]

        # Get existing or create new
        result = await self.db.execute(
            select(DocumentSequence)
            .where(
                DocumentSequence.document_type == doc_type,
                DocumentSequence.financial_year == financial_year
            )
            .with_for_update()
        )
        sequence = result.scalar_one_or_none()

        if sequence:
            sequence.current_number = starting_number
            sequence.is_active = True
        else:
            sequence = DocumentSequence(
                document_type=doc_type,
                document_name=metadata["name"],
                company_code=self.company_code,
                financial_year=financial_year,
                current_number=starting_number,
                padding_length=metadata["padding"],
            )
            self.db.add(sequence)

        await self.db.flush()
        return sequence

    async def _get_or_create_sequence(
        self,
        document_type: str,
        financial_year: str
    ) -> DocumentSequence:
        """
        Get existing sequence with row lock, or create new one.

        Uses SELECT FOR UPDATE for atomic operations.

        Args:
            document_type: Document type code
            financial_year: Financial year string

        Returns:
            DocumentSequence record (locked for update)
        """
        # Try to get existing sequence with lock
        result = await self.db.execute(
            select(DocumentSequence)
            .where(
                DocumentSequence.document_type == document_type,
                DocumentSequence.financial_year == financial_year,
                DocumentSequence.is_active == True
            )
            .with_for_update()
        )
        sequence = result.scalar_one_or_none()

        if sequence:
            return sequence

        # Create new sequence
        metadata = DOCUMENT_METADATA[document_type]
        sequence = DocumentSequence(
            document_type=document_type,
            document_name=metadata["name"],
            company_code=self.company_code,
            financial_year=financial_year,
            current_number=0,
            padding_length=metadata["padding"],
        )
        self.db.add(sequence)
        await self.db.flush()

        # Re-fetch with lock to ensure atomicity
        result = await self.db.execute(
            select(DocumentSequence)
            .where(DocumentSequence.id == sequence.id)
            .with_for_update()
        )
        return result.scalar_one()


    async def sync_sequence_from_max(
        self,
        document_type: str,
        max_sequence_number: int,
        financial_year: Optional[str] = None
    ) -> DocumentSequence:
        """
        Sync a sequence to match the maximum used number.

        Use this to repair sequences that are out of sync with actual documents.

        Args:
            document_type: Document type code
            max_sequence_number: The highest sequence number found in documents
            financial_year: Optional FY string

        Returns:
            Updated sequence record
        """
        doc_type = document_type.upper()
        if doc_type not in DOCUMENT_METADATA:
            raise ValueError(f"Invalid document type: {doc_type}")

        if not financial_year:
            financial_year = DocumentSequence.get_financial_year()

        # Get or create sequence with lock
        result = await self.db.execute(
            select(DocumentSequence)
            .where(
                DocumentSequence.document_type == doc_type,
                DocumentSequence.financial_year == financial_year
            )
            .with_for_update()
        )
        sequence = result.scalar_one_or_none()

        old_number = sequence.current_number if sequence else 0

        if sequence:
            if max_sequence_number > sequence.current_number:
                sequence.current_number = max_sequence_number
        else:
            metadata = DOCUMENT_METADATA[doc_type]
            sequence = DocumentSequence(
                document_type=doc_type,
                document_name=metadata["name"],
                company_code=self.company_code,
                financial_year=financial_year,
                current_number=max_sequence_number,
                padding_length=metadata["padding"],
            )
            self.db.add(sequence)

        # Log to audit
        await self._log_audit(
            document_type=doc_type,
            financial_year=financial_year,
            operation="MANUAL_SYNC",
            old_number=old_number,
            new_number=max_sequence_number,
            source="API"
        )

        await self.db.flush()
        return sequence

    async def verify_and_repair_sequence(
        self,
        document_type: str,
        table_name: str,
        number_column: str,
        financial_year: Optional[str] = None
    ) -> dict:
        """
        Verify sequence is in sync with actual documents and repair if needed.

        Args:
            document_type: Document type code (PR, PO, GRN)
            table_name: Database table name
            number_column: Column containing document number
            financial_year: Optional FY string

        Returns:
            Dict with verification results
        """
        doc_type = document_type.upper()
        if not financial_year:
            financial_year = DocumentSequence.get_financial_year()

        # Get current sequence
        current = await self.get_current_number(doc_type, financial_year)

        # Get max from actual documents using raw SQL
        pattern = f"%/{financial_year}/%"
        result = await self.db.execute(
            text(f"""
                SELECT MAX(
                    CAST(
                        NULLIF(split_part({number_column}, '/', 4), '') AS INTEGER
                    )
                ) as max_seq
                FROM {table_name}
                WHERE {number_column} LIKE :pattern
            """),
            {"pattern": pattern}
        )
        row = result.fetchone()
        max_in_docs = row[0] if row and row[0] else 0

        status = "OK" if current >= max_in_docs else "MISMATCH"
        repaired = False

        if current < max_in_docs:
            await self.sync_sequence_from_max(doc_type, max_in_docs, financial_year)
            repaired = True

        return {
            "document_type": doc_type,
            "financial_year": financial_year,
            "sequence_counter": current,
            "max_in_documents": max_in_docs,
            "status": status,
            "repaired": repaired,
        }


# Convenience function for quick access
async def get_next_document_number(
    db: AsyncSession,
    document_type: str,
    company_code: str = "APL",
    financial_year: Optional[str] = None
) -> str:
    """
    Quick function to get next document number.

    Usage:
        pr_number = await get_next_document_number(db, "PR")
        po_number = await get_next_document_number(db, "PO")
    """
    service = DocumentSequenceService(db, company_code)
    return await service.get_next_number(document_type, financial_year)
