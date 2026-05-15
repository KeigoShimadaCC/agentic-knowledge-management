from pathlib import Path

from app.config import settings


def get_library_root() -> Path:
    return settings.library_root


def get_asset_path(sha256: str, ext: str) -> Path:
    return get_library_root() / "assets" / sha256[:2] / sha256 / f"original{ext}"


def get_tmp_path() -> Path:
    return get_library_root() / "tmp"


def validate_path_under_library_root(p: str) -> Path:
    """Resolve *p* and assert it is under LIBRARY_ROOT. Raises ValueError otherwise.

    Rejects symlinks that escape the root and paths to non-existent or unreadable files.
    Called by ingest_file before passing a path to the API.
    """
    resolved = Path(p).resolve()
    root = get_library_root().resolve()

    if not resolved.is_relative_to(root):
        raise ValueError(
            f"Path '{p}' is outside LIBRARY_ROOT ({root}). "
            "Only files under the library root may be ingested."
        )
    # Reject broken or escaping symlinks
    if resolved.is_symlink():
        link_target = resolved.readlink()
        if not link_target.is_absolute():
            link_target = (resolved.parent / link_target).resolve()
        if not link_target.is_relative_to(root):
            raise ValueError(f"Symlink '{p}' points outside LIBRARY_ROOT.")
    if not resolved.exists():
        raise ValueError(f"File not found: '{p}'")
    if not resolved.is_file():
        raise ValueError(f"Path is not a file: '{p}'")
    return resolved


def ensure_library_structure() -> None:
    root = get_library_root()
    for subdir in ("assets", "tmp", "exports", "chats"):
        (root / subdir).mkdir(parents=True, exist_ok=True)
