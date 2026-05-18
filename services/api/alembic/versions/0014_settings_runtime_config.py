"""Add runtime settings tables.

Revision ID: 0014
Revises: 0013
Create Date: 2026-05-19

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "settings_secrets",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("encrypted_value", sa.Text(), nullable=False),
        sa.Column("last_test_status", sa.String(length=16), nullable=True),
        sa.Column("last_test_error", sa.Text(), nullable=True),
        sa.Column("last_tested_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_settings_secrets_user_key", "settings_secrets", ["user_id", "key"], unique=True
    )
    op.create_index("ix_settings_secrets_user_id", "settings_secrets", ["user_id"])

    op.create_table(
        "settings_provider_tests",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("tested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_settings_provider_tests_user_provider",
        "settings_provider_tests",
        ["user_id", "provider"],
        unique=True,
    )
    op.create_index("ix_settings_provider_tests_user_id", "settings_provider_tests", ["user_id"])

    op.create_table(
        "ai_feature_settings",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("feature_key", sa.String(length=96), nullable=False),
        sa.Column("enabled", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=True),
        sa.Column("model", sa.String(length=128), nullable=True),
        sa.Column("temperature", sa.Float(), nullable=True),
        sa.Column("max_tokens", sa.Integer(), nullable=True),
        sa.Column("effort", sa.String(length=32), nullable=True),
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
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_ai_feature_settings_user_feature",
        "ai_feature_settings",
        ["user_id", "feature_key"],
        unique=True,
    )
    op.create_index("ix_ai_feature_settings_user_id", "ai_feature_settings", ["user_id"])

    op.create_table(
        "settings_preferences",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("key", sa.String(length=96), nullable=False),
        sa.Column(
            "value", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False
        ),
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
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_settings_preferences_user_key",
        "settings_preferences",
        ["user_id", "key"],
        unique=True,
    )
    op.create_index("ix_settings_preferences_user_id", "settings_preferences", ["user_id"])

    op.create_table(
        "prompt_overrides",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("prompt_key", sa.String(length=96), nullable=False),
        sa.Column("template", sa.Text(), nullable=False),
        sa.Column(
            "metadata", postgresql.JSONB(astext_type=sa.Text()), server_default="{}", nullable=False
        ),
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
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_prompt_overrides_user_prompt",
        "prompt_overrides",
        ["user_id", "prompt_key"],
        unique=True,
    )
    op.create_index("ix_prompt_overrides_user_id", "prompt_overrides", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_prompt_overrides_user_id", table_name="prompt_overrides")
    op.drop_index("uq_prompt_overrides_user_prompt", table_name="prompt_overrides")
    op.drop_table("prompt_overrides")
    op.drop_index("ix_settings_preferences_user_id", table_name="settings_preferences")
    op.drop_index("uq_settings_preferences_user_key", table_name="settings_preferences")
    op.drop_table("settings_preferences")
    op.drop_index("ix_ai_feature_settings_user_id", table_name="ai_feature_settings")
    op.drop_index("uq_ai_feature_settings_user_feature", table_name="ai_feature_settings")
    op.drop_table("ai_feature_settings")
    op.drop_index("ix_settings_provider_tests_user_id", table_name="settings_provider_tests")
    op.drop_index("uq_settings_provider_tests_user_provider", table_name="settings_provider_tests")
    op.drop_table("settings_provider_tests")
    op.drop_index("ix_settings_secrets_user_id", table_name="settings_secrets")
    op.drop_index("uq_settings_secrets_user_key", table_name="settings_secrets")
    op.drop_table("settings_secrets")
