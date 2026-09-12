from __future__ import annotations

import json
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, File, HTTPException, Query, UploadFile
from pydantic import BaseModel

from app.api.routes import scans
from app.services.pipeline.simple_pipeline import run_tools_for_scan

router = APIRouter()

EXCLUDE_DIRS = set(scans.EXCLUDE_DIRS)
ALLOWED_EXTENSIONS = {
    ".py", ".java",
    ".c", ".h",
    ".cc", ".cpp", ".cxx", ".hh", ".hpp", ".hxx",
}
MAX_FILE_SIZE_BYTES = scans.MAX_FILE_SIZE_BYTES
BASE_STORAGE = scans.BASE_STORAGE


class PastePayload(BaseModel):
    filename: str
    content: str


class GitHubPayload(BaseModel):
    repo_url: str
    ref: str = "main"


def _write_json(path: Path, data: Any) -> None:
    """Write JSON data to a file and create its parent folder first."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _read_json(path: Path) -> Optional[Any]:
    """Read JSON from a file when it exists."""
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _slugify(value: str) -> str:
    """Convert a project name into a storage-safe key using the shared helper."""
    return scans._slugify(value)


def _is_allowed_file(path: Path) -> bool:
    """Check whether a file has a supported extension and safe size."""
    if not path.is_file():
        return False
    if path.suffix.lower() not in ALLOWED_EXTENSIONS:
        return False
    try:
        return path.stat().st_size <= MAX_FILE_SIZE_BYTES
    except OSError:
        return False


def _has_supported_file(input_dir: Path) -> bool:
    """Check whether the input folder contains at least one supported source file."""
    return any(
        p.is_file() and p.suffix.lower() in ALLOWED_EXTENSIONS
        for p in input_dir.rglob("*")
    )


def _ingest_extracted_tree(extract_dir: Path, input_dir: Path) -> Dict[str, Any]:
    """Copy supported files from an extracted archive into the scan input folder."""
    def effective_root(root: Path) -> Path:
        """Remove a single unnecessary wrapper folder from an extracted archive."""
        try:
            children = [c for c in root.iterdir() if c.name not in EXCLUDE_DIRS]
        except OSError:
            return root
        dirs = [c for c in children if c.is_dir()]
        files = [c for c in children if c.is_file()]
        return dirs[0] if not files and len(dirs) == 1 else root

    base = effective_root(extract_dir)
    kept = 0
    skipped = 0
    skipped_samples: list[dict[str, str]] = []

    for path in base.rglob("*"):
        if path.is_dir() or any(part in EXCLUDE_DIRS for part in path.parts):
            continue
        if not _is_allowed_file(path):
            skipped += 1
            if len(skipped_samples) < 25:
                reason = "not_allowed"
                try:
                    if path.stat().st_size > MAX_FILE_SIZE_BYTES:
                        reason = "too_large"
                except OSError:
                    reason = "stat_failed"
                skipped_samples.append(
                    {"file": str(path.relative_to(base)), "reason": reason}
                )
            continue

        rel = path.relative_to(base)
        dest = input_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dest)
        kept += 1

    return {
        "kept": kept,
        "skipped": skipped,
        "max_file_size_bytes": MAX_FILE_SIZE_BYTES,
        "allowed_extensions": sorted(ALLOWED_EXTENSIONS),
        "excluded_dirs": sorted(EXCLUDE_DIRS),
        "skipped_samples": skipped_samples,
        "stripped_single_root": base != extract_dir,
        "root_used": base.name,
    }


def _save_ingestion(scan_path: Path, summary: Dict[str, Any]) -> None:
    """Save the ingestion summary for a scan."""
    _write_json(scan_path / "raw" / "ingestion.json", summary)


@router.post("/scans/{scan_id}/paste")
def paste_code(scan_id: str, payload: PastePayload) -> Dict[str, Any]:
    """Save pasted source code into the selected scan."""
    scan_path = BASE_STORAGE / scan_id
    if not scan_path.exists():
        raise HTTPException(status_code=404, detail="Scan not found")

    filename = payload.filename.replace("\\", "/").strip()
    if filename.startswith("/") or filename.startswith("..") or "/.." in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    if Path(filename).suffix.lower() not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Only .py, .java, .c, .h, .cc, .cpp, .cxx, .hh, .hpp, and .hxx files are supported",
        )

    target = scan_path / "input" / filename
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(payload.content, encoding="utf-8")

    return {"scan_id": scan_id, "saved": filename, "language": target.suffix.lower()[1:]}


@router.post("/scans/{scan_id}/upload_zip")
def upload_zip(scan_id: str, file: UploadFile = File(...)) -> Dict[str, Any]:
    """Extract a ZIP file and keep only supported source files."""
    scan_path = BASE_STORAGE / scan_id
    if not scan_path.exists():
        raise HTTPException(status_code=404, detail="Scan not found")
    if not file.filename or not file.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=400, detail="Only .zip uploads are supported")

    input_dir = scan_path / "input"
    input_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        zip_path = tmp_path / "upload.zip"
        zip_path.write_bytes(file.file.read())
        extract_dir = tmp_path / "extracted"
        extract_dir.mkdir()
        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(extract_dir)
        except zipfile.BadZipFile as exc:
            raise HTTPException(status_code=400, detail="Invalid zip file") from exc

        summary = _ingest_extracted_tree(extract_dir, input_dir)
        summary["source"] = {"type": "zip", "filename": file.filename}
        _save_ingestion(scan_path, summary)

    return {
        "scan_id": scan_id,
        "status": "UPLOADED",
        "kept": summary["kept"],
        "skipped": summary["skipped"],
        "stripped_root": summary["stripped_single_root"],
    }


@router.post("/scans/{scan_id}/github")
def ingest_github(scan_id: str, payload: GitHubPayload) -> Dict[str, Any]:
    """Download a GitHub repository, extract it, and keep supported source files."""
    scan_path = BASE_STORAGE / scan_id
    if not scan_path.exists():
        raise HTTPException(status_code=404, detail="Scan not found")

    input_dir = scan_path / "input"
    input_dir.mkdir(parents=True, exist_ok=True)

    owner, repo = scans._parse_github_repo(payload.repo_url)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        zip_path = tmp_path / "repo.zip"
        scans._download_github_zip(owner, repo, payload.ref, zip_path)
        extract_dir = tmp_path / "extracted"
        extract_dir.mkdir()
        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(extract_dir)
        except zipfile.BadZipFile as exc:
            raise HTTPException(status_code=400, detail="Downloaded file is not a valid zip") from exc

        summary = _ingest_extracted_tree(extract_dir, input_dir)
        summary["source"] = {
            "type": "github",
            "repo_url": payload.repo_url,
            "owner": owner,
            "repo": repo,
            "ref": payload.ref,
        }
        _save_ingestion(scan_path, summary)

    return {
        "scan_id": scan_id,
        "status": "GITHUB_INGESTED",
        "kept": summary["kept"],
        "skipped": summary["skipped"],
        "repo": f"{owner}/{repo}",
        "ref": payload.ref,
    }


@router.post("/scans/{scan_id}/start")
def start_scan(
    scan_id: str,
    project_name: Optional[str] = Query(default=None),
    project_key: Optional[str] = Query(default=None),
) -> Dict[str, Any]:
    """Validate the scan input, run analyzers, and return the scan result."""
    scan_path = BASE_STORAGE / scan_id
    if not scan_path.exists():
        raise HTTPException(status_code=404, detail="Scan not found")

    input_dir = scan_path / "input"
    raw_dir = scan_path / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    if not input_dir.exists() or not _has_supported_file(input_dir):
        _write_json(
            raw_dir / "runner_warnings.json",
            {"error": "No supported source files found (.py, .java, .c, .h, .cc, .cpp, .cxx, .hh, .hpp, .hxx)"},
        )
        return {"scan_id": scan_id, "status": "FAILED", "reason": "NO_SUPPORTED_FILES"}

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
