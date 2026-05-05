"""
Dramatiq background worker for document export.

Handles asynchronous export of document drafts to DOCX/PDF and tracks
job status via DocumentExportJob records.

.. warning::
   DEPLOYMENT RISK: Dramatiq workers require a running Redis broker.
   Required: Redis instance reachable at the configured REDIS_URL.
   Impact if missing: Enqueued export jobs will never execute; status will
   remain 'pending' indefinitely until a worker process is started.
"""

import asyncio
import uuid
from typing import Optional

import dramatiq

from breaking_law.shared.config import Config
from breaking_law.shared.database import Database
from breaking_law.documents.storage import Storage
from breaking_law.shared.audit import AuditService
from breaking_law.documents.export import ExportService
from breaking_law.infra.models import DocumentExportJob
from sqlalchemy import select


@dramatiq.actor(max_retries=3, time_limit=300000)
def export_document_version(
    job_id: str,
    version_id: str,
    law_firm_id: str,
    draft_json: dict,
    actor_user_id: Optional[str] = None,
) -> None:
    """
    Dramatiq actor entrypoint for document export.

    Args:
        job_id: UUID of the DocumentExportJob tracking record.
        version_id: UUID of the DocumentVersion to export.
        law_firm_id: Tenant ID for isolation.
        draft_json: Structured draft content dict.
        actor_user_id: Optional user ID that triggered the export.
    """
    asyncio.run(_export_async(job_id, version_id, law_firm_id, draft_json, actor_user_id))


async def _export_async(
    job_id: str,
    version_id: str,
    law_firm_id: str,
    draft_json: dict,
    actor_user_id: Optional[str],
) -> None:
    """Async implementation of document export."""
    cfg = Config()
    db_url = cfg.DATABASE_URL or "postgresql+asyncpg://localhost:5432/legal_db"
    db = Database(database_url=db_url, echo=False)
    session = db.session_factory()
    job: Optional[DocumentExportJob] = None

    try:
        result = await session.execute(
            select(DocumentExportJob).where(DocumentExportJob.id == uuid.UUID(job_id))
        )
        job = result.scalar_one_or_none()
        if job:
            job.status = "processing"
            await session.flush()

        storage = Storage(
            bucket_name=cfg.S3_BUCKET,
            endpoint_url=cfg.MINIO_ENDPOINT if cfg.STORAGE_PROVIDER == "minio" else cfg.S3_ENDPOINT,
            region_name=cfg.S3_REGION,
            access_key=cfg.STORAGE_ACCESS_KEY,
            secret_key=cfg.STORAGE_SECRET_KEY,
            sse_enabled=True,
        )
        export_service = ExportService(
            storage=storage,
            libreoffice_path=cfg.LIBREOFFICE_PATH,
        )

        result_data = await export_service.export_document(
            draft=draft_json,
            version_id=uuid.UUID(version_id),
            law_firm_id=uuid.UUID(law_firm_id),
        )

        if job:
            job.status = "completed"
            job.docx_storage_key = result_data.get("docx_storage_key")
            job.pdf_storage_key = result_data.get("pdf_storage_key")
            job.docx_url = result_data.get("docx_url")
            job.pdf_url = result_data.get("pdf_url")
            job.result = {"warning": result_data.get("warning")}

        await session.commit()
    except Exception as exc:
        await session.rollback()
        if job:
            job.status = "failed"
            job.error_message = str(exc)
            await session.commit()
        raise
    finally:
        await session.close()
        await db.close()
