"""
model/training/data_generator.py
Generates a realistic, class-imbalanced synthetic triage dataset.
Replace with a real dataset (MIMIC-III, eICU) for production.
"""

import numpy as np
import pandas as pd
from model.training.config import RAW_DATA_PATH

CHIEF_COMPLAINTS = [
    "chest_pain","shortness_of_breath","abdominal_pain","headache","fever",
    "trauma","dizziness","syncope","palpitations","back_pain",
    "nausea_vomiting","laceration","fracture","allergic_reaction","altered_mental_status",
]
ARRIVAL_MODES = ["ambulance","walk_in","police","helicopter"]
CONSCIOUSNESS  = ["alert","verbal","pain_response","unresponsive"]

_DISTS = {
    # cls → (age, hr, sbp, dbp, temp, rr, spo2, pain)
    0: dict(age=(45,20), hr=(80,12), sbp=(120,10), dbp=(78,8),
            temp=(37.0,.4), rr=(16,2), spo2=(98,1), pain=(2,1.5)),
    1: dict(age=(52,18), hr=(92,15), sbp=(130,15), dbp=(82,10),
            temp=(37.8,.6), rr=(19,3), spo2=(96,2), pain=(5,2)),
    2: dict(age=(58,20), hr=(110,20), sbp=(150,20), dbp=(90,12),
            temp=(38.5,.8), rr=(24,4), spo2=(93,3), pain=(7,2)),
    3: dict(age=(62,22), hr=(135,25), sbp=(90,25), dbp=(60,15),
            temp=(39.2,1.0), rr=(30,6), spo2=(88,4), pain=(9,1)),
}

_CC_WEIGHTS = {
    3:[.3,.2,.1,.05,.05,.1,.05,.05,.02,.02,.01,.01,.01,.02,.01],
    2:[.15,.15,.1,.08,.05,.12,.08,.07,.05,.04,.03,.03,.03,.02,.0],
    1:[.05,.05,.15,.1,.12,.05,.1,.05,.08,.1,.05,.02,.03,.02,.03],
    0:[.02,.02,.1,.12,.18,.03,.1,.02,.05,.15,.1,.05,.04,.01,.01],
}
_CON_WEIGHTS = {3:[.1,.2,.3,.4],2:[.3,.4,.2,.1],1:[.7,.25,.04,.01],0:[.95,.04,.01,.0]}


def generate_dataset(n: int = 6000, seed: int = 42) -> pd.DataFrame:
    # Seeded here (not at import time) so importing this module has no side effects.
    np.random.seed(seed)
    props = {0:.35, 1:.30, 2:.25, 3:.10}
    parts = []
    for cls, p in props.items():
        k = int(n * p)
        d = _DISTS[cls]
        w = np.array(_CC_WEIGHTS[cls]); w /= w.sum()
        am_w = [.4,.45,.05,.1] if cls >= 2 else [.1,.8,.05,.05]
        df = pd.DataFrame({
            "age":               np.clip(np.random.normal(d["age"][0],   d["age"][1],   k).astype(int),1,100),
            "heart_rate":        np.clip(np.random.normal(d["hr"][0],    d["hr"][1],    k).astype(int),30,220),
            "systolic_bp":       np.clip(np.random.normal(d["sbp"][0],   d["sbp"][1],   k).astype(int),50,240),
            "diastolic_bp":      np.clip(np.random.normal(d["dbp"][0],   d["dbp"][1],   k).astype(int),30,140),
            "temperature":       np.clip(np.round(np.random.normal(d["temp"][0],d["temp"][1],k),1),35.0,41.5),
            "respiratory_rate":  np.clip(np.random.normal(d["rr"][0],    d["rr"][1],    k).astype(int),8,50),
            "oxygen_saturation": np.clip(np.random.normal(d["spo2"][0],  d["spo2"][1],  k).astype(int),70,100),
            "pain_scale":        np.clip(np.random.normal(d["pain"][0],  d["pain"][1],  k).astype(int),0,10),
            "chief_complaint":   np.random.choice(CHIEF_COMPLAINTS, k, p=w),
            "arrival_mode":      np.random.choice(ARRIVAL_MODES, k, p=am_w),
            "consciousness":     np.random.choice(CONSCIOUSNESS, k, p=_CON_WEIGHTS[cls]),
            "triage_level":      cls,
        })
        parts.append(df)

    out = pd.concat(parts, ignore_index=True).sample(frac=1, random_state=seed).reset_index(drop=True)
    # Physiological consistency: diastolic must stay below systolic (the API enforces the same rule).
    out["diastolic_bp"] = np.minimum(out["diastolic_bp"], out["systolic_bp"] - 10)
    for col in ["temperature","diastolic_bp","pain_scale"]:
        out.loc[np.random.rand(len(out)) < .03, col] = np.nan   # simulate missing values
    return out


if __name__ == "__main__":
    RAW_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    df = generate_dataset()
    df.to_csv(RAW_DATA_PATH, index=False)
    print(f"Saved {len(df)} rows → {RAW_DATA_PATH}")
    print(df["triage_level"].value_counts().sort_index())
