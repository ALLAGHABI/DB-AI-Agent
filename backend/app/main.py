from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.reports_routes import router as reports_router
from .api.routes import router
from .config import settings

app = FastAPI(title="SmartDB v2", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.include_router(reports_router)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "version": "2.0.0"}
