"""
Shared feature engineering — used by BOTH training and the API so the two
can never drift apart (no train/serve skew).
"""
import numpy as np
import pandas as pd

from model.training.config import (  # single source of truth for feature lists
    ALL_FEATURES, ALL_NUMERIC, CATEGORICAL_FEATURES, DERIVED_FEATURES,
    NUMERIC_FEATURES as BASE_NUMERIC,
)

NUMERIC_FEATURES = ALL_NUMERIC  # base + derived (what the preprocessor scales)


def add_derived(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of df with clinical indicators added."""
    out = df.copy()
    sbp = out["systolic_bp"].replace(0, np.nan)
    out["shock_index"] = (out["heart_rate"] / sbp).fillna(0.0).round(3)
    out["map_mmhg"] = ((out["systolic_bp"] + 2 * out["diastolic_bp"]) / 3).round(1)
    out["pulse_pressure"] = out["systolic_bp"] - out["diastolic_bp"]
    out["fever_flag"] = (out["temperature"] > 38.0).astype(int)
    out["hypoxia_flag"] = (out["oxygen_saturation"] < 94).astype(int)
    out["tachycardia_flag"] = (out["heart_rate"] > 100).astype(int)
    return out
