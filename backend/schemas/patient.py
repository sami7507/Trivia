"""
backend/schemas/patient.py
Pydantic models for request validation and response formatting.
"""
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class ArrivalMode(str, Enum):
    walk_in = "walk_in"
    ambulance = "ambulance"
    police = "police"
    helicopter = "helicopter"


class ConsciousnessLevel(str, Enum):
    alert = "alert"
    verbal = "verbal"
    pain_response = "pain_response"
    unresponsive = "unresponsive"


class ChiefComplaint(str, Enum):
    chest_pain = "chest_pain"
    shortness_of_breath = "shortness_of_breath"
    abdominal_pain = "abdominal_pain"
    headache = "headache"
    fever = "fever"
    trauma = "trauma"
    dizziness = "dizziness"
    syncope = "syncope"
    palpitations = "palpitations"
    back_pain = "back_pain"
    nausea_vomiting = "nausea_vomiting"
    laceration = "laceration"
    fracture = "fracture"
    allergic_reaction = "allergic_reaction"
    altered_mental_status = "altered_mental_status"


# ── Request ────────────────────────────────────────────────────────────────────
class PatientInput(BaseModel):
    age: int = Field(..., ge=1, le=120, description="Patient age in years")
    heart_rate: int = Field(..., ge=20, le=300, description="Heart rate (bpm)")
    systolic_bp: int = Field(..., ge=40, le=260, description="Systolic blood pressure (mmHg)")
    diastolic_bp: int = Field(..., ge=20, le=160, description="Diastolic blood pressure (mmHg)")
    temperature: float = Field(..., ge=34.0, le=42.5, description="Body temperature (°C)")
    respiratory_rate: int = Field(..., ge=5, le=60, description="Respiratory rate (breaths/min)")
    oxygen_saturation: int = Field(..., ge=50, le=100, description="SpO₂ (%)")
    pain_scale: int = Field(..., ge=0, le=10, description="Pain scale 0–10")
    chief_complaint: ChiefComplaint
    arrival_mode: ArrivalMode
    consciousness: ConsciousnessLevel

    model_config = {
        "extra": "forbid",
        "json_schema_extra": {
            "example": {
                "age": 65, "heart_rate": 130, "systolic_bp": 85, "diastolic_bp": 55,
                "temperature": 39.2, "respiratory_rate": 28, "oxygen_saturation": 87,
                "pain_scale": 9, "chief_complaint": "chest_pain",
                "arrival_mode": "ambulance", "consciousness": "verbal",
            }
        },
    }

    @field_validator("temperature")
    @classmethod
    def _round_temp(cls, v: float) -> float:
        return round(v, 1)  # 38.29999999999999 → 38.3

    @model_validator(mode="after")
    def _bp_consistent(self):
        if self.diastolic_bp >= self.systolic_bp:
            raise ValueError("diastolic_bp must be lower than systolic_bp")
        return self


# ── Responses ──────────────────────────────────────────────────────────────────
DISCLAIMER = ("Educational decision-support demo. Not a medical device. "
              "Always follow clinical protocols and professional judgement.")


class FeatureImportanceItem(BaseModel):
    feature: str
    importance: float
    rank: int


class Contribution(BaseModel):
    feature: str = Field(..., description="Human-readable name, e.g. 'Oxygen saturation'")
    value: str = Field(..., description="The patient's value, e.g. '87 %'")
    effect: float = Field(..., description="Change in the predicted level's probability caused by this value "
                                           "(+ raises, − lowers) versus a normal baseline")
    direction: str = Field(..., description="'raises' or 'lowers'")


class DerivedVitals(BaseModel):
    shock_index: float = Field(..., description="HR / Systolic BP")
    map_mmhg: float = Field(..., description="Mean Arterial Pressure")
    pulse_pressure: int = Field(..., description="Systolic - Diastolic BP")
    fever: bool
    hypoxia: bool
    tachycardia: bool


class TriagePrediction(BaseModel):
    triage_level: int = Field(..., description="0=Non-Urgent, 1=Semi-Urgent, 2=Urgent, 3=Resuscitation")
    triage_label: str
    confidence: float = Field(..., description="Model probability of the returned level, 0–1")
    probabilities: Dict[str, float]
    color_code: str = Field(..., description="Hex color for UI")
    action_required: str = Field(..., description="Clinical action descriptor")
    wait_time: str
    derived_vitals: DerivedVitals
    top_features: List[FeatureImportanceItem]
    explanation: List[Contribution] = Field(default_factory=list,
                                            description="What-if explanation: why the model leaned this way")
    safety_override: bool = Field(False, description="True if rule-based red flags raised the level")
    override_reasons: List[str] = Field(default_factory=list)
    assessment_id: Optional[int] = None
    disclaimer: str = DISCLAIMER
    api_version: str = Field(default="2.2.0", description="API version")

    model_config = {"protected_namespaces": ()}


class HealthResponse(BaseModel):
    status: str
    is_model_loaded: bool
    database_ok: bool = True
    database_engine: str = "sqlite"
    version: str

    model_config = {"protected_namespaces": ()}


class AssessmentRecord(BaseModel):
    id: int
    created_at: str
    age: int
    chief_complaint: str
    triage_level: int
    triage_label: str
    confidence: float
    safety_override: bool


class StatsResponse(BaseModel):
    total: int
    by_level: Dict[str, int]
    avg_confidence: Optional[float] = None


class ErrorResponse(BaseModel):
    detail: str
    code: int
