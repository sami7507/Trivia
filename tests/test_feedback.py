"""In-app feedback: anyone can send it, only the author (service key) can read it."""
import pytest


def test_anyone_can_send_feedback(client):
    r = client.post("/api/v1/feedback", json={"message": "Great demo, love the explanations!", "rating": 5,
                                              "contact": "me@example.com"})
    assert r.status_code == 200 and r.json()["received"] is True and r.json()["id"] > 0


@pytest.mark.parametrize("body", [{"message": ""}, {"message": "hi"}, {"message": "x" * 2001},
                                  {"message": "fine message", "rating": 9}, {"message": "fine message", "extra": 1}])
def test_bad_feedback_rejected(client, body):
    assert client.post("/api/v1/feedback", json=body).status_code == 422


def test_reading_requires_service_key(client, monkeypatch):
    from backend.core.config import get_settings
    assert client.get("/api/v1/feedback").status_code in (401, 403)
    monkeypatch.setattr(get_settings(), "api_key", "author-key")
    assert client.get("/api/v1/feedback", headers={"X-API-Key": "wrong"}).status_code in (401, 403)
    client.post("/api/v1/feedback", json={"message": "readable by the author", "rating": 4})
    rows = client.get("/api/v1/feedback", headers={"X-API-Key": "author-key"}).json()
    assert rows and rows[0]["message"] == "readable by the author" and rows[0]["rating"] == 4


def test_regular_users_cannot_read_feedback(client, auth):
    assert client.get("/api/v1/feedback", headers=auth).status_code == 403


def test_signed_in_feedback_is_linked_then_unlinked_on_account_delete(client, monkeypatch):
    from backend.core.config import get_settings
    from database import db
    tok = client.post("/api/v1/auth/guest").json()["access_token"]
    h = {"Authorization": f"Bearer {tok}"}
    fid = client.post("/api/v1/feedback", json={"message": "linked feedback test"}, headers=h).json()["id"]
    uid = client.get("/api/v1/auth/me", headers=h).json()["id"]
    assert next(r for r in db.list_feedback(500) if r["id"] == fid)["user_id"] == uid
    client.delete("/api/v1/auth/me", headers=h)
    assert next(r for r in db.list_feedback(500) if r["id"] == fid)["user_id"] is None


def test_invalid_token_does_not_block_feedback(client):
    r = client.post("/api/v1/feedback", json={"message": "token is garbage but that's fine"},
                    headers={"Authorization": "Bearer nonsense"})
    assert r.status_code == 200
