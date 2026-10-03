"""
backend/routers/auth.py
Sign-in: Google (OAuth code flow), mobile (SMS one-time code), guest.

GET    /api/v1/auth/providers
GET    /api/v1/auth/google/login      → redirects to Google
GET    /api/v1/auth/google/callback   → redirects to FRONTEND_URL?code=<one-time>
POST   /api/v1/auth/exchange          one-time code → session token
POST   /api/v1/auth/otp/request       send SMS code
POST   /api/v1/auth/otp/verify        verify code → session token
POST   /api/v1/auth/guest             demo session
GET    /api/v1/auth/me
DELETE /api/v1/auth/me                delete account + data
"""
import logging
from urllib.parse import urlencode

from fastapi import APIRouter, Cookie, Depends, HTTPException, Query, Request, status
from fastapi.responses import RedirectResponse

from backend.core.config import get_settings
from backend.core.security import Principal, get_principal
from backend.schemas.auth import (ExchangeRequest, OtpSent, OtpVerify, PhoneRequest,
                                  ProvidersResponse, TokenResponse, UserOut)
from backend.services import auth_service as svc
from database import auth_store

logger = logging.getLogger("uvicorn.error")
router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])
COOKIE = "triavia_oauth"


def _token_response(user: dict) -> TokenResponse:
    token, ttl = svc.create_token(user)
    return TokenResponse(access_token=token, expires_in=ttl, user=UserOut(
        id=user["id"], provider=user["provider"],
        name=user.get("name") or ("Guest" if user["provider"] == "guest" else "User"),
        email=user.get("email") or None, phone_masked=svc.mask_phone(user.get("phone"))))


@router.get("/providers", response_model=ProvidersResponse)
def providers():
    s = get_settings()
    return ProvidersResponse(google=s.google_enabled, mobile=True, guest=s.allow_guest,
                             sms_delivery="sms" if s.twilio_enabled else "console",
                             auth_required=s.auth_required)


# ── Google ────────────────────────────────────────────────────────────────────
@router.get("/google/login", include_in_schema=get_settings().google_enabled)
def google_login():
    s = get_settings()
    if not s.google_enabled:
        raise HTTPException(503, "Google sign-in is not configured on this server.")
    state, nonce = svc.make_state()
    resp = RedirectResponse(svc.google_auth_url(state), status_code=302)
    resp.set_cookie(COOKIE, nonce, max_age=600, httponly=True, samesite="lax",
                    secure=s.backend_public_url.startswith("https"))
    return resp


@router.get("/google/callback", include_in_schema=False)
def google_callback(request: Request, code: str = Query(default=""), state: str = Query(default=""),
                    error: str = Query(default=""), triavia_oauth: str = Cookie(default=None)):
    s = get_settings()
    front = s.frontend_url.rstrip("/")

    def back(**q):
        r = RedirectResponse(f"{front}/?{urlencode(q)}", status_code=302)
        r.delete_cookie(COOKIE)
        return r

    if error or not code:
        return back(auth_error="Google sign-in was cancelled.")
    if not svc.verify_state(state, triavia_oauth):
        return back(auth_error="Sign-in session expired. Please try again.")
    try:
        info = svc.exchange_google_code(code)
    except Exception:
        logger.exception("Google token exchange failed")
        return back(auth_error="Google sign-in failed. Please try again.")
    user = auth_store.upsert_user("google", info["sub"], info.get("name", ""), info.get("email", ""))
    return back(code=auth_store.create_login_code(user["id"]))


@router.post("/exchange", response_model=TokenResponse)
def exchange(body: ExchangeRequest):
    uid = auth_store.consume_login_code(body.code)
    user = auth_store.get_user(uid) if uid else None
    if not user:
        raise HTTPException(401, "This sign-in link has expired. Please try again.")
    return _token_response(user)


# ── Mobile OTP ────────────────────────────────────────────────────────────────
@router.post("/otp/request", response_model=OtpSent)
def otp_request(body: PhoneRequest):
    s = get_settings()
    if auth_store.count_recent_otps(body.phone) >= 5:
        raise HTTPException(429, "Too many codes requested for this number. Try again in an hour.")
    auth_store.purge_stale()
    code = svc.new_otp()
    auth_store.save_otp(body.phone, svc.hash_otp(body.phone, code), s.otp_ttl_seconds)
    try:
        delivery = svc.send_sms(body.phone, f"Your Triavia code is {code}. It expires in "
                                            f"{s.otp_ttl_seconds // 60} minutes.")
    except Exception:
        logger.exception("SMS delivery failed")
        raise HTTPException(502, "Could not send the SMS. Please try again later.")
    return OtpSent(delivery=delivery, expires_in=s.otp_ttl_seconds,
                   dev_otp=code if s.otp_dev_echo else None)


@router.post("/otp/verify", response_model=TokenResponse)
def otp_verify(body: OtpVerify):
    result = auth_store.check_otp(body.phone, svc.hash_otp(body.phone, body.code))
    if result != "ok":
        msg = {"expired": "That code has expired. Request a new one.",
               "locked": "Too many wrong attempts. Request a new code.",
               "none": "No code was requested for this number."}.get(result, "Incorrect code.")
        raise HTTPException(401, msg)
    user = auth_store.upsert_user("mobile", body.phone, name="", phone=body.phone)
    return _token_response(user)


# ── Guest / session ───────────────────────────────────────────────────────────
@router.post("/guest", response_model=TokenResponse)
def guest():
    if not get_settings().allow_guest:
        raise HTTPException(403, "Guest access is disabled.")
    auth_store.purge_stale()
    import secrets
    return _token_response(auth_store.upsert_user("guest", secrets.token_hex(8), name="Guest"))


@router.get("/me", response_model=UserOut)
def me(p: Principal = Depends(get_principal)):
    if p.kind != "user":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Not a user session.")
    u = auth_store.get_user(p.user_id)
    return UserOut(id=u["id"], provider=u["provider"], name=u.get("name") or "User",
                   email=u.get("email") or None, phone_masked=svc.mask_phone(u.get("phone")))


@router.delete("/me")
def delete_me(p: Principal = Depends(get_principal)):
    if p.kind != "user":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Not a user session.")
    auth_store.delete_user(p.user_id)
    return {"deleted": True}
