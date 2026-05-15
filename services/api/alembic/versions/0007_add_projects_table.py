"""add projects

Revision ID: 0007
Revises: 0006
Create Date: 2026-05-15
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=True),
        sa.Column("period_end", sa.Date(), nullable=True),
        sa.Column("role", sa.Text(), nullable=True),
        sa.Column("organization", sa.Text(), nullable=True),
        sa.Column("problem", sa.Text(), nullable=True),
        sa.Column("actions", sa.Text(), nullable=True),
        sa.Column("results", sa.Text(), nullable=True),
        sa.Column("metrics", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column(
            "skills",
            postgresql.ARRAY(sa.Text()),
            server_default="{}",
            nullable=False,
        ),
        sa.Column("status", sa.String(16), server_default="active", nullable=False),
        sa.Column("confidence", sa.String(16), server_default="manual", nullable=False),
        sa.Column("extracted_from", sa.Uuid(), nullable=True),
        sa.Column("extracted_by_agent_run_id", sa.Uuid(), nullable=True),
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
        sa.ForeignKeyConstraint(["extracted_from"], ["objects.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["extracted_by_agent_run_id"], ["agent_runs.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_projects_period_start", "projects", ["period_start"])
    op.create_index("ix_projects_period_end", "projects", ["period_end"])
    op.create_index("ix_projects_status", "projects", ["status"])
    op.create_index(
        "ix_projects_skills",
        "projects",
        ["skills"],
        postgresql_using="gin",
    )


def downgrade() -> None:
    op.drop_index("ix_projects_skills", "projects")
    op.drop_index("ix_projects_status", "projects")
    op.drop_index("ix_projects_period_end", "projects")
    op.drop_index("ix_projects_period_start", "projects")
    op.drop_table("projects")
