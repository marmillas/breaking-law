"""
Deadlines router for the legal platform.

Handles deadline creation, listing, overdue/upcoming queries,
acknowledgment, and completion. All endpoints require authentication
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
)
from breaking_law.timekeeping.deadline_service import DeadlineService
from breaking_law.infra.models import Deadline, DeadlinePriority, DeadlineStatus
from breaking_law.domain.schemas.timekeeping import DeadlineCreate, DeadlineOut

router = APIRouter(
    prefix="/deadlines",
    tags=["deadlines"],
)


def _serialize_deadline(deadline: Deadline) -> DeadlineOut:
    """Convert ORM Deadline to response model."""
    return DeadlineOut(
        id=deadline.id,
        law_firm_id=deadline.law_firm_id,
        matter_id=deadline.matter_id,
        created_by=deadline.created_by,
        title=deadline.title,
        description=deadline.description,
        due_date=deadline.due_date.isoformat(),
        priority=deadline.priority.value,
        status=deadline.status.value,
        notification_sent_at=deadline.notification_sent_at.isoformat() if deadline.notification_sent_at else None,
        acknowledged_at=deadline.acknowledged_at.isoformat() if deadline.acknowledged_at else None,
        completed_at=deadline.completed_at.isoformat() if deadline.completed_at else None,
        created_at=deadline.created_at.isoformat(),
        updated_at=deadline.updated_at.isoformat(),
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/", response_model=DeadlineOut, status_code=status.HTTP_201_CREATED)
async def create_deadline(
    request: DeadlineCreate,
    db: AsyncSession = Depends(get_tenant_session),
    current_user: UserContext = Depends(get_current_user),
):
    """Create a new deadline for the current law firm."""
    service = DeadlineService(db)
    deadline = await service.create_deadline(
        law_firm_id=current_user.law_firm_id,
        created_by=current_user.user_id,
        title=request.title,
        description=request.description,
        due_date=request.due_date,
        priority=request.priority,
        matter_id=request.matter_id,
    )
    return _serialize_deadline(deadline)


@router.get("/", response_model=List[DeadlineOut])
async def list_deadlines(
    matter_id: Optional[uuid.UUID] = None,
    status: Optional[DeadlineStatus] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_tenant_session),
    current_user: UserContext = Depends(get_current_user),
):
    """List deadlines for the current law firm with optional filters."""
    service = DeadlineService(db)
    deadlines = await service.list_deadlines(
        law_firm_id=current_user.law_firm_id,
        matter_id=matter_id,
        status=status,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        offset=offset,
    )
    return [_serialize_deadline(d) for d in deadlines]


@router.get("/overdue", response_model=List[DeadlineOut])
async def get_overdue(
    db: AsyncSession = Depends(get_tenant_session),
    current_user: UserContext = Depends(get_current_user),
):
    """Return all overdue and uncompleted deadlines."""
    service = DeadlineService(db)
    deadlines = await service.get_overdue(current_user.law_firm_id)
    return [_serialize_deadline(d) for d in deadlines]


@router.get("/upcoming", response_model=List[DeadlineOut])
async def get_upcoming(
    days: int = 7,
    db: AsyncSession = Depends(get_tenant_session),
    current_user: UserContext = Depends(get_current_user),
):
    """Return deadlines due in the next N days."""
    service = DeadlineService(db)
    deadlines = await service.get_upcoming(current_user.law_firm_id, days=days)
    return [_serialize_deadline(d) for d in deadlines]


@router.post("/{deadline_id}/acknowledge", response_model=DeadlineOut)
async def acknowledge_deadline(
    deadline_id: uuid.UUID,
    db: AsyncSession = Depends(get_tenant_session),
    current_user: UserContext = Depends(get_current_user),
):
    """Acknowledge a deadline."""
    service = DeadlineService(db)
    deadline = await service.acknowledge(deadline_id, current_user.user_id)
    if not deadline:
        raise HTTPException(status_code=404, detail="Deadline not found")
    return _serialize_deadline(deadline)


@router.post("/{deadline_id}/complete", response_model=DeadlineOut)
async def complete_deadline(
    deadline_id: uuid.UUID,
    db: AsyncSession = Depends(get_tenant_session),
    current_user: UserContext = Depends(get_current_user),
):
    """Mark a deadline as completed."""
    service = DeadlineService(db)
    deadline = await service.complete(deadline_id)
    if not deadline:
        raise HTTPException(status_code=404, detail="Deadline not found")
    return _serialize_deadline(deadline)
