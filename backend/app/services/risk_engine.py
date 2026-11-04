"""
NEXUS AI Deterministic Risk Engine & Explainability Service.

Formula:
    R = 0.4 * H + 0.3 * E + 0.2 * V + 0.1 * D
    Bounded strictly between 0.0 and 100.0.

Classification Boundaries:
    - LOW:    0.0 <= score < 30.0   (0 - 29)
    - MEDIUM: 30.0 <= score < 60.0  (30 - 59)
    - HIGH:   60.0 <= score <= 100.0 (60 - 100, exactly 60 is HIGH)

Features:
    1. Strict mathematical factor decomposition (points & percentage of risk).
    2. Transparent influence tagging (AMPLIFYING > 50, DAMPENING < 50, NEUTRAL == 50).
    3. Deterministic narrative generation detailing primary and secondary drivers.
    4. Non-destructive what-if scenario simulation engine (Delta R analysis).
    5. Documented civic baseline estimation with zero silent invention.
"""
import uuid
from datetime import datetime, timezone
from typing import Tuple, List, Dict, Any, Optional

from app.schemas.risk import (
    RiskLevel,
    EstimationSource,
    ModelStatus,
    FactorInfluence,
    RiskFactorInput,
    FactorContribution,
    FactorContributions,
    RiskAssessmentResponse,
    SimulationRequest,
    SimulationResponse,
)

# Mathematical formula weights (sum = 1.0)
WEIGHT_HAZARD = 0.4
WEIGHT_EXPOSURE = 0.3
WEIGHT_VULNERABILITY = 0.2
WEIGHT_DURATION = 0.1

FACTOR_CONFIG = {
    "hazard": {
        "label": "Hazard Severity (H)",
        "weight": WEIGHT_HAZARD,
        "description": "Physical magnitude, toxicity, depth, or destructiveness of hazard",
    },
    "exposure": {
        "label": "Population & Asset Exposure (E)",
        "weight": WEIGHT_EXPOSURE,
        "description": "Density of residents, commuters, or critical civic infrastructure in affected zone",
    },
    "vulnerability": {
        "label": "Structural & Social Vulnerability (V)",
        "weight": WEIGHT_VULNERABILITY,
        "description": "Lack of stormwater drainage, elderly/pedestrian density, or missing backup utilities",
    },
    "duration": {
        "label": "Unresolved Duration (D)",
        "weight": WEIGHT_DURATION,
        "description": "Persistence or elapsed timeframe incident has remained active without resolution",
    },
}


def classify_risk_score(score: float) -> RiskLevel:
    """
    Classify a composite risk score into deterministic operational bands:
        - LOW:    0.0 <= score < 30.0
        - MEDIUM: 30.0 <= score < 60.0
        - HIGH:   60.0 <= score <= 100.0 (Score of exactly 60.0 is HIGH)

    Raises ValueError if score is out of the closed interval [0.0, 100.0].
    """
    if score < 0.0 or score > 100.0:
        raise ValueError(f"Risk score must be within [0.0, 100.0], got {score}")

    # Explicit threshold boundaries
    if score < 30.0:
        return RiskLevel.LOW
    elif score < 60.0:
        return RiskLevel.MEDIUM
    else:
        return RiskLevel.HIGH


def compute_weighted_risk(h: float, e: float, v: float, d: float) -> float:
    """
    Compute raw deterministic weighted risk score:
        R = 0.4*H + 0.3*E + 0.2*V + 0.1*D
    Bounded to [0.0, 100.0] and rounded to 2 decimal places.
    """
    for name, val in [("Hazard", h), ("Exposure", e), ("Vulnerability", v), ("Duration", d)]:
        if val < 0.0 or val > 100.0:
            raise ValueError(f"{name} must be within [0.0, 100.0], got {val}")

    raw_score = (WEIGHT_HAZARD * h) + (WEIGHT_EXPOSURE * e) + (WEIGHT_VULNERABILITY * v) + (WEIGHT_DURATION * d)
    clamped = max(0.0, min(100.0, raw_score))
    return round(clamped, 2)


def get_factor_influence(value: float) -> FactorInfluence:
    """
    Determine whether an individual factor amplifies (>50) or dampens (<50) risk
    relative to the neutral 50-point midpoint baseline.
    """
    if value > 50.0:
        return FactorInfluence.AMPLIFYING
    elif value < 50.0:
        return FactorInfluence.DAMPENING
    return FactorInfluence.NEUTRAL


def calculate_factor_contributions(factors: RiskFactorInput) -> Tuple[float, FactorContributions]:
    """
    Decompose the risk score into exact factor contributions.
    Returns:
        (total_risk_score, FactorContributions)
    """
    h_val = float(factors.hazard_severity)
    e_val = float(factors.exposure)
    v_val = float(factors.vulnerability)
    d_val = float(factors.duration)

    # Compute raw points contributed by each factor
    h_pts = round(WEIGHT_HAZARD * h_val, 2)
    e_pts = round(WEIGHT_EXPOSURE * e_val, 2)
    v_pts = round(WEIGHT_VULNERABILITY * v_val, 2)
    d_pts = round(WEIGHT_DURATION * d_val, 2)

    total_score = round(max(0.0, min(100.0, h_pts + e_pts + v_pts + d_pts)), 2)

    # Calculate percentage share of total score
    def _pct(pts: float) -> float:
        if total_score <= 0.0:
            return 0.0
        return round((pts / total_score) * 100.0, 1)

    h_pct = _pct(h_pts)
    e_pct = _pct(e_pts)
    v_pct = _pct(v_pts)
    d_pct = _pct(d_pts)

    # Create individual FactorContribution records
    c_hazard = FactorContribution(
        factor_name="hazard",
        factor_label=FACTOR_CONFIG["hazard"]["label"],
        input_value=h_val,
        weight=WEIGHT_HAZARD,
        weighted_points=h_pts,
        contribution_percentage=h_pct,
        influence=get_factor_influence(h_val),
        explanation=(
            f"Hazard severity ({h_val:.1f}/100) at 40% weight adds {h_pts:.1f} pts "
            f"({'amplifying' if h_val > 50 else 'dampening' if h_val < 50 else 'neutral'} risk)."
        ),
    )

    c_exposure = FactorContribution(
        factor_name="exposure",
        factor_label=FACTOR_CONFIG["exposure"]["label"],
        input_value=e_val,
        weight=WEIGHT_EXPOSURE,
        weighted_points=e_pts,
        contribution_percentage=e_pct,
        influence=get_factor_influence(e_val),
        explanation=(
            f"Exposure density ({e_val:.1f}/100) at 30% weight adds {e_pts:.1f} pts "
            f"({'amplifying' if e_val > 50 else 'dampening' if e_val < 50 else 'neutral'} risk)."
        ),
    )

    c_vulnerability = FactorContribution(
        factor_name="vulnerability",
        factor_label=FACTOR_CONFIG["vulnerability"]["label"],
        input_value=v_val,
        weight=WEIGHT_VULNERABILITY,
        weighted_points=v_pts,
        contribution_percentage=v_pct,
        influence=get_factor_influence(v_val),
        explanation=(
            f"Infrastructure vulnerability ({v_val:.1f}/100) at 20% weight adds {v_pts:.1f} pts "
            f"({'amplifying' if v_val > 50 else 'dampening' if v_val < 50 else 'neutral'} risk)."
        ),
    )

    c_duration = FactorContribution(
        factor_name="duration",
        factor_label=FACTOR_CONFIG["duration"]["label"],
        input_value=d_val,
        weight=WEIGHT_DURATION,
        weighted_points=d_pts,
        contribution_percentage=d_pct,
        influence=get_factor_influence(d_val),
        explanation=(
            f"Unresolved duration ({d_val:.1f}/100) at 10% weight adds {d_pts:.1f} pts "
            f"({'amplifying' if d_val > 50 else 'dampening' if d_val < 50 else 'neutral'} risk)."
        ),
    )

    # Rank factors by weighted point contributions (with tie-breaker by base weight)
    ranking = [
        ("hazard", h_pts, WEIGHT_HAZARD),
        ("exposure", e_pts, WEIGHT_EXPOSURE),
        ("vulnerability", v_pts, WEIGHT_VULNERABILITY),
        ("duration", d_pts, WEIGHT_DURATION),
    ]
    # Sort descending by points, then by weight
    ranking.sort(key=lambda x: (x[1], x[2]), reverse=True)

    primary_driver = ranking[0][0]
    secondary_driver = ranking[1][0] if ranking[1][1] > 0.0 or total_score == 0.0 else None

    contributions = FactorContributions(
        hazard=c_hazard,
        exposure=c_exposure,
        vulnerability=c_vulnerability,
        duration=c_duration,
        primary_driver=primary_driver,
        secondary_driver=secondary_driver,
    )

    return total_score, contributions


def generate_risk_explanation(
    score: float,
    level: RiskLevel,
    contributions: FactorContributions,
    factors: RiskFactorInput,
) -> str:
    """
    Generate a human-readable, transparent explainability narrative.
    Breaks down primary driver, amplifying vs dampening forces, and provenance.
    """
    primary = getattr(contributions, contributions.primary_driver)
    secondary = getattr(contributions, contributions.secondary_driver) if contributions.secondary_driver else None

    # Identify amplifying and dampening factors
    amplifiers = []
    dampeners = []
    for f_name in ["hazard", "exposure", "vulnerability", "duration"]:
        c = getattr(contributions, f_name)
        if c.influence == FactorInfluence.AMPLIFYING:
            amplifiers.append(f"{c.factor_label} ({c.input_value:.0f}/100)")
        elif c.influence == FactorInfluence.DAMPENING:
            dampeners.append(f"{c.factor_label} ({c.input_value:.0f}/100)")

    # Build clear transparent narrative
    paragraphs = [
        f"Incident evaluated at a composite risk score of {score:.1f}/100, placing it in the {level.value} risk category.",
        f"The primary driver is {primary.factor_label}, contributing {primary.weighted_points:.1f} points "
        f"({primary.contribution_percentage:.1f}% of total score at a {int(primary.weight * 100)}% weight multiplier).",
    ]

    if secondary and secondary.weighted_points > 0:
        paragraphs.append(
            f"The secondary driver is {secondary.factor_label}, adding {secondary.weighted_points:.1f} points "
            f"({secondary.contribution_percentage:.1f}% of total score)."
        )

    if amplifiers:
        paragraphs.append(f"Amplifying factors elevating risk above neutral baseline: {', '.join(amplifiers)}.")
    if dampeners:
        paragraphs.append(f"Mitigating factors keeping risk restrained: {', '.join(dampeners)}.")

    # Provenance note
    source_tag = factors.source.value
    notes_clause = f" with notes: '{factors.source_notes}'" if factors.source_notes else ""
    paragraphs.append(
        f"Provenance: Input parameters were supplied via {source_tag}{notes_clause}. "
        f"Calculated deterministically using formula R = 0.4H + 0.3E + 0.2V + 0.1D with zero synthetic imputation."
    )

    return " ".join(paragraphs)


def assess_risk(
    factors: RiskFactorInput,
    incident_id: Optional[str] = None,
    assessed_by: str = "system",
    ml_advisory: Optional[Dict[str, Any]] = None,
    model_status: Optional[ModelStatus] = None,
    include_ml_advisory: bool = False,
    title: Optional[str] = None,
    description: Optional[str] = None,
    category: Optional[str] = None,
) -> RiskAssessmentResponse:
    """
    Execute full risk assessment. Computes score, factor decomposition, and explainability narrative.
    Optionally evaluates ML classification pipeline as advisory context without modifying authoritative score.
    Returns immutable RiskAssessmentResponse.
    """
    score, contributions = calculate_factor_contributions(factors)
    level = classify_risk_score(score)
    explanation = generate_risk_explanation(score, level, contributions, factors)

    # Optional advisory ML inference (never replaces or mutates authoritative score)
    advisory_output = ml_advisory
    final_status = model_status or ModelStatus.DEMO

    if include_ml_advisory and advisory_output is None:
        try:
            from app.ml.inference import default_inference_service
            final_status = default_inference_service.status
            if default_inference_service.is_loaded:
                advisory_output = default_inference_service.predict_advisory(
                    title=title or "Civic Incident Evaluation",
                    description=description or "Civic Incident Context",
                    category=category or "general_safety",
                    factors=factors,
                )
        except Exception:
            advisory_output = None
            final_status = ModelStatus.INSUFFICIENT_DATA

    now_iso = datetime.now(timezone.utc).isoformat()
    assessment_id = f"risk_{uuid.uuid4().hex[:12]}"

    methodology_statement = (
        "Deterministic civic multi-criteria evaluation combining observed physical magnitude (40%), "
        "population exposure (30%), infrastructure vulnerability (20%), and unresolved duration (10%). "
        "Scoring is strictly bounded between 0.0 and 100.0 without unverified algorithmic adjustments."
    )

    return RiskAssessmentResponse(
        id=assessment_id,
        incident_id=incident_id,
        risk_score=score,
        risk_level=level,
        factors=factors,
        contributions=contributions,
        formula="R = 0.4H + 0.3E + 0.2V + 0.1D",
        methodology=methodology_statement,
        explanation=explanation,
        ml_advisory=advisory_output,
        model_status=final_status,
        model_version="v1.0.0-deterministic",
        assessed_by=assessed_by,
        created_at=now_iso,
    )


def simulate_intervention(
    request: SimulationRequest,
    simulated_by: str = "analyst",
) -> SimulationResponse:
    """
    Non-destructively evaluate a what-if civic intervention scenario.
    Compares baseline factors with simulated factors to compute Delta R,
    identifies level boundary transitions, and determines the primary mitigation driver.
    """
    base_score, base_contrib = calculate_factor_contributions(request.baseline_factors)
    base_level = classify_risk_score(base_score)

    sim_score, sim_contrib = calculate_factor_contributions(request.simulated_factors)
    sim_level = classify_risk_score(sim_score)

    score_diff = round(sim_score - base_score, 2)
    level_changed = (base_level != sim_level)

    # Calculate parameter shifts between baseline and simulated
    factor_shifts: List[str] = []
    reduction_candidates = []

    for f_key, weight in [
        ("hazard_severity", WEIGHT_HAZARD),
        ("exposure", WEIGHT_EXPOSURE),
        ("vulnerability", WEIGHT_VULNERABILITY),
        ("duration", WEIGHT_DURATION),
    ]:
        b_val = getattr(request.baseline_factors, f_key)
        s_val = getattr(request.simulated_factors, f_key)
        delta_val = s_val - b_val
        delta_pts = round(delta_val * weight, 2)

        if abs(delta_val) > 0.01:
            direction = "reduced" if delta_val < 0 else "increased"
            factor_shifts.append(
                f"{f_key.replace('_', ' ').capitalize()} {direction} by {abs(delta_val):.1f} pts "
                f"({delta_pts:+.1f} risk score impact)"
            )
            # Track reductions (negative delta_pts)
            if delta_pts < 0:
                reduction_candidates.append((f_key, abs(delta_pts)))

    if reduction_candidates:
        reduction_candidates.sort(key=lambda x: x[1], reverse=True)
        top_driver_key = reduction_candidates[0][0]
        top_driver_label = top_driver_key.replace("_", " ").capitalize()
        primary_mitigation_driver = f"{top_driver_label} mitigation (-{reduction_candidates[0][1]:.1f} pts)"
    elif score_diff > 0:
        primary_mitigation_driver = "No mitigation: scenario increases overall civic risk"
    else:
        primary_mitigation_driver = "Neutral intervention: no net risk score reduction"

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
        primary_mitigation_driver=primary_mitigation_driver,
        factors_responsible=factor_shifts or ["No factor shifts detected between baseline and simulated parameters."],
        is_simulation=True,
        intervention_notes=request.intervention_notes,
        simulated_by=simulated_by,
        created_at=now_iso,
    )


def estimate_incident_factors(incident_data: Dict[str, Any]) -> RiskFactorInput:
    """
    Transparently derive baseline risk factors for an incident from verified civic attributes.
    This helper is used when an incident does not yet possess manual sensor/analyst scores.

    CRITICAL RULE:
    The output is explicitly tagged as EstimationSource.DOCUMENTED_ESTIMATE with full notes.
    Values are NEVER silently invented or disguised as user-measured ground truth.
    """
    category = str(incident_data.get("category", "")).lower()
    severity_str = str(incident_data.get("severity", "")).upper()
    status_str = str(incident_data.get("status", "")).upper()

    # Heuristic baselines based on verified civic domain definitions
    severity_map = {
        "CRITICAL": 85.0,
        "HIGH": 65.0,
        "MEDIUM": 45.0,
        "LOW": 20.0,
    }
    hazard_val = severity_map.get(severity_str, 50.0)

    category_exposure_map = {
        "electrical": 75.0,     # High life-safety & fire risk
        "flooding": 70.0,       # Wide transit & residential coverage
        "waterlogging": 65.0,   # Road & residential exposure
        "road_damage": 55.0,    # Vehicular & pedestrian traffic
        "waste": 40.0,          # Localized neighborhood sanitation
        "extreme_heat": 60.0,   # Broad outdoor demographic exposure
    }
    # Match category keyword
    exposure_val = 50.0
    for key, val in category_exposure_map.items():
        if key in category:
            exposure_val = val
            break

    # Vulnerability heuristic (unresolved or critical status indicates higher vulnerability)
    vulnerability_val = 60.0 if severity_str in ["CRITICAL", "HIGH"] else 40.0

    # Duration heuristic based on status
    duration_map = {
        "OPEN": 60.0,
        "INVESTIGATING": 45.0,
        "IN_PROGRESS": 35.0,
        "RESOLVED": 10.0,
    }
    duration_val = duration_map.get(status_str, 50.0)

    derivation_notes = (
        f"Documented civic heuristic derived from severity={severity_str}, "
        f"category={category or 'unspecified'}, status={status_str}. "
        f"Requires analyst review for ground-truth confirmation."
    )

    return RiskFactorInput(
        hazard_severity=hazard_val,
        exposure=exposure_val,
        vulnerability=vulnerability_val,
        duration=duration_val,
        source=EstimationSource.DOCUMENTED_ESTIMATE,
        source_notes=derivation_notes,
    )
