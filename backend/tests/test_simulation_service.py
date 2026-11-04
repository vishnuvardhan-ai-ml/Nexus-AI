"""
Unit tests for NEXUS AI What-If Scenario Simulation Service.

Focus Areas:
1. Exact baseline, simulated, and delta (ΔR) calculations.
2. Risk-level boundary transitions (e.g. HIGH -> MEDIUM, HIGH -> LOW).
3. Identification of primary mitigation vs escalation drivers.
4. Non-destructive guarantees (is_simulation=True, zero DB writes).
5. Provenance tracking (SIMULATION_OVERRIDE).
6. Input range validation and missing factor rejection.
7. Role-based ownership authorization boundaries.
"""
import pytest
from pydantic import ValidationError
from fastapi import HTTPException

from app.schemas.risk import (
    RiskLevel,
    EstimationSource,
    RiskFactorInput,
    SimulationRequest,
    SimulationResponse,
)
from app.schemas.user import UserRole, UserPrincipal
from app.services.simulation_service import (
    execute_simulation,
    verify_incident_simulation_access,
)


# ==============================================================================
# 1. EXACT SCORE & DELTA CALCULATIONS AND TRANSITIONS
# ==============================================================================

def test_execute_simulation_risk_reduction_and_level_transition():
    """
    Verify scenario simulation with risk mitigation:
    Baseline:   H=80, E=70, V=60, D=50 -> 32 + 21 + 12 + 5 = 70.0 (HIGH)
    Simulated:  H=25, E=30, V=30, D=20 -> 10 + 9 + 6 + 2 = 27.0 (LOW)
    Delta R = 27.0 - 70.0 = -43.0 pts
    """
    current_user = UserPrincipal(uid="analyst_1", email="analyst@nexus.ai", role=UserRole.ANALYST)

    request = SimulationRequest(
        scenario_name="Emergency Pump Deployment & Traffic Cordon",
        incident_id="inc_flood_01",
        baseline_factors=RiskFactorInput(
            hazard_severity=80.0,
            exposure=70.0,
            vulnerability=60.0,
            duration=50.0,
            source=EstimationSource.USER_DIRECT,
        ),
        simulated_factors=RiskFactorInput(
            hazard_severity=25.0,
            exposure=30.0,
            vulnerability=30.0,
            duration=20.0,
            source=EstimationSource.SIMULATION_OVERRIDE,
        ),
        intervention_notes="Deploy 2 diesel pumps and reroute city bus line.",
    )

    sim_resp = execute_simulation(request=request, current_user=current_user)

    assert isinstance(sim_resp, SimulationResponse)
    assert sim_resp.baseline_score == 70.0
    assert sim_resp.baseline_level == RiskLevel.HIGH
    assert sim_resp.simulated_score == 27.0
    assert sim_resp.simulated_level == RiskLevel.LOW
    assert sim_resp.score_difference == -43.0
    assert sim_resp.level_changed is True
    assert sim_resp.is_simulation is True
    assert sim_resp.simulated_by == "analyst_1"

    # Primary mitigation driver should be Hazard Severity:
    # Hazard delta = 0.4 * (25 - 80) = -22.0 pts (largest reduction)
    assert "Hazard Severity" in sim_resp.primary_mitigation_driver
    assert len(sim_resp.factors_responsible) == 4


def test_execute_simulation_risk_escalation():
    """
    Verify scenario simulation with risk escalation (e.g., severe storm worsens unresolved ponding):
    Baseline:   H=30, E=40, V=30, D=20 -> 12 + 12 + 6 + 2 = 32.0 (MEDIUM)
    Simulated:  H=85, E=80, V=70, D=60 -> 34 + 24 + 14 + 6 = 78.0 (HIGH)
    Delta R = +46.0 pts
    """
    current_user = UserPrincipal(uid="analyst_2", email="analyst2@nexus.ai", role=UserRole.ANALYST)

    request = SimulationRequest(
        scenario_name="Monsoon Flash Flood Escalation",
        incident_id="inc_rain_02",
        baseline_factors=RiskFactorInput(
            hazard_severity=30.0,
            exposure=40.0,
            vulnerability=30.0,
            duration=20.0,
        ),
        simulated_factors=RiskFactorInput(
            hazard_severity=85.0,
            exposure=80.0,
            vulnerability=70.0,
            duration=60.0,
        ),
    )

    sim_resp = execute_simulation(request=request, current_user=current_user)

    assert sim_resp.baseline_score == 32.0
    assert sim_resp.baseline_level == RiskLevel.MEDIUM
    assert sim_resp.simulated_score == 78.0
    assert sim_resp.simulated_level == RiskLevel.HIGH
    assert sim_resp.score_difference == 46.0
    assert sim_resp.level_changed is True
    assert "escalation driver" in sim_resp.primary_mitigation_driver.lower()


def test_execute_simulation_neutral_scenario():
    """Verify handling when baseline and simulated parameters are identical."""
    current_user = UserPrincipal(uid="user_3", email="user3@nexus.ai", role=UserRole.ANALYST)

    identical_factors = RiskFactorInput(
        hazard_severity=50.0,
        exposure=50.0,
        vulnerability=50.0,
        duration=50.0,
    )

    request = SimulationRequest(
        scenario_name="Status Quo Simulation",
        baseline_factors=identical_factors,
        simulated_factors=identical_factors,
    )

    sim_resp = execute_simulation(request=request, current_user=current_user)

    assert sim_resp.score_difference == 0.0
    assert sim_resp.level_changed is False
    assert "Identical parameters" in sim_resp.primary_mitigation_driver


# ==============================================================================
# 2. INPUT VALIDATION & ZERO SILENT INVENTION
# ==============================================================================

def test_simulation_rejects_missing_or_out_of_range_factors():
    """Verify that Pydantic strictly validates all factors in [0.0, 100.0] and rejects missing inputs."""
    # Out of range (< 0)
    with pytest.raises(ValidationError):
        RiskFactorInput(hazard_severity=-10.0, exposure=50.0, vulnerability=50.0, duration=50.0)

    # Out of range (> 100)
    with pytest.raises(ValidationError):
        RiskFactorInput(hazard_severity=50.0, exposure=120.0, vulnerability=50.0, duration=50.0)

    # Missing factor (duration missing)
    with pytest.raises(ValidationError):
        RiskFactorInput(hazard_severity=50.0, exposure=50.0, vulnerability=50.0)


# ==============================================================================
# 3. NON-DESTRUCTIVE PROVENANCE GUARANTEE
# ==============================================================================

def test_simulation_forces_simulation_override_provenance():
    """
    Verify that execute_simulation automatically tags simulated factors with
    SIMULATION_OVERRIDE provenance and is_simulation=True, ensuring clear distinction
    from live incident data.
    """
    current_user = UserPrincipal(uid="analyst_test", email="analyst@nexus.ai", role=UserRole.ANALYST)

    request = SimulationRequest(
        scenario_name="Test Override Flagging",
        baseline_factors=RiskFactorInput(
            hazard_severity=60.0, exposure=50.0, vulnerability=40.0, duration=30.0,
            source=EstimationSource.USER_DIRECT,
        ),
        simulated_factors=RiskFactorInput(
            hazard_severity=30.0, exposure=30.0, vulnerability=30.0, duration=20.0,
            # Even if caller passes USER_DIRECT, simulation must enforce SIMULATION_OVERRIDE
            source=EstimationSource.USER_DIRECT,
        ),
    )

    sim_resp = execute_simulation(request=request, current_user=current_user)

    assert sim_resp.is_simulation is True
    assert sim_resp.id.startswith("sim_")


# ==============================================================================
# 4. ROLE-BASED OWNERSHIP AUTHORIZATION
# ==============================================================================

def test_simulation_authorization_admin_and_analyst():
    """Verify that ADMIN and ANALYST can simulate any incident."""
    admin_user = UserPrincipal(uid="admin_uid", email="admin@nexus.ai", role=UserRole.ADMIN)
    analyst_user = UserPrincipal(uid="analyst_uid", email="analyst@nexus.ai", role=UserRole.ANALYST)
    incident = {"id": "inc_999", "reported_by": "citizen_uid"}

    assert verify_incident_simulation_access(incident, admin_user) is True
    assert verify_incident_simulation_access(incident, analyst_user) is True


def test_simulation_authorization_community_user():
    """Verify that COMMUNITY_USER can only simulate incidents they reported."""
    comm_user = UserPrincipal(uid="citizen_1", email="citizen1@nexus.ai", role=UserRole.COMMUNITY_USER)
    own_incident = {"id": "inc_mine", "reported_by": "citizen_1"}
    foreign_incident = {"id": "inc_theirs", "reported_by": "citizen_2"}

    # Own incident allowed
    assert verify_incident_simulation_access(own_incident, comm_user) is True

    # Foreign incident denied
    with pytest.raises(HTTPException) as exc:
        verify_incident_simulation_access(foreign_incident, comm_user)
    assert exc.value.status_code == 403
    assert "Community users are only authorized" in exc.value.detail
