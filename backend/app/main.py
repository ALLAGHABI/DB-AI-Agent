from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .api.reports_routes import router as reports_router
from .api.routes import router
from .config import settings
from .errors import AppError

app = FastAPI(title="SmartDB v2", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    """كل أخطاء المجال تُرسل كرمز + معاملات — الواجهة تترجمها للغة المستخدم."""
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.to_detail()})


app.include_router(router)
app.include_router(reports_router)


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "version": "2.0.0"}
