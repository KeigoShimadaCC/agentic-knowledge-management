"""Add http transport type to mcp_connections.

Revision ID: 0012
Revises: 0011
Create Date: 2026-05-17

"""

from alembic import op

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("ck_mcp_connections_transport", "mcp_connections")
    op.create_check_constraint(
        "ck_mcp_connections_transport",
        "mcp_connections",
        "transport IN ('stdio', 'sse', 'http')",
    )


def downgrade() -> None:
    op.drop_constraint("ck_mcp_connections_transport", "mcp_connections")
    op.create_check_constraint(
        "ck_mcp_connections_transport",
        "mcp_connections",
        "transport IN ('stdio', 'sse')",
    )
