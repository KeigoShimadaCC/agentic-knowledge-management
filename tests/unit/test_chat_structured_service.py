import pytest
from app.services.chat_structured_service import (
    parse_structured_summary_output,
    structured_summary_hash,
)
from fastapi import HTTPException


def test_parse_structured_summary_output_accepts_fenced_json():
    summary = parse_structured_summary_output(
        """```json
        {"title":"T","summary":"S","claims":[{"claim":"C","turn_refs":[2,2],"confidence":"high"}]}
        ```"""
    )

    assert summary.title == "T"
    assert summary.claims[0].turn_refs == [2]


def test_parse_structured_summary_output_rejects_bad_json():
    with pytest.raises(HTTPException) as exc:
        parse_structured_summary_output("not json")

    assert exc.value.status_code == 502


def test_structured_summary_hash_is_stable():
    one = parse_structured_summary_output('{"title":"T","summary":"S"}')
    two = parse_structured_summary_output('{"summary":"S","title":"T"}')

    assert structured_summary_hash(one) == structured_summary_hash(two)
