"""
NEXUS AI Multi-Modal Scikit-learn Risk Classification Pipeline.

Features:
- ColumnTransformer combining TF-IDF text features (title + description),
  categorical one-hot encoding, and standard scaled numeric civic factors.
- Safe, explicit sparse-to-dense conversion specifically for HistGradientBoostingClassifier,
  while keeping sparse processing for LogisticRegression and RandomForestClassifier.
- Candidate evaluation: LogisticRegression, RandomForestClassifier, HistGradientBoostingClassifier.
- Stratified 5-fold Cross-Validation + hold-out test set evaluation.
- Model artifact packaging with complete metadata and synthetic-demo disclosures.
"""
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Tuple, Optional, List

import numpy as np
import pandas as pd
import joblib
from sklearn.compose import ColumnTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import OneHotEncoder, StandardScaler, FunctionTransformer
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, HistGradientBoostingClassifier
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score

from app.schemas.risk import ModelStatus
from app.ml.dataset import (
    generate_synthetic_benchmark_dataset,
    get_train_test_split,
    DATASET_DISCLOSURE_LABEL,
)

# Silence loky multi-process warning on Windows
os.environ.setdefault("LOKY_MAX_CPU_COUNT", "4")

DEFAULT_MODEL_DIR = Path(__file__).resolve().parent.parent.parent / "artifacts"
DEFAULT_MODEL_PATH = DEFAULT_MODEL_DIR / "risk_model_v1.joblib"

MODEL_VERSION = "v1.0.0-synthetic-demo"
DEMO_DISCLAIMER = (
    "Advisory Scikit-learn demonstration model. Trained on synthetic civic benchmark data "
    "generated from the weighted multi-criteria formula R = 0.4H + 0.3E + 0.2V + 0.1D (+ noise). "
    "Authoritative operational risk scoring is strictly determined by the deterministic multi-criteria engine. "
    "This model does not claim physical disaster predictive certainty."
)


def to_dense_array(x: Any) -> np.ndarray:
    """
    Safely convert sparse matrix to dense ndarray for estimators requiring dense input
    (specifically HistGradientBoostingClassifier).
    """
    if hasattr(x, "toarray"):
        return x.toarray()
    return np.asarray(x)


def build_preprocessor() -> ColumnTransformer:
    """
    Construct ColumnTransformer combining:
    1. TF-IDF vectorization on text content (max_features=200, ngram_range=(1,2)).
    2. One-hot encoding on category (ignoring unknown categories at inference).
    3. StandardScaler on numeric factor inputs (hazard_severity, exposure, vulnerability, duration).

    Produces a compact sparse matrix (~210 features) without memory blowup.
    """
    return ColumnTransformer(
        transformers=[
            (
                "text",
                TfidfVectorizer(
                    max_features=200,
                    ngram_range=(1, 2),
                    stop_words="english",
                ),
                "text_content",
            ),
            (
                "cat",
                OneHotEncoder(
                    handle_unknown="ignore",
                    sparse_output=True,
                ),
                ["category"],
            ),
            (
                "num",
                StandardScaler(),
                ["hazard_severity", "exposure", "vulnerability", "duration"],
            ),
        ],
        remainder="drop",
    )


def create_candidate_pipelines(random_state: int = 42) -> Dict[str, Pipeline]:
    """
    Construct candidate pipelines with shared preprocessing.
    - LogisticRegression: native sparse support.
    - RandomForestClassifier: native sparse support, single-threaded for Windows reproducibility.
    - HistGradientBoostingClassifier: explicit to_dense_array conversion step.
    """
    return {
        "LogisticRegression": Pipeline([
            ("preprocessor", build_preprocessor()),
            ("classifier", LogisticRegression(
                max_iter=1000,
                random_state=random_state,
                C=1.0,
            )),
        ]),
        "RandomForestClassifier": Pipeline([
            ("preprocessor", build_preprocessor()),
            ("classifier", RandomForestClassifier(
                n_estimators=100,
                max_depth=12,
                random_state=random_state,
                n_jobs=1,
            )),
        ]),
        "HistGradientBoostingClassifier": Pipeline([
            ("preprocessor", build_preprocessor()),
            ("to_dense", FunctionTransformer(to_dense_array, accept_sparse=True)),
            ("classifier", HistGradientBoostingClassifier(
                max_iter=100,
                max_depth=6,
                random_state=random_state,
            )),
        ]),
    }


def evaluate_models(
    X_train: pd.DataFrame,
    y_train: pd.Series,
    X_test: pd.DataFrame,
    y_test: pd.Series,
    random_state: int = 42,
    cv_folds: int = 5,
) -> Tuple[str, Pipeline, Dict[str, Any], List[Dict[str, Any]]]:
    """
    Train and evaluate all candidate models using both hold-out test set and Stratified 5-fold CV.
    Model selection is based on test Macro F1 and CV mean score, avoiding selection on training performance.

    Returns:
        (best_model_name, best_fitted_pipeline, best_model_metrics, all_evaluations_summary)
    """
    candidates = create_candidate_pipelines(random_state=random_state)
    cv = StratifiedKFold(n_splits=cv_folds, shuffle=True, random_state=random_state)

    evaluations: List[Dict[str, Any]] = []
    fitted_pipelines: Dict[str, Pipeline] = {}

    for name, pipeline in candidates.items():
        # Stratified cross-validation on training split
        cv_scores = cross_val_score(pipeline, X_train, y_train, cv=cv, scoring="f1_macro")
        cv_mean = float(np.mean(cv_scores))
        cv_std = float(np.std(cv_scores))

        # Fit on full training split
        pipeline.fit(X_train, y_train)
        fitted_pipelines[name] = pipeline

        # Evaluate on holdout test split
        y_pred = pipeline.predict(X_test)
        test_acc = float(accuracy_score(y_test, y_pred))
        test_f1 = float(f1_score(y_test, y_pred, average="macro"))
        test_prec = float(precision_score(y_test, y_pred, average="macro", zero_division=0))
        test_rec = float(recall_score(y_test, y_pred, average="macro", zero_division=0))

        eval_summary = {
            "algorithm": name,
            "cv_macro_f1_mean": round(cv_mean, 4),
            "cv_macro_f1_std": round(cv_std, 4),
            "test_accuracy": round(test_acc, 4),
            "test_macro_f1": round(test_f1, 4),
            "test_macro_precision": round(test_prec, 4),
            "test_macro_recall": round(test_rec, 4),
        }
        evaluations.append(eval_summary)

    # Sort descending by test_macro_f1, then cv_macro_f1_mean
    evaluations.sort(key=lambda x: (x["test_macro_f1"], x["cv_macro_f1_mean"]), reverse=True)
    best_summary = evaluations[0]
    best_name = best_summary["algorithm"]
    best_pipeline = fitted_pipelines[best_name]

    return best_name, best_pipeline, best_summary, evaluations


def train_and_save_pipeline(
    n_samples: int = 1200,
    output_path: Optional[Path] = None,
    random_state: int = 42,
) -> Dict[str, Any]:
    """
    Generate synthetic civic benchmark dataset, evaluate candidate models, select champion,
    and persist the fitted pipeline with full metadata and disclosures.
    """
    save_path = output_path or DEFAULT_MODEL_PATH
    save_path.parent.mkdir(parents=True, exist_ok=True)

    # 1. Generate synthetic benchmark data
    df = generate_synthetic_benchmark_dataset(n_samples=n_samples, random_state=random_state)
    class_distribution = df["risk_level"].value_counts().to_dict()

    # 2. Split into stratified train & test
    X_train, X_test, y_train, y_test = get_train_test_split(df, test_size=0.2, random_state=random_state)

    # 3. Evaluate candidates
    best_name, best_pipeline, best_metrics, all_evals = evaluate_models(
        X_train=X_train,
        y_train=y_train,
        X_test=X_test,
        y_test=y_test,
        random_state=random_state,
        cv_folds=5,
    )

    # 4. Assemble artifact package
    classes = list(best_pipeline.classes_)
    now_iso = datetime.now(timezone.utc).isoformat()

    artifact = {
        "pipeline": best_pipeline,
        "model_version": MODEL_VERSION,
        "model_status": ModelStatus.DEMO.value,
        "algorithm": best_name,
        "classes": classes,
        "metrics": {
            "accuracy": best_metrics["test_accuracy"],
            "macro_f1": best_metrics["test_macro_f1"],
            "precision_macro": best_metrics["test_macro_precision"],
            "recall_macro": best_metrics["test_macro_recall"],
            "cv_mean_score": best_metrics["cv_macro_f1_mean"],
            "cv_std_score": best_metrics["cv_macro_f1_std"],
            "metric_disclosure": (
                "Metrics reflect performance on synthetic benchmark data generated from the authoritative "
                "scoring formula with noise. High accuracy indicates the model has learned the synthetic civic "
                "scoring rule, NOT independent predictive power over real-world disaster events."
            ),
        },
        "all_evaluations": all_evals,
        "dataset_metadata": {
            "dataset_label": DATASET_DISCLOSURE_LABEL,
            "total_samples": len(df),
            "train_samples": len(X_train),
            "test_samples": len(X_test),
            "class_distribution": class_distribution,
            "random_state": random_state,
            "label_rule": "R = 0.4H + 0.3E + 0.2V + 0.1D + eps (eps ~ N(0, 2.5^2))",
        },
        "disclaimer": DEMO_DISCLAIMER,
        "is_probabilistic_forecast": False,
        "trained_at": now_iso,
    }

    # 5. Persist artifact to disk
    joblib.dump(artifact, save_path)

    return artifact
