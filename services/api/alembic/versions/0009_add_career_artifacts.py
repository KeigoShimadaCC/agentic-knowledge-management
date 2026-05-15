"""add career artifact tables

Revision ID: 0009
Revises: 0008
Create Date: 2026-05-16
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "resume_bullet_sets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("target_role", sa.Text(), nullable=True),
        sa.Column("emphasis", sa.Text(), nullable=True),
        sa.Column("count", sa.SmallInteger(), nullable=False),
        sa.Column("bullets", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("agent_run_id", sa.Uuid(), nullable=True),
        sa.Column("prompt_version", sa.String(16), nullable=True),
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
        sa.ForeignKeyConstraint(["agent_run_id"], ["agent_runs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["id"], ["objects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["objects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_resume_bullet_sets_project_id",
        "resume_bullet_sets",
        ["project_id"],
    )

    op.create_table(
        "interview_story_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("question_type", sa.String(16), server_default="behavioral", nullable=False),
        sa.Column("target_role", sa.Text(), nullable=True),
        sa.Column("max_words", sa.Integer(), server_default="400", nullable=False),
        sa.Column("word_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("story", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("agent_run_id", sa.Uuid(), nullable=True),
        sa.Column("prompt_version", sa.String(16), nullable=True),
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
        sa.ForeignKeyConstraint(["agent_run_id"], ["agent_runs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["id"], ["objects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["objects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_interview_story_records_project_id",
        "interview_story_records",
        ["project_id"],
    )
    op.create_index(
        "ix_interview_story_records_question_type",
        "interview_story_records",
        ["question_type"],
    )


def downgrade() -> None:
    op.drop_index("ix_interview_story_records_question_type", "interview_story_records")
    op.drop_index("ix_interview_story_records_project_id", "interview_story_records")
    op.drop_table("interview_story_records")
    op.drop_index("ix_resume_bullet_sets_project_id", "resume_bullet_sets")
    op.drop_table("resume_bullet_sets")
