VALID_OBJECT_KINDS = ("page", "asset", "note", "bookmark", "collection", "source", "chat")


def is_valid_object_kind(kind: str) -> bool:
    return kind in VALID_OBJECT_KINDS


def validate_object_kind(kind: str) -> str:
    if not is_valid_object_kind(kind):
        allowed = ", ".join(VALID_OBJECT_KINDS)
        raise ValueError(f"Unsupported object kind '{kind}'. Expected one of: {allowed}")
    return kind
