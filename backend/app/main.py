from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path

from app.api.routes.multi_language_scans import router as multi_language_scans_router
from app.api.routes.scans import router as scans_router
from app.api.routes.projects import router as projects_router

app = FastAPI(title="AI-Powered Code Intelligence & Review Platform")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# The multi-language router is registered first so its compatible
# paste/upload/GitHub/start endpoints handle both Python and Java.
app.include_router(multi_language_scans_router)
app.include_router(scans_router)
app.include_router(projects_router)

BASE_STORAGE = Path(__file__).resolve().parents[1] / "storage"
BASE_STORAGE.mkdir(parents=True, exist_ok=True)


@app.get("/health")
def health_check():
    return {"status": "ok"}
