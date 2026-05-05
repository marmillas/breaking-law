"""
Document-related SQLAlchemy ORM models.

.. warning::
    DEPLOYMENT RISK: The DocumentChunk model uses a Variant column type and production PostgreSQL must have pgvector installed.
    Required: PostgreSQL with pgvector extension enabled (`CREATE EXTENSION vector;`).
    Impact if missing: DocumentChunk table creation fails on PostgreSQL; embedding queries will not work in production. SQLite tests use JSON fallback automatically.
"""

import uuid
import enum
from datetime import datetime
from typing import Optional, List

from sqlalchemy import (
    String, Text, Integer, Boolean, DateTime, ForeignKey, JSON, Enum
)
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from pgvector.sqlalchemy import Vector

from breaking_law.infra.models.base import Base, _utc_now


class ParserStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"
    indexed = "indexed"


class AccessLevel(str, enum.Enum):
    read = "read"
    write = "write"
    owner = "owner"


class EditorDraftStatus(str, enum.Enum):
    draft = "draft"
    saved = "saved"
    exported = "exported"


class Document(Base):
    """Represents a legal document with versioning and ACL support."""
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    law_firm_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    matter_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    owner_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    classification: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )
    is_confidential: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utc_now, onupdate=_utc_now, nullable=False
    )
    retention_policy: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    deletion_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    versions: Mapped[List["DocumentVersion"]] = relationship(
        back_populates="document",
        order_by="DocumentVersion.version_number.desc()",
        cascade="all, delete-orphan",
    )


class DocumentVersion(Base):
    """Represents an immutable version of a document."""
    __tablename__ = "document_versions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("documents.id", ondelete="CASCADE"), nullable=False
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    sha256_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    parser_status: Mapped[ParserStatus] = mapped_column(
        Enum(ParserStatus), default=ParserStatus.pending, nullable=False
    )
    extracted_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utc_now, nullable=False
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False
    )

    document: Mapped["Document"] = relationship(back_populates="versions")
    chunks: Mapped[List["DocumentChunk"]] = relationship(
        back_populates="version",
        order_by="DocumentChunk.chunk_index",
        cascade="all, delete-orphan",
    )
    parse_jobs: Mapped[List["DocumentParseJob"]] = relationship(
        back_populates="version",
        order_by="DocumentParseJob.created_at.desc()",
        cascade="all, delete-orphan",
    )
    export_jobs: Mapped[List["DocumentExportJob"]] = relationship(
        back_populates="version",
        order_by="DocumentExportJob.created_at.desc()",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        {"sqlite_autoincrement": False},
    )


class DocumentParseJob(Base):
    """Tracks background parsing jobs for document versions."""
    __tablename__ = "document_parse_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("document_versions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)
    result: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utc_now, onupdate=_utc_now, nullable=False
    )

    version: Mapped["DocumentVersion"] = relationship(back_populates="parse_jobs")


class DocumentExportJob(Base):
    """Tracks background export jobs for document versions."""
    __tablename__ = "document_export_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("document_versions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[str] = mapped_column(String(50), default="pending", nullable=False)
    docx_storage_key: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    pdf_storage_key: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    docx_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    pdf_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utc_now, onupdate=_utc_now, nullable=False
    )

    version: Mapped["DocumentVersion"] = relationship(back_populates="export_jobs")


class DocumentACL(Base):
    """Granular access control entry for a document."""
    __tablename__ = "document_acl"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    role: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    access_level: Mapped[AccessLevel] = mapped_column(
        Enum(AccessLevel), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utc_now, nullable=False
    )


class DocumentChunk(Base):
    """Searchable chunk of a document version with embedding vector."""
    __tablename__ = "document_chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    version_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("document_versions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    law_firm_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    text_content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding = mapped_column(
        JSON().with_variant(Vector(1536), "postgresql"),
        nullable=True,
    )
    search_vector = mapped_column(
        Text().with_variant(TSVECTOR(), "postgresql"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utc_now, nullable=False
    )

    version: Mapped["DocumentVersion"] = relationship(back_populates="chunks")


class EditorDraft(Base):
    """Represents a browser-based document editor draft with autosave support."""
    __tablename__ = "editor_drafts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    law_firm_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=False, index=True
    )
    document_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    matter_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("matters.id", ondelete="SET NULL"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    content: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    status: Mapped[EditorDraftStatus] = mapped_column(
        Enum(EditorDraftStatus), default=EditorDraftStatus.draft, nullable=False
    )
    last_autosaved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=_utc_now, onupdate=_utc_now, nullable=False
    )
