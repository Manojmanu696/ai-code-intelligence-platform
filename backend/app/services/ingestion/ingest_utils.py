from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


DEFAULT_EXCLUDED_DIRS = {
    ".git",
    "node_modules",
    "dist",
    "build",
    ".venv",
    "venv",
    "__pycache__",
    ".mypy_cache",
    "coverage",
    ".pytest_cache",
    ".next",
    "target",
}

DEFAULT_ALLOWED_EXTENSIONS = {".py"}
DEFAULT_MAX_FILE_SIZE_BYTES = 1 * 1024 * 1024  # 1MB


@dataclass(frozen=True)
class IngestRules:
    excluded_dirs: set[str] = None  # type: ignore[assignment]
    allowed_extensions: set[str] = None  # type: ignore[assignment]
    max_file_size_bytes: int = DEFAULT_MAX_FILE_SIZE_BYTES

    def __post_init__(self) -> None:
        object.__setattr__(self, "excluded_dirs", self.excluded_dirs or set(DEFAULT_EXCLUDED_DIRS))
        object.__setattr__(self, "allowed_extensions", self.allowed_extensions or set(DEFAULT_ALLOWED_EXTENSIONS))


def is_excluded_path(path: Path, rules: IngestRules) -> bool:
    # Exclude any path that contains an excluded dir segment anywhere
    for part in path.parts:
        if part in rules.excluded_dirs:
            return True
    return False


def is_allowed_file(path: Path, rules: IngestRules) -> bool:
    if path.suffix.lower() not in rules.allowed_extensions:
        return False
    try:
        if path.stat().st_size > rules.max_file_size_bytes:
            return False
    except FileNotFoundError:
        return False
    return True