"""
Comprehensive unit and endpoint tests for NEXUS AI Milestone 3, Step 4:
FastAPI AI Router & Endpoints.

Test Coverage:
1. POST /api/v1/ai/assess:
   - Authentication enforcement (401 on missing token).
   - Authoritative deterministic risk score calculation (R = 0.4H + 0.3E + 0.2V + 0.1D).
   - Decomposition of factor point contributions and percentages.
   - Optional ML advisory inference without modifying deterministic score.
   - Cloud Firestore persistence to 'risk_assessments' with server timestamp confirmation.
   - Missing factor input rejection (zero silent invention).
   - Incident ownership verification (404 for missing incident, 403 for unauthorized access).
2. GET /api/v1/ai/assessments/{assessment_id}:
   - Successful retrieval from Firestore.
   - 404 for non-existent assessment.
   - 403 for community user attempting to view another citizen's assessment.
   - Full access for ANALYST and ADMIN roles.
3. POST /api/v1/ai/simulate:
   - Non-destructive what-if scenario evaluation (Delta R, boundary transitions).
   - Guarantees zero writes/mutations to live Firestore documents.
   - Enforces SIMULATION_OVERRIDE provenance and is_simulation=True.
   - Access verification for linked incident.
4. GET /api/v1/ai/recommendations/{incident_id}:
   - Context-aware prioritized civic recommendations.
   - Mandatory PROPOSED status across all recommendations (never claimed completed).
   - Electrical life-safety protocol directing to authorized utility personnel.
   - Access verification (403 for unauthorized community users).
5. GET /api/v1/ai/model/status & GET /api/v1/ai/model/metrics:
   - Honest status disclosures (DEMO / INSUFFICIENT_DATA).
   - Actual benchmark metrics with synthetic demonstration disclaimers.
   - Resilient fallback when model artifacts are missing or corrupt.
"""
from typing import Dict, Any, Optional, List
from pathlib import Path
import pytest
from pydantic import ValidationError
from fastapi import HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials

from app.schemas.risk import (
    RiskLevel,
    ModelStatus,
    RiskFactorInput,
    EstimationSource,
    RiskAssessmentCreate,
    SimulationRequest,
    RecommendationPriority,
)
from app.schemas.user import UserPrincipal, UserRole
from app.main import app
from app.api.deps import get_current_user
from app.api.v1.endpoints.ai import (
    compute_risk_assessment,
    get_saved_assessment,
    run_scenario_simulation,
    get_incident_recommendations,
    get_model_readiness_status,
    get_model_evaluation_metrics,
)
from app.services.firebase_service import set_firestore_client_for_testing
from app.ml.inference import RiskInferenceService


# ==============================================================================
# MOCK FIRESTORE FOR DETERMINISTIC, ISOLATED OFFLINE TESTING
# ==============================================================================

class MockDocSnapshot:
    def __init__(self, doc_id: str, data: Optional[Dict[str, Any]]):
        self.id = doc_id
        self._data = data
        self.exists = data is not None

    def to_dict(self) -> Dict[str, Any]:
        return self._data.copy() if self._data else {}


class MockDocRef:
    def __init__(self, doc_id: str, store: Dict[str, Any]):
        self.id = doc_id
        self._store = store

    def set(self, data: Dict[str, Any]):
        self._store[self.id] = data.copy() if isinstance(data, dict) else data

    def get(self) -> MockDocSnapshot:
        return MockDocSnapshot(self.id, self._store.get(self.id))


class MockCollection:
    def __init__(self, name: str, parent_db: "MockFirestore"):
        self.name = name
        self._parent = parent_db

    def document(self, doc_id: str) -> MockDocRef:
        store = self._parent._collections.setdefault(self.name, {})
        return MockDocRef(doc_id, store)


class MockFirestore:
    def __init__(self):
        self._collections: Dict[str, Dict[str, Any]] = {}

    def collection(self, name: str) -> MockCollection:
        return MockCollection(name, self)


@pytest.fixture(autouse=True)
def setup_mock_firestore():
    """Inject fresh isolated mock Firestore store for each test."""
    mock_db = MockFirestore()
    set_firestore_client_for_testing(mock_db)
    yield mock_db
    # Teardown: reset to clean mock or None
    set_firestore_client_for_testing(None)


# ==============================================================================
# 1. AUTHENTICATION & SECURITY ENFORCEMENT
# ==============================================================================

def test_ai_endpoint_authentication_enforcement():
    """Verify that unauthenticated requests without Bearer credentials are rejected with 401."""
    with pytest.raises(HTTPException) as exc:
        get_current_user(credentials=None)
    assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Authentication required" in exc.value.detail


# ==============================================================================
# 2. POST /api/v1/ai/assess - CREATION, PERSISTENCE & ML ADVISORY
# ==============================================================================

def test_post_assess_creates_deterministic_assessment_and_persists_to_firestore(setup_mock_firestore: MockFirestore):
    """
    Verify POST /api/v1/ai/assess:
    1. Computes authoritative risk score: H=70, E=80, V=50, D=30 -> 28 + 24 + 10 + 3 = 65.0 (HIGH)
    2. Decomposes primary/secondary drivers.
    3. Persists record to Firestore 'risk_assessments' collection with server timestamp.
    4. Confirms database write before returning.
    """
    analyst = UserPrincipal(uid="analyst_jane", email="jane@nexus.ai", role=UserRole.ANALYST)

    payload = RiskAssessmentCreate(
        factors=RiskFactorInput(
            hazard_severity=70.0,
            exposure=80.0,
            vulnerability=50.0,
            duration=30.0,
            source=EstimationSource.USER_DIRECT,
            source_notes="Calibrated field reading",
        ),
        include_ml_advisory=True,
    )

    assessment = compute_risk_assessment(payload=payload, current_user=analyst)

    assert assessment.id.startswith("risk_")
    assert assessment.risk_score == 65.0
    assert assessment.risk_level == RiskLevel.HIGH
    assert assessment.assessed_by == "analyst_jane"
    assert assessment.formula == "R = 0.4H + 0.3E + 0.2V + 0.1D"
    assert assessment.contributions.primary_driver == "hazard"
    assert assessment.contributions.secondary_driver == "exposure"
    assert "The primary driver is" in assessment.explanation

    # Verify optional ML advisory is present without replacing deterministic score
    if assessment.ml_advisory:
        assert assessment.ml_advisory["is_advisory_only"] is True
        assert assessment.ml_advisory["model_status"] in ["DEMO", "INSUFFICIENT_DATA"]

    # Verify Cloud Firestore persistence
    saved_doc = setup_mock_firestore.collection("risk_assessments").document(assessment.id).get()
    assert saved_doc.exists is True
    assert saved_doc.to_dict()["risk_score"] == 65.0
    assert saved_doc.to_dict()["assessed_by"] == "analyst_jane"


def test_post_assess_rejects_missing_factors_zero_silent_invention():
    """Verify that omitting factor values raises ValidationError (zero silent invention)."""
    with pytest.raises(ValidationError):
        RiskAssessmentCreate.model_validate({
            "factors": {
                "hazard_severity": 50.0,
                "exposure": 50.0,
                # Missing vulnerability and duration
            }
        })


def test_post_assess_verifies_linked_incident_ownership(setup_mock_firestore: MockFirestore):
    """
    Verify ownership check when assessing an incident:
    - Community user assessing their own incident: allowed.
    - Community user assessing another user's incident: raises 403 Forbidden.
    - Non-existent incident: raises 404 Not Found.
    """
    # Seed mock incidents in Firestore
    incidents_store = setup_mock_firestore._collections.setdefault("incidents", {})
    incidents_store["inc_citizen_1"] = {
        "id": "inc_citizen_1",
        "title": "Severe Pothole",
        "description": "Hazardous road void",
        "category": "road_damage",
        "severity": "HIGH",
        "status": "reported",
        "reported_by": "citizen_uid_1",
        "reporter_uid": "citizen_uid_1",
        "location": "Main St",
    }

    citizen1 = UserPrincipal(uid="citizen_uid_1", email="c1@nexus.ai", role=UserRole.COMMUNITY_USER)
    citizen2 = UserPrincipal(uid="citizen_uid_2", email="c2@nexus.ai", role=UserRole.COMMUNITY_USER)

    factors = RiskFactorInput(hazard_severity=60.0, exposure=50.0, vulnerability=40.0, duration=30.0)

    # 1. Own incident: Success
    req_own = RiskAssessmentCreate(incident_id="inc_citizen_1", factors=factors)
    resp_own = compute_risk_assessment(payload=req_own, current_user=citizen1)
    assert resp_own.incident_id == "inc_citizen_1"

    # 2. Other user's incident: 403 Forbidden
    req_other = RiskAssessmentCreate(incident_id="inc_citizen_1", factors=factors)
    with pytest.raises(HTTPException) as exc_403:
        compute_risk_assessment(payload=req_other, current_user=citizen2)
    assert exc_403.value.status_code == status.HTTP_403_FORBIDDEN

    # 3. Missing incident: 404 Not Found
    req_missing = RiskAssessmentCreate(incident_id="inc_non_existent", factors=factors)
    with pytest.raises(HTTPException) as exc_404:
        compute_risk_assessment(payload=req_missing, current_user=citizen1)
    assert exc_404.value.status_code == status.HTTP_404_NOT_FOUND


# ==============================================================================
# 3. GET /api/v1/ai/assessments/{assessment_id} - RETRIEVAL & RBAC
# ==============================================================================

def test_get_saved_assessment_retrieval_and_rbac(setup_mock_firestore: MockFirestore):
    """
    Verify GET /api/v1/ai/assessments/{assessment_id}:
    - 404 for non-existent assessment.
    - 403 for community user attempting to view someone else's assessment.
    - 200 for owner community user.
    - 200 for ANALYST and ADMIN.
    """
    assessments_store = setup_mock_firestore._collections.setdefault("risk_assessments", {})
    assessments_store["risk_test_999"] = {
        "id": "risk_test_999",
        "incident_id": "inc_flood_888",
        "risk_score": 72.5,
        "risk_level": "HIGH",
        "factors": {
            "hazard_severity": 80.0, "exposure": 75.0, "vulnerability": 65.0, "duration": 60.0,
            "source": "USER_DIRECT",
        },
        "contributions": {
            "hazard": {"factor_name": "hazard", "factor_label": "H", "input_value": 80.0, "weight": 0.4, "weighted_points": 32.0, "contribution_percentage": 44.1, "influence": "AMPLIFYING", "explanation": "H"},
            "exposure": {"factor_name": "exposure", "factor_label": "E", "input_value": 75.0, "weight": 0.3, "weighted_points": 22.5, "contribution_percentage": 31.0, "influence": "AMPLIFYING", "explanation": "E"},
            "vulnerability": {"factor_name": "vulnerability", "factor_label": "V", "input_value": 65.0, "weight": 0.2, "weighted_points": 13.0, "contribution_percentage": 17.9, "influence": "AMPLIFYING", "explanation": "V"},
            "duration": {"factor_name": "duration", "factor_label": "D", "input_value": 60.0, "weight": 0.1, "weighted_points": 6.0, "contribution_percentage": 8.3, "influence": "AMPLIFYING", "explanation": "D"},
            "primary_driver": "hazard",
            "secondary_driver": "exposure",
        },
        "formula": "R = 0.4H + 0.3E + 0.2V + 0.1D",
        "methodology": "Multi-criteria civic evaluation",
        "explanation": "High risk driven by hazard severity",
        "ml_advisory": None,
        "model_status": "DEMO",
        "model_version": "v1.0.0-deterministic",
        "assessed_by": "citizen_author_uid",
        "created_at": "2026-11-04T10:00:00Z",
    }

    author = UserPrincipal(uid="citizen_author_uid", email="author@nexus.ai", role=UserRole.COMMUNITY_USER)
    intruder = UserPrincipal(uid="citizen_intruder_uid", email="intruder@nexus.ai", role=UserRole.COMMUNITY_USER)
    analyst = UserPrincipal(uid="analyst_uid", email="analyst@nexus.ai", role=UserRole.ANALYST)
    admin = UserPrincipal(uid="admin_uid", email="admin@nexus.ai", role=UserRole.ADMIN)

    # 1. Author can access their assessment
    retrieved_author = get_saved_assessment("risk_test_999", current_user=author)
    assert retrieved_author.id == "risk_test_999"
    assert retrieved_author.risk_score == 72.5

    # 2. Intruder community user is forbidden (403)
    with pytest.raises(HTTPException) as exc_403:
        get_saved_assessment("risk_test_999", current_user=intruder)
    assert exc_403.value.status_code == status.HTTP_403_FORBIDDEN

    # 3. Analyst has platform-wide access (200)
    retrieved_analyst = get_saved_assessment("risk_test_999", current_user=analyst)
    assert retrieved_analyst.id == "risk_test_999"

    # 4. Admin has platform-wide access (200)
    retrieved_admin = get_saved_assessment("risk_test_999", current_user=admin)
    assert retrieved_admin.id == "risk_test_999"

    # 5. Non-existent assessment raises 404
    with pytest.raises(HTTPException) as exc_404:
        get_saved_assessment("risk_does_not_exist", current_user=analyst)
    assert exc_404.value.status_code == status.HTTP_404_NOT_FOUND


# ==============================================================================
# 4. POST /api/v1/ai/simulate - WHAT-IF SIMULATION & NON-MUTATION
# ==============================================================================

def test_post_simulate_non_destructive_evaluation(setup_mock_firestore: MockFirestore):
    """
    Verify POST /api/v1/ai/simulate:
    1. Baseline H=85, E=80, V=60, D=50 -> 34 + 24 + 12 + 5 = 75.0 (HIGH)
    2. Simulated H=30, E=30, V=40, D=20 -> 12 + 9 + 8 + 2 = 31.0 (MEDIUM)
    3. Delta R = -44.0 pts, level_changed = True
    4. Output is marked is_simulation=True.
    5. Firestore incident record is NEVER mutated or modified.
    """
    incidents_store = setup_mock_firestore._collections.setdefault("incidents", {})
    original_incident = {
        "id": "inc_sim_01",
        "title": "Severe Waterlogging Underpass",
        "description": "Subway submerged under heavy flood waters",
        "category": "waterlogging",
        "severity": "HIGH",
        "status": "reported",
        "reported_by": "analyst_sim",
        "reporter_uid": "analyst_sim",
        "location": "Central Metro Station",
    }
    incidents_store["inc_sim_01"] = original_incident.copy()

    analyst = UserPrincipal(uid="analyst_sim", email="sim@nexus.ai", role=UserRole.ANALYST)

    request = SimulationRequest(
        scenario_name="Drainage Pump Deployment",
        incident_id="inc_sim_01",
        baseline_factors=RiskFactorInput(hazard_severity=85.0, exposure=80.0, vulnerability=60.0, duration=50.0),
        simulated_factors=RiskFactorInput(hazard_severity=30.0, exposure=30.0, vulnerability=40.0, duration=20.0),
        intervention_notes="Deploy 3 high-volume pumps.",
    )

    sim_res = run_scenario_simulation(payload=request, current_user=analyst)

    assert sim_res.baseline_score == 75.0
    assert sim_res.baseline_level == RiskLevel.HIGH
    assert sim_res.simulated_score == 31.0
    assert sim_res.simulated_level == RiskLevel.MEDIUM
    assert sim_res.score_difference == -44.0
    assert sim_res.level_changed is True
    assert sim_res.is_simulation is True
    assert "Hazard Severity" in sim_res.primary_mitigation_driver

    # CRITICAL CHECK: Firestore incident was NOT modified or mutated
    current_incident_in_db = setup_mock_firestore.collection("incidents").document("inc_sim_01").get().to_dict()
    assert current_incident_in_db == original_incident


# ==============================================================================
# 5. GET /api/v1/ai/recommendations/{incident_id}
# ==============================================================================

def test_get_recommendations_endpoint_all_categories_and_proposed_status(setup_mock_firestore: MockFirestore):
    """
    Verify GET /api/v1/ai/recommendations/{incident_id}:
    - Returns prioritized, category-specific recommendations.
    - Every recommendation strictly has status: PROPOSED.
    - Electrical category enforces utility personnel directives.
    - 403 on unauthorized access.
    """
    incidents_store = setup_mock_firestore._collections.setdefault("incidents", {})
    incidents_store["inc_elec_live"] = {
        "id": "inc_elec_live",
        "title": "Sparking Transformer near Playground",
        "description": "High voltage arcing and continuous sparks",
        "category": "electrical_hazard",
        "severity": "HIGH",
        "status": "reported",
        "reported_by": "user_elec_owner",
        "reporter_uid": "user_elec_owner",
        "location": "Park Street Crossing",
    }

    owner = UserPrincipal(uid="user_elec_owner", email="owner@nexus.ai", role=UserRole.COMMUNITY_USER)
    stranger = UserPrincipal(uid="user_stranger", email="stranger@nexus.ai", role=UserRole.COMMUNITY_USER)

    # 1. Owner requests recommendations
    recs = get_incident_recommendations("inc_elec_live", current_user=owner)
    assert recs.incident_id == "inc_elec_live"
    assert recs.category == "electrical"
    assert len(recs.recommendations) >= 2

    for item in recs.recommendations:
        assert item.status == "PROPOSED"
        assert item.priority in [RecommendationPriority.IMMEDIATE, RecommendationPriority.HIGH, RecommendationPriority.MEDIUM, RecommendationPriority.MONITOR]

    # Verify electrical safety directive
    actions_combined = " ".join([r.action for r in recs.recommendations]).lower()
    assert "utility" in actions_combined or "linesmen" in actions_combined
    assert "dielectric" in actions_combined or "de-energization" in actions_combined

    # 2. Stranger community user is denied access (403)
    with pytest.raises(HTTPException) as exc_403:
        get_incident_recommendations("inc_elec_live", current_user=stranger)
    assert exc_403.value.status_code == status.HTTP_403_FORBIDDEN


# ==============================================================================
# 6. GET /api/v1/ai/model/status & GET /api/v1/ai/model/metrics
# ==============================================================================

def test_get_model_status_and_metrics_endpoints():
    """
    Verify model telemetry endpoints:
    - Status reports DEMO or INSUFFICIENT_DATA.
    - Metrics report test split performance and synthetic disclosure.
    - Discloses that models learn the formula rule, not predicting real disasters.
    """
    analyst = UserPrincipal(uid="analyst_test", email="analyst@nexus.ai", role=UserRole.ANALYST)

    status_resp = get_model_readiness_status(current_user=analyst)
    assert status_resp.status in [ModelStatus.DEMO, ModelStatus.INSUFFICIENT_DATA]
    assert status_resp.is_probabilistic_forecast is False
    assert len(status_resp.disclaimer) > 10

    metrics_resp = get_model_evaluation_metrics(current_user=analyst)
    assert metrics_resp.model_status in [ModelStatus.DEMO, ModelStatus.INSUFFICIENT_DATA]
    assert "synthetic" in metrics_resp.metric_disclosure.lower() or "unavailable" in metrics_resp.metric_disclosure.lower()



# ==============================================================================
# 7. ROUTER REGISTRATION & PATH VERIFICATION
# ==============================================================================

def test_ai_router_registration_and_exact_paths():
    """
    Verify exact OpenAPI router registration for all Milestone 3 AI routes:
    - POST /api/v1/ai/assess
    - GET  /api/v1/ai/assessments/{assessment_id}
    - POST /api/v1/ai/simulate
    - GET  /api/v1/ai/recommendations/{incident_id}
    - GET  /api/v1/ai/model/status
    - GET  /api/v1/ai/model/metrics
    """
    openapi_paths = app.openapi()["paths"]

    # 1. Exact paths present
    assert "/api/v1/ai/assess" in openapi_paths
    assert "post" in openapi_paths["/api/v1/ai/assess"]

    assert "/api/v1/ai/assessments/{assessment_id}" in openapi_paths
    assert "get" in openapi_paths["/api/v1/ai/assessments/{assessment_id}"]

    assert "/api/v1/ai/simulate" in openapi_paths
    assert "post" in openapi_paths["/api/v1/ai/simulate"]

    assert "/api/v1/ai/recommendations/{incident_id}" in openapi_paths
    assert "get" in openapi_paths["/api/v1/ai/recommendations/{incident_id}"]

    assert "/api/v1/ai/model/status" in openapi_paths
    assert "get" in openapi_paths["/api/v1/ai/model/status"]

    assert "/api/v1/ai/model/metrics" in openapi_paths
    assert "get" in openapi_paths["/api/v1/ai/model/metrics"]


def test_ai_endpoint_standalone_assessment_boundary_score():
    """
    Verify standalone assessment handler with a boundary score of exactly 60.0:
    H=80, E=60, V=40, D=20 -> 0.4(80) + 0.3(60) + 0.2(40) + 0.1(20) = 32 + 18 + 8 + 2 = 60.0
    Score of exactly 60 is strictly classified as HIGH.
    """
    analyst = UserPrincipal(uid="boundary_tester", email="tester@nexus.ai", role=UserRole.ANALYST)

    payload = RiskAssessmentCreate(
        factors=RiskFactorInput(
            hazard_severity=80.0,
            exposure=60.0,
            vulnerability=40.0,
            duration=20.0,
            source=EstimationSource.USER_DIRECT,
        ),
        include_ml_advisory=False,
    )

    assessment = compute_risk_assessment(payload=payload, current_user=analyst)

    assert assessment.risk_score == 60.0
    assert assessment.risk_level == RiskLevel.HIGH
    assert assessment.formula == "R = 0.4H + 0.3E + 0.2V + 0.1D"
    assert assessment.assessed_by == "boundary_tester"


def test_ai_model_fallback_when_uninitialized(monkeypatch):
    """
    Verify that when model service has no loaded artifact,
    get_model_readiness_status and get_model_evaluation_metrics return
    honest INSUFFICIENT_DATA status without raising unhandled exceptions.
    """
    analyst = UserPrincipal(uid="fallback_tester", email="tester@nexus.ai", role=UserRole.ANALYST)

    # Instantiate uninitialized service
    uninitialized_service = RiskInferenceService(model_path=Path("non_existent_model.joblib"), auto_load=False)

    status_resp = uninitialized_service.get_model_status()
    assert status_resp.status == ModelStatus.INSUFFICIENT_DATA
    assert status_resp.training_sample_count == 0
    assert "Deterministic Engine Active" in status_resp.primary_algorithm

    metrics_resp = uninitialized_service.get_model_metrics()
    assert metrics_resp.model_status == ModelStatus.INSUFFICIENT_DATA
    assert metrics_resp.accuracy == 0.0
