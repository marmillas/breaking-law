"""
FastAPI dependencies for the legal platform.

Provides database sessions, storage clients, authentication via JWT,
and RBAC enforcement. These are wired into routers via FastAPI's
dependency injection system.

.. warning::
   PostgreSQL Row-Level Security (RLS) is now ACTIVE on all tenant-scoped
   tables. Sessions that access tenant data MUST use `get_tenant_session()`
   so that the `app.current_law_firm_id` runtime parameter is set before
   any query runs. If the parameter is missing, RLS policies return zero
   rows (fail-closed). Auth endpoints that run before a user is resolved
   (login, refresh) use `get_db_session()` and rely on lookup policies.

.. note::
   RESOLVED: Refresh token rotation with replay detection is now implemented.
   - Tokens are stored as SHA-256 hashes (raw tokens never persisted).
   - Rotation links old and new tokens via `replaced_by_token_hash`.
   - Replay attacks trigger full family revocation (all tokens in the family are revoked).
   - Endpoints: POST /auth/refresh, POST /auth/logout, POST /auth/revoke-all.
"""

import uuid
from typing import AsyncGenerator

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from breaking_law.shared.database import Database
from breaking_law.documents.storage import Storage
from breaking_law.shared.audit import AuditService
from breaking_law.documents.parsing import DocumentParser
from breaking_law.shared.config import Config
from breaking_law.identity.service import AuthService
from breaking_law.infra.models import User
from breaking_law.shared.rls import (
    set_tenant_context,
    set_user_context,
    set_role_context,
    reset_tenant_context,
)
from breaking_law.shared.embeddings import get_embedding_client as _get_embedding_client, EmbeddingClient
from breaking_law.search.llm import get_llm_client as _get_llm_client, LLMRouter


# ---------------------------------------------------------------------------
# Global config and infrastructure instances (initialized on first use)
# ---------------------------------------------------------------------------

_config: Config | None = None
_database: Database | None = None
_storage: Storage | None = None
_parser: DocumentParser | None = None

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


# ---------------------------------------------------------------------------
# User context model
# ---------------------------------------------------------------------------

class UserContext(BaseModel):
    """Authenticated user context injected into every protected endpoint."""
    user_id: uuid.UUID
    law_firm_id: uuid.UUID
    email: str
    role: str
    full_name: str


# ---------------------------------------------------------------------------
# Infrastructure getters
# ---------------------------------------------------------------------------

def get_config() -> Config:
    """Get or create application configuration."""
    global _config
    if _config is None:
        _config = Config()
    return _config


def get_database() -> Database:
    """Get or create database manager."""
    global _database
    if _database is None:
        cfg = get_config()
        db_url = cfg.DATABASE_URL or "postgresql+asyncpg://localhost:5432/legal_db"
        _database = Database(database_url=db_url, echo=False)
    return _database


def get_storage() -> Storage:
    """Get or create storage client."""
    global _storage
    if _storage is None:
        cfg = get_config()
        endpoint = cfg.MINIO_ENDPOINT if cfg.STORAGE_PROVIDER == "minio" else cfg.S3_ENDPOINT
        _storage = Storage(
            bucket_name=cfg.S3_BUCKET,
            endpoint_url=endpoint,
            region_name=cfg.S3_REGION,
            access_key=cfg.STORAGE_ACCESS_KEY,
            secret_key=cfg.STORAGE_SECRET_KEY,
            sse_enabled=True,
        )
    return _storage


def get_parser() -> DocumentParser:
    """Get or create document parser."""
    global _parser
    if _parser is None:
        cfg = get_config()
        _parser = DocumentParser(
            ocr_enabled=cfg.OCR_ENABLED,
            tesseract_path=cfg.TESSERACT_PATH,
        )
    return _parser


def get_embedding_client() -> EmbeddingClient:
    """Get or create embedding client based on configuration."""
    cfg = get_config()
    return _get_embedding_client(cfg)


# ---------------------------------------------------------------------------
# Database session dependency
# ---------------------------------------------------------------------------

async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session for a request."""
    db = get_database()
    session = db.session_factory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


# ---------------------------------------------------------------------------
# Authentication dependency (JWT)
# ---------------------------------------------------------------------------

async def _resolve_user_from_token(token: str, db: AsyncSession) -> UserContext:
    """Shared helper to resolve a UserContext from a raw JWT string."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    cfg = get_config()
    auth_service = AuthService(
        secret_key=cfg.SECRET_KEY,
        algorithm=cfg.ALGORITHM,
        access_token_expire_minutes=cfg.ACCESS_TOKEN_EXPIRE_MINUTES,
    )

    payload = auth_service.decode_token(token)
    if payload is None:
        raise credentials_exception

    user_id_str = payload.get("sub")
    if user_id_str is None:
        raise credentials_exception

    try:
        user_uuid = uuid.UUID(user_id_str)
    except ValueError:
        raise credentials_exception

    # Set RLS context from JWT claims so the user query respects tenant isolation
    firm_id_str = payload.get("firm_id")
    role_str = payload.get("role")
    if firm_id_str:
        await set_tenant_context(db, firm_id_str)
    await set_user_context(db, user_id_str)
    if role_str:
        await set_role_context(db, role_str)

    result = await db.execute(
        select(User).where(User.id == user_uuid, User.is_active.is_(True))
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception

    return UserContext(
        user_id=user.id,
        law_firm_id=user.law_firm_id,
        email=user.email,
        role=user.role,
        full_name=user.full_name,
    )


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db_session),
) -> UserContext:
    """
    Resolve current user from JWT Bearer token.

    Validates the token signature and expiry, sets the PostgreSQL RLS
    tenant context using the `firm_id` claim in the JWT, then fetches
    the user from the database to ensure the account is still active.
    """
    return await _resolve_user_from_token(token, db)


async def get_current_user_from_query_token(
    token: str,
    db: AsyncSession = Depends(get_db_session),
) -> UserContext:
    """
    Resolve current user from a `token` query parameter.

    Used by SSE/EventSource where custom headers are not supported.
    """
    return await _resolve_user_from_token(token, db)


async def get_tenant_session(
    current_user: UserContext = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
) -> AsyncGenerator[AsyncSession, None]:
    """
    Yield an async database session with RLS tenant context set.

    This dependency chains `get_current_user` and `get_db_session` so
    that the same session is used, but the PostgreSQL `app.current_law_firm_id`
    parameter is guaranteed to be set before any tenant-scoped query runs.
    """
    await set_tenant_context(db, str(current_user.law_firm_id))
    await set_user_context(db, str(current_user.user_id))
    await set_role_context(db, current_user.role)
    try:
        yield db
    finally:
        await reset_tenant_context(db)


# ---------------------------------------------------------------------------
# RBAC dependency factory
# ---------------------------------------------------------------------------

def require_role(allowed_roles: list[str]):
    """
    Factory that returns a dependency enforcing role-based access control.

    Usage:
        @router.post("/", dependencies=[Depends(require_role(["owner", "lawyer"]))])
    """
    async def _role_checker(
        current_user: UserContext = Depends(get_current_user),
    ) -> UserContext:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{current_user.role}' is not authorized for this operation",
            )
        return current_user
    return _role_checker


# ---------------------------------------------------------------------------
# Audit service dependency
# ---------------------------------------------------------------------------

async def get_audit_service(
    db: AsyncSession = Depends(get_db_session),
) -> AuditService:
    """Create an audit service bound to the current database session."""
    return AuditService(db_session=db)


def get_llm_client() -> LLMRouter:
    """Get or create LLM client based on configuration."""
    cfg = get_config()
    return _get_llm_client(cfg)


async def get_rag_service(
    db: AsyncSession = Depends(get_tenant_session),
):
    """Create a RAG service bound to the current database session."""
    # Local imports to avoid circular dependency
    from breaking_law.search.search_service import SearchService
    from breaking_law.search.retrieval_service import RetrievalService
    from breaking_law.search.rag_service import RAGService

    cfg = get_config()
    embedding_client = _get_embedding_client(cfg)
    llm_client = _get_llm_client(cfg)
    search_service = SearchService(db, embedding_client)
    retrieval_service = RetrievalService(search_service)
    return RAGService(
        retrieval_service=retrieval_service,
        llm_client=llm_client,
    )


async def get_time_service(
    db: AsyncSession = Depends(get_tenant_session),
):
    """Create a time tracking service bound to the current database session."""
    from breaking_law.timekeeping.time_service import TimeService
    return TimeService(db)


async def get_deadline_service(
    db: AsyncSession = Depends(get_tenant_session),
):
    """Create a deadline service bound to the current database session."""
    from breaking_law.timekeeping.deadline_service import DeadlineService
    return DeadlineService(db)


async def get_notification_service(
    db: AsyncSession = Depends(get_tenant_session),
):
    """Create a notification service bound to the current database session."""
    from breaking_law.crm.service import NotificationService
    return NotificationService(db)


async def get_retention_service(
    db: AsyncSession = Depends(get_tenant_session),
):
    """Create a retention service bound to the current database session."""
    from breaking_law.retention.service import RetentionService
    audit = AuditService(db_session=db)
    return RetentionService(db, audit)


async def get_editor_service(
    db: AsyncSession = Depends(get_tenant_session),
):
    """Create an editor service bound to the current database session."""
    from breaking_law.documents.editor_service import EditorService
    return EditorService(db)


async def get_calendar_service(
    db: AsyncSession = Depends(get_tenant_session),
):
    """Create a calendar service bound to the current database session."""
    from breaking_law.timekeeping.calendar_service import CalendarService
    return CalendarService(db)
