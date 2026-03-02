from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Query

router = APIRouter()

# backend/app/api/routes/projects.py -> parents[3] = backend/
PROJECT_ROOT = Path(__file__).resolve().parents[3]
STORAGE_ROOT = PROJECT_ROOT / "storage"


@router.get("/projects/{project_key}/trend")
def get_trend(project_key: str, limit: int = Query(100, ge=1, le=1000)) -> Dict[str, Any]:
    safe_key = project_key.replace("/", "__").replace(":", "__")
    trend_file = STORAGE_ROOT / "history" / safe_key / "trend.jsonl"

    if not trend_file.exists():
        raise HTTPException(status_code=404, detail="No trend data for this project_key yet")

    lines = trend_file.read_text(encoding="utf-8").splitlines()
    lines = lines[-limit:]

    points: List[Dict[str, Any]] = []
    for ln in lines:
        try:
            points.append(json.loads(ln))
        except Exception:
            continue

    return {"project_key": project_key, "points": points}