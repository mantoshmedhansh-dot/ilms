"""AMC (Annual Maintenance Contract) API endpoints."""
from typing import Optional, List
from uuid import UUID
from datetime import datetime, date, timezone, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy import select, func, desc, and_, or_
from sqlalchemy.orm import selectinload
from pydantic import BaseModel

from app.api.deps import DB, get_current_user
from app.models.user import User
from app.models.amc import AMCContract, AMCPlan, AMCStatus
from app.models.customer import Customer
from app.models.product import Product
from app.models.installation import Installation
from uuid import uuid4
from app.core.module_decorators import require_module

router = APIRouter()


# ==================== Schemas ====================

class AMCPlanCreate(BaseModel):
    name: str
    code: str
    amc_type: str = "STANDARD"
    category_id: Optional[UUID] = None
    duration_months: int = 12
    base_price: Decimal
    tax_rate: Decimal = Decimal("18")
    services_included: int = 2
    parts_covered: bool = False
    labor_covered: bool = True
    emergency_support: bool = False
    priority_service: bool = False
    discount_on_parts: Decimal = Decimal("0")
    terms_and_conditions: Optional[str] = None
    description: Optional[str] = None


class AMCContractCreate(BaseModel):
    customer_id: UUID
    product_id: UUID
    installation_id: Optional[UUID] = None
    serial_number: str
    amc_type: str = "STANDARD"
    plan_id: Optional[UUID] = None
    start_date: date
    duration_months: int = 12
    total_services: int = 2
    base_price: Decimal
    discount_amount: Decimal = Decimal("0")
    parts_covered: bool = False
    labor_covered: bool = True
    emergency_support: bool = False
    priority_service: bool = False
    discount_on_parts: Decimal = Decimal("0")
    terms_and_conditions: Optional[str] = None
    notes: Optional[str] = None


# ==================== Plan Endpoints ====================

@router.get("/plans")
@require_module("crm_service")
async def list_amc_plans(
    db: DB,
    current_user: User = Depends(get_current_user),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    is_active: Optional[bool] = None,
    amc_type: Optional[str] = None,
    category_id: Optional[UUID] = None,
):
    """List AMC plans."""
    query = select(AMCPlan)

    conditions = []
    if is_active is not None:
        conditions.append(AMCPlan.is_active == is_active)
    if amc_type:
        conditions.append(AMCPlan.amc_type == amc_type.upper())
    if category_id:
        conditions.append(AMCPlan.category_id == category_id)

    if conditions:
        query = query.where(and_(*conditions))

    # Count
    count_query = select(func.count()).select_from(AMCPlan)
    if conditions:
        count_query = count_query.where(and_(*conditions))
    total = await db.scalar(count_query) or 0

    # Paginate
    query = query.order_by(AMCPlan.sort_order, AMCPlan.name)
    query = query.offset((page - 1) * size).limit(size)

    result = await db.execute(query)
    plans = result.scalars().all()

    return {
        "items": [
            {
                "id": str(plan.id),
                "name": plan.name,
                "code": plan.code,
                "amc_type": plan.amc_type,
                "duration_months": plan.duration_months,
                "base_price": float(plan.base_price),
                "tax_rate": float(plan.tax_rate),
                "services_included": plan.services_included,
                "parts_covered": plan.parts_covered,
                "labor_covered": plan.labor_covered,
                "emergency_support": plan.emergency_support,
                "priority_service": plan.priority_service,
                "discount_on_parts": float(plan.discount_on_parts),
                "is_active": plan.is_active,
                "description": plan.description,
            }
            for plan in plans
        ],
        "total": total,
        "page": page,
        "size": size,
    }


@router.get("/plans/{plan_id}")
@require_module("crm_service")
async def get_amc_plan(
    plan_id: UUID,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Get AMC plan details."""
    plan = await db.get(AMCPlan, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    return {
        "id": str(plan.id),
        "name": plan.name,
        "code": plan.code,
        "amc_type": plan.amc_type,
        "category_id": str(plan.category_id) if plan.category_id else None,
        "product_ids": plan.product_ids,
        "duration_months": plan.duration_months,
        "base_price": float(plan.base_price),
        "tax_rate": float(plan.tax_rate),
        "services_included": plan.services_included,
        "parts_covered": plan.parts_covered,
        "labor_covered": plan.labor_covered,
        "emergency_support": plan.emergency_support,
        "priority_service": plan.priority_service,
        "discount_on_parts": float(plan.discount_on_parts),
        "terms_and_conditions": plan.terms_and_conditions,
        "description": plan.description,
        "is_active": plan.is_active,
        "sort_order": plan.sort_order,
    }


@router.post("/plans", status_code=status.HTTP_201_CREATED)
@require_module("crm_service")
async def create_amc_plan(
    data: AMCPlanCreate,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Create a new AMC plan."""
    # Check for duplicate code
    existing = await db.execute(
        select(AMCPlan).where(AMCPlan.code == data.code)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Plan code already exists")

    plan = AMCPlan(
        name=data.name,
        code=data.code,
        amc_type=data.amc_type.upper(),
        category_id=data.category_id,
        duration_months=data.duration_months,
        base_price=data.base_price,
        tax_rate=data.tax_rate,
        services_included=data.services_included,
        parts_covered=data.parts_covered,
        labor_covered=data.labor_covered,
        emergency_support=data.emergency_support,
        priority_service=data.priority_service,
        discount_on_parts=data.discount_on_parts,
        terms_and_conditions=data.terms_and_conditions,
        description=data.description,
        is_active=True,
    )
    db.add(plan)
    await db.commit()
    await db.refresh(plan)

    return {"id": str(plan.id), "code": plan.code, "message": "Plan created successfully"}


@router.put("/plans/{plan_id}")
@require_module("crm_service")
async def update_amc_plan(
    plan_id: UUID,
    data: AMCPlanCreate,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Update an AMC plan."""
    plan = await db.get(AMCPlan, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        if field == "amc_type":
            value = value.upper()
        setattr(plan, field, value)

    await db.commit()

    return {"message": "Plan updated successfully"}


# ==================== Contract Endpoints ====================

@router.get("/contracts")
@require_module("crm_service")
async def list_amc_contracts(
    db: DB,
    current_user: User = Depends(get_current_user),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    amc_type: Optional[str] = None,
    customer_id: Optional[UUID] = None,
    product_id: Optional[UUID] = None,
    expiring_in_days: Optional[int] = None,
    search: Optional[str] = None,
):
    """List AMC contracts."""
    query = select(AMCContract).options(
        selectinload(AMCContract.customer),
        selectinload(AMCContract.product),
        selectinload(AMCContract.installation),
    )

    conditions = []

    if status:
        conditions.append(AMCContract.status == status.upper())

    if amc_type:
        conditions.append(AMCContract.amc_type == amc_type.upper())

    if customer_id:
        conditions.append(AMCContract.customer_id == customer_id)

    if product_id:
        conditions.append(AMCContract.product_id == product_id)

    if expiring_in_days:
        expiry_date = date.today() + timedelta(days=expiring_in_days)
        conditions.append(
            and_(
                AMCContract.end_date <= expiry_date,
                AMCContract.end_date >= date.today(),
                AMCContract.status == "ACTIVE"
            )
        )

    if search:
        conditions.append(
            or_(
                AMCContract.contract_number.ilike(f"%{search}%"),
                AMCContract.serial_number.ilike(f"%{search}%"),
            )
        )

    if conditions:
        query = query.where(and_(*conditions))

    # Count
    count_query = select(func.count()).select_from(AMCContract)
    if conditions:
        count_query = count_query.where(and_(*conditions))
    total = await db.scalar(count_query) or 0

    # Paginate
    query = query.order_by(desc(AMCContract.start_date))
    query = query.offset((page - 1) * size).limit(size)

    result = await db.execute(query)
    contracts = result.scalars().all()

    return {
        "items": [
            {
                "id": str(c.id),
                "contract_number": c.contract_number,
                "amc_type": c.amc_type,
                "status": c.status,
                "customer_id": str(c.customer_id),
                "customer_name": f"{c.customer.first_name} {c.customer.last_name}" if c.customer else None,
                "product_name": c.product.name if c.product else None,
                "serial_number": c.serial_number,
                "start_date": c.start_date.isoformat() if c.start_date else None,
                "end_date": c.end_date.isoformat() if c.end_date else None,
                "days_remaining": c.days_remaining,
                "total_services": c.total_services,
                "services_used": c.services_used,
                "services_remaining": c.services_remaining,
                "total_amount": float(c.total_amount),
                "payment_status": c.payment_status,
                "next_service_due": c.next_service_due.isoformat() if c.next_service_due else None,
            }
            for c in contracts
        ],
        "total": total,
        "page": page,
        "size": size,
    }


@router.get("/contracts/stats")
@require_module("crm_service")
async def get_contract_stats(
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Get AMC contract statistics."""
    # By status
    status_query = select(
        AMCContract.status,
        func.count().label("count")
    ).group_by(AMCContract.status)
    status_result = await db.execute(status_query)
    by_status = {row[0]: row[1] for row in status_result.all()}

    # Active contracts value
    active_value_query = select(func.sum(AMCContract.total_amount)).where(
        AMCContract.status == "ACTIVE"
    )
    active_value = await db.scalar(active_value_query) or Decimal("0")

    # Expiring in 30 days
    expiry_date = date.today() + timedelta(days=30)
    expiring_query = select(func.count()).select_from(AMCContract).where(
        and_(
            AMCContract.end_date <= expiry_date,
            AMCContract.end_date >= date.today(),
            AMCContract.status == "ACTIVE"
        )
    )
    expiring_soon = await db.scalar(expiring_query) or 0

    # Services due this month
    month_end = date.today().replace(day=28) + timedelta(days=4)
    month_end = month_end.replace(day=1) - timedelta(days=1)
    services_due_query = select(func.count()).select_from(AMCContract).where(
        and_(
            AMCContract.next_service_due <= month_end,
            AMCContract.next_service_due >= date.today(),
            AMCContract.status == "ACTIVE"
        )
    )
    services_due = await db.scalar(services_due_query) or 0

    return {
        "by_status": by_status,
        "active_contracts": by_status.get("ACTIVE", 0),
        "active_value": float(active_value),
        "expiring_in_30_days": expiring_soon,
        "services_due_this_month": services_due,
        "total": sum(by_status.values()),
    }


@router.get("/contracts/{contract_id}")
@require_module("crm_service")
async def get_amc_contract(
    contract_id: UUID,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Get AMC contract details."""
    query = select(AMCContract).options(
        selectinload(AMCContract.customer),
        selectinload(AMCContract.product),
        selectinload(AMCContract.installation),
        selectinload(AMCContract.service_requests),
        selectinload(AMCContract.creator),
        selectinload(AMCContract.approver),
    ).where(AMCContract.id == contract_id)

    result = await db.execute(query)
    contract = result.scalar_one_or_none()

    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    return {
        "id": str(contract.id),
        "contract_number": contract.contract_number,
        "amc_type": contract.amc_type,
        "status": contract.status,
        "customer": {
            "id": str(contract.customer_id),
            "name": f"{contract.customer.first_name} {contract.customer.last_name}" if contract.customer else None,
            "phone": contract.customer.phone if contract.customer else None,
        },
        "product": {
            "id": str(contract.product_id),
            "name": contract.product.name if contract.product else None,
        },
        "installation_id": str(contract.installation_id) if contract.installation_id else None,
        "serial_number": contract.serial_number,
        "start_date": contract.start_date.isoformat() if contract.start_date else None,
        "end_date": contract.end_date.isoformat() if contract.end_date else None,
        "duration_months": contract.duration_months,
        "days_remaining": contract.days_remaining,
        "is_active": contract.is_active,
        "total_services": contract.total_services,
        "services_used": contract.services_used,
        "services_remaining": contract.services_remaining,
        "service_schedule": contract.service_schedule,
        "next_service_due": contract.next_service_due.isoformat() if contract.next_service_due else None,
        "base_price": float(contract.base_price),
        "tax_amount": float(contract.tax_amount),
        "discount_amount": float(contract.discount_amount),
        "total_amount": float(contract.total_amount),
        "payment_status": contract.payment_status,
        "payment_mode": contract.payment_mode,
        "payment_reference": contract.payment_reference,
        "paid_at": contract.paid_at.isoformat() if contract.paid_at else None,
        "parts_covered": contract.parts_covered,
        "labor_covered": contract.labor_covered,
        "emergency_support": contract.emergency_support,
        "priority_service": contract.priority_service,
        "discount_on_parts": float(contract.discount_on_parts),
        "terms_and_conditions": contract.terms_and_conditions,
        "is_renewable": contract.is_renewable,
        "renewal_reminder_sent": contract.renewal_reminder_sent,
        "notes": contract.notes,
        "service_requests": [
            {
                "id": str(sr.id),
                "ticket_number": sr.ticket_number,
                "status": sr.status,
                "created_at": sr.created_at.isoformat() if sr.created_at else None,
            }
            for sr in (contract.service_requests or [])
        ],
        "created_at": contract.created_at.isoformat() if contract.created_at else None,
    }


@router.post("/contracts", status_code=status.HTTP_201_CREATED)
@require_module("crm_service")
async def create_amc_contract(
    data: AMCContractCreate,
    db: DB,
    current_user: User = Depends(get_current_user),
):
    """Create a new AMC contract."""
    # Validate customer
    customer = await db.get(Customer, data.customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    # Validate product
    product = await db.get(Product, data.product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Generate contract number (AMC-YYYYMMDD-XXXX format)
    today = date.today()
    random_suffix = str(uuid4())[:8].upper()
    contract_number = f"AMC-{today.strftime('%Y%m%d')}-{random_suffix}"

    # Calculate end date
    end_date = data.start_date + timedelta(days=data.duration_months * 30)

    # Calculate tax
    tax_amount = data.base_price * Decimal("0.18")  # 18% GST
    total_amount = data.base_price + tax_amount - data.discount_amount

    # Create service schedule
    service_interval = data.duration_months // data.total_services
    service_schedule = []
    for i in range(data.total_services):
        service_month = i * service_interval + (service_interval // 2)
        service_schedule.append({
            "service_number": i + 1,
            "due_month": service_month,
            "scheduled_date": None,
            "completed_date": None,
        })

    contract = AMCContract(
        contract_number=contract_number,
        amc_type=data.amc_type.upper(),
        status="DRAFT",
        customer_id=data.customer_id,
        product_id=data.product_id,
        installation_id=data.installation_id,
        serial_number=data.serial_number,
        start_date=data.start_date,
        end_date=end_date,
        duration_months=data.duration_months,
        total_services=data.total_services,
        services_remaining=data.total_services,
        base_price=data.base_price,
        tax_amount=tax_amount,
        discount_amount=data.discount_amount,
        total_amount=total_amount,
        parts_covered=data.parts_covered,
        labor_covered=data.labor_covered,
        emergency_support=data.emergency_support,
        priority_service=data.priority_service,
        discount_on_parts=data.discount_on_parts,
        terms_and_conditions=data.terms_and_conditions,
        notes=data.notes,
        service_schedule=service_schedule,
        next_service_due=data.start_date + timedelta(days=service_interval * 30 // 2),
        created_by=current_user.id,
    )
    db.add(contract)
    await db.commit()
    await db.refresh(contract)

    return {
        "id": str(contract.id),
        "contract_number": contract.contract_number,
        "message": "AMC contract created successfully",
    }


@router.post("/contracts/{contract_id}/activate")
@require_module("crm_service")
async def activate_contract(
    contract_id: UUID,
    payment_mode: str,
    payment_reference: Optional[str] = None,
    db: DB = None,
    current_user: User = Depends(get_current_user),
):
    """Activate an AMC contract after payment."""
    contract = await db.get(AMCContract, contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    if contract.status != "DRAFT" and contract.status != "PENDING_PAYMENT":
        raise HTTPException(
            status_code=400,
            detail=f"Cannot activate contract with status {contract.status}"
        )

    contract.status = "ACTIVE"
    contract.payment_status = "PAID"  # UPPERCASE per coding standards
    contract.payment_mode = payment_mode
    contract.payment_reference = payment_reference
    contract.paid_at = datetime.now(timezone.utc)
    contract.approved_by = current_user.id

    await db.commit()

    return {"message": "Contract activated", "status": contract.status}


@router.post("/contracts/{contract_id}/use-service")
@require_module("crm_service")
async def use_service(
    contract_id: UUID,
    service_request_id: Optional[UUID] = None,
    db: DB = None,
    current_user: User = Depends(get_current_user),
):
    """Record a service used against the contract."""
    contract = await db.get(AMCContract, contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    if contract.status != "ACTIVE":
        raise HTTPException(status_code=400, detail="Contract is not active")

    if contract.services_remaining <= 0:
        raise HTTPException(status_code=400, detail="No services remaining")

    contract.services_used += 1
    contract.services_remaining -= 1

    # Update service schedule
    if contract.service_schedule:
        for service in contract.service_schedule:
            if not service.get("completed_date"):
                service["completed_date"] = date.today().isoformat()
                break

    # Calculate next service due
    if contract.services_remaining > 0:
        remaining_days = (contract.end_date - date.today()).days
        interval = remaining_days // contract.services_remaining
        contract.next_service_due = date.today() + timedelta(days=interval)
    else:
        contract.next_service_due = None

    await db.commit()

    return {
        "message": "Service recorded",
        "services_used": contract.services_used,
        "services_remaining": contract.services_remaining,
    }


@router.post("/contracts/{contract_id}/renew")
@require_module("crm_service")
async def renew_contract(
    contract_id: UUID,
    new_plan_id: Optional[UUID] = None,
    duration_months: int = 12,
    db: DB = None,
    current_user: User = Depends(get_current_user),
):
    """Renew an AMC contract."""
    old_contract = await db.get(AMCContract, contract_id)
    if not old_contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    if old_contract.status not in ["ACTIVE", "EXPIRED"]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot renew contract with status {old_contract.status}"
        )

    # Get plan if specified
    base_price = old_contract.base_price
    total_services = old_contract.total_services
    if new_plan_id:
        plan = await db.get(AMCPlan, new_plan_id)
        if plan:
            base_price = plan.base_price
            total_services = plan.services_included

    # Create new contract number
    random_suffix = str(uuid4())[:8].upper()
    new_contract_number = f"AMC-{date.today().strftime('%Y%m%d')}-{random_suffix}"
    start_date = max(old_contract.end_date, date.today())
    end_date = start_date + timedelta(days=duration_months * 30)
    tax_amount = base_price * Decimal("0.18")
    total_amount = base_price + tax_amount

    new_contract = AMCContract(
        contract_number=new_contract_number,
        amc_type=old_contract.amc_type,
        status="DRAFT",
        customer_id=old_contract.customer_id,
        product_id=old_contract.product_id,
        installation_id=old_contract.installation_id,
        serial_number=old_contract.serial_number,
        start_date=start_date,
        end_date=end_date,
        duration_months=duration_months,
        total_services=total_services,
        services_remaining=total_services,
        base_price=base_price,
        tax_amount=tax_amount,
        total_amount=total_amount,
        parts_covered=old_contract.parts_covered,
        labor_covered=old_contract.labor_covered,
        emergency_support=old_contract.emergency_support,
        priority_service=old_contract.priority_service,
        discount_on_parts=old_contract.discount_on_parts,
        terms_and_conditions=old_contract.terms_and_conditions,
        renewed_from_id=old_contract.id,
        created_by=current_user.id,
    )
    db.add(new_contract)

    # Update old contract
    old_contract.status = "RENEWED"
    old_contract.renewed_to_id = new_contract.id

    await db.commit()
    await db.refresh(new_contract)

    return {
        "id": str(new_contract.id),
        "contract_number": new_contract.contract_number,
        "message": "Contract renewed successfully",
    }
