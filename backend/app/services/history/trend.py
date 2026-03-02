from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import urlparse


def _safe_project_key_from_ingestion(ingestion: Optional[Dict[str, Any]]) -> str:
    if not isinstance(ingestion, dict):
        return "local:unknown"

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
                return f"local:{base}"

    return "local:unknown"


def append_trend_point(
    *,
    storage_root: Path,
    scan_id: str,
    ingestion: Optional[Dict[str, Any]],
    metrics: Optional[Dict[str, Any]],
    score: Optional[Dict[str, Any]],
) -> Path:
    project_key = _safe_project_key_from_ingestion(ingestion)

    safe_key = project_key.replace("/", "__").replace(":", "__")
    hist_dir = storage_root / "history" / safe_key
    hist_dir.mkdir(parents=True, exist_ok=True)

    trend_file = hist_dir / "trend.jsonl"

    totals = (metrics or {}).get("totals") or {}
    by_sev = totals.get("by_severity") or {}

    point = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "project_key": project_key,
        "scan_id": scan_id,
        "loc": totals.get("loc", 0),
        "issues": totals.get("issues", 0),
        "by_severity": {
            "low": by_sev.get("low", 0),
            "medium": by_sev.get("medium", 0),
            "high": by_sev.get("high", 0),
        },
        "final_score": (score or {}).get("final_score"),
        "penalty": (score or {}).get("penalty"),
        "method": (score or {}).get("method"),
    }

    with trend_file.open("a", encoding="utf-8") as f:
        f.write(json.dumps(point) + "\n")

    return trend_file