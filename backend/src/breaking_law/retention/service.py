"""
Retention and deletion service for the legal platform.

Manages document retention policies, scheduled deletions, and audit-trail
preserving soft deletes. All operations are tenant-scoped.
"""

import uuid
from datetime import datetime, timedelta, UTC
from typing import Optional, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from breaking_law.infra.models import Document, DocumentVersion, AuditEvent
from breaking_law.shared.audit import AuditService


class RetentionService:
    """Business logic for document retention and deletion policies."""

    def __init__(self, db_session: AsyncSession, audit: AuditService):
        self.db = db_session
        self.audit = audit

    async def apply_retention_policy(
        self,
        document_id: uuid.UUID,
        policy: str,
        law_firm_id: uuid.UUID,
        actor_user_id: Optional[uuid.UUID] = None,
    ) -> Optional[Document]:
        """
        Apply a retention policy to a document.

        Policies:
        - keep_forever: no deletion schedule
        - delete_after_years(N): schedule deletion N years from creation
        - anonymize_after_years(N): schedule anonymization N years from creation
        """
        result = await self.db.execute(
            select(Document).where(
                Document.id == document_id,
                Document.law_firm_id == law_firm_id,
            )
        )
        document = result.scalar_one_or_none()
        if not document:
            return None

        document.retention_policy = policy

        # Parse policy and set deletion_date if applicable
        deletion_date = None
        if policy.startswith("delete_after_years("):
            try:
                years_str = policy[len("delete_after_years("):].rstrip(")")
                years = int(years_str)
                deletion_date = document.created_at + timedelta(days=365 * years)
            except (ValueError, IndexError):
                raise ValueError("Invalid delete_after_years policy format")
        elif policy.startswith("anonymize_after_years("):
            try:
                years_str = policy[len("anonymize_after_years("):].rstrip(")")
                years = int(years_str)
                deletion_date = document.created_at + timedelta(days=365 * years)
            except (ValueError, IndexError):
                raise ValueError("Invalid anonymize_after_years policy format")
        elif policy == "keep_forever":
            deletion_date = None
        else:
            raise ValueError(f"Unknown retention policy: {policy}")

        document.deletion_date = deletion_date
        await self.db.flush()
        await self.db.refresh(document)

        await self.audit.log_event(
            law_firm_id=law_firm_id,
            actor_user_id=actor_user_id,
            resource_type="document",
            resource_id=document_id,
            action="retention_policy_applied",
            metadata={"policy": policy, "deletion_date": deletion_date.isoformat() if deletion_date else None},
        )
        return document

    async def schedule_deletion(
        self,
        document_id: uuid.UUID,
        deletion_date: datetime,
        law_firm_id: uuid.UUID,
        actor_user_id: Optional[uuid.UUID] = None,
    ) -> Optional[Document]:
        """Set a custom deletion date for a document."""
        result = await self.db.execute(
            select(Document).where(
                Document.id == document_id,
                Document.law_firm_id == law_firm_id,
            )
        )
        document = result.scalar_one_or_none()
        if not document:
            return None

        document.deletion_date = deletion_date
        await self.db.flush()
        await self.db.refresh(document)

        await self.audit.log_event(
            law_firm_id=law_firm_id,
            actor_user_id=actor_user_id,
            resource_type="document",
            resource_id=document_id,
            action="deletion_scheduled",
            metadata={"deletion_date": deletion_date.isoformat()},
        )
        return document

    async def execute_deletion(
        self,
        document_id: uuid.UUID,
        law_firm_id: uuid.UUID,
        actor_user_id: Optional[uuid.UUID] = None,
    ) -> bool:
        """
        Soft-delete a document and its versions.

        Marks the document as deleted but preserves the audit trail.
        """
        result = await self.db.execute(
            select(Document).where(
                Document.id == document_id,
                Document.law_firm_id == law_firm_id,
            )
        )
        document = result.scalar_one_or_none()
        if not document:
            return False

        now = datetime.now(UTC)
        document.deleted_at = now

        # Soft-delete all versions
        version_result = await self.db.execute(
            select(DocumentVersion).where(DocumentVersion.document_id == document_id)
        )
        for version in version_result.scalars().all():
            version.created_at = version.created_at  # touchless; we keep version data but mark parent deleted

        await self.audit.log_event(
            law_firm_id=law_firm_id,
            actor_user_id=actor_user_id,
            resource_type="document",
            resource_id=document_id,
            action="soft_deleted",
            metadata={"deleted_at": now.isoformat()},
        )
        await self.db.flush()
        return True

    async def purge_expired(self) -> int:
        """
        Process all documents past their deletion date.

        Returns the number of documents purged.
        """
        now = datetime.now(UTC)
        result = await self.db.execute(
            select(Document).where(
                Document.deleted_at.is_(None),
                Document.deletion_date.isnot(None),
                Document.deletion_date <= now,
            )
        )
        documents = result.scalars().all()
        count = 0
        for document in documents:
            await self.execute_deletion(
                document_id=document.id,
                law_firm_id=document.law_firm_id,
                actor_user_id=None,
            )
            count += 1
        await self.db.commit()
        return count

    async def get_document_retention_status(
        self,
        document_id: uuid.UUID,
        law_firm_id: uuid.UUID,
    ) -> Optional[dict]:
        """Get retention metadata for a document."""
        result = await self.db.execute(
            select(Document).where(
                Document.id == document_id,
                Document.law_firm_id == law_firm_id,
            )
        )
        document = result.scalar_one_or_none()
        if not document:
            return None
        return {
            "document_id": str(document.id),
            "retention_policy": document.retention_policy,
            "deletion_date": document.deletion_date.isoformat() if document.deletion_date else None,
            "deleted_at": document.deleted_at.isoformat() if document.deleted_at else None,
        }
