"""Sign-in flows: guest, mobile OTP, Google (mocked), sessions."""
import time
from urllib.parse import parse_qs, urlparse

import jwt
import pytest


def test_providers(client):
    p = client.get("/api/v1/auth/providers").json()
    assert p["google"] is True and p["mobile"] is True and p["guest"] is True


def test_guest_session_and_me(client):
    r = client.post("/api/v1/auth/guest")
    assert r.status_code == 200 and r.json()["user"]["provider"] == "guest"
    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {r.json()['access_token']}"})
    assert me.status_code == 200 and me.json()["name"] == "Guest"


def test_guest_disabled(client, monkeypatch):
    from backend.core.config import get_settings
    monkeypatch.setattr(get_settings(), "allow_guest", False)
    assert client.post("/api/v1/auth/guest").status_code == 403


def test_bad_and_expired_tokens_rejected(client):
    assert client.get("/api/v1/auth/me", headers={"Authorization": "Bearer nope"}).status_code == 401
    from backend.services.auth_service import signing_key
    expired = jwt.encode({"sub": "1", "exp": int(time.time()) - 5}, signing_key(), algorithm="HS256")
    assert client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {expired}"}).status_code == 401


class TestMobileOtp:
    phone = "+919876543210"

    def test_full_login(self, client):
        r = client.post("/api/v1/auth/otp/request", json={"phone": self.phone})
        assert r.status_code == 200 and r.json()["delivery"] == "console"
        code = r.json()["dev_otp"]
        v = client.post("/api/v1/auth/otp/verify", json={"phone": self.phone, "code": code})
        assert v.status_code == 200
        assert v.json()["user"]["provider"] == "mobile"
        assert "9876" not in v.json()["user"]["phone_masked"]          # masked
        # a code is single-use
        assert client.post("/api/v1/auth/otp/verify", json={"phone": self.phone, "code": code}).status_code == 401

    def test_same_phone_same_account(self, client):
        ids = []
        for _ in range(2):
            code = client.post("/api/v1/auth/otp/request", json={"phone": "+14155552671"}).json()["dev_otp"]
            ids.append(client.post("/api/v1/auth/otp/verify",
                                   json={"phone": "+14155552671", "code": code}).json()["user"]["id"])
        assert ids[0] == ids[1]

    def test_wrong_code_locks_after_5_attempts(self, client):
        phone = "+447911123456"
        real = client.post("/api/v1/auth/otp/request", json={"phone": phone}).json()["dev_otp"]
        wrong = "000000" if real != "000000" else "111111"
        for _ in range(5):
            assert client.post("/api/v1/auth/otp/verify", json={"phone": phone, "code": wrong}).status_code == 401
        r = client.post("/api/v1/auth/otp/verify", json={"phone": phone, "code": real})
        assert r.status_code == 401 and "attempts" in r.json()["detail"]

    def test_invalid_phone_422(self, client):
        assert client.post("/api/v1/auth/otp/request", json={"phone": "12345"}).status_code == 422

    def test_request_rate_limit(self, client):
        phone = "+61412345678"
        codes = [client.post("/api/v1/auth/otp/request", json={"phone": phone}).status_code for _ in range(6)]
        assert codes[:5] == [200] * 5 and codes[5] == 429

    def test_otp_not_stored_in_plain_text(self, client):
        from database.db import connect
        phone = "+819012345678"
        code = client.post("/api/v1/auth/otp/request", json={"phone": phone}).json()["dev_otp"]
        with connect() as c:
            stored = c.execute("SELECT code_hash FROM otp_codes WHERE phone=?", (phone,)).fetchone()["code_hash"]
        assert stored != code and len(stored) == 64


class TestGoogle:
    def test_login_redirects_to_google_with_state(self, client):
        r = client.get("/api/v1/auth/google/login", follow_redirects=False)
        assert r.status_code == 302
        loc = urlparse(r.headers["location"])
        q = parse_qs(loc.query)
        assert loc.netloc == "accounts.google.com"
        assert q["client_id"][0].startswith("test-client-id") and "state" in q
        assert q["redirect_uri"][0].endswith("/api/v1/auth/google/callback")
        assert "triavia_oauth" in r.headers["set-cookie"] and "httponly" in r.headers["set-cookie"].lower()

    def test_callback_rejects_bad_state(self, client):
        r = client.get("/api/v1/auth/google/callback?code=abc&state=forged", follow_redirects=False)
        assert r.status_code == 302 and "auth_error" in r.headers["location"]

    def test_full_flow_with_mocked_google(self, client, monkeypatch):
        from backend.services import auth_service
        monkeypatch.setattr(auth_service, "exchange_google_code",
                            lambda code: {"sub": "g-123", "email": "sami@example.com",
                                          "name": "Sami Test", "email_verified": True})
        login = client.get("/api/v1/auth/google/login", follow_redirects=False)
        state = parse_qs(urlparse(login.headers["location"]).query)["state"][0]
        cb = client.get(f"/api/v1/auth/google/callback?code=goog&state={state}", follow_redirects=False)
        assert cb.status_code == 302
        loc = urlparse(cb.headers["location"])
        assert loc.netloc == "localhost:8501"
        one_time = parse_qs(loc.query)["code"][0]
        ex = client.post("/api/v1/auth/exchange", json={"code": one_time})
        assert ex.status_code == 200 and ex.json()["user"]["email"] == "sami@example.com"
        # the one-time code cannot be replayed
        assert client.post("/api/v1/auth/exchange", json={"code": one_time}).status_code == 401

    def test_callback_without_cookie_is_rejected(self, client):
        state, _ = __import__("backend.services.auth_service", fromlist=["x"]).make_state()
        client.cookies.clear()
        r = client.get(f"/api/v1/auth/google/callback?code=goog&state={state}", follow_redirects=False)
        assert "auth_error" in r.headers["location"]


def test_delete_account_removes_data(client, payload):
    tok = client.post("/api/v1/auth/guest").json()["access_token"]
    h = {"Authorization": f"Bearer {tok}"}
    client.post("/api/v1/predict", json=payload, headers=h)
    assert client.delete("/api/v1/auth/me", headers=h).json() == {"deleted": True}
    assert client.get("/api/v1/auth/me", headers=h).status_code == 401
