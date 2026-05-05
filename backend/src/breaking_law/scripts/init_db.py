"""
Database initialization script.

Runs Alembic migrations to bring the database to the latest revision.
Run with: python -m breaking_law.scripts.init_db
"""

import sys
from pathlib import Path

# Add src to path if running directly
src_path = Path(__file__).resolve().parent.parent.parent
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from alembic.config import Config as AlembicConfig
from alembic import command


def init_database() -> None:
    """Apply all pending Alembic migrations."""
    alembic_cfg = AlembicConfig("alembic.ini")
    command.upgrade(alembic_cfg, "head")
    print("Database migrated to latest revision.")


if __name__ == "__main__":
    init_database()
