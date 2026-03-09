from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from app.services.runners.bandit_runner import run_bandit
from app.services.runners.flake8_runner import run_flake8
from app.services.runners.runner_utils import write_json

from app.services.processors.normalize import (
    normalize_flake8,
    normalize_bandit,
    build_unified_issues,
)
from app.services.processors.metrics import build_metrics
from app.services.scoring.scoring import compute_score

from app.services.history.trend import append_trend_point
from app.services.ai.generator import generate_ai_outputs


def _read_json(p: Path) -> Optional[Any]:
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def _write_json(p: Path, data: Any) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _to_scan_rel_path(path_str: str, scan_path: Path) -> str:
    if not path_str:
        return path_str
    try:
        return Path(path_str).relative_to(scan_path).as_posix()
    except Exception:
        s = str(path_str)
        marker = "/input/"
        if marker in s:
            return "input/" + s.split(marker, 1)[1]
        return s


def postprocess_scan(scan_path: Path) -> Dict[str, Any]:
    raw_dir = scan_path / "raw"
    norm_dir = scan_path / "normalized"
    metrics_dir = scan_path / "metrics"
    score_dir = scan_path / "score"

    # Read raw outputs
    flake8_raw = _read_json(raw_dir / "flake8.json") or {}
    bandit_raw = _read_json(raw_dir / "bandit.json") or {}

    # Normalize per-tool
    flake8_norm = normalize_flake8(flake8_raw)
    bandit_norm = normalize_bandit(bandit_raw)

    # Write per-tool normalized
    _write_json(norm_dir / "flake8.normalized.json", flake8_norm)
    _write_json(norm_dir / "bandit.normalized.json", bandit_norm)

    # Unified issues
    unified = build_unified_issues(flake8_norm, bandit_norm)

    # Fix unified file paths to scan-relative (input/...)
    for it in unified:
        if isinstance(it, dict) and it.get("file"):
            it["file"] = _to_scan_rel_path(str(it["file"]), scan_path)

    _write_json(norm_dir / "unified_issues.json", unified)

    # Metrics uses unified issues
    metrics = build_metrics([flake8_norm, bandit_norm], unified_issues=unified)
    _write_json(metrics_dir / "metrics.json", metrics)

    # Score
    score = compute_score(metrics)
    _write_json(score_dir / "score.json", score)

    # ✅ AI Summary (rule-based now, LLM later)
    # This writes: scan_path/ai/ai_summary.json
    generate_ai_outputs(
        scan_path=scan_path,
        unified_issues=unified,
        metrics=metrics,
        score=score,
    )

    # ✅ Trend append
    ingestion = _read_json(raw_dir / "ingestion.json")
    storage_root = scan_path.parent.parent  # .../backend/storage
    trend_file = append_trend_point(
        storage_root=storage_root,
        scan_id=scan_path.name,
        ingestion=ingestion,
        metrics=metrics,
        score=score,
    )

    return {
        "normalized_files": [
            str(norm_dir / "flake8.normalized.json"),
            str(norm_dir / "bandit.normalized.json"),
            str(norm_dir / "unified_issues.json"),
        ],
        "metrics_file": str(metrics_dir / "metrics.json"),
        "score_file": str(score_dir / "score.json"),
        "ai_file": str(scan_path / "ai" / "ai_summary.json"),
        "trend_file": str(trend_file),
        "final_score": score.get("final_score"),
    }


def run_tools_for_scan(scan_path: Path) -> Dict[str, Any]:
    input_dir = scan_path / "input"
    raw_dir = scan_path / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    warnings_file = raw_dir / "runner_warnings.json"

    if not input_dir.exists():
        write_json(
            warnings_file,
            {"error": "input directory not found", "input_dir": str(input_dir)},
        )
        return {"status": "FAILED", "reason": "NO_INPUT_DIR"}

    # Run tools -> raw/
    run_flake8(input_dir=input_dir, out_json=raw_dir / "flake8.json", warnings_json=warnings_file)
    run_bandit(input_dir=input_dir, out_json=raw_dir / "bandit.json", warnings_json=warnings_file)

    write_json(raw_dir / "runner_done.json", {"status": "DONE"})

    # Postprocess
    try:
        post = postprocess_scan(scan_path)
        return {"status": "DONE", "postprocess": post}
    except Exception as e:
        write_json(raw_dir / "postprocess_error.json", {"error": str(e)})
        return {"status": "FAILED", "reason": "POSTPROCESS_ERROR", "error": str(e)}