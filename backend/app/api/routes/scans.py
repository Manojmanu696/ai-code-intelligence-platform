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