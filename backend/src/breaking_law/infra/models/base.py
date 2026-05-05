"""
SQLAlchemy Base and utilities for the models package.
"""

from datetime import datetime, UTC

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


def _utc_now() -> datetime:
    return datetime.now(UTC)
