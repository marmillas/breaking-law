"""
Dramatiq background worker for retention policy enforcement.

Runs daily to purge documents that have passed their deletion date.

.. warning::
    DEPLOYMENT RISK: Dramatiq workers require a running Redis broker.
    Required: Redis instance reachable at the configured REDIS_URL.
    Impact if missing: Expired documents will not be purged automatically;
    retention policies will not be enforced until a worker process is started.
"""

import asyncio
import uuid

import dramatiq

from breaking_law.shared.config import Config
from breaking_law.shared.database import Database
from breaking_law.shared.audit import AuditService
from breaking_law.retention.service import RetentionService


@dramatiq.actor(max_retries=3, time_limit=300000)
def purge_expired_documents() -> None:
    """
    Purge all documents that have passed their deletion date.

    This actor should be triggered by an external scheduler (e.g. cron
    or periodiq) on a daily basis.
    """
    asyncio.run(_purge_async())


async def _purge_async() -> None:
    """Async implementation of expired document purge."""
    cfg = Config()
    db_url = cfg.DATABASE_URL or "postgresql+asyncpg://localhost:5432/legal_db"
    db = Database(database_url=db_url, echo=False)
    session = db.session_factory()

    try:
        audit = AuditService(db_session=session)
        retention_service = RetentionService(session, audit)
        purged_count = await retention_service.purge_expired()

        # Log execution to audit trail
        await audit.log_event(
            law_firm_id=uuid.UUID("00000000-0000-0000-0000-000000000000"),
            actor_user_id=None,
            resource_type="retention_worker",
            resource_id=uuid.UUID("00000000-0000-0000-0000-000000000000"),
            action="purge_executed",
            metadata={"purged_count": purged_count},
        )
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()
        await db.close()
