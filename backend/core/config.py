"""
backend/core/config.py
Settings (env-driven), paths and triage level definitions.
"""
from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT_DIR = Path(__file__).resolve().parent.parent.parent

TRIAGE_LEVELS = {
    0: {"label": "Non-Urgent", "color": "#22c55e",
        "action": "Standard care — can be managed in fast-track",
        "wait": "2–4 hours"},
    1: {"label": "Semi-Urgent", "color": "#f59e0b",
        "action": "Monitor vitals every 30 min — physician review within 1–2 hours",
        "wait": "1–2 hours"},
    2: {"label": "Urgent", "color": "#ef4444",
        "action": "Immediate nursing assessment + physician notification — IV access mandatory",
        "wait": "Within 30 minutes"},
    3: {"label": "Resuscitation", "color": "#7c3aed",
        "action": "ACTIVATE RESUSCITATION TEAM — airway management, IV ×2, full monitoring",
        "wait": "Immediate"},
}

MODEL_PATH = ROOT_DIR / "model" / "artifacts" / "triage_model.pkl"
SCALER_PATH = ROOT_DIR / "model" / "artifacts" / "preprocessor.pkl"
ENCODER_PATH = ROOT_DIR / "model" / "artifacts" / "label_encoder.pkl"
METRICS_PATH = ROOT_DIR / "assets" / "metrics.json"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Triavia"
    version: str = "2.2.0"
    author: str = "Sami"
    contact: str = "sami757007@gmail.com"
    debug: bool = False

    # Security
    cors_origins: str = "*"          # comma-separated; set to your Streamlit URL in production
    api_key: str = ""                # optional machine-to-machine key (X-API-Key header)
    rate_limit_per_minute: int = 60  # per client IP, 0 = off

    # Authentication
    auth_required: bool = True       # require sign-in for predictions/history
    allow_guest: bool = True         # "Continue as guest" button (demos/interviews)
    secret_key: str = ""             # JWT signing key — SET THIS in production (long random string)
    jwt_expire_minutes: int = 720
    guest_expire_minutes: int = 120
    frontend_url: str = "http://localhost:8501"       # where Google sign-in returns the user
    backend_public_url: str = "http://localhost:8000"  # used to build the Google redirect URI

    # Google sign-in (OAuth 2.0 authorization-code flow)
    google_client_id: str = ""
    google_client_secret: str = ""

    # Mobile (SMS one-time code) sign-in
    sms_provider: str = "console"    # console (prints code in API logs) | twilio
    otp_ttl_seconds: int = 300
    otp_dev_echo: bool = False       # LOCAL DEMOS ONLY: return the code in the API response
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_from: str = ""


    @property
    def google_enabled(self) -> bool:
        return bool(self.google_client_id and self.google_client_secret)

    @property
    def twilio_enabled(self) -> bool:
        return self.sms_provider == "twilio" and bool(
            self.twilio_account_sid and self.twilio_auth_token and self.twilio_from)

    @property
    def cors_origin_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()] or ["*"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
