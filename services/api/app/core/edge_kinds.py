from __future__ import annotations

CANONICAL_EDGE_KINDS = frozenset(
    {
        "links_to",
        "cites",
        "derives_from",
        "mentions",
        "supports",
        "contradicts",
        "related_to",
        "summarizes",
        "belongs_to_project",
        "evidence_for",
        "created_from",
    }
)

LEGACY_EDGE_KINDS = frozenset(
    {
        "link",
        "embed",
        "child",
        "tag",
        "related",
        "citation",
    }
)

VALID_EDGE_KINDS = CANONICAL_EDGE_KINDS | LEGACY_EDGE_KINDS

EDGE_KIND_ALIASES = {
    "link": "links_to",
    "related": "related_to",
    "citation": "cites",
}


def is_valid_edge_kind(kind: str) -> bool:
    return kind in VALID_EDGE_KINDS


def validate_edge_kind(kind: str) -> str:
    if not is_valid_edge_kind(kind):
        allowed = ", ".join(sorted(VALID_EDGE_KINDS))
        raise ValueError(f"Unsupported edge kind '{kind}'. Expected one of: {allowed}")
    return kind
