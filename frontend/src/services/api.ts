/**
 * NEXUS AI API Client Service
 */
import {
  SystemHealthResponse,
  UserPrincipal,
  UserProfile,
  Incident,
  IncidentCreateInput,
  IncidentListResponse,
  IncidentStatsResponse,
  RiskAssessmentCreateInput,
  RiskAssessmentResponse,
  SimulationRequest,
  SimulationResponse,
  RecommendationListResponse,
  ModelStatusResponse,
  ModelMetricsResponse,
  GeoIncidentCollectionResponse,
  GeoSummaryResponse,
  GeoClusterItem,
  GeoIncidentQueryParams,
  IncidentCategory,
  MitigationActionPreset,
  MultiScenarioSimulationRequest,
  MultiScenarioSimulationResponse,
  MitigationReportRequest,
  MitigationReportResponse,
} from '../types';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
    this.name = 'ApiError';
  }
}

async function request<T>(
  endpoint: string,
  options: RequestInit = {},
  token?: string | null
): Promise<T> {
  const headers = new Headers(options.headers || {});
  headers.set('Accept', 'application/json');

  if (options.body && !(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json');
  }

  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let errorMessage = `Server error ${response.status}`;
    try {
      const errData = await response.json();
      if (errData && errData.detail) {
        errorMessage = typeof errData.detail === 'string' ? errData.detail : JSON.stringify(errData.detail);
      }
    } catch {
      // ignore json parse error on error response
    }
    throw new ApiError(response.status, errorMessage);
  }

  return response.json() as Promise<T>;
}

/**
 * Fetch verified system health and telemetry from FastAPI backend.
 */
export async function getSystemHealth(): Promise<SystemHealthResponse> {
  return request<SystemHealthResponse>('/health');
}

/**
 * Fetch authenticated user profile & verified role claims.
 */
export async function getCurrentUser(token: string): Promise<UserPrincipal> {
  return request<UserPrincipal>('/auth/me', { method: 'GET' }, token);
}

/**
 * Synchronize user profile into Firestore database.
 */
export async function syncUserProfile(
  displayName: string | null,
  token: string
): Promise<UserProfile> {
  return request<UserProfile>(
    '/auth/sync-profile',
    {
      method: 'POST',
      body: JSON.stringify({ display_name: displayName }),
    },
    token
  );
}

/**
 * Ingest new community incident report.
 */
export async function createIncident(
  incidentData: IncidentCreateInput,
  token: string
): Promise<Incident> {
  return request<Incident>(
    '/incidents',
    {
      method: 'POST',
      body: JSON.stringify(incidentData),
    },
    token
  );
}

/**
 * List community incidents with optional taxonomy filters and pagination.
 */
export async function getIncidents(
  filters: {
    category?: string;
    severity?: string;
    status?: string;
    search?: string;
    page?: number;
    page_size?: number;
  } = {},
  token?: string | null
): Promise<IncidentListResponse> {
  const params = new URLSearchParams();
  if (filters.category) params.set('category', filters.category);
  if (filters.severity) params.set('severity', filters.severity);
  if (filters.status) params.set('status', filters.status);
  if (filters.search) params.set('search', filters.search);
  if (filters.page) params.set('page', filters.page.toString());
  if (filters.page_size) params.set('page_size', filters.page_size.toString());

  const queryStr = params.toString() ? `?${params.toString()}` : '';
  return request<IncidentListResponse>(`/incidents${queryStr}`, { method: 'GET' }, token);
}

/**
 * Retrieve real incident telemetry stats from backend.
 */
export async function getIncidentStats(
  token?: string | null
): Promise<IncidentStatsResponse> {
  return request<IncidentStatsResponse>('/incidents/stats', { method: 'GET' }, token);
}

/**
 * Retrieve individual incident report by unique ID.
 */
export async function getIncidentById(
  incidentId: string,
  token?: string | null
): Promise<Incident> {
  return request<Incident>(`/incidents/${incidentId}`, { method: 'GET' }, token);
}


// ============================================================================
// Milestone 3: Risk Assessment, Simulation & Model Telemetry Client APIs
// ============================================================================

/**
 * Execute authoritative deterministic risk assessment for an incident or custom factors.
 * Optionally includes advisory ML prediction labeled DEMO.
 */
export async function assessIncident(
  payload: RiskAssessmentCreateInput,
  token?: string | null
): Promise<RiskAssessmentResponse> {
  return request<RiskAssessmentResponse>(
    '/ai/assess',
    {
      method: 'POST',
      body: JSON.stringify(payload),
    },
    token
  );
}

/**
 * Retrieve saved risk assessment from Cloud Firestore by unique ID.
 */
export async function getAssessment(
  assessmentId: string,
  token?: string | null
): Promise<RiskAssessmentResponse> {
  return request<RiskAssessmentResponse>(
    `/ai/assessments/${assessmentId}`,
    { method: 'GET' },
    token
  );
}

/**
 * Run non-destructive what-if civic scenario simulation.
 * Calculates score delta, boundary transitions, and mitigation drivers without mutating live data.
 */
export async function simulateScenario(
  payload: SimulationRequest,
  token?: string | null
): Promise<SimulationResponse> {
  return request<SimulationResponse>(
    '/ai/simulate',
    {
      method: 'POST',
      body: JSON.stringify(payload),
    },
    token
  );
}

/**
 * Retrieve category-specific prioritized civic recommendations.
 * Every recommendation strictly holds status: PROPOSED.
 */
export async function getRecommendations(
  incidentId: string,
  token?: string | null
): Promise<RecommendationListResponse> {
  return request<RecommendationListResponse>(
    `/ai/recommendations/${incidentId}`,
    { method: 'GET' },
    token
  );
}

/**
 * Retrieve Scikit-learn model readiness status and transparency disclosures.
 */
export async function getModelStatus(
  token?: string | null
): Promise<ModelStatusResponse> {
  return request<ModelStatusResponse>(
    '/ai/model/status',
    { method: 'GET' },
    token
  );
}

/**
 * Retrieve model test split evaluation metrics with synthetic benchmark disclosures.
 */
export async function getModelMetrics(
  token?: string | null
): Promise<ModelMetricsResponse> {
  return request<ModelMetricsResponse>(
    '/ai/model/metrics',
    { method: 'GET' },
    token
  );
}

// ============================================================================
// Milestone 4: Geospatial Intelligence & Interactive Risk Mapping API
// ============================================================================

/**
 * Retrieve geospatial incidents as a GeoJSON RFC 7946 FeatureCollection.
 * Strictly preserves WGS84 coordinate ordering [longitude, latitude].
 * Returns unplotted incident items and counts without silent data loss.
 * Unassessed incidents return null risk_score and risk_level with NOT_ASSESSED status.
 */
export async function getGeoIncidents(
  params?: GeoIncidentQueryParams,
  token?: string | null
): Promise<GeoIncidentCollectionResponse> {
  const searchParams = new URLSearchParams();
  if (params?.category) searchParams.set('category', params.category);
  if (params?.risk_level) searchParams.set('risk_level', params.risk_level);
  if (params?.status) searchParams.set('status', params.status);
  if (params?.min_lat !== undefined) searchParams.set('min_lat', String(params.min_lat));
  if (params?.min_lng !== undefined) searchParams.set('min_lng', String(params.min_lng));
  if (params?.max_lat !== undefined) searchParams.set('max_lat', String(params.max_lat));
  if (params?.max_lng !== undefined) searchParams.set('max_lng', String(params.max_lng));
  if (params?.only_own !== undefined) searchParams.set('only_own', String(params.only_own));
  if (params?.limit !== undefined) searchParams.set('limit', String(params.limit));

  const queryString = searchParams.toString();
  const endpoint = queryString ? `/geo/incidents?${queryString}` : '/geo/incidents';
  return request<GeoIncidentCollectionResponse>(endpoint, { method: 'GET' }, token);
}

/**
 * Retrieve aggregate geospatial coverage metrics and risk distribution.
 */
export async function getGeoSummary(
  token?: string | null
): Promise<GeoSummaryResponse> {
  return request<GeoSummaryResponse>('/geo/summary', { method: 'GET' }, token);
}

/**
 * Retrieve exploratory spatial clusters.
 * Discloses that cluster nodes represent sampled observations, not continuous coverage.
 */
export async function getGeoClusters(
  params?: { category?: IncidentCategory; grid_size?: number },
  token?: string | null
): Promise<GeoClusterItem[]> {
  const searchParams = new URLSearchParams();
  if (params?.category) searchParams.set('category', params.category);
  if (params?.grid_size !== undefined) searchParams.set('grid_size', String(params.grid_size));

  const queryString = searchParams.toString();
  const endpoint = queryString ? `/geo/clusters?${queryString}` : '/geo/clusters';
  return request<GeoClusterItem[]>(endpoint, { method: 'GET' }, token);
}

// ============================================================================
// Milestone 5: What-If Simulation Engine & Municipal Mitigation Planning API
// ============================================================================

/**
 * Retrieve validated municipal mitigation presets for a specific incident category.
 * Each preset provides transparent parameter deltas and indicative resource benchmarks.
 */
export async function getMitigationPresets(
  category: string,
  token?: string | null
): Promise<MitigationActionPreset[]> {
  return request<MitigationActionPreset[]>(
    `/ai/mitigation/presets/${encodeURIComponent(category)}`,
    { method: 'GET' },
    token
  );
}

/**
 * Execute a multi-scenario what-if simulation evaluating 2 to 5 competing scenarios against one common baseline.
 * Performs deterministic calculations in-memory without mutating live data or creating Firestore documents.
 */
export async function simulateMultiScenarios(
  payload: MultiScenarioSimulationRequest,
  token?: string | null
): Promise<MultiScenarioSimulationResponse> {
  return request<MultiScenarioSimulationResponse>(
    '/ai/simulate/multi',
    {
      method: 'POST',
      body: JSON.stringify(payload),
    },
    token
  );
}

/**
 * Generate a structured executive mitigation brief and formatted Markdown report.
 * All proposed actions remain explicitly tagged with status PROPOSED.
 */
export async function generateMitigationReport(
  payload: MitigationReportRequest,
  token?: string | null
): Promise<MitigationReportResponse> {
  return request<MitigationReportResponse>(
    '/ai/mitigation/report',
    {
      method: 'POST',
      body: JSON.stringify(payload),
    },
    token
  );
}


