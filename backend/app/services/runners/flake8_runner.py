from __future__ import annotations

import json
from pathlib import Path

from app.services.runners.runner_utils import run_command, write_json


def run_flake8(input_dir: Path, out_json: Path, warnings_json: Path) -> None:
    """
    Runs flake8 only against Python source files and writes JSON output.
    Java and other non-Python files are intentionally excluded.
    """
    python_files = sorted(
        path for path in input_dir.rglob("*.py") if path.is_file()
    )

    if not python_files:
        write_json(out_json, {})
        return

    cmd = [
        "flake8",
        *[str(path) for path in python_files],
        "--format=json",
        "--exit-zero",
    ]

    result = run_command(cmd, timeout_sec=120)

    if result["stdout"].strip():
        try:
            parsed = json.loads(result["stdout"])
            write_json(out_json, parsed)
        except Exception:
            write_json(
                warnings_json,
                {"tool": "flake8", "warning": "Invalid JSON output", **result},
            )
    else:
        write_json(out_json, {})

    if not result["ok"] and result["stderr"].strip():
        write_json(
            warnings_json,
            {"tool": "flake8", "warning": "Non-zero return", **result},
        )