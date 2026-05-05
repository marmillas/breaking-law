"""
Editor router for the legal platform.

Provides endpoints for browser-based document editor drafts,
autosave, and promotion to real documents. All endpoints require
authentication and are tenant-scoped.
"""

import uuid
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from breaking_law.api.deps import (
    get_tenant_session,
    get_current_user,
    UserContext,
)
from breaking_law.documents.editor_service import EditorService
from breaking_law.infra.models import EditorDraft, EditorDraftStatus
from breaking_law.domain.schemas.documents import (
    CreateDraftRequest,
    AutosaveRequest,
    InsertCitationRequest,
    DraftOut,
    EditorDocumentOut,
)

router = APIRouter(
    prefix="/editor",
    tags=["editor"],
)


def _serialize_draft(draft: EditorDraft) -> DraftOut:
    """Convert ORM EditorDraft to response model."""
    return DraftOut(
        id=draft.id,
        law_firm_id=draft.law_firm_id,
        document_id=draft.document_id,
        user_id=draft.user_id,
        matter_id=draft.matter_id,
        title=draft.title,
        content=draft.content,
        status=draft.status.value,
        last_autosaved_at=draft.last_autosaved_at.isoformat() if draft.last_autosaved_at else None,
        created_at=draft.created_at.isoformat(),
        updated_at=draft.updated_at.isoformat(),
    )


def _serialize_document(document) -> EditorDocumentOut:
    """Convert ORM Document to response model."""
    return EditorDocumentOut(
        id=document.id,
        law_firm_id=document.law_firm_id,
        matter_id=document.matter_id,
        owner_user_id=document.owner_user_id,
        title=document.title,
        classification=document.classification,
        is_confidential=document.is_confidential,
        created_at=document.created_at.isoformat(),
        updated_at=document.updated_at.isoformat(),
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/drafts", response_model=DraftOut, status_code=status.HTTP_201_CREATED)
async def create_draft(
    request: CreateDraftRequest,
    db: AsyncSession = Depends(get_tenant_session),
    current_user: UserContext = Depends(get_current_user),
):
    """Create a new editor draft for the current user."""
    service = EditorService(db)
    draft = await service.create_draft(
        user_id=current_user.user_id,
        law_firm_id=current_user.law_firm_id,
        title=request.title,
        matter_id=request.matter_id,
    )
    return _serialize_draft(draft)


@router.put("/drafts/{draft_id}/autosave", response_model=DraftOut)
async def autosave_draft(
    draft_id: uuid.UUID,
    request: AutosaveRequest,
    db: AsyncSession = Depends(get_tenant_session),
    current_user: UserContext = Depends(get_current_user),
):
    """Autosave draft content. Lightweight and fast."""
    service = EditorService(db)
    draft = await service.autosave(draft_id, request.content)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    return _serialize_draft(draft)


@router.get("/drafts/{draft_id}", response_model=DraftOut)
async def get_draft(
    draft_id: uuid.UUID,
    db: AsyncSession = Depends(get_tenant_session),
    current_user: UserContext = Depends(get_current_user),
):
    """Retrieve a draft by ID."""
    service = EditorService(db)
    draft = await service.get_draft(draft_id)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    if draft.law_firm_id != current_user.law_firm_id:
        raise HTTPException(status_code=404, detail="Draft not found")
    return _serialize_draft(draft)


@router.get("/drafts", response_model=List[DraftOut])
async def list_drafts(
    status: Optional[EditorDraftStatus] = None,
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_tenant_session),
    current_user: UserContext = Depends(get_current_user),
):
    """List drafts for the current user."""
    service = EditorService(db)
    drafts = await service.list_drafts(
        user_id=current_user.user_id,
        law_firm_id=current_user.law_firm_id,
        status=status,
        limit=limit,
        offset=offset,
    )
    return [_serialize_draft(d) for d in drafts]


@router.post("/drafts/{draft_id}/save-as-document", response_model=EditorDocumentOut)
async def save_as_document(
    draft_id: uuid.UUID,
    db: AsyncSession = Depends(get_tenant_session),
    current_user: UserContext = Depends(get_current_user),
):
    """Promote a draft to a real Document."""
    service = EditorService(db)
    document = await service.save_as_document(draft_id, current_user.user_id)
    if not document:
        raise HTTPException(status_code=404, detail="Draft not found")
    return _serialize_document(document)


@router.post("/drafts/{draft_id}/insert-citation", response_model=DraftOut)
async def insert_citation(
    draft_id: uuid.UUID,
    request: InsertCitationRequest,
    db: AsyncSession = Depends(get_tenant_session),
    current_user: UserContext = Depends(get_current_user),
):
    """Insert a citation block into a draft."""
    service = EditorService(db)
    draft = await service.insert_citation(draft_id, request.citation_block)
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    return _serialize_draft(draft)
