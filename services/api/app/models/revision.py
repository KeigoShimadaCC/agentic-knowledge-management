import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ObjectRevision(Base):
    __tablename__ = "object_revisions"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, server_default=text("gen_random_uuid()")
    )
    object_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("objects.id", ondelete="CASCADE"))
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    rev_num: Mapped[int] = mapped_column(Integer, nullable=False)
    changed_by: Mapped[str] = mapped_column(String(64), nullable=False, server_default="user")
    agent_run_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("agent_runs.id", ondelete="SET NULL"), nullable=True
    )
    before_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    after_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    __table_args__ = (
        Index("ix_object_revisions_object_id", "object_id"),
        Index("ix_object_revisions_user_id", "user_id"),
        Index("ix_object_revisions_agent_run_id", "agent_run_id"),
        UniqueConstraint("object_id", "rev_num"),
    )
