from __future__ import annotations
from pathlib import Path

EXCLUDE_DIRS = {
    ".git", "node_modules", "dist", "build", ".venv", "venv", "__pycache__",
    ".mypy_cache", "coverage", ".pytest_cache", ".next", "target",
}

ALLOWED_EXTENSIONS = {".py"}  # MVP locked
MAX_FILE_SIZE_BYTES = 1_048_576  # 1MB


def should_skip_dir(dir_name: str) -> bool:
    return dir_name in EXCLUDE_DIRS


def is_allowed_file(p: Path) -> bool:
    if not p.is_file():
        return False
    if p.suffix.lower() not in ALLOWED_EXTENSIONS:
        return False
    try:
        if p.stat().st_size > MAX_FILE_SIZE_BYTES:
            return False
    except OSError:
        return False
    return True