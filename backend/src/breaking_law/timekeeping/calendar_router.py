"""
Calendar router for the legal platform.

Provides iCal export endpoints for deadlines, time entries,
and matter-specific events. All endpoints require authentication
and are tenant-scoped.
"""

import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.ext.asyncio import AsyncSession

from breaking_law.api.deps import (
    get_tenant_session,
    get_current_user,
    UserContext,
)
from breaking_law.timekeeping.calendar_service import CalendarService

router = APIRouter(
    prefix="/calendar",
    tags=["calendar"],
)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/deadlines.ics")
async def export_deadlines_ical(
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    db: AsyncSession = Depends(get_tenant_session),
    current_user: UserContext = Depends(get_current_user),
):
    """Download deadlines as an iCal file."""
    service = CalendarService(db)
    ical = await service.export_deadlines_to_ical(
        law_firm_id=current_user.law_firm_id,
        date_from=date_from,
        date_to=date_to,
    )
    return Response(
        content=ical,
        media_type="text/calendar",
        headers={
            "Content-Disposition": 'attachment; filename="deadlines.ics"'
        },
    )


@router.get("/time-entries.ics")
async def export_time_entries_ical(
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    db: AsyncSession = Depends(get_tenant_session),
    current_user: UserContext = Depends(get_current_user),
):
    """Download time entries as an iCal file."""
    service = CalendarService(db)
    ical = await service.export_time_entries_to_ical(
        law_firm_id=current_user.law_firm_id,
        date_from=date_from,
        date_to=date_to,
    )
    return Response(
        content=ical,
        media_type="text/calendar",
        headers={
            "Content-Disposition": 'attachment; filename="time-entries.ics"'
        },
    )


@router.get("/matter/{matter_id}.ics")
async def export_matter_ical(
    matter_id: uuid.UUID,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    db: AsyncSession = Depends(get_tenant_session),
    current_user: UserContext = Depends(get_current_user),
):
    """Download all calendar events for a specific matter as iCal."""
    service = CalendarService(db)
    ical = await service.export_matter_to_ical(
        law_firm_id=current_user.law_firm_id,
        matter_id=matter_id,
        date_from=date_from,
        date_to=date_to,
    )
    return Response(
        content=ical,
        media_type="text/calendar",
        headers={
            "Content-Disposition": f'attachment; filename="matter-{matter_id}.ics"'
        },
    )
