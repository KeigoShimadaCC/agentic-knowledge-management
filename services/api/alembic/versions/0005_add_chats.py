"""add chats

Revision ID: 0005
Revises: 0004
Create Date: 2026-05-14
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "chats",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("external_chat_id", sa.Text(), nullable=True),
        sa.Column("source_filename", sa.Text(), nullable=True),
        sa.Column("raw_storage_path", sa.Text(), nullable=False),
        sa.Column("raw_format", sa.String(16), nullable=False),
        sa.Column("turn_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "imported_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("parsed_turns", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("content_text", sa.Text(), server_default="", nullable=False),
        sa.Column("metadata", postgresql.JSONB(), server_default="{}", nullable=False),
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
        sa.ForeignKeyConstraint(["id"], ["objects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_chats_provider", "chats", ["provider"])
    op.create_index("ix_chats_imported_at", "chats", ["imported_at"])


def downgrade() -> None:
    op.drop_index("ix_chats_imported_at", "chats")
    op.drop_index("ix_chats_provider", "chats")
    op.drop_table("chats")
