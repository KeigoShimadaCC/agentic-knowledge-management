from pathlib import Path

from app.config import settings


def get_library_root() -> Path:
    return settings.library_root


def get_asset_path(sha256: str, ext: str) -> Path:
    return get_library_root() / "assets" / sha256[:2] / sha256 / f"original{ext}"


def get_tmp_path() -> Path:
    return get_library_root() / "tmp"


def ensure_library_structure() -> None:
    root = get_library_root()
    for subdir in ("assets", "tmp", "exports"):
        (root / subdir).mkdir(parents=True, exist_ok=True)
