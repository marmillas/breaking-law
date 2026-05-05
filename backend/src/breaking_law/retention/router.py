"""
Retention router for the legal platform.

Handles retention policy assignment and deletion scheduling for documents.
Requires owner role. All endpoints require authentication and are tenant-scoped.
"""

import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from breaking_law.api.deps import (
    get_tenant_session,
    get_current_user,
    UserContext,
    require_role,
)
from breaking_law.retention.service import RetentionService
from breaking_law.shared.audit import AuditService
from breaking_law.domain.schemas.documents import (
    RetentionPolicyRequest,
    RetentionStatusOut,
    ScheduleDeletionRequest,
    MessageOut,
)

router = APIRouter(
    prefix="/retention",
    tags=["retention"],
)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/{document_id}/policy",
    response_model=RetentionStatusOut,
    dependencies=[Depends(require_role(["owner"]))],
)
async def set_retention_policy(
    document_id: uuid.UUID,
    request: RetentionPolicyRequest,
    db: AsyncSession = Depends(get_tenant_session),
    current_user: UserContext = Depends(get_current_user),
):
    """Apply a retention policy to a document. Requires owner role."""
    audit = AuditService(db_session=db)
    service = RetentionService(db, audit)
    document = await service.apply_retention_policy(
        document_id=document_id,
        policy=request.policy,
        law_firm_id=current_user.law_firm_id,
        actor_user_id=current_user.user_id,
    )
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return RetentionStatusOut(
        document_id=str(document.id),
        retention_policy=document.retention_policy,
        deletion_date=document.deletion_date.isoformat() if document.deletion_date else None,
        deleted_at=document.deleted_at.isoformat() if document.deleted_at else None,
    )


@router.post(
    "/{document_id}/schedule-deletion",
    response_model=RetentionStatusOut,
    dependencies=[Depends(require_role(["owner"]))],
)
async def schedule_deletion(
    document_id: uuid.UUID,
    request: ScheduleDeletionRequest,
    db: AsyncSession = Depends(get_tenant_session),
    current_user: UserContext = Depends(get_current_user),
):
    """Schedule a document for deletion on a specific date. Requires owner role."""
    audit = AuditService(db_session=db)
    service = RetentionService(db, audit)
    document = await service.schedule_deletion(
        document_id=document_id,
        deletion_date=request.deletion_date,
        law_firm_id=current_user.law_firm_id,
        actor_user_id=current_user.user_id,
    )
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return RetentionStatusOut(
        document_id=str(document.id),
        retention_policy=document.retention_policy,
        deletion_date=document.deletion_date.isoformat() if document.deletion_date else None,
        deleted_at=document.deleted_at.isoformat() if document.deleted_at else None,
    )
