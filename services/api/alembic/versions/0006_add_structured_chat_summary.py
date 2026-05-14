"""add structured chat summary fields

Revision ID: 0006
Revises: 0005
Create Date: 2026-05-14
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("chats", sa.Column("structured_summary", postgresql.JSONB(), nullable=True))
    op.add_column(
        "chats",
        sa.Column(
            "structured_summary_status",
            sa.String(16),
            nullable=False,
            server_default="none",
        ),
    )
    op.add_column(
        "chats",
        sa.Column("structured_summary_agent_run_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "chats",
        sa.Column("structured_summary_updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column("chats", sa.Column("structured_summary_hash", sa.String(64), nullable=True))
    op.create_foreign_key(
        "fk_chats_structured_summary_agent_run_id_agent_runs",
        "chats",
        "agent_runs",
        ["structured_summary_agent_run_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_chats_structured_summary_status",
        "chats",
        ["structured_summary_status"],
    )


def downgrade() -> None:
    op.drop_index("ix_chats_structured_summary_status", "chats")
    op.drop_constraint(
        "fk_chats_structured_summary_agent_run_id_agent_runs",
        "chats",
        type_="foreignkey",
    )
    op.drop_column("chats", "structured_summary_hash")
    op.drop_column("chats", "structured_summary_updated_at")
    op.drop_column("chats", "structured_summary_agent_run_id")
    op.drop_column("chats", "structured_summary_status")
    op.drop_column("chats", "structured_summary")
