from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Any

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 150
MIN_CHUNK_CHARS = 20


@dataclass(frozen=True)
class ChunkData:
    chunk_idx: int
    content: str
    content_hash: str
    token_count: int
    source_locator: dict[str, Any] | None = None


def chunk_text(text: str, source_locator: dict[str, Any] | None = None) -> list[ChunkData]:
    if not text or not text.strip():
        return []

    chunks: list[ChunkData] = []
    start = _first_non_space(text, 0)

    while start < len(text):
        end = _choose_chunk_end(text, start)
        content = text[start:end].strip()

        if len(content) >= MIN_CHUNK_CHARS:
            chunks.append(
                ChunkData(
                    chunk_idx=len(chunks),
                    content=content,
                    content_hash=sha256(content.encode("utf-8")).hexdigest()[:32],
                    token_count=len(content) // 4,
                    source_locator=source_locator,
                )
            )

        if end >= len(text):
            break

        next_start = max(end - CHUNK_OVERLAP, start + 1)
        start = _first_non_space(text, next_start)

    return chunks


def _choose_chunk_end(text: str, start: int) -> int:
    hard_end = min(start + CHUNK_SIZE, len(text))
    if hard_end == len(text):
        return hard_end

    min_end = min(start + MIN_CHUNK_CHARS, hard_end)
    paragraph_end = text.rfind("\n\n", min_end, hard_end)
    if paragraph_end != -1:
        return paragraph_end + 2

    sentence_end = max(text.rfind(mark, min_end, hard_end) for mark in ".?!")
    if sentence_end != -1:
        return sentence_end + 1

    word_end = _last_whitespace(text, min_end, hard_end)
    if word_end != -1:
        return word_end

    return hard_end


def _last_whitespace(text: str, start: int, end: int) -> int:
    for idx in range(end - 1, start - 1, -1):
        if text[idx].isspace():
            return idx
    return -1


def _first_non_space(text: str, start: int) -> int:
    while start < len(text) and text[start].isspace():
        start += 1
    return start
