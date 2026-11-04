"""
NEXUS AI What-If Scenario Simulation Service.

Provides non-destructive what-if scenario simulations using the deterministic
multi-criteria risk engine (R = 0.4H + 0.3E + 0.2V + 0.1D).

MANDATORY CONSTRAINTS:
1. Non-destructive: Never mutates, updates, or creates records in Cloud Firestore.
2. Provenance: Flags all simulated factors as EstimationSource.SIMULATION_OVERRIDE and is_simulation=True.
3. Delta Analysis: Computes exact delta (simulated_score - baseline_score), identifies boundary
   transitions (e.g. HIGH -> MEDIUM), and determines the primary factor driving improvement or deterioration.
4. Authorization: Role-based validation prevents community users from simulating scenarios on
   incidents they did not author.
5. Transparency: Clearly distinguishes hypothetical scenario simulations from real observations.
"""
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
import uuid
from fastapi import HTTPException, status

from app.schemas.risk import (
    RiskLevel,
    EstimationSource,
    RiskFactorInput,
    SimulationRequest,
    SimulationResponse,
)
from app.schemas.user import UserRole, UserPrincipal
from app.services.risk_engine import (
    calculate_factor_contributions,
    classify_risk_score,
    WEIGHT_HAZARD,
    WEIGHT_EXPOSURE,
    WEIGHT_VULNERABILITY,
    WEIGHT_DURATION,
)

FACTOR_WEIGHT_MAP = {
    "hazard_severity": ("Hazard Severity (H)", WEIGHT_HAZARD),
    "exposure": ("Exposure (E)", WEIGHT_EXPOSURE),
    "vulnerability": ("Vulnerability (V)", WEIGHT_VULNERABILITY),
    "duration": ("Duration (D)", WEIGHT_DURATION),
}


def verify_incident_simulation_access(
    incident_data: Dict[str, Any],
    current_user: UserPrincipal,
) -> bool:
    """
    Enforce ownership and role-based authorization for scenario simulations:
    - ADMIN and ANALYST have full simulation access across all civic incidents.
    - COMMUNITY_USER can only simulate scenarios on incidents they reported.
    Raises HTTPException(403) if access is denied.
    """
    if current_user.role in [UserRole.ADMIN, UserRole.ANALYST]:
        return True

    reporter_uid = incident_data.get("reported_by") or incident_data.get("reporter_uid")
    if reporter_uid == current_user.uid:
        return True

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Access denied: Community users are only authorized to simulate scenarios for incidents they reported.",
    )


def execute_simulation(
    request: SimulationRequest,
    current_user: UserPrincipal,
    incident_data: Optional[Dict[str, Any]] = None,
) -> SimulationResponse:
    """
    Execute non-destructive what-if scenario simulation.

    Steps:
    1. Check authorization if incident_data is linked.
    2. Enforce SIMULATION_OVERRIDE provenance on simulated factors.
    3. Calculate baseline and simulated scores via deterministic weighted formula.
    4. Compute Delta R and identify risk-level boundary transitions.
    5. Decompose factor shifts and determine primary mitigation or escalation driver.
    6. Return immutable SimulationResponse with is_simulation=True.
    """
    # 1. Authorization check if linked to a specific incident
    if incident_data is not None:
        verify_incident_simulation_access(incident_data, current_user)

    # 2. Force provenance tag to prevent simulated data from disguising as ground truth
    sim_factors = request.simulated_factors.model_copy()
    sim_factors.source = EstimationSource.SIMULATION_OVERRIDE
    if not sim_factors.source_notes:
        sim_factors.source_notes = f"Simulated what-if scenario '{request.scenario_name}' by UID {current_user.uid}"

    # 3. Calculate baseline score & level
    base_score, base_contrib = calculate_factor_contributions(request.baseline_factors)
    base_level = classify_risk_score(base_score)

    # 4. Calculate simulated score & level
    sim_score, sim_contrib = calculate_factor_contributions(sim_factors)
    sim_level = classify_risk_score(sim_score)

    # 5. Delta calculations
    score_diff = round(sim_score - base_score, 2)
    level_changed = (base_level != sim_level)

    # 6. Factor-by-factor parameter shift decomposition
    factor_shifts: List[str] = []
    delta_points_list = []

    for f_attr, (f_label, weight) in FACTOR_WEIGHT_MAP.items():
        b_val = getattr(request.baseline_factors, f_attr)
        s_val = getattr(sim_factors, f_attr)
        diff_val = s_val - b_val
        diff_pts = round(diff_val * weight, 2)

        if abs(diff_val) > 0.01:
            verb = "decreased" if diff_val < 0 else "increased"
            factor_shifts.append(
                f"{f_label} {verb} from {b_val:.1f} to {s_val:.1f} ({diff_pts:+.1f} risk score impact)"
            )
            delta_points_list.append((f_label, diff_pts, diff_val))

    # 7. Identify primary driver of improvement or deterioration
    if delta_points_list:
        if score_diff < 0:
            # Improvement: find largest negative point contribution
            delta_points_list.sort(key=lambda x: x[1])  # Most negative first
            top_mitigator = delta_points_list[0]
            primary_driver_text = (
                f"Primary mitigation driver: {top_mitigator[0]} reduction "
                f"({top_mitigator[1]:+.1f} pts, parameter reduced by {abs(top_mitigator[2]):.1f})"
            )
        elif score_diff > 0:
            # Deterioration: find largest positive point contribution
            delta_points_list.sort(key=lambda x: x[1], reverse=True)  # Most positive first
            top_escalator = delta_points_list[0]
            primary_driver_text = (
                f"Primary escalation driver: {top_escalator[0]} increase "
                f"({top_escalator[1]:+.1f} pts, parameter increased by {abs(top_escalator[2]):.1f})"
            )
        else:
            primary_driver_text = "Neutral scenario: Factor shifts cancelled out, resulting in zero net score change."
    else:
        primary_driver_text = "Identical parameters: No factor modifications detected between baseline and simulated inputs."

    now_iso = datetime.now(timezone.utc).isoformat()
    sim_id = f"sim_{uuid.uuid4().hex[:12]}"

    return SimulationResponse(
        id=sim_id,
        scenario_name=request.scenario_name,
        incident_id=request.incident_id,
        baseline_score=base_score,
        baseline_level=base_level,
        simulated_score=sim_score,
        simulated_level=sim_level,
        score_difference=score_diff,
        level_changed=level_changed,
        primary_mitigation_driver=primary_driver_text,
        factors_responsible=factor_shifts or ["Baseline and simulated parameters are identical."],
        is_simulation=True,
        intervention_notes=request.intervention_notes,
        simulated_by=current_user.uid,
        created_at=now_iso,
    )
