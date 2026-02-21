from fastapi import FastAPI
from app.api.routes.scans import router as scans_router
from pathlib import Path

BASE_STORAGE = Path(__file__).resolve().parents[1] / "storage"
BASE_STORAGE.mkdir(parents=True, exist_ok=True)


app = FastAPI(title="AI-Powered Code Intelligence & Review Platform")

app.include_router(scans_router)

@app.get("/health")
def health_check():
    return {"status": "ok"}
