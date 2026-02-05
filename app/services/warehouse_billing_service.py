"""
Warehouse Billing Service - Phase 10: Storage & Operations Billing.

Business logic for warehouse billing operations.
"""
import uuid
from datetime import datetime, timezone, date, timedelta
from decimal import Decimal
from typing import Optional, List, Tuple, Dict, Any

from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.warehouse_billing import (
    BillingContract, BillingRateCard, StorageCharge, HandlingCharge,
    ValueAddedServiceCharge, BillingInvoice, BillingInvoiceItem,
    BillingType, ContractStatus, InvoiceStatus, BillingPeriod, ChargeCategory
)
from app.schemas.warehouse_billing import (
    BillingContractCreate, BillingContractUpdate, ContractActivate,
    BillingRateCardCreate, BillingRateCardUpdate,
    StorageChargeCreate, HandlingChargeCreate, VASChargeCreate,
    BillingInvoiceCreate, BillingInvoiceUpdate,
    InvoiceSend, InvoicePayment, InvoiceDispute, GenerateInvoice,
    BillingDashboard
)


class WarehouseBillingService:
    """Service for warehouse billing operations."""

    def __init__(self, db: AsyncSession, tenant_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id

    # =========================================================================
    # CONTRACTS
    # =========================================================================

    async def _generate_contract_number(self) -> str:
        """Generate unique contract number."""
        today = datetime.now(timezone.utc).strftime("%Y%m")
        prefix = f"BC-{today}"

        query = select(func.count(BillingContract.id)).where(
            BillingContract.contract_number.like(f"{prefix}%")
        )
        count = await self.db.scalar(query) or 0
        return f"{prefix}-{count + 1:04d}"

    async def create_contract(
        self,
        data: BillingContractCreate,
        user_id: Optional[uuid.UUID] = None
    ) -> BillingContract:
        """Create a billing contract."""
        contract = BillingContract(
            tenant_id=self.tenant_id,
            contract_number=await self._generate_contract_number(),
            contract_name=data.contract_name,
            description=data.description,
            status=ContractStatus.DRAFT.value,
            customer_id=data.customer_id,
            warehouse_id=data.warehouse_id,
            billing_type=data.billing_type.value,
            billing_period=data.billing_period.value,
            billing_day=data.billing_day,
            start_date=data.start_date,
            end_date=data.end_date,
            auto_renew=data.auto_renew,
            minimum_storage_fee=data.minimum_storage_fee,
            minimum_handling_fee=data.minimum_handling_fee,
            minimum_monthly_fee=data.minimum_monthly_fee,
            payment_terms_days=data.payment_terms_days,
            currency=data.currency,
            late_fee_percent=data.late_fee_percent,
            grace_period_days=data.grace_period_days,
            volume_discounts=data.volume_discounts,
            special_terms=data.special_terms,
            notes=data.notes,
            created_by=user_id
        )
        self.db.add(contract)
        await self.db.flush()

        # Add rate cards if provided
        if data.rate_cards:
            for rc_data in data.rate_cards:
                rate_card = BillingRateCard(
                    tenant_id=self.tenant_id,
                    contract_id=contract.id,
                    charge_category=rc_data.charge_category.value,
                    charge_type=rc_data.charge_type,
                    charge_name=rc_data.charge_name,
                    description=rc_data.description,
                    billing_model=rc_data.billing_model,
                    uom=rc_data.uom,
                    base_rate=rc_data.base_rate,
                    min_charge=rc_data.min_charge,
                    max_charge=rc_data.max_charge,
                    tiered_rates=rc_data.tiered_rates,
                    time_based_rates=rc_data.time_based_rates,
                    effective_from=rc_data.effective_from,
                    effective_to=rc_data.effective_to,
                    notes=rc_data.notes
                )
                self.db.add(rate_card)

        await self.db.commit()
        await self.db.refresh(contract)
        return contract

    async def get_contract(
        self,
        contract_id: uuid.UUID,
        include_rate_cards: bool = True
    ) -> Optional[BillingContract]:
        """Get contract by ID."""
        query = select(BillingContract).where(
            and_(
                BillingContract.id == contract_id,
                BillingContract.tenant_id == self.tenant_id
            )
        )
        if include_rate_cards:
            query = query.options(selectinload(BillingContract.rate_cards))

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def list_contracts(
        self,
        customer_id: Optional[uuid.UUID] = None,
        warehouse_id: Optional[uuid.UUID] = None,
        status: Optional[ContractStatus] = None,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[BillingContract], int]:
        """List contracts with filters."""
        query = select(BillingContract).where(
            BillingContract.tenant_id == self.tenant_id
        )

        if customer_id:
            query = query.where(BillingContract.customer_id == customer_id)
        if warehouse_id:
            query = query.where(BillingContract.warehouse_id == warehouse_id)
        if status:
            query = query.where(BillingContract.status == status.value)

        count_query = select(func.count()).select_from(query.subquery())
        total = await self.db.scalar(count_query) or 0

        query = query.options(selectinload(BillingContract.rate_cards))
        query = query.order_by(BillingContract.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all()), total

    async def update_contract(
        self,
        contract_id: uuid.UUID,
        data: BillingContractUpdate
    ) -> Optional[BillingContract]:
        """Update contract."""
        contract = await self.get_contract(contract_id)
        if not contract:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if field in ["billing_type", "billing_period"] and value:
                value = value.value
            setattr(contract, field, value)

        contract.updated_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(contract)
        return contract

    async def activate_contract(
        self,
        contract_id: uuid.UUID,
        user_id: uuid.UUID
    ) -> Optional[BillingContract]:
        """Activate a contract."""
        contract = await self.get_contract(contract_id)
        if not contract or contract.status != ContractStatus.DRAFT.value:
            return None

        contract.status = ContractStatus.ACTIVE.value
        contract.approved_by = user_id
        contract.approved_at = datetime.now(timezone.utc)
        contract.updated_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(contract)
        return contract

    # =========================================================================
    # RATE CARDS
    # =========================================================================

    async def add_rate_card(
        self,
        contract_id: uuid.UUID,
        data: BillingRateCardCreate
    ) -> Optional[BillingRateCard]:
        """Add rate card to contract."""
        contract = await self.get_contract(contract_id, include_rate_cards=False)
        if not contract:
            return None

        rate_card = BillingRateCard(
            tenant_id=self.tenant_id,
            contract_id=contract_id,
            charge_category=data.charge_category.value,
            charge_type=data.charge_type,
            charge_name=data.charge_name,
            description=data.description,
            billing_model=data.billing_model,
            uom=data.uom,
            base_rate=data.base_rate,
            min_charge=data.min_charge,
            max_charge=data.max_charge,
            tiered_rates=data.tiered_rates,
            time_based_rates=data.time_based_rates,
            effective_from=data.effective_from,
            effective_to=data.effective_to,
            notes=data.notes
        )
        self.db.add(rate_card)
        await self.db.commit()
        await self.db.refresh(rate_card)
        return rate_card

    async def update_rate_card(
        self,
        rate_card_id: uuid.UUID,
        data: BillingRateCardUpdate
    ) -> Optional[BillingRateCard]:
        """Update rate card."""
        query = select(BillingRateCard).where(
            and_(
                BillingRateCard.id == rate_card_id,
                BillingRateCard.tenant_id == self.tenant_id
            )
        )
        result = await self.db.execute(query)
        rate_card = result.scalar_one_or_none()
        if not rate_card:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(rate_card, field, value)

        rate_card.updated_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(rate_card)
        return rate_card

    # =========================================================================
    # CHARGES
    # =========================================================================

    async def create_storage_charge(
        self,
        data: StorageChargeCreate
    ) -> StorageCharge:
        """Create a storage charge."""
        amount = data.quantity * data.rate

        charge = StorageCharge(
            tenant_id=self.tenant_id,
            contract_id=data.contract_id,
            customer_id=data.customer_id,
            warehouse_id=data.warehouse_id,
            rate_card_id=data.rate_card_id,
            charge_date=data.charge_date,
            storage_type=data.storage_type,
            zone_id=data.zone_id,
            quantity=data.quantity,
            uom=data.uom,
            rate=data.rate,
            amount=amount,
            breakdown=data.breakdown,
            notes=data.notes
        )
        self.db.add(charge)
        await self.db.commit()
        await self.db.refresh(charge)
        return charge

    async def create_handling_charge(
        self,
        data: HandlingChargeCreate
    ) -> HandlingCharge:
        """Create a handling charge."""
        amount = data.quantity * data.rate
        labor_amount = Decimal("0")
        if data.labor_hours and data.labor_rate:
            labor_amount = data.labor_hours * data.labor_rate

        charge = HandlingCharge(
            tenant_id=self.tenant_id,
            contract_id=data.contract_id,
            customer_id=data.customer_id,
            warehouse_id=data.warehouse_id,
            rate_card_id=data.rate_card_id,
            charge_date=data.charge_date,
            charge_category=data.charge_category.value,
            charge_type=data.charge_type,
            charge_description=data.charge_description,
            source_type=data.source_type,
            source_id=data.source_id,
            source_number=data.source_number,
            quantity=data.quantity,
            uom=data.uom,
            rate=data.rate,
            amount=amount,
            labor_hours=data.labor_hours,
            labor_rate=data.labor_rate,
            labor_amount=labor_amount,
            notes=data.notes
        )
        self.db.add(charge)
        await self.db.commit()
        await self.db.refresh(charge)
        return charge

    async def create_vas_charge(
        self,
        data: VASChargeCreate
    ) -> ValueAddedServiceCharge:
        """Create a VAS charge."""
        amount = data.quantity * data.rate

        charge = ValueAddedServiceCharge(
            tenant_id=self.tenant_id,
            contract_id=data.contract_id,
            customer_id=data.customer_id,
            warehouse_id=data.warehouse_id,
            rate_card_id=data.rate_card_id,
            charge_date=data.charge_date,
            service_type=data.service_type,
            service_name=data.service_name,
            service_description=data.service_description,
            source_type=data.source_type,
            source_id=data.source_id,
            source_number=data.source_number,
            quantity=data.quantity,
            uom=data.uom,
            rate=data.rate,
            amount=amount,
            materials_cost=data.materials_cost,
            materials_detail=data.materials_detail,
            notes=data.notes
        )
        self.db.add(charge)
        await self.db.commit()
        await self.db.refresh(charge)
        return charge

    async def list_unbilled_charges(
        self,
        contract_id: uuid.UUID,
        from_date: date,
        to_date: date
    ) -> Dict[str, List]:
        """List unbilled charges for a contract."""
        storage_query = select(StorageCharge).where(
            and_(
                StorageCharge.tenant_id == self.tenant_id,
                StorageCharge.contract_id == contract_id,
                StorageCharge.charge_date >= from_date,
                StorageCharge.charge_date <= to_date,
                StorageCharge.is_billed == False
            )
        )
        storage_result = await self.db.execute(storage_query)
        storage_charges = list(storage_result.scalars().all())

        handling_query = select(HandlingCharge).where(
            and_(
                HandlingCharge.tenant_id == self.tenant_id,
                HandlingCharge.contract_id == contract_id,
                HandlingCharge.charge_date >= from_date,
                HandlingCharge.charge_date <= to_date,
                HandlingCharge.is_billed == False
            )
        )
        handling_result = await self.db.execute(handling_query)
        handling_charges = list(handling_result.scalars().all())

        vas_query = select(ValueAddedServiceCharge).where(
            and_(
                ValueAddedServiceCharge.tenant_id == self.tenant_id,
                ValueAddedServiceCharge.contract_id == contract_id,
                ValueAddedServiceCharge.charge_date >= from_date,
                ValueAddedServiceCharge.charge_date <= to_date,
                ValueAddedServiceCharge.is_billed == False
            )
        )
        vas_result = await self.db.execute(vas_query)
        vas_charges = list(vas_result.scalars().all())

        return {
            "storage": storage_charges,
            "handling": handling_charges,
            "vas": vas_charges
        }

    # =========================================================================
    # INVOICES
    # =========================================================================

    async def _generate_invoice_number(self) -> str:
        """Generate unique invoice number."""
        today = datetime.now(timezone.utc).strftime("%Y%m")
        prefix = f"WBI-{today}"

        query = select(func.count(BillingInvoice.id)).where(
            BillingInvoice.invoice_number.like(f"{prefix}%")
        )
        count = await self.db.scalar(query) or 0
        return f"{prefix}-{count + 1:04d}"

    async def generate_invoice(
        self,
        data: GenerateInvoice,
        user_id: Optional[uuid.UUID] = None
    ) -> BillingInvoice:
        """Generate an invoice from unbilled charges."""
        # Get contract
        contract = await self.get_contract(data.contract_id)
        if not contract:
            raise ValueError("Contract not found")

        # Get unbilled charges
        charges = await self.list_unbilled_charges(
            data.contract_id,
            data.period_start,
            data.period_end
        )

        # Calculate amounts
        storage_amount = sum(c.amount for c in charges["storage"]) if data.include_storage else Decimal("0")
        handling_amount = sum(c.amount for c in charges["handling"]) if data.include_handling else Decimal("0")
        vas_amount = sum(c.amount for c in charges["vas"]) if data.include_vas else Decimal("0")
        labor_amount = sum(c.labor_amount for c in charges["handling"]) if data.include_handling else Decimal("0")

        subtotal = storage_amount + handling_amount + vas_amount + labor_amount

        # Apply minimums
        if data.apply_minimums:
            if storage_amount < contract.minimum_storage_fee:
                storage_amount = contract.minimum_storage_fee
            if handling_amount < contract.minimum_handling_fee:
                handling_amount = contract.minimum_handling_fee
            subtotal = storage_amount + handling_amount + vas_amount + labor_amount
            if subtotal < contract.minimum_monthly_fee:
                subtotal = contract.minimum_monthly_fee

        # Calculate tax (18% GST default)
        tax_rate = Decimal("18")
        tax_amount = subtotal * tax_rate / 100

        total_amount = subtotal + tax_amount
        due_date = data.period_end + timedelta(days=contract.payment_terms_days)

        # Create invoice
        invoice = BillingInvoice(
            tenant_id=self.tenant_id,
            invoice_number=await self._generate_invoice_number(),
            status=InvoiceStatus.DRAFT.value,
            contract_id=contract.id,
            customer_id=contract.customer_id,
            warehouse_id=contract.warehouse_id,
            period_start=data.period_start,
            period_end=data.period_end,
            invoice_date=date.today(),
            due_date=due_date,
            storage_amount=storage_amount,
            handling_amount=handling_amount,
            vas_amount=vas_amount,
            labor_amount=labor_amount,
            subtotal=subtotal,
            tax_amount=tax_amount,
            tax_rate=tax_rate,
            total_amount=total_amount,
            balance_due=total_amount,
            currency=contract.currency,
            created_by=user_id
        )
        self.db.add(invoice)
        await self.db.flush()

        # Add line items
        line_number = 1
        if data.include_storage and charges["storage"]:
            item = BillingInvoiceItem(
                tenant_id=self.tenant_id,
                invoice_id=invoice.id,
                charge_category="STORAGE",
                charge_type="STORAGE_TOTAL",
                description=f"Storage charges for {data.period_start} to {data.period_end}",
                quantity=Decimal("1"),
                uom="LUMP",
                rate=storage_amount,
                amount=storage_amount,
                line_number=line_number
            )
            self.db.add(item)
            line_number += 1

        if data.include_handling and charges["handling"]:
            item = BillingInvoiceItem(
                tenant_id=self.tenant_id,
                invoice_id=invoice.id,
                charge_category="HANDLING",
                charge_type="HANDLING_TOTAL",
                description=f"Handling charges for {data.period_start} to {data.period_end}",
                quantity=Decimal("1"),
                uom="LUMP",
                rate=handling_amount,
                amount=handling_amount,
                line_number=line_number
            )
            self.db.add(item)
            line_number += 1

        if data.include_vas and charges["vas"]:
            item = BillingInvoiceItem(
                tenant_id=self.tenant_id,
                invoice_id=invoice.id,
                charge_category="VAS",
                charge_type="VAS_TOTAL",
                description=f"Value-added service charges for {data.period_start} to {data.period_end}",
                quantity=Decimal("1"),
                uom="LUMP",
                rate=vas_amount,
                amount=vas_amount,
                line_number=line_number
            )
            self.db.add(item)

        # Mark charges as billed
        for charge in charges["storage"]:
            charge.invoice_id = invoice.id
            charge.is_billed = True
        for charge in charges["handling"]:
            charge.invoice_id = invoice.id
            charge.is_billed = True
        for charge in charges["vas"]:
            charge.invoice_id = invoice.id
            charge.is_billed = True

        await self.db.commit()
        await self.db.refresh(invoice)
        return invoice

    async def get_invoice(
        self,
        invoice_id: uuid.UUID,
        include_items: bool = True
    ) -> Optional[BillingInvoice]:
        """Get invoice by ID."""
        query = select(BillingInvoice).where(
            and_(
                BillingInvoice.id == invoice_id,
                BillingInvoice.tenant_id == self.tenant_id
            )
        )
        if include_items:
            query = query.options(selectinload(BillingInvoice.line_items))

        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def list_invoices(
        self,
        customer_id: Optional[uuid.UUID] = None,
        warehouse_id: Optional[uuid.UUID] = None,
        status: Optional[InvoiceStatus] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[BillingInvoice], int]:
        """List invoices with filters."""
        query = select(BillingInvoice).where(
            BillingInvoice.tenant_id == self.tenant_id
        )

        if customer_id:
            query = query.where(BillingInvoice.customer_id == customer_id)
        if warehouse_id:
            query = query.where(BillingInvoice.warehouse_id == warehouse_id)
        if status:
            query = query.where(BillingInvoice.status == status.value)
        if from_date:
            query = query.where(BillingInvoice.invoice_date >= from_date)
        if to_date:
            query = query.where(BillingInvoice.invoice_date <= to_date)

        count_query = select(func.count()).select_from(query.subquery())
        total = await self.db.scalar(count_query) or 0

        query = query.order_by(BillingInvoice.created_at.desc()).offset(skip).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all()), total

    async def send_invoice(
        self,
        invoice_id: uuid.UUID,
        data: InvoiceSend
    ) -> Optional[BillingInvoice]:
        """Send an invoice."""
        invoice = await self.get_invoice(invoice_id)
        if not invoice or invoice.status not in [
            InvoiceStatus.DRAFT.value, InvoiceStatus.PENDING.value
        ]:
            return None

        invoice.status = InvoiceStatus.SENT.value
        invoice.sent_at = datetime.now(timezone.utc)
        invoice.sent_to = data.email
        invoice.updated_at = datetime.now(timezone.utc)

        # In production, send email here

        await self.db.commit()
        await self.db.refresh(invoice)
        return invoice

    async def record_payment(
        self,
        invoice_id: uuid.UUID,
        data: InvoicePayment
    ) -> Optional[BillingInvoice]:
        """Record a payment for an invoice."""
        invoice = await self.get_invoice(invoice_id)
        if not invoice:
            return None

        invoice.paid_amount += data.amount
        invoice.balance_due = invoice.total_amount - invoice.paid_amount
        invoice.last_payment_date = data.payment_date
        invoice.payment_reference = data.payment_reference

        if invoice.balance_due <= 0:
            invoice.status = InvoiceStatus.PAID.value
        elif invoice.paid_amount > 0:
            invoice.status = InvoiceStatus.PARTIAL.value

        invoice.updated_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(invoice)
        return invoice

    # =========================================================================
    # DASHBOARD
    # =========================================================================

    async def get_dashboard(
        self,
        warehouse_id: Optional[uuid.UUID] = None,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None
    ) -> BillingDashboard:
        """Get billing dashboard statistics."""
        if not from_date:
            from_date = date.today().replace(day=1)
        if not to_date:
            to_date = date.today()

        # Contract counts
        active_contracts = await self.db.scalar(
            select(func.count(BillingContract.id)).where(
                and_(
                    BillingContract.tenant_id == self.tenant_id,
                    BillingContract.status == ContractStatus.ACTIVE.value
                )
            )
        ) or 0

        total_contracts = await self.db.scalar(
            select(func.count(BillingContract.id)).where(
                BillingContract.tenant_id == self.tenant_id
            )
        ) or 0

        # Invoice counts
        def invoice_count_query(status):
            return select(func.count(BillingInvoice.id)).where(
                and_(
                    BillingInvoice.tenant_id == self.tenant_id,
                    BillingInvoice.status == status.value
                )
            )

        pending_invoices = await self.db.scalar(invoice_count_query(InvoiceStatus.PENDING)) or 0
        sent_invoices = await self.db.scalar(invoice_count_query(InvoiceStatus.SENT)) or 0
        overdue_invoices = await self.db.scalar(invoice_count_query(InvoiceStatus.OVERDUE)) or 0
        disputed_invoices = await self.db.scalar(invoice_count_query(InvoiceStatus.DISPUTED)) or 0

        # Financial MTD
        total_billed_mtd = await self.db.scalar(
            select(func.sum(BillingInvoice.total_amount)).where(
                and_(
                    BillingInvoice.tenant_id == self.tenant_id,
                    BillingInvoice.invoice_date >= from_date,
                    BillingInvoice.invoice_date <= to_date
                )
            )
        ) or Decimal("0")

        total_collected_mtd = await self.db.scalar(
            select(func.sum(BillingInvoice.paid_amount)).where(
                and_(
                    BillingInvoice.tenant_id == self.tenant_id,
                    BillingInvoice.last_payment_date >= from_date,
                    BillingInvoice.last_payment_date <= to_date
                )
            )
        ) or Decimal("0")

        total_outstanding = await self.db.scalar(
            select(func.sum(BillingInvoice.balance_due)).where(
                and_(
                    BillingInvoice.tenant_id == self.tenant_id,
                    BillingInvoice.status.in_([
                        InvoiceStatus.SENT.value,
                        InvoiceStatus.PARTIAL.value,
                        InvoiceStatus.OVERDUE.value
                    ])
                )
            )
        ) or Decimal("0")

        # Revenue breakdown
        storage_revenue_mtd = await self.db.scalar(
            select(func.sum(BillingInvoice.storage_amount)).where(
                and_(
                    BillingInvoice.tenant_id == self.tenant_id,
                    BillingInvoice.invoice_date >= from_date,
                    BillingInvoice.invoice_date <= to_date
                )
            )
        ) or Decimal("0")

        handling_revenue_mtd = await self.db.scalar(
            select(func.sum(BillingInvoice.handling_amount)).where(
                and_(
                    BillingInvoice.tenant_id == self.tenant_id,
                    BillingInvoice.invoice_date >= from_date,
                    BillingInvoice.invoice_date <= to_date
                )
            )
        ) or Decimal("0")

        vas_revenue_mtd = await self.db.scalar(
            select(func.sum(BillingInvoice.vas_amount)).where(
                and_(
                    BillingInvoice.tenant_id == self.tenant_id,
                    BillingInvoice.invoice_date >= from_date,
                    BillingInvoice.invoice_date <= to_date
                )
            )
        ) or Decimal("0")

        # Unbilled charges
        unbilled_storage = await self.db.scalar(
            select(func.sum(StorageCharge.amount)).where(
                and_(
                    StorageCharge.tenant_id == self.tenant_id,
                    StorageCharge.is_billed == False
                )
            )
        ) or Decimal("0")

        unbilled_handling = await self.db.scalar(
            select(func.sum(HandlingCharge.amount)).where(
                and_(
                    HandlingCharge.tenant_id == self.tenant_id,
                    HandlingCharge.is_billed == False
                )
            )
        ) or Decimal("0")

        unbilled_vas = await self.db.scalar(
            select(func.sum(ValueAddedServiceCharge.amount)).where(
                and_(
                    ValueAddedServiceCharge.tenant_id == self.tenant_id,
                    ValueAddedServiceCharge.is_billed == False
                )
            )
        ) or Decimal("0")

        # Recent invoices
        recent_invoices_query = select(BillingInvoice).where(
            BillingInvoice.tenant_id == self.tenant_id
        ).order_by(BillingInvoice.created_at.desc()).limit(5)
        recent_invoices_result = await self.db.execute(recent_invoices_query)
        recent_invoices = list(recent_invoices_result.scalars().all())

        return BillingDashboard(
            active_contracts=active_contracts,
            total_contracts=total_contracts,
            pending_invoices=pending_invoices,
            sent_invoices=sent_invoices,
            overdue_invoices=overdue_invoices,
            disputed_invoices=disputed_invoices,
            total_billed_mtd=total_billed_mtd,
            total_collected_mtd=total_collected_mtd,
            total_outstanding=total_outstanding,
            storage_revenue_mtd=storage_revenue_mtd,
            handling_revenue_mtd=handling_revenue_mtd,
            vas_revenue_mtd=vas_revenue_mtd,
            unbilled_storage=unbilled_storage,
            unbilled_handling=unbilled_handling,
            unbilled_vas=unbilled_vas,
            recent_invoices=recent_invoices,
            recent_payments=[]
        )
