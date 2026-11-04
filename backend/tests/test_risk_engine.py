"""
Tests for NEXUS AI Deterministic Risk Engine & Factor Decomposition.

Focus areas:
1. Exact boundary tests for LOW (0–29), MEDIUM (30–59), and HIGH (60–100), including score of exactly 60.
2. Out-of-bounds rejection (< 0 and > 100).
3. Factor contribution decomposition, weights (0.4H, 0.3E, 0.2V, 0.1D), and percentage totals.
4. Input validation (strict rejection of missing/out-of-range factors, no silent invention).
5. Influence classification (AMPLIFYING > 50, DAMPENING < 50, NEUTRAL == 50).
6. Explainability narrative and provenance tracking.
7. Non-destructive what-if scenario simulations (Delta R analysis).
8. Documented civic estimate heuristics with transparent provenance tags.
"""
import pytest
from pydantic import ValidationError

from app.schemas.risk import (
    RiskLevel,
    EstimationSource,
    FactorInfluence,
    RiskFactorInput,
    SimulationRequest,
)
from app.services.risk_engine import (
    classify_risk_score,
    compute_weighted_risk,
    calculate_factor_contributions,
    generate_risk_explanation,
    assess_risk,
    simulate_intervention,
    estimate_incident_factors,
    get_factor_influence,
)


# ==============================================================================
# 1. BOUNDARY AND CLASSIFICATION TESTS
# ==============================================================================

def test_classify_risk_score_exact_boundaries():
    """
    Verify exact mathematical classification thresholds:
    LOW:    0.0 <= score < 30.0
    MEDIUM: 30.0 <= score < 60.0
    HIGH:   60.0 <= score <= 100.0 (Score of exactly 60 is strictly HIGH)
    """
    # Lower bound & LOW range
    assert classify_risk_score(0.0) == RiskLevel.LOW
    assert classify_risk_score(15.5) == RiskLevel.LOW
    assert classify_risk_score(29.0) == RiskLevel.LOW
    assert classify_risk_score(29.99) == RiskLevel.LOW

    # Boundary transition at 30.0
    assert classify_risk_score(30.0) == RiskLevel.MEDIUM
    assert classify_risk_score(45.0) == RiskLevel.MEDIUM
    assert classify_risk_score(59.0) == RiskLevel.MEDIUM
    assert classify_risk_score(59.99) == RiskLevel.MEDIUM

    # Boundary transition at exactly 60.0 (Mandatory requirement: exactly 60 is HIGH)
    assert classify_risk_score(60.0) == RiskLevel.HIGH
    assert classify_risk_score(60.01) == RiskLevel.HIGH
    assert classify_risk_score(75.5) == RiskLevel.HIGH
    assert classify_risk_score(100.0) == RiskLevel.HIGH


def test_classify_risk_score_out_of_bounds_rejection():
    """Verify that scores outside [0.0, 100.0] are strictly rejected with ValueError."""
    with pytest.raises(ValueError, match="within \\[0.0, 100.0\\]"):
        classify_risk_score(-0.1)

    with pytest.raises(ValueError, match="within \\[0.0, 100.0\\]"):
        classify_risk_score(-50.0)

    with pytest.raises(ValueError, match="within \\[0.0, 100.0\\]"):
        classify_risk_score(100.01)

    with pytest.raises(ValueError, match="within \\[0.0, 100.0\\]"):
        classify_risk_score(250.0)


# ==============================================================================
# 2. WEIGHTED FORMULA AND FACTOR DECOMPOSITION TESTS
# ==============================================================================

def test_compute_weighted_risk_formula():
    """
    Verify formula: R = 0.4H + 0.3E + 0.2V + 0.1D
    """
    # All zeros
    assert compute_weighted_risk(0.0, 0.0, 0.0, 0.0) == 0.0

    # Max values
    assert compute_weighted_risk(100.0, 100.0, 100.0, 100.0) == 100.0

    # Individual factor isolate test
    # Hazard: 0.4 * 100 = 40.0
    assert compute_weighted_risk(100.0, 0.0, 0.0, 0.0) == 40.0

    # Exposure: 0.3 * 100 = 30.0
    assert compute_weighted_risk(0.0, 100.0, 0.0, 0.0) == 30.0

    # Vulnerability: 0.2 * 100 = 20.0
    assert compute_weighted_risk(0.0, 0.0, 100.0, 0.0) == 20.0

    # Duration: 0.1 * 100 = 10.0
    assert compute_weighted_risk(0.0, 0.0, 0.0, 100.0) == 10.0

    # Mixed realistic scenario: H=70, E=80, V=50, D=30
    # Expected: 0.4(70) + 0.3(80) + 0.2(50) + 0.1(30) = 28 + 24 + 10 + 3 = 65.0
    assert compute_weighted_risk(70.0, 80.0, 50.0, 30.0) == 65.0


def test_calculate_factor_contributions_details():
    """
    Verify mathematical decomposition into points, percentages, and ranked drivers.
    Scenario: H=70, E=80, V=50, D=30 -> Total R = 65.0
    """
    factors = RiskFactorInput(
        hazard_severity=70.0,
        exposure=80.0,
        vulnerability=50.0,
        duration=30.0,
        source=EstimationSource.USER_DIRECT,
    )

    score, contrib = calculate_factor_contributions(factors)

    assert score == 65.0
    # Hazard: 0.4 * 70 = 28.0 pts -> (28 / 65) * 100 = 43.1%
    assert contrib.hazard.weighted_points == 28.0
    assert contrib.hazard.weight == 0.4
    assert contrib.hazard.contribution_percentage == 43.1
    assert contrib.hazard.influence == FactorInfluence.AMPLIFYING

    # Exposure: 0.3 * 80 = 24.0 pts -> (24 / 65) * 100 = 36.9%
    assert contrib.exposure.weighted_points == 24.0
    assert contrib.exposure.weight == 0.3
    assert contrib.exposure.contribution_percentage == 36.9
    assert contrib.exposure.influence == FactorInfluence.AMPLIFYING

    # Vulnerability: 0.2 * 50 = 10.0 pts -> (10 / 65) * 100 = 15.4%
    assert contrib.vulnerability.weighted_points == 10.0
    assert contrib.vulnerability.weight == 0.2
    assert contrib.vulnerability.contribution_percentage == 15.4
    assert contrib.vulnerability.influence == FactorInfluence.NEUTRAL

    # Duration: 0.1 * 30 = 3.0 pts -> (3 / 65) * 100 = 4.6%
    assert contrib.duration.weighted_points == 3.0
    assert contrib.duration.weight == 0.1
    assert contrib.duration.contribution_percentage == 4.6
    assert contrib.duration.influence == FactorInfluence.DAMPENING

    # Primary and secondary driver ranking
    assert contrib.primary_driver == "hazard"
    assert contrib.secondary_driver == "exposure"


def test_calculate_factor_contributions_zero_score():
    """Verify clean handling when all inputs are 0 (no division by zero in percentages)."""
    factors = RiskFactorInput(
        hazard_severity=0.0,
        exposure=0.0,
        vulnerability=0.0,
        duration=0.0,
    )
    score, contrib = calculate_factor_contributions(factors)
    assert score == 0.0
    assert contrib.hazard.contribution_percentage == 0.0
    assert contrib.exposure.contribution_percentage == 0.0
    assert contrib.vulnerability.contribution_percentage == 0.0
    assert contrib.duration.contribution_percentage == 0.0


def test_factor_influence_classification():
    """Verify influence classification against neutral 50-point midpoint."""
    assert get_factor_influence(50.1) == FactorInfluence.AMPLIFYING
    assert get_factor_influence(99.0) == FactorInfluence.AMPLIFYING
    assert get_factor_influence(49.9) == FactorInfluence.DAMPENING
    assert get_factor_influence(10.0) == FactorInfluence.DAMPENING
    assert get_factor_influence(50.0) == FactorInfluence.NEUTRAL


# ==============================================================================
# 3. STRICT SCHEMA VALIDATION & ZERO SILENT INVENTION
# ==============================================================================

def test_risk_factor_input_rejects_missing_fields():
    """
    Verify that missing H, E, V, or D fields are strictly rejected.
    The system NEVER silently invents missing factor values.
    """
    # Missing duration
    with pytest.raises(ValidationError) as exc:
        RiskFactorInput(hazard_severity=50.0, exposure=50.0, vulnerability=50.0)
    assert "duration" in str(exc.value)

    # Missing hazard
    with pytest.raises(ValidationError) as exc:
        RiskFactorInput(exposure=50.0, vulnerability=50.0, duration=50.0)
    assert "hazard_severity" in str(exc.value)


def test_risk_factor_input_range_enforcement():
    """Verify that inputs outside [0.0, 100.0] are rejected by Pydantic."""
    with pytest.raises(ValidationError):
        RiskFactorInput(hazard_severity=-5.0, exposure=50.0, vulnerability=50.0, duration=50.0)

    with pytest.raises(ValidationError):
        RiskFactorInput(hazard_severity=50.0, exposure=105.0, vulnerability=50.0, duration=50.0)

    with pytest.raises(ValidationError):
        RiskFactorInput(hazard_severity=50.0, exposure=50.0, vulnerability=-0.01, duration=50.0)

    with pytest.raises(ValidationError):
        RiskFactorInput(hazard_severity=50.0, exposure=50.0, vulnerability=50.0, duration=100.1)


# ==============================================================================
# 4. EXPLAINABILITY & PROVENANCE REPORTING
# ==============================================================================

def test_generate_risk_explanation_contains_provenance_and_drivers():
    """Verify narrative transparency includes driver breakdown, percentages, and provenance."""
    factors = RiskFactorInput(
        hazard_severity=85.0,
        exposure=90.0,
        vulnerability=40.0,
        duration=20.0,
        source=EstimationSource.USER_DIRECT,
        source_notes="Verified by station field sensor #14",
    )

    assessment = assess_risk(factors=factors, incident_id="inc_test_123", assessed_by="analyst_uid_456")

    assert assessment.risk_score > 0
    assert assessment.risk_level in [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH]
    assert assessment.incident_id == "inc_test_123"
    assert assessment.assessed_by == "analyst_uid_456"

    # Narrative checks
    assert "The primary driver is" in assessment.explanation
    assert "USER_DIRECT" in assessment.explanation
    assert "Verified by station field sensor #14" in assessment.explanation
    assert "R = 0.4H + 0.3E + 0.2V + 0.1D" in assessment.explanation


# ==============================================================================
# 5. WHAT-IF SCENARIO SIMULATION ENGINE
# ==============================================================================

def test_simulate_intervention_delta_r_and_level_transition():
    """
    Verify non-destructive intervention simulation:
    Baseline: H=85, E=80, V=60, D=50 -> Score = 34 + 24 + 12 + 5 = 75.0 (HIGH)
    Intervention: Water pumps deployed and traffic redirected -> H=30, E=30, V=40, D=20
    Simulated score: 12 + 9 + 8 + 2 = 31.0 (MEDIUM)
    Delta R = 31.0 - 75.0 = -44.0 pts (Risk reduction)
    """
    baseline = RiskFactorInput(
        hazard_severity=85.0,
        exposure=80.0,
        vulnerability=60.0,
        duration=50.0,
    )
    simulated = RiskFactorInput(
        hazard_severity=30.0,
        exposure=30.0,
        vulnerability=40.0,
        duration=20.0,
        source=EstimationSource.SIMULATION_OVERRIDE,
    )

    request = SimulationRequest(
        scenario_name="Pump Deployment & Road Diversion",
        incident_id="inc_live_789",
        baseline_factors=baseline,
        simulated_factors=simulated,
        intervention_notes="Deploys high-volume drainage pumps and reroutes bus transit routes.",
    )

    result = simulate_intervention(request=request, simulated_by="analyst_jane")

    assert result.is_simulation is True
    assert result.baseline_score == 75.0
    assert result.baseline_level == RiskLevel.HIGH
    assert result.simulated_score == 31.0
    assert result.simulated_level == RiskLevel.MEDIUM
    assert result.score_difference == -44.0
    assert result.level_changed is True
    assert "Hazard severity mitigation" in result.primary_mitigation_driver
    assert len(result.factors_responsible) >= 4
    assert result.simulated_by == "analyst_jane"


# ==============================================================================
# 6. DOCUMENTED CIVIC ESTIMATION HELPER (ZERO SILENT INVENTION)
# ==============================================================================

def test_estimate_incident_factors_documented_provenance():
    """
    Verify that civic baseline estimation sets DOCUMENTED_ESTIMATE source
    and includes explicit transparent reasoning in source_notes.
    """
    incident = {
        "title": "Severe road waterlogging near Metro Station",
        "category": "waterlogging",
        "severity": "CRITICAL",
        "status": "OPEN",
    }

    factors = estimate_incident_factors(incident)

    assert factors.source == EstimationSource.DOCUMENTED_ESTIMATE
    assert factors.hazard_severity == 85.0  # CRITICAL maps to 85
    assert factors.exposure == 65.0         # Waterlogging exposure heuristic
    assert factors.vulnerability == 60.0    # High/Critical vulnerability
    assert factors.duration == 60.0         # OPEN status persistence
    assert "Documented civic heuristic" in factors.source_notes
    assert "severity=CRITICAL" in factors.source_notes
