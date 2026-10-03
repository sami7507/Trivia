import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["TRIAVIA_DB_PATH"] = str(Path(tempfile.mkdtemp()) / "test.db")
# Run the whole suite against PostgreSQL:  set TEST_DATABASE_URL=postgresql://user:pass@localhost:5432/dbname
if os.getenv("TEST_DATABASE_URL"):
    os.environ["DATABASE_URL"] = os.environ["TEST_DATABASE_URL"]
else:
    os.environ.pop("DATABASE_URL", None)
os.environ.update({"RATE_LIMIT_PER_MINUTE": "0", "SECRET_KEY": "test-secret-key-test-secret-key-123",
                   "OTP_DEV_ECHO": "true", "GOOGLE_CLIENT_ID": "test-client-id.apps.googleusercontent.com",
                   "GOOGLE_CLIENT_SECRET": "test-secret", "AUTH_REQUIRED": "true",
                   "FRONTEND_URL": "http://localhost:8501"})

import pytest
from fastapi.testclient import TestClient

from backend.core.config import MODEL_PATH

PAYLOAD = {
    "age": 65, "heart_rate": 130, "systolic_bp": 85, "diastolic_bp": 55,
    "temperature": 39.2, "respiratory_rate": 28, "oxygen_saturation": 87,
    "pain_scale": 9, "chief_complaint": "chest_pain",
    "arrival_mode": "ambulance", "consciousness": "verbal",
}


@pytest.fixture(scope="session")
def payload():
    return dict(PAYLOAD)


@pytest.fixture(scope="session", autouse=True)
def _clean_database():
    """Start every test session from empty tables (matters for a persistent Postgres test DB)."""
    from database import db
    with db.connect() as c:
        for table in ("assessments", "otp_codes", "login_codes", "users"):
            c.execute(f"DELETE FROM {table}")
    yield


@pytest.fixture(scope="session")
def client():
    if not MODEL_PATH.exists():  # tiny model so the suite is self-contained
        from model.train import train
        train(1500, 60, 3, make_plots=False, verbose=False)
    from backend.main import app
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def auth(client):
    """Fresh guest session → Authorization header."""
    tok = client.post("/api/v1/auth/guest").json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}
