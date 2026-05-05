"""
Dramatiq background worker for deadline monitoring and notification creation.

Scans for upcoming and overdue deadlines and creates notifications for users.

.. warning::
    DEPLOYMENT RISK: Dramatiq periodic scheduler requires a running Redis broker
    and a separate worker process. For periodic execution, configure an external
    cron job or install `periodiq` and use `@dramatiq.periodic` decorators.
    Required: Redis instance reachable at the configured REDIS_URL.
    Impact if missing: Deadline notifications will not be created automatically.
"""

import asyncio
import uuid
from datetime import datetime, timedelta, UTC
from typing import List

import dramatiq

from breaking_law.shared.config import Config
from breaking_law.shared.database import Database
from breaking_law.infra.models import Deadline, DeadlineStatus, DeadlinePriority, Notification
from sqlalchemy import select


@dramatiq.actor(max_retries=3, time_limit=60000)
def scan_deadlines(law_firm_id: str) -> None:
    """
    Scan deadlines for a law firm and create notifications.

    Args:
        law_firm_id: Tenant ID to scan.
    """
    asyncio.run(_scan_deadlines_async(law_firm_id))


async def _scan_deadlines_async(law_firm_id: str) -> None:
    """Async implementation of deadline scanning."""
    cfg = Config()
    db_url = cfg.DATABASE_URL or "postgresql+asyncpg://localhost:5432/legal_db"
    db = Database(database_url=db_url, echo=False)
    session = db.session_factory()

    try:
        now = datetime.now(UTC)
        upcoming_threshold = now + timedelta(hours=48)

        # Find upcoming deadlines (due in < 48h) that are not completed
        upcoming_result = await session.execute(
            select(Deadline).where(
                Deadline.law_firm_id == uuid.UUID(law_firm_id),
                Deadline.due_date <= upcoming_threshold,
                Deadline.due_date >= now,
                Deadline.status.notin_([DeadlineStatus.completed]),
                Deadline.notification_sent_at.is_(None),
            )
        )
        upcoming_deadlines = upcoming_result.scalars().all()

        for deadline in upcoming_deadlines:
            notification = Notification(
                law_firm_id=deadline.law_firm_id,
                user_id=deadline.created_by,
                deadline_id=deadline.id,
                title=f"Upcoming deadline: {deadline.title}",
                message=f"Deadline '{deadline.title}' is due on {deadline.due_date.isoformat()}",
                priority=deadline.priority,
                read=False,
            )
            session.add(notification)
            deadline.notification_sent_at = now

        # Find overdue deadlines and escalate
        overdue_result = await session.execute(
            select(Deadline).where(
                Deadline.law_firm_id == uuid.UUID(law_firm_id),
                Deadline.due_date < now,
                Deadline.status.notin_([DeadlineStatus.completed, DeadlineStatus.overdue]),
            )
        )
        overdue_deadlines = overdue_result.scalars().all()

        for deadline in overdue_deadlines:
            deadline.status = DeadlineStatus.overdue
            notification = Notification(
                law_firm_id=deadline.law_firm_id,
                user_id=deadline.created_by,
                deadline_id=deadline.id,
                title=f"OVERDUE: {deadline.title}",
                message=f"Deadline '{deadline.title}' was due on {deadline.due_date.isoformat()} and is now overdue.",
                priority=DeadlinePriority.critical,
                read=False,
            )
            session.add(notification)

        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()
        await db.close()
