"""
Database infrastructure for legal platform.

Provides async SQLAlchemy engine and session management with proper
session scoping for FastAPI dependency injection.
"""

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession


class Database:
    """Async database manager with session factory."""

    def __init__(self, database_url: str, echo: bool = False):
        """
        Initialize async database engine and session factory.

        Args:
            database_url: SQLAlchemy async database URL (e.g. postgresql+asyncpg://...)
            echo: Enable SQL statement logging.
        """
        self.engine = create_async_engine(database_url, echo=echo)
        self.session_factory = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
            autocommit=False,
        )

    async def get_session(self) -> AsyncSession:
        """Get a new async database session."""
        return self.session_factory()

    async def close(self):
        """Dispose the database engine."""
        await self.engine.dispose()
