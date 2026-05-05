"""
Time tracking service for the legal platform.

Handles timer start/stop, time entry lifecycle, and billing report generation.
All operations are tenant-scoped.
"""

import uuid
from datetime import datetime, UTC
from typing import Optional, List

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from breaking_law.infra.models import TimeEntry, TimeEntryStatus


class TimeService:
    """Business logic for time tracking and billing entries."""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def start_timer(
        self,
        user_id: uuid.UUID,
        law_firm_id: uuid.UUID,
        matter_id: Optional[uuid.UUID] = None,
        client_id: Optional[uuid.UUID] = None,
        description: Optional[str] = None,
    ) -> TimeEntry:
        """Start a new timer entry."""
        entry = TimeEntry(
            law_firm_id=law_firm_id,
            user_id=user_id,
            matter_id=matter_id,
            client_id=client_id,
            description=description,
            started_at=datetime.now(UTC),
            status=TimeEntryStatus.draft,
        )
        self.db.add(entry)
        await self.db.flush()
        await self.db.refresh(entry)
        return entry

    async def stop_timer(self, entry_id: uuid.UUID) -> Optional[TimeEntry]:
        """Stop a running timer and compute duration."""
        result = await self.db.execute(
            select(TimeEntry).where(TimeEntry.id == entry_id)
        )
        entry = result.scalar_one_or_none()
        if not entry:
            return None
        if entry.ended_at is not None:
            raise ValueError("Timer already stopped")
        entry.ended_at = datetime.now(UTC)
        started = entry.started_at
        if started.tzinfo is None:
            started = started.replace(tzinfo=UTC)
        delta = entry.ended_at - started
        entry.duration_minutes = int(delta.total_seconds() / 60)
        entry.status = TimeEntryStatus.draft
        await self.db.flush()
        await self.db.refresh(entry)
        return entry

    async def list_entries(
        self,
        law_firm_id: uuid.UUID,
        user_id: Optional[uuid.UUID] = None,
        matter_id: Optional[uuid.UUID] = None,
        client_id: Optional[uuid.UUID] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        status: Optional[TimeEntryStatus] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[TimeEntry]:
        """List time entries with optional filters."""
        query = select(TimeEntry).where(TimeEntry.law_firm_id == law_firm_id)
        if user_id:
            query = query.where(TimeEntry.user_id == user_id)
        if matter_id:
            query = query.where(TimeEntry.matter_id == matter_id)
        if client_id:
            query = query.where(TimeEntry.client_id == client_id)
        if start_date:
            query = query.where(TimeEntry.started_at >= start_date)
        if end_date:
            query = query.where(TimeEntry.started_at <= end_date)
        if status:
            query = query.where(TimeEntry.status == status)
        query = query.order_by(TimeEntry.started_at.desc()).limit(limit).offset(offset)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def submit_for_approval(self, entry_id: uuid.UUID) -> Optional[TimeEntry]:
        """Submit a time entry for approval."""
        result = await self.db.execute(
            select(TimeEntry).where(TimeEntry.id == entry_id)
        )
        entry = result.scalar_one_or_none()
        if not entry:
            return None
        if entry.status != TimeEntryStatus.draft:
            raise ValueError("Only draft entries can be submitted")
        entry.status = TimeEntryStatus.submitted
        await self.db.flush()
        await self.db.refresh(entry)
        return entry

    async def approve_entry(self, entry_id: uuid.UUID) -> Optional[TimeEntry]:
        """Approve a submitted time entry."""
        result = await self.db.execute(
            select(TimeEntry).where(TimeEntry.id == entry_id)
        )
        entry = result.scalar_one_or_none()
        if not entry:
            return None
        if entry.status != TimeEntryStatus.submitted:
            raise ValueError("Only submitted entries can be approved")
        entry.status = TimeEntryStatus.approved
        await self.db.flush()
        await self.db.refresh(entry)
        return entry

    async def generate_report(
        self,
        law_firm_id: uuid.UUID,
        client_id: Optional[uuid.UUID] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> dict:
        """Generate a billing report with total hours and matter breakdown."""
        query = select(TimeEntry).where(
            TimeEntry.law_firm_id == law_firm_id,
            TimeEntry.status == TimeEntryStatus.approved,
        )
        if client_id:
            query = query.where(TimeEntry.client_id == client_id)
        if start_date:
            query = query.where(TimeEntry.started_at >= start_date)
        if end_date:
            query = query.where(TimeEntry.started_at <= end_date)
        result = await self.db.execute(query)
        entries = list(result.scalars().all())

        total_minutes = 0
        billable_minutes = 0
        matter_breakdown: dict = {}

        for entry in entries:
            mins = entry.duration_minutes or 0
            total_minutes += mins
            if entry.billable:
                billable_minutes += mins
            matter_id = str(entry.matter_id) if entry.matter_id else "unassigned"
            if matter_id not in matter_breakdown:
                matter_breakdown[matter_id] = {"minutes": 0, "billable_minutes": 0}
            matter_breakdown[matter_id]["minutes"] += mins
            if entry.billable:
                matter_breakdown[matter_id]["billable_minutes"] += mins

        return {
            "total_hours": round(total_minutes / 60, 2),
            "billable_hours": round(billable_minutes / 60, 2),
            "total_entries": len(entries),
            "matter_breakdown": matter_breakdown,
        }
