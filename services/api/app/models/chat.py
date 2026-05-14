import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Chat(Base):
    __tablename__ = "chats"

    id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("objects.id", ondelete="CASCADE"), primary_key=True
    )
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    external_chat_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_filename: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_storage_path: Mapped[str] = mapped_column(Text, nullable=False)
    raw_format: Mapped[str] = mapped_column(String(16), nullable=False)
    turn_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    imported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    parsed_turns: Mapped[list] = mapped_column(JSONB, nullable=False, server_default="[]")
    content_text: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, nullable=False, server_default="{}")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
