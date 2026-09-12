from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from app.services.runners.bandit_runner import run_bandit
from app.services.runners.flake8_runner import run_flake8
from app.services.runners.pmd_runner import run_pmd
from app.services.runners.cppcheck_runner import run_cppcheck
from app.services.runners.runner_utils import write_json
from app.services.processors.normalize import normalize_flake8, normalize_bandit, build_unified_issues
from app.services.processors.normalize_pmd import normalize_pmd
from app.services.processors.normalize_cppcheck import normalize_cppcheck
from app.services.processors.metrics import build_metrics
from app.services.scoring.scoring import compute_score
from app.services.history.trend import append_trend_point
from app.services.ai.generator import generate_ai_outputs


def _read_json(p: Path) -> Optional[Any]:
    """Read JSON from a file if the file exists."""
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def _write_json(p: Path, data: Any) -> None:
    """Create parent folders and write data as formatted JSON."""
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _to_scan_rel_path(path_str: str, scan_path: Path) -> str:
    """Convert an absolute scan file path into a relative project path."""
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
    """Combine analyzer reports, metrics, score, AI output, and history."""
    raw_dir = scan_path / "raw"
    norm_dir = scan_path / "normalized"
    metrics_dir = scan_path / "metrics"
    score_dir = scan_path / "score"

    flake8_norm = normalize_flake8(_read_json(raw_dir / "flake8.json") or {})
    bandit_norm = normalize_bandit(_read_json(raw_dir / "bandit.json") or {})
    pmd_norm = normalize_pmd(_read_json(raw_dir / "pmd.json") or {})
    cppcheck_norm = normalize_cppcheck(_read_json(raw_dir / "cppcheck.json") or {})

    _write_json(norm_dir / "flake8.normalized.json", flake8_norm)
    _write_json(norm_dir / "bandit.normalized.json", bandit_norm)
    _write_json(norm_dir / "pmd.normalized.json", pmd_norm)
    _write_json(norm_dir / "cppcheck.normalized.json", cppcheck_norm)

    unified = build_unified_issues(flake8_norm, bandit_norm, pmd_norm, cppcheck_norm)
    for item in unified:
        if isinstance(item, dict) and item.get("file"):
            item["file"] = _to_scan_rel_path(str(item["file"]), scan_path)
    _write_json(norm_dir / "unified_issues.json", unified)

    metrics = build_metrics([flake8_norm, bandit_norm, pmd_norm, cppcheck_norm], unified_issues=unified)
    _write_json(metrics_dir / "metrics.json", metrics)

    score = compute_score(metrics)
    _write_json(score_dir / "score.json", score)

    generate_ai_outputs(scan_path=scan_path, unified_issues=unified, metrics=metrics, score=score)

    ingestion = _read_json(raw_dir / "ingestion.json")
    storage_root = scan_path.parent.parent
    trend_file = append_trend_point(storage_root=storage_root, scan_id=scan_path.name, ingestion=ingestion, metrics=metrics, score=score)

    return {
        "normalized_files": [
            str(norm_dir / "flake8.normalized.json"),
            str(norm_dir / "bandit.normalized.json"),
            str(norm_dir / "pmd.normalized.json"),
            str(norm_dir / "cppcheck.normalized.json"),
            str(norm_dir / "unified_issues.json"),
        ],
        "metrics_file": str(metrics_dir / "metrics.json"),
        "score_file": str(score_dir / "score.json"),
        "ai_file": str(scan_path / "ai" / "ai_summary.json"),
        "trend_file": str(trend_file),
        "final_score": score.get("final_score"),
    }


def run_tools_for_scan(scan_path: Path) -> Dict[str, Any]:
    """Run all configured static analyzers and then postprocess the scan."""
    input_dir = scan_path / "input"
    raw_dir = scan_path / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    warnings_file = raw_dir / "runner_warnings.json"

    if not input_dir.exists():
        write_json(warnings_file, {"error": "input directory not found", "input_dir": str(input_dir)})
        return {"status": "FAILED", "reason": "NO_INPUT_DIR"}

    run_flake8(input_dir=input_dir, out_json=raw_dir / "flake8.json", warnings_json=warnings_file)
    run_bandit(input_dir=input_dir, out_json=raw_dir / "bandit.json", warnings_json=warnings_file)
    run_pmd(input_dir=input_dir, out_json=raw_dir / "pmd.json", warnings_json=warnings_file)
    run_cppcheck(input_dir=input_dir, out_json=raw_dir / "cppcheck.json", warnings_json=warnings_file)
    write_json(raw_dir / "runner_done.json", {"status": "DONE"})

    try:
        post = postprocess_scan(scan_path)
        return {"status": "DONE", "postprocess": post}
    except Exception as e:
        write_json(raw_dir / "postprocess_error.json", {"error": str(e)})
        return {"status": "FAILED", "reason": "POSTPROCESS_ERROR", "error": str(e)}
