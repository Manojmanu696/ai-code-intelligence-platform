from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse


def _safe_dir_key(project_key: str) -> str:
    # folder-safe key (supports github:owner/repo)
    return (project_key or "unknown").replace("/", "__").replace(":", "__").strip() or "unknown"


def _project_key_from_ingestion(ingestion: Optional[Dict[str, Any]]) -> str:
    """
    ✅ KEY RULE (MVP):
    - ZIP scans: use ingestion["root_used"] if present (ex: ai-code-intelligence-platform-main)
    - GitHub scans: github:owner/repo if available
    - Fallback: zip filename base
    """
    if not isinstance(ingestion, dict):
        return "local-unknown"

    # ✅ ZIP: best key is root_used (what your ingestion already produces)
    root_used = ingestion.get("root_used")
    if isinstance(root_used, str) and root_used.strip():
        return root_used.strip()

    source = ingestion.get("source")
    if isinstance(source, dict):
        stype = (source.get("type") or "").lower()

        if stype == "github":
            owner = source.get("owner")
            repo = source.get("repo")
            if owner and repo:
                return f"github:{owner}/{repo}"

            repo_url = source.get("repo_url")
            if isinstance(repo_url, str) and "github.com" in repo_url:
                try:
                    p = urlparse(repo_url)
                    parts = [x for x in p.path.split("/") if x]
                    if len(parts) >= 2:
                        return f"github:{parts[0]}/{parts[1].replace('.git','')}"
                except Exception:
                    pass

        if stype == "zip":
            fname = source.get("filename")
            if isinstance(fname, str) and fname.strip():
                base = Path(fname).name
                if base.lower().endswith(".zip"):
                    base = base[:-4]
                return base.strip() or "local-zip"

    return "local-unknown"


def append_trend_point(
    *,
    storage_root: Path,
    scan_id: str,
    ingestion: Optional[Dict[str, Any]],
    metrics: Optional[Dict[str, Any]],
    score: Optional[Dict[str, Any]],
) -> Path:
    project_key = _project_key_from_ingestion(ingestion)
    safe_key = _safe_dir_key(project_key)

    hist_dir = storage_root / "history" / safe_key
    hist_dir.mkdir(parents=True, exist_ok=True)

    trend_file = hist_dir / "trend.jsonl"

    totals = (metrics or {}).get("totals") or {}
    by_sev = totals.get("by_severity") or {}

    point = {
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "project_key": project_key,
        "scan_id": scan_id,
        "loc": int(totals.get("loc") or 0),
        "issues": int(totals.get("issues") or 0),
        "by_severity": {
            "low": int(by_sev.get("low") or 0),
            "medium": int(by_sev.get("medium") or 0),
            "high": int(by_sev.get("high") or 0),
        },
        "final_score": (score or {}).get("final_score"),
        "penalty": (score or {}).get("penalty"),
        "method": (score or {}).get("method"),
    }

    with trend_file.open("a", encoding="utf-8") as f:
        f.write(json.dumps(point, ensure_ascii=False) + "\n")

    return trend_file


def read_trend_points(
    *,
    storage_root: Path,
    project_key: str,
    limit: int = 30,
) -> List[Dict[str, Any]]:
    safe_key = _safe_dir_key(project_key)
    trend_file = storage_root / "history" / safe_key / "trend.jsonl"
    if not trend_file.exists():
        return []

    lines = trend_file.read_text(encoding="utf-8").splitlines()
    lines = [l.strip() for l in lines if l.strip()]
    if not lines:
        return []

    lines = lines[-max(1, int(limit)) :]

    out: List[Dict[str, Any]] = []
    for line in lines:
        try:
            out.append(json.loads(line))
        except Exception:
            continue
    return out