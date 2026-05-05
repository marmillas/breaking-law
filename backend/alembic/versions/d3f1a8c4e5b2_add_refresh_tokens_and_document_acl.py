"""add refresh tokens and document acl

Revision ID: d3f1a8c4e5b2
Revises: b2e5a8c4d3f1
Create Date: 2026-05-04 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = "d3f1a8c4e5b2"
down_revision: Union[str, None] = "b2e5a8c4d3f1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "refresh_tokens",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("token_hash", sa.String(64), nullable=False, index=True),
        sa.Column("issued_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("replaced_by_token_hash", sa.String(64), nullable=True),
        sa.Column("family_id", UUID(as_uuid=True), nullable=False, index=True),
    )

    op.create_table(
        "document_acl",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("document_id", UUID(as_uuid=True), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("user_id", UUID(as_uuid=True), nullable=True, index=True),
        sa.Column("role", sa.String(50), nullable=True),
        sa.Column("access_level", sa.Enum("read", "write", "owner", name="accesslevel"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
    )


def downgrade() -> None:
    op.drop_table("document_acl")
    op.execute("DROP TYPE IF EXISTS accesslevel")
    op.drop_table("refresh_tokens")
