import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from breaking_law.shared.database import Database


def test_database_creates_async_engine():
    db = Database(database_url="sqlite+aiosqlite:///:memory:", echo=False)
    assert db.engine is not None
    assert str(db.engine.url) == "sqlite+aiosqlite:///:memory:"


def test_database_session_factory_returns_async_session():
    db = Database(database_url="sqlite+aiosqlite:///:memory:", echo=False)
    session = db.session_factory()
    assert isinstance(session, AsyncSession)
