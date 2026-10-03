"""
backend/routers/feedback.py
POST /api/v1/feedback   anyone can send feedback (signed-in users are linked, guests/visitors anonymous)
GET  /api/v1/feedback   author only — requires the X-API-Key service key
"""
import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.core.security import Principal, optional_principal, require_service
from backend.schemas.feedback import FeedbackIn, FeedbackReceipt, FeedbackRecord
from database import db

logger = logging.getLogger("uvicorn.error")
router = APIRouter(prefix="/api/v1/feedback", tags=["Feedback"])


@router.post("", response_model=FeedbackReceipt, summary="Send feedback")
def send_feedback(body: FeedbackIn, p: Principal = Depends(optional_principal)):
    try:
        new_id = db.save_feedback(body.message, body.rating, body.contact, p.scope_user_id)
    except Exception:
        logger.exception("Could not save feedback")
        raise HTTPException(500, "Could not save your feedback. Please try again.")
    return FeedbackReceipt(id=new_id)


@router.get("", response_model=List[FeedbackRecord], summary="Read feedback (author only)")
def read_feedback(limit: int = Query(100, ge=1, le=1000), _: Principal = Depends(require_service)):
    return db.list_feedback(limit)
