"""
PostgreSQL Row-Level Security infrastructure.

Provides helpers to set the tenant context at the start of each
database session and to manage RLS policies via migrations.

.. warning::
   DEPLOYMENT RISK: RLS policies rely on the `app.current_law_firm_id`
   runtime parameter. If this parameter is not set at the start of a
   session, the user will see NO rows (fail-closed). The application
   MUST call `set_tenant_context()` before any queries.
   Required: PostgreSQL 13+ with RLS enabled on tenant tables.
   Impact if missing: Queries return empty results if RLS is enabled
   but the context parameter is not set.
"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

TENANT_PARAM = "app.current_law_firm_id"
USER_PARAM = "app.current_user_id"
ROLE_PARAM = "app.current_user_role"


async def set_tenant_context(session: AsyncSession, law_firm_id: str) -> None:
    """
    Set the tenant context for the current database session.

    Must be called at the start of every session that will access
    tenant-scoped tables. This tells PostgreSQL which law_firm_id
    the current user belongs to, and RLS policies will use it to
    filter rows automatically.

    Args:
        session: Active async database session.
        law_firm_id: UUID of the current user's law firm as a string.
    """
    if session.bind and getattr(session.bind.dialect, "name", None) != "postgresql":
        return
    await session.execute(
        text(f"SELECT set_config('{TENANT_PARAM}', :v, false)"),
        {"v": str(law_firm_id)},
    )


async def set_user_context(session: AsyncSession, user_id: str) -> None:
    """
    Set the user context for owner-bypass RLS policies.

    Args:
        session: Active async database session.
        user_id: UUID of the current user as a string.
    """
    if session.bind and getattr(session.bind.dialect, "name", None) != "postgresql":
        return
    await session.execute(
        text(f"SELECT set_config('{USER_PARAM}', :v, false)"),
        {"v": str(user_id)},
    )


async def set_role_context(session: AsyncSession, role: str) -> None:
    """
    Set the role context for admin-write RLS policies.

    Args:
        session: Active async database session.
        role: Role string of the current user.
    """
    if session.bind and getattr(session.bind.dialect, "name", None) != "postgresql":
        return
    await session.execute(
        text(f"SELECT set_config('{ROLE_PARAM}', :v, false)"),
        {"v": role or ""},
    )


async def reset_tenant_context(session: AsyncSession) -> None:
    """Reset tenant context (e.g., during logout or session teardown)."""
    if session.bind and getattr(session.bind.dialect, "name", None) != "postgresql":
        return
    await session.execute(
        text(f"SELECT set_config('{TENANT_PARAM}', '', true)")
    )
    await session.execute(
        text(f"SELECT set_config('{USER_PARAM}', '', true)")
    )
    await session.execute(
        text(f"SELECT set_config('{ROLE_PARAM}', '', true)")
    )
