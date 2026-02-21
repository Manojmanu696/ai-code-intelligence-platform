from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any


def run_command(cmd: list[str], timeout_sec: int = 60) -> dict[str, Any]:
    """
    Runs a CLI command with timeout and captures stdout/stderr.
    Returns a structured dict so we can save warnings/errors cleanly.
    """
    try:
        p = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            check=False,
        )
        return {
            "ok": p.returncode == 0,
            "returncode": p.returncode,
            "stdout": p.stdout,
            "stderr": p.stderr,
            "cmd": cmd,
        }
    except subprocess.TimeoutExpired:
        return {
            "ok": False,
            "returncode": None,
            "stdout": "",
            "stderr": f"Timeout after {timeout_sec}s",
            "cmd": cmd,
        }


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))