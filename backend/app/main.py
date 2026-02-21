from fastapi import FastAPI
from app.api.routes.scans import router as scans_router

app = FastAPI(title="AI-Powered Code Intelligence & Review Platform")

app.include_router(scans_router)

@app.get("/health")
def health_check():
    return {"status": "ok"}
