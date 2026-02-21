from __future__ import annotations

from pathlib import Path

from app.services.runners.runner_utils import run_command, write_json


def run_bandit(input_dir: Path, out_json: Path, warnings_json: Path) -> None:
    """
    Runs bandit recursively on input directory and writes JSON output.
    """
    cmd = [
        "bandit",
        "-r",
        str(input_dir),
        "-f",
        "json",
        "-q",        # quieter output
        "--exit-zero"  # do not fail pipeline due to findings
    ]

    result = run_command(cmd, timeout_sec=180)

    # bandit json is in stdout
    if result["stdout"].strip():
        try:
            write_json(out_json, result["stdout"] and __import__("json").loads(result["stdout"]))
        except Exception:
            write_json(warnings_json, {"tool": "bandit", "warning": "Invalid JSON output", **result})
            write_json(out_json, {})
    else:
        write_json(out_json, {})

    if not result["ok"] and result["stderr"].strip():
        write_json(warnings_json, {"tool": "bandit", "warning": "Non-zero return", **result})