"""API tests — the original suite, adapted for authenticated access, plus new cases."""
import pytest

from backend.core.config import MODEL_PATH




class TestPredictEndpoint:
    def test_requires_sign_in(self, client, payload):
        assert client.post("/api/v1/predict", json=payload).status_code == 401

    def test_predict_returns_200(self, client, payload, auth):
        assert client.post("/api/v1/predict", json=payload, headers=auth).status_code == 200

    def test_predict_response_schema(self, client, payload, auth):
        body = client.post("/api/v1/predict", json=payload, headers=auth).json()
        for key in ["triage_level", "triage_label", "confidence", "probabilities", "color_code",
                    "action_required", "wait_time", "derived_vitals", "top_features",
                    "safety_override", "assessment_id", "disclaimer"]:
            assert key in body, f"Missing key: {key}"

    def test_triage_level_and_confidence_range(self, client, payload, auth):
        body = client.post("/api/v1/predict", json=payload, headers=auth).json()
        assert body["triage_level"] in [0, 1, 2, 3] and 0.0 <= body["confidence"] <= 1.0

    def test_probabilities_sum_to_one(self, client, payload, auth):
        body = client.post("/api/v1/predict", json=payload, headers=auth).json()
        assert abs(sum(body["probabilities"].values()) - 1.0) < 0.01

    def test_critical_patient_is_urgent_or_worse(self, client, payload, auth):
        assert client.post("/api/v1/predict", json=payload, headers=auth).json()["triage_level"] >= 2

    def test_low_acuity_patient(self, client, payload, auth):
        mild = {**payload, "age": 25, "heart_rate": 74, "systolic_bp": 122, "diastolic_bp": 80,
                "temperature": 36.7, "respiratory_rate": 15, "oxygen_saturation": 99, "pain_scale": 2,
                "chief_complaint": "laceration", "arrival_mode": "walk_in", "consciousness": "alert"}
        assert client.post("/api/v1/predict", json=mild, headers=auth).json()["triage_level"] <= 1

    def test_safety_override(self, client, payload, auth):
        body = client.post("/api/v1/predict", json={**payload, "consciousness": "unresponsive"},
                           headers=auth).json()
        assert body["triage_level"] == 3

    def test_invalid_patient_422(self, client, payload, auth):
        assert client.post("/api/v1/predict", json={**payload, "age": 999}, headers=auth).status_code == 422


def test_health_endpoint_is_public(client):
    r = client.get("/api/v1/health")
    assert r.status_code == 200 and r.json()["status"] in ["ok", "degraded"]
    assert r.json()["is_model_loaded"] is True and r.json()["database_ok"] is True


def test_metrics_requires_auth_then_works(client, auth):
    assert client.get("/api/v1/metrics").status_code == 401
    assert client.get("/api/v1/metrics", headers=auth).status_code == 200


def test_history_is_private_per_user(client, payload):
    a = {"Authorization": "Bearer " + client.post("/api/v1/auth/guest").json()["access_token"]}
    b = {"Authorization": "Bearer " + client.post("/api/v1/auth/guest").json()["access_token"]}
    client.post("/api/v1/predict", json=payload, headers=a)
    client.post("/api/v1/predict", json=payload, headers=a)
    assert client.get("/api/v1/stats", headers=a).json()["total"] == 2
    assert client.get("/api/v1/stats", headers=b).json()["total"] == 0
    assert client.delete("/api/v1/history", headers=a).json()["deleted"] == 2
    assert client.get("/api/v1/history", headers=a).json() == []


def test_service_api_key(client, payload, monkeypatch):
    from backend.core.config import get_settings
    monkeypatch.setattr(get_settings(), "api_key", "secret")
    assert client.post("/api/v1/predict", json=payload, headers={"X-API-Key": "wrong"}).status_code == 401
    assert client.post("/api/v1/predict", json=payload, headers={"X-API-Key": "secret"}).status_code == 200


def test_auth_not_required_mode(client, payload, monkeypatch):
    from backend.core.config import get_settings
    monkeypatch.setattr(get_settings(), "auth_required", False)
    assert client.post("/api/v1/predict", json=payload).status_code == 200


class TestExplanation:
    def test_explanation_returned_and_sorted(self, client, payload, auth):
        ex = client.post("/api/v1/predict", json=payload, headers=auth).json()["explanation"]
        assert 1 <= len(ex) <= 6
        assert [abs(e["effect"]) for e in ex] == sorted([abs(e["effect"]) for e in ex], reverse=True)
        assert all(e["direction"] == ("raises" if e["effect"] > 0 else "lowers") for e in ex)

    def test_critical_vitals_raise_the_level(self, client, payload, auth):
        ex = client.post("/api/v1/predict", json=payload, headers=auth).json()["explanation"]
        assert any(e["feature"] == "Oxygen saturation" and e["effect"] > 0 for e in ex)

    def test_normal_patient_has_no_big_drivers(self, client, payload, auth):
        normal = {**payload, "age": 40, "heart_rate": 80, "systolic_bp": 120, "diastolic_bp": 78,
                  "temperature": 37.0, "respiratory_rate": 16, "oxygen_saturation": 98, "pain_scale": 0,
                  "chief_complaint": "headache", "arrival_mode": "walk_in", "consciousness": "alert"}
        ex = client.post("/api/v1/predict", json=normal, headers=auth).json()["explanation"]
        assert ex == []   # every value already equals the baseline → nothing to explain
