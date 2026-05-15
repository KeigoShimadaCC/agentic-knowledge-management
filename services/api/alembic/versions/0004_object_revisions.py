"""object revisions table and ai_generated flag

Revision ID: 0004
Revises: 0003
Create Date: 2026-05-14
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "object_revisions",
        sa.Column("id", sa.Uuid(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("object_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("rev_num", sa.Integer(), nullable=False),
        sa.Column("changed_by", sa.String(64), nullable=False, server_default="user"),
        sa.Column("agent_run_id", sa.Uuid(), nullable=True),
        sa.Column(
            "before_snapshot",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "after_snapshot",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["agent_run_id"], ["agent_runs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["object_id"], ["objects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("object_id", "rev_num"),
    )
    op.create_index("ix_object_revisions_object_id", "object_revisions", ["object_id"])
    op.create_index("ix_object_revisions_user_id", "object_revisions", ["user_id"])
    op.create_index("ix_object_revisions_agent_run_id", "object_revisions", ["agent_run_id"])
    op.add_column(
        "objects",
        sa.Column("ai_generated", sa.Boolean(), nullable=False, server_default="false"),
    )


def downgrade() -> None:
    op.drop_column("objects", "ai_generated")
    op.drop_index("ix_object_revisions_agent_run_id", "object_revisions")
    op.drop_index("ix_object_revisions_user_id", "object_revisions")
    op.drop_index("ix_object_revisions_object_id", "object_revisions")
    op.drop_table("object_revisions")
