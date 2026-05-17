"""Add mobile session metadata.

Revision ID: 0013
Revises: 0012
Create Date: 2026-05-17

"""

import sqlalchemy as sa

from alembic import op

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "sessions",
        sa.Column("client_type", sa.String(length=16), server_default="web", nullable=False),
    )
    op.add_column("sessions", sa.Column("device_name", sa.String(length=255), nullable=True))
    op.create_check_constraint(
        "ck_sessions_client_type",
        "sessions",
        "client_type IN ('web', 'ios')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_sessions_client_type", "sessions")
    op.drop_column("sessions", "device_name")
    op.drop_column("sessions", "client_type")
