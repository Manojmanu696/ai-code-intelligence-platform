from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path

from app.api.routes.scans import router as scans_router
from app.api.routes.projects import router as projects_router

app = FastAPI(title="AI-Powered Code Intelligence & Review Platform")

# -----------------------------
# CORS Middleware (IMPORTANT)
# -----------------------------
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

# -----------------------------
# Routers
# -----------------------------
app.include_router(scans_router)
app.include_router(projects_router)

# -----------------------------
# Storage Setup
# -----------------------------
BASE_STORAGE = Path(__file__).resolve().parents[1] / "storage"
BASE_STORAGE.mkdir(parents=True, exist_ok=True)

# -----------------------------
# Health Endpoint
# -----------------------------
@app.get("/health")
def health_check():
    return {"status": "ok"}