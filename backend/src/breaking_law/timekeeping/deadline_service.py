"""
Deadline service for the legal platform.

Manages deadline creation, lifecycle, and querying for overdue and upcoming items.
All operations are tenant-scoped.
"""

import uuid
from datetime import datetime, timedelta, UTC
from typing import Optional, List

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from breaking_law.infra.models import Deadline, DeadlineStatus, DeadlinePriority


class DeadlineService:
    """Business logic for deadline management."""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def create_deadline(
        self,
        law_firm_id: uuid.UUID,
        created_by: uuid.UUID,
        title: str,
        description: Optional[str] = None,
        due_date: datetime = None,
        priority: DeadlinePriority = DeadlinePriority.medium,
        matter_id: Optional[uuid.UUID] = None,
    ) -> Deadline:
        """Create a new deadline."""
        if due_date is None:
            due_date = datetime.now(UTC)
        deadline = Deadline(
            law_firm_id=law_firm_id,
            created_by=created_by,
            matter_id=matter_id,
            title=title,
            description=description,
            due_date=due_date,
            priority=priority,
            status=DeadlineStatus.pending,
        )
        self.db.add(deadline)
        await self.db.flush()
        await self.db.refresh(deadline)
        return deadline

    async def get_deadline(self, deadline_id: uuid.UUID, law_firm_id: uuid.UUID) -> Optional[Deadline]:
        """Get a single deadline by ID, scoped to tenant."""
        result = await self.db.execute(
            select(Deadline).where(
                Deadline.id == deadline_id,
                Deadline.law_firm_id == law_firm_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_deadlines(
        self,
        law_firm_id: uuid.UUID,
        matter_id: Optional[uuid.UUID] = None,
        status: Optional[DeadlineStatus] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Deadline]:
        """List deadlines with optional filters."""
        query = select(Deadline).where(Deadline.law_firm_id == law_firm_id)
        if matter_id:
            query = query.where(Deadline.matter_id == matter_id)
        if status:
            query = query.where(Deadline.status == status)
        if start_date:
            query = query.where(Deadline.due_date >= start_date)
        if end_date:
            query = query.where(Deadline.due_date <= end_date)
        query = query.order_by(Deadline.due_date.asc()).limit(limit).offset(offset)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def acknowledge(self, deadline_id: uuid.UUID, user_id: uuid.UUID) -> Optional[Deadline]:
        """Mark a deadline as acknowledged by a user."""
        result = await self.db.execute(
            select(Deadline).where(Deadline.id == deadline_id)
        )
        deadline = result.scalar_one_or_none()
        if not deadline:
            return None
        if deadline.status == DeadlineStatus.completed:
            raise ValueError("Cannot acknowledge a completed deadline")
        deadline.status = DeadlineStatus.acknowledged
        deadline.acknowledged_at = datetime.now(UTC)
        await self.db.flush()
        await self.db.refresh(deadline)
        return deadline

    async def complete(self, deadline_id: uuid.UUID) -> Optional[Deadline]:
        """Mark a deadline as completed."""
        result = await self.db.execute(
            select(Deadline).where(Deadline.id == deadline_id)
        )
        deadline = result.scalar_one_or_none()
        if not deadline:
            return None
        deadline.status = DeadlineStatus.completed
        deadline.completed_at = datetime.now(UTC)
        await self.db.flush()
        await self.db.refresh(deadline)
        return deadline

    async def get_overdue(self, law_firm_id: uuid.UUID) -> List[Deadline]:
        """Return all overdue and uncompleted deadlines."""
        now = datetime.now(UTC)
        result = await self.db.execute(
            select(Deadline).where(
                Deadline.law_firm_id == law_firm_id,
                Deadline.due_date < now,
                Deadline.status.notin_([DeadlineStatus.completed]),
            ).order_by(Deadline.due_date.asc())
        )
        return list(result.scalars().all())

    async def get_upcoming(self, law_firm_id: uuid.UUID, days: int = 7) -> List[Deadline]:
        """Return deadlines due in the next N days."""
        now = datetime.now(UTC)
        future = now + timedelta(days=days)
        result = await self.db.execute(
            select(Deadline).where(
                Deadline.law_firm_id == law_firm_id,
                Deadline.due_date >= now,
                Deadline.due_date <= future,
                Deadline.status.notin_([DeadlineStatus.completed]),
            ).order_by(Deadline.due_date.asc())
        )
        return list(result.scalars().all())
