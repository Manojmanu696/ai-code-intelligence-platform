from __future__ import annotations

from pathlib import Path

from app.services.runners.bandit_runner import run_bandit
from app.services.runners.flake8_runner import run_flake8
from app.services.runners.runner_utils import write_json


def run_tools_for_scan(scan_path: Path) -> None:
    """
    Synchronous pipeline step:
    input/ -> run flake8 + bandit -> write to raw/
    """
    input_dir = scan_path / "input"
    raw_dir = scan_path / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    warnings_file = raw_dir / "runner_warnings.json"

    # Basic sanity check
    if not input_dir.exists():
        write_json(warnings_file, {"error": "input directory not found", "input_dir": str(input_dir)})
        return

    run_flake8(
        input_dir=input_dir,
        out_json=raw_dir / "flake8.json",
        warnings_json=warnings_file,
    )

    run_bandit(
        input_dir=input_dir,
        out_json=raw_dir / "bandit.json",
        warnings_json=warnings_file,
    )

    write_json(raw_dir / "runner_done.json", {"status": "DONE"})