"""
Region-based filtering middleware and utilities.
Provides attribute-based access control (ABAC) based on user's assigned region.
"""

from typing import Optional, List, Set
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.region import Region
from app.models.role import RoleLevel
from app.core.permissions import get_level_value


class RegionFilter:
    """
    Region-based filter for ABAC (Attribute-Based Access Control).
    Filters data based on user's assigned region in the hierarchy.
    """

    def __init__(self, user: User, db: AsyncSession):
        """
        Initialize region filter.

        Args:
            user: The current user
            db: Database session
        """
        self.user = user
        self.db = db
        self._allowed_region_ids: Optional[Set[uuid.UUID]] = None

    @property
    def has_region(self) -> bool:
        """Check if user has an assigned region."""
        return self.user.region_id is not None

    @property
    def user_region_id(self) -> Optional[uuid.UUID]:
        """Get user's assigned region ID."""
        return self.user.region_id

    def should_filter_by_region(self) -> bool:
        """
        Determine if data should be filtered by region.

        SUPER_ADMIN and DIRECTOR levels see all data.
        HEAD, MANAGER, EXECUTIVE see only their region's data.
        """
        # Get user's highest role level
        if not self.user.roles:
            return True  # No roles = filter by region

        # Get level with lowest value (highest authority)
        highest_level = min((role.level for role in self.user.roles), key=get_level_value)

        # SUPER_ADMIN and DIRECTOR see everything
        if highest_level in (RoleLevel.SUPER_ADMIN.name, RoleLevel.DIRECTOR.name):
            return False

        # Others are filtered by region
        return True

    async def get_allowed_region_ids(self) -> Set[uuid.UUID]:
        """
        Get all region IDs the user is allowed to access.
        Includes the user's region and all its descendants.

        Returns:
            Set of allowed region UUIDs
        """
        if self._allowed_region_ids is not None:
            return self._allowed_region_ids

        if not self.has_region:
            # No region assigned = empty set (no access)
            self._allowed_region_ids = set()
            return self._allowed_region_ids

        # Get user's region and all descendants
        allowed_ids = {self.user_region_id}

        # Recursively get all child regions
        async def get_descendants(parent_id: uuid.UUID) -> Set[uuid.UUID]:
            stmt = select(Region.id).where(Region.parent_id == parent_id)
            result = await self.db.execute(stmt)
            child_ids = {row[0] for row in result.all()}

            descendants = child_ids.copy()
            for child_id in child_ids:
                descendants.update(await get_descendants(child_id))

            return descendants

        allowed_ids.update(await get_descendants(self.user_region_id))

        self._allowed_region_ids = allowed_ids
        return self._allowed_region_ids

    async def filter_by_region(
        self,
        query,
        region_column,
        allow_null: bool = False
    ):
        """
        Apply region filter to a SQLAlchemy query.

        Args:
            query: SQLAlchemy select statement
            region_column: The column to filter on (e.g., Order.region_id)
            allow_null: If True, also include records with null region

        Returns:
            Modified query with region filter applied
        """
        if not self.should_filter_by_region():
            return query

        allowed_ids = await self.get_allowed_region_ids()

        if not allowed_ids:
            # No regions allowed - return query that matches nothing
            return query.where(False)

        if allow_null:
            return query.where(
                (region_column.in_(allowed_ids)) |
                (region_column.is_(None))
            )
        else:
            return query.where(region_column.in_(allowed_ids))

    async def can_access_region(self, region_id: uuid.UUID) -> bool:
        """
        Check if user can access a specific region.

        Args:
            region_id: The region ID to check

        Returns:
            True if user can access the region
        """
        if not self.should_filter_by_region():
            return True

        allowed_ids = await self.get_allowed_region_ids()
        return region_id in allowed_ids

    async def get_region_hierarchy(self) -> List[dict]:
        """
        Get the region hierarchy for the user.
        Returns the user's region and its descendants as a tree.

        Returns:
            List of region dictionaries with nested children
        """
        if not self.has_region:
            return []

        # Get user's region
        stmt = select(Region).where(Region.id == self.user_region_id)
        result = await self.db.execute(stmt)
        user_region = result.scalar_one_or_none()

        if not user_region:
            return []

        async def build_tree(region: Region) -> dict:
            # Get children
            stmt = (
                select(Region)
                .where(Region.parent_id == region.id)
                .where(Region.is_active == True)
                .order_by(Region.name)
            )
            result = await self.db.execute(stmt)
            children = result.scalars().all()

            return {
                "id": str(region.id),
                "name": region.name,
                "code": region.code,
                "type": region.type,
                "children": [await build_tree(child) for child in children]
            }

        return [await build_tree(user_region)]


async def get_region_filter(user: User, db: AsyncSession) -> RegionFilter:
    """
    Factory function to create a RegionFilter instance.

    Usage in endpoints:
        region_filter = await get_region_filter(current_user, db)
        query = await region_filter.filter_by_region(query, Order.region_id)
    """
    return RegionFilter(user, db)


# Example usage in an endpoint:
"""
from app.middleware.region_filter import get_region_filter

@router.get("/orders")
async def list_orders(
    db: DB,
    current_user: CurrentUser,
):
    # Create region filter
    region_filter = await get_region_filter(current_user, db)

    # Build query
    query = select(Order).order_by(Order.created_at.desc())

    # Apply region filter
    query = await region_filter.filter_by_region(query, Order.region_id)

    # Execute
    result = await db.execute(query)
    orders = result.scalars().all()

    return orders
"""
