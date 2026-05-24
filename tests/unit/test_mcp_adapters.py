"""Unit tests for MCP tool-result adapters.

Adapters convert untrusted external MCP `tools/call` output into KosObject
inputs. Silent field-mapping regressions here corrupt the KB, so the four
adapters and the `get_adapter()` pattern dispatch are covered explicitly.
"""

from app.mcp_client.adapters import (
    BraveSearchAdapter,
    Context7Adapter,
    GenericAdapter,
    GitHubIssueAdapter,
    PageInput,  # noqa: F401  (re-exported for downstream test files)
    SourceInput,
    get_adapter,
)


def test_generic_adapter_returns_source_input_with_url_and_text():
    item = {
        "title": "Hello world",
        "url": "https://example.com/post",
        "snippet": "A friendly greeting from the test fixture.",
    }
    result = {"structuredContent": {"results": [item]}}

    adapter = GenericAdapter()
    out = adapter.adapt(result, "source")

    assert len(out) == 1
    src = out[0]
    assert isinstance(src, SourceInput)
    assert src.title == "Hello world"
    assert src.url == "https://example.com/post"
    assert src.extracted_text == "A friendly greeting from the test fixture."
    assert src.source_type == "web"
    assert src.metadata == {"mcp_result": item}
    assert src.preview_data == item


def test_brave_adapter_matches_pattern_and_returns_multiple_sources():
    adapter = get_adapter("brave_web_search")
    assert isinstance(adapter, BraveSearchAdapter), (
        "brave_web_search should dispatch to BraveSearchAdapter, not Generic"
    )

    result = {
        "structuredContent": {
            "results": [
                {"title": "First hit", "url": "https://a.test/", "snippet": "alpha"},
                {"title": "Second hit", "url": "https://b.test/", "snippet": "beta"},
            ]
        }
    }
    out = adapter.adapt(result, "source")

    assert len(out) == 2
    titles = [s.title for s in out]
    assert titles == ["First hit", "Second hit"]
    assert all(isinstance(s, SourceInput) for s in out)
    assert all(s.source_type == "web" for s in out)


def test_github_adapter_adds_source_family_metadata():
    adapter = get_adapter("github_get_issue")
    assert isinstance(adapter, GitHubIssueAdapter)

    result = {
        "structuredContent": {
            "issues": [
                {
                    "title": "Bug: thing broken",
                    "html_url": "https://github.com/o/r/issues/42",
                    "body": "Steps to reproduce...",
                },
                {
                    "title": "PR: fix thing",
                    "html_url": "https://github.com/o/r/pull/43",
                    "body": "This fixes the bug.",
                },
            ]
        }
    }
    out = adapter.adapt(result, "source")

    assert len(out) == 2
    for src in out:
        assert isinstance(src, SourceInput)
        assert src.source_type == "web"
        assert src.metadata is not None
        assert src.metadata["source_family"] == "github"
        # URL must come from html_url since GitHub items don't use plain `url`.
        assert src.url is not None
        assert src.url.startswith("https://github.com/")


def test_context7_adapter_adds_source_family_metadata():
    adapter = get_adapter("query-docs")
    assert isinstance(adapter, Context7Adapter)

    result = {
        "structuredContent": {
            "documents": [
                {
                    "title": "React useState",
                    "url": "https://react.dev/reference/react/useState",
                    "content": "useState is a React Hook that lets you add state...",
                }
            ]
        }
    }
    out = adapter.adapt(result, "source")

    assert len(out) == 1
    src = out[0]
    assert isinstance(src, SourceInput)
    assert src.title == "React useState"
    assert src.metadata is not None
    assert src.metadata["source_family"] == "context7"
