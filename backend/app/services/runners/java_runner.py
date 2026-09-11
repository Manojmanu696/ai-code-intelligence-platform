from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Dict

from app.services.runners.runner_utils import run_command, write_json


def _java_loc(input_dir: Path) -> int:
    total = 0
    for path in input_dir.rglob("*.java"):
        try:
            total += len(path.read_text(encoding="utf-8", errors="replace").splitlines())
        except OSError:
            continue
    return total


def run_java_analysis(
    input_dir: Path,
    out_json: Path,
    warnings_json: Path,
) -> None:
    """Run PMD on Java source files and persist normalized raw JSON input."""
    loc = _java_loc(input_dir)
    java_files = list(input_dir.rglob("*.java"))

    if not java_files:
        write_json(out_json, {"pmdVersion": None, "files": [], "loc": 0})
        return

    pmd_bin = shutil.which("pmd")
    if not pmd_bin:
        write_json(
            warnings_json,
            {
                "tool": "pmd",
                "warning": "PMD executable not found. Install PMD and ensure it is on PATH.",
            },
        )
        write_json(out_json, {"pmdVersion": None, "files": [], "loc": loc})
        return

    cmd = [
        pmd_bin,
        "check",
        "--dir",
        str(input_dir),
        "--rulesets",
        "category/java/errorprone.xml,category/java/security.xml,category/java/bestpractices.xml",
        "--format",
        "json",
        "--no-fail-on-violation",
    ]

    result: Dict[str, Any] = run_command(cmd, timeout_sec=180)

    stdout = str(result.get("stdout") or "").strip()
    stderr = str(result.get("stderr") or "").strip()

    if stdout:
        try:
            parsed = json.loads(stdout)
            if not isinstance(parsed, dict):
                parsed = {"pmdVersion": None, "files": []}
            parsed["loc"] = loc
            write_json(out_json, parsed)
        except json.JSONDecodeError as exc:
            write_json(
                warnings_json,
                {
                    "tool": "pmd",
                    "warning": f"PMD returned non-JSON output: {exc}",
                    "stderr": stderr,
                },
            )
            write_json(out_json, {"pmdVersion": None, "files": [], "loc": loc})
    else:
        write_json(out_json, {"pmdVersion": None, "files": [], "loc": loc})

    if stderr and int(result.get("returncode", 0) or 0) not in (0, 4):
        write_json(
            warnings_json,
            {
                "tool": "pmd",
                "warning": "PMD execution returned an unexpected status.",
                "returncode": result.get("returncode"),
                "stderr": stderr,
            },
        )
