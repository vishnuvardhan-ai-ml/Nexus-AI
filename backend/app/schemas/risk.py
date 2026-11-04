"""
Pydantic schemas for NEXUS AI Risk Intelligence, Factor Contributions, Explainability, and Scenario Simulation.
Formula: R = 0.4H + 0.3E + 0.2V + 0.1D
"""
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, field_validator


class RiskLevel(str, Enum):
    LOW = "LOW"        # 0–29
    MEDIUM = "MEDIUM"  # 30–59
    HIGH = "HIGH"      # 60–100


class EstimationSource(str, Enum):
    USER_DIRECT = "USER_DIRECT"                    # Explicitly measured/supplied by user
    DOCUMENTED_ESTIMATE = "DOCUMENTED_ESTIMATE"    # Derived from verified civic assessment standards
    SIMULATION_OVERRIDE = "SIMULATION_OVERRIDE"    # Explicit analyst scenario modification


class ModelStatus(str, Enum):
    DEMO = "DEMO"                                  # Trained on synthetic demonstration benchmark
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"        # Insufficient real-world ground-truth data available
    TRAINED = "TRAINED"                            # Validated on legitimate production data


class FactorInfluence(str, Enum):
    AMPLIFYING = "AMPLIFYING"                      # Value > 50 increases risk above neutral baseline
    DAMPENING = "DAMPENING"                        # Value < 50 mitigates risk below neutral baseline
    NEUTRAL = "NEUTRAL"                            # Value == 50 baseline neutral


class RiskFactorInput(BaseModel):
    """
    Mandatory input values for transparent risk scoring.
    All factor values are strictly normalized between 0.0 and 100.0.
    Missing values are never silently invented; they must be provided or explicitly documented.
    """
    hazard_severity: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="H: Observed physical hazard severity or magnitude (0-100)"
    )
    exposure: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="E: Population density, critical infrastructure, or traffic exposed (0-100)"
    )
    vulnerability: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="V: Fragility, lack of drainage/backup, or vulnerable populations (0-100)"
    )
    duration: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="D: Persistence or timeframe hazard has remained unresolved (0-100)"
    )
    source: EstimationSource = Field(
        default=EstimationSource.USER_DIRECT,
        description="Explicit provenance of input values. Never silently invented."
    )
    source_notes: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Optional measurement context, sensor reading, or field observation notes."
    )


class FactorContribution(BaseModel):
    """Individual mathematical factor contribution to the composite risk score."""
    factor_name: str = Field(..., description="Technical identifier of the factor")
    factor_label: str = Field(..., description="Human-readable factor title")
    input_value: float = Field(..., description="Raw input value (0-100)")
    weight: float = Field(..., description="Formula weight multiplier")
    weighted_points: float = Field(..., description="Absolute points contributed to score (weight * input_value)")
    contribution_percentage: float = Field(..., description="Percentage of total risk score driven by this factor")
    influence: FactorInfluence = Field(..., description="Whether factor amplifies or dampens risk relative to neutral 50")
    explanation: str = Field(..., description="Plain-language assessment of factor contribution")


class FactorContributions(BaseModel):
    """Comprehensive decomposition of the weighted risk scoring formula."""
    hazard: FactorContribution
    exposure: FactorContribution
    vulnerability: FactorContribution
    duration: FactorContribution
    primary_driver: str = Field(..., description="Factor providing the largest weighted point contribution")
    secondary_driver: Optional[str] = Field(default=None, description="Factor providing the second largest contribution")


class RiskAssessmentCreate(BaseModel):
    """Request payload to assess risk for an incident or standalone civic scenario."""
    incident_id: Optional[str] = Field(default=None, description="Optional incident ID in Firestore")
    factors: RiskFactorInput = Field(..., description="Strictly validated factor inputs (H, E, V, D)")
    include_ml_advisory: bool = Field(
        default=False,
        description="Whether to execute ML classification pipeline as advisory context"
    )


class RiskAssessmentResponse(BaseModel):
    """Complete, transparent risk intelligence assessment response."""
    id: str = Field(..., description="Server-generated unique assessment ID")
    incident_id: Optional[str] = Field(default=None, description="Associated incident ID if linked")
    risk_score: float = Field(..., ge=0.0, le=100.0, description="Deterministic risk score bounded 0–100")
    risk_level: RiskLevel = Field(..., description="Deterministic category: LOW (0-29), MEDIUM (30-59), HIGH (60-100)")
    factors: RiskFactorInput = Field(..., description="Validated factor inputs evaluated")
    contributions: FactorContributions = Field(..., description="Decomposed factor point contributions")
    formula: str = Field(
        default="R = 0.4H + 0.3E + 0.2V + 0.1D",
        description="Exact deterministic scoring equation"
    )
    methodology: str = Field(
        ...,
        description="Methodological transparency disclosure"
    )
    explanation: str = Field(..., description="Human-readable explainability narrative")
    ml_advisory: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Advisory Scikit-learn model outputs clearly labeled with confidence limitations"
    )
    model_status: ModelStatus = Field(
        default=ModelStatus.DEMO,
        description="Honest operational status of ML models (DEMO, INSUFFICIENT_DATA, or TRAINED)"
    )
    model_version: str = Field(default="v1.0.0-deterministic", description="Model engine version")
    assessed_by: str = Field(..., description="UID of authenticated analyst or system reporter")
    created_at: str = Field(..., description="ISO UTC timestamp of assessment calculation")


class SimulationRequest(BaseModel):
    """What-if scenario simulation request to evaluate potential interventions non-destructively."""
    incident_id: Optional[str] = Field(default=None, description="Original incident ID for baseline reference")
    scenario_name: str = Field(
        default="What-If Intervention Scenario",
        min_length=3,
        max_length=150,
        description="Descriptive name of the simulated scenario"
    )
    baseline_factors: RiskFactorInput = Field(..., description="Pre-intervention baseline factor values")
    simulated_factors: RiskFactorInput = Field(..., description="Post-intervention simulated factor values")
    intervention_notes: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Civic intervention details (e.g., deployed 3 water pumps, traffic rerouted)"
    )


class SimulationResponse(BaseModel):
    """Non-destructive scenario simulation output comparing baseline and intervention states."""
    id: str = Field(..., description="Unique simulation identifier")
    scenario_name: str
    incident_id: Optional[str] = None
    baseline_score: float = Field(..., ge=0.0, le=100.0)
    baseline_level: RiskLevel
    simulated_score: float = Field(..., ge=0.0, le=100.0)
    simulated_level: RiskLevel
    score_difference: float = Field(..., description="ΔR = simulated_score - baseline_score (negative denotes risk reduction)")
    level_changed: bool = Field(..., description="Whether intervention crossed a risk classification boundary")
    primary_mitigation_driver: str = Field(..., description="Parameter shift responsible for largest risk reduction")
    factors_responsible: List[str] = Field(..., description="List of factor parameter shifts observed")
    is_simulation: bool = Field(
        default=True,
        description="Strictly flagged as simulation; never mutates live incident records"
    )
    intervention_notes: Optional[str] = None
    simulated_by: str
    created_at: str


class RecommendationPriority(str, Enum):
    IMMEDIATE = "IMMEDIATE"   # High risk / life safety
    HIGH = "HIGH"             # Escalating hazard / severe traffic/utility disruption
    MEDIUM = "MEDIUM"         # Preventive civic action
    MONITOR = "MONITOR"       # Low risk baseline watch


class RecommendationItem(BaseModel):
    """Context-aware actionable civic intervention recommendation."""
    id: str = Field(..., description="Unique recommendation ID")
    action: str = Field(..., description="Concise actionable operational directive")
    priority: RecommendationPriority
    rationale: str = Field(..., description="Transparent mathematical and domain justification")
    suggested_next_step: str = Field(..., description="Concrete operational step for civic response teams")
    status: str = Field(
        default="PROPOSED",
        description="Strict status indicator: intervention is PROPOSED, not completed"
    )
    responsible_department: Optional[str] = Field(
        default=None,
        description="Designated municipal department or utility agency"
    )


class RecommendationListResponse(BaseModel):
    """Collection of prioritized recommendations for an incident or assessed scenario."""
    incident_id: Optional[str] = None
    risk_score: float
    risk_level: RiskLevel
    category: str
    dominant_factor: str
    recommendations: List[RecommendationItem]
    generated_at: str


class ModelStatusResponse(BaseModel):
    """Honest transparency status regarding Scikit-learn intelligence engine readiness."""
    status: ModelStatus = Field(..., description="DEMO, INSUFFICIENT_DATA, or TRAINED")
    model_version: str
    primary_algorithm: str
    candidate_algorithms_evaluated: List[str]
    training_sample_count: int
    data_source_disclosure: str
    is_probabilistic_forecast: bool = Field(
        default=False,
        description="Always False: engine does not claim to predict disasters with certainty"
    )
    disclaimer: str
    last_evaluated_at: str


class ModelMetricsResponse(BaseModel):
    """Model evaluation metrics on benchmark test split with clear demonstration disclaimers."""
    model_version: str
    model_status: ModelStatus
    benchmark_dataset: str
    sample_count: int
    train_split_count: int
    test_split_count: int
    cross_validation_folds: int
    accuracy: float
    macro_f1: float
    precision_macro: float
    recall_macro: float
    cv_mean_score: float
    cv_std_score: float
    metric_disclosure: str
