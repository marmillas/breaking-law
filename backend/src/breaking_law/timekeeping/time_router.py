"""
Time tracking router for the legal platform.

Handles timer start/stop, time entry listing, submission, approval,
and billing report generation. All endpoints require authentication
and are tenant-scoped.
"""

import uuid
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from breaking_law.api.deps import (
    get_tenant_session,
    get_current_user,
    UserContext,
    require_role,
)
from breaking_law.timekeeping.time_service import TimeService
from breaking_law.infra.models import TimeEntry, TimeEntryStatus
from breaking_law.domain.schemas.timekeeping import StartTimerRequest, TimeEntryOut, ReportOut

router = APIRouter(
    prefix="/time",
    tags=["time"],
)


def _serialize_entry(entry: TimeEntry) -> TimeEntryOut:
    """Convert ORM TimeEntry to response model."""
    return TimeEntryOut(
        id=entry.id,
        law_firm_id=entry.law_firm_id,
        user_id=entry.user_id,
        matter_id=entry.matter_id,
        client_id=entry.client_id,
        description=entry.description,
        started_at=entry.started_at.isoformat(),
        ended_at=entry.ended_at.isoformat() if entry.ended_at else None,
        duration_minutes=entry.duration_minutes,
        billable=entry.billable,
        billing_rate=entry.billing_rate,
        status=entry.status.value,
        created_at=entry.created_at.isoformat(),
        updated_at=entry.updated_at.isoformat(),
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/start", response_model=TimeEntryOut, status_code=status.HTTP_201_CREATED)
async def start_timer(
    request: StartTimerRequest,
    db: AsyncSession = Depends(get_tenant_session),
    current_user: UserContext = Depends(get_current_user),
):
    """Start a new timer for the current user."""
    service = TimeService(db)
    entry = await service.start_timer(
        user_id=current_user.user_id,
        law_firm_id=current_user.law_firm_id,
        matter_id=request.matter_id,
        client_id=request.client_id,
        description=request.description,
    )
    return _serialize_entry(entry)


@router.post("/{entry_id}/stop", response_model=TimeEntryOut)
async def stop_timer(
    entry_id: uuid.UUID,
    db: AsyncSession = Depends(get_tenant_session),
    current_user: UserContext = Depends(get_current_user),
):
    """Stop a running timer."""
    service = TimeService(db)
    entry = await service.stop_timer(entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Time entry not found")
    return _serialize_entry(entry)


@router.get("/entries", response_model=List[TimeEntryOut])
async def list_entries(
    matter_id: Optional[uuid.UUID] = None,
    client_id: Optional[uuid.UUID] = None,
    status: Optional[TimeEntryStatus] = None,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_tenant_session),
    current_user: UserContext = Depends(get_current_user),
):
    """List time entries for the current law firm."""
    service = TimeService(db)
    entries = await service.list_entries(
        law_firm_id=current_user.law_firm_id,
        matter_id=matter_id,
        client_id=client_id,
        status=status,
        limit=limit,
        offset=offset,
    )
    return [_serialize_entry(e) for e in entries]


@router.post("/{entry_id}/submit", response_model=TimeEntryOut)
async def submit_entry(
    entry_id: uuid.UUID,
    db: AsyncSession = Depends(get_tenant_session),
    current_user: UserContext = Depends(get_current_user),
):
    """Submit a time entry for approval."""
    service = TimeService(db)
    entry = await service.submit_for_approval(entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Time entry not found")
    return _serialize_entry(entry)


@router.post(
    "/{entry_id}/approve",
    response_model=TimeEntryOut,
    dependencies=[Depends(require_role(["owner", "lawyer"]))],
)
async def approve_entry(
    entry_id: uuid.UUID,
    db: AsyncSession = Depends(get_tenant_session),
    current_user: UserContext = Depends(get_current_user),
):
    """Approve a submitted time entry. Requires owner or lawyer role."""
    service = TimeService(db)
    entry = await service.approve_entry(entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Time entry not found")
    return _serialize_entry(entry)


@router.get("/report", response_model=ReportOut)
async def get_report(
    client_id: Optional[uuid.UUID] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: AsyncSession = Depends(get_tenant_session),
    current_user: UserContext = Depends(get_current_user),
):
    """Generate a billing report for approved time entries."""
    service = TimeService(db)
    report = await service.generate_report(
        law_firm_id=current_user.law_firm_id,
        client_id=client_id,
        start_date=start_date,
        end_date=end_date,
    )
    return ReportOut(**report)
