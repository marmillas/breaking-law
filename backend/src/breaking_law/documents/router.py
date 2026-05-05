"""
Documents router for the legal platform.

Handles document upload, versioning, retrieval, download, and processing triggers.
All endpoints enforce tenant isolation and granular ACL via law_firm_id in JWT.
"""

import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from breaking_law.api.deps import (
    get_db_session,
    get_tenant_session,
    get_storage,
    get_parser,
    get_current_user,
    get_config,
    UserContext,
)
from breaking_law.documents.service import DocumentService
from breaking_law.documents.worker_parse import process_document_version
from breaking_law.documents.worker_export import export_document_version
from breaking_law.shared.audit import AuditService
from breaking_law.infra.models import Document, DocumentVersion, DocumentParseJob, DocumentExportJob, AccessLevel
from breaking_law.domain.schemas.documents import (
    DocumentVersionOut,
    DocumentOut,
    UploadResponse,
    SignedUrlResponse,
    ProcessResponse,
    ParseJobResponse,
    ExportRequest,
    ExportResponse,
    ExportStatusResponse,
    ACLOut,
    ACLGrantRequest,
)

router = APIRouter(
    prefix="/documents",
    tags=["documents"],
)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _build_document_out(doc: Document) -> DocumentOut:
    """Convert ORM Document to response model."""
    return DocumentOut(
        id=doc.id,
        law_firm_id=doc.law_firm_id,
        matter_id=doc.matter_id,
        owner_user_id=doc.owner_user_id,
        title=doc.title,
        classification=doc.classification,
        is_confidential=doc.is_confidential,
        created_at=doc.created_at.isoformat(),
        updated_at=doc.updated_at.isoformat(),
        versions=[
            DocumentVersionOut(
                id=v.id,
                version_number=v.version_number,
                storage_key=v.storage_key,
                sha256_hash=v.sha256_hash,
                mime_type=v.mime_type,
                size_bytes=v.size_bytes,
                parser_status=v.parser_status.value,
                created_at=v.created_at.isoformat(),
                created_by=v.created_by,
            )
            for v in doc.versions
        ],
    )


def _build_acl_out(acl) -> ACLOut:
    """Convert ORM DocumentACL to response model."""
    return ACLOut(
        id=acl.id,
        document_id=acl.document_id,
        user_id=acl.user_id,
        role=acl.role,
        access_level=acl.access_level.value,
        created_at=acl.created_at.isoformat(),
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/upload", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(..., description="Document file (PDF, DOCX, TXT)"),
    title: str = Form(..., description="Document title"),
    matter_id: Optional[uuid.UUID] = Form(None, description="Associated matter UUID"),
    classification: Optional[str] = Form(None, description="Document classification"),
    is_confidential: bool = Form(False, description="Mark as confidential"),
    db: AsyncSession = Depends(get_tenant_session),
    current_user: UserContext = Depends(get_current_user),
):
    """
    Upload a new document.

    Stores the file in S3-compatible object storage with SSE encryption,
    creates a Document and initial DocumentVersion in PostgreSQL,
    and writes an audit event.
    """
    user_id = current_user.user_id
    law_firm_id = current_user.law_firm_id

    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    # Validate MIME type
    allowed_mimes = {
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/plain",
        "image/png",
        "image/jpeg",
    }
    mime_type = file.content_type or "application/octet-stream"
    if mime_type not in allowed_mimes:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {mime_type}. Allowed: PDF, DOCX, TXT, PNG, JPEG",
        )

    # Read file content
    file_content = await file.read()
    if not file_content:
        raise HTTPException(status_code=400, detail="Empty file")

    # Validate file size
    cfg = get_config()
    max_size_bytes = cfg.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(file_content) > max_size_bytes:
        raise HTTPException(
            status_code=413,
            detail="El archivo excede el límite de 50MB",
        )

    # Build service
    storage = get_storage()
    audit = AuditService(db_session=db)
    parser = get_parser()
    service = DocumentService(db, storage, audit, parser)

    try:
        document = await service.upload_document(
            file_content=file_content,
            filename=file.filename,
            mime_type=mime_type,
            title=title,
            law_firm_id=law_firm_id,
            owner_user_id=user_id,
            matter_id=matter_id,
            classification=classification,
            is_confidential=is_confidential,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    # Ensure versions are loaded
    version = document.versions[0]

    return UploadResponse(
        document_id=document.id,
        version_id=version.id,
        version_number=version.version_number,
        message="Document uploaded successfully",
    )


@router.get("/{document_id}", response_model=DocumentOut)
async def get_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_tenant_session),
    current_user: UserContext = Depends(get_current_user),
):
    """Get a document by ID including its version history."""
    law_firm_id = current_user.law_firm_id

    storage = get_storage()
    audit = AuditService(db_session=db)
    parser = get_parser()
    service = DocumentService(db, storage, audit, parser)

    document = await service.get_document(document_id, law_firm_id, current_user)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    return _build_document_out(document)


@router.get("/", response_model=List[DocumentOut])
async def list_documents(
    matter_id: Optional[uuid.UUID] = None,
    status: Optional[str] = Query(None, description="Filter by latest version parser status"),
    document_type: Optional[str] = Query(None, description="Filter by document classification"),
    client_id: Optional[uuid.UUID] = Query(None, description="Filter by associated matter's client ID"),
    date_from: Optional[str] = Query(None, description="Filter by created_at >= ISO date"),
    date_to: Optional[str] = Query(None, description="Filter by created_at <= ISO date"),
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_tenant_session),
    current_user: UserContext = Depends(get_current_user),
):
    """List documents for the current law firm with optional filters."""
    law_firm_id = current_user.law_firm_id

    date_from_dt: Optional[datetime] = None
    date_to_dt: Optional[datetime] = None
    if date_from:
        try:
            date_from_dt = datetime.fromisoformat(date_from.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date_from format. Use ISO 8601.")
    if date_to:
        try:
            date_to_dt = datetime.fromisoformat(date_to.replace("Z", "+00:00"))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date_to format. Use ISO 8601.")

    storage = get_storage()
    audit = AuditService(db_session=db)
    parser = get_parser()
    service = DocumentService(db, storage, audit, parser)

    documents = await service.list_documents(
        law_firm_id=law_firm_id,
        user=current_user,
        matter_id=matter_id,
        status=status,
        document_type=document_type,
        client_id=client_id,
        date_from=date_from_dt,
        date_to=date_to_dt,
        limit=limit,
        offset=offset,
    )
    return [_build_document_out(doc) for doc in documents]


@router.post("/{document_id}/versions", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def create_version(
    document_id: uuid.UUID,
    file: UploadFile = File(..., description="New version file"),
    db: AsyncSession = Depends(get_tenant_session),
    current_user: UserContext = Depends(get_current_user),
):
    """
    Create a new version of an existing document.

    Uploads the new file blob and increments the version number.
    Requires write access to the document.
    """
    user_id = current_user.user_id
    law_firm_id = current_user.law_firm_id

    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    allowed_mimes = {
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/plain",
        "image/png",
        "image/jpeg",
    }
    mime_type = file.content_type or "application/octet-stream"
    if mime_type not in allowed_mimes:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {mime_type}. Allowed: PDF, DOCX, TXT, PNG, JPEG",
        )

    file_content = await file.read()
    if not file_content:
        raise HTTPException(status_code=400, detail="Empty file")

    # Validate file size
    cfg = get_config()
    max_size_bytes = cfg.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(file_content) > max_size_bytes:
        raise HTTPException(
            status_code=413,
            detail="El archivo excede el límite de 50MB",
        )

    storage = get_storage()
    audit = AuditService(db_session=db)
    parser = get_parser()
    service = DocumentService(db, storage, audit, parser)

    try:
        version = await service.create_version(
            document_id=document_id,
            file_content=file_content,
            filename=file.filename,
            mime_type=mime_type,
            law_firm_id=law_firm_id,
            owner_user_id=user_id,
            user=current_user,
        )
    except ValueError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    return UploadResponse(
        document_id=document_id,
        version_id=version.id,
        version_number=version.version_number,
        message="Version created successfully",
    )


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_tenant_session),
    current_user: UserContext = Depends(get_current_user),
):
    """Delete a document and all its versions. Requires owner access."""
    law_firm_id = current_user.law_firm_id

    storage = get_storage()
    audit = AuditService(db_session=db)
    parser = get_parser()
    service = DocumentService(db, storage, audit, parser)

    deleted = await service.delete_document(document_id, law_firm_id, current_user)
    if not deleted:
        raise HTTPException(status_code=403, detail="Document not found or access denied")


@router.get("/{document_id}/versions/{version_id}/download", response_model=SignedUrlResponse)
async def download_version(
    document_id: uuid.UUID,
    version_id: uuid.UUID,
    db: AsyncSession = Depends(get_tenant_session),
    current_user: UserContext = Depends(get_current_user),
):
    """
    Generate a short-lived signed URL to download a specific document version.
    Requires read access.
    """
    user_id = current_user.user_id
    law_firm_id = current_user.law_firm_id

    storage = get_storage()
    audit = AuditService(db_session=db)
    parser = get_parser()
    service = DocumentService(db, storage, audit, parser)

    try:
        url = await service.get_version_download_url(
            document_id=document_id,
            version_id=version_id,
            law_firm_id=law_firm_id,
            actor_user_id=user_id,
            user=current_user,
            expiration=300,
        )
    except ValueError as exc:
        raise HTTPException(status_code=403, detail=str(exc))
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    return SignedUrlResponse(download_url=url, expires_in_seconds=300)


@router.post("/{document_id}/versions/{version_id}/process", response_model=ProcessResponse)
async def process_version(
    document_id: uuid.UUID,
    version_id: uuid.UUID,
    db: AsyncSession = Depends(get_tenant_session),
    current_user: UserContext = Depends(get_current_user),
):
    """
    Queue a background job to parse and index a document version.

    Returns immediately with a pending status. Use the parse job polling
    endpoint to track progress.
    """
    user_id = current_user.user_id
    law_firm_id = current_user.law_firm_id

    storage = get_storage()
    audit = AuditService(db_session=db)
    parser = get_parser()
    service = DocumentService(db, storage, audit, parser)

    try:
        job = await service.create_parse_job(
            version_id=version_id,
            law_firm_id=law_firm_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    process_document_version.send(
        str(job.id),
        str(version_id),
        str(law_firm_id),
        str(user_id),
    )

    return ProcessResponse(
        version_id=version_id,
        parser_status="pending",
        message="Processing queued",
    )


@router.get("/parse-jobs/{job_id}", response_model=ParseJobResponse)
async def get_parse_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_tenant_session),
    current_user: UserContext = Depends(get_current_user),
):
    """Get the status of a background parse job."""
    law_firm_id = current_user.law_firm_id

    storage = get_storage()
    audit = AuditService(db_session=db)
    parser = get_parser()
    service = DocumentService(db, storage, audit, parser)

    job = await service.get_parse_job(job_id, law_firm_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return ParseJobResponse(
        id=job.id,
        version_id=job.version_id,
        status=job.status,
        result=job.result,
        error_message=job.error_message,
        created_at=job.created_at.isoformat(),
        updated_at=job.updated_at.isoformat(),
    )


@router.post("/{document_id}/export", response_model=ExportResponse, status_code=status.HTTP_202_ACCEPTED)
async def export_document(
    document_id: uuid.UUID,
    request: ExportRequest,
    db: AsyncSession = Depends(get_tenant_session),
    current_user: UserContext = Depends(get_current_user),
):
    """
    Queue a background job to export a document version to DOCX and PDF.

    Returns immediately with a pending status. Use the export status
    endpoint to poll progress.
    """
    user_id = current_user.user_id
    law_firm_id = current_user.law_firm_id

    storage = get_storage()
    audit = AuditService(db_session=db)
    parser = get_parser()
    service = DocumentService(db, storage, audit, parser)

    try:
        job = await service.create_export_job(
            version_id=request.version_id,
            law_firm_id=law_firm_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    export_document_version.send(
        str(job.id),
        str(request.version_id),
        str(law_firm_id),
        request.draft,
        str(user_id),
    )

    return ExportResponse(
        job_id=job.id,
        version_id=request.version_id,
        status="pending",
        message="Export queued",
    )


@router.get("/{document_id}/export/status", response_model=ExportStatusResponse)
async def get_export_status(
    document_id: uuid.UUID,
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_tenant_session),
    current_user: UserContext = Depends(get_current_user),
):
    """Get the status of a background export job."""
    law_firm_id = current_user.law_firm_id

    storage = get_storage()
    audit = AuditService(db_session=db)
    parser = get_parser()
    service = DocumentService(db, storage, audit, parser)

    job = await service.get_export_job(job_id, law_firm_id)
    if not job:
        raise HTTPException(status_code=404, detail="Export job not found")

    warning = None
    if job.result and isinstance(job.result, dict):
        warning = job.result.get("warning")

    return ExportStatusResponse(
        id=job.id,
        version_id=job.version_id,
        status=job.status,
        docx_url=job.docx_url,
        pdf_url=job.pdf_url,
        warning=warning,
        error_message=job.error_message,
        created_at=job.created_at.isoformat(),
        updated_at=job.updated_at.isoformat(),
    )


# ---------------------------------------------------------------------------
# ACL endpoints
# ---------------------------------------------------------------------------

@router.post("/{document_id}/acl", response_model=ACLOut, status_code=status.HTTP_201_CREATED)
async def grant_acl(
    document_id: uuid.UUID,
    request: ACLGrantRequest,
    db: AsyncSession = Depends(get_tenant_session),
    current_user: UserContext = Depends(get_current_user),
):
    """Grant access to a document for a user or role. Requires owner access."""
    law_firm_id = current_user.law_firm_id

    storage = get_storage()
    audit = AuditService(db_session=db)
    parser = get_parser()
    service = DocumentService(db, storage, audit, parser)

    # Only owners can grant access
    if not await service.check_document_access(current_user, document_id, AccessLevel.owner):
        raise HTTPException(status_code=403, detail="Document not found or access denied")

    try:
        level = AccessLevel(request.access_level)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid access level. Must be: read, write, owner")

    try:
        acl = await service.grant_access(
            document_id=document_id,
            user_id=request.user_id,
            role=request.role,
            access_level=level,
            law_firm_id=law_firm_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    return _build_acl_out(acl)


@router.delete("/{document_id}/acl/{acl_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_acl(
    document_id: uuid.UUID,
    acl_id: uuid.UUID,
    db: AsyncSession = Depends(get_tenant_session),
    current_user: UserContext = Depends(get_current_user),
):
    """Revoke an ACL entry. Requires owner access."""
    law_firm_id = current_user.law_firm_id

    storage = get_storage()
    audit = AuditService(db_session=db)
    parser = get_parser()
    service = DocumentService(db, storage, audit, parser)

    # Only owners can revoke access
    if not await service.check_document_access(current_user, document_id, AccessLevel.owner):
        raise HTTPException(status_code=403, detail="Document not found or access denied")

    revoked = await service.revoke_access(acl_id, law_firm_id)
    if not revoked:
        raise HTTPException(status_code=404, detail="ACL entry not found")


@router.get("/{document_id}/acl", response_model=List[ACLOut])
async def list_acl(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_tenant_session),
    current_user: UserContext = Depends(get_current_user),
):
    """List all ACL entries for a document. Requires read access."""
    law_firm_id = current_user.law_firm_id

    storage = get_storage()
    audit = AuditService(db_session=db)
    parser = get_parser()
    service = DocumentService(db, storage, audit, parser)

    # Check read access
    if not await service.check_document_access(current_user, document_id, AccessLevel.read):
        raise HTTPException(status_code=403, detail="Document not found or access denied")

    try:
        acls = await service.list_acl_entries(document_id, law_firm_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    return [_build_acl_out(acl) for acl in acls]
