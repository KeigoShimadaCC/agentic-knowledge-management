"""Adapters that turn raw MCP tool responses into KnowledgeOS object inputs."""

from __future__ import annotations

import json
from dataclasses import dataclass
from fnmatch import fnmatch
from typing import Any


@dataclass
class PageInput:
    title: str
    content_text: str
    content_json: dict[str, Any]
    metadata: dict[str, Any]


@dataclass
class SourceInput:
    title: str
    extracted_text: str
    source_type: str = "web"
    url: str | None = None
    preview_data: dict[str, Any] | None = None
    metadata: dict[str, Any] | None = None


def _safe_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, indent=2)


def _text_from_content(content: Any) -> str:
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict):
                parts.append(_safe_text(item.get("text") or item.get("content") or item))
            else:
                parts.append(_safe_text(item))
        return "\n\n".join(part for part in parts if part)
    return _safe_text(content)


def _structured_payload(result: dict[str, Any]) -> Any:
    if "structuredContent" in result:
        return result["structuredContent"]
    if "content" in result:
        text = _text_from_content(result["content"])
        with suppress_json_error():
            return json.loads(text)
        return {"text": text}
    return result


class suppress_json_error:
    def __enter__(self):
        return None

    def __exit__(self, exc_type, _exc, _tb):
        return exc_type is json.JSONDecodeError


def _result_items(payload: Any) -> list[Any]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("results", "items", "documents", "issues", "pullRequests", "data"):
            value = payload.get(key)
            if isinstance(value, list):
                return value
        return [payload]
    return [{"text": _safe_text(payload)}]


def _item_title(item: dict[str, Any], fallback: str) -> str:
    for key in ("title", "name", "heading", "number"):
        value = item.get(key)
        if value:
            return str(value)[:240]
    return fallback


def _item_url(item: dict[str, Any]) -> str | None:
    for key in ("url", "html_url", "web_url", "link", "source"):
        value = item.get(key)
        if value:
            return str(value)
    return None


def _item_body(item: dict[str, Any]) -> str:
    for key in ("text", "content", "body", "description", "summary", "snippet", "markdown"):
        value = item.get(key)
        if value:
            return _safe_text(value)
    return _safe_text(item)


class GenericAdapter:
    patterns = ["*"]

    def adapt(self, result: dict[str, Any], target_kind: str) -> list[PageInput | SourceInput]:
        payload = _structured_payload(result)
        items = _result_items(payload)
        adapted: list[PageInput | SourceInput] = []
        for idx, item in enumerate(items, start=1):
            item_dict = item if isinstance(item, dict) else {"text": item}
            title = _item_title(item_dict, f"MCP result {idx}")
            text = _item_body(item_dict)
            metadata = {"mcp_result": item_dict}
            if target_kind == "page":
                adapted.append(
                    PageInput(
                        title=title,
                        content_text=text,
                        content_json={"type": "doc", "content": [{"type": "paragraph"}]},
                        metadata=metadata,
                    )
                )
            else:
                adapted.append(
                    SourceInput(
                        title=title,
                        extracted_text=text,
                        url=_item_url(item_dict),
                        preview_data=item_dict,
                        metadata=metadata,
                    )
                )
        return adapted


class BraveSearchAdapter(GenericAdapter):
    patterns = ["brave_*", "web_search*", "exa_*", "search*"]


class GitHubIssueAdapter(GenericAdapter):
    patterns = ["github_*", "issue_*", "get_issue*", "get_pull*"]

    def adapt(self, result: dict[str, Any], target_kind: str) -> list[PageInput | SourceInput]:
        adapted = super().adapt(result, target_kind)
        for item in adapted:
            item.metadata = {**(item.metadata or {}), "source_family": "github"}
            if isinstance(item, SourceInput):
                item.source_type = "web"
        return adapted


class Context7Adapter(GenericAdapter):
    patterns = ["context7*", "get_library_docs*", "resolve_library*"]

    def adapt(self, result: dict[str, Any], target_kind: str) -> list[PageInput | SourceInput]:
        adapted = super().adapt(result, target_kind)
        for item in adapted:
            item.metadata = {**(item.metadata or {}), "source_family": "context7"}
        return adapted


_ADAPTERS = [BraveSearchAdapter(), GitHubIssueAdapter(), Context7Adapter(), GenericAdapter()]


def get_adapter(tool_name: str) -> GenericAdapter:
    for adapter in _ADAPTERS:
        if any(fnmatch(tool_name, pattern) for pattern in adapter.patterns):
            return adapter
    return _ADAPTERS[-1]
