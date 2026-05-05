"""
Document schemas for documents, versions, editor drafts, and retention.
"""

import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class DocumentVersionOut(BaseModel):
    id: uuid.UUID
    version_number: int
    storage_key: str
    sha256_hash: str
    mime_type: str
    size_bytes: int
    parser_status: str
    created_at: str
    created_by: uuid.UUID

    class Config:
        from_attributes = True


class DocumentOut(BaseModel):
    id: uuid.UUID
    law_firm_id: uuid.UUID
    matter_id: Optional[uuid.UUID]
    owner_user_id: uuid.UUID
    title: str
    classification: Optional[str]
    is_confidential: bool
    created_at: str
    updated_at: str
    versions: List[DocumentVersionOut]

    class Config:
        from_attributes = True


class UploadResponse(BaseModel):
    document_id: uuid.UUID
    version_id: uuid.UUID
    version_number: int
    message: str


class SignedUrlResponse(BaseModel):
    download_url: str
    expires_in_seconds: int


class ProcessResponse(BaseModel):
    version_id: uuid.UUID
    parser_status: str
    message: str


class ParseJobResponse(BaseModel):
    id: uuid.UUID
    version_id: uuid.UUID
    status: str
    result: Optional[dict]
    error_message: Optional[str]
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class ExportRequest(BaseModel):
    version_id: uuid.UUID
    draft: dict
    branding: Optional[dict] = None


class ExportResponse(BaseModel):
    job_id: uuid.UUID
    version_id: uuid.UUID
    status: str
    message: str


class ExportStatusResponse(BaseModel):
    id: uuid.UUID
    version_id: uuid.UUID
    status: str
    docx_url: Optional[str]
    pdf_url: Optional[str]
    warning: Optional[str]
    error_message: Optional[str]
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class ACLOut(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    user_id: Optional[uuid.UUID]
    role: Optional[str]
    access_level: str
    created_at: str

    class Config:
        from_attributes = True


class ACLGrantRequest(BaseModel):
    user_id: Optional[uuid.UUID] = None
    role: Optional[str] = None
    access_level: str


class CreateDraftRequest(BaseModel):
    title: str
    matter_id: Optional[uuid.UUID] = None


class AutosaveRequest(BaseModel):
    content: list


class InsertCitationRequest(BaseModel):
    citation_block: dict


class DraftOut(BaseModel):
    id: uuid.UUID
    law_firm_id: uuid.UUID
    document_id: Optional[uuid.UUID] = None
    user_id: uuid.UUID
    matter_id: Optional[uuid.UUID] = None
    title: str
    content: Optional[list] = None
    status: str
    last_autosaved_at: Optional[str] = None
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class EditorDocumentOut(BaseModel):
    id: uuid.UUID
    law_firm_id: uuid.UUID
    matter_id: Optional[uuid.UUID] = None
    owner_user_id: uuid.UUID
    title: str
    classification: Optional[str] = None
    is_confidential: bool
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class RetentionPolicyRequest(BaseModel):
    policy: str


class RetentionStatusOut(BaseModel):
    document_id: str
    retention_policy: Optional[str] = None
    deletion_date: Optional[str] = None
    deleted_at: Optional[str] = None


class ScheduleDeletionRequest(BaseModel):
    deletion_date: datetime


class MessageOut(BaseModel):
    message: str
