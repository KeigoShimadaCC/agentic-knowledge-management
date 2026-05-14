from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.config import settings
from app.core.library import get_library_root

PARSER_VERSION = "phase6a.v1"


def store_batch_raw(content: bytes, *, provider: str) -> str:
    batch_id = uuid.uuid4()
    rel_path = f"chats/{provider}/imports/{batch_id}/raw.json"
    _atomic_write(get_library_root() / rel_path, content)
    return rel_path


def store_chat_raw(
    *,
    chat_id: uuid.UUID,
    provider: str,
    raw_format: str,
    content: bytes,
    metadata: dict[str, Any],
) -> str:
    ext = "md" if raw_format == "md" else raw_format
    rel_path = f"chats/{provider}/{chat_id}/raw.{ext}"
    _atomic_write(get_library_root() / rel_path, content)
    _atomic_write_json(
        get_library_root() / f"chats/{provider}/{chat_id}/metadata.json",
        {
            **metadata,
            "provider": provider,
            "raw_format": raw_format,
            "raw_storage_path": rel_path,
            "byte_size": len(content),
            "sha256": hashlib.sha256(content).hexdigest(),
            "imported_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "parser_version": PARSER_VERSION,
        },
    )
    return rel_path


def raw_payload_bytes(payload: Any, raw_format: str) -> bytes:
    if isinstance(payload, bytes):
        return payload
    if raw_format == "json":
        return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
    return str(payload).encode("utf-8")


def resolve_library_path(relative_path: str) -> Path:
    root = get_library_root().resolve()
    path = (root / relative_path).resolve()
    if root != path and root not in path.parents:
        raise ValueError("Path is outside library root")
    return path


def _atomic_write(path: Path, content: bytes) -> None:
    if len(content) > settings.chat_import_max_bytes:
        raise ValueError("Chat import exceeds configured size limit.")
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(f"{path.suffix}.tmp")
    tmp.write_bytes(content)
    tmp.rename(path)


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    _atomic_write(path, json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8"))
