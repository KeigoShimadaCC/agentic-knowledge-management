import uuid
from datetime import datetime

from sqlalchemy import ARRAY, Boolean, DateTime, ForeignKey, Index, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.object_kinds import VALID_OBJECT_KINDS
from app.db.base import Base

VALID_KINDS = VALID_OBJECT_KINDS


class KosObject(Base):
    __tablename__ = "objects"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[list] = mapped_column(ARRAY(String), nullable=False, server_default="{}")
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, server_default="{}")
    is_pinned: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    is_archived: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    ai_generated: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("idx_objects_user_id", "user_id"),
        Index("idx_objects_kind", "kind"),
        Index(
            "idx_objects_deleted_at_null",
            "deleted_at",
            postgresql_where=text("deleted_at IS NULL"),
        ),
        Index("idx_objects_created_at", "created_at"),
    )
