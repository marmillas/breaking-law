"""
Notification service for the legal platform.

Manages user notifications, unread tracking, and urgent action inbox.
All operations are tenant-scoped.
"""

import uuid
from typing import Optional, List

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from breaking_law.infra.models import Notification, DeadlinePriority


class NotificationService:
    """Business logic for notification management."""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def create_notification(
        self,
        law_firm_id: uuid.UUID,
        user_id: uuid.UUID,
        title: str,
        message: str,
        priority: DeadlinePriority = DeadlinePriority.medium,
        deadline_id: Optional[uuid.UUID] = None,
    ) -> Notification:
        """Create a new notification for a user."""
        notification = Notification(
            law_firm_id=law_firm_id,
            user_id=user_id,
            deadline_id=deadline_id,
            title=title,
            message=message,
            priority=priority,
            read=False,
        )
        self.db.add(notification)
        await self.db.flush()
        await self.db.refresh(notification)
        return notification

    async def list_unread(
        self,
        user_id: uuid.UUID,
        law_firm_id: uuid.UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Notification]:
        """List unread notifications ordered by priority."""
        priority_order = {
            DeadlinePriority.critical: 0,
            DeadlinePriority.high: 1,
            DeadlinePriority.medium: 2,
            DeadlinePriority.low: 3,
        }
        result = await self.db.execute(
            select(Notification).where(
                Notification.user_id == user_id,
                Notification.law_firm_id == law_firm_id,
                Notification.read.is_(False),
            ).order_by(
                Notification.priority.asc(),
                Notification.created_at.desc(),
            ).limit(limit).offset(offset)
        )
        notifications = list(result.scalars().all())
        # Re-sort to ensure critical/high come first regardless of enum ordering
        notifications.sort(key=lambda n: (priority_order.get(n.priority, 2), -n.created_at.timestamp()))
        return notifications

    async def mark_read(self, notification_id: uuid.UUID, user_id: uuid.UUID) -> Optional[Notification]:
        """Mark a single notification as read."""
        result = await self.db.execute(
            select(Notification).where(
                Notification.id == notification_id,
                Notification.user_id == user_id,
            )
        )
        notification = result.scalar_one_or_none()
        if not notification:
            return None
        notification.read = True
        await self.db.flush()
        await self.db.refresh(notification)
        return notification

    async def mark_all_read(self, user_id: uuid.UUID, law_firm_id: uuid.UUID) -> int:
        """Mark all unread notifications as read for a user. Returns count updated."""
        result = await self.db.execute(
            select(Notification).where(
                Notification.user_id == user_id,
                Notification.law_firm_id == law_firm_id,
                Notification.read.is_(False),
            )
        )
        notifications = result.scalars().all()
        count = 0
        for notification in notifications:
            notification.read = True
            count += 1
        await self.db.flush()
        return count

    async def get_urgent_actions(
        self,
        user_id: uuid.UUID,
        law_firm_id: uuid.UUID,
        limit: int = 50,
    ) -> List[Notification]:
        """Return high and critical unread notifications for the urgent actions inbox."""
        result = await self.db.execute(
            select(Notification).where(
                Notification.user_id == user_id,
                Notification.law_firm_id == law_firm_id,
                Notification.read.is_(False),
                Notification.priority.in_([DeadlinePriority.high, DeadlinePriority.critical]),
            ).order_by(
                Notification.priority.asc(),
                Notification.created_at.desc(),
            ).limit(limit)
        )
        return list(result.scalars().all())
