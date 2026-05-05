"""
Tests for PostgreSQL Row-Level Security infrastructure.

.. note::
   Full RLS integration tests require a live PostgreSQL database.
   The test suite runs on SQLite (aiosqlite) where RLS is not supported.
   Therefore integration tests are skipped automatically when PostgreSQL
   is not detected.
"""

import os
import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock

from breaking_law.shared.rls import (
    TENANT_PARAM,
    USER_PARAM,
    ROLE_PARAM,
    set_tenant_context,
    set_user_context,
    set_role_context,
    reset_tenant_context,
)
from breaking_law.api.deps import get_tenant_session, UserContext


def _using_postgres() -> bool:
    """Detect whether the test environment is targeting PostgreSQL."""
    url = os.getenv("TEST_DATABASE_URL", "")
    return "postgresql" in url or "postgres" in url


# ---------------------------------------------------------------------------
# Mock-based unit tests (run on all backends)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_set_tenant_context_sets_parameter():
    session = AsyncMock()
    session.bind = MagicMock()
    session.bind.dialect.name = "postgresql"

    await set_tenant_context(session, "550e8400-e29b-41d4-a716-446655440000")

    session.execute.assert_awaited_once()
    call_args = session.execute.call_args
    sql_text = str(call_args[0][0])
    assert "set_config" in sql_text
    assert TENANT_PARAM in sql_text
    assert call_args[0][1]["v"] == "550e8400-e29b-41d4-a716-446655440000"


@pytest.mark.asyncio
async def test_reset_tenant_context_clears_parameter():
    session = AsyncMock()
    session.bind = MagicMock()
    session.bind.dialect.name = "postgresql"

    await reset_tenant_context(session)

    assert session.execute.await_count == 3
    calls = [str(c[0][0]) for c in session.execute.call_args_list]
    assert any(TENANT_PARAM in c for c in calls)
    assert any(USER_PARAM in c for c in calls)
    assert any(ROLE_PARAM in c for c in calls)


@pytest.mark.asyncio
async def test_set_tenant_context_is_noop_on_sqlite():
    session = AsyncMock()
    session.bind = MagicMock()
    session.bind.dialect.name = "sqlite"

    await set_tenant_context(session, "550e8400-e29b-41d4-a716-446655440000")
    session.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_tenant_session_yields_session_with_context():
    session = AsyncMock()
    session.bind = MagicMock()
    session.bind.dialect.name = "postgresql"

    user = UserContext(
        user_id=uuid.uuid4(),
        law_firm_id=uuid.uuid4(),
        email="test@example.com",
        role="owner",
        full_name="Test",
    )

    gen = get_tenant_session(current_user=user, db=session)
    yielded = await gen.__anext__()
    assert yielded is session

    # Verify context was set
    assert session.execute.await_count == 3  # tenant, user, role

    # Ensure finally block runs without error
    try:
        await gen.__anext__()
    except StopAsyncIteration:
        pass

    # Verify reset was called (3 more executes)
    assert session.execute.await_count == 6


# ---------------------------------------------------------------------------
# PostgreSQL-only integration tests
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not _using_postgres(), reason="RLS requires PostgreSQL")
@pytest.mark.asyncio
async def test_rls_blocks_cross_tenant_access():
    """
    Integration test: create two law firms and users, insert data for both,
    then query as user 1 and verify only user 1's data is returned.
    """
    # This test is a placeholder for full PostgreSQL RLS integration.
    # When TEST_DATABASE_URL points to PostgreSQL, implement the full
    # two-tenant scenario using a real database session.
    pytest.skip("Full integration test stub — implement when PostgreSQL test DB is available")


@pytest.mark.skipif(not _using_postgres(), reason="RLS requires PostgreSQL")
@pytest.mark.asyncio
async def test_rls_fail_closed_when_no_context():
    """
    Verify that when tenant context is NOT set, queries return empty results.
    """
    pytest.skip("Full integration test stub — implement when PostgreSQL test DB is available")


@pytest.mark.skipif(not _using_postgres(), reason="RLS requires PostgreSQL")
@pytest.mark.asyncio
async def test_owner_bypass():
    """
    Verify document owner can see their own document even with RLS.
    """
    pytest.skip("Full integration test stub — implement when PostgreSQL test DB is available")
