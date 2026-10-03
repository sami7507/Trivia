"""
database/auth_store.py — users, one-time SMS codes and single-use login codes.
Secrets (OTP codes, login codes) are only ever stored as hashes.
"""
import hashlib
import hmac
import secrets
import time
from typing import Any, Dict, Optional

from datetime import datetime, timedelta, timezone

from database.db import connect, now_iso

OTP_MAX_ATTEMPTS = 5


def _row(r) -> Optional[Dict[str, Any]]:
    return dict(r) if r else None


# ── Users ─────────────────────────────────────────────────────────────────────
def upsert_user(provider: str, provider_id: str, name: str = "", email: str = "",
                phone: str = "") -> Dict[str, Any]:
    now = now_iso()
    with connect() as c:
        c.execute(
            """INSERT INTO users (provider, provider_id, name, email, phone, created_at, last_login_at)
               VALUES (?,?,?,?,?,?,?)
               ON CONFLICT(provider, provider_id) DO UPDATE SET
                 name = COALESCE(NULLIF(excluded.name,''), users.name),
                 email = COALESCE(NULLIF(excluded.email,''), users.email),
                 last_login_at = excluded.last_login_at""",
            (provider, provider_id, name, email, phone, now, now))
        return dict(c.execute("SELECT * FROM users WHERE provider=? AND provider_id=?",
                              (provider, provider_id)).fetchone())


def get_user(user_id: int) -> Optional[Dict[str, Any]]:
    with connect() as c:
        return _row(c.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone())


def delete_user(user_id: int) -> None:
    with connect() as c:
        c.execute("DELETE FROM assessments WHERE user_id=?", (user_id,))
        c.execute("UPDATE feedback SET user_id=NULL WHERE user_id=?", (user_id,))  # keep feedback, drop the link
        c.execute("DELETE FROM login_codes WHERE user_id=?", (user_id,))
        c.execute("DELETE FROM users WHERE id=?", (user_id,))


def purge_stale() -> None:
    """Remove expired codes and guest accounts older than 24 h (with their data)."""
    now = time.time()
    cutoff = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    with connect() as c:
        c.execute("DELETE FROM otp_codes WHERE expires_at < ?", (now - 3600,))
        c.execute("DELETE FROM login_codes WHERE expires_at < ?", (now,))
        old = [r["id"] for r in c.execute(
            "SELECT id FROM users WHERE provider='guest' AND created_at < ?", (cutoff,)).fetchall()]
        for uid in old:
            c.execute("DELETE FROM assessments WHERE user_id=?", (uid,))
            c.execute("DELETE FROM users WHERE id=?", (uid,))


# ── SMS one-time codes ────────────────────────────────────────────────────────
def count_recent_otps(phone: str, window_s: int = 3600) -> int:
    with connect() as c:
        return int(c.execute("SELECT COUNT(*) AS n FROM otp_codes WHERE phone=? AND created_at > ?",
                             (phone, time.time() - window_s)).fetchone()["n"])


def save_otp(phone: str, code_hash: str, ttl_s: int) -> None:
    now = time.time()
    with connect() as c:
        # Old rows are kept (for the hourly request limit); only the newest code is ever checked.
        c.execute("INSERT INTO otp_codes (phone, code_hash, expires_at, created_at) VALUES (?,?,?,?)",
                  (phone, code_hash, now + ttl_s, now))


def check_otp(phone: str, code_hash: str) -> str:
    """Returns 'ok' | 'invalid' | 'expired' | 'locked' | 'none'."""
    with connect() as c:
        r = c.execute("SELECT * FROM otp_codes WHERE phone=? ORDER BY id DESC LIMIT 1", (phone,)).fetchone()
        if not r:
            return "none"
        if r["expires_at"] < time.time():
            c.execute("DELETE FROM otp_codes WHERE id=?", (r["id"],))
            return "expired"
        if r["attempts"] >= OTP_MAX_ATTEMPTS:
            return "locked"
        if hmac.compare_digest(r["code_hash"], code_hash):
            c.execute("UPDATE otp_codes SET code_hash='consumed' WHERE phone=?", (phone,))  # single use
            return "ok"
        c.execute("UPDATE otp_codes SET attempts = attempts + 1 WHERE id=?", (r["id"],))
        return "invalid"


# ── Single-use login codes (Google redirect → frontend) ───────────────────────
def _h(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()


def create_login_code(user_id: int, ttl_s: int = 120) -> str:
    code = secrets.token_urlsafe(32)
    with connect() as c:
        c.execute("INSERT INTO login_codes (code_hash, user_id, expires_at) VALUES (?,?,?)",
                  (_h(code), user_id, time.time() + ttl_s))
    return code


def consume_login_code(code: str) -> Optional[int]:
    with connect() as c:
        r = c.execute("SELECT user_id, expires_at FROM login_codes WHERE code_hash=?", (_h(code),)).fetchone()
        if not r:
            return None
        c.execute("DELETE FROM login_codes WHERE code_hash=?", (_h(code),))
        return int(r["user_id"]) if r["expires_at"] >= time.time() else None
