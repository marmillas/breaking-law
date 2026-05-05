"""
Dramatiq background worker for document parsing and indexing.

Enqueues document processing off the request path. After parsing,
the worker chunks the extracted text, generates embeddings, and
stores chunks for future semantic and full-text search.

.. warning::
   DEPLOYMENT RISK: Dramatiq workers require a running Redis broker, and enqueued jobs will not execute until a worker process is started (`dramatiq breaking_law.documents.worker_parse`).
   Required: Redis broker reachable at the configured REDIS_URL and a worker process running.
   Impact if missing: Background parse jobs remain in 'pending' state indefinitely and document text will never be extracted or indexed.
"""

import asyncio
import uuid
from typing import Optional

import dramatiq

from breaking_law.shared.config import Config
from breaking_law.shared.database import Database
from breaking_law.documents.storage import Storage
from breaking_law.shared.audit import AuditService
from breaking_law.documents.parsing import DocumentParser
from breaking_law.infra.models import DocumentParseJob, DocumentChunk, ParserStatus
from breaking_law.shared.embeddings import chunk_text, get_embedding_client, FullTextSearch
from breaking_law.documents.service import DocumentService
from sqlalchemy import select


@dramatiq.actor(max_retries=3, time_limit=300000)
def process_document_version(
    job_id: str,
    version_id: str,
    law_firm_id: str,
    actor_user_id: Optional[str] = None,
) -> None:
    """
    Dramatiq actor entrypoint.

    Args:
        job_id: UUID of the DocumentParseJob tracking record.
        version_id: UUID of the DocumentVersion to process.
        law_firm_id: Tenant ID for isolation.
        actor_user_id: Optional user ID that triggered the job.
    """
    asyncio.run(_process_async(job_id, version_id, law_firm_id, actor_user_id))


async def _process_async(
    job_id: str,
    version_id: str,
    law_firm_id: str,
    actor_user_id: Optional[str],
) -> None:
    """Async implementation of document processing and indexing."""
    cfg = Config()
    db_url = cfg.DATABASE_URL or "postgresql+asyncpg://localhost:5432/legal_db"
    db = Database(database_url=db_url, echo=False)
    session = db.session_factory()
    job: Optional[DocumentParseJob] = None

    try:
        result = await session.execute(
            select(DocumentParseJob).where(DocumentParseJob.id == uuid.UUID(job_id))
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
        audit = AuditService(db_session=session)
        parser = DocumentParser(
            ocr_enabled=cfg.OCR_ENABLED,
            tesseract_path=cfg.TESSERACT_PATH,
        )
        service = DocumentService(session, storage, audit, parser)

        version = await service.process_version(
            version_id=uuid.UUID(version_id),
            law_firm_id=uuid.UUID(law_firm_id),
            actor_user_id=uuid.UUID(actor_user_id) if actor_user_id else None,
        )

        if version.parser_status == ParserStatus.completed and version.extracted_text:
            # Chunk and embed
            chunks = chunk_text(version.extracted_text)
            embedding_client = get_embedding_client(cfg)

            try:
                embeddings = await embedding_client.embed(chunks)
            except Exception as embed_exc:
                # Embedding failure — mark as failed gracefully
                version.parser_status = ParserStatus.failed
                if job:
                    job.status = "failed"
                    job.error_message = f"Embedding failed: {embed_exc}"
                await session.commit()
                raise

            for idx, text in enumerate(chunks):
                embedding = embeddings[idx]
                # Build tsvector SQL for PostgreSQL; SQLite stores None
                tsvector_sql = FullTextSearch.build_tsvector(":text")
                chunk = DocumentChunk(
                    version_id=uuid.UUID(version_id),
                    law_firm_id=uuid.UUID(law_firm_id),
                    chunk_index=idx,
                    text_content=text,
                    embedding=embedding,
                    search_vector=None,  # Trigger populates this on PostgreSQL
                )
                session.add(chunk)

            # Update status to indexed
            version.parser_status = ParserStatus.indexed

            if job:
                job.status = "completed"
                job.result = {"chunks_created": len(chunks)}
        else:
            if job:
                job.status = "failed"
                job.error_message = "Parsing failed or produced no text"

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
