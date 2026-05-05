"""
Calendar service for the legal platform.

Generates iCal (RFC 5545) file content for deadlines and time entries.
All operations are tenant-scoped.
"""

import uuid
from datetime import datetime, timedelta, UTC
from typing import Optional, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from breaking_law.infra.models import Deadline, TimeEntry


class CalendarService:
    """Business logic for iCal export of deadlines and time entries."""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    # ------------------------------------------------------------------
    # iCal generation helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _format_ical_datetime(dt: datetime) -> str:
        """Format a datetime as UTC iCal datetime string."""
        if dt.tzinfo is None:
            # Assume naive datetimes are already in UTC
            dt = dt.replace(tzinfo=UTC)
        return dt.strftime("%Y%m%dT%H%M%SZ")

    @staticmethod
    def _generate_ical_event(
        uid: str,
        summary: str,
        description: str,
        start: datetime,
        end: Optional[datetime] = None,
        url: Optional[str] = None,
    ) -> str:
        """Generate a single VEVENT block."""
        lines = [
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{CalendarService._format_ical_datetime(datetime.now(UTC))}",
            f"SUMMARY:{CalendarService._escape_ical_text(summary)}",
            f"DESCRIPTION:{CalendarService._escape_ical_text(description)}",
            f"DTSTART:{CalendarService._format_ical_datetime(start)}",
        ]
        if end:
            lines.append(f"DTEND:{CalendarService._format_ical_datetime(end)}")
        if url:
            lines.append(f"URL:{url}")
        lines.append("END:VEVENT")
        return "\r\n".join(lines)

    @staticmethod
    def _escape_ical_text(text: str) -> str:
        """Escape special characters for iCal text values."""
        return text.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")

    @staticmethod
    def _wrap_ical_calendar(events: List[str]) -> str:
        """Wrap VEVENT blocks in a VCALENDAR container."""
        lines = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//Breaking Law//Legal Platform//EN",
            "CALSCALE:GREGORIAN",
            "METHOD:PUBLISH",
        ]
        for event in events:
            lines.append(event)
        lines.append("END:VCALENDAR")
        return "\r\n".join(lines)

    # ------------------------------------------------------------------
    # Export methods
    # ------------------------------------------------------------------

    async def export_deadlines_to_ical(
        self,
        law_firm_id: uuid.UUID,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> str:
        """Generate iCal content for all deadlines in a date range."""
        query = select(Deadline).where(Deadline.law_firm_id == law_firm_id)
        if date_from:
            query = query.where(Deadline.due_date >= date_from)
        if date_to:
            query = query.where(Deadline.due_date <= date_to)
        query = query.order_by(Deadline.due_date.asc())
        result = await self.db.execute(query)
        deadlines = result.scalars().all()

        events = []
        for deadline in deadlines:
            matter_ref = f"Matter: {deadline.matter_id}" if deadline.matter_id else "No matter"
            event = self._generate_ical_event(
                uid=f"deadline-{deadline.id}@breaking-law",
                summary=deadline.title,
                description=f"{deadline.description or ''}\n{matter_ref}",
                start=deadline.due_date,
            )
            events.append(event)

        return self._wrap_ical_calendar(events)

    async def export_time_entries_to_ical(
        self,
        law_firm_id: uuid.UUID,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> str:
        """Generate iCal content for time entries as time blocks."""
        query = select(TimeEntry).where(TimeEntry.law_firm_id == law_firm_id)
        if date_from:
            query = query.where(TimeEntry.started_at >= date_from)
        if date_to:
            query = query.where(TimeEntry.started_at <= date_to)
        query = query.order_by(TimeEntry.started_at.asc())
        result = await self.db.execute(query)
        entries = result.scalars().all()

        events = []
        for entry in entries:
            matter_ref = f"Matter: {entry.matter_id}" if entry.matter_id else "No matter"
            end = entry.ended_at or (entry.started_at + timedelta(minutes=entry.duration_minutes or 0))
            event = self._generate_ical_event(
                uid=f"timeentry-{entry.id}@breaking-law",
                summary=entry.description or "Time entry",
                description=f"Duration: {entry.duration_minutes or 0} min\n{matter_ref}",
                start=entry.started_at,
                end=end,
            )
            events.append(event)

        return self._wrap_ical_calendar(events)

    async def export_matter_to_ical(
        self,
        law_firm_id: uuid.UUID,
        matter_id: uuid.UUID,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> str:
        """Generate iCal content for all deadlines and time entries of a specific matter."""
        events = []

        # Deadlines for matter
        query = select(Deadline).where(
            Deadline.law_firm_id == law_firm_id,
            Deadline.matter_id == matter_id,
        )
        if date_from:
            query = query.where(Deadline.due_date >= date_from)
        if date_to:
            query = query.where(Deadline.due_date <= date_to)
        query = query.order_by(Deadline.due_date.asc())
        result = await self.db.execute(query)
        for deadline in result.scalars().all():
            event = self._generate_ical_event(
                uid=f"deadline-{deadline.id}@breaking-law",
                summary=deadline.title,
                description=deadline.description or "",
                start=deadline.due_date,
            )
            events.append(event)

        # Time entries for matter
        query = select(TimeEntry).where(
            TimeEntry.law_firm_id == law_firm_id,
            TimeEntry.matter_id == matter_id,
        )
        if date_from:
            query = query.where(TimeEntry.started_at >= date_from)
        if date_to:
            query = query.where(TimeEntry.started_at <= date_to)
        query = query.order_by(TimeEntry.started_at.asc())
        result = await self.db.execute(query)
        for entry in result.scalars().all():
            end = entry.ended_at or (entry.started_at + timedelta(minutes=entry.duration_minutes or 0))
            event = self._generate_ical_event(
                uid=f"timeentry-{entry.id}@breaking-law",
                summary=entry.description or "Time entry",
                description=f"Duration: {entry.duration_minutes or 0} min",
                start=entry.started_at,
                end=end,
            )
            events.append(event)

        return self._wrap_ical_calendar(events)
