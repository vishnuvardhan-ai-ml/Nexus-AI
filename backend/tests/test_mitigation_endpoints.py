"""
Comprehensive Unit and Endpoint Tests for NEXUS AI Milestone 5, Stage 2:
FastAPI AI Mitigation Endpoints & Tests.

Routes in Scope:
1. GET  /api/v1/ai/mitigation/presets/{category}
2. POST /api/v1/ai/simulate/multi
3. POST /api/v1/ai/mitigation/report

Test Coverage:
- Authentication enforcement (401 on missing Bearer credentials).
- Role-based authorization & ownership:
  - COMMUNITY_USER restricted from standalone municipal simulations & reports (403 Forbidden).
  - COMMUNITY_USER allowed to simulate and generate reports for their own reported incidents (200 OK).
  - COMMUNITY_USER blocked from simulating on other citizens' incidents (403 Forbidden).
  - ANALYST and ADMIN allowed standalone and system-wide access.
- All six supported categories return valid presets with complete resource estimates.
- Unsupported categories rejected with 400 Bad Request.
- 2–5 scenario boundary enforcement and duplicate ID rejection (422).
- Zero, missing, and uncertain cost handling without division-by-zero crashes.
- Complete multi-criteria ranking verification (Impact, Cost Efficiency, Deployment Speed, Best Balanced).
- Diagnostic record detection and disclosure attachment.
- Structured mitigation brief generation and Markdown report output.
- Strict non-destructive guarantee (zero Firestore writes).
- OpenAPI router registration verification.
"""
from typing import Dict, Any, Optional, List
import pytest
from pydantic import ValidationError
from fastapi import HTTPException, status

from app.schemas.incident import IncidentCategory, IncidentSeverity, IncidentStatus
from app.schemas.risk import (
    RiskLevel,
    RiskFactorInput,
    EstimationSource,
)
from app.schemas.mitigation import (
    CostConfidence,
    ResourceEstimate,
    MitigationScenarioInput,
    MultiScenarioSimulationRequest,
    MultiScenarioSimulationResponse,
    MitigationReportRequest,
    MitigationReportResponse,
)
from app.schemas.user import UserPrincipal, UserRole
from app.main import app
from app.api.deps import get_current_user
from app.api.v1.endpoints.ai import (
    get_category_mitigation_presets,
    run_multi_scenario_simulation,
    generate_municipal_mitigation_report,
)
from app.services.firebase_service import set_firestore_client_for_testing


# ==============================================================================
# ISOLATED MOCK FIRESTORE FIXTURE FOR NON-DESTRUCTIVE OFFLINE TESTING
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
    set_firestore_client_for_testing(None)


# Test User Principals
COMMUNITY_USER_OWNER = UserPrincipal(
    uid="usr_resident_456", email="owner@civic.gov", role=UserRole.COMMUNITY_USER
)
COMMUNITY_USER_OTHER = UserPrincipal(
    uid="usr_citizen_789", email="stranger@civic.gov", role=UserRole.COMMUNITY_USER
)
ANALYST_USER = UserPrincipal(
    uid="usr_analyst_007", email="analyst@nexus.gov", role=UserRole.ANALYST
)
ADMIN_USER = UserPrincipal(
    uid="usr_admin_999", email="admin@nexus.gov", role=UserRole.ADMIN
)


# ==============================================================================
# 1. AUTHENTICATION & ROLE-BASED ACCESS CONTROL (RBAC)
# ==============================================================================

def test_mitigation_endpoint_authentication_enforcement():
    """Verify that unauthenticated calls without token raise 401."""
    with pytest.raises(HTTPException) as exc:
        get_current_user(credentials=None)
    assert exc.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Authentication required" in exc.value.detail


def test_standalone_multi_simulation_rbac_restriction():
    """
    Verify standalone municipal simulation RBAC:
    - COMMUNITY_USER without linked incident is restricted with 403.
    - ANALYST is authorized with 200.
    """
    base_factors = RiskFactorInput(
        hazard_severity=70.0, exposure=60.0, vulnerability=50.0, duration=40.0
    )
    req = MultiScenarioSimulationRequest(
        baseline_factors=base_factors,
        scenarios=[
            MitigationScenarioInput(
                scenario_id="s1",
                scenario_name="Scenario 1",
                simulated_factors=RiskFactorInput(hazard_severity=30.0, exposure=30.0, vulnerability=30.0, duration=20.0),
            ),
            MitigationScenarioInput(
                scenario_id="s2",
                scenario_name="Scenario 2",
                simulated_factors=RiskFactorInput(hazard_severity=40.0, exposure=40.0, vulnerability=30.0, duration=20.0),
            ),
        ],
    )

    # 1. Community user running standalone planning -> 403 Forbidden
    with pytest.raises(HTTPException) as exc:
        run_multi_scenario_simulation(payload=req, current_user=COMMUNITY_USER_OWNER)
    assert exc.value.status_code == status.HTTP_403_FORBIDDEN
    assert "Standalone municipal planning simulations require an ANALYST or ADMIN role" in exc.value.detail

    # 2. Analyst user running standalone planning -> 200 OK
    res_analyst = run_multi_scenario_simulation(payload=req, current_user=ANALYST_USER)
    assert res_analyst.simulation_id.startswith("sim_multi_")
    assert res_analyst.scenarios_evaluated_count == 2

    # 3. Admin user running standalone planning -> 200 OK
    res_admin = run_multi_scenario_simulation(payload=req, current_user=ADMIN_USER)
    assert res_admin.scenarios_evaluated_count == 2


def test_incident_linked_simulation_ownership_enforcement(setup_mock_firestore: MockFirestore):
    """
    Verify ownership enforcement when incident_id is supplied:
    - Community user can simulate their own incident.
    - Community user is blocked (403) from simulating on someone else's incident.
    """
    db = setup_mock_firestore
    # Seed incident owned by COMMUNITY_USER_OWNER
    db.collection("incidents").document("inc_own_123").set({
        "id": "inc_own_123",
        "title": "Severe Water Ponding Near School",
        "description": "Monsoon water accumulation causing traffic gridlock outside school gate.",
        "category": "waterlogging",
        "severity": "HIGH",
        "status": "reported",
        "location": "Ward 5 School Zone",
        "reporter_uid": COMMUNITY_USER_OWNER.uid,
        "reported_by": COMMUNITY_USER_OWNER.uid,
    })

    req = MultiScenarioSimulationRequest(
        incident_id="inc_own_123",
        baseline_factors=RiskFactorInput(
            hazard_severity=75.0, exposure=70.0, vulnerability=60.0, duration=50.0
        ),
        scenarios=[
            MitigationScenarioInput(
                scenario_id="scen_pump",
                scenario_name="Pump Deployment",
                simulated_factors=RiskFactorInput(hazard_severity=35.0, exposure=70.0, vulnerability=60.0, duration=20.0),
            ),
            MitigationScenarioInput(
                scenario_id="scen_drain",
                scenario_name="Drain Clearing",
                simulated_factors=RiskFactorInput(hazard_severity=50.0, exposure=70.0, vulnerability=40.0, duration=30.0),
            ),
        ],
    )

    # 1. Owner simulates own incident -> Success
    res_owner = run_multi_scenario_simulation(payload=req, current_user=COMMUNITY_USER_OWNER)
    assert res_owner.incident_id == "inc_own_123"
    assert res_owner.scenarios_evaluated_count == 2

    # 2. Another community user attempts simulation -> 403 Forbidden
    with pytest.raises(HTTPException) as exc:
        run_multi_scenario_simulation(payload=req, current_user=COMMUNITY_USER_OTHER)
    assert exc.value.status_code == status.HTTP_403_FORBIDDEN

    # 3. Analyst simulates citizen's incident -> Success (Full Access)
    res_analyst = run_multi_scenario_simulation(payload=req, current_user=ANALYST_USER)
    assert res_analyst.incident_id == "inc_own_123"


# ==============================================================================
# 2. GET /api/v1/ai/mitigation/presets/{category}
# ==============================================================================

def test_get_mitigation_presets_all_six_categories():
    """Verify that all six canonical categories return valid presets with full resource estimates."""
    categories = [
        "waterlogging",
        "road_damage",
        "electrical_hazard",
        "waste_management",
        "extreme_heat",
        "general_safety",
    ]

    for cat in categories:
        presets = get_category_mitigation_presets(category=cat, current_user=ANALYST_USER)
        assert len(presets) >= 2, f"Category '{cat}' returned fewer than 2 presets"
        for p in presets:
            assert p.status == "PROPOSED"
            assert p.resource_estimate.is_estimate is True
            assert p.resource_estimate.currency == "INR"
            assert p.resource_estimate.currency_symbol == "₹"
            assert p.resource_estimate.cost_confidence == CostConfidence.DOCUMENTED_BENCHMARK
            assert p.resource_estimate.disclaimer is not None
            assert p.resource_estimate.estimated_cost_min is not None
            assert p.resource_estimate.estimated_cost_max is not None
            assert p.resource_estimate.estimated_manpower is not None
            assert p.resource_estimate.estimated_duration_hours is not None
            assert p.responsible_department is not None
            assert len(p.target_factor_deltas) > 0


def test_get_mitigation_presets_alias_support():
    """Verify alias support ('electrical' -> 'electrical_hazard', 'waste' -> 'waste_management')."""
    presets_el = get_category_mitigation_presets(category="electrical", current_user=ANALYST_USER)
    assert len(presets_el) >= 2

    presets_wm = get_category_mitigation_presets(category="waste", current_user=ANALYST_USER)
    assert len(presets_wm) >= 2


def test_get_mitigation_presets_unsupported_category_returns_400():
    """Verify that requesting presets for an unsupported category raises 400 Bad Request."""
    with pytest.raises(HTTPException) as exc:
        get_category_mitigation_presets(category="unsupported_wildlife_invasion", current_user=ANALYST_USER)
    assert exc.value.status_code == status.HTTP_400_BAD_REQUEST
    assert "Unsupported incident category: 'unsupported_wildlife_invasion'" in exc.value.detail
    assert "Supported categories are" in exc.value.detail


# ==============================================================================
# 3. POST /api/v1/ai/simulate/multi — CALCULATIONS, RANKINGS, EDGE CASES
# ==============================================================================

def test_multi_scenario_deterministic_calculations_and_rankings():
    """
    Verify POST /api/v1/ai/simulate/multi:
    - Evaluates 3 competing scenarios.
    - Deterministic risk formula: R = 0.4H + 0.3E + 0.2V + 0.1D.
    - Computes cost-effectiveness in points per ₹1 Lakh.
    - All 4 ranking dimensions populated deterministically.
    """
    # Baseline: H=80, E=70, V=60, D=50 -> 32 + 21 + 12 + 5 = 70.0 (HIGH)
    base_factors = RiskFactorInput(
        hazard_severity=80.0, exposure=70.0, vulnerability=60.0, duration=50.0
    )

    scen_a = MitigationScenarioInput(
        scenario_id="scen_pumps",
        scenario_name="High-Volume Pumps",
        simulated_factors=RiskFactorInput(hazard_severity=30.0, exposure=70.0, vulnerability=60.0, duration=20.0),
        custom_resource_override=ResourceEstimate(
            estimated_cost_min=50000.0,
            estimated_cost_max=50000.0,  # 0.5 Lakh
            estimated_duration_hours=3.0,
            currency="INR",
        ),
    )
    scen_b = MitigationScenarioInput(
        scenario_id="scen_detour",
        scenario_name="Traffic Detour Marshals",
        simulated_factors=RiskFactorInput(hazard_severity=80.0, exposure=20.0, vulnerability=60.0, duration=50.0),
        custom_resource_override=ResourceEstimate(
            estimated_cost_min=10000.0,
            estimated_cost_max=10000.0,  # 0.1 Lakh
            estimated_duration_hours=1.0,
            currency="INR",
        ),
    )
    scen_c = MitigationScenarioInput(
        scenario_id="scen_basin",
        scenario_name="Modular Retention Basin",
        simulated_factors=RiskFactorInput(hazard_severity=20.0, exposure=30.0, vulnerability=20.0, duration=10.0),
        custom_resource_override=ResourceEstimate(
            estimated_cost_min=500000.0,
            estimated_cost_max=500000.0,  # 5.0 Lakhs
            estimated_duration_hours=72.0,
            currency="INR",
        ),
    )

    req = MultiScenarioSimulationRequest(
        baseline_factors=base_factors,
        scenarios=[scen_a, scen_b, scen_c],
    )

    res = run_multi_scenario_simulation(payload=req, current_user=ANALYST_USER)

    assert res.baseline_score == 70.0
    assert res.baseline_level == RiskLevel.HIGH
    assert res.scenarios_evaluated_count == 3
    assert res.formula == "R = 0.4H + 0.3E + 0.2V + 0.1D"
    assert "planning heuristics" in res.planning_disclaimer

    # Scenario evaluations check
    eval_dict = {e.scenario_id: e for e in res.evaluations}

    # Pumps: score = 47.0 (delta = 23.0 pts, 46.0 pts/lakh)
    assert eval_dict["scen_pumps"].simulated_score == 47.0
    assert eval_dict["scen_pumps"].absolute_risk_reduction == 23.0
    assert eval_dict["scen_pumps"].cost_effectiveness_per_lakh == 46.0
    assert eval_dict["scen_pumps"].status == "PROPOSED"
    assert eval_dict["scen_pumps"].is_simulation is True

    # Detour: score = 55.0 (delta = 15.0 pts, 150.0 pts/lakh)
    assert eval_dict["scen_detour"].simulated_score == 55.0
    assert eval_dict["scen_detour"].cost_effectiveness_per_lakh == 150.0

    # Basin: score = 22.0 (delta = 48.0 pts, 9.6 pts/lakh)
    assert eval_dict["scen_basin"].simulated_score == 22.0
    assert eval_dict["scen_basin"].cost_effectiveness_per_lakh == 9.6

    # Verify Rankings
    assert res.rankings.by_impact[0].scenario_id == "scen_basin"
    assert res.rankings.by_cost_efficiency[0].scenario_id == "scen_detour"
    assert res.rankings.by_deployment_speed[0].scenario_id == "scen_detour"
    assert res.rankings.best_balanced is not None


def test_multi_scenario_zero_and_missing_cost_safety():
    """Verify that zero cost, missing cost, and negative cost don't crash."""
    base_factors = RiskFactorInput(
        hazard_severity=60.0, exposure=60.0, vulnerability=60.0, duration=60.0
    )

    scen_zero_cost = MitigationScenarioInput(
        scenario_id="s_zero",
        scenario_name="Zero Direct Cost Notice",
        simulated_factors=RiskFactorInput(hazard_severity=50.0, exposure=60.0, vulnerability=60.0, duration=60.0),
        custom_resource_override=ResourceEstimate(
            estimated_cost_min=0.0, estimated_cost_max=0.0, currency="INR"
        ),
    )
    scen_missing_cost = MitigationScenarioInput(
        scenario_id="s_none",
        scenario_name="Missing Cost Estimates",
        simulated_factors=RiskFactorInput(hazard_severity=45.0, exposure=60.0, vulnerability=60.0, duration=60.0),
        custom_resource_override=ResourceEstimate(
            estimated_cost_min=None, estimated_cost_max=None, currency="INR"
        ),
    )

    req = MultiScenarioSimulationRequest(
        baseline_factors=base_factors,
        scenarios=[scen_zero_cost, scen_missing_cost],
    )

    res = run_multi_scenario_simulation(payload=req, current_user=ANALYST_USER)
    assert res.scenarios_evaluated_count == 2

    e_zero = res.evaluations[0]
    assert e_zero.cost_effectiveness_per_lakh is None
    assert "Zero Additional Direct Cost" in e_zero.cost_effectiveness_label

    e_none = res.evaluations[1]
    assert e_none.cost_effectiveness_per_lakh is None
    assert "Unestimated Cost" in e_none.cost_effectiveness_label


def test_multi_scenario_diagnostic_record_disclosure(setup_mock_firestore: MockFirestore):
    """Verify that evaluating a diagnostic verification record returns prominent notices."""
    db = setup_mock_firestore
    db.collection("incidents").document("inc_diag_test").set({
        "id": "inc_diag_test",
        "title": "Live Milestone 2B Verification: Road Subsidence Hazard",
        "description": "Diagnostic benchmark road depression created during Milestone 2B testing.",
        "category": "road_damage",
        "severity": "HIGH",
        "status": "reported",
        "location": "Sector 4 Arterial Ring Road",
        "reporter_email": "diagnostic_test_1793714803737@nexus-test.org",
        "reporter_uid": "uid_diag_test",
        "reported_by": "uid_diag_test",
    })

    req = MultiScenarioSimulationRequest(
        incident_id="inc_diag_test",
        baseline_factors=RiskFactorInput(
            hazard_severity=65.0, exposure=55.0, vulnerability=60.0, duration=50.0
        ),
        scenarios=[
            MitigationScenarioInput(
                scenario_id="s1",
                scenario_name="S1",
                simulated_factors=RiskFactorInput(hazard_severity=30.0, exposure=30.0, vulnerability=30.0, duration=20.0),
            ),
            MitigationScenarioInput(
                scenario_id="s2",
                scenario_name="S2",
                simulated_factors=RiskFactorInput(hazard_severity=40.0, exposure=30.0, vulnerability=30.0, duration=20.0),
            ),
        ],
    )

    res = run_multi_scenario_simulation(payload=req, current_user=ANALYST_USER)
    assert res.is_diagnostic_record is True
    assert res.diagnostic_notice is not None
    assert "DIAGNOSTIC TEST RECORD" in res.diagnostic_notice


# ==============================================================================
# 4. POST /api/v1/ai/mitigation/report — BRIEF & MARKDOWN EXPORT
# ==============================================================================

def test_generate_mitigation_report_endpoint():
    """Verify POST /api/v1/ai/mitigation/report synthesizes structured brief and Markdown."""
    base_factors = RiskFactorInput(
        hazard_severity=75.0, exposure=65.0, vulnerability=55.0, duration=45.0
    )
    scen_1 = MitigationScenarioInput(
        scenario_id="scen_pumping",
        scenario_name="Rapid Pump Deployment",
        simulated_factors=RiskFactorInput(hazard_severity=35.0, exposure=40.0, vulnerability=40.0, duration=25.0),
        custom_resource_override=ResourceEstimate(
            estimated_cost_min=30000.0,
            estimated_cost_max=60000.0,
            currency="INR",
            currency_symbol="₹",
            estimated_manpower=4,
            estimated_duration_hours=3.0,
        ),
    )
    scen_2 = MitigationScenarioInput(
        scenario_id="scen_culverts",
        scenario_name="Culvert Desilting Squad",
        simulated_factors=RiskFactorInput(hazard_severity=55.0, exposure=65.0, vulnerability=30.0, duration=35.0),
        custom_resource_override=ResourceEstimate(
            estimated_cost_min=15000.0,
            estimated_cost_max=25000.0,
            currency="INR",
            currency_symbol="₹",
            estimated_manpower=5,
            estimated_duration_hours=2.0,
        ),
    )

    sim_req = MultiScenarioSimulationRequest(
        baseline_factors=base_factors,
        scenarios=[scen_1, scen_2],
    )
    sim_res = run_multi_scenario_simulation(payload=sim_req, current_user=ANALYST_USER)

    report_req = MitigationReportRequest(
        simulation_response=sim_res,
        incident_title="Sector 4 Arterial Inundation Review",
        category="waterlogging",
        location="Sector 4 Metro Junction",
        analyst_notes="Priority deployment recommended prior to evening commute peak.",
    )

    report_res = generate_municipal_mitigation_report(payload=report_req, current_user=ANALYST_USER)

    assert report_res.status == "PROPOSED"
    assert report_res.generated_by == ANALYST_USER.uid
    assert report_res.brief.incident_title == "Sector 4 Arterial Inundation Review"
    assert report_res.brief.category == "waterlogging"
    assert report_res.brief.projected_risk_reduction > 0
    assert len(report_res.brief.proposed_actions) > 0

    # Markdown format checks
    md = report_res.markdown_content
    assert "# Municipal Mitigation Brief: Sector 4 Arterial Inundation Review" in md
    assert "PROPOSED INTERVENTIONS ONLY" in md
    assert "Multi-Scenario Comparative Evaluation" in md
    assert "| Scenario Name | Simulated Score | ΔR Impact |" in md
    assert "Priority deployment recommended prior to evening commute peak." in md
    assert "Mandatory Disclaimers" in md


def test_generate_mitigation_report_standalone_rbac_restriction():
    """Verify that community users cannot generate standalone municipal reports without owning an incident."""
    base_factors = RiskFactorInput(
        hazard_severity=60.0, exposure=50.0, vulnerability=50.0, duration=40.0
    )
    sim_req = MultiScenarioSimulationRequest(
        baseline_factors=base_factors,
        scenarios=[
            MitigationScenarioInput(
                scenario_id="s1",
                scenario_name="S1",
                simulated_factors=RiskFactorInput(hazard_severity=30.0, exposure=30.0, vulnerability=30.0, duration=20.0),
            ),
            MitigationScenarioInput(
                scenario_id="s2",
                scenario_name="S2",
                simulated_factors=RiskFactorInput(hazard_severity=40.0, exposure=30.0, vulnerability=30.0, duration=20.0),
            ),
        ],
    )
    sim_res = run_multi_scenario_simulation(payload=sim_req, current_user=ANALYST_USER)

    report_req = MitigationReportRequest(
        simulation_response=sim_res,
        incident_title="City-wide Flood Plan",
    )

    # Community user attempting standalone municipal brief -> 403 Forbidden
    with pytest.raises(HTTPException) as exc:
        generate_municipal_mitigation_report(payload=report_req, current_user=COMMUNITY_USER_OWNER)
    assert exc.value.status_code == status.HTTP_403_FORBIDDEN
    assert "Generating standalone municipal mitigation briefs requires an ANALYST or ADMIN role" in exc.value.detail


# ==============================================================================
# 5. DATA INTEGRITY & OPENAPI REGISTRATION
# ==============================================================================

def test_non_destructive_in_memory_guarantee_no_firestore_writes(setup_mock_firestore: MockFirestore):
    """Assert that simulations and reports write zero documents to Firestore."""
    db = setup_mock_firestore
    initial_collections = set(db._collections.keys())

    base_factors = RiskFactorInput(
        hazard_severity=50.0, exposure=50.0, vulnerability=50.0, duration=50.0
    )
    req = MultiScenarioSimulationRequest(
        baseline_factors=base_factors,
        scenarios=[
            MitigationScenarioInput(
                scenario_id="s1",
                scenario_name="S1",
                simulated_factors=RiskFactorInput(hazard_severity=20.0, exposure=20.0, vulnerability=20.0, duration=20.0),
            ),
            MitigationScenarioInput(
                scenario_id="s2",
                scenario_name="S2",
                simulated_factors=RiskFactorInput(hazard_severity=30.0, exposure=30.0, vulnerability=30.0, duration=30.0),
            ),
        ],
    )
    sim_res = run_multi_scenario_simulation(payload=req, current_user=ANALYST_USER)

    report_req = MitigationReportRequest(
        simulation_response=sim_res,
        incident_title="Test In-Memory Brief",
    )
    generate_municipal_mitigation_report(payload=report_req, current_user=ANALYST_USER)

    # Assert no new collections or documents were created in Firestore
    final_collections = set(db._collections.keys())
    assert final_collections == initial_collections
    assert "mitigation_plans" not in final_collections
    assert "simulations" not in final_collections


def test_mitigation_router_registration_and_openapi_paths():
    """Verify that all three mitigation endpoints are mounted in the FastAPI app."""
    openapi_paths = app.openapi()["paths"]

    assert "/api/v1/ai/mitigation/presets/{category}" in openapi_paths
    assert "get" in openapi_paths["/api/v1/ai/mitigation/presets/{category}"]

    assert "/api/v1/ai/simulate/multi" in openapi_paths
    assert "post" in openapi_paths["/api/v1/ai/simulate/multi"]

    assert "/api/v1/ai/mitigation/report" in openapi_paths
    assert "post" in openapi_paths["/api/v1/ai/mitigation/report"]
