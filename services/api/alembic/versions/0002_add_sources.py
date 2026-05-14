"""add sources

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-14
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "CREATE TYPE source_type_enum AS ENUM "
        "('pdf', 'image', 'video', 'audio', 'youtube', 'web', 'csv', 'file')"
    )
    op.create_table(
        "sources",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "source_type",
            postgresql.ENUM(
                "pdf",
                "image",
                "video",
                "audio",
                "youtube",
                "web",
                "csv",
                "file",
                name="source_type_enum",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("asset_id", sa.Uuid(), nullable=True),
        sa.Column("ingestion_status", sa.String(16), server_default="pending", nullable=False),
        sa.Column("extracted_text", sa.Text(), nullable=True),
        sa.Column("page_count", sa.Integer(), nullable=True),
        sa.Column("thumbnail_path", sa.Text(), nullable=True),
        sa.Column("preview_data", postgresql.JSONB(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["asset_id"], ["objects.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["id"], ["objects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sources_ingestion_status", "sources", ["ingestion_status"])


def downgrade() -> None:
    op.drop_table("sources")
    op.execute("DROP TYPE source_type_enum")
