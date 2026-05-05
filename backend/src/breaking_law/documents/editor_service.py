"""
Document editor service for the legal platform.

Manages browser-based editor drafts with autosave, citation insertion,
and promotion to real Documents. All operations are tenant-scoped.
"""

import uuid
from datetime import datetime, UTC
from typing import Optional, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from breaking_law.infra.models import (
    EditorDraft,
    EditorDraftStatus,
    Document,
    DocumentVersion,
    ParserStatus,
)


class EditorService:
    """Business logic for document editor drafts and autosave."""

    def __init__(self, db_session: AsyncSession):
        self.db = db_session

    async def create_draft(
        self,
        user_id: uuid.UUID,
        law_firm_id: uuid.UUID,
        title: str,
        matter_id: Optional[uuid.UUID] = None,
    ) -> EditorDraft:
        """Create a new empty editor draft."""
        draft = EditorDraft(
            law_firm_id=law_firm_id,
            user_id=user_id,
            matter_id=matter_id,
            title=title,
            content=[],
            status=EditorDraftStatus.draft,
        )
        self.db.add(draft)
        await self.db.flush()
        await self.db.refresh(draft)
        return draft

    async def autosave(
        self,
        draft_id: uuid.UUID,
        content_json: list,
    ) -> Optional[EditorDraft]:
        """Save content to a draft and update the autosave timestamp."""
        result = await self.db.execute(
            select(EditorDraft).where(EditorDraft.id == draft_id)
        )
        draft = result.scalar_one_or_none()
        if not draft:
            return None
        draft.content = content_json
        draft.last_autosaved_at = datetime.now(UTC)
        await self.db.flush()
        await self.db.refresh(draft)
        return draft

    async def get_draft(self, draft_id: uuid.UUID) -> Optional[EditorDraft]:
        """Retrieve a draft by ID."""
        result = await self.db.execute(
            select(EditorDraft).where(EditorDraft.id == draft_id)
        )
        return result.scalar_one_or_none()

    async def list_drafts(
        self,
        user_id: uuid.UUID,
        law_firm_id: uuid.UUID,
        status: Optional[EditorDraftStatus] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[EditorDraft]:
        """List drafts for a user, scoped to tenant."""
        query = select(EditorDraft).where(
            EditorDraft.user_id == user_id,
            EditorDraft.law_firm_id == law_firm_id,
        )
        if status:
            query = query.where(EditorDraft.status == status)
        query = query.order_by(EditorDraft.updated_at.desc()).limit(limit).offset(offset)
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def save_as_document(
        self,
        draft_id: uuid.UUID,
        owner_user_id: uuid.UUID,
    ) -> Optional[Document]:
        """
        Promote a draft to a real Document with a first version.

        Creates a Document record and an initial DocumentVersion
        with the draft content serialized as extracted text.
        """
        result = await self.db.execute(
            select(EditorDraft).where(EditorDraft.id == draft_id)
        )
        draft = result.scalar_one_or_none()
        if not draft:
            return None

        # Create the Document
        document = Document(
            law_firm_id=draft.law_firm_id,
            matter_id=draft.matter_id,
            owner_user_id=owner_user_id,
            title=draft.title,
        )
        self.db.add(document)
        await self.db.flush()

        # Create initial version with draft content as extracted text
        version = DocumentVersion(
            document_id=document.id,
            version_number=1,
            storage_key="",  # No file blob for editor-created documents yet
            sha256_hash="",
            mime_type="application/json",
            size_bytes=0,
            parser_status=ParserStatus.completed,
            extracted_text=str(draft.content) if draft.content else "",
            created_by=owner_user_id,
        )
        self.db.add(version)

        # Link draft to document and mark as saved
        draft.document_id = document.id
        draft.status = EditorDraftStatus.saved
        await self.db.flush()
        await self.db.refresh(document)
        return document

    async def insert_citation(
        self,
        draft_id: uuid.UUID,
        citation_block: dict,
    ) -> Optional[EditorDraft]:
        """
        Insert a citation block into the draft content.

        If the citation block does not have an 'id', one is generated.
        The block is appended to the end of the content array.
        """
        result = await self.db.execute(
            select(EditorDraft).where(EditorDraft.id == draft_id)
        )
        draft = result.scalar_one_or_none()
        if not draft:
            return None

        content = list(draft.content or [])

        if "id" not in citation_block:
            citation_block["id"] = str(uuid.uuid4())

        content.append(citation_block)
        draft.content = content
        draft.last_autosaved_at = datetime.now(UTC)
        await self.db.flush()
        await self.db.refresh(draft)
        return draft
