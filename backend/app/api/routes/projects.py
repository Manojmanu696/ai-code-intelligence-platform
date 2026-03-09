from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query

router = APIRouter()


def _safe_project_key(project_key: str) -> str:
    # keep it simple; your history writer already decides keys,
    # but this helps avoid weird paths
    return project_key.strip()


def _trend_path(storage_root: Path, project_key: str) -> Path:
    # storage_root = backend/storage
    return storage_root / "history" / project_key / "trend.jsonl"


def _read_last_n_jsonl(p: Path, limit: int) -> List[Dict[str, Any]]:
    if not p.exists():
        return []
    lines = p.read_text(encoding="utf-8").splitlines()
    lines = [ln for ln in lines if ln.strip()]
    tail = lines[-limit:] if limit > 0 else lines
    out: List[Dict[str, Any]] = []
    for ln in tail:
        try:
            out.append(json.loads(ln))
        except Exception:
            continue
    return out


@router.get("/projects/{project_key}/trend")
def get_project_trend(project_key: str, limit: int = Query(30, ge=1, le=200)) -> Dict[str, Any]:
    """
    Canonical endpoint used by frontend:
      GET /projects/<project_key>/trend?limit=30
    """
    storage_root = Path(__file__).resolve().parents[3] / "storage"  # backend/storage
    key = _safe_project_key(project_key)
    p = _trend_path(storage_root, key)

    points = _read_last_n_jsonl(p, limit=limit)
    return {"project_key": key, "limit": limit, "points": points}


@router.get("/projects/trend")
def get_project_trend_query(
    project_key: str = Query(...),
    limit: int = Query(30, ge=1, le=200),
) -> Dict[str, Any]:
    """
    Compatibility alias (some frontend tries this):
      GET /projects/trend?project_key=...&limit=30
    """
    return get_project_trend(project_key=project_key, limit=limit)


@router.get("/scans/trend")
def get_scans_trend(
    project_key: str = Query(...),
    limit: int = Query(30, ge=1, le=200),
) -> Dict[str, Any]:
    """
    Compatibility alias (frontend tries this too):
      GET /scans/trend?project_key=...&limit=30
    """
    return get_project_trend(project_key=project_key, limit=limit)