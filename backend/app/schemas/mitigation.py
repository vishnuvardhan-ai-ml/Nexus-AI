"""
NEXUS AI Municipal Mitigation & Multi-Scenario Simulation Schemas.

Defines strongly-typed Pydantic schemas for:
- Category-specific municipal mitigation action presets.
- Resource estimations (cost in INR/configurable currency, manpower, duration).
- Multi-scenario comparative simulation requests and evaluations (2-5 scenarios).
- Multi-criteria scenario prioritization (Impact, Cost Efficiency, Deployment Speed).
- Explainable municipal mitigation brief structures.
"""
from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, field_validator

from app.schemas.risk import (
    RiskLevel,
    RiskFactorInput,
    RecommendationPriority,
)


class MitigationCategory(str, Enum):
    WATERLOGGING = "waterlogging"
    ROAD_DAMAGE = "road_damage"
    ELECTRICAL_HAZARD = "electrical_hazard"
    WASTE_MANAGEMENT = "waste_management"
    EXTREME_HEAT = "extreme_heat"
    GENERAL_SAFETY = "general_safety"


class FeasibilityRating(str, Enum):
    HIGH = "HIGH"          # Readily executable with standard municipal equipment and ward crew
    MODERATE = "MODERATE"  # Requires inter-agency coordination or specialized machinery
    COMPLEX = "COMPLEX"    # Capital-intensive, requires major civil works or site permits


class CostConfidence(str, Enum):
    DOCUMENTED_BENCHMARK = "DOCUMENTED_BENCHMARK"  # Based on standard municipal works schedule heuristics
    USER_SPECIFIED = "USER_SPECIFIED"              # Manually entered by municipal planner/analyst
    UNVERIFIED_ASSUMPTION = "UNVERIFIED_ASSUMPTION"# Working assumption pending site procurement audit


class ResourceEstimate(BaseModel):
    """
    Transparent resource estimation footprint for a mitigation intervention.
    Explicitly labeled as an indicative planning estimate, never a certified tender or budget sanction.
    """
    estimated_cost_min: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Minimum projected intervention cost"
    )
    estimated_cost_max: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Maximum projected intervention cost"
    )
    currency: str = Field(default="INR", description="Three-letter ISO currency code (Default: INR)")
    currency_symbol: str = Field(default="₹", description="Currency symbol for formatted display (Default: ₹)")
    cost_confidence: CostConfidence = Field(
        default=CostConfidence.DOCUMENTED_BENCHMARK,
        description="Confidence classification of cost parameter"
    )
    cost_notes: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Documented basis of cost range (e.g. municipal standard rate benchmark)"
    )
    estimated_manpower: Optional[int] = Field(
        default=None,
        ge=0,
        description="Estimated personnel / crew size required for execution"
    )
    manpower_notes: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Crew composition description (e.g. 1 engineer, 3 machine operators)"
    )
    estimated_duration_hours: Optional[float] = Field(
        default=None,
        ge=0.0,
        description="Estimated operational deployment lead-time / duration in hours"
    )
    duration_notes: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Timeframe notes (e.g. initial setup 1 hour, continuous operation 4 hours)"
    )
    is_estimate: bool = Field(
        default=True,
        description="Mandatory integrity disclosure: strictly an estimate, not a verified expenditure"
    )
    disclaimer: str = Field(
        default=(
            "Estimates are indicative planning benchmarks for decision support. "
            "Actual expenditure and schedules are subject to formal municipal procurement and field dispatch."
        ),
        description="Standard municipal disclaimer"
    )

    @property
    def mean_cost(self) -> Optional[float]:
        """Compute the arithmetic mean of cost bounds if at least one bound is provided."""
        if self.estimated_cost_min is not None and self.estimated_cost_max is not None:
            return round((self.estimated_cost_min + self.estimated_cost_max) / 2.0, 2)
        if self.estimated_cost_min is not None:
            return float(self.estimated_cost_min)
        if self.estimated_cost_max is not None:
            return float(self.estimated_cost_max)
        return None


class MitigationActionPreset(BaseModel):
    """
    Cataloged municipal mitigation action preset with transparent domain parameter deltas.
    """
    id: str = Field(..., description="Unique technical identifier of the action preset")
    category: str = Field(..., description="Target incident category (e.g. waterlogging)")
    title: str = Field(..., min_length=3, max_length=150, description="Action title")
    description: str = Field(..., description="Detailed operational description")
    mechanism: str = Field(..., description="Physical or civic mechanism driving risk attenuation")
    target_factor_deltas: Dict[str, float] = Field(
        ...,
        description="Expected parameter shifts on H, E, V, D (negative values indicate reduction)"
    )
    resource_estimate: ResourceEstimate = Field(..., description="Estimated cost, crew, and duration")
    feasibility: FeasibilityRating = Field(default=FeasibilityRating.HIGH, description="Implementation feasibility")
    assumptions: str = Field(..., description="Explicit field assumptions required for effectiveness")
    responsible_department: str = Field(..., description="Designated municipal department")
    status: str = Field(default="PROPOSED", description="Always PROPOSED; never claimed completed")


class ParameterShiftAttribution(BaseModel):
    """
    Detailed parameter-by-parameter tracking of which factor changed and why.
    """
    factor: str = Field(..., description="Factor key: hazard_severity, exposure, vulnerability, duration")
    factor_label: str = Field(..., description="Human-readable label (e.g. Hazard Severity (H))")
    baseline_value: float = Field(..., description="Baseline parameter value (0-100)")
    simulated_value: float = Field(..., description="Simulated parameter value (0-100)")
    delta_value: float = Field(..., description="simulated_value - baseline_value")
    formula_weight: float = Field(..., description="Multiplier weight in deterministic equation")
    risk_points_impact: float = Field(..., description="Weighted point impact (delta_value * formula_weight)")
    rationale: str = Field(..., description="Explanation of why this parameter shifted under the scenario")


class MitigationScenarioInput(BaseModel):
    """
    Configuration for an individual scenario in a multi-scenario simulation.
    """
    scenario_id: str = Field(..., min_length=1, max_length=50, description="Unique scenario slug or id")
    scenario_name: str = Field(..., min_length=2, max_length=150, description="Human-readable scenario title")
    description: Optional[str] = Field(default=None, max_length=1000, description="Optional scenario overview")
    simulated_factors: RiskFactorInput = Field(..., description="Simulated H, E, V, D parameters")
    action_ids: List[str] = Field(
        default_factory=list,
        description="Optional IDs of action presets bundled into this scenario"
    )
    custom_resource_override: Optional[ResourceEstimate] = Field(
        default=None,
        description="Optional custom resource estimate overriding catalog default"
    )
    assumptions: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Explicit user or engineering assumptions for this scenario"
    )


class ScenarioEvaluation(BaseModel):
    """
    Complete evaluation of one scenario against the common baseline.
    """
    scenario_id: str
    scenario_name: str
    description: Optional[str] = None
    baseline_score: float = Field(..., ge=0.0, le=100.0)
    baseline_level: RiskLevel
    simulated_score: float = Field(..., ge=0.0, le=100.0)
    simulated_level: RiskLevel
    absolute_risk_reduction: float = Field(
        ...,
        description="R_base - R_sim (positive indicates risk reduction)"
    )
    relative_risk_reduction_pct: float = Field(
        ...,
        description="((R_base - R_sim) / R_base) * 100% (safely handles R_base=0)"
    )
    level_changed: bool = Field(..., description="Whether risk classification band changed")
    level_transition: Optional[str] = Field(
        default=None,
        description="e.g. 'HIGH -> MEDIUM' or 'No change'"
    )
    primary_mitigation_driver: str = Field(
        ...,
        description="Factor shift contributing the largest risk reduction"
    )
    parameter_shifts: List[ParameterShiftAttribution] = Field(
        default_factory=list,
        description="Detailed shift breakdown for each factor"
    )
    resource_estimate: ResourceEstimate = Field(
        ...,
        description="Estimated cost, crew size, and deployment duration"
    )
    cost_effectiveness_per_lakh: Optional[float] = Field(
        default=None,
        description="Risk points reduced per ₹1 Lakh (₹1,00,000 INR). None if cost is 0 or missing."
    )
    cost_effectiveness_label: str = Field(
        ...,
        description="Human-readable efficiency index description (e.g. '12.4 pts / ₹1 Lakh')"
    )
    feasibility: FeasibilityRating = Field(default=FeasibilityRating.HIGH)
    is_simulation: bool = Field(default=True, description="Strictly flagged as simulation")
    status: str = Field(default="PROPOSED", description="Strictly PROPOSED")
    provenance_notes: str = Field(..., description="Audit trace of data source and inputs evaluated")


class ScenarioRankItem(BaseModel):
    """Single ranked scenario entry under a specific optimization dimension."""
    rank: int = Field(..., ge=1, description="Rank position (1 = Best)")
    scenario_id: str
    scenario_name: str
    metric_value: Optional[float] = None
    metric_label: str
    rationale: str


class MultiScenarioRankings(BaseModel):
    """
    Comparative multi-criteria rankings across three distinct decision criteria.
    """
    by_impact: List[ScenarioRankItem] = Field(
        ...,
        description="Ranked by highest absolute risk reduction (|Delta R|)"
    )
    by_cost_efficiency: List[ScenarioRankItem] = Field(
        ...,
        description="Ranked by risk points reduced per ₹1 Lakh"
    )
    by_deployment_speed: List[ScenarioRankItem] = Field(
        ...,
        description="Ranked by shortest deployment lead-time in hours"
    )
    best_balanced: Optional[ScenarioRankItem] = Field(
        default=None,
        description="Recommended balanced scenario weighing impact, cost, and speed"
    )


class MultiScenarioSimulationRequest(BaseModel):
    """
    Request to evaluate 2 to 5 competing mitigation scenarios against one common baseline.
    """
    incident_id: Optional[str] = Field(default=None, description="Linked incident ID in database if applicable")
    incident_category: Optional[str] = Field(default=None, description="Category for contextual action presets")
    baseline_factors: RiskFactorInput = Field(..., description="Common pre-intervention baseline factors (H, E, V, D)")
    scenarios: List[MitigationScenarioInput] = Field(
        ...,
        min_length=2,
        max_length=5,
        description="2 to 5 competing what-if mitigation scenarios"
    )
    currency: str = Field(default="INR", description="Three-letter currency code (Default: INR)")
    currency_symbol: str = Field(default="₹", description="Display currency symbol (Default: ₹)")
    cost_unit_lakhs: float = Field(default=1.0, ge=0.01, description="Benchmarking unit divisor in Lakhs (Default: 1.0 = ₹1,00,000)")
    include_diagnostic: bool = Field(
        default=False,
        description="Set true only when deliberately evaluating diagnostic/test records"
    )

    @field_validator("scenarios")
    @classmethod
    def validate_unique_scenario_ids(cls, scenarios: List[MitigationScenarioInput]) -> List[MitigationScenarioInput]:
        ids = [s.scenario_id for s in scenarios]
        if len(ids) != len(set(ids)):
            raise ValueError(f"Scenario IDs must be unique across the request. Found duplicates in: {ids}")
        return scenarios


class MultiScenarioSimulationResponse(BaseModel):
    """
    Comparative multi-scenario simulation output.
    """
    simulation_id: str
    incident_id: Optional[str] = None
    is_diagnostic_record: bool = Field(
        default=False,
        description="Whether this incident is a diagnostic verification record"
    )
    diagnostic_notice: Optional[str] = None
    baseline_score: float
    baseline_level: RiskLevel
    baseline_factors: RiskFactorInput
    scenarios_evaluated_count: int
    evaluations: List[ScenarioEvaluation]
    rankings: MultiScenarioRankings
    currency: str = "INR"
    currency_symbol: str = "₹"
    formula: str = "R = 0.4H + 0.3E + 0.2V + 0.1D"
    methodology: str
    planning_disclaimer: str
    created_at: str


class MitigationBriefAction(BaseModel):
    """Action line item in structured mitigation brief."""
    action_id: str
    title: str
    department: str
    priority: RecommendationPriority
    status: str = "PROPOSED"


class MitigationPlanBrief(BaseModel):
    """
    Structured executive mitigation brief suitable for export to Markdown or JSON.
    """
    brief_id: str
    incident_id: Optional[str] = None
    incident_title: Optional[str] = None
    category: str
    location: Optional[str] = None
    is_diagnostic: bool = False
    baseline_score: float
    baseline_level: RiskLevel
    recommended_scenario_id: str
    recommended_scenario_name: str
    projected_score: float
    projected_level: RiskLevel
    projected_risk_reduction: float
    estimated_cost_range: str
    estimated_manpower: str
    estimated_duration: str
    proposed_actions: List[MitigationBriefAction] = Field(default_factory=list)
    assumptions_and_sources: List[str] = Field(default_factory=list)
    disclaimers: List[str] = Field(default_factory=list)
    generated_at: str


class MitigationReportRequest(BaseModel):
    """
    Request to synthesize an executive municipal mitigation brief from multi-scenario simulation results.
    """
    incident_id: Optional[str] = Field(default=None, description="Linked incident ID in database if applicable")
    simulation_response: MultiScenarioSimulationResponse = Field(
        ...,
        description="Validated multi-scenario simulation output to generate brief from"
    )
    preferred_scenario_id: Optional[str] = Field(
        default=None,
        description="Optional explicit scenario ID chosen for municipal implementation. Defaults to best_balanced."
    )
    incident_title: Optional[str] = Field(
        default=None,
        max_length=200,
        description="Optional custom title for executive brief"
    )
    category: Optional[str] = Field(
        default=None,
        description="Incident taxonomy category"
    )
    location: Optional[str] = Field(
        default=None,
        max_length=250,
        description="Geographic location landmark"
    )
    analyst_notes: Optional[str] = Field(
        default=None,
        max_length=1500,
        description="Optional administrative context or operational instructions"
    )


class MitigationReportResponse(BaseModel):
    """
    Structured municipal mitigation brief and formatted Markdown report.
    """
    brief: MitigationPlanBrief
    markdown_content: str = Field(..., description="Full executive brief formatted in GitHub Flavored Markdown")
    status: str = Field(default="PROPOSED", description="Strictly PROPOSED; not an administrative commitment")
    generated_by: str = Field(..., description="UID of authenticated requesting user")
    planning_disclaimer: str = Field(
        default=(
            "All recommendations and resource figures are planning heuristics with status PROPOSED. "
            "Does not assert administrative approval, budget sanction, or contractor engagement."
        )
    )

