from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

SUPPORTED_PROVIDERS = {"auto", "chatgpt", "claude", "markdown", "plain_text", "unknown"}
SUPPORTED_RAW_FORMATS = {"json", "md", "txt"}
ROLE_MAP = {
    "human": "user",
    "user": "user",
    "assistant": "assistant",
    "claude": "assistant",
    "system": "system",
    "tool": "tool",
}
SPEAKER_RE = re.compile(
    r"^\s*(?:#{1,6}\s*)?(User|Human|Assistant|Claude|System|Tool)\s*:?\s*$|"
    r"^\s*(User|Human|Assistant|Claude|System|Tool)\s*:\s*(.*)$",
    re.IGNORECASE,
)


class ChatParseError(ValueError):
    pass


@dataclass
class ParsedTurn:
    turn_index: int
    role: str
    author: str | None
    content: str
    created_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "turn_index": self.turn_index,
            "role": self.role,
            "author": self.author,
            "content": self.content,
            "created_at": self.created_at.isoformat().replace("+00:00", "Z")
            if self.created_at
            else None,
            "metadata": self.metadata,
        }


@dataclass
class ParsedChat:
    title: str
    provider: str
    external_chat_id: str | None
    raw_format: str
    turns: list[ParsedTurn]
    content_text: str
    started_at: datetime | None = None
    ended_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    raw_payload: Any = None


def parse_chat_import(
    content: bytes,
    *,
    provider: str = "auto",
    raw_format: str | None = None,
    title: str | None = None,
) -> list[ParsedChat]:
    provider = _normalize_provider(provider)
    raw_format = raw_format or _infer_format(content)

    if raw_format not in SUPPORTED_RAW_FORMATS:
        raise ChatParseError("Unsupported chat import format. Use .json, .md, .markdown, or .txt.")

    text = content.decode("utf-8-sig", errors="replace")
    if raw_format == "json" or provider == "chatgpt":
        return _parse_json(text, provider=provider, title=title)

    parsed_provider = "claude" if provider == "claude" else provider
    if provider == "auto":
        parsed_provider = "markdown" if raw_format == "md" else "plain_text"
    return [_parse_text(text, provider=parsed_provider, raw_format=raw_format, title=title)]


def _parse_json(text: str, *, provider: str, title: str | None) -> list[ParsedChat]:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ChatParseError(f"Malformed JSON chat import: {exc.msg}") from exc

    conversations = _extract_chatgpt_conversations(payload)
    if conversations:
        return [_parse_chatgpt_conversation(item, fallback_title=title) for item in conversations]

    if provider in {"chatgpt", "auto"}:
        raise ChatParseError("JSON import did not match a supported ChatGPT conversations export.")
    raise ChatParseError("Unsupported JSON chat import structure.")


def _extract_chatgpt_conversations(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict) and "mapping" in item]
    if isinstance(payload, dict):
        conversations = payload.get("conversations")
        if isinstance(conversations, list):
            return [item for item in conversations if isinstance(item, dict) and "mapping" in item]
        if "mapping" in payload:
            return [payload]
    return []


def _parse_chatgpt_conversation(
    conversation: dict[str, Any], *, fallback_title: str | None
) -> ParsedChat:
    mapping = conversation.get("mapping")
    if not isinstance(mapping, dict):
        raise ChatParseError("ChatGPT conversation is missing a mapping object.")

    nodes = sorted(mapping.values(), key=_chatgpt_node_sort_key)
    turns: list[ParsedTurn] = []
    for node in nodes:
        if not isinstance(node, dict):
            continue
        message = node.get("message")
        if not isinstance(message, dict):
            continue
        content = _chatgpt_message_text(message.get("content"))
        if not content.strip():
            continue
        author_data = message.get("author") if isinstance(message.get("author"), dict) else {}
        role = _normalize_role(str(author_data.get("role") or "unknown"))
        author = author_data.get("name") if isinstance(author_data.get("name"), str) else None
        created_at = _datetime_from_chatgpt(message.get("create_time"))
        turns.append(
            ParsedTurn(
                turn_index=len(turns),
                role=role,
                author=author,
                content=content.strip(),
                created_at=created_at,
                metadata={"message_id": message.get("id")},
            )
        )

    if not turns:
        raise ChatParseError("ChatGPT conversation did not contain readable message turns.")

    return _build_parsed_chat(
        title=fallback_title or str(conversation.get("title") or "Imported ChatGPT conversation"),
        provider="chatgpt",
        external_chat_id=str(conversation.get("id")) if conversation.get("id") else None,
        raw_format="json",
        turns=turns,
        metadata={"source": "chatgpt_export"},
        raw_payload=conversation,
    )


def _parse_text(text: str, *, provider: str, raw_format: str, title: str | None) -> ParsedChat:
    turns = _split_speaker_turns(text)
    if not turns:
        stripped = text.strip()
        if stripped:
            turns = [ParsedTurn(turn_index=0, role="unknown", author=None, content=stripped)]

    if not turns:
        raise ChatParseError("Chat import is empty.")

    return _build_parsed_chat(
        title=title or "Imported chat transcript",
        provider=provider if provider != "auto" else "unknown",
        external_chat_id=None,
        raw_format=raw_format,
        turns=turns,
        metadata={"source": "text_transcript"},
        raw_payload=text,
    )


def _split_speaker_turns(text: str) -> list[ParsedTurn]:
    turns: list[ParsedTurn] = []
    current_role: str | None = None
    current_author: str | None = None
    buffer: list[str] = []

    def flush() -> None:
        nonlocal buffer, current_role, current_author
        content = "\n".join(buffer).strip()
        if current_role and content:
            turns.append(
                ParsedTurn(
                    turn_index=len(turns),
                    role=current_role,
                    author=current_author,
                    content=content,
                )
            )
        buffer = []

    for line in text.splitlines():
        match = SPEAKER_RE.match(line)
        if match:
            flush()
            speaker = match.group(1) or match.group(2) or ""
            inline = match.group(3) or ""
            current_role = _normalize_role(speaker)
            current_author = speaker
            if inline.strip():
                buffer.append(inline.strip())
            continue
        if current_role:
            buffer.append(line)
    flush()
    return turns


def _build_parsed_chat(
    *,
    title: str,
    provider: str,
    external_chat_id: str | None,
    raw_format: str,
    turns: list[ParsedTurn],
    metadata: dict[str, Any],
    raw_payload: Any,
) -> ParsedChat:
    started_at = next((turn.created_at for turn in turns if turn.created_at), None)
    ended_at = next((turn.created_at for turn in reversed(turns) if turn.created_at), None)
    return ParsedChat(
        title=title.strip() or "Imported chat transcript",
        provider=provider,
        external_chat_id=external_chat_id,
        raw_format=raw_format,
        turns=turns,
        content_text=_content_text(turns),
        started_at=started_at,
        ended_at=ended_at,
        metadata=metadata,
        raw_payload=raw_payload,
    )


def _chatgpt_node_sort_key(node: Any) -> tuple[float, str]:
    if not isinstance(node, dict):
        return (0, "")
    message = node.get("message")
    create_time = message.get("create_time") if isinstance(message, dict) else None
    value = create_time if isinstance(create_time, int | float) else 0
    return (float(value), str(node.get("id") or ""))


def _chatgpt_message_text(content: Any) -> str:
    if not isinstance(content, dict):
        return ""
    parts = content.get("parts")
    if isinstance(parts, list):
        return "\n".join(_serialize_part(part) for part in parts if _serialize_part(part).strip())
    text = content.get("text")
    return str(text) if text is not None else ""


def _serialize_part(part: Any) -> str:
    if isinstance(part, str):
        return part
    if part is None:
        return ""
    if isinstance(part, dict):
        return json.dumps(part, ensure_ascii=False, sort_keys=True)
    return str(part)


def _datetime_from_chatgpt(value: Any) -> datetime | None:
    if isinstance(value, int | float):
        return datetime.fromtimestamp(float(value), tz=UTC)
    return None


def _infer_format(content: bytes) -> str:
    prefix = content.lstrip()[:1]
    if prefix in {b"{", b"["}:
        return "json"
    text = content[:4096].decode("utf-8-sig", errors="ignore")
    if re.search(r"^\s*#{1,6}\s*(User|Human|Assistant|Claude)\b", text, re.MULTILINE):
        return "md"
    return "txt"


def _normalize_provider(provider: str) -> str:
    value = provider.strip().lower()
    if value not in SUPPORTED_PROVIDERS:
        raise ChatParseError(f"Unsupported provider '{provider}'.")
    return value


def _normalize_role(role: str) -> str:
    return ROLE_MAP.get(role.strip().lower(), "unknown")


def _content_text(turns: list[ParsedTurn]) -> str:
    parts = []
    for turn in turns:
        label = turn.author or turn.role.title()
        parts.append(f"[{label}] {turn.content}")
    return "\n\n".join(parts)
