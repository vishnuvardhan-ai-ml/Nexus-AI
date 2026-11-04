import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  CartesianGrid,
  Cell,
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
} from 'recharts';
import {
  SlidersHorizontal,
  Plus,
  Trash2,
  TrendingDown,
  TrendingUp,
  AlertTriangle,
  ShieldAlert,
  ShieldCheck,
  CheckCircle2,
  Info,
  Layers,
  Sparkles,
  Download,
  FileText,
  Building2,
  Clock,
  Users,
  IndianRupee,
  Award,
  Zap,
  ArrowRight,
  ExternalLink,
  RefreshCw,
  X,
  FileDown,
  Filter,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import {
  getIncidents,
  getIncidentById,
  assessIncident,
  getMitigationPresets,
  simulateMultiScenarios,
  generateMitigationReport,
} from '../services/api';
import {
  Incident,
  IncidentCategory,
  RiskLevel,
  RiskFactorInput,
  MitigationActionPreset,
  MitigationScenarioInput,
  ScenarioEvaluation,
  MultiScenarioRankings,
  MultiScenarioSimulationRequest,
  MultiScenarioSimulationResponse,
  MitigationReportRequest,
  MitigationReportResponse,
  CostConfidence,
  FeasibilityRating,
  ResourceEstimate,
} from '../types';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';

// Helper: Risk Level Badge
const getRiskBadge = (level: RiskLevel | null | undefined) => {
  if (!level) {
    return <Badge variant="neutral">NOT_ASSESSED</Badge>;
  }
  switch (level) {
    case 'HIGH':
      return <Badge variant="high" dot>HIGH RISK</Badge>;
    case 'MEDIUM':
      return <Badge variant="medium" dot>MEDIUM RISK</Badge>;
    case 'LOW':
      return <Badge variant="low" dot>LOW RISK</Badge>;
    default:
      return <Badge variant="neutral">{level}</Badge>;
  }
};

// Helper: Feasibility Badge
const getFeasibilityBadge = (rating?: FeasibilityRating) => {
  switch (rating) {
    case 'HIGH':
      return <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-emerald-950/40 text-emerald-300 border border-emerald-500/30">FEASIBLE (HIGH)</span>;
    case 'MODERATE':
      return <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-amber-950/40 text-amber-300 border border-amber-500/30">MODERATE FEASIBILITY</span>;
    case 'COMPLEX':
      return <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-rose-950/40 text-rose-300 border border-rose-500/30">COMPLEX / CIVIL WORKS</span>;
    default:
      return <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-navy-900 text-slate-400 border border-navy-800">STANDARD</span>;
  }
};

// Helper: Confidence Tier Badge
const getConfidenceBadge = (confidence?: CostConfidence) => {
  switch (confidence) {
    case 'DOCUMENTED_BENCHMARK':
      return <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-sky-950/40 text-sky-300 border border-sky-500/30">BENCHMARK HEURISTIC</span>;
    case 'USER_SPECIFIED':
      return <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-purple-950/40 text-purple-300 border border-purple-500/30">USER SPECIFIED</span>;
    case 'UNVERIFIED_ASSUMPTION':
    default:
      return <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-slate-800/60 text-slate-300 border border-slate-700">UNVERIFIED ASSUMPTION</span>;
  }
};

const CATEGORIES: { label: string; value: IncidentCategory }[] = [
  { label: 'Waterlogging & Inundation', value: 'waterlogging' },
  { label: 'Road & Structural Damage', value: 'road_damage' },
  { label: 'Electrical & Utility Hazard', value: 'electrical_hazard' },
  { label: 'Waste Accumulation', value: 'waste_management' },
  { label: 'Extreme Heat & Microclimate', value: 'extreme_heat' },
];

export const MitigationPlannerPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const incidentIdParam = searchParams.get('incident_id');
  const { user, role, token } = useAuth();

  // Role Gate check: Analyst and Admin only
  const isAuthorized = role === 'ANALYST' || role === 'ADMIN';

  // Incident selection & baseline state
  const [incidentList, setIncidentList] = useState<Incident[]>([]);
  const [selectedIncidentId, setSelectedIncidentId] = useState<string>(incidentIdParam || '');
  const [selectedIncident, setSelectedIncident] = useState<Incident | null>(null);
  const [loadingIncident, setLoadingIncident] = useState<boolean>(false);
  const [selectedCategory, setSelectedCategory] = useState<IncidentCategory>('waterlogging');

  // Baseline Factors State
  const [baselineH, setBaselineH] = useState<number>(75);
  const [baselineE, setBaselineE] = useState<number>(70);
  const [baselineV, setBaselineV] = useState<number>(60);
  const [baselineD, setBaselineD] = useState<number>(50);
  const [isAssessed, setIsAssessed] = useState<boolean>(false);
  const [assessmentScore, setAssessmentScore] = useState<number | null>(null);
  const [assessmentLevel, setAssessmentLevel] = useState<RiskLevel | null>(null);

  // Diagnostic Record Detection
  const [isDiagnosticRecord, setIsDiagnosticRecord] = useState<boolean>(false);
  const [includeDiagnostic, setIncludeDiagnostic] = useState<boolean>(false);

  // Preset Catalogue State
  const [presets, setPresets] = useState<MitigationActionPreset[]>([]);
  const [loadingPresets, setLoadingPresets] = useState<boolean>(false);

  // Multi-Scenario Builder State (2 to 5 scenarios)
  const [scenarios, setScenarios] = useState<MitigationScenarioInput[]>([
    {
      scenario_id: 'scen_rapid_response',
      scenario_name: 'Rapid Containment & Immediate Crew Dispatch',
      description: 'Deploy ward quick-response teams to contain direct exposure and attenuate hazard drivers.',
      simulated_factors: {
        hazard_severity: 45,
        exposure: 50,
        vulnerability: 50,
        duration: 25,
        source: 'USER_DIRECT',
      },
      custom_resource_override: {
        estimated_cost_min: 25000,
        estimated_cost_max: 60000,
        currency: 'INR',
        currency_symbol: '₹',
        cost_confidence: 'DOCUMENTED_BENCHMARK',
        cost_notes: 'Standard municipal municipal ward dispatch and short-term machinery mobilization rates',
        estimated_manpower: 4,
        manpower_notes: '1 Junior Engineer, 3 Field Technicians',
        estimated_duration_hours: 4.5,
        duration_notes: 'Setup 45 mins, continuous operation 3.5 hours',
        is_estimate: true,
      },
      assumptions: 'Assumes rapid street clearance and clear utility right-of-way.',
    },
    {
      scenario_id: 'scen_engineered_diversion',
      scenario_name: 'Engineered Diversion & Structural Isolation',
      description: 'Deploy heavy mechanical equipment, secondary bypass pumping, and physical barricades.',
      simulated_factors: {
        hazard_severity: 30,
        exposure: 35,
        vulnerability: 40,
        duration: 15,
        source: 'USER_DIRECT',
      },
      custom_resource_override: {
        estimated_cost_min: 85000,
        estimated_cost_max: 180000,
        currency: 'INR',
        currency_symbol: '₹',
        cost_confidence: 'DOCUMENTED_BENCHMARK',
        cost_notes: 'Heavy machinery deployment, specialized dewatering pumps, and traffic wardens',
        estimated_manpower: 8,
        manpower_notes: '2 Senior Civil Engineers, 6 Equipment Operators',
        estimated_duration_hours: 8.0,
        duration_notes: 'Site setup 1.5 hours, intensive diversion 6.5 hours',
        is_estimate: true,
      },
      assumptions: 'Assumes inter-agency police traffic coordination and heavy crane access.',
    },
  ]);

  const [activeScenarioIdx, setActiveScenarioIdx] = useState<number>(0);

  // Simulation execution results
  const [simulationResponse, setSimulationResponse] = useState<MultiScenarioSimulationResponse | null>(null);
  const [loadingSim, setLoadingSim] = useState<boolean>(false);
  const [simError, setSimError] = useState<string | null>(null);

  // Municipal Brief Generation State
  const [briefResponse, setBriefResponse] = useState<MitigationReportResponse | null>(null);
  const [loadingBrief, setLoadingBrief] = useState<boolean>(false);
  const [briefError, setBriefError] = useState<string | null>(null);
  const [showBriefModal, setShowBriefModal] = useState<boolean>(false);

  // Chart view mode
  const [activeChartTab, setActiveChartTab] = useState<'scores' | 'factors' | 'cost_efficiency'>('scores');

  // Load Incident Registry on Mount
  useEffect(() => {
    if (token && isAuthorized) {
      getIncidents({ page_size: 50 }, token)
        .then((res) => {
          setIncidentList(res.items || []);
        })
        .catch((err) => {
          console.warn('Failed to load incident registry for mitigation planner:', err);
        });
    }
  }, [token, isAuthorized]);

  // Load Presets whenever Category changes
  useEffect(() => {
    if (token && isAuthorized && selectedCategory) {
      setLoadingPresets(true);
      getMitigationPresets(selectedCategory, token)
        .then((data) => {
          setPresets(data || []);
        })
        .catch((err) => {
          console.warn('Could not load mitigation presets:', err);
          setPresets([]);
        })
        .finally(() => {
          setLoadingPresets(false);
        });
    }
  }, [selectedCategory, token, isAuthorized]);

  // Handle Incident Selection and Baseline Calibration
  useEffect(() => {
    if (!selectedIncidentId || !token || !isAuthorized) {
      if (!selectedIncidentId) {
        setSelectedIncident(null);
        setIsDiagnosticRecord(false);
      }
      return;
    }

    setLoadingIncident(true);
    getIncidentById(selectedIncidentId, token)
      .then(async (inc) => {
        setSelectedIncident(inc);
        setSelectedCategory(inc.category);

        // Check if diagnostic test record
        const isDiag =
          inc.id === 'inc_7ce367bfe3be' ||
          (inc.reporter_email && inc.reporter_email.includes('diagnostic_test')) ||
          inc.title.toLowerCase().includes('diagnostic') ||
          inc.description.toLowerCase().includes('diagnostic');

        setIsDiagnosticRecord(isDiag);
        if (isDiag) {
          setIncludeDiagnostic(true);
        }

        // Calibrate baseline factors
        const baseHVal = inc.severity === 'HIGH' ? 80 : inc.severity === 'MEDIUM' ? 50 : 25;
        const baseEVal = inc.category === 'electrical_hazard' || inc.category === 'waterlogging' ? 70 : 55;
        const baseVVal = inc.severity === 'HIGH' ? 65 : 45;
        const baseDVal = 50;

        setBaselineH(baseHVal);
        setBaselineE(baseEVal);
        setBaselineV(baseVVal);
        setBaselineD(baseDVal);
        setIsAssessed(false);
        setAssessmentScore(null);
        setAssessmentLevel(null);
      })
      .catch((err) => {
        console.warn('Could not inspect selected incident:', err);
      })
      .finally(() => {
        setLoadingIncident(false);
      });
  }, [selectedIncidentId, token, isAuthorized]);

  const handleComputeBaselineAssessment = async () => {
    if (!selectedIncident || !token) return;
    try {
      const res = await assessIncident(
        {
          incident_id: selectedIncident.id,
          factors: {
            hazard_severity: baselineH,
            exposure: baselineE,
            vulnerability: baselineV,
            duration: baselineD,
            source: 'USER_DIRECT',
          },
          include_ml_advisory: true,
        },
        token
      );
      setIsAssessed(true);
      setAssessmentScore(res.risk_score);
      setAssessmentLevel(res.risk_level);
    } catch (err) {
      console.warn('Failed to compute baseline assessment:', err);
    }
  };

  // Scenario Management Handlers
  const handleAddScenario = () => {
    if (scenarios.length >= 5) return;
    const newId = `scen_${Date.now()}`;
    const newIdx = scenarios.length + 1;
    const newScenario: MitigationScenarioInput = {
      scenario_id: newId,
      scenario_name: `Intervention Scenario ${String.fromCharCode(64 + newIdx)}`,
      description: 'Custom mitigation intervention evaluating alternative civil and operational tradeoffs.',
      simulated_factors: {
        hazard_severity: Math.max(10, baselineH - 25),
        exposure: Math.max(10, baselineE - 20),
        vulnerability: Math.max(10, baselineV - 15),
        duration: Math.max(10, baselineD - 15),
        source: 'USER_DIRECT',
      },
      custom_resource_override: {
        estimated_cost_min: 30000,
        estimated_cost_max: 75000,
        currency: 'INR',
        currency_symbol: '₹',
        cost_confidence: 'USER_SPECIFIED',
        cost_notes: 'Planner preliminary estimate pending field dispatch verification',
        estimated_manpower: 5,
        manpower_notes: '1 Engineer, 4 technicians',
        estimated_duration_hours: 6.0,
        duration_notes: 'Standard daytime deployment window',
        is_estimate: true,
      },
      assumptions: 'Standard site access and crew availability within 2 hours.',
    };

    const updated = [...scenarios, newScenario];
    setScenarios(updated);
    setActiveScenarioIdx(updated.length - 1);
  };

  const handleRemoveScenario = (indexToRemove: number) => {
    if (scenarios.length <= 2) return;
    const updated = scenarios.filter((_, idx) => idx !== indexToRemove);
    setScenarios(updated);
    if (activeScenarioIdx >= updated.length) {
      setActiveScenarioIdx(updated.length - 1);
    }
  };

  const handleUpdateActiveScenario = (patch: Partial<MitigationScenarioInput>) => {
    const updated = [...scenarios];
    updated[activeScenarioIdx] = {
      ...updated[activeScenarioIdx],
      ...patch,
    };
    setScenarios(updated);
  };

  const handleApplyPresetToActive = (preset: MitigationActionPreset) => {
    const updated = [...scenarios];
    const current = updated[activeScenarioIdx];

    // Compute shifted factors based on preset target_factor_deltas
    const deltas = preset.target_factor_deltas || {};
    const newH = Math.max(0, Math.min(100, baselineH + (deltas.hazard_severity || 0)));
    const newE = Math.max(0, Math.min(100, baselineE + (deltas.exposure || 0)));
    const newV = Math.max(0, Math.min(100, baselineV + (deltas.vulnerability || 0)));
    const newD = Math.max(0, Math.min(100, baselineD + (deltas.duration || 0)));

    updated[activeScenarioIdx] = {
      ...current,
      scenario_name: preset.title,
      description: preset.description,
      action_ids: [preset.id],
      simulated_factors: {
        hazard_severity: newH,
        exposure: newE,
        vulnerability: newV,
        duration: newD,
        source: 'DOCUMENTED_ESTIMATE',
      },
      custom_resource_override: {
        ...preset.resource_estimate,
        cost_confidence: 'DOCUMENTED_BENCHMARK',
        is_estimate: true,
      },
      assumptions: preset.assumptions,
    };
    setScenarios(updated);
  };

  // Run Multi-Scenario Simulation
  const handleExecuteSimulation = async () => {
    if (scenarios.length < 2 || scenarios.length > 5) {
      setSimError('Simulation requires between 2 and 5 competing scenarios.');
      return;
    }

    setLoadingSim(true);
    setSimError(null);

    const payload: MultiScenarioSimulationRequest = {
      incident_id: selectedIncidentId || undefined,
      incident_category: selectedCategory,
      baseline_factors: {
        hazard_severity: baselineH,
        exposure: baselineE,
        vulnerability: baselineV,
        duration: baselineD,
        source: 'USER_DIRECT',
      },
      scenarios: scenarios,
      currency: 'INR',
      currency_symbol: '₹',
      cost_unit_lakhs: 1.0,
      include_diagnostic: includeDiagnostic,
    };

    try {
      const res = await simulateMultiScenarios(payload, token);
      setSimulationResponse(res);
      // Automatically scroll down to results section
      setTimeout(() => {
        const el = document.getElementById('simulation-results-section');
        if (el) el.scrollIntoView({ behavior: 'smooth' });
      }, 100);
    } catch (err: unknown) {
      setSimError(err instanceof Error ? err.message : 'Multi-scenario simulation execution failed.');
    } finally {
      setLoadingSim(false);
    }
  };

  // Generate Executive Municipal Mitigation Brief
  const handleGenerateBrief = async () => {
    if (!simulationResponse) return;

    setLoadingBrief(true);
    setBriefError(null);

    const reportReq: MitigationReportRequest = {
      incident_id: selectedIncidentId || undefined,
      simulation_response: simulationResponse,
      preferred_scenario_id: simulationResponse.rankings.best_balanced?.scenario_id,
      incident_title: selectedIncident?.title || `Municipal Mitigation Study: ${selectedCategory.toUpperCase()}`,
      category: selectedCategory,
      location: selectedIncident?.location || 'Municipal Ward Operations Zone',
      analyst_notes: 'Priority evaluation for municipal executive council review. Status remains strictly PROPOSED.',
    };

    try {
      const reportRes = await generateMitigationReport(reportReq, token);
      setBriefResponse(reportRes);
      setShowBriefModal(true);
    } catch (err: unknown) {
      setBriefError(err instanceof Error ? err.message : 'Failed to synthesize municipal mitigation brief.');
    } finally {
      setLoadingBrief(false);
    }
  };

  // Download Markdown Report Handler
  const handleDownloadMarkdown = () => {
    if (!briefResponse?.markdown_content) return;
    const blob = new Blob([briefResponse.markdown_content], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `nexus_mitigation_brief_${briefResponse.brief.brief_id || 'export'}.md`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  // Transform Data for Recharts
  const scoreComparisonData = useMemo(() => {
    if (!simulationResponse) return [];
    const items = [
      {
        name: 'Baseline',
        score: Number(simulationResponse.baseline_score.toFixed(1)),
        level: simulationResponse.baseline_level,
        color: '#64748b',
      },
      ...simulationResponse.evaluations.map((e, idx) => {
        const colors = ['#00f0ff', '#10b981', '#f59e0b', '#a855f7', '#ec4899'];
        return {
          name: e.scenario_name.length > 18 ? e.scenario_name.substring(0, 16) + '...' : e.scenario_name,
          fullName: e.scenario_name,
          score: Number(e.simulated_score.toFixed(1)),
          delta: Number(e.absolute_risk_reduction.toFixed(1)),
          pct: Number(e.relative_risk_reduction_pct.toFixed(1)),
          level: e.simulated_level,
          color: colors[idx % colors.length],
        };
      }),
    ];
    return items;
  }, [simulationResponse]);

  const factorRadarData = useMemo(() => {
    if (!simulationResponse) return [];
    return [
      {
        factor: 'Hazard (H)',
        Baseline: simulationResponse.baseline_factors.hazard_severity,
        ...simulationResponse.evaluations.reduce((acc, ev) => {
          const shift = ev.parameter_shifts.find((s) => s.factor === 'hazard_severity');
          acc[ev.scenario_name] = shift ? shift.simulated_value : 0;
          return acc;
        }, {} as Record<string, number>),
      },
      {
        factor: 'Exposure (E)',
        Baseline: simulationResponse.baseline_factors.exposure,
        ...simulationResponse.evaluations.reduce((acc, ev) => {
          const shift = ev.parameter_shifts.find((s) => s.factor === 'exposure');
          acc[ev.scenario_name] = shift ? shift.simulated_value : 0;
          return acc;
        }, {} as Record<string, number>),
      },
      {
        factor: 'Vulnerability (V)',
        Baseline: simulationResponse.baseline_factors.vulnerability,
        ...simulationResponse.evaluations.reduce((acc, ev) => {
          const shift = ev.parameter_shifts.find((s) => s.factor === 'vulnerability');
          acc[ev.scenario_name] = shift ? shift.simulated_value : 0;
          return acc;
        }, {} as Record<string, number>),
      },
      {
        factor: 'Duration (D)',
        Baseline: simulationResponse.baseline_factors.duration,
        ...simulationResponse.evaluations.reduce((acc, ev) => {
          const shift = ev.parameter_shifts.find((s) => s.factor === 'duration');
          acc[ev.scenario_name] = shift ? shift.simulated_value : 0;
          return acc;
        }, {} as Record<string, number>),
      },
    ];
  }, [simulationResponse]);

  // Unauthorized View for Community Users
  if (!isAuthorized) {
    return (
      <div className="space-y-6 max-w-5xl mx-auto py-8">
        <div className="glass-panel rounded-2xl p-8 border border-rose-800/40 bg-gradient-to-br from-navy-950 via-rose-950/20 to-navy-900 text-center space-y-6 shadow-glow-card">
          <div className="w-16 h-16 rounded-2xl bg-rose-950/60 border border-rose-500/40 flex items-center justify-center mx-auto text-rose-400">
            <ShieldAlert className="w-8 h-8" />
          </div>
          <div className="space-y-2 max-w-xl mx-auto">
            <h2 className="text-xl font-bold text-white tracking-wide">
              Analyst & Administrator Authorization Required
            </h2>
            <p className="text-sm text-slate-300 leading-relaxed">
              The <span className="text-brand-cyan font-mono font-semibold">Municipal Mitigation Planner</span> evaluates multi-scenario civic interventions, cross-department resource allocations, and capital budget feasibility benchmarks. This decision-support workspace is restricted to accredited Municipal Analysts and Administrators.
            </p>
          </div>

          <div className="pt-4 border-t border-navy-800 flex flex-wrap justify-center gap-4">
            <Link to="/simulator">
              <Button variant="secondary" className="gap-2">
                <SlidersHorizontal className="w-4 h-4 text-brand-cyan" />
                <span>Go to What-If Simulator (Citizen Sandbox)</span>
              </Button>
            </Link>
            <Link to="/incidents">
              <Button variant="primary" className="gap-2">
                <span>View Incident Registry</span>
                <ArrowRight className="w-4 h-4" />
              </Button>
            </Link>
          </div>
        </div>
      </div>
    );
  }

  const activeScenario = scenarios[activeScenarioIdx] || scenarios[0];

  return (
    <div className="space-y-8 pb-16">
      {/* 1. Header & Disclaimers */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-4 border-b border-navy-800">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-brand-cyan/10 border border-brand-cyan/30 text-brand-cyan">
              <Layers className="w-5 h-5" />
            </div>
            <h1 className="text-2xl font-bold text-white tracking-tight">
              Municipal Mitigation Planner
            </h1>
            <Badge variant="cyan" dot>
              DECISION ENGINE
            </Badge>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Comparative multi-scenario what-if modeling, deterministic factor attribution, and municipal resource planning.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2 font-mono text-[11px]">
          <span className="px-2.5 py-1 rounded-md bg-navy-900 border border-navy-800 text-slate-400">
            FORMULA: <span className="text-brand-cyan font-bold">R = 0.4H + 0.3E + 0.2V + 0.1D</span>
          </span>
          <span className="px-2.5 py-1 rounded-md bg-amber-950/40 border border-amber-500/30 text-amber-300">
            STATUS: PROPOSED ONLY
          </span>
        </div>
      </div>

      {/* Diagnostic Record Warning Banner */}
      {isDiagnosticRecord && (
        <div className="p-4 rounded-xl bg-amber-950/30 border border-amber-500/40 text-amber-200 space-y-2 shadow-glow-card">
          <div className="flex items-center gap-2.5 font-bold text-sm">
            <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0" />
            <span>DIAGNOSTIC VERIFICATION RECORD DETECTED ({selectedIncidentId})</span>
          </div>
          <p className="text-xs text-amber-200/90 leading-relaxed">
            This incident was generated as a platform calibration benchmark. Results must remain classified as experimental verification tests and are excluded from operational municipal deployment work orders.
          </p>
          <div className="flex items-center gap-2 pt-1 font-mono text-xs">
            <input
              type="checkbox"
              id="diag-toggle"
              checked={includeDiagnostic}
              onChange={(e) => setIncludeDiagnostic(e.target.checked)}
              className="accent-amber-400 rounded cursor-pointer"
            />
            <label htmlFor="diag-toggle" className="cursor-pointer text-amber-300 font-semibold">
              Deliberately include diagnostic verification record in multi-scenario evaluation
            </label>
          </div>
        </div>
      )}

      {/* 2. Incident Selection & Baseline Panel */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Context Selection (5 cols) */}
        <div className="lg:col-span-5 glass-panel rounded-xl p-6 border border-navy-800 space-y-5 shadow-glow-card">
          <div className="flex items-center justify-between pb-3 border-b border-navy-800">
            <h3 className="text-sm font-bold text-white uppercase tracking-wider font-mono flex items-center gap-2">
              <Filter className="w-4 h-4 text-brand-cyan" />
              <span>Planning Baseline Target</span>
            </h3>
            {loadingIncident && (
              <div className="w-4 h-4 rounded-full border-2 border-brand-cyan border-t-transparent animate-spin" />
            )}
          </div>

          {/* Incident Selector */}
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-slate-300 flex items-center justify-between">
              <span>Select Linked Incident:</span>
              <span className="text-[10px] font-mono text-slate-500">From Platform Registry</span>
            </label>
            <select
              value={selectedIncidentId}
              onChange={(e) => {
                const newId = e.target.value;
                setSelectedIncidentId(newId);
                setSearchParams(newId ? { incident_id: newId } : {});
              }}
              className="w-full bg-navy-950 border border-navy-800 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-brand-cyan font-mono"
            >
              <option value="">-- Standalone Municipal Scenario (No Linked Incident) --</option>
              {incidentList.map((inc) => (
                <option key={inc.id} value={inc.id}>
                  [{inc.severity}] {inc.id} — {inc.title.substring(0, 40)}
                </option>
              ))}
            </select>
          </div>

          {/* Category Selector */}
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-slate-300">Hazard Taxonomy Category:</label>
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value as IncidentCategory)}
              className="w-full bg-navy-950 border border-navy-800 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-brand-cyan font-mono"
            >
              {CATEGORIES.map((c) => (
                <option key={c.value} value={c.value}>
                  {c.label}
                </option>
              ))}
            </select>
          </div>

          {/* Selected Incident Snapshot */}
          {selectedIncident ? (
            <div className="p-3.5 rounded-lg bg-navy-950/70 border border-navy-800 space-y-2 text-xs">
              <div className="flex items-center justify-between">
                <span className="font-bold text-white truncate max-w-[220px]">
                  {selectedIncident.title}
                </span>
                {getRiskBadge(assessmentLevel || (selectedIncident.severity as RiskLevel))}
              </div>
              <div className="flex items-center justify-between text-[11px] font-mono text-slate-400">
                <span>Location: {selectedIncident.location}</span>
                <span>Status: {selectedIncident.status}</span>
              </div>
              {isAssessed ? (
                <div className="pt-2 border-t border-navy-800/80 flex items-center justify-between text-xs font-mono">
                  <span className="text-slate-400">Authoritative Baseline:</span>
                  <span className="text-brand-cyan font-bold">{assessmentScore?.toFixed(1)} / 100</span>
                </div>
              ) : (
                <div className="pt-2 border-t border-navy-800/80 flex items-center justify-between gap-2">
                  <div className="text-[11px] font-mono text-amber-400 flex items-center gap-1.5">
                    <Info className="w-3.5 h-3.5 shrink-0" />
                    <span>Unassessed record.</span>
                  </div>
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={handleComputeBaselineAssessment}
                    className="text-[10px] h-6 px-2"
                  >
                    Assess Baseline
                  </Button>
                </div>
              )}
            </div>
          ) : (
            <div className="p-3 rounded-lg bg-navy-950/40 border border-dashed border-navy-800 text-[11px] font-mono text-slate-400">
              Operating in Standalone Planning Mode. Baseline factors represent city-wide or ward-level synthetic reference.
            </div>
          )}

          {/* Baseline H/E/V/D Controls */}
          <div className="space-y-3 pt-2">
            <span className="text-xs font-bold text-slate-200 uppercase tracking-wider font-mono block">
              Baseline Parameters (0–100)
            </span>
            <div className="grid grid-cols-2 gap-3 font-mono text-xs">
              <div className="p-2.5 rounded bg-navy-900 border border-navy-800 space-y-1">
                <div className="flex justify-between text-slate-400 text-[10px]">
                  <span>Hazard (H) [40%]</span>
                  <span className="text-white font-bold">{baselineH}</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={baselineH}
                  onChange={(e) => setBaselineH(Number(e.target.value))}
                  className="w-full accent-brand-cyan h-1.5 bg-navy-950 rounded cursor-pointer"
                />
              </div>

              <div className="p-2.5 rounded bg-navy-900 border border-navy-800 space-y-1">
                <div className="flex justify-between text-slate-400 text-[10px]">
                  <span>Exposure (E) [30%]</span>
                  <span className="text-white font-bold">{baselineE}</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={baselineE}
                  onChange={(e) => setBaselineE(Number(e.target.value))}
                  className="w-full accent-brand-cyan h-1.5 bg-navy-950 rounded cursor-pointer"
                />
              </div>

              <div className="p-2.5 rounded bg-navy-900 border border-navy-800 space-y-1">
                <div className="flex justify-between text-slate-400 text-[10px]">
                  <span>Vulnerability (V) [20%]</span>
                  <span className="text-white font-bold">{baselineV}</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={baselineV}
                  onChange={(e) => setBaselineV(Number(e.target.value))}
                  className="w-full accent-brand-cyan h-1.5 bg-navy-950 rounded cursor-pointer"
                />
              </div>

              <div className="p-2.5 rounded bg-navy-900 border border-navy-800 space-y-1">
                <div className="flex justify-between text-slate-400 text-[10px]">
                  <span>Duration (D) [10%]</span>
                  <span className="text-white font-bold">{baselineD}</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={baselineD}
                  onChange={(e) => setBaselineD(Number(e.target.value))}
                  className="w-full accent-brand-cyan h-1.5 bg-navy-950 rounded cursor-pointer"
                />
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: Vetted Action Preset Catalogue (7 cols) */}
        <div className="lg:col-span-7 glass-panel rounded-xl p-6 border border-navy-800 space-y-4 shadow-glow-card">
          <div className="flex items-center justify-between pb-3 border-b border-navy-800">
            <div>
              <h3 className="text-sm font-bold text-white uppercase tracking-wider font-mono flex items-center gap-2">
                <Zap className="w-4 h-4 text-brand-cyan" />
                <span>Municipal Action Preset Catalogue</span>
              </h3>
              <p className="text-[11px] text-slate-400">
                Pre-configured municipal interventions for <span className="text-brand-cyan font-mono">{selectedCategory}</span> with documented parameter shifts and indicative resource bounds.
              </p>
            </div>
            {loadingPresets && (
              <div className="w-4 h-4 rounded-full border-2 border-brand-cyan border-t-transparent animate-spin" />
            )}
          </div>

          <div className="space-y-3 max-h-[360px] overflow-y-auto pr-1">
            {presets.length > 0 ? (
              presets.map((p) => {
                const est = p.resource_estimate;
                return (
                  <div
                    key={p.id}
                    className="p-3.5 rounded-lg bg-navy-950/70 border border-navy-800/80 hover:border-brand-cyan/40 transition-all space-y-2 group"
                  >
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1.5">
                      <div className="flex items-center gap-2">
                        <span className="font-bold text-xs text-white group-hover:text-brand-cyan transition-colors">
                          {p.title}
                        </span>
                        {getFeasibilityBadge(p.feasibility)}
                      </div>
                      <Button
                        size="sm"
                        variant="secondary"
                        onClick={() => handleApplyPresetToActive(p)}
                        className="text-[10px] h-7 px-2.5 gap-1 shrink-0"
                      >
                        <Plus className="w-3 h-3 text-brand-cyan" />
                        <span>Apply to Active Scenario</span>
                      </Button>
                    </div>

                    <p className="text-[11px] text-slate-300 leading-relaxed">
                      {p.description}
                    </p>

                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-2 border-t border-navy-900 text-[10px] font-mono text-slate-400">
                      <div>
                        <span className="block text-slate-500">Indicative Cost:</span>
                        <span className="text-slate-200 font-semibold">
                          ₹{est.estimated_cost_min?.toLocaleString()} – ₹{est.estimated_cost_max?.toLocaleString()}
                        </span>
                      </div>
                      <div>
                        <span className="block text-slate-500">Crew Size:</span>
                        <span className="text-slate-200 font-semibold">{est.estimated_manpower} personnel</span>
                      </div>
                      <div>
                        <span className="block text-slate-500">Lead-Time:</span>
                        <span className="text-slate-200 font-semibold">{est.estimated_duration_hours} hrs</span>
                      </div>
                      <div>
                        <span className="block text-slate-500">Dept:</span>
                        <span className="text-slate-200 truncate block">{p.responsible_department}</span>
                      </div>
                    </div>
                  </div>
                );
              })
            ) : (
              <div className="text-center py-8 text-xs font-mono text-slate-500">
                {loadingPresets ? 'FETCHING MUNICIPAL PRESETS...' : 'NO PRESETS FOUND FOR THIS CATEGORY.'}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* 3. Multi-Scenario Builder Workspace */}
      <div className="glass-panel rounded-xl p-6 sm:p-8 border border-navy-800 space-y-6 shadow-glow-card">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-navy-800">
          <div>
            <h2 className="text-lg font-bold text-white tracking-tight flex items-center gap-2">
              <SlidersHorizontal className="w-5 h-5 text-brand-cyan" />
              <span>Multi-Scenario Builder (2 to 5 Scenarios)</span>
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Configure competing mitigation packages. Sliders define simulated post-intervention parameter shifts.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-xs font-mono text-slate-400">
              Count: <span className="text-brand-cyan font-bold">{scenarios.length}/5</span>
            </span>
            <Button
              size="sm"
              variant="secondary"
              onClick={handleAddScenario}
              disabled={scenarios.length >= 5}
              className="gap-1.5 text-xs"
            >
              <Plus className="w-3.5 h-3.5 text-brand-cyan" />
              <span>Add Scenario</span>
            </Button>
          </div>
        </div>

        {/* Scenario Tabs */}
        <div className="flex items-center gap-2 overflow-x-auto pb-2 border-b border-navy-800/60 font-mono text-xs">
          {scenarios.map((scen, idx) => (
            <button
              key={scen.scenario_id}
              onClick={() => setActiveScenarioIdx(idx)}
              className={`flex items-center gap-2 px-3.5 py-2 rounded-lg transition-all border shrink-0 ${
                activeScenarioIdx === idx
                  ? 'bg-brand-cyan/15 border-brand-cyan text-brand-cyan font-bold shadow-glow-cyan'
                  : 'bg-navy-950/60 border-navy-800 text-slate-400 hover:text-white hover:border-slate-700'
              }`}
            >
              <span>{idx + 1}. {scen.scenario_name.substring(0, 20)}</span>
              {scenarios.length > 2 && (
                <span
                  onClick={(e) => {
                    e.stopPropagation();
                    handleRemoveScenario(idx);
                  }}
                  className="p-1 hover:text-rose-400 rounded transition-colors"
                  title="Remove scenario"
                >
                  <Trash2 className="w-3 h-3" />
                </span>
              )}
            </button>
          ))}
        </div>

        {/* Active Scenario Configuration Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 pt-2">
          {/* Metadata & H/E/V/D Sliders (7 cols) */}
          <div className="lg:col-span-7 space-y-5">
            <div className="space-y-3">
              <div>
                <label className="text-xs font-semibold text-slate-300">Scenario Name:</label>
                <input
                  type="text"
                  value={activeScenario.scenario_name}
                  onChange={(e) => handleUpdateActiveScenario({ scenario_name: e.target.value })}
                  className="w-full bg-navy-950 border border-navy-800 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-brand-cyan font-mono mt-1"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-300">Operational Description & Mechanism:</label>
                <textarea
                  rows={2}
                  value={activeScenario.description || ''}
                  onChange={(e) => handleUpdateActiveScenario({ description: e.target.value })}
                  placeholder="Describe the physical intervention..."
                  className="w-full bg-navy-950 border border-navy-800 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-brand-cyan mt-1"
                />
              </div>
            </div>

            {/* Sliders */}
            <div className="space-y-4 pt-2">
              <h4 className="text-xs font-bold text-slate-200 uppercase tracking-wider font-mono flex items-center justify-between">
                <span>Simulated Factor Adjustments</span>
                <span className="text-[10px] text-slate-500">Slide to test intervention impact</span>
              </h4>

              {/* 1. Hazard Severity */}
              <div className="p-3.5 rounded-lg bg-navy-950/80 border border-navy-800 space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-semibold text-slate-200">
                    Hazard Severity (H) — <span className="font-mono text-brand-cyan">40% Formula Weight</span>
                  </span>
                  <div className="flex items-center gap-2 font-mono text-xs">
                    <span className="text-slate-500">Base: {baselineH}</span>
                    <span className="text-slate-400">→</span>
                    <span className="text-brand-cyan font-bold">
                      {activeScenario.simulated_factors.hazard_severity} / 100
                    </span>
                    <span className="text-[10px] text-slate-400">
                      (Δ {(activeScenario.simulated_factors.hazard_severity - baselineH).toFixed(0)})
                    </span>
                  </div>
                </div>
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={activeScenario.simulated_factors.hazard_severity}
                  onChange={(e) =>
                    handleUpdateActiveScenario({
                      simulated_factors: {
                        ...activeScenario.simulated_factors,
                        hazard_severity: Number(e.target.value),
                      },
                    })
                  }
                  className="w-full accent-brand-cyan h-2 bg-navy-900 rounded cursor-pointer"
                />
              </div>

              {/* 2. Exposure */}
              <div className="p-3.5 rounded-lg bg-navy-950/80 border border-navy-800 space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-semibold text-slate-200">
                    Human & Asset Exposure (E) — <span className="font-mono text-brand-cyan">30% Formula Weight</span>
                  </span>
                  <div className="flex items-center gap-2 font-mono text-xs">
                    <span className="text-slate-500">Base: {baselineE}</span>
                    <span className="text-slate-400">→</span>
                    <span className="text-brand-cyan font-bold">
                      {activeScenario.simulated_factors.exposure} / 100
                    </span>
                    <span className="text-[10px] text-slate-400">
                      (Δ {(activeScenario.simulated_factors.exposure - baselineE).toFixed(0)})
                    </span>
                  </div>
                </div>
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={activeScenario.simulated_factors.exposure}
                  onChange={(e) =>
                    handleUpdateActiveScenario({
                      simulated_factors: {
                        ...activeScenario.simulated_factors,
                        exposure: Number(e.target.value),
                      },
                    })
                  }
                  className="w-full accent-brand-cyan h-2 bg-navy-900 rounded cursor-pointer"
                />
              </div>

              {/* 3. Vulnerability */}
              <div className="p-3.5 rounded-lg bg-navy-950/80 border border-navy-800 space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-semibold text-slate-200">
                    Infrastructure Vulnerability (V) — <span className="font-mono text-brand-cyan">20% Formula Weight</span>
                  </span>
                  <div className="flex items-center gap-2 font-mono text-xs">
                    <span className="text-slate-500">Base: {baselineV}</span>
                    <span className="text-slate-400">→</span>
                    <span className="text-brand-cyan font-bold">
                      {activeScenario.simulated_factors.vulnerability} / 100
                    </span>
                    <span className="text-[10px] text-slate-400">
                      (Δ {(activeScenario.simulated_factors.vulnerability - baselineV).toFixed(0)})
                    </span>
                  </div>
                </div>
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={activeScenario.simulated_factors.vulnerability}
                  onChange={(e) =>
                    handleUpdateActiveScenario({
                      simulated_factors: {
                        ...activeScenario.simulated_factors,
                        vulnerability: Number(e.target.value),
                      },
                    })
                  }
                  className="w-full accent-brand-cyan h-2 bg-navy-900 rounded cursor-pointer"
                />
              </div>

              {/* 4. Duration */}
              <div className="p-3.5 rounded-lg bg-navy-950/80 border border-navy-800 space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-semibold text-slate-200">
                    Unresolved Duration (D) — <span className="font-mono text-brand-cyan">10% Formula Weight</span>
                  </span>
                  <div className="flex items-center gap-2 font-mono text-xs">
                    <span className="text-slate-500">Base: {baselineD}</span>
                    <span className="text-slate-400">→</span>
                    <span className="text-brand-cyan font-bold">
                      {activeScenario.simulated_factors.duration} / 100
                    </span>
                    <span className="text-[10px] text-slate-400">
                      (Δ {(activeScenario.simulated_factors.duration - baselineD).toFixed(0)})
                    </span>
                  </div>
                </div>
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={activeScenario.simulated_factors.duration}
                  onChange={(e) =>
                    handleUpdateActiveScenario({
                      simulated_factors: {
                        ...activeScenario.simulated_factors,
                        duration: Number(e.target.value),
                      },
                    })
                  }
                  className="w-full accent-brand-cyan h-2 bg-navy-900 rounded cursor-pointer"
                />
              </div>
            </div>
          </div>

          {/* Indicative Resource Parameters (5 cols) */}
          <div className="lg:col-span-5 glass-panel rounded-xl p-5 border border-navy-800 space-y-4">
            <h4 className="text-xs font-bold text-white uppercase tracking-wider font-mono flex items-center gap-2 pb-2 border-b border-navy-800">
              <Building2 className="w-4 h-4 text-brand-cyan" />
              <span>Indicative Municipal Resources</span>
            </h4>

            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-[11px] font-semibold text-slate-300">Min Cost (₹ INR):</label>
                  <input
                    type="number"
                    min="0"
                    step="1000"
                    value={activeScenario.custom_resource_override?.estimated_cost_min ?? 0}
                    onChange={(e) =>
                      handleUpdateActiveScenario({
                        custom_resource_override: {
                          ...activeScenario.custom_resource_override,
                          estimated_cost_min: Number(e.target.value),
                          is_estimate: true,
                        },
                      })
                    }
                    className="w-full bg-navy-950 border border-navy-800 rounded px-2.5 py-1.5 text-xs text-white focus:outline-none focus:border-brand-cyan font-mono mt-1"
                  />
                </div>
                <div>
                  <label className="text-[11px] font-semibold text-slate-300">Max Cost (₹ INR):</label>
                  <input
                    type="number"
                    min="0"
                    step="1000"
                    value={activeScenario.custom_resource_override?.estimated_cost_max ?? 0}
                    onChange={(e) =>
                      handleUpdateActiveScenario({
                        custom_resource_override: {
                          ...activeScenario.custom_resource_override,
                          estimated_cost_max: Number(e.target.value),
                          is_estimate: true,
                        },
                      })
                    }
                    className="w-full bg-navy-950 border border-navy-800 rounded px-2.5 py-1.5 text-xs text-white focus:outline-none focus:border-brand-cyan font-mono mt-1"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-[11px] font-semibold text-slate-300">Crew Size (Headcount):</label>
                  <input
                    type="number"
                    min="0"
                    value={activeScenario.custom_resource_override?.estimated_manpower ?? 0}
                    onChange={(e) =>
                      handleUpdateActiveScenario({
                        custom_resource_override: {
                          ...activeScenario.custom_resource_override,
                          estimated_manpower: Number(e.target.value),
                          is_estimate: true,
                        },
                      })
                    }
                    className="w-full bg-navy-950 border border-navy-800 rounded px-2.5 py-1.5 text-xs text-white focus:outline-none focus:border-brand-cyan font-mono mt-1"
                  />
                </div>
                <div>
                  <label className="text-[11px] font-semibold text-slate-300">Duration (Hours):</label>
                  <input
                    type="number"
                    min="0"
                    step="0.5"
                    value={activeScenario.custom_resource_override?.estimated_duration_hours ?? 0}
                    onChange={(e) =>
                      handleUpdateActiveScenario({
                        custom_resource_override: {
                          ...activeScenario.custom_resource_override,
                          estimated_duration_hours: Number(e.target.value),
                          is_estimate: true,
                        },
                      })
                    }
                    className="w-full bg-navy-950 border border-navy-800 rounded px-2.5 py-1.5 text-xs text-white focus:outline-none focus:border-brand-cyan font-mono mt-1"
                  />
                </div>
              </div>

              <div>
                <label className="text-[11px] font-semibold text-slate-300">Cost Confidence Classification:</label>
                <select
                  value={activeScenario.custom_resource_override?.cost_confidence || 'DOCUMENTED_BENCHMARK'}
                  onChange={(e) =>
                    handleUpdateActiveScenario({
                      custom_resource_override: {
                        ...activeScenario.custom_resource_override,
                        cost_confidence: e.target.value as CostConfidence,
                        is_estimate: true,
                      },
                    })
                  }
                  className="w-full bg-navy-950 border border-navy-800 rounded px-2.5 py-1.5 text-xs text-white focus:outline-none focus:border-brand-cyan font-mono mt-1"
                >
                  <option value="DOCUMENTED_BENCHMARK">DOCUMENTED_BENCHMARK (Heuristic rate)</option>
                  <option value="USER_SPECIFIED">USER_SPECIFIED (Analyst estimate)</option>
                  <option value="UNVERIFIED_ASSUMPTION">UNVERIFIED_ASSUMPTION (Working draft)</option>
                </select>
              </div>

              <div>
                <label className="text-[11px] font-semibold text-slate-300">Assumptions & Caveats:</label>
                <textarea
                  rows={2}
                  value={activeScenario.assumptions || ''}
                  onChange={(e) => handleUpdateActiveScenario({ assumptions: e.target.value })}
                  placeholder="e.g. Assumes dry weather window during execution..."
                  className="w-full bg-navy-950 border border-navy-800 rounded px-2.5 py-1.5 text-xs text-white focus:outline-none focus:border-brand-cyan mt-1"
                />
              </div>
            </div>

            <div className="pt-2 border-t border-navy-800 text-[10px] font-mono text-slate-400">
              Disclaimer: All resource figures are planning estimates with status PROPOSED. Does not constitute tender award or expenditure sanction.
            </div>
          </div>
        </div>

        {/* Action Button: Run Multi-Scenario Simulation */}
        <div className="pt-4 border-t border-navy-800 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="text-xs font-mono text-slate-400">
            {scenarios.length >= 2 && scenarios.length <= 5 ? (
              <span className="text-emerald-400 flex items-center gap-1.5">
                <CheckCircle2 className="w-4 h-4" />
                <span>Ready to evaluate {scenarios.length} competing scenarios against common baseline.</span>
              </span>
            ) : (
              <span className="text-rose-400 flex items-center gap-1.5">
                <AlertTriangle className="w-4 h-4" />
                <span>Simulation requires 2 to 5 scenarios (currently {scenarios.length}).</span>
              </span>
            )}
          </div>

          <Button
            variant="primary"
            onClick={handleExecuteSimulation}
            disabled={loadingSim || scenarios.length < 2 || scenarios.length > 5}
            className="gap-2 px-6"
          >
            {loadingSim ? (
              <>
                <div className="w-4 h-4 rounded-full border-2 border-navy-950 border-t-transparent animate-spin" />
                <span>Evaluating Scenarios...</span>
              </>
            ) : (
              <>
                <Sparkles className="w-4 h-4" />
                <span>Execute Comparative Simulation</span>
              </>
            )}
          </Button>
        </div>

        {simError && (
          <div className="p-3.5 rounded-lg bg-rose-950/40 border border-rose-500/40 text-xs text-rose-300 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 shrink-0" />
            <span>{simError}</span>
          </div>
        )}
      </div>

      {/* ===================================================================== */}
      {/* 4. Comparative Visualization & Multi-Criteria Rankings Section */}
      {/* ===================================================================== */}
      {simulationResponse && (
        <div id="simulation-results-section" className="space-y-6 pt-4">
          <div className="glass-panel rounded-xl p-6 sm:p-8 border border-navy-800 space-y-6 shadow-glow-card">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-navy-800">
              <div>
                <h3 className="text-lg font-bold text-white tracking-tight flex items-center gap-2">
                  <Award className="w-5 h-5 text-brand-cyan" />
                  <span>Comparative Scenario Evaluation & Trade-off Analysis</span>
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Evaluated {simulationResponse.scenarios_evaluated_count} scenarios deterministically in-memory. Zero Firestore records mutated.
                </p>
              </div>

              <div className="flex items-center gap-2">
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={handleGenerateBrief}
                  disabled={loadingBrief}
                  className="gap-1.5 text-xs"
                >
                  <FileText className="w-4 h-4 text-brand-cyan" />
                  <span>Generate Municipal Brief</span>
                </Button>
              </div>
            </div>

            {/* Quick KPI Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {/* 1. Baseline */}
              <div className="p-4 rounded-xl bg-navy-950/70 border border-navy-800 space-y-1">
                <span className="text-[10px] font-mono text-slate-400 uppercase tracking-wider block">
                  Common Baseline
                </span>
                <div className="text-2xl font-bold font-mono text-white">
                  {simulationResponse.baseline_score.toFixed(1)} / 100
                </div>
                <div>{getRiskBadge(simulationResponse.baseline_level)}</div>
              </div>

              {/* 2. Best Impact */}
              <div className="p-4 rounded-xl bg-navy-900/60 border border-brand-cyan/40 space-y-1 shadow-glow-card">
                <span className="text-[10px] font-mono text-brand-cyan uppercase tracking-wider block">
                  Top Risk Reduction (ΔR)
                </span>
                <div className="text-2xl font-bold font-mono text-brand-cyan">
                  {simulationResponse.rankings.by_impact[0]?.metric_value !== undefined
                    ? `-${simulationResponse.rankings.by_impact[0].metric_value?.toFixed(1)} pts`
                    : 'N/A'}
                </div>
                <span className="text-[11px] text-slate-300 font-sans truncate block">
                  {simulationResponse.rankings.by_impact[0]?.scenario_name}
                </span>
              </div>

              {/* 3. Top Cost Efficiency */}
              <div className="p-4 rounded-xl bg-navy-900/60 border border-emerald-500/40 space-y-1">
                <span className="text-[10px] font-mono text-emerald-400 uppercase tracking-wider block">
                  Top Cost Efficiency
                </span>
                <div className="text-lg font-bold font-mono text-emerald-300 truncate">
                  {simulationResponse.rankings.by_cost_efficiency[0]?.metric_label || 'Zero Direct Cost'}
                </div>
                <span className="text-[11px] text-slate-300 font-sans truncate block">
                  {simulationResponse.rankings.by_cost_efficiency[0]?.scenario_name}
                </span>
              </div>

              {/* 4. Best Balanced */}
              <div className="p-4 rounded-xl bg-purple-950/30 border border-purple-500/40 space-y-1">
                <span className="text-[10px] font-mono text-purple-300 uppercase tracking-wider block">
                  Recommended Balanced
                </span>
                <div className="text-sm font-bold text-white truncate">
                  {simulationResponse.rankings.best_balanced?.scenario_name || 'Balanced Alternative'}
                </div>
                <span className="text-[10px] font-mono text-purple-300 block">
                  {simulationResponse.rankings.best_balanced?.metric_label}
                </span>
              </div>
            </div>

            {/* Chart View Tabs */}
            <div className="space-y-4 pt-2">
              <div className="flex items-center gap-2 border-b border-navy-800 pb-2">
                <button
                  onClick={() => setActiveChartTab('scores')}
                  className={`px-3 py-1.5 rounded-lg text-xs font-mono transition-colors ${
                    activeChartTab === 'scores'
                      ? 'bg-brand-cyan/20 text-brand-cyan font-bold border border-brand-cyan/40'
                      : 'text-slate-400 hover:text-white'
                  }`}
                >
                  Risk Score Comparison (Bar)
                </button>
                <button
                  onClick={() => setActiveChartTab('factors')}
                  className={`px-3 py-1.5 rounded-lg text-xs font-mono transition-colors ${
                    activeChartTab === 'factors'
                      ? 'bg-brand-cyan/20 text-brand-cyan font-bold border border-brand-cyan/40'
                      : 'text-slate-400 hover:text-white'
                  }`}
                >
                  Factor Shift Profile (Radar)
                </button>
              </div>

              {/* Chart Content */}
              {activeChartTab === 'scores' ? (
                <div className="h-72 w-full pt-4">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={scoreComparisonData} margin={{ top: 10, right: 20, left: 0, bottom: 20 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                      <XAxis dataKey="name" stroke="#94a3b8" fontSize={11} tickLine={false} />
                      <YAxis domain={[0, 100]} stroke="#94a3b8" fontSize={11} />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: '#070b14',
                          border: '1px solid #1e293b',
                          borderRadius: '8px',
                          color: '#fff',
                          fontFamily: 'monospace',
                          fontSize: '11px',
                        }}
                      />
                      <Bar dataKey="score" name="Risk Score (0-100)" radius={[4, 4, 0, 0]}>
                        {scoreComparisonData.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={entry.color} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              ) : (
                <div className="h-80 w-full pt-2">
                  <ResponsiveContainer width="100%" height="100%">
                    <RadarChart data={factorRadarData} margin={{ top: 10, right: 30, left: 30, bottom: 10 }}>
                      <PolarGrid stroke="#1e293b" />
                      <PolarAngleAxis dataKey="factor" stroke="#94a3b8" fontSize={11} />
                      <PolarRadiusAxis domain={[0, 100]} stroke="#475569" fontSize={10} />
                      <Radar name="Baseline" dataKey="Baseline" stroke="#64748b" fill="#64748b" fillOpacity={0.2} />
                      {simulationResponse.evaluations.map((ev, idx) => {
                        const colors = ['#00f0ff', '#10b981', '#f59e0b', '#a855f7'];
                        const col = colors[idx % colors.length];
                        return (
                          <Radar
                            key={ev.scenario_id}
                            name={ev.scenario_name}
                            dataKey={ev.scenario_name}
                            stroke={col}
                            fill={col}
                            fillOpacity={0.25}
                          />
                        );
                      })}
                      <Legend wrapperStyle={{ fontSize: '11px', fontFamily: 'monospace' }} />
                      <Tooltip
                        contentStyle={{
                          backgroundColor: '#070b14',
                          border: '1px solid #1e293b',
                          borderRadius: '8px',
                          fontSize: '11px',
                        }}
                      />
                    </RadarChart>
                  </ResponsiveContainer>
                </div>
              )}
            </div>

            {/* Multi-Criteria Rankings Breakdown */}
            <div className="space-y-3 pt-4 border-t border-navy-800">
              <h4 className="text-xs font-bold text-white uppercase tracking-wider font-mono">
                Multi-Criteria Scenario Rankings (Deterministic Backend Ordering)
              </h4>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {/* 1. Impact */}
                <div className="p-4 rounded-xl bg-navy-950/80 border border-navy-800 space-y-2.5">
                  <span className="text-xs font-bold text-brand-cyan font-mono flex items-center gap-1.5">
                    <TrendingDown className="w-4 h-4" />
                    <span>Ranked by Impact (|ΔR|)</span>
                  </span>
                  <div className="space-y-2 text-xs">
                    {simulationResponse.rankings.by_impact.map((r) => (
                      <div key={r.scenario_id} className="p-2 rounded bg-navy-900 border border-navy-800/60 space-y-1">
                        <div className="flex items-center justify-between">
                          <span className="font-bold text-white">#{r.rank} {r.scenario_name}</span>
                          <span className="font-mono text-brand-cyan font-bold">{r.metric_label}</span>
                        </div>
                        <p className="text-[10px] text-slate-400">{r.rationale}</p>
                      </div>
                    ))}
                  </div>
                </div>

                {/* 2. Cost Efficiency */}
                <div className="p-4 rounded-xl bg-navy-950/80 border border-navy-800 space-y-2.5">
                  <span className="text-xs font-bold text-emerald-400 font-mono flex items-center gap-1.5">
                    <IndianRupee className="w-4 h-4" />
                    <span>Ranked by Cost Efficiency</span>
                  </span>
                  <div className="space-y-2 text-xs">
                    {simulationResponse.rankings.by_cost_efficiency.map((r) => (
                      <div key={r.scenario_id} className="p-2 rounded bg-navy-900 border border-navy-800/60 space-y-1">
                        <div className="flex items-center justify-between">
                          <span className="font-bold text-white">#{r.rank} {r.scenario_name}</span>
                          <span className="font-mono text-emerald-300 font-bold">{r.metric_label}</span>
                        </div>
                        <p className="text-[10px] text-slate-400">{r.rationale}</p>
                      </div>
                    ))}
                  </div>
                </div>

                {/* 3. Deployment Speed */}
                <div className="p-4 rounded-xl bg-navy-950/80 border border-navy-800 space-y-2.5">
                  <span className="text-xs font-bold text-purple-400 font-mono flex items-center gap-1.5">
                    <Clock className="w-4 h-4" />
                    <span>Ranked by Deployment Speed</span>
                  </span>
                  <div className="space-y-2 text-xs">
                    {simulationResponse.rankings.by_deployment_speed.map((r) => (
                      <div key={r.scenario_id} className="p-2 rounded bg-navy-900 border border-navy-800/60 space-y-1">
                        <div className="flex items-center justify-between">
                          <span className="font-bold text-white">#{r.rank} {r.scenario_name}</span>
                          <span className="font-mono text-purple-300 font-bold">{r.metric_label}</span>
                        </div>
                        <p className="text-[10px] text-slate-400">{r.rationale}</p>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>

            {/* 5. Municipal Resource Planning Comparison Table */}
            <div className="space-y-3 pt-4 border-t border-navy-800">
              <h4 className="text-xs font-bold text-white uppercase tracking-wider font-mono flex items-center gap-2">
                <Building2 className="w-4 h-4 text-brand-cyan" />
                <span>Municipal Resource Footprint & Feasibility Comparison</span>
              </h4>

              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="border-b border-navy-800 text-[10px] font-mono text-slate-400 uppercase tracking-wider bg-navy-950/60">
                      <th className="p-3">Scenario</th>
                      <th className="p-3">Risk Shift</th>
                      <th className="p-3">Cost Range (₹ INR)</th>
                      <th className="p-3">Efficiency Index</th>
                      <th className="p-3">Crew Size</th>
                      <th className="p-3">Hours</th>
                      <th className="p-3">Confidence</th>
                      <th className="p-3">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-navy-800/60">
                    {simulationResponse.evaluations.map((ev) => {
                      const est = ev.resource_estimate;
                      return (
                        <tr key={ev.scenario_id} className="hover:bg-navy-900/40 transition-colors">
                          <td className="p-3 font-semibold text-white">
                            <div>{ev.scenario_name}</div>
                            <span className="text-[10px] font-mono text-slate-500">ID: {ev.scenario_id}</span>
                          </td>
                          <td className="p-3 font-mono">
                            <span className="text-brand-cyan font-bold">-{ev.absolute_risk_reduction.toFixed(1)} pts</span>
                            <span className="text-[10px] text-slate-400 block">({ev.level_transition || 'No level change'})</span>
                          </td>
                          <td className="p-3 font-mono">
                            {est.estimated_cost_min !== null && est.estimated_cost_min !== undefined ? (
                              <span>₹{est.estimated_cost_min.toLocaleString()} – ₹{est.estimated_cost_max?.toLocaleString()}</span>
                            ) : (
                              <span className="text-slate-500">Unestimated</span>
                            )}
                          </td>
                          <td className="p-3 font-mono text-emerald-300">
                            {ev.cost_effectiveness_label}
                          </td>
                          <td className="p-3 font-mono">{est.estimated_manpower ? `${est.estimated_manpower} crew` : '—'}</td>
                          <td className="p-3 font-mono">{est.estimated_duration_hours ? `${est.estimated_duration_hours} hrs` : '—'}</td>
                          <td className="p-3">{getConfidenceBadge(est.cost_confidence)}</td>
                          <td className="p-3">
                            <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-amber-950/40 text-amber-300 border border-amber-500/30">
                              PROPOSED
                            </span>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ===================================================================== */}
      {/* 5. Executive Municipal Mitigation Brief Modal */}
      {/* ===================================================================== */}
      {showBriefModal && briefResponse && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm">
          <div className="glass-panel rounded-2xl w-full max-w-4xl max-h-[90vh] flex flex-col border border-brand-cyan/40 bg-navy-950 shadow-glow-card">
            {/* Modal Header */}
            <div className="flex items-center justify-between p-6 border-b border-navy-800">
              <div className="flex items-center gap-2.5">
                <div className="p-2 rounded-lg bg-brand-cyan/10 border border-brand-cyan/30 text-brand-cyan">
                  <FileText className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-white">
                    Executive Municipal Mitigation Brief Preview
                  </h3>
                  <span className="text-[10px] font-mono text-amber-300">
                    STATUS: PROPOSED — Not an administrative expenditure commitment
                  </span>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <Button size="sm" variant="primary" onClick={handleDownloadMarkdown} className="gap-1.5 text-xs">
                  <Download className="w-3.5 h-3.5" />
                  <span>Download Markdown (.md)</span>
                </Button>
                <button
                  onClick={() => setShowBriefModal(false)}
                  className="p-1.5 text-slate-400 hover:text-white rounded-lg hover:bg-navy-900 transition-colors"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
            </div>

            {/* Modal Content */}
            <div className="p-6 overflow-y-auto space-y-6 text-xs text-slate-300 font-mono">
              <div className="p-4 rounded-xl bg-navy-900 border border-navy-800 space-y-2">
                <div className="flex items-center justify-between font-bold text-white">
                  <span>Target: {briefResponse.brief.incident_title}</span>
                  <span className="text-brand-cyan">Brief ID: {briefResponse.brief.brief_id}</span>
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-[11px] text-slate-400">
                  <span>Baseline: {briefResponse.brief.baseline_score.toFixed(1)} ({briefResponse.brief.baseline_level})</span>
                  <span>Projected: {briefResponse.brief.projected_score.toFixed(1)} ({briefResponse.brief.projected_level})</span>
                  <span>Reduction: -{briefResponse.brief.projected_risk_reduction.toFixed(1)} pts</span>
                  <span>Recommended: {briefResponse.brief.recommended_scenario_name}</span>
                </div>
              </div>

              {/* Raw Markdown Render Preview */}
              <div className="space-y-2">
                <span className="text-xs font-bold text-slate-200 uppercase tracking-wider block">
                  Markdown Report Export Content:
                </span>
                <pre className="p-4 rounded-xl bg-navy-950 border border-navy-800 text-[11px] text-slate-300 overflow-x-auto whitespace-pre-wrap leading-relaxed">
                  {briefResponse.markdown_content}
                </pre>
              </div>
            </div>

            {/* Modal Footer */}
            <div className="p-4 border-t border-navy-800 flex items-center justify-between text-[11px] font-mono text-slate-500">
              <span>Generated by: {briefResponse.generated_by}</span>
              <Button size="sm" variant="secondary" onClick={() => setShowBriefModal(false)}>
                Close Preview
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default MitigationPlannerPage;
