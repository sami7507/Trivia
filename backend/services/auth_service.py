"""
backend/services/auth_service.py
JWT sessions, OAuth state, OTP generation/hashing, SMS delivery and Google OAuth calls.
"""
import hashlib
import hmac
import logging
import secrets
import time
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlencode

import httpx
import jwt

from backend.core.config import get_settings

logger = logging.getLogger("uvicorn.error")
_EPHEMERAL_KEY = secrets.token_urlsafe(48)  # used only if SECRET_KEY is unset (sessions reset on restart)

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"


def signing_key() -> str:
    return get_settings().secret_key or _EPHEMERAL_KEY


# ── Session tokens ────────────────────────────────────────────────────────────
def create_token(user: Dict[str, Any]) -> Tuple[str, int]:
    s = get_settings()
    minutes = s.guest_expire_minutes if user["provider"] == "guest" else s.jwt_expire_minutes
    now = int(time.time())
    payload = {"sub": str(user["id"]), "prov": user["provider"], "iat": now, "exp": now + minutes * 60}
    return jwt.encode(payload, signing_key(), algorithm="HS256"), minutes * 60


def decode_token(token: str) -> Dict[str, Any]:
    return jwt.decode(token, signing_key(), algorithms=["HS256"], options={"require": ["exp", "sub"]})


# ── OAuth state (CSRF protection) ─────────────────────────────────────────────
def make_state() -> Tuple[str, str]:
    nonce = secrets.token_urlsafe(16)
    state = jwt.encode({"n": nonce, "t": "oauth", "exp": int(time.time()) + 600},
                       signing_key(), algorithm="HS256")
    return state, nonce


def verify_state(state: str, cookie_nonce: Optional[str]) -> bool:
    try:
        data = jwt.decode(state, signing_key(), algorithms=["HS256"])
    except jwt.PyJWTError:
        return False
    return data.get("t") == "oauth" and bool(cookie_nonce) and hmac.compare_digest(
        str(data.get("n", "")), cookie_nonce)


# ── Google OAuth ──────────────────────────────────────────────────────────────
def google_redirect_uri() -> str:
    return f"{get_settings().backend_public_url.rstrip('/')}/api/v1/auth/google/callback"


def google_auth_url(state: str) -> str:
    q = {"client_id": get_settings().google_client_id, "redirect_uri": google_redirect_uri(),
         "response_type": "code", "scope": "openid email profile", "state": state,
         "prompt": "select_account", "access_type": "online"}
    return f"{GOOGLE_AUTH_URL}?{urlencode(q)}"


def exchange_google_code(code: str) -> Dict[str, Any]:
    """Swap the authorization code for the user's Google profile. Raises on any failure."""
    s = get_settings()
    with httpx.Client(timeout=10) as client:
        t = client.post(GOOGLE_TOKEN_URL, data={
            "code": code, "client_id": s.google_client_id, "client_secret": s.google_client_secret,
            "redirect_uri": google_redirect_uri(), "grant_type": "authorization_code"})
        t.raise_for_status()
        access = t.json()["access_token"]
        u = client.get(GOOGLE_USERINFO_URL, headers={"Authorization": f"Bearer {access}"})
        u.raise_for_status()
        info = u.json()
    if not info.get("sub") or not info.get("email_verified", False):
        raise ValueError("Google account email is not verified")
    return info


# ── Mobile OTP ────────────────────────────────────────────────────────────────
def new_otp() -> str:
    return f"{secrets.randbelow(10**6):06d}"


def hash_otp(phone: str, code: str) -> str:
    return hmac.new(signing_key().encode(), f"{phone}:{code}".encode(), hashlib.sha256).hexdigest()


def mask_phone(phone: Optional[str]) -> Optional[str]:
    return f"{phone[:3]}{'•' * max(0, len(phone) - 6)}{phone[-3:]}" if phone else None


def send_sms(phone: str, body: str) -> str:
    """Returns the delivery channel used: 'sms' or 'console'."""
    s = get_settings()
    if s.twilio_enabled:
        r = httpx.post(
            f"https://api.twilio.com/2010-04-01/Accounts/{s.twilio_account_sid}/Messages.json",
            auth=(s.twilio_account_sid, s.twilio_auth_token),
            data={"To": phone, "From": s.twilio_from, "Body": body}, timeout=10)
        r.raise_for_status()
        return "sms"
    logger.warning("[DEMO SMS → %s] %s", mask_phone(phone), body)  # visible in the API console
    return "console"
