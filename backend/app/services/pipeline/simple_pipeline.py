from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from app.services.runners.bandit_runner import run_bandit
from app.services.runners.flake8_runner import run_flake8
from app.services.runners.runner_utils import write_json

from app.services.processors.normalize import normalize_flake8, normalize_bandit
from app.services.processors.metrics import build_metrics
from app.services.scoring.scoring import compute_score


# -----------------------------
# JSON helpers
# -----------------------------
def _read_json(p: Path) -> Optional[Any]:
    """Read JSON from file. Returns None if file doesn't exist."""
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def _write_json(p: Path, data: Any) -> None:
    """Write JSON to file, creating parent directories if needed."""
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")


# -----------------------------
# Post-processing step
# raw -> normalized -> metrics -> score
# -----------------------------
def postprocess_scan(scan_path: Path) -> Dict[str, Any]:
    """
    Uses raw outputs written by runners:
      raw/flake8.json
      raw/bandit.json

    Produces:
      normalized/flake8.normalized.json
      normalized/bandit.normalized.json
      metrics/metrics.json
      score/score.json
    """
    raw_dir = scan_path / "raw"
    norm_dir = scan_path / "normalized"
    metrics_dir = scan_path / "metrics"
    score_dir = scan_path / "score"

    flake8_raw = _read_json(raw_dir / "flake8.json") or []
    bandit_raw = _read_json(raw_dir / "bandit.json") or {}

    flake8_norm = normalize_flake8(flake8_raw)
    bandit_norm = normalize_bandit(bandit_raw)

    _write_json(norm_dir / "flake8.normalized.json", flake8_norm)
    _write_json(norm_dir / "bandit.normalized.json", bandit_norm)

    metrics = build_metrics([flake8_norm, bandit_norm])
    _write_json(metrics_dir / "metrics.json", metrics)

    score = compute_score(metrics)
    _write_json(score_dir / "score.json", score)

    return {
        "normalized_files": [
            str(norm_dir / "flake8.normalized.json"),
            str(norm_dir / "bandit.normalized.json"),
        ],
        "metrics_file": str(metrics_dir / "metrics.json"),
        "score_file": str(score_dir / "score.json"),
        "final_score": score.get("final_score"),
    }


# -----------------------------
# Main synchronous pipeline
# -----------------------------
def run_tools_for_scan(scan_path: Path) -> Dict[str, Any]:
    """
    Synchronous scan pipeline (MVP):
      input/ -> run flake8 + bandit -> write raw/
              -> postprocess -> write normalized/metrics/score

    Returns a summary dict to be used by your API if needed.
    """
    input_dir = scan_path / "input"
    raw_dir = scan_path / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    warnings_file = raw_dir / "runner_warnings.json"

    # Sanity check: input exists
    if not input_dir.exists():
        write_json(
            warnings_file,
            {
                "error": "input directory not found",
                "input_dir": str(input_dir),
            },
        )
        return {"status": "FAILED", "reason": "NO_INPUT_DIR"}

    # 1) Run tools -> raw/
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

    # 2) Postprocess raw -> normalized/metrics/score
    try:
        post = postprocess_scan(scan_path)
        return {"status": "DONE", "postprocess": post}
    except Exception as e:
        # If postprocess fails, record it (so debugging is easy)
        write_json(
            raw_dir / "postprocess_error.json",
            {"error": str(e)},
        )
        return {"status": "FAILED", "reason": "POSTPROCESS_ERROR", "error": str(e)}