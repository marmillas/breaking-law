"""add full text search

Revision ID: f1a2b3c4d5e6
Revises: e4f8a9c1b2d3
Create Date: 2026-05-04 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, None] = "e4f8a9c1b2d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add search_vector TSVECTOR column to document_chunks
    op.add_column(
        "document_chunks",
        sa.Column(
            "search_vector",
            sa.Text().with_variant(sa.dialects.postgresql.TSVECTOR(), "postgresql"),
            nullable=True,
        ),
    )

    # Create GIN index on search_vector (PostgreSQL only)
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'pg_trgm') THEN
                -- pg_trgm is available, but we want a GIN index on tsvector
                CREATE INDEX idx_chunks_search ON document_chunks USING GIN(search_vector);
            ELSE
                -- Fallback: create a standard btree index if GIN is not available
                -- In practice, this should not happen on PostgreSQL with proper extensions
                CREATE INDEX idx_chunks_search ON document_chunks(search_vector);
            END IF;
        END $$;
        """
    )

    # Create trigger function to auto-update tsvector from chunk text
    op.execute(
        """
        CREATE OR REPLACE FUNCTION document_chunks_update_tsvector()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.search_vector := to_tsvector('spanish', NEW.text_content);
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    # Create trigger
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_trigger WHERE tgname = 'trg_document_chunks_tsvector'
            ) THEN
                CREATE TRIGGER trg_document_chunks_tsvector
                    BEFORE INSERT OR UPDATE ON document_chunks
                    FOR EACH ROW
                    EXECUTE FUNCTION document_chunks_update_tsvector();
            END IF;
        END $$;
        """
    )

    # Update existing rows to populate search_vector
    op.execute(
        """
        UPDATE document_chunks
        SET search_vector = to_tsvector('spanish', text_content)
        WHERE search_vector IS NULL;
        """
    )


def downgrade() -> None:
    # Drop trigger
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_trigger WHERE tgname = 'trg_document_chunks_tsvector'
            ) THEN
                DROP TRIGGER trg_document_chunks_tsvector ON document_chunks;
            END IF;
        END $$;
        """
    )

    # Drop trigger function
    op.execute(
        """
        DROP FUNCTION IF EXISTS document_chunks_update_tsvector();
        """
    )

    # Drop index
    op.execute(
        """
        DROP INDEX IF EXISTS idx_chunks_search;
        """
    )

    # Drop column
    op.drop_column("document_chunks", "search_vector")
