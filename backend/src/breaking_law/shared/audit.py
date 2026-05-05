"""
Audit logging infrastructure for the legal platform.

All audit events are written synchronously before a response is returned.
The audit log is append-only and immutable.
"""

import uuid
import hashlib
from datetime import datetime, UTC
from typing import Optional, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession

from breaking_law.infra.models import AuditEvent


class AuditService:
    """Service for creating and querying immutable audit events."""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    @staticmethod
    def compute_hash(data: bytes) -> str:
        """Compute SHA-256 hash of raw data for integrity verification."""
        return hashlib.sha256(data).hexdigest()

    async def log_event(
        self,
        law_firm_id: uuid.UUID,
        resource_type: str,
        resource_id: uuid.UUID,
        action: str,
        actor_user_id: Optional[uuid.UUID] = None,
        input_data: Optional[bytes] = None,
        output_data: Optional[bytes] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AuditEvent:
        """
        Log an immutable audit event.

        This method is synchronous in intent (called before response return)
        but uses async DB operations. Callers should await it and ensure
        the transaction commits before responding.
        """
        event = AuditEvent(
            law_firm_id=law_firm_id,
            actor_user_id=actor_user_id,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            input_hash=self.compute_hash(input_data) if input_data else None,
            output_hash=self.compute_hash(output_data) if output_data else None,
            event_metadata=metadata or {},
            timestamp=datetime.now(UTC),
        )
        self.db.add(event)
        await self.db.flush()
        return event

    async def log_document_upload(
        self,
        law_firm_id: uuid.UUID,
        document_id: uuid.UUID,
        version_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        filename: str,
        size_bytes: int,
        mime_type: str,
    ) -> AuditEvent:
        """Convenience method for logging document uploads."""
        return await self.log_event(
            law_firm_id=law_firm_id,
            resource_type="document",
            resource_id=document_id,
            action="upload",
            actor_user_id=actor_user_id,
            metadata={
                "version_id": str(version_id),
                "filename": filename,
                "size_bytes": size_bytes,
                "mime_type": mime_type,
            },
        )

    async def log_document_read(
        self,
        law_firm_id: uuid.UUID,
        document_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        version_id: Optional[uuid.UUID] = None,
    ) -> AuditEvent:
        """Convenience method for logging document reads/downloads."""
        metadata = {}
        if version_id:
            metadata["version_id"] = str(version_id)
        return await self.log_event(
            law_firm_id=law_firm_id,
            resource_type="document",
            resource_id=document_id,
            action="read",
            actor_user_id=actor_user_id,
            metadata=metadata,
        )

    async def log_document_delete(
        self,
        law_firm_id: uuid.UUID,
        document_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        soft: bool = True,
    ) -> AuditEvent:
        """Convenience method for logging document deletions."""
        return await self.log_event(
            law_firm_id=law_firm_id,
            resource_type="document",
            resource_id=document_id,
            action="soft_delete" if soft else "hard_delete",
            actor_user_id=actor_user_id,
        )

    async def log_document_parse(
        self,
        law_firm_id: uuid.UUID,
        document_id: uuid.UUID,
        version_id: uuid.UUID,
        actor_user_id: Optional[uuid.UUID],
        status: str,
        error_message: Optional[str] = None,
    ) -> AuditEvent:
        """Convenience method for logging document parsing results."""
        metadata = {
            "version_id": str(version_id),
            "parser_status": status,
        }
        if error_message:
            metadata["error"] = error_message
        return await self.log_event(
            law_firm_id=law_firm_id,
            resource_type="document",
            resource_id=document_id,
            action="parse",
            actor_user_id=actor_user_id,
            metadata=metadata,
        )
