"""enable rls policies

Revision ID: e4f8a9c1b2d3
Revises: d3f1a8c4e5b2
Create Date: 2026-05-04 17:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = "e4f8a9c1b2d3"
down_revision: Union[str, None] = "d3f1a8c4e5b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _enable_rls(table: str, using_expr: str, with_check_expr: str | None = None) -> None:
    op.execute(f"ALTER TABLE IF EXISTS {table} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE IF EXISTS {table} FORCE ROW LEVEL SECURITY")
    check = f"WITH CHECK ({with_check_expr})" if with_check_expr else ""
    op.execute(f"CREATE POLICY {table}_tenant_isolation ON {table} USING ({using_expr}) {check}")


# ---------------------------------------------------------------------------
# Upgrade
# ---------------------------------------------------------------------------

def upgrade() -> None:
    # Add law_firm_id to refresh_tokens for RLS context preservation
    op.add_column(
        "refresh_tokens",
        sa.Column("law_firm_id", UUID(as_uuid=True), nullable=True, index=True),
    )

    # --- Tables with direct law_firm_id column ---
    _enable_rls(
        "law_firms",
        "id = current_setting('app.current_law_firm_id', true)::uuid",
        "id = current_setting('app.current_law_firm_id', true)::uuid",
    )
    _enable_rls(
        "users",
        "law_firm_id = current_setting('app.current_law_firm_id', true)::uuid",
        "law_firm_id = current_setting('app.current_law_firm_id', true)::uuid",
    )
    _enable_rls(
        "clients",
        "law_firm_id = current_setting('app.current_law_firm_id', true)::uuid",
        "law_firm_id = current_setting('app.current_law_firm_id', true)::uuid",
    )
    _enable_rls(
        "matters",
        "law_firm_id = current_setting('app.current_law_firm_id', true)::uuid",
        "law_firm_id = current_setting('app.current_law_firm_id', true)::uuid",
    )
    _enable_rls(
        "documents",
        "law_firm_id = current_setting('app.current_law_firm_id', true)::uuid",
        "law_firm_id = current_setting('app.current_law_firm_id', true)::uuid",
    )
    _enable_rls(
        "document_chunks",
        "law_firm_id = current_setting('app.current_law_firm_id', true)::uuid",
        "law_firm_id = current_setting('app.current_law_firm_id', true)::uuid",
    )
    _enable_rls(
        "document_acl",
        "law_firm_id = current_setting('app.current_law_firm_id', true)::uuid",
        "law_firm_id = current_setting('app.current_law_firm_id', true)::uuid",
    )

    # --- Tables with indirect law_firm_id (via JOIN) ---
    op.execute("ALTER TABLE IF EXISTS document_versions ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE IF EXISTS document_versions FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY document_versions_tenant_isolation ON document_versions
            USING (document_id IN (
                SELECT id FROM documents
                WHERE law_firm_id = current_setting('app.current_law_firm_id', true)::uuid
            ))
            WITH CHECK (document_id IN (
                SELECT id FROM documents
                WHERE law_firm_id = current_setting('app.current_law_firm_id', true)::uuid
            ))
        """
    )

    op.execute("ALTER TABLE IF EXISTS document_parse_jobs ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE IF EXISTS document_parse_jobs FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY document_parse_jobs_tenant_isolation ON document_parse_jobs
            USING (version_id IN (
                SELECT dv.id FROM document_versions dv
                JOIN documents d ON dv.document_id = d.id
                WHERE d.law_firm_id = current_setting('app.current_law_firm_id', true)::uuid
            ))
            WITH CHECK (version_id IN (
                SELECT dv.id FROM document_versions dv
                JOIN documents d ON dv.document_id = d.id
                WHERE d.law_firm_id = current_setting('app.current_law_firm_id', true)::uuid
            ))
        """
    )

    op.execute("ALTER TABLE IF EXISTS document_export_jobs ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE IF EXISTS document_export_jobs FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY document_export_jobs_tenant_isolation ON document_export_jobs
            USING (version_id IN (
                SELECT dv.id FROM document_versions dv
                JOIN documents d ON dv.document_id = d.id
                WHERE d.law_firm_id = current_setting('app.current_law_firm_id', true)::uuid
            ))
            WITH CHECK (version_id IN (
                SELECT dv.id FROM document_versions dv
                JOIN documents d ON dv.document_id = d.id
                WHERE d.law_firm_id = current_setting('app.current_law_firm_id', true)::uuid
            ))
        """
    )

    op.execute("ALTER TABLE IF EXISTS refresh_tokens ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE IF EXISTS refresh_tokens FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY refresh_tokens_tenant_isolation ON refresh_tokens
            USING (user_id IN (
                SELECT id FROM users
                WHERE law_firm_id = current_setting('app.current_law_firm_id', true)::uuid
            ))
            WITH CHECK (user_id IN (
                SELECT id FROM users
                WHERE law_firm_id = current_setting('app.current_law_firm_id', true)::uuid
            ))
        """
    )

    # --- Audit events: tenant read + admin write ---
    op.execute("ALTER TABLE IF EXISTS audit_events ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE IF EXISTS audit_events FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY audit_events_tenant_read ON audit_events
            FOR SELECT
            USING (law_firm_id = current_setting('app.current_law_firm_id', true)::uuid)
        """
    )
    op.execute(
        """
        CREATE POLICY audit_events_admin_write ON audit_events
            FOR ALL
            USING (
                law_firm_id = current_setting('app.current_law_firm_id', true)::uuid
                AND current_setting('app.current_user_role', true) IN ('owner', 'admin')
            )
            WITH CHECK (
                law_firm_id = current_setting('app.current_law_firm_id', true)::uuid
                AND current_setting('app.current_user_role', true) IN ('owner', 'admin')
            )
        """
    )

    # --- Documents owner bypass ---
    op.execute(
        """
        CREATE POLICY documents_owner_bypass ON documents
            FOR ALL
            USING (owner_user_id = current_setting('app.current_user_id', true)::uuid)
        """
    )

    # --- Auth lookup policies (required when tenant context is not yet known) ---
    op.execute(
        """
        CREATE POLICY users_login_lookup ON users
            FOR SELECT
            USING (email = current_setting('app.login_email', true))
        """
    )
    op.execute(
        """
        CREATE POLICY refresh_tokens_hash_lookup ON refresh_tokens
            FOR SELECT
            USING (token_hash = current_setting('app.token_hash', true))
        """
    )

    # --- Future-proofed tables (conditional) ---
    future_tables = [
        "time_entries",
        "deadlines",
        "notifications",
        "email_messages",
        "pending_actions",
    ]
    for table in future_tables:
        op.execute(
            f"""
            DO $$
            BEGIN
                IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = '{table}') THEN
                    ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;
                    ALTER TABLE {table} FORCE ROW LEVEL SECURITY;
                    CREATE POLICY {table}_tenant_isolation ON {table}
                        USING (law_firm_id = current_setting('app.current_law_firm_id', true)::uuid)
                        WITH CHECK (law_firm_id = current_setting('app.current_law_firm_id', true)::uuid);
                END IF;
            END $$;
            """
        )


# ---------------------------------------------------------------------------
# Downgrade
# ---------------------------------------------------------------------------

def downgrade() -> None:
    tables = [
        "law_firms",
        "users",
        "clients",
        "matters",
        "documents",
        "document_versions",
        "document_chunks",
        "document_acl",
        "document_parse_jobs",
        "document_export_jobs",
        "refresh_tokens",
        "audit_events",
        "time_entries",
        "deadlines",
        "notifications",
        "email_messages",
        "pending_actions",
    ]

    for table in tables:
        op.execute(f"DROP POLICY IF EXISTS {table}_tenant_isolation ON {table}")

    op.execute("DROP POLICY IF EXISTS documents_owner_bypass ON documents")
    op.execute("DROP POLICY IF EXISTS audit_events_tenant_read ON audit_events")
    op.execute("DROP POLICY IF EXISTS audit_events_admin_write ON audit_events")
    op.execute("DROP POLICY IF EXISTS refresh_tokens_hash_lookup ON refresh_tokens")
    op.execute("DROP POLICY IF EXISTS users_login_lookup ON users")

    for table in tables:
        op.execute(f"ALTER TABLE IF EXISTS {table} DISABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE IF EXISTS {table} NO FORCE ROW LEVEL SECURITY")

    op.drop_column("refresh_tokens", "law_firm_id")
