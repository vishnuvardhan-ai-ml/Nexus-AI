"""
NEXUS AI Risk Intelligence, Explainability, Scenario Simulation, and Model Telemetry Endpoints.

Routes:
- POST /api/v1/ai/assess
- GET  /api/v1/ai/assessments/{assessment_id}
- POST /api/v1/ai/simulate
- GET  /api/v1/ai/recommendations/{incident_id}
- GET  /api/v1/ai/model/status
- GET  /api/v1/ai/model/metrics
- GET  /api/v1/ai/mitigation/presets/{category}
- POST /api/v1/ai/simulate/multi
- POST /api/v1/ai/mitigation/report
"""
import logging
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, Request, HTTPException, status
from firebase_admin import firestore

from app.core.config import settings
from app.core.rate_limit import rate_limit
from app.schemas.risk import (
    RiskAssessmentCreate,
    RiskAssessmentResponse,
    SimulationRequest,
    SimulationResponse,
    RecommendationListResponse,
    ModelStatusResponse,
    ModelMetricsResponse,
    RiskLevel,
    EstimationSource,
)
from app.schemas.mitigation import (
    MitigationActionPreset,
    MultiScenarioSimulationRequest,
    MultiScenarioSimulationResponse,
    MitigationReportRequest,
    MitigationReportResponse,
)
from app.schemas.user import UserPrincipal, UserRole
from app.api.deps import get_current_user
from app.services.firebase_service import get_firestore_client
from app.services.incident_service import get_incident_by_id
from app.services.risk_engine import (
    assess_risk,
    estimate_incident_factors,
    calculate_factor_contributions,
    classify_risk_score,
)
from app.services.recommendation_service import generate_recommendations
from app.services.simulation_service import (
    execute_simulation,
    verify_incident_simulation_access,
)
from app.services.mitigation_service import (
    get_mitigation_presets,
    is_supported_category,
    SUPPORTED_CATEGORIES,
    simulate_multi_scenarios,
    generate_mitigation_plan_brief,
    generate_mitigation_brief_markdown,
)
from app.ml.inference import default_inference_service

logger = logging.getLogger("nexus.api.ai")

router = APIRouter()


@router.post(
    "/assess",
    response_model=RiskAssessmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Compute Authoritative Risk Assessment",
    description=(
        "Calculates deterministic risk score (R = 0.4H + 0.3E + 0.2V + 0.1D), decomposes "
        "factor point contributions, generates plain-language explainability narrative, "
        "attaches optional advisory Scikit-learn inference, and persists the assessment to Firestore."
    ),
)
@rate_limit(settings.RATE_LIMIT_AI)
def compute_risk_assessment(
    payload: RiskAssessmentCreate,
    current_user: UserPrincipal = Depends(get_current_user),
    request: Request = None,
) -> RiskAssessmentResponse:
    """
    Execute authoritative risk assessment under the authenticated user.
    Enforces ownership verification if linked to an existing incident.
    """
    incident_title = None
    incident_desc = None
    incident_cat = None

    # 1. Incident access & ownership check if incident_id is supplied
    if payload.incident_id:
        # get_incident_by_id enforces:
        # - 404 if incident does not exist
        # - 403 if community user attempts to access another user's incident
        # - Full access for ANALYST and ADMIN
        incident = get_incident_by_id(payload.incident_id, current_user=current_user)
        incident_title = incident.title
        incident_desc = incident.description
        incident_cat = incident.category.value

    # 2. Compute authoritative deterministic assessment
    assessment = assess_risk(
        factors=payload.factors,
        incident_id=payload.incident_id,
        assessed_by=current_user.uid,
        include_ml_advisory=payload.include_ml_advisory,
        title=incident_title,
        description=incident_desc,
        category=incident_cat,
    )

    # 3. Persist assessment to Cloud Firestore collection 'risk_assessments'
    db = get_firestore_client()
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Cloud Firestore client is unavailable. Cannot persist risk assessment.",
        )

    doc_data: Dict[str, Any] = {
        "id": assessment.id,
        "incident_id": assessment.incident_id,
        "risk_score": assessment.risk_score,
        "risk_level": assessment.risk_level.value,
        "factors": assessment.factors.model_dump(),
        "contributions": assessment.contributions.model_dump(),
        "formula": assessment.formula,
        "methodology": assessment.methodology,
        "explanation": assessment.explanation,
        "ml_advisory": assessment.ml_advisory,
        "model_status": assessment.model_status.value,
        "model_version": assessment.model_version,
        "assessed_by": current_user.uid,
        "created_at": assessment.created_at,
        "server_timestamp": firestore.SERVER_TIMESTAMP,
    }

    try:
        db.collection("risk_assessments").document(assessment.id).set(doc_data)
        logger.info(
            f"Persisted risk assessment '{assessment.id}' for incident '{assessment.incident_id}' by UID '{current_user.uid}'"
        )
    except Exception as exc:
        logger.error(f"Failed to persist risk assessment to Firestore: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Firestore assessment write failed: {exc}",
        ) from exc

    return assessment


@router.get(
    "/assessments/{assessment_id}",
    response_model=RiskAssessmentResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve Saved Risk Assessment",
    description="Retrieves a persisted risk assessment from Cloud Firestore with strict ownership and RBAC validation.",
)
@rate_limit(settings.RATE_LIMIT_DEFAULT)
def get_saved_assessment(
    assessment_id: str,
    current_user: UserPrincipal = Depends(get_current_user),
    request: Request = None,
) -> RiskAssessmentResponse:
    """
    Retrieve saved risk assessment.
    COMMUNITY_USER: Can only view assessments they authored.
    ANALYST / ADMIN: Can view any assessment in the platform.
    """
    db = get_firestore_client()
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Cloud Firestore client is unavailable.",
        )

    try:
        doc = db.collection("risk_assessments").document(assessment_id).get()
    except Exception as exc:
        logger.error(f"Failed to fetch assessment '{assessment_id}' from Firestore: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Firestore assessment query failed: {exc}",
        ) from exc

    if not doc.exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Risk assessment with ID '{assessment_id}' not found.",
        )

    data = doc.to_dict() or {}

    # Authorization Check
    creator_uid = data.get("assessed_by")
    if current_user.role == UserRole.COMMUNITY_USER and creator_uid != current_user.uid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Community users are restricted to accessing their own risk assessments.",
        )

    # Exclude server_timestamp before parsing response schema
    data.pop("server_timestamp", None)
    return RiskAssessmentResponse(**data)


@router.post(
    "/simulate",
    response_model=SimulationResponse,
    status_code=status.HTTP_200_OK,
    summary="Run What-If Scenario Simulation",
    description=(
        "Executes a non-destructive what-if scenario simulation comparing baseline factors "
        "with simulated post-intervention factors. Computes Delta R, classification transitions, "
        "and primary mitigation drivers without mutating live incident records."
    ),
)
@rate_limit(settings.RATE_LIMIT_AI)
def run_scenario_simulation(
    payload: SimulationRequest,
    current_user: UserPrincipal = Depends(get_current_user),
    request: Request = None,
) -> SimulationResponse:
    """
    Run hypothetical civic scenario simulation.
    Guaranteed non-destructive: never writes or alters Firestore documents.
    """
    incident_dict = None
    if payload.incident_id:
        incident = get_incident_by_id(payload.incident_id, current_user=current_user)
        incident_dict = incident.model_dump()

    return execute_simulation(
        request=payload,
        current_user=current_user,
        incident_data=incident_dict,
    )


@router.get(
    "/recommendations/{incident_id}",
    response_model=RecommendationListResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate Context-Aware Civic Recommendations",
    description=(
        "Generates deterministic, prioritized civic recommendations tailored to incident category, "
        "authoritative risk level, and primary mathematical formula drivers. Every item strictly has status PROPOSED."
    ),
)
@rate_limit(settings.RATE_LIMIT_AI)
def get_incident_recommendations(
    incident_id: str,
    current_user: UserPrincipal = Depends(get_current_user),
    request: Request = None,
) -> RecommendationListResponse:
    """
    Retrieve prioritized, category-specific recommendations for an incident report.
    Enforces ownership: community users can only access recommendations for their own reports.
    """
    # 1. Fetch incident with ownership validation
    incident = get_incident_by_id(incident_id, current_user=current_user)

    # 2. Derive factors (documented civic estimate if no custom sensor inputs exist)
    factors = estimate_incident_factors(incident.model_dump())

    # 3. Calculate score & decompose drivers
    score, contributions = calculate_factor_contributions(factors)
    level = classify_risk_score(score)

    # 4. Generate context-aware recommendations
    return generate_recommendations(
        risk_score=score,
        risk_level=level,
        category=incident.category.value,
        primary_driver=contributions.primary_driver,
        secondary_driver=contributions.secondary_driver,
        incident_id=incident.id,
    )


@router.get(
    "/model/status",
    response_model=ModelStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Model Status & Transparency Disclosures",
    description="Retrieves machine learning model readiness status, candidate evaluation history, and synthetic data disclosures.",
)
@rate_limit(settings.RATE_LIMIT_DEFAULT)
def get_model_readiness_status(
    current_user: UserPrincipal = Depends(get_current_user),
    request: Request = None,
) -> ModelStatusResponse:
    """Return model status (DEMO or INSUFFICIENT_DATA) and operational limitations."""
    return default_inference_service.get_model_status()


@router.get(
    "/model/metrics",
    response_model=ModelMetricsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Model Evaluation Metrics",
    description="Retrieves benchmark accuracy, F1, precision, and recall with explicit synthetic demonstration disclosures.",
)
@rate_limit(settings.RATE_LIMIT_DEFAULT)
def get_model_evaluation_metrics(
    current_user: UserPrincipal = Depends(get_current_user),
    request: Request = None,
) -> ModelMetricsResponse:
    """Return synthetic benchmark test metrics and transparency disclosures."""
    return default_inference_service.get_model_metrics()


# ============================================================================
# Milestone 5: Municipal Mitigation Presets, Multi-Simulation & Brief Endpoints
# ============================================================================

@router.get(
    "/mitigation/presets/{category}",
    response_model=List[MitigationActionPreset],
    status_code=status.HTTP_200_OK,
    summary="Get Category Mitigation Action Presets",
    description=(
        "Retrieves validated municipal mitigation action presets for the specified incident category. "
        "Supports all six civic hazard taxonomies (waterlogging, road_damage, electrical_hazard, "
        "waste_management, extreme_heat, general_safety). Returns 400 for unsupported categories."
    ),
)
@rate_limit(settings.RATE_LIMIT_DEFAULT)
def get_category_mitigation_presets(
    category: str,
    current_user: UserPrincipal = Depends(get_current_user),
    request: Request = None,
) -> List[MitigationActionPreset]:
    """
    Retrieve validated municipal mitigation presets for an incident category.
    Includes indicative cost, crew size, deployment hours, and engineering assumptions.
    """
    if not is_supported_category(category):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Unsupported incident category: '{category}'. "
                f"Supported categories are: {', '.join(SUPPORTED_CATEGORIES)}."
            ),
        )
    return get_mitigation_presets(category)


@router.post(
    "/simulate/multi",
    response_model=MultiScenarioSimulationResponse,
    status_code=status.HTTP_200_OK,
    summary="Run Multi-Scenario What-If Mitigation Simulation",
    description=(
        "Simulates 2 to 5 competing municipal mitigation scenarios against one common baseline. "
        "Calculates baseline and simulated scores using deterministic formula R = 0.4H + 0.3E + 0.2V + 0.1D, "
        "computes absolute and relative delta, tracks parameter shifts, safe cost-effectiveness (points per ₹1 Lakh), "
        "and multi-criteria rankings without mutating live incident records."
    ),
)
@rate_limit(settings.RATE_LIMIT_AI)
def run_multi_scenario_simulation(
    payload: MultiScenarioSimulationRequest,
    current_user: UserPrincipal = Depends(get_current_user),
    request: Request = None,
) -> MultiScenarioSimulationResponse:
    """
    Execute non-destructive comparative simulation evaluating 2 to 5 scenarios against one baseline.
    Enforces authorization:
    - If incident_id is linked: Community users can only simulate on incidents they reported.
    - If no incident_id is linked (standalone municipal planning): Requires ANALYST or ADMIN role.
    """
    incident_dict = None
    if payload.incident_id:
        incident = get_incident_by_id(payload.incident_id, current_user=current_user)
        incident_dict = incident.model_dump()
        verify_incident_simulation_access(incident_dict, current_user)
    elif current_user.role == UserRole.COMMUNITY_USER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Access denied: Standalone municipal planning simulations require an ANALYST or ADMIN role. "
                "Community users may only simulate mitigation for incidents they personally reported."
            ),
        )

    return simulate_multi_scenarios(
        request=payload,
        incident_data=incident_dict,
    )


@router.post(
    "/mitigation/report",
    response_model=MitigationReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate Municipal Mitigation Plan Brief",
    description=(
        "Synthesizes an executive-level municipal mitigation brief from validated multi-scenario results. "
        "Includes baseline context, comparative matrix, transparent assumption citations, resource footprints, "
        "and prioritized action line items with status PROPOSED. Formats full report in Markdown."
    ),
)
@rate_limit("10/minute")
def generate_municipal_mitigation_report(
    payload: MitigationReportRequest,
    current_user: UserPrincipal = Depends(get_current_user),
    request: Request = None,
) -> MitigationReportResponse:
    """
    Generate structured mitigation brief and formatted Markdown report.
    Enforces authorization:
    - If incident_id is linked: Community users can only generate briefs for incidents they reported.
    - If no incident_id is linked: Requires ANALYST or ADMIN role.
    """
    incident_title = payload.incident_title
    incident_location = payload.location
    incident_category = payload.category

    if payload.incident_id:
        incident = get_incident_by_id(payload.incident_id, current_user=current_user)
        incident_dict = incident.model_dump()
        verify_incident_simulation_access(incident_dict, current_user)
        if not incident_title:
            incident_title = incident.title
        if not incident_location:
            incident_location = incident.location
        if not incident_category:
            incident_category = incident.category.value
    elif current_user.role == UserRole.COMMUNITY_USER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Access denied: Generating standalone municipal mitigation briefs requires an ANALYST or ADMIN role. "
                "Community users may only generate briefs for incidents they personally reported."
            ),
        )

    brief = generate_mitigation_plan_brief(
        simulation_response=payload.simulation_response,
        preferred_scenario_id=payload.preferred_scenario_id,
        incident_title=incident_title,
        category=incident_category,
        location=incident_location,
    )

    markdown_text = generate_mitigation_brief_markdown(
        brief=brief,
        simulation_response=payload.simulation_response,
    )

    if payload.analyst_notes:
        markdown_text += f"\n## 6. Administrative / Field Notes\n\n{payload.analyst_notes}\n"

    return MitigationReportResponse(
        brief=brief,
        markdown_content=markdown_text,
        status="PROPOSED",
        generated_by=current_user.uid,
    )

