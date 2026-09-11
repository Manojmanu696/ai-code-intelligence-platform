from __future__ import annotations

import json
from pathlib import Path

from app.services.runners.runner_utils import run_command, write_json


def _java_loc(input_dir: Path) -> int:
    total = 0
    for path in input_dir.rglob("*.java"):
        try:
            total += len(path.read_text(encoding="utf-8", errors="replace").splitlines())
        except OSError:
            continue
    return total


def run_pmd(input_dir: Path, out_json: Path, warnings_json: Path) -> None:
    """Run PMD against Java source files and persist its JSON report."""
    java_files = list(input_dir.rglob("*.java"))
    if not java_files:
        write_json(out_json, {"pmdVersion": None, "files": [], "loc": 0})
        return

    cmd = [
        "pmd",
        "check",
        "-d",
        str(input_dir),
        "-R",
        "rulesets/java/quickstart.xml,category/java/security.xml",
        "-f",
        "json",
        "--no-fail-on-violation",
    ]

    result = run_command(cmd, timeout_sec=180)
    loc = _java_loc(input_dir)

    if result["stdout"].strip():
        try:
            parsed = json.loads(result["stdout"])
            if not isinstance(parsed, dict):
                parsed = {"files": []}
            parsed["loc"] = loc
            write_json(out_json, parsed)
        except Exception:
            write_json(
                warnings_json,
                {
                    "tool": "pmd",
                    "warning": "Invalid JSON output",
                    "stderr": result.get("stderr", ""),
                },
            )
            write_json(out_json, {"pmdVersion": None, "files": [], "loc": loc})
    else:
        write_json(out_json, {"pmdVersion": None, "files": [], "loc": loc})

    if result["stderr"].strip() and result["returncode"] not in (0, 4):
        write_json(
            warnings_json,
            {
                "tool": "pmd",
                "warning": "PMD returned a non-standard status",
                **result,
            },
        )
