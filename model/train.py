"""
Training pipeline.   python model/train.py [--samples N] [--trees N] [--quick]

Produces (all consumed by the API):
    model/artifacts/triage_model.pkl   {"model": RandomForest, "feature_names": [...]}
    model/artifacts/preprocessor.pkl   fitted ColumnTransformer
    model/artifacts/label_encoder.pkl  fitted LabelEncoder
    assets/metrics.json + plots
"""
import argparse
import json
import pickle
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (accuracy_score, classification_report,
                             confusion_matrix, f1_score, roc_auc_score)
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import LabelEncoder, MinMaxScaler, OneHotEncoder

from model.training import config as C
from model.training.data_generator import generate_dataset
from model.training.features import (ALL_FEATURES, CATEGORICAL_FEATURES,
                                     NUMERIC_FEATURES, add_derived)


def _preprocessor() -> ColumnTransformer:
    return ColumnTransformer(
        [("num", Pipeline([("imputer", SimpleImputer(strategy="median")),
                           ("scaler", MinMaxScaler())]), NUMERIC_FEATURES),
         ("cat", Pipeline([("imputer", SimpleImputer(strategy="most_frequent")),
                           ("encoder", OneHotEncoder(handle_unknown="ignore", sparse_output=False))]),
          CATEGORICAL_FEATURES)],
        verbose_feature_names_out=False,
    )


def _forest(n_estimators, seed):
    return RandomForestClassifier(**{**C.RF_PARAMS, "n_estimators": n_estimators, "random_state": seed})


engineer_features = add_derived  # backwards-compatible name used by notebooks/tests


LEVEL_COLORS = ["#22c55e", "#f59e0b", "#ef4444", "#7c3aed"]


def _plots(y_test, y_pred, names, importances, class_counts):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    C.ASSETS_DIR.mkdir(exist_ok=True)

    cm = confusion_matrix(y_test, y_pred)
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.imshow(cm, cmap="Blues")
    ax.set_xticks(range(4), C.LEVEL_NAMES); ax.set_yticks(range(4), C.LEVEL_NAMES)
    for i in range(4):
        for j in range(4):
            ax.text(j, i, cm[i, j], ha="center", va="center", fontsize=12,
                    color="white" if cm[i, j] > cm.max() / 2 else "black")
    ax.set_xlabel("Predicted"); ax.set_ylabel("Actual")
    ax.set_title("Confusion Matrix — Triavia", fontweight="bold")
    fig.tight_layout(); fig.savefig(C.ASSETS_DIR / "confusion_matrix.png", dpi=150); plt.close(fig)

    top = np.argsort(importances)[::-1][:15][::-1]
    fig, ax = plt.subplots(figsize=(9, 6))
    ax.barh([names[i] for i in top], importances[top],
            color=plt.cm.RdYlGn(np.linspace(.3, .85, len(top))), edgecolor="white", height=.65)
    for k, i in enumerate(top):
        ax.text(importances[i] + .002, k, f"{importances[i]:.3f}", va="center", fontsize=9)
    ax.set_title("Top 15 Feature Importances (Random Forest)", fontweight="bold")
    ax.set_xlim(0, importances[top].max() * 1.2)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout(); fig.savefig(C.ASSETS_DIR / "feature_importance.png", dpi=150); plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 5))
    vals = [class_counts.get(n, 0) for n in C.LEVEL_NAMES]
    bars = ax.bar(C.LEVEL_NAMES, vals, color=LEVEL_COLORS, edgecolor="white", width=.55)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + max(vals) * .01, str(v), ha="center", fontweight="bold")
    ax.set_ylabel("Patients"); ax.set_title("Triage Level Distribution", fontweight="bold")
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout(); fig.savefig(C.ASSETS_DIR / "class_distribution.png", dpi=150); plt.close(fig)


def train(n_samples=C.N_SAMPLES, n_estimators=C.RF_PARAMS["n_estimators"], cv_folds=C.CV_FOLDS,
          make_plots=True, seed=C.SEED, verbose=True) -> dict:
    log = print if verbose else (lambda *a, **k: None)
    log(f"[1/5] Generating {n_samples} synthetic patients …")
    raw = generate_dataset(n_samples, seed)
    C.RAW_DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    raw.to_csv(C.RAW_DATA_PATH, index=False)
    df = add_derived(raw)
    df.to_csv(C.PROC_DATA_PATH, index=False)

    X, y = df[ALL_FEATURES], df["triage_level"].astype(int)
    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=C.TEST_SIZE, stratify=y, random_state=seed)

    log(f"[2/5] {cv_folds}-fold stratified cross-validation …")
    cv = StratifiedKFold(cv_folds, shuffle=True, random_state=seed)
    pipe = Pipeline([("pre", _preprocessor()), ("rf", _forest(n_estimators, seed))])
    cv_scores = cross_val_score(pipe, X_tr, y_tr, cv=cv, scoring="f1_weighted", n_jobs=1)

    log("[3/5] Fitting final model …")
    pre = _preprocessor().fit(X_tr)
    model = _forest(n_estimators, seed).fit(pre.transform(X_tr), y_tr)
    feature_names = [str(n) for n in pre.get_feature_names_out()]

    log("[4/5] Evaluating …")
    X_te_t = pre.transform(X_te)
    y_pred = model.predict(X_te_t)
    proba = model.predict_proba(X_te_t)
    imp = model.feature_importances_
    order = np.argsort(imp)[::-1][:15]
    class_counts = {C.LEVEL_NAMES[int(k)]: int(v) for k, v in y.value_counts().sort_index().items()}
    metrics = {
        "accuracy": round(accuracy_score(y_te, y_pred), 4),
        "weighted_f1": round(f1_score(y_te, y_pred, average="weighted"), 4),
        "macro_f1": round(f1_score(y_te, y_pred, average="macro"), 4),
        "roc_auc_ovr": round(roc_auc_score(y_te, proba, multi_class="ovr", average="macro"), 4),
        "roc_auc_weighted": round(roc_auc_score(y_te, proba, multi_class="ovr", average="weighted"), 4),
        "cv_f1_mean": round(float(cv_scores.mean()), 4),
        "cv_f1_std": round(float(cv_scores.std()), 4),
        "confusion_matrix": confusion_matrix(y_te, y_pred).tolist(),
        "classification_report": classification_report(
            y_te, y_pred, target_names=C.LEVEL_NAMES, output_dict=True, zero_division=0),
        "feature_importances": [{"feature": feature_names[i], "importance": round(float(imp[i]), 5)}
                                for i in order],
        "class_distribution": class_counts,
        "model_type": "RandomForestClassifier",
        "n_estimators": int(n_estimators),
        "n_train": int(len(X_tr)),
        "n_test": int(len(X_te)),
        "n_samples": int(n_samples),
        "data_source": "synthetic",
        "trained_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }

    log("[5/5] Saving artifacts …")
    C.ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    le = LabelEncoder().fit([0, 1, 2, 3])
    for name, obj in [("triage_model.pkl", {"model": model, "feature_names": feature_names}),
                      ("preprocessor.pkl", pre), ("label_encoder.pkl", le)]:
        with open(C.ARTIFACT_DIR / name, "wb") as f:
            pickle.dump(obj, f)
    C.ASSETS_DIR.mkdir(exist_ok=True)
    (C.ASSETS_DIR / "metrics.json").write_text(json.dumps(metrics, indent=2))
    if make_plots:
        _plots(y_te, y_pred, feature_names, imp, class_counts)
    log(f"✅ Done — accuracy {metrics['accuracy']}, weighted F1 {metrics['weighted_f1']}, "
        f"AUC {metrics['roc_auc_ovr']}")
    return metrics


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--samples", type=int, default=C.N_SAMPLES)
    ap.add_argument("--trees", type=int, default=C.RF_PARAMS["n_estimators"])
    ap.add_argument("--quick", action="store_true", help="small/fast run for testing")
    a = ap.parse_args()
    if a.quick:
        train(1500, 60, 3, make_plots=False)
    else:
        train(a.samples, a.trees)
