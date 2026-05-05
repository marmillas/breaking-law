"""add time tracking deadlines notifications and retention

Revision ID: a1b2c3d4e5f6
Revises: f1a2b3c4d5e6
Create Date: 2026-05-04 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "f1a2b3c4d5e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add retention columns to documents
    op.add_column("documents", sa.Column("retention_policy", sa.String(100), nullable=True))
    op.add_column("documents", sa.Column("deletion_date", sa.DateTime(), nullable=True))
    op.add_column("documents", sa.Column("deleted_at", sa.DateTime(), nullable=True))

    # Create time_entries table
    op.create_table(
        "time_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("law_firm_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("matter_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("matters.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clients.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("ended_at", sa.DateTime(), nullable=True),
        sa.Column("duration_minutes", sa.Integer(), nullable=True),
        sa.Column("billable", sa.Boolean(), default=True, nullable=False),
        sa.Column("billing_rate", sa.Float(), nullable=True),
        sa.Column("status", sa.Enum("draft", "submitted", "approved", name="timeentrystatus"), nullable=False),
        sa.Column("created_at", sa.DateTime(), default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # Create deadlines table
    op.create_table(
        "deadlines",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("law_firm_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("matter_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("matters.id", ondelete="CASCADE"), nullable=True, index=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("due_date", sa.DateTime(), nullable=False, index=True),
        sa.Column("priority", sa.Enum("low", "medium", "high", "critical", name="deadlinepriority"), nullable=False),
        sa.Column("status", sa.Enum("pending", "acknowledged", "completed", "overdue", name="deadlinestatus"), nullable=False),
        sa.Column("notification_sent_at", sa.DateTime(), nullable=True),
        sa.Column("acknowledged_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
    )

    # Create notifications table
    op.create_table(
        "notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("law_firm_id", postgresql.UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("deadline_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("deadlines.id", ondelete="CASCADE"), nullable=True, index=True),
        sa.Column("title", sa.String(300), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("priority", sa.Enum("low", "medium", "high", "critical", name="deadlinepriority"), nullable=False),
        sa.Column("read", sa.Boolean(), default=False, nullable=False),
        sa.Column("created_at", sa.DateTime(), default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("notifications")
    op.drop_table("deadlines")
    op.drop_table("time_entries")
    op.drop_column("documents", "deleted_at")
    op.drop_column("documents", "deletion_date")
    op.drop_column("documents", "retention_policy")
    op.execute("DROP TYPE IF EXISTS timeentrystatus")
    op.execute("DROP TYPE IF EXISTS deadlinepriority")
    op.execute("DROP TYPE IF EXISTS deadlinestatus")
