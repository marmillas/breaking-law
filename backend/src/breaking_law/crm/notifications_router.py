"""
Notifications router for the legal platform.

Handles unread notification listing, urgent actions inbox,
and marking notifications as read. All endpoints require authentication
and are tenant-scoped.
"""

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from breaking_law.api.deps import (
    get_tenant_session,
    get_current_user,
    UserContext,
)
from breaking_law.crm.service import NotificationService
from breaking_law.infra.models import Notification, DeadlinePriority
from breaking_law.domain.schemas.crm import NotificationOut, MarkReadResponse, MarkAllReadResponse

router = APIRouter(
    prefix="/notifications",
    tags=["notifications"],
)


def _serialize_notification(notification: Notification) -> NotificationOut:
    """Convert ORM Notification to response model."""
    return NotificationOut(
        id=notification.id,
        law_firm_id=notification.law_firm_id,
        user_id=notification.user_id,
        deadline_id=notification.deadline_id,
        title=notification.title,
        message=notification.message,
        priority=notification.priority.value,
        read=notification.read,
        created_at=notification.created_at.isoformat(),
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/", response_model=List[NotificationOut])
async def list_unread(
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_tenant_session),
    current_user: UserContext = Depends(get_current_user),
):
    """List unread notifications for the current user."""
    service = NotificationService(db)
    notifications = await service.list_unread(
        user_id=current_user.user_id,
        law_firm_id=current_user.law_firm_id,
        limit=limit,
        offset=offset,
    )
    return [_serialize_notification(n) for n in notifications]


@router.get("/urgent", response_model=List[NotificationOut])
async def get_urgent_actions(
    limit: int = 50,
    db: AsyncSession = Depends(get_tenant_session),
    current_user: UserContext = Depends(get_current_user),
):
    """Return high and critical unread notifications for the urgent actions inbox."""
    service = NotificationService(db)
    notifications = await service.get_urgent_actions(
        user_id=current_user.user_id,
        law_firm_id=current_user.law_firm_id,
        limit=limit,
    )
    return [_serialize_notification(n) for n in notifications]


@router.post("/{notification_id}/read", response_model=NotificationOut)
async def mark_read(
    notification_id: uuid.UUID,
    db: AsyncSession = Depends(get_tenant_session),
    current_user: UserContext = Depends(get_current_user),
):
    """Mark a single notification as read."""
    service = NotificationService(db)
    notification = await service.mark_read(notification_id, current_user.user_id)
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")
    return _serialize_notification(notification)


@router.post("/read-all", response_model=MarkAllReadResponse)
async def mark_all_read(
    db: AsyncSession = Depends(get_tenant_session),
    current_user: UserContext = Depends(get_current_user),
):
    """Mark all unread notifications as read for the current user."""
    service = NotificationService(db)
    count = await service.mark_all_read(
        user_id=current_user.user_id,
        law_firm_id=current_user.law_firm_id,
    )
    return MarkAllReadResponse(marked_count=count)
