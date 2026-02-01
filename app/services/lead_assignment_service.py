"""
Round-Robin Lead Assignment Service

Automatically distributes incoming leads among sales team members
using various assignment strategies:
- Round-robin: Even distribution in sequence
- Load-balanced: Based on current workload
- Skill-based: Match lead type to agent skills
- Geographic: Based on pincode/region

Supports:
- Assignment rules per lead source
- Team/queue management
- Availability checking
- Assignment history tracking
"""

from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List
from uuid import UUID
from enum import Enum

from sqlalchemy import select, and_, or_, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.lead import Lead, LeadSource, LeadStatus
from app.models.user import User


class AssignmentStrategy(str, Enum):
    """Lead assignment strategies."""
    ROUND_ROBIN = "ROUND_ROBIN"
    LOAD_BALANCED = "LOAD_BALANCED"
    SKILL_BASED = "SKILL_BASED"
    GEOGRAPHIC = "GEOGRAPHIC"
    RANDOM = "RANDOM"


class LeadAssignmentError(Exception):
    """Custom exception for lead assignment errors."""
    def __init__(self, message: str, details: Dict = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class LeadAssignmentService:
    """
    Service for automatic lead distribution among sales agents.
    """

    def __init__(self, db: AsyncSession, company_id: UUID):
        self.db = db
        self.company_id = company_id

    async def get_available_agents(
        self,
        team_id: Optional[UUID] = None,
        required_skills: List[str] = None
    ) -> List[User]:
        """
        Get list of available sales agents for lead assignment.

        Filters:
        - Is active user
        - Has SALES or TELECALLING role
        - Is not on leave (if leave tracking enabled)
        - Within working hours (if configured)
        """
        query = select(User).where(
            and_(
                User.company_id == self.company_id,
                User.is_active == True,
            )
        )

        # Filter by team if specified
        if team_id:
            query = query.where(User.team_id == team_id)

        # Filter by role (SALES, TELECALLING, SALES_AGENT)
        query = query.where(
            or_(
                User.role.in_(["SALES", "TELECALLING", "SALES_AGENT", "SALES_REP"]),
                User.department == "Sales"
            )
        )

        result = await self.db.execute(query)
        agents = list(result.scalars().all())

        # Filter by skills if specified
        if required_skills and agents:
            agents = [
                agent for agent in agents
                if agent.skills and any(skill in agent.skills for skill in required_skills)
            ]

        return agents

    async def get_agent_current_load(self, agent_id: UUID) -> Dict:
        """
        Get current workload metrics for an agent.

        Returns:
        - open_leads: Number of unassigned/in-progress leads
        - leads_today: Leads assigned today
        - leads_this_week: Leads assigned this week
        - conversion_rate: Recent conversion rate
        """
        today = datetime.now(timezone.utc).date()
        week_start = today - timedelta(days=today.weekday())

        # Open leads (not converted/closed)
        open_leads_query = select(func.count(Lead.id)).where(
            and_(
                Lead.assigned_to == agent_id,
                Lead.status.in_([
                    LeadStatus.NEW, LeadStatus.CONTACTED,
                    LeadStatus.QUALIFIED, LeadStatus.NURTURING
                ])
            )
        )
        open_leads_result = await self.db.execute(open_leads_query)
        open_leads = open_leads_result.scalar() or 0

        # Leads assigned today
        today_query = select(func.count(Lead.id)).where(
            and_(
                Lead.assigned_to == agent_id,
                func.date(Lead.assigned_at) == today
            )
        )
        today_result = await self.db.execute(today_query)
        leads_today = today_result.scalar() or 0

        # Leads this week
        week_query = select(func.count(Lead.id)).where(
            and_(
                Lead.assigned_to == agent_id,
                func.date(Lead.assigned_at) >= week_start
            )
        )
        week_result = await self.db.execute(week_query)
        leads_this_week = week_result.scalar() or 0

        return {
            "agent_id": str(agent_id),
            "open_leads": open_leads,
            "leads_today": leads_today,
            "leads_this_week": leads_this_week,
        }

    async def get_next_agent_round_robin(
        self,
        team_id: Optional[UUID] = None,
        lead_source: Optional[str] = None
    ) -> Optional[User]:
        """
        Get next agent in round-robin sequence.

        Uses last assignment timestamp to determine next agent.
        """
        agents = await self.get_available_agents(team_id=team_id)

        if not agents:
            return None

        if len(agents) == 1:
            return agents[0]

        # Find agent with oldest last assignment
        agent_with_oldest_assignment = None
        oldest_assignment_time = datetime.now(timezone.utc)

        for agent in agents:
            # Get last assigned lead for this agent
            last_assignment_query = select(Lead.assigned_at).where(
                Lead.assigned_to == agent.id
            ).order_by(desc(Lead.assigned_at)).limit(1)

            result = await self.db.execute(last_assignment_query)
            last_assigned = result.scalar_one_or_none()

            if last_assigned is None:
                # Agent has no leads, prioritize them
                return agent

            if last_assigned < oldest_assignment_time:
                oldest_assignment_time = last_assigned
                agent_with_oldest_assignment = agent

        return agent_with_oldest_assignment or agents[0]

    async def get_next_agent_load_balanced(
        self,
        team_id: Optional[UUID] = None,
        max_daily_leads: int = 50
    ) -> Optional[User]:
        """
        Get agent with lowest current workload.

        Considers:
        - Open lead count
        - Today's lead count (vs max_daily_leads)
        """
        agents = await self.get_available_agents(team_id=team_id)

        if not agents:
            return None

        if len(agents) == 1:
            return agents[0]

        min_load = float('inf')
        best_agent = None

        for agent in agents:
            load = await self.get_agent_current_load(agent.id)

            # Skip if already at daily limit
            if load["leads_today"] >= max_daily_leads:
                continue

            # Score based on open leads and today's count
            score = load["open_leads"] * 2 + load["leads_today"]

            if score < min_load:
                min_load = score
                best_agent = agent

        return best_agent or agents[0]

    async def get_next_agent_geographic(
        self,
        pincode: str,
        team_id: Optional[UUID] = None
    ) -> Optional[User]:
        """
        Get agent based on geographic territory.

        Matches lead pincode to agent's assigned territory.
        Falls back to round-robin if no match found.
        """
        agents = await self.get_available_agents(team_id=team_id)

        if not agents:
            return None

        # Extract state/region from pincode
        state_code = pincode[:2] if pincode else None

        # Find agent with matching territory
        for agent in agents:
            if hasattr(agent, 'assigned_pincodes') and agent.assigned_pincodes:
                if pincode in agent.assigned_pincodes:
                    return agent

            if hasattr(agent, 'assigned_states') and agent.assigned_states:
                if state_code in agent.assigned_states:
                    return agent

        # Fall back to round-robin
        return await self.get_next_agent_round_robin(team_id=team_id)

    async def assign_lead(
        self,
        lead_id: UUID,
        strategy: AssignmentStrategy = AssignmentStrategy.ROUND_ROBIN,
        team_id: Optional[UUID] = None,
        force_agent_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None
    ) -> Lead:
        """
        Assign a lead to an agent.

        Args:
            lead_id: ID of lead to assign
            strategy: Assignment strategy to use
            team_id: Optional team to assign from
            force_agent_id: Manually specify agent (bypasses auto-assignment)
            user_id: User performing the action

        Returns:
            Updated lead with assignment
        """
        # Get lead
        result = await self.db.execute(
            select(Lead).where(Lead.id == lead_id)
        )
        lead = result.scalar_one_or_none()

        if not lead:
            raise LeadAssignmentError("Lead not found")

        # Get agent
        agent = None

        if force_agent_id:
            # Manual assignment
            agent_result = await self.db.execute(
                select(User).where(User.id == force_agent_id)
            )
            agent = agent_result.scalar_one_or_none()
        else:
            # Auto-assignment based on strategy
            if strategy == AssignmentStrategy.ROUND_ROBIN:
                agent = await self.get_next_agent_round_robin(
                    team_id=team_id,
                    lead_source=lead.source if lead.source else None
                )
            elif strategy == AssignmentStrategy.LOAD_BALANCED:
                agent = await self.get_next_agent_load_balanced(team_id=team_id)
            elif strategy == AssignmentStrategy.GEOGRAPHIC:
                agent = await self.get_next_agent_geographic(
                    pincode=lead.pincode or "",
                    team_id=team_id
                )
            else:
                agent = await self.get_next_agent_round_robin(team_id=team_id)

        if not agent:
            raise LeadAssignmentError(
                "No available agents found for assignment",
                {"strategy": strategy.value, "team_id": str(team_id) if team_id else None}
            )

        # Update lead
        lead.assigned_to = agent.id
        lead.assigned_at = datetime.now(timezone.utc)
        lead.assigned_by = user_id
        lead.assignment_strategy = strategy.value

        # Update status if new
        if lead.status == LeadStatus.NEW:
            lead.status = LeadStatus.ASSIGNED.value

        await self.db.commit()
        await self.db.refresh(lead)

        return lead

    async def bulk_assign_leads(
        self,
        lead_ids: List[UUID],
        strategy: AssignmentStrategy = AssignmentStrategy.ROUND_ROBIN,
        team_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None
    ) -> Dict:
        """
        Assign multiple leads in bulk.

        Returns summary of assignments.
        """
        results = {
            "assigned": 0,
            "failed": 0,
            "assignments": [],
            "errors": []
        }

        for lead_id in lead_ids:
            try:
                lead = await self.assign_lead(
                    lead_id=lead_id,
                    strategy=strategy,
                    team_id=team_id,
                    user_id=user_id
                )
                results["assigned"] += 1
                results["assignments"].append({
                    "lead_id": str(lead_id),
                    "assigned_to": str(lead.assigned_to),
                })
            except LeadAssignmentError as e:
                results["failed"] += 1
                results["errors"].append({
                    "lead_id": str(lead_id),
                    "error": e.message
                })

        return results

    async def reassign_lead(
        self,
        lead_id: UUID,
        new_agent_id: UUID,
        reason: str = "",
        user_id: Optional[UUID] = None
    ) -> Lead:
        """
        Reassign a lead to a different agent.

        Tracks reassignment history.
        """
        result = await self.db.execute(
            select(Lead).where(Lead.id == lead_id)
        )
        lead = result.scalar_one_or_none()

        if not lead:
            raise LeadAssignmentError("Lead not found")

        # Store previous assignment info
        previous_agent_id = lead.assigned_to
        previous_assignment_time = lead.assigned_at

        # Update assignment
        lead.assigned_to = new_agent_id
        lead.assigned_at = datetime.now(timezone.utc)
        lead.assigned_by = user_id
        lead.reassignment_count = (lead.reassignment_count or 0) + 1
        lead.last_reassignment_reason = reason

        # Add to history (if history field exists)
        if hasattr(lead, 'assignment_history') and lead.assignment_history is None:
            lead.assignment_history = []

        if hasattr(lead, 'assignment_history'):
            lead.assignment_history.append({
                "from_agent": str(previous_agent_id) if previous_agent_id else None,
                "to_agent": str(new_agent_id),
                "at": datetime.now(timezone.utc).isoformat(),
                "by": str(user_id) if user_id else None,
                "reason": reason
            })

        await self.db.commit()
        await self.db.refresh(lead)

        return lead

    async def get_unassigned_leads(
        self,
        limit: int = 100,
        source: Optional[str] = None
    ) -> List[Lead]:
        """Get leads that haven't been assigned yet."""
        query = select(Lead).where(
            and_(
                Lead.company_id == self.company_id,
                Lead.assigned_to == None,
                Lead.status.in_([LeadStatus.NEW, LeadStatus.ASSIGNED])
            )
        )

        if source:
            query = query.where(Lead.source == LeadSource(source))

        query = query.order_by(Lead.created_at.asc()).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def auto_assign_all_pending(
        self,
        strategy: AssignmentStrategy = AssignmentStrategy.ROUND_ROBIN,
        team_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None
    ) -> Dict:
        """
        Auto-assign all unassigned leads.

        Useful for batch processing at scheduled intervals.
        """
        unassigned = await self.get_unassigned_leads()

        if not unassigned:
            return {
                "assigned": 0,
                "failed": 0,
                "message": "No unassigned leads found"
            }

        return await self.bulk_assign_leads(
            lead_ids=[lead.id for lead in unassigned],
            strategy=strategy,
            team_id=team_id,
            user_id=user_id
        )

    async def get_assignment_stats(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict:
        """
        Get lead assignment statistics.

        Returns distribution of leads among agents.
        """
        if not start_date:
            start_date = datetime.now(timezone.utc) - timedelta(days=30)
        if not end_date:
            end_date = datetime.now(timezone.utc)

        # Get assignments per agent
        query = select(
            Lead.assigned_to,
            func.count(Lead.id).label("lead_count")
        ).where(
            and_(
                Lead.company_id == self.company_id,
                Lead.assigned_at >= start_date,
                Lead.assigned_at <= end_date,
                Lead.assigned_to != None
            )
        ).group_by(Lead.assigned_to)

        result = await self.db.execute(query)
        distribution = result.all()

        return {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            "agent_distribution": [
                {
                    "agent_id": str(row.assigned_to),
                    "lead_count": row.lead_count
                }
                for row in distribution
            ],
            "total_leads": sum(row.lead_count for row in distribution)
        }
