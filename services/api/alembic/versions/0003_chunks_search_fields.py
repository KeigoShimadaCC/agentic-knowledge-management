"""prepare chunks for idempotent search indexing

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-14
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add user_id for ownership-scoped queries and security filtering.
    # Populated from objects.user_id for any pre-existing chunks, then made NOT NULL.
    op.add_column("chunks", sa.Column("user_id", sa.Uuid(), nullable=True))
    op.execute(
        "UPDATE chunks SET user_id = objects.user_id "
        "FROM objects WHERE chunks.object_id = objects.id"
    )
    op.alter_column("chunks", "user_id", nullable=False)
    op.create_foreign_key(
        "fk_chunks_user_id", "chunks", "users", ["user_id"], ["id"], ondelete="CASCADE"
    )
    op.create_index("ix_chunks_user_id", "chunks", ["user_id"])

    # Search-readiness fields for idempotent chunking and embedding pipelines.
    op.add_column("chunks", sa.Column("source_locator", postgresql.JSONB(), nullable=True))
    op.add_column("chunks", sa.Column("content_hash", sa.Text(), nullable=True))
    op.add_column(
        "chunks",
        sa.Column(
            "embedding_status",
            sa.String(16),
            nullable=False,
            server_default="pending",
        ),
    )
    op.add_column("chunks", sa.Column("embedding_model", sa.Text(), nullable=True))
    op.add_column("chunks", sa.Column("embedded_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("chunks", sa.Column("qdrant_point_id", sa.Text(), nullable=True))
    op.add_column(
        "chunks",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.create_index("ix_chunks_embedding_status", "chunks", ["embedding_status"])
    op.create_index("ix_chunks_object_id", "chunks", ["object_id"])
    op.create_index("ix_chunks_content_hash", "chunks", ["content_hash"])


def downgrade() -> None:
    op.drop_index("ix_chunks_content_hash", "chunks")
    op.drop_index("ix_chunks_object_id", "chunks")
    op.drop_index("ix_chunks_embedding_status", "chunks")
    op.drop_index("ix_chunks_user_id", "chunks")
    op.drop_constraint("fk_chunks_user_id", "chunks", type_="foreignkey")
    op.drop_column("chunks", "updated_at")
    op.drop_column("chunks", "qdrant_point_id")
    op.drop_column("chunks", "embedded_at")
    op.drop_column("chunks", "embedding_model")
    op.drop_column("chunks", "embedding_status")
    op.drop_column("chunks", "content_hash")
    op.drop_column("chunks", "source_locator")
    op.drop_column("chunks", "user_id")
