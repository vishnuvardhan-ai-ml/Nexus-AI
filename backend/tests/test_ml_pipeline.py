"""
Unit tests for NEXUS AI Scikit-learn Intelligence Pipeline, Benchmark Dataset,
Inference Service, and Resilient Fallback Architecture.

Test Coverage:
1. Dataset reproducibility, ethical disclosure labels, and category completeness.
2. Compatible multi-modal preprocessing (TF-IDF + OneHot + StandardScaler).
3. Sparse-to-dense conversion safety for HistGradientBoostingClassifier.
4. Model candidate evaluation (LogisticRegression, RandomForestClassifier, HistGradientBoostingClassifier).
5. Model persistence, metadata packaging, and synthetic demonstration disclosures.
6. Advisory inference execution, confidence probabilities, and advisory flags.
7. Graceful fallback on missing or corrupt model artifacts (INSUFFICIENT_DATA status).
8. Strict protection of the authoritative deterministic risk scoring engine.
"""
from pathlib import Path
import pytest
import numpy as np
import pandas as pd
import joblib

from app.schemas.risk import (
    RiskLevel,
    ModelStatus,
    RiskFactorInput,
    EstimationSource,
)
from app.ml.dataset import (
    generate_synthetic_benchmark_dataset,
    get_train_test_split,
    DATASET_DISCLOSURE_LABEL,
    CATEGORIES,
)
from app.ml.pipeline import (
    build_preprocessor,
    to_dense_array,
    create_candidate_pipelines,
    evaluate_models,
    train_and_save_pipeline,
    DEFAULT_MODEL_PATH,
    MODEL_VERSION,
)
from app.ml.inference import RiskInferenceService
from app.services.risk_engine import assess_risk


# ==============================================================================
# 1. DATASET GENERATION & ETHICAL DISCLOSURE TESTS
# ==============================================================================

def test_dataset_reproducibility():
    """Verify that dataset generation is deterministic with fixed random seeds."""
    df1 = generate_synthetic_benchmark_dataset(n_samples=300, random_state=42)
    df2 = generate_synthetic_benchmark_dataset(n_samples=300, random_state=42)
    df3 = generate_synthetic_benchmark_dataset(n_samples=300, random_state=99)

    pd.testing.assert_frame_equal(df1, df2)
    assert not df1["composite_score"].equals(df3["composite_score"])


def test_dataset_contains_all_categories_and_mandatory_disclosures():
    """
    Verify that dataset includes all 5 civic hazard categories plus general safety,
    and every single record is explicitly tagged with the DEMO DATA disclosure label.
    """
    df = generate_synthetic_benchmark_dataset(n_samples=600, random_state=42)

    # All categories present
    present_categories = set(df["category"].unique())
    for cat in CATEGORIES:
        assert cat in present_categories

    # Explicit disclosure labels on every row
    assert (df["dataset_label"] == DATASET_DISCLOSURE_LABEL).all()
    assert (df["is_synthetic"] == True).all()

    # Bounded values
    assert (df["hazard_severity"] >= 0.0).all() and (df["hazard_severity"] <= 100.0).all()
    assert (df["exposure"] >= 0.0).all() and (df["exposure"] <= 100.0).all()
    assert (df["vulnerability"] >= 0.0).all() and (df["vulnerability"] <= 100.0).all()
    assert (df["duration"] >= 0.0).all() and (df["duration"] <= 100.0).all()
    assert (df["composite_score"] >= 0.0).all() and (df["composite_score"] <= 100.0).all()

    # Valid risk levels
    valid_levels = {RiskLevel.LOW.value, RiskLevel.MEDIUM.value, RiskLevel.HIGH.value}
    assert set(df["risk_level"].unique()).issubset(valid_levels)


def test_get_train_test_split_stratification():
    """Verify that train/test split partitions cleanly without data leakage."""
    df = generate_synthetic_benchmark_dataset(n_samples=300, random_state=42)
    X_train, X_test, y_train, y_test = get_train_test_split(df, test_size=0.2, random_state=42)

    assert len(X_train) + len(X_test) == len(df)
    assert len(X_test) == int(len(df) * 0.2)
    assert set(y_train.unique()) == set(y_test.unique())


# ==============================================================================
# 2. PREPROCESSING & SPARSE/DENSE TRANSFORMATIONS
# ==============================================================================

def test_preprocessing_and_sparse_dense_transformations():
    """
    Verify that ColumnTransformer produces valid features and
    to_dense_array safely converts sparse matrices for HistGradientBoosting.
    """
    df = generate_synthetic_benchmark_dataset(n_samples=60, random_state=42)
    preprocessor = build_preprocessor()

    X_trans = preprocessor.fit_transform(df)

    # Scikit-learn ColumnTransformer output is sparse
    assert hasattr(X_trans, "toarray") or isinstance(X_trans, np.ndarray)

    # Test safe conversion to dense array
    dense_trans = to_dense_array(X_trans)
    assert isinstance(dense_trans, np.ndarray)
    assert not hasattr(dense_trans, "toarray")
    assert dense_trans.shape[0] == 60


# ==============================================================================
# 3. MODEL EVALUATION & PERSISTENCE
# ==============================================================================

def test_candidate_models_evaluation():
    """
    Verify that all 3 candidate models (LogisticRegression, RandomForest, HistGradientBoosting)
    fit cleanly, predict valid classes, and return comparative metrics.
    """
    df = generate_synthetic_benchmark_dataset(n_samples=180, random_state=42)
    X_train, X_test, y_train, y_test = get_train_test_split(df, test_size=0.25, random_state=42)

    best_name, best_pipeline, best_summary, all_evals = evaluate_models(
        X_train=X_train,
        y_train=y_train,
        X_test=X_test,
        y_test=y_test,
        random_state=42,
        cv_folds=3,
    )

    assert best_name in ["LogisticRegression", "RandomForestClassifier", "HistGradientBoostingClassifier"]
    assert len(all_evals) == 3
    for eval_item in all_evals:
        assert eval_item["test_accuracy"] > 0.80
        assert eval_item["test_macro_f1"] > 0.80
        assert eval_item["cv_macro_f1_mean"] > 0.80

    # Ensure best pipeline can predict
    preds = best_pipeline.predict(X_test)
    assert len(preds) == len(X_test)


def test_train_and_save_pipeline_custom_path(tmp_path: Path):
    """Verify complete pipeline training, packaging, and persistence to artifact file."""
    output_file = tmp_path / "test_model_artifact.joblib"
    artifact = train_and_save_pipeline(n_samples=180, output_path=output_file, random_state=42)

    assert output_file.exists()
    assert artifact["model_version"] == MODEL_VERSION
    assert artifact["model_status"] == ModelStatus.DEMO.value
    assert "metrics" in artifact
    assert "dataset_metadata" in artifact
    assert "disclaimer" in artifact

    # Verify reloading with joblib
    reloaded = joblib.load(output_file)
    assert "pipeline" in reloaded
    assert reloaded["algorithm"] == artifact["algorithm"]


# ==============================================================================
# 4. INFERENCE SERVICE & ADVISORY BEHAVIOR
# ==============================================================================

def test_inference_service_predict_advisory():
    """Verify that RiskInferenceService produces structured advisory predictions."""
    service = RiskInferenceService(model_path=DEFAULT_MODEL_PATH, auto_load=True)

    if not service.is_loaded:
        # Train once if not yet generated
        train_and_save_pipeline(n_samples=240, output_path=DEFAULT_MODEL_PATH)
        service.load_model(DEFAULT_MODEL_PATH)

    assert service.is_loaded is True
    assert service.status == ModelStatus.DEMO

    factors = RiskFactorInput(
        hazard_severity=85.0,
        exposure=85.0,
        vulnerability=70.0,
        duration=60.0,
        source=EstimationSource.USER_DIRECT,
    )

    advisory = service.predict_advisory(
        title="High voltage line snapped",
        description="Sparks and active arcing on pavement",
        category="electrical",
        factors=factors,
    )

    assert advisory is not None
    assert advisory["ml_predicted_level"] in ["LOW", "MEDIUM", "HIGH"]
    assert advisory["confidence"] >= 0.0 and advisory["confidence"] <= 1.0
    assert advisory["is_advisory_only"] is True
    assert "class_probabilities" in advisory
    assert "disclaimer" in advisory

    # Status response check
    status_resp = service.get_model_status()
    assert status_resp.status == ModelStatus.DEMO
    assert status_resp.is_probabilistic_forecast is False
    assert len(status_resp.candidate_algorithms_evaluated) >= 1

    # Metrics response check
    metrics_resp = service.get_model_metrics()
    assert metrics_resp.model_status == ModelStatus.DEMO
    assert metrics_resp.accuracy > 0.80


# ==============================================================================
# 5. RESILIENT FALLBACK ON MISSING OR CORRUPT ARTIFACTS
# ==============================================================================

def test_inference_service_missing_artifact_fallback(tmp_path: Path):
    """Verify graceful fallback when model artifact file is missing."""
    missing_path = tmp_path / "non_existent_model.joblib"
    service = RiskInferenceService(model_path=missing_path, auto_load=True)

    assert service.is_loaded is False
    assert service.status == ModelStatus.INSUFFICIENT_DATA

    factors = RiskFactorInput(
        hazard_severity=50.0,
        exposure=50.0,
        vulnerability=50.0,
        duration=50.0,
    )

    # predict_advisory should return None gracefully without raising exceptions
    advisory = service.predict_advisory(
        title="Pothole",
        description="Pothole on road",
        category="road_damage",
        factors=factors,
    )
    assert advisory is None

    # Status response should honestly state INSUFFICIENT_DATA
    status_resp = service.get_model_status()
    assert status_resp.status == ModelStatus.INSUFFICIENT_DATA
    assert "Deterministic Engine Active" in status_resp.primary_algorithm

    # Metrics response should return 0.0 with unavailable disclosure
    metrics_resp = service.get_model_metrics()
    assert metrics_resp.model_status == ModelStatus.INSUFFICIENT_DATA
    assert metrics_resp.accuracy == 0.0


def test_inference_service_corrupt_artifact_fallback(tmp_path: Path):
    """Verify graceful fallback when model artifact file contains corrupted data."""
    corrupt_path = tmp_path / "corrupt_model.joblib"
    with open(corrupt_path, "wb") as f:
        f.write(b"NOT_A_VALID_JOBLIB_PICKLE_HEADER_CORRUPTED_BYTES")

    service = RiskInferenceService(model_path=corrupt_path, auto_load=True)

    assert service.is_loaded is False
    assert service.status == ModelStatus.INSUFFICIENT_DATA


# ==============================================================================
# 6. DETERMINISTIC RISK ENGINE AUTHORITY PRESERVATION
# ==============================================================================

def test_authoritative_deterministic_score_is_never_overridden():
    """
    Verify that assess_risk calculates the authoritative score deterministically
    via R = 0.4H + 0.3E + 0.2V + 0.1D, whether ML advisory is included or excluded.
    """
    factors = RiskFactorInput(
        hazard_severity=70.0,
        exposure=80.0,
        vulnerability=50.0,
        duration=30.0,
        source=EstimationSource.USER_DIRECT,
    )
    # Expected: 0.4(70) + 0.3(80) + 0.2(50) + 0.1(30) = 28 + 24 + 10 + 3 = 65.0 (HIGH)

    # 1. Assessment without ML advisory
    resp_deterministic = assess_risk(factors=factors)
    assert resp_deterministic.risk_score == 65.0
    assert resp_deterministic.risk_level == RiskLevel.HIGH
    assert resp_deterministic.ml_advisory is None

    # 2. Assessment with ML advisory enabled
    resp_with_advisory = assess_risk(
        factors=factors,
        include_ml_advisory=True,
        title="Flooding on Main St",
        description="Drain clogged and water accumulating",
        category="waterlogging",
    )
    # Risk score and level MUST remain strictly authoritative and identical
    assert resp_with_advisory.risk_score == 65.0
    assert resp_with_advisory.risk_level == RiskLevel.HIGH
    assert resp_with_advisory.formula == "R = 0.4H + 0.3E + 0.2V + 0.1D"
    if resp_with_advisory.ml_advisory:
        assert resp_with_advisory.ml_advisory["is_advisory_only"] is True
