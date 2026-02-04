from __future__ import annotations

from pathlib import Path, PurePosixPath


def safe_upload_path(base_dir: Path, filename: str) -> Path:
    base = base_dir.resolve()
    normalized = filename.replace("\\", "/").lstrip("/")
    pure = PurePosixPath(normalized)
    parts = [part for part in pure.parts if part not in ("", ".", "..")]
    if not parts:
        raise ValueError("Invalid filename")
    candidate = (base / Path(*parts)).resolve()
    if not candidate.is_relative_to(base):
        raise ValueError("Invalid filename path")
    return candidate
