from __future__ import annotations

import json
import re
import shutil
import tempfile
import urllib.request
import zipfile
from pathlib import Path
from typing import Any, Dict, Optional
from uuid import uuid4

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from pydantic import BaseModel

from app.services.pipeline.simple_pipeline import run_tools_for_scan

router = APIRouter()

# Project root = .../final-folder/backend/app/api/routes/scans.py
# parents[3] = backend/
PROJECT_ROOT = Path(__file__).resolve().parents[3]
BASE_STORAGE = PROJECT_ROOT / "storage" / "scans"
BASE_STORAGE.mkdir(parents=True, exist_ok=True)

# -----------------------------
# MVP Ignore/Exclude Rules (LOCKED)
# -----------------------------
EXCLUDE_DIRS = {
    ".git",
    "node_modules",
    "dist",
    "build",
    ".venv",
    "venv",
    "__pycache__",
    ".mypy_cache",
    "coverage",
    ".pytest_cache",
    ".next",
    "target",
    "__MACOSX",
}

ALLOWED_EXTENSIONS = {".py"}  # MVP locked: Python-only
MAX_FILE_SIZE_BYTES = 1_048_576  # 1MB


# -----------------------------
# Models
# -----------------------------
class PastePayload(BaseModel):
    filename: str
    content: str


class GitHubPayload(BaseModel):
    repo_url: str
    ref: str = "main"


# -----------------------------
# JSON helpers
# -----------------------------
def _read_json(p: Path) -> Optional[Any]:
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def _write_json(p: Path, data: Any) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _to_rel_path(path_str: str, scan_path: Path) -> str:
    """
    Convert an absolute path inside this scan to a clean relative path.

    Example:
      /Users/.../storage/scans/<scan_id>/input/test.py -> input/test.py
    """
    if not path_str:
        return path_str

    try:
        p = Path(path_str)
        rel = p.relative_to(scan_path)
        return rel.as_posix()
    except Exception:
        pass

    s = str(path_str)
    marker = "/input/"
    if marker in s:
        return "input/" + s.split(marker, 1)[1]

    return s


def _slugify(s: str) -> str:
    """
    Stable project key generator.
    Example:
      'My Project' -> 'my-project'
    """
    s = (s or "").strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"-{2,}", "-", s).strip("-")
    return s or "project"


def _normalize_issue_paths(items: Any, scan_path: Path) -> Any:
    if not isinstance(items, list):
        return items

    for item in items:
        if isinstance(item, dict) and item.get("file"):
            item["file"] = _to_rel_path(str(item["file"]), scan_path)

    return items


def _normalize_ai_payload(ai_obj: Any, scan_path: Path) -> Any:
    if not isinstance(ai_obj, dict):
        return ai_obj

    top_risky = ai_obj.get("top_risky_issues")
    if isinstance(top_risky, list):
        for item in top_risky:
            if isinstance(item, dict) and item.get("file"):
                item["file"] = _to_rel_path(str(item["file"]), scan_path)

    issues_enriched = ai_obj.get("issues_enriched")
    if isinstance(issues_enriched, list):
        for item in issues_enriched:
            if isinstance(item, dict) and item.get("file"):
                item["file"] = _to_rel_path(str(item["file"]), scan_path)

    return ai_obj


# -----------------------------
# Ingestion helpers
# -----------------------------
def _should_skip_dir(name: str) -> bool:
    return name in EXCLUDE_DIRS


def _is_allowed_file(p: Path) -> bool:
    if not p.is_file():
        return False

    if p.suffix.lower() not in ALLOWED_EXTENSIONS:
        return False

    try:
        if p.stat().st_size > MAX_FILE_SIZE_BYTES:
            return False
    except OSError:
        return False

    return True


def _has_any_python_file(input_dir: Path) -> bool:
    return any(p.suffix.lower() == ".py" for p in input_dir.rglob("*.py"))


def _ingest_extracted_tree(extract_dir: Path, input_dir: Path) -> Dict[str, Any]:
    """
    Walk extracted tree, apply exclude rules + allowed extensions + max size,
    and copy into input/ while preserving relative paths.

    If the zip extracts into a single top-level folder (common GitHub zips),
    strip that folder so paths become clean:
      backend/... instead of repo-main/backend/...
    """

    def _effective_root(root: Path) -> Path:
        try:
            children = list(root.iterdir())
        except Exception:
            return root

        visible = []
        for child in children:
            name = child.name
            if _should_skip_dir(name):
                continue
            if name == "__MACOSX":
                continue
            visible.append(child)

        dirs = [p for p in visible if p.is_dir()]
        files = [p for p in visible if p.is_file()]

        if len(files) == 0 and len(dirs) == 1:
            return dirs[0]

        return root

    kept = 0
    skipped = 0
    skipped_samples: list[dict[str, str]] = []

    base = _effective_root(extract_dir)

    for p in base.rglob("*"):
        if any(_should_skip_dir(part) for part in p.parts):
            continue

        if p.is_dir():
            continue

        if not _is_allowed_file(p):
            skipped += 1

            if len(skipped_samples) < 25:
                reason = "not_allowed"
                try:
                    if p.stat().st_size > MAX_FILE_SIZE_BYTES:
                        reason = "too_large"
                except OSError:
                    reason = "stat_failed"

                try:
                    rel_name = str(p.relative_to(base))
                except Exception:
                    rel_name = str(p)

                skipped_samples.append({"file": rel_name, "reason": reason})
            continue

        rel = p.relative_to(base)
        dest = input_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, dest)
        kept += 1

    return {
        "kept": kept,
        "skipped": skipped,
        "max_file_size_bytes": MAX_FILE_SIZE_BYTES,
        "allowed_extensions": sorted(ALLOWED_EXTENSIONS),
        "excluded_dirs": sorted(EXCLUDE_DIRS),
        "skipped_samples": skipped_samples,
        "stripped_single_root": bool(base != extract_dir),
        "root_used": base.name,
    }


# -----------------------------
# GitHub download helpers
# -----------------------------
def _parse_github_repo(repo_url: str) -> tuple[str, str]:
    """
    Accepts:
      https://github.com/owner/repo
      https://github.com/owner/repo/
      https://github.com/owner/repo.git
    Returns:
      (owner, repo)
    """
    s = repo_url.strip()
    match = re.match(r"^https?://github\.com/([^/]+)/([^/]+?)(?:\.git)?/?$", s)
    if not match:
        raise HTTPException(status_code=400, detail="Invalid GitHub repo URL")

    return match.group(1), match.group(2)


def _download_github_zip(owner: str, repo: str, ref: str, out_path: Path) -> None:
    """
    Download a zipball using GitHub API (public repos).
    Rate limits apply.
    """
    zip_url = f"https://api.github.com/repos/{owner}/{repo}/zipball/{ref}"

    req = urllib.request.Request(
        zip_url,
        headers={
            "User-Agent": "final-folder-mvp-scanner",
            "Accept": "application/vnd.github+json",
        },
        method="GET",
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            out_path.write_bytes(resp.read())
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to download GitHub zip: {exc}",
        ) from exc


# -----------------------------
# Endpoints
# -----------------------------
@router.post("/scans")
def create_scan() -> Dict[str, Any]:
    """Creates an isolated scan workspace."""
    scan_id = str(uuid4())
    scan_path = BASE_STORAGE / scan_id

    for folder in ["input", "raw", "normalized", "metrics", "score", "ai"]:
        (scan_path / folder).mkdir(parents=True, exist_ok=True)

    return {"scan_id": scan_id, "status": "CREATED"}


@router.get("/scans/{scan_id}/status")
def scan_status(scan_id: str) -> Dict[str, Any]:
    scan_path = BASE_STORAGE / scan_id
    if not scan_path.exists():
        raise HTTPException(status_code=404, detail="Scan not found")

    raw_dir = scan_path / "raw"
    done = (raw_dir / "runner_done.json").exists()
    return {"scan_id": scan_id, "status": "DONE" if done else "READY"}


@router.post("/scans/{scan_id}/paste")
def paste_code(scan_id: str, payload: PastePayload) -> Dict[str, Any]:
    """Save a single file into input/ for scanning."""
    scan_path = BASE_STORAGE / scan_id
    if not scan_path.exists():
        raise HTTPException(status_code=404, detail="Scan not found")

    fname = payload.filename.replace("\\", "/").strip()
    if fname.startswith("/") or fname.startswith("..") or "/.." in fname:
        raise HTTPException(status_code=400, detail="Invalid filename")

    if Path(fname).suffix.lower() not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Only .py files allowed in MVP")

    input_dir = scan_path / "input"
    input_dir.mkdir(parents=True, exist_ok=True)

    file_path = input_dir / fname
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(payload.content, encoding="utf-8")

    return {"scan_id": scan_id, "saved": fname}


@router.post("/scans/{scan_id}/upload_zip")
def upload_zip(scan_id: str, file: UploadFile = File(...)) -> Dict[str, Any]:
    """
    MVP: Upload a project zip, extract, apply exclude rules,
    and copy allowed .py files into input/.

    Writes raw/ingestion.json summary.
    """
    scan_path = BASE_STORAGE / scan_id
    if not scan_path.exists():
        raise HTTPException(status_code=404, detail="Scan not found")

    if not file.filename or not file.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="Only .zip uploads are supported")

    input_dir = scan_path / "input"
    raw_dir = scan_path / "raw"
    input_dir.mkdir(parents=True, exist_ok=True)
    raw_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        zip_path = tmp_path / "upload.zip"
        zip_path.write_bytes(file.file.read())

        extract_dir = tmp_path / "extracted"
        extract_dir.mkdir(parents=True, exist_ok=True)

        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(extract_dir)
        except zipfile.BadZipFile as exc:
            raise HTTPException(status_code=400, detail="Invalid zip file") from exc

        ingestion_summary = _ingest_extracted_tree(extract_dir, input_dir)
        ingestion_summary["source"] = {"type": "zip", "filename": file.filename}
        _write_json(raw_dir / "ingestion.json", ingestion_summary)

    return {
        "scan_id": scan_id,
        "status": "UPLOADED",
        "kept": ingestion_summary["kept"],
        "skipped": ingestion_summary["skipped"],
        "stripped_root": ingestion_summary.get("stripped_single_root", False),
    }


@router.post("/scans/{scan_id}/github")
def ingest_github(scan_id: str, payload: GitHubPayload) -> Dict[str, Any]:
    """
    MVP: Download a public GitHub repo zipball and ingest into input/.

    Writes raw/ingestion.json summary.
    """
    scan_path = BASE_STORAGE / scan_id
    if not scan_path.exists():
        raise HTTPException(status_code=404, detail="Scan not found")

    input_dir = scan_path / "input"
    raw_dir = scan_path / "raw"
    input_dir.mkdir(parents=True, exist_ok=True)
    raw_dir.mkdir(parents=True, exist_ok=True)

    owner, repo = _parse_github_repo(payload.repo_url)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        zip_path = tmp_path / "repo.zip"

        _download_github_zip(owner, repo, payload.ref, zip_path)

        extract_dir = tmp_path / "extracted"
        extract_dir.mkdir(parents=True, exist_ok=True)

        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(extract_dir)
        except zipfile.BadZipFile as exc:
            raise HTTPException(
                status_code=400,
                detail="Downloaded file is not a valid zip",
            ) from exc

        ingestion_summary = _ingest_extracted_tree(extract_dir, input_dir)
        ingestion_summary["source"] = {
            "type": "github",
            "repo_url": payload.repo_url,
            "owner": owner,
            "repo": repo,
            "ref": payload.ref,
        }
        _write_json(raw_dir / "ingestion.json", ingestion_summary)

    return {
        "scan_id": scan_id,
        "status": "GITHUB_INGESTED",
        "kept": ingestion_summary["kept"],
        "skipped": ingestion_summary["skipped"],
        "repo": f"{owner}/{repo}",
        "ref": payload.ref,
        "stripped_root": ingestion_summary.get("stripped_single_root", False),
    }


@router.post("/scans/{scan_id}/start")
def start_scan(
    scan_id: str,
    project_name: Optional[str] = Query(default=None),
    project_key: Optional[str] = Query(default=None),
) -> Dict[str, Any]:
    """
    Starts the scan pipeline synchronously (MVP scope).

    Trend stability fix:
    - Persist project_name/project_key into raw/ingestion.json BEFORE pipeline
    - If only project_name is given, project_key is auto-generated
    """
    scan_path = BASE_STORAGE / scan_id
    if not scan_path.exists():
        raise HTTPException(status_code=404, detail="Scan not found")

    input_dir = scan_path / "input"
    raw_dir = scan_path / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    if not input_dir.exists() or not _has_any_python_file(input_dir):
        _write_json(
            raw_dir / "runner_warnings.json",
            {"error": "No Python (.py) files found in input/ (MVP requires .py)"},
        )
        return {"scan_id": scan_id, "status": "FAILED", "reason": "NO_PY_FILES"}

    ingestion_path = raw_dir / "ingestion.json"
    ingestion = _read_json(ingestion_path) or {"source": {"type": "unknown"}}

    if project_name:
        ingestion["project_name"] = project_name

    if project_key:
        ingestion["project_key"] = project_key
    elif project_name and not ingestion.get("project_key"):
        ingestion["project_key"] = _slugify(project_name)

    _write_json(ingestion_path, ingestion)

    result = run_tools_for_scan(scan_path)
    return {"scan_id": scan_id, "status": "DONE", "result": result}


@router.get("/scans/{scan_id}/results")
def get_scan_results(scan_id: str) -> Dict[str, Any]:
    """
    Returns raw + normalized + unified_issues + metrics + score + ai for frontend.
    Also fixes absolute paths into relative ones like input/test.py.
    """
    scan_path = BASE_STORAGE / scan_id
    if not scan_path.exists():
        raise HTTPException(status_code=404, detail="Scan not found")

    raw_dir = scan_path / "raw"
    norm_dir = scan_path / "normalized"
    metrics_dir = scan_path / "metrics"
    score_dir = scan_path / "score"
    ai_dir = scan_path / "ai"

    ingestion_obj = _read_json(raw_dir / "ingestion.json") or {}

    raw: Dict[str, Any] = {
        "ingestion": ingestion_obj,
        "flake8": _read_json(raw_dir / "flake8.json") or {},
        "bandit": _read_json(raw_dir / "bandit.json") or {},
        "runner_done": _read_json(raw_dir / "runner_done.json") or {},
        "runner_warnings": _read_json(raw_dir / "runner_warnings.json"),
        "pipeline_error": _read_json(raw_dir / "pipeline_error.json"),
        "postprocess_error": _read_json(raw_dir / "postprocess_error.json"),
    }

    normalized: Dict[str, Any] = {
        "flake8": _read_json(norm_dir / "flake8.normalized.json") or {},
        "bandit": _read_json(norm_dir / "bandit.normalized.json") or {},
    }

    unified_issues = _read_json(norm_dir / "unified_issues.json") or []
    if not isinstance(unified_issues, list):
        unified_issues = []

    metrics = _read_json(metrics_dir / "metrics.json") or {}
    score = _read_json(score_dir / "score.json") or {}
    ai_summary = _read_json(ai_dir / "ai_summary.json")

    # -----------------------------
    # Fix raw paths -> relative
    # -----------------------------
    if isinstance(raw.get("flake8"), dict):
        new_flake8 = {}
        for fname, items in raw["flake8"].items():
            rel_name = _to_rel_path(fname, scan_path)

            if isinstance(items, list):
                for item in items:
                    if isinstance(item, dict) and "filename" in item:
                        item["filename"] = _to_rel_path(item["filename"], scan_path)

            new_flake8[rel_name] = items

        raw["flake8"] = new_flake8

    bandit_raw = raw.get("bandit")
    if isinstance(bandit_raw, dict):
        results_list = bandit_raw.get("results")
        if isinstance(results_list, list):
            for item in results_list:
                if isinstance(item, dict) and "filename" in item:
                    item["filename"] = _to_rel_path(item["filename"], scan_path)

        metrics_obj = bandit_raw.get("metrics")
        if isinstance(metrics_obj, dict):
            new_metrics = {}
            for key, value in metrics_obj.items():
                if isinstance(key, str) and (key.startswith("/") or "/input/" in key):
                    new_metrics[_to_rel_path(key, scan_path)] = value
                else:
                    new_metrics[key] = value
            bandit_raw["metrics"] = new_metrics

    fl_norm = normalized.get("flake8")
    if isinstance(fl_norm, dict) and isinstance(fl_norm.get("issues"), list):
        for item in fl_norm["issues"]:
            if isinstance(item, dict) and "file" in item:
                item["file"] = _to_rel_path(item["file"], scan_path)

    bd_norm = normalized.get("bandit")
    if isinstance(bd_norm, dict) and isinstance(bd_norm.get("issues"), list):
        for item in bd_norm["issues"]:
            if isinstance(item, dict) and "file" in item:
                item["file"] = _to_rel_path(item["file"], scan_path)

    _normalize_issue_paths(unified_issues, scan_path)

    if isinstance(metrics, dict):
        top_refactor = metrics.get("top_refactor_priority")
        if isinstance(top_refactor, list):
            for item in top_refactor:
                if isinstance(item, dict) and item.get("file"):
                    item["file"] = _to_rel_path(str(item["file"]), scan_path)

        heatmap = metrics.get("heatmap")
        if isinstance(heatmap, dict):
            new_heatmap = {}
            for key, value in heatmap.items():
                if isinstance(key, str):
                    new_heatmap[_to_rel_path(key, scan_path)] = value
                else:
                    new_heatmap[key] = value
            metrics["heatmap"] = new_heatmap

        top_files = metrics.get("top_files")
        if isinstance(top_files, list):
            for item in top_files:
                if isinstance(item, dict) and item.get("file"):
                    item["file"] = _to_rel_path(str(item["file"]), scan_path)

    ai_summary = _normalize_ai_payload(ai_summary, scan_path)

    project_key = ingestion_obj.get("project_key")
    project_name = ingestion_obj.get("project_name")

    return {
        "scan_id": scan_id,
        "status": "OK",
        "project_key": project_key,
        "project_name": project_name,
        "raw": raw,
        "normalized": normalized,
        "unified_issues": unified_issues,
        "metrics": metrics,
        "score": score,
        "ai": {
            "exists": ai_summary is not None,
            "summary": ai_summary,
        },
    }


@router.get("/health")
def health() -> Dict[str, Any]:
    return {"status": "ok"}