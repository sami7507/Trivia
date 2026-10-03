"""
model/training/config.py  — ML pipeline configuration
"""
from pathlib import Path

ROOT_DIR      = Path(__file__).resolve().parent.parent.parent
DATA_DIR      = ROOT_DIR / "data"
RAW_DATA_PATH = DATA_DIR / "raw"  / "triage_dataset.csv"
PROC_DATA_PATH= DATA_DIR / "processed" / "triage_processed.csv"
ARTIFACT_DIR  = ROOT_DIR / "model" / "artifacts"
ASSETS_DIR    = ROOT_DIR / "assets"

NUMERIC_FEATURES = [
    "age", "heart_rate", "systolic_bp", "diastolic_bp",
    "temperature", "respiratory_rate", "oxygen_saturation", "pain_scale",
]
DERIVED_FEATURES = [
    "shock_index", "map_mmhg", "pulse_pressure",
    "fever_flag", "hypoxia_flag", "tachycardia_flag",
]
CATEGORICAL_FEATURES = ["chief_complaint", "arrival_mode", "consciousness"]
ALL_NUMERIC   = NUMERIC_FEATURES + DERIVED_FEATURES
ALL_FEATURES  = ALL_NUMERIC + CATEGORICAL_FEATURES
TARGET_COLUMN = "triage_level"

RANDOM_STATE  = 42
TEST_SIZE     = 0.20
CV_FOLDS      = 5
N_SAMPLES     = 6000
SEED          = RANDOM_STATE

RF_PARAMS = {
    "n_estimators":      300,
    "max_depth":         None,
    "min_samples_split": 4,
    "min_samples_leaf":  2,
    "class_weight":      "balanced",
    "random_state":      RANDOM_STATE,
    "n_jobs":            -1,
}

# Reserved for an optional XGBoost experiment (xgboost is not a runtime dependency).
XGB_PARAMS = {
    "n_estimators":       300,
    "max_depth":          6,
    "learning_rate":      0.05,
    "subsample":          0.8,
    "colsample_bytree":   0.8,
    "eval_metric":        "mlogloss",
    "random_state":       RANDOM_STATE,
    "n_jobs":             -1,
}

TRIAGE_LABELS = {0: "Non-Urgent", 1: "Semi-Urgent", 2: "Urgent", 3: "Resuscitation"}
LEVEL_NAMES   = [TRIAGE_LABELS[i] for i in range(4)]
