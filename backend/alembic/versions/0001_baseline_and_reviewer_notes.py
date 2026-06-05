"""baseline: stamp existing schema and add missing reviewer_notes column

The database was originally created by SQLAlchemy create_all() without Alembic,
so alembic_version did not exist. This migration:
  1. Adds the missing reviewer_notes column to coding_sessions.
  2. Adds a server-side default of 'pending' to review_status (it already
     exists as NOT NULL but had no server default, which risks bare INSERT
     failures).
  3. Acts as the baseline revision (down_revision = None) so all future
     migrations chain from here.

Safe for existing data:
  - reviewer_notes is nullable  — existing rows get NULL, no data loss.
  - review_status server default — existing rows already have a value;
    ALTER COLUMN ... SET DEFAULT affects only future inserts, not existing rows.

Revision ID: 0001_baseline
Revises:     (none — this is the root)
Create Date: 2026-06-03
"""

from alembic import op
import sqlalchemy as sa

revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # ── 1. Add reviewer_notes if it doesn't exist ─────────────────────────────
    # Guard with information_schema check so re-running is safe.
    result = conn.execute(sa.text("""
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'coding_sessions'
          AND column_name = 'reviewer_notes'
    """))
    if result.fetchone() is None:
        op.add_column(
            "coding_sessions",
            sa.Column("reviewer_notes", sa.Text(), nullable=True),
        )

    # ── 2. Add server-side default to review_status ───────────────────────────
    # The column already exists as NOT NULL.  Adding a server default means
    # INSERT statements that omit review_status will no longer fail.
    op.alter_column(
        "coding_sessions",
        "review_status",
        existing_type=sa.String(50),
        existing_nullable=False,
        server_default="pending",
    )


def downgrade() -> None:
    # Remove the server default (restore original state)
    op.alter_column(
        "coding_sessions",
        "review_status",
        existing_type=sa.String(50),
        existing_nullable=False,
        server_default=None,
    )

    # Drop reviewer_notes
    op.drop_column("coding_sessions", "reviewer_notes")
