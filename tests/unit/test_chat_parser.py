import json
from pathlib import Path

import pytest
from app.services.chat_parser import ChatParseError, parse_chat_import

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "chats"


def test_plain_text_fallback() -> None:
    parsed = parse_chat_import(
        b"Loose transcript with unusualmarker text.",
        provider="plain_text",
        raw_format="txt",
    )

    assert len(parsed) == 1
    assert parsed[0].provider == "plain_text"
    assert parsed[0].turns[0].role == "unknown"
    assert "unusualmarker" in parsed[0].content_text


def test_markdown_speaker_parsing() -> None:
    parsed = parse_chat_import(
        b"User: hello\nAssistant: hi there",
        provider="markdown",
        raw_format="md",
    )[0]

    assert [turn.role for turn in parsed.turns] == ["user", "assistant"]
    assert parsed.turns[1].content == "hi there"


def test_chatgpt_fixture_batch_parsing() -> None:
    parsed = parse_chat_import(FIXTURES.joinpath("chatgpt_sample.json").read_bytes())

    assert len(parsed) == 2
    assert parsed[0].provider == "chatgpt"
    assert parsed[0].external_chat_id == "conv-alpha"
    assert "Phase six alpha" in parsed[0].content_text


def test_claude_like_markdown_fallback() -> None:
    parsed = parse_chat_import(
        FIXTURES.joinpath("claude_sample.md").read_bytes(),
        provider="claude",
        raw_format="md",
    )[0]

    assert parsed.provider == "claude"
    assert [turn.role for turn in parsed.turns] == ["user", "assistant"]


def test_malformed_json_error() -> None:
    with pytest.raises(ChatParseError):
        parse_chat_import(b"{bad json", raw_format="json")


def test_unsupported_json_structure_error() -> None:
    with pytest.raises(ChatParseError):
        parse_chat_import(json.dumps({"messages": []}).encode("utf-8"), raw_format="json")
