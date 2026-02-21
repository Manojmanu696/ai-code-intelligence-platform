from fastapi import APIRouter, HTTPException
from uuid import uuid4
from pathlib import Path
from pydantic import BaseModel
from app.services.pipeline.simple_pipeline import run_tools_for_scan

router = APIRouter()

# Dynamically resolve project root (avoids hardcoding paths)
PROJECT_ROOT = Path(__file__).resolve().parents[3]
BASE_STORAGE = PROJECT_ROOT / "storage" / "scans"


@router.post("/scans")
def create_scan():
    """
    Creates an isolated scan workspace.
    Each scan gets its own structured processing pipeline.
    """
    scan_id = str(uuid4())
    scan_path = BASE_STORAGE / scan_id

    # Create processing pipeline folders
    for folder in ["input", "raw", "normalized", "metrics", "score", "ai"]:
        (scan_path / folder).mkdir(parents=True, exist_ok=True)

    return {"scan_id": scan_id, "status": "CREATED"}


@router.get("/scans/{scan_id}/status")
def scan_status(scan_id: str):
    """
    Used to track scan lifecycle.
    """
    scan_path = BASE_STORAGE / scan_id

    if not scan_path.exists():
        raise HTTPException(status_code=404, detail="Scan not found")

    return {"scan_id": scan_id, "status": "READY"}


class PasteRequest(BaseModel):
    # Validates incoming pasted code automatically
    filename: str
    content: str


@router.post("/scans/{scan_id}/paste")
def paste_code(scan_id: str, payload: PasteRequest):
    """
    Code ingestion endpoint.
    Stores user-submitted source code in workspace.
    """
    scan_path = BASE_STORAGE / scan_id

    if not scan_path.exists():
        raise HTTPException(status_code=404, detail="scan_id not found")

    file_path = scan_path / "input" / payload.filename
    file_path.write_text(payload.content)

    return {
        "scan_id": scan_id,
        "filename": payload.filename,
        "status": "FILE_SAVED"
    }
@router.post("/scans/{scan_id}/start")
def start_scan(scan_id: str):
    """
    Starts the scan pipeline synchronously (MVP scope).
    Runs flake8 + bandit and writes outputs into raw/.
    """
    scan_path = BASE_STORAGE / scan_id
    if not scan_path.exists():
        raise HTTPException(status_code=404, detail="scan_id not found")

    run_tools_for_scan(scan_path)

    return {"scan_id": scan_id, "status": "DONE", "stage": "RUN_TOOLS"}

from pathlib import Path
import json
from fastapi import APIRouter, HTTPException

router = APIRouter()

BASE_STORAGE = Path(__file__).resolve().parents[3] / "storage" / "scans"  # adjust if your file depth differs


def _read_json_safe(path: Path):
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


@router.get("/scans/{scan_id}/results")
def get_scan_results(scan_id: str):
    scan_path = BASE_STORAGE / scan_id
    if not scan_path.exists():
        raise HTTPException(status_code=404, detail="scan_id not found")

    raw_dir = scan_path / "raw"
    norm_dir = scan_path / "normalized"
    metrics_dir = scan_path / "metrics"
    score_dir = scan_path / "score"
    ai_dir = scan_path / "ai"

    # Core artifacts
    flake8_raw = _read_json_safe(raw_dir / "flake8.json")
    bandit_raw = _read_json_safe(raw_dir / "bandit.json")
    runner_done = _read_json_safe(raw_dir / "runner_done.json") or _read_json_safe(raw_dir / "runner_done.json")

    flake8_norm = _read_json_safe(norm_dir / "flake8.normalized.json")
    bandit_norm = _read_json_safe(norm_dir / "bandit.normalized.json")

    metrics = _read_json_safe(metrics_dir / "metrics.json")
    score = _read_json_safe(score_dir / "score.json")

    # Error files (optional)
    postprocess_error = _read_json_safe(raw_dir / "postprocess_error.json")
    runner_warnings = _read_json_safe(raw_dir / "runner_warnings.json")

    # Build status
    status = "CREATED"
    if runner_done:
        status = "DONE"
    if postprocess_error:
        status = "POSTPROCESS_FAILED"

    # Small summary (safe defaults)
    summary = {
        "flake8_issues": (flake8_norm or {}).get("counts", {}).get("total", None),
        "bandit_issues": (bandit_norm or {}).get("counts", {}).get("total", None),
        "final_score": (score or {}).get("final_score", None),
    }

    return {
        "scan_id": scan_id,
        "status": status,
        "summary": summary,
        "raw": {
            "flake8": flake8_raw,
            "bandit": bandit_raw,
            "runner_done": runner_done,
            "runner_warnings": runner_warnings,
            "postprocess_error": postprocess_error,
        },
        "normalized": {
            "flake8": flake8_norm,
            "bandit": bandit_norm,
        },
        "metrics": metrics,
        "score": score,
        "ai": {
            # placeholder for future: ai_dir / "ai.json"
            "exists": ai_dir.exists(),
        },
    }