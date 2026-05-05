"""
Document service for the legal platform.

Orchestrates document upload, versioning, storage, parsing, and audit logging.
Enforces tenant isolation and granular ACL on all operations.
"""

import uuid
import tempfile
import os
import hashlib
import io
from datetime import datetime, UTC
from typing import Optional, List

from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from breaking_law.infra.models import (
    Document, DocumentVersion, DocumentParseJob, DocumentExportJob,
    ParserStatus, DocumentACL, AccessLevel, Matter,
)
from breaking_law.documents.storage import Storage
from breaking_law.shared.audit import AuditService
from breaking_law.documents.parsing import DocumentParser
from breaking_law.api.deps import UserContext


class DocumentService:
    """Business logic for document lifecycle management."""

    def __init__(
        self,
        db_session: AsyncSession,
        storage: Storage,
        audit: AuditService,
        parser: DocumentParser,
    ):
        self.db = db_session
        self.storage = storage
        self.audit = audit
        self.parser = parser

    # ------------------------------------------------------------------
    # ACL helpers
    # ------------------------------------------------------------------

    async def check_document_access(
        self,
        user: UserContext,
        document_id: uuid.UUID,
        required_level: AccessLevel,
    ) -> bool:
        """
        Check whether a user has at least `required_level` access to a document.

        Access hierarchy: owner > write > read.
        Owner always has full access. If no ACL entries exist, fall back
        to tenant isolation (any firm member can read/write).
        """
        result = await self.db.execute(
            select(Document).where(
                Document.id == document_id,
                Document.law_firm_id == user.law_firm_id,
            )
        )
        document = result.scalar_one_or_none()
        if not document:
            return False

        # Owner always has full access
        if document.owner_user_id == user.user_id:
            return True

        # Count ACL entries for this document
        acl_count_result = await self.db.execute(
            select(func.count(DocumentACL.id)).where(
                DocumentACL.document_id == document_id
            )
        )
        acl_count = acl_count_result.scalar() or 0

        if acl_count == 0:
            # No ACL entries — fallback to tenant isolation for read/write only
            if required_level == AccessLevel.owner:
                return False
            return True

        # Build level filter: if required is "read", allow read/write/owner
        # if required is "write", allow write/owner
        # if required is "owner", allow only owner (already handled above)
        allowed_levels = {required_level.value}
        if required_level == AccessLevel.read:
            allowed_levels = {AccessLevel.read.value, AccessLevel.write.value, AccessLevel.owner.value}
        elif required_level == AccessLevel.write:
            allowed_levels = {AccessLevel.write.value, AccessLevel.owner.value}

        # Check user-specific or role-based ACL
        acl_result = await self.db.execute(
            select(DocumentACL).where(
                DocumentACL.document_id == document_id,
                or_(
                    DocumentACL.user_id == user.user_id,
                    DocumentACL.role == user.role,
                ),
                DocumentACL.access_level.in_(allowed_levels),
            )
        )
        return acl_result.scalar_one_or_none() is not None

    async def grant_access(
        self,
        document_id: uuid.UUID,
        user_id: Optional[uuid.UUID],
        role: Optional[str],
        access_level: AccessLevel,
        law_firm_id: uuid.UUID,
    ) -> DocumentACL:
        """
        Grant access to a document for a specific user or role.

        Args:
            document_id: Target document.
            user_id: Specific user to grant access to (nullable for role-based).
            role: Specific role to grant access to (nullable for user-based).
            access_level: Level of access (read, write, owner).
            law_firm_id: Tenant ID for isolation check.

        Returns:
            Created DocumentACL record.

        Raises:
            ValueError: If document not found or both user_id and role are None.
        """
        if user_id is None and role is None:
            raise ValueError("Either user_id or role must be provided")

        result = await self.db.execute(
            select(Document).where(
                Document.id == document_id,
                Document.law_firm_id == law_firm_id,
            )
        )
        document = result.scalar_one_or_none()
        if not document:
            raise ValueError("Document not found or access denied")

        acl = DocumentACL(
            document_id=document_id,
            user_id=user_id,
            role=role,
            access_level=access_level,
        )
        self.db.add(acl)
        await self.db.flush()
        return acl

    async def revoke_access(
        self,
        acl_id: uuid.UUID,
        law_firm_id: uuid.UUID,
    ) -> bool:
        """
        Revoke an ACL entry by ID.

        Args:
            acl_id: ACL entry to revoke.
            law_firm_id: Tenant ID for isolation check.

        Returns:
            True if deleted, False if not found.
        """
        result = await self.db.execute(
            select(DocumentACL)
            .join(Document)
            .where(
                DocumentACL.id == acl_id,
                Document.law_firm_id == law_firm_id,
            )
        )
        acl = result.scalar_one_or_none()
        if not acl:
            return False

        await self.db.delete(acl)
        await self.db.flush()
        return True

    # ------------------------------------------------------------------
    # Document operations
    # ------------------------------------------------------------------

    async def upload_document(
        self,
        file_content: bytes,
        filename: str,
        mime_type: str,
        title: str,
        law_firm_id: uuid.UUID,
        owner_user_id: uuid.UUID,
        matter_id: Optional[uuid.UUID] = None,
        classification: Optional[str] = None,
        is_confidential: bool = False,
    ) -> Document:
        """
        Upload a new document: store blob, persist metadata, create initial version, audit.

        Args:
            file_content: Raw file bytes.
            filename: Original filename.
            mime_type: Detected MIME type.
            title: Document title.
            law_firm_id: Tenant ID.
            owner_user_id: Uploading user ID.
            matter_id: Optional associated matter.
            classification: Optional document classification.
            is_confidential: Whether document is confidential.

        Returns:
            Created Document with versions loaded.
        """
        # Validate file size (max 50MB per spec)
        max_size = 50 * 1024 * 1024
        if len(file_content) > max_size:
            raise ValueError("File exceeds maximum size of 50MB")

        # Calculate SHA-256
        sha256_hash = hashlib.sha256(file_content).hexdigest()

        # Create document record first to get ID for storage key
        document = Document(
            law_firm_id=law_firm_id,
            matter_id=matter_id,
            owner_user_id=owner_user_id,
            title=title,
            classification=classification,
            is_confidential=is_confidential,
        )
        self.db.add(document)
        await self.db.flush()

        # Build storage key: {law_firm_id}/{document_id}/{version_id}/{filename}
        version_id = uuid.uuid4()
        storage_key = f"{law_firm_id}/{document.id}/{version_id}/{filename}"

        # Upload to object storage
        fileobj = io.BytesIO(file_content)
        upload_ok = self.storage.upload_fileobj(
            fileobj=fileobj,
            key=storage_key,
            metadata={
                "filename": filename,
                "title": title,
                "law_firm_id": str(law_firm_id),
                "document_id": str(document.id),
                "version_id": str(version_id),
            },
            content_type=mime_type,
        )
        if not upload_ok:
            raise RuntimeError(f"Failed to upload document to storage: {storage_key}")

        # Create initial version
        version = DocumentVersion(
            id=version_id,
            document_id=document.id,
            version_number=1,
            storage_key=storage_key,
            sha256_hash=sha256_hash,
            mime_type=mime_type,
            size_bytes=len(file_content),
            parser_status=ParserStatus.pending,
            created_by=owner_user_id,
        )
        self.db.add(version)
        await self.db.flush()

        # Audit log
        await self.audit.log_document_upload(
            law_firm_id=law_firm_id,
            document_id=document.id,
            version_id=version.id,
            actor_user_id=owner_user_id,
            filename=filename,
            size_bytes=len(file_content),
            mime_type=mime_type,
        )

        await self.db.refresh(document, attribute_names=["versions"])
        return document

    async def create_version(
        self,
        document_id: uuid.UUID,
        file_content: bytes,
        filename: str,
        mime_type: str,
        law_firm_id: uuid.UUID,
        owner_user_id: uuid.UUID,
        user: UserContext,
    ) -> DocumentVersion:
        """
        Create a new version of an existing document.

        Args:
            document_id: Existing document ID.
            file_content: Raw file bytes.
            filename: Original filename.
            mime_type: Detected MIME type.
            law_firm_id: Tenant ID (for isolation check).
            owner_user_id: User creating the version.
            user: Authenticated user context for ACL check.

        Returns:
            Created DocumentVersion.

        Raises:
            ValueError: If document not found or user lacks write access.
        """
        # Verify document exists and belongs to tenant
        result = await self.db.execute(
            select(Document).where(
                Document.id == document_id,
                Document.law_firm_id == law_firm_id,
            )
        )
        document = result.scalar_one_or_none()
        if not document:
            raise ValueError("Document not found or access denied")

        # ACL check
        if not await self.check_document_access(user, document_id, AccessLevel.write):
            raise ValueError("Document not found or access denied")

        # Validate file size
        max_size = 50 * 1024 * 1024
        if len(file_content) > max_size:
            raise ValueError("File exceeds maximum size of 50MB")

        # Calculate SHA-256
        sha256_hash = hashlib.sha256(file_content).hexdigest()

        # Determine next version number
        result = await self.db.execute(
            select(func.max(DocumentVersion.version_number)).where(
                DocumentVersion.document_id == document_id
            )
        )
        max_version = result.scalar() or 0
        next_version = max_version + 1

        # Create version record and storage key
        version_id = uuid.uuid4()
        storage_key = f"{law_firm_id}/{document_id}/{version_id}/{filename}"

        # Upload to storage
        fileobj = io.BytesIO(file_content)
        upload_ok = self.storage.upload_fileobj(
            fileobj=fileobj,
            key=storage_key,
            metadata={
                "filename": filename,
                "law_firm_id": str(law_firm_id),
                "document_id": str(document_id),
                "version_id": str(version_id),
            },
            content_type=mime_type,
        )
        if not upload_ok:
            raise RuntimeError(f"Failed to upload version to storage: {storage_key}")

        version = DocumentVersion(
            id=version_id,
            document_id=document_id,
            version_number=next_version,
            storage_key=storage_key,
            sha256_hash=sha256_hash,
            mime_type=mime_type,
            size_bytes=len(file_content),
            parser_status=ParserStatus.pending,
            created_by=owner_user_id,
        )
        self.db.add(version)
        await self.db.flush()

        # Update document updated_at
        document.updated_at = datetime.now(UTC)

        # Audit log
        await self.audit.log_event(
            law_firm_id=law_firm_id,
            resource_type="document",
            resource_id=document_id,
            action="create_version",
            actor_user_id=owner_user_id,
            metadata={
                "version_id": str(version_id),
                "version_number": next_version,
                "filename": filename,
                "size_bytes": len(file_content),
            },
        )

        return version

    async def process_version(
        self,
        version_id: uuid.UUID,
        law_firm_id: uuid.UUID,
        actor_user_id: Optional[uuid.UUID] = None,
    ) -> DocumentVersion:
        """
        Process a document version: download, parse, extract text, update status.

        Args:
            version_id: Version ID to process.
            law_firm_id: Tenant ID (isolation check).
            actor_user_id: User or system actor triggering processing.

        Returns:
            Updated DocumentVersion.
        """
        # Fetch version with document for tenant check
        result = await self.db.execute(
            select(DocumentVersion)
            .join(Document)
            .where(
                DocumentVersion.id == version_id,
                Document.law_firm_id == law_firm_id,
            )
        )
        version = result.scalar_one_or_none()
        if not version:
            raise ValueError("Version not found or access denied")

        # Update status to processing
        version.parser_status = ParserStatus.processing
        await self.db.flush()

        # Download file to temporary location
        import io
        fileobj = io.BytesIO()
        download_ok = self.storage.download_fileobj(version.storage_key, fileobj)
        if not download_ok:
            version.parser_status = ParserStatus.failed
            await self.audit.log_document_parse(
                law_firm_id=law_firm_id,
                document_id=version.document_id,
                version_id=version.id,
                actor_user_id=actor_user_id,
                status="failed",
                error_message="Failed to download file from storage",
            )
            await self.db.flush()
            raise RuntimeError("Failed to download file for processing")

        # Write to temp file for parsers
        suffix = ".pdf" if "pdf" in version.mime_type else ".docx" if "word" in version.mime_type or "docx" in version.mime_type else ".txt"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(fileobj.getvalue())
            tmp_path = tmp.name

        try:
            result = self.parser.process_document(tmp_path, version.mime_type)
            if result["success"]:
                version.extracted_text = result["text"]
                version.parser_status = ParserStatus.completed
                await self.audit.log_document_parse(
                    law_firm_id=law_firm_id,
                    document_id=version.document_id,
                    version_id=version.id,
                    actor_user_id=actor_user_id,
                    status="completed",
                )
            else:
                version.parser_status = ParserStatus.failed
                await self.audit.log_document_parse(
                    law_firm_id=law_firm_id,
                    document_id=version.document_id,
                    version_id=version.id,
                    actor_user_id=actor_user_id,
                    status="failed",
                    error_message=result["error"],
                )
        except Exception as exc:
            version.parser_status = ParserStatus.failed
            await self.audit.log_document_parse(
                law_firm_id=law_firm_id,
                document_id=version.document_id,
                version_id=version.id,
                actor_user_id=actor_user_id,
                status="failed",
                error_message=str(exc),
            )
        finally:
            os.unlink(tmp_path)

        await self.db.flush()
        return version

    async def get_document(
        self,
        document_id: uuid.UUID,
        law_firm_id: uuid.UUID,
        user: UserContext,
    ) -> Optional[Document]:
        """
        Get a document by ID with tenant isolation and ACL check.

        Args:
            document_id: Document UUID.
            law_firm_id: Tenant ID.
            user: Authenticated user context for ACL check.

        Returns:
            Document or None if not found / not accessible.
        """
        result = await self.db.execute(
            select(Document)
            .where(
                Document.id == document_id,
                Document.law_firm_id == law_firm_id,
            )
        )
        document = result.scalar_one_or_none()
        if not document:
            return None

        if not await self.check_document_access(user, document_id, AccessLevel.read):
            return None

        return document

    async def list_documents(
        self,
        law_firm_id: uuid.UUID,
        user: UserContext,
        matter_id: Optional[uuid.UUID] = None,
        status: Optional[str] = None,
        document_type: Optional[str] = None,
        client_id: Optional[uuid.UUID] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Document]:
        """
        List documents for a tenant with optional filters and ACL enforcement.

        Only returns documents the user has read access to. Documents with no
        ACL entries are visible to all firm members (fallback behavior).

        Args:
            law_firm_id: Tenant ID.
            user: Authenticated user context.
            matter_id: Optional matter filter.
            status: Filter by latest version parser_status.
            document_type: Filter by document classification.
            client_id: Filter by associated matter's client_id.
            date_from: Filter by created_at >= date_from.
            date_to: Filter by created_at <= date_to.
            limit: Maximum results.
            offset: Pagination offset.

        Returns:
            List of Document objects.
        """
        from sqlalchemy import exists

        # Subquery: documents that have at least one ACL entry
        acl_exists = exists().where(DocumentACL.document_id == Document.id)

        # Subquery: user has explicit ACL for this document
        user_acl = exists().where(
            DocumentACL.document_id == Document.id,
            or_(
                DocumentACL.user_id == user.user_id,
                DocumentACL.role == user.role,
            ),
        )

        stmt = select(Document).where(
            Document.law_firm_id == law_firm_id,
            or_(
                Document.owner_user_id == user.user_id,
                ~acl_exists,  # no ACL entries -> fallback
                user_acl,     # explicit ACL match
            ),
        )

        if matter_id:
            stmt = stmt.where(Document.matter_id == matter_id)

        if document_type:
            stmt = stmt.where(Document.classification == document_type)

        if date_from:
            stmt = stmt.where(Document.created_at >= date_from)

        if date_to:
            stmt = stmt.where(Document.created_at <= date_to)

        if client_id:
            stmt = stmt.join(Matter, Document.matter_id == Matter.id).where(
                Matter.client_id == client_id
            )

        if status:
            # Filter by latest version parser_status using a correlated subquery
            latest_version_status = (
                select(DocumentVersion.parser_status)
                .where(DocumentVersion.document_id == Document.id)
                .order_by(DocumentVersion.version_number.desc())
                .limit(1)
                .correlate(Document)
                .scalar_subquery()
            )
            stmt = stmt.where(latest_version_status == status)

        stmt = stmt.order_by(Document.created_at.desc()).limit(limit).offset(offset)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def delete_document(
        self,
        document_id: uuid.UUID,
        law_firm_id: uuid.UUID,
        user: UserContext,
    ) -> bool:
        """
        Delete a document and all its versions if the user has owner access.

        Args:
            document_id: Document UUID.
            law_firm_id: Tenant ID.
            user: Authenticated user context.

        Returns:
            True if deleted, False if not found or access denied.
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

        if not await self.check_document_access(user, document_id, AccessLevel.owner):
            return False

        await self.db.delete(document)
        await self.db.flush()
        return True

    async def get_version_download_url(
        self,
        document_id: uuid.UUID,
        version_id: uuid.UUID,
        law_firm_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        user: UserContext,
        expiration: int = 300,
    ) -> str:
        """
        Generate a short-lived signed download URL for a document version.

        Args:
            document_id: Document UUID.
            version_id: Version UUID.
            law_firm_id: Tenant ID.
            actor_user_id: Requesting user.
            user: Authenticated user context for ACL check.
            expiration: URL expiry in seconds.

        Returns:
            Presigned URL string.

        Raises:
            ValueError: If document/version not found or access denied.
            RuntimeError: If URL generation fails.
        """
        result = await self.db.execute(
            select(DocumentVersion)
            .join(Document)
            .where(
                DocumentVersion.id == version_id,
                DocumentVersion.document_id == document_id,
                Document.law_firm_id == law_firm_id,
            )
        )
        version = result.scalar_one_or_none()
        if not version:
            raise ValueError("Version not found or access denied")

        if not await self.check_document_access(user, document_id, AccessLevel.read):
            raise ValueError("Version not found or access denied")

        url = self.storage.generate_presigned_url(
            key=version.storage_key, expiration=expiration
        )
        if not url:
            raise RuntimeError("Failed to generate download URL")

        await self.audit.log_document_read(
            law_firm_id=law_firm_id,
            document_id=document_id,
            actor_user_id=actor_user_id,
            version_id=version_id,
        )

        return url

    async def create_parse_job(
        self,
        version_id: uuid.UUID,
        law_firm_id: uuid.UUID,
    ) -> DocumentParseJob:
        """
        Create a tracking record for a background parse job.

        Args:
            version_id: Document version to parse.
            law_firm_id: Tenant ID for isolation.

        Returns:
            Created DocumentParseJob.
        """
        job = DocumentParseJob(
            version_id=version_id,
            status="pending",
        )
        self.db.add(job)
        await self.db.flush()
        return job

    async def get_parse_job(
        self,
        job_id: uuid.UUID,
        law_firm_id: uuid.UUID,
    ) -> Optional[DocumentParseJob]:
        """
        Retrieve a parse job with tenant isolation.

        Args:
            job_id: Parse job UUID.
            law_firm_id: Tenant ID.

        Returns:
            DocumentParseJob or None if not found / not accessible.
        """
        result = await self.db.execute(
            select(DocumentParseJob)
            .join(DocumentVersion)
            .join(Document)
            .where(
                DocumentParseJob.id == job_id,
                Document.law_firm_id == law_firm_id,
            )
        )
        return result.scalar_one_or_none()

    async def create_export_job(
        self,
        version_id: uuid.UUID,
        law_firm_id: uuid.UUID,
    ) -> DocumentExportJob:
        """
        Create a tracking record for a background export job.

        Args:
            version_id: Document version to export.
            law_firm_id: Tenant ID for isolation.

        Returns:
            Created DocumentExportJob.
        """
        job = DocumentExportJob(
            version_id=version_id,
            status="pending",
        )
        self.db.add(job)
        await self.db.flush()
        return job

    async def get_export_job(
        self,
        job_id: uuid.UUID,
        law_firm_id: uuid.UUID,
    ) -> Optional[DocumentExportJob]:
        """
        Retrieve an export job with tenant isolation.

        Args:
            job_id: Export job UUID.
            law_firm_id: Tenant ID.

        Returns:
            DocumentExportJob or None if not found / not accessible.
        """
        result = await self.db.execute(
            select(DocumentExportJob)
            .join(DocumentVersion)
            .join(Document)
            .where(
                DocumentExportJob.id == job_id,
                Document.law_firm_id == law_firm_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_acl_entries(
        self,
        document_id: uuid.UUID,
        law_firm_id: uuid.UUID,
    ) -> List[DocumentACL]:
        """
        List all ACL entries for a document.

        Args:
            document_id: Document UUID.
            law_firm_id: Tenant ID for isolation.

        Returns:
            List of DocumentACL entries.

        Raises:
            ValueError: If document not found.
        """
        result = await self.db.execute(
            select(Document).where(
                Document.id == document_id,
                Document.law_firm_id == law_firm_id,
            )
        )
        if result.scalar_one_or_none() is None:
            raise ValueError("Document not found or access denied")

        acl_result = await self.db.execute(
            select(DocumentACL).where(DocumentACL.document_id == document_id)
        )
        return list(acl_result.scalars().all())
