"""
NEXUS AI Scikit-learn Risk Advisory Inference Service.

CRITICAL ARCHITECTURAL CONSTRAINTS:
1. Operational Risk Authority: The deterministic weighted risk formula
   (R = 0.4H + 0.3E + 0.2V + 0.1D) is ALWAYS the primary, authoritative risk engine.
2. Advisory Role Only: ML classification predictions are advisory secondary context.
   They NEVER overwrite, replace, or silently manipulate the authoritative score.
3. Model Status Transparency: Status is reported as DEMO or INSUFFICIENT_DATA.
   It is NEVER claimed to predict real-world disasters with physical certainty.
4. Fault Tolerance: If model artifacts are missing, corrupt, or uninitialized,
   the service fails gracefully without crashing the application or tests.
"""
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
import numpy as np
import pandas as pd
import joblib

from app.schemas.risk import (
    ModelStatus,
    RiskFactorInput,
    ModelStatusResponse,
    ModelMetricsResponse,
)
from app.ml.pipeline import DEFAULT_MODEL_PATH, MODEL_VERSION, DEMO_DISCLAIMER

logger = logging.getLogger("nexus.ml.inference")


class RiskInferenceService:
    """
    Manages Scikit-learn risk advisory classification inference,
    model lifecycle, and transparency telemetry.
    """

    def __init__(
        self,
        model_path: Optional[Path] = None,
        auto_load: bool = True,
    ) -> None:
        self.model_path = model_path or DEFAULT_MODEL_PATH
        self.pipeline: Any = None
        self.artifact_metadata: Dict[str, Any] = {}
        self.is_loaded: bool = False
        self.status: ModelStatus = ModelStatus.INSUFFICIENT_DATA
        self.model_version: str = MODEL_VERSION
        self.primary_algorithm: str = "Unavailable"
        self.candidate_algorithms: List[str] = []
        self.classes: List[str] = ["HIGH", "LOW", "MEDIUM"]

        if auto_load:
            self.load_model(self.model_path)

    def load_model(self, model_path: Optional[Path] = None) -> bool:
        """
        Safely load model artifact from disk.
        Returns True if loaded, False if missing or corrupted.
        """
        target_path = model_path or self.model_path
        if not target_path.exists():
            logger.warning(
                f"Model artifact not found at {target_path}. "
                "Operating in INSUFFICIENT_DATA fallback mode (deterministic engine active)."
            )
            self.is_loaded = False
            self.status = ModelStatus.INSUFFICIENT_DATA
            self.pipeline = None
            return False

        try:
            artifact = joblib.load(target_path)
            if not isinstance(artifact, dict) or "pipeline" not in artifact:
                raise ValueError("Artifact format invalid: missing 'pipeline' key")

            self.pipeline = artifact["pipeline"]
            self.artifact_metadata = artifact
            self.model_version = artifact.get("model_version", MODEL_VERSION)
            self.status = ModelStatus(artifact.get("model_status", ModelStatus.DEMO.value))
            self.primary_algorithm = artifact.get("algorithm", "Scikit-Learn Classifier")
            self.classes = list(getattr(self.pipeline, "classes_", ["HIGH", "LOW", "MEDIUM"]))

            evals = artifact.get("all_evaluations", [])
            self.candidate_algorithms = [e.get("algorithm", "") for e in evals if "algorithm" in e]
            if not self.candidate_algorithms and self.primary_algorithm:
                self.candidate_algorithms = [self.primary_algorithm]

            self.is_loaded = True
            logger.info(f"Loaded ML model '{self.primary_algorithm}' ({self.model_version}) with status {self.status.value}")
            return True

        except Exception as exc:
            logger.error(
                f"Failed to load model artifact from {target_path}: {exc}. "
                "Falling back to INSUFFICIENT_DATA mode."
            )
            self.is_loaded = False
            self.status = ModelStatus.INSUFFICIENT_DATA
            self.pipeline = None
            return False

    def predict_advisory(
        self,
        title: str,
        description: str,
        category: str,
        factors: RiskFactorInput,
    ) -> Optional[Dict[str, Any]]:
        """
        Generate non-authoritative advisory classification and confidence probabilities.
        Returns None if model is unavailable or in fallback mode.
        """
        if not self.is_loaded or self.pipeline is None:
            return None

        try:
            # Build input row matching training feature set
            combined_text = f"{title}. {description}"
            input_df = pd.DataFrame([{
                "title": title,
                "description": description,
                "text_content": combined_text,
                "category": category.lower(),
                "hazard_severity": float(factors.hazard_severity),
                "exposure": float(factors.exposure),
                "vulnerability": float(factors.vulnerability),
                "duration": float(factors.duration),
            }])

            predicted_label = str(self.pipeline.predict(input_df)[0])

            # Extract class probability distribution if supported
            probabilities: Dict[str, float] = {}
            confidence = 1.0
            if hasattr(self.pipeline, "predict_proba"):
                probs = self.pipeline.predict_proba(input_df)[0]
                for cls_name, prob in zip(self.classes, probs):
                    probabilities[cls_name] = round(float(prob), 4)
                if predicted_label in probabilities:
                    confidence = probabilities[predicted_label]
                else:
                    confidence = float(np.max(probs))

            return {
                "ml_predicted_level": predicted_label,
                "confidence": round(float(confidence), 3),
                "class_probabilities": probabilities,
                "model_status": self.status.value,
                "model_version": self.model_version,
                "primary_algorithm": self.primary_algorithm,
                "is_advisory_only": True,
                "disclaimer": (
                    "Advisory demonstration prediction. Authoritative operational risk score is "
                    "computed deterministically by the multi-criteria engine."
                ),
            }

        except Exception as exc:
            logger.warning(f"Inference calculation failed: {exc}. Advisory skipped.")
            return None

    def get_model_status(self) -> ModelStatusResponse:
        """Return transparency disclosure on model operational readiness."""
        now_iso = datetime.now(timezone.utc).isoformat()
        dataset_meta = self.artifact_metadata.get("dataset_metadata", {})
        total_samples = dataset_meta.get("total_samples", 0)

        if not self.is_loaded:
            return ModelStatusResponse(
                status=ModelStatus.INSUFFICIENT_DATA,
                model_version="unavailable",
                primary_algorithm="None (Deterministic Engine Active)",
                candidate_algorithms_evaluated=[],
                training_sample_count=0,
                data_source_disclosure="No validated machine learning model artifact found on system.",
                is_probabilistic_forecast=False,
                disclaimer="Operational risk scoring is executing exclusively via deterministic civic formulas.",
                last_evaluated_at=now_iso,
            )

        return ModelStatusResponse(
            status=self.status,
            model_version=self.model_version,
            primary_algorithm=self.primary_algorithm,
            candidate_algorithms_evaluated=self.candidate_algorithms,
            training_sample_count=total_samples,
            data_source_disclosure=(
                f"Trained on {total_samples} synthetic civic hazard scenarios labeled via "
                "deterministic multi-criteria formula with Gaussian noise. Disclosed as DEMO DATA."
            ),
            is_probabilistic_forecast=False,
            disclaimer=DEMO_DISCLAIMER,
            last_evaluated_at=self.artifact_metadata.get("trained_at", now_iso),
        )

    def get_model_metrics(self) -> ModelMetricsResponse:
        """Return benchmark evaluation metrics on hold-out test split."""
        dataset_meta = self.artifact_metadata.get("dataset_metadata", {})
        metrics = self.artifact_metadata.get("metrics", {})

        if not self.is_loaded or not metrics:
            return ModelMetricsResponse(
                model_version="unavailable",
                model_status=ModelStatus.INSUFFICIENT_DATA,
                benchmark_dataset="N/A",
                sample_count=0,
                train_split_count=0,
                test_split_count=0,
                cross_validation_folds=0,
                accuracy=0.0,
                macro_f1=0.0,
                precision_macro=0.0,
                recall_macro=0.0,
                cv_mean_score=0.0,
                cv_std_score=0.0,
                metric_disclosure="No model loaded. Machine learning metrics are unavailable.",
            )

        return ModelMetricsResponse(
            model_version=self.model_version,
            model_status=self.status,
            benchmark_dataset=dataset_meta.get("dataset_label", "DEMO DATA — NOT REAL INCIDENTS"),
            sample_count=dataset_meta.get("total_samples", 0),
            train_split_count=dataset_meta.get("train_samples", 0),
            test_split_count=dataset_meta.get("test_samples", 0),
            cross_validation_folds=5,
            accuracy=metrics.get("accuracy", 0.0),
            macro_f1=metrics.get("macro_f1", 0.0),
            precision_macro=metrics.get("precision_macro", 0.0),
            recall_macro=metrics.get("recall_macro", 0.0),
            cv_mean_score=metrics.get("cv_mean_score", 0.0),
            cv_std_score=metrics.get("cv_std_score", 0.0),
            metric_disclosure=metrics.get(
                "metric_disclosure",
                "Metrics reflect performance on synthetic demonstration benchmark data.",
            ),
        )


# Global singleton instance for application reuse
default_inference_service = RiskInferenceService(auto_load=True)
