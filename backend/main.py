"""
backend/main.py — FastAPI entry-point.

    uvicorn backend.main:app --reload --port 8000
Docs: http://localhost:8000/docs
"""
import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse

from backend.core.config import get_settings
from backend.core.security import RateLimitMiddleware, SecurityHeadersMiddleware
from backend.routers.auth import router as auth_router
from backend.routers.feedback import router as feedback_router
from backend.routers.predict import router as predict_router
from backend.services.predictor_service import PredictorService
from database import db

logger = logging.getLogger("uvicorn.error")
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    try:
        PredictorService.get_instance()
        logger.info("✅ Model loaded on startup.")
    except Exception as e:
        logger.warning("⚠️  Model not found on startup: %s — run `python model/train.py`", e)
    if not settings.secret_key:
        logger.warning("SECRET_KEY is not set — using a temporary key; sign-ins reset on every restart.")
    if not settings.auth_required:
        logger.warning("AUTH_REQUIRED=false — the API is open without sign-in.")
    if settings.otp_dev_echo:
        logger.warning("OTP_DEV_ECHO=true — SMS codes are returned in API responses (demo only!).")
    yield


app = FastAPI(
    title=f"{settings.app_name} API",
    description=(
        f"## 🩺 {settings.app_name}\n\n"
        "ML-powered Emergency Department triage decision support.\n\n"
        "| Level | Label | Wait |\n|---|---|---|\n"
        "| 0 | Non-Urgent | 2–4 hours |\n| 1 | Semi-Urgent | 1–2 hours |\n"
        "| 2 | Urgent | ≤30 minutes |\n| 3 | Resuscitation | Immediate |\n\n"
        f"Built by {settings.author} · {settings.contact}\n\n"
        "> ⚠️ **Educational use only.** Not a medical device."
    ),
    version=settings.version,
    lifespan=lifespan,
    contact={"name": settings.author, "email": settings.contact},
    license_info={"name": "MIT"},
    docs_url="/docs",
    redoc_url="/redoc",
)

origins = settings.cors_origin_list
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=origins != ["*"],   # wildcard + credentials is invalid/insecure
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-API-Key"],
)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(SecurityHeadersMiddleware)


@app.exception_handler(Exception)
async def unhandled(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s", request.url.path)
    return JSONResponse({"detail": "Internal server error."}, status_code=500)


app.include_router(auth_router)
app.include_router(predict_router)
app.include_router(feedback_router)


@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/docs")
