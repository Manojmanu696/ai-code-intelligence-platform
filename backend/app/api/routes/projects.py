from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, Query

from app.services.history.trend import read_trend_points

router = APIRouter()


def _storage_root() -> Path:
    return Path(__file__).resolve().parents[3] / "storage"


@router.get("/projects/{project_key}/trend")
def get_project_trend(
    project_key: str,
    limit: int = Query(30, ge=1, le=200),
) -> Dict[str, Any]:
    points = read_trend_points(
        storage_root=_storage_root(),
        project_key=project_key,
        limit=limit,
    )
    return {
        "project_key": project_key,
        "limit": limit,
        "points": points,
    }


@router.get("/projects/trend")
def get_project_trend_query(
    project_key: str = Query(...),
    limit: int = Query(30, ge=1, le=200),
) -> Dict[str, Any]:
    return get_project_trend(project_key=project_key, limit=limit)


@router.get("/scans/trend")
def get_scans_trend(
    project_key: str = Query(...),
    limit: int = Query(30, ge=1, le=200),
) -> Dict[str, Any]:
    return get_project_trend(project_key=project_key, limit=limit)