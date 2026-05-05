import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from breaking_law.main import app
from breaking_law.infra.models import Base
from breaking_law.api.deps import get_db_session, get_tenant_session
from breaking_law.shared.rls import set_tenant_context
import uuid


@pytest_asyncio.fixture
async def db_session() -> AsyncSession:
    """Provide an async in-memory SQLite session with tables created."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
        autocommit=False,
    )
    session = session_factory()
    yield session
    await session.close()
    await engine.dispose()


@pytest_asyncio.fixture
async def async_client(db_session: AsyncSession) -> AsyncClient:
    """Provide an HTTPX async client for the FastAPI app with DB override."""

    async def _override_get_db():
        yield db_session

    async def _override_get_tenant_db():
        # On SQLite set_tenant_context is a no-op, but we keep the call
        # for parity with production behaviour.
        await set_tenant_context(db_session, str(uuid.uuid4()))
        yield db_session

    app.dependency_overrides[get_db_session] = _override_get_db
    app.dependency_overrides[get_tenant_session] = _override_get_tenant_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()
