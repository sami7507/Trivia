"""
HTTP client for the Triavia API — friendly errors, retries, cold-start tolerance.

NOTE: this module is shared by all Streamlit sessions, so it never stores a user's
token globally; callers pass `token` explicitly on every request.
"""
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional

import httpx


def _secret(name: str, default: str = "") -> str:
    """Environment variable first (Streamlit Cloud also exposes secrets as env vars), then
    secrets.toml — but only if that file exists, otherwise Streamlit shows a red error box."""
    value = os.getenv(name)
    if value:
        return value
    for path in (Path.home() / ".streamlit" / "secrets.toml", Path.cwd() / ".streamlit" / "secrets.toml"):
        if path.exists():
            try:
                import streamlit as st
                if name in st.secrets:
                    return str(st.secrets[name])
            except Exception:
                pass
            break
    return default


BACKEND_URL = _secret("BACKEND_URL", "http://localhost:8000").rstrip("/")
# URL the *browser* can reach (differs from BACKEND_URL when running inside Docker)
PUBLIC_BACKEND_URL = _secret("BACKEND_PUBLIC_URL", BACKEND_URL).rstrip("/")


class ApiError(Exception):
    """Message is safe to show to end users."""


class AuthExpired(ApiError):
    """The session token is missing, invalid or expired."""


def _request(method: str, path: str, json: Optional[dict] = None, token: Optional[str] = None,
             timeout: float = 45.0, retries: int = 2) -> Any:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    for attempt in range(retries + 1):
        try:
            r = httpx.request(method, f"{BACKEND_URL}{path}", json=json, headers=headers, timeout=timeout)
        except (httpx.ConnectError, httpx.TimeoutException):
            time.sleep(2 * (attempt + 1))      # free-tier servers may be waking up — retry
            continue
        if r.status_code == 200:
            return r.json()
        detail = ""
        try:
            detail = r.json().get("detail", "")
        except Exception:
            pass
        if r.status_code == 401:
            if token:
                raise AuthExpired("Your session has expired. Please sign in again.")
            raise ApiError(detail if isinstance(detail, str) and detail else "Please sign in.")
        if r.status_code == 422:
            if isinstance(detail, list) and detail:
                msg = str(detail[0].get("msg", "")).replace("Value error, ", "")
                raise ApiError(msg or "Some values look invalid.")
            raise ApiError("Some values look invalid. Please check the highlighted ranges.")
        if r.status_code in (403, 429, 502, 503) and isinstance(detail, str) and detail:
            raise ApiError(detail)
        raise ApiError("Something went wrong on the server. Please try again.")
    raise ApiError("Can't reach the server. It may be starting up — please retry in ~30 seconds.")


# ── Auth ──────────────────────────────────────────────────────────────────────
def providers() -> Optional[Dict[str, Any]]:
    try:
        r = httpx.get(f"{BACKEND_URL}/api/v1/auth/providers", timeout=8.0)
        return r.json() if r.status_code == 200 else None
    except Exception:
        return None


def google_login_url() -> str:
    return f"{PUBLIC_BACKEND_URL}/api/v1/auth/google/login"


def exchange_code(code: str):
    return _request("POST", "/api/v1/auth/exchange", json={"code": code}, retries=1)


def request_otp(phone: str):
    return _request("POST", "/api/v1/auth/otp/request", json={"phone": phone}, retries=1)


def verify_otp(phone: str, code: str):
    return _request("POST", "/api/v1/auth/otp/verify", json={"phone": phone, "code": code}, retries=0)


def guest_login():
    return _request("POST", "/api/v1/auth/guest", retries=2)


def delete_account(token=None):
    return _request("DELETE", "/api/v1/auth/me", token=token, retries=0)


# ── App endpoints ─────────────────────────────────────────────────────────────
def predict(payload: Dict[str, Any], token: Optional[str] = None):
    return _request("POST", "/api/v1/predict", json=payload, token=token)


def health() -> Optional[Dict[str, Any]]:
    try:
        r = httpx.get(f"{BACKEND_URL}/api/v1/health", timeout=8.0)
        return r.json() if r.status_code == 200 else None
    except Exception:
        return None


def send_feedback(payload: Dict[str, Any], token: Optional[str] = None):
    return _request("POST", "/api/v1/feedback", json=payload, token=token, retries=1)


def history(limit: int = 100, token: Optional[str] = None):
    return _request("GET", f"/api/v1/history?limit={limit}", token=token, retries=1)


def stats(token: Optional[str] = None):
    return _request("GET", "/api/v1/stats", token=token, retries=1)


def metrics(token: Optional[str] = None):
    return _request("GET", "/api/v1/metrics", token=token, retries=1)


def clear_history(token: Optional[str] = None):
    return _request("DELETE", "/api/v1/history", token=token, retries=0)
