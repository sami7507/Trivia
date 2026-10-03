"""
backend/core/security.py
Principal resolution (user JWT / service API key), security headers, rate limiter.
"""
import secrets
import time
from collections import defaultdict, deque
from dataclasses import dataclass
from typing import Optional

import jwt
from fastapi import Depends, Header, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from backend.core.config import get_settings


@dataclass
class Principal:
    kind: str                       # "user" | "service" | "anon"
    user_id: Optional[int] = None
    name: str = ""

    @property
    def scope_user_id(self) -> Optional[int]:
        """Only real users are restricted to their own data."""
        return self.user_id if self.kind == "user" else None


def get_principal(authorization: str = Header(default=""),
                  x_api_key: str = Header(default="")) -> Principal:
    from backend.services import auth_service  # local import avoids cycles
    from database import auth_store

    s = get_settings()
    if authorization.lower().startswith("bearer "):
        try:
            payload = auth_service.decode_token(authorization[7:].strip())
            user = auth_store.get_user(int(payload["sub"]))
        except (jwt.PyJWTError, ValueError):
            user = None
        if not user:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Session expired. Please sign in again.",
                                headers={"WWW-Authenticate": "Bearer"})
        return Principal("user", user["id"], user.get("name") or "")
    if s.api_key and x_api_key and secrets.compare_digest(x_api_key.encode(), s.api_key.encode()):
        return Principal("service", None, "service")
    if not s.auth_required:
        return Principal("anon")
    raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Please sign in to continue.",
                        headers={"WWW-Authenticate": "Bearer"})


def optional_principal(authorization: str = Header(default="")) -> Principal:
    """Like get_principal but never fails — used by public endpoints that merely *prefer* to know the user."""
    from backend.services import auth_service
    from database import auth_store
    try:
        if authorization.lower().startswith("bearer "):
            payload = auth_service.decode_token(authorization[7:].strip())
            user = auth_store.get_user(int(payload["sub"]))
            if user:
                return Principal("user", user["id"], user.get("name") or "")
    except Exception:
        pass
    return Principal("anon")


def require_service(p: Principal = Depends(get_principal)) -> Principal:
    """Only the holder of the server's API_KEY (the author) may read feedback."""
    if p.kind != "service":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Service access required (send the X-API-Key header).")
    return p


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Sliding-window limiter per client IP (single-process; use Redis if you scale out)."""

    def __init__(self, app):
        super().__init__(app)
        self.hits = defaultdict(deque)

    async def dispatch(self, request, call_next):
        limit = get_settings().rate_limit_per_minute
        path = request.url.path
        if limit <= 0 or not path.startswith("/api/") or path.endswith("/health"):
            return await call_next(request)
        fwd = request.headers.get("x-forwarded-for", "")
        ip = fwd.split(",")[0].strip() or (request.client.host if request.client else "unknown")
        now = time.monotonic()
        q = self.hits[ip]
        while q and now - q[0] > 60:
            q.popleft()
        if len(q) >= limit:
            retry = max(1, int(60 - (now - q[0])))
            return JSONResponse({"detail": "Too many requests. Please slow down."},
                                status_code=429, headers={"Retry-After": str(retry)})
        q.append(now)
        return await call_next(request)
