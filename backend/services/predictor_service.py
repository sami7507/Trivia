"""
backend/services/predictor_service.py

Business-logic layer between the FastAPI router and the raw model.
Loads artifacts once (singleton) and applies a clinical safety net on top of the ML output.
"""
import logging
import pickle
from pathlib import Path
from typing import List, Tuple

import numpy as np
import pandas as pd

from backend.core.config import ENCODER_PATH, MODEL_PATH, SCALER_PATH, TRIAGE_LEVELS
from backend.schemas.patient import (Contribution, DerivedVitals, FeatureImportanceItem,
                                     PatientInput, TriagePrediction)
from model.training.features import ALL_FEATURES, add_derived

logger = logging.getLogger("uvicorn.error")


# "Normal" reference patient used by the what-if explanation.
BASELINE = {"age": 40, "heart_rate": 80, "systolic_bp": 120, "diastolic_bp": 78, "temperature": 37.0,
            "respiratory_rate": 16, "oxygen_saturation": 98, "pain_scale": 0,
            "chief_complaint": "headache", "arrival_mode": "walk_in", "consciousness": "alert"}
FIELD_LABELS = {  # field → (display name, value format)
    "age": ("Age", "{} yrs"), "heart_rate": ("Heart rate", "{} bpm"),
    "systolic_bp": ("Systolic BP", "{} mmHg"), "diastolic_bp": ("Diastolic BP", "{} mmHg"),
    "temperature": ("Temperature", "{:.1f} °C"), "respiratory_rate": ("Respiratory rate", "{} /min"),
    "oxygen_saturation": ("Oxygen saturation", "{} %"), "pain_scale": ("Pain level", "{} /10"),
    "chief_complaint": ("Main complaint", "{}"), "arrival_mode": ("Arrival", "{}"),
    "consciousness": ("Consciousness", "{}"),
}


def _load(path: Path):
    with open(path, "rb") as f:  # artifacts are produced locally by model/train.py — never load untrusted pickles
        return pickle.load(f)


def safety_floor(raw: dict) -> Tuple[int, List[str]]:
    """Rule-based red flags → minimum triage level the ML model may not go below."""
    level, why = 0, []

    def flag(lvl, msg):
        nonlocal level
        level = max(level, lvl)
        why.append(msg)

    if raw["consciousness"] == "unresponsive":
        flag(3, "Patient is unresponsive")
    if raw["oxygen_saturation"] < 85:
        flag(3, f"Critical hypoxia (SpO₂ {raw['oxygen_saturation']}%)")
    if raw["systolic_bp"] < 70:
        flag(3, f"Profound hypotension (SBP {raw['systolic_bp']} mmHg)")
    if raw["heart_rate"] < 40 or raw["heart_rate"] > 180:
        flag(3, f"Extreme heart rate ({raw['heart_rate']} bpm)")
    if 85 <= raw["oxygen_saturation"] < 90:
        flag(2, f"Severe hypoxia (SpO₂ {raw['oxygen_saturation']}%)")
    if 70 <= raw["systolic_bp"] < 90:
        flag(2, f"Hypotension (SBP {raw['systolic_bp']} mmHg)")
    if raw["respiratory_rate"] > 30 or raw["respiratory_rate"] < 8:
        flag(2, f"Abnormal respiratory rate ({raw['respiratory_rate']}/min)")
    if 140 < raw["heart_rate"] <= 180:
        flag(2, f"Severe tachycardia ({raw['heart_rate']} bpm)")
    if raw["consciousness"] == "pain_response":
        flag(2, "Responds to pain only")
    return level, why


class PredictorService:
    _instance = None

    def __init__(self):
        logger.info("Loading model artifacts …")
        bundle = _load(MODEL_PATH)
        self.model = bundle["model"]
        self.feat_names = bundle["feature_names"]
        self.preprocessor = _load(SCALER_PATH)
        self.label_encoder = _load(ENCODER_PATH)
        logger.info("PredictorService ready ✓")

    @classmethod
    def get_instance(cls) -> "PredictorService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _top_features(self, X: np.ndarray, top_n: int = 6) -> List[FeatureImportanceItem]:
        local = self.model.feature_importances_ * np.abs(X[0])  # cheap local approximation
        idx = np.argsort(local)[::-1][:top_n]
        return [
            FeatureImportanceItem(
                feature=self.feat_names[i].replace("_", " ").title(),
                importance=round(float(local[i]), 5), rank=r + 1)
            for r, i in enumerate(idx)
        ]

    def explain(self, raw: dict, target: int, top_n: int = 6) -> List[Contribution]:
        """
        What-if explanation: for every input, set ONLY that value to a normal baseline and see how the
        model's probability for `target` changes. effect = P(actual) − P(value normalised).
        """
        rows = [raw]
        for field, base in BASELINE.items():
            alt = {**raw, field: base}
            alt["diastolic_bp"] = min(alt["diastolic_bp"], alt["systolic_bp"] - 5)  # stay physiological
            rows.append(alt)
        df = add_derived(pd.DataFrame(rows))
        proba = self.model.predict_proba(self.preprocessor.transform(df[ALL_FEATURES]))
        col = [int(c) for c in self.model.classes_].index(target)
        actual = proba[0, col]
        items = []
        for (field, _), p_alt in zip(BASELINE.items(), proba[1:, col]):
            effect = float(actual - p_alt)
            if abs(effect) < 0.005:
                continue
            name, fmt = FIELD_LABELS[field]
            val = raw[field]
            val = str(val).replace("_", " ") if isinstance(val, str) else val
            items.append(Contribution(feature=name, value=fmt.format(val), effect=round(effect, 4),
                                      direction="raises" if effect > 0 else "lowers"))
        return sorted(items, key=lambda c: abs(c.effect), reverse=True)[:top_n]

    def predict(self, patient: PatientInput) -> TriagePrediction:
        raw = patient.model_dump(mode="json")  # enums → plain strings
        df = add_derived(pd.DataFrame([raw]))
        row = df.iloc[0]

        X = self.preprocessor.transform(df[ALL_FEATURES])
        proba = self.model.predict_proba(X)[0]
        classes = [int(c) for c in self.model.classes_]
        pred = classes[int(np.argmax(proba))]
        p_by_class = {c: float(p) for c, p in zip(classes, proba)}

        model_top = pred  # the level the model itself favoured (before any safety escalation)
        floor, reasons = safety_floor(raw)
        override = floor > pred
        if override:
            pred = floor
        info = TRIAGE_LEVELS[pred]

        return TriagePrediction(
            triage_level=pred,
            triage_label=info["label"],
            confidence=round(p_by_class.get(pred, 0.0), 4),
            probabilities={TRIAGE_LEVELS[c]["label"]: round(p_by_class.get(c, 0.0), 4)
                           for c in range(4)},
            color_code=info["color"],
            action_required=info["action"],
            wait_time=info["wait"],
            derived_vitals=DerivedVitals(
                shock_index=float(row["shock_index"]), map_mmhg=float(row["map_mmhg"]),
                pulse_pressure=int(row["pulse_pressure"]), fever=bool(row["fever_flag"]),
                hypoxia=bool(row["hypoxia_flag"]), tachycardia=bool(row["tachycardia_flag"])),
            top_features=self._top_features(X),
            explanation=self.explain(raw, model_top),
            safety_override=override,
            override_reasons=reasons if override else [],
        )
