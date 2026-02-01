"""API endpoints for Campaign Management module."""
from datetime import datetime, date, timezone
from typing import Optional, List
from uuid import UUID
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.campaign import (
    CampaignTemplate, AudienceSegment, Campaign, CampaignRecipient,
    CampaignAutomation, CampaignAutomationLog, UnsubscribeList,
    CampaignType, CampaignStatus, CampaignCategory,
    AudienceType, DeliveryStatus
)
from app.models.user import User
from app.models.customer import Customer
from app.schemas.campaign import (
    # Templates
    CampaignTemplateCreate, CampaignTemplateUpdate, CampaignTemplateResponse,
    # Segments
    AudienceSegmentCreate, AudienceSegmentUpdate, AudienceSegmentResponse,
    # Campaigns
    CampaignCreate, CampaignUpdate, CampaignResponse,
    CampaignDetailResponse, CampaignListResponse, CampaignScheduleRequest,
    # Recipients
    CampaignRecipientResponse, CampaignRecipientListResponse,
    # Automations
    CampaignAutomationCreate, CampaignAutomationUpdate, CampaignAutomationResponse,
    # Unsubscribe
    UnsubscribeRequest, UnsubscribeResponse,
    # Dashboard
    CampaignDashboardResponse, CampaignPerformanceResponse
)
from app.api.deps import get_current_user
from app.core.module_decorators import require_module

router = APIRouter()


# ==================== Campaign Template Endpoints ====================

@router.post("/templates", response_model=CampaignTemplateResponse, status_code=status.HTTP_201_CREATED)
@require_module("marketing")
async def create_template(
    data: CampaignTemplateCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new campaign template."""
    template = CampaignTemplate(
        name=data.name,
        description=data.description,
        campaign_type=data.campaign_type,
        category=data.category,
        subject=data.subject,
        content=data.content,
        html_content=data.html_content,
        variables=data.variables,
        media_urls=data.media_urls,
        is_active=data.is_active,
        created_by_id=current_user.id
    )
    db.add(template)
    await db.commit()
    await db.refresh(template)
    return template


@router.get("/templates", response_model=List[CampaignTemplateResponse])
@require_module("marketing")
async def list_templates(
    campaign_type: Optional[CampaignType] = None,
    category: Optional[CampaignCategory] = None,
    is_active: Optional[bool] = True,
    search: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List campaign templates."""
    query = select(CampaignTemplate)

    if campaign_type:
        query = query.where(CampaignTemplate.campaign_type == campaign_type)
    if category:
        query = query.where(CampaignTemplate.category == category)
    if is_active is not None:
        query = query.where(CampaignTemplate.is_active == is_active)
    if search:
        query = query.where(
            or_(
                CampaignTemplate.name.ilike(f"%{search}%"),
                CampaignTemplate.subject.ilike(f"%{search}%")
            )
        )

    query = query.order_by(CampaignTemplate.created_at.desc())
    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    return result.scalars().all()


@router.get("/templates/{template_id}", response_model=CampaignTemplateResponse)
@require_module("marketing")
async def get_template(
    template_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get campaign template by ID."""
    result = await db.execute(
        select(CampaignTemplate).where(CampaignTemplate.id == template_id)
    )
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template


@router.put("/templates/{template_id}", response_model=CampaignTemplateResponse)
@require_module("marketing")
async def update_template(
    template_id: UUID,
    data: CampaignTemplateUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update campaign template."""
    result = await db.execute(
        select(CampaignTemplate).where(CampaignTemplate.id == template_id)
    )
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    if template.is_system:
        raise HTTPException(status_code=400, detail="Cannot modify system templates")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(template, field, value)

    template.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(template)
    return template


@router.delete("/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
@require_module("marketing")
async def delete_template(
    template_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete (deactivate) campaign template."""
    result = await db.execute(
        select(CampaignTemplate).where(CampaignTemplate.id == template_id)
    )
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    if template.is_system:
        raise HTTPException(status_code=400, detail="Cannot delete system templates")

    template.is_active = False
    template.updated_at = datetime.now(timezone.utc)
    await db.commit()


# ==================== Audience Segment Endpoints ====================

@router.post("/segments", response_model=AudienceSegmentResponse, status_code=status.HTTP_201_CREATED)
@require_module("marketing")
async def create_segment(
    data: AudienceSegmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new audience segment."""
    segment = AudienceSegment(
        name=data.name,
        description=data.description,
        segment_type=data.segment_type,
        conditions=[c.model_dump() for c in data.conditions] if data.conditions else None,
        condition_logic=data.condition_logic,
        customer_ids=data.customer_ids,
        is_active=data.is_active,
        created_by_id=current_user.id
    )

    # Calculate estimated size for manual list
    if data.segment_type == AudienceType.MANUAL_LIST and data.customer_ids:
        segment.estimated_size = len(data.customer_ids)
        segment.last_calculated_at = datetime.now(timezone.utc)

    db.add(segment)
    await db.commit()
    await db.refresh(segment)
    return segment


@router.get("/segments", response_model=List[AudienceSegmentResponse])
@require_module("marketing")
async def list_segments(
    segment_type: Optional[AudienceType] = None,
    is_active: Optional[bool] = True,
    search: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List audience segments."""
    query = select(AudienceSegment)

    if segment_type:
        query = query.where(AudienceSegment.segment_type == segment_type)
    if is_active is not None:
        query = query.where(AudienceSegment.is_active == is_active)
    if search:
        query = query.where(AudienceSegment.name.ilike(f"%{search}%"))

    query = query.order_by(AudienceSegment.created_at.desc())
    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    return result.scalars().all()


@router.get("/segments/{segment_id}", response_model=AudienceSegmentResponse)
@require_module("marketing")
async def get_segment(
    segment_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get audience segment by ID."""
    result = await db.execute(
        select(AudienceSegment).where(AudienceSegment.id == segment_id)
    )
    segment = result.scalar_one_or_none()
    if not segment:
        raise HTTPException(status_code=404, detail="Segment not found")
    return segment


@router.put("/segments/{segment_id}", response_model=AudienceSegmentResponse)
@require_module("marketing")
async def update_segment(
    segment_id: UUID,
    data: AudienceSegmentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update audience segment."""
    result = await db.execute(
        select(AudienceSegment).where(AudienceSegment.id == segment_id)
    )
    segment = result.scalar_one_or_none()
    if not segment:
        raise HTTPException(status_code=404, detail="Segment not found")

    update_data = data.model_dump(exclude_unset=True)

    if "conditions" in update_data and update_data["conditions"]:
        update_data["conditions"] = [c if isinstance(c, dict) else c.model_dump() for c in update_data["conditions"]]

    for field, value in update_data.items():
        setattr(segment, field, value)

    segment.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(segment)
    return segment


@router.post("/segments/{segment_id}/calculate", response_model=AudienceSegmentResponse)
@require_module("marketing")
async def calculate_segment_size(
    segment_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Calculate and update segment size."""
    result = await db.execute(
        select(AudienceSegment).where(AudienceSegment.id == segment_id)
    )
    segment = result.scalar_one_or_none()
    if not segment:
        raise HTTPException(status_code=404, detail="Segment not found")

    # For ALL_CUSTOMERS, count all active customers
    if segment.segment_type == AudienceType.ALL_CUSTOMERS:
        count_result = await db.execute(
            select(func.count(Customer.id)).where(Customer.is_active == True)
        )
        segment.estimated_size = count_result.scalar() or 0

    # For MANUAL_LIST, count customer_ids
    elif segment.segment_type == AudienceType.MANUAL_LIST:
        segment.estimated_size = len(segment.customer_ids) if segment.customer_ids else 0

    # For DYNAMIC, we would need to evaluate conditions
    # This is a simplified version - in production, you'd build dynamic queries
    else:
        count_result = await db.execute(
            select(func.count(Customer.id)).where(Customer.is_active == True)
        )
        segment.estimated_size = count_result.scalar() or 0

    segment.last_calculated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(segment)
    return segment


# ==================== Campaign CRUD Endpoints ====================

@router.post("", response_model=CampaignResponse, status_code=status.HTTP_201_CREATED)
@require_module("marketing")
async def create_campaign(
    data: CampaignCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new campaign."""
    # Generate campaign code
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    count_result = await db.execute(
        select(func.count(Campaign.id)).where(
            Campaign.campaign_code.like(f"CAMP-{today}%")
        )
    )
    count = count_result.scalar() or 0
    campaign_code = f"CAMP-{today}-{count + 1:04d}"

    campaign = Campaign(
        campaign_code=campaign_code,
        name=data.name,
        description=data.description,
        campaign_type=data.campaign_type,
        category=data.category,
        status=CampaignStatus.DRAFT,
        template_id=data.template_id,
        subject=data.subject,
        content=data.content,
        html_content=data.html_content,
        media_urls=data.media_urls,
        cta_text=data.cta_text,
        cta_url=data.cta_url,
        audience_type=data.audience_type,
        segment_id=data.segment_id,
        scheduled_at=data.scheduled_at,
        is_recurring=data.is_recurring,
        recurrence_pattern=data.recurrence_pattern,
        recurrence_config=data.recurrence_config,
        sender_name=data.sender_name,
        sender_email=data.sender_email,
        sender_phone=data.sender_phone,
        reply_to=data.reply_to,
        budget_amount=data.budget_amount,
        daily_limit=data.daily_limit,
        hourly_limit=data.hourly_limit,
        tags=data.tags,
        created_by_id=current_user.id
    )

    db.add(campaign)
    await db.commit()
    await db.refresh(campaign)
    return campaign


@router.get("", response_model=CampaignListResponse)
@require_module("marketing")
async def list_campaigns(
    status: Optional[CampaignStatus] = None,
    campaign_type: Optional[CampaignType] = None,
    category: Optional[CampaignCategory] = None,
    search: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List campaigns with filters."""
    query = select(Campaign)
    count_query = select(func.count(Campaign.id))

    filters = []

    if status:
        filters.append(Campaign.status == status)
    if campaign_type:
        filters.append(Campaign.campaign_type == campaign_type)
    if category:
        filters.append(Campaign.category == category)
    if search:
        filters.append(
            or_(
                Campaign.name.ilike(f"%{search}%"),
                Campaign.campaign_code.ilike(f"%{search}%")
            )
        )
    if start_date:
        filters.append(Campaign.created_at >= datetime.combine(start_date, datetime.min.time()))
    if end_date:
        filters.append(Campaign.created_at <= datetime.combine(end_date, datetime.max.time()))

    if filters:
        query = query.where(and_(*filters))
        count_query = count_query.where(and_(*filters))

    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Get paginated results
    query = query.order_by(Campaign.created_at.desc())
    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    campaigns = result.scalars().all()

    return CampaignListResponse(
        items=campaigns,
        total=total,
        skip=skip,
        limit=limit
    )


@router.get("/{campaign_id}", response_model=CampaignDetailResponse)
@require_module("marketing")
async def get_campaign(
    campaign_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get campaign details."""
    result = await db.execute(
        select(Campaign).where(Campaign.id == campaign_id)
    )
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign


@router.put("/{campaign_id}", response_model=CampaignResponse)
@require_module("marketing")
async def update_campaign(
    campaign_id: UUID,
    data: CampaignUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update campaign."""
    result = await db.execute(
        select(Campaign).where(Campaign.id == campaign_id)
    )
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    if campaign.status not in [CampaignStatus.DRAFT, CampaignStatus.SCHEDULED]:
        raise HTTPException(status_code=400, detail="Can only edit draft or scheduled campaigns")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(campaign, field, value)

    campaign.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(campaign)
    return campaign


@router.delete("/{campaign_id}", status_code=status.HTTP_204_NO_CONTENT)
@require_module("marketing")
async def delete_campaign(
    campaign_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Cancel/delete a campaign."""
    result = await db.execute(
        select(Campaign).where(Campaign.id == campaign_id)
    )
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    if campaign.status == CampaignStatus.RUNNING:
        raise HTTPException(status_code=400, detail="Cannot delete running campaign. Pause it first.")

    campaign.status = CampaignStatus.CANCELLED.value
    campaign.updated_at = datetime.now(timezone.utc)
    await db.commit()


# ==================== Campaign Workflow Endpoints ====================

@router.post("/{campaign_id}/schedule", response_model=CampaignResponse)
@require_module("marketing")
async def schedule_campaign(
    campaign_id: UUID,
    data: CampaignScheduleRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Schedule a campaign for future sending."""
    result = await db.execute(
        select(Campaign).where(Campaign.id == campaign_id)
    )
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    if campaign.status != CampaignStatus.DRAFT:
        raise HTTPException(status_code=400, detail="Only draft campaigns can be scheduled")

    if data.scheduled_at <= datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Scheduled time must be in the future")

    campaign.scheduled_at = data.scheduled_at
    campaign.status = CampaignStatus.SCHEDULED.value
    campaign.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(campaign)
    return campaign


@router.post("/{campaign_id}/start", response_model=CampaignResponse)
@require_module("marketing")
async def start_campaign(
    campaign_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Start a campaign immediately."""
    result = await db.execute(
        select(Campaign).where(Campaign.id == campaign_id)
    )
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    if campaign.status not in [CampaignStatus.DRAFT, CampaignStatus.SCHEDULED]:
        raise HTTPException(status_code=400, detail="Can only start draft or scheduled campaigns")

    campaign.status = CampaignStatus.RUNNING.value
    campaign.started_at = datetime.now(timezone.utc)
    campaign.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(campaign)
    return campaign


@router.post("/{campaign_id}/pause", response_model=CampaignResponse)
@require_module("marketing")
async def pause_campaign(
    campaign_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Pause a running campaign."""
    result = await db.execute(
        select(Campaign).where(Campaign.id == campaign_id)
    )
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    if campaign.status != CampaignStatus.RUNNING:
        raise HTTPException(status_code=400, detail="Can only pause running campaigns")

    campaign.status = CampaignStatus.PAUSED.value
    campaign.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(campaign)
    return campaign


@router.post("/{campaign_id}/resume", response_model=CampaignResponse)
@require_module("marketing")
async def resume_campaign(
    campaign_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Resume a paused campaign."""
    result = await db.execute(
        select(Campaign).where(Campaign.id == campaign_id)
    )
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    if campaign.status != CampaignStatus.PAUSED:
        raise HTTPException(status_code=400, detail="Can only resume paused campaigns")

    campaign.status = CampaignStatus.RUNNING.value
    campaign.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(campaign)
    return campaign


@router.post("/{campaign_id}/complete", response_model=CampaignResponse)
@require_module("marketing")
async def complete_campaign(
    campaign_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Mark campaign as completed."""
    result = await db.execute(
        select(Campaign).where(Campaign.id == campaign_id)
    )
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    if campaign.status not in [CampaignStatus.RUNNING, CampaignStatus.PAUSED]:
        raise HTTPException(status_code=400, detail="Can only complete running or paused campaigns")

    campaign.status = CampaignStatus.COMPLETED.value
    campaign.completed_at = datetime.now(timezone.utc)
    campaign.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(campaign)
    return campaign


# ==================== Campaign Recipients Endpoints ====================

@router.get("/{campaign_id}/recipients", response_model=CampaignRecipientListResponse)
@require_module("marketing")
async def list_campaign_recipients(
    campaign_id: UUID,
    status: Optional[DeliveryStatus] = None,
    search: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List campaign recipients."""
    query = select(CampaignRecipient).where(CampaignRecipient.campaign_id == campaign_id)
    count_query = select(func.count(CampaignRecipient.id)).where(CampaignRecipient.campaign_id == campaign_id)

    if status:
        query = query.where(CampaignRecipient.status == status)
        count_query = count_query.where(CampaignRecipient.status == status)
    if search:
        search_filter = or_(
            CampaignRecipient.email.ilike(f"%{search}%"),
            CampaignRecipient.phone.ilike(f"%{search}%"),
            CampaignRecipient.name.ilike(f"%{search}%")
        )
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)

    # Get total count
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Get paginated results
    query = query.order_by(CampaignRecipient.created_at.desc())
    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    recipients = result.scalars().all()

    return CampaignRecipientListResponse(
        items=recipients,
        total=total,
        skip=skip,
        limit=limit
    )


# ==================== Campaign Automation Endpoints ====================

@router.post("/automations", response_model=CampaignAutomationResponse, status_code=status.HTTP_201_CREATED)
@require_module("marketing")
async def create_automation(
    data: CampaignAutomationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new campaign automation."""
    automation = CampaignAutomation(
        name=data.name,
        description=data.description,
        trigger_type=data.trigger_type,
        trigger_conditions=data.trigger_conditions,
        delay_minutes=data.delay_minutes,
        template_id=data.template_id,
        campaign_type=data.campaign_type,
        is_active=data.is_active,
        max_per_customer=data.max_per_customer,
        cooldown_days=data.cooldown_days,
        created_by_id=current_user.id
    )
    db.add(automation)
    await db.commit()
    await db.refresh(automation)
    return automation


@router.get("/automations", response_model=List[CampaignAutomationResponse])
@require_module("marketing")
async def list_automations(
    trigger_type: Optional[str] = None,
    campaign_type: Optional[CampaignType] = None,
    is_active: Optional[bool] = True,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List campaign automations."""
    query = select(CampaignAutomation)

    if trigger_type:
        query = query.where(CampaignAutomation.trigger_type == trigger_type)
    if campaign_type:
        query = query.where(CampaignAutomation.campaign_type == campaign_type)
    if is_active is not None:
        query = query.where(CampaignAutomation.is_active == is_active)

    query = query.order_by(CampaignAutomation.created_at.desc())
    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    return result.scalars().all()


@router.get("/automations/{automation_id}", response_model=CampaignAutomationResponse)
@require_module("marketing")
async def get_automation(
    automation_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get campaign automation by ID."""
    result = await db.execute(
        select(CampaignAutomation).where(CampaignAutomation.id == automation_id)
    )
    automation = result.scalar_one_or_none()
    if not automation:
        raise HTTPException(status_code=404, detail="Automation not found")
    return automation


@router.put("/automations/{automation_id}", response_model=CampaignAutomationResponse)
@require_module("marketing")
async def update_automation(
    automation_id: UUID,
    data: CampaignAutomationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update campaign automation."""
    result = await db.execute(
        select(CampaignAutomation).where(CampaignAutomation.id == automation_id)
    )
    automation = result.scalar_one_or_none()
    if not automation:
        raise HTTPException(status_code=404, detail="Automation not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(automation, field, value)

    automation.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(automation)
    return automation


@router.delete("/automations/{automation_id}", status_code=status.HTTP_204_NO_CONTENT)
@require_module("marketing")
async def delete_automation(
    automation_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Deactivate campaign automation."""
    result = await db.execute(
        select(CampaignAutomation).where(CampaignAutomation.id == automation_id)
    )
    automation = result.scalar_one_or_none()
    if not automation:
        raise HTTPException(status_code=404, detail="Automation not found")

    automation.is_active = False
    automation.updated_at = datetime.now(timezone.utc)
    await db.commit()


# ==================== Unsubscribe Endpoints ====================

@router.post("/unsubscribe", response_model=UnsubscribeResponse, status_code=status.HTTP_201_CREATED)
@require_module("marketing")
async def unsubscribe(
    data: UnsubscribeRequest,
    db: AsyncSession = Depends(get_db)
):
    """Unsubscribe from campaign communications."""
    if not data.email and not data.phone:
        raise HTTPException(status_code=400, detail="Either email or phone is required")

    # Check if already unsubscribed
    query = select(UnsubscribeList).where(UnsubscribeList.channel == data.channel)
    if data.email:
        query = query.where(UnsubscribeList.email == data.email)
    elif data.phone:
        query = query.where(UnsubscribeList.phone == data.phone)

    result = await db.execute(query)
    existing = result.scalar_one_or_none()

    if existing:
        return existing

    # Find customer
    customer_id = None
    if data.email:
        cust_result = await db.execute(
            select(Customer).where(Customer.email == data.email)
        )
        customer = cust_result.scalar_one_or_none()
        if customer:
            customer_id = customer.id
    elif data.phone:
        cust_result = await db.execute(
            select(Customer).where(Customer.phone == data.phone)
        )
        customer = cust_result.scalar_one_or_none()
        if customer:
            customer_id = customer.id

    unsub = UnsubscribeList(
        customer_id=customer_id,
        email=data.email,
        phone=data.phone,
        channel=data.channel,
        reason=data.reason,
        source_campaign_id=data.campaign_id
    )
    db.add(unsub)
    await db.commit()
    await db.refresh(unsub)
    return unsub


@router.get("/unsubscribe/check")
@require_module("marketing")
async def check_unsubscribe(
    email: Optional[str] = None,
    phone: Optional[str] = None,
    channel: Optional[CampaignType] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Check if email/phone is unsubscribed."""
    if not email and not phone:
        raise HTTPException(status_code=400, detail="Either email or phone is required")

    query = select(UnsubscribeList)

    if email:
        query = query.where(UnsubscribeList.email == email)
    elif phone:
        query = query.where(UnsubscribeList.phone == phone)

    if channel:
        query = query.where(UnsubscribeList.channel == channel)

    result = await db.execute(query)
    unsubscribes = result.scalars().all()

    return {
        "is_unsubscribed": len(unsubscribes) > 0,
        "channels": [u.channel for u in unsubscribes]
    }


# ==================== Dashboard & Analytics Endpoints ====================

@router.get("/stats/dashboard", response_model=CampaignDashboardResponse)
@require_module("marketing")
async def get_campaign_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get campaign dashboard metrics."""
    today = date.today()

    # Total campaigns
    total_result = await db.execute(select(func.count(Campaign.id)))
    total_campaigns = total_result.scalar() or 0

    # Active (running) campaigns
    active_result = await db.execute(
        select(func.count(Campaign.id)).where(Campaign.status == CampaignStatus.RUNNING)
    )
    active_campaigns = active_result.scalar() or 0

    # Scheduled campaigns
    scheduled_result = await db.execute(
        select(func.count(Campaign.id)).where(Campaign.status == CampaignStatus.SCHEDULED)
    )
    scheduled_campaigns = scheduled_result.scalar() or 0

    # Completed campaigns
    completed_result = await db.execute(
        select(func.count(Campaign.id)).where(Campaign.status == CampaignStatus.COMPLETED)
    )
    completed_campaigns = completed_result.scalar() or 0

    # By status
    status_result = await db.execute(
        select(Campaign.status, func.count(Campaign.id))
        .group_by(Campaign.status)
    )
    by_status = {str(row[0].value): row[1] for row in status_result.fetchall()}

    # By type
    type_result = await db.execute(
        select(Campaign.campaign_type, func.count(Campaign.id))
        .group_by(Campaign.campaign_type)
    )
    by_type = {str(row[0].value): row[1] for row in type_result.fetchall()}

    # Aggregate metrics
    metrics_result = await db.execute(
        select(
            func.sum(Campaign.total_sent),
            func.sum(Campaign.total_delivered),
            func.sum(Campaign.total_opened),
            func.sum(Campaign.total_clicked),
            func.sum(Campaign.total_bounced),
            func.sum(Campaign.total_unsubscribed),
            func.sum(Campaign.total_cost)
        )
    )
    metrics = metrics_result.fetchone()

    total_sent = metrics[0] or 0
    total_delivered = metrics[1] or 0
    total_opened = metrics[2] or 0
    total_clicked = metrics[3] or 0
    total_bounced = metrics[4] or 0
    total_unsubscribed = metrics[5] or 0
    total_cost = metrics[6] or Decimal("0")

    # Calculate rates
    delivery_rate = Decimal(str(round(total_delivered / total_sent * 100, 2))) if total_sent > 0 else Decimal("0")
    open_rate = Decimal(str(round(total_opened / total_delivered * 100, 2))) if total_delivered > 0 else Decimal("0")
    click_rate = Decimal(str(round(total_clicked / total_opened * 100, 2))) if total_opened > 0 else Decimal("0")
    bounce_rate = Decimal(str(round(total_bounced / total_sent * 100, 2))) if total_sent > 0 else Decimal("0")

    # Top performing campaigns (by open rate)
    top_result = await db.execute(
        select(Campaign)
        .where(Campaign.total_sent > 0)
        .order_by((Campaign.total_opened / Campaign.total_sent).desc())
        .limit(5)
    )
    top_campaigns_raw = top_result.scalars().all()
    top_campaigns = [
        {
            "id": str(c.id),
            "name": c.name,
            "type": c.campaign_type,
            "sent": c.total_sent,
            "opened": c.total_opened,
            "open_rate": round(c.total_opened / c.total_sent * 100, 2) if c.total_sent > 0 else 0
        }
        for c in top_campaigns_raw
    ]

    return CampaignDashboardResponse(
        date=today,
        total_campaigns=total_campaigns,
        active_campaigns=active_campaigns,
        scheduled_campaigns=scheduled_campaigns,
        completed_campaigns=completed_campaigns,
        by_status=by_status,
        by_type=by_type,
        total_sent=total_sent,
        total_delivered=total_delivered,
        total_opened=total_opened,
        total_clicked=total_clicked,
        total_bounced=total_bounced,
        total_unsubscribed=total_unsubscribed,
        delivery_rate=delivery_rate,
        open_rate=open_rate,
        click_rate=click_rate,
        bounce_rate=bounce_rate,
        total_cost=total_cost,
        top_campaigns=top_campaigns
    )


@router.get("/{campaign_id}/performance", response_model=CampaignPerformanceResponse)
@require_module("marketing")
async def get_campaign_performance(
    campaign_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get detailed performance metrics for a campaign."""
    result = await db.execute(
        select(Campaign).where(Campaign.id == campaign_id)
    )
    campaign = result.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    # Calculate rates
    delivery_rate = Decimal(str(round(campaign.total_delivered / campaign.total_sent * 100, 2))) if campaign.total_sent > 0 else Decimal("0")
    open_rate = Decimal(str(round(campaign.total_opened / campaign.total_delivered * 100, 2))) if campaign.total_delivered > 0 else Decimal("0")
    click_rate = Decimal(str(round(campaign.total_clicked / campaign.total_delivered * 100, 2))) if campaign.total_delivered > 0 else Decimal("0")
    click_to_open = Decimal(str(round(campaign.total_clicked / campaign.total_opened * 100, 2))) if campaign.total_opened > 0 else Decimal("0")
    bounce_rate = Decimal(str(round(campaign.total_bounced / campaign.total_sent * 100, 2))) if campaign.total_sent > 0 else Decimal("0")
    unsub_rate = Decimal(str(round(campaign.total_unsubscribed / campaign.total_delivered * 100, 2))) if campaign.total_delivered > 0 else Decimal("0")

    cost_per_send = Decimal(str(round(float(campaign.total_cost) / campaign.total_sent, 2))) if campaign.total_sent > 0 else Decimal("0")
    cost_per_click = Decimal(str(round(float(campaign.total_cost) / campaign.total_clicked, 2))) if campaign.total_clicked > 0 else Decimal("0")

    return CampaignPerformanceResponse(
        campaign_id=campaign.id,
        campaign_name=campaign.name,
        campaign_type=campaign.campaign_type,
        status=campaign.status,
        target_count=campaign.target_count,
        total_sent=campaign.total_sent,
        delivered=campaign.total_delivered,
        delivery_rate=delivery_rate,
        opened=campaign.total_opened,
        open_rate=open_rate,
        unique_opens=campaign.total_opened,  # Would need separate tracking
        clicked=campaign.total_clicked,
        click_rate=click_rate,
        unique_clicks=campaign.total_clicked,  # Would need separate tracking
        click_to_open_rate=click_to_open,
        bounced=campaign.total_bounced,
        bounce_rate=bounce_rate,
        unsubscribed=campaign.total_unsubscribed,
        unsubscribe_rate=unsub_rate,
        failed=campaign.total_failed,
        total_cost=campaign.total_cost,
        cost_per_send=cost_per_send,
        cost_per_click=cost_per_click
    )
