from pathlib import Path

from app.core.library import get_library_root


def store_file(content: bytes, sha256: str, filename: str) -> str:
    ext = Path(filename).suffix.lower()
    rel_path = f"assets/{sha256[:2]}/{sha256}/original{ext}"
    abs_path = get_library_root() / rel_path

    if abs_path.exists():
        return rel_path

    abs_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = abs_path.with_suffix(".tmp")
    tmp.write_bytes(content)
    tmp.rename(abs_path)
    return rel_path


def get_absolute_path(storage_path: str) -> Path:
    return get_library_root() / storage_path
