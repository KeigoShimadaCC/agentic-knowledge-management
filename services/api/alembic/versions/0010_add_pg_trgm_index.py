"""add pg_trgm extension and GIN indexes for multilingual ILIKE search

Revision ID: 0010
Revises: 0009
Create Date: 2026-05-16

Enables the pg_trgm Postgres extension and creates GIN trigram indexes on
objects.title and objects.description. These make ILIKE queries (used as the
multilingual keyword-search fallback for languages like Japanese that ts_vector
cannot tokenize) run in O(log n) rather than O(n) sequential scans.

No change to search_service.py is required — Postgres uses the GIN index
automatically when the query planner sees an ILIKE on an indexed column.
"""

from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Enable trigram extension (bundled with Postgres; safe to run if already present)
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    # GIN trigram index on title — searched in every ILIKE fallback path
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_objects_title_trgm"
        " ON objects USING gin (title gin_trgm_ops)"
    )

    # GIN trigram index on description — searched in project/workspace ILIKE queries
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_objects_description_trgm"
        " ON objects USING gin (description gin_trgm_ops)"
        " WHERE description IS NOT NULL"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_objects_description_trgm")
    op.execute("DROP INDEX IF EXISTS idx_objects_title_trgm")
    # pg_trgm extension is not dropped — other objects or future migrations may depend on it.
    # Remove manually with: DROP EXTENSION IF EXISTS pg_trgm;
