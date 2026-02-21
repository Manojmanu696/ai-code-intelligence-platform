from __future__ import annotations

import json
from pathlib import Path

from app.services.runners.runner_utils import run_command, write_json


def run_flake8(input_dir: Path, out_json: Path, warnings_json: Path) -> None:
    """
    Runs flake8 against the input directory and writes JSON output.
    Uses flake8-json plugin formatter ("--format=json").
    """
    cmd = [
        "flake8",
        str(input_dir),
        "--format=json",
        "--exit-zero",  # do not fail pipeline even if issues exist
    ]

    result = run_command(cmd, timeout_sec=120)

    # flake8-json prints JSON to stdout
    if result["stdout"].strip():
        try:
            parsed = json.loads(result["stdout"])
            write_json(out_json, parsed)
        except Exception:
            # fallback: save raw stdout if parsing fails
            write_json(warnings_json, {"tool": "flake8", "warning": "Invalid JSON output", **result})
    else:
        write_json(out_json, {})  # no issues found (or no output)

    if not result["ok"] and result["stderr"].strip():
        write_json(warnings_json, {"tool": "flake8", "warning": "Non-zero return", **result})