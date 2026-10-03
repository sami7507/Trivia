"""
backend/routers/predict.py
POST   /api/v1/predict   core triage prediction
GET    /api/v1/health    liveness + readiness
GET    /api/v1/metrics   model performance metrics
GET    /api/v1/history   recent assessments (anonymous)
GET    /api/v1/stats     aggregate stats
DELETE /api/v1/history   wipe stored assessments
"""
import json
import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse

from backend.core.config import METRICS_PATH, get_settings
from backend.core.security import Principal, get_principal
from backend.schemas.patient import (AssessmentRecord, HealthResponse, PatientInput,
                                     StatsResponse, TriagePrediction)
from backend.services.predictor_service import PredictorService
from database import db

logger = logging.getLogger("uvicorn.error")
router = APIRouter(prefix="/api/v1", tags=["Triage"])


def get_predictor() -> PredictorService:
    try:
        return PredictorService.get_instance()
    except Exception:
        logger.exception("Model failed to load")
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE,
                            "Model not available. Run `python model/train.py` first.")


@router.post("/predict", response_model=TriagePrediction, summary="Predict triage level",
             responses={401: {"description": "Not signed in"}, 422: {"description": "Invalid input"},
                        429: {"description": "Rate limited"}, 503: {"description": "Model not ready"}})
def predict_triage(patient: PatientInput,
                   predictor: PredictorService = Depends(get_predictor),
                   principal: Principal = Depends(get_principal)) -> TriagePrediction:
    try:
        result = predictor.predict(patient)
    except Exception:
        logger.exception("Prediction failed")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR,
                            "Prediction failed. Please try again.")
    try:  # history is best-effort; never fail a prediction because of storage
        result.assessment_id = db.save_assessment(patient.model_dump(mode="json"),
                                                  result.model_dump(), principal.scope_user_id)
    except Exception:
        logger.exception("Could not save assessment")
    return result


@router.get("/health", response_model=HealthResponse, summary="Health check")
def health_check() -> HealthResponse:
    try:
        PredictorService.get_instance()
        loaded = True
    except Exception:
        loaded = False
    db_ok = db.ping()
    return HealthResponse(status="ok" if loaded and db_ok else "degraded",
                          is_model_loaded=loaded, database_ok=db_ok,
                          database_engine=db.engine_name(),
                          version=get_settings().version)


@router.get("/metrics", summary="Model evaluation metrics")
def get_metrics(_: Principal = Depends(get_principal)):
    if not METRICS_PATH.exists():
        raise HTTPException(404, "Metrics not found. Run `python model/train.py`.")
    return JSONResponse(json.loads(METRICS_PATH.read_text()))


@router.get("/history", response_model=List[AssessmentRecord], summary="Your recent assessments")
def history(limit: int = Query(50, ge=1, le=500), p: Principal = Depends(get_principal)):
    return [{**r, "safety_override": bool(r["safety_override"])}
            for r in db.list_assessments(limit, p.scope_user_id)]


@router.get("/stats", response_model=StatsResponse, summary="Your assessment statistics")
def stats(p: Principal = Depends(get_principal)):
    return db.stats(p.scope_user_id)


@router.delete("/history", summary="Delete your stored assessments")
def clear_history(p: Principal = Depends(get_principal)):
    return {"deleted": db.clear_assessments(p.scope_user_id)}
