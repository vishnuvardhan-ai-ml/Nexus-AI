/**
 * NEXUS AI - Platform Type Definitions
 */

export type UserRole = 'COMMUNITY_USER' | 'ANALYST' | 'ADMIN';

export type IncidentCategory =
  | 'waterlogging'
  | 'road_damage'
  | 'electrical_hazard'
  | 'waste_management'
  | 'extreme_heat';

export type IncidentSeverity = 'LOW' | 'MEDIUM' | 'HIGH';

export type RiskLevel = IncidentSeverity;

export type IncidentStatus = 'reported' | 'investigating' | 'mitigating' | 'resolved';

export interface HealthSubsystems {
  classifier: string;
  risk_engine: string;
  database: string;
}

export interface SystemHealthResponse {
  status: 'healthy' | 'degraded' | 'down';
  service: string;
  version: string;
  timestamp: string;
  environment: string;
  subsystems: HealthSubsystems;
}

export interface UserPrincipal {
  uid: string;
  email: string;
  role: UserRole;
  claims?: Record<string, unknown>;
}

export interface UserProfile {
  uid: string;
  email: string;
  display_name?: string | null;
  role: UserRole;
  created_at: string;
  updated_at?: string | null;
}

export interface IncidentCreateInput {
  title: string;
  description: string;
  category: IncidentCategory;
  severity: IncidentSeverity;
  location: string;
  latitude?: number | null;
  longitude?: number | null;
  image_url?: string | null;
}

export interface Incident {
  id: string;
  title: string;
  description: string;
  category: IncidentCategory;
  severity: IncidentSeverity;
  location: string;
  latitude?: number | null;
  longitude?: number | null;
  image_url?: string | null;
  status: IncidentStatus;
  reported_by: string;
  reporter_email: string;
  created_at: string;
  updated_at: string;
}

export interface IncidentListResponse {
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  items: Incident[];
}

export interface IncidentStatsResponse {
  total_incidents: number;
  active_incidents: number;
  resolved_incidents: number;
  high_severity_count: number;
  medium_severity_count: number;
  low_severity_count: number;
  category_counts: Record<string, number>;
  mean_risk_score: number;
}

// ============================================================================
// Milestone 3: Risk Intelligence, ML Telemetry, Explainability & Simulation
// ============================================================================

export type EstimationSource =
  | 'USER_DIRECT'
  | 'DOCUMENTED_ESTIMATE'
  | 'SIMULATION_OVERRIDE';

export type ModelStatus = 'DEMO' | 'INSUFFICIENT_DATA' | 'TRAINED';

export type FactorInfluence = 'AMPLIFYING' | 'DAMPENING' | 'NEUTRAL';

export type RecommendationPriority = 'IMMEDIATE' | 'HIGH' | 'MEDIUM' | 'MONITOR';

export interface RiskFactorInput {
  hazard_severity: number;
  exposure: number;
  vulnerability: number;
  duration: number;
  source?: EstimationSource;
  source_notes?: string | null;
}

export interface FactorContribution {
  factor_name: string;
  factor_label: string;
  input_value: number;
  weight: number;
  weighted_points: number;
  contribution_percentage: number;
  influence: FactorInfluence;
  explanation: string;
}

export interface FactorContributions {
  hazard: FactorContribution;
  exposure: FactorContribution;
  vulnerability: FactorContribution;
  duration: FactorContribution;
  primary_driver: string;
  secondary_driver?: string | null;
}

export interface AdvisoryMLOutput {
  ml_predicted_level: string;
  confidence: number;
  class_probabilities?: Record<string, number>;
  model_status: string;
  model_version: string;
  primary_algorithm?: string;
  is_advisory_only: boolean;
  disclaimer: string;
}

export interface RiskAssessmentCreateInput {
  incident_id?: string | null;
  factors: RiskFactorInput;
  include_ml_advisory?: boolean;
}

export interface RiskAssessmentResponse {
  id: string;
  incident_id?: string | null;
  risk_score: number;
  risk_level: RiskLevel;
  factors: RiskFactorInput;
  contributions: FactorContributions;
  formula: string;
  methodology: string;
  explanation: string;
  ml_advisory?: AdvisoryMLOutput | null;
  model_status: ModelStatus;
  model_version: string;
  assessed_by: string;
  created_at: string;
}

export interface SimulationRequest {
  scenario_name: string;
  incident_id?: string | null;
  baseline_factors: RiskFactorInput;
  simulated_factors: RiskFactorInput;
  intervention_notes?: string | null;
}

export interface SimulationResponse {
  id: string;
  scenario_name: string;
  incident_id?: string | null;
  baseline_score: number;
  baseline_level: RiskLevel;
  simulated_score: number;
  simulated_level: RiskLevel;
  score_difference: number;
  level_changed: boolean;
  primary_mitigation_driver: string;
  factors_responsible: string[];
  is_simulation: boolean;
  intervention_notes?: string | null;
  simulated_by: string;
  created_at: string;
}

export interface RecommendationItem {
  id: string;
  action: string;
  priority: RecommendationPriority;
  rationale: string;
  suggested_next_step: string;
  status: 'PROPOSED';
  responsible_department?: string | null;
}

export interface RecommendationListResponse {
  incident_id?: string | null;
  risk_score: number;
  risk_level: RiskLevel;
  category: string;
  dominant_factor: string;
  recommendations: RecommendationItem[];
  generated_at: string;
}

export interface ModelStatusResponse {
  status: ModelStatus;
  model_version: string;
  primary_algorithm: string;
  candidate_algorithms_evaluated: string[];
  training_sample_count: number;
  data_source_disclosure: string;
  is_probabilistic_forecast: boolean;
  disclaimer: string;
  last_evaluated_at: string;
}

export interface ModelMetricsResponse {
  model_version: string;
  model_status: ModelStatus;
  benchmark_dataset: string;
  sample_count: number;
  train_split_count: number;
  test_split_count: number;
  cross_validation_folds: number;
  accuracy: number;
  macro_f1: number;
  precision_macro: number;
  recall_macro: number;
  cv_mean_score: number;
  cv_std_score: number;
  metric_disclosure: string;
}

// ============================================================================
// Milestone 4: Geospatial Intelligence, GeoJSON (RFC 7946) & Risk Mapping
// ============================================================================

export type CoordinatePrecision = 'EXACT' | 'GENERALIZED';

export type AssessmentStatus = 'ASSESSED' | 'NOT_ASSESSED';

export interface GeoPointGeometry {
  type: 'Point';
  /**
   * WGS84 coordinate pair in strictly [longitude, latitude] order per RFC 7946.
   */
  coordinates: [number, number];
}

export interface GeoIncidentProperties {
  id: string;
  title: string;
  category: IncidentCategory;
  severity: IncidentSeverity;
  status: IncidentStatus;
  location_name: string;
  created_at: string;

  // Authoritative Risk Assessment Join (null when unassessed)
  assessment_status: AssessmentStatus;
  risk_score: number | null;
  risk_level: RiskLevel | null;
  assessment_id: string | null;
  assessed_at: string | null;
  primary_driver: string | null;

  // Privacy & Ownership Metadata
  precision: CoordinatePrecision;
  is_own_incident: boolean;
}

export interface GeoIncidentFeature {
  type: 'Feature';
  id: string;
  geometry: GeoPointGeometry;
  properties: GeoIncidentProperties;
}

export interface UnplottedIncidentSummary {
  id: string;
  title: string;
  category: IncidentCategory;
  severity: IncidentSeverity;
  status: IncidentStatus;
  location_name: string;
  created_at: string;
  assessment_status: AssessmentStatus;
  risk_score: number | null;
  risk_level: RiskLevel | null;
  reason: string;
}

export interface BoundingBox {
  min_lat: number;
  min_lng: number;
  max_lat: number;
  max_lng: number;
}

export interface GeoIncidentCollectionResponse {
  type: 'FeatureCollection';
  features: GeoIncidentFeature[];
  total_matched: number;
  geocoded_count: number;
  unplotted_count: number;
  unplotted_items: UnplottedIncidentSummary[];
  bbox: [number, number, number, number] | null; // [min_lng, min_lat, max_lng, max_lat]
  center_coordinates: [number, number] | null; // [lng, lat]
  limit_applied: number;
  has_more: boolean;
}

export interface GeoSummaryResponse {
  total_incidents: number;
  geocoded_count: number;
  unplotted_count: number;
  coverage_percentage: number;
  high_risk_count: number;
  medium_risk_count: number;
  low_risk_count: number;
  not_assessed_count: number;
  category_distribution: Record<string, number>;
  active_incidents_count: number;
}

export interface GeoClusterItem {
  cluster_id: string;
  centroid: [number, number]; // [lng, lat]
  count: number;
  high_risk_count: number;
  medium_risk_count: number;
  low_risk_count: number;
  not_assessed_count: number;
  dominant_category: string | null;
  is_exploratory: boolean;
}

export interface GeoIncidentQueryParams {
  category?: IncidentCategory;
  risk_level?: RiskLevel;
  status?: IncidentStatus;
  min_lat?: number;
  min_lng?: number;
  max_lat?: number;
  max_lng?: number;
  only_own?: boolean;
  limit?: number;
}

// ============================================================================
// Milestone 5: What-If Simulation Engine & Municipal Mitigation Planning
// ============================================================================

export type MitigationCategory =
  | 'waterlogging'
  | 'road_damage'
  | 'electrical_hazard'
  | 'waste_management'
  | 'extreme_heat'
  | 'general_safety';

export type FeasibilityRating = 'HIGH' | 'MODERATE' | 'COMPLEX';

export type CostConfidence =
  | 'DOCUMENTED_BENCHMARK'
  | 'USER_SPECIFIED'
  | 'UNVERIFIED_ASSUMPTION';

/**
 * Indicative planning resource estimate footprint for a mitigation intervention.
 * Strictly labeled as an indicative estimate, never a certified tender or budget sanction.
 */
export interface ResourceEstimate {
  estimated_cost_min?: number | null;
  estimated_cost_max?: number | null;
  currency?: string;
  currency_symbol?: string;
  cost_confidence?: CostConfidence;
  cost_notes?: string | null;
  estimated_manpower?: number | null;
  manpower_notes?: string | null;
  estimated_duration_hours?: number | null;
  duration_notes?: string | null;
  is_estimate?: boolean;
  disclaimer?: string;
  mean_cost?: number | null;
}

/**
 * Cataloged municipal mitigation action preset with transparent domain parameter deltas.
 */
export interface MitigationActionPreset {
  id: string;
  category: string;
  title: string;
  description: string;
  mechanism: string;
  target_factor_deltas: Record<string, number>;
  resource_estimate: ResourceEstimate;
  feasibility: FeasibilityRating;
  assumptions: string;
  responsible_department: string;
  status: 'PROPOSED';
}

/**
 * Detailed parameter-by-parameter tracking of which factor changed and why.
 */
export interface ParameterShiftAttribution {
  factor: string;
  factor_label: string;
  baseline_value: number;
  simulated_value: number;
  delta_value: number;
  formula_weight: number;
  risk_points_impact: number;
  rationale: string;
}

/**
 * Configuration for an individual scenario in a multi-scenario simulation.
 */
export interface MitigationScenarioInput {
  scenario_id: string;
  scenario_name: string;
  description?: string | null;
  simulated_factors: RiskFactorInput;
  action_ids?: string[];
  custom_resource_override?: ResourceEstimate | null;
  assumptions?: string | null;
}

/**
 * Complete evaluation of one scenario against the common baseline.
 */
export interface ScenarioEvaluation {
  scenario_id: string;
  scenario_name: string;
  description?: string | null;
  baseline_score: number;
  baseline_level: RiskLevel;
  simulated_score: number;
  simulated_level: RiskLevel;
  absolute_risk_reduction: number;
  relative_risk_reduction_pct: number;
  level_changed: boolean;
  level_transition?: string | null;
  primary_mitigation_driver: string;
  parameter_shifts: ParameterShiftAttribution[];
  resource_estimate: ResourceEstimate;
  cost_effectiveness_per_lakh?: number | null;
  cost_effectiveness_label: string;
  feasibility: FeasibilityRating;
  is_simulation: boolean;
  status: 'PROPOSED';
  provenance_notes: string;
}

/**
 * Single ranked scenario entry under a specific optimization dimension.
 */
export interface ScenarioRankItem {
  rank: number;
  scenario_id: string;
  scenario_name: string;
  metric_value?: number | null;
  metric_label: string;
  rationale: string;
}

/**
 * Comparative multi-criteria rankings across three distinct decision criteria.
 */
export interface MultiScenarioRankings {
  by_impact: ScenarioRankItem[];
  by_cost_efficiency: ScenarioRankItem[];
  by_deployment_speed: ScenarioRankItem[];
  best_balanced?: ScenarioRankItem | null;
}

/**
 * Request to evaluate 2 to 5 competing mitigation scenarios against one common baseline.
 */
export interface MultiScenarioSimulationRequest {
  incident_id?: string | null;
  incident_category?: string | null;
  baseline_factors: RiskFactorInput;
  scenarios: MitigationScenarioInput[];
  currency?: string;
  currency_symbol?: string;
  cost_unit_lakhs?: number;
  include_diagnostic?: boolean;
}

/**
 * Comparative multi-scenario simulation output.
 */
export interface MultiScenarioSimulationResponse {
  simulation_id: string;
  incident_id?: string | null;
  is_diagnostic_record: boolean;
  diagnostic_notice?: string | null;
  baseline_score: number;
  baseline_level: RiskLevel;
  baseline_factors: RiskFactorInput;
  scenarios_evaluated_count: number;
  evaluations: ScenarioEvaluation[];
  rankings: MultiScenarioRankings;
  currency: string;
  currency_symbol: string;
  formula: string;
  methodology: string;
  planning_disclaimer: string;
  created_at: string;
}

/**
 * Action line item in structured mitigation brief.
 */
export interface MitigationBriefAction {
  action_id: string;
  title: string;
  department: string;
  priority: RecommendationPriority;
  status: 'PROPOSED';
}

/**
 * Structured executive mitigation brief suitable for export to Markdown or JSON.
 */
export interface MitigationPlanBrief {
  brief_id: string;
  incident_id?: string | null;
  incident_title?: string | null;
  category: string;
  location?: string | null;
  is_diagnostic: boolean;
  baseline_score: number;
  baseline_level: RiskLevel;
  recommended_scenario_id: string;
  recommended_scenario_name: string;
  projected_score: number;
  projected_level: RiskLevel;
  projected_risk_reduction: number;
  estimated_cost_range: string;
  estimated_manpower: string;
  estimated_duration: string;
  proposed_actions: MitigationBriefAction[];
  assumptions_and_sources: string[];
  disclaimers: string[];
  generated_at: string;
}

/**
 * Request to synthesize an executive municipal mitigation brief from multi-scenario simulation results.
 */
export interface MitigationReportRequest {
  incident_id?: string | null;
  simulation_response: MultiScenarioSimulationResponse;
  preferred_scenario_id?: string | null;
  incident_title?: string | null;
  category?: string | null;
  location?: string | null;
  analyst_notes?: string | null;
}

/**
 * Structured municipal mitigation brief and formatted Markdown report.
 */
export interface MitigationReportResponse {
  brief: MitigationPlanBrief;
  markdown_content: string;
  status: 'PROPOSED';
  generated_by: string;
  planning_disclaimer: string;
}


